"""Phase 1, step 3 — per-cell export from Earth Engine (+ SoilGrids WCS) for the 1 km grid.

Reads config.yaml and the grid of scripts/01b_build_grid.py. Writes to outputs/01_export/:
  static/cells.parquet          cell_id, row, col, frac_inside, x/y and lon/lat of the clipped-cell centroid
  static/dem.parquet            ALOS AW3D30 V4.1 elevation per cell (mean, stdDev, min, max; m)
  static/soil.parquet           SoilGrids clay, silt, sand (%), ocd (kg/m³), wv0010 (vol %): 0–5, 5–15 cm and
                                the depth-weighted 0–15 cm value used for modelling
  <year>/hls_monthly.parquet    NDVI mean/std, valid-pixel fraction, clear days per pixel, share of
                                high-aerosol observations, per cell-month
  <year>/hls_meta.json          acquisition days and granules per month
  <year>/climate_daily.parquet  daily ERA5-Land / CHIRPS in physical units + FAO-56 ET0, per cell-day
  <year>/climate_monthly.parquet
  run.log

Usage:
  python scripts/01_export.py --years 2022                # static (if missing) + one year
  python scripts/01_export.py --all                       # every year of config period
  python scripts/01_export.py --years 2022 --parts hls    # only some parts: static, hls, climate
  add --overwrite to recompute existing files
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import ee  # noqa: E402
import geopandas as gpd  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from tadla.config import gcp_project, load_config, repo_path  # noqa: E402
from tadla.data import climate, soilgrids  # noqa: E402
from tadla.data import gee_export as g  # noqa: E402
from tadla.data.grid import clip_cells  # noqa: E402

log = logging.getLogger("01_export")

HLS_COLUMNS = ["cell_id", "ndvi_mean", "ndvi_stdDev", "ndvi_count", "px_count", "nclear_mean", "nclear_max",
               "aerohi_mean"]


def retry(fn, what: str, tries: int = 4, wait_s: int = 20):
    for k in range(1, tries + 1):
        try:
            return fn()
        except ee.EEException as exc:
            if k == tries:
                raise
            log.warning("%s failed (%s), retry %d/%d in %ds", what, str(exc)[:120], k, tries - 1, wait_s)
            time.sleep(wait_s)


# ----------------------------------------------------------------------------- static
def export_static(cfg, cc: gpd.GeoDataFrame, fc, out: Path, overwrite: bool) -> None:
    out.mkdir(parents=True, exist_ok=True)
    epsg = int(cfg["crs"]["epsg"])

    p = out / "cells.parquet"
    if overwrite or not p.exists():
        cent = cc.geometry.centroid                 # centroid of the part of the cell inside the area
        ll = gpd.GeoSeries(cent, crs=cc.crs).to_crs(4326)   # PROJ, standard EPSG datum shift
        cells = pd.DataFrame({
            "cell_id": cc.cell_id, "row": cc.row, "col": cc["col"], "frac_inside": cc.frac_inside,
            "area_inside_m2": cc.area_inside_m2, "x_centroid": cent.x, "y_centroid": cent.y,
            "lon_deg": ll.x, "lat_deg": ll.y})
        cells.to_parquet(p, index=False)
        log.info("static: cells.parquet (%d cells)", len(cells))

    p = out / "dem.parquet"
    if overwrite or not p.exists():
        df = retry(lambda: g.fetch_table(g.dem_cells(fc, cfg["export"]["dem"])), "DEM")
        df = df.rename(columns={"mean": "dem_mean_m", "stdDev": "dem_std_m", "min": "dem_min_m", "max": "dem_max_m"})
        df.to_parquet(p, index=False)
        log.info("static: dem.parquet, mean elevation %.1f–%.1f m", df.dem_mean_m.min(), df.dem_mean_m.max())

    p = out / "soil.parquet"
    if overwrite or not p.exists():
        sc = cfg["export"]["soilgrids"]
        bbox = soilgrids.igh_bbox(cc.total_bounds, epsg)
        soil = pd.DataFrame({"cell_id": cc.cell_id.to_numpy()})
        for prop in sc["properties"]:
            for depth in sc["depths"]:
                tif = soilgrids.download(sc["wcs"], prop, depth, bbox, repo_path(sc["raw_dir"]))
                raw = soilgrids.cell_means(tif, cc, sc["resample_m"])
                # mapped units -> conventional units (see tadla.data.soilgrids docstring)
                soil[f"{prop}_{depth.replace('-', '_')}"] = raw / soilgrids.CONVERSION[prop]
            # depth-weighted topsoil value (decisions.md D9)
            w = sc["depth_weights"]
            soil[f"{prop}_0_15cm"] = sum(soil[f"{prop}_{d.replace('-', '_')}"] * wt for d, wt in w.items()) / sum(w.values())
        soil.to_parquet(p, index=False)
        log.info("static: soil.parquet, columns %s", [c for c in soil.columns if c != "cell_id"])


# ----------------------------------------------------------------------------- one year
def export_hls_year(cfg, fc, region, year: int, out: Path, overwrite: bool) -> None:
    p = out / "hls_monthly.parquet"
    if p.exists() and not overwrite:
        log.info("%d: hls_monthly.parquet exists, skipped", year)
        return
    hcfg = dict(cfg["export"]["hls"])
    hcfg["collections"] = cfg["gee"]["collections"]
    frames, meta = [], {}
    for m in range(1, 13):
        t0 = time.time()
        fcm, md = g.hls_month(fc, hcfg, cfg["gee"]["hls_tiles"], region, year, m)
        df = retry(lambda: g.fetch_table(fcm, HLS_COLUMNS), f"HLS {year}-{m:02d}")
        meta[f"{year}-{m:02d}"] = md.getInfo()
        df["year"], df["month"] = year, m
        frames.append(df)
        log.info("%d-%02d HLS: %s, %.0fs", year, m, meta[f"{year}-{m:02d}"], time.time() - t0)
    hls = pd.concat(frames, ignore_index=True).rename(columns={
        "ndvi_stdDev": "ndvi_std", "ndvi_count": "n_valid_px", "px_count": "n_px",
        "nclear_mean": "n_clear_mean", "nclear_max": "n_clear_max", "aerohi_mean": "aero_hi_frac"})
    hls["valid_frac"] = hls.n_valid_px / hls.n_px.where(hls.n_px > 0)
    hls.to_parquet(p, index=False)
    (out / "hls_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")


def export_climate_year(cfg, fc, static_cells: pd.DataFrame, year: int, out: Path, overwrite: bool) -> None:
    p = out / "climate_monthly.parquet"
    if p.exists() and not overwrite:
        log.info("%d: climate_monthly.parquet exists, skipped", year)
        return
    days = []
    for m in range(1, 13):
        t0 = time.time()
        fcm = g.climate_month(fc, year, m, cfg["export"]["climate"]["sample_scale_m"], int(cfg["crs"]["epsg"]))
        wide = retry(lambda: g.fetch_table(fcm), f"climate {year}-{m:02d}")
        days.append(climate.to_physical(climate.wide_to_long(wide, year, m)))
        log.info("%d-%02d climate: %d cell-days, %.0fs", year, m, len(days[-1]), time.time() - t0)
    daily = climate.add_et0(pd.concat(days, ignore_index=True), static_cells)
    daily.to_parquet(out / "climate_daily.parquet", index=False)
    climate.monthly(daily).to_parquet(p, index=False)


# ----------------------------------------------------------------------------- main
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", type=int, nargs="*", default=[])
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--parts", default="static,hls,climate")
    ap.add_argument("--overwrite", action="store_true")
    args = ap.parse_args()

    cfg = load_config()
    out_root = repo_path(cfg["export"]["out_dir"])
    out_root.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                        handlers=[logging.StreamHandler(),
                                  logging.FileHandler(out_root / "run.log", mode="a", encoding="utf-8")])
    years = list(range(cfg["period"]["start_year"], cfg["period"]["end_year"] + 1)) if args.all else args.years
    parts = set(args.parts.split(","))
    log.info("=== run: years=%s parts=%s overwrite=%s", years, sorted(parts), args.overwrite)

    g.init_ee(gcp_project(cfg))
    cells = gpd.read_file(repo_path(cfg["grid"]["file"]))
    area = gpd.read_file(cfg["paths"]["area_shapefile"])
    cc = clip_cells(cells, area)
    fc = g.cells_fc(cc, int(cfg["crs"]["epsg"]))
    region = ee.FeatureCollection(cfg["paths"]["gee_area_asset_v2"]).geometry()   # only for filterBounds

    static_dir = out_root / "static"
    if "static" in parts or not (static_dir / "dem.parquet").exists():
        export_static(cfg, cc, fc, static_dir, args.overwrite and "static" in parts)
    static_cells = pd.read_parquet(static_dir / "cells.parquet").merge(
        pd.read_parquet(static_dir / "dem.parquet")[["cell_id", "dem_mean_m"]], on="cell_id", how="left")
    # elevation for Rso (Eq. 37); slivers without a DEM value get the area median (effect < 0.5 %)
    static_cells["z_m"] = static_cells.dem_mean_m.fillna(static_cells.dem_mean_m.median())

    for y in years:
        yd = out_root / str(y)
        yd.mkdir(exist_ok=True)
        if "hls" in parts:
            export_hls_year(cfg, fc, region, y, yd, args.overwrite)
        if "climate" in parts:
            export_climate_year(cfg, fc, static_cells, y, yd, args.overwrite)
    log.info("=== done")


if __name__ == "__main__":
    main()
