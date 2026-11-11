"""Polyfill a country's admin boundaries into the res-7 H3 grid (SDD §12.2).

Each cell is assigned to the deepest admin unit containing its centroid; parent levels are
filled by walking up the hierarchy. Idempotent: re-running replaces the country's cells.
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction

from apps.geo.models import ANALYSIS_RES, Country

SQL = """
WITH units AS (
    SELECT id, (ST_Dump(geom)).geom AS g
    FROM geo_adminunit
    WHERE country_id = %(country)s AND level = %(level)s AND valid_to IS NULL
),
cells AS (
    SELECT DISTINCT ON (cell) cell, id AS leaf_id
    FROM units, LATERAL h3_polygon_to_cells(g, %(res)s) AS cell
    ORDER BY cell, id
)
INSERT INTO geo_hexcell (h3, country_id, admin_l{level}_id, geom)
SELECT cell, %(country)s, leaf_id, h3_cell_to_boundary_geometry(cell)
FROM cells
"""

PARENT_SQL = """
UPDATE geo_hexcell h SET admin_l{parent_level}_id = a.parent_id
FROM geo_adminunit a
WHERE h.country_id = %(country)s AND h.admin_l{level}_id = a.id
"""


class Command(BaseCommand):
    help = "Build the H3 res-7 grid for a country from its deepest loaded admin level."

    def add_arguments(self, parser):
        parser.add_argument("iso3")
        parser.add_argument("--level", type=int, help="Admin level to polyfill (default: deepest)")

    @transaction.atomic
    def handle(self, *args, iso3: str, level: int | None, **opts):
        try:
            country = Country.objects.get(iso3=iso3.upper())
        except Country.DoesNotExist as e:
            raise CommandError(f"Unknown country {iso3}") from e

        level = level or max((u["level"] for u in country.admin_levels), default=None)
        if level is None or level > 4:
            raise CommandError("Pass --level 1..4 (hex_cell stores admin_l1..l4)")
        if not country.admin_units.filter(level=level, valid_to__isnull=True).exists():
            raise CommandError(f"No admin units at level {level} for {iso3}; load boundaries first")

        params = {"country": country.id, "level": level, "res": ANALYSIS_RES}
        with connection.cursor() as cur:
            cur.execute("DELETE FROM geo_hexcell WHERE country_id = %s", [country.id])
            cur.execute(SQL.format(level=level), params)
            n = cur.rowcount
            for lvl in range(level, 1, -1):
                cur.execute(PARENT_SQL.format(level=lvl, parent_level=lvl - 1), params)
        self.stdout.write(self.style.SUCCESS(f"{iso3}: {n} res-{ANALYSIS_RES} cells"))
