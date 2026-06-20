---
name: xic-pr-closeout
description: XIC Extractor overlay for the global pr-closeout skill. Use when preparing, opening, updating, or closing out an XIC PR or branch where phase/spec work, validation artifacts, RAW-backed evidence, workflow rules, public contracts, multiple commits, or downstream handoff need durable review context. Do not use for simple status checks, tiny commits with no PR, or pure GitHub mechanics already covered by create-pr/commit.
---

# XIC PR Closeout

Repo-specific overlay for global `pr-closeout`. Load the global skill first for
PR/branch narrative, verification, residual risk, and follow-up structure; then
apply XIC readiness labels, artifact rules, CI-equivalent gates, and
merge/history expectations.

If the global skill is unavailable, report `global skill unavailable` and use
`AGENTS.md`, `docs/agent-subagent-routing.md`, and the XIC references below as
fallback closeout guidance.

## XIC Additions

Include when relevant:

- readiness label: `diagnostic_only`, `shadow_ready`, `production_candidate`,
  `production_ready`, or `inconclusive`;
- validation tier: synthetic, focused tests, 8RAW, 85RAW, targeted benchmark,
  manual EIC/MS2 review, or CI shard;
- downstream handoff impact, especially whether `alignment_matrix.tsv` is
  preserved or changed;
- whether `peak_candidates.tsv` is debug/audit projection or production
  contract;
- important artifacts or output indexes under `output/` or `docs/superpowers/`;
- skipped RAW validation and what future evidence would close the risk;
- merge mode and whether branch history, worktree contents, or local `output/`
  artifacts must be preserved.

## Overclaim Guard

Do not claim production behavior from wrappers, reports, sidecars, or TSV
diagnostics alone. State what was observed and what remains unproven.

Do not imply handoff productization progress unless the PR actually advances
`TraceGroup`, `PeakHypothesis`, `EvidenceVector`, `IntegrationResult`,
`AuditTrail`, or downstream matrix handoff.

## References

- XIC CI-equivalent gate and closeout fields:
  `references/xic-closeout-gates.md`
- Trigger and near-neighbor cases:
  `evals/trigger-cases.md`
- Portable skill interface metadata:
  `agents/interface.yaml`
