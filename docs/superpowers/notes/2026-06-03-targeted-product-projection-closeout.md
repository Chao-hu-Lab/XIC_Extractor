# Targeted Product Projection Closeout

**Date:** 2026-06-03
**Verdict:** scoped `production_ready` for targeted product detection under the
default target/settings contract.

## Decision

Targeted product detection now uses `TargetedProductProjection.product_state`
and `counted_detection` as the product authority. Legacy score, confidence,
cap, NL, RT, shape, and trace labels remain visible evidence or diagnostic
inputs, but they do not directly decide workbook detected versus ND in product
mode.

## Key Behavior

- ISTD rows with finite positive RT/area and supporting candidate-aligned
  product/NL/MS2 evidence are counted when the targeted projection conditions
  are satisfied.
- `NL_FAIL` on an ISTD can remain visible as review evidence while the row is
  `detected_flagged`, when the evidence supports plausible DDA NL dropout.
- Legacy morphology/shape/trace labels are review evidence for ISTDs when
  positive MS1, candidate-aligned product/NL/MS2, and role-aware RT context
  support the selected peak. They are not hard product vetoes in that case.
- For targeted analytes/STDs with an ISTD pair, anchor-guided selection is
  quality-aware: a random small nearest peak should not beat a complete
  candidate peak, and a far complete peak should not escape the anchor decision.
- Legacy morphology/shape/trace and `VERY_LOW` labels are review evidence for
  targeted analytes when finite positive RT/area, candidate-aligned product/NL
  support, anchor-guided selection context, and no anchor/RT/NL conflict support
  the same selected peak.
- Analyte `NL_FAIL` and `NO_MS2` rows are not promoted without a separate
  approved analyte policy.
- Targeted projection labels do not feed untargeted identity, owner/family/cell
  policy, or clean benchmark denominators.

## Validation Artifacts

Root:

```text
output/targeted_projection_default_targets_20260603_030225/
```

Primary artifacts:

- `launch_provenance.tsv`
- `run_skip_excel_after_selection_anchor_guard_timing.json`
- `base/output/xic_results_20260603_0419.xlsx`
- `base/output/xic_results_long.csv`
- `targeted_projection_acceptance_summary_after_selection_anchor_guard.tsv`
- `sentinel_projection_assertions_after_selection_anchor_guard.tsv`
- `istd_not_counted_blockers_after_selection_anchor_guard.tsv`
- `analyte_nl_fail_counted_after_selection_anchor_guard.tsv`
- `analyte_old_vs_current_after_selection_anchor_guard.tsv`
- `consumer_authority_audit.tsv`
- `targeted_projection_no_leak_audit.tsv`

## Gate Summary

85 tissue RAW default-target targeted extraction:

- Excel run exit code: `0`
- CSV-retention rerun exit code: `0`
- RAW count: `85`
- target count: `14`
- long rows: `1190`
- projection schema invalid/inconsistent rows: `0`
- sample error rows: `0`
- ISTD rows counted: `595 / 595`
- analyte `NL_FAIL` rows counted: `0`
- sentinel assertion failures: `0`
- old-workbook detected analyte rows lost: `0`
- old-workbook not-detected analyte rows newly counted: `2`, both `5-medC`
  `detected_flagged` with `legacy_confidence_review`.

Sentinels:

- `TumorBC2258_DNA / d3-N6-medA`: `detected_flagged`, counted `TRUE`.
- `TumorBC2289_DNA / d3-5-medC`: `detected_flagged`, counted `TRUE`, with
  plausible DDA NL dropout review evidence.

## Verification

Focused no-RAW tests:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests/test_peak_scoring.py tests/test_signal_processing.py tests/test_signal_processing_selection.py tests/test_result_assembly.py tests/test_targeted_product_projection.py tests/test_csv_writers.py tests/test_csv_to_excel.py tests/test_excel_pipeline.py tests/test_review_metrics.py tests/test_review_report.py
```

Observed: `262 passed`.

Lint/type:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor tests
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor
```

Observed: ruff passed; mypy reported no issues in `xic_extractor`.

## Residual Risk

This closeout covers targeted product detection under default targets/settings.
It does not claim untargeted alignment identity readiness, manual EIC/MS2 truth
for every analyte, new analyte `NL_FAIL` promotion policy, or final cleanup of
legacy targeted scoring as an evidence producer.
