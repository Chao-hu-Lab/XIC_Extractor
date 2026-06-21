# CID-NL Discovery Product Roadmap - 2026-06-21

## Purpose

Make CID-NL Discovery product-ready without dragging Backfill into the same
decision loop. Backfill remains its own product lane; this roadmap only answers:
which CID-NL discovered feature evidence can become default product output?

## Current State

- Active Discovery product scope:
  `cid_nl_adopt_ready_feature_inclusion_95_cells`.
- Current tier:
  `production_ready` / `product_ready_default_matrix_activated` for those 95
  cells only.
- Current product effect:
  `write_cid_nl_discovery_default_cell`.
- Compatibility note:
  the shared `QuantMatrixVersion` writer still uses legacy
  `accepted_backfill` / `write_accepted_backfill` status names internally.
  Those names are writer compatibility terms, not Backfill product scope.

## Non-Goals

- Do not reopen broad Backfill.
- Do not expand the 511-cell Backfill authority.
- Do not treat CID-NL/MS2 evidence as direct ProductWriter authority.
- Do not delete, merge, or demote source/successor row identities without a
  separate row-identity contract.
- Do not put full matrices or 95-cell generated manifests into version control.

## Product Path

1. Stabilize the current 95-cell Discovery scope.
   The current scope must stay reproducible through check-only replay, status
   index validation, authority validation, and artifact-retention validation.
   Current shortcut:
   `uv run python -m scripts.check_cid_nl_discovery_release_slice`.

2. Define the next Discovery-only expansion slice.
   The slice must be expressed as CID-NL Discovery candidates, not Backfill
   candidates. A candidate can move forward only when it has row identity,
   tag/source provenance, value delta, and expected matrix effect.

3. Build an expected-diff/provenance gate for that slice.
   The gate must prove exact keyset, exact values, preserved existing successor
   context, omitted no-target handling, and no unrelated matrix drift.

4. Activate only the passing slice.
   A passing slice may become a new registered Discovery writer scope. Failed,
   held, or ambiguous candidates stay outside default output.

## Acceptance Criteria For The Next CID-NL Slice

- Uses Discovery vocabulary in public artifacts:
  `accepted_discovery_cell_count`, `discovery_default_write`, or equivalent.
- Preserves legacy writer compatibility only in explicitly named compatibility
  fields.
- Has focused tests for row identity, source/successor provenance, tag evidence,
  matrix diff, and artifact retention.
- Updates the control plane only if maturity tier, active lane, authority,
  schema, or public contract changes.
- Produces a plain-language report that says what is product output and what is
  still review/diagnostic evidence.

## Stop Rule

Stop and split the work if the next step needs Backfill 4613 review, broad
Backfill policy changes, workbook/GUI behavior changes, selected peak/area
mutation, counted-detection changes, or source/successor identity deletion.
