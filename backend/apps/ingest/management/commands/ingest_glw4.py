"""GLW4 (2015) → livestock density per hex: cattle, goats, sheep and TLU (SDD §9.3).

    python manage.py ingest_glw4 UGA

Source: FAO Gridded Livestock of the World v4, 2015, dasymetric ("Da") heads per pixel at
5 arc-minutes, from Harvard Dataverse (CC0). Heads per hex = Σ pixel heads × share of the pixel
inside the hex; density = heads ÷ hex area. TLU factors: cattle 0.7, sheep/goat 0.1 (§9.3).
Not yet calibrated to census totals (SDD §8.5 `census`, pilot phase).
"""

from __future__ import annotations

from datetime import date

import numpy as np
from django.core.management.base import BaseCommand
from rasterio.enums import Resampling

from apps.catalog.models import Indicator
from apps.ingest.cache import cache_dir, download, sha256, sha256_text
from apps.ingest.common import country_grid, get_country, publish_cog
from apps.ingest.grid import read_to_grid
from apps.ingest.run import IngestRun
from apps.ingest.writer import STATIC_PERIOD, write_indicator
from apps.ingest.zonal import HexWeights, load_hexes

DATAFILE = "https://dataverse.harvard.edu/api/access/datafile/{id}"
RES = 1 / 12  # 5 arc-minutes, the GLW4 grid

# key, species, Dataverse DOI, datafile id of "5_<sp>_2015_Da.tif", TLU factor
SPECIES = [
    ("cattle_density", "cattle", "doi:10.7910/DVN/LHBICE", 6769711, 0.7),
    ("goat_density", "goats", "doi:10.7910/DVN/YYG6ET", 6769696, 0.1),
    ("sheep_density", "sheep", "doi:10.7910/DVN/VZOYHM", 6769626, 0.1),
]
# Plausible national cattle totals (heads) for a sanity check; outside → warning.
CATTLE_TOTAL_RANGE = (1e6, 6e7)


class Command(BaseCommand):
    help = "Ingest FAO GLW4 2015 livestock densities (cattle, goats, sheep, TLU) per hex."

    def add_arguments(self, parser):
        parser.add_argument("iso3")
        parser.add_argument("--no-cogs", action="store_true")

    def handle(self, *args, iso3, no_cogs, **opts):
        country = get_country(iso3)
        grid = country_grid(country, RES)
        hexes = load_hexes(country.id)
        W = HexWeights(hexes, grid)
        cdir = cache_dir("glw4")

        with IngestRun(
            "glw4",
            version_label="GLW4-2015",
            params={"iso3": country.iso3, "grid": grid.key},
            echo=self.stdout.write,
        ) as run:
            tlu = np.zeros(len(hexes), dtype="float64")
            checksums = []
            for key, species, doi, file_id, factor in SPECIES:
                path = download(DATAFILE.format(id=file_id), cdir / f"{species}_2015_Da.tif")
                checksums.append(sha256(path))
                run.sources.append(f"{doi} datafile {file_id}")
                heads_px = read_to_grid(str(path), grid, resampling=Resampling.nearest)
                run.check_range(f"{species} heads per pixel", heads_px, 0, 1e7)
                heads = W.sum(heads_px)[:, 0].astype("float64")
                total = float(heads.sum())
                run.stats[f"{species}_total_heads"] = round(total)
                if species == "cattle":
                    lo, hi = CATTLE_TOTAL_RANGE
                    run.check(
                        "national cattle total plausible",
                        lo <= total <= hi,
                        {"heads": round(total)},
                        level="warn",
                    )
                density = (heads / hexes.area_km2).astype("float32")
                tlu += heads * factor
                self._write(run, key, hexes, density)
                if not no_cogs:
                    cell_km2 = (RES * 111.32) ** 2 * np.cos(
                        np.radians(grid.north - (np.arange(grid.shape[0]) + 0.5) * RES)
                    )[:, None]
                    publish_cog(
                        heads_px / cell_km2,
                        grid,
                        run.version,
                        iso3=country.iso3,
                        name=f"{species}_density_2015",
                        period=None,
                    )

            self._write(run, "tlu_density", hexes, (tlu / hexes.area_km2).astype("float32"))
            run.checksum = sha256_text(*checksums)
            run.data_date = date(2015, 12, 31)
            run.notes = "GLW4 2015 dasymetric; TLU = 0.7 cattle + 0.1 (sheep + goats); uncalibrated"

    def _write(self, run, key, hexes, values):
        run.check_range(key, values, 0, 10000)
        run.check_completeness(key, values, hexes.land)
        n = write_indicator(
            Indicator.objects.get(key=key), run.version.id, hexes.h3, [STATIC_PERIOD], values
        )
        run.record(key, values, [STATIC_PERIOD], n)
        self.stdout.write(f"  {key}: {n} rows")
