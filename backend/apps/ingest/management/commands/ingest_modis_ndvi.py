"""MODIS NDVI → NDVI anomaly (z) and VCI per hex (SDD §9.1, §12.2).

    python manage.py ingest_modis_ndvi UGA                    # 2015-01 → last full month
    python manage.py ingest_modis_ndvi UGA --start 2026-01

Source: MOD13Q1 v061 (Terra, 16-day, 250 m) on Microsoft Planetary Computer. Composites are read
from the 1 km COG overview onto a 0.01° grid (≈ 5 cells per res-7 hex), monthly NDVI is the mean
of the composites that start in that month, and the baseline is 2001–2020 (SDD §9.1).
Fill (-3000) and values outside the valid range are dropped; no QA-band masking yet (method note).
"""

from __future__ import annotations

import warnings
from collections import defaultdict
from datetime import date

import numpy as np
from django.core.management.base import BaseCommand, CommandError

from apps.catalog.models import Indicator
from apps.ingest import stats
from apps.ingest.cache import cache_dir, sha256_text
from apps.ingest.common import country_grid, get_country, parallel_map, publish_cog
from apps.ingest.grid import cached, mosaic, read_to_grid, with_retries
from apps.ingest.run import IngestRun
from apps.ingest.sources import PcSigner, gdal_path, pc_client, search
from apps.ingest.writer import write_indicator
from apps.ingest.zonal import HexWeights, load_hexes

COLLECTION = "modis-13Q1-061"
ASSET = "250m_16_days_NDVI"
RES = 0.01
FILL = -3000
VALID = (-2000, 10000)
SCALE = 1e-4
Z_CLIP = 5.0  # |z| beyond this is clipped (method note)


