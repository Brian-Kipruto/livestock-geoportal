from django.db import connection
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@extend_schema(responses={200: dict})
@api_view(["GET"])
@permission_classes([AllowAny])
@throttle_classes([])
def health(request):
    """Liveness + DB extension check, used by compose healthchecks and uptime monitors."""
    with connection.cursor() as cur:
        cur.execute(
            "SELECT extname, extversion FROM pg_extension "
            "WHERE extname IN ('postgis', 'h3', 'h3_postgis')"
        )
        extensions = dict(cur.fetchall())
    return Response({"status": "ok", "extensions": extensions})
