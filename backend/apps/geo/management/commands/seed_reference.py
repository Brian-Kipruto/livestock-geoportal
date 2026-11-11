"""Seed reference configuration: countries, dataset catalogue, indicators, POI types, layers.

Idempotent (update_or_create on natural keys). Source of truth: SDD §8.5, §9, §11.3.
"""

from django.contrib.gis.geos import Polygon
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.catalog.models import Dataset, Indicator, Layer
from apps.geo.models import Country
from apps.poi.models import PoiType

BIMODAL_SEASONS = [
    {"key": "long_rains", "label": "Long rains", "months": [3, 4, 5]},
    {"key": "short_rains", "label": "Short rains", "months": [10, 11, 12]},
]

COUNTRIES = [
    {
        "iso3": "UGA",
        "name": "Uganda",
        "bbox": (29.5, -1.5, 35.1, 4.3),
        "admin_levels": [
            {"level": 1, "label": "Region"},
            {"level": 2, "label": "District"},
            {"level": 3, "label": "Sub-county"},
        ],
        "languages": ["en", "sw"],
    },
    {
        "iso3": "KEN",
        "name": "Kenya",
        "bbox": (33.9, -4.8, 41.95, 5.1),
        "admin_levels": [
            {"level": 1, "label": "County"},
            {"level": 2, "label": "Sub-county"},
            {"level": 3, "label": "Ward"},
        ],
        "languages": ["en", "sw"],
    },
]

# key, name, provider, licence, url, cadence, access
DATASETS = [
    (
        "admin_uga",
        "Uganda COD-AB boundaries",
        "UBOS via OCHA/HDX",
        "CC BY-IGO",
        "https://data.humdata.org",
        "ad-hoc",
        "public",
    ),
    (
        "admin_ken",
        "Kenya COD-AB boundaries",
        "KNBS via OCHA/HDX",
        "CC BY-IGO",
        "https://data.humdata.org",
        "ad-hoc",
        "public",
    ),
    (
        "modis_ndvi",
        "MODIS MOD13Q1 NDVI",
        "NASA LP DAAC",
        "Public domain",
        "https://lpdaac.usgs.gov",
        "16-day",
        "public",
    ),
    (
        "s2_ndvi",
        "Sentinel-2 NDVI / geomedian",
        "Digital Earth Africa",
        "CC BY 4.0",
        "https://explorer.digitalearth.africa",
        "monthly",
        "public",
    ),
    (
        "wofs",
        "Water Observations from Space",
        "Digital Earth Africa",
        "CC BY 4.0",
        "https://explorer.digitalearth.africa",
        "monthly",
        "public",
    ),
    (
        "chirps",
        "CHIRPS rainfall",
        "UCSB Climate Hazards Center",
        "CC BY 4.0",
        "https://data.chc.ucsb.edu/products/",
        "monthly",
        "public",
    ),
    (
        "era5land",
        "ERA5-Land",
        "Copernicus C3S",
        "Copernicus licence",
        "https://cds.climate.copernicus.eu",
        "monthly",
        "public",
    ),
    (
        "cmip6",
        "NEX-GDDP-CMIP6",
        "NASA",
        "CC BY-SA 4.0",
        "https://registry.opendata.aws",
        "static",
        "public",
    ),
    (
        "glw4",
        "Gridded Livestock of the World 4",
        "FAO",
        "CC BY 4.0",
        "https://dataverse.harvard.edu",
        "static",
        "public",
    ),
    (
        "worldcover",
        "ESA WorldCover",
        "ESA",
        "CC BY 4.0",
        "https://esa-worldcover.org",
        "annual",
        "public",
    ),
    (
        "osm",
        "OpenStreetMap extract",
        "OSM contributors / Geofabrik",
        "ODbL",
        "https://download.geofabrik.de/africa/",
        "monthly",
        "public",
    ),
    (
        "travel",
        "Travel time to cities",
        "Malaria Atlas Project",
        "CC BY 4.0",
        "https://malariaatlas.org",
        "static",
        "public",
    ),
    (
        "worldpop",
        "WorldPop population",
        "WorldPop",
        "CC BY 4.0",
        "https://hub.worldpop.org",
        "annual",
        "public",
    ),
    (
        "wdpa",
        "Protected areas (WDPA)",
        "UNEP-WCMC",
        "Non-commercial — check",
        "https://protectedplanet.net",
        "quarterly",
        "public",
    ),
    (
        "gps",
        "Partner GPS collars",
        "Project partners",
        "Restricted — data sharing agreement",
        "",
        "ad-hoc",
        "restricted",
    ),
    (
        "markets_partner",
        "Partner livestock market data",
        "Project partners",
        "Partner agreement",
        "",
        "ad-hoc",
        "registered",
    ),
]

