# Instrument QC Phases 3-6 Consolidated Spec And Plan

## Purpose

This document consolidates the remaining instrument QC roadmap into one
spec/plan. Do not create one spec and one plan per future phase unless a later
phase becomes large enough to require its own reviewed plan.

Baseline already implemented:

- Phase 1: opt-in SDOLEK MS1 trend TSV/JSON/diagnostics.
- Phase 2: human-review workbook `instrument_qc_trend_sdolek.xlsx`.
- Method-doc sequence manifest diagnostic:
  `tools/diagnostics/instrument_qc_sequence_manifest.py`.
- SDOLEK calibration diagnostic:
  `tools/diagnostics/instrument_qc_sdolek_calibration.py`.

The next phases should extend instrument QC without changing targeted,
untargeted, matrix identity, peak selection, scoring, or the main extraction
pipeline.

## Core Contract

Instrument QC is an acquisition-review surface, not a production quantitation
gate.

- It remains opt-in.
- It reads RAW only when explicitly invoked.
- It does not change biological target extraction or untargeted alignment.
- TSV/JSON are the machine-readable contract.
- XLSX is the human review surface.
- `SampleInfo.xlsx` is downstream evidence only; method/sequence docs remain
  the authoritative order/source contract.
- LC-MS/MS is the only supported workflow. GC-MS is out of scope.
- HCD/wHCD evidence is deferred. Do not wire HCD into Phase 3-5.

## Evidence Semantics

### SDO/LEK Trend Meaning

SDO/LEK evidence should be interpreted as instrument/system suitability trend
evidence:

- RT movement: retention-axis drift or method/run condition change.
- Area movement: response/sensitivity trend.
- Width movement: chromatography or integration-definition change.
- Missing signal: possible acquisition, extraction, or sample/prep issue.

It is not a full chemical identity confirmation because current Phase 1/2
SDOLEK output is `MS1_ONLY`. If MS1 trend is unstable, report the instability;
do not claim the selected peak is chemically wrong unless a later MS2 evidence
phase proves that.

### Method Docs And Order

Injection order has exactly one first-class source in this repo:

```text
method / sequence docs -> sequence manifest -> Sample_Name,Injection_Order CSV
```

`SampleInfo.xlsx` may be compared during review, but it must not define
pipeline truth.

## Phase 3: Mix STDs And Blank Audit

### Goal

Add instrument QC coverage beyond SDOLEK:

- Mix STDs MS1 trend extraction.
- Blank TIC/BPC audit only after RAW reader capability is characterized.
- Optional workbook sheets for the new instrument QC surfaces.

### Scope

Phase 3 is audit-only.

Allowed:

- Add a focused Mix STDs target registry.
- Add Mix STDs trend TSV/JSON outputs.
- Add `Mix STDs Trend` workbook sheet.
- Add a RAW-reader capability check for TIC/BPC before implementing Blank.
- Add Blank TIC/BPC TSV/JSON only if the capability exists and is testable.
- Deduplicate `/STDs` vs `/Pairs` sources before extracting Mix STDs.

Target-source rule:

- Mix STDs targets must come from a reviewed instrument-QC target registry or
  method-doc-derived config.
- A user-reviewed existing XIC `targets.csv` is accepted when explicitly passed
  with `--mixstds-target-registry`; only MS1 fields (`label/mz/rt_min/rt_max/
  ppm_tol`) are used.
- Do not silently reuse biological target lists, targeted extraction configs,
  or FeatureHunter feature lists as instrument-QC truth.

Not allowed:

- No HCD/wHCD.
- No sample-group classifier changes for biological samples.
- No hidden extraction from biological RAWs.
- No threshold tuning based on one batch unless recorded as audit-only.
- No default lifecycle writes.

### Output Contract

Recommended new outputs:

```text
instrument_qc_mixstds_trend.tsv
instrument_qc_mixstds_trend.json
instrument_qc_mixstds_diagnostics.tsv
instrument_qc_blank_tic.tsv
instrument_qc_blank_tic.json
```

Workbook additions:

```text
Overview
SDOLEK Trend
Mix STDs Trend
Blank TIC (only when supported)
Diagnostics
```

