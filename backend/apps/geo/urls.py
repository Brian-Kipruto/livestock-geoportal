from django.urls import path

from . import views

urlpatterns = [
    path("countries/", views.CountryList.as_view(), name="country-list"),
    path(
        "countries/<str:iso3>/admin-units/",
        views.CountryAdminUnitList.as_view(),
        name="country-admin-units",
    ),
    path("admin-units/<int:pk>/", views.AdminUnitDetail.as_view(), name="admin-unit-detail"),
]
