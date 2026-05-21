# Instrument QC Matrix Calibration Productization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` to implement this plan checkpoint-by-checkpoint. Do not skip review gates.

## Goal

Turn clean instrument QC standards into a manifest-backed calibration product that can generate safe matrix preview sidecars before any production matrix correction is considered.

## Corrected Direction

The first implementation target is **not** a full Level 1 product. The first PR should produce a Level 0 calibration evidence bundle and, only after that is stable, a separate Level 1 matrix preview sidecar.

The maturity labels are contract-critical:

- **Level 0:** manifest-backed evidence bundle only.
  - `product_maturity_level="level_0"`
  - `overall_verdict="diagnostic_only"`
  - no matrix preview claims.
- **Level 1:** explicit matrix preview sidecar.
  - requires `--matrix-input`
  - writes rejoinable `matrix_*_calibration_preview.tsv`
  - proves source matrix hash unchanged.

RT preview is the realistic first matrix preview. Response preview remains shadow/audit-only until biological transfer validation exists.

## Operator Quickstart Contract

The calibration product command consumes existing instrument QC outputs. Operators must first generate those outputs:

```powershell
uv --cache-dir .uv-cache run python scripts\run_instrument_qc.py `
  --raw-dir <raw_root> `
  --output-dir <instrument_qc_output_dir> `
  --mode sdolek `
  --method-doc "<method_docx>" `
  --emit-mixstds `
  --mixstds-target-registry config\MixSTDs.csv `
  --emit-hcd-audit
```

Then build the Level 0 bundle:

```powershell
uv --cache-dir .uv-cache run python tools\diagnostics\instrument_qc_matrix_calibration_preview.py `
  --instrument-qc-dir <instrument_qc_output_dir> `
  --output-dir <bundle_output_dir>
```

Then, only when a supported matrix input exists, build Level 1 preview:

```powershell
uv --cache-dir .uv-cache run python tools\diagnostics\instrument_qc_matrix_calibration_preview.py `
  --instrument-qc-dir <instrument_qc_output_dir> `
  --matrix-input <alignment_cells.tsv> `
  --matrix-input-role untargeted_cell_table `
  --preview-kind rt `
  --output-dir <bundle_output_dir>
```

## Public Surface

Create or update:

- `xic_extractor/instrument_qc/calibration_product_models.py`
- `xic_extractor/instrument_qc/calibration_product_writers.py`
- `xic_extractor/instrument_qc/calibration_product_loaders.py`
- `xic_extractor/instrument_qc/calibration_product_preview.py`
- `tools/diagnostics/instrument_qc_matrix_calibration_preview.py`
- `tests/test_instrument_qc_calibration_product_models.py`
- `tests/test_instrument_qc_calibration_product_writers.py`
- `tests/test_instrument_qc_matrix_calibration_preview.py`
- `tests/test_instrument_qc_matrix_calibration_preview_cli.py`

Do not change:

- production extraction output
- targeted reliability state
- untargeted matrix identity
- scoring
- resolver behavior
- DNP normalization
- existing instrument QC MS1 trend TSV headers

## Checkpoint 0: Contract Cleanup

### Tasks

- [ ] Keep this plan and the spec aligned on maturity levels.
- [ ] Ensure the plan does not call Level 0 evidence output `preview_ready`.
- [ ] Keep mid/long-term work as deferred outlines, not executable tasks in this PR.

### Review Gate

- [ ] Confirm every occurrence of `preview_ready` is tied to real matrix preview sidecars.
- [ ] Confirm Level 0 without `--matrix-input` produces only diagnostic artifacts.
- [ ] Confirm Level 1 requires a supported `--matrix-input`.

## Checkpoint 1: Level 0 Models And Writers

### Required Model Contracts

Add typed models/enums for:

- `CalibrationBundleManifest`
- `ArtifactInventoryItem`
- `CalibrationEvidenceRow`
- `CalibrationEvidenceSummary`
- `ProductSupportStatus`
- `NeutralLossSupportStatus`
- `CoverageStatus`
- `CorrectionStatus`
- `ResponseTransferStatus`
- `MatrixRTPreviewRow`
- `MatrixResponsePreviewRow`

Status values must preserve product/MS2 meaning:

