---
name: xic-productization-pulse
description: Use when the user asks for an XIC productization pulse, weekly status, launch/readiness check, lane snapshot, blocker summary, or a plain-language report of what changed and what still needs evidence.
---

# XIC Productization Pulse

Produce a one-page, time-windowed readout of productization health from local
repo evidence. It is a read-side report: it does not promote tiers, mutate
matrix outputs, run RAW, or replace the control plane.

## Inputs

Accept an optional window such as `24h`, `7d`, `30d`, or a lane name. If absent,
default to `7d` for broad status and `24h` for launch-day or same-day checks.

## Read Order

1. `docs/superpowers/plans/2026-06-15-productization-control-plane.md`
2. `docs/superpowers/handoffs/current/cc-framework-improvements-productization.md`
3. `git status --short --branch`
4. `git log --since="<window>" --oneline --decorate`
5. Relevant specs, notes, and artifact summaries named by the control plane.
6. `tools/diagnostics/INDEX.md` only for lanes whose diagnostic contract is in
   question.

Avoid broad `output/` scans. Read named artifact summaries first; inspect large
TSV files only when a count or schema claim depends on them.

## Report Shape

Save to:

```text
docs/superpowers/pulse-reports/YYYY-MM-DD-HHMM-productization-pulse.md
```

Use these sections, capped to one readable page:

```markdown
# XIC Productization Pulse - YYYY-MM-DD HH:mm

## Verdict
Plain-language current state in 3-5 bullets.

## Lane Snapshot
| Lane | Tier | Evidence Added | Blocker / Next Evidence |

## What Changed
Only changes backed by commits, docs, tests, or artifacts.

## Evidence Freshness
Commands/artifacts actually inspected, with dates when available.

## Risks Of Overclaim
Claims that must not be inferred from the current evidence.

## Next Best Actions
1-3 actions that would most reduce product uncertainty.
```

## Rules

- Do not claim tests, RAW validation, or expected-diff passed unless the current
  pulse actually inspected that output or cites a committed record.
- Do not turn `diagnostic_only` or sidecar visibility into product behavior.
- Do not rerun 85RAW. A pulse may recommend a run, but only if it would change a
  named decision.
- Prefer concrete blocker language: "needs oracle", "needs expected-diff",
  "GUI disconnected", "schema contract unclear", "human product decision".
- Keep the first paragraph understandable to the user without requiring TSV or
  code knowledge.

## Closeout

End with the saved report path and one short "read this first next time" line.

## References

- Trigger and near-neighbor cases:
  `evals/trigger-cases.md`
- Portable skill interface metadata:
  `agents/interface.yaml`
