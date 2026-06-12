# Large Diagnostics PR Review Retrospective

Date: 2026-06-12

Scope: PR #84, `codex/backfill-diagnostics-architecture`, which refactored
diagnostics architecture, shared TSV helpers, matrix identity projection, RAW
overlay locality/reuse, and recorded the 8RAW matrix-only vs deep-audit parity
gate.

## What Worked

- Review effort was spent on high blast-radius surfaces first:
  `xic_extractor/tabular_io.py`, matrix identity projection, shadow production
  projection, backfill overlay selection, overlay RAW batching/cache, backfill
  scope fast paths, and adduct candidate pruning.
- The PR was judged against the actual decision it could close: 8RAW
  matrix-only vs deep-audit parity for activation decisions, value delta,
  matrix output, and identity sidecars.
- 85RAW was explicitly kept out of scope. That made the review honest: the PR
  could be accepted as an 8RAW-backed architecture/performance cleanup without
  overclaiming 85RAW production readiness.
- For a 277-file diff, the review avoided fake completeness. It inspected
  central helpers, representative writer migrations, and focused tests, then
  reported residual risk from PR size.

## Reusable Lesson

Large XIC diagnostics PRs should not be reviewed by evenly scanning every
changed writer. Build a blast-radius map first:

1. Shared helpers and compatibility shims.
2. Public contract surfaces: CLI/config/schema/workbook/matrix/value-delta.
3. Diagnostic architecture boundaries: CLI orchestration vs package logic.
4. RAW access locality, batching, cache, and fallback behavior.
5. Product-vs-diagnostic claims.
6. Evidence tier: CI, focused tests, 8RAW, 85RAW, targeted benchmark, manual
   EIC/MS2 review, or diagnostic-only artifact review.

If no high-confidence issue is found, say so plainly and name what remains
unproven. Do not invent findings to compensate for large diff size.

The stronger upstream lesson is now captured separately in
`2026-06-12-dataset-agnostic-evidence-architecture-principle.md`: avoid creating
the debt in the first place by requiring architecture/reuse/call-cost preflight
before non-trivial diagnostics, RAW evidence, preset performance, matrix
activation, or new evidence-provider work.

## Codified Surfaces

- Added `.codex/skills/xic-large-pr-review/SKILL.md` for future large PR review
  prompts.
- Updated `docs/agent-subagent-routing.md` so this repo-local skill has a clear
  trigger and does not conflict with `xic-pr-closeout`.
- Updated `docs/architecture-contract.md` to make large diagnostics review
  start from shared helpers and public contracts.
- Updated `tools/diagnostics/INDEX.md` to point diagnostics refactor reviews at
  the new skill and reinforce representative parity over mechanical churn.

## Stop Rule

Use the skill when the user asks to review a PR and the diff is large, stacked,
diagnostics-heavy, or tied to preset performance/parity/RAW evidence. Do not use
it for ordinary small PRs, simple CI triage, or PR description closeout.