- `supported`
- `partial`
- `not_triggered`
- `product_missing`
- `unmapped`
- `parse_error`
- `not_applicable`

`not_triggered` must never mean analyte absence.

### Required Writer Contracts

Write:

- `instrument_qc_calibration_manifest.json`
- `instrument_qc_calibration_evidence.tsv`
- `instrument_qc_calibration_evidence_summary.json`

The manifest must include:

- `schema_version`
- `bundle_id`
- `run_id`
- `product_maturity_level`
- `overall_verdict`
- `artifact_inventory`
- `source_artifacts`
- `source_contracts`
- `generation_command`
- `created_at_utc`
- `created_by`
- `status_counts`
- `first_human_file`
- `first_machine_file`

`created_at_utc` must be an actual UTC timestamp, not `not_recorded`.

`artifact_inventory` must list every bundle artifact, including summary JSON.

### Tests

- [ ] model enums are string-compatible.
- [ ] manifest records entrypoint metadata and real artifact inventory.
- [ ] evidence summary JSON includes row counts by source type, matrix context, coverage, product support, and calibration eligibility.
- [ ] writer round-trips JSON and TSV with stable keys.
- [ ] `ArtifactInventoryItem.path` type is consistent with implementation and tests.

### Commit

```powershell
git add xic_extractor\instrument_qc\calibration_product_models.py `
  xic_extractor\instrument_qc\calibration_product_writers.py `
  tests\test_instrument_qc_calibration_product_models.py `
  tests\test_instrument_qc_calibration_product_writers.py
git commit -m "feat: define calibration product bundle contract"
```

## Checkpoint 2: Level 0 Evidence Bundle

### Required Inputs

Read available instrument QC outputs from `--instrument-qc-dir`:

- `instrument_qc_sdolek_trend.tsv`
- `instrument_qc_mixstds_trend.tsv`
- `instrument_qc_hcd_audit.tsv`
- `instrument_qc_hcd_audit.json`
- method-doc manifest / sequence manifest if present

If some expected inputs are missing, do not fake completeness. Emit Level 0 output with:

- `overall_verdict="diagnostic_only"`
- explicit source coverage status
- clear missing-artifact reason in summary JSON

### Evidence Mapping

Evidence rows must preserve source semantics:

- SDO/LEK clean standards are their own source type.
- Mix STDs clean standards are their own source type.
- HCD/CID product evidence is annotation confidence, not numeric correction.
- CID/dR/R/MeR and HCD/base-product evidence must not be collapsed into a single `detected/not_detected` field.
- `no_ms2_trigger` maps to `not_triggered`, not `product_missing`.
- `no_product_match` maps to `product_missing`.
- unmapped base/product group maps to `unmapped`.
- parser failure maps to `parse_error`.

### Level 0 Outputs

Required:

- `instrument_qc_calibration_manifest.json`
- `instrument_qc_calibration_evidence.tsv`
- `instrument_qc_calibration_evidence_summary.json`

No matrix preview TSV is produced in Level 0.

### Tests

- [ ] SDOLEK trend rows become clean SDO/LEK evidence rows.
- [ ] Mix STDs trend rows become clean Mix STDs evidence rows.
- [ ] HCD audit statuses preserve `not_triggered`, `product_missing`, `unmapped`, and `parse_error`.
- [ ] missing optional input is recorded as incomplete coverage, not silently ignored.
- [ ] bad numeric values fail with a clear error naming file, column, and row.
- [ ] missing required TSV columns fail with a clear error.
- [ ] summary JSON status counts match evidence TSV rows.
- [ ] no matrix preview artifact appears when `--matrix-input` is omitted.

### Commit

```powershell
git add xic_extractor\instrument_qc\calibration_product_loaders.py `
  xic_extractor\instrument_qc\calibration_product_preview.py `
  tests\test_instrument_qc_matrix_calibration_preview.py
