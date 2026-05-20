# Instrument QC SDOLEK Calibration v1 Implementation Plan

> **For agentic workers:** Implement checkpoint-by-checkpoint. Use
> `superpowers:executing-plans` if that workflow is available. Use subagents only
> when the user explicitly authorizes delegated/parallel work. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the missing method-doc entry point plus an audit-only calibration/report layer for Phase 1 SDOLEK outputs, separating NoSplit-prior mismatch from batch-relative RT/area/width trends.

**Architecture:** Implement two small diagnostic pipelines under `tools/diagnostics/` plus focused domain helpers in `xic_extractor.instrument_qc`. The first converts method / sequence docs into an auditable sequence manifest and normalized injection-order CSV. The second reads Phase 1 TSV/JSON plus that docs-derived CSV and writes calibrated TSV/JSON/Markdown. Neither pipeline opens RAW or changes Phase 1 extraction.

**Injection-order source rule:** the only accepted source is method/sequence docs
or a manifest generated from those docs. `SampleInfo.xlsx` is downstream output
evidence, not a valid pipeline input or fallback source.

**Tech Stack:** Python, `csv`, `json`, `statistics`, existing `injection_rolling.read_injection_order`, bundled docx reader utilities / `python-docx` if available in the project environment, pytest.

---

## Checkpoint 0: Freeze Phase 1 Review Fixes

**Files:**

- Modified by review:
  - `xic_extractor/instrument_qc/pipeline.py`
  - `xic_extractor/instrument_qc/writers.py`
  - `tests/test_instrument_qc_pipeline.py`
  - `tests/test_instrument_qc_writers.py`
  - `tests/test_run_instrument_qc.py`

- [x] Confirm Phase 1 still passes:

```powershell
uv --cache-dir .uv-cache run pytest tests\test_instrument_qc_classification.py tests\test_instrument_qc_pipeline.py tests\test_instrument_qc_writers.py tests\test_run_instrument_qc.py -q
uv --cache-dir .uv-cache run ruff check .
uv --cache-dir .uv-cache run mypy xic_extractor
```

- [x] Commit review fixes before Phase 2 implementation:

```powershell
git add xic_extractor/instrument_qc/pipeline.py xic_extractor/instrument_qc/writers.py tests/test_instrument_qc_pipeline.py tests/test_instrument_qc_writers.py tests/test_run_instrument_qc.py
git commit -m "fix: preserve instrument qc metadata and dll defaults"
```

Review gate:

- Real SDOLEK smoke returns 22 detected rows.
- JSON contains `metadata_source_status`.
- The reviewed Phase 2 spec/plan is committed separately or intentionally kept
  uncommitted for user review; do not mix Phase 1 bug fixes with Phase 2 code.

## Checkpoint 1: Method-Doc Sequence Manifest

**Files:**

- Create: `xic_extractor/instrument_qc/sequence_manifest.py`
- Create: `xic_extractor/instrument_qc/sequence_manifest_writers.py`
- Create: `tools/diagnostics/instrument_qc_sequence_manifest.py`
- Test: `tests/test_instrument_qc_sequence_manifest.py`
- Test: `tests/test_instrument_qc_sequence_manifest_cli.py`

Tasks:

- [x] Parse method / sequence doc text into candidate injection entries.
- [x] Classify entries into instrument QC classes where possible:
  `SDOLEK`, `MIX_STDS`, `BLANK`, `POOLED_QC`, `UNKNOWN`.
- [x] Normalize docs display names to candidate RAW stems using explicit,
  auditable rules.
- [x] Match normalized stems against RAW stems under the supplied raw root.
- [x] Write `instrument_qc_sequence_manifest.tsv`.
- [x] Write compatibility `instrument_qc_injection_order.csv` with
  `Sample_Name,Injection_Order`.
- [x] Write JSON/Markdown summary with matched / unmatched / ambiguous counts.
- [x] State that `SampleInfo.xlsx` can only be used as downstream comparison
  evidence, not as a pipeline input or fallback.

Focused tests:

- synthetic doc text with SDO/LEK entries produces manifest rows;
- manifest preserves `doc_display_name`, `raw_stem`, `injection_order`, class,
  match status, confidence, and reason;
