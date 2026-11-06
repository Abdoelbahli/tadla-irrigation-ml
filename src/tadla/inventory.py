"""Read-only inventory of the old project material (Phase 0).

Walks the folders listed in ``config.yaml -> inventory.roots`` with ``os.scandir`` and
``stat`` ONLY. File contents are never read, so OneDrive "online-only" files are never
downloaded, and nothing is moved, renamed or deleted.

Some directories are reported as ONE item because their content is a single logical
object: Zarr stores (detected by their metadata file, with or without a ``.zarr``
suffix), ``.git`` repositories and caches.

Categories (CLAUDE.md, Phase 0):
  A  re-downloadable raw data (or junk) — deletable once the new pipeline's data are
     exported and checked;
  B  derived intermediates backing the current report — keep until the new results
     are validated, then delete;
  C  keep (small, irreplaceable: shapefiles, code, figures, metrics, model files...).
"""
from __future__ import annotations

import csv
import os
import re
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

GB = 1e9  # decimal gigabyte (10^9 bytes)
MB = 1e6

# Windows file attributes that mean "content lives in the cloud, not on disk".
_CLOUD_ONLY_FLAGS = 0x1000 | 0x40000 | 0x400000  # OFFLINE | RECALL_ON_OPEN | RECALL_ON_DATA_ACCESS

ZARR_MARKERS = ("zarr.json", ".zgroup", ".zarray", ".zmetadata")
CACHE_DIR_NAMES = {"__pycache__", ".ne_cache", ".ipynb_checkpoints", ".pytest_cache"}

SHAPEFILE_EXT = {".shp", ".shx", ".dbf", ".prj", ".cpg", ".sbn", ".sbx", ".qmd", ".qpj"}
VECTOR_EXT = {".gpkg", ".geojson", ".kml", ".kmz"}
CODE_EXT = {".py", ".ipynb", ".js", ".r", ".sh", ".bat", ".ps1"}
DOC_EXT = {".docx", ".doc", ".md", ".pdf", ".pptx", ".xlsx", ".odt", ".tex", ".bib", ".rst"}
FIGURE_EXT = {".png", ".jpg", ".jpeg", ".svg", ".eps", ".gif"}
SMALL_TABLE_EXT = {".json", ".csv", ".txt", ".yml", ".yaml", ".log", ".cfg", ".ini", ".toml"}
ARRAY_EXT = {".nc", ".tif", ".tiff", ".npy", ".npz", ".parquet", ".h5", ".hdf", ".grib", ".grb", ".zip"}
JUNK_EXT = {".crdownload", ".part", ".tmp", ".partial"}

# Raw data folders on D: (CLAUDE.md: "CHIRPS, ERA5, NDVI NetCDF exports" -> category A)
RAW_DATA_ROOT_NAMES = {"chirps", "era5", "era5-11", "ndvi_netcdf"}
# Folder holding the merged cubes built from those NetCDFs -> category B
DERIVED_DATA_ROOT_NAMES = {"combined_data"}


@dataclass
class Item:
    root: str
    rel: str            # path relative to root, forward slashes
    kind: str           # file | zarr store | git repository | cache
    ext: str
    size: int           # logical bytes (sum over files for bundles)
    n_files: int
    mtime: float        # latest modification time (max over files for bundles)
    onedrive: bool
    cloud_only: bool
    category: str = ""
    reason: str = ""
    flag: str = ""      # extra warning, e.g. secrets

    @property
    def name(self) -> str:
        return self.rel.rsplit("/", 1)[-1]

    @property
    def parent(self) -> str:
        return self.rel.rsplit("/", 1)[0] if "/" in self.rel else "."


# ----------------------------------------------------------------------------- walking
def onedrive_roots() -> list[str]:
    """OneDrive folders declared by the OneDrive client in the environment."""
    roots = []
    for var in ("OneDrive", "OneDriveConsumer", "OneDriveCommercial"):
        val = os.environ.get(var)
        if val:
            roots.append(os.path.normcase(os.path.abspath(val)))
    return sorted(set(roots))


def _in_onedrive(path: str, od_roots: list[str]) -> bool:
    p = os.path.normcase(os.path.abspath(path))
    if any(p == r or p.startswith(r + os.sep) for r in od_roots):
        return True
    # fallback when the environment variables are missing
    return any(part.lower().startswith("onedrive") for part in Path(p).parts)


