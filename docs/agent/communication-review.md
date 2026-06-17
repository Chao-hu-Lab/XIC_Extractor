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
  purpose, verdict, important artifacts, validation commands/results, and an
  explicit next-step recommendation.

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
