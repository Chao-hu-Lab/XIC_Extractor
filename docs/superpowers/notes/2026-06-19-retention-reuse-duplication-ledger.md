# Retention reuse duplication ledger

Date: 2026-06-19
Branch: `cc/framework-improvements`

## Verdict

The validation and fixture retention cleanup exposed a real shallow-module
pattern: multiple scripts owned the same mechanical responsibilities instead of
reusing one retention artifact interface. This note records the extracted
owners and the remaining seams that should be deepened before adding another
parallel productization or validation workflow.

## Extracted Owner

`xic_extractor/artifact_retention.py` now owns mechanical retention helpers:

- policy decision discovery from `RETENTION.md`
- TSV inventory loading and path indexing
- repo path normalization
- git tracked/untracked/deleted path enumeration
- missing-inventory detection
- retained-file size, line-count, and SHA256 metadata

`scripts/check_validation_artifact_retention.py` and
`scripts/check_superpowers_fixture_retention.py` are now thinner adapters. They
still own policy-specific validation rules, fixture authority rules, rendered
reference checks, and human-review/archive semantics.

`xic_extractor/alignment/quant_matrix_artifacts.py` now owns mechanical
QuantMatrix artifact helpers:

- summary JSON object loading
- source-root path resolution and repo-relative display paths
- output artifact records with SHA256
- bundle-relative artifact resolution with path-escape checks
- externalized `cell_provenance` replacement summary/local-copy resolution
- source-summary input hash comparison
- materialized `cell_provenance` replay from tracked full TSV,
  SHA-checked externalized local copy, or activation rerun
- replay `cell_provenance` hash comparison against tracked `source_sha256`

The QuantMatrix phase scripts remain adapters that declare their required
bundle labels and own phase-specific schema, authority, readiness, stale-output,
and Product Ready wording.

## Remaining Candidate Seams

- Schema-check mechanics can be shared, but schema authority statements should
  stay local to each productization phase.
- Phase scripts still own when replay is required and how stale-output/readiness
  results are interpreted; keep that authority local unless another caller
  needs the same orchestration.
- Rendered artifact reference checks currently belong to validation retention;
  move them only if fixtures or another surface grows the same need.

## Non-Goals

- Do not build one generic validation framework that hides domain authority.
- Do not move ProductWriter, default extraction, workbook, GUI, selected
  peak/area/counting, Backfill authority, or matrix semantics.
- Do not promote diagnostic or retention helper behavior into production
  maturity tiers without a separate expected-diff contract.
