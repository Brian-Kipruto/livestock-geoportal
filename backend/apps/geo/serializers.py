from rest_framework import serializers

from .models import AdminUnit, Country


class CountrySerializer(serializers.ModelSerializer):
    bbox = serializers.SerializerMethodField()

    class Meta:
        model = Country
        fields = ["iso3", "name", "admin_levels", "seasons", "languages", "bbox"]

    def get_bbox(self, obj: Country) -> list[float]:
        return list(obj.default_bbox.extent)  # [minx, miny, maxx, maxy]


class AdminUnitLightSerializer(serializers.ModelSerializer):
    """No geometry — geometry is served as vector tiles by Martin."""

    parent_id = serializers.IntegerField(allow_null=True)

    class Meta:
        model = AdminUnit
        fields = ["id", "level", "code", "name", "parent_id", "boundary_version"]


class AdminUnitDetailSerializer(serializers.ModelSerializer):
    bbox = serializers.SerializerMethodField()
    parents = serializers.SerializerMethodField()
    country = serializers.CharField(source="country.iso3")

    class Meta:
        model = AdminUnit
        fields = ["id", "country", "level", "code", "name", "boundary_version", "bbox", "parents"]

    def get_bbox(self, obj: AdminUnit) -> list[float]:
        return list(obj.geom.extent)

    def get_parents(self, obj: AdminUnit) -> list[dict]:
        return AdminUnitLightSerializer(obj.ancestors(), many=True).data
