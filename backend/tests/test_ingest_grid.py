"""Grid snapping, raster reading and hex zonal weights on synthetic data."""

import geopandas as gpd
import h3
import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin
from shapely.geometry import Polygon

from apps.ingest.grid import Grid, mosaic, read_to_grid
from apps.ingest.zonal import HexSet, HexWeights


def test_grid_snaps_outward():
    g = Grid.covering((29.57, -1.48, 35.03, 4.22), 0.05)
    assert g.bounds == pytest.approx((29.55, -1.5, 35.05, 4.25))
    assert g.shape == (115, 110)
    assert g.transform.c == pytest.approx(29.55) and g.transform.f == pytest.approx(4.25)


def _write(path, data, transform, crs="EPSG:4326", nodata=None):
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        width=data.shape[1],
        height=data.shape[0],
        count=1,
        dtype=data.dtype,
        crs=crs,
        transform=transform,
        nodata=nodata,
    ) as dst:
        dst.write(data, 1)


def test_read_to_grid_masks_nodata_and_range(tmp_path):
    data = np.arange(100, dtype="int16").reshape(10, 10)
    data[0, 0] = -3000
    p = tmp_path / "a.tif"
    _write(p, data, from_origin(30, 2, 0.1, 0.1), nodata=-3000)
    grid = Grid(30, 1, 31, 2, 0.1)
    out = read_to_grid(str(p), grid, valid_range=(0, 90), scale=0.5)
    assert np.isnan(out[0, 0])  # nodata
    assert np.isnan(out[9, 9])  # 99 > valid max 90
    assert out[0, 1] == pytest.approx(0.5)


def test_read_to_grid_outside_is_nan(tmp_path):
    p = tmp_path / "b.tif"
    _write(p, np.ones((10, 10), "float32"), from_origin(50, 2, 0.1, 0.1))
    assert np.isnan(read_to_grid(str(p), Grid(30, 1, 31, 2, 0.1))).all()


def test_read_to_grid_reprojects(tmp_path):
    # A constant raster in Web Mercator lands as the same constant on the 4326 grid.
    p = tmp_path / "c.tif"
    _write(
        p,
        np.full((200, 200), 7, "float32"),
        from_origin(3330000, 225000, 1000, 1000),
        crs="EPSG:3857",
    )
    out = read_to_grid(str(p), Grid(30.2, 0.5, 31.5, 1.8, 0.05))
    assert np.nanmin(out) == pytest.approx(7) and np.nanmax(out) == pytest.approx(7)


def test_mosaic_first_valid():
    g = Grid(0, 0, 2, 1, 1)
    a = np.array([[1, np.nan]], "float32")
    b = np.array([[5, 2]], "float32")
    assert mosaic([a, b], g).tolist() == [[1, 2]]


def _hexset(cells):
    geoms = [Polygon([(lng, lat) for lat, lng in h3.cell_to_boundary(c)]) for c in cells]
    gdf = gpd.GeoDataFrame({"h3": cells}, geometry=geoms, crs="EPSG:4326")
    area = np.array([h3.cell_area(c, unit="km^2") for c in cells])
    return HexSet(h3=np.array(cells), gdf=gdf, area_km2=area, land=np.ones(len(cells), bool))


def test_hex_weights_mean_and_sum():
    center = h3.latlng_to_cell(1.0, 32.0, 7)
    cells = sorted([center, *h3.grid_ring(center, 1)[:2]])
    hexes = _hexset(cells)
    grid = Grid.covering(tuple(hexes.gdf.total_bounds), 0.002, pad=0.01)
    W = HexWeights(hexes, grid)

    const = np.full(grid.shape, 3.0, "float32")
    assert np.allclose(W.mean(const), 3.0)

    # Left half NaN: hexes mostly in the NaN half get NaN, others keep the value.
    half = const.copy()
    half[:, : grid.shape[1] // 2] = np.nan
    m = W.mean(half)
    assert np.all(np.isnan(m) | np.isclose(m, 3.0))

    # Summing "1 per pixel" counts pixels ≈ hex area / pixel area.
    px_km2 = (0.002 * 111.32) ** 2
    counts = W.sum(np.ones(grid.shape, "float32"))[:, 0]
    assert np.allclose(counts * px_km2, hexes.area_km2, rtol=0.02)

    # Time stacks reduce column-wise.
    stack = np.stack([const, const * 2])
    assert np.allclose(W.mean(stack), [[3.0, 6.0]] * len(cells))
