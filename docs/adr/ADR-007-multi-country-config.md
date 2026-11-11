# ADR-007 — Multi-country by configuration

**Status:** Proposed

## Context
Uganda is the pilot; Kenya and Somalia follow (C6, NFR-10). The GPS data country may decide the demo country (R2).

## Decision
A `geo.Country` row holds ISO3, admin level labels, seasons, default bbox and languages. Admin units are a versioned hierarchy table. All API calls take `country`. Adding a country = config + data, no code.

## Consequences
- Seed data in `manage.py seed_reference` (UGA, KEN).
