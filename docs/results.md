# Results log

Every metric produced by the pipeline is recorded here with its source file and date. This feeds the thesis text.
Values are copied from output files, never typed from memory.

## Old work (baseline to beat) — period 2017–2023, 2018 excluded from training

Verified on 2026-11-06 against the old output files (see [old_code_notes.md](old_code_notes.md) §3).

| Setting | n (test) | R² | RMSE | Other | Source file (in `Desktop\train\`) |
|---|---:|---:|---:|---|---|
| Pixel 20 m, random split, 10 features | 25,266,269 px-months | 0.4215 | 0.1633 | | `retrain_metrics.json` |
| 1 km, random 80/20 split, 10 features | 11,506 cell-months | 0.8976 | 0.0451 | | `retrain_1km_metrics.json` |
| 1 km, 2022 temporal holdout | 9,588 cell-months | 0.3671 | 0.1047 | MAE 0.0853, bias +0.0610 | `retrain_1km_holdout2022_metrics.json` |
| 1 km, 2018 (partial coverage year) | 3,758 cell-months | −0.096 | 0.164 | bias −0.049 | `outputs_chapter4\validation_1km_2018_summary.json` |
| Pixel model **with** `year`, `x`, `y` | — | "≈ 0.99" | — | **no saved output**; hard-coded in old figure script | — |

## New pipeline

## Phase 1 — exported dataset, 2016–2025 (800 cells × 120 months)

Source: `outputs/01c_check_export/summary.csv` (scripts/01_export.py + 01c_check_export.py, run 2026-11-07).
Area means weighted by the area of each cell inside the study area. ET0 = FAO-56 Penman-Monteith from ERA5-Land
(decisions.md D7); actual ET = ERA5-Land total evaporation; rain = CHIRPS; NDVI = HLS v2.0 (decisions.md D6).

| Year | NDVI mean | NDVI peak (month) | clear days/pixel, worst month | cell-months < 1 clear day | rain mm | ET0 mm | ET0 July | actual ET mm (peak month) | TerraClimate | WaPOR v2 | WaPOR v3 | r NDVI vs old |
|---:|---:|---|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|
| 2016 | 0.500 | 0.608 (3) | 2.5 | 9 | 356 | 1472 | 210 | 372 (5) | 1654 | 1756 | — | — |
| 2017 | 0.504 | 0.692 (3) | 3.4 | 2 | 300 | 1581 | 216 | 291 (3) | 1706 | 1839 | — | 0.620 |
| 2018 | 0.543 | 0.721 (3) | 4.7 | 0 | 490 | 1307 | 203 | 631 (5) | 1512 | 1519 | 1360 | — |
| 2019 | 0.498 | 0.575 (4) | 6.4 | 0 | 360 | 1505 | 205 | 340 (4) | 1842 | 1741 | 1552 | 0.976 |
| 2020 | 0.499 | 0.592 (4) | 2.7 | 0 | 332 | 1518 | 221 | 340 (5) | 1780 | 1767 | 1588 | 0.954 |
| 2021 | 0.482 | 0.666 (3) | 6.5 | 0 | 340 | 1496 | 218 | 323 (3) | 1773 | 1758 | 1588 | 0.987 |
| 2022 | 0.393 | 0.526 (4) | 5.7 | 0 | 358 | 1544 | 218 | 282 (4) | 1843 | 1720 | 1614 | 0.984 |
| 2023 | 0.335 | 0.457 (3) | 7.0 | 0 | 251 | 1543 | 219 | 272 (3) | 1847 | — | 1652 | 0.984 |
| 2024 | 0.318 | 0.395 (2) | 7.5 | 0 | 266 | 1543 | 218 | 249 (3) | 1810 | — | 1638 | — |
| 2025 | 0.354 | 0.521 (4) | 6.4 | 0 | 394 | 1497 | 217 | 352 (4) | — | — | 1604 | — |
| **mean** | 0.443 | | | | 345 | 1501 | 215 | 345 | | | | |

- ET0 2016–2025: mean 1501 mm/yr (range 1307–1581), July mean 215 mm
  (range 203–221). Ratio this export / product: TerraClimate
  0.86 (0.82–0.93),
  WaPOR v2 0.86 (0.84–0.90),
  WaPOR v3 0.95 (0.93–0.97).
- Rain 2016–2025: mean 345 mm/yr (range 251–490); CHIRPS daily vs pentad annual
  totals differ by -3.8 to -1.1 mm.
- ERA5-Land daily sums = native 24 h accumulation in every year (max difference 0);
  24 hourly wind records every day.
- NDVI: area mean ≈ 0.48–0.54 in 2016–2021, then 0.39 (2022), 0.34 (2023), 0.32 (2024), 0.35 (2025).
- Actual ET exceeds CHIRPS rain in 2018 (631 vs 490 mm): ERA5-Land is driven by its own ERA5 precipitation, not CHIRPS.
- Comparison with the old 1 km table (same cells and months): rain r = 0.999 and actual ET r = 0.985–0.996 every
  year; NDVI r = 0.95–0.99 with HLS ≈ +0.05 higher (B8A vs B8, decisions.md D6), except 2017 (r = 0.62):
  the old February–March 2017 NDVI is corrupted (old_code_notes.md §4.17).