- normalized injection-order CSV contains only matched rows;
- unmatched docs rows are retained in manifest but not silently passed as valid
  order rows;
- `SampleInfo.xlsx` is not accepted as an input flag or fallback source;
- ambiguous name matches require manual review status.

Review gate:

- No plan or code path treats `SampleInfo` as source truth.
- Name reconciliation is isolated to this module.
- The output manifest can explain exactly why SDO/LEK rows did or did not match
  RAW stems.

## Checkpoint 2: Calibration Domain Model

**Files:**

- Create: `xic_extractor/instrument_qc/calibration.py`
- Test: `tests/test_instrument_qc_calibration.py`

Tasks:

- [x] Add dataclasses for calibrated rows and summary.
- [x] Parse Phase 1 trend rows from TSV.
- [x] Compute compound-level medians for RT, area, and width.
- [x] Compute batch-relative deltas and ratios.
- [x] Preserve NoSplit reference fields, including
  `reference_base_width_min` and `base_width_ratio_to_reference`.
- [x] Assign `prior_conflict_flags`, `batch_trend_flags`, and `review_bucket`.
- [x] Carry Phase 1 metadata source status into the calibration summary.
- [x] Report Phase 2 injection-order join status without making missing
  injection order a row-level failure.
- [x] Mark the metadata source contract as `method_docs_only`.
- [x] Reject or clearly classify non-doc-derived order files as invalid by
  documented provenance; do not silently accept `SampleInfo.xlsx` as equivalent.

Focused tests:

- detected SDO/LEK rows with stable batch metrics become `stable_ms1_trend`;
- strong NoSplit RT mismatch with stable batch metrics becomes `prior_reference_mismatch`;
- batch-relative area / RT / width outlier takes precedence over prior-only
  mismatch while preserving prior flags;
- `MS1_ONLY` alone does not become `identity_evidence_insufficient`;
- missing injection order does not block batch-relative medians;
- missing injection order suppresses only order-dependent drift flags;
- partial injection-order match reports `partial_match` metadata status;
- downstream `SampleInfo.xlsx` is not accepted as a valid source contract in
  calibration tests;
- fewer than 3 detected rows leaves batch-relative fields blank;
- non-detected rows become `not_detected_or_error`;
- `identity_evidence` remains `MS1_ONLY`.

Review gate:

- No RAW reader import.
- No targeted/untargeted imports.

## Checkpoint 3: Calibration Writers

**Files:**

- Create: `xic_extractor/instrument_qc/calibration_writers.py`
- Test: `tests/test_instrument_qc_calibration_writers.py`

Tasks:

- [x] Write `instrument_qc_sdolek_calibrated_trend.tsv`.
- [x] Write `instrument_qc_sdolek_calibration_summary.json`.
- [x] Write concise `instrument_qc_sdolek_review.md`.

Focused tests:

- TSV headers match spec exactly.
- JSON summary includes counts by compound/status/bucket.
- JSON summary includes `phase1_metadata_source_status` and
  `calibration_metadata_status`.
- Markdown report includes verdict, MS1-only caveat, detected counts, and top review rows.

Review gate:

- Markdown first section is readable without opening TSV.
- No workbook output.

## Checkpoint 4: Calibration Diagnostic CLI

**Files:**

- Create: `tools/diagnostics/instrument_qc_sdolek_calibration.py`
- Test: `tests/test_instrument_qc_sdolek_calibration_cli.py`

Tasks:

- [x] Add required args: `--trend-tsv`, `--trend-json`, `--output-dir`.
- [x] Add optional arg: `--injection-order-source`.
- [x] Validate missing required columns with clear errors.
- [x] Return exit code `0` on success and `2` on user-correctable input errors.
- [x] Do not reread RAW and do not import RAW reader modules.

Focused tests:

- CLI writes all three artifacts from synthetic Phase 1 TSV/JSON.
- missing trend TSV returns `2`;
- missing required column returns `2` with column name;
- docs-derived injection order joins rows when supplied.
- missing docs-derived injection order still exits `0` for exploratory
  calibration and reports `injection_order_status = missing`, but cannot satisfy
  the full Phase 2 real-data acceptance gate.
