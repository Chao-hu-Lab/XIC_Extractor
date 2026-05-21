# Instrument QC Mid/Long-Term Calibration Gates Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans`
> to implement this plan checkpoint-by-checkpoint. Steps use checkbox (`- [ ]`)
> syntax for tracking. Do not promote any correction layer without the go/no-go
> gates in this plan passing.

**Goal:** Convert the spec's Level 2 through Level 5 goals into explicit
go/no-go diagnostics and decision notes.

**Architecture:** Keep calibration evidence as sidecars. The domain classifiers
live in `xic_extractor/instrument_qc/`; file reading/writing lives in matching
IO modules; `tools/diagnostics/` scripts stay thin CLI wrappers. Mid-term work
can become RT-aware audit / alignment-support, while long-term RT/response
production remains blocked unless the evidence gates pass.

**Tech Stack:** Python dataclasses, TSV/JSON/Markdown diagnostic artifacts,
pytest, ruff, mypy.

---

## Product Boundaries

This plan may add:

- biological ISTD transfer audit;
- RT calibration maturity go/no-go report;
- decision notes summarizing Level 2 through Level 5 readiness.

This plan must not change:

- `alignment_matrix.tsv`;
- `alignment_review.tsv`;
- `alignment_cells.tsv` schema;
- targeted reliability;
- peak scoring;
- resolver behavior;
- matrix identity / production gates;
- DNP normalization;
- production RT or response correction.

## File Structure

- `xic_extractor/instrument_qc/rt_transfer_audit.py`
  - Domain classifier for clean-standard to biological-ISTD RT transfer.
- `xic_extractor/instrument_qc/rt_transfer_audit_io.py`
  - TSV/JSON/Markdown adapters for transfer audit.
- `tools/diagnostics/instrument_qc_biological_istd_transfer_audit.py`
  - Thin CLI wrapper for transfer audit.
- `xic_extractor/instrument_qc/calibration_maturity_gate.py`
  - Domain classifier for Level 2 through Level 5 go/no-go decisions.
- `xic_extractor/instrument_qc/calibration_maturity_gate_io.py`
  - Loads existing summaries and writes maturity gate outputs.
- `tools/diagnostics/instrument_qc_calibration_maturity_gate.py`
  - Thin CLI wrapper for maturity gate.
- `docs/superpowers/notes/2026-05-21-instrument-qc-rt-aware-midterm-preview.md`
  - Human-facing evidence and decision note.
- `tests/test_instrument_qc_rt_transfer_audit.py`
  - Transfer audit domain tests.
- `tests/test_instrument_qc_biological_istd_transfer_audit_cli.py`
  - Transfer audit CLI contract tests.
- `tests/test_instrument_qc_calibration_maturity_gate.py`
  - Maturity gate domain tests.
- `tests/test_instrument_qc_calibration_maturity_gate_cli.py`
  - Maturity gate CLI contract tests.

## Checkpoint 0: Worktree Guard And Current Evidence Freeze

### Tasks

- [x] Confirm current worktree is
  `C:\Users\user\Desktop\XIC_Extractor\.worktrees\instrument-qc-trend`.
- [x] Confirm branch is `codex/instrument-qc-trend`.
- [x] Confirm dirty diff belongs to instrument-QC calibration productization.
- [x] Do not commit or stage unrelated graphify / architecture work.

### Go / No-Go

- **GO** if the branch and dirty diff match this task.
- **NO-GO** if the current directory or branch is not the instrument-QC worktree.

### Validation

```powershell
git status --short --branch
```

## Checkpoint 1: Biological ISTD Transfer Audit

### Tasks

- [x] Add domain transfer classification:
  - `transfer_supported`
  - `direction_supported_magnitude_shifted`
  - `transfer_not_supported`
  - `insufficient_biological_istd`
  - `insufficient_clean_standard`
- [x] Add TSV/JSON/Markdown writer.
- [x] Add CLI:
  `tools\diagnostics\instrument_qc_biological_istd_transfer_audit.py`.
