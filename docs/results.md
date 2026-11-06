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

_No results yet (Phase 0)._
