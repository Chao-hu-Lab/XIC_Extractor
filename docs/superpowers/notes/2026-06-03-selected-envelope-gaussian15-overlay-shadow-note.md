# Selected-Envelope Gaussian15 Overlay / Shadow Area Note

Date: 2026-06-03

## Decision

`gaussian_15` is now the default selected-envelope morphology trace. It is an
Xcalibur-like review/boundary trace, not an exact reproduction of Xcalibur's
closed smoothing implementation and not a product area source.

Primary area remains raw XIC integrated over the selected interval with AsLS
baseline subtraction. Gaussian15 area is emitted only as a diagnostic shadow
comparison over the same old/envelope intervals.

## Implementation Surface

- `SelectedEnvelopePolicy.morphology_trace_method` defaults to `gaussian_15`.
- Legacy `smooth_15` remains available as a named morphology trace.
- `selected_envelope_diagnostics.tsv` includes:
  - `gaussian15_area_old_interval_shadow`
  - `gaussian15_area_selected_envelope_shadow`
  - `gaussian15_area_delta_ratio_shadow`
- `selected_envelope_plot_review.py` overlays Gaussian15 morphology/residual on
  the RAW/AsLS review plots.

## Verification

Focused no-RAW checks:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_selected_full_envelope_policy.py tests\test_selected_full_envelope_diagnostics.py tests\test_selected_envelope_review_queue.py tests\test_selected_full_envelope_projection.py tests\test_selected_full_envelope_output.py tests\test_selected_envelope_plot_review.py tests\test_selected_full_envelope_changed_row_review.py tests\test_selected_full_envelope_oracle.py tests\test_selected_full_envelope_oracle_artifacts.py tests\test_selected_full_envelope_fe0_contract.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor\peak_detection\selected_envelope.py xic_extractor\peak_detection\selected_envelope_diagnostics.py tools\diagnostics\selected_envelope_plot_review.py tests\test_selected_full_envelope_policy.py tests\test_selected_full_envelope_diagnostics.py tests\test_selected_envelope_plot_review.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor\peak_detection\selected_envelope.py xic_extractor\peak_detection\selected_envelope_diagnostics.py
```

Observed results:

- `94 passed`
- `All checks passed!`
- `Success: no issues found in 2 source files`

RAW-backed diagnostic run:

```powershell
.venv\Scripts\python.exe scripts\validation_harness.py --suite tissue-8raw --base-dir . --output-root output\selected_full_envelope_realdata_preflight --run-id fe4_8raw_selected_envelope_gaussian15_20260603 --resolver-mode region_first_safe_merge --parallel-mode process --parallel-workers 4 --data-dir "C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation" --setting emit_peak_candidates=true
```

Observed result:

- `tissue-8raw: passed`
- output workbook:
  `output\selected_full_envelope_realdata_preflight\fe4_8raw_selected_envelope_gaussian15_20260603\tissue_8raw_region_first_safe_merge\xic_results_process_w4.xlsx`
- diagnostics:
  `output\selected_full_envelope_realdata_preflight\fe4_8raw_selected_envelope_gaussian15_20260603\tissue_8raw_region_first_safe_merge\selected_envelope_diagnostics.tsv`

Review queue:

- rows: `95`
- changed: `95`
- gate: `externalize`
- unresolved blocker count: `29`
- high-risk strata:
  `context_apex_conflict;overmerge_rejected;split_supported`

Plot artifacts:

- `output\selected_full_envelope_realdata_preflight\fe4_8raw_selected_envelope_gaussian15_20260603\selected_envelope_plot_review_all_changed\selected_envelope_plot_index.tsv`
- `output\selected_full_envelope_realdata_preflight\fe4_8raw_selected_envelope_gaussian15_20260603\selected_envelope_plot_review_all_changed\plots\`

## Current Interpretation

Gaussian15 improves review readability by smoothing spike-level RAW morphology,
but it does not close the selected-envelope product gate. The 8RAW gate remains
`externalize`.

The plots show that several high-risk rows are not baseline failures. They are
selected-candidate, context-apex, split, or overmerge conflicts. These cases
should remain review-only until candidate selection and neighbor/split evidence
are handled with an approved product policy.