def _bundle_kind(entry: os.DirEntry) -> str | None:
    name = entry.name
    if name == ".git":
        return "git repository"
    if name in CACHE_DIR_NAMES:
        return "cache"
    if name.lower().endswith(".zarr"):
        return "zarr store"
    try:
        if any(os.path.exists(os.path.join(entry.path, m)) for m in ZARR_MARKERS):
            return "zarr store"
    except OSError:
        pass
    return None


def file_ext(name: str) -> str:
    """Lower-case extension, or "" when the suffix is not a real extension
    (e.g. "1.21.0" -> "", ".env" -> "")."""
    ext = Path(name).suffix.lower()
    return ext if re.fullmatch(r"\.[a-z][a-z0-9_-]{0,11}", ext) else ""


def _cloud_only(st: os.stat_result) -> bool:
    return bool(getattr(st, "st_file_attributes", 0) & _CLOUD_ONLY_FLAGS)


def _summarise_dir(path: str) -> tuple[int, int, float, bool]:
    size = n = 0
    mtime = 0.0
    cloud = False
    for dirpath, _dirs, files in os.walk(path):
        for f in files:
            try:
                st = os.stat(os.path.join(dirpath, f), follow_symlinks=False)
            except OSError:
                continue
            size += st.st_size
            n += 1
            mtime = max(mtime, st.st_mtime)
            cloud = cloud or _cloud_only(st)
    return size, n, mtime, cloud


def walk_root(root: str, od_roots: list[str], errors: list[str]) -> list[Item]:
    """Collect files (and bundles) under ``root``. Only metadata is touched."""
    items: list[Item] = []
    root_path = Path(root)
    if not root_path.is_dir():
        errors.append(f"root not found: {root}")
        return items
    stack = [root_path]
    while stack:
        d = stack.pop()
        try:
            entries = list(os.scandir(d))
        except OSError as exc:
            errors.append(f"cannot list {d}: {exc}")
            continue
        for e in entries:
            rel = Path(e.path).relative_to(root_path).as_posix()
            od = _in_onedrive(e.path, od_roots)
            if e.is_dir(follow_symlinks=False):
                kind = _bundle_kind(e)
                if kind is None:
                    stack.append(Path(e.path))
                    continue
                size, n, mtime, cloud = _summarise_dir(e.path)
                ext = ".zarr" if kind == "zarr store" else ""
                items.append(Item(str(root_path), rel, kind, ext, size, n, mtime, od, cloud))
            elif e.is_file(follow_symlinks=False):
                try:
                    st = e.stat(follow_symlinks=False)
                except OSError as exc:
                    errors.append(f"cannot stat {e.path}: {exc}")
                    continue
                ext = file_ext(e.name)
                items.append(Item(str(root_path), rel, "file", ext, st.st_size, 1,
                                  st.st_mtime, od, _cloud_only(st)))
    return items


