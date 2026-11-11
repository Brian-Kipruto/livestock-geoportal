from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.common.views import health

admin.site.site_header = "Livestock Geoportal — Data administration"
admin.site.site_title = "Livestock Geoportal admin"

api_v1 = [
    path("health/", health, name="health"),
    path("", include("apps.geo.urls")),
    path("", include("apps.catalog.urls")),
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
]

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include(api_v1)),
]
