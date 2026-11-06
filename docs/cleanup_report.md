# Clean-up report — old project material (Phase 0)

Generated 2026-11-06 14:34 by `scripts/00_inventory.py`. **Read-only:** only file metadata was read (no file content, so OneDrive online-only files were not downloaded). Nothing was moved or deleted.

- Sizes are logical sizes in **GB = 10⁹ bytes** (Windows Explorer shows GiB: multiply by 0.931).
- A Zarr store, a `.git` folder or a cache folder is counted as **one item** (its file count is shown).
- Full per-file listing: `outputs/00_inventory/inventory_full.csv` (git-ignored).
- Content-level checks (what produced what, verified duplicates, bugs found) are in [old_code_notes.md](old_code_notes.md).

**Total scanned: 622.53 GB in 31,823 files** (1,317 items after grouping).

## Categories

| Cat. | Meaning | When it can go |
|---|---|---|
| **A** | Re-downloadable raw data (CHIRPS, ERA5, NDVI NetCDF, GEE GeoTIFFs), caches and junk | once the new pipeline's data are exported and checked |
| **B** | Derived intermediates that back the current report (Zarr cubes, `.npy` predictions, training `.parquet`, backups, output rasters) | once the new results are validated |
| **C** | Keep: shapefiles, code & notebooks, figures, metrics `.json/.csv`, model `.txt`, derived tables < 10 MB | keep (archive old code into one zip) |

Classification is rule-based (`src/tadla/inventory.py::classify`); the reason for each item is given in the tables. You decide what is deleted; when cleaning, items are first moved to a `_to_delete` folder.

## Summary per folder

| Folder | Items | Files | Total GB | A GB | B GB | C GB | In OneDrive |
|---|---:|---:|---:|---:|---:|---:|:---:|
| `C:\Users\abdel\OneDrive\Desktop\train` | 1,177 | 13,394 | 18.45 | 0.12 | 18.24 | 0.10 | yes |
| `C:\Users\abdel\OneDrive\Desktop\PFE_Project` | 93 | 1,162 | 56.04 | 0.12 | 55.92 | 0.01 | yes |
| `D:\CHIRPS` | 7 | 7 | 12.29 | 12.29 | 0.00 | 0.00 | no |
| `D:\climat_data` | 1 | 1 | 0.00 | 0.00 | 0.00 | 0.00 | no |
| `D:\COMBINED_DATA` | 4 | 17,224 | 376.52 | 0.00 | 376.52 | 0.00 | no |
| `D:\ERA5` | 21 | 21 | 112.81 | 112.81 | 0.00 | 0.00 | no |
| `D:\ERA5-11` | 7 | 7 | 3.97 | 3.97 | 0.00 | 0.00 | no |
| `D:\NDVI_NetCDF` | 7 | 7 | 42.44 | 42.44 | 0.00 | 0.00 | no |
| **Total** | 1,317 | 31,823 | **622.53** | 171.75 | 450.67 | 0.10 | |

## The 30 largest items

