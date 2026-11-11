"""Shared vocabularies used across the data model (SDD §2.3, §8.4)."""

from django.db import models


class Theme(models.TextChoices):
    PASTURE_WATER = "pasture_water", "Pasture & water"
    CLIMATE = "climate", "Climate risk"
    LIVESTOCK = "livestock", "Livestock"
    MARKETS = "markets", "Markets & access"
    LAND = "land", "Land & tenure"
    HEALTH = "health", "Animal health"
    MOVEMENT = "movement", "Movement"
    BOUNDARIES = "boundaries", "Boundaries & reference"


class ValueChain(models.TextChoices):
    UPSTREAM = "upstream", "Upstream"
    MIDSTREAM = "midstream", "Midstream"
    DOWNSTREAM = "downstream", "Downstream"


class AccessLevel(models.TextChoices):
    PUBLIC = "public", "Public"
    REGISTERED = "registered", "Registered"
    RESTRICTED = "restricted", "Restricted"


class Role(models.TextChoices):
    """UI presentation presets — NOT permissions (SDD §3.2)."""

    POLICY = "policy", "Policy"
    INVESTOR = "investor", "Investor"
    TECHNICAL = "technical", "Technical"
