# PostgreSQL 16 + PostGIS 3 + h3-pg (ADR-002), all from the PGDG apt repo that the official
# image already configures. (postgis/postgis:16-* is bullseye-based and PGDG dropped bullseye.)
FROM postgres:16-bookworm

# Some Docker hosts lack IPv6 routes; apt would hang on AAAA records.
RUN echo 'Acquire::ForceIPv4 "true";' > /etc/apt/apt.conf.d/99force-ipv4 \
 && apt-get update \
 && apt-get install -y --no-install-recommends \
      postgresql-16-postgis-3 postgresql-16-postgis-3-scripts postgresql-16-h3 \
 && rm -rf /var/lib/apt/lists/*

COPY initdb/ /docker-entrypoint-initdb.d/
