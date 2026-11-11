from django.contrib.gis import admin

from .models import Poi, PoiType


@admin.register(PoiType)
class PoiTypeAdmin(admin.ModelAdmin):
    list_display = ["key", "name", "value_chain"]


@admin.register(Poi)
class PoiAdmin(admin.GISModelAdmin):
    list_display = ["name", "poi_type", "country", "source_dataset"]
    list_filter = ["country", "poi_type", "source_dataset"]
    search_fields = ["name"]
