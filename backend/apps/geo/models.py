"""Countries, admin hierarchy and the H3 grid (SDD §8.2–8.4, ADR-002, ADR-007)."""

from django.contrib.gis.db import models
from django.contrib.postgres.fields import ArrayField

from apps.common.fields import H3IndexField

ANALYSIS_RES = 7  # core analysis resolution
DISPLAY_RES = 6  # national display resolution
MOVEMENT_RES = 8  # movement detail resolution


class Country(models.Model):
    """Multi-country by configuration: everything country-specific lives here (NFR-10)."""

    iso3 = models.CharField(max_length=3, unique=True)
    name = models.CharField(max_length=120)
    admin_levels = models.JSONField(
        help_text='e.g. [{"level":1,"label":"Region"},{"level":2,"label":"District"}]'
    )
    seasons = models.JSONField(
        default=list,
        blank=True,
        help_text='e.g. [{"key":"long_rains","label":"Long rains","months":[3,4,5]}]',
    )
    default_bbox = models.PolygonField(srid=4326)
    languages = ArrayField(models.CharField(max_length=8), default=list)
    sources = models.JSONField(
        default=dict,
        blank=True,
        help_text='Source ids, e.g. {"hdx_cod_ab": "cod-ab-uga", "geofabrik": "africa/uganda"}',
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "countries"
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.iso3})"


class AdminUnit(models.Model):
    """Versioned admin boundaries — Ugandan districts split often, so keep versions."""

    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name="admin_units")
    level = models.PositiveSmallIntegerField()
    code = models.CharField(max_length=64, help_text="Official code (UBOS / KNBS / COD-AB pcode)")
    name = models.CharField(max_length=200)
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="children"
    )
    boundary_version = models.CharField(max_length=40, help_text="e.g. UBOS-2024, COD-AB-2020")
    valid_from = models.DateField(null=True, blank=True)
    valid_to = models.DateField(null=True, blank=True)
    geom = models.MultiPolygonField(srid=4326)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["country", "level", "code", "boundary_version"],
                name="admin_unit_unique_code_per_version",
            )
        ]
        indexes = [models.Index(fields=["country", "level"])]
        ordering = ["country", "level", "name"]

    def __str__(self) -> str:
        return f"{self.name} (L{self.level})"

    def ancestors(self) -> list["AdminUnit"]:
        chain, node = [], self.parent
        while node is not None:
            chain.append(node)
            node = node.parent
        return list(reversed(chain))


class HexCell(models.Model):
    """Res-7 analysis cell. Assigned to admin units by centroid (SDD §8.2)."""

    h3 = H3IndexField(primary_key=True)
    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name="hex_cells")
    admin_l1 = models.ForeignKey(
        AdminUnit, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    admin_l2 = models.ForeignKey(
        AdminUnit, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    admin_l3 = models.ForeignKey(
        AdminUnit, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    admin_l4 = models.ForeignKey(
        AdminUnit, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    land_frac = models.FloatField(null=True, blank=True)
    geom = models.PolygonField(srid=4326)

    class Meta:
        indexes = [models.Index(fields=["country"])]

    def __str__(self) -> str:
        return self.h3


class Road(models.Model):
    """OSM road network, filtered to classes that matter for livestock access (SDD §9.4)."""

    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name="roads")
    osm_id = models.BigIntegerField()
    highway = models.CharField(max_length=40)
    name = models.CharField(max_length=200, blank=True)
    surface = models.CharField(max_length=40, blank=True)
    dataset_version = models.ForeignKey(
        "catalog.DatasetVersion", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    geom = models.LineStringField(srid=4326)

    class Meta:
        indexes = [models.Index(fields=["country", "highway"])]

    def __str__(self) -> str:
        return self.name or f"{self.highway} {self.osm_id}"


class Waterway(models.Model):
    """OSM rivers, streams and canals."""

    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name="waterways")
    osm_id = models.BigIntegerField()
    waterway = models.CharField(max_length=40)
    name = models.CharField(max_length=200, blank=True)
    dataset_version = models.ForeignKey(
        "catalog.DatasetVersion", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    geom = models.LineStringField(srid=4326)

    class Meta:
        indexes = [models.Index(fields=["country", "waterway"])]

    def __str__(self) -> str:
        return self.name or f"{self.waterway} {self.osm_id}"
