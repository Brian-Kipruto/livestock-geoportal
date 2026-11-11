"""OpenStreetMap → roads, waterways and water points (SDD §8.5 `osm`, §9.4).

    python manage.py ingest_osm UGA                          # HOT exports on HDX (default)
    python manage.py ingest_osm UGA --provider geofabrik     # full .osm.pbf from Geofabrik
    python manage.py ingest_osm UGA --provider geofabrik --source /path/uganda.osm.pbf

Two ways to get the same OSM data:
- `hotosm` (default): HOT's per-country thematic exports on HDX (`hotosm_<iso3>_roads`,
  `_waterways`, `_points_of_interest`), GeoPackages on S3 — fast, refreshed weekly-ish. The POI
  export has `amenity` / `man_made` but not `natural`, so springs are not included.
- `geofabrik`: `<region>-latest.osm.pbf` read with GDAL's OSM driver (all tags; slow mirror days).

Keeps road classes that matter for livestock access, rivers/streams/canals, and water points
(wells, boreholes, taps, watering places, springs) as `water_point` POIs. Features are clipped
to the country's current boundaries. Idempotent: the country's OSM-sourced rows are replaced.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from email.utils import parsedate_to_datetime
from pathlib import Path

import geopandas as gpd
import pandas as pd
import pyogrio
from django.contrib.gis.geos import GEOSGeometry
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.db.models import Count

from apps.catalog.models import Dataset
from apps.geo.models import Road, Waterway
from apps.ingest.cache import cache_dir, download, http_json, http_text, sha256
from apps.ingest.common import get_country
from apps.ingest.run import IngestRun
from apps.poi.models import Poi, PoiType

GEOFABRIK = "https://download.geofabrik.de/{region}-latest.osm.pbf"
HDX_PACKAGE = "https://data.humdata.org/api/3/action/package_show?id={id}"

ROAD_CLASSES = [
    "motorway",
    "motorway_link",
    "trunk",
    "trunk_link",
    "primary",
    "primary_link",
    "secondary",
    "secondary_link",
    "tertiary",
    "tertiary_link",
    "unclassified",
    "track",
]
WATERWAY_CLASSES = ["river", "stream", "canal"]
# (tag, value) pairs that make a node a livestock-relevant water point.
WATER_POINT_TAGS = {
    ("amenity", "drinking_water"),
    ("amenity", "water_point"),
    ("amenity", "watering_place"),
    ("man_made", "water_well"),
    ("man_made", "borehole"),
    ("man_made", "water_tap"),
    ("natural", "spring"),
}
POI_ATTRS = ("operator", "access", "pump", "seasonal")
_TAG = re.compile(r'"((?:[^"\\]|\\.)*)"=>"((?:[^"\\]|\\.)*)"')


def parse_other_tags(s: str | None) -> dict[str, str]:
    """GDAL's OSM driver packs unlisted tags as `"k"=>"v","k2"=>"v2"`."""
    return dict(_TAG.findall(s or ""))


def water_point_kind(tags: dict[str, str]) -> str | None:
    for k, v in tags.items():
        if (k, v) in WATER_POINT_TAGS:
            return f"{k}={v}"
    return None


def _in_list(col: str, values: list[str] | set[str]) -> str:
    return f"{col} IN ({', '.join(repr(v) for v in sorted(values))})"


def osm_ref(v) -> tuple[int, str]:
    """`way/123` (HOT exports) or `123` (GDAL OSM driver) → (123, "way/123" | "123")."""
    text = str(v)
    return int(text.rsplit("/", 1)[-1]), text


def _clean(v) -> str:
    return "" if v is None or (isinstance(v, float) and pd.isna(v)) else str(v)


@dataclass
class OsmExtract:
    """Standardised frames: roads/ways have osm_id, name, class, geometry; points have tags."""

    roads: gpd.GeoDataFrame  # osm_id, name, highway, surface
    ways: gpd.GeoDataFrame  # osm_id, name, waterway
    points: gpd.GeoDataFrame  # osm_id, name, tags (dict)
    origin: str
    checksum: str
    data_date: date


