---
name: xic-pr-stack-repair
description: Use before repairing, splitting, retargeting, rebuilding, or merging stacked XIC PRs, especially when CI failures involve stale PR bases, repeated global ledger edits, externalized output/local_validation_artifacts, clean-checkout artifact gaps, or superseded branches. This is a stack-boundary and artifact-ownership workflow, not a normal PR description, read-only review, or one-PR CI bugfix.
---

# XIC PR Stack Repair

Use this before code fixes when a PR series, split branch, or superseded branch
has red CI or confusing diffs. First decide whether the failure is a
stack-boundary problem, not an ordinary code failure.

## Flow

Read `references/repair-checklist.md`, then produce a stack map covering:

- base/head branch, stale base, and superseded branch status;
- repeated files across PRs, especially global ledgers, active handoffs,
  artifact inventories, retained fixture manifests, and CI checkers;
- which PR owns product behavior, artifact hygiene, fixture retention, and final
  rollup docs;
- whether default CI needs ignored `output/`, `.worktrees/`, or
  `local_validation_artifacts/` bytes.

## Repair Rules

- If an earlier PR needs a later cleanup PR to pass CI, stop and rebuild the
  boundary. The cleanup either belongs in the earlier PR or in an already-merged
  prerequisite.
- If a branch contains stale stack commits, rebuild from the intended base and
  cherry-pick only in-scope commits.
- Keep default CI clean-checkout safe; ignored local artifact bytes require an
  explicit opt-in flag.
- Keep global ledgers and active handoffs out of intermediate PRs unless that
  PR truly owns the ledger update.
- Preserve machine-required handoff/control-plane anchors when pruning docs.
- Collapse local repair noise into logical commits before publishing.
- If GitHub Actions checks do not appear after a ref change, diagnose token,
  event, filter, branch-protection, and approval causes before rewriting or
  pushing again. Use `workflow_dispatch`, rerun, normal push, or authorized
  `git push --force-with-lease` only when that matches the branch state.

## Verification

For artifact-boundary or productization-adjacent stack repairs, run the focused
checks in `references/repair-checklist.md` before the full PR gate.

Then use `xic-pr-closeout` for PR description, readiness labels, CI-equivalent
gate, residual risk, and merge narrative.

Trigger coverage lives in `evals/trigger-cases.json` with
`evals/semantic_config.json`. Update those cases before broadening the trigger
description.

## Stop Rules

Stop patching and report the stack problem when:

- a PR has a stale base or superseded head but CI is being fixed on top of it;
- two PRs mutate the same global ledger or handoff with different snapshots;
- CI failure depends on ignored local artifacts missing from clean checkout;
- GitHub shows no Actions checks and the token/event/filter/approval cause has
  not been identified.
