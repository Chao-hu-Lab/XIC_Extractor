# Agent Workflow Routing

This document defines when to use repo-local Codex subagents, active goals, and
runtime guardrails for XIC Extractor. It is an operating guide, not a second
source of truth for project parameters. Stable runners, RAW paths, validation
tiers, and command shapes still live in `docs/agent/parameter-settings.md`.

The role set was informed by public Codex subagent catalogs, including
`https://github.com/VoltAgent/awesome-codex-subagents`, but collapsed for this
repo. The goal is not to preserve every concern as a separate identity. The
goal is to keep a small set of reviewer families with explicit triggers.
This is not a cost-saving or token-minimizing policy. For this repo, use tools,
plugins, and subagents generously when they make the work less blind, more
parallel, or better evidenced.

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

Reusable workflow skills should live in the global skill roots and may be
mirrored to the Claude Code compatibility root when that runtime needs them.
Repo-local skills under `.codex/skills` should exist only when XIC needs an
execution checklist that cannot live cleanly in this routing doc. Use skills
when their trigger threshold applies before recreating process instructions:

- global `goal-execution` for goal contract creation, review, tightening, and
  execution; `xic-goal-execution` only adds XIC constraints and validation tiers.
- global `critical-artifact-review` for multi-angle review of durable specs,
  plans, goal prompts, workflow rules, handoff docs, and public contracts. It
  must read this routing doc when running in XIC; do not maintain a duplicate
  XIC critical-review skill.
- `xic-large-pr-review` for large XIC PR reviews, especially diagnostics,
  architecture, preset-performance, parity, 8RAW/85RAW, activation/value-delta,
  matrix identity, or RAW-locality changes. It complements the normal
  code-review stance by focusing on high blast-radius contracts and validation
  evidence.
- `xic-architecture-preflight` before implementing or planning non-trivial
  diagnostics, RAW-backed evidence, preset-performance changes,
  matrix/activation/value-delta paths, model-selection work, HCD-PI, Delta Mass,
  CID-NL expansion, or other evidence-provider additions. It forces reuse,
  ownership, call-cost, public-contract, and validation-gate decisions before
  coding.
- global `pr-closeout` for durable PR/branch closeout; `xic-pr-closeout` only
  adds XIC readiness labels and artifact rules.
- `xic-pr-stack-repair` before repairing, retargeting, rebuilding, or merging a
  stacked/superseded PR series when stale bases, repeated ledger edits,
  externalized artifacts, or clean-checkout CI dependencies are plausible.
- `xic-raw-validation` remains repo-local because 8RAW/85RAW, Thermo RAW paths,
  output levels, heartbeat, timing, and benchmark acceptance are XIC-specific.

Every skill, role, plugin, or workflow route needs a visible adoption reason.
This is a decision-map rule, not a scarcity rule. Use available official
capabilities such as Superpowers workflows, multi-agent reviewers, CodeGraph,
GitHub/gh, official docs/search, and focused real-data validation when they can
answer a concrete question faster or with stronger evidence than local manual
work. If a new route does not offer a clearer decision, lower repeat-failure
risk, better recovery, or repo-specific capability that an existing owner lacks,
improve the existing owner instead of adding a parallel entry.

This repo owns only XIC-specific overlays and routing docs. Global skills are
environment-level workflow dependencies outside this repo diff. If a named
global skill is unavailable, report `global skill unavailable`, use `AGENTS.md`,
this routing doc, and `docs/agent/parameter-settings.md` as the minimal fallback
checklist, and do not recreate or copy the global workflow into the repo.

GStack skills are still available and not retired. For this repo, treat them as
upstream workflow references or explicit user-requested tools while the local
skills mature. Do not silently replace the repo-local XIC contracts with a broad
gstack ship/PR/deploy workflow; if a gstack workflow proves better, absorb the
specific lesson into the local skill or explicitly switch the route.

## Dispatch Rules

- Default is main agent only.
- Normal review is one or two reviewers, but broad rule audits, workflow
  rewrites, productization gates, or user-requested debate may use three or more
  reviewers when each reviewer has a distinct decision to challenge.
- Do not downgrade reviewer count, model strength, or useful tooling only to
  save tokens or cost. Downgrade only when the task is clearly mechanical or a
  runtime/tool limit forces it, and report the reason.
- When the user explicitly says to use subagents to review a spec, plan, goal,
  or workflow rule, use the critical artifact review flow below. Do not satisfy
  that request with one generic reviewer unless a thread limit blocks the
  required review and the bypass is reported.
- Reviewer dispatch is an auditable checklist item, not a tool-enforced gate.
  When a hard trigger below applies, the plan/final summary must state which
  reviewer was used or why it was intentionally bypassed.
- Subagents do not auto-spawn. Delegate explicitly and give each reviewer a
  bounded read-only task.
