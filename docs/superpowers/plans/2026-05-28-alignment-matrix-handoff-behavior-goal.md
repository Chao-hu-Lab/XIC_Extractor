# Alignment Matrix Handoff Behavior Goal

```text
/goal
GOAL:
Make `alignment_matrix.tsv` and the optional `alignment_results.xlsx` Matrix
projection consume the handoff spine selected integration contract for matrix
cell values while preserving existing schemas and current value parity when
selected integration is derived from the same legacy owner/backfill peak.

CONTEXT:
- Repository/worktree: XIC Extractor,
  `codex/alignment-matrix-handoff-behavior`.
- Product direction:
  `TraceGroup -> PeakHypothesis -> EvidenceVector -> IntegrationResult ->
  AuditTrail -> downstream matrix`.
- Active contract spec:
  `docs/superpowers/specs/2026-05-28-alignment-matrix-handoff-behavior-spec.md`.
- Validation label:
  `production_ready` after explicit follow-up 8RAW/85RAW
  `validation-minimal` foreground runs and primary artifact parity.
- Implementation plan:
  `docs/superpowers/plans/2026-05-28-alignment-matrix-handoff-behavior-implementation-plan.md`.
- Repo instructions:
  `AGENTS.md`, `docs/agent-subagent-routing.md`, and
  `docs/agent-parameter-settings.md`.
- Current code path:
  `alignment_matrix.tsv` is written through `alignment.tsv_writer`,
  `alignment.production_decisions`, `alignment.cell_quality`, and
  `alignment.matrix.AlignedCell`.
- Related projection:
  `alignment_results.xlsx` Matrix sheet uses `alignment.xlsx_writer` and the same
  production decision set.

CONSTRAINTS:
- Do not change `alignment_matrix.tsv` column names, order, row inclusion rules,
  or downstream handoff filename.
- Keep `alignment_results.xlsx` sheet names and column order unchanged; its
  `Matrix` sheet should mirror the same production matrix value projection as
  `alignment_matrix.tsv`, while audit scalar `area` fields stay legacy
  projections.
- Do not change resolver defaults, RT policy, NL matching, baseline/ASLS
  behavior, CWT behavior, workbook schemas, CLI/config keys, or Phase2 cleanup.
- Preserve existing alignment matrix value parity when selected integration is
  built from the same legacy owner/backfill peak or owner scalar fields.
- If selected integration exists, it is authoritative for matrix area; do not
  silently fall back to legacy `area` when the selected integration area is
  invalid.
- Keep implementation surgical and scoped to alignment matrix handoff behavior.
- Verification integrity: do not weaken or bypass tests, assertions, lint,
  validation, generated-output checks, or external blockers to make the goal
  pass; fix the root cause or report the blocker.

DONE WHEN:
- `AlignedCell` has a selected `IntegrationResult` slot and a single canonical
  matrix-area accessor.
- Cell quality and production matrix decisions use that accessor.
- Owner detected, owner backfill, family integration, and legacy alignment
  backfill paths populate selected integration when selected peak/scalar values
  are already known; any intentionally unpopulated matrix-producing path is
  named as `legacy_area_fallback` and tested.
- Focused tests prove selected-integration projection, invalid selected-area
  authority, matrix TSV schema/order stability, workbook projection consistency,
  and owner/backfill wiring parity.
- Spec, goal, and plan have been reviewed by the repo-local reviewer roles
  required by `docs/agent-subagent-routing.md`, and blocking findings are fixed.
- Post-implementation critical/devex review has been run or explicitly scoped
  down with evidence.
- No unrelated dirty files or generated runtime artifacts are included.

VERIFY:
- Run:
  `$pyFiles = git ls-files --modified --others --exclude-standard -- '*.py'; python -m ruff check $pyFiles`
- Run:
  `$env:PYTHONDONTWRITEBYTECODE='1'; $files = Get-ChildItem tests -Filter 'test_alignment_*.py' | ForEach-Object { $_.FullName }; python -m pytest -p no:cacheprovider @files -q`
- Run:
  `$env:PYTHONDONTWRITEBYTECODE='1'; python -m pytest -p no:cacheprovider tests\test_alignment_xlsx_writer.py -q`
- Run:
  `$env:PYTHONDONTWRITEBYTECODE='1'; python -m pytest -p no:cacheprovider tests\test_untargeted_final_matrix_contract.py -q`
- Inspect:
  `git diff --check`, `git diff --cached --check` after staging, and
  `git status --short --branch`.
- If any command cannot run, stop and report the exact blocker.

OUTPUT:
- Changed files.
- Reviewers used and blocker fixes.
- Verification output.
- Remaining risk, including that this is synthetic/contract validated and real
  RAW validation is scoped to primary artifact parity for this PR.
- Next action: commit/open PR or further fix.

STOP RULES:
- Stop on missing secrets, production credentials, destructive data operations,
  unclear product decisions, or unsafe permissions.
- Stop on public schema changes not named in the spec.
- Stop if a reviewer finding contradicts the product direction or requires a
  user decision.
- Stop if RAW runner paths or long validation become necessary; this goal is
  synthetic/contract validation only unless the user explicitly asks for RAW.
- Stop after three failed attempts on the same symptom and revisit root cause.
- Do not mark complete until the current state is audited against DONE WHEN.
```
