# Drought index (SPI-3) — `spi3`

**Status:** provisional (SDD §9.2) · **Pipeline:** `ingest_chirps`

## Formula
Standardised Precipitation Index (McKee et al. 1993) on 3-month rainfall totals:
1. Sum the hex's monthly CHIRPS totals over the 3 months ending in month m.
2. For each hex and calendar month, fit a gamma distribution to the 1991–2020 baseline sums
   (Thom 1958 maximum-likelihood approximation), with a point mass q for zero totals.
3. SPI = Φ⁻¹(q + (1 − q)·G(x)), where G is the fitted gamma CDF. Clipped to ±3.

No value when fewer than 10 baseline years have rain, or when any month in the window is missing.

## Classes (McKee)
≥ 2 extremely wet · 1.5–2 very wet · 1–1.5 moderately wet · −1 to 1 near normal ·
−1.5 to −1 moderately dry · −2 to −1.5 severely dry · ≤ −2 extremely dry.

## Limitations
- Gamma fit per hex on 30 values: fine for SPI-3; SPI-12 (not yet produced) needs the same check.
- See `rain_anom_pct.md` for CHIRPS caveats.

## Sign-off
—
