"""Grid conventions: alignment, north-up row order, exact inside fractions."""
import geopandas as gpd
import pytest
from shapely.geometry import Polygon, box

from tadla.data.grid import build_grid, cell_id

EPSG = 26191


def area_gdf(geom):
    return gpd.GeoDataFrame({"id": [1]}, geometry=[geom], crs=f"EPSG:{EPSG}")


def test_fractions_sum_to_area_and_alignment():
    poly = box(349_759, 179_330, 352_200, 181_500)          # 2.441 km x 2.17 km, unaligned
    cells, frame = build_grid(area_gdf(poly), 1000, EPSG)
    assert frame["x_left"] == 349_000 and frame["y_top"] == 182_000
    assert (cells.x_min % 1000 == 0).all() and (cells.y_min % 1000 == 0).all()
    assert cells.area_inside_m2.sum() == pytest.approx(poly.area, rel=1e-12)
    assert ((cells.frac_inside > 0) & (cells.frac_inside <= 1)).all()
    assert len(cells) == 4 * 3                               # cols 349..352, rows 179..181


def test_row_zero_is_north():
    poly = box(349_500, 179_500, 351_500, 182_500)
    cells, frame = build_grid(area_gdf(poly), 1000, EPSG)
    north = cells.loc[cells.row == 0]
    south = cells.loc[cells.row == cells.row.max()]
    assert north.y_min.min() > south.y_min.max()
    # affine transform maps (col + .5, row + .5) to the cell centre
    a, _, c, _, e, f = frame["transform"]
    for _, r in cells.iterrows():
        assert c + a * (r.col + 0.5) == r.x_center
        assert f + e * (r.row + 0.5) == r.y_center


def test_edge_touching_cell_excluded():
    poly = box(349_000, 179_000, 350_000, 180_000)           # exactly one cell
    cells, _ = build_grid(area_gdf(poly), 1000, EPSG)
    assert list(cells.cell_id) == [cell_id(349_000, 179_000)] == ["X349_Y179"]
    assert cells.frac_inside.iloc[0] == pytest.approx(1.0)


def test_triangle_fraction():
    tri = Polygon([(349_000, 179_000), (350_000, 179_000), (349_000, 180_000)])
    cells, _ = build_grid(area_gdf(tri), 1000, EPSG)
    assert len(cells) == 1 and cells.frac_inside.iloc[0] == pytest.approx(0.5)
