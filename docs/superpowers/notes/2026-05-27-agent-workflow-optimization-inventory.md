# Agent Workflow Optimization Inventory

**Date:** 2026-05-27
**Branch:** `codex/agent-workflow-optimization`
**Status:** inventory + docs alignment + CLI preflight guard; no RAW validation rerun

## Scope

This branch is a short-lived optimization branch for agent workflow, validation
defaults, and project-operation entry points. It is intentionally separate from
the handoff productization branch so repo process improvements do not blur with
product behavior work.

The goal is not to create another agent settings system. The goal is to audit the
current source-of-truth surface, identify drift, and update the existing entry
points.

## Current Canonical Entries

| Area | Current canonical entry | Current status |
|---|---|---|
| Repo-local agent contract | `AGENTS.md` | Good top-level router. It points to project layout and maintained parameter settings. |
| Stable local runners / RAW paths / validation tiers | `docs/agent-parameter-settings.md` | Current strongest operational source of truth. It records `.venv` RAW runner, RAW/DLL paths, `validation-minimal`, heartbeat, foreground 85RAW, and known anti-patterns. |
| Directory placement / scratch hygiene | `docs/project-layout.md` | Good file-placement source of truth. Some static counts are stale by nature but not blocking. |
| Diagnostic tool discoverability | `tools/diagnostics/INDEX.md` | Good index. It now documents diagnostic groups and shared `diagnostic_io.py`. |
| Handoff product direction | `docs/superpowers/notes/2026-05-27-handoff-productization-c0-source-of-truth.md` | Current source of truth for C0 spine direction. Older handoff checklist is historical inventory. |

## Existing Implementation Surface

- `pyproject.toml` exposes five user-facing scripts:
  `xic-extractor`, `xic-extractor-cli`, `xic-discovery-cli`,
  `xic-align-cli`, and `xic-align-validate-cli`.
- Code layout currently has eight main `xic_extractor/` subpackages:
  `alignment`, `configuration`, `diagnostics`, `discovery`, `extraction`,
  `instrument_qc`, `output`, and `peak_detection`.
- Repository scale at inventory time:
  - `xic_extractor/`: 235 tracked files
  - `scripts/`: 22 tracked files
  - `tools/diagnostics/`: 122 tracked files
  - `tests/`: 242 tracked files
  - `docs/superpowers/specs/`: 75 tracked files
  - `docs/superpowers/plans/`: 74 tracked files
  - `docs/superpowers/notes/`: 41 tracked files before this note
- Largest code modules are still concentrated in alignment / scoring /
  diagnostics. This is expected, but it means operational defaults must steer
  agents to the right existing helpers before they invent new diagnostics.

## Drift / Gaps

### 1. Validation Harness Docs Are Older Than Agent Parameter Settings

`docs/agent-parameter-settings.md` correctly says that validation and downstream
handoff should default to:

```text
validation-minimal + production-equivalent + validation-fast + super-window
+ timing heartbeat
```

It also says `.xlsx` and HTML are not the formal large-run delivery contract.

`docs/validation-harness.md` still presents older workbook-centered flows:

- `tissue-8raw` and `tissue-85raw` output contract is described as
  `xic_results_process_w4.xlsx`;
- untargeted fast-path examples still use `--output-level machine`;
- full 85RAW gate still points to `scripts\validation_harness.py`, not the
  currently verified foreground `scripts.run_alignment` shape with heartbeat.

This is the most likely documentation source of repeated wrong command shapes.

Recommended action:

- Update `docs/validation-harness.md` so it defers large alignment validation to
  `docs/agent-parameter-settings.md`.
- Keep workbook validation docs only for targeted extraction / workbook-specific
  gates.
- Add an explicit warning that validation harness is not the canonical 85RAW
  alignment acceptance runner unless it is updated to emit the same minimal
  machine contract and heartbeat.

### 2. README Still Describes Older Delivery Semantics For Some Workflows

`README.md` still says the default XIC extraction delivery is an Excel workbook,
which is valid for targeted GUI extraction. But its validation / alignment
section still shows `--output-level machine` and mentions workbook parity as if
that were the primary large-run contract.

Recommended action:

- Do not rewrite the whole README.
- Add a short distinction:
  - targeted GUI extraction: workbook remains human-facing delivery;
  - alignment validation / downstream statistics: `alignment_matrix.tsv` under
    `validation-minimal` is the machine delivery surface.

### 3. Repo-Local Skills Should Stay Thin; Review Roles Are Project Subagents

No repo-local `skills/` directory is present in this worktree. The repeated
problem was not missing skill code; it was inconsistent entry-point use and
under-specified review roles. This branch therefore adds a small project-specific
`.codex/agents/` set for recurring read-only reviewers, while keeping workflow
rules in `AGENTS.md`.