| # | Size GB | Modified | Type | Cat. | Path | Reason |
|---:|---:|---|---|:---:|---|---|
| 1 | 143.30 | 2025-06-29 | .nc | **B** | `D:\COMBINED_DATA\combined_data.nc` | merged cube built from the D:\ NetCDFs (derived intermediate) |
| 2 | 83.71 | 2026-05-10 | zarr store (13,221 files) | **B** | `D:\COMBINED_DATA\combined_with_static.zarr` | Zarr cube (derived intermediate) |
| 3 | 79.59 | 2025-07-05 | .zip | **B** | `D:\COMBINED_DATA\combined_with_static.zarr.zip` | zipped copy of a Zarr cube |
| 4 | 69.91 | 2025-06-29 | zarr store (4,001 files) | **B** | `D:\COMBINED_DATA\combined_data.zarr` | Zarr cube (derived intermediate) |
| 5 | 8.23 | 2025-06-14 | .tif | **A** | `D:\ERA5\ERA5_2018_with_time.tif` | raw data exported from GEE and resampled; reproducible by the new pipeline |
| 6 | 8.23 | 2025-06-14 | .tif | **A** | `D:\ERA5\ERA5_2019_with_time.tif` | raw data exported from GEE and resampled; reproducible by the new pipeline |
| 7 | 8.23 | 2025-06-14 | .tif | **A** | `D:\ERA5\ERA5_2020_with_time.tif` | raw data exported from GEE and resampled; reproducible by the new pipeline |
| 8 | 8.23 | 2025-06-15 | .tif | **A** | `D:\ERA5\ERA5_2021_with_time.tif` | raw data exported from GEE and resampled; reproducible by the new pipeline |
| 9 | 8.23 | 2025-06-15 | .tif | **A** | `D:\ERA5\ERA5_2022_with_time.tif` | raw data exported from GEE and resampled; reproducible by the new pipeline |
| 10 | 8.23 | 2025-06-15 | .tif | **A** | `D:\ERA5\ERA5_2023_with_time.tif` | raw data exported from GEE and resampled; reproducible by the new pipeline |
| 11 | 8.23 | 2025-06-15 | .tif | **A** | `D:\ERA5\ERA5_2017_with_time.tif` | raw data exported from GEE and resampled; reproducible by the new pipeline |
| 12 | 8.23 | 2025-05-01 | .tif | **B** | `C:\Users\abdel\OneDrive\Desktop\PFE_Project\Data\Processed\Weather\ERA5_Annual\ERA5_2017_corrected.tif` | processed (reprojected / resampled) intermediate of the old pipeline |
| 13 | 8.23 | 2025-05-03 | .tif | **A** | `D:\ERA5\ERA5_2018_reproj.tif` | raw data exported from GEE and resampled; reproducible by the new pipeline |
| 14 | 8.23 | 2025-05-03 | .tif | **A** | `D:\ERA5\ERA5_2019_reproj.tif` | raw data exported from GEE and resampled; reproducible by the new pipeline |
| 15 | 8.23 | 2025-05-03 | .tif | **A** | `D:\ERA5\ERA5_2020_reproj.tif` | raw data exported from GEE and resampled; reproducible by the new pipeline |
| 16 | 8.23 | 2025-05-03 | .tif | **A** | `D:\ERA5\ERA5_2021_reproj.tif` | raw data exported from GEE and resampled; reproducible by the new pipeline |
| 17 | 8.23 | 2025-05-03 | .tif | **A** | `D:\ERA5\ERA5_2022_reproj.tif` | raw data exported from GEE and resampled; reproducible by the new pipeline |
| 18 | 8.23 | 2025-05-03 | .tif | **A** | `D:\ERA5\ERA5_2023_reproj.tif` | raw data exported from GEE and resampled; reproducible by the new pipeline |
| 19 | 6.41 | 2025-06-16 | .nc | **A** | `D:\NDVI_NetCDF\NDVI_2021.nc` | raw data exported from GEE and resampled; reproducible by the new pipeline |
| 20 | 6.39 | 2025-06-16 | .nc | **A** | `D:\NDVI_NetCDF\NDVI_2020.nc` | raw data exported from GEE and resampled; reproducible by the new pipeline |
| 21 | 6.38 | 2025-06-16 | .nc | **A** | `D:\NDVI_NetCDF\NDVI_2017.nc` | raw data exported from GEE and resampled; reproducible by the new pipeline |
| 22 | 6.38 | 2025-06-16 | .nc | **A** | `D:\NDVI_NetCDF\NDVI_2019.nc` | raw data exported from GEE and resampled; reproducible by the new pipeline |
| 23 | 6.37 | 2025-06-16 | .nc | **A** | `D:\NDVI_NetCDF\NDVI_2022.nc` | raw data exported from GEE and resampled; reproducible by the new pipeline |
| 24 | 6.36 | 2025-06-16 | .nc | **A** | `D:\NDVI_NetCDF\NDVI_2023.nc` | raw data exported from GEE and resampled; reproducible by the new pipeline |
| 25 | 6.15 | 2026-05-10 | zarr store (12,164 files) | **B** | `C:\Users\abdel\OneDrive\Desktop\train\clipped_dataset_v5.zarr` | Zarr cube (derived intermediate) |
| 26 | 4.16 | 2025-06-16 | .nc | **A** | `D:\NDVI_NetCDF\NDVI_2018.nc` | raw data exported from GEE and resampled; reproducible by the new pipeline |
| 27 | 3.09 | 2025-09-08 | .zip | **B** | `C:\Users\abdel\OneDrive\Desktop\train\clipped_dataset_v5.zarr.zip` | zipped copy of a Zarr cube |
| 28 | 1.99 | 2025-03-10 | .tif | **B** | `C:\Users\abdel\OneDrive\Desktop\PFE_Project\Data\Processed\Weather\ERA5_Annual\ERA5_2020_reproj.tif` | processed (reprojected / resampled) intermediate of the old pipeline |
| 29 | 1.99 | 2025-03-10 | .tif | **B** | `C:\Users\abdel\OneDrive\Desktop\PFE_Project\Data\Processed\Weather\ERA5_Annual\ERA5_2019_reproj.tif` | processed (reprojected / resampled) intermediate of the old pipeline |
| 30 | 1.99 | 2025-03-10 | .tif | **B** | `C:\Users\abdel\OneDrive\Desktop\PFE_Project\Data\Processed\Weather\CHIRPS_Annual\CHIRPS_2020_reproj.tif` | processed (reprojected / resampled) intermediate of the old pipeline |