If Blank support is not implemented yet, the workbook should omit `Blank TIC`
and report `BLANK_TIC_UNSUPPORTED` in diagnostics.
Sheet order must stay stable when `Blank TIC` is present or absent, and
`Diagnostics` remains the final sheet.

### Acceptance

- SDOLEK output remains unchanged except for workbook sheet additions.
- Mix STDs extraction never includes biological RAWs.
- Duplicate `/STDs` and `/Pairs` candidates are reported, not double counted.
- Blank support has a RAW-reader capability test before implementation.
- Missing Blank support fails as a documented diagnostic, not a crash.

## Phase 4: Method-Doc Integration Into Instrument QC CLI

### Goal

Make method/sequence docs first-class in `scripts/run_instrument_qc.py`, so the
operator does not need to manually run a separate manifest converter first.

### Scope

Allowed:

- Add `--method-doc` to `scripts/run_instrument_qc.py`.
- When supplied, generate the sequence manifest under `--output-dir`.
- Use the generated `instrument_qc_injection_order.csv` for the same run.
- Continue accepting `--injection-order-source` for already generated,
  docs-derived CSVs.
- Preserve the standalone manifest diagnostic CLI for manual review.

Not allowed:

- No `--sample-info` input.
- No fallback to `SampleInfo.xlsx`.
- No hidden inference from file modification time or folder ordering.
- No biological sample ordering changes.

### Output Contract

When `--method-doc` is supplied, write:

```text
instrument_qc_sequence_manifest.tsv
instrument_qc_injection_order.csv
instrument_qc_sequence_manifest.json
instrument_qc_sequence_manifest.md
```

Then the trend outputs should use that generated injection-order CSV.

### Acceptance

- Running with `--method-doc` produces the same manifest contract as the
  standalone diagnostic.
- Repeated doc display names are matched to suffix RAW stems by sequence order.
- `SampleInfo.xlsx` is rejected with a clear error if supplied as method doc.
- Missing or unsupported method doc returns exit code `2`, not a traceback.

## Phase 5: Cross-Batch Lifecycle Dataset

### Goal

Persist instrument QC summaries across batches only when explicitly requested,
so long-term RT/area/width trends can be reviewed without reprocessing old RAWs.

### Scope

Allowed:

- Add explicit opt-in flags:

```powershell
--append-lifecycle
--instrument-id <id>
--lifecycle-root <path>
--allow-duplicate-lifecycle-run
```

- Append run-level and row-level summaries.
- Use atomic write or temp-file replacement for append safety.
- Record code version, run timestamp, instrument id, method-doc source, and
  output paths.

Not allowed:

- No hidden writes to user home.
- No automatic lifecycle append by default.
- No lifecycle mutation during unit tests unless using `tmp_path`.
- No biological result data in lifecycle files.

### Output Contract

Recommended lifecycle files:

```text
instrument_qc_lifecycle_runs.tsv
instrument_qc_lifecycle_sdolek.tsv
instrument_qc_lifecycle_mixstds.tsv
instrument_qc_lifecycle_blank.tsv
instrument_qc_lifecycle_summary.json
```

Minimum run-level columns:

```text
run_id
timestamp_utc
instrument_id
method_doc
raw_dir
output_dir
code_version
sdolek_row_count
mixstds_row_count
blank_row_count
diagnostic_counts
```

### Acceptance

- No lifecycle files are written without `--append-lifecycle`.
- Missing `--instrument-id` or `--lifecycle-root` with append enabled returns
  exit code `2`.
- Lifecycle append computes a `run_fingerprint` from `instrument_id`,
  `method_doc`, `raw_dir`, source artifact paths, source artifact hashes, and
  code version.
- Re-running an existing fingerprint returns exit code `2` by default and
  reports `DUPLICATE_LIFECYCLE_RUN`.
- Duplicate append is allowed only when `--allow-duplicate-lifecycle-run` is
  explicitly supplied.
- Lifecycle files can be read by a small diagnostic without RAW access.

## Phase 6: Instrument QC Decision Report And MS2 Readiness Gate

### Goal

Create a compact decision report that turns the collected QC evidence into a
human-readable review outcome, then decide whether an MS2 evidence phase is
actually justified.

### Scope

Allowed:

