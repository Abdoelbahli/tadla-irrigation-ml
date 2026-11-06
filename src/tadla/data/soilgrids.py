"""SoilGrids 2.0 (ISRIC) download through WCS and per-cell aggregation.

`wv0010` is not available in Earth Engine (checked 2026-11-06), so all five soil properties are
taken from the same source, the ISRIC WCS (https://maps.isric.org), in the native SoilGrids
projection (Interrupted Goode Homolosine, 250 m), and aggregated locally.

Units (ISRIC SoilGrids FAQ, "mapped units" -> conventional units, divide by the factor):
  clay, silt, sand : g/kg            / 10 -> %  (g/100 g)
  ocd              : hg/m³           / 10 -> kg/m³ (organic carbon density)
  wv0010           : 10⁻³ cm³/cm³    / 10 -> vol. %  (volumetric water content at 10 kPa)
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import requests

IGH = "+proj=igh +lat_0=0 +lon_0=0 +datum=WGS84 +units=m +no_defs"
CONVERSION = {"clay": 10.0, "silt": 10.0, "sand": 10.0, "ocd": 10.0, "wv0010": 10.0}
UNITS = {"clay": "%", "silt": "%", "sand": "%", "ocd": "kg/m3", "wv0010": "vol%"}


def igh_bbox(bounds_projected, epsg: int, margin_m: float = 1000.0) -> tuple[float, float, float, float]:
    """Bounding box in Homolosine metres of a projected bounding box (densified edges)."""
    from pyproj import Transformer
    xmin, ymin, xmax, ymax = bounds_projected
    xmin, ymin, xmax, ymax = xmin - margin_m, ymin - margin_m, xmax + margin_m, ymax + margin_m
    xs = np.r_[np.linspace(xmin, xmax, 50), np.full(50, xmax), np.linspace(xmax, xmin, 50), np.full(50, xmin)]
    ys = np.r_[np.full(50, ymin), np.linspace(ymin, ymax, 50), np.full(50, ymax), np.linspace(ymax, ymin, 50)]
    tx, ty = Transformer.from_crs(f"EPSG:{epsg}", IGH, always_xy=True).transform(xs, ys)
    return float(np.min(tx)), float(np.min(ty)), float(np.max(tx)), float(np.max(ty))


def download(wcs: str, prop: str, depth: str, bbox_igh, out_dir: Path, overwrite: bool = False) -> Path:
    """GetCoverage of '<prop>_<depth>_mean' as GeoTIFF in the native CRS."""
    out_dir.mkdir(parents=True, exist_ok=True)
    cov = f"{prop}_{depth}_mean"
    path = out_dir / f"{cov}.tif"
    if path.exists() and not overwrite:
        return path
    minx, miny, maxx, maxy = bbox_igh
    params = [("map", f"/map/{prop}.map"), ("SERVICE", "WCS"), ("VERSION", "2.0.1"),
              ("REQUEST", "GetCoverage"), ("COVERAGEID", cov), ("FORMAT", "image/tiff"),
              ("SUBSET", f"X({minx},{maxx})"), ("SUBSET", f"Y({miny},{maxy})")]
    r = requests.get(wcs, params=params, timeout=120)
    if r.status_code != 200 or not r.content.startswith((b"II*", b"MM\x00*")):
        raise RuntimeError(f"WCS {cov}: HTTP {r.status_code}, {r.content[:300]!r}")
    path.write_bytes(r.content)
    return path


def cell_means(tif: Path, cells_clipped, resample_m: float) -> np.ndarray:
    """Mean of the raster over each clipped cell (raw mapped units).

    The 250 m raster is resampled (nearest neighbour, no smoothing) onto a `resample_m` grid in
    the cells' CRS; a cell value is the mean over the fine pixels whose centre falls inside the
    clipped cell, i.e. an area-weighted mean of the SoilGrids pixels. Nodata is excluded."""
    import rasterio
    from rasterio.features import rasterize
    from rasterio.transform import from_origin
    from rasterio.warp import Resampling, reproject

    xmin, ymin, xmax, ymax = cells_clipped.total_bounds
    xmin, ymax = np.floor(xmin / resample_m) * resample_m, np.ceil(ymax / resample_m) * resample_m
    width = int(np.ceil((xmax - xmin) / resample_m))
    height = int(np.ceil((ymax - ymin) / resample_m))
    transform = from_origin(xmin, ymax, resample_m, resample_m)
    with rasterio.open(tif) as src:
        # The WCS GeoTIFFs declare no nodata value. Unmapped (non-soil) pixels come as 0 in 9 of
        # the 10 layers (same 356 pixels; smallest real values >= 138; clay+silt+sand = 999–1001
        # g/kg elsewhere) and as -32768 in wv0010 5–15 cm (checked 2026-11-06). All five
        # properties are strictly positive, so every value <= 0 is treated as nodata.
        dst = np.full((height, width), np.nan, dtype="float64")
        reproject(source=rasterio.band(src, 1), destination=dst, dst_transform=transform,
                  dst_crs=cells_clipped.crs, dst_nodata=np.nan, src_nodata=src.nodata,
                  resampling=Resampling.nearest)
        dst[dst <= 0] = np.nan
    ids = rasterize(((g, i + 1) for i, g in enumerate(cells_clipped.geometry) if not g.is_empty),
                    out_shape=(height, width), transform=transform, fill=0, dtype="int32")
    ok = (ids > 0) & np.isfinite(dst)
    n = len(cells_clipped) + 1
    s = np.bincount(ids[ok], weights=dst[ok], minlength=n)
    c = np.bincount(ids[ok], minlength=n)
    with np.errstate(invalid="ignore", divide="ignore"):
        return (s / c)[1:]
