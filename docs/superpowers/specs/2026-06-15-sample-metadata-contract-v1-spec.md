# Sample metadata contract v1 spec

日期: 2026-06-15
狀態: runtime_parity_adapter
目標 tier: `partial_internal` -> `production_ready` for no-output injection-order parity; `blocked` for role-aware value behavior
控制台: [productization control plane](../plans/2026-06-15-productization-control-plane.md)

## Productization intake

- Feature/lane: `sample_metadata_contract_v1`
- Current tier:
  - `injection_order_source`: `production_ready` for no-output order projection
  - sample metadata roles: `blocked` for value-changing behavior
- Desired tier this slice:
  - `production_ready` for using `sample_metadata_v1` as an
    `injection_order_source` / sample-column / anchor-lookup parity input.
  - `blocked` for role/batch/matrix/exclusion behavior that would alter
    extraction, QC, alignment, normalized, counted, or matrix values.
- Product surface touched:
  - `xic_extractor.sample_metadata`
  - `scripts/validate_sample_metadata.py`
  - `xic_extractor.extraction.pipeline.resolve_injection_order`
  - `xic_extractor.alignment.pipeline.run_alignment`
  - `scripts/run_alignment.py --sample-column-injection-order`
  - `scripts/run_instrument_qc.py --method-doc` additive
    `instrument_qc_sample_metadata.tsv`
  - future sample metadata TSV/CSV schema
- Domain authority owner:
  - `xic_extractor.sample_metadata` owns the shared schema, role validation, exclusion guard, and injection-order projection.
  - Existing extraction uses sample metadata only to produce the same
    injection-order mapping shape as legacy `Sample_Name,Injection_Order`.
- Files/modules likely touched:
  - `xic_extractor/sample_metadata.py`
  - `scripts/validate_sample_metadata.py`
  - `xic_extractor/extraction/pipeline.py`
  - `xic_extractor/alignment/pipeline.py`
  - `scripts/run_alignment.py`
  - `tests/test_sample_metadata.py`
- Public contract affected:
  - Adds `sample_metadata_v1`.
  - Defines shared columns for sample identity, raw stem, injection order, role, batch, prep batch, matrix type, group, and exclusion.
- Expected output change: none for extraction/QC/alignment values. The only
  runtime behavior change is that `injection_order_source` can now point to a
  `sample_metadata_v1` CSV/TSV and produce the same order mapping.
  Instrument-QC may emit an additive `sample_metadata_v1` sidecar from the
  existing method-doc sequence manifest, but that sidecar must not alter
  instrument-QC quant/trend outputs. Alignment may use a `sample_metadata_v1`
  CSV/TSV through `--sample-column-injection-order`, but only to project the
  same injection-order mapping used to sort output sample columns.
- Expected-diff needed: no for this slice.
- Validation fixture: focused unit/CLI tests.
- Stop rule:
  - Stop before using sample metadata roles to change extraction, QC,
    alignment, normalization, or matrix values.
  - Stop before using sample roles to exclude rows or alter matrix values.
- Rollback rule:
  - Remove the validator and `sample_metadata` module; existing `injection_order_source` behavior remains.
- Downstream consumer:
  - extraction rolling priors, instrument QC, normalization/calibration, alignment.

## First slice contract

### Required columns

| Column | Meaning |
|---|---|
| `schema_version` | Must be `sample_metadata_v1`. |
| `sample_name` | Primary sample identity used by product outputs. |
| `raw_stem` | RAW filename stem alias; defaults to `sample_name` when blank. |
| `injection_order` | Positive integer when available. |
| `sample_role` | One of the supported role values. |
| `batch_id` | Acquisition batch when known. |
| `prep_batch_id` | Preparation batch when known. |
| `matrix_type` | Matrix/material label, free text for now. |
| `group` | Biological/analysis group label. |
| `excluded` | `TRUE` or `FALSE`; defaults to false when blank. |
| `exclusion_reason` | Required when `excluded=TRUE`. |

Identity rules:

