# Architecture Decision Records

One file per decision. Status: Proposed → Accepted (after GO) → Superseded.
Template: Context · Decision · Consequences. Source: SDD §6.4.

| ADR | Decision | Status |
|---|---|---|
| [001](ADR-001-backend-django.md) | Django + DRF + GeoDjango backend | Accepted |
| [002](ADR-002-h3-grid.md) | H3 hex grid (res 6/7/8) as the common analysis unit | Proposed |
| [003](ADR-003-de-africa-primary-eo.md) | DE Africa primary EO source; no GEE at runtime | Proposed |
| [004](ADR-004-cogs-titiler.md) | Rasters as COGs in object storage + TiTiler | Proposed |
| [005](ADR-005-maplibre-deckgl.md) | MapLibre + deck.gl, ECharts | Proposed |
| [006](ADR-006-gps-privacy.md) | GPS privacy: raw fixes restricted; k ≥ 3 aggregates | Proposed |
| [007](ADR-007-multi-country-config.md) | Multi-country via config, not code | Proposed |
| [008](ADR-008-template-profiles.md) | Template-based profile text (no LLM) | Proposed |
| [009](ADR-009-seaweedfs-object-storage.md) | SeaweedFS instead of MinIO for local/self-hosted S3 | Proposed |
