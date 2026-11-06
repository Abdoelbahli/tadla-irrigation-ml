"""Phase 0 — read-only inventory of the old project folders.

Reads config.yaml -> inventory, walks every root (metadata only, nothing is read,
moved or deleted) and writes:
  docs/cleanup_report.md                     categories A/B/C, 30 largest, duplicates,
                                             OneDrive heavy files, total GB per category
  outputs/00_inventory/inventory_full.csv    one row per item (git-ignored)
  outputs/00_inventory/run.log

Usage:  python scripts/00_inventory.py [--config config.yaml]
"""
from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tadla.config import load_config, repo_path  # noqa: E402
from tadla.inventory import (  # noqa: E402
    GB, MB, apply_rules, build_report, onedrive_roots, walk_root, write_csv,
)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--config", default=None)
    args = ap.parse_args()

    cfg = load_config(args.config)
    inv = cfg["inventory"]
    out_dir = repo_path(cfg["paths"]["outputs_dir"]) / "00_inventory"
    out_dir.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.StreamHandler(), logging.FileHandler(out_dir / "run.log", mode="w", encoding="utf-8")],
    )
    log = logging.getLogger("00_inventory")

    od = onedrive_roots()
    log.info("OneDrive roots from environment: %s", od or "none")
    items, errors = [], []
    for root in inv["roots"]:
        t0 = time.time()
        found = walk_root(root, od, errors)
        log.info("%-45s %6d items %9.2f GB  (%.1fs)", root, len(found),
                 sum(i.size for i in found) / GB, time.time() - t0)
        items.extend(found)

    apply_rules(items, small_derived_bytes=float(inv.get("small_derived_mb", 10)) * MB)
    for c in "ABC":
        log.info("category %s: %d items, %.2f GB", c,
                 sum(1 for i in items if i.category == c), sum(i.size for i in items if i.category == c) / GB)
    for e in errors:
        log.warning(e)

    csv_path = repo_path(inv["full_listing_csv"])
    write_csv(sorted(items, key=lambda i: -i.size), csv_path)
    log.info("full listing -> %s", csv_path)

    report_path = repo_path(inv["report"])
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(build_report(items, inv["roots"], inv, errors), encoding="utf-8")
    log.info("report -> %s", report_path)


if __name__ == "__main__":
    main()
