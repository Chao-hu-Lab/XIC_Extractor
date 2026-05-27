# Agent Workflow Routing

This document defines when to use repo-local Codex subagents, active goals, and
runtime guardrails for XIC Extractor. It is an operating guide, not a second
source of truth for project parameters. Stable runners, RAW paths, validation
tiers, and command shapes still live in `docs/agent-parameter-settings.md`.

The role set was informed by public Codex subagent catalogs, including
`https://github.com/VoltAgent/awesome-codex-subagents`, but collapsed for this
repo. The goal is not to preserve every concern as a separate identity. The
goal is to keep a small set of reviewer families with explicit triggers.

The routing also absorbs the parts of Google's engineering practices that fit
this repo: favor changes that improve code health without chasing perfection,
review high-level design before details, keep changes small and self-contained,
make tests useful rather than decorative, and keep the change description clear
about what changed and why.

Goal usage follows the contract shape from `majiayu000/awesome-goal-prompts`:
one measurable objective, real context, hard constraints, auditable completion,
fresh verification, output expectations, and stop rules. The repo adopts the
shape, not the full external catalog. A goal-shaped contract is not the same as
registering an active runtime goal; active goals require explicit user request
or runtime permission.

## Dispatch Rules

- Default is main agent only.
- Normal maximum dispatch is two reviewers.
- Use three reviewers only when surfaces are genuinely independent and the
  findings can change the next action.
- Reviewer dispatch is an auditable checklist item, not a tool-enforced gate.
  When a hard trigger below applies, the plan/final summary must state which
  reviewer was used or why it was intentionally bypassed.
- Subagents do not auto-spawn. Delegate explicitly and give each reviewer a
  bounded read-only task.
- The main agent owns synthesis, file edits, final judgment, and verification.
- Reviewer subagents are read-only. `implementation-worker` is the only
  repo-local role allowed to edit assigned files. `tester` is workspace-write
  only for command side effects such as caches, logs, and named output
  artifacts. Do not give two agents the same write scope.
- If thread limits block full review, dispatch in this order: mandatory blocker
  reviewer, original blocker re-check, then optional specialist.

## Reviewer Output Contract

Every reviewer should return the same compact shape:

```text
Verdict:
Blocking findings:
Evidence:
Would this change next action?:
Smallest fix:
Residual risk:
```

Findings that cannot change the next action should be labeled minor or deferred.

Family-specific required fields:

- `strategy-challenger`: `Decision closed?`, `Exit rule`
- `implementation-contract-reviewer`: `Public contract touched`,
  `Tests/coverage checked`
- `validation-evidence-reviewer`: `Mode`, `run_ok`, `gate_ok`,
  `production_ready`, `inconclusive`
- `docs-handoff-reviewer`: `Canonical source checked`,
  `Human/machine surface impact`
- `ops-triager`: `Existing skill used or bypass reason`,
  `Reproduction command`
- `outside-frame-researcher`: `Trigger met`, `Sources`

## Active Role Families

Reviewer families:

| Role | Use when | Includes |
| --- | --- | --- |
| `strategy-challenger` | High-risk plan/spec, phase design, handoff productization, legacy-path concern | Assumption mapping, product direction, decision ownership, critical challenge |
| `implementation-contract-reviewer` | Code/public contract change, CLI/config/schema/parser/test behavior, diagnostic entrypoint changes | Code path mapping, contract review, test strategy, diagnostics reuse |
| `validation-evidence-reviewer` | RAW/science/benchmark decision, 8RAW/85RAW preflight or acceptance, timing/performance evidence | Validation ops, gate acceptance, LC-MS/MS evidence, performance profiling |
| `docs-handoff-reviewer` | Docs/source-of-truth change, output handoff, report/review surface, agent routing/TOML changes | Docs drift, output contract, human review UX, agent workflow regression |
| `ops-triager` | CI red, Windows/PowerShell/runbook failure, local runner or path problem | CI triage, Windows ops, command reproduction |
| `outside-frame-researcher` | Manual trigger only: local evidence cannot discriminate design options, or two local iterations failed | Bounded external docs/literature/open-source scan |

Execution roles:

| Role | Use when | Guardrail |
| --- | --- | --- |
| `implementation-worker` | A small, self-contained implementation slice can be assigned with an explicit non-overlapping write scope | Workspace-write; must stop if the scope needs unassigned files |
| `tester` | Clean-context verification, failure reproduction, or test-validity review is useful | Workspace-write for command side effects only; no source/docs/config/test edits, staging, commits, or reverts |

## Hard Triggers

- Any 85RAW run, likely >30 minute RAW run, or production-equivalent validation
  must document `validation-evidence-reviewer` preflight before launch and
  acceptance review after completion, or state the bypass reason.