Recommended action:

- Do not add a repo-local skill system yet.
- Keep recurring review roles as project subagents, not a second parameter or
  skill source of truth.
- If a skill is added later, make it a thin reusable workflow that points to
  `docs/agent-parameter-settings.md`, `tools/diagnostics/INDEX.md`, and the
  active spec/plan. It should not duplicate stable paths or command bodies.
- Keep a small set of recurring review families in `.codex/agents/`, not one
  subagent per concern. The final model is five active families plus one manual
  outside-frame researcher.
- Treat specialized concerns as modes inside those families: strategy,
  implementation/contract, validation/evidence, docs/handoff, and ops triage.

### 4. CodeGraph Is Available But Not Initialized In This Worktree

`codegraph` CLI exists on the machine, but this new worktree returns
`Not initialized`.

Recommended action:

- Before code-level architecture edits on this branch, initialize CodeGraph for
  this worktree or explicitly proceed with `rg` + targeted reads.
- Do not make CodeGraph initialization part of every branch unless the branch
  needs structural inspection.

### 5. Diagnostic Tool Index Is Good, But Agents Need A Stronger Preflight Habit

`tools/diagnostics/INDEX.md` is now useful: it groups phase gates, evidence
consistency, alignment diagnostics, backfill reviews, peak/candidate audits,
targeted benchmarks, instrument QC, visualization, area/region audits, and shared
infrastructure.

The remaining risk is not discoverability alone. It is that agents skip the
index when under time pressure and create a new script or rerun an expensive
workflow.

Recommended action:

- Keep `AGENTS.md` as the rule.
- Add a smaller operational checklist in `docs/agent-parameter-settings.md` or
  `docs/validation-harness.md`: before expensive validation, check existing
  note/output/index first, then name why existing artifacts cannot answer.

## Recommended Optimization Order

1. Fix stale validation documentation first.
   This has the highest leverage because it directly affects 85RAW runtime,
   output size, and repeated launch failures.

2. Add one tiny validation preflight helper or documented command, only if it
   reduces repeated human/agent mistakes:
   - verify discovery index sample count;
   - verify candidate CSV and RAW/DLL paths;
   - print the canonical 85RAW alignment command shape;
   - refuse background `Start-Process` mode by design.

3. Tighten README wording for alignment/downstream handoff without changing
   targeted GUI workbook documentation.

4. Only after those are stable, decide whether a repo-local skill is worth it.
   The first skill should orchestrate existing docs; it should not become a
   second parameter-settings document.

## Not In Scope For This Branch

- Product behavior changes.
- Handoff Step 2 consumer migration.
- New diagnostics unless the inventory shows no existing tool can answer the
  decision.
- 85RAW reruns.
- Broad module decomposition.

## First Pass Updates

After this inventory, the branch updated the stale validation documentation
surface:

- `docs/validation-harness.md` now states that `scripts\validation_harness.py`
  is a targeted extraction / workbook comparison harness, not the canonical
  alignment acceptance runner.
- `README.md` now separates targeted workbook regression from untargeted
  alignment / downstream handoff and points large alignment validation to
  `docs/agent-parameter-settings.md`.
- `docs/agent-parameter-settings.md` now clarifies that the validation harness
  is not the 85RAW alignment acceptance runner unless it implements the same
  minimal machine contract and heartbeat shape documented there.
- `scripts.run_alignment` now supports `--expected-sample-count` and
  `--preflight-only`, turning the common 8RAW/85RAW discovery-index mismatch
  from a manual reminder into a CLI-enforced launch guard. The preflight uses
  the production discovery-batch parser and checks candidate CSV / RAW path
  existence without loading candidates or opening RAW files.
- `AGENTS.md` now requires non-trivial reviews to include a critical-thinking
  angle and records repeated syntax failures as operational memory.

## Critical-thinking Review

- Strongest assumption: sample count plus candidate CSV / RAW path existence is
  enough to stop the repeated wrong-launch failure mode. It is not a full
  artifact freshness proof, so phase notes still need to identify the current
  discovery artifact.
- Stale-artifact risk: `--preflight-only` validates launch shape and artifact
  existence, but intentionally does not parse every candidate row or read RAW
  chromatograms. A successful preflight does not prove the full run will
  complete.
- Cheaper oracle: for most wrong-index mistakes, `--expected-sample-count` is
  cheaper and less error-prone than manually remembering `(Import-Csv ...).Count`.
- Invalidation condition: if future discovery indexes contain non-sample rows or
  support multi-row-per-sample semantics, the sample-count guard must be
  replaced by an explicit sample-stem cardinality guard.

## Second Pass Updates