## Detail per folder

One row per directory (items directly inside it). Categories are split when mixed.

### `C:\Users\abdel\OneDrive\Desktop\train`

| Directory | Items | Size GB | Types | Last modified | Category (GB) | Main reason |
|---|---:|---:|---|---|---|---|
| `.` | 33 | 13.70 | .py×10, .tif×4, .txt×4, .npy×4 | 2026-07-28 | A: 0.00 / B: 13.69 / C: 0.01 | Zarr cube (derived intermediate) |
| `Viz` | 4 | 0.06 | .py×2, cache (28 files), .png | 2026-06-13 | A: 0.06 / C: 0.00 | cache, regenerated or re-downloaded automatically |
| `Viz/Climat` | 13 | 0.00 | .png×9, .py×3, (none) | 2026-04-01 | C: 0.00 | figure / image |
| `Viz/Climat_fr` | 8 | 0.00 | .png×8 | 2026-07-28 | C: 0.00 | figure / image |
| `Viz/landuse` | 11 | 0.01 | .svg×6, .png×2, .jpg×2, .py | 2026-04-07 | C: 0.01 | figure / image |
| `Viz/landuse_fr` | 2 | 0.01 | .png×2 | 2026-07-28 | C: 0.01 | figure / image |
| `Viz/morphology` | 9 | 0.01 | .png×7, .py×2 | 2026-04-05 | C: 0.01 | figure / image |
| `Viz/morphology_fr` | 7 | 0.01 | .png×7 | 2026-07-28 | C: 0.01 | figure / image |
| `figures_fr` | 7 | 0.00 | .png×7 | 2026-07-27 | C: 0.00 | figure / image |
| `files` | 28 | 0.00 | .py×28 | 2026-05-30 | C: 0.00 | code or notebook (archive into one zip) |
| `outputs_chapter4` | 7 | 0.00 | .json×4, .csv×3 | 2026-05-30 | C: 0.00 | small metrics / table / text file |
| `outputs_chapter4/diagnostics_2018` | 6 | 0.00 | .png×4, .csv×2 | 2026-05-29 | C: 0.00 | figure / image |
| `outputs_chapter4/figures` | 18 | 0.00 | .png×18 | 2026-06-13 | C: 0.00 | figure / image |
| `outputs_chapter4/figures_fr` | 11 | 0.00 | .png×11 | 2026-07-27 | C: 0.00 | figure / image |
| `outputs_chapter4/irrigation_1km_bausch_neale_1987` | 2 | 0.00 | .json, .csv | 2026-05-30 | C: 0.00 | small metrics / table / text file |
| `outputs_chapter4/irrigation_1km_bausch_neale_1987/monthly` | 168 | 0.00 | .tif×168 | 2026-05-30 | B: 0.00 | derived output raster (regenerated by the new pipeline) |
| `outputs_chapter4/irrigation_1km_bausch_neale_1987/seasonal` | 5 | 0.00 | .tif×5 | 2026-05-30 | B: 0.00 | derived output raster (regenerated by the new pipeline) |
| `outputs_chapter4/irrigation_1km_duchemin_2006` | 2 | 0.00 | .json, .csv | 2026-05-30 | C: 0.00 | small metrics / table / text file |
| `outputs_chapter4/irrigation_1km_duchemin_2006/monthly` | 168 | 0.00 | .tif×168 | 2026-05-30 | B: 0.00 | derived output raster (regenerated by the new pipeline) |
| `outputs_chapter4/irrigation_1km_duchemin_2006/seasonal` | 5 | 0.00 | .tif×5 | 2026-05-30 | B: 0.00 | derived output raster (regenerated by the new pipeline) |
| `outputs_chapter4/irrigation_bausch_neale_1987` | 2 | 0.00 | .json, .csv | 2026-05-17 | C: 0.00 | small metrics / table / text file |
| `outputs_chapter4/irrigation_bausch_neale_1987/monthly` | 252 | 0.47 | .tif×252 | 2026-05-17 | B: 0.47 | derived output raster (regenerated by the new pipeline) |
| `outputs_chapter4/irrigation_bausch_neale_1987/seasonal` | 9 | 0.04 | .tif×9 | 2026-05-17 | B: 0.04 | derived output raster (regenerated by the new pipeline) |
| `outputs_chapter4/irrigation_duchemin_2006` | 2 | 0.00 | .json, .csv | 2026-05-17 | C: 0.00 | small metrics / table / text file |
| `outputs_chapter4/irrigation_duchemin_2006/monthly` | 252 | 0.40 | .tif×252 | 2026-05-17 | B: 0.40 | derived output raster (regenerated by the new pipeline) |
| `outputs_chapter4/irrigation_duchemin_2006/seasonal` | 9 | 0.04 | .tif×9 | 2026-05-17 | B: 0.04 | derived output raster (regenerated by the new pipeline) |
| `outputs_chapter4/ndvi_predictions_1km` | 84 | 0.00 | .tif×84 | 2026-05-30 | B: 0.00 | derived output raster (regenerated by the new pipeline) |
| `outputs_chapter4/shap` | 11 | 0.04 | .png×5, .tif×4, .json, .parquet | 2026-05-24 | B: 0.04 / C: 0.00 | derived intermediate (prediction array / training table / cube) |
| `outputs_chapter4/shap_1km` | 8 | 0.00 | .png×6, .json×2 | 2026-05-30 | C: 0.00 | figure / image |
| `train` | 19 | 2.22 | .png×7, (none)×5, .ipynb×2, cache (28 files) | 2026-03-30 | A: 0.06 / B: 2.14 / C: 0.02 | derived intermediate (prediction array / training table / cube) |
| `train/thematic_maps` | 4 | 0.18 | .png×2, .npy, .ipynb | 2026-03-30 | B: 0.18 / C: 0.00 | derived intermediate (prediction array / training table / cube) |
| `train/thematic_maps/annual_maps` | 7 | 0.01 | .png×7 | 2025-11-15 | C: 0.01 | figure / image |
| `train/thematic_maps/results` | 3 | 1.25 | .txt, .csv, .nc | 2025-11-15 | B: 1.25 / C: 0.00 | derived intermediate (prediction array / training table / cube) |
| `train/thematic_maps/time_series` | 1 | 0.00 | .png | 2025-11-15 | C: 0.00 | figure / image |

