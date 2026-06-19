# XIC productization handoff

Updated: 2026-06-20
Branch: `cc/framework-improvements`

This is a compact current-state snapshot. It is not product authority. Tier,
active lane, and promotion-gate authority remain in
`docs/superpowers/plans/2026-06-15-productization-control-plane.md`.

## Current Verdict

The tracked default QuantMatrix remains the current detected + 511 accepted
Backfill product output. ProductWriter default output and Backfill authority did
not change in this slice.

CID-NL Discovery/alignment row identity has moved beyond one-RAW diagnostic
evidence. The A owner-deepened path now has focused tests plus 8RAW and 85RAW
alignment evidence showing that `300.1605 -> 184.113` can become a primary
matrix identity while `301.165 -> 185.116` remains a valid dR-tag row identity.

Readiness for this CID-NL packet is `production_candidate` for
Discovery-to-alignment row identity. It is not
`product_ready_default_matrix_activated` because the tracked default activation
bundle was not regenerated from the new 85RAW artifacts.

## Product State

- Current default tier: `product_ready_default_matrix_activated`.
- Product authority scope: `backfill_policy_write_ready_rows`.
- Current Backfill writer authority: exactly 511 accepted Backfill cells.
- Broad 4613-row Backfill remains parked.
- Default matrix/ProductWriter/workbook/GUI/Backfill authority were not changed.
- CID-NL/MS2 evidence remains evidence-provider input; it is not direct
  ProductWriter authority.

## Status Index Anchors

These anchors keep `scripts/check_productization_state.py` fail-closed. They do
not make this handoff the tier authority.

- Broad Backfill auto-write remains parked
- Goal 0/1 hardening added
- machine-adjudicated without granting new writer authority
- Goal 2 added Review Packet / Approval Workflow v1
- lockbox_shadow_automation_experiment_v1
- Goal 4 added Missing-Overlay Evidence Recovery v1
- keep only as explanation/triage
- Targeted MS1 shape identity limited rescue remains production-ready
- GUI and broader targets remain blocked
- `sample_metadata_v1` remains production-ready for no-output ordering
- roles/batch/matrix/exclusion must not alter quant output
- ReviewAction selected-candidate switch and manual-boundary area recompute remain parked
- manual-boundary area recompute remain parked
- classification and planning only

## CID-NL Evidence

Validation note:
`docs/superpowers/validation/cid_nl_product_ready_alignment_v1/README.md`.

8RAW alignment:

- Input Discovery: `output/discovery/cid_nl_product_ready_8raw_20260620_fix2`.
- Output alignment: `output/discovery/cid_nl_product_ready_alignment_8raw_20260620_fix3`.
- `300.1605 -> 184.113`: `FAM001386`, 8/8,
  `product_matrix_identity_complete`, high confidence.
- `301.165 -> 185.116`: `FAM001414`, 8/8,
  `product_matrix_identity_complete`, high confidence,
  `consolidation_state=not_consolidated`.

85RAW alignment:

- Input Discovery: `output/discovery/cid_nl_product_ready_85raw_20260620_fix2`.
- Output alignment: `output/discovery/cid_nl_product_ready_alignment_85raw_20260620_fix3`.
- Discovery parser smoke passed; candidate rows `317036`; duplicate
  `ms1_feature_row_id` count `0`.
- `300.1605 -> 184.113`: `FAM011499`, 85/85,
  `product_matrix_identity_complete`, high confidence.
- `301.165 -> 185.116`: `FAM011783`, 83/85,
  `product_matrix_identity_complete`, centered at
  `family_center_mz=301.165`, `family_product_mz=185.116`.
  Residual risk: `identity_confidence=review` with backfill-evidence review
  flags, so this preserves row identity but does not by itself justify default
  activation.
- TumorBC2312 provenance for preserved 301 row:
  `TumorBC2312_DNA#19561@mz301.164978_p185.115845`,
  `write_matrix_value=TRUE`, `include_in_primary_matrix=TRUE`.
- TumorBC2312 Discovery source state:
  `discovery_candidate_state=ms1_feature_nl_rescued`,
  `ms1_feature_row_id=TumorBC2312_DNA|DNA_dR|301.164978|23.341692`.

## Code Decisions

- Discovery candidate merging may merge seed evidence by shared
  `ms1_feature_row_id` when product identity matches and each candidate is
  compatible with the configured neutral loss.
- Alignment primary consolidation may use shared-MS1 fallback only across
  different neutral-loss tags. Same-tag rows with distinct product identity must
  stay separate unless they pass the normal product/loss identity tolerances.
- This keeps B's useful concept, feature/MS1-primary identity, inside the
  existing A owner path instead of creating a second Discovery system.

## Boundaries

- Do not maintain two Discovery systems.
- Do not make CID-NL/MS2 evidence direct ProductWriter authority.
- Do not treat candidates as matrix rows.
- Do not use `301.165 -> 185.116` as authority for `300.1605 -> 184.113`.
- Do not delete/demote `301.165 -> 185.116` when it has its own tag evidence.
- Do not run or update default activation without a separate expected-diff goal.

## Latest Local Checks

- `python -m pytest tests/test_alignment_primary_consolidation.py -q`
  passed: `9 passed`.
- `python -m pytest tests/test_discovery_ms1_backfill.py -q`
  passed: `20 passed`.
- 8RAW alignment preflight and rerun completed.
- 85RAW alignment preflight and rerun completed with canonical
  `validation-fast`, `raw-workers 11`, `super-window`,
  `production-equivalent`, and `audit-evidence-mode none`.

## Next Actions

1. Run focused integration checks and productization-state checker after the
   current code/docs edits.
2. Request subagent review of the consolidation/merge rule and evidence
   wording; fix any actionable findings.
3. Commit the task-scoped code/tests/docs.
4. Open a separate expected-diff/default-activation goal if the released
   default `quant_matrix.tsv` should materialize the recovered `300.1605` row.
