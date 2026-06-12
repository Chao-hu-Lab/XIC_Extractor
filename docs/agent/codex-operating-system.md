# Codex Operating System

This repo uses a small Codex operating system: root rules, nested docs, focused
skills, minimal hooks, and explicit subagent routing. The goal is to catch
high-cost mistakes early without turning every task into ceremony.

## Placement Model

- `AGENTS.md`: always-loaded repo invariants and hard gates only.
- `docs/agent/*.md`: nested contracts for detailed communication, execution,
  planning, validation, architecture, and public contracts.
- `.codex/skills/`: XIC-specific reusable workflows that need a checklist at
  execution time.
- `.codex/rules/*.rules`: command-prefix policy for destructive or high-impact
  operations.
- `.codex/hooks.json` and `.codex/hooks/*.py`: low-noise lifecycle checks.
- `.codex/agents/*.toml`: opt-in reviewer/worker profiles, routed by
  `docs/agent-subagent-routing.md`.
- Automations: only for recurring workspace jobs or heartbeat follow-ups that
  would otherwise be forgotten; do not turn every checklist into an automation.

## Current Repo-Local Hooks

The hook set is intentionally small:

- `UserPromptSubmit`: scans the prompt for XIC high-risk keywords and injects
  workflow context for architecture preflight, PR review, or RAW validation. It
  also blocks prompt text that looks like a pasted secret.
- `PreToolUse`: blocks clear destructive git commands and background RAW
  launches through `Start-Process`; adds context when edits touch
  execution-affecting config or root agent contracts.
- `PostToolUse`: catches pytest runs that collected zero tests, and points the
  agent to fix the node id instead of treating the run as validation.

Hooks are guardrails, not full enforcement. Keep them deterministic, fast, and
rarely chatty. If a hook fires too often without changing behavior, remove or
narrow it.

## Current Repo-Local Rules

Rules cover command prefixes where the desired behavior is stable:

- forbid known destructive git rollback commands;
- prompt before untracked-file cleanup, recursive deletion, external/background
  launch, `git push`, and `gh pr merge`.

Rules apply to Codex approval policy and are evaluated from `.codex/rules/` when
the project `.codex/` layer is trusted. Restart Codex after editing rules.

## Adoption Rules

Add a new rule, hook, skill, subagent, or automation only when it satisfies at
least one condition:

- it blocks a repeated high-cost failure before work starts;
- it improves reuse of an existing owner/helper;
- it closes a validation or contract decision earlier;
- it reduces noisy manual review without hiding product risk.

Do not add one just because a feature exists. Prefer improving an existing hook
or skill over adding a parallel one.

## Self-Improvement Rule

When an agent correction, repeated failure, or review finding suggests durable
guidance, first decide the scope:

- global rule: applies across repos;
- repo root `AGENTS.md`: high-frequency XIC invariant that should influence
  every turn;
- nested `docs/agent/*.md`: detailed XIC contract that agents should load when
  relevant;
- repo skill: reusable XIC workflow with an execution checklist;
- hook/rule: deterministic early brake for repeated high-cost failure;
- no durable rule: one-off situation.

Before adding new guidance, search the relevant owner for an existing rule to
tighten. If root `AGENTS.md` grows past about 200 lines, consolidate or move
details into nested docs alongside any additions.

## Change Protocol

Changes to `.codex/config.toml`, `.codex/hooks.json`, `.codex/rules/`, hook
scripts, execpolicy, or subagent TOML are execution-affecting config changes.
Before closeout:

```powershell
git diff --check
Get-Content .codex\hooks\fixtures\prompt_architecture.json -Raw | python .codex\hooks\xic_prompt_router.py
Get-Content .codex\hooks\fixtures\pretool_git_reset.json -Raw | python .codex\hooks\xic_pre_tool_guard.py
Get-Content .codex\hooks\fixtures\posttool_zero_tests.json -Raw | python .codex\hooks\xic_post_tool_guard.py
```

Also scan the diff for secrets, private local paths, absolute machine-specific
paths, and accidentally tracked local Codex config.

## Trust And Review

Project-local hooks require Codex hook trust. Use `/hooks` in Codex to inspect,
review, trust, or disable changed hook definitions. New or modified hook
definitions are skipped until trusted by the runtime.

## What Not To Automate Yet

- Do not auto-run 85RAW. Keep it explicit and foreground unless the user creates
  a dedicated automation.
- Do not auto-format or rewrite planning docs at stop time.
- Do not auto-create PRs, merge, push, or branch-clean without explicit user
  request.
- Do not auto-promote diagnostic-only evidence into production behavior.
