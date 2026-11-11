# ADR-005 — MapLibre GL + deck.gl; ECharts; Zustand

**Status:** Proposed

## Context
AfLIP used Leaflet + Redux with static layers and weak UX. We need WebGL hex rendering, track replay and no proprietary keys (C3).

## Decision
MapLibre GL JS for basemap/vector tiles; deck.gl (`H3HexagonLayer`, `TripsLayer`, `PathLayer`) via `MapboxOverlay`; ECharts for charts; Zustand for state; TanStack Query for server state.

## Consequences
- WebGL2 required (NFR-13); a fallback message is shown otherwise.
- Dev basemap currently uses OSM raster tiles; replace with a self-hosted PMTiles basemap before the demo (OSM tile policy, Lite mode).
