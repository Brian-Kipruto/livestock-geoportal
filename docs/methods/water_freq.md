# Surface water frequency — `water_freq`

**Status:** provisional (SDD §9.1) · **Pipeline:** `ingest_wofs` · **Temporal:** annual

## Formula
water_freq(y) = Σ wet observations ÷ Σ clear observations × 100, over the hex, for year y.

## Inputs
- Digital Earth Africa WOfS annual summaries (`wofs_ls_summary_annual`, Landsat, 30 m),
  bands `count_wet` and `count_clear`, read from COG overviews onto a 0.005° grid.
- Ratio of sums, not mean of per-pixel frequencies: it stays exact at any overview level and
  ignores pixels with no clear view (count_clear = 0). (The pre-2023 `frequency` files have no
  nodata tag, so their overviews spread NaN; the count bands don't have that problem.)

## Land fraction
`wofs_ls_summary_alltime` sets `geo_hexcell.land_frac` = 1 − share of the hex where all-time
frequency ≥ 80 % (permanent water). Hexes with land_frac < 0.5 are treated as water for the
completeness checks of land-only products (CHIRPS, MODIS).

## Deviation from the SDD
SDD §9.1 asks for a monthly series. DE Africa publishes WOfS summaries annually (and all-time),
not monthly; monthly would mean compositing scene-level `wofs_ls` ourselves. Annual for M1.
Distance to permanent water + water points (also §9.1) is not built yet.

## Sign-off
—
