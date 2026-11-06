"""Phase 1, step 1 — check the real temporal coverage of every Earth Engine collection
over the study area, to fix the study period (complete calendar years only).

Reads config.yaml (gee.collections, gee.check_years, paths.gee_area_asset) and writes
  outputs/01a_check_collections/collections.json   first/last image, counts per year and month
  outputs/01a_check_collections/per_year.csv
  outputs/01a_check_collections/run.log
Read-only: nothing is exported.

Usage:  python scripts/01a_check_collections.py
"""
from __future__ import annotations

import json
import logging
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd  # noqa: E402

from tadla.config import gcp_project, load_config, repo_path  # noqa: E402
from tadla.data.gee_export import (  # noqa: E402
    collection_summary, heavy_collection_summary, hls_acquisitions, init_ee, study_area,
)


def main() -> None:
    cfg = load_config()
    out = repo_path(cfg["paths"]["outputs_dir"]) / "01a_check_collections"
    out.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s",
                        handlers=[logging.StreamHandler(),
                                  logging.FileHandler(out / "run.log", mode="w", encoding="utf-8")])
    log = logging.getLogger("01a")

    init_ee(gcp_project(cfg))
    region = study_area(cfg["paths"]["gee_area_asset"])
    y0, y1 = cfg["gee"]["check_years"]
    today = date.today()
    months_to = f"{today.year}-{today.month:02d}-01"          # current month excluded
    months_from = f"{today.year - 1}-01-01"

    results = {}
    for key, cid in cfg["gee"]["collections"].items():
        log.info("querying %s (%s)", key, cid)
        try:
            if key in cfg["gee"].get("heavy_collections", []):
                last_window = (f"{today.year - 1}-{today.month:02d}-01", months_to)
                results[key] = heavy_collection_summary(cid, region, (cfg["gee"]["heavy_check_from"], y1),
                                                        last_window)
                results[key]["note"] = "heavy collection: counted from heavy_check_from only; first image not searched"
            else:
                results[key] = collection_summary(cid, region, (y0, y1), months_from, months_to)
        except Exception as exc:  # report and continue with the other collections
            log.error("  %s failed: %s", cid, exc)
            results[key] = {"id": cid, "error": str(exc)}
            continue
        r = results[key]
        log.info("  first %s | last start %s | last end %s", r["first_start"], r["last_start"], r["last_end"])

    # HLS: counts restricted to the real MGRS tiles, and distinct acquisition dates
    tiles = cfg["gee"]["hls_tiles"]
    hls_rows = []
    for key in ("hls_s30", "hls_l30"):
        acq = hls_acquisitions(cfg["gee"]["collections"][key], region, tiles, "2013-01-01", months_to)
        log.info("%s: %d granules on tiles %s", key, len(acq), tiles)
        for tile, d in acq:
            hls_rows.append({"product": key, "tile": tile, "date": d})
    hls = pd.DataFrame(hls_rows)
    hls["year"] = hls.date.str[:4].astype(int)
    hls["month"] = hls.date.str[:6]
    hls.to_csv(out / "hls_granules.csv", index=False)
    g = hls.groupby(["product", "year"])
    yearly = pd.DataFrame({
        "granules": g.size(),
        "distinct_dates": g.date.nunique(),
        # same tile, same date, more than one granule (must be mosaicked per date before counting)
        "duplicate_tile_dates": g.size() - hls.drop_duplicates(["product", "tile", "date"]).groupby(["product", "year"]).size(),
    })
    yearly.to_csv(out / "hls_per_year.csv")
    both = hls.groupby("month").date.nunique().rename("distinct_dates_s30_or_l30")
    both.to_csv(out / "hls_dates_per_month.csv")
    log.info("HLS per year (real tiles only):\n%s", yearly.unstack(0).to_string())

    results["_meta"] = {"queried_on": today.isoformat(), "region": cfg["paths"]["gee_area_asset"],
                        "note": "counts = images whose footprint intersects the study area"}
    (out / "collections.json").write_text(json.dumps(results, indent=2), encoding="utf-8")

    # raw HLS counts include spurious antimeridian tiles: see hls_per_year.csv for real counts
    rows = {(f"{k}_raw_incl_spurious_tiles" if k.startswith("hls") else k): v["per_year"]
            for k, v in results.items() if not k.startswith("_") and "per_year" in v}
    pd.DataFrame(rows).rename_axis("year").to_csv(out / "per_year.csv")
    log.info("written %s", out)


if __name__ == "__main__":
    main()
