---
name: xic-raw-validation
description: Use this before launching or accepting XIC Extractor RAW-backed validation when the task involves 8RAW/85RAW, alignment validation, production-equivalent gates, benchmark acceptance, timing heartbeat, or expensive RAW I/O. Do not use it for pure unit tests, synthetic no-RAW checks, or reading existing artifacts unless the result is being used as gate evidence.
---

# XIC RAW Validation

Use this skill before launching or accepting RAW-backed validation for XIC
Extractor.

This is the execution checklist for the repo's expensive validation workflow.
It points to canonical parameters instead of duplicating them.

## Trigger Threshold

Use this skill when:

- launching, rerunning, or accepting 8RAW / 85RAW validation;
- validating alignment, benchmark, timing, heartbeat, or production-equivalent
  outputs;
- a RAW-backed command may run longer than a normal focused test;
- existing artifacts are being used as gate evidence.

Do not use this skill for:

- unit tests or synthetic no-RAW tests;
- quick code import checks;
- reading a validation note for background only;
- small diagnostics that do not touch RAW files or gate interpretation.

## Required Reading

Read first:

- `AGENTS.md`
- `docs/agent-parameter-settings.md`
- `docs/agent-subagent-routing.md`
- active validation spec, plan, output index, or note

Search existing artifacts before rerunning:

- `tools/diagnostics/INDEX.md`
- relevant `docs/superpowers/notes/`
- task-specific `output/` directories

## Preflight

Before launching a RAW run, state:

- decision the run can close;
- sample set: synthetic, 8RAW, 85RAW, targeted benchmark, or manual EIC;
- documented Python runner and Thermo DLL/RAW paths;
- foreground command shape;
- output level and expected artifacts;
- heartbeat or timing sidecars;
- timeout or stop condition;
- why existing artifacts cannot answer the question.

For alignment validation, prefer `--output-level validation-minimal` unless the
task explicitly needs human review/debug reports.

Do not launch 85RAW via background `Start-Process` from the Codex shell unless
the user explicitly approves an external-terminal or automation path.

## Reviewer Trigger

Use `validation-evidence-reviewer` for:

- any 85RAW run;
- likely >30 minute RAW run;
- production-equivalent validation;
- benchmark or gate acceptance that affects product readiness.

Use mode `preflight` before launch and mode `acceptance`, `science`, or
`performance` after the run as appropriate.

## Acceptance Labels

Keep these separate:

- `run_ok`: command completed and emitted expected artifacts.
- `gate_ok`: artifacts satisfy the stated gate.
- `production_ready`: evidence supports production behavior.
- `inconclusive`: result cannot close the decision; name missing evidence or
  exit rule.

Preflight output is not validation. A timing heartbeat is not correctness.
Diagnostic sidecars are not downstream delivery unless the active contract says
so.

## Output Surface Rules

For large alignment validation, the primary machine delivery surface is
`alignment_matrix.tsv`. Targeted benchmark diagnostics also need
`alignment_review.tsv` and `alignment_cells.tsv`.

Do not produce `.xlsx`, HTML, owner-edge, status-matrix, event-owner, or
ambiguous-owner outputs for large validation unless a human review or debug task
explicitly needs them.

## Stop Conditions

Stop and inspect instead of relaunching when:

- heartbeat stalls or exceeds expected runtime;
- preflight fails or checks a weaker contract than the real command;
- output artifacts are missing or unexpectedly huge;
- the run cannot change the next action;
- the command uses an undocumented runner/path combination;
- PowerShell, sandbox, approval, or writable-root uncertainty appears.

When sandbox or command-shape uncertainty is the issue, run:

```powershell
python -m scripts.agent_sandbox_doctor --command "<command>"
```

The doctor is diagnostic only; it does not execute the command or replace user
approval.
