---
name: xic-raw-validation
description: Use this before launching or accepting XIC Extractor RAW-backed validation when the task involves 8RAW/85RAW, alignment validation, production-equivalent gates, benchmark acceptance, timing heartbeat, or expensive RAW I/O. Do not use it for pure unit tests, synthetic no-RAW checks, or reading existing artifacts unless the result is being used as gate evidence.
---

# XIC RAW Validation

Execution checklist for expensive RAW-backed validation. It points to canonical
parameters instead of duplicating runner details.

## Use When

- launching, rerunning, or accepting 8RAW / 85RAW validation;
- validating alignment, benchmark, timing, heartbeat, or production-equivalent
  outputs;
- a RAW-backed command may run longer than a focused test;
- existing RAW artifacts are being used as gate evidence.

Do not use for pure unit tests, synthetic no-RAW checks, quick imports, or
reading a note for background only.

## Preflight Before Launch

State the decision the run can close, sample set, documented runner and
Thermo/RAW paths, foreground command shape, output level, expected artifacts,
heartbeat/timing sidecars, timeout or stop condition, and why existing artifacts
cannot answer the question.

For alignment validation, prefer `--output-level validation-minimal` unless a
human review/debug task explicitly needs more output. Do not launch 85RAW via
background `Start-Process` from the Codex shell without explicit approval.

## Acceptance Boundary

Keep labels separate: `run_ok`, `gate_ok`, `production_ready`, and
`inconclusive`. Preflight output is not validation. Timing heartbeat is not
correctness. Diagnostic sidecars are not downstream delivery unless the active
contract says so.

## References

- Required reading, artifact search, reviewer trigger, and output rules:
  `references/raw-validation-contract.md`
- Stop conditions and sandbox doctor:
  `references/raw-stop-rules.md`
- Trigger and near-neighbor cases:
  `evals/trigger-cases.md`
- Portable skill interface metadata:
  `agents/interface.yaml`