- Add an HTML or Markdown decision report from existing instrument QC artifacts.
- Summarize SDOLEK, Mix STDs, Blank, method-doc metadata, and lifecycle status.
- Classify run-level state:
  - `qc_review_ready`
  - `metadata_incomplete`
  - `sensitivity_review`
  - `rt_drift_review`
  - `blank_contamination_review`
  - `identity_evidence_limited`
  - `insufficient_evidence`
- Add an MS2 readiness section that says whether SDO/LEK MS2 evidence should
  be implemented later.

Not allowed:

- No HCD/wHCD implementation in Phase 6.
- No automatic production pass/fail gate.
- No targeted/untargeted result mutation.
- No claim that MS1-only evidence proves chemical identity.

### MS2 Readiness Rule

Recommend a later MS2 phase only if all are true:

- SDO/LEK MS1 trend remains scientifically useful after Phase 3-5.
- A representative method actually contains usable CID/wHCD product-ion scans.
- The RAW reader can expose the required MS2 evidence deterministically.
- Manual review shows MS1-only ambiguity that cannot be resolved with RT/area
  trend evidence alone.

If any condition fails, keep SDO/LEK as MS1-only instrument trend evidence.

### Acceptance

- The decision report opens without needing TSV knowledge.
- First screen shows verdict, method-doc status, row counts, and top concerns.
- It links or names source artifacts.
- It states explicitly that MS1-only SDO/LEK is trend evidence, not identity
  confirmation.
- It does not add new extraction rules.

## Implementation Checkpoints

### Checkpoint 0: Preflight And Contract Review

- Confirm active branch/worktree.
- Confirm Phase 1/2 tests still pass.
- Confirm no dirty unrelated changes.
- Update this file if the user changes phase ordering.

### Checkpoint 1: Phase 3 Mix STDs Characterization

- Add/confirm target registry structure.
- Add tests for Mix STDs classification and `/STDs` vs `/Pairs` dedup.
- Add RAW-reader capability probe for Blank TIC/BPC.
- Stop before Blank implementation if TIC/BPC support is absent.

Expected tests:

```powershell
uv --cache-dir .uv-cache run pytest tests\test_instrument_qc_mixstds.py tests\test_instrument_qc_blank.py -q
```

Review gate:

- No biological RAWs enter the candidate set.
- Blank support status is explicit.

### Checkpoint 2: Phase 3 Outputs

- Implement Mix STDs TSV/JSON/diagnostics.
- Add workbook sheet if Mix STDs outputs exist.
- Add Blank TIC/BPC only if Checkpoint 1 proved support.
- Run synthetic tests and one real-data smoke.

Example smoke command:

```powershell
uv --cache-dir .uv-cache run python scripts\run_instrument_qc.py `
  --raw-dir C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R `
  --output-dir output\instrument_qc\phase3_mixstds_smoke `
  --mode sdolek `
  --emit-mixstds `
  --mixstds-target-registry <reviewed-instrument-qc-mixstds-targets.csv>
```

Review gate:

- SDOLEK TSV/JSON unchanged.
- Workbook sheet order is stable.

### Checkpoint 3: Phase 4 Method-Doc CLI Integration

- Add `--method-doc`.
- Generate manifest into output dir.
- Feed generated injection-order CSV into SDOLEK/Mix STDs extraction.
- Keep standalone manifest CLI.

Example command:

```powershell
uv --cache-dir .uv-cache run python scripts\run_instrument_qc.py `
  --raw-dir C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R `
  --output-dir output\instrument_qc\phase4_method_doc_smoke `
  --mode sdolek `
  --method-doc "C:\Users\user\Desktop\NTU cancer\2025台大乳癌組織數據for Jia\20260105中研院台大Breast cancer tissue\20260105 中研院分析.docx"
