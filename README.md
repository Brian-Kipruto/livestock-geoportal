# Livestock Value Chain Geoportal

A web geoportal that combines satellite, climate, livestock and movement data on a common
hexagon grid so policymakers, investors and technical officers can see **where livestock
investment is viable, what the risks are, and how conditions are changing**.

Commissioned by the UN Economic Commission for Africa (NRFS Section). Pilot: Uganda;
multi-country by configuration (Kenya, Somalia later). ECA owns the code.

> Status: **M1 — Data core (Uganda).** Real boundaries, the H3 grid and the first indicators
> (rainfall anomaly, SPI-3, NDVI anomaly, VCI, surface water, livestock density) are ingested
> into the database with validation reports. The UI does not read them yet (M3); the NDVI
> hexes on the map are still an *illustrative* pattern, labelled as such.

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
| `backend/` | Django project (`config/`) and apps: `geo` (countries, admin units, H3 grid, OSM roads/waterways), `catalog` (datasets, versions, indicators, layers), `poi`, `movement` (restricted GPS + public aggregates), `ingest` (pipelines, SDD §12), `common` |
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
| Refresh freshness tokens | `docker compose exec django python manage.py refresh_dataset_status` |
| Frontend tests / lint / build | `cd frontend && npm test && npm run lint && npm run build` |
| Celery dashboard | `docker compose --profile ops up -d flower` → http://localhost:5555 |

## Data core (SDD §12, Appendix A)

Pipelines are management commands for now (Celery wiring follows in the pilot). Run them in
this order for a country; each is idempotent and writes a `DatasetVersion` plus a validation
report to `media/reports/<dataset>/` (see admin → Dataset versions).

```bash
docker compose exec django python manage.py load_admin_boundaries UGA   # OCHA COD-AB from HDX
docker compose exec django python manage.py build_hex_grid UGA          # H3 res 7, all admin levels
docker compose exec django python manage.py ingest_wofs UGA             # water_freq + hex land_frac
docker compose exec django python manage.py ingest_chirps UGA           # rain_anom_pct, spi3
docker compose exec django python manage.py ingest_modis_ndvi UGA       # ndvi_anom_z, vci (~30 min first run)
docker compose exec django python manage.py ingest_glw4 UGA             # livestock densities
docker compose exec django python manage.py ingest_osm UGA              # roads, waterways, water points
docker compose restart martin                                           # pick up new tile sources
docker compose exec django python manage.py data_core_report UGA        # checkpoint summary
```

Sources are public and need no accounts: Digital Earth Africa (CHIRPS, WOfS), Microsoft
Planetary Computer (MODIS), UCSB CHC (CHIRPS gaps), Harvard Dataverse (GLW4), HOT OSM exports
on HDX (roads, waterways, water points; `--provider geofabrik` for a full .pbf), HDX (boundaries). Downloads and decoded rasters are cached in the `ingest_cache` volume, so
re-runs are quick. Methods: [docs/methods](docs/methods/README.md) (all provisional).

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
