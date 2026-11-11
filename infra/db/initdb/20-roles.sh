#!/bin/bash
# Read-only role for Martin. It is granted ONLY the `tiles` schema (see catalog migration),
# so restricted tables such as movement_gpsfix are unreachable from tiles (ADR-006).
set -euo pipefail
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<SQL
DO \$\$ BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'martin_ro') THEN
    CREATE ROLE martin_ro LOGIN PASSWORD '${MARTIN_DB_PASSWORD:?MARTIN_DB_PASSWORD not set}';
  END IF;
END \$\$;
REVOKE ALL ON SCHEMA public FROM martin_ro;
SQL