### `C:\Users\abdel\OneDrive\Desktop\PFE_Project`

| Directory | Items | Size GB | Types | Last modified | Category (GB) | Main reason |
|---|---:|---:|---|---|---|---|
| `.` | 7 | 0.00 | (none)×3, .yml×2, git repository (1,070 files), .md | 2026-03-30 | C: 0.00 | version history of the old code |
| `Data` | 1 | 0.04 | .whl | 2025-02-11 | A: 0.04 | Python wheel, re-downloadable |
| `Data/Processed/GIS` | 1 | 0.00 | .tif | 2025-02-09 | B: 0.00 | processed (reprojected / resampled) intermediate of the old pipeline |
| `Data/Processed/GIS/Soil` | 12 | 4.32 | .tif×12 | 2025-03-09 | B: 4.32 | processed (reprojected / resampled) intermediate of the old pipeline |
| `Data/Processed/GIS/Study_Area_Boundary` | 24 | 14.40 | .nc×14, .cpg×2, .dbf×2, .prj×2 | 2025-02-28 | B: 14.40 / C: 0.00 | processed (reprojected / resampled) intermediate of the old pipeline |
| `Data/Processed/GIS/Topography` | 3 | 2.06 | .tif×3 | 2025-03-06 | B: 2.06 | processed (reprojected / resampled) intermediate of the old pipeline |
| `Data/Processed/Weather` | 1 | 0.37 | .tif | 2025-02-25 | B: 0.37 | processed (reprojected / resampled) intermediate of the old pipeline |
| `Data/Processed/Weather/CHIRPS_Annual` | 7 | 12.85 | .tif×7 | 2025-03-10 | B: 12.85 | processed (reprojected / resampled) intermediate of the old pipeline |
| `Data/Processed/Weather/ERA5_Annual` | 8 | 21.92 | .tif×8 | 2025-05-01 | B: 21.92 | processed (reprojected / resampled) intermediate of the old pipeline |
| `Data/Raw/GIS/Soil` | 5 | 0.00 | .tif×5 | 2025-03-06 | A: 0.00 | raw GEE export |
| `Data/Raw/GIS/Soil/tadla_wcs.tif` | 5 | 0.00 | .cpg, .dbf, .prj, .shp | 2025-02-12 | C: 0.00 | vector / shapefile component |
| `Data/Raw/GIS/Study_Area_Boundary` | 1 | 0.00 | .zip | 2025-02-08 | C: 0.00 | small archive in Data/Raw (content not inspected; likely boundary data) |
| `Data/Raw/GIS/Study_Area_Boundary/Tadla_plain` | 5 | 0.00 | .cpg, .dbf, .prj, .shp | 2025-02-08 | C: 0.00 | vector / shapefile component |
| `Data/Raw/GIS/Study_Area_Boundary/Tadla_plain_boundary` | 5 | 0.00 | .cpg, .dbf, .prj, .shp | 2025-02-09 | C: 0.00 | vector / shapefile component |
| `Data/Raw/GIS/Topography` | 2 | 0.07 | .tif×2 | 2025-02-10 | A: 0.07 | raw GEE export |
| `Data/Raw/Weather` | 2 | 0.01 | .tif×2 | 2025-02-25 | A: 0.01 | raw GEE export |
| `Scripts` | 1 | 0.00 | .ipynb | 2026-04-23 | C: 0.00 | code or notebook (archive into one zip) |
| `Scripts/Phase1_Data_Preprocessing` | 3 | 0.00 | .ipynb×2, .tif | 2025-07-13 | C: 0.00 | code or notebook (archive into one zip) |

