from django.contrib.gis import admin

from .models import AdminUnit, Country


@admin.register(Country)
class CountryAdmin(admin.GISModelAdmin):
    list_display = ["iso3", "name", "is_active"]


@admin.register(AdminUnit)
class AdminUnitAdmin(admin.GISModelAdmin):
    list_display = ["name", "level", "code", "country", "boundary_version", "valid_to"]
    list_filter = ["country", "level", "boundary_version"]
    search_fields = ["name", "code"]
    raw_id_fields = ["parent"]