def _lines(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Explode multi-lines; drop anything that isn't a line."""
    gdf = gdf[gdf.geometry.notna()].explode(index_parts=False)
    return gdf[gdf.geometry.geom_type == "LineString"]


def _points(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Mapped as areas (e.g. a reservoir-side watering place) → a point inside the shape."""
    gdf = gdf[gdf.geometry.notna()].copy()
    not_pt = gdf.geometry.geom_type != "Point"
    gdf.loc[not_pt, "geometry"] = gdf.loc[not_pt, "geometry"].representative_point()
    return gdf


def read_hotosm(iso: str, echo) -> OsmExtract:
    files, dates = {}, []
    for theme in ("roads", "waterways", "points_of_interest"):
        pkg = http_json(HDX_PACKAGE.format(id=f"hotosm_{iso}_{theme}"))["result"]
        res = next((r for r in pkg["resources"] if "GeoPackage" in r["name"]), None)
        if res is None:
            raise CommandError(f"No GeoPackage in HDX hotosm_{iso}_{theme}")
        dates.append(date.fromisoformat(pkg["last_modified"][:10]))
        stamp = pkg["last_modified"][:10]
        echo(f"Downloading HOT {theme} ({stamp}) …")
        files[theme] = download(
            res["url"], cache_dir("osm", iso, "hotosm", stamp) / f"{theme}.gpkg.zip"
        )

    roads = pyogrio.read_dataframe(
        files["roads"],
        columns=["id", "name", "highway", "surface"],
        where=_in_list("highway", ROAD_CLASSES),
    ).rename(columns={"id": "osm_id"})
    ways = pyogrio.read_dataframe(
        files["waterways"],
        columns=["id", "name", "waterway"],
        where=_in_list("waterway", WATERWAY_CLASSES),
    ).rename(columns={"id": "osm_id"})
    amen = {v for k, v in WATER_POINT_TAGS if k == "amenity"}
    made = {v for k, v in WATER_POINT_TAGS if k == "man_made"}
    pts = pyogrio.read_dataframe(
        files["points_of_interest"],
        columns=["id", "name", "amenity", "man_made"],
        where=f"{_in_list('amenity', amen)} OR {_in_list('man_made', made)}",
    ).rename(columns={"id": "osm_id"})
    pts["tags"] = [
        {k: v for k, v in (("amenity", a), ("man_made", m)) if _clean(v)}
        for a, m in zip(pts["amenity"], pts["man_made"], strict=True)
    ]
    checksum = "|".join(sha256(p)[:16] for p in files.values())
    return OsmExtract(
        roads=_lines(roads),
        ways=_lines(ways),
        points=_points(pts),
        origin=f"HDX hotosm_{iso}_{{roads,waterways,points_of_interest}}",
        checksum=checksum,
        data_date=min(dates),
    )


def read_geofabrik(country, source: str | None, echo) -> OsmExtract:
    iso = country.iso3.lower()
    if source:
        pbf, origin, data_date, md5 = Path(source), source, date.today(), sha256(Path(source))
    else:
        region = country.sources.get("geofabrik")
        if not region:
            raise CommandError(f"{country.iso3}: set sources.geofabrik in geo.Country")
        url = GEOFABRIK.format(region=region)
        # Geofabrik doesn't answer HEAD reliably; the .md5 file shares the extract's date.
        body, headers = http_text(url + ".md5")
        md5, modified = body.split()[0], headers.get("Last-Modified")
        data_date = parsedate_to_datetime(modified).date() if modified else date.today()
        echo(f"Downloading {url} (md5 {md5[:8]}) …")
        pbf = download(url, cache_dir("osm", iso) / f"{md5}.osm.pbf", timeout=1800)
        origin = url

    roads = pyogrio.read_dataframe(
        pbf,
        layer="lines",
        columns=["osm_id", "name", "highway", "other_tags"],
        where=_in_list("highway", ROAD_CLASSES),
    )
    roads["surface"] = [parse_other_tags(t).get("surface", "") for t in roads["other_tags"]]
    ways = pyogrio.read_dataframe(
        pbf,
        layer="lines",
        columns=["osm_id", "name", "waterway"],
        where=_in_list("waterway", WATERWAY_CLASSES),
    )
    pts = pyogrio.read_dataframe(
        pbf,
        layer="points",
        columns=["osm_id", "name", "man_made", "other_tags"],
        where="man_made IS NOT NULL OR other_tags LIKE '%amenity%' OR other_tags LIKE '%natural%'",
    )
    tags = []
    for other, man_made in zip(pts["other_tags"], pts["man_made"], strict=True):
        t = parse_other_tags(other)
        if _clean(man_made):
            t["man_made"] = man_made
        tags.append(t)
    pts["tags"] = tags
    return OsmExtract(
        roads=_lines(roads),
        ways=_lines(ways),
        points=_points(pts),
        origin=origin,
        checksum=md5,
        data_date=data_date,
    )


class Command(BaseCommand):
    help = "Ingest OSM roads, waterways and water points (HOT exports on HDX, or Geofabrik)."

    def add_arguments(self, parser):
        parser.add_argument("iso3")
        parser.add_argument("--provider", choices=["hotosm", "geofabrik"], default="hotosm")
        parser.add_argument("--source", help="Local .osm.pbf (geofabrik provider only)")

    def handle(self, *args, iso3, provider, source, **opts):
        country = get_country(iso3)
        echo = self.stdout.write
        if provider == "hotosm":
            osm_data = read_hotosm(country.iso3.lower(), echo)
        else:
            osm_data = read_geofabrik(country, source, echo)

        with IngestRun(
            "osm",
            version_label=f"{country.iso3} {osm_data.data_date:%Y-%m-%d} ({provider})",
            params={"iso3": country.iso3, "provider": provider, "source": osm_data.origin},
            echo=echo,
        ) as run:
            run.sources.append(osm_data.origin)
            run.checksum = osm_data.checksum
            run.data_date = osm_data.data_date
            self._load(run, country, osm_data)

    def _load(self, run, country, x: OsmExtract):
        osm = Dataset.objects.get(key="osm")
        version = run.version
        water_point = PoiType.objects.get(key="water_point")

        Road.objects.filter(country=country).delete()
        Waterway.objects.filter(country=country).delete()
        Poi.objects.filter(country=country, source_dataset=osm).delete()

        Road.objects.bulk_create(
            (
                Road(
                    country=country,
                    osm_id=osm_ref(r.osm_id)[0],
                    highway=r.highway,
                    name=_clean(r.name)[:200],
                    surface=_clean(r.surface)[:40],
                    dataset_version=version,
                    geom=GEOSGeometry(memoryview(r.geometry.wkb), srid=4326),
                )
                for r in x.roads.itertuples()
            ),
            batch_size=5000,
        )
        Waterway.objects.bulk_create(
            (
                Waterway(
                    country=country,
                    osm_id=osm_ref(r.osm_id)[0],
                    waterway=r.waterway,
                    name=_clean(r.name)[:200],
                    dataset_version=version,
                    geom=GEOSGeometry(memoryview(r.geometry.wkb), srid=4326),
                )
                for r in x.ways.itertuples()
            ),
            batch_size=5000,
        )
        pois = []
        for r in x.points.itertuples():
            kind = water_point_kind(r.tags)
            if kind:
                pois.append(
                    Poi(
                        country=country,
                        poi_type=water_point,
                        name=_clean(r.name)[:200],
                        external_id=f"osm:{osm_ref(r.osm_id)[1]}",
                        attributes={
                            "osm": kind,
                            **{k: r.tags[k] for k in POI_ATTRS if k in r.tags},
                        },
                        source_dataset=osm,
                        geom=GEOSGeometry(memoryview(r.geometry.wkb), srid=4326),
                    )
                )
        Poi.objects.bulk_create(pois, batch_size=5000)

        clipped = self._clip(country.id, osm.id)
        counts = {
            "roads": Road.objects.filter(country=country).count(),
            "waterways": Waterway.objects.filter(country=country).count(),
            "water_points": Poi.objects.filter(country=country, source_dataset=osm).count(),
        }
        by_class = dict(
            Road.objects.filter(country=country).values_list("highway").annotate(n=Count("id"))
        )
        run.stats.update(
            {"counts": counts, "clipped_outside_country": clipped, "roads_by_class": by_class}
        )
        run.check("roads loaded", counts["roads"] > 1000, counts)
        run.check(
            "primary/trunk roads present",
            by_class.get("primary", 0) + by_class.get("trunk", 0) > 0,
            by_class,
        )
        run.check("waterways loaded", counts["waterways"] > 0, counts, level="warn")
        run.check("water points loaded", counts["water_points"] > 0, counts, level="warn")
        for k, v in counts.items():
            self.stdout.write(f"  {k}: {v}")
        run.notes = f"{x.origin}; checksum {x.checksum}"

    def _clip(self, country_id: int, osm_dataset_id: int) -> dict[str, int]:
        """Drop features entirely outside the country's current level-1 boundaries."""
        out = {}
        with connection.cursor() as cur:
            cur.execute(
                "CREATE TEMP TABLE _cty ON COMMIT DROP AS SELECT ST_Union(geom) AS g "
                "FROM geo_adminunit WHERE country_id = %s AND level = 1 AND valid_to IS NULL",
                [country_id],
            )
            cur.execute("CREATE INDEX ON _cty USING gist (g)")
            for table, label, extra in (
                ("geo_road", "roads", ""),
                ("geo_waterway", "waterways", ""),
                ("poi_poi", "water_points", f"AND t.source_dataset_id = {int(osm_dataset_id)}"),
            ):
                cur.execute(
                    f"DELETE FROM {table} t USING _cty WHERE t.country_id = %s {extra} "  # noqa: S608
                    "AND _cty.g IS NOT NULL AND NOT ST_Intersects(t.geom, _cty.g)",
                    [country_id],
                )
                out[label] = cur.rowcount
            cur.execute("DROP TABLE _cty")
        return out
