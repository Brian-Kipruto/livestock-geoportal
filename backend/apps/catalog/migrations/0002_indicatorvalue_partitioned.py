"""Create the range-partitioned hex time-series table (SDD §8.4).

Django can't declare partitioned tables, so `IndicatorValue` is `managed = False` and the table
is created here. Partitions: one for static values (period 1900-01-01), one per year
2000–2035, and a DEFAULT catch-all. `catalog_ensure_year_partition(y)` adds more years.
"""

from django.db import migrations

CREATE = """
CREATE TABLE catalog_indicatorvalue (
    indicator_id        bigint NOT NULL REFERENCES catalog_indicator(id),
    h3                  h3index NOT NULL,
    period_start        date NOT NULL,
    scenario            varchar(10) NOT NULL DEFAULT 'obs',
    horizon             varchar(12) NOT NULL DEFAULT 'current',
    value               real,
    value_p10           real,
    value_p90           real,
    dataset_version_id  bigint REFERENCES catalog_datasetversion(id),
    PRIMARY KEY (indicator_id, h3, period_start, scenario, horizon)
) PARTITION BY RANGE (period_start);

CREATE TABLE catalog_indicatorvalue_static PARTITION OF catalog_indicatorvalue
    FOR VALUES FROM ('1900-01-01') TO ('1901-01-01');
CREATE TABLE catalog_indicatorvalue_default PARTITION OF catalog_indicatorvalue DEFAULT;

CREATE OR REPLACE FUNCTION catalog_ensure_year_partition(y int) RETURNS void
LANGUAGE plpgsql AS $$
BEGIN
  EXECUTE format(
    'CREATE TABLE IF NOT EXISTS catalog_indicatorvalue_y%s PARTITION OF catalog_indicatorvalue
       FOR VALUES FROM (%L) TO (%L)',
    y, make_date(y, 1, 1), make_date(y + 1, 1, 1));
END $$;

SELECT catalog_ensure_year_partition(y) FROM generate_series(2000, 2035) AS y;

CREATE INDEX catalog_indicatorvalue_h3_idx ON catalog_indicatorvalue (h3);
CREATE INDEX catalog_indicatorvalue_period_idx
    ON catalog_indicatorvalue (indicator_id, period_start, scenario, horizon);
"""

DROP = """
DROP TABLE IF EXISTS catalog_indicatorvalue CASCADE;
DROP FUNCTION IF EXISTS catalog_ensure_year_partition(int);
"""


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0001_initial"),
        ("common", "0001_extensions_and_groups"),
    ]

    operations = [migrations.RunSQL(CREATE, reverse_sql=DROP)]