- `sample_name` values must be unique.
- `raw_stem` values must be unique when present.
- `sample_name` and `raw_stem` share one alias namespace for injection-order
  projection. A value used as one row's `sample_name` cannot be another row's
  `raw_stem`, and a value used as one row's `raw_stem` cannot be another row's
  `sample_name`.
- A row may still use the same value for its own `sample_name` and `raw_stem`.

### Supported sample roles

- `study_sample`
- `qc`
- `pooled_qc`
- `blank`
- `calibrator`
- `solvent`
- `system_suitability`
- `unknown`

## Implementation closeout

- Implemented owner: `xic_extractor.sample_metadata`
- Implemented public surface:
  - `SAMPLE_METADATA_SCHEMA_VERSION = sample_metadata_v1`
  - `SAMPLE_METADATA_COLUMNS`
  - typed `SampleMetadata`
  - `is_sample_metadata_source(...)`
  - `load_sample_metadata(...)`
  - `sample_metadata_to_injection_order(...)`
  - `summarize_sample_metadata(...)`
  - `scripts/validate_sample_metadata.py`
  - `xic_extractor.instrument_qc.sequence_manifest_writers.write_sample_metadata_tsv(...)`
  - `scripts/run_instrument_qc.py --method-doc` writes
    `instrument_qc_sample_metadata.tsv`
  - `xic_extractor.alignment.pipeline.run_alignment(...)` accepts a
    `sample_metadata_v1` file through `sample_column_injection_order`
  - `scripts/run_alignment.py --sample-column-injection-order` documents the
    legacy injection-order CSV/XLSX path and the `sample_metadata_v1` CSV/TSV
    path
  - `tools/diagnostics/analyze_rt_normalization_anchors.py --sample-info`
    accepts `sample_metadata_v1` CSV/TSV for injection-based reference sources
- Runtime adoption:
  - `resolve_injection_order(...)` keeps legacy `Sample_Name,Injection_Order`
    files on the old parser.
  - If the configured `injection_order_source` is a `sample_metadata_v1`
    CSV/TSV, extraction projects it into the existing injection-order mapping.
  - If alignment receives a `sample_metadata_v1` CSV/TSV through
    `sample_column_injection_order`, it projects the same mapping and uses it
    only for final matrix/status sample-column ordering.
  - If RT-normalization anchor diagnostics receive a `sample_metadata_v1`
    CSV/TSV through `--sample-info`, they project the same mapping and use it
    only for `injection-local-median` / `injection-loess` reference lookup.
- Tier after runtime parity slice:
  - `production_ready` for no-output injection-order parity through
    `injection_order_source`, alignment sample-column ordering, and
    RT-normalization anchor diagnostic reference lookup.
  - `production_ready` for additive instrument-QC `sample_metadata_v1`
    sidecar projection from method-doc rows.
  - `blocked` for roles/batch/matrix/exclusion behavior that would change
    product values; those fields remain metadata only until a separate
    expected-diff gate and product decision exist.
- Expected-diff: not required; this slice does not mutate extraction outputs.
- Validation:
  - `python -m pytest tests\test_sample_metadata.py tests\test_injection_rolling.py tests\test_extractor_run.py -q`
  - `$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor\sample_metadata.py scripts\validate_sample_metadata.py tests\test_sample_metadata.py`
  - `$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor\sample_metadata.py scripts\validate_sample_metadata.py`
- Post-review hardening: validator now rejects cross-namespace
  `sample_name`/`raw_stem` alias collisions before projection to
  injection-order mapping.
- Residual blocker before full shared runtime adoption:
  - role-aware QC/blank/batch/matrix/exclusion behavior remains blocked
  - calibration/normalization must not write back to main matrix until an
    expected-diff gate and product decision exist
  - no product behavior may use sample roles for exclusion or correction until expected-diff gates exist

## Instrument-QC projection closeout, 2026-06-16

