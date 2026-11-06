"""Earth Engine helpers: initialisation, catalogue checks (and, later, the 1 km exports)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import ee

_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


def init_ee(project: str) -> None:
    """Initialise Earth Engine for the given Cloud project (credentials from `earthengine authenticate`)."""
    ee.Initialize(project=project)


def study_area(asset_id: str) -> ee.Geometry:
    return ee.FeatureCollection(asset_id).geometry()


def _iso(ms: float | None) -> str | None:
    if ms is None:
        return None
    # not datetime.fromtimestamp(): it fails on Windows for dates before 1970 (ERA5-Land starts 1950)
    return (_EPOCH + timedelta(milliseconds=ms)).strftime("%Y-%m-%d %H:%M")


def collection_summary(coll_id: str, region: ee.Geometry, years: tuple[int, int],
                       months_from: str, months_to: str, find_first: bool = True) -> dict:
    """Real temporal coverage of a collection over `region`.

    Returns the first/last image (system:time_start, and system:time_end of the last image),
    the number of images per calendar year in `years` (inclusive), and per month between
    `months_from` and `months_to` (YYYY-MM-01, end exclusive). Image counts are taken over
    images whose footprint intersects `region`. With ``find_first=False`` (very large
    collections such as ERA5-Land hourly) the first image is not searched and is reported
    as None.
    """
    col = ee.ImageCollection(coll_id).filterBounds(region)

    # 1) cheap metadata counts per year and per recent month
    y0, y1 = years
    per_year = ee.List.sequence(y0, y1).map(
        lambda y: col.filterDate(ee.Date.fromYMD(y, 1, 1), ee.Date.fromYMD(ee.Number(y).add(1), 1, 1)).size()
    )
    start = ee.Date(months_from)
    n_months = ee.Date(months_to).difference(start, "month").round()
    per_month = ee.List.sequence(0, n_months.subtract(1)).map(
        lambda k: col.filterDate(start.advance(k, "month"), start.advance(ee.Number(k).add(1), "month")).size()
    )
    counts = ee.Dictionary({"per_year": per_year, "per_month": per_month}).getInfo()
    nonzero = [y for y, n in zip(range(y0, y1 + 1), counts["per_year"]) if n > 0]

    # 2) first/last image, sorting only inside the first/last non-empty year
    #    (sorting a whole global collection such as ERA5-Land hourly exceeds EE memory).
    #    If the collection starts before y0, the true start is found with one extra query.
    info = {"first_start": None, "last_start": None, "last_end": None}
    if nonzero:
        def in_year(y):
            return col.filterDate(f"{y}-01-01", f"{y + 1}-01-01")
        last = in_year(nonzero[-1]).limit(1, "system:time_start", False).first()
        query = {"last_start": last.get("system:time_start"), "last_end": last.get("system:time_end")}
        if find_first:
            first_scope = in_year(nonzero[0]) if nonzero[0] > y0 else col.filterDate("1900-01-01", f"{y0 + 1}-01-01")
            query["first_start"] = first_scope.limit(1, "system:time_start", True).first().get("system:time_start")
        info.update(ee.Dictionary(query).getInfo())
    info.update(counts)

    months = []
    d = datetime.strptime(months_from, "%Y-%m-%d")
    for _ in info["per_month"]:
        months.append(d.strftime("%Y-%m"))
        d = d.replace(year=d.year + (d.month == 12), month=d.month % 12 + 1)
    return {
        "id": coll_id,
        "first_start": _iso(info["first_start"]),
        "last_start": _iso(info["last_start"]),
        "last_end": _iso(info["last_end"]),
        "per_year": dict(zip(range(y0, y1 + 1), info["per_year"])),
        "per_month": dict(zip(months, info["per_month"])),
    }


def hls_tile_filter(tiles: list[str]) -> ee.Filter:
    """Keep only HLS granules of the given MGRS tiles (system:index = 'T29SQR_20230302T110431')."""
    return ee.Filter.Or(*[ee.Filter.stringStartsWith("system:index", f"{t}_") for t in tiles])


def hls_acquisitions(coll_id: str, region: ee.Geometry, tiles: list[str], start: str, end: str) -> list[tuple[str, str]]:
    """(tile, YYYYMMDD) of every HLS granule over `region` restricted to `tiles` (duplicates kept)."""
    col = ee.ImageCollection(coll_id).filterBounds(region).filterDate(start, end).filter(hls_tile_filter(tiles))
    ids = col.aggregate_array("system:index").getInfo()
    return [(i.split("_")[0], i.split("_")[1][:8]) for i in ids]


def heavy_collection_summary(coll_id: str, region: ee.Geometry, years: tuple[int, int],
                             last_window: tuple[str, str]) -> dict:
    """Light-weight check for very large collections (e.g. ERA5-Land hourly, ~8,760 images/yr):
    per-year counts as independent size() calls, and the last image searched only inside
    `last_window` (start, end). The first image is not searched."""
    col = ee.ImageCollection(coll_id).filterBounds(region)
    y0, y1 = years
    sizes = [col.filterDate(f"{y}-01-01", f"{y + 1}-01-01").size() for y in range(y0, y1 + 1)]
    last = col.filterDate(*last_window).limit(1, "system:time_start", False).first()
    # two separate requests: bundled into one, they exceed EE's per-request memory (checked)
    info = {"per_year": ee.List(sizes).getInfo()}
    info.update(ee.Dictionary({"last_start": last.get("system:time_start"),
                               "last_end": last.get("system:time_end")}).getInfo())
    return {"id": coll_id, "first_start": None,
            "last_start": _iso(info["last_start"]), "last_end": _iso(info["last_end"]),
            "per_year": dict(zip(range(y0, y1 + 1), info["per_year"])), "per_month": {}}


def wait_for_task(task: "ee.batch.Task", poll_s: int = 10, timeout_s: int = 1800) -> dict:
    """Block until an EE batch task finishes; raise if it fails."""
    import time
    t0 = time.time()
    while True:
        st = task.status()
        if st["state"] in ("COMPLETED", "FAILED", "CANCELLED"):
            if st["state"] != "COMPLETED":
                raise RuntimeError(f"task {st.get('description')} {st['state']}: {st.get('error_message')}")
            return st
        if time.time() - t0 > timeout_s:
            raise TimeoutError(f"task {st.get('description')} still {st['state']} after {timeout_s}s")
        time.sleep(poll_s)


def upload_geometry_asset(geom_projected, epsg: int, asset_id: str, properties: dict) -> dict:
    """Write a shapely geometry given in EPSG:`epsg` to an EE table asset.

    The geometry is passed to EE in its projected CRS (planar edges), so EE applies its own
    EPSG transformation (identical to PROJ for EPSG:26191, see decisions.md D4)."""
    from shapely.geometry import mapping
    feat = ee.Feature(ee.Geometry(mapping(geom_projected), f"EPSG:{epsg}", False), properties)
    task = ee.batch.Export.table.toAsset(collection=ee.FeatureCollection([feat]),
                                         description=asset_id.split("/")[-1], assetId=asset_id)
    task.start()
    return wait_for_task(task)


# =============================================================================================
# Per-cell layers (Phase 1, step 3). Every function returns an ee.FeatureCollection with one
# feature per grid cell; nothing is exported as a raster.
# =============================================================================================

def cells_fc(cells_gdf, epsg: int) -> ee.FeatureCollection:
    """Grid cells (already clipped to the study area) as an EE collection.

    Geometries are sent in their projected CRS with planar edges, so EE applies the same
    EPSG:26191 -> WGS84 transformation as PROJ (decisions.md D4)."""
    from shapely.geometry import mapping
    feats = [ee.Feature(ee.Geometry(mapping(g), f"EPSG:{epsg}", False), {"cell_id": cid})
             for cid, g in zip(cells_gdf["cell_id"], cells_gdf.geometry)]
    return ee.FeatureCollection(feats)


def fetch_table(fc: ee.FeatureCollection, columns: list[str] | None = None):
    """Download a (small) feature collection as a pandas DataFrame, without geometries."""
    import pandas as pd
    if columns:
        fc = fc.select(columns, None, False)
    else:
        fc = fc.map(lambda f: f.setGeometry(None))
    feats = fc.getInfo()["features"]
    return pd.DataFrame([f["properties"] for f in feats])


# ---------------------------------------------------------------- HLS NDVI
def _hls_ndvi(coll_id: str, nir: str, red: str, masked_bits: list[int], tiles: list[str],
              region: ee.Geometry, start: ee.Date, end: ee.Date) -> ee.ImageCollection:
    """Cloud-masked NDVI of every HLS granule of the real MGRS tiles.

    HLS v2.0 reflectances are already scaled to 0–1 in EE (checked 2026-11-06); NDVI is a ratio
    so scaling does not matter anyway. NIR = B8A for S30 (the band harmonised with OLI B5,
    it carries the bandpass adjustment), B5 for L30; red = B4 for both.
    Fmask: a pixel is kept only if none of `masked_bits` is set
    (1 cloud, 2 adjacent to cloud/shadow, 3 cloud shadow, 4 snow/ice; water (5) and the
    aerosol level (6–7) are NOT masked — see docs/decisions.md).
    Pixels with nir + red <= 0 or NDVI outside [-1, 1] are dropped.
    """
    bitmask = sum(1 << b for b in masked_bits)
    col = (ee.ImageCollection(coll_id).filterBounds(region).filterDate(start, end)
           .filter(hls_tile_filter(tiles)))

    def prep(img):
        r = img.select(red)
        n = img.select(nir)
        ndvi = n.subtract(r).divide(n.add(r)).rename("ndvi")
        ok = (img.select("Fmask").bitwiseAnd(bitmask).eq(0)
              .And(n.add(r).gt(0)).And(ndvi.gte(-1)).And(ndvi.lte(1)))
        return ndvi.updateMask(ok).copyProperties(img, ["system:time_start"]).set(
            "day", img.date().format("YYYY-MM-dd"))

    return col.map(prep)


def hls_month(cells: ee.FeatureCollection, cfg_hls: dict, tiles: list[str], region: ee.Geometry,
              year: int, month: int) -> tuple[ee.FeatureCollection, ee.Dictionary]:
    """Monthly HLS NDVI per cell.

    1. granules of the same day (S30 and/or L30, overlapping tiles, duplicates) are averaged
       per pixel -> one daily image (a day counts once);
    2. per pixel: monthly mean of the clear daily NDVI, and number of clear days;
    3. per cell (pixel centres inside the clipped cell, native 30 m UTM 29N grid):
       ndvi_mean, ndvi_stdDev (spatial), ndvi_count (pixels with >= 1 clear day),
       px_count (all pixels) -> valid fraction = ndvi_count / px_count,
       nclear_mean / nclear_max (clear days per pixel, 0 where never clear).
    """
    start = ee.Date.fromYMD(year, month, 1)
    end = start.advance(1, "month")
    s30 = _hls_ndvi(cfg_hls["collections"]["hls_s30"], cfg_hls["nir_band"]["hls_s30"], cfg_hls["red_band"],
                    cfg_hls["fmask_masked_bits"], tiles, region, start, end)
    l30 = _hls_ndvi(cfg_hls["collections"]["hls_l30"], cfg_hls["nir_band"]["hls_l30"], cfg_hls["red_band"],
                    cfg_hls["fmask_masked_bits"], tiles, region, start, end)
    both = s30.merge(l30)
    days = both.aggregate_array("day").distinct()
    daily = ee.ImageCollection.fromImages(
        days.map(lambda d: both.filter(ee.Filter.eq("day", d)).mean().set("day", d)))
    img = ee.Image.cat(
        daily.mean().rename("ndvi"),
        daily.count().unmask(0).rename("nclear"),
        ee.Image.constant(1).rename("px"),
    )
    reducer = (ee.Reducer.mean().combine(ee.Reducer.stdDev(), sharedInputs=True)
               .combine(ee.Reducer.count(), sharedInputs=True)
               .combine(ee.Reducer.max(), sharedInputs=True)).unweighted()
    fc = img.reduceRegions(collection=cells, reducer=reducer, crs=cfg_hls["crs"], scale=cfg_hls["scale"])
    meta = ee.Dictionary({"n_days": days.size(), "n_granules_s30": s30.size(), "n_granules_l30": l30.size()})
    return fc, meta


# ---------------------------------------------------------------- ERA5-Land + CHIRPS (daily)
# Raw daily variables exported per cell; unit conversions and ET0 are done in
# tadla.data.climate (Python, unit-tested). Names -> (collection band, raw unit).
ERA5_DAILY_BANDS = {
    "tmax": "temperature_2m_max",                    # K, max of hourly 2 m temperature
    "tmin": "temperature_2m_min",                    # K, min of hourly 2 m temperature
    "tmean": "temperature_2m",                       # K, daily mean
    "tdew": "dewpoint_temperature_2m",               # K, daily mean dew point
    "sp": "surface_pressure",                        # Pa, daily mean
    "ssrd": "surface_solar_radiation_downwards_sum", # J m-2 day-1
    "te": "total_evaporation_sum",                   # m water eq. day-1, ECMWF sign: < 0 = evaporation
    "swvl1": "volumetric_soil_water_layer_1",        # m3 m-3, 0–7 cm, daily mean
    "swvl2": "volumetric_soil_water_layer_2",        # m3 m-3, 7–28 cm, daily mean
}


def _era5_day(day: ee.Date) -> ee.Image:
    """ERA5-Land daily variables + daily mean wind speed computed from HOURLY data.

    Wind: DAILY_AGGR only holds daily-mean u/v components; the speed of the mean vector
    underestimates the mean speed. Here speed = sqrt(u² + v²) for each hour (10 m), then the
    mean of the 24 hourly speeds of the UTC day -> ws10 (m s-1)."""
    nxt = day.advance(1, "day")
    daily = (ee.ImageCollection("ECMWF/ERA5_LAND/DAILY_AGGR").filterDate(day, nxt).first()
             .select(list(ERA5_DAILY_BANDS.values()), list(ERA5_DAILY_BANDS.keys())))
    hourly = (ee.ImageCollection("ECMWF/ERA5_LAND/HOURLY").filterDate(day, nxt)
              .select(["u_component_of_wind_10m", "v_component_of_wind_10m"]))
    ws = hourly.map(lambda i: i.select(0).hypot(i.select(1))).mean().rename("ws10")
    nh = ee.Image.constant(hourly.size()).rename("nhours")
    return daily.addBands(ws).addBands(nh)


def climate_month(cells: ee.FeatureCollection, year: int, month: int, sample_scale: float,
                  epsg: int) -> ee.FeatureCollection:
    """Daily ERA5-Land and CHIRPS values per cell for one month (one column per variable and day,
    e.g. 'tmax_d07', 'rain_d07').

    Each daily stack is computed on its native grid (ERA5-Land 0.1°, CHIRPS 0.05°) and then
    sampled on a `sample_scale` grid in EPSG:`epsg` with nearest-neighbour resampling, so a
    cell value is the area-weighted mean of the coarse pixels it overlaps (no smoothing).
    CHIRPS daily precipitation is in mm day-1.
    """
    import calendar
    n = calendar.monthrange(year, month)[1]
    era5_proj = (ee.ImageCollection("ECMWF/ERA5_LAND/DAILY_AGGR").first()
                 .select("temperature_2m").projection())
    chirps = ee.ImageCollection("UCSB-CHG/CHIRPS/DAILY")
    chirps_proj = chirps.first().projection()
    era5_days, rain_days = [], []
    for d in range(1, n + 1):
        day = ee.Date.fromYMD(year, month, d)
        e = _era5_day(day)
        era5_days.append(e.rename(e.bandNames().map(lambda b: ee.String(b).cat(f"_d{d:02d}"))))
        rain_days.append(chirps.filterDate(day, day.advance(1, "day")).first()
                         .select("precipitation").rename(f"rain_d{d:02d}"))
    stack = ee.Image.cat(
        ee.Image.cat(era5_days).reproject(era5_proj),
        ee.Image.cat(rain_days).reproject(chirps_proj),
    )
    return stack.reduceRegions(collection=cells, reducer=ee.Reducer.mean(),
                               crs=f"EPSG:{epsg}", scale=sample_scale)


# ---------------------------------------------------------------- static: DEM
def dem_cells(cells: ee.FeatureCollection, cfg_dem: dict) -> ee.FeatureCollection:
    """Elevation per cell from ALOS AW3D30 (DSM, metres): mean, stdDev, min, max, sampled on the
    native ~30 m grid (UTM 29N, 30 m)."""
    dem = ee.ImageCollection(cfg_dem["collection"]).select(cfg_dem["band"]).mosaic().rename("dem")
    reducer = (ee.Reducer.mean().combine(ee.Reducer.stdDev(), sharedInputs=True)
               .combine(ee.Reducer.minMax(), sharedInputs=True))
    return dem.reduceRegions(collection=cells, reducer=reducer, crs=cfg_dem["crs"], scale=cfg_dem["scale"])