- a source identified as downstream `SampleInfo.xlsx` returns `2` or reports
  `injection_order_status = invalid` with a clear reason.

Review gate:

- CLI is diagnostic-only.
- It does not import RAW reader.

## Checkpoint 5: Real 11-RAW SDOLEK Validation

First generate docs-derived manifest:

```powershell
uv --cache-dir .uv-cache run python tools\diagnostics\instrument_qc_sequence_manifest.py `
  --method-doc "C:\Users\user\Desktop\NTU cancer\2025台大乳癌組織數據for Jia\20260105中研院台大Breast cancer tissue\20260105 中研院分析.docx" `
  --raw-dir C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R `
  --output-dir output\instrument_qc\20260105_sequence_manifest_cp1
```

Inputs:

```text
output\instrument_qc\20260105_sdo_lek_review_fix\instrument_qc_sdolek_trend.tsv
output\instrument_qc\20260105_sdo_lek_review_fix\instrument_qc_sdolek_trend.json
output\instrument_qc\20260105_sequence_manifest_cp1\instrument_qc_injection_order.csv
```

Run:

```powershell
uv --cache-dir .uv-cache run python tools\diagnostics\instrument_qc_sdolek_calibration.py `
  --trend-tsv output\instrument_qc\20260105_sdo_lek_review_fix\instrument_qc_sdolek_trend.tsv `
  --trend-json output\instrument_qc\20260105_sdo_lek_review_fix\instrument_qc_sdolek_trend.json `
  --injection-order-source output\instrument_qc\20260105_sequence_manifest_cp1\instrument_qc_injection_order.csv `
  --output-dir output\instrument_qc\20260105_sdo_lek_calibration_cp4
```

Acceptance:

- Manifest exists and lists the SDO/LEK docs entries with match status.
- Compatibility injection-order CSV exists and is docs-derived.
- Output has 22 calibrated rows.
- Report verdict is `review_ready` if all rows are detected.
- Matched SDO/LEK rows have injection order filled; unmatched names are reported
  in manifest, not silently ignored.
- LEK prior RT mismatch is described as prior/reference conflict, not chemical identity confirmation.
- Width mismatch is described as prior-width comparability issue if batch widths are internally stable.
- No real-data output is committed.

Actual CP4 smoke result:

- output directory:
  `output\instrument_qc\20260105_sdo_lek_calibration_cp4`
- report verdict: `review_ready`
- calibrated rows: 22
- injection-order status: `partial_match`
- matched injection-order rows: 16
- unmatched injection-order rows: 6

## Checkpoint 6: Final Validation

Run:

```powershell
uv --cache-dir .uv-cache run pytest tests\test_instrument_qc_sequence_manifest.py tests\test_instrument_qc_sequence_manifest_cli.py -q
uv --cache-dir .uv-cache run pytest tests\test_instrument_qc_calibration.py tests\test_instrument_qc_calibration_writers.py tests\test_instrument_qc_sdolek_calibration_cli.py -q
uv --cache-dir .uv-cache run pytest tests\test_instrument_qc_classification.py tests\test_instrument_qc_pipeline.py tests\test_instrument_qc_writers.py tests\test_run_instrument_qc.py -q
uv --cache-dir .uv-cache run ruff check .
uv --cache-dir .uv-cache run mypy xic_extractor
uv --cache-dir .uv-cache run mypy tools\diagnostics\instrument_qc_sdolek_calibration.py
```

Actual final validation:

- instrument QC focused suite: 49 passed.
- `ruff check .`: passed.
- `mypy xic_extractor`: passed.
- `mypy tools\diagnostics\instrument_qc_sdolek_calibration.py`: passed.

Final decision:

- `calibration_ready`: Phase 2 diagnostic explains SDO/LEK trend without new RAW logic.
- `metadata_needed`: method-doc-derived injection order/source manifest is required before useful order-dependent drift interpretation.
- `ms2_evidence_needed`: MS1-only evidence cannot explain LEK/SDO identity enough for next use.

Default target conclusion:

```text
calibration_ready
```
