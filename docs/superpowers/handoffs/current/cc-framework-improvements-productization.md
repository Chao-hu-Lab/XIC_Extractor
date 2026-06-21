# XIC productization handoff

Updated: 2026-06-21
Branch: `cc/framework-improvements`

This is the current-state snapshot. Product authority remains anchored in
`docs/superpowers/plans/2026-06-15-productization-control-plane.md` and
`docs/superpowers/validation/productization_status_index_v1.tsv`.

## Current Verdict

The product tier is `product_ready_default_matrix_activated`.

Registered writer scopes:

- Backfill current write-ready scope: 511 cells under
  `backfill_policy_write_ready_rows`; broad Backfill remains parked.
- CID-NL Discovery default product activation v1: 95 cells across 20
  transitions under `cid_nl_adopt_ready_feature_inclusion_95_cells`.

The immediate product direction is Discovery first. Backfill is not the next
main line unless explicitly reopened with a separate goal.

## Discovery Lane

CID-NL is default-active only for the 95 adopt-ready Discovery cells.

Public CID-NL artifacts now use Discovery-first language:

- `product_lane=cid_nl_discovery`
- `product_scope_kind=discovery_default_activation`
- `accepted_discovery_cell_count=95`
- `written_discovery_cell_count=95`
- `default_activation_effect=write_cid_nl_discovery_default_cell`

Legacy `accepted_backfill`, `written_backfill_count`,
`cell_status=accepted_backfill`, and `write_accepted_backfill` terms are kept
only as `QuantMatrixVersion` compatibility fields. They are not Backfill product
scope.

Primary Discovery roadmap:

- `docs/superpowers/plans/2026-06-21-cid-nl-discovery-product-roadmap.md`

Operational skill for future major workflow/productization work:

- `.codex/skills/xic-rule-first-development/`

Current release-slice checker:

- `uv run python -m scripts.check_cid_nl_discovery_release_slice`
- Focused test: `uv run pytest tests/test_cid_nl_discovery_release_slice.py -q`

## Current Discovery Evidence

- Activation status: `pass`.
- Activation label: `product_ready_default_matrix_activated`.
- Accepted Discovery default writes: 95 cells.
- Transitions: 20.
- Contract source split: 73 primary supported, 9 agent-resolved, 13
  manual-resolved cells.
- Existing successor detected context preserved: 337 cells.
- Omitted no-target cells preserved: 27 cells.
- Expected-diff replay: 95 expected, 95 written, 0 unused.
- Matrix delta: exact keyset pass; 95 changed cells and no extra/missing
  changes.
- Cell provenance: exact keyset pass through the shared
  `ProductionAcceptanceManifest -> QuantMatrixVersion` writer.
- Release-slice checker: pass.
- RAW/85RAW rerun: not run for this cleanup; the activation remains no-RAW
  replay from existing 85RAW-derived artifacts.

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

## Boundaries

- Do not maintain a second Discovery/ProductWriter system.
- Do not put full default matrices into version control.
- Do not treat candidates as matrix rows.
- Do not expand beyond the 95 CID-NL cells without a new Discovery
  expected-diff/provenance gate.
- Do not make CID-NL/MS2 evidence direct ProductWriter authority.
- Do not demote/delete `301.165 -> 185.116` while it has its own tag evidence.
- Do not reopen broad Backfill while the active goal is Discovery productization.

## Status Index Anchors

Active writer lanes:

- `backfill_current_write_ready_scope`
- `cid_nl_default_product_activation_v1`

Anchor phrases retained for the status checker:

- `product_ready_default_matrix_activated`
- `CID-NL default product activation v1`
- `CID-NL Discovery Release Slice Checker v1`
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

Continue with Discovery only: either stabilize the current 95-cell release slice
or define the next CID-NL expansion slice with its own expected-diff,
provenance, row-identity, and artifact-retention gate. The release-slice checker
is now the quickest current-state sanity check. Do not route this through broad
Backfill.
