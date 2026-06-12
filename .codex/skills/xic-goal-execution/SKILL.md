---
name: xic-goal-execution
description: XIC Extractor overlay for the global goal-execution skill. Use when the user asks to create, tighten, review, audit, execute, or close a goal for XIC work, or when an XIC task is phase-sized, RAW/data-backed, PR-ready, CI/release-like, cross-turn, or repeatedly drifting. First use the global `goal-execution` contract shape, then apply XIC-specific goal quality gates, context, validation tiers, RAW stop rules, and handoff/productization constraints. Do not use for tiny bug fixes, simple commits, one-command status checks, or focused RAW validation with an obvious done state.
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

## Execution Modes

Pick the smallest mode that fits the user's request:

- `create`: turn a broad request into one measurable goal contract.
- `tighten`: fix an existing goal that is too broad, unverifiable, or missing
  stop rules.
- `review`: critique a proposed goal before execution; do not edit code.
- `execute`: work against the accepted goal and update progress only when
  evidence changes.
- `audit`: check whether an active goal is still valid after new artifacts,
  reviewer findings, CI results, or user direction.
- `close`: verify completion, name residual risk, leave handoff, and mark the
  runtime goal complete only when the objective is actually achieved.

If the user asks to "set a goal and handle it", start with `tighten` for one
pass, then `execute`. Do not skip the quality gate just because the user is
eager to proceed.

## Default-First Goal Drafting

When creating a goal, output the best copy-ready goal first. Do not lead with a
blank template or a long questionnaire.

- If uncertainty is low-risk, choose conservative defaults and state the
  assumption.
- Ask only when the answer changes cost, risk, ownership, public contracts, or
  product direction.
- If the domain or artifact is unfamiliar, make the goal discovery-first:
  inspect repo docs, existing scripts, sample data, official references, or
  user-provided material before implementation.
- If choices are needed, use short numbered options with a recommended default.
  Avoid open-ended interviews unless a multiple-choice version would hide an
  important decision.
- Keep `/goal` as the executable command prefix. For Chinese users, the goal
  body can be Chinese; do not change the command to `/目標` or `/目标`.

## Minimal Goal Shape

If the global skill cannot be loaded, create or tighten goals with this compact
shape:

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

Keep `Objective` singular. If the work has multiple independent outcomes,
split the goal or name the primary objective and make the rest explicit
non-goals. `Done when` must be auditable from files, commands, PR state, or
validation artifacts.

## Goal Quality Gate

Before creating or executing an XIC goal, inspect the contract. Tighten or stop
when any answer is weak:

- **Single objective**: Is there exactly one primary outcome? If not, split the
  goal or state the non-goals.
- **Phase type**: Is it docs, cleanup, diagnostic, engineering, science,
  behavior change, PR/CI, or release? Mixed phase types need explicit ordering.
- **Decision closure**: What decision can this goal close? If the proposed gate
  cannot change the next action, shrink or remove it.
- **Verification fit**: Does verification match the phase type: focused tests,
  artifact parity, 8RAW, 85RAW, targeted benchmark, manual EIC/MS2 review, or
  CI? Do not overclaim a weaker tier.
- **Boundaries**: Does the goal name allowed write surfaces and forbidden paths
  separately from behavioral constraints?
- **Iteration policy**: Does it require one focused change at a time, rerunning
  relevant checks after meaningful edits, and a new source of evidence after
  repeated failures?
- **Public contract risk**: Does it touch CLI/config, TSV/CSV/workbook schema,
  matrix identity, activation decisions, selected peak/area, or downstream
  handoff fields? If yes, require a contract update and focused output test.
- **Architecture risk**: Does it add diagnostics, RAW-backed evidence, preset
  performance work, matrix activation, HCD-PI, Delta Mass, CID-NL expansion, or
  a new evidence provider? If yes, use `xic-architecture-preflight` first.
- **Stop rules**: Are there concrete conditions that require user decision
  instead of more tool calls?
- **Pause conditions**: Are external permissions, credentials, production data,
  destructive operations, unclear ownership, or product-direction decisions
  separated from normal completion?
- **Handoff**: Will a later agent know what changed, what was verified, what
  remains risky, and where the artifacts are?

Do not create or continue a runtime goal if the objective is only "improve
everything", "clean up the repo", or "finish all architecture debt" without a
bounded surface and verification gate.

## Governor Behavior

While executing:

- Keep the active goal visible in decisions; do not drift into adjacent cleanup.
- Prefer existing diagnostics, specs, and validation outputs before rerunning
  expensive RAW jobs.
- After the same failure shape repeats twice, stop retrying the same approach.
  inspect logs/artifacts, reduce to a smaller repro, consult docs, or report the
  blocker.
- If the work uncovers a larger backlog, record it as follow-up instead of
  silently expanding the goal.
- If a reviewer finding, CI failure, or new data invalidates the goal contract,
  switch to `audit` and report the mismatch before continuing.
- Near closeout, compare the actual diff and verification against `Done when`.
  Do not mark complete because the budget is low or because partial work is
  useful.

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
- the same failure shape repeats twice without new evidence;
- a reviewer finding contradicts the user's product direction and needs a
  decision.
