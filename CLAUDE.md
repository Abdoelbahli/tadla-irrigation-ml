# tadla-irrigation-ml — project brief for Claude Code

Master's thesis (PFE), Faculté des Sciences Béni Mellal. Author: Abdellah EL BAHLI. Supervisor: Pr. B. EL MANSOURI.
Goal: predict monthly NDVI over the irrigated Tadla plain (Morocco) with LightGBM, then derive FAO-56 net irrigation
requirement maps. **Scientific accuracy is the top priority**: never invent numbers, sources or results; if something is
uncertain, say so and check it.

## Why this rebuild
The old work is spread across 30+ scripts (diagnose_*, reinfer_*, add_et0_*, …) on a 10 m cube of ~1.2 billion cells.
Rebuild it as ONE clean, reproducible repo whose numbered steps regenerate every result and figure of the thesis.
The old files stay untouched as the fallback until the new results are validated.

## Established facts (keep consistent)
- Study area: `area.shp` (EPSG:26191, Merchich / Nord Maroc), 701.83 km², extent ≈ 7°00'W–6°24'W, 32°12'N–32°27'N.
- OLD period: 2017-01 → 2023-12 (84 months; the rebuild extends it, see Decisions §0). 2018 has a Sentinel-2 gap (~30 % coverage Jan–Nov, full in Dec) → excluded
  from training, reported separately, never used as a holdout.
- Old final model: LightGBM at 1 km (799 cells), 10 features: rainfall, evaporation, clay, silt, sand, dem, ocd, wv0010,
  month, day_of_year. `year`, `y`, `x` were removed (temporal-leakage diagnosis: with `year`, R² ≈ 0.99 was fake).
- Old results (baseline to compare against): pixel 20 m R² = 0.42; 1 km random split R² = 0.90 (RMSE 0.045);
  2022 temporal holdout R² = 0.37 (RMSE 0.105, bias +0.061).
- `evaporation` in the old model = ERA5-Land `total_evaporation` (ACTUAL ET), |value|×1000, monthly sum of daily values,
  range 1.2–88.6 mm/month, spring peak. It is NOT FAO-56 ET0.
- FAO-56 ET0 (Penman-Monteith, from ERA5-Land base variables): ≈ 1150 mm/yr, July ≈ 165 mm. Used in ETc = Kc·ET0.
- Old LightGBM params: regression/rmse, learning_rate 0.1, num_leaves 31, feature_fraction 0.8, bagging_fraction 0.8,
  bagging_freq 5, min_data_in_leaf 20, 1000 rounds, early stopping 50. CPU only (the Intel UHD GPU cannot run LightGBM's GPU trainer).
- Irrigation: Kc = a·NDVI + b, clip [0, 1.3]; IR = max(0, Kc·ET0 − rainfall); only where NDVI > 0.20.
  Stress mask: NDVI < 0.30 AND ET0 − rainfall > 0.
  Old coefficients: Duchemin 2006 a=1.64, b=−0.14; Bausch & Neale 1987 a=1.25, b=+0.20.

## Open points to resolve (do not silently assume)
1. Duchemin et al. 2006 may define Kcb = 1.64·(NDVI − 0.14) (i.e. b ≈ −0.23). Check the paper before coding the coefficients.
2. Bausch & Neale 1987 is a maize study (Colorado), not "Mediterranean"; check its coefficients.
3. Which DEM feeds `dem`: SRTM 30 m or the ALOS-derived 10 m `tadla_dem_10m.tif`. Pick one and document it.

## Decisions for the rebuild
0. **Period: extend beyond 2017–2023, complete years only (up to Dec 2025).** Check each collection's real end date
   in Earth Engine before fixing the period; never include a partial year.
   **NDVI source (main): NASA HLS v2.0** — `NASA/HLS/HLSS30/v002` (Sentinel-2, from 2015-11-28) +
   `NASA/HLS/HLSL30/v002` (Landsat 8/9, from 2013-04-11), 30 m, harmonised surface reflectance, Fmask cloud/shadow mask.
   Why: the GEE catalog warns that `COPERNICUS/S2_SR_HARMONIZED` "2017–2018 L2 coverage … is not yet global" — the likely
   cause of the old 2018 gap. HLS gives one consistent record → target period 2016–2025 (10 full years, 2018 included).
   30 m is plenty because everything is aggregated to 1 km.
   **Optional long-record experiment:** `MODIS/061/MOD13Q1` NDVI (250 m, 16-day, from 2000) → 2001–2025 at 1 km, to test
   whether 25 years improve temporal generalisation. Report it as a separate, labelled experiment.
   For every month and cell, also export the valid-pixel fraction and the number of clear observations; drop cell-months
   below a documented threshold.
1. Aggregate to the 1 km grid INSIDE Google Earth Engine: per cell & month, mean of valid NDVI pixels
   + valid-pixel fraction; CHIRPS monthly sum; ERA5-Land actual ET and FAO-56 ET0; SoilGrids 0–10 cm
   (clay, silt, sand, ocd, wv0010 → volumetric %); DEM. 799 cells × ~120 months is small: pull results as tables
   (reduceRegions) instead of big raster exports. No 10 m cube.
   Candidate extra predictors (test, keep only if they help LOYO): ERA5-Land soil moisture (`volumetric_soil_water_layer_1/2`),
   2 m air temperature, 3-month cumulative rainfall, lag-1 NDVI, an irrigated/cropland mask (e.g. ESA WorldCover).
   Note in the thesis that ERA5-Land soil moisture does not simulate irrigation.
2. Test BOTH ET inputs as model features: A) actual ET, B) FAO-56 ET0. Report both, keep the better one, explain why.
3. Validation: leave-one-year-out over all complete years of the new period, report mean ± spread and per-year values;
   also the 80/20 random split for comparison with the old 0.90. Never include year/x/y as features.
   Also report results on the OLD period (2017–2023, Sentinel-2-era) so the gain from more years is measurable.
   Chapter II climate figures must be regenerated for the same new period, so the whole thesis uses one period.