- Any CI red or required-check uncertainty starts with the existing CI skill
  workflow, such as `$gh-fix-ci`, when available. Use `ops-triager` only when
  check metadata, branch protection, Windows runner behavior, or local
  reproduction remains unclear after the skill path.
- Any `.codex/agents/*.toml`, `docs/agent-subagent-routing.md`, or AGENTS
  workflow-rule change gets `docs-handoff-reviewer` to check role overlap,
  trigger drift, and output-contract regression.
- Any phase plan that could preserve a bad legacy path, overclaim evidence, or
  add an expensive gate gets `strategy-challenger`.
- Any public CLI/config/schema/workbook/TSV/downstream handoff change gets
  `implementation-contract-reviewer`.
- Use `implementation-worker` only when the task can be split like a small
  self-contained CL: one reason to change, explicit write scope, related tests,
  and no shared write surface with the main agent or another worker.
- Use `tester` when verification should be independent from the implementer, a
  regression must be reproduced, or test validity is the risk.
- Use a goal-shaped contract when the task is long-running, multi-step, crosses
  multiple turns, or has repeatedly drifted in past work. Register an active goal
  only when the user explicitly asks for one or the runtime explicitly permits
  it. Do not use a goal for tiny bug fixes, simple commits, or one-command
  status checks.

## Phase Routing

| Situation | Default | Add only if trigger fires |
| --- | --- | --- |
| New phase plan / spec | `strategy-challenger` | `outside-frame-researcher` only when local evidence cannot discriminate options |
| Handoff productization planning | `strategy-challenger` | `implementation-contract-reviewer` if consumer migration touches code/public contract |
| Code implementation review | `implementation-contract-reviewer` | `docs-handoff-reviewer` for public docs/output, `validation-evidence-reviewer` for RAW/science behavior |
| Parallel implementation slice | `implementation-worker` | `tester` after the worker returns when behavior or tests changed |
| Diagnostics / tool changes | `implementation-contract-reviewer` | `docs-handoff-reviewer` if `tools/diagnostics/INDEX.md` or lifecycle docs change |
| Expensive RAW run preflight | `validation-evidence-reviewer` with `mode=preflight` | `ops-triager` if runner/path/PowerShell failure is suspected |
| Validation result acceptance | `validation-evidence-reviewer` with `mode=acceptance`; add `mode=science` or `mode=performance` only when needed | `docs-handoff-reviewer` if the result changes downstream or human review surfaces |
| CI red / PR check failure | Existing CI skill first; `ops-triager` only for unclear check metadata, branch protection, Windows runner, or reproduction | `implementation-contract-reviewer` or `validation-evidence-reviewer` after failure class is known |
| Documentation / workflow rules | `docs-handoff-reviewer` | `strategy-challenger` if the rule changes phase planning or gate behavior |
| Performance optimization | `validation-evidence-reviewer` | `implementation-contract-reviewer` if code changes public behavior |
| Long-running goal execution | Main agent uses a goal-shaped contract and owns completion; register an active goal only with explicit user request or runtime permission | `strategy-challenger` before launch when goal scope could become a backlog; `tester` at the end when verification integrity matters |

`validation-evidence-reviewer` prompts must name a mode. Allowed modes are
`preflight`, `acceptance`, `science`, and `performance`; use at most two modes in
one review.

## Goal Contracts

Use the full goal shape for high-risk, long-running, cross-module, RAW/data,
CI, migration, release, or productization work. Use compact goal shape only
when the context is obvious and verification is one or two commands.

Default to writing or following the contract. Do not call the runtime's active
goal creation tool unless the user explicitly asked for a goal run, or a
system/developer/runtime instruction explicitly says to create one.

Every repo goal should include:

- `GOAL`: one measurable finish line, not a backlog.
- `CONTEXT`: exact files, docs, artifacts, commands, failures, screenshots, or
  plans to read first.
- `CONSTRAINTS`: what must not change, public contracts to preserve, and
  verification integrity.
- `DONE WHEN`: mechanically checkable end state.
- `VERIFY`: fresh commands, reports, screenshots, artifacts, or exact blockers.
- `OUTPUT`: changed files, key decisions, verification, residual risk, and next
  action.
- `STOP RULES`: secrets, production access, destructive data operations, unclear
  product decisions, or three failed attempts on the same symptom.

For XIC Extractor, goals should normally reference `AGENTS.md`,
`docs/agent-parameter-settings.md`, this routing doc, the active spec/plan, and
existing diagnostics or validation artifacts. Avoid broad goals such as
"improve the pipeline" unless the goal first asks for a bounded plan.

## 補強 Loop

Post-review補強 should not spawn a new panel.

1. Main agent fixes the blocker directly.
2. Ask the original blocker reviewer to re-check, when available.
3. Add one more reviewer only if the fix moved into a new domain or changed
   scope, contract, or gate behavior.
