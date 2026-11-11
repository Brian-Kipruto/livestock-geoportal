"""Custom model fields.

H3IndexField maps to the native ``h3index`` type from the h3-pg extension (ADR-002).
Values travel through Django as the canonical 15-char hex string, e.g. ``"8767a4b6fffffff"``.
"""

from django.db import models


class H3IndexField(models.Field):
    description = "H3 cell index (h3-pg h3index)"

    def db_type(self, connection):  # noqa: ARG002
        return "h3index"

    def from_db_value(self, value, expression, connection):  # noqa: ARG002
        return None if value is None else str(value)

    def to_python(self, value):
        return None if value is None else str(value)

    def get_prep_value(self, value):
        return None if value is None else str(value).lower()
