# 5-hmdC own-max opt-in review packet

更新日期: 2026-06-16
分支: `cc/framework-improvements`
狀態: 使用者已接受 8RAW review；85RAW 已跑完。後續已補 generic support
producer，確認不是只能改 5 rows。建議標成 explicit opt-in
`production_candidate`，但還不能稱整體 `production_ready`

## 先講結論

這包要審的不是「一般 run 是否自動補 5-hmdC」。目前預設仍然不補。

這包要審的是：當使用者明確提供 reviewed
`targeted_ms1_shape_identity_v0.tsv` 時，系統是否可以把
`own_max_same_peak_support` 當成額外 evidence，讓原本因 `NL_FAIL` 被
`not_counted` 的 analyte 進入 `detected_flagged`。

8RAW smoke 已跑過。baseline 和 opt-in 的差異只有一列：
`TumorBC2263_DNA / 5-hmdC`。

使用者 review 後接受這個方向，並確認 backfill/rescue 類結果只能算
`detected_flagged`，不能算乾淨 `detected`。第一輪 85RAW 用手動 review 的
5-row TSV 跑完；結果是 5 個 support TSV rows 全部生效，且沒有額外 row 被改。

後續已修正上游限制：新增 generic support producer 從 baseline 長表自動挑候選
rows，再開 RAW 抽 Gaussian-smoothed MS1 trace 產 support TSV。用 generic TSV
重跑 85RAW opt-in 後，產品輸出剛好改到 11 rows，不再只限原本 5 rows。

| 欄位 | Baseline | Opt-in |
| --- | --- | --- |
| Product State | `not_counted` | `detected_flagged` |
| Counted Detection | `FALSE` | `TRUE` |
| Review State | `review_required` | `flagged` |
| RT | `ND` | `9.1705` |
| Area | `ND` | `145695.76` |
| Confidence | `VERY_LOW` | `MEDIUM` |
| Support change | no `own_max_same_peak_support` | adds `own_max_same_peak_support` |
| Not-counted reason | `analyte_nl_fail_requires_policy` | removed |

## 85RAW result

85RAW baseline/opt-in 都已成功完成，CSV-only，不產 Excel。

| Sample | Target | Baseline | Opt-in | RT | Area |
| --- | --- | --- | --- | ---: | ---: |
| `BenignfatBC1028_DNA` | `5-hmdC` | `not_counted / FALSE` | `detected_flagged / TRUE` | 9.0432 | 832133.71 |
| `BenignfatBC1108_DNA` | `5-hmdC` | `not_counted / FALSE` | `detected_flagged / TRUE` | 9.1403 | 218821.67 |
| `NormalBC2302_DNA` | `5-hmdC` | `not_counted / FALSE` | `detected_flagged / TRUE` | 9.1599 | 58187.92 |
| `TumorBC2263_DNA` | `5-hmdC` | `not_counted / FALSE` | `detected_flagged / TRUE` | 9.1705 | 145695.76 |
| `TumorBC2294_DNA` | `5-hmdC` | `not_counted / FALSE` | `detected_flagged / TRUE` | 9.1171 | 63221.90 |

Gate checks:

- `xic_results_long.csv`: `1190` rows baseline vs `1190` rows opt-in.
- Changed targeted rows: `5`.
- Changed targeted rows exactly match the 5 reviewed support TSV keys.
- Unexpected changed rows: `0`.
- Support rows that did not change output: `0`.
- Wide matrix changed cells: `30`, only the 5 samples' `5-hmdC_RT`,
  `5-hmdC_Int`, `5-hmdC_Area`, `5-hmdC_PeakStart`, `5-hmdC_PeakEnd`,
  `5-hmdC_PeakWidth`.
- `xic_diagnostics.csv` SHA was identical between baseline and opt-in.

## Generic support producer result

這段是後續補上的最新版結論。原本只改 5 rows，不是因為 product gate 只能吃
5 rows，而是因為 support TSV 只餵了手動 review 的 5 rows。

新的 producer:

```powershell
.venv\Scripts\python.exe -m tools.diagnostics.build_targeted_ms1_shape_identity_supports `
  --long-csv output\ms1_shape_identity_optin_85raw_20260616\baseline\output\xic_results_long.csv `
  --raw-dir C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R `
  --dll-dir C:\Xcalibur\system\programs `
  --config-dir config `
  --output-tsv output\ms1_shape_identity_generic_support_85raw_20260616\targeted_ms1_shape_identity_v0.tsv
```

Producer output:

- Candidate rows: `11`
- Evidence rows: `11`
- Trace requests: `13`
- Supported rows: `11 / 11`
- Target split: `5-hmdC = 10`, `5-medC = 1`

Generic 85RAW opt-in output:

| Sample | Target | Baseline | Opt-in | RT | Area | Own-max sim |
| --- | --- | --- | --- | ---: | ---: | ---: |
| `BenignfatBC0980_DNA` | `5-hmdC` | `not_counted / FALSE` | `detected_flagged / TRUE` | 9.0915 | 93914.37 | 0.941123 |
| `BenignfatBC1028_DNA` | `5-hmdC` | `not_counted / FALSE` | `detected_flagged / TRUE` | 9.0432 | 832133.71 | 0.999570 |
| `BenignfatBC1108_DNA` | `5-hmdC` | `not_counted / FALSE` | `detected_flagged / TRUE` | 9.1403 | 218821.67 | 0.891062 |
| `NormalBC2259_DNA` | `5-hmdC` | `not_counted / FALSE` | `detected_flagged / TRUE` | 9.0921 | 32081.59 | 0.980747 |
| `NormalBC2264_DNA` | `5-medC` | `not_counted / FALSE` | `detected_flagged / TRUE` | 12.7302 | 14641482.59 | 0.952358 |
| `NormalBC2270_DNA` | `5-hmdC` | `not_counted / FALSE` | `detected_flagged / TRUE` | 9.1715 | 224179.99 | 0.980368 |
| `NormalBC2272_DNA` | `5-hmdC` | `not_counted / FALSE` | `detected_flagged / TRUE` | 9.1332 | 18852.37 | 0.937315 |
| `NormalBC2294_DNA` | `5-hmdC` | `not_counted / FALSE` | `detected_flagged / TRUE` | 9.1700 | 64928.37 | 0.938411 |
| `NormalBC2302_DNA` | `5-hmdC` | `not_counted / FALSE` | `detected_flagged / TRUE` | 9.1599 | 58187.92 | 0.845699 |
| `TumorBC2263_DNA` | `5-hmdC` | `not_counted / FALSE` | `detected_flagged / TRUE` | 9.1705 | 145695.76 | 0.927740 |
| `TumorBC2294_DNA` | `5-hmdC` | `not_counted / FALSE` | `detected_flagged / TRUE` | 9.1171 | 63221.90 | 0.874897 |

Generic gate checks:

- Changed targeted rows: `11`.
- All changed rows are `not_counted / FALSE -> detected_flagged / TRUE`.
- Wide matrix changed cells: `66`, exactly the 11 rows'
  `RT/Int/Area/PeakStart/PeakEnd/PeakWidth`.
- Baseline and generic opt-in `xic_diagnostics.csv` SHA256 are identical:
  `59D3572A85F0F2596388C9374D34628320DF1660FBF722AAFCBB4934A34FC135`.

Generic evidence paths:

| 類型 | 路徑 |
| --- | --- |
| Generic support TSV | `output/ms1_shape_identity_generic_support_85raw_20260616/targeted_ms1_shape_identity_v0.tsv` |
| Generic opt-in long CSV | `output/ms1_shape_identity_generic_support_85raw_20260616/optin/output/xic_results_long.csv` |
| Generic row diff summary | `output/ms1_shape_identity_generic_support_85raw_20260616/expected_diff_summary.tsv` |
| Generic matrix diff summary | `output/ms1_shape_identity_generic_support_85raw_20260616/matrix_diff_summary.tsv` |

## 你要判斷什麼

- `TumorBC2263_DNA / 5-hmdC` 的 `9.1705 min` 峰，從 Gaussian-smoothed own-max
  overlay 看，是否像同一個峰群。
- 這個 opt-in 行為是否符合產品語意：不是自動放行，而是「paired RT /
  area-ratio 已支持，再加 reviewed own-max same-peak support」才放行。
- generic producer 的 11-row 85RAW diff 是否符合產品語意：它不是自動放行所有
  `NL_FAIL`，而是只放行已通過 pair support 且 own-max same-peak 支持的 rows。

## Evidence paths

| 類型 | 路徑 |
| --- | --- |
| Gaussian-smoothed overlay PNG | `output/ms1_rescue_5hmdc_own_max_similarity_20260616/5hmdc_own_max_similarity_diagnostic.png` |
| Gaussian-smoothed overlay PDF | `output/ms1_rescue_5hmdc_own_max_similarity_20260616/5hmdc_own_max_similarity_diagnostic.pdf` |
| 5-case own-max summary | `output/ms1_rescue_5hmdc_own_max_similarity_20260616/own_max_similarity_summary.tsv` |
| Reviewed support TSV | `output/ms1_rescue_5hmdc_own_max_similarity_20260616/targeted_ms1_shape_identity_v0.tsv` |
| 8RAW baseline output | `output/ms1_shape_identity_optin_8raw_20260616/baseline/output/xic_results_long.csv` |
| 8RAW opt-in output | `output/ms1_shape_identity_optin_8raw_20260616/optin/output/xic_results_long.csv` |
| 8RAW diff summary | `output/ms1_shape_identity_optin_8raw_20260616/expected_diff_summary.tsv` |
| 85RAW baseline output | `output/ms1_shape_identity_optin_85raw_20260616/baseline/output/xic_results_long.csv` |
| 85RAW opt-in output | `output/ms1_shape_identity_optin_85raw_20260616/optin/output/xic_results_long.csv` |
| 85RAW targeted diff summary | `output/ms1_shape_identity_optin_85raw_20260616/expected_diff_summary.tsv` |
| 85RAW matrix diff summary | `output/ms1_shape_identity_optin_85raw_20260616/matrix_diff_summary.tsv` |
| Baseline manifest | `output/ms1_shape_identity_optin_8raw_20260616/baseline/output/method_manifest.json` |
| Opt-in manifest | `output/ms1_shape_identity_optin_8raw_20260616/optin/output/method_manifest.json` |

## Manual 5-row reviewed support rows

這些 rows 來自 `targeted_ms1_shape_identity_v0.tsv`。它們是
`diagnostic_only_no_product_write`；只有透過 explicit opt-in settings/CLI 才會進
normal extraction projection。

| Sample | Candidate RT | Ref RT | Anchor delta | ISTD RT | Pair delta | Own-max sim | Competing status |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `TumorBC2263_DNA` | 9.1705 | 9.1403 | 0.0302 | 9.0466 | 0.1239 | 0.986372 | `no_competing_peak_observed` |
| `NormalBC2302_DNA` | 9.1599 | 9.1403 | 0.0196 | 9.0258 | 0.1341 | 0.884525 | `no_competing_peak_observed` |
| `BenignfatBC1108_DNA` | 9.1403 | 9.1403 | 0 | 9.0236 | 0.1167 | 0.993612 | `no_competing_peak_observed` |
| `BenignfatBC1028_DNA` | 9.0432 | 9.1403 | -0.0971 | 8.9603 | 0.0829 | 0.874984 | `no_competing_peak_observed` |
| `TumorBC2294_DNA` | 9.1171 | 9.1403 | -0.0232 | 9.0235 | 0.0936 | 0.992603 | `no_competing_peak_observed` |

注意：`targeted_ms1_shape_identity_v0.tsv` 是從 trace grid 轉出來的 support
surface；competing-peak 的人工判讀仍要看原始
`own_max_similarity_summary.tsv`。例如 `TumorBC2294_DNA` 原 summary 中有
`9.7142 min / 0.20005 own-max ratio` 的 competing peak 訊息，但本次 8RAW smoke
真正被產品輸出改到的是 `TumorBC2263_DNA`，不是 `TumorBC2294_DNA`。

## Commands already run

Baseline:

```powershell
.venv\Scripts\python.exe -m scripts.run_extraction `
  --base-dir output\ms1_shape_identity_optin_8raw_20260616\baseline `
  --data-dir C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation `
  --skip-excel
```

