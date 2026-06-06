# Cleanup And Retirement One-Pass Goal

```text
/goal
GOAL:
On branch `codex/cleanup-retirement-foundation`, complete one PR that follows
the reviewed cleanup and retirement specs end to end: clean up diagnostic
ownership boundaries, satisfy or fail-closed the linear-edge retirement gates,
delete `linear_edge` when the gates pass, retire `arbitrated`, refresh the
cleanup roadmap state, and open a PR with one logical commit per completed
phase.

This goal is intentionally one-pass. Do not turn `linear_edge` retirement into
an unbounded "later PR" unless the current evidence proves a real blocker. A
real blocker must be named, reviewed, and recorded as a phase result.

CONTEXT:
- Repository/worktree:
  current XIC Extractor checkout, branch `codex/cleanup-retirement-foundation`.
- Current baseline:
  PR #78 is merged into `master`. AsLS is the primary baseline integration path;
  `linear_edge` remains as rollback/comparator/fallback/migration support.
- Repo instructions and routing:
  `AGENTS.md`,
  `docs/agent-subagent-routing.md`,
  `docs/agent-parameter-settings.md`,
  `docs/diagnostic-ledger.md`.
- Cleanup and retirement specs:
  `docs/superpowers/specs/2026-06-01-technical-debt-and-dead-code-cleanup-roadmap-v2-spec.md`,
  `docs/superpowers/specs/2026-05-24-peak-pipeline-cleanup-roadmap-overview-spec.md`,
  `docs/superpowers/specs/2026-05-24-peak-pipeline-cleanup-baseline-module-consolidation-spec.md`,
  `docs/superpowers/specs/2026-05-24-peak-pipeline-cleanup-area-integration-single-entry-spec.md`,
  `docs/superpowers/specs/2026-05-24-peak-pipeline-cleanup-linear-edge-retirement-spec.md`,
  `docs/superpowers/specs/2026-05-24-peak-pipeline-cleanup-resolver-collapse-spec.md`,
  `docs/superpowers/specs/2026-05-26-peak-pipeline-asls-truth-validation-spec.md`,
  `docs/superpowers/specs/2026-05-26-diagnostic-tool-lifecycle-spec.md`.
- Existing implementation plans:
  `docs/superpowers/plans/2026-06-01-asls-linear-edge-retirement-bc-implementation-plan.md`,
  `docs/superpowers/plans/2026-06-01-asls-tier-c-baseline-evidence-gate-implementation-plan.md`.
- Diagnostic catalog:
  `tools/diagnostics/INDEX.md`.
- Source-of-truth note:
  this goal intentionally supersedes cleanup roadmap v2's R1-only "next PR"
  recommendation for this branch after explicit user direction. Roadmap v2 stays
  historical context and a guardrail, but this goal is the active execution
  contract for the cleanup/retirement PR.
- Phase 0 execution baseline:
  branch `codex/cleanup-retirement-foundation`; dirty scope before the Phase 0
  commit is only
  `?? docs/superpowers/plans/2026-06-01-cleanup-retirement-one-pass-goal.md`.
  Pre-execution reviewers `strategy-challenger` and
  `implementation-contract-reviewer` both returned `PASS` after the blocker
  fixes were folded into this contract.

CONSTRAINTS:
- This PR may complete cleanup and retirement work, but every behavior-affecting
  deletion must satisfy its gate before the deletion commit lands.
- Do not preserve `linear_edge` merely because it is old public behavior. Its
  accepted direction is retirement.
- Do not delete `linear_edge` if the current-code Tier C evidence, blank/carryover
  disposition or exclusion, C1a/C5 prerequisites, or rollback-column deprecation
  is absent or failing. Instead, produce a reviewed `BLOCKED_BY_*` phase result
  with exact evidence.
- Do not delete `arbitrated` until public config behavior and fixture/test
  migration are explicit. If removal would silently break config, implement the
  migration or reviewed rejection behavior first.
- Preserve useful Savitzky-Golay utility behavior. This goal retires
  `arbitrated`; `legacy_savgol` stays accepted unchanged unless a phase adds a
  separate reviewed C2 policy and tests for that mode.
- Before deleting `linear_edge`, choose and test old public behavior for
  `baseline_integration_method=linear_edge`, CLI
  `--baseline-integration-method linear_edge`, and
  `BASELINE_INTEGRATION_METHOD=linear_edge`: either reject with a replacement
  message or keep a one-cycle alias with a deprecation warning.
- Preserve downstream contracts unless the phase explicitly retires them with
  tests and docs:
  `alignment_matrix.tsv`, workbook sheets, CLI flags, config keys, diagnostic
  TSV/JSON/Markdown schemas, run metadata keys, and import compatibility shims.
- Do not run a broad dead-code deletion audit. Delete only items named by these
  phases and only after their own gate passes.
- Every completed implementation phase must end in exactly one logical commit.
  A blocker phase may commit only docs/notes/tests that record the blocker.
- Verification integrity:
  do not weaken tests, type checks, lint, assertions, schema checks, diagnostic
  gates, or reviewer blockers to make the goal pass. Fix the root cause or
  record the blocker.

SUBAGENT / XHIGH REVIEW PROTOCOL:
- Before execution, review this goal and the first implementation plan with
  repo-routed read-only subagents:
  `strategy-challenger` and `implementation-contract-reviewer`.
- Before any phase that deletes `linear_edge`, removes rollback columns, or
  removes public resolver modes, run a blocking review using:
  `implementation-contract-reviewer` and `validation-evidence-reviewer`.
- If a reviewer finding contradicts user product direction or the specs, escalate
  to an xhigh decision pass. The pass must answer:
  1. Is the blocker real?
  2. Can it be fixed in this PR without changing the product contract silently?
  3. What is the smallest patch that lets the phase continue?
  4. If it cannot continue, what exact `BLOCKED_BY_*` result should be recorded?
- Use the repo补强 loop:
  fix blocker -> ask the original blocker reviewer to re-check -> add a third
  reviewer only if the fix moved into a new domain. Stop after three failed
  attempts on the same symptom and record the unresolved blocker.

PHASES AND COMMITS:

Phase 0 - Goal And Execution Contract
Commit: docs-only.
Purpose:
- Land this goal and, if needed, a short phase execution plan.
- Record branch baseline, known dirty scope, and subagent review disposition.
Done when:
- Goal/plan have no blocking review findings.
- `git status --short --branch` is recorded.

Phase 1 - Diagnostic Ownership Boundary (R1)
Commit: move-only.
Purpose:
- Move shared diagnostic IO/evidence helpers from tool-only ownership to a
  package-owned canonical path, while keeping `tools/diagnostics` as CLI/report
  wrapper and compatibility shim.
Required work:
- Choose a canonical path that does not violate the diagnostic lifecycle spec,
  or update the lifecycle spec with a schema-neutral infrastructure carveout.
- Keep `tools/diagnostics/diagnostic_io.py` import-compatible as a shim.
- Update package imports so `xic_extractor/` no longer imports
  `tools.diagnostics.*`.
- Update `tools/diagnostics/INDEX.md` shared-infrastructure wording.
Done when:
- No `xic_extractor/` module imports `tools.diagnostics.*`.
- Canonical-path tests and shim compatibility tests pass.
- Existing diagnostic TSV read/write behavior is unchanged.

Phase 2 - Diagnostic Lifecycle Catalog Refresh (R2)
Commit: docs/catalog-only unless a tiny no-behavior smoke test is needed.
Purpose:
- Refresh `tools/diagnostics/INDEX.md` counts and lifecycle wording so future
  gates do not drift.
Required work:
- Recount entry-point headings and helper files.
- Mark gate candidates individually; do not promote broad topic groups by
  proximity.
- Add tombstone or stale-count notes only when backed by current scan evidence.
Done when:
- INDEX totals match current scan or explicitly state why they are approximate.
- No diagnostic tool is deleted or promoted in this phase.

Phase 3 - C1a Baseline Module Consolidation
Commit: move-only.
Purpose:
- Finish the AsLS baseline ownership cleanup required before C1b.
Required work:
- Move the AsLS baseline implementation into the peak-detection package-owned
  location named by C1a.
- Keep top-level `xic_extractor.baseline` as a compatibility re-export unless a
  reviewed breaking-change note explicitly allows removal.
- Update imports that can safely use the new canonical path.
Done when:
- Public import compatibility for `xic_extractor.baseline.asls_baseline` passes.
- Production code uses the canonical package path where appropriate.
- No area values, baselines, scores, or output schemas change.

Phase 4 - C5 Single Integration Entry Closeout
Commit: method-preserving integration cleanup.
Purpose:
- Prove every maintained baseline-corrected integration caller routes through
  the single selector or an approved comparator interface.
Required work:
- Scan `xic_extractor/`, `tools/`, `scripts/`, and tests for direct
  `integrate_linear_edge_baseline` callers.
- Migrate production/package callers to `integrate_with_baseline` or direct
  AsLS-only integration when allowed by the C5/C1b specs.
- For maintained diagnostics, either route through an approved comparator
  interface or mark the diagnostic as retired before C1b.
Done when:
- No production/package caller directly calls `integrate_linear_edge_baseline`.
- Any remaining diagnostic/test caller is explicitly classified as comparator,
  migration guard, or deletion-diff-only.

Phase 5 - Tier C Evidence Assembly Before Rollback Removal
Commit: evidence artifacts, fixture updates, docs/notes, or small gate fixes.
Purpose:
- Assemble the current-code evidence required to decide whether linear-edge can
  proceed to rollback schema cleanup and final retirement GO.
Required work:
- Run or validate the AsLS-vs-linear-edge Tier C baseline evidence gate using
  existing artifacts when fresh and sufficient, or generate the missing bounded
  evidence with documented RAW/DLL runner settings.
- Validate blank/carryover safety or an explicit exclusion/pass-through
  contract.
- Validate C1a and C5 prerequisite status.
- Record whether rollback-column removal is still a prerequisite before final
  retirement GO.
Done when:
- `asls_truth_validation` for `decision_target=linear-edge-retirement` emits
  `REQUIRES_RETIREMENT_PREREQS`, `BLOCKED_BY_TIER_C`,
  `BLOCKED_BY_BLANK_SAFETY`, or `NO_GO_KEEP_LINEAR_EDGE`.
- This phase must not emit the final `GO_FOR_LINEAR_EDGE_RETIREMENT` if
  rollback columns are still present or the post-removal schema is not frozen.
- If blocked, the blocker is concrete enough that another PR would know exactly
  what evidence or contract is missing.

Phase 6 - Rollback Column Deprecation / Removal
Commit: schema-contract cleanup.
Purpose:
- Remove the temporary linear-edge rollback audit surface only if Phase 5 leaves
  retirement as `REQUIRES_RETIREMENT_PREREQS`.
Required work:
- Remove or deprecate `area_baseline_corrected_linear_edge` and
  `baseline_score_linear_edge` only after an approved schema/deprecation note.
- Update writer tests, diagnostic readers, and docs.
Done when:
- Accepted audit schemas no longer require recomputing linear-edge rollback
  columns, or the phase records a reviewed `BLOCKED_BY_ROLLBACK_SCHEMA` result.
- The exact post-removal `alignment_cell_integration_audit.tsv` header/order is
  frozen in a schema note with a hash or equivalent machine-checkable snapshot.
- Writer tests assert removed rollback columns are absent.
- Diagnostic readers either accept the new schema or fail with an actionable
  regeneration/migration message.

Phase 6b - Final Retirement Prerequisite Manifest And GO
Commit: evidence manifest or docs/test update.
Purpose:
- Re-run the final linear-edge retirement decision after rollback schema cleanup,
  so deletion is based on the actual post-rollback contract.
Required work:
- Rebuild the C1a, C5, Tier C, blank/carryover, old-config behavior, and
  rollback-schema prerequisite manifest.
- Run or refresh `asls_truth_validation` with
  `decision_target=linear-edge-retirement` against the post-Phase-6 state.
Done when:
- The gate emits `GO_FOR_LINEAR_EDGE_RETIREMENT`, or records a reviewed
  `BLOCKED_BY_TIER_C`, `BLOCKED_BY_BLANK_SAFETY`,
  `BLOCKED_BY_ROLLBACK_SCHEMA`, `BLOCKED_BY_PUBLIC_CONFIG_MIGRATION`,
  `BLOCKED_BY_RETIREMENT_PREREQS`, or `NO_GO_KEEP_LINEAR_EDGE` result.
- Phase 7 cannot start without `GO_FOR_LINEAR_EDGE_RETIREMENT`.

Phase 7 - C1b Linear-Edge Deletion
Commit: deletion commit.
Purpose:
- Delete the linear-edge baseline implementation and selector support once
  Phase 3, Phase 4, Phase 5, Phase 6, and Phase 6b gates pass.
Required work:
- Before deletion, implement and test the chosen old public behavior for
  `baseline_integration_method=linear_edge`, CLI
  `--baseline-integration-method linear_edge`, and
  `BASELINE_INTEGRATION_METHOD=linear_edge`.
- Delete `integrate_linear_edge_baseline`.
- Remove `"linear_edge"` from `BaselineMethod`, settings schema, config docs,
  selector dispatch, tests, and diagnostic code paths that are no longer needed.
- Remove linear-edge-only fixtures or convert them to historical regression
  artifacts outside production selectors.
Done when:
- Repository-wide scan finds no maintained `linear_edge` production/config/
  diagnostic selector support except historical docs describing retirement.
- Settings parser, CLI/env behavior, run metadata, config docs, and selector
  tests cover the old `linear_edge` input behavior.
- AsLS-only production integration tests pass.
- C1b spec acceptance criteria are satisfied.

Phase 8 - C2 Arbitrated Resolver Retirement
Commit: resolver retirement commit.
Purpose:
- Retire the experimental `arbitrated` resolver mode in the same cleanup PR.
  `legacy_savgol` is explicitly out of scope and remains accepted unchanged
  unless this phase adds a separate reviewed policy and tests.
Required work:
- Scan public config, CLI/env surfaces, docs, tests, scripts, diagnostics, and
  likely external callers for `resolver_mode=arbitrated` / `arbitrated`.
- Run a bounded one-shot 8RAW comparison for `resolver_mode=arbitrated` against
  the supported resolver path before removing it, unless current artifacts
  already answer the same question.
- Decide public config behavior: warn+map, reject with migration message, or
  preserve alias for one compatibility cycle.
- Remove the arbitrated branch and helper code only after tests pin the chosen
  config behavior.
- Preserve useful non-arbitrated logic if it is still used by supported modes.
Done when:
- `arbitrated` is no longer an accepted production resolver mode, or it is an
  explicit compatibility alias with deprecation warning and removal date.
- Tests cover old config behavior and supported resolver behavior.
- If blocked, the phase records one of:
  `BLOCKED_BY_EXTERNAL_RESOLVER_CALLER`, `BLOCKED_BY_ARBITRATED_BETTER`, or
  `BLOCKED_BY_CONFIG_MIGRATION`.

Phase 9 - Cleanup Roadmap And Spec Closeout
Commit: docs closeout.
Purpose:
- Make the durable docs match the actual code state after this PR.
Required work:
- Update the cleanup roadmap v2, peak-pipeline cleanup overview, C1a/C2/C5/C1b
  specs, diagnostic lifecycle notes, and `tools/diagnostics/INDEX.md`.
- Mark completed phases, true blockers, and remaining out-of-scope work.
Done when:
- Docs do not claim `linear_edge` is still pending if it was deleted.
- If deletion was blocked, docs name the exact blocker and the evidence path.
- No stale marker wording remains in touched docs.

Phase 10 - Final Verification And PR Closeout
Commit: none unless validation note or docs update is required.
Purpose:
- Prove the PR is reviewable and safe.
Required work:
- Run the XIC PR gate:
  `$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor tests`
  `$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor`
  `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -v --tb=short -x`
- Run focused tests named by each phase.
- Run docs smoke checks and `git diff --check`.
- Open PR with phase-by-phase commit summary, verification, and residual risk.
Done when:
- PR is open and describes which phases completed, which were blocked, and why.
- Worktree is clean except intentional local artifacts.

DONE WHEN:
- Phase 1 through Phase 9, including Phase 6b, have either completed with commits
  or stopped with a reviewed, concrete `BLOCKED_BY_*` /
  `NO_GO_KEEP_LINEAR_EDGE` result.
- If all retirement gates pass, `linear_edge` and `arbitrated` are no longer
  maintained production/config behavior.
- `linear_edge` deletion happens only after Phase 6b emits
  `GO_FOR_LINEAR_EDGE_RETIREMENT`.
- If any retirement gate does not pass, the PR still lands the safe foundation
  phases and records the exact blocker without pretending the retirement is
  complete.
- Each completed phase has one logical commit.
- No unrelated cleanup, broad dead-code purge, or speculative refactor is mixed
  into the PR.
- Full PR verification passes or the exact environment blocker is reported.

VERIFY:
- Phase-specific focused tests before each commit.
- Required XIC PR gate before opening or marking PR ready:
  `$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor tests`
  `$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor`
  `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -v --tb=short -x`
- If RAW-backed evidence is needed, use `docs/agent-parameter-settings.md`
  runner paths, preflight, output-level rules, heartbeat/timing expectations,
  and no background `Start-Process` 85RAW pattern.
- Inspect:
  `git status --short --branch`,
  staged diff before every commit,
  final PR diff,
  relevant diagnostic summaries and plots for Tier C.

OUTPUT:
- Phase-by-phase status table.
- Commit list with phase mapping.
- Files changed by phase.
- Subagent/xhigh review findings and fixes.
- Verification command outputs.
- Tier C / C1b decision result.
- Remaining risk and next action.
- PR URL.

STOP RULES:
- Stop only for real blockers, not uncertainty-by-default.
- Stop if Tier C evidence or blank/carryover safety shows AsLS should not retire
  linear-edge for the scoped production path.
- Stop if old `linear_edge` config/CLI/env behavior is still undecided before
  deletion.
- Stop if the `arbitrated` one-shot comparison materially outperforms the
  supported resolver path for the scoped acceptance fixture.
- Stop if deleting a public config/schema/import path would silently break users
  and no migration behavior is accepted.
- Stop if a RAW validation command needs unavailable paths/DLLs or repeats a
  known failed launch pattern.
- Stop after three failed fixes for the same blocker and record the blocker with
  evidence.
- Do not mark the goal complete until final state is checked against DONE WHEN.
```
