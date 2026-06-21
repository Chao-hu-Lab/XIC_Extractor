# XIC productization handoff

Updated: 2026-06-21
Branch: `cc/framework-improvements`

This is a current-state snapshot, not product authority. Tier and lane
authority remain in
`docs/superpowers/plans/2026-06-15-productization-control-plane.md`.

## Current Verdict

The active default QuantMatrix remains
`product_ready_default_matrix_activated` for the existing detected cells plus
exactly 511 accepted Backfill cells under `backfill_policy_write_ready_rows`.

CID-NL Discovery is now on the correct untargeted track:

1. Feature inclusion first: CID-NL/MS2 evidence plus a real MS1 feature can
   justify carrying a successor hypothesis forward as an untargeted feature.
2. Identity authority second: replacement, merge, dedupe, or old-cell migration
   requires a separate expected-diff gate.

No maturity tier, active lane, ProductWriter authority, Backfill writer
authority, workbook/GUI behavior, selected peak/area, counted detection, or
active default matrix bundle changed.

The narrowed CID-NL activation bundle is now
`production_candidate_activation_adopt_gate`: 95 cells across 20 transitions
are adopt-ready as input to a later explicit public activation change. This is
not default activation and not ProductWriter authority.

## Current Review Surface

- Background note:
  `docs/deepresearch/Untargeted LC-MS Feature Discovery Background.md`
- Product report:
  `docs/superpowers/validation/cid_nl_default_activation_gallery_review_v1/README.md`
- Versioned manual verdicts:
  `docs/superpowers/validation/cid_nl_default_activation_gallery_review_v1/cid_nl_manual_feature_inclusion_review.tsv`
- Maintained reader guide:
  `docs/superpowers/validation/evidence_overlay_interpretation_guide.html`
- Main Gallery:
  `output/validation/cid_nl_default_activation_gallery_review_v1/backfill_evidence_reconciliation_gallery.html`
- Paired differential Gallery:
  `output/validation/cid_nl_default_activation_gallery_review_v1/differential_overlays/cid_nl_differential_overlay_gallery.html`
- Feature-inclusion gate:
  `output/validation/cid_nl_default_activation_gallery_review_v1/feature_inclusion_gate/`
- Activated-copy candidate and acceptance:
  `output/validation/cid_nl_default_activation_gallery_review_v1/activation_copy_candidate/`
- Activation adopt gate:
  `output/validation/cid_nl_default_activation_gallery_review_v1/activation_adopt_gate/`

## Evidence Snapshot

- Successor decision packet: pass; 511 decision rows, 147 legacy
  `write_authorized` candidate cells, 337 detected-baseline existing-successor
  cells, 27 omitted no-target cells.
- Main Gallery packet: pass; 90 review groups, 529 representative cells, 85
  overlay-linked groups, 87 source/successor or no-successor transitions.
- Paired differential overlays: pass; 78 rendered transitions, 78 PNGs, 78
  trace JSON files, 484 reviewed source/successor decision cells.
- Feature-inclusion gate: pass; 87 transitions, 78 overlay-ready transitions,
  147 candidate cells split into 73 supported, 46 review-required, and 28
  current-bundle-blocked cells. The 46 review-required cells are now further
  resolved into 9 agent-resolved expected-diff cells, 13 manual-resolved
  expected-diff cells, and 24 agent-held cells.
- Expected-diff contracts: 95 cells across 20 transitions are eligible for the
  validation copy: 73 primary supported cells, 9 second-pass agent-resolved
  cells, and 13 manual-resolved cells.
- Agent-held queue: 24 cells across 6 transitions are held out of the current
  bundle because source/no-support evidence is stronger than successor support.
- User-review queue: 0 cells. The four former user-review transitions are
  manual-resolved as successor feature-inclusion supported:
  `FAM011440 -> FAM015713`, `FAM011837 -> FAM016144`,
  `FAM018342 -> FAM026285`, and `FAM020176 -> FAM030972`. For
  `FAM020176 -> FAM030972`, only `FAM030972` feature inclusion is supported;
  `FAM020176` source evidence remains `unjudgeable_bad_trace` and must not be
  used for source deletion or migration.
- Blocked queue: 28 cells across 17 transitions are excluded from the current
  activation bundle by current paired overlay evidence.
- Activated-copy candidate: pass; 95 changed blank matrix cells across 20
  transitions under
  `output/validation/cid_nl_default_activation_gallery_review_v1/activation_copy_candidate/`.
  This is a validation copy only, not the default matrix.
- Activated-copy acceptance: pass; 95 contract cells, 95 value-delta rows, 95
  exact matrix changes, 0 forbidden overlaps, 0 unexpected changes, 0 missing
  changes, and `production_ready=FALSE`.
- Activation adopt gate: `adopt_ready`; label
  `production_candidate_activation_adopt_gate`; 95 contract cells, 95
  validation-copy changes, 20 transitions, 0 forbidden overlaps, 0 unexpected
  changes, 0 missing changes, `product_writer_changed=FALSE`,
  `default_quant_matrix_changed=FALSE`, `workbook_gui_changed=FALSE`, and
  `production_ready=FALSE`.
- Existing context and omitted behavior are preserved: 337 existing-successor
  context cells and 27 omitted no-target cells are not activation writes.

## Boundaries

- Do not maintain two Discovery systems.
- Do not make CID-NL/MS2 evidence direct ProductWriter authority.
- Do not treat candidates as matrix rows.
- Do not change default matrix/ProductWriter/workbook/GUI/Backfill authority
  without an explicit expected-diff gate.
- Do not delete or demote `301.165 -> 185.116` while it has its own tag
  evidence.
- A source peak does not invalidate successor feature inclusion; it only opens
  a replacement/merge/dedupe/co-existing-feature question.

## Status Index Anchors

Current lane anchors retained for `productization_status_index_v1`:

- `backfill_current_write_ready_scope`
- `broad_backfill_autowrite`
- `productization_authority_firewall_v1`
- `mechanical_adjudication_contract_v1`
- `review_packet_workflow_v1`
- `peak_choice_truth_lockbox_v1`
- `missing_overlay_evidence_recovery_v1`
- `quality_explanation_sidecar_v1`
- `targeted_ms1_shape_identity_limited_rescue_v1`
- `targeted_ms1_shape_identity_broader_targets`
- `sample_metadata_order_projection_v1`
- `sample_metadata_role_value_behavior`
- `review_action_candidate_sidecar_v1`
- `review_action_selected_candidate_switch`
- `review_action_manual_boundary_area_writer`
- `calibration_normalization_activation`
- `gui_replay_parity`

## Next Step

The adopt/hold decision is closed for the narrowed validation bundle:
`adopt_ready`, not default-active. The next step, if continuing toward product
readiness, is an explicit public-surface default activation change. That change
must intentionally update ProductWriter/default matrix behavior and prove the
same 95-cell expected diff, provenance, preserved 337 existing-successor
context cells, preserved 27 omitted no-target cells, and no unrelated output
drift.
