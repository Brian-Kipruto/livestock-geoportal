"""Datasets, provenance, indicators and map layers (SDD §8.3–8.6, NFR-12)."""

from django.contrib.postgres.fields import ArrayField
from django.db import models

from apps.common.choices import AccessLevel, Role, Theme, ValueChain
from apps.common.fields import H3IndexField


class Dataset(models.Model):
    class Cadence(models.TextChoices):
        DAILY = "daily"
        DEKADAL = "dekadal"
        SIXTEEN_DAY = "16-day"
        MONTHLY = "monthly"
        QUARTERLY = "quarterly"
        ANNUAL = "annual"
        STATIC = "static"
        AD_HOC = "ad-hoc"

    class Status(models.TextChoices):
        LIVE = "live"
        STALE = "stale"
        PENDING = "pending"
        ERROR = "error"

    key = models.SlugField(max_length=60, unique=True)
    name = models.CharField(max_length=200)
    provider = models.CharField(max_length=200)
    licence = models.CharField(max_length=200)
    url = models.URLField(blank=True)
    update_cadence = models.CharField(max_length=20, choices=Cadence.choices)
    access_level = models.CharField(
        max_length=20, choices=AccessLevel.choices, default=AccessLevel.PUBLIC
    )
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    last_job_failed = models.BooleanField(default=False)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["key"]

    def __str__(self) -> str:
        return self.key

    @property
    def latest_version(self) -> "DatasetVersion | None":
        return self.versions.order_by("-data_date", "-ingested_at").first()


class DatasetVersion(models.Model):
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE, related_name="versions")
    version_label = models.CharField(max_length=80, blank=True)
    data_date = models.DateField(null=True, blank=True, help_text="Date the data represents")
    ingested_at = models.DateTimeField(auto_now_add=True)
    checksum = models.CharField(max_length=128, blank=True)
    validation_report = models.CharField(max_length=500, blank=True, help_text="Object-store key")
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-ingested_at"]

    def __str__(self) -> str:
        return f"{self.dataset.key} {self.version_label or self.data_date}"


class Indicator(models.Model):
    class Temporal(models.TextChoices):
        STATIC = "static"
        MONTHLY = "monthly"
        SEASONAL = "seasonal"
        SCENARIO = "scenario"

    class AggMethod(models.TextChoices):
        MEAN = "mean"
        SUM = "sum"
        MAX = "max"
        MODE = "mode"

    key = models.SlugField(max_length=60, unique=True)
    name = models.CharField(max_length=200)
    unit = models.CharField(max_length=40, blank=True)
    theme = models.CharField(max_length=20, choices=Theme.choices)
    value_chain = models.CharField(max_length=12, choices=ValueChain.choices)
    temporal = models.CharField(max_length=10, choices=Temporal.choices)
    agg_method = models.CharField(max_length=6, choices=AggMethod.choices)
    higher_is_better = models.BooleanField(null=True)
    classes = models.JSONField(null=True, blank=True, help_text="Class breaks + hazard mapping")
    method_doc = models.TextField(blank=True, help_text="Link to docs/methods/… or markdown")
    is_provisional = models.BooleanField(default=True, help_text="Until method sign-off (§9)")
    dataset = models.ForeignKey(
        Dataset, null=True, blank=True, on_delete=models.SET_NULL, related_name="indicators"
    )

    class Meta:
        ordering = ["theme", "key"]

    def __str__(self) -> str:
        return self.key


class IndicatorValue(models.Model):
    """Hex time series. Table is range-partitioned by period_start (created in raw SQL)."""

    pk = models.CompositePrimaryKey("indicator", "h3", "period_start", "scenario", "horizon")
    indicator = models.ForeignKey(Indicator, on_delete=models.DO_NOTHING)
    h3 = H3IndexField()
    period_start = models.DateField(help_text="Month start; 1900-01-01 for static")
    scenario = models.CharField(max_length=10, default="obs")  # obs | ssp245 | ssp585
    horizon = models.CharField(max_length=12, default="current")  # current | 2021-2040 | 2041-2060
    value = models.FloatField(null=True)
    value_p10 = models.FloatField(null=True)
    value_p90 = models.FloatField(null=True)
    dataset_version = models.ForeignKey(
        DatasetVersion, null=True, on_delete=models.DO_NOTHING, related_name="+"
    )

    class Meta:
        managed = False
        db_table = "catalog_indicatorvalue"

    def __str__(self) -> str:
        return f"{self.indicator_id}:{self.h3}@{self.period_start}"


class RasterAsset(models.Model):
    """A COG in object storage, rendered via TiTiler (ADR-004)."""

    dataset_version = models.ForeignKey(
        DatasetVersion, on_delete=models.CASCADE, related_name="rasters"
    )
    key = models.CharField(max_length=500, help_text="s3://bucket/path.tif")
    period_start = models.DateField(null=True, blank=True)
    band = models.PositiveSmallIntegerField(default=1)

    def __str__(self) -> str:
        return self.key


class Layer(models.Model):
    """What the layer dock shows: an indicator (hex), a vector tile source or a raster."""

    class Kind(models.TextChoices):
        HEX = "hex"
        VECTOR = "vector"
        RASTER = "raster"

    key = models.SlugField(max_length=60, unique=True)
    name = models.CharField(max_length=200)
    kind = models.CharField(max_length=10, choices=Kind.choices)
    theme = models.CharField(max_length=20, choices=Theme.choices)
    countries = models.ManyToManyField("geo.Country", blank=True, help_text="Empty = all")
    indicator = models.ForeignKey(Indicator, null=True, blank=True, on_delete=models.SET_NULL)
    dataset = models.ForeignKey(Dataset, null=True, blank=True, on_delete=models.SET_NULL)
    vector_source = models.CharField(max_length=100, blank=True, help_text="Martin source id")
    style = models.JSONField(default=dict, blank=True, help_text="Ramp / paint properties")
    legend = models.JSONField(default=dict, blank=True)
    roles = ArrayField(
        models.CharField(max_length=12, choices=Role.choices),
        default=list,
        blank=True,
        help_text="Role presets that list this layer; empty = all",
    )
    default_on = models.BooleanField(default=False)
    sort_order = models.PositiveSmallIntegerField(default=100)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["theme", "sort_order", "name"]

    def __str__(self) -> str:
        return self.key
