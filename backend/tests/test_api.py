import h3
import pytest
from django.contrib.gis.geos import MultiPolygon, Polygon
from django.core.management import call_command
from django.db import connection
from rest_framework.test import APIClient

from apps.geo.models import AdminUnit, Country, HexCell
from apps.movement.models import MovementHexDay
from apps.movement.privacy import publishable


@pytest.fixture
def client():
    return APIClient()


def test_health_reports_extensions(client, db):
    r = client.get("/api/v1/health/")
    assert r.status_code == 200
    assert {"postgis", "h3"} <= set(r.json()["extensions"])


def test_countries(client, seeded):
    r = client.get("/api/v1/countries/")
    assert r.status_code == 200
    iso = {c["iso3"] for c in r.json()}
    assert iso == {"UGA", "KEN"}


def test_layers_carry_freshness(client, seeded):
    r = client.get("/api/v1/layers/?country=UGA&role=policy")
    assert r.status_code == 200
    ndvi = next(layer for layer in r.json() if layer["key"] == "ndvi_anom_z")
    assert ndvi["source"]["status"] == "pending"
    assert ndvi["source"]["dataset"] == "modis_ndvi"


def test_admin_units_and_hex_grid(client, seeded):
    uga = Country.objects.get(iso3="UGA")
    poly = MultiPolygon(Polygon.from_bbox((34.4, 2.3, 34.8, 2.7)))  # ~ around Moroto
    region = AdminUnit.objects.create(
        country=uga, level=1, code="R1", name="Karamoja", boundary_version="test", geom=poly
    )
    district = AdminUnit.objects.create(
        country=uga,
        level=2,
        code="D1",
        name="Moroto",
        parent=region,
        boundary_version="test",
        geom=poly,
    )

    r = client.get("/api/v1/countries/UGA/admin-units/?level=2")
    assert [u["name"] for u in r.json()] == ["Moroto"]

    r = client.get(f"/api/v1/admin-units/{district.id}/")
    assert r.json()["parents"][0]["name"] == "Karamoja"

    call_command("build_hex_grid", "UGA", "--level", "2", verbosity=0)
    cells = HexCell.objects.filter(country=uga)
    assert cells.count() > 100  # ~0.16 deg² ≈ 1,950 km² / 5.2 km²
    cell = cells.first()
    assert cell.admin_l2_id == district.id and cell.admin_l1_id == region.id
    with connection.cursor() as cur:
        cur.execute("SELECT h3_get_resolution(%s::h3index)", [cell.h3])
        assert cur.fetchone()[0] == 7


def test_movement_k_threshold(db):
    a = h3.latlng_to_cell(2.5, 34.6, 8)
    b = next(c for c in h3.grid_disk(a, 1) if c != a)
    MovementHexDay.objects.create(h3=a, day="2026-10-01", animal_count=2, fixes=40)
    MovementHexDay.objects.create(h3=b, day="2026-10-01", animal_count=3, fixes=60)
    assert publishable(MovementHexDay.objects.all()).count() == 1
