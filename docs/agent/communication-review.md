# Communication And Review Surfaces

This file carries the longer communication and review rules that used to live in
root `AGENTS.md`. Keep the root file limited to high-frequency guardrails.

## Verdict-First Communication

- Non-trivial wrap-ups must state the current verdict first: what is done, what
  is still blocked, and the next recommended step.
- Use plain language before implementation detail. Say what changed, where, how
  it was checked, what was skipped, and what risk remains.
- During long, tool-heavy work, explain what question the current tools are
  answering and how the result changes the next action. Do not rely on internal
  artifact names such as board row counts, slice labels, or TSV filenames
  without translating what they mean for the product decision.
- Final answers for implementation or validation work should include, when
  applicable: conclusion, changed files or artifact paths, verification run,
  remaining risk, and next action.

## Human Review Surfaces

- Separate machine artifacts from human review surfaces. TSV/JSON may be
  exhaustive; Markdown specs are mostly for agents; human-facing reports should
  be short, visual or indexed, and decision-oriented.
- Manual review requests should include a compact review index with identifiers:
  sample, label or family id, m/z, RT/window, status, reason, and linked
  artifact path.
- Worktree or PR closeout should leave an operator-readable handoff: branch/task
  purpose, verdict, important artifacts, validation commands/results, active
  blockers, rejected paths still likely to recur, and an explicit next-step
  recommendation. Keep it as current state, not a chronological log.
- Handoffs are branch-scoped. The default active handoff is the ignored local
  file `docs/superpowers/handoffs/current/ACTIVE.local.md`; use a branch-named
  ignored local file only when multiple branches need simultaneous state.
  Before editing a repo-tracked handoff, verify the file name and its `Branch:`
  / `Status:` match the current branch or PR workflow.
- Active handoffs should stay short enough to read every time, normally under
  about 200 lines. Completed phase summaries belong in the PR body by default;
  force-add repo archive summaries only when they are intentionally public
  evidence. Long logs, stack traces, and scratch analysis belong in Obsidian
  only when still useful.
- When long context is moved to Obsidian, the active local handoff remains a
  self-sufficient stub. Obsidian links are optional deep context, not required
  for understanding the next safe action.
- Treat repo handoffs and PR bodies as public-facing summaries. They may state
  the approved decision, validation actually run, residual risk, and next
  action, but they must not paste private Obsidian reasoning, raw command
  transcripts, local absolute paths, sample-level investigation detail, or
  private data placement back into the repo.
- PR body is the normal durable closeout surface. Condense the branch handoff
  into the PR body instead of treating the current handoff as the final record;
  add compact completed phase summaries under `docs/superpowers/closeouts/`
  only when they must remain in repo.
- Handoff retention is inventory-driven only for git-tracked handoff files.
  Ignored local handoffs do not need `RETENTION.tsv` rows. Any force-added file
  under `docs/superpowers/handoffs/current/` or
  `docs/superpowers/handoffs/archive/` must also be recorded in
  `docs/superpowers/handoffs/RETENTION.tsv`. Use
  `tools/diagnostics/handoff_retention_audit.py` before PR closeout only when
  tracked handoff files changed. The audit is not deletion approval.
- Status labels such as `[active]`, `[blocked]`, `[done]`, and `[superseded]`
  are useful in open-work sections. Remove `[done]` and `[superseded]` items
  from the active handoff during the next prune unless they prevent repeated
  mistakes.

## Review Checklist

After completing changes, quickly check:

- requirement fit;
- public contract drift;
- GUI / CLI / API behavior divergence;
- regression risk;
- missing tests;
- security issues;
- over-complexity;
- generated artifacts, marker maps, lockfiles, or docs that should be synced.

When reviewing progress or a checklist, distinguish infrastructure existence
from usable product behavior. Reports, wrappers, sidecars, and audit artifacts
prove observability; they do not prove production behavior.
