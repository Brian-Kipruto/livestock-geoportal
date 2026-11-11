"""Indicator maths on hex time series (SDD §9.1–9.2). All methods are provisional until sign-off.

Arrays are (n_hex, T) with one column per consecutive calendar month; `months` holds the
calendar month (1–12) of each column and `baseline` marks the columns in the reference period.
"""

from __future__ import annotations

import warnings
from datetime import date

import numpy as np
from scipy.special import gammainc
from scipy.stats import norm

MIN_BASELINE_YEARS = 10


def month_range(start: date, end: date) -> list[date]:
    out, y, m = [], start.year, start.month
    while (y, m) <= (end.year, end.month):
        out.append(date(y, m, 1))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def month_end(d: date) -> date:
    nxt = date(d.year + 1, 1, 1) if d.month == 12 else date(d.year, d.month + 1, 1)
    return date.fromordinal(nxt.toordinal() - 1)


def parse_month(s: str) -> date:
    y, m = s.split("-")[:2]
    return date(int(y), int(m), 1)


def _by_month(values, months, baseline, fn):
    out = np.full((values.shape[0], 12), np.nan, dtype="float64")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        for m in range(1, 13):
            cols = baseline & (months == m)
            if cols.sum() >= MIN_BASELINE_YEARS:
                out[:, m - 1] = fn(values[:, cols], axis=1)
    return out


def climatology(values: np.ndarray, months: np.ndarray, baseline: np.ndarray) -> dict:
    """Per-hex, per-calendar-month mean/std/min/max over the baseline columns."""
    return {
        "mean": _by_month(values, months, baseline, np.nanmean),
        "std": _by_month(values, months, baseline, lambda a, axis: np.nanstd(a, axis=axis, ddof=1)),
        "min": _by_month(values, months, baseline, np.nanmin),
        "max": _by_month(values, months, baseline, np.nanmax),
    }


def zscore(values: np.ndarray, months: np.ndarray, clim: dict, eps: float = 1e-6) -> np.ndarray:
    mu, sd = clim["mean"][:, months - 1], clim["std"][:, months - 1]
    with np.errstate(invalid="ignore", divide="ignore"):
        z = (values - mu) / sd
    z[~(sd > eps)] = np.nan
    return z.astype("float32")


def pct_of_mean(values: np.ndarray, months: np.ndarray, clim: dict, min_mean: float = 1.0):
    """Value as % of the long-term monthly mean; NaN where the mean is below `min_mean`."""
    mu = clim["mean"][:, months - 1]
    with np.errstate(invalid="ignore", divide="ignore"):
        pct = values / mu * 100.0
    pct[~(mu >= min_mean)] = np.nan
    return pct.astype("float32")


def vci(values: np.ndarray, months: np.ndarray, clim: dict) -> np.ndarray:
    """Vegetation Condition Index, 0–100 (clipped when outside the baseline range)."""
    lo, hi = clim["min"][:, months - 1], clim["max"][:, months - 1]
    rng = hi - lo
    with np.errstate(invalid="ignore", divide="ignore"):
        out = (values - lo) / rng * 100.0
    out[~(rng > 1e-6)] = np.nan
    return np.clip(out, 0, 100).astype("float32")


def rolling_sum(values: np.ndarray, k: int) -> np.ndarray:
    """k-month accumulation ending at each column; NaN for the first k-1 columns."""
    out = np.full(values.shape, np.nan, dtype="float64")
    if k <= values.shape[1]:
        windows = np.lib.stride_tricks.sliding_window_view(values.astype("float64"), k, axis=1)
        out[:, k - 1 :] = windows.sum(axis=-1)  # NaN if any month in the window is missing
    return out


def spi(precip: np.ndarray, months: np.ndarray, baseline: np.ndarray, scale: int) -> np.ndarray:
    """Standardised Precipitation Index (McKee et al. 1993) with a gamma fit per hex and
    calendar month (Thom 1958 MLE approximation) and a point mass at zero. Clipped to ±3."""
    acc = rolling_sum(precip, scale)
    out = np.full(acc.shape, np.nan, dtype="float64")
    for m in range(1, 13):
        base_cols = baseline & (months == m)
        if base_cols.sum() < MIN_BASELINE_YEARS:
            continue
        x = acc[:, base_cols]
        valid = np.isfinite(x)
        pos = valid & (x > 0)
        n_valid = valid.sum(axis=1)
        n_pos = pos.sum(axis=1)
        q = np.where(n_valid > 0, 1 - n_pos / np.maximum(n_valid, 1), np.nan)
        with np.errstate(invalid="ignore", divide="ignore"):
            xp = np.where(pos, x, np.nan)
            mean = np.nanmean(xp, axis=1)
            A = np.log(mean) - np.nanmean(np.log(xp), axis=1)
            alpha = (1 + np.sqrt(1 + 4 * A / 3)) / (4 * A)
            beta = mean / alpha
        fit_ok = (n_pos >= MIN_BASELINE_YEARS) & np.isfinite(alpha) & (alpha > 0)

        cols = months == m
        target = acc[:, cols]
        with np.errstate(invalid="ignore", divide="ignore"):
            G = gammainc(alpha[:, None], np.where(target > 0, target, 0) / beta[:, None])
        H = q[:, None] + (1 - q[:, None]) * G
        H = np.clip(H, 1e-6, 1 - 1e-6)
        s = norm.ppf(H)
        s[~fit_ok] = np.nan
        s[~np.isfinite(target)] = np.nan
        out[:, cols] = s
    return np.clip(out, -3, 3).astype("float32")
