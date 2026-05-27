# Resolver Default Switch Implementation Note

**Date:** 2026-05-24
**Branch:** codex/peak-pipeline-modernization
**Worktree:** .worktrees/peak-pipeline-modernization
**Gate status:** diagnostic_only

## Implemented

- `region_first_safe_merge` is now the canonical settings default.
- `config/settings.example.csv` now documents `region_first_safe_merge` as the default resolver mode.
- `scripts/run_alignment.py --resolver-mode` now defaults to `region_first_safe_merge`.
- After 8RAW hotfix review, `scripts/run_alignment.py` still rewrites
  `region_first_safe_merge` to `local_minimum` for untargeted alignment
  production peak picking. Region-first evidence is audit context there, not a
  production quantification change.
- `scripts/validation_harness.py` now defaults extraction validation runs to `region_first_safe_merge`.
- Safe-merge failed-gate reasons are emitted as additive candidate audit data.
- `peak_candidates.tsv` now includes `safe_merge_rejection_reason` after the safe-merge promotion provenance columns.

## Verified

- `python -m pytest tests\test_config.py tests\test_run_alignment.py -q`
  - Result: 96 passed.
- `python -m pytest tests\test_region_safe_merge.py -q`
  - Result: 15 passed.
- `python -m pytest tests\test_peak_candidate_table.py tests\test_region_safe_merge.py -q`
  - Result: 27 passed.
- `python -m pytest tests\test_config.py tests\test_run_alignment.py tests\test_region_safe_merge.py tests\test_peak_candidate_table.py -q`
  - Result: 123 passed.
- `python -m pytest tests\test_validation_harness.py -q`
  - Result: 21 passed.
- `python -m pytest tests\test_config.py tests\test_run_alignment.py tests\test_validation_harness.py tests\test_region_safe_merge.py tests\test_peak_candidate_table.py -q`
  - Result: 144 passed.
- `codegraph affected xic_extractor\settings_schema.py scripts\run_alignment.py scripts\validation_harness.py scripts\validation_harness_core.py xic_extractor\peak_detection\region_safe_merge.py xic_extractor\peak_detection\models.py xic_extractor\peak_detection\hypotheses.py xic_extractor\extraction\peak_candidate_table.py`
  - Result: no test files affected by the changed files.
- `python -m pytest tests\test_region_first_safe_merge_comparison.py tests\test_csv_writers.py -q`
  - Result: 11 passed.
- `python -m pytest tests\test_peak_hypotheses.py tests\test_peak_candidate_audit.py tests\test_output_columns.py -q`
  - Result: 15 passed.
- `python -m py_compile scripts\run_alignment.py scripts\validation_harness.py scripts\validation_harness_core.py xic_extractor\settings_schema.py xic_extractor\peak_detection\region_safe_merge.py xic_extractor\peak_detection\models.py xic_extractor\peak_detection\hypotheses.py xic_extractor\extraction\peak_candidate_table.py`
  - Result: exit code 0.

## Post-Implementation Review

Review status: completed after plan execution.

Findings fixed before closing the slice:

- Split the `safe_merge_rejection_reason` row-builder test away from promotion provenance so the fixture does not imply that a promoted candidate and rejected candidate share the same audit state.
- Added `scripts/validation_harness.py` and `ValidationRunSpec` resolver defaults to the P1 default surface after review found they still defaulted to `local_minimum`.
- Updated the P1 spec and implementation plan to document the validation harness
  default surface and the hotfix alignment production guard.

Remaining review verdict: no known actionable unit-level issue. Gate status remains `diagnostic_only` because real-data gates have not run.

## Not Yet Production Ready

- 8RAW strict ISTD benchmark was not run in this implementation slice.
- 85RAW cohort validation was not run.
- Identity coherence gate was not run.
- Cleanup C-spec implementation remains out of scope until Phase 1 real-data validation has a recorded GO / NO-GO.

## Next Gate

Run the Phase 1 acceptance commands from the resolver default switch spec and record GO / NO-GO separately.
