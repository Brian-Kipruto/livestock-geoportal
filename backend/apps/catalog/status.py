"""Freshness status logic (SDD §8.6) — drives the Live / n d ago / stale / pending tokens."""

from datetime import date

CADENCE_DAYS: dict[str, int | None] = {
    "daily": 1,
    "dekadal": 10,
    "16-day": 16,
    "monthly": 31,
    "quarterly": 92,
    "annual": 366,
    "static": None,  # never stale
    "ad-hoc": None,
}

STALE_FACTOR = 1.5


def compute_status(
    cadence: str, latest_data_date: date | None, last_job_failed: bool, today: date
) -> str:
    """live if data_date within 1.5x cadence; stale beyond; pending if no version; error if
    the last job failed."""
    if last_job_failed:
        return "error"
    if latest_data_date is None:
        return "pending"
    period = CADENCE_DAYS.get(cadence)
    if period is None:
        return "live"
    age_days = (today - latest_data_date).days
    return "live" if age_days <= period * STALE_FACTOR else "stale"
