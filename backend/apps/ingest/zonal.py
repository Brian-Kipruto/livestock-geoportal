"""Zonal statistics from a regular grid to the country's H3 res-7 cells (SDD §8.2, §12.1).

exactextract gives, for every hex, the grid cells it touches and the fraction of each cell it
covers. Those fractions become a sparse (hex × pixel) matrix, so a whole time series is
reduced to hexes with one sparse matrix product instead of one polygon pass per period.
"""

from __future__ import annotations

from dataclasses import dataclass

import geopandas as gpd
import h3
import numpy as np
import shapely
from django.db import connection
from exactextract import exact_extract
from exactextract.raster import NumPyRasterSource
from rasterio.crs import CRS
from scipy import sparse

from .grid import Grid

MIN_COVER = 0.5  # a hex needs valid data on ≥ 50 % of its area to get a value


@dataclass
class HexSet:
    h3: np.ndarray  # str, sorted
    gdf: gpd.GeoDataFrame
    area_km2: np.ndarray
    land: np.ndarray  # bool: hex counts towards completeness (land_frac ≥ 0.5 or unknown)

    def __len__(self) -> int:
        return len(self.h3)


def load_hexes(country_id: int) -> HexSet:
    with connection.cursor() as cur:
        cur.execute(
            "SELECT h3::text, ST_AsBinary(geom), land_frac FROM geo_hexcell "
            "WHERE country_id = %s ORDER BY h3",
            [country_id],
        )
        rows = cur.fetchall()
    if not rows:
        raise ValueError("No hex grid for this country; run build_hex_grid first")
    ids = np.array([r[0] for r in rows])
    geoms = shapely.from_wkb([bytes(r[1]) for r in rows])
    land_frac = np.array([np.nan if r[2] is None else r[2] for r in rows], dtype="float32")
    gdf = gpd.GeoDataFrame({"h3": ids}, geometry=geoms, crs="EPSG:4326")
    area = np.array([h3.cell_area(c, unit="km^2") for c in ids])
    land = np.isnan(land_frac) | (land_frac >= 0.5)
    return HexSet(h3=ids, gdf=gdf, area_km2=area, land=land)


class HexWeights:
    """Coverage-fraction matrix W (n_hex × n_pixel) for one grid."""

    def __init__(self, hexes: HexSet, grid: Grid):
        self.grid = grid
        ny, nx = grid.shape
        template = NumPyRasterSource(
            np.zeros((ny, nx), dtype="uint8"),
            grid.west,
            grid.south,
            grid.east,
            grid.north,
            srs_wkt=CRS.from_string(grid.crs).to_wkt(),
        )
        df = exact_extract(template, hexes.gdf, ["cell_id", "coverage"], output="pandas")
        rows = np.repeat(np.arange(len(df)), df["cell_id"].map(len).to_numpy())
        cols = np.concatenate(df["cell_id"].to_numpy()).astype(np.int64)
        vals = np.concatenate(df["coverage"].to_numpy()).astype(np.float32)
        self.W = sparse.csr_matrix((vals, (rows, cols)), shape=(len(df), ny * nx))
        self.total = np.asarray(self.W.sum(axis=1)).ravel()

    def _flatten(self, stack: np.ndarray) -> np.ndarray:
        if stack.ndim == 2:
            stack = stack[None]
        return stack.reshape(stack.shape[0], -1).T  # (pixels, T)

    def mean(self, stack: np.ndarray, min_cover: float = MIN_COVER) -> np.ndarray:
        """Area-weighted mean per hex → (n_hex, T). NaN where < min_cover of the hex is valid."""
        X = self._flatten(stack)
        valid = ~np.isnan(X)
        num = self.W @ np.where(valid, X, 0).astype("float64")
        den = self.W @ valid.astype("float64")
        with np.errstate(invalid="ignore", divide="ignore"):
            out = num / den
        out[den < min_cover * self.total[:, None]] = np.nan
        return out.astype("float32")

    def sum(self, stack: np.ndarray) -> np.ndarray:
        """Coverage-weighted sum per hex → (n_hex, T). For per-pixel counts (e.g. heads)."""
        X = self._flatten(stack)
        return (self.W @ np.nan_to_num(X).astype("float64")).astype("float32")
