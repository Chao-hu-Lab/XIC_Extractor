# XIC productization handoff

Updated: 2026-06-21
Branch: `cc/framework-improvements`

This is the current-state snapshot. Product authority is anchored in
`docs/superpowers/plans/2026-06-15-productization-control-plane.md`,
`docs/superpowers/specs/productization_authority_manifest.v1.json`, and
`docs/superpowers/validation/productization_status_index_v1.tsv`.

## Current Verdict

The product tier remains `product_ready_default_matrix_activated`.

Active writer scopes:

- `backfill_current_write_ready_scope`: 511 cells under
  `backfill_policy_write_ready_rows`.
- `cid_nl_default_product_activation_v1`: 95 cells under
  `cid_nl_adopt_ready_feature_inclusion_95_cells`.
- `backfill_expansion_default_product_activation_v1`: 666 cells under
  `backfill_expansion_raw_trace_expected_diff_666_cells`.

Broad Backfill auto-write remains parked. The 666-cell Backfill expansion scope
is a bounded default activation packet, not permission to write the 929 pressure
cells, the 263 held cells, or future sample batches without the same rule and
expected-diff contract.

## What Changed

`backfill_expansion_default_product_activation_v1` is now the explicit public
default activation change for the 666-cell packet. It reuses the existing
ProductionAcceptanceManifest + expected-diff + QuantMatrixVersion writer path.

The activation writes:

- 666 Backfill values;
- exactly 666 changed matrix cells;
- 666 accepted cell-provenance rows from `ProductionAcceptanceManifest`;
- 0 unused expected-diff rows.

The 263 held cells are still excluded: 254 lack exact sample-local alignment
evidence and 9 were trace-absent in the RAW overlay gate.

## Discovery Lane

CID-NL Discovery is closed for the current 85RAW-derived product question.
Default activation is limited to 95 adopt-ready Discovery cells across 20
transitions.

Target guardrails still hold: `300.1605 -> 184.113` is recovered as source
context, and `301.165 -> 185.116` remains its own `DNA_dR` source-tag context.
CID-NL/MS2 evidence remains an evidence provider; it does not directly become
ProductWriter authority.

## Backfill Expansion Chain

- `backfill_expansion_census_v1`: 20 CID-NL active successor rows create a
  1700-cell universe: 676 detected, 95 Discovery-written, 929 blank pressure
  cells. The 1010 parked future-pressure cells remain parked.
- `backfill_expansion_evidence_availability_v1`: existing mechanical/trace
  recovery coverage is 0/929, so sample-local evidence was required.
- `backfill_expansion_sample_local_ms1_evidence_v1`: exact sample-local
  alignment evidence exists for 675/929 cells; 254 remain held.
- `backfill_expansion_raw_overlay_trace_identity_v1`: evidence-only RAW overlay
  confirms trace signal for 666/675 alignment-present cells; 9 trace-absent
  cells remain held.
- `backfill_expansion_expected_diff_provenance_v1`: the 666 RAW-observed cells
  form a contract-valid packet with schema-valid manifest rows, expected diff,
  dry-run writer output, and provenance.
- `backfill_expansion_default_product_activation_v1`: the packet is now a
  production-ready bounded default activation lane.

## Boundaries

- Do not maintain a second Discovery or ProductWriter system.
- Do not put full matrices, full opportunity maps, cell provenance dumps, or
  generated overlay bundles into git; heavy outputs stay under `output/`.
- Do not treat candidates as matrix rows.
- Do not expand the 95 CID-NL lane without a new Discovery expected-diff gate.
- Do not expand the 666 Backfill expansion lane beyond its exact packet without
  a new expected-diff and authority update.
- Do not route the 263 held cells into ProductWriter without exact sample-local
  evidence and a new gate.
- Do not project row/family evidence onto sample cells.
- Do not unpark broad Backfill without an independent truth source plus
  expected-diff authority update.
- Do not change workbook/GUI, selected peak, selected area, or counted
  detection from this activation.

## Current Gate Commands

- `uv run python -m scripts.check_backfill_expansion_census --check-only`
- `uv run python -m scripts.check_backfill_expansion_evidence_availability --check-only`
- `uv run python -m scripts.check_backfill_expansion_sample_local_ms1_evidence --check-only`
- `uv run python -m scripts.check_backfill_expansion_raw_overlay_trace_identity --check-only`
- `uv run python -m scripts.check_backfill_expansion_expected_diff_provenance --check-only`
- `uv run python -m scripts.build_backfill_expansion_default_product_activation --check-only --require-pass`
- `uv run python -m scripts.check_productization_state`
- `uv run python -m scripts.check_validation_artifact_retention`

## Status Index Anchors

Active writer lanes:

- `backfill_current_write_ready_scope`
- `cid_nl_default_product_activation_v1`
- `backfill_expansion_default_product_activation_v1`

Required anchor phrases:

- `product_ready_default_matrix_activated`
- `CID-NL default product activation v1`
- `Backfill Expansion Default Product Activation v1`
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

For this 85RAW-derived packet, Discovery plus bounded Backfill expansion can be
treated as product-ready default activation.

For future sample batches, do not repeat this manual gate-by-gate rollout once
the rule is stable. Collapse the evidence chain into a CLI/GUI preset that
directly runs the same bounded rule, emits the activation outputs, and records
the authority scope, expected diff, and provenance.
