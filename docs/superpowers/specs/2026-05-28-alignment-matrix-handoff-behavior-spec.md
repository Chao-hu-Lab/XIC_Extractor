# Alignment Matrix Handoff Behavior Spec

## Verdict

Status: `production_ready` after synthetic contract verification plus 8RAW/85RAW
primary artifact parity.

Validation status: synthetic/contract tests plus foreground 8RAW and 85RAW
`validation-minimal` runs. The raw validation evidence is recorded in
`docs/superpowers/notes/2026-05-28-pr70-alignment-matrix-handoff-raw-validation-note.md`.

This PR is not a spec-only checkpoint. It directly migrates the primary
`alignment_matrix.tsv` value path to the handoff spine contract while preserving
the emitted matrix schema and current value parity when the spine integration is
derived from the same selected peak.

## Decision Closed

The downstream correction/statistics delivery surface is `alignment_matrix.tsv`.
The optional `alignment_results.xlsx` Matrix sheet is a human/operator projection
of the same production decision set. The behavior question for this PR is
whether matrix cell values can be projected from the selected `IntegrationResult`
contract instead of reading only legacy `AlignedCell.area`.

Answer: yes, with a narrow compatibility rule.

## Behavior Contract

- `AlignedCell.selected_integration` is the alignment-facing selected
  `IntegrationResult` slot.
- `AlignedCell.matrix_area` is the canonical matrix value source:
  selected integration `area_raw_counts_seconds` first, legacy `area` fallback.
- Legacy fallback is named internally as `legacy_area_fallback` through
  `AlignedCell.matrix_area_source`; it is not an emitted schema field. The only
  current matrix-producing fallback allowed by this PR is a legacy alignment
  detected member with positive `ms1_area` but incomplete peak geometry, covered
  by regression test.
- If a selected integration exists, it is authoritative. Invalid selected
  integration area does not silently fall back to legacy `area`; the cell becomes
  non-quantifiable through the existing `invalid_area` path.
- `alignment_matrix.tsv` column names, order, row inclusion logic, RT policy,
  baseline behavior, resolver defaults, and audit schemas do not change in this
  PR.
- If `alignment_results.xlsx` is emitted, its `Matrix` sheet follows the same
  production matrix value projection as `alignment_matrix.tsv`; workbook sheet
  names, column order, and Audit scalar `area` projections remain unchanged.
  The workbook is a compatibility projection, not the downstream delivery
  surface for this PR.
- `alignment_cells.tsv` remains a compatibility/audit projection of existing
  `AlignedCell` scalar fields. This PR does not add TSV columns.

## Scope

Now:

- Add the selected integration slot to `AlignedCell`.
- Populate selected integration for every current matrix-producing integration
  path where selected peak or scalar owner fields are already known: owner
  detected cells, owner backfill, family integration, and legacy alignment
  backfill. Any intentionally unpopulated path must be named as legacy fallback
  and covered by a test.
- Make cell quality and production decisions use `cell.matrix_area`.
- Add focused synthetic tests for selected-integration matrix projection,
  invalid selected-integration authority, TSV/workbook schema stability, and
  owner / backfill wiring.

Not in scope:

- ASLS or baseline default promotion.
- Resolver default changes.
- CWT promotion or retirement.
- 8RAW / 85RAW validation as a prerequisite for this small contract migration.
- Phase2 cleanup.

## Acceptance

- Focused alignment tests pass.
- Final closeout reports `production_ready` only after the explicit follow-up
  8RAW/85RAW validation passes. Before that evidence, the status is only
  `production_candidate`.
- Existing matrix TSV header/order and workbook Matrix headers remain unchanged.
- Existing alignment workbook sheet/header contracts remain unchanged when the
  workbook projection is emitted.
- A controlled synthetic selected integration with a deliberately different
  positive raw area changes only the emitted matrix cell value, leaving schema,
  row inclusion, status, RT policy, resolver behavior, and audit scalar fields
  unchanged.
- A controlled synthetic selected integration with an invalid area changes the
  existing quantifiability decision through `invalid_area`; this is intentional
  selected-integration authority, not a value-only invariant.
- Existing behavior remains value-equivalent when selected integration is derived
  from the same selected peak or legacy owner fields.
- Missing selected integration does not create hidden fallback drift: any
  matrix-producing fallback must be named `legacy_area_fallback` and tested.
  Invalid selected integration never falls back.
