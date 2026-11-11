# Rainfall vs long-term mean — `rain_anom_pct`

**Status:** provisional (SDD §9.2) · **Pipeline:** `ingest_chirps`

## Formula
anomaly = P(m, y) / P̄(m) × 100, where P is the hex's monthly rainfall total (mm) and P̄ the
1991–2020 mean for that calendar month. 100 = normal; 50 = half the usual rain.

## Inputs
- CHIRPS v2.0 monthly totals (0.05°), from Digital Earth Africa (`rainfall_chirps_monthly`, COGs).
- Hex value = area-weighted mean of CHIRPS cells (a 0.05° cell is ~30 km², larger than a
  res-7 hex, so neighbouring hexes often share a value).

## Rules
- No value where the long-term monthly mean is < 1 mm (dry-season months in the north-east);
  a percentage of almost nothing is not meaningful.

## Limitations
- CHIRPS has no values over large lakes; lake hexes are excluded from completeness checks via
  `land_frac` (from WOfS).
- Latest month uses CHIRPS *final*; preliminary data is not used.

## Sign-off
—
