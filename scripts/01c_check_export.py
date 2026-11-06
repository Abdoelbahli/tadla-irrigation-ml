"""Phase 1, step 4 — sanity checks of one exported year.

Reads outputs/01_export/{static,<year>} and writes outputs/01c_check_export/<year>/:
  checks.md       all numbers below
  seasonal.png    area-mean monthly NDVI, valid fraction, rainfall, ET0, actual ET
  run.log

Checks
 1. NDVI range, seasonal cycle, valid-pixel fraction and clear days per month.
 2. Area-mean annual rainfall, ET0 (CLAUDE.md: ~1150 mm/yr, July ~165 mm), actual ET (spring peak).
 3. ERA5-Land DAILY_AGGR daily sums vs the sum of the 24 hourly values (radiation, evaporation).
 4. CHIRPS: monthly totals from the daily vs the pentad product.
 5. Static layers: elevation range, soil ranges, clay+silt+sand ~ 100 %.
 6. Cell-by-cell comparison with the old 1 km table (Desktop/train/aggregated_1km_data.parquet)
    when the year is one of the old training years (2017, 2019–2023).
Area means are weighted by the area of each cell inside the study area.

Usage:  python scripts/01c_check_export.py --year 2022
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import ee  # noqa: E402
import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from tadla.config import gcp_project, load_config, repo_path  # noqa: E402

OLD_1KM = Path(r"C:\Users\abdel\OneDrive\Desktop\train\aggregated_1km_data.parquet")
OLD_YEARS = [2017, 2019, 2020, 2021, 2022, 2023]   # order of the 72 months in the old table (2018 excluded)


def wmean(x: pd.Series, w: pd.Series) -> float:
    ok = x.notna() & w.notna()
    return float(np.average(x[ok], weights=w[ok])) if ok.any() else float("nan")


def era5_daily_vs_native(point: ee.Geometry, days: list[str]) -> pd.DataFrame:
    """DAILY_AGGR *_sum bands vs ERA5's native 24 h accumulation of day D, i.e. the accumulated
    band of the HOURLY image at 00 UTC of D+1 (ECMWF convention). Also shows the sum of EE's
    derived '*_hourly' bands, which does NOT match (found 2026-11-06) and is not used."""
    rows = []
    H = ee.ImageCollection("ECMWF/ERA5_LAND/HOURLY")
    for d in days:
        day = ee.Date(d)
        nxt = day.advance(1, "day")
        da = ee.ImageCollection("ECMWF/ERA5_LAND/DAILY_AGGR").filterDate(day, nxt).first()
        nat = H.filterDate(nxt, nxt.advance(1, "hour")).first()
        hs = H.filterDate(day, nxt).select(["surface_solar_radiation_downwards_hourly",
                                            "total_evaporation_hourly"]).sum()
        def v(img, b):
            return img.select(b).reduceRegion(ee.Reducer.first(), point, 11132).get(b)
        r = ee.Dictionary({
            "ssrd_daily": v(da, "surface_solar_radiation_downwards_sum"),
            "ssrd_native": v(nat, "surface_solar_radiation_downwards"),
            "ssrd_sum_hourly": v(hs, "surface_solar_radiation_downwards_hourly"),
            "te_daily": v(da, "total_evaporation_sum"),
            "te_native": v(nat, "total_evaporation"),
            "te_sum_hourly": v(hs, "total_evaporation_hourly")}).getInfo()
        rows.append({"day": d, **{k: (x / 1e6 if k.startswith("ssrd") else x * 1000) for k, x in r.items()}})
    return pd.DataFrame(rows)


def chirps_daily_vs_pentad(region: ee.Geometry, year: int) -> pd.DataFrame:
    rows = []
    for m in range(1, 13):
        s = ee.Date.fromYMD(year, m, 1)
        e = s.advance(1, "month")
        dly = ee.ImageCollection("UCSB-CHG/CHIRPS/DAILY").filterDate(s, e).sum()
        pen = ee.ImageCollection("UCSB-CHG/CHIRPS/PENTAD").filterDate(s, e).sum()
        v = ee.Dictionary({
            "daily": dly.reduceRegion(ee.Reducer.mean(), region, 5566).get("precipitation"),
            "pentad": pen.reduceRegion(ee.Reducer.mean(), region, 5566).get("precipitation")}).getInfo()
        rows.append({"month": m, "daily_sum_mm": v["daily"], "pentad_sum_mm": v["pentad"]})
    return pd.DataFrame(rows)


def compare_old(year: int, hls: pd.DataFrame, clim: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    """New vs old 1 km cell-month values for one of the old training years."""
    old = pd.read_parquet(OLD_1KM)
    k = OLD_YEARS.index(year)
    old = old[(old._month_idx >= 12 * k) & (old._month_idx < 12 * (k + 1))].copy()
    old["month"] = old._month_idx - 12 * k + 1
    old["cell_id"] = [f"X{x / 1000:g}_Y{y / 1000:g}" for x, y in zip(old._cell_x, old._cell_y)]
    new = hls[["cell_id", "month", "ndvi_mean"]].merge(clim[["cell_id", "month", "rain_mm", "et_actual_mm"]],
                                                       on=["cell_id", "month"])
    j = new.merge(old[["cell_id", "month", "NDVI", "rainfall", "evaporation", "month_old"]]
                  if "month_old" in old else old[["cell_id", "month", "NDVI", "rainfall", "evaporation"]],
                  on=["cell_id", "month"], how="inner")
    rows = []
    for new_c, old_c, label in [("ndvi_mean", "NDVI", "NDVI (HLS vs old Sentinel-2)"),
                                ("rain_mm", "rainfall", "rainfall mm/month (CHIRPS vs old CHIRPS)"),
                                ("et_actual_mm", "evaporation", "actual ET mm/month (ERA5-Land vs old ERA5-Land)")]:
        ok = j[[new_c, old_c]].dropna()
        rows.append({"variable": label, "n_cell_months": len(ok),
                     "r": ok[new_c].corr(ok[old_c]), "mean_new": ok[new_c].mean(), "mean_old": ok[old_c].mean(),
                     "mean_diff_new_minus_old": (ok[new_c] - ok[old_c]).mean(),
                     "mae": (ok[new_c] - ok[old_c]).abs().mean()})
    # month alignment check: area-mean monthly rainfall correlation, old vs new
    a = j.groupby("month")[["rain_mm", "rainfall"]].mean()
    note = f"month alignment: corr of monthly area-mean rainfall new vs old = {a.rain_mm.corr(a.rainfall):.3f}"
    return pd.DataFrame(rows), note


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int, required=True)
    args = ap.parse_args()
    y = args.year
    cfg = load_config()
    src = repo_path(cfg["export"]["out_dir"])
    out = repo_path(cfg["paths"]["outputs_dir"]) / "01c_check_export" / str(y)
    out.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(message)s",
                        handlers=[logging.StreamHandler(), logging.FileHandler(out / "run.log", mode="w", encoding="utf-8")])
    log = logging.getLogger("01c")
    md: list[str] = [f"# Export sanity checks — {y}", ""]

    cells = pd.read_parquet(src / "static" / "cells.parquet")
    dem = pd.read_parquet(src / "static" / "dem.parquet")
    soil = pd.read_parquet(src / "static" / "soil.parquet")
    hls = pd.read_parquet(src / str(y) / "hls_monthly.parquet").merge(cells[["cell_id", "area_inside_m2"]], on="cell_id")
    clim = pd.read_parquet(src / str(y) / "climate_monthly.parquet").merge(cells[["cell_id", "area_inside_m2"]], on="cell_id")
    daily = pd.read_parquet(src / str(y) / "climate_daily.parquet")

    # ---------------------------------------------------------------- 1. NDVI
    h = hls.dropna(subset=["ndvi_mean"])
    md += ["## 1. HLS NDVI", "",
           f"- cell-months with NDVI: {len(h)} / {len(hls)} (cells with no 30 m pixel centre: "
           f"{int((hls.n_px == 0).sum() / 12)})",
           f"- NDVI of cell-months: min {h.ndvi_mean.min():.3f}, 1st pct {h.ndvi_mean.quantile(.01):.3f}, "
           f"median {h.ndvi_mean.median():.3f}, 99th pct {h.ndvi_mean.quantile(.99):.3f}, max {h.ndvi_mean.max():.3f}",
           "", "| Month | NDVI area mean | NDVI min–max (cells) | valid frac: mean / min | cells with valid frac < 0.5 | clear days per pixel (mean) |",
           "|---:|---:|---|---|---:|---:|"]
    seas = []
    for m, gm in hls.groupby("month"):
        g2 = gm.dropna(subset=["ndvi_mean"])
        row = {"month": m, "ndvi": wmean(g2.ndvi_mean, g2.area_inside_m2),
               "vf": wmean(gm.valid_frac, gm.area_inside_m2), "nclear": wmean(gm.n_clear_mean, gm.area_inside_m2)}
        seas.append(row)
        md.append(f"| {m} | {row['ndvi']:.3f} | {g2.ndvi_mean.min():.2f}–{g2.ndvi_mean.max():.2f} | "
                  f"{row['vf']:.3f} / {gm.valid_frac.min():.2f} | {int((gm.valid_frac < 0.5).sum())} | {row['nclear']:.1f} |")
    seas = pd.DataFrame(seas)

    # ---------------------------------------------------------------- 2. climate
    gc = clim.groupby("cell_id")
    ann = pd.DataFrame({"rain": gc.rain_mm.sum(min_count=12), "et0": gc.et0_mm.sum(min_count=12),
                        "eta": gc.et_actual_mm.sum(min_count=12), "area": gc.area_inside_m2.first()})
    n_nodata_cells = int(ann.rain.isna().sum())
    mon = clim.groupby("month").apply(lambda d: pd.Series({
        "rain": wmean(d.rain_mm, d.area_inside_m2), "et0": wmean(d.et0_mm, d.area_inside_m2),
        "eta": wmean(d.et_actual_mm, d.area_inside_m2), "t2m": wmean(d.t2m_c, d.area_inside_m2),
        "swvl1": wmean(d.swvl1, d.area_inside_m2), "u2": wmean(d.u2_ms, d.area_inside_m2),
        "rs": wmean(d.rs_mj, d.area_inside_m2)}), include_groups=False).reset_index()
    md += ["", "## 2. Climate (area means)", "",
           f"- cells without climate values (slivers): {n_nodata_cells}",
           f"- annual rainfall: **{wmean(ann.rain, ann.area):.0f} mm** (cells {ann.rain.min():.0f}–{ann.rain.max():.0f})",
           f"- annual FAO-56 ET0: **{wmean(ann.et0, ann.area):.0f} mm** (cells {ann.et0.min():.0f}–{ann.et0.max():.0f}); "
           f"July **{mon.loc[mon.month == 7, 'et0'].iloc[0]:.0f} mm** — CLAUDE.md expects ≈ 1150 mm/yr and ≈ 165 mm in July",
           f"- annual actual ET (ERA5-Land): **{wmean(ann.eta, ann.area):.0f} mm**; peak month "
           f"{int(mon.loc[mon.eta.idxmax(), 'month'])} ({mon.eta.max():.1f} mm)",
           f"- daily records: {len(daily)}; hourly records behind the wind speed: "
           f"min {daily.nhours.min():.0f}, max {daily.nhours.max():.0f} per day; "
           f"cell-days without ET0: {int(daily.et0_mm.isna().sum())}",
           f"- monthly actual ET < 0 (net condensation): {int((clim.et_actual_mm < 0).sum())} cell-months",
           "", "| Month | rain mm | ET0 mm | actual ET mm | T2m °C | Rs MJ/m²/d | u2 m/s | soil water L1 m³/m³ |",
           "|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for _, r in mon.iterrows():
        md.append(f"| {int(r.month)} | {r.rain:.1f} | {r.et0:.1f} | {r.eta:.1f} | {r.t2m:.1f} | {r.rs:.1f} | {r.u2:.2f} | {r.swvl1:.3f} |")

    # ---------------------------------------------------------------- 3–4. EE consistency checks
    g_init = gcp_project(cfg)
    ee.Initialize(project=g_init)
    c0 = cells.loc[cells.frac_inside.idxmax()]
    pt = ee.Geometry.Point([c0.x_centroid, c0.y_centroid], "EPSG:26191")
    dv = era5_daily_vs_native(pt, [f"{y}-01-15", f"{y}-04-15", f"{y}-07-15", f"{y}-10-15"])
    md += ["", "## 3. ERA5-Land daily sums vs native 24 h accumulation (one pixel; ssrd MJ m-2, te mm)", "",
           f"- max |daily - native|: ssrd {np.abs(dv.ssrd_daily - dv.ssrd_native).max():.4f} MJ, "
           f"te {np.abs(dv.te_daily - dv.te_native).max():.4f} mm (the export uses the daily sums)", "",
           dv.round(3).to_markdown(index=False)]
    region = ee.FeatureCollection(cfg["paths"]["gee_area_asset_v2"]).geometry()
    cp = chirps_daily_vs_pentad(region, y)
    md += ["", "## 4. CHIRPS monthly totals: daily vs pentad (area mean)", "",
           f"- annual: daily {cp.daily_sum_mm.sum():.1f} mm, pentad {cp.pentad_sum_mm.sum():.1f} mm; "
           f"max monthly |difference| {np.abs(cp.daily_sum_mm - cp.pentad_sum_mm).max():.2f} mm"]

    # ---------------------------------------------------------------- 5. static
    tex = soil.clay_0_5cm + soil.silt_0_5cm + soil.sand_0_5cm
    md += ["", "## 5. Static layers", "",
           f"- ALOS elevation (cell means): {dem.dem_mean_m.min():.1f}–{dem.dem_mean_m.max():.1f} m, "
           f"median {dem.dem_mean_m.median():.1f}; cells without value: {int(dem.dem_mean_m.isna().sum())}",
           f"- clay+silt+sand 0–5 cm: {tex.min():.1f}–{tex.max():.1f} % (cells without soil value: {int(tex.isna().sum())})"]
    for c in [c for c in soil.columns if c != "cell_id"]:
        md.append(f"- {c}: {soil[c].min():.1f}–{soil[c].max():.1f}, median {soil[c].median():.1f}")

    # ---------------------------------------------------------------- 6. old data
    if y in OLD_YEARS and OLD_1KM.exists():
        cmp, note = compare_old(y, hls, clim)
        md += ["", "## 6. Comparison with the old 1 km table (same cells and months)", "", f"- {note}", "",
               cmp.round(3).to_markdown(index=False)]

    (out / "checks.md").write_text("\n".join(md), encoding="utf-8")

    fig, ax = plt.subplots(1, 3, figsize=(15, 3.8))
    ax[0].plot(seas.month, seas.ndvi, "o-", label="NDVI (area mean)")
    ax[0].plot(seas.month, seas.vf, "s--", label="valid-pixel fraction")
    ax[0].set_ylim(0, 1); ax[0].legend(); ax[0].set_title(f"HLS {y}")
    ax[1].bar(mon.month - 0.2, mon.rain, 0.4, label="rain (CHIRPS)")
    ax[1].bar(mon.month + 0.2, mon.eta, 0.4, label="actual ET (ERA5-Land)")
    ax[1].legend(); ax[1].set_title("mm / month")
    ax[2].plot(mon.month, mon.et0, "o-", color="tab:red", label="FAO-56 ET0")
    ax[2].legend(); ax[2].set_title("mm / month")
    for a in ax:
        a.set_xticks(range(1, 13))
    fig.tight_layout(); fig.savefig(out / "seasonal.png", dpi=110); plt.close(fig)
    log.info("\n".join(md))


if __name__ == "__main__":
    main()
