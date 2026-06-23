# Planning And Workflows

This file owns planning discipline, reusable workflow routing, and owner
migration policy. Stable runners and validation command shapes remain in
`docs/agent-parameter-settings.md`.

## Planning And Review

- Before phase plans or expensive validation, name the decision the run can
  close, strongest existing oracle, missing independent evidence, expected
  runtime/artifacts, and fail-fast or inconclusive path.
- Use tools proactively. Pick the available search, CodeGraph, subagent,
  plugin, external-docs, or real-data validation path that best closes the
  decision; do not choose a weaker path only to save tokens or cost.
- For long tool chains, write the decision map first: question, evidence source,
  action if pass, action if fail. This prevents blind loops without discouraging
  tool use.
- Any `audit_only`, `shadow_only`, or `diagnostic_only` path needs an exit rule:
  promote, kill, externalize, or name the single missing evidence.
- Do not expand a specific validation run when its result cannot change the next
  action; use a different tool or stop with the blocker instead.
- Use a goal-shaped contract for long-running, multi-step, cross-turn, or
  repeatedly drifting work. Goal contracts must point to canonical local
  surfaces, active specs/plans, and existing diagnostics or validation outputs.
- Non-trivial specs, plans, docs, workflow rules, and implementations need a
  critical-thinking review angle: strongest assumption, stale-artifact risk,
  cheaper existing oracle, or condition that would invalidate the path.

## Goal Contract Shape

Use goals for phase-sized, cross-turn, RAW/data-backed, PR-ready, CI/release-like,
or repeatedly drifting work. Do not use a runtime goal for tiny bug fixes, simple
status checks, or one-command validations with an obvious done state.

A useful goal is one measurable objective plus enough context to prevent drift.
It should include:

```markdown
Objective:
Context:
Constraints:
In scope:
Out of scope:
Current surfaces/artifacts:
Plan:
Verification:
Boundaries:
Iteration policy:
Done when:
Pause if:
Stop rules:
Handoff:
```

Keep `Objective` singular. If two outcomes need different verification gates,
split them into separate goals or state which one is primary. `Done when` must
be auditable from files, commands, PR state, or validation artifacts. `Stop
rules` must name conditions that require user decision instead of continued
blind continuation.

When drafting a goal for a vague request, give the best executable version
first rather than a blank form. Choose conservative defaults for low-risk
unknowns and ask only when the answer changes cost, risk, ownership, public
contracts, or product direction. If the domain is unfamiliar, make discovery of
repo docs, existing scripts, sample data, or official references part of the
goal before implementation.

Keep `Done when` for completion evidence and `Pause if` for human/external
blockers such as credentials, production data, destructive operations,
permissions, budget, unclear ownership, or product-direction decisions.
Iteration should be bounded: after the same failure shape repeats twice, require
a new source of evidence instead of another blind retry.

## Skills And Subagents

- When the user asks for subagent review, follow
  `docs/agent-subagent-routing.md`. Do not replace a requested multi-angle
  review with one generic reviewer unless a runtime limit blocks it and the
  bypass is reported.
- Repo-local execution subagents are opt-in. The main agent owns synthesis,
  edits, final judgment, and verification.
- Reusable workflows belong in global skills first. Repo-local `.codex/skills/`
  entries should exist only for XIC-specific checklists that cannot live cleanly
  in routing docs.
- Use `xic-architecture-preflight` before implementing or planning non-trivial
  diagnostics, RAW-backed evidence, preset-performance changes,
  matrix/activation/value-delta paths, model-selection work, HCD-PI, Delta Mass,
  CID-NL expansion, or other evidence-provider additions.
- Use `xic-large-pr-review` for large diagnostics, architecture, preset
  performance, parity, 8RAW/85RAW, activation/value-delta, matrix identity, or
  RAW-locality PR reviews.

## Legacy Owner Transformation Policy

- The project direction is explicit transformation: successor modules absorb the
  useful capability and product invariants of legacy owners, fix the legacy pain
  points, then retire or reduce the legacy owner to a thin compatibility adapter.
- When the user explicitly asks to absorb a legacy owner into an existing
  successor model, do not stop at another shadow/report/spec layer if a bounded
  ownership-transfer slice can be named.
- A valid ownership-transfer slice names: current owner, successor owner,
  public surface, preserved invariant, expected product diff or parity oracle,
  and the focused tests that prove it.
- After those are named, prefer implementing one narrow transfer over creating a
  new broad plan. Review gates should close the decision and then unblock
  execution; they should not become an indefinite replacement for migration.
- Tests protect product invariants, not old module shapes. When a successor owns
  an invariant, migrate the test to the successor surface or delete the
  legacy-specific test. Keep legacy tests only for public compatibility,
  explicit rejection/migration behavior, or parity during an active transition.
- Do not preserve a legacy owner merely because tests exist. First classify what
  the tests protect: product invariant, compatibility contract, diagnostic
  evidence, or obsolete implementation detail.
- Keep public safety rules: if selected peak, selected area, confidence, reason,
  matrix identity, workbook schema, TSV schema, or config behavior would change,
  require an expected-diff contract and focused output tests before promotion.
- `audit_only`, `shadow_only`, and `diagnostic_only` artifacts must still name an
  exit rule, but for owner-migration work the exit rule should include the
  smallest next production or adapter transfer, not only the missing evidence.
