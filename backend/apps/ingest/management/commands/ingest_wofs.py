"""WOfS → annual surface-water frequency per hex, and the hex land fraction (SDD §9.1).

    python manage.py ingest_wofs UGA                     # 2015 → last complete year
    python manage.py ingest_wofs UGA --start 2020 --end 2024

Source: Digital Earth Africa `wofs_ls_summary_annual` (Landsat, 30 m) read from the COG overviews
onto a 0.005° grid. `water_freq` = mean % of clear observations that saw water, per hex and
year. DE Africa has no monthly WOfS summary, so the indicator is annual (SDD §9.1 asks monthly;
noted in the method note). `wofs_ls_summary_alltime` sets `geo_hexcell.land_frac` (1 − share of
the hex that is water ≥ 80 % of the time), which the completeness checks use to skip lakes.
"""

from __future__ import annotations

from datetime import date

import numpy as np
from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from apps.catalog.models import Indicator
from apps.ingest.cache import cache_dir, sha256_text
from apps.ingest.common import country_grid, get_country, parallel_map, publish_cog
from apps.ingest.grid import cached, mosaic, read_to_grid
from apps.ingest.run import IngestRun
from apps.ingest.sources import DEA_ENV, dea_client, gdal_path, search
from apps.ingest.writer import write_indicator
from apps.ingest.zonal import HexWeights, load_hexes

ANNUAL = "wofs_ls_summary_annual"
ALLTIME = "wofs_ls_summary_alltime"
RES = 0.005
PERMANENT = 0.8  # frequency ≥ 80 % = permanent water (SDD §9.1)


class Command(BaseCommand):
    help = "Ingest DE Africa WOfS annual summaries: water_freq per hex + hex land fraction."

    def add_arguments(self, parser):
        parser.add_argument("iso3")
        parser.add_argument("--start", type=int, default=2015)
        parser.add_argument("--end", type=int, help="Last year (default: last complete year)")
        parser.add_argument("--no-cogs", action="store_true")

    def handle(self, *args, iso3, start, end, no_cogs, **opts):
        country = get_country(iso3)
        grid = country_grid(country, RES)
        end = end or date.today().year - 1
        client = dea_client()
        cdir = cache_dir("wofs", country.iso3.lower(), grid.key)

        def read_mosaic(name: str, items, band: str = "frequency") -> np.ndarray:
            hrefs = sorted(gdal_path(it.assets[band].href) for it in items)

            def load(href):
                return read_to_grid(href, grid, env=DEA_ENV)

            return cached(
                cdir / f"{name}.npy",
                lambda: mosaic(parallel_map(load, hrefs, echo=self.stdout.write, label=name), grid),
            ), hrefs

        hexes = load_hexes(country.id)
        self.stdout.write(f"Zonal weights for {len(hexes)} hexes …")
        W = HexWeights(hexes, grid)

        with IngestRun(
            "wofs",
            version_label=f"{start}…{end}",
            params={"iso3": country.iso3, "start": start, "end": end, "grid": grid.key},
            echo=self.stdout.write,
        ) as run:
            # All-time summary → land fraction (used by completeness checks everywhere).
            items = search(client, ALLTIME, grid.bounds, date(1984, 1, 1), date.today())
            run.check("all-time summary found", bool(items), {"items": len(items)})
            alltime, hrefs = read_mosaic("alltime", items)
            run.sources.extend(hrefs)
            permanent = np.where(
                np.isnan(alltime), np.nan, (alltime >= PERMANENT).astype("float32")
            )
            water_share = W.mean(permanent, min_cover=0.0)[:, 0]
            land_frac = np.where(np.isfinite(water_share), 1 - water_share, 1.0)
            with connection.cursor() as cur:
                cur.execute("CREATE TEMP TABLE _lf (h3 h3index, f real) ON COMMIT DROP")
                with cur.copy("COPY _lf (h3, f) FROM STDIN") as cp:
                    for cell, f in zip(hexes.h3, land_frac, strict=True):
                        cp.write_row((cell, float(f)))
                cur.execute(
                    "UPDATE geo_hexcell h SET land_frac = _lf.f FROM _lf WHERE h.h3 = _lf.h3"
                )
                cur.execute("DROP TABLE _lf")
            hexes.land = land_frac >= 0.5
            run.stats["land_frac"] = {
                "water_hexes": int((land_frac < 0.5).sum()),
                "land_hexes": int((land_frac >= 0.5).sum()),
            }
            self.stdout.write(f"  land_frac set; {int((land_frac < 0.5).sum())} mostly-water hexes")

            # Annual frequency = Σ wet ÷ Σ clear observations. Using the count bands (no NaN,
            # 0 = no clear view) keeps the ratio exact at any overview level; the pre-2023
            # `frequency` files have no nodata tag, so their overviews smear NaN (≈ 30 % at 1/16).
            years = list(range(start, end + 1))
            wet, clear = [], []
            for y in years:
                items = search(client, ANNUAL, grid.bounds, date(y, 1, 1), date(y, 12, 31))
                if not items:
                    raise CommandError(f"No {ANNUAL} items for {y}")
                for band, acc in (("count_wet", wet), ("count_clear", clear)):
                    arr, hrefs = read_mosaic(f"{y}_{band}", items, band)
                    run.sources.extend(hrefs)
                    acc.append(arr)
            wet, clear = np.stack(wet), np.stack(clear)
            run.check_range("annual wet observations", wet, 0, 400)
            run.check_range("annual clear observations", clear, 0, 400)
            run.checksum = sha256_text(*run.sources)

            hex_wet, hex_clear = W.sum(wet), W.sum(clear)
            with np.errstate(invalid="ignore", divide="ignore"):
                values = np.where(hex_clear > 0, hex_wet / hex_clear * 100.0, np.nan)
                stack = np.where(clear > 0, wet / clear, np.nan).astype("float32")
            periods = [date(y, 1, 1) for y in years]
            run.check_range("water_freq", values, 0, 100)
            # Completeness over every hex (open water must have a value too).
            run.check_completeness(
                "water_freq", values, np.ones(len(hexes), bool), [str(y) for y in years]
            )
            n = write_indicator(
                Indicator.objects.get(key="water_freq"), run.version.id, hexes.h3, periods, values
            )
            run.record("water_freq", values, periods, n)
            self.stdout.write(f"  water_freq: {n} rows")

            if not no_cogs:
                for y, arr in zip(years, stack, strict=True):
                    publish_cog(
                        arr * 100.0,
                        grid,
                        run.version,
                        iso3=country.iso3,
                        name=f"water_freq_{y}",
                        period=date(y, 1, 1),
                    )

            run.data_date = date(end, 12, 31)
            run.notes = (
                "DE Africa WOfS annual summaries (Landsat); Σ count_wet ÷ Σ count_clear per hex "
                "at 0.005° from COG overviews"
            )
