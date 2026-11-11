# Livestock density — `tlu_density`, `cattle_density`, `goat_density`, `sheep_density`

**Status:** provisional (SDD §9.3) · **Pipeline:** `ingest_glw4` · **Temporal:** static (2015)

## Formula
heads(hex) = Σ pixel heads × share of the pixel inside the hex (exactextract coverage);
density = heads ÷ hex area (km²).
TLU = 0.7 × cattle + 0.1 × (sheep + goats). Camels and donkeys are not in GLW4 2015.

## Inputs
FAO Gridded Livestock of the World v4, 2015, **dasymetric** layers (`*_2015_Da.tif`, heads per
pixel, 5 arc-minutes ≈ 85 km²) from Harvard Dataverse, licence CC0 1.0.

## Limitations
- A GLW4 pixel is ~15× a res-7 hex: hex values are the pixel's density, not finer detail.
- 2015 baseline, not calibrated to census totals (UBOS/MAAIF, SDD §8.5 `census`, pilot phase).
- The validation report records national totals per species as a sanity check.

## Sign-off
—
