import pytest
from django.core.management import call_command


@pytest.fixture
def seeded(db):
    call_command("seed_reference", verbosity=0)
