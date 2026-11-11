from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_control
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import generics

from .models import AdminUnit, Country
from .serializers import AdminUnitDetailSerializer, AdminUnitLightSerializer, CountrySerializer

cached = method_decorator(cache_control(public=True, max_age=300), name="dispatch")


@cached
class CountryList(generics.ListAPIView):
    """Active countries + configuration (FR-G1)."""

    serializer_class = CountrySerializer
    queryset = Country.objects.filter(is_active=True)
    pagination_class = None


@cached
@extend_schema(parameters=[OpenApiParameter("level", int), OpenApiParameter("parent", int)])
class CountryAdminUnitList(generics.ListAPIView):
    """Admin units for a country, without geometry (FR-G2)."""

    serializer_class = AdminUnitLightSerializer
    pagination_class = None

    def get_queryset(self):
        country = get_object_or_404(Country, iso3=self.kwargs["iso3"].upper(), is_active=True)
        qs = AdminUnit.objects.filter(country=country, valid_to__isnull=True).defer("geom")
        if level := self.request.query_params.get("level"):
            qs = qs.filter(level=level)
        if parent := self.request.query_params.get("parent"):
            qs = qs.filter(parent_id=parent)
        return qs


@cached
class AdminUnitDetail(generics.RetrieveAPIView):
    serializer_class = AdminUnitDetailSerializer
    queryset = AdminUnit.objects.select_related("country", "parent")
