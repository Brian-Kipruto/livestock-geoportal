# ADR-004 — Rasters as COGs in object storage, served by TiTiler

**Status:** Proposed

## Context
Detail-zoom raster layers (NDVI, rainfall, land cover) are needed (FR-E3). GeoServer is heavy to maintain; rasters in PostGIS bloat the DB and backups.

## Decision
Cloud-Optimised GeoTIFFs in S3-compatible object storage, dynamic tiles via TiTiler. TiTiler only accepts URLs under an allow-list (`TITILER_ALLOWED_PREFIXES`, see `infra/titiler/app.py`) to prevent SSRF.

## Consequences
- No GeoServer, no rasters in PostGIS.
- `catalog.RasterAsset` records each COG and its dataset version.
