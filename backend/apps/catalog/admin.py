from django.contrib import admin

from .models import Dataset, DatasetVersion, Indicator, Layer, RasterAsset


class DatasetVersionInline(admin.TabularInline):
    model = DatasetVersion
    extra = 0
    readonly_fields = ["ingested_at"]


@admin.register(Dataset)
class DatasetAdmin(admin.ModelAdmin):
    list_display = ["key", "name", "provider", "update_cadence", "access_level", "status"]
    list_filter = ["status", "access_level", "update_cadence"]
    search_fields = ["key", "name", "provider"]
    inlines = [DatasetVersionInline]


@admin.register(Indicator)
class IndicatorAdmin(admin.ModelAdmin):
    list_display = ["key", "name", "theme", "value_chain", "temporal", "is_provisional"]
    list_filter = ["theme", "value_chain", "temporal", "is_provisional"]


@admin.register(Layer)
class LayerAdmin(admin.ModelAdmin):
    list_display = ["key", "name", "kind", "theme", "default_on", "sort_order", "is_active"]
    list_filter = ["kind", "theme", "is_active"]
    list_editable = ["sort_order", "is_active"]


admin.site.register(RasterAsset)
