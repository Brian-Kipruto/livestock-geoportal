# Vegetation Condition Index — `vci`

**Status:** provisional · **Pipeline:** `ingest_modis_ndvi` (same inputs as `ndvi_anom_z.md`)

## Formula
VCI = (NDVI − NDVI_min(m)) / (NDVI_max(m) − NDVI_min(m)) × 100, per hex and calendar month,
with min/max over the 2001–2020 baseline. Clipped to 0–100 when the current value lies outside
the baseline range. No value where the baseline range is ~0.

No value for mostly-water hexes (`land_frac` < 0.5), as for the NDVI anomaly.

## Classes (common drought-monitoring convention, to confirm)
< 10 extreme · 10–20 severe · 20–35 moderate · 35–50 normal · > 50 above normal.

## Limitations
As for the NDVI anomaly. VCI is sensitive to single extreme baseline years (min/max), so it is
best read alongside the z-score.

## Sign-off
—
