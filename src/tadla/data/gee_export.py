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