### `D:\CHIRPS`

| Directory | Items | Size GB | Types | Last modified | Category (GB) | Main reason |
|---|---:|---:|---|---|---|---|
| `.` | 7 | 12.29 | .nc×7 | 2025-06-15 | A: 12.29 | raw data exported from GEE and resampled; reproducible by the new pipeline |

### `D:\climat_data`

| Directory | Items | Size GB | Types | Last modified | Category (GB) | Main reason |
|---|---:|---:|---|---|---|---|
| `.` | 1 | 0.00 | .csv | 2026-03-30 | C: 0.00 | small metrics / table / text file |

### `D:\COMBINED_DATA`

| Directory | Items | Size GB | Types | Last modified | Category (GB) | Main reason |
|---|---:|---:|---|---|---|---|
| `.` | 4 | 376.52 | .nc, zarr store (4,001 files), zarr store (13,221 files), .zip | 2026-05-10 | B: 376.52 | merged cube built from the D:\ NetCDFs (derived intermediate) |

### `D:\ERA5`

| Directory | Items | Size GB | Types | Last modified | Category (GB) | Main reason |
|---|---:|---:|---|---|---|---|
| `.` | 21 | 112.81 | .tif×14, .nc×7 | 2025-06-15 | A: 112.81 | raw data exported from GEE and resampled; reproducible by the new pipeline |

### `D:\ERA5-11`

| Directory | Items | Size GB | Types | Last modified | Category (GB) | Main reason |
|---|---:|---:|---|---|---|---|
| `.` | 7 | 3.97 | .nc×7 | 2025-06-15 | A: 3.97 | raw data exported from GEE and resampled; reproducible by the new pipeline |

### `D:\NDVI_NetCDF`

| Directory | Items | Size GB | Types | Last modified | Category (GB) | Main reason |
|---|---:|---:|---|---|---|---|
| `.` | 7 | 42.44 | .nc×7 | 2025-06-16 | A: 42.44 | raw data exported from GEE and resampled; reproducible by the new pipeline |

## Duplicates (same name and same size)

102 groups; 4.03 GB would be freed by keeping one copy of each. Same name + size is a strong hint, not a proof (content was not compared). Groups that share the same set of folders are collapsed into one row.

