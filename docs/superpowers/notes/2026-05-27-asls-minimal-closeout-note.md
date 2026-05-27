# AsLS Minimal Closeout Note

**Date:** 2026-05-27
**Verdict:** ASLS is closed for the Phase 1 supported scope. No additional
external-tool audit, 85RAW rerun, or Tier C truth work is required before
starting method-preserving cleanup or handoff-spine work.

## Closed Scope

- `baseline_integration_method` defaults to `asls`.
- The default promoted schema uses AsLS for
  `alignment_cell_integration_audit.tsv:area_baseline_corrected`.
- Linear-edge rollback columns remain temporary audit compatibility fields:
  `area_baseline_corrected_linear_edge` and `baseline_score_linear_edge`.
- 8RAW promoted-schema validation found no identity / RT / boundary hard
  blocker for the supported audit-promotion scope.
- 85RAW `validation-minimal + super-window` foreground validation completed and
  reproduced the accepted `alignment_matrix.tsv`, `alignment_review.tsv`, and
  `alignment_cells.tsv` delivery surface, with known benchmark WARN exceptions
  already recorded.
- P2c B1/B2 truth validation supports C1b planning only:
  `GO_FOR_C1B_PLAN_SYNTHETIC_ONLY` for planning and `REQUIRES_TIER_C` for
  linear-edge retirement.

## Stop Conditions

Do not spend more Phase 1 effort trying to prove what is already decided:

- old strict linear-edge RSD comparison is not the source of truth;
- P3/asari/MassCube is external-reference evidence only and is not a P2b gate;
- P6/OBI-Warp is not triggered by the current RT evidence;
- area differences caused by changing the baseline are not a blocker when
  identity, RT, boundary, and primary-delivery outputs remain accepted.

## Still Blocked

- Do not delete `integrate_linear_edge_baseline`.
- Do not remove P2b rollback columns without a separate schema/deprecation note.
- Do not describe AsLS as proven absolute baseline truth.
- Do not start C1b implementation until C1a, C5, rollback-column deprecation,
  and P2c `GO_FOR_LINEAR_EDGE_RETIREMENT` are all satisfied.

## Next Action

Proceed with one of these low-risk Phase 2 directions:

- handoff-spine scaffold / dual-write work (`PeakHypothesis`, `EvidenceVector`,
  `IntegrationResult`, `AuditTrail`);
- C5 method-preserving single integration entry;
- C1a pure baseline relocation if it is kept import-compatible.

These should preserve current outputs and validate by parity, not by adding new
ASLS gate layers.
