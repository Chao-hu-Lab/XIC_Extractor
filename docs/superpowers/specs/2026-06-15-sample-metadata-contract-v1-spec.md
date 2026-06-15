# Sample metadata contract v1 spec

日期: 2026-06-15
狀態: runtime_parity_adapter
目標 tier: `partial_internal` -> `production_surface` for injection-order parity; `production_candidate` for roles
控制台: [productization control plane](../plans/2026-06-15-productization-control-plane.md)

## Productization intake

- Feature/lane: `sample_metadata_contract_v1`
- Current tier:
  - `injection_order_source`: `production_surface` for order only
  - sample metadata roles: `partial_internal`
- Desired tier this slice:
  - `production_surface` for using `sample_metadata_v1` as an
    `injection_order_source` parity input.
  - `production_candidate` for role/batch/matrix schema only.
- Product surface touched:
  - `xic_extractor.sample_metadata`
  - `scripts/validate_sample_metadata.py`
  - `xic_extractor.extraction.pipeline.resolve_injection_order`
  - future sample metadata TSV/CSV schema
- Domain authority owner:
  - `xic_extractor.sample_metadata` owns the shared schema, role validation, exclusion guard, and injection-order projection.
  - Existing extraction uses sample metadata only to produce the same
    injection-order mapping shape as legacy `Sample_Name,Injection_Order`.
- Files/modules likely touched:
  - `xic_extractor/sample_metadata.py`
  - `scripts/validate_sample_metadata.py`
  - `xic_extractor/extraction/pipeline.py`
  - `tests/test_sample_metadata.py`
- Public contract affected:
  - Adds `sample_metadata_v1`.
  - Defines shared columns for sample identity, raw stem, injection order, role, batch, prep batch, matrix type, group, and exclusion.
- Expected output change: none for extraction/QC/alignment values. The only
  runtime behavior change is that `injection_order_source` can now point to a
  `sample_metadata_v1` CSV/TSV and produce the same order mapping.
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
- Runtime adoption:
  - `resolve_injection_order(...)` keeps legacy `Sample_Name,Injection_Order`
    files on the old parser.
  - If the configured `injection_order_source` is a `sample_metadata_v1`
    CSV/TSV, extraction projects it into the existing injection-order mapping.
- Tier after runtime parity slice:
  - `production_surface` for injection-order parity through
    `injection_order_source`.
  - `production_candidate` for roles/batch/matrix/exclusion metadata; those
    fields still do not affect product values.
- Expected-diff: not required; this slice does not mutate extraction outputs.
- Validation:
  - `python -m pytest tests\test_sample_metadata.py tests\test_injection_rolling.py tests\test_extractor_run.py -q`
  - `$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor\sample_metadata.py scripts\validate_sample_metadata.py tests\test_sample_metadata.py`
  - `$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor\sample_metadata.py scripts\validate_sample_metadata.py`
- Post-review hardening: validator now rejects cross-namespace
  `sample_name`/`raw_stem` alias collisions before projection to
  injection-order mapping.
- Residual blocker before full shared runtime adoption:
  - instrument-QC sequence manifest is not yet projected into `sample_metadata_v1`
  - alignment and normalization do not yet consume this resolver
  - no product behavior may use sample roles for exclusion or correction until expected-diff gates exist