- Repo-local `.codex/agents/*.toml` files are role profiles, not guaranteed
  runtime `agent_type` values. If the available tool exposes only generic
  `reviewer`, spawn that generic reviewer and paste the relevant repo-local role
  brief into the prompt. Name the intended role in the prompt and final
  synthesis.
- The main agent owns synthesis, file edits, final judgment, and verification.
- Reviewer subagents are read-only. `implementation-worker` is the only
  repo-local role allowed to edit assigned files. `tester` is workspace-write
  only for command side effects such as caches, logs, and named output
  artifacts. Do not give two agents the same write scope.
- If thread limits block full review, dispatch in this order: mandatory blocker
  reviewer, original blocker re-check, then optional specialist. Close stale
  agents before downgrading a required multi-angle review. If the review still
  cannot fit, run reviewers sequentially rather than silently collapsing to one
  angle.

## Tool And Plugin Posture

- Tools are first-class engineering leverage. Use `rg`/targeted reads for text,
  CodeGraph for structural ownership/impact questions, GitHub/gh for PR and CI
  state, Superpowers/global skills for reusable workflows, and subagents for
  independent review or implementation slices.
- Before a long tool chain or expensive run, write the one-line decision map:
  `question -> tool/evidence -> action if pass -> action if fail`.
- If the question is exploratory, use parallel subagents or bounded outside
  research instead of serially guessing.
- If a tool result cannot change the next action, skip that specific run; do
  not use this as a reason to avoid other useful tools.
- For user-facing updates, translate internal artifact names into plain
  language before relying on them as evidence.

## Reviewer Output Contract

Every reviewer should return the same compact shape:

