from django.contrib import admin

from .models import Collar, Herd


class CollarInline(admin.TabularInline):
    model = Collar
    extra = 0


@admin.register(Herd)
class HerdAdmin(admin.ModelAdmin):
    list_display = ["code", "species", "country"]
    list_filter = ["species", "country"]
    inlines = [CollarInline]
