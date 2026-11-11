"""k-anonymity helpers for public movement aggregates (ADR-006, NFR-7)."""

from django.conf import settings
from django.db.models import QuerySet


def publishable(qs: QuerySet, k: int | None = None) -> QuerySet:
    """Filter a MovementHexDay queryset to cells safe for public display."""
    return qs.filter(animal_count__gte=k if k is not None else settings.GPS_K_THRESHOLD)
