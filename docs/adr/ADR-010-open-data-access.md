# ADR-010 — Open data access: public cloud catalogues first, documented fallbacks

**Status:** Proposed (refines ADR-003 and SDD Appendix A for M1)

## Context
M1 needs boundaries, CHIRPS, MODIS NDVI, WOfS, GLW4 and OSM for Uganda without waiting on
accounts (Earthdata, CDS). In Nov 2026, each source has quirks:
- Digital Earth Africa STAC serves CHIRPS monthly and WOfS as public COGs (anonymous S3, af-south-1),
  but the CHIRPS catalogue is missing a few months (2022-07, 2023-12, 2024-07, 2024-08).
- MODIS MOD13Q1 v061 is on Microsoft Planetary Computer as COGs with an anonymous SAS token;
  Terra and Aqua are both absent there for 2025-07…2025-10.
- Pre-2023 WOfS annual `frequency` files have no nodata tag, so their overviews spread NaN.
- Geofabrik's mirror served the Uganda extract at ~5 KB/s (hours) and does not answer HEAD.
- Planetary Computer STAC stalled paging a single 26-year MODIS search.

## Decision
- Read from public cloud catalogues first: DE Africa (CHIRPS, WOfS), Planetary Computer (MODIS),
  Harvard Dataverse (GLW4, CC0), HOT's OSM exports on HDX (roads, waterways, POIs — default;
  Geofabrik .pbf kept as `--provider geofabrik`), HDX (COD-AB). No account needed.
- STAC searches run one calendar year at a time.
- Read COG overviews at the coarsest level that is still finer than the target grid, then
  reduce to H3 res 7 with exactextract coverage weights (one sparse matrix per grid).
- Fallbacks are explicit and recorded in the validation report:
  CHIRPS gaps ← UCSB CHC archive (same product); MODIS month without Terra ← Aqua; MODIS
  months missing on both stay empty with a **warning** (baseline gaps fail the run).
- WOfS frequency = Σ count_wet ÷ Σ count_clear (exact at any overview, no NaN issue).
- Every run is all-or-nothing in one transaction; a failed check rolls back and marks the
  dataset `error`, with the report still stored.

## Consequences
- The NDVI series has a hole for 2025-07…2025-10 until it is backfilled from NASA LP DAAC
  (needs a free Earthdata login — SDD "Accounts to create now").
- Reading the 1 km MODIS overview (not native 250 m) is adequate for ~5 km² hexes; method note
  says so.
- Raw downloads and decoded rasters live in the `ingest_cache` volume; re-runs re-read nothing.
