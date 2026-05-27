---
name: xic-critical-artifact-review
description: XIC Extractor overlay for the global critical-artifact-review skill. Use for non-trivial XIC specs, plans, goal prompts, phase designs, workflow rules, public contracts, validation gates, RAW-cost decisions, PR/handoff docs, or handoff productization review. First use global `critical-artifact-review`; then apply XIC reviewer routing, readiness labels, RAW validation risks, and downstream artifact rules. Do not use for typo-only docs edits, simple status answers, or ordinary implementation review unless a durable XIC decision is being changed.
---

# XIC Critical Artifact Review

This is a repo-specific overlay. The reusable workflow lives in the global
`critical-artifact-review` skill. Do not duplicate the global workflow here.

If the global skill is unavailable, report `global skill unavailable` and use
`AGENTS.md` plus `docs/agent-subagent-routing.md` as the fallback review
contract.

Use the global skill first for trigger threshold, ownership/placement review,
review angles, prompt shape, and synthesis. Then apply XIC routing and domain
rules below.

## XIC Routing Source

Read `docs/agent-subagent-routing.md`, especially `Critical Artifact Review`.
That document remains the canonical XIC review matrix. Do not copy a competing
routing table into this skill.

If the runtime exposes only a generic `reviewer`, paste the intended repo-local
role brief into the reviewer prompt and name the intended role in synthesis.

## XIC Review Risks

Ask reviewers to challenge these when relevant:

- whether the artifact advances the handoff spine or only polishes legacy DTOs;
- whether an `audit_only`, `shadow_only`, or `diagnostic_only` path has an exit
  rule;
- whether a gate can actually change the next action;
- whether validation cost is justified by independent evidence value;
- whether downstream surfaces such as `alignment_matrix.tsv` or
  `peak_candidates.tsv` are described correctly;
- whether RAW runner, output-level, heartbeat, and artifact retention rules are
  clear.

## XIC Synthesis

After review, report:

- review angles and intended repo-local roles used;
- blockers fixed;
- non-blocking findings deferred;
- docs/code smoke checks run;
- whether ownership/placement was challenged;
- whether the artifact is `diagnostic_only`, `shadow_ready`,
  `production_candidate`, `production_ready`, or `inconclusive`.
