# Shared Peak Identity Evidence Context7 Task 0 Placement Note

**Date:** 2026-05-29
**Status:** planning placement note
**Branch:** `codex/shared-peak-identity-evidence`
**Related issue:** GitHub issue #74,
`Task 0: Context7 official-docs check for shared peak identity evidence`
**Task 0 audit:** `2026-05-29-shared-peak-identity-context7-package-audit.md`

## Verdict

The Context7 / official-docs package-semantics check is now Task 0 for the
shared peak identity evidence chain work. It should run before the next
spec-to-goal-to-plan execution for this branch.

This task is no longer primarily queued behind the AsLS / baseline cleanup
track. Future AsLS / baseline work should still apply the rule when it touches
evidence-affecting package behavior, but the immediate owner is the current
qualitative evidence-chain phase.

## Why Move It Here

The next qualitative evidence-chain PR is likely to touch or interpret package
behavior in peak shape, boundary, similarity, calibration, and tabular evidence
assembly. A stale or shallow assumption about those package defaults can change
the diagnostic conclusion before any production behavior changes.

Likely package-sensitive surfaces include:

- `scipy.signal` peak shape, CWT, smoothing, prominence, width, and local
  signal behavior;
- `numpy` / `pandas` interpolation, grouping, missing-value handling, joins,
  ranking, and serialization that affect machine-readable evidence;
- `sklearn` metrics, calibration, clustering, or model-selection helpers if
  used for evidence scoring or comparison;
- RAW / mzML / vendor-adapter packages if the phase reads traces through a new
  or altered adapter path.

## Task 0 Contract

Before finalizing the current branch's spec, goal, plan, or implementation,
inspect non-trivial third-party package usage through Context7 or equivalent
official documentation.

For each package behavior that can materially affect a scientific or product
decision, record:

- package / module / symbol;
- relevant parameters or defaults;
- official-doc finding;
- decision impact for this branch;
- whether the finding changes the plan, only informs tests, or is not relevant.

Do not trigger this gate for trivial stable calls with explicit parameters, such
as ordinary TSV writing. Do not treat third-party documentation as product
authority; it only calibrates the semantics of tools used by the product. Real
data, manual EIC/MS2 review, and repo-specific contracts remain the deciding
evidence.

## Done When

- The current branch has a short Task 0 audit note or plan section listing the
  package-sensitive surfaces considered.
- Any package semantics that affect peak identity evidence, shape, boundary,
  MS2 pattern comparison, or calibration are backed by Context7 or official
  docs.
- The follow-up spec / goal / plan states whether package-semantics findings
  changed implementation scope, tests, or stop rules.
- If no package behavior is material for the selected implementation slice, the
  note says so explicitly and names the surfaces reviewed.

## Stop Rule

If Context7 / official docs contradict current assumptions in a way that could
change peak identity evidence or promotion criteria, stop before implementation
and revise the spec or plan. If the contradiction is only about a diagnostic
helper with no decision impact, record it as a test or wording update instead
of expanding scope.
