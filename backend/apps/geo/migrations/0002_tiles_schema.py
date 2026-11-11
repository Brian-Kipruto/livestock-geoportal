"""Curated `tiles` schema for Martin (ADR-006).

Martin's role (`martin_ro`, created by infra/db/initdb) can read ONLY this schema. Every vector
tile source is a reviewed view here, so restricted tables (GPS fixes, herds) can never be
published by accident. Add new sources as views in a new migration.
"""

from django.db import migrations

VIEWS = """
CREATE SCHEMA IF NOT EXISTS tiles;

CREATE OR REPLACE VIEW tiles.admin_unit AS
SELECT a.id, c.iso3 AS country, a.level, a.code, a.name, a.parent_id, a.boundary_version, a.geom
FROM geo_adminunit a
JOIN geo_country c ON c.id = a.country_id
WHERE a.valid_to IS NULL AND c.is_active;

CREATE OR REPLACE VIEW tiles.poi AS
SELECT p.id, c.iso3 AS country, t.key AS poi_type, t.value_chain, p.name, p.geom
FROM poi_poi p
JOIN geo_country c ON c.id = p.country_id
JOIN poi_poitype t ON t.id = p.poi_type_id
WHERE c.is_active;

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'martin_ro') THEN
    GRANT USAGE ON SCHEMA tiles TO martin_ro;
    GRANT SELECT ON ALL TABLES IN SCHEMA tiles TO martin_ro;
    ALTER DEFAULT PRIVILEGES IN SCHEMA tiles GRANT SELECT ON TABLES TO martin_ro;
  END IF;
END $$;
"""

DROP = "DROP VIEW IF EXISTS tiles.poi; DROP VIEW IF EXISTS tiles.admin_unit;"


class Migration(migrations.Migration):
    dependencies = [
        ("geo", "0001_initial"),
        ("poi", "0001_initial"),
    ]

    operations = [migrations.RunSQL(VIEWS, reverse_sql=DROP)]
