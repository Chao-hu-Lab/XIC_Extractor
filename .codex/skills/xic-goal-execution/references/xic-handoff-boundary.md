# XIC Handoff Boundary

Apply the global current-state handoff rule through this overlay because XIC
goals are usually launched via `$goal-execution`.

Use the active handoff named by the goal, control plane, plan, or PR workflow;
use `HANDOFF.md` only when the current goal establishes it as active. The active
handoff is a short continuation snapshot, not the productization tier authority.
Tier history, lane evidence, and per-round maintenance logs belong in the
control plane, named specs, validation notes, or archive.

For XIC, the three-layer rule is:

- active handoff: short current-state snapshot;
- archive: completed phase summaries only, not raw progress logs;
- notes: optional long logs, scratch analysis, and temporary exploration.

Before each meaningful checkpoint, compact-risk pause, or closeout:

1. Inspect `git status`, intended dirty scope, and latest validation evidence.
2. Rewrite the active handoff from current repo state instead of appending a
   chronological update.
3. Keep only active constraints, decisions, blockers, validation, relevant file
   changes, rejected paths likely to be repeated, and next 1-3 actions.
4. Use `[active]`, `[blocked]`, `[done]`, and `[superseded]` labels only when
   they make pruning easier.
5. If the active handoff is over about 200 lines, prune before continuing unless
   the user explicitly asks for a longer handoff.

Hooks may remind that a handoff is stale or missing, but the executing agent
owns the rewrite and pruning.
