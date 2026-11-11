# Method notes

One note per indicator (`<indicator_key>.md`): formula, inputs, baseline, thresholds, limitations, sign-off.
Nothing is shown to users as anything but **provisional** until Gladys (and the GIS expert where relevant) signs off (SDD §9).

| Indicator | Note | Pipeline | Sign-off |
|---|---|---|---|
| ndvi_anom_z | [ndvi_anom_z.md](ndvi_anom_z.md) | `ingest_modis_ndvi` | — |
| vci | [vci.md](vci.md) | `ingest_modis_ndvi` | — |
| water_freq | [water_freq.md](water_freq.md) | `ingest_wofs` | — |
| rain_anom_pct | [rain_anom_pct.md](rain_anom_pct.md) | `ingest_chirps` | — |
| spi3 | [spi3.md](spi3.md) | `ingest_chirps` | — |
| tlu_density, cattle/goat/sheep_density | [tlu_density.md](tlu_density.md) | `ingest_glw4` | — |

## Shared rules
- Grid: H3 res 7 (analysis), aggregated to res 6 (display) by the indicator's `agg_method`
  (SDD §8.2). Hexes are assigned to admin units by centroid.
- Zonal step: source rasters are read onto a regular EPSG:4326 grid, then reduced to hexes with
  exactextract coverage fractions. A hex needs valid data on ≥ 50 % of its area.
- Every run writes a `DatasetVersion` and a validation report (range, completeness < 95 % = warning,
  source-specific checks) to object storage, `media/reports/<dataset>/` (SDD §8.6).
