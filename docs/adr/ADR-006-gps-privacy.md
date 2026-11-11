# ADR-006 — GPS privacy

**Status:** Proposed

## Context
Herd locations are sensitive for pastoralist communities (C7, R10).

## Decision
- `movement_herd`, `movement_collar`, `movement_gpsfix`, `movement_movementdaily` are restricted: never in public endpoints or tiles.
- Public consumers only see `movement_movementhexday` cells with `animal_count >= GPS_K_THRESHOLD` (default 3); smaller cells are suppressed or merged to the parent hex. Helper: `apps.movement.privacy.publishable()`.
- Martin connects as `martin_ro`, which has **no grant on `public`** — only on the `tiles` schema of curated views.
- Herd codes are pseudonymised; no owner names stored.

## Consequences
- Any new tile source must be added as a view in `tiles`, which forces a review.
