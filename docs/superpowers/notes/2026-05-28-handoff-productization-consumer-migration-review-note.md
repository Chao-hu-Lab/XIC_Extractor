# Handoff Productization Consumer Migration Review Note

## Verdict

Post-implementation review found blockers and DX concerns. All blocking findings
were fixed before closeout.

## Reviewers

- `critical-artifact-review` / contract reviewer
  - Verdict: `BLOCKING` before fixes.
  - Finding: public `ExtractionResult` runtime type hints failed under
    `typing.get_type_hints(...)` because `PeakHypothesis` and
    `IntegrationResult` were only imported under `TYPE_CHECKING`.
  - Finding: selected integration `PeakWidth` needed to preserve the existing
    non-negative width contract, rather than exposing a negative
    `rt_width_min`.
  - Residual risk: `Detection Counted` in score-breakdown remains legacy
    detection logic by design; this PR migrates wide/long CSV numeric
    projection only.
- `devex-review`
  - Verdict: `DONE_WITH_CONCERNS` before fixes.
  - Finding: the implementation plan looked unexecuted because the checklist
    remained open while closeout claimed completion.
  - Finding: the ruff command needed a reproducible non-escalated cache setting
    for this Windows sandbox.
  - Finding: reviewer evidence needed a durable note instead of only an
    in-thread subagent message.

## Fixes

- `ExtractionResult` now imports `PeakHypothesis` and `IntegrationResult` at
  runtime, and `tests/test_result_assembly.py` verifies
  `typing.get_type_hints(ExtractionResult)` resolves.
- `ExtractionResult.reported_peak_width` returns
  `abs(selected_integration.rt_width_min)` for selected integration output.
  Result assembly and CSV tests use a negative divergent `rt_width_min` and
  expect positive `PeakWidth`.
- CSV writer peak-existence detection now requires all numeric peak metrics to
  be present before emitting numeric MS1 fields, matching the plan's all-or-ND
  projection contract.
- The implementation plan now has an execution-status banner pointing to the
  closeout note as the current status source.
- Ruff verification now uses `$env:UV_CACHE_DIR='.uv-cache'`, which avoids the
  user-profile `uv` cache permission failure and keeps cache artifacts ignored
  inside the worktree.

## Current Status

Status is `handoff_spine_consumer_migration_ready` / `production_candidate`.
No 8RAW or 85RAW validation is required for this scoped consumer migration.
