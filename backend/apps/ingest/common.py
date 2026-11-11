"""Shared plumbing for the ingest management commands."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path

import numpy as np
from django.conf import settings
from django.contrib.gis.db.models import Extent
from django.core.management.base import CommandError

from apps.catalog.models import DatasetVersion, RasterAsset
from apps.geo.models import Country

from .cache import cache_dir
from .grid import Grid, write_cog
from .storage import put_file


def get_country(iso3: str) -> Country:
    try:
        return Country.objects.get(iso3=iso3.upper())
    except Country.DoesNotExist as e:
        raise CommandError(f"Unknown country {iso3}; run seed_reference") from e


def country_bounds(country: Country) -> tuple[float, float, float, float]:
    """Extent of the current level-1 boundaries, falling back to the configured bbox."""
    ext = country.admin_units.filter(level=1, valid_to__isnull=True).aggregate(e=Extent("geom"))
    return ext["e"] or country.default_bbox.extent


def country_grid(country: Country, res: float, pad: float | None = None) -> Grid:
    return Grid.covering(country_bounds(country), res, pad=res if pad is None else pad)


def parallel_map[T, R](
    fn: Callable[[T], R], items: Iterable[T], *, echo, label: str, threads: int | None = None
) -> list[R]:
    """Run `fn` over `items` in threads (I/O-bound remote reads), keeping input order."""
    items = list(items)
    results: list[R | None] = [None] * len(items)
    done = 0
    step = max(1, len(items) // 20)
    with ThreadPoolExecutor(max_workers=threads or settings.INGEST_THREADS) as pool:
        futures = {pool.submit(fn, it): i for i, it in enumerate(items)}
        for fut in as_completed(futures):
            results[futures[fut]] = fut.result()
            done += 1
            if done % step == 0 or done == len(items):
                echo(f"  {label}: {done}/{len(items)}")
    return results  # type: ignore[return-value]


def publish_cog(
    array: np.ndarray,
    grid: Grid,
    version: DatasetVersion,
    *,
    iso3: str,
    name: str,
    period: date | None,
) -> RasterAsset:
    """Write a COG, upload it to the COG bucket and register it as a RasterAsset."""
    ds_key = version.dataset.key
    local = cache_dir("cogs", iso3, ds_key) / f"{name}.tif"
    write_cog(array, grid, local)
    key = put_file(local, settings.S3_BUCKET_COG, f"{iso3.lower()}/{ds_key}/{name}.tif")
    RasterAsset.objects.filter(key=key).delete()  # re-runs replace the asset row
    return RasterAsset.objects.create(dataset_version=version, key=key, period_start=period)


def path_for(*parts: str) -> Path:
    return cache_dir(*parts[:-1]) / parts[-1]