class Command(BaseCommand):
    help = "Ingest MODIS MOD13Q1 NDVI: ndvi_anom_z and vci per hex."

    def add_arguments(self, parser):
        parser.add_argument("iso3")
        parser.add_argument("--start", default="2015-01", help="First month to write (YYYY-MM)")
        parser.add_argument("--end", help="Last month (default: last complete month)")
        parser.add_argument("--baseline", default="2001:2020")
        parser.add_argument("--no-cogs", action="store_true")

    def handle(self, *args, iso3, start, end, baseline, no_cogs, **opts):
        country = get_country(iso3)
        grid = country_grid(country, RES)
        b0, b1 = (int(y) for y in baseline.split(":"))
        show_start = stats.parse_month(start)
        today = date.today()
        read_end = stats.parse_month(end) if end else date(today.year, today.month, 1)
        read_start = min(date(b0, 1, 1), show_start)

        self.stdout.write(f"Searching {COLLECTION} {read_start:%Y-%m} → {read_end:%Y-%m} …")
        found = search(pc_client(), COLLECTION, grid.bounds, read_start, stats.month_end(read_end))
        # Reprocessed granules appear twice (same product/date/tile, new production stamp in
        # the id's last part): keep only the newest.
        latest: dict[str, object] = {}
        for it in sorted(found, key=lambda it: it.id):
            latest[it.id.rsplit(".", 1)[0]] = it
        found = list(latest.values())

        def by_platform(prefix: str) -> dict[date, dict[date, list]]:
            """month → composite start date → tile items, for one platform."""
            out: dict[date, dict[date, list]] = defaultdict(lambda: defaultdict(list))
            for it in found:
                if it.id.startswith(prefix):
                    d = date.fromisoformat(it.properties["start_datetime"][:10])
                    out[date(d.year, d.month, 1)][d].append(it)
            return out

        terra, aqua = by_platform("MOD13Q1"), by_platform("MYD13Q1")
        if not terra:
            raise CommandError("No MOD13Q1 items found")
        if not end:  # last month Terra has published
            read_end = max(terra)
        months = stats.month_range(read_start, read_end)

        # Terra is the series (consistent since 2000); Aqua fills a month only when Terra has
        # nothing for it. Months with neither stay empty (warning, or failure in the baseline).
        composites: dict[date, list] = {}
        by_month: dict[date, list[date]] = defaultdict(list)
        aqua_months = []
        for mo in months:
            source = terra.get(mo) or aqua.get(mo)
            if not terra.get(mo) and aqua.get(mo):
                aqua_months.append(f"{mo:%Y-%m}")
            for d, tiles in (source or {}).items():
                composites[d] = tiles
                by_month[mo].append(d)
        items = [it for tiles in composites.values() for it in tiles]

        with IngestRun(
            "modis_ndvi",
            version_label=f"{max(show_start, months[0]):%Y-%m}…{read_end:%Y-%m}",
            params={
                "iso3": country.iso3,
                "start": start,
                "end": f"{read_end:%Y-%m}",
                "baseline": baseline,
                "grid": grid.key,
                "platform": "Terra (MOD13Q1); Aqua (MYD13Q1) only for months Terra lacks",
            },
            echo=self.stdout.write,
        ) as run:
            missing = [mo for mo in months if not by_month.get(mo)]
            base_missing = [f"{mo:%Y-%m}" for mo in missing if b0 <= mo.year <= b1]
            run.check("baseline months all present", not base_missing, {"missing": base_missing})
            run.check(
                "every display month has composites",
                not missing,
                {
                    "missing": [f"{mo:%Y-%m}" for mo in missing][:24],
                    "note": "absent from Planetary Computer; backfill from LP DAAC (Earthdata)",
                },
                level="warn",
            )
            run.check(
                "Terra series used", not aqua_months, {"aqua_months": aqua_months}, level="warn"
            )
            tiles = {len(v) for v in composites.values()}
            run.check(
                "same tile count per composite",
                len(tiles) == 1,
                {"tiles": sorted(tiles)},
                level="warn",
            )
            run.sources.extend(sorted(it.id for it in items))
            run.checksum = sha256_text(*sorted(it.id for it in items))

            signer = PcSigner()
            cdir = cache_dir("modis_ndvi", country.iso3.lower(), grid.key)

            def fetch(item) -> None:  # fills the on-disk cache; arrays are loaded per month
                href = item.assets[ASSET].href
                cached(
                    cdir / f"{item.id}.npy",
                    lambda: with_retries(
                        lambda: read_to_grid(
                            gdal_path(signer.sign(href)),
                            grid,
                            nodata=FILL,
                            valid_range=VALID,
                            scale=SCALE,
                        )
                    ),
                )

            parallel_map(
                fetch,
                sorted(items, key=lambda it: it.id),
                echo=self.stdout.write,
                label="tiles read",
            )

            monthly = np.full((len(months), *grid.shape), np.nan, dtype="float32")
            for i, mo in enumerate(months):
                layers = [
                    mosaic((np.load(cdir / f"{it.id}.npy") for it in composites[d]), grid)
                    for d in sorted(by_month.get(mo, []))
                ]
                if layers:
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore", RuntimeWarning)  # all-NaN pixels
                        monthly[i] = np.nanmean(np.stack(layers), axis=0)
            run.check_range("monthly NDVI", monthly, -0.2, 1.0)

            hexes = load_hexes(country.id)
            self.stdout.write(f"Zonal weights for {len(hexes)} hexes …")
            ndvi = HexWeights(hexes, grid).mean(monthly).astype("float64")

            cal = np.array([mo.month for mo in months])
            base = np.array([b0 <= mo.year <= b1 for mo in months])
            clim = stats.climatology(ndvi, cal, base)
            sel = np.array([mo >= show_start for mo in months])
            show = [mo for mo in months if mo >= show_start]
            labels = [f"{mo:%Y-%m}" for mo in show]
            # Vegetation indices over open water are noise: mostly-water hexes get no value.
            z = stats.zscore(ndvi, cal, clim)[:, sel]
            v = stats.vci(ndvi, cal, clim)[:, sel]
            z[~hexes.land] = np.nan
            v[~hexes.land] = np.nan
            # Shoreline/wetland hexes with a near-constant baseline give huge |z|; clip (noted).
            clipped = int((np.abs(z) > Z_CLIP).sum())
            run.stats["ndvi_anom_z_clipped"] = {
                "limit": Z_CLIP,
                "values": clipped,
                "share": round(clipped / max(1, int(np.isfinite(z).sum())), 5),
            }
            z = np.clip(z, -Z_CLIP, Z_CLIP)
            run.stats["water_hexes_skipped"] = int((~hexes.land).sum())
            for key, values, lo, hi in (
                ("ndvi_anom_z", z, -Z_CLIP, Z_CLIP),
                ("vci", v, 0, 100),
            ):
                run.check_range(key, values, lo, hi)
                run.check_completeness(key, values, hexes.land, labels)
                n = write_indicator(
                    Indicator.objects.get(key=key), run.version.id, hexes.h3, show, values
                )
                run.record(key, values, show, n)
                self.stdout.write(f"  {key}: {n} rows")

            if not no_cogs:
                for i, mo in enumerate(months):
                    if mo >= show_start:
                        publish_cog(
                            monthly[i],
                            grid,
                            run.version,
                            iso3=country.iso3,
                            name=f"ndvi_{mo:%Y-%m}",
                            period=mo,
                        )
                self.stdout.write(f"  published {len(show)} NDVI COGs")

            run.data_date = stats.month_end(show[-1])
            run.notes = (
                "MOD13Q1 v061 Terra via Planetary Computer, 1 km overview; baseline " + baseline
            )
