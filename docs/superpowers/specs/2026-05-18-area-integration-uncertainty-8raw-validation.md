# Area Integration Uncertainty 8RAW Validation

**Date:** 2026-05-18
**Branch:** `codex/region-first-safe-merge-validation`
**Decision status:** `D3_AREA_CHECK_INCONCLUSIVE`

## Scope

This validation checked the audit-only area integration uncertainty plumbing.
It did not change targeted extraction, production alignment quantification,
matrix identity, workbook schema, or `alignment_cells.tsv` schema.

Targeted 8RAW was not rerun because the existing CP1 artifact already contained
the required selected candidate baseline and uncertainty fields.

## Inputs

- Targeted artifact:
  `output/validation_harness/evidence_spine_tracegroup_cp1_8raw_keepcsv/tissue_8raw_local_minimum/`
- Discovery index:
  `output/discovery/region_safe_merge_v1_8raw_dR/discovery_batch_index.csv`
- Baseline alignment for hash comparison:
  `output/alignment/evidence_spine_tracegroup_cp2_8raw_region_first_safe_merge/`

## Generated Validation Artifacts

- Alignment with opt-in integration audit:
  `output/alignment/area_uncertainty_cp4_8raw_region_first_safe_merge/`
- Evidence spine consistency:
  `output/diagnostics/area_uncertainty_cp4_evidence_spine_8raw/`
- Area integration uncertainty diagnostic:
  `output/diagnostics/area_integration_uncertainty_cp4_8raw/`
- Alignment timing:
  `output/diagnostics/area_uncertainty_cp4_8raw_region_first_safe_merge_alignment_timing.json`

Real-data output artifacts are validation outputs only and are not committed.

## Contract Checks

- `alignment_matrix.tsv` hash unchanged:
  `3EA29292127A94328D1A7B1EF072B0A911D609555AC0B4153C2166141202CA7E`
- `alignment_review.tsv` hash unchanged:
  `9BAF49F353FBCF4CAA1299CCABE0B2A31DDBE979A5CE5D81A61957290204AACA`
- `alignment_cells.tsv` header unchanged.
- `alignment_cell_integration_audit.tsv` exists only because
  `--emit-alignment-integration-audit` was explicitly passed.
- Integration audit rows by status:
  - `detected`: 2961
  - `rescued`: 3318
  - `duplicate_assigned`: 10687
- Detected/rescued alignment cells both have matching integration audit row
  counts in the sidecar.

## Area Uncertainty Summary

Rows checked: 72

Bucket counts:

- `area_consistent_low_uncertainty`: 1
- `boundary_sensitive`: 1
- `high_uncertainty`: 39
- `label_only_mismatch`: 15
- `missing_alignment_match`: 16
- `integration_context_incomplete`: 0
- `unexplained_area_mismatch`: 0

## Focus Target Observations

`d3-N6-medA` did not reproduce an area mismatch in this validation. All eight
rows matched the same untargeted family (`FAM000242`) with raw area ratio near
1.0 and evidence spine mismatch reason `consistent`.

`Breast_Cancer_Tissue_pooled_QC5 / d3-N6-medA` was classified as
`boundary_sensitive` because the selected targeted top-boundary alternative
area ratio was `0.64729`; this is boundary-model context, not a reproduced raw
area mismatch.

`15N5-8-oxodG`, `5-medC`, and `5-hmdC` were explicitly classified. Their main
signals were `high_uncertainty` and `label_only_mismatch`, while raw area ratios
remained broadly consistent in the matched rows.

## Verdict

The audit plumbing passes the 8RAW contract checks, but the representative
`d3-N6-medA` area mismatch is absent in this run. The validation conclusion is
therefore `D3_AREA_CHECK_INCONCLUSIVE`.

Do not recommend production area, resolver, scoring, reliability, or matrix
identity changes from this checkpoint. Keep the diagnostic sidecar and
uncertainty report as audit tooling only.