git commit -m "feat: build level0 calibration evidence bundle"
```

## Checkpoint 3: Level 1 Matrix Preview Sidecar

### Scope

Implement Level 1 preview for one source first:

- supported first input: `alignment_cells.tsv`
- role: `untargeted_cell_table`
- preview kind: `rt`

Response preview may be parsed as a future option but must stay blocked unless the response transfer gate exists.

### CLI Contract

Add:

- `--matrix-input <path>`
- `--matrix-input-role untargeted_cell_table|targeted_result_table|external_matrix`
- `--preview-kind rt|response|both`

Rules:

- If `--matrix-input` is absent: emit Level 0 only.
- If `--matrix-input` is present: validate role and required columns.
- If `--preview-kind rt` is requested: emit RT preview sidecar.
- If `--preview-kind response` is requested before response transfer validation exists: emit blocked preview rows, not corrected production values.

### Matrix Rejoin Contract

Every preview row must include:

- `matrix_source`
- `matrix_source_hash`
- `matrix_schema_version`
- `source_row_id`
- `source_cell_key`
- `feature_id`
- `matrix_column_name`
- `sample_name`
- `sample_stem`
- `raw_file_stem`
- `feature_mz`
- `raw_feature_rt_min`
- `injection_order`

For `alignment_cells.tsv`, define stable keys as:

- `source_row_id`: 1-based TSV row number after header unless an existing stable id column exists.
- `source_cell_key`: `<feature_family_id>|<sample_stem>`.

The source matrix/cell TSV must be read-only. The preview command must never rewrite it.

### Level 1 Outputs

When RT preview is requested:

- `instrument_qc_calibration_manifest.json`
- `instrument_qc_calibration_evidence.tsv`
- `instrument_qc_calibration_evidence_summary.json`
- `matrix_rt_calibration_preview.tsv`
- `matrix_rt_calibration_preview_summary.json`

When response preview is requested:

- `matrix_response_calibration_preview.tsv`
- `matrix_response_calibration_preview_summary.json`

The manifest `artifact_inventory` must include every generated artifact.

### RT Preview Policy

RT preview is annotation-only:

- compute `rt_if_standard_corrected_min` only when coverage is sufficient.
- include `predicted_rt_delta_min`.
- include `rt_uncertainty_min`.
- include `correction_status`.
- blocked rows must explain why.

Do not change:

- `alignment_matrix.tsv`
- `alignment_review.tsv`
- `alignment_cells.tsv`
- workbook output

### Tests

- [ ] Level 1 requires `--matrix-input`.
- [ ] unsupported matrix role fails clearly.
- [ ] `alignment_cells.tsv` loader validates required columns.
- [ ] sidecar rows are rejoinable to source rows by `source_row_id`.
- [ ] sidecar rows are rejoinable to source cells by `source_cell_key`.
- [ ] `matrix_source_hash` equals the pre-command source hash.
- [ ] source matrix hash is unchanged after command.
- [ ] preview summary JSON counts `applied_preview`, `blocked_not_covered`, `blocked_missing_value`, and `not_applicable`.
- [ ] response preview does not impute missing, blank, zero, absent, unchecked, or not-detected cells.

### Commit

```powershell
git add xic_extractor\instrument_qc\calibration_product_preview.py `
  tests\test_instrument_qc_matrix_calibration_preview.py
git commit -m "feat: add level1 calibration matrix preview sidecar"
```

## Checkpoint 4: CLI And Operator Errors

### Tasks

- [ ] Implement CLI adapter only in `tools/diagnostics/instrument_qc_matrix_calibration_preview.py`.
- [ ] Print generated artifact paths.
- [ ] Return exit code `2` for user/input errors.
- [ ] Return exit code `1` for unexpected processing errors only if they are not already clear `ValueError`s.

### Required Error Coverage

- missing `--instrument-qc-dir`
- missing required Level 0 TSV columns
- missing `--matrix-input` for Level 1 mode
- bad numeric value in any TSV
- unsupported `--matrix-input-role`
- matrix input lacks required join columns
- source hash cannot be read
- output directory cannot be created

### Tests

- [ ] CLI emits Level 0 artifacts with no matrix input.
- [ ] CLI emits Level 1 preview artifacts with `--matrix-input`.
- [ ] CLI does not produce Level 1 artifacts without `--matrix-input`.
- [ ] CLI error messages name the failing file and column where possible.

### Commit

```powershell
git add tools\diagnostics\instrument_qc_matrix_calibration_preview.py `
  tests\test_instrument_qc_matrix_calibration_preview_cli.py
