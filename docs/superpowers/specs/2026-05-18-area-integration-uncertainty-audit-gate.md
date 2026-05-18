# Area Integration Uncertainty Audit Gate

**Date:** 2026-05-18
**Status:** Planned
**Branch:** `codex/region-first-safe-merge-validation`
**Depends on:** `2026-05-18-region-first-safe-merge-validation-decision.md`

## Summary

This phase adds an audit gate for area integration uncertainty. It does not add
a resolver and does not change production quantification. The goal is to explain
area mismatch cases with shared integration evidence:

- boundary differences
- baseline sensitivity
- area uncertainty
- RT/area consistency where diagnostic labels disagree

If the 8RAW validation does not reproduce a representative `d3-N6-medA` area
mismatch, the result is `inconclusive`. In that case this phase may keep the
diagnostic plumbing, but it must not recommend production behavior changes.

## Non-Goals

This phase does not change:

- `XIC Results`
- workbook schema
- `alignment_matrix.tsv`
- `alignment_review.tsv`
- `alignment_cells.tsv` schema
- scoring, neutral-loss logic, targeted reliability states, production gates,
  default resolver behavior, or matrix identity
- debug or validation output-level artifact contracts

The alignment integration audit is an explicit opt-in sidecar only. It is not
added automatically by `debug` or `validation` output levels.

## Baseline Artifacts

The initial validation should reuse these artifacts unless they lack required
fields:

- Targeted 8RAW:
  `output/validation_harness/evidence_spine_tracegroup_cp1_8raw_keepcsv/tissue_8raw_local_minimum/`
- Untargeted alignment 8RAW:
  `output/alignment/evidence_spine_tracegroup_cp2_8raw_region_first_safe_merge/`
- Evidence spine diagnostic:
  `output/diagnostics/evidence_spine_consistency_cp3_8raw/`

If a required field is missing, rerun only the minimal needed step and document
why the existing artifact was insufficient.

## Checkpoints

### Checkpoint 0: Contract And Preflight

- Add this tracked audit-only contract.
- Confirm the worktree is clean before implementation begins.
- Commit as `docs: define area integration uncertainty audit gate`.

### Checkpoint 1: Shared Integration Audit Model

- Add `CellIntegrationAuditSummary` and a shared integration-audit helper.
- Compute audit fields from existing trace, boundary, and area evidence:
  - raw area
  - baseline-corrected area
  - area uncertainty
  - baseline type and score
  - integration scan count
  - `uncertainty_fraction = area_uncertainty / raw_area`
  - `baseline_fraction = baseline_corrected_area / raw_area`
- The helper may be called from peak region audit code, but it must not alter
  selected peak, RT, area, candidate ranking, or reliability state.
- Invalid or missing trace context must return an empty audit object instead of
  raising.

### Checkpoint 2: Untargeted Alignment Integration Audit Sidecar

- Add explicit CLI flag `--emit-alignment-integration-audit`.
- Add opt-in sidecar artifact `alignment_cell_integration_audit.tsv`.
- Keep `alignment_cells.tsv` header unchanged.
- Carry integration audit on `AlignedCell`; writers may only serialize existing
  cell audit data and must not rescan RAW files.
- Without the explicit flag, the produced artifact set must remain unchanged.

Sidecar columns:

- `feature_family_id`
- `sample_stem`
- `status`
- `area`
- `apex_rt`
- `peak_start_rt`
- `peak_end_rt`
- `neutral_loss_tag`
- `family_center_mz`
- `family_center_rt`
- `area_baseline_corrected`
- `area_uncertainty`
- `baseline_type`
- `baseline_score`
- `uncertainty_fraction`
- `baseline_fraction`
- `integration_scan_count`

### Checkpoint 3: Area Uncertainty Diagnostic

