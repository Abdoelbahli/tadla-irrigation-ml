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

## D6 — HLS NDVI processing (2026-11-06)

- NDVI = (NIR − red)/(NIR + red) with NIR = B8A for S30 (the Sentinel-2 band harmonised with Landsat OLI B5;
  it is the band carrying the HLS bandpass adjustment) and B5 for L30; red = B4. HLS v2.0 reflectances are
  already scaled to 0–1 in Earth Engine.
- Fmask (bit definitions checked in the EE catalogue): pixels with bit 1 cloud, 2 adjacent to cloud/shadow,
  3 cloud shadow or 4 snow/ice set are masked. Not masked: bit 5 water (temporarily flooded irrigated fields
  could be flagged) and bits 6–7 aerosol level (a clear July pixel checked was flagged "high"; masking it would
  remove much of the summer data). Can be revisited.
- Per pixel: granules of the same day are averaged (a day counts once), then the monthly mean of clear days and
  the number of clear days. Per cell: mean over 30 m pixel centres inside the clipped cell, spatial std,
  valid-pixel fraction, mean and max clear days.
- 2022 check: the valid-pixel fraction is 1.00 in every month (each pixel has ≥ 1 clear day), so the number of
  clear days per pixel (5.7–12.3 per month in 2022) is the informative quality indicator for the threshold.
- B8A gives NDVI +0.031 (March 2022) to +0.045 (July 2022) higher than B8 on the same S30 pixels; this explains
  most of the +0.046 mean difference with the old Sentinel-2 NDVI (B8). **Relevant to the Kc–NDVI open point:**
  the coefficients must be used with an NDVI comparable to the one of the source paper.

## D7 — Climate inputs and FAO-56 ET0 (2026-11-06)

- ERA5-Land `DAILY_AGGR` for Tmax, Tmin, mean dew point, surface pressure, incoming solar radiation and total
  evaporation. Checked: its daily sums equal ERA5's native 24 h accumulation (value at 00 UTC of the next day)
  exactly; the sums of EE's derived `*_hourly` bands do not (up to ×2 for evaporation on a July day) and are not used.
- Wind: hourly speed √(u² + v²) at 10 m, averaged over the 24 h of the UTC day, converted to 2 m (FAO-56 Eq. 47).
- Daily FAO-56 Penman-Monteith (Eq. 6) in Python (`tadla/irrigation/fao56.py`, tested against FAO-56 Examples 8
  and 18): ea = e°(Tdew) (Eq. 14); Rn from Rs for the reference grass (albedo 0.23, Eqs. 37–40, Rso with the ALOS
  cell elevation); P from ERA5-Land; G = 0. Monthly ET0 = sum of daily values.
- Actual ET = −1000 × Σ daily `total_evaporation_sum` (ECMWF sign: negative = evaporation); no cell-month was
  negative in 2022.
- Coarse grids (ERA5-Land 0.1°, CHIRPS 0.05°) are computed on their native grid and sampled at 100 m with
  nearest neighbour: a cell value is the area-weighted mean of the coarse pixels it overlaps.
- **2022 result: ET0 = 1544 mm (area mean), July 218 mm — not the ≈ 1150 / 165 mm of CLAUDE.md.** The old ET0
  GeoTIFF (producing script missing) gives 1149 mm at cell X380_Y190; recomputing 2022 there with (a) the speed
  of the daily-mean wind vector and (b) ERA5-Land's own surface net radiation reproduces the old file within
  0.5–2.5 % in every month (1132 vs 1149 mm, monthly correlation 0.9999). Both choices depart from the FAO-56
  reference definition (scalar wind speed; Rn of the reference grass). Each alone: −10 % (wind), −16 % (Rn).
  Hargreaves (Eq. 52) gives 1710 mm at that cell. No independent station value was found yet.
  Caveat (FAO-56 Annex 6): ERA5-Land does not simulate irrigation, so its air is drier/hotter than over the
  irrigated plain; using e°(Tmin) as humidity lowers ET0 by only 4 % at that cell.
  **Pending: your confirmation, then update of the CLAUDE.md "established facts".**

## D8 — DEM: ALOS AW3D30 V4.1 (2026-11-06)

`JAXA/ALOS/AW3D30/V4_1` (DSM, m); V3_2, used by the old work, is deprecated in Earth Engine. Cell mean, std,
min, max on the 30 m UTM 29N grid. 2022 check: cell means 369–475 m, median 419 m.

## D9 — Soil: SoilGrids 2.0 via ISRIC WCS, 0–5 and 5–15 cm (2026-11-06)

- `wv0010` is not in Earth Engine, so all five properties come from the ISRIC WCS in the native Homolosine
  projection (250 m) and are averaged per cell after nearest-neighbour resampling to 25 m.
- Units (ISRIC FAQ): clay/silt/sand g/kg ÷ 10 → %, ocd hg/m³ ÷ 10 → kg/m³, wv0010 (volumetric water content at
  10 kPa, not saturation) 10⁻³ cm³/cm³ ÷ 10 → vol %.
- Nodata: values ≤ 0 (0 in 9 layers, −32768 in wv0010 5–15 cm; the GeoTIFFs declare none). 796/800 cells
  have values; clay+silt+sand = 100.0–100.1 %.
- SoilGrids has no 0–10 cm layer; the old work used 0–5 cm. Both 0–5 and 5–15 cm are exported.
  **Pending: which depth (or depth-weighted 0–15 cm) is used for modelling.**