- [x] Run on existing clean-standard and biological QC ISTD summaries.
- [x] Write explicit `istd_scope` into transfer audit JSON / Markdown.

### ISTD Scope Contract

Default scope:

```text
provided_biological_qc_istd_summary_rows
```

Meaning:

- The audit evaluates every row present in the supplied biological QC ISTD
  summary.
- It does not infer DNA-only, RNA-only, or multi-tag active scope by label.
- If a future run needs DNA-only or multi-tag filtering, the upstream summary or
  this CLI must be called with an explicit `--istd-scope` value and matching
  filtered input.
- Level 2 may use transfer row counts only when the output JSON includes
  non-empty `istd_scope`.

### Go / No-Go

- **GO to Level 2 alignment-support** if transfer audit has at least three
  informative ISTD rows, where informative means `transfer_supported` or
  `direction_supported_magnitude_shifted`, and every unsupported / insufficient
  row remains explicit.
- **NO-GO to production RT correction** if any ISTD row is
  `transfer_not_supported`, `insufficient_biological_istd`, or
  `insufficient_clean_standard`.

### Validation

```powershell
uv --cache-dir .uv-cache run pytest `
  tests\test_instrument_qc_rt_transfer_audit.py `
  tests\test_instrument_qc_biological_istd_transfer_audit_cli.py -q

uv --cache-dir .uv-cache run python tools\diagnostics\instrument_qc_biological_istd_transfer_audit.py `
  --clean-standard-summary-tsv output\diagnostics\instrument_qc_midterm_evidence_20260521\clean_standard_rt_response_summary.tsv `
  --biological-qc-istd-summary-tsv output\diagnostics\instrument_qc_midterm_evidence_20260521\biological_qc_istd_drift_summary.tsv `
  --istd-scope provided_biological_qc_istd_summary_rows `
  --output-dir output\diagnostics\instrument_qc_biological_istd_transfer_audit_20260521
```

## Checkpoint 1.5: Artifact Preflight

### Tasks

- [x] Verify all required artifact paths exist before running the maturity gate.
- [x] If Level 1 RT preview artifacts are missing, rerun
  `instrument_qc_matrix_calibration_preview.py`.
- [x] If transfer audit JSON is missing or lacks `istd_scope`, rerun
  `instrument_qc_biological_istd_transfer_audit.py`.
- [x] If inputs cannot be regenerated from available local artifacts, stop and
  write `NO-GO: required_artifact_missing`.

### Required Preflight Artifacts

```text
output\diagnostics\instrument_qc_rt_aware_midterm_level1_8raw_20260521\instrument_qc_rt_drift_model_summary.json
output\diagnostics\instrument_qc_rt_aware_midterm_level1_8raw_20260521\matrix_rt_calibration_preview_summary.json
output\diagnostics\instrument_qc_rt_aware_midterm_level1_8raw_20260521\matrix_rt_calibration_preview.tsv
output\diagnostics\instrument_qc_biological_istd_transfer_audit_20260521\biological_istd_rt_transfer_audit.json
```

### Rebuild Commands

Regenerate Level 1 RT preview if required:

```powershell
uv --cache-dir .uv-cache run python tools\diagnostics\instrument_qc_matrix_calibration_preview.py `
  --instrument-qc-dir output\instrument_qc\hcd_audit_v1_sdolek_whcd_review_20260520 `
  --matrix-input output\alignment\instrument_qc_calibration_level1_8raw_20260521\alignment_cells.tsv `
  --matrix-input-role untargeted_cell_table `
  --preview-kind rt `
  --output-dir output\diagnostics\instrument_qc_rt_aware_midterm_level1_8raw_20260521
