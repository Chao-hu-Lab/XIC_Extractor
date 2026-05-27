---
name: xic-goal-execution
description: XIC Extractor overlay for the global goal-execution skill. Use when the user asks to create or execute a goal for XIC work, or when an XIC task is phase-sized, RAW/data-backed, PR-ready, CI/release-like, cross-turn, or repeatedly drifting. First use the global `goal-execution` contract shape, then apply XIC-specific context, validation tiers, RAW stop rules, and handoff/productization constraints. Do not use for tiny bug fixes, simple commits, one-command status checks, or focused RAW validation with an obvious done state.
---

# XIC Goal Execution

This is a repo-specific overlay. The reusable workflow lives in the global
`goal-execution` skill. Do not duplicate the global workflow here.

If the global skill is unavailable, report `global skill unavailable` and use
`AGENTS.md`, `docs/agent-subagent-routing.md`, and the XIC additions below as
the fallback goal contract.

Use the global skill first for:

- source-backed goal shape;
- `create`, `tighten`, `review`, and `execute` modes;
- runtime goal creation rules;
- full and compact templates;
- completion audit and stop rules.

Then apply the XIC-specific additions below.

## Required XIC Context

Every non-trivial XIC goal should read:

- `AGENTS.md`;
- `docs/agent-subagent-routing.md`;
- `docs/agent-parameter-settings.md` if Python, RAW, validation, DLLs, timing,
  output levels, or long-running commands are involved;
- the active spec, plan, note, PR, diagnostic index, or validation output named
  by the user;
- existing artifacts under `output/` or `docs/superpowers/` before rerunning
  expensive validation.

## XIC Constraints To Consider

Add these when relevant:

- preserve public contracts: CLI flags, config keys, TSV/workbook schemas,
  `alignment_matrix.tsv`, downstream handoff fields, and diagnostic marker maps;
- distinguish `diagnostic_only`, `shadow_ready`, `production_candidate`,
  `production_ready`, and `inconclusive`;
- do not treat wrapper/report/sidecar existence as product behavior;
- do not run 85RAW through background `Start-Process` from the Codex shell;
- do not generate large `.xlsx`, HTML, owner-edge, status-matrix, event-owner,
  or ambiguous-owner artifacts for validation unless the task explicitly needs
  them;
- do not let cleanup phases change production behavior unless the goal says so;
- do not polish legacy DTOs when the goal is handoff productization unless that
  directly advances the spine contract.

## XIC Verification Tiers

Name the tier in `VERIFY` and final output:

- synthetic no-RAW tests;
- focused unit/contract tests;
- 8RAW validation;
- 85RAW validation;
- targeted benchmark;
- manual EIC/MS2 review;
- CI shard / GitHub checks.

If real-data validation is skipped, say why and what future evidence would close
the risk.

## XIC Stop Rules

Stop instead of guessing when:

- a planned change touches public schemas, workbook sheets, CLI/config keys, or
  `alignment_matrix.tsv` without a contract update;
- RAW runner paths, Thermo DLLs, or output levels are unclear;
- a long RAW run lacks heartbeat/timing sidecars or starts repeating a known
  failed launch pattern;
- the goal's gate cannot change the next action;
- a reviewer finding contradicts the user's product direction and needs a
  decision.
