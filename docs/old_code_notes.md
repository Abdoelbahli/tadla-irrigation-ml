# Old code — provenance notes (Phase 0)

What produced each current result of the old work, answered from the code and the files themselves
(read-only; nothing in the old folders was modified). Written 2026-11-06.

Old folders: `C:\Users\abdel\OneDrive\Desktop\train` (abbreviated `train\`) and
`C:\Users\abdel\OneDrive\Desktop\PFE_Project` (`PFE\`). `files\` = `train\files\`.

**Evidence levels used below**
- **verified** — checked by reading code *and* the output file (values, metadata or timestamps).
- **from code** — read from the code; the output file was not opened.
- **not found** — the producing code is not in either folder.

---

## 1. Open point 3 — which DEM feeds `dem`? → **ALOS AW3D30 V3.2 DSM** (verified)

Not SRTM. Chain and evidence:

1. `PFE\Scripts\Phase1_Data_Preprocessing\Data_collection_and_preprocessing.ipynb`, cells 43–44:
   `ee.ImageCollection("JAXA/ALOS/AW3D30/V3_2").select('DSM').mosaic()`, exported as `Tadla_DEM`
   at 12.5 m in EPSG:26191 → `PFE\Data\Raw\GIS\Topography\Tadla_DEM.tif` (int16, 12.5 m, band description `DSM`).
   Cell 41 only calls `NASA/NASADEM_HGT/001` to test authentication.
2. Cell 86: bilinear resampling onto the 10 m NDVI grid → `PFE\Data\Processed\GIS\Topography\tadla_dem_10m.tif`
   (`config.yml: dem_processed`).
3. `PFE\Scripts\Phase2_Machine_Learning.ipynb`, cell 4: `"dem": rxr.open_rasterio(tadla_dem_10m.tif)`
   → `D:\COMBINED_DATA\combined_with_static.zarr`.
4. `train\clipped_dataset_v5.zarr` (the cube every model used) is the clip of that cube (clip script not found, see §5).

Checks run on 2026-11-06:

| Comparison | n points | Exactly equal | Mean \|diff\| |
|---|---:|---:|---:|
| `dem` in `clipped_dataset_v5.zarr` vs `tadla_dem_10m.tif` (same 10 m pixel centres) | 5,000 | **100 %** | 0.000 m |
| raw `Tadla_DEM.tif` vs `JAXA/ALOS/AW3D30/V3_2` DSM queried in Earth Engine on the same 12.5 m grid | 300 | **100 %** | 0.000 m |
| raw `Tadla_DEM.tif` vs `USGS/SRTMGL1_003` | 300 | 20 % | 1.73 m |
| raw `Tadla_DEM.tif` vs `NASA/NASADEM_HGT/001` | 300 | 3 % | 3.62 m |

Consequences:
- The thesis workflow figure (`train\generer_figures_fr.py:72`, Fig. III.1) says **"SoilGrids + SRTM"**: this is
  wrong for the old work and must be corrected (or the rebuild must really use SRTM, see the decision below).
- Earth Engine now flags `JAXA/ALOS/AW3D30/V3_2` as **deprecated** (warning returned on 2026-11-06).
- Values over the study area: 354–496 m, median 421 m.
- **Decision to take (yours):** for the rebuild, either keep ALOS AW3D30 (newer version in the catalog, to check)
  or switch to SRTM/NASADEM. At 1 km both differ by ~2–4 m on average, so the model will barely notice;
  what matters is that the thesis text matches the code.

---

## 2. Data chain upstream of the models

| Step | Output | Produced by | Level |
|---|---|---|---|
| Sentinel-2 NDVI export | `Sentinel2_Tadla_NDVI_{year}` (Drive) | Phase 1 nb, cells 76–77 — **but this code is an annual Apr–Sep median composite** with `CLOUDY_PIXEL_PERCENTAGE < 10` and no use of the SCL band. The cube holds **monthly** NDVI, so the monthly export code is **not** this one | not found |
| CHIRPS daily export | `CHIRPS_Daily_Tadla_2017-2023` (5 km, EPSG:4326) | Phase 1 nb, cell 53 (`UCSB-CHG/CHIRPS/DAILY`) | from code |
| ERA5-Land actual ET export | `ERA5_Land_Evaporation_Tadla_2017-2023` | Phase 1 nb, cell 55: `ECMWF/ERA5_LAND/DAILY_AGGR`, band `total_evaporation_sum`; cell 63 ×1000 (m → mm) | from code |
| ALOS DEM | see §1 | Phase 1 nb, cells 43–44, 86 | verified |
| SoilGrids clay/silt/sand/ocd/wv0010 | `PFE\Data\Raw\GIS\Soil\*.tif` → `*_10m.tif` | Phase 1 nb (cell 29 and the resampling cell 130). Cell 29 computes `clay/10` but writes the **unconverted** array (no-op); the final cube is nevertheless in % (clay+silt+sand median = 100.0) | from code + values checked |
| Monthly 10 m NetCDFs | `D:\NDVI_NetCDF`, `D:\CHIRPS`, `D:\ERA5` `{name}_{year}.nc` (18,904 × 9,068 px, 12 months each) | **not found** (no code writes these paths; Phase 1 nb cell 140 writes `{dataset}_monthly_{year}.nc` in a different folder) | not found |
| `D:\ERA5-11\*.nc` | 7 files | **not found**. Same name and size as `D:\ERA5\*.nc`; values identical on 3 months × 240,000 px of 2018 → **likely a copy** | verified (sample) |
| Merged cube | `D:\COMBINED_DATA\combined_data.zarr` | Phase 2 nb, cell 3 (`xr.merge` of the three NetCDF folders, 2017–2023) | from code |
| Cube + static layers | `D:\COMBINED_DATA\combined_with_static.zarr` | Phase 2 nb, cell 4 (adds clay, silt, sand, ocd, wv0010, dem, slope, aspect; masks `NDVI == -9999`) | from code |
| Clipped cube | `train\clipped_dataset_v5.zarr` (84 × 2,627 × 5,643, 10 m, 2017-01 → 2023-12) | **not found**. `train\train\train.ipynb` refers to it at `C:/Users/AbdellahELBahli/Desktop/project/` — another machine/account | not found |
| FAO-56 ET0 | `train\ERA5_FAO56_ET0_Tadla_2017-2023.tif` (84 bands `et0_YYYY_MM`, 0.1°, EPSG:4326, 7 × 4 px) | **not found** (probably an Earth Engine Code Editor script). `train\verify_pet_file.py` only clips it (`*_clipped.tif`) | not found |
| ET0 into the cube | variable `et0_fao56` | `files\add_et0_to_v5.py` (v5 cube), `files\add_et0_to_zarr.py` (combined_with_static) | from code |
| `ERA5_PET_Tadla_2017-2023.tif` (bands `pet_YYYY_MM`) | — | **not found**; no script found uses it except `verify_pet_file.py` | not found |
| Chapter II climate table | `D:\climat_data\tadla_era5_climate_2017_2023.csv` | `train\Viz\Climat\dw.py` (`ECMWF/ERA5_LAND/MONTHLY_AGGR`) | from code |

Cube values checked on one 2022 window (mm/month): `evaporation` positive, peak in March–April (54–61) and low
in summer (6–11), as stated in CLAUDE.md; `et0_fao56` 2022 sum ≈ 1,162 mm, July 158.7; `rainfall` July 0.0.
`train\outputs_chapter4\et0_sanity_check.json`: summer median 156.9 mm/month.

---

## 3. Which script produced each current result

### Models (LightGBM `.txt`)

| Model file | Features (read from the file) | Produced by | Metrics file |
|---|---|---|---|
| `train\train\ndvi_model_no_2018.txt` | **13: y, x, rainfall, evaporation, clay, silt, sand, dem, ocd, wv0010, month, year, day_of_year** | `train\train\train.ipynb` cells 12–13 (`run_pipeline_exclude_2018`) | none saved |
| `train\ndvi_model_no_year.txt` | 10 (no year/x/y) | `files\retrain_no_year.py` (v5 cube, `spatial_sample=2` → 20 m, 2018 excluded) | `train\retrain_metrics.json` |
| `train\ndvi_model_1km.txt` | 10 | `files\aggregate_1km.py` (1 km means of the pixel table, 80/20 random split) | `train\retrain_1km_metrics.json` |
| `train\ndvi_model_1km_no_2022.txt` | 10 | `files\holdout_2022_1km.py` (train 2017, 2019–2021, 2023; test 2022) | `train\retrain_1km_holdout2022_metrics.json` |

### Metrics (all **verified** against the files)

| CLAUDE.md baseline | File | Exact value |
|---|---|---|
| pixel 20 m R² = 0.42 | `retrain_metrics.json` | test R² 0.4215, RMSE 0.1633 (train 18,000,000 rows / test 25,266,269 rows) |
| 1 km random split R² = 0.90, RMSE 0.045 | `retrain_1km_metrics.json` | test R² 0.8976, RMSE 0.0451 (46,022 / 11,506 rows) |
| 2022 holdout R² = 0.37, RMSE 0.105, bias +0.061 | `retrain_1km_holdout2022_metrics.json` = `outputs_chapter4\validation_2022_1km_summary.json` | R² 0.3671, RMSE 0.1047, MAE 0.0853, bias +0.0610 (9,588 cell-months; 799 cells/month) |
| (not in CLAUDE.md) 2018 at 1 km | `outputs_chapter4\validation_1km_2018_summary.json` ← `files\validate_2018_1km.py` | R² −0.096, RMSE 0.164 (3,758 cell-months) |
| (not in CLAUDE.md) 2018 at 10 m | `outputs_chapter4\validation_2018_summary.json` ← `files\validate_2018.py` | R² −0.131, RMSE 0.246 — **uses the 13-feature model** |
| "R² ≈ 0.99 with `year`" | **no file found** | Only hard-coded in `generer_figures_fr.py:150,177` (Fig. III.3, IV.1). Not traceable to a saved output. |

### Predictions

| File | Produced by | Model used |
|---|---|---|
| `train\train\ndvi_predictions.npy/.nc` (72 months, no 2018) | `train\train\train.ipynb` | 13-feature model; `reinfer_all.py` docstring says it had inference bugs |
| `train\ndvi_predictions_2018.npy`, `ndvi_predictions_full.npy` | `files\infer_2018.py` | 13-feature model |
| `train\ndvi_predictions_full_clean.npy` (84 × 2,627 × 5,643) | `files\reinfer_all.py` (last writer, 2026-05-13; `clean_predictions.py` writes the same name earlier) | **13-feature model** — confirmed by `train\inference_log.txt` ("Features (13): ['y','x',…,'year',…]") and by dates (file 05-13, no-year model created 05-26) |
| `train\ndvi_predictions_1km.npy` + `_meta.json`, `outputs_chapter4\ndvi_predictions_1km\*.tif` | `files\infer_1km.py` | `ndvi_model_1km.txt` (10 features), ≥ 100 valid pixels per cell; 779 cells have predictions (the 2022 holdout counts 799 cells/month, from the 20 m training table) |

### SHAP

| Output | Produced by | Model |
|---|---|---|
| `outputs_chapter4\shap\` | `files\run_shap.py` | 13-feature model (the "biased" model of Fig. IV.5) |
| `outputs_chapter4\shap_1km\` | `files\run_shap_1km.py` | `ndvi_model_1km.txt` + `aggregated_1km_data.parquet` |

### Irrigation maps (Kc coefficients are an open point — not reviewed here)

| Output | Produced by | NDVI input |
|---|---|---|
| `outputs_chapter4\irrigation_{duchemin_2006,bausch_neale_1987}\` (10 m) | `files\irrigation_logic.py` | `ndvi_predictions_full_clean.npy` → **13-feature model** |
| `outputs_chapter4\irrigation_1km_{duchemin_2006,bausch_neale_1987}\` | `files\irrigation_logic_1km.py` (ET0 = `et0_fao56`, rainfall from the v5 cube, aggregated to 1 km) | `ndvi_predictions_1km.npy` |
| `outputs_chapter4\et0_sanity_check.json` | `files\irrigation_logic.py` | — |
| `outputs_chapter4\diagnostics_2018\` | `files\diagnose_2018_coverage.py` | — |

### Figures

| Figures | Script | Data source |
|---|---|---|
| `train\figures_fr\` III.1, III.2, III.3, IV.1, IV.4, IV.5, IV.12 | `train\generer_figures_fr.py` | **values hard-coded**. IV.4 matches `shap_1km\feature_importance_1km.json`; IV.12 matches the 1 km `summary_stats_1km.csv` (sum of monthly `mean_IR_FAO56_mm`, ±1 mm rounding); IV.1/III.3 R² values: see the 0.99 caveat |
| `outputs_chapter4\figures_fr\` IV.2, IV.3, IV.6–IV.11, IV.13–IV.15 | `train\generer_figures_donnees_fr.py` | 1 km CSV/JSON, `ndvi_model_1km.txt`, 1 km GeoTIFFs |
| `outputs_chapter4\figures\` (English versions of the same) | `train\Viz\generate_remaining_figures.py` | same |
| `train\Viz\Climat_fr\climate_*` | `train\graphs_climat_fr.py` | `D:\climat_data\…csv` |
| `train\Viz\Climat_fr\rainfall_*` | `train\plot_rainfall_fr.py` | v5 cube `rainfall` |
| `train\Viz\landuse_fr\` | `train\plot_landuse_fr.py` | v5 cube `NDVI` |
| `train\Viz\morphology_fr\` (DEM, slope, aspect, hypsometry) | `train\plot_morphology_fr.py` | v5 cube `dem` (ALOS); slope/aspect recomputed with `np.gradient` |
| `train\Viz\morphology_fr\morpho_drainage_network_fr.png` | `train\plot_drainage_network_fr.py` | `area.shp`, `Desktop\Shapefiles\…` (bassins, oueds) |
| study-area map | `train\study_area_map_fr.py` | output path set in its own config dict |

English versions under `train\Viz\Climat`, `landuse`, `morphology` come from the scripts with the same names
in those folders.

---

## 4. Problems found (to fix in the rebuild and/or mention in the thesis)

1. **The 1 km GeoTIFFs are mirrored north–south (verified).** `files\infer_1km.py:200–205` stores row 0 = the
   *southernmost* cell (cell_y_min = 179 km) but writes the transform with origin y = 180 km and a −1000 m step,
   so rows run southwards. As georeferenced, only 5 of 779 NDVI cells (Jul 2022) and 6 of the IR cells touch
   `area.shp`; flipping the rows puts 779/779 inside. `irrigation_logic_1km.py` reuses the same transform.
   *Affected:* all `outputs_chapter4\ndvi_predictions_1km\*.tif`, `irrigation_1km_*\monthly|seasonal\*.tif`, and
   the map figures **IV.9, IV.10, IV.13, IV.14, IV.15** (French and English), which show the plain upside down
   (checked visually on Fig. IV.13). *Not affected:* metrics, CSV summaries, Fig. IV.11/IV.12 (no maps).
2. **The 10 m irrigation maps, 10 m 2018 validation and 10 m SHAP come from the 13-feature model with `year`, `x`,
   `y`** (see §3). Only the 1 km chain uses the leakage-free model.
3. **Fig. III.1 says "SRTM"; the DEM is ALOS AW3D30** (§1).
4. **"R² ≈ 0.99 with year" has no saved source** (§3). If the thesis keeps this narrative, the rebuild should
   re-measure it once (same features, LOYO and random split) and save it.
5. **1 km random split shares cells and neighbouring months between train and test** — explains part of the gap
   between 0.90 (random) and 0.37 (2022 holdout). The rebuild's leave-one-year-out answers this.
6. **Irrigation maps use model predictions for months that were in the training set** (the 1 km model saw ~80 %
   of 2017–2023 cell-months except 2018). Methodological choice to discuss: observed NDVI where available,
   or out-of-fold (LOYO) predictions.
7. **Both LightGBM runs report `best_iteration = 1000`** (pixel and 1 km): early stopping never triggered, so the
   1000-round cap was binding.
8. **Pixel model split is unusual:** 18,000,000 training rows vs 25,266,269 test rows (`retrain_metrics.json`).
9. **Climate CSV wind speed is a vector mean:** `dw.py` computes √(ū² + v̄²) from *monthly-mean* u, v components
   (e.g. 0.59 m/s in Jan 2017), which underestimates the real mean wind speed. Fix in the Chapter II figures; never
   use it for ET0 (FAO-56 needs the scalar wind speed at 2 m).
10. **Producing code missing** for: monthly Sentinel-2 NDVI, the D:\ NetCDFs, the clip to `clipped_dataset_v5.zarr`,
    the ET0 GeoTIFF. The old ET0 method therefore cannot be audited; the rebuild recomputes ET0 itself.
11. **Static layers broadcast over time:** in `combined_with_static`/v5, `dem` etc. are stored as (y, x, time) after
    `where(NDVI != -9999)`; `slope` is −9999 everywhere in the slice checked (not a model feature; the Chapter II
    slope map recomputes slope from the DEM, so it is not affected).
12. **Phase 1 cell 29** converts clay to % but writes the original array (harmless here, the final cube is in %).
13. **`.env` files** exist in `PFE\` and `train\Viz\Climat\`: never include them in the code archive.
14. **Soil depth is 0–5 cm, not 0–10 cm:** Phase 1 nb cell 23 downloads `<prop>_0-5cm_mean` from the ISRIC WCS
    (SoilGrids has no 0–10 cm layer; its depths are 0–5, 5–15, 15–30 … cm). The same cell comments `wv0010` as
    "water content at saturation"; per ISRIC it is the **volumetric water content at 10 kPa** suction.
15. **`ocd` in the old cube is 10× too small:** median 2.76 in `clipped_dataset_v5.zarr`, while SoilGrids `ocd`
    0–5 cm over the area has median 272 hg/m³ = 27.2 kg/m³ (checked 2026-11-06). clay (29.4 vs 30.3 %) and
    wv0010 (34.4 vs 34.7 %) agree, so `ocd` was probably divided by 10 twice. Harmless for LightGBM (monotonic
    rescaling), but any `ocd` value or axis quoted in the thesis (e.g. SHAP dependence plots) is wrong by 10×.
16. **The old "FAO-56 ET0" is not a reference ET0 (reconstructed, 2026-11-06):** recomputing 2022 at cell
    X380_Y190 with the speed of the daily-mean wind vector and ERA5-Land's surface net radiation reproduces
    `ERA5_FAO56_ET0_Tadla_2017-2023.tif` within 0.5–2.5 % every month (1132 vs 1149 mm; r = 0.9999). Standard FAO-56
    (scalar wind, reference-grass Rn) gives 1532 mm there. The "≈ 1150 mm/yr, July ≈ 165 mm" of CLAUDE.md comes from
    this file. See decisions.md D7. The old irrigation requirements (IR = Kc·ET0 − P) inherit the lower ET0.