4. Done means the blocker is closed and the relevant test, docs smoke, TOML
   parse, or validation artifact is cited.

## Worker / Tester Rules

- Worker roles are for execution, not design authority. The main agent must give
  the worker a file/module write scope and acceptance criteria.
- Do not use a worker to explore an unclear architecture. Use
  `strategy-challenger` or `implementation-contract-reviewer` first.
- Do not run multiple workers on overlapping files or schemas.
- Tester roles are verification-only. They may run commands that create normal
  test caches, logs, and named output artifacts, but they should not edit source
  files or silently fix failures. Tester reports must include whether `git
  status --short` contains only expected verification side effects.
- If a tester finds a failure, the main agent decides whether to fix directly,
  assign an implementation worker with a new write scope, or revise the plan.

## Sandbox And Approval Posture

Current recommended posture for this repo:

- Main implementation sessions: `sandbox_mode = "workspace-write"` with
  `approval_policy = "on-request"`.
- Reviewer, ops-triage, and outside-frame research roles:
  `sandbox_mode = "read-only"`.
- Tester role: `sandbox_mode = "workspace-write"` only because pytest,
  validation commands, and local runners often write caches, logs, and output
  sidecars. Tester prompts must forbid source/docs/config/test edits, staging,
  commits, reverts, renames, and deletes, and must report the final dirty scope.
- `danger-full-access`, `approval_policy = "never"`, broad writable roots, and
  persistent execpolicy rules are not default development settings. Use them
  only for a reviewed, bounded operation with a named rollback or recovery path.
- Project-local `.codex/config.toml` is intentionally not added in this branch.
  The global config already sets the normal model, sandbox, approvals, MCP, and
  plugin posture. Duplicating that in-repo would create another drift surface.
- If a future PR adds `.codex/config.toml` or `.codex/execpolicy/`, it must state
  why `AGENTS.md`, parameter settings, and normal approval prompts are
  insufficient, then run a config/TOML smoke check.
- Before changing sandbox posture for a command, prefer
  `python -m scripts.agent_sandbox_doctor --command "<command>"`. The doctor is
  diagnostic only; it does not execute the command or replace human approval.

## Hooks Adoption

Hooks can help only when they prevent a repeated failure mode without hiding
important decisions. Do not install repo-local active hooks just because hooks
exist.

Candidate hooks, in order:

1. Passive `Stop` or `SessionEnd` summary: record branch, dirty diff summary,
   active goal status, commands/tests run, and whether verification was skipped.
2. Passive `UserPromptSubmit` warning: flag risky phrases such as 85RAW,
   `Start-Process`, `danger-full-access`, broad cleanup, or merge/push without
   forcing a block.
3. Blocking hook only after a passive hook proves value: block repeated known
   anti-patterns such as launching 85RAW in background from the Codex shell.

Hook output must be short and auditable. It should point to the existing
canonical document or runner; it must not embed another copy of the rules.
Changes to hooks require `docs-handoff-reviewer`, because hook config affects
future agent execution before the agent can reason about the repo.

## Change Size And Reviewability

- Prefer small, self-contained changes. If a change mixes behavior, refactor,
  docs, generated artifacts, and validation, split it unless the coupling is
  necessary to preserve the contract.
- For large or stacked work, tell reviewers what the main part of the change is
  and which files are intentionally out of scope.
- Reviewer comments should distinguish blockers from optional improvements.
  Nits must not block progress when the change improves code health.
- PR or closeout descriptions should state what changed, why it changed, tests
  run, known shortcomings, and follow-up direction.

## Acceptance Labels

Validation summaries must keep these separate:

- `run_ok`: the command completed and emitted expected artifacts.
- `gate_ok`: the artifacts satisfy the stated gate.
- `production_ready`: the evidence is strong enough for production behavior.
- `inconclusive`: the run cannot close the decision; name the missing evidence
  or exit rule.

## Outside-Frame Trigger

Use `outside-frame-researcher` only when one of these is true:

- Existing local oracles cannot discriminate between credible design options.
- Two local low-cost iterations failed to change the decision.
- The method family itself is uncertain and an external guideline, paper, or
  mature implementation could change the gate design.

Output must be bounded: 2-4 sources or examples, the design idea each source
supports, and the minimum local experiment that would make it worth
implementing.

## Anti-Patterns

- Do not dispatch all agents just because a task is important.
- Do not use subagents to avoid reading the repo yourself.
- Do not let reviewer findings become new scope without checking whether they
  close the current decision.
- Do not create a new role for a one-off concern. Add a role only after the
  concern recurs and cannot fit an existing family.
- Do not treat orchestration as the product. The purpose of subagents is to
  improve decisions and reduce repeated mistakes, not to add ceremony.
