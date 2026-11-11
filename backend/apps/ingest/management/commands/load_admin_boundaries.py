"""Load OCHA COD-AB admin boundaries for a country (SDD §8.5 admin_*, Appendix A step 1).

    python manage.py load_admin_boundaries UGA
    python manage.py load_admin_boundaries UGA --source /data/cache/admin/uga.gdb.zip

Reads layers `<iso3>_admin1..N` with `admN_pcode` / `admN_name` columns (the COD-AB schema),
loads them as boundary version `COD-AB-<valid_on year>-<version>`, links parents by pcode and
closes (valid_to) any older version. Idempotent per boundary version.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import geopandas as gpd
import pandas as pd
import pyogrio
from django.contrib.gis.geos import GEOSGeometry, MultiPolygon
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from shapely import make_valid
from shapely.geometry import MultiPolygon as ShpMulti

from apps.geo.models import AdminUnit
from apps.ingest.cache import cache_dir, download, http_json, sha256
from apps.ingest.common import get_country
from apps.ingest.run import IngestRun

HDX_PACKAGE = "https://data.humdata.org/api/3/action/package_show?id={id}"
FORMAT_PREFERENCE = (".gdb.zip", ".gpkg.zip", ".gpkg", ".shp.zip")


def _hdx_resource(package_id: str) -> tuple[str, str]:
    pkg = http_json(HDX_PACKAGE.format(id=package_id))["result"]
    by_name = {r["name"]: r["url"] for r in pkg["resources"]}
    for suffix in FORMAT_PREFERENCE:
        for name, url in by_name.items():
            if name.lower().endswith(suffix):
                return name, url
    raise CommandError(f"No GIS resource in HDX package {package_id}: {list(by_name)}")


def _to_multi(geom) -> MultiPolygon:
    g = make_valid(geom)
    if g.geom_type == "GeometryCollection":
        g = ShpMulti([p for p in g.geoms if p.geom_type == "Polygon"])
    if g.geom_type == "Polygon":
        g = ShpMulti([g])
    out = GEOSGeometry(memoryview(g.wkb), srid=4326)
    if not isinstance(out, MultiPolygon):
        raise ValueError(f"unexpected geometry {g.geom_type}")
    return out


class Command(BaseCommand):
    help = "Load COD-AB admin boundaries (all levels) from HDX or a local file."

    def add_arguments(self, parser):
        parser.add_argument("iso3")
        parser.add_argument("--source", help="Local path or URL (default: HDX COD-AB package)")
        parser.add_argument("--max-level", type=int, help="Deepest level (default: config)")

    def handle(self, *args, iso3: str, source: str | None, max_level: int | None, **opts):
        country = get_country(iso3)
        iso = country.iso3.lower()
        max_level = max_level or max(lv["level"] for lv in country.admin_levels)

        if source and not source.startswith("http"):
            path, origin = source, source
        else:
            if source:
                name, url = source.rsplit("/", 1)[-1], source
            else:
                pkg = country.sources.get("hdx_cod_ab")
                if not pkg:
                    raise CommandError(f"{country.iso3}: set sources.hdx_cod_ab in geo.Country")
                name, url = _hdx_resource(pkg)
            self.stdout.write(f"Downloading {name} …")
            path, origin = str(download(url, cache_dir("admin", iso) / name)), url

        layers = {name for name, _ in pyogrio.list_layers(path)}
        frames: dict[int, gpd.GeoDataFrame] = {}
        for level in range(0, max_level + 1):
            layer = f"{iso}_admin{level}"
            if layer not in layers:
                raise CommandError(f"Layer {layer} not found in {path}: {sorted(layers)}")
            frames[level] = gpd.read_file(path, layer=layer)

        meta = frames[0].iloc[0]
        valid_on = pd.Timestamp(meta["valid_on"]).date() if pd.notna(meta["valid_on"]) else None
        version = f"COD-AB-{valid_on.year if valid_on else 'undated'}-{meta.get('version') or 'v'}"

        with IngestRun(
            f"admin_{iso}",
            version_label=version,
            params={"iso3": country.iso3, "source": origin, "max_level": max_level},
            echo=self.stdout.write,
        ) as run:
            run.sources.append(origin)
            run.checksum = sha256(Path(path))
            run.data_date = valid_on or timezone.localdate()
            self._load(run, country, frames, version, valid_on, max_level)

    def _load(self, run, country, frames, version, valid_on: date | None, max_level: int):
        adm0_area = float(frames[0]["area_sqkm"].iloc[0]) if "area_sqkm" in frames[0] else None
        units_by_code: dict[str, AdminUnit] = {}
        for level in range(1, max_level + 1):
            gdf = frames[level]
            run.check(f"L{level} CRS is EPSG:4326", gdf.crs.to_epsg() == 4326, str(gdf.crs))
            code_col, name_col = f"adm{level}_pcode", f"adm{level}_name"
            parent_col = f"adm{level - 1}_pcode"
            run.check(
                f"L{level} pcodes unique",
                gdf[code_col].is_unique,
                {"duplicates": gdf[code_col][gdf[code_col].duplicated()].tolist()[:10]},
            )
            if level > 1:
                missing = sorted(set(gdf[parent_col]) - set(units_by_code))
                run.check(f"L{level} parents exist", not missing, {"missing": missing[:10]})
            if adm0_area:
                area = float(gdf["area_sqkm"].sum())
                run.check(
                    f"L{level} area matches country (±1 %)",
                    abs(area - adm0_area) / adm0_area < 0.01,
                    {"units_km2": round(area), "country_km2": round(adm0_area)},
                    level="warn",
                )

            for row in gdf.itertuples(index=False):
                code = getattr(row, code_col)
                unit, _ = AdminUnit.objects.update_or_create(
                    country=country,
                    level=level,
                    code=code,
                    boundary_version=version,
                    defaults={
                        "name": getattr(row, name_col),
                        "parent": units_by_code.get(getattr(row, parent_col))
                        if level > 1
                        else None,
                        "valid_from": valid_on,
                        "valid_to": None,
                        "geom": _to_multi(row.geometry),
                    },
                )
                units_by_code[code] = unit
            run.stats[f"level_{level}"] = {"units": len(gdf)}
            self.stdout.write(f"  L{level}: {len(gdf)} units")

        closed = (
            AdminUnit.objects.filter(country=country, valid_to__isnull=True)
            .exclude(boundary_version=version)
            .update(valid_to=valid_on or timezone.localdate())
        )
        run.notes = f"{version}; closed {closed} units from older versions"