4. Optional, clearly labelled experiments: NDVI anomaly target; lag-1 NDVI feature.
5. SHAP (TreeSHAP) on the final model; irrigation maps for both Kc parameterisations; French figures (decimal comma,
   French labels; keep NDVI, LightGBM, SHAP, FAO-56, CHIRPS, ERA5-Land, SoilGrids, SRTM, Sentinel-2 and variable names in English).

## Target structure
```
tadla-irrigation-ml/
  README.md  environment.yml  config.yaml        # ALL paths, years, CRS, params live here
  CLAUDE.md                                      # this file
  src/tadla/
    data/        gee_export.py  build_dataset.py
    model/       train.py  validate.py  explain.py
    irrigation/  fao56.py
    figures/     ch2_fr.py  ch3_fr.py  ch4_fr.py
  scripts/       01_export.py 02_build_dataset.py 03_train.py 04_validate.py
                 05_explain.py 06_predict.py 07_irrigation.py 08_figures.py
  tests/         unit/sanity checks (units, ET0 magnitude, feature list has no year/x/y)
  data/  outputs/                                # git-ignored
```

## Libraries
- Keep: `earthengine-api`, `pandas`, `numpy`, `lightgbm`, `shap`, `scikit-learn` (LeaveOneGroupOut by year), `matplotlib`,
  `geopandas`, `rioxarray`/`rasterio` (only to write the 1 km GeoTIFF maps).
- Add: `optuna` for a small, LOYO-based hyperparameter search (never tune on the test year); `pyyaml` for config; `pytest`.
- Drop: `dask`, `zarr`, `cupy` (the CUDA warnings in every old run come from CuPy) — not needed at 1 km.
- Optional comparison only if time allows: one alternative model (e.g. XGBoost or a simple linear/ridge baseline) to show
  LightGBM's gain is real. Pin all versions in `environment.yml`.

## Phase 0 — inventory and clean-up of old data (do this FIRST, delete NOTHING)
Old material (>100 GB):
- Code/projects: `C:\Users\abdel\OneDrive\Desktop\train`, `C:\Users\abdel\OneDrive\Desktop\PFE_Project`
- Data: `D:\CHIRPS`, `D:\climat_data`, `D:\COMBINED_DATA`, `D:\ERA5`, `D:\ERA5-11`, `D:\NDVI_NetCDF`
Write `scripts/00_inventory.py` that walks these folders and writes `docs/cleanup_report.md` listing, per folder and for
the 30 largest files: size, last-modified date, file type, and a category:
- **A. Re-downloadable raw data** (CHIRPS, ERA5, NDVI NetCDF exports, GEE GeoTIFFs): can be deleted once the new
  pipeline's data are exported and checked.
- **B. Derived intermediates** (Zarr cubes, `.npy` prediction arrays, `retrain_prepared_data.parquet`, backups like
  `*_BACKUP_before_et0`): keep until the new results are validated (they back the current report), then delete.
- **C. Keep** (small, irreplaceable): `area.shp` and other shapefiles, report .docx/.md, figures used in the thesis,
  metrics `.json/.csv`, trained model `.txt` files, notebooks and scripts — archive old code into one zip.
Also flag duplicates (same name + size) and OneDrive-synced heavy files (they also eat cloud quota).
The report must end with the total GB per category. Never delete: the user decides; if asked to clean, move items to a
`_to_delete` folder first.

## Working rules
- Ask before deleting or overwriting anything in the old project folders.
- Each step reads config.yaml, writes to outputs/<step>/, logs what it did, and can be re-run on its own.
- Keep a `docs/results.md` updated with every metric produced (this feeds the thesis text).
- Commit in small steps with clear messages.