| Name(s) | Size GB (one copy) | Copies | Folders |
|---|---:|---:|---|
| 7 files, e.g. `ERA5_2017.nc`, `ERA5_2021.nc` | 3.97 | 2 | `D:\ERA5`<br>`D:\ERA5-11` (A) |
| `.ne_cache` | 0.06 | 2 | `C:\Users\abdel\OneDrive\Desktop\train\Viz`<br>`C:\Users\abdel\OneDrive\Desktop\train\train` (A) |
| 2 files, e.g. `months_needs_irrigation.tif`, `months_stressed_in_deficit.tif` | 0.00 | 2 | `C:\Users\abdel\OneDrive\Desktop\train\outputs_chapter4\irrigation_bausch_neale_1987\seasonal`<br>`C:\Users\abdel\OneDrive\Desktop\train\outputs_chapter4\irrigation_duchemin_2006\seasonal` (B) |
| 54 files, e.g. `IR_FAO56_2017-02.tif`, `IR_FAO56_2017-12.tif` | 0.00 | 2 | `C:\Users\abdel\OneDrive\Desktop\train\outputs_chapter4\irrigation_bausch_neale_1987\monthly`<br>`C:\Users\abdel\OneDrive\Desktop\train\outputs_chapter4\irrigation_duchemin_2006\monthly` (B) |
| 37 files, e.g. `IR_FAO56_2018-01.tif`, `IR_FAO56_2017-02.tif` | 0.00 | 2 | `C:\Users\abdel\OneDrive\Desktop\train\outputs_chapter4\irrigation_1km_bausch_neale_1987\monthly`<br>`C:\Users\abdel\OneDrive\Desktop\train\outputs_chapter4\irrigation_1km_duchemin_2006\monthly` (B) |
| `months_stressed_in_deficit.tif` | 0.00 | 2 | `C:\Users\abdel\OneDrive\Desktop\train\outputs_chapter4\irrigation_1km_bausch_neale_1987\seasonal`<br>`C:\Users\abdel\OneDrive\Desktop\train\outputs_chapter4\irrigation_1km_duchemin_2006\seasonal` (B) |

### Same name, different size, different folders (≥ 0.1 GB) — possible duplicates

| Name | Locations (size GB) |
|---|---|
| `ERA5_2018_reproj.tif` | `C:\Users\abdel\OneDrive\Desktop\PFE_Project\Data\Processed\Weather\ERA5_Annual\ERA5_2018_reproj.tif` (1.89)<br>`D:\ERA5\ERA5_2018_reproj.tif` (8.23) |
| `ERA5_2019_reproj.tif` | `C:\Users\abdel\OneDrive\Desktop\PFE_Project\Data\Processed\Weather\ERA5_Annual\ERA5_2019_reproj.tif` (1.99)<br>`D:\ERA5\ERA5_2019_reproj.tif` (8.23) |
| `ERA5_2020_reproj.tif` | `C:\Users\abdel\OneDrive\Desktop\PFE_Project\Data\Processed\Weather\ERA5_Annual\ERA5_2020_reproj.tif` (1.99)<br>`D:\ERA5\ERA5_2020_reproj.tif` (8.23) |
| `ERA5_2021_reproj.tif` | `C:\Users\abdel\OneDrive\Desktop\PFE_Project\Data\Processed\Weather\ERA5_Annual\ERA5_2021_reproj.tif` (1.98)<br>`D:\ERA5\ERA5_2021_reproj.tif` (8.23) |
| `ERA5_2022_reproj.tif` | `C:\Users\abdel\OneDrive\Desktop\PFE_Project\Data\Processed\Weather\ERA5_Annual\ERA5_2022_reproj.tif` (1.95)<br>`D:\ERA5\ERA5_2022_reproj.tif` (8.23) |
| `ERA5_2023_reproj.tif` | `C:\Users\abdel\OneDrive\Desktop\PFE_Project\Data\Processed\Weather\ERA5_Annual\ERA5_2023_reproj.tif` (1.95)<br>`D:\ERA5\ERA5_2023_reproj.tif` (8.23) |
| `ERA5_2017_reproj.tif` | `C:\Users\abdel\OneDrive\Desktop\PFE_Project\Data\Processed\Weather\ERA5_Annual\ERA5_2017_reproj.tif` (1.94)<br>`D:\ERA5\ERA5_2017_reproj.tif` (1.87) |

## OneDrive-synced heavy items (≥ 0.1 GB)

Everything under a OneDrive folder is synced to the cloud and counts against the OneDrive quota unless it is excluded from sync. **74.49 GB** of the scanned material is inside OneDrive; 51 items are ≥ 0.1 GB (73.09 GB). Items whose content is online-only (not on this disk): 0.

