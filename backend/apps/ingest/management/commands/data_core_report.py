"""M1 checkpoint: what is in the data core for a country (SDD §16.1 "indicators verified in DB").

python manage.py data_core_report UGA [--json]
"""

from __future__ import annotations

import json

from django.core.management.base import BaseCommand
from django.db import connection

from apps.catalog.models import Dataset
from apps.geo.models import AdminUnit, HexCell, Road, Waterway
from apps.ingest.common import get_country
from apps.poi.models import Poi

INDICATOR_SQL = """
WITH r7 AS (SELECT h3 FROM geo_hexcell WHERE country_id = %(country)s),
cells AS (
    SELECT h3, 7 AS res FROM r7
    UNION ALL
    SELECT DISTINCT h3_cell_to_parent(h3, 6), 6 FROM r7
)
SELECT i.key, i.temporal,
       count(*) FILTER (WHERE c.res = 7) AS rows_r7,
       count(*) FILTER (WHERE c.res = 6) AS rows_r6,
       count(DISTINCT v.period_start) AS periods,
       min(v.period_start) AS first, max(v.period_start) AS last,
       min(v.value) FILTER (WHERE c.res = 7) AS vmin,
       max(v.value) FILTER (WHERE c.res = 7) AS vmax,
       avg(v.value) FILTER (WHERE c.res = 7) AS vmean
FROM catalog_indicatorvalue v
JOIN cells c ON c.h3 = v.h3
JOIN catalog_indicator i ON i.id = v.indicator_id
GROUP BY i.key, i.temporal ORDER BY i.key
"""

LATEST_COVERAGE_SQL = """
SELECT i.key, count(v.h3)::float / NULLIF(
         (SELECT count(*) FROM geo_hexcell WHERE country_id = %(country)s
            AND coalesce(land_frac, 1) >= 0.5), 0)
FROM catalog_indicator i
JOIN catalog_indicatorvalue v ON v.indicator_id = i.id
  AND v.period_start = (SELECT max(period_start) FROM catalog_indicatorvalue
                        WHERE indicator_id = i.id)
JOIN geo_hexcell h ON h.h3 = v.h3 AND h.country_id = %(country)s
  AND coalesce(h.land_frac, 1) >= 0.5
GROUP BY i.key
"""


class Command(BaseCommand):
    help = "Summarise boundaries, hex grid, indicators and dataset status for a country."

    def add_arguments(self, parser):
        parser.add_argument("iso3")
        parser.add_argument("--json", action="store_true")

    def handle(self, *args, iso3, json: bool = False, **opts):
        country = get_country(iso3)
        params = {"country": country.id}
        with connection.cursor() as cur:
            cur.execute(INDICATOR_SQL, params)
            cols = [c.name for c in cur.description]
            indicators = [dict(zip(cols, r, strict=True)) for r in cur.fetchall()]
            cur.execute(LATEST_COVERAGE_SQL, params)
            coverage = dict(cur.fetchall())
        for row in indicators:
            row["latest_land_coverage"] = coverage.get(row["key"])

        report = {
            "country": country.iso3,
            "admin_units": {
                f"L{lv}": AdminUnit.objects.filter(
                    country=country, level=lv, valid_to__isnull=True
                ).count()
                for lv in (1, 2, 3, 4)
            },
            "hex_cells": HexCell.objects.filter(country=country).count(),
            "hex_cells_land": HexCell.objects.filter(country=country, land_frac__gte=0.5).count(),
            "roads": Road.objects.filter(country=country).count(),
            "waterways": Waterway.objects.filter(country=country).count(),
            "pois": Poi.objects.filter(country=country).count(),
            "indicators": indicators,
            "datasets": [
                {
                    "key": d.key,
                    "status": d.status,
                    "latest": (v := d.latest_version) and v.version_label,
                    "data_date": v and v.data_date,
                    "validation": v and v.validation,
                    "report": v and v.validation_report,
                }
                for d in Dataset.objects.all()
                if d.versions.exists() or d.status != "pending"
            ],
        }
        if json:
            self.stdout.write(_dumps(report))
            return
        self._print(report)

    def _print(self, r):
        w = self.stdout.write
        w(f"== Data core: {r['country']} ==")
        w(f"Admin units (current): {r['admin_units']}")
        w(f"Hex cells (res 7): {r['hex_cells']}  land ≥ 50 %: {r['hex_cells_land']}")
        w(f"Roads: {r['roads']}  Waterways: {r['waterways']}  POIs: {r['pois']}")
        w("")
        w(
            f"{'indicator':16} {'temporal':8} {'rows r7':>10} {'rows r6':>9} {'periods':>7} "
            f"{'first':>10} {'last':>10} {'min':>9} {'max':>9} {'mean':>9} {'cover':>6}"
        )
        for i in r["indicators"]:
            cov = i["latest_land_coverage"]
            w(
                f"{i['key']:16} {i['temporal']:8} {i['rows_r7']:>10} {i['rows_r6']:>9} "
                f"{i['periods']:>7} {i['first']!s:>10} {i['last']!s:>10} {i['vmin']:>9.3g} "
                f"{i['vmax']:>9.3g} {i['vmean']:>9.3g} {(f'{cov:.1%}' if cov else '—'):>6}"
            )
        w("")
        w(f"{'dataset':12} {'status':8} {'data date':>10}  validation")
        for d in r["datasets"]:
            v = d["validation"] or {}
            verdict = (
                "—"
                if not v
                else f"{'PASS' if v.get('passed') else 'FAIL'} "
                f"({v.get('checks', 0)} checks, {v.get('warnings', 0)} warnings)"
            )
            report = d["report"] or ""
            w(f"{d['key']:12} {d['status']:8} {d['data_date']!s:>10}  {verdict}  {report}")


def _dumps(obj) -> str:
    return json.dumps(obj, indent=2, default=str)
