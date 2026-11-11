"""Indicator maths (SDD §9.1–9.2) on synthetic series."""

from datetime import date

import numpy as np
import pytest

from apps.ingest import stats


def _series(years: int, start_year: int = 1991, seed: int = 0, n_hex: int = 3):
    rng = np.random.default_rng(seed)
    months = stats.month_range(date(start_year, 1, 1), date(start_year + years - 1, 12, 1))
    cal = np.array([m.month for m in months])
    seasonal = 50 + 40 * np.sin(2 * np.pi * cal / 12)
    values = rng.gamma(shape=4.0, scale=seasonal / 4.0, size=(n_hex, len(months)))
    return months, cal, values


def test_month_helpers():
    assert stats.month_range(date(2024, 11, 1), date(2025, 2, 1)) == [
        date(2024, 11, 1),
        date(2024, 12, 1),
        date(2025, 1, 1),
        date(2025, 2, 1),
    ]
    assert stats.month_end(date(2024, 2, 1)) == date(2024, 2, 29)
    assert stats.parse_month("2026-10") == date(2026, 10, 1)


def test_zscore_and_pct_of_mean_on_baseline():
    _, cal, values = _series(30)
    base = np.ones(values.shape[1], bool)
    clim = stats.climatology(values, cal, base)
    z = stats.zscore(values, cal, clim)
    # Over the baseline itself, z has mean 0 and (sample) std 1 per calendar month.
    for m in range(1, 13):
        zm = z[:, cal == m]
        assert np.allclose(zm.mean(axis=1), 0, atol=1e-5)
        assert np.allclose(zm.std(axis=1, ddof=1), 1, atol=1e-4)
    pct = stats.pct_of_mean(values, cal, clim)
    assert np.allclose(np.nanmean(pct[:, cal == 1], axis=1), 100, atol=1e-3)


def test_vci_bounds_and_extremes():
    _, cal, values = _series(20)
    base = np.ones(values.shape[1], bool)
    clim = stats.climatology(values, cal, base)
    v = stats.vci(values, cal, clim)
    assert np.nanmin(v) == 0 and np.nanmax(v) == 100
    # A value above the baseline max is clipped to 100.
    over = values.copy()
    over[:, -1] = clim["max"][:, cal[-1] - 1] * 2
    assert np.all(stats.vci(over, cal, clim)[:, -1] == 100)


def test_rolling_sum_only_spoils_windows_with_gaps():
    x = np.array([[1.0, 2.0, np.nan, 4.0, 5.0, 6.0]])
    r = stats.rolling_sum(x, 2)
    assert np.isnan(r[0, 0]) and r[0, 1] == 3
    assert np.isnan(r[0, 2]) and np.isnan(r[0, 3])
    assert r[0, 4] == 9 and r[0, 5] == 11


def test_spi_is_standard_normal_over_baseline():
    _, cal, values = _series(30, n_hex=4, seed=1)
    base = np.ones(values.shape[1], bool)
    s = stats.spi(values, cal, base, 3)
    finite = s[np.isfinite(s)]
    assert abs(finite.mean()) < 0.1
    assert 0.85 < finite.std() < 1.15
    assert finite.min() >= -3 and finite.max() <= 3


def test_spi_handles_zero_rain_months():
    _, cal, values = _series(30, n_hex=1, seed=2)
    values[:, cal == 7] = 0.0  # a reliably dry month
    base = np.ones(values.shape[1], bool)
    s = stats.spi(values, cal, base, 1)
    # All-zero month: no gamma fit possible → NaN rather than a fake extreme.
    assert np.all(np.isnan(s[:, cal == 7]))
    assert np.isfinite(s[:, cal == 1]).all()


@pytest.mark.parametrize("years", [5])
def test_short_baseline_gives_nan(years):
    _, cal, values = _series(years)
    base = np.ones(values.shape[1], bool)
    clim = stats.climatology(values, cal, base)
    assert np.isnan(clim["mean"]).all()
