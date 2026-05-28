# Alignment Matrix Handoff Behavior Implementation Plan

> Scope note: this plan is being added in the same PR as the behavior change.
> An initial candidate diff already exists in this worktree; Task 0 audits and
> normalizes that diff before continuing. This preserves the requested
> spec/goal/plan/review flow without splitting PR70 into a spec-only branch.

## Objective

Move the downstream `alignment_matrix.tsv` value source and optional
`alignment_results.xlsx` Matrix projection from direct legacy `AlignedCell.area`
reads to the handoff spine selected `IntegrationResult` contract, while
preserving schemas and current value parity for integrations derived from the
same peak or owner scalar fields.

Validation label: `production_ready` after synthetic/contract verification plus
explicit follow-up 8RAW/85RAW primary artifact parity.

## Now

- [x] Task 0 - Scope and current-diff audit
  - Confirm branch/worktree and dirty scope.
  - Confirm the change touches alignment matrix behavior, not Phase2 cleanup.
  - Confirm no generated runtime artifacts are staged or required.

- [x] Task 1 - Contract artifacts
  - Keep behavior contract in
    `docs/superpowers/specs/2026-05-28-alignment-matrix-handoff-behavior-spec.md`.
  - Keep finish-line contract in
    `docs/superpowers/plans/2026-05-28-alignment-matrix-handoff-behavior-goal.md`.
  - Review both with `strategy-challenger` and
    `implementation-contract-reviewer`; apply blocking fixes.

- [x] Task 2 - Matrix value contract
  - Add `AlignedCell.selected_integration`.
  - Add a single matrix value accessor that prefers selected
    `IntegrationResult.area_raw_counts_seconds` and falls back to legacy
    `area`.
  - Update cell quality and production decisions to use the accessor.

- [x] Task 3 - Selected integration wiring
  - Add an alignment-facing adapter that builds `IntegrationResult` from legacy
    peak/scalar inputs without changing selection logic.
  - Populate selected integration in owner detected cells.
  - Populate selected integration in owner backfill, family integration, and
    legacy backfill paths.
  - Name and test any intentionally unpopulated matrix-producing path as legacy
    fallback; otherwise treat missing wiring as a blocker.
  - The only accepted fallback in this PR is legacy alignment detected members
    with positive area but incomplete peak geometry; it is named
    `legacy_area_fallback` via `AlignedCell.matrix_area_source` and regression
    tested.
  - Preserve scalar fields used by audit TSVs and compatibility surfaces.

- [x] Task 4 - Contract and parity tests
  - Test selected integration area projection into cell quality and production
    decision values.
  - Test selected integration authority when its area is invalid.
  - Test `alignment_matrix.tsv` schema/order stability and selected-integration
    value projection.
  - Test existing `alignment_results.xlsx` `Matrix` sheet projection stays
    consistent with the same production matrix value source when emitted, while
    Audit scalar fields remain legacy projections.
  - Test owner/backfill wiring parity.
  - Expand to all `test_alignment_*.py` synthetic tests and final matrix
    contract tests.

- [x] Task 5 - Post-implementation review and closeout
  - Run implementation review with `implementation-contract-reviewer`.
  - Run `critical-artifact-review` against the durable artifacts and diff.
  - Run `devex-review` in artifact/CLI-oriented mode, scoped to command
    reproducibility and developer recovery rather than web onboarding.
  - Fix blockers, rerun focused verification, and summarize residual risk.

## Later

- Real 8RAW and 85RAW validation was explicitly requested after
  synthetic/contract tests and passed. Evidence is recorded in
  `docs/superpowers/notes/2026-05-28-pr70-alignment-matrix-handoff-raw-validation-note.md`.
- Baseline/ASLS promotion and resolver/CWT retirement remain separate behavior
  decisions.

## Not In Scope

- Phase2 cleanup.
- `alignment_matrix.tsv` schema changes.
- New workbook generation paths, HTML, large validation output,
  owner-edge/status-matrix/event-owner artifacts.
- Workbook schema changes. The existing `alignment_results.xlsx` `Matrix` sheet
  mirrors the production matrix value projection, but sheet names, column order,
  and audit scalar `area` fields stay unchanged.
- New CLI/config flags or diagnostic entrypoints.

## Verification Commands

```powershell
$pyFiles = git ls-files --modified --others --exclude-standard -- '*.py'
python -m ruff check $pyFiles
```

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
$files = Get-ChildItem tests -Filter 'test_alignment_*.py' | ForEach-Object { $_.FullName }
python -m pytest -p no:cacheprovider @files -q
```

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python -m pytest -p no:cacheprovider tests\test_untargeted_final_matrix_contract.py -q
```

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python -m pytest -p no:cacheprovider tests\test_alignment_xlsx_writer.py -q
```

```powershell
git diff --check
git diff --cached --check
git status --short --branch
```

## Acceptance

- The matrix value call path is:
  `write_alignment_matrix_tsv -> build_production_decisions ->
  build_cell_quality_decisions -> AlignedCell.matrix_area`.
- Existing matrix schema/order is unchanged.
- Existing alignment workbook schema/order is unchanged, and the `Matrix` sheet
  uses the same production matrix value projection if emitted.
- A positive selected integration can deliberately change only the emitted
  matrix cell value in a synthetic fixture.
- An invalid selected integration deliberately changes the existing
  quantifiability decision through `invalid_area`.
- Owner/backfill-derived selected integration remains value-equivalent to the
  existing scalar fields.
- Any selected-integration-missing matrix-producing value path is either wired or
  explicitly named/tested as `legacy_area_fallback`.
- All blockers from artifact and implementation review are fixed or explicitly
  deferred as non-blocking.

## Review Closeout

- `docs-handoff-reviewer`: PASS at the pre-RAW stage. Spec/goal/plan correctly
  avoided `production_ready` before real-data evidence; after explicit follow-up
  RAW validation, the status is upgraded to `production_ready` for this PR.
- `implementation-contract-reviewer`: initial BLOCKER on an unnamed legacy area
  fallback path. Fixed by adding `AlignedCell.matrix_area_source`,
  `legacy_area_fallback` contract wording, and regression tests for incomplete
  legacy peak geometry. Re-check PASS.
- `devex-review`: CLEAR. Commands are PowerShell-correct, include modified plus
  untracked Python files for ruff, and stop rules prevent accidental RAW
  escalation. Added staged-diff whitespace check as a PR/commit-time reminder.
- RAW validation: 8RAW and 85RAW foreground `validation-minimal` runs passed
  with primary `alignment_matrix.tsv`, `alignment_review.tsv`, and
  `alignment_cells.tsv` byte-identical to accepted P8b outputs.