```text
Verdict:
Blocking findings:
Evidence:
Would this change next action?:
Smallest fix:
Residual risk:
Ownership / placement:
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
| `implementation-contract-reviewer` | Code/public contract change, CLI/config/schema/parser/test behavior, diagnostic entrypoint changes | Code path mapping, contract review, test strategy, diagnostics reuse; add the PR-review lenses below when their triggers fire |
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
- Any `.codex/agents/*.toml`, `docs/agent/subagent-routing.md`, or AGENTS
  workflow-rule change gets `docs-handoff-reviewer` to check role overlap,
  trigger drift, and output-contract regression.
- Any phase plan that could preserve a bad legacy path, overclaim evidence, or
  add an expensive gate gets `strategy-challenger`.
- Any public CLI/config/schema/workbook/TSV/downstream handoff change gets
  `implementation-contract-reviewer`.
- Any diff that adds or changes broad exception handling, fallback/default
  behavior, fail-open/fail-closed gates, missing-artifact behavior, or
  user-facing error messages adds the `silent-failure` lens to
  `implementation-contract-reviewer`.
- Any diff that adds or materially changes dataclasses, protocols, schema
  models, domain DTOs, public contract rows, or invariant-bearing state adds
  the `type-invariant` lens to `implementation-contract-reviewer`.
- Any PR/update that changes behavior, parser/writer gates, diagnostics,
  public output contracts, matrix-writing authority, or validation acceptance
  adds the `test-coverage-quality` lens to `implementation-contract-reviewer`
  or a verification-only `tester`.
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

## PR Review Lenses From Claude Plugins

The Claude official `pr-review-toolkit` plugin is useful as a prompt library,
not as a primary Codex runtime surface. Its agents are Claude-agent/command
files, not Codex skills in this environment. Do not add parallel XIC role
families for them. Instead, paste the relevant lens into the existing
`implementation-contract-reviewer` or `tester` prompt when the trigger fires.

- `silent-failure`: inspect all `try/except`, broad catches, warning-only
  failures, fallback/default branches, missing-artifact handling, optional
  suppression, retry exhaustion, and fail-open behavior. For XIC, this is
  especially important around diagnostics, RAW/TSV loading, activation gates,
  expected-diff checks, productization tier claims, and user-readable errors.
- `type-invariant`: inspect new or changed dataclasses, protocols, schema
  models, public row contracts, and stateful domain objects for invariants,
  construction-time validation, mutation safety, and whether illegal states are
  representable. For XIC, focus on `Trace`, `TraceGroup`, `PeakHypothesis`,
  `EvidenceVector`, `IntegrationResult`, `AuditTrail`, ReviewAction schemas,
  method manifests, and matrix/value-delta row contracts.
- `test-coverage-quality`: inspect whether tests protect behavior and public
  contracts rather than implementation details. Prioritize negative tests,
  boundary cases, fail-closed behavior, expected-diff/output schema tests,
  diagnostics index coverage, and real-data validation claims when relevant.

Use these lenses to make Codex subagent prompts sharper. Do not enable
Claude-only loops or memory systems just to access these ideas.

## Critical Artifact Review

Use the global `critical-artifact-review` workflow when this section triggers.
That global skill is responsible for discovering and following this routing doc;
this section is the XIC-specific contract.

When the user asks for subagent or critical review of durable artifacts, dispatch
by review angle, not by artifact count. If two independent artifacts are reviewed
in the same turn, each artifact gets the relevant angles unless the main agent
explicitly reports a thread-limit downgrade and runs the missing angle
sequentially.

| Artifact | Required reviewers | Add when relevant |
| --- | --- | --- |
| Handoff productization spec or phase plan | `strategy-challenger` and `implementation-contract-reviewer` | `docs-handoff-reviewer` when docs/source-of-truth wording changes |
| Cleanup-only structural spec | `implementation-contract-reviewer` | `strategy-challenger` when phase order, legacy retirement, or product direction could drift |
| Validation, RAW, benchmark, or gate spec | `strategy-challenger` and `validation-evidence-reviewer` | `ops-triager` for runner/path/PowerShell risk |
| Workflow, AGENTS, subagent, hook, sandbox, or goal-routing spec | `docs-handoff-reviewer` and `strategy-challenger` | `implementation-contract-reviewer` when CLI/config/tests are touched |
| Small docs wording-only change | `docs-handoff-reviewer` | none unless it changes a gate or public contract |

For every reviewer prompt, include:

- exact worktree and file path;
- intended repo-local role name;
- read-only constraint;
- the decision the reviewer should challenge;
- the compact output contract from this document.

For XIC artifacts, reviewer prompts should challenge the strongest assumption
instead of proofreading. Ask for stale-artifact risk, cheaper existing oracle,
public-contract drift, validation cost vs decision value, missing exit rule, and
whether the artifact advances the handoff spine or only preserves legacy shape.
When relevant, name downstream surfaces such as `alignment_matrix.tsv`,
`peak_candidates.tsv`, readiness labels, RAW runner/output-level rules, and
artifact retention.

Trigger phrases that must use this section for non-trivial durable artifacts
include: `subagent review`, `用 subagent 審`, `審 spec`, `審 plan`,
`挑戰這份 spec`, `critical-thinking review`, `review goal prompt`,
`review workflow`, and `review handoff`. For typo-only or link-only docs
changes, use a local self-review or `docs-handoff-reviewer` instead of a full
review.

## Goal Contracts

Use the global `goal-execution` skill for goal creation, tightening, review, and
runtime execution. Apply `.codex/skills/xic-goal-execution/SKILL.md` only for
XIC-specific context, validation tiers, RAW stop rules, and handoff/productization
constraints.

Do not maintain a second goal template in this routing doc. The global skill is
the canonical reusable contract shape. XIC goals should normally reference
`AGENTS.md`, `docs/agent/parameter-settings.md`, this routing doc, the active
spec/plan, and existing diagnostics or validation artifacts. Avoid broad goals
such as "improve the pipeline" unless the goal first asks for a bounded plan.

## 補強 Loop

Post-review補強 should not spawn a new review group.

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
- For RAW-backed runs, use `.codex/skills/xic-raw-validation/SKILL.md` before
  launching or accepting the result.

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

Use the global `pr-closeout` workflow when preparing, opening, updating, or
closing out a PR or development branch whose description will become future
project memory. Apply `.codex/skills/xic-pr-closeout/SKILL.md` for XIC-specific
readiness labels, validation tiers, downstream handoff, RAW artifacts, and
merge/history expectations.

Use `.codex/skills/xic-large-pr-review/SKILL.md` when reviewing a large or
diagnostics-heavy PR. The review should build a blast-radius map first, inspect
shared helpers and public contracts before mechanical writer churn, and report
the strongest evidence actually checked: CI, focused tests, 8RAW parity, 85RAW
parity, targeted benchmark, manual EIC/MS2 review, or `diagnostic_only`.

Before opening, updating, or marking a PR ready, the main agent must run the
PR Verification Gate in `docs/agent/execution-gates.md` from the active
worktree. Do not replace the shard gate with a monolithic full-suite pytest run.

Any real lint, typecheck, or test failure is a blocker and must be fixed before
PR. If the sandbox blocks dependency resolution, executable spawn, or DLL
loading, rerun the same command with appropriate approval rather than replacing
it with a narrower check. Record the exact commands and results in the closeout
surface.

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
- Two bounded local iterations failed to change the decision.
- The method family itself is uncertain and an external guideline, paper, or
  mature implementation could change the gate design.

Output must be bounded: 2-4 sources or examples, the design idea each source
supports, and the minimum local experiment that would make it worth
implementing.

## Anti-Patterns

- Do not dispatch agents without distinct questions or non-overlapping review
  angles. It is fine to dispatch several agents for a broad audit when each one
  can change the decision.
- Do not use subagents to avoid reading the repo yourself.
- Do not let reviewer findings become new scope without checking whether they
  close the current decision.
- Do not create a new role for a one-off concern. Add a role only after the
  concern recurs and cannot fit an existing family.
- Do not treat orchestration as the product. The purpose of tools and subagents
  is to improve decisions, expose evidence, and reduce repeated mistakes, not to
  add ceremony or hide uncertainty.
