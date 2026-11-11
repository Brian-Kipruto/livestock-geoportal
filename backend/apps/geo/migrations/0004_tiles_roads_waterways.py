"""Vector tile sources for OSM roads and waterways (ADR-006: tile sources live in `tiles`).

These are Martin *function* sources rather than views so detail depends on zoom: a national
view of every track and stream is ~1 MB per tile. Classes shown:
  road      z < 8: motorway…secondary · z 8–10: + tertiary, unclassified · z ≥ 11: + track
  waterway  z < 9: rivers, canals     · z ≥ 9: + streams
SECURITY DEFINER lets `martin_ro` execute them without read access to the base tables.
Martin picks up new sources on restart.
"""

from django.db import migrations

FUNCTIONS = """
CREATE OR REPLACE FUNCTION tiles.road(z integer, x integer, y integer)
RETURNS bytea
LANGUAGE sql STABLE PARALLEL SAFE SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
  WITH b AS (SELECT ST_TileEnvelope(z, x, y) AS env),
  feats AS (
    SELECT r.id, c.iso3 AS country, r.highway, r.name, r.surface,
           ST_AsMVTGeom(ST_Transform(r.geom, 3857), b.env, 4096, 64, true) AS geom
    FROM geo_road r
    JOIN geo_country c ON c.id = r.country_id AND c.is_active
    CROSS JOIN b
    WHERE r.geom && ST_Transform(b.env, 4326)
      AND (
        r.highway IN ('motorway', 'motorway_link', 'trunk', 'trunk_link', 'primary',
                      'primary_link', 'secondary', 'secondary_link')
        OR (z >= 8 AND r.highway IN ('tertiary', 'tertiary_link', 'unclassified'))
        OR z >= 11
      )
  )
  SELECT ST_AsMVT(feats, 'road', 4096, 'geom') FROM feats;
$$;

CREATE OR REPLACE FUNCTION tiles.waterway(z integer, x integer, y integer)
RETURNS bytea
LANGUAGE sql STABLE PARALLEL SAFE SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
  WITH b AS (SELECT ST_TileEnvelope(z, x, y) AS env),
  feats AS (
    SELECT w.id, c.iso3 AS country, w.waterway, w.name,
           ST_AsMVTGeom(ST_Transform(w.geom, 3857), b.env, 4096, 64, true) AS geom
    FROM geo_waterway w
    JOIN geo_country c ON c.id = w.country_id AND c.is_active
    CROSS JOIN b
    WHERE w.geom && ST_Transform(b.env, 4326)
      AND (w.waterway IN ('river', 'canal') OR z >= 9)
  )
  SELECT ST_AsMVT(feats, 'waterway', 4096, 'geom') FROM feats;
$$;

REVOKE ALL ON FUNCTION tiles.road(integer, integer, integer) FROM PUBLIC;
REVOKE ALL ON FUNCTION tiles.waterway(integer, integer, integer) FROM PUBLIC;
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'martin_ro') THEN
    GRANT EXECUTE ON FUNCTION tiles.road(integer, integer, integer) TO martin_ro;
    GRANT EXECUTE ON FUNCTION tiles.waterway(integer, integer, integer) TO martin_ro;
  END IF;
END $$;
"""

DROP = """
DROP FUNCTION IF EXISTS tiles.waterway(integer, integer, integer);
DROP FUNCTION IF EXISTS tiles.road(integer, integer, integer);
"""


class Migration(migrations.Migration):
    dependencies = [
        ("geo", "0003_country_sources_hexcell_admin_l4_road_waterway"),
    ]

    operations = [migrations.RunSQL(FUNCTIONS, reverse_sql=DROP)]