```

Expected tests:

```powershell
uv --cache-dir .uv-cache run pytest tests\test_instrument_qc_method_doc_cli.py tests\test_run_instrument_qc.py -q
```

Review gate:

- `SampleInfo.xlsx` rejection is covered by tests.
- `--help` explains method-doc vs injection-order-source.

### Checkpoint 4: Phase 5 Lifecycle Append

- Add opt-in flags and validation.
- Add lifecycle writer module.
- Add duplicate-run behavior.
- Add tests using `tmp_path`.

Example command:

```powershell
uv --cache-dir .uv-cache run python scripts\run_instrument_qc.py `
  --raw-dir C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R `
  --output-dir output\instrument_qc\phase5_lifecycle_smoke `
  --mode sdolek `
  --method-doc "C:\Users\user\Desktop\NTU cancer\2025台大乳癌組織數據for Jia\20260105中研院台大Breast cancer tissue\20260105 中研院分析.docx" `
  --append-lifecycle `
  --instrument-id Orbitrap-20260105 `
  --lifecycle-root output\instrument_qc_lifecycle
```

Expected tests:

```powershell
uv --cache-dir .uv-cache run pytest tests\test_instrument_qc_lifecycle.py tests\test_run_instrument_qc.py -q
```

Review gate:

- No writes happen without `--append-lifecycle`.
- No user-home writes.

### Checkpoint 5: Phase 6 Decision Report

- Add decision model and renderer.
- Generate compact Markdown or HTML from existing artifacts.
- Include MS2 readiness section, but do not implement MS2 extraction.

Example command:

```powershell
uv --cache-dir .uv-cache run python tools\diagnostics\instrument_qc_decision_report.py `
  --instrument-qc-dir output\instrument_qc\phase5_lifecycle_smoke `
  --output-md output\instrument_qc\phase6_decision_report\instrument_qc_decision_report.md
```

Expected tests:

```powershell
uv --cache-dir .uv-cache run pytest tests\test_instrument_qc_decision_report.py -q
```

Review gate:

- The report is human-first and does not require reading TSVs first.
- It does not overclaim MS1-only identity evidence.

### Checkpoint 6: Final Validation

Focused tests:

```powershell
uv --cache-dir .uv-cache run pytest tests\test_instrument_qc_classification.py tests\test_instrument_qc_pipeline.py tests\test_instrument_qc_writers.py tests\test_instrument_qc_workbook.py tests\test_run_instrument_qc.py -q
```

Phase-specific tests:

```powershell
uv --cache-dir .uv-cache run pytest tests\test_instrument_qc_mixstds.py tests\test_instrument_qc_blank.py tests\test_instrument_qc_method_doc_cli.py tests\test_instrument_qc_lifecycle.py tests\test_instrument_qc_decision_report.py -q
```

Final checks:

```powershell
uv --cache-dir .uv-cache run ruff check .
uv --cache-dir .uv-cache run mypy xic_extractor
```

Real-data smoke:

- Run only explicitly.
- Do not commit real-data output.
- Record output paths and row counts in the plan or decision note.

## Stop Conditions

Stop and ask for direction if:

- Mix STDs target definitions are not available or conflict with method docs.
- Blank TIC/BPC cannot be accessed by the current RAW reader.
- Method-doc parsing cannot reliably map repeated display names to RAW stems.
- Lifecycle append needs a database or locking model beyond flat files.
- MS2 evidence would require HCD/wHCD implementation before the user approves
  that scope.

## Expected Phase Outcomes

- Phase 3: instrument QC covers SDOLEK plus Mix STDs, and Blank support is
  either implemented or explicitly blocked by RAW-reader capability.
- Phase 4: method docs become first-class input to the instrument QC CLI.
- Phase 5: lifecycle trends can be built intentionally across batches.
- Phase 6: a compact decision report tells the operator what happened and
  whether later MS2 evidence is justified.

## GSTACK REVIEW REPORT

| Review | Trigger | Why | Runs | Status | Findings |
|--------|---------|-----|------|--------|----------|
| Eng Review | `/plan-eng-review` | Architecture & tests | 1 | CLEAR | Tightened Mix STDs source-of-truth, conditional Blank sheet contract, lifecycle duplicate semantics, and phase-specific validation commands. |
| DX Review | `/plan-devex-review` | Developer execution clarity | 1 | CLEAR | Added copy-paste smoke commands, concrete test filenames, explicit duplicate flag behavior, and stable workbook/report expectations. |

- **UNRESOLVED:** 0
- **VERDICT:** ENG + DX CLEARED — ready to implement Phase 3, with each checkpoint reviewed before proceeding.