Opt-in:

```powershell
.venv\Scripts\python.exe -m scripts.run_extraction `
  --base-dir output\ms1_shape_identity_optin_8raw_20260616\optin `
  --data-dir C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation `
  --skip-excel `
  --targeted-ms1-shape-identity-support-tsv output\ms1_rescue_5hmdc_own_max_similarity_20260616\targeted_ms1_shape_identity_v0.tsv
```

85RAW baseline:

```powershell
.venv\Scripts\python.exe -m scripts.run_extraction `
  --base-dir output\ms1_shape_identity_optin_85raw_20260616\baseline `
  --data-dir C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R `
  --skip-excel
```

85RAW opt-in:

```powershell
.venv\Scripts\python.exe -m scripts.run_extraction `
  --base-dir output\ms1_shape_identity_optin_85raw_20260616\optin `
  --data-dir C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R `
  --skip-excel `
  --targeted-ms1-shape-identity-support-tsv output\ms1_rescue_5hmdc_own_max_similarity_20260616\targeted_ms1_shape_identity_v0.tsv
```

No-RAW checks:

```powershell
python -m pytest tests\test_settings_new_fields.py tests\test_config.py tests\test_extractor_run.py tests\test_run_extraction.py tests\test_method_manifest.py tests\test_result_assembly.py tests\test_paired_area_ratio_projection.py tests\test_targeted_product_projection.py tests\test_ms1_shape_identity.py tests\test_targeted_ms1_shape_identity.py tests\test_targeted_ms1_shape_identity_from_grid.py tests\test_targeted_ms1_shape_identity_support_builder.py tests\test_build_targeted_ms1_shape_identity_supports.py tests\test_targeted_ms1_shape_identity_projection.py tests\test_family_ms1_overlay_plot.py tests\test_family_ms1_overlay_batch.py tests\test_family_ms1_alignment_experiment.py tests\test_changed_row_mode_overlay_review.py -q
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check <changed-surface>
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy <changed-source-files>
git diff --check
```

Observed result:

- `259 passed`
- `ruff` passed
- `mypy` passed for the new generic producer source files and the prior
  opt-in source files
- `git diff --check` had no whitespace errors
- 8RAW baseline and opt-in both exited successfully
- 85RAW baseline and 5-row opt-in both exited successfully
- 85RAW generic opt-in exited successfully and changed exactly 11 rows

## Reviewer checklist

- [ ] The Gaussian-smoothed overlay supports the 9.04-9.17 min same-peak mode.
- [ ] `TumorBC2263_DNA / 5-hmdC` at `9.1705 min` is a plausible review-positive
      peak, not just a noise shoulder.
- [x] The 8RAW opt-in diff changing exactly one row is acceptable.
- [x] `detected_flagged` is the right state; this should not become clean
      `detected` without further evidence.
- [ ] It is acceptable that default extraction remains unchanged unless the
      reviewed support TSV is explicitly supplied.
- [x] Historical decision: run 85RAW after the 8RAW smoke.
- [x] The first 85RAW result changing exactly the 5 manually reviewed support
      rows is acceptable as a narrow smoke.
- [x] The generic producer result proves the rule is not limited to the original
      5 rows: it changed exactly 11 eligible rows.
- [ ] Decision: promote explicit opt-in workflow to `production_candidate`, or
      hold for more manual EIC/MS2 evidence.

## My current recommendation

Approve this as `production_candidate` for explicit opt-in review workflow only.

Do not call the full product path `production_ready` yet. The missing pieces are
GUI wiring and a clearer policy for when generic same-peak support TSVs are
allowed to become durable product inputs rather than diagnostic artifacts.