```

Regenerate biological ISTD transfer audit if required:

```powershell
uv --cache-dir .uv-cache run python tools\diagnostics\instrument_qc_biological_istd_transfer_audit.py `
  --clean-standard-summary-tsv output\diagnostics\instrument_qc_midterm_evidence_20260521\clean_standard_rt_response_summary.tsv `
  --biological-qc-istd-summary-tsv output\diagnostics\instrument_qc_midterm_evidence_20260521\biological_qc_istd_drift_summary.tsv `
  --istd-scope provided_biological_qc_istd_summary_rows `
  --output-dir output\diagnostics\instrument_qc_biological_istd_transfer_audit_20260521
```

## Checkpoint 2: RT Calibration Maturity Gate

### Tasks

- [x] Add domain maturity gate classifier for:
  - Level 2: `rt_aware_audit_alignment_support`
  - Level 3: `rt_production_candidate`
  - Level 4: `response_shadow_candidate`
  - Level 5: `response_production_candidate`
- [x] Inputs:
  - `instrument_qc_rt_drift_model_summary.json`
  - `matrix_rt_calibration_preview_summary.json`
  - `matrix_rt_calibration_preview.tsv`
  - `biological_istd_rt_transfer_audit.json`
  - optional response preview / response model summaries
- [x] Outputs:
  - `instrument_qc_calibration_maturity_gate.tsv`
  - `instrument_qc_calibration_maturity_gate.json`
  - `instrument_qc_calibration_maturity_gate.md`
- [x] Keep the CLI wrapper thin and deterministic.

### Go / No-Go

- **Level 2 GO** if:
  - RT model summary exists;
  - matrix RT preview summary exists;
  - transfer audit exists;
  - transfer audit declares non-empty `istd_scope`;
  - preview rows include `shadow_only`;
  - transfer audit has at least three informative ISTD rows;
  - Level 2 output clearly states audit-only / no matrix mutation.
- **Level 3 NO-GO** if any of these are true:
  - LOAO `FAIL` count is greater than 0;
  - LOAO p95 absolute error is greater than `0.30 min`;
  - transfer audit contains `transfer_not_supported`;
  - transfer audit contains `insufficient_biological_istd`;
  - matrix preview TSV contains extrapolated rows;
  - matrix preview TSV contains blocked rows and no reviewed production
    exclusion policy exists.
- **Level 4 NO-GO** unless a response model and biological response transfer
  audit both exist.
- **Level 5 NO-GO** unless Level 4 passes and downstream DNP/statistical
  compatibility has been validated.

### Validation

```powershell
uv --cache-dir .uv-cache run pytest `
  tests\test_instrument_qc_calibration_maturity_gate.py `
  tests\test_instrument_qc_calibration_maturity_gate_cli.py -q

uv --cache-dir .uv-cache run python tools\diagnostics\instrument_qc_calibration_maturity_gate.py `
  --rt-model-summary-json output\diagnostics\instrument_qc_rt_aware_midterm_level1_8raw_20260521\instrument_qc_rt_drift_model_summary.json `
  --matrix-rt-preview-summary-json output\diagnostics\instrument_qc_rt_aware_midterm_level1_8raw_20260521\matrix_rt_calibration_preview_summary.json `
  --matrix-rt-preview-tsv output\diagnostics\instrument_qc_rt_aware_midterm_level1_8raw_20260521\matrix_rt_calibration_preview.tsv `
  --biological-istd-transfer-json output\diagnostics\instrument_qc_biological_istd_transfer_audit_20260521\biological_istd_rt_transfer_audit.json `
  --output-dir output\diagnostics\instrument_qc_calibration_maturity_gate_20260521
```

## Checkpoint 3: Decision Note Closeout

### Tasks

- [x] Update
  `docs/superpowers/notes/2026-05-21-instrument-qc-rt-aware-midterm-preview.md`
  with maturity gate result paths and Level 2 through Level 5 decisions.
- [x] State explicitly:
  - Level 2 may proceed as audit / alignment-support.
  - Level 3 is not ready for production correction.
  - Level 4 and Level 5 are blocked until response model and biological
    response transfer evidence exist.

### Go / No-Go

