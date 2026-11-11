"""Enable PostGIS + h3-pg and create the auth groups from SDD §13.

CREATE EXTENSION needs a superuser; in prod the DB init script creates them first
so this migration becomes a no-op.
"""

from django.db import migrations

GROUPS = ["registered", "steward", "admin"]


def create_groups(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    for name in GROUPS:
        Group.objects.get_or_create(name=name)


def remove_groups(apps, schema_editor):
    apps.get_model("auth", "Group").objects.filter(name__in=GROUPS).delete()


class Migration(migrations.Migration):
    initial = True
    dependencies = [("auth", "0012_alter_user_first_name_max_length")]

    operations = [
        migrations.RunSQL(
            "CREATE EXTENSION IF NOT EXISTS postgis;"
            "CREATE EXTENSION IF NOT EXISTS h3;"
            "CREATE EXTENSION IF NOT EXISTS h3_postgis CASCADE;",
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.RunPython(create_groups, remove_groups),
    ]