The first review pass found that a row-count-only preflight could create false
safety. The branch then tightened the workflow contract:

- `scripts.run_alignment` now uses the same discovery-batch parser as the real
  alignment run.
- Preflight checks candidate CSV existence and RAW path existence without loading
  candidate rows or opening RAW files.
- Preflight output explicitly says `diagnostic_only` and `no validation
  completed`.
- `--expected-sample-count 85` now enforces the canonical 85RAW launch contract:
  minimal output, production-equivalent backfill, no heavy audit evidence,
  validation-fast profile, super-window, timing sidecars, and local `.venv`
  Python.
- RAW path hard-fail is scoped to preflight and canonical 85RAW validation; a
  normal alignment launch can still let the pipeline represent missing RAW
  samples through its existing downstream semantics.
- Duplicate `sample_stem` values are rejected because the shared parser stores
  per-sample artifacts in dictionaries.
- `README.md`, `docs/validation-harness.md`, and
  `docs/agent-parameter-settings.md` now describe `validation-minimal` as the
  primary machine gate surface, while acknowledging lightweight sidecars.
- The `620.9 s` historical 85RAW evidence is no longer presented as proof that
  the newer `--expected-sample-count 85` guard was part of that run.
- `.codex/agents/` now contains a collapsed project subagent set inspired by
  public Codex subagent role catalogs: `strategy-challenger`,
  `implementation-contract-reviewer`, `validation-evidence-reviewer`,
  `docs-handoff-reviewer`, `ops-triager`, and manual-trigger
  `outside-frame-researcher`. The branch intentionally does not import broad
  agent packs wholesale.
- `docs/agent-subagent-routing.md` now maps planning, implementation review,
  expensive validation, acceptance, CI red, documentation/rule changes,
  performance work, and post-review補強 to role families with dispatch caps,
  hard triggers, and a shared reviewer output contract.
- `AGENTS.md` now points to the routing doc without turning the top-level agent
  contract into a second role catalog.

## Third Pass Role Consolidation

A follow-up subagent review challenged the 16-role design as too granular. The
branch accepted that finding and collapsed the roles:

- Active families are capped at five: strategy, implementation/contract,
  validation/evidence, docs/handoff, and ops triage.
- `outside-frame-researcher` is manual-trigger only when local evidence cannot
  discriminate options.
- Normal dispatch is capped at two reviewers; three reviewers require genuinely
  independent surfaces and findings that can change the next action.
- Post-review補強 is a fixed loop: main agent fixes, original blocker reviewer
  re-checks when available, and one extra reviewer is added only if scope,
  contract, or gate behavior changed.
- Validation acceptance must keep `run_ok`, `gate_ok`, `production_ready`, and
  `inconclusive` separate.
- Reviewer hard triggers are documented as auditable checklist items, not
  fictional tool-enforced gates.
- CI red paths use the existing CI skill workflow first; `ops-triager` is for
  unclear check metadata, branch protection, Windows runner, or reproduction.
- `validation-evidence-reviewer` requires explicit mode selection:
  `preflight`, `acceptance`, `science`, `performance`, with at most two modes per
  review.
- Repo-local subagents now pin `model = "gpt-5.5"` with role-specific reasoning
  effort: high for strategy/validation, medium for implementation, docs,
  operations, and outside-frame research.

## Fourth Pass: Google Eng Practices And Execution Roles

Reviewing Google's engineering practices exposed two missing pieces:

- The routing model needs to make small, self-contained changes and useful tests
  first-class operating rules, not just review preferences.
- Clean-context implementers and testers are useful, but only when their scope is
  explicit and bounded.

The branch therefore adds two opt-in execution roles:

- `implementation-worker`: workspace-write, `model = "gpt-5.5"`, high reasoning.
  It requires a non-overlapping file/module write scope and must stop if the
  task needs unassigned files.
- `tester`: verification-only workspace-write, `model = "gpt-5.5"`, high
  reasoning. It reproduces failures, verifies fixes, and checks whether tests
  would catch regressions, while forbidding source/docs/config/test edits unless
  separately assigned.

The routing doc now distinguishes reviewer families from execution roles and
records reviewability rules adapted from Google practices: design before detail,
small self-contained changes, tests that actually validate behavior, blocker vs
nit separation, and clear what/why closeout descriptions.

External role reference considered:
`https://github.com/VoltAgent/awesome-codex-subagents`. The useful pieces for
this repo were project-local `.codex/agents/`, read-only reviewer sandboxing,
and explicit delegation. The broad catalog was not copied wholesale because this
repo needs a small stable review set, not a large role inventory.

## Fifth Pass: Goals, Sandbox, And Hooks

The workflow review then checked Codex runtime surfaces instead of adding more
agent roles.

Findings:

