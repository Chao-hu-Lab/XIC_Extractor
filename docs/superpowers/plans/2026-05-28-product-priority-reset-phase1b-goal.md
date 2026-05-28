# Product Priority Reset Phase 1b Goal

This goal uses the `Plan-Then-Goal Execution`, `Long Task Until Verification`,
and `Completion Audit Before Done` shapes from the local
`awesome-goal-prompts` reference.

```text
/goal
GOAL:
Complete Product Priority Reset Phase 1b by implementing the reviewed
cell-evidence-backed untargeted promotion policy, validating it on the required
synthetic and RAW surfaces, and producing exactly one qualitative-selection gate
classification for PR #72.

CONTEXT:
- Repository/worktree:
  C:\Users\user\Desktop\XIC_Extractor\.worktrees\product-priority-reset
- Active branch:
  codex/product-priority-reset
- Repo instructions:
  AGENTS.md
  docs/agent-subagent-routing.md
  docs/agent-parameter-settings.md
- Decision spec:
  docs/superpowers/specs/2026-05-28-product-priority-reset-decision-spec.md
- Reviewed implementation plan:
  docs/superpowers/plans/2026-05-28-product-priority-reset-phase1b-implementation-plan.md
- Existing gate note to update or replace:
  docs/superpowers/notes/2026-05-28-qualitative-selection-acceptance-gate-note.md
- Production / diagnostic code surfaces:
  xic_extractor/alignment/matrix_identity.py
  xic_extractor/alignment/identity_gates.py
  xic_extractor/discovery/evidence_score.py
  tools/diagnostics/single_dr_production_gate_decision_report.py
- Test surfaces:
  tests/test_alignment_matrix_identity.py
  tests/test_single_dr_production_gate_decision_report.py
  tests/test_discovery_evidence.py
  tests/test_alignment_tsv_writer.py
- Stable validation inputs:
  C:\Users\user\Desktop\XIC_Extractor\local_validation_artifacts\discovery\accepted_p8b\8raw\discovery_batch_index.csv
  C:\Users\user\Desktop\XIC_Extractor\local_validation_artifacts\discovery\accepted_p8b\85raw\discovery_batch_index.csv

CONSTRAINTS:
- Execute the reviewed implementation plan unless live evidence forces a smaller
  safe adjustment that preserves the spec.
- Keep scope limited to untargeted discovery / alignment matrix promotion for
  rescued-heavy single-dR rows and the gate note needed to classify that change.
- Do not change targeted scoring, targeted workbooks, resolver defaults,
  baseline defaults, ASLS promotion, CWT production behavior, boundary selector
  defaults, matrix schema, or Phase2 cleanup.
- Do not create target-specific exceptions for `FAM000264`, `d3-N6-medA`,
  `TumorBC2289_DNA`, or `TumorBC2290_DNA`.
- Do not globally retune emitted discovery `evidence_score`; promotion-only
  components may be added only if existing score/tier semantics stay pinned.
- Production decisions must expose canonical `identity_reason` and supplemental
  `row_flags` in `alignment_review.tsv`. Sidecars or diagnostics may add detail
  but cannot be the only decision surface.
- RAW validation must use active-worktree `.venv\Scripts\python.exe`, foreground
  execution, `validation-minimal`, `production-equivalent`,
  `audit-evidence-mode none`, `validation-fast`, `super-window`, and heartbeat
  timing outputs.
- Do not run 85RAW unless focused tests pass and 8RAW closes or narrows the
  decision. Reused 85RAW evidence must be reclassified under the new policy and
  produce the required production delta table.
- Verification integrity: do not weaken or bypass tests, assertions,
  validation, generated-output checks, review gates, or blockers to make the
  goal pass; fix the root cause or report the blocker.

DONE WHEN:
- A shared cell-evidence-backed promotion policy exists and is used by both
  production matrix identity decisions and the single-dR diagnostic, including a
  TSV adapter for `alignment_review.tsv` / `alignment_cells.tsv`.
- Focused tests cover the shared policy, matrix identity behavior, diagnostic
  parity, discovery score stability, TSV reason/flag output, and delta-table
  behavior.
- 8RAW validation has been run or blocked by a named preflight failure according
  to the reviewed plan.
- 85RAW has been reused, refreshed, or intentionally skipped according to the
  reviewed plan's stop rules.
- `docs/superpowers/notes/2026-05-28-qualitative-selection-acceptance-gate-note.md`
  contains command shapes, artifact paths, risky-row collateral, validation
  outcome, review outcome, and exactly one `Final Classification:` line from
  the four allowed classifications.
- Post-implementation subagent review has run with at least
  `implementation-contract-reviewer` and `validation-evidence-reviewer`; blocking
  findings are fixed or become explicit `NO_GO` / `INCONCLUSIVE` reasons.
- No unrelated dirty files are staged or hidden by verification side effects.

VERIFY:
- Run the focused no-RAW pytest shard named in the implementation plan.
- Run the 8RAW preflight and, when preflight passes, the foreground 8RAW
  validation-minimal command.
- Run the single-dR production gate diagnostic on the post-change 8RAW output.
- If 85RAW is required by the plan, run the 85RAW preflight before any full
  foreground 85RAW command.
- Run Markdown / diff smoke checks for the spec, plan, goal, and gate note.
- Inspect `git status --short --branch` before final reporting.
- If any verification cannot run, stop and report the exact blocker.

OUTPUT:
- Changed files grouped by purpose.
- Tests and validation commands run, with pass/fail or blocker.
- 8RAW and 85RAW evidence status.
- Final gate classification.
- Reviewer findings and resolution.
- Remaining risk and the single recommended next action.

STOP RULES:
- Stop on missing RAW/DLL/runtime paths, missing accepted discovery inputs,
  missing worktree `.venv`, secrets, production credentials, destructive data
  operations, unsafe permissions, or unclear product decisions.
- Stop if production promotion requires diagnostic-only overlay evidence or a
  target-specific exception.
- Stop if 8RAW is `NO_GO` or has more than three unresolved rows; do not run
  85RAW just to inspect what happens.
- Stop if reused or refreshed 85RAW evidence cannot produce a complete
  production delta table under the new policy.
- Stop after three failed attempts on the same symptom and revisit the root
  cause hypothesis.
- Do not mark complete until the current state has been checked against
  DONE WHEN and VERIFY.
```