git commit -m "feat: add calibration product diagnostic cli"
```

## Checkpoint 5: Validation And Review

### Focused Test Suite

```powershell
uv --cache-dir .uv-cache run pytest `
  tests\test_instrument_qc_calibration_product_models.py `
  tests\test_instrument_qc_calibration_product_writers.py `
  tests\test_instrument_qc_matrix_calibration_preview.py `
  tests\test_instrument_qc_matrix_calibration_preview_cli.py `
  tests\test_instrument_qc_pipeline.py `
  tests\test_run_instrument_qc.py -q
```

### Lint And Typecheck

```powershell
uv --cache-dir .uv-cache run ruff check `
  xic_extractor\instrument_qc `
  tools\diagnostics\instrument_qc_matrix_calibration_preview.py `
  tests\test_instrument_qc_calibration_product_models.py `
  tests\test_instrument_qc_calibration_product_writers.py `
  tests\test_instrument_qc_matrix_calibration_preview.py `
  tests\test_instrument_qc_matrix_calibration_preview_cli.py

uv --cache-dir .uv-cache run mypy `
  xic_extractor\instrument_qc `
  tools\diagnostics\instrument_qc_matrix_calibration_preview.py
```

### Real-Data Smoke

Use current instrument QC output generated from:

- RAW root: `C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R`
- method doc: `C:\Users\user\Desktop\NTU cancer\2025台大乳癌組織數據for Jia\20260105中研院台大Breast cancer tissue\20260105 中研院分析.docx`
- Mix STDs registry: `config\MixSTDs.csv`

Run Level 0 first. Then run Level 1 only if a supported `alignment_cells.tsv` input is available.

Acceptance:

- Level 0 evidence bundle includes SDO/LEK, Mix STDs, and HCD coverage status.
- Level 0 does not create matrix preview artifacts.
- Level 1 preview sidecar is rejoinable to source rows/cells.
- Source matrix/cell input hash remains unchanged.
- No production matrix, workbook, scoring, reliability, or resolver behavior changes.

## Deferred Mid-Term Outline: Biological ISTD RT Transfer

Do not implement until Level 0 and Level 1 are reviewed.

Future goals:

- build current-code biological QC ISTD evidence from targeted outputs.
- validate clean-standard RT observations against biological QC ISTD drift.
- model RT drift by injection order, RT region, compound/group, and support status.
- report when clean standards do not transfer to biological matrix.

Hard rule:

- no RT correction may become production behavior until biological ISTD validation passes on current-code artifacts.

## Deferred Long-Term Outline: Response Drift Shadow

Do not implement until biological transfer evidence exists.

Future goals:

- response-drift preview remains shadow-only.
- zero, blank, missing, ND, absent, unchecked, and not-detected values must never be imputed.
- response correction must distinguish clean-only support from biological support.
- workbook review surface may be added after machine-readable Level 1 artifacts are stable.

Hard rule:

- no response-corrected matrix may be emitted as production output in this plan.

## Stop Conditions

Stop and write a decision note instead of continuing when:

- Level 0 cannot produce manifest, evidence TSV, and summary JSON.
- Level 1 preview rows cannot be safely rejoined to source matrix/cell input.
- source matrix hash changes during preview generation.
- product/MS2 statuses collapse `not_triggered`, `product_missing`, `unmapped`, or `parse_error`.
- biological ISTD evidence is stale but the run claims biological transfer.
- response preview creates corrected values from missing, blank, zero, absent, unchecked, or not-detected cells.
- any task requires changing targeted reliability, untargeted matrix identity, final matrix values, scoring, resolver behavior, or DNP normalization.

## Self-Review Checklist

- [ ] Level 0 and Level 1 are not conflated.
- [ ] `preview_ready` appears only when matrix preview sidecars exist.
- [ ] Matrix preview has stable rejoin keys and hash checks.
- [ ] Evidence bundle includes summary JSON.
- [ ] Manifest inventory lists every artifact.
- [ ] SDO/LEK, Mix STDs, and HCD source coverage are explicit.
- [ ] HCD/CID status mapping preserves review semantics.
- [ ] Mid/long-term work is deferred and cannot be accidentally executed as part of the first PR.
