"""CHIRPS monthly rainfall → rainfall anomaly and SPI-3 per hex (SDD §9.2, §12.2).

    python manage.py ingest_chirps UGA                       # 2015-01 → latest available
    python manage.py ingest_chirps UGA --start 2024-01 --end 2024-12

Source: CHIRPS v2.0 monthly COGs on Digital Earth Africa (`rainfall_chirps_monthly`); months
missing there are taken from the UCSB CHC archive (same product). The
1991–2020 baseline months are read too (cached), so anomalies and SPI can be computed, but only
the requested display months are written. Rainfall totals are published as COGs (raster layer).
"""

from __future__ import annotations

from datetime import date

import numpy as np
from django.core.management.base import BaseCommand, CommandError
from rasterio.enums import Resampling

from apps.catalog.models import Indicator
from apps.ingest import stats
from apps.ingest.cache import cache_dir, download, sha256_text
from apps.ingest.common import country_grid, get_country, parallel_map, publish_cog
from apps.ingest.grid import cached, read_to_grid
from apps.ingest.run import IngestRun
from apps.ingest.sources import DEA_ENV, dea_client, gdal_path, search
from apps.ingest.writer import write_indicator
from apps.ingest.zonal import HexWeights, load_hexes

COLLECTION = "rainfall_chirps_monthly"
RES = 0.05  # native CHIRPS grid; bounds snap to it so no resampling happens
SPI_SCALE = 3
CHC_MONTHLY = "https://data.chc.ucsb.edu/products/CHIRPS/v2.0/africa_monthly/tifs/chirps-v2.0.{m:%Y.%m}.tif.gz"


class Command(BaseCommand):
    help = "Ingest CHIRPS monthly rainfall: rain_anom_pct and spi3 per hex."

    def add_arguments(self, parser):
        parser.add_argument("iso3")
        parser.add_argument("--start", default="2015-01", help="First month to write (YYYY-MM)")
        parser.add_argument("--end", help="Last month to write (default: latest available)")
        parser.add_argument("--baseline", default="1991:2020", help="Baseline years")
        parser.add_argument("--no-cogs", action="store_true", help="Skip publishing COGs")

    def handle(self, *args, iso3, start, end, baseline, no_cogs, **opts):
        country = get_country(iso3)
        grid = country_grid(country, RES, pad=RES)
        b0, b1 = (int(y) for y in baseline.split(":"))
        show_start = stats.parse_month(start)
        # SPI-3 for the first display month needs the two months before it.
        y, m = show_start.year, show_start.month - (SPI_SCALE - 1)
        while m < 1:
            y, m = y - 1, m + 12
        read_start = min(date(b0, 1, 1), date(y, m, 1))
        today = date.today()
        read_end = stats.parse_month(end) if end else date(today.year, today.month, 1)

        self.stdout.write(f"Searching {COLLECTION} {read_start:%Y-%m} → {read_end:%Y-%m} …")
        items = search(dea_client(), COLLECTION, grid.bounds, read_start, stats.month_end(read_end))
        by_month = {}
        for it in items:
            d = (
                it.datetime.date()
                if it.datetime
                else date.fromisoformat(it.properties["start_datetime"][:10])
            )
            by_month[date(d.year, d.month, 1)] = gdal_path(it.assets["rainfall"].href)
        if not by_month:
            raise CommandError("No CHIRPS items found")
        last = max(by_month)
        if not end:
            read_end = last
        months = stats.month_range(read_start, read_end)
        show = [mo for mo in months if mo >= show_start]

        with IngestRun(
            "chirps",
            version_label=f"{show[0]:%Y-%m}…{show[-1]:%Y-%m}",
            params={
                "iso3": country.iso3,
                "start": start,
                "end": f"{read_end:%Y-%m}",
                "baseline": baseline,
                "grid": grid.key,
            },
            echo=self.stdout.write,
        ) as run:
            # DE Africa's catalogue has a few holes; fill them from the CHC archive (same
            # product and grid), downloaded once and read through /vsigzip/.
            gaps = [mo for mo in months if mo not in by_month]
            filled = []
            for mo in gaps:
                url = CHC_MONTHLY.format(m=mo)
                try:
                    path = download(url, cache_dir("chirps", "chc") / url.rsplit("/", 1)[1])
                except Exception as e:  # recorded below as a missing month
                    self.stdout.write(f"  CHC fallback failed for {mo:%Y-%m}: {e}")
                    continue
                by_month[mo] = f"/vsigzip/{path}"
                filled.append(f"{mo:%Y-%m}")
            run.check(
                "DE Africa gaps filled from CHC archive",
                len(filled) == len(gaps),
                {"gaps": [f"{mo:%Y-%m}" for mo in gaps], "filled": filled},
            )
            missing = [f"{mo:%Y-%m}" for mo in months if mo not in by_month]
            run.check("no missing months", not missing, {"missing": missing[:24]})
            hrefs = [by_month[mo] for mo in months]
            run.sources.extend(hrefs)
            run.checksum = sha256_text(*hrefs)

            cdir = cache_dir("chirps", country.iso3.lower(), grid.key)

            def load(mo_href):
                mo, href = mo_href
                return cached(
                    cdir / f"{mo:%Y-%m}.npy",
                    lambda: read_to_grid(href, grid, resampling=Resampling.nearest, env=DEA_ENV),
                )

            stack = np.stack(
                parallel_map(
                    load,
                    list(zip(months, hrefs, strict=True)),
                    echo=self.stdout.write,
                    label="months read",
                )
            )
            run.check_range("monthly rainfall (mm)", stack, 0, 2500)

            hexes = load_hexes(country.id)
            self.stdout.write(f"Zonal weights for {len(hexes)} hexes …")
            W = HexWeights(hexes, grid)
            rain = W.mean(stack).astype("float64")  # (n_hex, T)

            cal = np.array([mo.month for mo in months])
            base = np.array([b0 <= mo.year <= b1 for mo in months])
            run.check(
                "baseline complete",
                base.sum() == (b1 - b0 + 1) * 12,
                {"baseline_months": int(base.sum())},
            )
            clim = stats.climatology(rain, cal, base)
            anom = stats.pct_of_mean(rain, cal, clim)
            spi3 = stats.spi(rain, cal, base, SPI_SCALE)

            sel = np.array([mo >= show_start for mo in months])
            labels = [f"{mo:%Y-%m}" for mo in show]
            for key, values, lo, hi in (
                ("rain_anom_pct", anom[:, sel], 0, 2000),
                ("spi3", spi3[:, sel], -3, 3),
            ):
                run.check_range(key, values, lo, hi)
                run.check_completeness(key, values, hexes.land, labels)
                n = write_indicator(
                    Indicator.objects.get(key=key), run.version.id, hexes.h3, show, values
                )
                run.record(key, values, show, n)
                self.stdout.write(f"  {key}: {n} rows")

            if not no_cogs:
                idx = {mo: i for i, mo in enumerate(months)}
                for mo in show:
                    publish_cog(
                        stack[idx[mo]],
                        grid,
                        run.version,
                        iso3=country.iso3,
                        name=f"rainfall_{mo:%Y-%m}",
                        period=mo,
                    )
                self.stdout.write(f"  published {len(show)} rainfall COGs")

            run.data_date = stats.month_end(show[-1])
            run.notes = "CHIRPS v2.0 via Digital Earth Africa; anomaly vs 1991–2020 monthly mean"
