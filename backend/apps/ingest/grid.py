"""Target grids and source-raster reading (SDD §12.1 "Transform").

Every pipeline reads its sources onto one regular EPSG:4326 grid that covers the country, then
hands that stack to the hex zonal step. Remote COGs are read at the coarsest overview that is
still finer than the target grid, so a 30 m product does not pull full-resolution tiles.
"""

from __future__ import annotations

import math
import time
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import rasterio
import rasterio.errors
from affine import Affine
from rasterio.enums import Resampling
from rasterio.errors import WindowError
from rasterio.warp import reproject, transform_bounds
from rasterio.windows import Window, from_bounds

GDAL_DEFAULTS = {
    "GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR",
    "GDAL_HTTP_MAX_RETRY": "5",
    "GDAL_HTTP_RETRY_DELAY": "2",
    "CPL_VSIL_CURL_ALLOWED_EXTENSIONS": ".tif,.tiff,.TIF",
    "VSI_CACHE": "TRUE",
}


@dataclass(frozen=True)
class Grid:
    """A north-up EPSG:4326 grid. Bounds are snapped to whole multiples of `res`."""

    west: float
    south: float
    east: float
    north: float
    res: float
    crs: str = "EPSG:4326"

    @classmethod
    def covering(cls, bounds: tuple[float, float, float, float], res: float, pad: float = 0.0):
        w, s, e, n = bounds
        snap_down = lambda v: math.floor(round(v / res, 6)) * res  # noqa: E731
        snap_up = lambda v: math.ceil(round(v / res, 6)) * res  # noqa: E731
        return cls(snap_down(w - pad), snap_down(s - pad), snap_up(e + pad), snap_up(n + pad), res)

    @property
    def shape(self) -> tuple[int, int]:
        return (
            round((self.north - self.south) / self.res),
            round((self.east - self.west) / self.res),
        )

    @property
    def transform(self) -> Affine:
        return Affine(self.res, 0.0, self.west, 0.0, -self.res, self.north)

    @property
    def bounds(self) -> tuple[float, float, float, float]:
        return (self.west, self.south, self.east, self.north)

    @property
    def key(self) -> str:
        """Stable id used to key cached arrays to this grid."""
        return f"{self.west:.4f}_{self.south:.4f}_{self.east:.4f}_{self.north:.4f}_{self.res:.6f}"

    def empty(self) -> np.ndarray:
        return np.full(self.shape, np.nan, dtype="float32")


def read_to_grid(
    href: str,
    grid: Grid,
    *,
    resampling: Resampling = Resampling.average,
    nodata: float | None = None,
    valid_range: tuple[float, float] | None = None,
    scale: float = 1.0,
    env: Mapping[str, str] | None = None,
) -> np.ndarray:
    """Read band 1 of `href` onto `grid` as float32, with NaN for nodata/out-of-range/no-cover."""
    out = grid.empty()
    with rasterio.Env(**{**GDAL_DEFAULTS, **(env or {})}), rasterio.open(href) as src:
        src_bounds = transform_bounds(grid.crs, src.crs, *grid.bounds, densify_pts=21)
        try:
            window = (
                from_bounds(*src_bounds, transform=src.transform)
                .round_offsets(op="floor")
                .round_lengths(op="ceil")
                .intersection(Window(0, 0, src.width, src.height))
            )
        except WindowError:
            return out  # source does not overlap the grid
        if window.width < 1 or window.height < 1:
            return out

        # Pick the coarsest overview factor that is still at least as fine as the target.
        target_res_src = (src_bounds[2] - src_bounds[0]) / grid.shape[1]
        wanted = max(1.0, target_res_src / abs(src.res[0]))
        factor = max([1, *(o for o in src.overviews(1) if o <= wanted)])
        out_shape = (
            max(1, math.ceil(window.height / factor)),
            max(1, math.ceil(window.width / factor)),
        )
        arr = src.read(1, window=window, out_shape=out_shape, resampling=Resampling.nearest)
        win_transform = src.window_transform(window) @ Affine.scale(
            window.width / out_shape[1], window.height / out_shape[0]
        )

        data = arr.astype("float32")
        src_nodata = src.nodata if nodata is None else nodata
        if src_nodata is not None and not np.isnan(src_nodata):
            data[arr == src_nodata] = np.nan
        if valid_range is not None:
            data[(data < valid_range[0]) | (data > valid_range[1])] = np.nan
        if scale != 1.0:
            data *= scale

        reproject(
            data,
            out,
            src_transform=win_transform,
            src_crs=src.crs,
            dst_transform=grid.transform,
            dst_crs=grid.crs,
            src_nodata=np.nan,
            dst_nodata=np.nan,
            resampling=resampling,
        )
    return out


def with_retries(fn, tries: int = 4, delay: float = 5.0):
    """Remote COG reads occasionally fail mid-transfer; retry with backoff before giving up."""
    for attempt in range(tries):
        try:
            return fn()
        except rasterio.errors.RasterioIOError:
            if attempt == tries - 1:
                raise
            time.sleep(delay * 2**attempt)
    raise AssertionError("unreachable")


def mosaic(arrays: Iterable[np.ndarray], grid: Grid) -> np.ndarray:
    """First-valid mosaic of same-grid arrays (tiles that don't overlap, or overlap equally)."""
    out = grid.empty()
    for a in arrays:
        np.copyto(out, a, where=np.isnan(out) & ~np.isnan(a))
    return out


def cached(path: Path, compute) -> np.ndarray:
    """Load an array from `path` (.npy) or compute and save it. Keeps re-runs cheap."""
    if path.exists():
        return np.load(path)
    arr = compute()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.stem + ".part.npy")
    np.save(tmp, arr)
    tmp.rename(path)
    return arr


def write_cog(array: np.ndarray, grid: Grid, path: Path) -> Path:
    """Write a float32 COG (NaN nodata) for TiTiler (ADR-004)."""
    profile = {
        "driver": "COG",
        "dtype": "float32",
        "count": 1,
        "height": grid.shape[0],
        "width": grid.shape[1],
        "crs": grid.crs,
        "transform": grid.transform,
        "nodata": np.nan,
        "compress": "DEFLATE",
        "predictor": 3,
        "overview_resampling": "average",
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(array.astype("float32"), 1)
    return path
