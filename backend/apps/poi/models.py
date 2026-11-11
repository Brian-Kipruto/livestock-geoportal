"""Points of interest: water points, markets, vet centres, abattoirs… (SDD §8.4)."""

from django.contrib.gis.db import models

from apps.common.choices import ValueChain


class PoiType(models.Model):
    key = models.SlugField(max_length=40, unique=True)  # water_point, market, vet_centre…
    name = models.CharField(max_length=120)
    value_chain = models.CharField(max_length=12, choices=ValueChain.choices)
    icon = models.CharField(max_length=40, blank=True)

    def __str__(self) -> str:
        return self.name


class Poi(models.Model):
    country = models.ForeignKey("geo.Country", on_delete=models.CASCADE, related_name="pois")
    poi_type = models.ForeignKey(PoiType, on_delete=models.PROTECT, related_name="pois")
    name = models.CharField(max_length=200, blank=True)
    attributes = models.JSONField(default=dict, blank=True)
    source_dataset = models.ForeignKey(
        "catalog.Dataset", null=True, blank=True, on_delete=models.SET_NULL, related_name="pois"
    )
    geom = models.PointField(srid=4326)

    class Meta:
        verbose_name = "point of interest"
        indexes = [models.Index(fields=["country", "poi_type"])]

    def __str__(self) -> str:
        return self.name or f"{self.poi_type} #{self.pk}"