# ----------------------------------------------------------------------------- rules
def classify(item: Item, small_derived_bytes: float = 10 * MB) -> tuple[str, str]:
    """Return (category, reason). Rules are applied in order; first match wins."""
    rel_l = item.rel.lower()
    name_l = item.name.lower()
    root_name = Path(item.root).name.lower()
    parts = rel_l.split("/")

    # 1. bundles
    if item.kind == "git repository":
        return "C", "version history of the old code"
    if item.kind == "cache":
        return "A", "cache, regenerated or re-downloaded automatically"
    if item.kind == "zarr store":
        if "backup" in name_l:
            return "B", "backup copy of a Zarr cube"
        return "B", "Zarr cube (derived intermediate)"

    # 2. junk
    if item.ext in JUNK_EXT:
        return "A", "incomplete browser download / temporary file"
    if item.ext == "" and item.size < 100_000 and re.fullmatch(r"=?[0-9][0-9.]*", name_l):
        return "A", "stray pip output (unquoted `pip install pkg>=x.y` redirected to a file)"
    if item.ext == ".whl":
        return "A", "Python wheel, re-downloadable"

    # 3. always-keep types
    if item.ext == ".env" or name_l == ".env":
        return "C", "environment file (may hold credentials)"
    if item.ext in SHAPEFILE_EXT or item.ext in VECTOR_EXT:
        return "C", "vector / shapefile component"
    if item.ext in CODE_EXT:
        return "C", "code or notebook (archive into one zip)"
    if item.ext in DOC_EXT:
        return "C", "document"
    if item.ext in FIGURE_EXT:
        return "C", "figure / image"
    if name_l.startswith("ndvi_model") and item.ext == ".txt":
        return "C", "trained LightGBM model file"
    if item.ext in SMALL_TABLE_EXT:
        if item.size <= small_derived_bytes:
            return "C", "small metrics / table / text file"
        return "B", "large derived table"
    if name_l.startswith(".git"):
        return "C", "git configuration file"

    # 4. data / arrays, by location
    if item.ext in ARRAY_EXT or item.ext == "":
        if "backup" in rel_l:
            return "B", "backup copy"
        if name_l.endswith(".zarr.zip"):
            return "B", "zipped copy of a Zarr cube"
        if root_name in RAW_DATA_ROOT_NAMES:
            return "A", "raw data exported from GEE and resampled; reproducible by the new pipeline"
        if root_name in DERIVED_DATA_ROOT_NAMES:
            return "B", "merged cube built from the D:\\ NetCDFs (derived intermediate)"
        if "raw" in parts and item.ext in {".tif", ".tiff", ".nc", ".zip"}:
            if item.ext == ".zip" and item.size <= small_derived_bytes:
                return "C", "small archive in Data/Raw (content not inspected; likely boundary data)"
            return "A", "raw GEE export"
        if "processed" in parts or "harmonized" in parts:
            return "B", "processed (reprojected / resampled) intermediate of the old pipeline"
        if "outputs_chapter4" in parts and item.ext in {".tif", ".tiff"}:
            return "B", "derived output raster (regenerated by the new pipeline)"
        if item.ext in {".npy", ".npz", ".parquet", ".nc"}:
            if item.size <= small_derived_bytes:
                return "C", "small derived array / table backing reported results (negligible size)"
            return "B", "derived intermediate (prediction array / training table / cube)"
        if item.ext in {".tif", ".tiff"}:
            if item.size <= small_derived_bytes:
                return "C", "small raster outside the data folders (negligible size; may be the only record)"
            return "A", "GEE GeoTIFF export"
        if item.ext == ".zip":
            if item.size <= small_derived_bytes:
                return "C", "small archive (content not inspected)"
            return "B", "large archive (content not inspected)"

    # 5. fallback: keep by default, ask for a manual review
    return "C", "unclassified type, kept by default (review manually)"


def apply_rules(items: list[Item], small_derived_bytes: float) -> None:
    for it in items:
        it.category, it.reason = classify(it, small_derived_bytes)
        if it.name.lower() == ".env" or it.ext == ".env":
            it.flag = "may contain credentials: never copy into a public repo or archive"


# ----------------------------------------------------------------------------- analysis
def find_duplicates(items: list[Item]) -> list[list[Item]]:
    """Groups of >= 2 items sharing the same name (case-insensitive) AND size."""
    groups: dict[tuple[str, int], list[Item]] = defaultdict(list)
    for it in items:
        if it.size == 0:
            continue
        groups[(it.name.lower(), it.size)].append(it)
    dups = [g for g in groups.values() if len(g) > 1]
    dups.sort(key=lambda g: g[0].size * (len(g) - 1), reverse=True)
    return dups


def find_same_name_diff_size(items: list[Item], min_bytes: float) -> list[list[Item]]:
    """Large items with the same name but different sizes (possible duplicates)."""
    groups: dict[str, list[Item]] = defaultdict(list)
    for it in items:
        if it.size >= min_bytes:
            groups[it.name.lower()].append(it)
    out = [g for g in groups.values()
           if len(g) > 1 and len({i.size for i in g}) > 1 and len({i.root for i in g}) > 1]
    out.sort(key=lambda g: max(i.size for i in g), reverse=True)
    return out


def write_csv(items: list[Item], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(asdict(items[0]).keys()) if items else []
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields + ["size_gb", "modified"])
        w.writeheader()
        for it in items:
            row = asdict(it)
            row["size_gb"] = f"{it.size / GB:.4f}"
            row["modified"] = _date(it.mtime)
            w.writerow(row)


# ----------------------------------------------------------------------------- report
def _date(ts: float) -> str:
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d") if ts else "—"


def _gb(n: float) -> str:
    return f"{n / GB:,.2f}"


def _full(it: Item) -> str:
    return str(Path(it.root) / it.rel.replace("/", os.sep))


def _type(it: Item) -> str:
    if it.kind != "file":
        return f"{it.kind} ({it.n_files:,} files)"
    return it.ext or "(none)"


def _cat_split(items: list[Item]) -> dict[str, int]:
    out = {"A": 0, "B": 0, "C": 0}
    for it in items:
        out[it.category] += it.size
    return out


