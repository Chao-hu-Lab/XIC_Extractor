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

CID-NL Discovery/alignment row identity is `production_candidate` evidence. It
recovers `300.1605 -> 184.113` as a primary row and preserves
`301.165 -> 185.116` as its own dR-tag row. No ProductWriter output, default
matrix, workbook, GUI behavior, selected peak/area, counted detection, active
lane, maturity tier, or Backfill writer authority changed.

Default activation identity blocking is now resolved for the CID-NL candidate
contract: all 511 accepted authority cells are classified, with 0 unresolved
identity cells. This does not mean default activation has been written.

## Latest Evidence

85RAW alignment output:

- `output/discovery/cid_nl_product_ready_alignment_85raw_20260620_fix3`
- `300.1605 -> 184.113`: `FAM011499`, `Mz=300.161`, `RT=23.3493`,
  `85/85`, `identity_confidence=high`, `neutral_loss_tag=DNA_dR`,
  source `TumorBC2312_DNA#19561@mz300.160635_p184.113235`.
- `301.165 -> 185.116`: `FAM011783`, `Mz=301.165`, `RT=23.3413`,
  `83/85`, `identity_confidence=review`, `neutral_loss_tag=DNA_dR`,
  source `TumorBC2312_DNA#19561@mz301.164978_p185.115845`.

Default activation gates:

- Preflight:
  `docs/superpowers/validation/cid_nl_default_activation_preflight_v1/`
  target alignment evidence passes, replay remains blocked by identity
  compatibility.
- Bridge gate:
  `docs/superpowers/validation/cid_nl_default_activation_bridge_gate_v1/`
  classifies 147 pass and 364 blocked bridge cells.
- Authority reconstruction:
  `docs/superpowers/validation/cid_nl_default_activation_authority_reconstruction_gate_v1/`
  proves 147 blank writes replay in memory and reduces the problem to 101
  identity cells.
- Cell-local identity:
  `docs/superpowers/validation/cid_nl_default_activation_cell_local_identity_gate_v1/`
  resolves 74 ambiguous cells as detected-baseline no-write supersession,
  leaving 27.
- Remaining identity:
  `docs/superpowers/validation/cid_nl_default_activation_remaining_identity_gate_v1/`
  passes with 511 classified cells and 0 unresolved identity cells.

Remaining-identity contract:

- 147 `write_ready_blank` candidate writes.
- 337 detected-baseline/no-write cells.
- 27 explicit no-write scope removals:
  19 missing bridge identity, 5 all-blank ambiguity, 3 multiple-detected
  ambiguity.
- The gate records row identity/source context and still treats candidates as
  non-authoritative.

Heartbeat audit:

- Alignment reruns have `timing.live.json` for both 8RAW and 85RAW.
- Discovery input artifacts have `timing.json` only, no live heartbeat files.

## Boundaries

- Do not maintain two Discovery systems.
- Do not make CID-NL/MS2 evidence direct ProductWriter authority.
- Do not treat candidates as matrix rows.
- Do not use `301.165 -> 185.116` as authority for `300.1605 -> 184.113`.
- Do not delete/demote `301.165 -> 185.116` when it has its own tag evidence.
- Do not run or update default activation without the next expected-diff /
  candidate-build gate.

## Latest Local Checks

- `python -m pytest tests/test_cid_nl_default_activation_remaining_identity_gate.py -q`
  passed: `8 passed`.
- `uv run ruff check scripts/check_cid_nl_default_activation_remaining_identity_gate.py tests/test_cid_nl_default_activation_remaining_identity_gate.py`
  passed.
- `python scripts/check_cid_nl_default_activation_remaining_identity_gate.py --require-pass`
  exited `0` and wrote the passing summary/audit.

Residual from the previous full test run: full pytest still had an unrelated
stale lockbox shadow automation artifact failure after 2080 passed. This slice
did not modify that lockbox area.

## Next Product Step

Build the default-activation expected-diff/candidate gate. It must write only
the 147 blank cells, preserve the 337 detected/no-write cells, omit the 27
scope removals, and continue proving that CID-NL/MS2 evidence and candidate
rows are not direct ProductWriter authority.

## Status Index Anchors

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
