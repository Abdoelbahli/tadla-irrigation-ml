"""Phase 1, step 4 — sanity checks of exported years.

Reads outputs/01_export/{static,<year>} and writes to outputs/01c_check_export/:
  <year>/checks.md      all checks below for one year
  <year>/seasonal.png   area-mean monthly NDVI, clear days, rainfall, actual ET, ET0 (+ independent products)
  summary.md / summary.csv   one row per checked year
  run.log

Checks per year
 1. NDVI range and seasonal cycle; valid-pixel fraction, clear days per pixel, share of high-aerosol
    observations, per month.
 2. Area-mean rainfall, FAO-56 ET0 (annual, July), actual ET (annual, peak month); data completeness.
 3. ET0 vs independent reference-ET products in Earth Engine (area means):
    TerraClimate `pet` (monthly, ×0.1 mm), FAO WaPOR v2 and v3 L1 RET (daily, ×0.1 mm/day, summed).
 4. ERA5-Land DAILY_AGGR daily sums vs ERA5's native 24 h accumulation (one pixel, four days).
 5. CHIRPS monthly totals: daily vs pentad product.
 6. Static layers: elevation, soil ranges, clay+silt+sand ≈ 100 %.
 7. Cell-by-cell comparison with the old 1 km table (Desktop/train/aggregated_1km_data.parquet) for the
    old training years (2017, 2019–2023).
Area means are weighted by the area of each cell inside the study area.

Usage:  python scripts/01c_check_export.py --years 2022 2023      or      --all
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

log = logging.getLogger("01c")
OLD_1KM = Path(r"C:\Users\abdel\OneDrive\Desktop\train\aggregated_1km_data.parquet")
OLD_YEARS = [2017, 2019, 2020, 2021, 2022, 2023]   # order of the 72 months in the old table (2018 excluded)

# Independent reference-ET products: (collection, band, scale factor, temporal step, last complete year)
ET0_PRODUCTS = {
    "TerraClimate": ("IDAHO_EPSCOR/TERRACLIMATE", "pet", 0.1, "monthly", (1958, 2024)),
    "WaPOR v2": ("FAO/WAPOR/2/L1_RET_E", "L1_RET_E", 0.1, "daily", (2009, 2022)),
    "WaPOR v3": ("FAO/WAPOR/3/L1_RET_E", "L1-RET-E", 0.1, "daily", (2018, 2025)),
}


def wmean(x: pd.Series, w: pd.Series) -> float:
    ok = x.notna() & w.notna()
    return float(np.average(x[ok], weights=w[ok])) if ok.any() else float("nan")


# ----------------------------------------------------------------------------- EE checks
def et0_products(region: ee.Geometry, year: int) -> pd.DataFrame:
    """Monthly area-mean reference ET (mm) of the independent products available for `year`."""
    out = {}
    for name, (cid, band, scale, step, (y0, y1)) in ET0_PRODUCTS.items():
        if not (y0 <= year <= y1):
            continue
        vals = []
        for m in range(1, 13):
            s = ee.Date.fromYMD(year, m, 1)
            col = ee.ImageCollection(cid).filterDate(s, s.advance(1, "month")).select(band)
            vals.append(col.sum().reduceRegion(ee.Reducer.mean(), region, 1000).get(band))
        out[name] = np.array(ee.List(vals).getInfo(), dtype=float) * scale
    return pd.DataFrame(out, index=pd.Index(range(1, 13), name="month"))


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
    vals = []
    for m in range(1, 13):
        s = ee.Date.fromYMD(year, m, 1)
        e = s.advance(1, "month")
        dly = ee.ImageCollection("UCSB-CHG/CHIRPS/DAILY").filterDate(s, e).sum()
        pen = ee.ImageCollection("UCSB-CHG/CHIRPS/PENTAD").filterDate(s, e).sum()
        vals.append(ee.List([dly.reduceRegion(ee.Reducer.mean(), region, 5566).get("precipitation"),
                             pen.reduceRegion(ee.Reducer.mean(), region, 5566).get("precipitation")]))
    v = np.array(ee.List(vals).getInfo(), dtype=float)
    return pd.DataFrame({"month": range(1, 13), "daily_sum_mm": v[:, 0], "pentad_sum_mm": v[:, 1]})


# ----------------------------------------------------------------------------- old table
def compare_old(year: int, hls: pd.DataFrame, clim: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    """New vs old 1 km cell-month values for one of the old training years."""
    old = pd.read_parquet(OLD_1KM)
    k = OLD_YEARS.index(year)
    old = old[(old._month_idx >= 12 * k) & (old._month_idx < 12 * (k + 1))].copy()
    old["month"] = old._month_idx - 12 * k + 1
    old["cell_id"] = [f"X{x / 1000:g}_Y{y / 1000:g}" for x, y in zip(old._cell_x, old._cell_y)]
    new = hls[["cell_id", "month", "ndvi_mean"]].merge(clim[["cell_id", "month", "rain_mm", "et_actual_mm"]],
                                                       on=["cell_id", "month"])
    j = new.merge(old[["cell_id", "month", "NDVI", "rainfall", "evaporation"]], on=["cell_id", "month"], how="inner")
    rows = []
    for new_c, old_c, label in [("ndvi_mean", "NDVI", "NDVI (HLS vs old Sentinel-2)"),
                                ("rain_mm", "rainfall", "rainfall mm/month (CHIRPS vs old CHIRPS)"),
                                ("et_actual_mm", "evaporation", "actual ET mm/month (ERA5-Land vs old ERA5-Land)")]:
        ok = j[[new_c, old_c]].dropna()
        rows.append({"variable": label, "n_cell_months": len(ok),
                     "r": ok[new_c].corr(ok[old_c]), "mean_new": ok[new_c].mean(), "mean_old": ok[old_c].mean(),
                     "mean_diff_new_minus_old": (ok[new_c] - ok[old_c]).mean(),
                     "mae": (ok[new_c] - ok[old_c]).abs().mean()})
    a = j.groupby("month")[["rain_mm", "rainfall"]].mean()
    note = f"month alignment: corr of monthly area-mean rainfall new vs old = {a.rain_mm.corr(a.rainfall):.3f}"
    return pd.DataFrame(rows), note


# ----------------------------------------------------------------------------- one year
def check_year(cfg: dict, y: int, src: Path, out: Path, region: ee.Geometry, static: dict) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    cells, dem, soil = static["cells"], static["dem"], static["soil"]
    hls = pd.read_parquet(src / str(y) / "hls_monthly.parquet").merge(cells[["cell_id", "area_inside_m2"]], on="cell_id")
    clim = pd.read_parquet(src / str(y) / "climate_monthly.parquet").merge(cells[["cell_id", "area_inside_m2"]], on="cell_id")
    daily = pd.read_parquet(src / str(y) / "climate_daily.parquet")
    md: list[str] = [f"# Export sanity checks — {y}", ""]
    S: dict = {"year": y}

    # 1. NDVI ------------------------------------------------------------------
    h = hls.dropna(subset=["ndvi_mean"])
    has_aero = "aero_hi_frac" in hls
    md += ["## 1. HLS NDVI", "",
           f"- cell-months with NDVI: {len(h)} / {len(hls)} (cells with no 30 m pixel centre: "
           f"{int((hls.n_px == 0).sum() / 12)})",
           f"- NDVI of cell-months: min {h.ndvi_mean.min():.3f}, 1st pct {h.ndvi_mean.quantile(.01):.3f}, "
           f"median {h.ndvi_mean.median():.3f}, 99th pct {h.ndvi_mean.quantile(.99):.3f}, max {h.ndvi_mean.max():.3f}",
           f"- cell-months with < 1 / < 2 clear days per pixel (cell mean): "
           f"{int((hls.n_clear_mean < 1).sum())} / {int((hls.n_clear_mean < 2).sum())}",
           "", "| Month | NDVI area mean | NDVI min–max (cells) | valid frac mean / min | clear days/pixel: mean / min cell"
           + (" | high-aerosol share |" if has_aero else " |"),
           "|---:|---:|---|---|---|" + ("---:|" if has_aero else "")]
    seas = []
    for m, gm in hls.groupby("month"):
        g2 = gm.dropna(subset=["ndvi_mean"])
        row = {"month": m, "ndvi": wmean(g2.ndvi_mean, g2.area_inside_m2),
               "vf": wmean(gm.valid_frac, gm.area_inside_m2), "nclear": wmean(gm.n_clear_mean, gm.area_inside_m2),
               "nclear_min": g2.n_clear_mean.min(),
               "aero": wmean(gm.aero_hi_frac, gm.area_inside_m2) if has_aero else np.nan}
        seas.append(row)
        md.append(f"| {m} | {row['ndvi']:.3f} | {g2.ndvi_mean.min():.2f}–{g2.ndvi_mean.max():.2f} | "
                  f"{row['vf']:.3f} / {gm.valid_frac.min():.2f} | {row['nclear']:.1f} / {row['nclear_min']:.1f}"
                  + (f" | {row['aero']:.2f} |" if has_aero else " |"))
    seas = pd.DataFrame(seas)
    S.update({"ndvi_mean": wmean(h.ndvi_mean, h.area_inside_m2), "ndvi_peak_month": int(seas.loc[seas.ndvi.idxmax(), "month"]),
              "ndvi_peak": seas.ndvi.max(), "ndvi_min_month_value": seas.ndvi.min(),
              "clear_days_min_month": seas.nclear.min(), "clear_days_min_cell": seas.nclear_min.min(),
              "cellmonths_lt1_clear": int((hls.n_clear_mean < 1).sum()), "valid_frac_min": hls.valid_frac.min(),
              "aero_hi_share": wmean(hls.aero_hi_frac, hls.area_inside_m2) if has_aero else np.nan})

    # 2. climate ---------------------------------------------------------------
    gc = clim.groupby("cell_id")
    ann = pd.DataFrame({"rain": gc.rain_mm.sum(min_count=12), "et0": gc.et0_mm.sum(min_count=12),
                        "eta": gc.et_actual_mm.sum(min_count=12), "area": gc.area_inside_m2.first()})
    mon = clim.groupby("month").apply(lambda d: pd.Series({
        "rain": wmean(d.rain_mm, d.area_inside_m2), "et0": wmean(d.et0_mm, d.area_inside_m2),
        "eta": wmean(d.et_actual_mm, d.area_inside_m2), "t2m": wmean(d.t2m_c, d.area_inside_m2),
        "swvl1": wmean(d.swvl1, d.area_inside_m2), "u2": wmean(d.u2_ms, d.area_inside_m2),
        "rs": wmean(d.rs_mj, d.area_inside_m2)}), include_groups=False).reset_index()
    S.update({"rain_mm": wmean(ann.rain, ann.area), "et0_mm": wmean(ann.et0, ann.area),
              "et0_july_mm": float(mon.loc[mon.month == 7, "et0"].iloc[0]), "eta_mm": wmean(ann.eta, ann.area),
              "eta_peak_month": int(mon.loc[mon.eta.idxmax(), "month"]),
              "hours_per_day_min": daily.nhours.min(), "cells_no_climate": int(ann.rain.isna().sum())})
    md += ["", "## 2. Climate (area means)", "",
           f"- cells without climate values (slivers): {S['cells_no_climate']}",
           f"- annual rainfall: **{S['rain_mm']:.0f} mm** (cells {ann.rain.min():.0f}–{ann.rain.max():.0f})",
           f"- annual FAO-56 ET0: **{S['et0_mm']:.0f} mm** (cells {ann.et0.min():.0f}–{ann.et0.max():.0f}); "
           f"July **{S['et0_july_mm']:.0f} mm** (the old work's ≈ 1150 mm/yr was not a reference ET0, decisions.md D7)",
           f"- annual actual ET (ERA5-Land): **{S['eta_mm']:.0f} mm**; peak month {S['eta_peak_month']} ({mon.eta.max():.1f} mm)",
           f"- daily records: {len(daily)}; hourly records behind the wind speed: min {daily.nhours.min():.0f}, "
           f"max {daily.nhours.max():.0f} per day; cell-days without ET0: {int(daily.et0_mm.isna().sum())}",
           f"- monthly actual ET < 0 (net condensation): {int((clim.et_actual_mm < 0).sum())} cell-months",
           "", "| Month | rain mm | ET0 mm | actual ET mm | T2m °C | Rs MJ/m²/d | u2 m/s | soil water L1 m³/m³ |",
           "|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for _, r in mon.iterrows():
        md.append(f"| {int(r.month)} | {r.rain:.1f} | {r.et0:.1f} | {r.eta:.1f} | {r.t2m:.1f} | {r.rs:.1f} | {r.u2:.2f} | {r.swvl1:.3f} |")

    # 3. independent ET0 products ------------------------------------------------
    prod = et0_products(region, y)
    if not prod.empty:
        prod.insert(0, "this export (FAO-56, ERA5-Land)", mon.set_index("month").et0)
        md += ["", "## 3. ET0 vs independent reference-ET products (area mean, mm)", "",
               "| | " + " | ".join(prod.columns) + " |", "|---|" + "---:|" * len(prod.columns),
               "| **annual** | " + " | ".join(f"**{v:.0f}**" for v in prod.sum()) + " |",
               "| July | " + " | ".join(f"{v:.0f}" for v in prod.loc[7]) + " |",
               "| monthly corr. with this export | " + " | ".join(f"{prod.iloc[:, 0].corr(prod[c]):.3f}" for c in prod.columns) + " |"]
        for c in prod.columns[1:]:
            S[f"et0_{c.replace(' ', '_')}_mm"] = prod[c].sum()

    # 4–5. ERA5 and CHIRPS consistency ----------------------------------------------
    c0 = cells.loc[cells.frac_inside.idxmax()]
    pt = ee.Geometry.Point([c0.x_centroid, c0.y_centroid], "EPSG:26191")
    dv = era5_daily_vs_native(pt, [f"{y}-01-15", f"{y}-04-15", f"{y}-07-15", f"{y}-10-15"])
    S["era5_daily_vs_native_maxdiff"] = max(np.abs(dv.ssrd_daily - dv.ssrd_native).max(), np.abs(dv.te_daily - dv.te_native).max())
    md += ["", "## 4. ERA5-Land daily sums vs native 24 h accumulation (one pixel; ssrd MJ m-2, te mm)", "",
           f"- max |daily − native|: ssrd {np.abs(dv.ssrd_daily - dv.ssrd_native).max():.4f} MJ, "
           f"te {np.abs(dv.te_daily - dv.te_native).max():.4f} mm (the export uses the daily sums)", "",
           dv.round(3).to_markdown(index=False)]
    cp = chirps_daily_vs_pentad(region, y)
    S["chirps_daily_minus_pentad_mm"] = cp.daily_sum_mm.sum() - cp.pentad_sum_mm.sum()
    md += ["", "## 5. CHIRPS monthly totals: daily vs pentad (area mean)", "",
           f"- annual: daily {cp.daily_sum_mm.sum():.1f} mm, pentad {cp.pentad_sum_mm.sum():.1f} mm; "
           f"max monthly |difference| {np.abs(cp.daily_sum_mm - cp.pentad_sum_mm).max():.2f} mm"]

    # 6. static ------------------------------------------------------------------
    tex = soil.clay_0_15cm + soil.silt_0_15cm + soil.sand_0_15cm
    md += ["", "## 6. Static layers", "",
           f"- ALOS elevation (cell means): {dem.dem_mean_m.min():.1f}–{dem.dem_mean_m.max():.1f} m, "
           f"median {dem.dem_mean_m.median():.1f}; cells without value: {int(dem.dem_mean_m.isna().sum())}",
           f"- clay+silt+sand 0–15 cm: {tex.min():.1f}–{tex.max():.1f} % (cells without soil value: {int(tex.isna().sum())})"]
    for c in [c for c in soil.columns if c != "cell_id"]:
        md.append(f"- {c}: {soil[c].min():.1f}–{soil[c].max():.1f}, median {soil[c].median():.1f}")

    # 7. old data ----------------------------------------------------------------
    if y in OLD_YEARS and OLD_1KM.exists():
        cmp, note = compare_old(y, hls, clim)
        md += ["", "## 7. Comparison with the old 1 km table (same cells and months)", "", f"- {note}", "",
               cmp.round(3).to_markdown(index=False)]
        S.update({"old_r_ndvi": cmp.r[0], "old_dmean_ndvi": cmp.mean_diff_new_minus_old[0],
                  "old_r_rain": cmp.r[1], "old_r_eta": cmp.r[2]})

    (out / "checks.md").write_text("\n".join(md), encoding="utf-8")

    fig, ax = plt.subplots(1, 3, figsize=(15, 3.8))
    ax[0].plot(seas.month, seas.ndvi, "o-", label="NDVI (area mean)")
    ax0b = ax[0].twinx()
    ax0b.bar(seas.month, seas.nclear, 0.5, alpha=0.25, color="grey", label="clear days / pixel")
    ax[0].set_ylim(0, 1); ax[0].legend(loc="upper right"); ax0b.legend(loc="lower left"); ax[0].set_title(f"HLS {y}")
    ax[1].bar(mon.month - 0.2, mon.rain, 0.4, label="rain (CHIRPS)")
    ax[1].bar(mon.month + 0.2, mon.eta, 0.4, label="actual ET (ERA5-Land)")
    ax[1].legend(); ax[1].set_title("mm / month")
    ax[2].plot(mon.month, mon.et0, "o-", color="tab:red", label="FAO-56 ET0 (this export)")
    for c in prod.columns[1:] if not prod.empty else []:
        ax[2].plot(prod.index, prod[c], "--", lw=1, label=c)
    ax[2].legend(fontsize=8); ax[2].set_title("reference ET, mm / month")
    for a in ax:
        a.set_xticks(range(1, 13))
    fig.tight_layout(); fig.savefig(out / "seasonal.png", dpi=110); plt.close(fig)
    log.info("%d checked: NDVI %.3f, rain %.0f, ET0 %.0f (July %.0f), ETa %.0f mm", y, S["ndvi_mean"],
             S["rain_mm"], S["et0_mm"], S["et0_july_mm"], S["eta_mm"])
    return S


# ----------------------------------------------------------------------------- main
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", type=int, nargs="*", default=[])
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()
    cfg = load_config()
    src = repo_path(cfg["export"]["out_dir"])
    out_root = repo_path(cfg["paths"]["outputs_dir"]) / "01c_check_export"
    out_root.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s",
                        handlers=[logging.StreamHandler(), logging.FileHandler(out_root / "run.log", mode="a", encoding="utf-8")])
    years = list(range(cfg["period"]["start_year"], cfg["period"]["end_year"] + 1)) if args.all else args.years

    ee.Initialize(project=gcp_project(cfg))
    region = ee.FeatureCollection(cfg["paths"]["gee_area_asset_v2"]).geometry()
    static = {"cells": pd.read_parquet(src / "static" / "cells.parquet"),
              "dem": pd.read_parquet(src / "static" / "dem.parquet"),
              "soil": pd.read_parquet(src / "static" / "soil.parquet")}
    rows = [check_year(cfg, y, src, out_root / str(y), region, static) for y in years]

    # merge with previously checked years so summary.csv accumulates
    summ = pd.DataFrame(rows)
    p = out_root / "summary.csv"
    if p.exists():
        prev = pd.read_csv(p)
        summ = pd.concat([prev[~prev.year.isin(summ.year)], summ]).sort_values("year")
    summ.to_csv(p, index=False)
    cols = {"year": "Year", "ndvi_mean": "NDVI mean", "ndvi_peak": "NDVI peak", "ndvi_peak_month": "peak month",
            "clear_days_min_month": "clear days, worst month", "clear_days_min_cell": "clear days, worst cell-month",
            "cellmonths_lt1_clear": "cell-months < 1 clear day", "aero_hi_share": "high-aerosol share",
            "rain_mm": "rain mm", "et0_mm": "ET0 mm", "et0_july_mm": "ET0 July", "eta_mm": "actual ET mm",
            "eta_peak_month": "ETa peak month", "et0_TerraClimate_mm": "TerraClimate", "et0_WaPOR_v2_mm": "WaPOR v2",
            "et0_WaPOR_v3_mm": "WaPOR v3", "old_r_ndvi": "r NDVI vs old", "old_dmean_ndvi": "ΔNDVI vs old",
            "old_r_rain": "r rain vs old", "old_r_eta": "r ETa vs old"}
    t = summ[[c for c in cols if c in summ]].rename(columns=cols)
    (out_root / "summary.md").write_text("# Export checks — summary per year\n\n" + t.round(3).to_markdown(index=False),
                                         encoding="utf-8")
    log.info("summary -> %s", out_root / "summary.md")


if __name__ == "__main__":
    main()