def build_report(items: list[Item], roots: list[str], cfg: dict, errors: list[str]) -> str:
    n_largest = int(cfg.get("n_largest", 30))
    heavy = float(cfg.get("heavy_file_gb", 0.1)) * GB
    small_mb = cfg.get("small_derived_mb", 10)
    L: list[str] = []
    a = L.append

    tot = _cat_split(items)
    total = sum(tot.values())
    a("# Clean-up report — old project material (Phase 0)")
    a("")
    a(f"Generated {datetime.now().strftime('%Y-%m-%d %H:%M')} by `scripts/00_inventory.py`. "
      "**Read-only:** only file metadata was read (no file content, so OneDrive online-only files "
      "were not downloaded). Nothing was moved or deleted.")
    a("")
    a("- Sizes are logical sizes in **GB = 10⁹ bytes** (Windows Explorer shows GiB: multiply by 0.931).")
    a("- A Zarr store, a `.git` folder or a cache folder is counted as **one item** (its file count is shown).")
    a("- Full per-file listing: `outputs/00_inventory/inventory_full.csv` (git-ignored).")
    a("- Content-level checks (what produced what, verified duplicates, bugs found) are in "
      "[old_code_notes.md](old_code_notes.md).")
    a("")
    a(f"**Total scanned: {_gb(total)} GB in {sum(i.n_files for i in items):,} files** "
      f"({len(items):,} items after grouping).")
    a("")

    # categories
    a("## Categories")
    a("")
    a("| Cat. | Meaning | When it can go |")
    a("|---|---|---|")
    a("| **A** | Re-downloadable raw data (CHIRPS, ERA5, NDVI NetCDF, GEE GeoTIFFs), caches and junk | "
      "once the new pipeline's data are exported and checked |")
    a("| **B** | Derived intermediates that back the current report (Zarr cubes, `.npy` predictions, "
      "training `.parquet`, backups, output rasters) | once the new results are validated |")
    a(f"| **C** | Keep: shapefiles, code & notebooks, figures, metrics `.json/.csv`, model `.txt`, "
      f"derived tables < {small_mb} MB | keep (archive old code into one zip) |")
    a("")
    a("Classification is rule-based (`src/tadla/inventory.py::classify`); the reason for each item is "
      "given in the tables. You decide what is deleted; when cleaning, items are first moved to a "
      "`_to_delete` folder.")
    a("")

    # per root summary
    a("## Summary per folder")
    a("")
    a("| Folder | Items | Files | Total GB | A GB | B GB | C GB | In OneDrive |")
    a("|---|---:|---:|---:|---:|---:|---:|:---:|")
    by_root: dict[str, list[Item]] = defaultdict(list)
    for it in items:
        by_root[it.root].append(it)
    for r in roots:
        rr = str(Path(r))
        its = by_root.get(rr, [])
        s = _cat_split(its)
        od = "yes" if its and all(i.onedrive for i in its) else ("partly" if any(i.onedrive for i in its) else "no")
        a(f"| `{rr}` | {len(its):,} | {sum(i.n_files for i in its):,} | {_gb(sum(s.values()))} | "
          f"{_gb(s['A'])} | {_gb(s['B'])} | {_gb(s['C'])} | {od} |")
    a(f"| **Total** | {len(items):,} | {sum(i.n_files for i in items):,} | **{_gb(total)}** | "
      f"{_gb(tot['A'])} | {_gb(tot['B'])} | {_gb(tot['C'])} | |")
    a("")

    # largest items
    a(f"## The {n_largest} largest items")
    a("")
    a("| # | Size GB | Modified | Type | Cat. | Path | Reason |")
    a("|---:|---:|---|---|:---:|---|---|")
    for k, it in enumerate(sorted(items, key=lambda i: i.size, reverse=True)[:n_largest], 1):
        a(f"| {k} | {_gb(it.size)} | {_date(it.mtime)} | {_type(it)} | **{it.category}** | "
          f"`{_full(it)}` | {it.reason} |")
    a("")

    # per folder detail
    a("## Detail per folder")
    a("")
    a("One row per directory (items directly inside it). Categories are split when mixed.")
    for r in roots:
        rr = str(Path(r))
        its = by_root.get(rr, [])
        a("")
        a(f"### `{rr}`")
        a("")
        if not its:
            a("_empty or not found_")
            continue
        dirs: dict[str, list[Item]] = defaultdict(list)
        for it in its:
            dirs[it.parent].append(it)
        a("| Directory | Items | Size GB | Types | Last modified | Category (GB) | Main reason |")
        a("|---|---:|---:|---|---|---|---|")
        for d in sorted(dirs):
            g = dirs[d]
            s = _cat_split(g)
            exts: dict[str, int] = defaultdict(int)
            for it in g:
                exts[_type(it) if it.kind != "file" else (it.ext or "(none)")] += 1
            ext_s = ", ".join(f"{e}×{n}" if n > 1 else e for e, n in
                              sorted(exts.items(), key=lambda kv: -kv[1])[:4])
            present = sorted({it.category for it in g})
            cat_s = " / ".join(f"{c}: {_gb(s[c])}" for c in present)
            main = max(g, key=lambda i: i.size)
            a(f"| `{d}` | {len(g)} | {_gb(sum(s.values()))} | {ext_s} | {_date(max(i.mtime for i in g))} | "
              f"{cat_s} | {main.reason} |")
    a("")

    # duplicates
    dups = find_duplicates(items)
    wasted = sum(g[0].size * (len(g) - 1) for g in dups)
    a("## Duplicates (same name and same size)")
    a("")
    a(f"{len(dups)} groups; {_gb(wasted)} GB would be freed by keeping one copy of each. "
      "Same name + size is a strong hint, not a proof (content was not compared). "
      "Groups that share the same set of folders are collapsed into one row.")
    a("")
    if dups:
        # collapse groups that live in the same set of folders
        by_dirs: dict[tuple[str, ...], list[list[Item]]] = defaultdict(list)
        for g in dups:
            key = tuple(sorted(str(Path(i.root) / i.parent.replace("/", os.sep)) for i in g))
            by_dirs[key].append(g)
        rows = sorted(by_dirs.items(), key=lambda kv: -sum(g[0].size * (len(g) - 1) for g in kv[1]))
        a("| Name(s) | Size GB (one copy) | Copies | Folders |")
        a("|---|---:|---:|---|")
        for dirs_key, groups in rows:
            names = [g[0].name for g in groups]
            label = f"`{names[0]}`" if len(names) == 1 else (
                f"{len(names)} files, e.g. `{names[0]}`, `{names[1]}`")
            size1 = sum(g[0].size for g in groups)
            cats = sorted({i.category for g in groups for i in g})
            a(f"| {label} | {_gb(size1)} | {len(groups[0])} | "
              + "<br>".join(f"`{d}`" for d in dirs_key) + f" ({'/'.join(cats)}) |")
    a("")
    near = find_same_name_diff_size(items, heavy)
    if near:
        a(f"### Same name, different size, different folders (≥ {heavy / GB:.1f} GB) — possible duplicates")
        a("")
        a("| Name | Locations (size GB) |")
        a("|---|---|")
        for g in near:
            a(f"| `{g[0].name}` | " + "<br>".join(f"`{_full(i)}` ({_gb(i.size)})" for i in g) + " |")
        a("")

    # onedrive
    od_heavy = sorted([i for i in items if i.onedrive and i.size >= heavy], key=lambda i: -i.size)
    od_total = sum(i.size for i in items if i.onedrive)
    a(f"## OneDrive-synced heavy items (≥ {heavy / GB:.1f} GB)")
    a("")
    a(f"Everything under a OneDrive folder is synced to the cloud and counts against the OneDrive quota "
      f"unless it is excluded from sync. **{_gb(od_total)} GB** of the scanned material is inside "
      f"OneDrive; {len(od_heavy)} items are ≥ {heavy / GB:.1f} GB "
      f"({_gb(sum(i.size for i in od_heavy))} GB). "
      f"Items whose content is online-only (not on this disk): "
      f"{sum(1 for i in items if i.onedrive and i.cloud_only)}.")
    a("")
    if od_heavy:
        a("| Size GB | Cat. | Path |")
        a("|---:|:---:|---|")
        for it in od_heavy:
            a(f"| {_gb(it.size)} | {it.category} | `{_full(it)}` |")
    a("")

    # flags
    flagged = [i for i in items if i.flag]
    if flagged:
        a("## Flags")
        a("")
        for it in flagged:
            a(f"- `{_full(it)}` — {it.flag}")
        a("")
    if errors:
        a("## Walk errors")
        a("")
        for e in errors:
            a(f"- {e}")
        a("")

    # totals (must be last)
    a("## Total per category")
    a("")
    a("| Category | Items | GB |")
    a("|---|---:|---:|")
    for c, label in (("A", "A — re-downloadable raw data / junk"),
                     ("B", "B — derived intermediates (delete after validation)"),
                     ("C", "C — keep")):
        a(f"| {label} | {sum(1 for i in items if i.category == c):,} | **{_gb(tot[c])}** |")
    a(f"| **All** | {len(items):,} | **{_gb(total)}** |")
    a("")
    return "\n".join(L)
