# Targeted Expected-Diff BC1055 Closeout

**Date:** 2026-06-04
**Readiness label:** `row_specific_expected_diff_production_ready`
**Scope:** `BenignfatBC1055_DNA / 8-oxodG` row-specific targeted candidate switch

## Verdict

The row-specific expected-diff gate can now switch the targeted product
candidate when the approval references runtime product candidate IDs and the
candidate has role-aware RT plus paired-area-ratio support.

This closes the concrete `BenignfatBC1055_DNA / 8-oxodG` mismatch: the final
workbook uses the right-side complete peak instead of the small legacy-selected
peak. The visible product workbook surface is now projection-first:
`Product State`, `Counted Detection`, `Review State`, and projection-backed
`Reason` are the decision surface. Legacy `Confidence`, score, and cap evidence
is hidden/technical audit material and must not be used as product authority.

This does not promote general target pair auto-reselection. General automation
still needs broader false-positive review and transfer/calibration evidence.

## Evidence

Baseline workbook:

```text
output/targeted_expected_diff_validation_20260604_141723/output/xic_results_20260604_1418.xlsx
```

Final production-ready 8RAW harness workbook:

```text
output/target_pair_rt_production_ready_20260604/bc1055_row_approval_8raw_semantic_surface_final/tissue_8raw_region_first_safe_merge/xic_results_serial_w1.xlsx
```

Expected-diff approval registry used for the run:

```text
output/target_pair_rt_production_ready_20260604/bc1055_row_approval/model_selection_expected_diff_approvals.tsv
```

Target-pair product-switch summary:

```text
output/target_pair_rt_production_ready_20260604/bc1055_row_approval_8raw_semantic_surface_final/tissue_8raw_region_first_safe_merge/target_pair_rt_auto_reselection_summary.tsv
```

Observed final diff:

```text
changed_rows=1
row=BenignfatBC1055_DNA / 8-oxodG
rt=16.3866 -> 17.1355
area=39219.86 -> 1850221.22
peak_start=16.1381 -> 16.8026
peak_end=16.6778 -> 17.5520
product_state=ambiguous -> detected_flagged
counted_detection=FALSE -> TRUE
reason=decision: detected_flagged; support: ms1_peak_present, ms1_coherent,
  chrom_peak_segment_context, role_aware_rt_support, paired_area_ratio_support,
  trace_coherent; review: plausible_nl_dropout_review,
  plausible_dda_nl_dropout, legacy_confidence_review
```

Detection-count impact:

```text
8-oxodG: 3/8 -> 4/8
all other target labels unchanged in the 8RAW run
```

Product switch guardrail:

```text
product_switch_allowed_true_count=1
auto_reselected_count=1
product_switch_accepted_count=1
accepted_row=BenignfatBC1055_DNA / 8-oxodG
non_approved_auto_reselected_rows=0
```

The final support reasons include:

```text
ms1_coherent
chrom_peak_segment_context
role_aware_rt_support
paired_area_ratio_support
trace_coherent
```

## Product-ID Rule

The first attempted approval used audit-overlay candidate IDs from
`peak_candidates.tsv`. That is not a valid product-switch input because overlay
rows may include proposal sources that do not exist in runtime product
hypotheses.

The valid approval uses runtime product candidate IDs:

```text
legacy=BenignfatBC1055_DNA|8-oxodG|region_first_safe_merge|local_minimum;chrom_peak_segment|16.38663|16.13814|16.67782
successor=BenignfatBC1055_DNA|8-oxodG|region_first_safe_merge|chrom_peak_segment|17.13547|16.80263|17.55202
```

Overlay plots may justify the evidence summary, but `ExpectedDiffApprovalRecord`
must reference IDs that exist in the runtime `PeakHypothesis` set. If the
successor ID is overlay-only or otherwise missing from runtime hypotheses, the
product switch must fail closed.

## Verification

Focused no-RAW tests:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests/test_peak_model_selection.py tests/test_result_assembly.py tests/test_handoff_spine_runtime.py tests/test_target_extraction.py tests/test_target_pair_rt_auto_reselection.py tests/test_evidence_semantics.py
```

Observed:

```text
86 passed
```

Static checks:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor\peak_detection\model_selection.py xic_extractor\extraction\result_assembly.py tests\test_peak_model_selection.py tests\test_result_assembly.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor\peak_detection\model_selection.py xic_extractor\extraction\result_assembly.py
```

Observed:

```text
All checks passed.
Success: no issues found in 2 source files.
```

8RAW targeted run:

```powershell
.venv\Scripts\python.exe scripts\validation_harness.py --suite tissue-8raw --base-dir . --output-root output\target_pair_rt_production_ready_20260604 --run-id bc1055_row_approval_8raw_semantic_surface_final --resolver-mode region_first_safe_merge --parallel-mode serial --parallel-workers 1 --data-dir C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation --setting emit_peak_candidates=true --setting target_pair_rt_calibration_path=C:\Users\user\Desktop\XIC_Extractor\output\target_pair_rt_false_positive_review_20260604\target_pair_rt_calibration_review_bootstrap.tsv --setting model_selection_expected_diff_approval_registry=C:\Users\user\Desktop\XIC_Extractor\output\target_pair_rt_production_ready_20260604\bc1055_row_approval\model_selection_expected_diff_approvals.tsv
```

Observed:

```text
tissue-8raw: passed
product_switch_allowed_true_count=1
auto_reselected_count=1
product_switch_accepted_count=1
accepted_row=BenignfatBC1055_DNA / 8-oxodG
visible_surface=Product State / Counted Detection / Review State / Reason
hidden_legacy_surface=Confidence / confidence summary counts / Low Confidence Rows
```

Public-surface regression tests:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests/test_csv_writers.py tests/test_csv_to_excel.py tests/test_output_columns.py
```

Observed:

```text
90 passed when run with the review/output contract slice:
tests/test_csv_to_excel.py tests/test_output_schema_contract.py
tests/test_output_columns.py tests/test_review_metrics.py
tests/test_review_report.py tests/test_csv_writers.py
```

## Remaining Risk

- This is row-specific approval, not a general automatic pair-RT rule.
- Broader target-pair reselection still needs false-positive review, especially
  rows where pair RT is strong but MS2/NL is not observed.
- The legacy `Confidence` field remains audit evidence only. It is hidden from
  the visible XIC Results surface, and product review status is owned by
  projection/NL state rather than legacy confidence.
- Untargeted learning from this slice must use shared low-level evidence and
  model-selection semantics, not target labels or targeted pass/fail shortcuts.
