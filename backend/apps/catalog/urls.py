from django.urls import path

from . import views

urlpatterns = [
    path("datasets/", views.DatasetList.as_view(), name="dataset-list"),
    path("indicators/", views.IndicatorList.as_view(), name="indicator-list"),
    path("layers/", views.LayerList.as_view(), name="layer-list"),
]
