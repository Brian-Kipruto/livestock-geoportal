# Livestock Value Chain Geoportal

A web geoportal that combines satellite, climate, livestock and movement data on a common
hexagon grid so policymakers, investors and technical officers can see **where livestock
investment is viable, what the risks are, and how conditions are changing**.

Commissioned by the UN Economic Commission for Africa (NRFS Section). Pilot: Uganda;
multi-country by configuration (Kenya, Somalia later). ECA owns the code.

> Status: **M0 — Spec & setup.** The data model, API skeleton, compose stack and UI shell
> exist. No real data is ingested yet; the NDVI hexes on the map are an *illustrative*
> pattern, labelled as such.

## Architecture

```
React SPA (MapLibre + deck.gl) ──► Caddy ──┬─► /api, /admin  → Django + DRF (gunicorn)
                                           ├─► /tiles/v/*    → Martin (vector tiles, `tiles` schema only)
                                           ├─► /tiles/r/*    → TiTiler (COGs, allow-listed)
                                           └─► /media/*      → S3 (SeaweedFS locally)
Django ◄─► PostgreSQL 16 + PostGIS + h3-pg     Celery worker/beat ◄─► Redis
```

Decisions are recorded in [docs/adr](docs/adr/README.md).

## Repository layout

| Path | What |
|---|---|
| `backend/` | Django project (`config/`) and apps: `geo` (countries, admin units, H3 grid), `catalog` (datasets, versions, indicators, layers), `poi`, `movement` (restricted GPS + public aggregates), `common` |
| `frontend/` | React 18 + Vite + TypeScript SPA: `app/`, `components/`, `map/`, `features/<screen>/`, `state/`, `api/`, `i18n/`, `styles/` |
| `infra/` | Dockerfiles/config for db (PostGIS + h3-pg), caddy, martin, titiler, seaweedfs |
| `docs/adr/` | Architecture decision records |
| `docs/methods/` | Method notes per indicator (need sign-off before leaving "provisional") |

## Quick start (local)

Requirements: Docker with Compose v2, Node 20 (for frontend dev).

```bash
cp .env.example .env        # then change every secret
docker compose up -d --build
docker compose exec django python manage.py seed_reference
docker compose exec django python manage.py createsuperuser
```

- Portal: http://localhost:8080
- API docs: http://localhost:8080/api/v1/docs/
- Admin: http://localhost:8080/admin/

Frontend with hot reload (proxies `/api` and `/tiles` to the stack on :8080):

```bash
cd frontend && npm install && npm run dev   # http://localhost:5173
```

## Common tasks

| Task | Command |
|---|---|
| Backend tests | `docker compose exec django pytest` |
| Backend lint | `docker compose exec django ruff check .` |
| New migrations | `docker compose exec django python manage.py makemigrations` |
| Build H3 grid | `docker compose exec django python manage.py build_hex_grid UGA` (after loading admin units) |
| Refresh freshness tokens | `docker compose exec django python manage.py refresh_dataset_status` |
| Frontend tests / lint / build | `cd frontend && npm test && npm run lint && npm run build` |
| Celery dashboard | `docker compose --profile ops up -d flower` → http://localhost:5555 |

## API (v1)

`/api/v1/health/`, `/countries/`, `/countries/{iso3}/admin-units/?level=`, `/admin-units/{id}/`,
`/indicators/`, `/layers/?country=&role=`, `/datasets/`. Schema at `/api/v1/schema/`.
Hex data, stats, movement, compare and profiles endpoints follow the SDD §10 milestones.

## Privacy

Raw GPS fixes and herd identities are restricted. Public movement data is hex-aggregated with
at least `GPS_K_THRESHOLD` (default 3) animals per cell. Martin's DB role can only read the
curated `tiles` schema. See [ADR-006](docs/adr/ADR-006-gps-privacy.md).

## Conventions

- Scoped commits; code and docs in separate commits.
- Every feature: spec section updated → GO → build → tests → visual sign-off → ADR if a decision was made.
- All UI strings through i18n keys; status tokens always carry a text label.