- **GO** if the note can explain every maturity level from machine-readable
  outputs.
- **NO-GO** if any maturity decision exists only as prose without TSV/JSON
  evidence.

## Checkpoint 4: Final Validation

### Tests

```powershell
uv --cache-dir .uv-cache run pytest `
  tests\test_instrument_qc_calibration_rt_model.py `
  tests\test_instrument_qc_rt_transfer_audit.py `
  tests\test_instrument_qc_biological_istd_transfer_audit_cli.py `
  tests\test_instrument_qc_calibration_maturity_gate.py `
  tests\test_instrument_qc_calibration_maturity_gate_cli.py `
  tests\test_instrument_qc_matrix_calibration_preview.py `
  tests\test_instrument_qc_matrix_calibration_preview_cli.py `
  tests\test_instrument_qc_calibration_product_models.py `
  tests\test_instrument_qc_calibration_product_writers.py -q
```

### Lint And Typecheck

```powershell
uv --cache-dir .uv-cache run ruff check `
  tools\diagnostics\instrument_qc_biological_istd_transfer_audit.py `
  tools\diagnostics\instrument_qc_calibration_maturity_gate.py `
  tools\diagnostics\instrument_qc_matrix_calibration_preview.py `
  xic_extractor\instrument_qc\calibration_rt_model.py `
  xic_extractor\instrument_qc\rt_transfer_audit.py `
  xic_extractor\instrument_qc\rt_transfer_audit_io.py `
  xic_extractor\instrument_qc\calibration_maturity_gate.py `
  xic_extractor\instrument_qc\calibration_maturity_gate_io.py `
  xic_extractor\instrument_qc\calibration_product_models.py `
  xic_extractor\instrument_qc\calibration_product_preview.py `
  xic_extractor\instrument_qc\calibration_product_writers.py `
  tests\test_instrument_qc_calibration_rt_model.py `
  tests\test_instrument_qc_rt_transfer_audit.py `
  tests\test_instrument_qc_biological_istd_transfer_audit_cli.py `
  tests\test_instrument_qc_calibration_maturity_gate.py `
  tests\test_instrument_qc_calibration_maturity_gate_cli.py `
  tests\test_instrument_qc_matrix_calibration_preview.py `
  tests\test_instrument_qc_matrix_calibration_preview_cli.py `
  tests\test_instrument_qc_calibration_product_models.py `
  tests\test_instrument_qc_calibration_product_writers.py

uv --cache-dir .uv-cache run mypy `
  xic_extractor\instrument_qc\calibration_rt_model.py `
  xic_extractor\instrument_qc\rt_transfer_audit.py `
  xic_extractor\instrument_qc\rt_transfer_audit_io.py `
  xic_extractor\instrument_qc\calibration_maturity_gate.py `
  xic_extractor\instrument_qc\calibration_maturity_gate_io.py `
  xic_extractor\instrument_qc\calibration_product_models.py `
  xic_extractor\instrument_qc\calibration_product_writers.py `
  xic_extractor\instrument_qc\calibration_product_preview.py `
  tools\diagnostics\instrument_qc_matrix_calibration_preview.py `
  tools\diagnostics\instrument_qc_biological_istd_transfer_audit.py `
  tools\diagnostics\instrument_qc_calibration_maturity_gate.py
```

## Self-Review

- [x] Level 2 is audit-only and cannot mutate matrix values.
- [x] Level 3 has explicit blockers, not vague caution text.
- [x] Level 3 reads row-level matrix RT preview coverage/blocker evidence.
- [x] ISTD transfer row counts are tied to an explicit `istd_scope`.
- [x] Required artifact preflight has rebuild or stop behavior.
- [x] Level 4 and Level 5 are not implemented as correction layers.
- [x] Every go/no-go decision has machine-readable evidence.
- [x] CLI scripts do not contain domain classification logic.
- [x] No production scoring, resolver, reliability, matrix identity, or DNP
  behavior is changed.
