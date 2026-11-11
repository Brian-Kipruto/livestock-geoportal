"""Herd movement (SDD §8.4, §9.5).

PRIVACY (ADR-006, NFR-7): Herd, Collar and GpsFix are RESTRICTED. They must never be exposed
through public endpoints or vector tiles. Public consumers only see MovementHexDay rows with
animal_count >= settings.GPS_K_THRESHOLD. Martin's DB role has no grant on these tables.
"""

from django.contrib.gis.db import models

from apps.common.fields import H3IndexField


class Herd(models.Model):
    code = models.CharField(max_length=40, unique=True, help_text="Pseudonymised code, no names")
    species = models.CharField(max_length=20)  # cattle | goat | sheep | camel
    country = models.ForeignKey("geo.Country", on_delete=models.PROTECT, related_name="herds")
    owner_alias = models.CharField(max_length=60, blank=True, help_text="Alias only — never a name")

    def __str__(self) -> str:
        return self.code


class Collar(models.Model):
    herd = models.ForeignKey(Herd, on_delete=models.CASCADE, related_name="collars")
    device_id = models.CharField(max_length=80, unique=True)
    deployed_on = models.DateField(null=True, blank=True)
    retired_on = models.DateField(null=True, blank=True)

    def __str__(self) -> str:
        return self.device_id


class GpsFix(models.Model):
    pk = models.CompositePrimaryKey("collar", "ts")
    collar = models.ForeignKey(Collar, on_delete=models.CASCADE, related_name="fixes")
    ts = models.DateTimeField()
    geom = models.PointField(srid=4326)
    hdop = models.FloatField(null=True, blank=True)
    fix_quality = models.SmallIntegerField(null=True, blank=True)
    is_valid = models.BooleanField(default=True)

    class Meta:
        verbose_name = "GPS fix"
        indexes = [models.Index(fields=["ts"])]


class MovementDaily(models.Model):
    pk = models.CompositePrimaryKey("herd", "day")
    herd = models.ForeignKey(Herd, on_delete=models.CASCADE, related_name="daily")
    day = models.DateField()
    km_travelled = models.FloatField(null=True)
    min_dist_water_km = models.FloatField(null=True)
    max_disp_km = models.FloatField(null=True, help_text="Max displacement from start")
    cross_border = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = "movement daily"


class MovementHexDay(models.Model):
    """Public aggregate: published only where animal_count >= k (NFR-7)."""

    pk = models.CompositePrimaryKey("h3", "day", "species")
    h3 = H3IndexField()
    day = models.DateField()
    species = models.CharField(max_length=20, default="all")
    animal_count = models.PositiveIntegerField()
    fixes = models.PositiveIntegerField()

    class Meta:
        indexes = [models.Index(fields=["day"])]