- `run_instrument_qc.py --method-doc` now writes
  `instrument_qc_sample_metadata.tsv` next to
  `instrument_qc_sequence_manifest.tsv`,
  `instrument_qc_injection_order.csv`,
  `instrument_qc_sequence_manifest.json`, and
  `instrument_qc_sequence_manifest.md`.
- The sidecar uses the shared `sample_metadata_v1` columns and includes only
  actual RAW rows: matched method-doc rows plus raw-dir-only instrument-QC rows.
  Unmatched/ambiguous doc-only rows remain in the sequence manifest and are not
  projected as sample metadata.
- Instrument-QC class maps to metadata role only:
  `SDOLEK -> system_suitability`, `MIX_STDS -> calibrator`,
  `BLANK -> blank`, `POOLED_QC -> pooled_qc`, otherwise `unknown`.
- Safe behavior boundary: the sidecar is additive metadata. The pipeline still
  receives the legacy `instrument_qc_injection_order.csv` for order parity; role,
  batch, matrix, group, and exclusion fields do not alter trend values,
  extraction output, counted detection, or matrix values.
- Validation:
  - `python -m pytest tests\test_instrument_qc_sequence_manifest.py tests\test_run_instrument_qc.py -q`
  - touched-file ruff/mypy for `sequence_manifest_writers.py`,
    `scripts/run_instrument_qc.py`, and focused tests.

## Alignment column-order projection closeout, 2026-06-17

- `run_alignment(...)` now detects `sample_metadata_v1` when
  `sample_column_injection_order` is provided.
- The shared metadata parser projects `sample_name` and `raw_stem` aliases into
  the existing injection-order mapping. Alignment still uses the same
  `order_sample_columns_by_injection(...)` behavior as the legacy
  `Sample_Name,Injection_Order` file.
- Safe behavior boundary: this changes sample-column ordering only when the
  user already supplied `--sample-column-injection-order`. It does not read
  sample roles, exclusions, batch, matrix type, or group to alter matrix values,
  counted detection, feature acceptance, or backfill activation.
- Validation:
  - `python -m pytest tests\test_alignment_pipeline_outputs.py::test_pipeline_orders_sample_columns_by_sample_metadata_v1 tests\test_alignment_pipeline_outputs.py::test_pipeline_orders_sample_columns_by_injection_order tests\test_alignment_pipeline_outputs.py::test_pipeline_keeps_input_sample_order_without_injection_source -q`
  - touched-file ruff for `xic_extractor\alignment\pipeline.py` and
    `tests\test_alignment_pipeline_outputs.py`

## RT-normalization anchor resolver closeout, 2026-06-17

- `analyze_rt_normalization_anchors.py --sample-info` now detects
  `sample_metadata_v1` when `reference_source` is `injection-local-median` or
  `injection-loess`.
- The shared metadata parser projects `sample_name` and `raw_stem` aliases into
  the existing injection-order mapping. Legacy `Sample_Name,Injection_Order`
  files still use the legacy parser.
- Safe behavior boundary: sample roles, exclusions, batch, matrix type, and
  group remain metadata only. They do not alter normalized values, matrix
  values, counted detection, feature acceptance, or calibration/main-matrix
  writes.
- Validation:
  - `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests\test_rt_normalization_anchors.py -q` (`16 passed`)
  - touched-file ruff/mypy recorded in the control-plane closeout
  - subagent reviewer `Descartes` found no P1/P2 blocker; the P3 request to
    cover `injection-loess` parity was fixed in the same focused suite

## Tier closeout, 2026-06-17

- The no-output resolver parity lane is now treated as `production_ready` for
  order projection only. This means the shared `sample_metadata_v1` parser may
  feed existing injection-order behavior in extraction, alignment sample-column
  ordering, and RT-normalization anchor lookup, and instrument-QC may emit the
  additive metadata sidecar.
- This does not authorize sample roles, blank/QC labels, batch, matrix type,
  group, or exclusion fields to change quant output, counted detection,
  normalized values, workbook values, or primary matrix values.
- Role-aware behavior remains `blocked` until there is an explicit
  expected-diff gate and a product decision describing how values may change.
