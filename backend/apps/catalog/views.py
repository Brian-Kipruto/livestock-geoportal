from django.db.models import Q
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import generics

from .models import Dataset, Indicator, Layer
from .serializers import DatasetSerializer, IndicatorSerializer, LayerSerializer


class DatasetList(generics.ListAPIView):
    """Sources, licences and freshness — feeds status tokens + profile sources section."""

    serializer_class = DatasetSerializer
    queryset = Dataset.objects.prefetch_related("versions")
    pagination_class = None


@extend_schema(parameters=[OpenApiParameter("theme", str)])
class IndicatorList(generics.ListAPIView):
    serializer_class = IndicatorSerializer
    pagination_class = None
    filterset_fields = ["theme", "value_chain", "temporal"]
    queryset = Indicator.objects.select_related("dataset")


@extend_schema(parameters=[OpenApiParameter("country", str), OpenApiParameter("role", str)])
class LayerList(generics.ListAPIView):
    """Layer list with style, legend and freshness status (FR-E1, FR-E10)."""

    serializer_class = LayerSerializer
    pagination_class = None

    def get_queryset(self):
        qs = (
            Layer.objects.filter(is_active=True)
            .select_related("indicator__dataset", "dataset")
            .prefetch_related("dataset__versions", "indicator__dataset__versions")
        )
        params = self.request.query_params
        if country := params.get("country"):
            qs = qs.filter(Q(countries__iso3=country.upper()) | Q(countries__isnull=True))
        if role := params.get("role"):
            qs = qs.filter(Q(roles__contains=[role]) | Q(roles=[]))
        return qs.distinct()
