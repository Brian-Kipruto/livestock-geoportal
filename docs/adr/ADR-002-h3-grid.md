# ADR-002 — H3 hexagon grid as the common analysis unit

**Status:** Proposed

## Context
Satellite, climate, livestock and movement data come at different resolutions. AfLIP shipped static pre-rendered layers that were slow and could not be filtered.

## Decision
Every indicator is summarised to H3 cells: **res 7** (~5.2 km²) for analysis, aggregated to **res 6** for national display, **res 8** for movement detail inside study areas. Stored with h3-pg (`h3index` type); cells are assigned to admin units by centroid (`h3_polygon_to_cells`). Built by `manage.py build_hex_grid <ISO3>`.

## Consequences
- Country payloads are compact `[h3, value]` arrays rendered client-side by deck.gl (NFR-4).
- Instant client-side filtering/scoring (Finder) without server round-trips.
- Hexes straddling borders need area-weighted stats where precision matters.
