# NDVI anomaly (z-score) — `ndvi_anom_z`

**Status:** provisional (awaiting sign-off, SDD §9.1) · **Pipeline:** `ingest_modis_ndvi`

## Formula
z = (NDVI(m, y) − μ(m)) / σ(m), per res-7 hex and calendar month m, with μ and σ (sample std)
taken over the baseline years.

## Inputs
- MODIS MOD13Q1 v061, Terra only (one consistent series since 2000), 16-day, 250 m, read from
  Microsoft Planetary Computer.
- Composites are read from the 1 km COG overview onto a 0.01° grid (≈ 5 cells per hex).
  Fill (−3000) and values outside the valid range [−2000, 10000] are dropped. Scale 1e-4.
- Monthly NDVI per pixel = mean of the composites whose 16-day window **starts** in that month.
- Hex value = area-weighted mean of the grid cells (exactextract coverage fractions). A hex needs
  valid data on ≥ 50 % of its area, otherwise it has no value.

## Baseline
2001–2020 (20 years), as in SDD §9.1.

## Hazard classes (provisional, SDD §9.1)
≥ −0.5 Normal · −0.5 to −1.0 Watch · −1.0 to −1.5 Alert · < −1.5 Emergency. To be aligned with
NDMA / IGAD-ICPAC conventions.

## Rules
- No value for mostly-water hexes (`land_frac` < 0.5, from WOfS): NDVI over open water is noise.
- z is clipped to ±5. Shoreline and wetland hexes can have a near-constant baseline (σ ≈ 0.02),
  which gives |z| of 30–50 for ordinary changes; the report counts how many values were clipped.
  (First Uganda run: ≈ 0.35 % of land values had |z| > 4.)

## Limitations
- No QA-band (pixel reliability) masking yet: cloud-contaminated composites lower NDVI, which
  can show as negative anomalies in very cloudy months. Candidate fix: mask reliability ≥ 2.
- 1 km overview, not native 250 m. Adequate for ~5 km² hexes; not for field-scale use.
- Monthly assignment by composite start date means a composite straddling two months counts
  in the first.

## Sign-off
— (Gladys / GIS expert)