- Add `tools/diagnostics/area_integration_uncertainty_audit.py`.
- Required inputs:
  - `--evidence-spine-rows-tsv`
  - `--targeted-peak-candidates-tsv`
  - `--targeted-boundaries-tsv`
  - `--alignment-integration-audit-tsv`
  - `--output-dir`
- Outputs:
  - `area_integration_uncertainty_summary.tsv`
  - `area_integration_uncertainty_rows.tsv`
  - `area_integration_uncertainty.json`
  - `area_integration_uncertainty.md`

Classification thresholds:

- raw area consistent: ratio in `[0.80, 1.25]`
- high uncertainty: `uncertainty_fraction > 0.20`
- low baseline fraction: `< 0.30`
- boundary delta concern: start or end delta `> 0.10 min`
- boundary alternative concern: selected candidate top-boundary area ratio
  outside `[0.80, 1.25]`

Bucket precedence:

1. `missing_alignment_match`
2. `integration_context_incomplete`
3. `area_consistent_low_uncertainty`
4. `label_only_mismatch`
5. `baseline_explains_raw_mismatch`
6. `boundary_sensitive`
7. `high_uncertainty`
8. `unexplained_area_mismatch`

### Checkpoint 4: 8RAW Validation Gate

- Rerun targeted 8RAW only if the existing targeted debug artifact lacks needed
  integration-audit fields.
- Rerun 8RAW alignment with:
  - `validation-fast`
  - `--emit-alignment-cells`
  - `--emit-alignment-integration-audit`
  - `region_first_safe_merge`
- Run evidence spine consistency and area integration uncertainty diagnostics.

Acceptance:

- targeted `xic_results.csv` and workbook selected RT/area stay unchanged if
  targeted is rerun
- `alignment_matrix.tsv` hash unchanged
- `alignment_review.tsv` hash unchanged
- `alignment_cells.tsv` header unchanged
- `alignment_cell_integration_audit.tsv` exists and has non-empty audit rows for
  detected/rescued cells
- `d3-N6-medA`, `15N5-8-oxodG`, `5-medC`, and `5-hmdC` rows are explicitly
  classified

If representative `d3-N6-medA` area mismatch does not reproduce, record
`D3_AREA_CHECK_INCONCLUSIVE` and stop before any production recommendation.

### Checkpoint 5: Decision

Write a final decision note with exactly one decision:

- `baseline_uncertainty_next`
- `boundary_model_selection_next`
- `label_calibration_next`
- `evidence_context_incomplete`
- `inconclusive`

Decision rules:

- If raw area mismatch becomes consistent after baseline correction, choose
  `baseline_uncertainty_next`.
- If mismatch follows boundary deltas or top-boundary alternatives, choose
  `boundary_model_selection_next`.
- If RT/area are consistent but region labels differ, choose
  `label_calibration_next`.
- If required audit fields are missing, choose `evidence_context_incomplete`.
- If the representative mismatch is absent, choose `inconclusive`.

## Test Plan

- `uv --cache-dir .uv-cache run pytest tests\test_baseline_integration.py tests\test_peak_region_audit.py -q`
- `uv --cache-dir .uv-cache run pytest tests\test_alignment_tsv_writer.py tests\test_alignment_output_levels.py tests\test_alignment_pipeline.py tests\test_run_alignment.py -q`
- `uv --cache-dir .uv-cache run pytest tests\test_area_integration_uncertainty_audit.py -q`
- `uv --cache-dir .uv-cache run pytest tests\test_evidence_spine_consistency.py tests\test_peak_candidate_boundaries.py tests\test_peak_candidate_table.py -q`
- `uv --cache-dir .uv-cache run ruff check .`
- `uv --cache-dir .uv-cache run mypy xic_extractor`
- `uv --cache-dir .uv-cache run mypy tools\diagnostics\area_integration_uncertainty_audit.py`

## Review Rule

Each checkpoint must be reviewed before the next checkpoint starts. If a
checkpoint fails, write the failure reason and stop instead of broadening scope.

