---
name: xic-goal-execution
description: XIC Extractor overlay for the global goal-execution skill. Use when the user asks to create, tighten, review, audit, execute, or close a goal for XIC work, or when an XIC task is phase-sized, RAW/data-backed, PR-ready, CI/release-like, cross-turn, or repeatedly drifting. Do not use for tiny bug fixes, simple commits, one-command status checks, or focused RAW validation with an obvious done state.
---

# XIC Goal Execution

Repo-specific overlay for global `goal-execution`. Load the global skill first;
this overlay adds XIC product, RAW, validation, handoff, and control-plane
constraints.

If the global skill is unavailable, report `global skill unavailable` and use
the compact fallback shape in `references/xic-goal-gates.md`.

## Use Pattern

1. Pick the smallest global mode: `create`, `tighten`, `review`, `execute`,
   `audit`, or `close`.
2. Apply XIC goal gates before execution: objective, phase, decision closure,
   verification tier, public-contract risk, architecture risk, and handoff.
3. Read required XIC context before rerunning expensive validation.
4. Keep execution inside the accepted goal; record adjacent backlog as follow-up.
5. At closeout, name the strongest verification tier actually used and residual
   product risk.

## XIC Defaults

- Non-trivial XIC goals read `AGENTS.md`, `docs/agent-subagent-routing.md`, the
  named spec/plan/artifact, and `docs/agent-parameter-settings.md` when Python,
  RAW, DLL, timing, output level, or long-running validation is involved.
- Distinguish `diagnostic_only`, `shadow_ready`, `production_candidate`,
  `production_ready`, and `inconclusive`.
- Wrapper/report/sidecar existence is not product behavior.
- Public-surface risk needs expected-diff or focused output tests.
- RAW-backed architecture or evidence-provider work uses
  `xic-architecture-preflight` first.

## Stop Rules

Stop instead of guessing when public schemas, workbook sheets, CLI/config keys,
`alignment_matrix.tsv`, RAW runner paths, Thermo DLLs, heartbeat/timing sidecars,
or product direction are unclear.

## References

- XIC goal gates, fallback shape, and governor behavior:
  `references/xic-goal-gates.md`
- Required context, constraints, verification tiers, and RAW stop rules:
  `references/xic-context-validation.md`
- Handoff snapshot and productization control-plane boundary:
  `references/xic-handoff-boundary.md`
- Trigger and near-neighbor cases:
  `evals/trigger-cases.md`
- Portable skill interface metadata:
  `agents/interface.yaml`