# key, name, unit, theme, value_chain, temporal, agg, higher_is_better, dataset
INDICATORS = [
    (
        "ndvi_anom_z",
        "NDVI anomaly",
        "z",
        "pasture_water",
        "upstream",
        "monthly",
        "mean",
        True,
        "modis_ndvi",
    ),
    (
        "vci",
        "Vegetation Condition Index",
        "%",
        "pasture_water",
        "upstream",
        "monthly",
        "mean",
        True,
        "modis_ndvi",
    ),
    (
        "water_freq",
        "Surface water frequency",
        "%",
        "pasture_water",
        "upstream",
        "monthly",
        "mean",
        True,
        "wofs",
    ),
    (
        "rain_anom_pct",
        "Rainfall vs long-term mean",
        "%",
        "climate",
        "midstream",
        "monthly",
        "mean",
        True,
        "chirps",
    ),
    (
        "spi3",
        "Drought index (SPI-3)",
        "SPI",
        "climate",
        "midstream",
        "monthly",
        "mean",
        True,
        "chirps",
    ),
    (
        "tlu_density",
        "Livestock density",
        "TLU/km²",
        "livestock",
        "upstream",
        "static",
        "sum",
        None,
        "glw4",
    ),
]

HAZARD_Z = {
    "breaks": [-1.5, -1.0, -0.5],
    "labels": ["emergency", "alert", "watch", "normal"],
    "provisional": True,
}

POI_TYPES = [
    ("water_point", "Water point", "upstream"),
    ("market", "Livestock market", "downstream"),
    ("vet_centre", "Veterinary centre", "midstream"),
    ("abattoir", "Abattoir", "downstream"),
    ("holding_ground", "Holding ground", "downstream"),
]

# key, name, kind, theme, indicator, dataset, vector_source, default_on, order
LAYERS = [
    ("ndvi_anom_z", "NDVI anomaly", "hex", "pasture_water", "ndvi_anom_z", None, "", True, 10),
    ("water_freq", "Surface water", "hex", "pasture_water", "water_freq", None, "", False, 20),
    ("water_points", "Water points", "vector", "pasture_water", None, "osm", "poi", True, 30),
    ("spi3", "Drought index (SPI-3)", "hex", "climate", "spi3", None, "", False, 10),
    ("rain_anom_pct", "Rainfall anomaly", "hex", "climate", "rain_anom_pct", None, "", False, 20),
    ("tlu_density", "Livestock density", "hex", "livestock", "tlu_density", None, "", False, 10),
    ("herd_tracks", "GPS herd tracks", "hex", "movement", None, "gps", "", False, 20),
    ("markets", "Markets", "vector", "markets", None, "markets_partner", "poi", False, 10),
    (
        "admin_units",
        "Admin boundaries",
        "vector",
        "boundaries",
        None,
        "admin_uga",
        "admin_unit",
        True,
        10,
    ),
]


class Command(BaseCommand):
    help = "Seed countries, dataset catalogue, indicators, POI types and layers (idempotent)."

    @transaction.atomic
    def handle(self, *args, **opts):
        for c in COUNTRIES:
            Country.objects.update_or_create(
                iso3=c["iso3"],
                defaults={
                    "name": c["name"],
                    "admin_levels": c["admin_levels"],
                    "seasons": BIMODAL_SEASONS,
                    "default_bbox": Polygon.from_bbox(c["bbox"]),
                    "languages": c["languages"],
                },
            )
        for key, name, prov, lic, url, cad, acc in DATASETS:
            Dataset.objects.update_or_create(
                key=key,
                defaults=dict(
                    name=name,
                    provider=prov,
                    licence=lic,
                    url=url,
                    update_cadence=cad,
                    access_level=acc,
                ),
            )
        for key, name, unit, theme, vc, temporal, agg, hib, ds in INDICATORS:
            Indicator.objects.update_or_create(
                key=key,
                defaults=dict(
                    name=name,
                    unit=unit,
                    theme=theme,
                    value_chain=vc,
                    temporal=temporal,
                    agg_method=agg,
                    higher_is_better=hib,
                    dataset=Dataset.objects.get(key=ds),
                    classes=HAZARD_Z if key == "ndvi_anom_z" else None,
                    method_doc=f"docs/methods/{key}.md",
                ),
            )
        for key, name, vc in POI_TYPES:
            PoiType.objects.update_or_create(key=key, defaults={"name": name, "value_chain": vc})
        for key, name, kind, theme, ind, ds, vsrc, on, order in LAYERS:
            Layer.objects.update_or_create(
                key=key,
                defaults=dict(
                    name=name,
                    kind=kind,
                    theme=theme,
                    vector_source=vsrc,
                    default_on=on,
                    sort_order=order,
                    indicator=Indicator.objects.get(key=ind) if ind else None,
                    dataset=Dataset.objects.get(key=ds) if ds else None,
                ),
            )
        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {len(COUNTRIES)} countries, {len(DATASETS)} datasets, "
                f"{len(INDICATORS)} indicators, {len(POI_TYPES)} POI types, {len(LAYERS)} layers"
            )
        )
