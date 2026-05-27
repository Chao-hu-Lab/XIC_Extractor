# Area Integration Uncertainty Decision

**Date:** 2026-05-18
**Branch:** `codex/region-first-safe-merge-validation`
**Decision:** `inconclusive`

## Scope

This phase added audit-only area integration uncertainty tooling:

- shared `CellIntegrationAuditSummary`
- opt-in `alignment_cell_integration_audit.tsv`
- area integration uncertainty diagnostic report
- 8RAW validation note

It did not change production peak area, resolver behavior, targeted reliability,
workbook schema, alignment matrix identity, or output-level artifact contracts.

## Evidence

8RAW validation passed the audit plumbing contract:

- `alignment_matrix.tsv` hash unchanged.
- `alignment_review.tsv` hash unchanged.
- `alignment_cells.tsv` header unchanged.
- Opt-in integration sidecar was generated only with
  `--emit-alignment-integration-audit`.
- Detected and rescued cells had non-empty integration audit rows.
- The diagnostic classified all required focus labels:
  - `d3-N6-medA`
  - `15N5-8-oxodG`
  - `5-medC`
  - `5-hmdC`

The area uncertainty diagnostic reported:

- `area_consistent_low_uncertainty`: 1
- `boundary_sensitive`: 1
- `high_uncertainty`: 39
- `label_only_mismatch`: 15
- `missing_alignment_match`: 16
- `integration_context_incomplete`: 0
- `unexplained_area_mismatch`: 0

## Interpretation

The representative `d3-N6-medA` area mismatch did not reproduce in this run.
All eight `d3-N6-medA` rows had raw area ratio near 1.0 and evidence spine
mismatch reason `consistent`.

One `d3-N6-medA` row was `boundary_sensitive`, but that came from targeted
top-boundary alternative context rather than an observed raw area mismatch.

Most remaining matched rows were explainable as either:

- `high_uncertainty`: baseline/uncertainty metrics need review, but raw targeted
  and untargeted area ratios were often already consistent.
- `label_only_mismatch`: RT/area are consistent while diagnostic region/local
  mixture labels disagree.

## Decision

Final decision: `inconclusive`.

Keep the integration audit sidecar and diagnostic as audit tooling. Do not
change production area integration, default resolver, targeted reliability,
matrix identity, or scoring based on this phase.

## Next Trigger

The next production-oriented step should wait until a representative area
mismatch reproduces with this audit context enabled.

- If raw mismatch becomes baseline-consistent, revisit baseline uncertainty.
- If mismatch follows boundary deltas or top-boundary alternatives, revisit
  boundary/model-selection.
- If RT/area are consistent but labels disagree, tune diagnostic label
  calibration only.
- If required audit fields are missing, fix evidence plumbing before any
  algorithm discussion.

## 2026-05-25 P4 Formula Compatibility Note

The original decision used the legacy in-peak first-difference MAD
`area_uncertainty` formula. P4 changes the audit TSV value to
`baseline_residual_mad_v1` and emits TSV-local provenance columns. Prior
bucket counts and thresholds should not be compared numerically without
re-running the area uncertainty diagnostic.

