---
title: "Codex Environment Noise Triage"
date: "2026-06-24"
category: "workflow"
module: "agent-environment"
status: "current"
tags: ["codex", "git-lock", "hooks", "environment-noise"]
source_refs:
  - ".codex/hooks/xic_post_tool_guard.py"
  - ".codex/hooks/fixtures/assert_hook_outputs.py"
  - "docs/agent/execution-gates.md"
  - "docs/agent/parameter-settings.md"
---

# Codex Environment Noise Triage

## When To Read

Read this when PR repair, CI work, or validation is slowed down by repeated
Codex/environment warnings: Git lock/ref-lock friction, stuck read-only Git
queries, GitHub Actions not starting after a ref update, or hook warnings that
do not match the command's real failure mode.

## Problem

Environment noise can make an already hard PR stack look worse than it is. In
this closeout, stale read-only `git.exe` queries and an over-broad hook warning
both produced repeated lock/ref-lock noise. One source was real local process
friction; another was a false positive where searching or reading docs that
mentioned `.git/index.lock` made the hook warn as if Git had failed.

## Tempting Wrong Path

Do not treat every hook warning as code failure. Do not keep retrying the same
Git operation while a stale process or lock may exist. Do not disable the hook
globally to stop noise; narrow the trigger so real safety warnings still fire.

## Working Pattern

Separate three cases before changing code:

- actual Git lock failure: a Git command reports an error such as inability to
  create `.git/index.lock` or lock a ref;
- stuck Git metadata query: read-only `git status`, `rev-parse`, `remote -v`,
  or config query remains alive long after it should have exited;
- hook false positive: command output merely displays lock-related text from
  docs, diffs, or source files, rather than reporting a lock failure from the
  Git operation's error stream.

For actual lock/process friction, inspect `.git/*.lock` and live `git.exe`
processes before removing stale locks or stopping stale read-only processes.
For hook false positives, add a fixture that proves the noisy command is silent
and the real failure still warns.

## Evidence

- Commands actually run:
  hook fixture smoke, ruff on hook files, `git diff --check`, and diff
  secret/local-path scan.
- Code:
  `xic_post_tool_guard.py` now only reports lock/ref friction when a Git command
  produces lock-error output on the error stream, not when a search or diff
  merely displays lock text.
- Tests:
  `assert_hook_outputs.py` covers the separation: `rg` and `git diff` output
  with lock text stay silent; real `git status` lock error still emits the
  warning.

## Limits

This does not prevent external Git integrations from spawning short-lived Git
queries. It only removes one false-positive warning class and records the manual
triage path for stale read-only Git processes.

## Next Time

1. If lock warnings repeat, inspect real `.git/*.lock` files and live `git.exe`
   processes first.
2. If the warning follows a docs/source search or a diff display, suspect hook
   false positive and add a fixture before changing the hook.
3. Keep hook changes narrow and rerun hook smoke, ruff, diff check, and
   secret/local-path scan before closeout.
