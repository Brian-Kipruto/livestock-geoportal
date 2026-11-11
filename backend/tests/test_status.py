from datetime import date

import pytest

from apps.catalog.status import compute_status

TODAY = date(2026, 11, 11)


@pytest.mark.parametrize(
    ("cadence", "data_date", "failed", "expected"),
    [
        ("monthly", None, False, "pending"),
        ("monthly", date(2026, 10, 1), False, "live"),  # 41 d <= 46.5
        ("monthly", date(2026, 9, 1), False, "stale"),  # 71 d
        ("16-day", date(2026, 10, 20), False, "live"),  # 22 d <= 24
        ("16-day", date(2026, 10, 15), False, "stale"),  # 27 d
        ("static", date(2015, 1, 1), False, "live"),
        ("monthly", date(2026, 11, 1), True, "error"),
    ],
)
def test_compute_status(cadence, data_date, failed, expected):
    assert compute_status(cadence, data_date, failed, TODAY) == expected
