# ADR-001 — Django + DRF + GeoDjango backend

**Status:** Accepted (SDD §6.4 ✅ DECIDED)

## Context
A sole developer must deliver an API, auth with roles, a data-steward admin and PDF generation, then hand it to a ministry IT team (C1, C5). The inception report names Django.

## Decision
Python 3.12, Django 5.2 LTS, Django REST Framework, GeoDjango on PostGIS, drf-spectacular for OpenAPI, Celery for jobs.

## Consequences
- Django admin is the steward interface for free (FR-A*), which lowers handover risk (R11).
- Heavy spatial queries are SQL views/functions called from DRF, not ORM chains.
- Django never serves tiles (Martin/TiTiler do).
