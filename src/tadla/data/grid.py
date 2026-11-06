"""Fixed analysis grid (default 1 km) in a projected CRS.

Conventions (to avoid the north-south flip of the old 1 km rasters, old_code_notes.md §4.1):
- cells are aligned on multiples of `cell_size` in the projected CRS;
- `row` 0 is the NORTHERNMOST row and increases southwards, `col` 0 is the westernmost
  column (standard raster order), so the affine transform is
  (cell_size, 0, x_left, 0, -cell_size, y_top).
"""
from __future__ import annotations

import math

import geopandas as gpd
from shapely.geometry import box


def grid_frame(bounds: tuple[float, float, float, float], cell_size: float) -> dict:
    """Aligned frame enclosing `bounds` (xmin, ymin, xmax, ymax)."""
    xmin, ymin, xmax, ymax = bounds
    x_left = math.floor(xmin / cell_size) * cell_size
    y_bottom = math.floor(ymin / cell_size) * cell_size
    x_right = math.ceil(xmax / cell_size) * cell_size
    y_top = math.ceil(ymax / cell_size) * cell_size
    return {
        "cell_size": cell_size,
        "x_left": x_left,
        "y_top": y_top,
        "ncol": round((x_right - x_left) / cell_size),
        "nrow": round((y_top - y_bottom) / cell_size),
        "transform": [cell_size, 0.0, x_left, 0.0, -cell_size, y_top],
    }


def cell_id(x_min: float, y_min: float) -> str:
    """Stable id from the lower-left corner in km, e.g. 'X349_Y179'."""
    return f"X{x_min / 1000:g}_Y{y_min / 1000:g}"


def build_grid(area: gpd.GeoDataFrame, cell_size: float, epsg: int) -> tuple[gpd.GeoDataFrame, dict]:
    """Cells of the aligned grid that overlap `area` with a positive area.

    Returns (cells, frame). `cells` has: cell_id, row, col, x_min, y_min, x_center, y_center,
    area_inside_m2, frac_inside (share of the cell inside the area, 0–1], geometry (the full cell).
    """
    area = area.to_crs(epsg=epsg)
    geom = area.geometry.union_all()
    frame = grid_frame(geom.bounds, cell_size)
    rows = []
    for r in range(frame["nrow"]):
        y_max = frame["y_top"] - r * cell_size
        y_min = y_max - cell_size
        for c in range(frame["ncol"]):
            x_min = frame["x_left"] + c * cell_size
            cell = box(x_min, y_min, x_min + cell_size, y_max)
            if not cell.intersects(geom):
                continue
            inside = cell.intersection(geom).area
            if inside <= 0:  # touches the boundary only along an edge or at a corner
                continue
            rows.append({
                "cell_id": cell_id(x_min, y_min), "row": r, "col": c,
                "x_min": x_min, "y_min": y_min,
                "x_center": x_min + cell_size / 2, "y_center": y_min + cell_size / 2,
                "area_inside_m2": inside, "frac_inside": inside / cell.area,
                "geometry": cell,
            })
    cells = gpd.GeoDataFrame(rows, geometry="geometry", crs=f"EPSG:{epsg}")
    frame["epsg"] = epsg
    frame["area_m2"] = geom.area
    return cells, frame


def clip_cells(cells: gpd.GeoDataFrame, area: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Cells cut to the study area (the part of each cell inside area.shp); same rows/ids."""
    geom = area.to_crs(cells.crs).geometry.union_all()
    out = cells.copy()
    out["geometry"] = cells.geometry.intersection(geom)
    return out