- Global Codex config already sets `model = "gpt-5.5"`,
  `model_reasoning_effort = "medium"`, `approval_policy = "on-request"`, and
  `sandbox_mode = "workspace-write"`.
- The repo branch has `.codex/agents/` only. It does not currently add
  project-local `.codex/config.toml`, `.codex/hooks.json`, or
  `.codex/execpolicy/`.
- Existing installed plugins already include hook examples for session start,
  stop-time review, and post-tool memory capture. Adding repo-local hooks now
  would create a new execution surface before this repo has a verified hook
  failure mode.
- `majiayu000/awesome-goal-prompts` is useful as a goal-contract pattern:
  one measurable goal, context, constraints, done conditions, fresh
  verification, output expectations, and stop rules. The repo should learn this
  structure rather than importing the whole catalog.

Decision:

- Do not add active repo-local hooks in this branch.
- Do not add project-local `.codex/config.toml` in this branch; the global config
  already covers the normal sandbox and approval posture.
- Document the accepted runtime posture in `AGENTS.md` and
  `docs/agent-subagent-routing.md`: main sessions use workspace-write +
  on-request, reviewer roles use read-only, tester uses workspace-write only for
  verification side effects, and high-risk runtime config changes require
  docs/handoff review.
- Add goal usage rules to the same routing entry point: goal-shaped contracts are
  for long-running, multi-step, easy-to-drift work, not small bug fixes or
  commits. Active runtime goals still require explicit user request or runtime
  permission.

Critical-thinking review:

- Strongest assumption: passive documentation is enough to stop repeated hook- or
  sandbox-related mistakes. If future runs still repeat the same failure, the
  next smallest step is a passive `Stop` summary hook, not a blocking hook.
- Stale-tool risk: Codex hooks are still a moving surface across CLI/app/plugin
  versions. Any future hook PR must verify the exact local hook schema and not
  rely only on external blog examples.
- Over-design risk: importing a full goal catalog or broad hook suite would
  recreate the same drift problem this branch is trying to remove.

Post-review correction:

- A read-only reviewer found two actionable issues: goal wording was too close
  to automatic active-goal creation, and `tester` was read-only while its job
  includes running pytest / validation commands that often write caches or
  sidecars.
- The docs now distinguish goal-shaped contracts from active runtime goals.
  Active goals are only created with explicit user request or runtime
  permission.
- `tester` is now verification-only workspace-write. It can run commands and
  produce normal verification side effects, but may not edit, stage, commit,
  revert, rename, or delete source/docs/config/test files unless assigned a
  separate implementation scope.

## Sixth Pass: Sandbox Doctor And Version-Control Privacy

The sandbox review found that documentation alone still leaves too much room for
repeating known bad launch shapes. This branch therefore adds
`scripts.agent_sandbox_doctor`, a small diagnostic-only preflight helper. It does
not execute the target command. It classifies common mistakes before they turn
into a failed long run:

- Bash heredoc / `export` / `&&` in PowerShell command strings.
- Background `Start-Process` for 85RAW or alignment heartbeat runs.
- RAW/DLL alignment commands that use bare `python` instead of the local
  `.venv\Scripts\python.exe`.
- Output directories outside the worktree or `C:\tmp`.
- Network/GitHub/package-install commands that need narrow approval.
- Broad unsafe Codex runtime config such as `danger-full-access` or
  `approval_policy = "never"`.

The version-control/privacy check separated real secret risk from path privacy:

- No high-confidence hardcoded token/private-key/API-key pattern was found in
  the current tracked scan after narrowing false positives like
  `task-specific`.
- The repository does contain many tracked machine-specific absolute paths,
  especially historical notes with `C:\Users\user\...` and local RAW/DLL paths
  under `C:\Xcalibur\...`. These are operationally useful in a private repo but
  are privacy-sensitive if the repo or PR target is public.
- The current diff now avoids adding new explicit `C:\Users\user\...` paths
  where a generic `$CODEX_HOME` / `%USERPROFILE%\.codex` wording is enough.
- `.gitignore` now ignores `.env`, `.env.*`, repo-local `.codex/config.toml`,
  and `.codex/execpolicy/` so local secrets and sandbox approvals are less
  likely to be committed by accident.

Critical-thinking review:

- Strongest assumption: this repo remains private or semi-private enough that
  tracked local RAW/DLL path memory is acceptable. If the repo becomes public,
  this assumption fails.
- Missing cleanup: existing historical notes still contain many absolute
  machine paths. This branch does not rewrite history or sanitize old notes,
  because that would be a separate privacy cleanup with a different risk
  profile.
- Next smallest useful step, if public sharing matters: split machine-local
  paths into an untracked local override and convert tracked docs to placeholders
  plus environment-variable examples.
