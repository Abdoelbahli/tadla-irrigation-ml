# Decision log

Each methodological decision, with the evidence behind it and the date. Feeds the thesis
"Matériel et méthodes" chapter.

## D1 — Study period: 2016–2025 (confirmed 2026-11-06)

Evidence: `scripts/01a_check_collections.py`, run 2026-11-06 over `tadla_area`
(outputs in `outputs/01a_check_collections/`).

| Collection | First image | Last image | 2025 |
|---|---|---|---|
| HLS S30 v002 | 2015-11-29 | 2026-11-01 | complete |
| HLS L30 v002 | 2013-04-12 | 2026-11-02 | complete |
| CHIRPS daily / pentad | 1981-01-01 | 2026-09-30 | complete |
| ERA5-Land hourly / daily / monthly | 1950 | 2026-10-31 / 2026-10-26 / 2026-09 | complete |
| MOD13Q1 | 2000-02-18 | composite of 2026-10-16 | complete |

- Start 2016: first complete year of HLS S30. End 2025: last year complete in every collection.
- HLS distinct acquisition dates per year (real tiles only): S30 68 (2016), 99 (2017), 141–159 (2018–2025);
  L30 ≈ 45 until 2021, 84–90 from 2022 (Landsat 9). Every month of 2016–2025 has ≥ 6 dates (S30 or L30).
  2016–2017 are sparser: if cloud masking leaves too few clear observations, the fallback is 2017–2025.
- 2018 is fully covered by HLS (141 S30 + 46 L30 dates), unlike the old Sentinel-2 SR collection.

## D2 — HLS granules are filtered by MGRS tile (2026-11-06)

`filterBounds(tadla_area)` also returns HLS granules from UTM zones 01 and 60 whose antimeridian-crossing
footprints intersect everything (31 such tiles). Only T29SPR, T29SQR and T29SQS cover the area.
Some tile-dates have two granules (S30: 26 in 2025): images are mosaicked per day before observations
are counted.

## D3 — Optional MODIS long-record experiment: 2001–2025 (pending)

MOD13Q1 starts 2000-02-18, so 2001 is its first complete year. Optional, reported separately; design:
MODIS model trained on 2001–2025 vs on 2016–2025, both evaluated by leave-one-year-out on 2016–2025.

## D4 — Spatial reference: `area.shp` with the standard EPSG transformation; EE asset not used (2026-11-06)

Evidence: `scripts/01b_build_grid.py` and checks run on 2026-11-06.

- Earth Engine and PROJ define EPSG:26191 identically, including the Merchich → WGS 84 shift
  TOWGS84 (31, 146, 47) m (EPSG transformation "Merchich to WGS 84 (1)"): the centroid of `area.shp`
  converted by both lands on the same point (0.0 m apart).
- The asset `projects/pfe-abdellahelbahli/assets/tadla_area` has the same area (701.837 vs 701.828 km²)
  but is offset by ≈ 152 m (≈ 148 m west, 31–36 m south). Converting `area.shp` *without* the datum shift
  reproduces the asset (symmetric difference 0.024 km², vs 9.85 km² with the shift): the upload ignored
  the datum shift, as happens with `.prj` files that carry no TOWGS84.
- A ground check (summer NDVI contrast across the boundary) was inconclusive: the boundary is not an NDVI
  edge at any tested offset. The polygon has 97 vertices (segments of ~2–3 km), so it is a generalised
  outline; the issue is consistency rather than precision.
- Decision: `area.shp` interpreted with the standard EPSG transformation is the single reference
  (this is also how the old work clipped its data). The grid is sent to Earth Engine as EPSG:26191
  polygons; the asset is not used for any geometry.

## D5 — 1 km grid (2026-11-06)

- Cells aligned on multiples of 1000 m in EPSG:26191; frame 27 rows × 58 columns, origin
  x = 349 000 m, y_top = 206 000 m; row 0 = north (old_code_notes.md §4.1).
- 800 cells overlap `area.shp` (positive-area overlap): 616 entirely inside, 698 ≥ 50 % inside,
  793 ≥ 1 % inside; inside areas sum to 701.8281 km² (= area of `area.shp`).
- All 779 cells of the old 1 km predictions are in the new grid; the 21 extra cells are slivers
  (≤ 3.3 % inside). Cells are kept with their `frac_inside`; any minimum fraction for modelling is
  decided with the valid-pixel statistics of the export.
