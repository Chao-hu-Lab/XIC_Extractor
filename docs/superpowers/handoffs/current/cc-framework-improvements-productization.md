# XIC productization handoff

Updated: 2026-06-20
Branch: `cc/framework-improvements`

This is a compact current-state snapshot. It is not product authority. Tier,
active lane, and promotion-gate authority remain in
`docs/superpowers/plans/2026-06-15-productization-control-plane.md`.

## Current Verdict

The tracked default QuantMatrix remains `product_ready_default_matrix_activated`
for the existing detected cells plus exactly 511 accepted Backfill cells under
`backfill_policy_write_ready_rows`.

CID-NL Discovery/alignment row identity is now `production_candidate` evidence:
the A owner-deepened path recovers `300.1605 -> 184.113` as a primary row and
preserves `301.165 -> 185.116` as its own dR-tag row. The new default activation
preflight is blocked because the old 511-cell authority IDs do not replay on
the new 85RAW alignment identity.

No ProductWriter output, default matrix, workbook, GUI behavior, selected
peak/area, counted detection, Backfill writer authority, active lane, or
maturity tier changed in the latest slice.

## Latest CID-NL Evidence

Validation packets:

- `docs/superpowers/validation/cid_nl_product_ready_alignment_v1/README.md`
- `docs/superpowers/validation/cid_nl_default_activation_preflight_v1/README.md`

85RAW alignment output:

- Path: `output/discovery/cid_nl_product_ready_alignment_85raw_20260620_fix3`.
- `300.1605 -> 184.113`: `FAM011499`, `Mz=300.161`, `RT=23.3493`,
  `85/85`, `identity_confidence=high`, `neutral_loss_tag=DNA_dR`,
  unique TumorBC2312 provenance with matching family/public/group identity,
  source
  `TumorBC2312_DNA#19561@mz300.160635_p184.113235`.
- `301.165 -> 185.116`: `FAM011783`, `Mz=301.165`, `RT=23.3413`,
  `83/85`, `identity_confidence=review`, `neutral_loss_tag=DNA_dR`,
  unique TumorBC2312 provenance with matching family/public/group identity,
  source
  `TumorBC2312_DNA#19561@mz301.164978_p185.115845`.
- The 301 row is preserved as its own product row and must not be used as
  authority for the 300 row.

Default activation preflight:

- Summary:
  `docs/superpowers/validation/cid_nl_default_activation_preflight_v1/cid_nl_default_activation_preflight_summary.json`.
- `overall_status=blocked`.
- `target_alignment_evidence_status=pass`.
- `replay.status=blocked`.
- 511 accepted authority cells and 511 expected-diff rows were supplied.
- 506 accepted cells are missing from the new matrix identity.
- First blocker:
  `FAM000380/BenignfatBC0980_DNA: peak_hypothesis_id missing from matrix identity`.

Heartbeat audit:

- Alignment reruns have `timing.live.json` for both 8RAW and 85RAW.
- Discovery input artifacts have `timing.json` only, no live heartbeat files.

## Boundaries

- Do not maintain two Discovery systems.
- Do not make CID-NL/MS2 evidence direct ProductWriter authority.
- Do not treat candidates as matrix rows.
- Do not use `301.165 -> 185.116` as authority for `300.1605 -> 184.113`.
- Do not delete/demote `301.165 -> 185.116` when it has its own tag evidence.
- Do not run or update default activation without a separate expected-diff /
  ID-bridge goal.

## Latest Local Checks

- `python -m pytest tests/test_cid_nl_default_activation_preflight.py -q`
  passed: `7 passed`.
- `uv run ruff check scripts/check_cid_nl_default_activation_preflight.py tests/test_cid_nl_default_activation_preflight.py`
  passed.
- `python scripts/check_cid_nl_default_activation_preflight.py` exited `0` and
  wrote the blocked preflight summary.

Residual from the previous full test run: full pytest still had an unrelated
stale lockbox shadow automation artifact failure after 2080 passed. This latest
slice did not modify that lockbox area.

## Next Product Step

Implement an explicit ID bridge / expected-diff contract that can prove the
current 511-cell Backfill authority remains exactly preserved while the
recovered `300.1605 -> 184.113` row is materialized in the released default
matrix. Until that bridge passes, CID-NL stays `production_candidate` and the
default bundle remains the current 511-cell product-ready activation.

## Status Index Anchors

These strings keep `scripts/check_productization_state.py` fail-closed:

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
