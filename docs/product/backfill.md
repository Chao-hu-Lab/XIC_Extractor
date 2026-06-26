# Backfill

Document status: product-topic source-of-truth summary.
Evidence label: `diagnostic_only` for this documentation-governance patch; this
page does not change Backfill writer authority or productization tier.

Backfill is the authority-gated path for filling accepted quantification values
into product-facing outputs. It is not a shortcut from diagnostics, overlays, or
candidate tables into the matrix.

This file is the public topic entry point. Detailed history can move to private
notes after the stable claims below are represented here or in the owner docs.

## Answers

Use this page to answer:

- Whether a Backfill candidate, audit row, sidecar row, or overlay can write a
  product matrix.
- Which repo owners decide Backfill writer authority and productization state.
- What path broad Backfill expansion must follow before publication.
- Which Backfill history can move to private notes after stable public claims
  are represented.

## Does Not Answer

This page does not decide:

- Current maturity tier, active lane, exact writer scope, or current accepted
  cell set. Use the control plane, status index, and authority manifest.
- Candidate-level truth for unresolved rows. Use validation packets,
  mechanical adjudication, and evidence owners.
- Sample-level private investigation details. Keep those in private notes or
  ignored artifacts.

## Current Contract

- Backfill acceptance means accepted quantification values, not automatic truth
  claims about every candidate feature.
- `ProductWriter` remains the only matrix-writing authority. Sidecars,
  galleries, blocker tokens, review tables, and diagnostics can explain or
  gate a decision, but they do not write product matrices unless the authority
  manifest explicitly grants that role.
- Any broader Backfill publication requires an explicit public authority
  contract, expected-diff evidence, and focused output tests.
- Broad auto-write from the full Backfill candidate universe is parked. The
  candidate/audit universe is not the writer pool.
- Current Backfill expansion work should prioritize mechanical adjudication,
  structured review, truth acquisition, trace-evidence recovery, and evidence
  provenance before any new writer scope.
- A stable lifecycle vocabulary is useful, but it is not writer authority by
  itself: missing call, Backfill candidate, evidence-chain packet, review item,
  approval decision, export policy, and quant-matrix version are separate
  states.
- Seed-aware review gates and shadow gates can classify Backfill readiness, but
  `shadow_gate_ready` is not matrix authority.
- Positive support must be provenance-valid. Display tokens in
  `alignment_review.tsv` do not promote a row without the approved source
  sidecar or authority chain.

## Public Surfaces

| Surface | Role |
| --- | --- |
| `ProductWriter` authority path | Only approved writer path for product matrix changes |
| Productization status index | Machine-checkable Backfill maturity and lane state |
| Authority manifest | Fail-closed writer scope and accepted authority records |
| Mechanical adjudication schema/index | Structured review evidence for candidate promotion decisions |
| Backfill validation packets | Evidence availability, replay, and expected-diff artifacts |
| `alignment_backfill_cell_evidence.tsv` | Compact alignment-side evidence sidecar; not writer authority by itself |

## Stable Categories

| Category | Meaning | Repo owner |
| --- | --- | --- |
| Current scoped writes | Already accepted cells that ProductWriter may publish | Authority manifest and productization status index |
| Candidate or audit rows | Rows available for review, classification, or evidence recovery | Backfill validation packets and mechanical adjudication index |
| Trace-matched unresolved rows | Rows with some trace-level evidence but insufficient authority | Backfill evidence lifecycle and adjudication surfaces |
| Missing-overlay rows | Rows blocked by absent or insufficient overlay evidence | Evidence availability packets and blocker reports |
| Expansion packets | Proposed future writer changes | Control plane, authority manifest, expected-diff packet, output tests |
| Evidence-chain packet | Structured source evidence for review or approval | Backfill evidence lifecycle and provenance owners |
| Approval decision | Human or machine-readable approval state | Review roundtrip and authority manifest gates |

## Workflow

1. Candidate or audit rows collect evidence through discovery, alignment,
   replay, overlay, or adjudication surfaces.
2. Rows are classified into current scoped writes, candidate/audit rows,
   trace-matched unresolved rows, missing-overlay rows, or expansion packets.
3. Promotion requires a public authority contract, expected-diff evidence, and
   focused output tests.
4. The authority manifest and productization status index record the accepted
   writer scope.
5. `ProductWriter` writes product-facing matrix values only for accepted scope.

## Verification Gates

Before changing Backfill product behavior, require the relevant subset of:

- productization state and authority checker pass;
- expected-diff packet for any new matrix-writing scope;
- focused output tests covering changed matrix values and identity sidecars;
- evidence-rule review for any new interpretation of trace, overlay, or
  candidate evidence;
- privacy scan if historical notes or sample-level review details are touched.

## Common Wrong Moves

- Treating the candidate/audit universe as the writer pool.
- Treating overlays, galleries, blocker tokens, or sidecars as matrix authority.
- Treating `shadow_gate_ready` as a write predicate.
- Treating `alignment_review.tsv` tokens as positive support without
  provenance-valid sidecars.
- Moving a historical Backfill note to private storage before its stable public
  claims are represented in repo owners.
- Updating a topic summary while leaving the control plane, status index, or
  authority manifest stale after a real authority change.

## Source Owners

Use these before changing product behavior or cleanup policy:

- [`docs/superpowers/plans/2026-06-15-productization-control-plane.md`](../superpowers/plans/2026-06-15-productization-control-plane.md)
- [`docs/superpowers/validation/productization_status_index_v1.tsv`](../superpowers/validation/productization_status_index_v1.tsv)
- [`docs/superpowers/specs/productization_authority_manifest.v1.json`](../superpowers/specs/productization_authority_manifest.v1.json)
- [`docs/superpowers/specs/mechanical_adjudication_schema.v1.json`](../superpowers/specs/mechanical_adjudication_schema.v1.json)
- [`docs/superpowers/validation/mechanical_adjudication_index_v1.tsv`](../superpowers/validation/mechanical_adjudication_index_v1.tsv)
- [`docs/superpowers/notes/backfill_broad_autowrite_feasibility_gate_v1.md`](../superpowers/notes/backfill_broad_autowrite_feasibility_gate_v1.md)
- [`docs/lcms-msms-evidence-rules.md`](../lcms-msms-evidence-rules.md)
- [`docs/superpowers/plans/2026-06-19-backfill-quant-matrix-product-blueprint.md`](../superpowers/plans/2026-06-19-backfill-quant-matrix-product-blueprint.md)
- [`docs/superpowers/notes/2026-05-19-seed-aware-backfill-review-index.md`](../superpowers/notes/2026-05-19-seed-aware-backfill-review-index.md)

## Cleanup Rule

Backfill diaries, reset notes, command transcripts, and detailed review debate
belong in Obsidian or ignored artifacts after their stable public claims are
covered here, in the control plane, or in the authority/evidence owners. Keep a
same-path repo stub only while exact referrers, checkers, hashes, fixtures, or
compatibility references still need that path, including old sidecar provenance
checkpoint notes.

## When To Update

Update this page when Backfill gains a new durable category, public sidecar,
promotion gate, or recurring wrong-move rule. If the change affects maturity
tier, active lane, writer authority, selected values, schema, or matrix output,
update the control plane, status index, authority manifest, and output tests
first.
