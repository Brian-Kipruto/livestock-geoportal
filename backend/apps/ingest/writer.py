"""Write hex values into the partitioned `catalog_indicatorvalue` table (SDD §8.4, §12.3).

Idempotent per (indicator, periods): the res-7 rows and their res-6 aggregates for the given
periods are replaced inside the caller's transaction. Only finite values are stored.
"""

from __future__ import annotations

import io
from collections.abc import Sequence
from datetime import date

import numpy as np
from django.db import connection

from apps.catalog.models import Indicator
from apps.geo.models import ANALYSIS_RES, DISPLAY_RES

STATIC_PERIOD = date(1900, 1, 1)

AGG_SQL = {
    "mean": "avg(value)",
    "sum": "sum(value)",
    "max": "max(value)",
    "mode": "mode() WITHIN GROUP (ORDER BY value)",
}


def write_indicator(
    indicator: Indicator,
    version_id: int,
    h3_ids: np.ndarray,
    periods: Sequence[date],
    values: np.ndarray,
    *,
    scenario: str = "obs",
    horizon: str = "current",
) -> int:
    """Replace `indicator` values for `periods`. `values` is (n_hex, len(periods)).

    Returns the number of res-7 rows written.
    """
    values = np.asarray(values, dtype="float32")
    if values.ndim == 1:
        values = values[:, None]
    if values.shape != (len(h3_ids), len(periods)):
        raise ValueError(f"values shape {values.shape} != ({len(h3_ids)}, {len(periods)})")

    periods = list(periods)
    with connection.cursor() as cur:
        for year in sorted({p.year for p in periods if p != STATIC_PERIOD}):
            cur.execute("SELECT catalog_ensure_year_partition(%s)", [year])
        cur.execute(
            "DELETE FROM catalog_indicatorvalue WHERE indicator_id = %s "
            "AND period_start = ANY(%s) AND scenario = %s AND horizon = %s",
            [indicator.id, periods, scenario, horizon],
        )
        cur.execute(
            "CREATE TEMP TABLE IF NOT EXISTS _ingest_iv "
            "(h3 h3index, period_start date, value real) ON COMMIT DROP"
        )
        cur.execute("TRUNCATE _ingest_iv")

        written = 0
        with cur.copy("COPY _ingest_iv (h3, period_start, value) FROM STDIN") as cp:
            for j, period in enumerate(periods):
                col = values[:, j]
                ok = np.isfinite(col)
                if not ok.any():
                    continue
                buf = io.StringIO()
                p = period.isoformat()
                for cell, v in zip(h3_ids[ok], col[ok], strict=True):
                    buf.write(f"{cell}\t{p}\t{v:.6g}\n")
                cp.write(buf.getvalue())
                written += int(ok.sum())

        cur.execute(
            "INSERT INTO catalog_indicatorvalue "
            "(indicator_id, h3, period_start, scenario, horizon, value, dataset_version_id) "
            "SELECT %s, h3, period_start, %s, %s, value, %s FROM _ingest_iv",
            [indicator.id, scenario, horizon, version_id],
        )
        agg = AGG_SQL[indicator.agg_method]
        cur.execute(
            "INSERT INTO catalog_indicatorvalue "  # noqa: S608 (constants only)
            "(indicator_id, h3, period_start, scenario, horizon, value, dataset_version_id) "
            f"SELECT %s, h3_cell_to_parent(h3, {DISPLAY_RES}), period_start, %s, %s, {agg}, %s "
            "FROM _ingest_iv WHERE h3_get_resolution(h3) = %s "
            "GROUP BY 2, period_start",
            [indicator.id, scenario, horizon, version_id, ANALYSIS_RES],
        )
        cur.execute("DROP TABLE _ingest_iv")
    return written
