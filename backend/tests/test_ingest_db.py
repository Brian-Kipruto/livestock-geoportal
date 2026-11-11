"""Writer idempotency, res-6 aggregation and the IngestRun report/rollback contract."""

from datetime import date

import h3
import numpy as np
import pytest
from django.db import connection

from apps.catalog.models import Dataset, DatasetVersion, Indicator
from apps.ingest import run as run_module
from apps.ingest.management.commands.ingest_osm import osm_ref, parse_other_tags, water_point_kind
from apps.ingest.run import IngestRun, ValidationFailed
from apps.ingest.writer import STATIC_PERIOD, write_indicator


@pytest.fixture
def reports(monkeypatch):
    stored = {}

    def fake_put_json(bucket, key, obj):
        stored[key] = obj
        return f"s3://{bucket}/{key}"

    monkeypatch.setattr(run_module, "put_json", fake_put_json)
    return stored


def _rows(indicator, res=None):
    sql = "SELECT h3::text, period_start, value FROM catalog_indicatorvalue WHERE indicator_id=%s"
    params = [indicator.id]
    if res:
        sql += " AND h3_get_resolution(h3) = %s"
        params.append(res)
    with connection.cursor() as cur:
        cur.execute(sql + " ORDER BY 1, 2", params)
        return cur.fetchall()


def test_write_indicator_replaces_and_aggregates(seeded):
    ind = Indicator.objects.get(key="spi3")
    version = DatasetVersion.objects.create(dataset=ind.dataset)
    parent = h3.latlng_to_cell(1.0, 32.0, 6)
    kids = sorted(h3.cell_to_children(parent, 7))[:3]
    periods = [date(2024, 1, 1), date(2024, 2, 1)]
    values = np.array([[1.0, np.nan], [2.0, 0.5], [3.0, 1.5]], "float32")

    n = write_indicator(ind, version.id, np.array(kids), periods, values)
    assert n == 5  # NaN not stored
    r6 = _rows(ind, 6)
    assert [(c, p, round(v, 3)) for c, p, v in r6] == [
        (parent, periods[0], 2.0),
        (parent, periods[1], 1.0),
    ]

    # Re-running the same periods replaces rows instead of duplicating them.
    write_indicator(ind, version.id, np.array(kids), periods, np.full_like(values, 9))
    assert len(_rows(ind, 7)) == 6 and {v for *_, v in _rows(ind)} == {9.0}


def test_write_indicator_static_period(seeded):
    ind = Indicator.objects.get(key="tlu_density")
    version = DatasetVersion.objects.create(dataset=ind.dataset)
    cell = h3.latlng_to_cell(2.5, 34.6, 7)
    write_indicator(ind, version.id, np.array([cell]), [STATIC_PERIOD], np.array([[12.5]]))
    assert _rows(ind, 7) == [(cell, STATIC_PERIOD, 12.5)]


def test_ingest_run_success_records_version_and_status(seeded, reports):
    with IngestRun("chirps", version_label="t", echo=lambda *_: None) as run:
        run.check_range("rain", np.array([0.0, 10.0]), 0, 100)
        run.check_completeness("rain", np.array([[1.0], [np.nan]]), np.array([True, True]))
        run.data_date = date.today()
    v = DatasetVersion.objects.get(pk=run.version.pk)
    assert v.validation == {"passed": True, "checks": 2, "warnings": 1, "failed": 0}
    assert v.validation_report.startswith("s3://media/reports/chirps/")
    ds = Dataset.objects.get(key="chirps")
    assert ds.status == "live" and not ds.last_job_failed
    report = reports[v.validation_report.removeprefix("s3://media/")]
    assert report["checks"][1]["status"] == "warn"


def test_ingest_run_failure_rolls_back(seeded, reports):
    with pytest.raises(ValidationFailed):
        with IngestRun("chirps", echo=lambda *_: None) as run:
            run.check_range("rain", np.array([-5.0]), 0, 100)
    assert not DatasetVersion.objects.filter(dataset__key="chirps").exists()
    ds = Dataset.objects.get(key="chirps")
    assert ds.status == "error" and ds.last_job_failed
    ((key, report),) = reports.items()
    assert key.endswith("-FAILED.json") and report["summary"]["passed"] is False


def test_osm_tag_parsing():
    tags = parse_other_tags('"amenity"=>"water_point","pump"=>"manual","name:en"=>"A \\"b\\""')
    assert tags["amenity"] == "water_point" and tags["pump"] == "manual"
    assert water_point_kind(tags) == "amenity=water_point"
    assert water_point_kind({"man_made": "borehole"}) == "man_made=borehole"
    assert water_point_kind({"amenity": "school"}) is None
    assert osm_ref("way/891580134") == (891580134, "way/891580134")
    assert osm_ref(42) == (42, "42")
