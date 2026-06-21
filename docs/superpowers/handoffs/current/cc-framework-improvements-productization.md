# XIC productization handoff

Updated: 2026-06-21
Branch: `cc/framework-improvements`

This is a current-state snapshot. Product authority remains anchored in
`docs/superpowers/plans/2026-06-15-productization-control-plane.md` and
`docs/superpowers/validation/productization_status_index_v1.tsv`.

## Current Verdict

The product tier is `product_ready_default_matrix_activated`.

Registered writer scopes:

- Backfill current write-ready scope: 511 cells under
  `backfill_policy_write_ready_rows`; broad Backfill remains parked.
- CID-NL default product activation v1: 95 cells across 20 transitions under
  `cid_nl_adopt_ready_feature_inclusion_95_cells`.

CID-NL is now default-active only for the 95 adopt-ready cells. It does not
grant source deletion, source/successor merge, dedupe, workbook/GUI changes,
selected peak/area rewrites, counted-detection changes, or direct ProductWriter
authority from CID-NL/MS2 evidence.

## Current Artifacts

- CID-NL default activation summary:
  `docs/superpowers/validation/cid_nl_default_product_activation_v1/cid_nl_default_product_activation_summary.json`
- CID-NL default activation checks:
  `docs/superpowers/validation/cid_nl_default_product_activation_v1/cid_nl_default_product_activation_checks.tsv`
- CID-NL compact activation manifest:
  `docs/superpowers/validation/cid_nl_default_product_activation_v1/cid_nl_default_product_activation_manifest.tsv`
- Full generated CID-NL default outputs:
  `output/validation/cid_nl_default_product_activation_v1/`
- Pre-activation Gallery/adopt evidence:
  `output/validation/cid_nl_default_activation_gallery_review_v1/`
- Human reader guide:
  `docs/superpowers/validation/evidence_overlay_interpretation_guide.html`

## Evidence Snapshot

- Activation status: `pass`.
- Activation label: `product_ready_default_matrix_activated`.
- Accepted CID-NL writes: 95 cells.
- Transitions: 20.
- Contract source split: 73 primary supported, 9 agent-resolved, 13
  manual-resolved cells.
- Existing successor detected context preserved: 337 cells.
- Omitted no-target cells preserved: 27 cells.
- Expected-diff replay: 95 expected, 95 written, 0 unused.
- Matrix delta: exact keyset pass; 95 changed cells and no extra/missing
  changes.
- Cell provenance: exact keyset pass; 95 accepted_backfill provenance rows
  from `ProductionAcceptanceManifest`.
- RAW/85RAW rerun: not run for this activation; the gate is no-RAW replay from
  existing 85RAW-derived artifacts.

## Boundaries

- Do not maintain a second Discovery/ProductWriter system.
- Do not put full default matrices into version control; full CID-NL output
  stays externalized under `output/validation/`.
- Do not treat candidates as matrix rows.
- Do not expand beyond the 95 CID-NL cells without a new expected-diff gate.
- Do not make CID-NL/MS2 evidence direct ProductWriter authority.
- Do not demote/delete `301.165 -> 185.116` while it has its own tag evidence.
- Broad Backfill is still parked.

## Status Index Anchors

Active writer lanes:

- `backfill_current_write_ready_scope`
- `cid_nl_default_product_activation_v1`

Non-writer lanes remain parked/blocked/diagnostic as recorded in
`productization_status_index_v1.tsv`.

Anchor phrases retained for the status checker:

- `product_ready_default_matrix_activated`
- `CID-NL default product activation v1`
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

## Next Step

Finish verification and commit this activation slice. After that, the next
product work should be a separate bounded-expansion goal: either expand CID-NL
only with a new expected-diff/provenance gate, or work on a different registered
lane. Do not expand writer scope by editing the status index alone.
