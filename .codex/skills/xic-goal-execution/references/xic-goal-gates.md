# XIC Goal Gates

Use this after loading global `goal-execution`.

## Fallback Goal Shape

If the global skill is unavailable, use:

```markdown
Objective:
Context:
Constraints:
In scope:
Out of scope:
Current surfaces/artifacts:
Plan:
Verification:
Done when:
Stop rules:
Handoff:
```

Keep `Objective` singular. `Done when` must be auditable from files, commands,
PR state, or validation artifacts.

## Quality Gate

Before creating or executing an XIC goal, tighten or stop when any answer is
weak:

- Single objective: one primary outcome, with non-goals named.
- Phase type: docs, cleanup, diagnostic, engineering, science, behavior change,
  PR/CI, or release; mixed phases need ordering.
- Decision closure: the goal must close a decision that can change next action.
- Tool leverage: use diagnostics, artifacts, tools, reviewers, or RAW runs that
  produce the strongest useful evidence.
- Verification fit: synthetic, focused tests, artifact parity, 8RAW, 85RAW,
  targeted benchmark, manual EIC/MS2 review, or CI.
- Public contract risk: CLI/config, TSV/CSV/workbook schema, matrix identity,
  activation, selected peak/area, or downstream handoff.
- Architecture risk: diagnostics, RAW-backed evidence, preset performance,
  matrix activation, HCD-PI, Delta Mass, CID-NL expansion, or evidence provider.
- Stop rules and handoff: future agents must know what changed, what remains
  risky, and where artifacts live.

Do not continue a runtime goal whose objective is only "improve everything",
"clean up the repo", or "finish all architecture debt".

## Governor Behavior

- Keep the active goal visible in decisions.
- Prefer existing diagnostics, specs, and validation outputs before rerunning
  expensive RAW jobs when they answer the same decision.
- If reviewer findings, CI failures, or new data invalidate the contract, switch
  to `audit` and report the mismatch before continuing.
- Near closeout, compare actual diff and verification against `Done when`.
