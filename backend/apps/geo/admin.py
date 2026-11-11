from django.contrib.gis import admin

from .models import AdminUnit, Country, Road, Waterway


@admin.register(Country)
class CountryAdmin(admin.GISModelAdmin):
    list_display = ["iso3", "name", "is_active"]


@admin.register(AdminUnit)
class AdminUnitAdmin(admin.GISModelAdmin):
    list_display = ["name", "level", "code", "country", "boundary_version", "valid_to"]
    list_filter = ["country", "level", "boundary_version"]
    search_fields = ["name", "code"]
    raw_id_fields = ["parent"]


@admin.register(Road)
class RoadAdmin(admin.GISModelAdmin):
    list_display = ["osm_id", "highway", "name", "country"]
    list_filter = ["country", "highway"]
    search_fields = ["name"]


@admin.register(Waterway)
class WaterwayAdmin(admin.GISModelAdmin):
    list_display = ["osm_id", "waterway", "name", "country"]
    list_filter = ["country", "waterway"]
    search_fields = ["name"]
