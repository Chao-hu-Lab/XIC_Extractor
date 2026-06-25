# Backfill Auto-Write Ground-Truth Strategy

Status: `repo_stub_plus_obsidian`
Validation status: `diagnostic_only`
Original note date: 2026-06-18

This same-path public stub preserves the durable strategy decision and referrer
compatibility for the historical strategy note. The long strategy exploration
was moved to the private Obsidian note
`[[XIC Backfill Autowrite Ground Truth Strategy]]` and read back before this
stub was written. Private vault access is optional and must not be required to
understand the product decision.

## Public Decision

This note is design history, not an implementation ticket. The current product
direction is no broad Backfill auto-write expansion from this strategy note.

The stable findings are:

- Backfill promotes the cell's own MS1 morphology area; it does not reconstruct
  a missing measurement by cross-sample transfer or sibling consensus.
- The 4613-row candidate universe is an audit/adjudication universe, not a
  writable-cell count.
- The current approved Backfill product-writing scope remains 511 `write_ready`
  cells.
- The 3015 dirty-but-trace-matched rows need independent peak-choice / area
  truth or another approved evidence class before any write authority can be
  considered.
- The 1087 `missing_overlay_path` rows remain unverifiable under the current
  contract and must not be auto-written without trace evidence.
- ISTD evidence can support limited truth checks, but it cannot by itself prove
  broad analyte peak-choice correctness or broad Backfill write authority.
- Round-trip reintegration and `quality_blockers` are diagnostic/explanation
  surfaces only; they do not grant ProductWriter authority.

The later `backfill_broad_autowrite_feasibility_gate_v1` decision packet parks
broad Backfill. That packet supersedes this strategy note as the active decision
surface.

## Repo Sources Of Truth

- Current Backfill tier, active lane, and writer authority:
  `docs/superpowers/plans/2026-06-15-productization-control-plane.md`
- Machine-checkable parked broad-autowrite state:
  `docs/superpowers/validation/productization_status_index_v1.tsv`
- ProductWriter authority manifest:
  `docs/superpowers/specs/productization_authority_manifest.v1.json`
- Mechanical adjudication schema and index:
  `docs/superpowers/specs/mechanical_adjudication_schema.v1.json`
  and `docs/superpowers/validation/mechanical_adjudication_index_v1.tsv`
- Current parked-lane decision packet:
  `docs/superpowers/notes/backfill_broad_autowrite_feasibility_gate_v1.md`

## Next Safe Action

Do not implement a classifier, degradation oracle, or writer expansion from this
historical strategy note. Reopen broad Backfill only with a new independent truth
source and a public expected-diff-backed authority contract.

No tracked-file removal is authorized by this stub.
