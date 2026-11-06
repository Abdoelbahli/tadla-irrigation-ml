"""Phase 1, step 2 — build the fixed 1 km analysis grid over the study area.

Reads config.yaml (paths.area_shapefile, crs.epsg, grid.cell_size_m) and writes to outputs/01b_grid/:
  grid_1km.gpkg      cells overlapping area.shp (EPSG:26191) with their inside fraction
  grid_1km.csv       same, without geometry
  grid_meta.json     frame (origin, rows, cols, affine transform) and the checks below
  grid_1km.png       quick-look map, north up, with the area outline
  run.log

Checks: area.shp area vs the 701.83 km² of CLAUDE.md; sum of inside areas == area; local
area.shp vs the Earth Engine asset (same polygon?); cell counts per inside-fraction class.

Usage:  python scripts/01b_build_grid.py
"""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import ee  # noqa: E402
import geopandas as gpd  # noqa: E402
import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from shapely.geometry import mapping  # noqa: E402

from tadla.config import gcp_project, load_config, repo_path  # noqa: E402
from tadla.data.gee_export import init_ee  # noqa: E402
from tadla.data.grid import build_grid  # noqa: E402

EXPECTED_AREA_KM2 = 701.83  # CLAUDE.md, "Established facts"


def compare_with_asset(local_geom, asset_id: str, epsg: int) -> dict:
    """Areas (km²) of the EE asset and of its symmetric difference with the local polygon,
    both computed planar in EPSG:`epsg`."""
    proj = f"EPSG:{epsg}"
    asset = ee.FeatureCollection(asset_id).geometry()
    local = ee.Geometry(mapping(local_geom), proj, False)
    sym = asset.symmetricDifference(local, maxError=0.1, proj=proj)
    res = ee.Dictionary({
        "asset_area_km2": asset.area(maxError=0.1, proj=proj).divide(1e6),
        "symdiff_area_km2": sym.area(maxError=0.1, proj=proj).divide(1e6),
    }).getInfo()
    return res


def main() -> None:
    cfg = load_config()
    out = repo_path(cfg["paths"]["outputs_dir"]) / "01b_grid"
    out.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s",
                        handlers=[logging.StreamHandler(),
                                  logging.FileHandler(out / "run.log", mode="w", encoding="utf-8")])
    log = logging.getLogger("01b")

    epsg = int(cfg["crs"]["epsg"])
    size = float(cfg["grid"]["cell_size_m"])
    area = gpd.read_file(cfg["paths"]["area_shapefile"])
    log.info("area.shp: %d feature(s), CRS %s", len(area), area.crs)
    if area.crs is None or area.crs.to_epsg() != epsg:
        raise ValueError(f"area.shp CRS is {area.crs}, expected EPSG:{epsg}")

    cells, frame = build_grid(area, size, epsg)
    area_km2 = frame["area_m2"] / 1e6
    inside_km2 = cells.area_inside_m2.sum() / 1e6
    checks = {
        "area_shp_km2": round(area_km2, 4),
        "expected_km2_claude_md": EXPECTED_AREA_KM2,
        "sum_inside_km2": round(inside_km2, 4),
        "n_cells": int(len(cells)),
        "n_cells_full": int((cells.frac_inside > 0.999999).sum()),
        "n_cells_frac_ge_0.5": int((cells.frac_inside >= 0.5).sum()),
        "n_cells_frac_ge_0.01": int((cells.frac_inside >= 0.01).sum()),
        "n_cells_frac_lt_0.01": int((cells.frac_inside < 0.01).sum()),
    }
    log.info("area.shp %.4f km² (CLAUDE.md: %.2f); sum of inside areas %.4f km²",
             area_km2, EXPECTED_AREA_KM2, inside_km2)
    assert abs(inside_km2 - area_km2) < 1e-6, "inside areas do not add up to the area"
    log.info("grid %d rows x %d cols, origin (x_left=%.0f, y_top=%.0f); %d cells overlap the area",
             frame["nrow"], frame["ncol"], frame["x_left"], frame["y_top"], len(cells))

    init_ee(gcp_project(cfg))
    asset_cmp = compare_with_asset(area.geometry.union_all(), cfg["paths"]["gee_area_asset"], epsg)
    checks.update({k: round(v, 6) for k, v in asset_cmp.items()})
    log.info("EE asset area %.4f km²; symmetric difference with area.shp %.6f km²",
             asset_cmp["asset_area_km2"], asset_cmp["symdiff_area_km2"])

    cells.to_file(out / "grid_1km.gpkg", driver="GPKG", layer="grid_1km")
    cells.drop(columns="geometry").to_csv(out / "grid_1km.csv", index=False)
    (out / "grid_meta.json").write_text(json.dumps({"frame": frame, "checks": checks}, indent=2),
                                        encoding="utf-8")

    fig, ax = plt.subplots(figsize=(10, 5))
    cells.plot(ax=ax, column="frac_inside", cmap="viridis", edgecolor="white", linewidth=0.2,
               legend=True, legend_kwds={"label": "fraction of the cell inside the area", "shrink": 0.7})
    area.boundary.plot(ax=ax, color="red", linewidth=0.8)
    ax.set_title(f"1 km grid: {len(cells)} cells overlapping area.shp (EPSG:{epsg}, north up)")
    ax.set_xlabel("x (m)"); ax.set_ylabel("y (m)")
    fig.tight_layout(); fig.savefig(out / "grid_1km.png", dpi=110); plt.close(fig)
    log.info("written %s", out)
    for k, v in checks.items():
        log.info("  %-24s %s", k, v)


if __name__ == "__main__":
    main()