| Size GB | Cat. | Path |
|---:|:---:|---|
| 8.23 | B | `C:\Users\abdel\OneDrive\Desktop\PFE_Project\Data\Processed\Weather\ERA5_Annual\ERA5_2017_corrected.tif` |
| 6.15 | B | `C:\Users\abdel\OneDrive\Desktop\train\clipped_dataset_v5.zarr` |
| 3.09 | B | `C:\Users\abdel\OneDrive\Desktop\train\clipped_dataset_v5.zarr.zip` |
| 1.99 | B | `C:\Users\abdel\OneDrive\Desktop\PFE_Project\Data\Processed\Weather\ERA5_Annual\ERA5_2020_reproj.tif` |
| 1.99 | B | `C:\Users\abdel\OneDrive\Desktop\PFE_Project\Data\Processed\Weather\ERA5_Annual\ERA5_2019_reproj.tif` |
| 1.99 | B | `C:\Users\abdel\OneDrive\Desktop\PFE_Project\Data\Processed\Weather\CHIRPS_Annual\CHIRPS_2020_reproj.tif` |
| 1.98 | B | `C:\Users\abdel\OneDrive\Desktop\PFE_Project\Data\Processed\Weather\ERA5_Annual\ERA5_2021_reproj.tif` |
| 1.95 | B | `C:\Users\abdel\OneDrive\Desktop\PFE_Project\Data\Processed\Weather\ERA5_Annual\ERA5_2023_reproj.tif` |
| 1.95 | B | `C:\Users\abdel\OneDrive\Desktop\PFE_Project\Data\Processed\Weather\ERA5_Annual\ERA5_2022_reproj.tif` |
| 1.94 | B | `C:\Users\abdel\OneDrive\Desktop\PFE_Project\Data\Processed\Weather\ERA5_Annual\ERA5_2017_reproj.tif` |
| 1.90 | B | `C:\Users\abdel\OneDrive\Desktop\PFE_Project\Data\Processed\Weather\CHIRPS_Annual\CHIRPS_2019_reproj.tif` |
| 1.89 | B | `C:\Users\abdel\OneDrive\Desktop\PFE_Project\Data\Processed\Weather\ERA5_Annual\ERA5_2018_reproj.tif` |
| 1.87 | B | `C:\Users\abdel\OneDrive\Desktop\PFE_Project\Data\Processed\Weather\CHIRPS_Annual\CHIRPS_2022_reproj.tif` |
| 1.83 | B | `C:\Users\abdel\OneDrive\Desktop\PFE_Project\Data\Processed\Weather\CHIRPS_Annual\CHIRPS_2023_reproj.tif` |
| 1.82 | B | `C:\Users\abdel\OneDrive\Desktop\PFE_Project\Data\Processed\Weather\CHIRPS_Annual\CHIRPS_2017_reproj.tif` |
| 1.78 | B | `C:\Users\abdel\OneDrive\Desktop\train\retrain_prepared_data.parquet` |
| 1.77 | B | `C:\Users\abdel\OneDrive\Desktop\PFE_Project\Data\Processed\Weather\CHIRPS_Annual\CHIRPS_2018_reproj.tif` |
| 1.66 | B | `C:\Users\abdel\OneDrive\Desktop\PFE_Project\Data\Processed\Weather\CHIRPS_Annual\CHIRPS_2021_reproj.tif` |
| 1.37 | B | `C:\Users\abdel\OneDrive\Desktop\PFE_Project\Data\Processed\GIS\Study_Area_Boundary\ERA5_monthly_2017.nc` |
| 1.37 | B | `C:\Users\abdel\OneDrive\Desktop\PFE_Project\Data\Processed\GIS\Study_Area_Boundary\ERA5_monthly_2018.nc` |
| 1.37 | B | `C:\Users\abdel\OneDrive\Desktop\PFE_Project\Data\Processed\GIS\Study_Area_Boundary\ERA5_monthly_2019.nc` |
| 1.37 | B | `C:\Users\abdel\OneDrive\Desktop\PFE_Project\Data\Processed\GIS\Study_Area_Boundary\ERA5_monthly_2020.nc` |
| 1.37 | B | `C:\Users\abdel\OneDrive\Desktop\PFE_Project\Data\Processed\GIS\Study_Area_Boundary\ERA5_monthly_2021.nc` |
| 1.37 | B | `C:\Users\abdel\OneDrive\Desktop\PFE_Project\Data\Processed\GIS\Study_Area_Boundary\ERA5_monthly_2022.nc` |
| 1.37 | B | `C:\Users\abdel\OneDrive\Desktop\PFE_Project\Data\Processed\GIS\Study_Area_Boundary\ERA5_monthly_2023.nc` |
| 1.25 | B | `C:\Users\abdel\OneDrive\Desktop\train\train\thematic_maps\results\complete_ndvi_predictions.nc` |
| 1.25 | B | `C:\Users\abdel\OneDrive\Desktop\train\ndvi_predictions_full.npy` |
| 1.25 | B | `C:\Users\abdel\OneDrive\Desktop\train\ndvi_predictions_full_clean.npy` |
| 1.07 | B | `C:\Users\abdel\OneDrive\Desktop\train\train\ndvi_predictions.nc` |
| 1.07 | B | `C:\Users\abdel\OneDrive\Desktop\train\train\ndvi_predictions.npy` |
| 0.69 | B | `C:\Users\abdel\OneDrive\Desktop\PFE_Project\Data\Processed\GIS\Study_Area_Boundary\CHIRPS_monthly_2017.nc` |
| 0.69 | B | `C:\Users\abdel\OneDrive\Desktop\PFE_Project\Data\Processed\GIS\Study_Area_Boundary\CHIRPS_monthly_2018.nc` |
| 0.69 | B | `C:\Users\abdel\OneDrive\Desktop\PFE_Project\Data\Processed\GIS\Study_Area_Boundary\CHIRPS_monthly_2019.nc` |
| 0.69 | B | `C:\Users\abdel\OneDrive\Desktop\PFE_Project\Data\Processed\GIS\Study_Area_Boundary\CHIRPS_monthly_2020.nc` |
| 0.69 | B | `C:\Users\abdel\OneDrive\Desktop\PFE_Project\Data\Processed\GIS\Study_Area_Boundary\CHIRPS_monthly_2021.nc` |
| 0.69 | B | `C:\Users\abdel\OneDrive\Desktop\PFE_Project\Data\Processed\GIS\Study_Area_Boundary\CHIRPS_monthly_2022.nc` |
| 0.69 | B | `C:\Users\abdel\OneDrive\Desktop\PFE_Project\Data\Processed\GIS\Study_Area_Boundary\CHIRPS_monthly_2023.nc` |
| 0.69 | B | `C:\Users\abdel\OneDrive\Desktop\PFE_Project\Data\Processed\GIS\Topography\tadla_dem_10m.tif` |
| 0.69 | B | `C:\Users\abdel\OneDrive\Desktop\PFE_Project\Data\Processed\GIS\Topography\tadla_aspect.tif` |
| 0.69 | B | `C:\Users\abdel\OneDrive\Desktop\PFE_Project\Data\Processed\GIS\Topography\tadla_slope.tif` |
| 0.69 | B | `C:\Users\abdel\OneDrive\Desktop\PFE_Project\Data\Processed\GIS\Soil\total_texture_masked.tif` |
| 0.62 | B | `C:\Users\abdel\OneDrive\Desktop\PFE_Project\Data\Processed\GIS\Soil\tadla_clay_10m.tif` |
| 0.62 | B | `C:\Users\abdel\OneDrive\Desktop\PFE_Project\Data\Processed\GIS\Soil\tadla_clay_processed.tif` |
| 0.61 | B | `C:\Users\abdel\OneDrive\Desktop\PFE_Project\Data\Processed\GIS\Soil\tadla_clay_10m_p.tif` |
| 0.55 | B | `C:\Users\abdel\OneDrive\Desktop\PFE_Project\Data\Processed\GIS\Soil\tadla_wv0010_10m.tif` |
| 0.45 | B | `C:\Users\abdel\OneDrive\Desktop\PFE_Project\Data\Processed\GIS\Soil\tadla_wv0010_processed.tif` |
| 0.37 | B | `C:\Users\abdel\OneDrive\Desktop\PFE_Project\Data\Processed\Weather\CHIRPS_2017_01.tif` |
| 0.35 | B | `C:\Users\abdel\OneDrive\Desktop\PFE_Project\Data\Processed\GIS\Soil\tadla_ocd_10m.tif` |
| 0.35 | B | `C:\Users\abdel\OneDrive\Desktop\PFE_Project\Data\Processed\GIS\Soil\tadla_ocd_processed.tif` |
| 0.18 | B | `C:\Users\abdel\OneDrive\Desktop\train\ndvi_predictions_2018.npy` |
| 0.18 | B | `C:\Users\abdel\OneDrive\Desktop\train\train\thematic_maps\2018_predictions.npy` |

## Flags

- `C:\Users\abdel\OneDrive\Desktop\train\Viz\Climat\.env` — may contain credentials: never copy into a public repo or archive
- `C:\Users\abdel\OneDrive\Desktop\PFE_Project\.env` — may contain credentials: never copy into a public repo or archive

## Total per category

| Category | Items | GB |
|---|---:|---:|
| A — re-downloadable raw data / junk | 61 | **171.75** |
| B — derived intermediates (delete after validation) | 1,018 | **450.67** |
| C — keep | 238 | **0.10** |
| **All** | 1,317 | **622.53** |
