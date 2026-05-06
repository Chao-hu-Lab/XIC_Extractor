# Local Minimum Preset Calibration v1 Results

**Date:** 2026-05-06
**Branch:** `codex/local-minimum-preset-calibration-v1`

## Command

```powershell
uv run python scripts\validation_harness.py `
  --suite manual-2raw `
  --grid calibration-v1 `
  --run-id local_minimum_calibration_v1 `
  --output-root output\validation_harness `
  --parallel-mode process `
  --parallel-workers 4
```

## Output

```text
C:\Users\user\Desktop\XIC_Extractor\.worktrees\local-minimum-preset-calibration-v1\output\validation_harness\local_minimum_calibration_v1\manual_2raw\local_minimum_param_sweep_summary.xlsx
```

## Summary

| Rank | Parameter set | Missing manual peaks | Large area misses | Area median abs pct error | RT max abs delta min |
|---:|---|---:|---:|---:|---:|
| 1 | `local_minimum_search_0p05` | 0 | 14 | 0.033835 | 2.119168 |
| 2 | `local_minimum_search_0p05_duration_1p5` | 0 | 14 | 0.033835 | 2.119168 |
| 3 | `local_minimum_search_0p05_duration_2p0` | 0 | 14 | 0.033835 | 2.119168 |
| 4 | `local_minimum_current` | 0 | 12 | 0.034381 | 2.119168 |
| 11 | `legacy_savgol` | 2 | 5 | 0.025676 | 0.794608 |

## Decision

Do not update the shipped `local_minimum` preset from this run.

Rationale:

- The best focused candidate improves median area error only slightly:
  `0.034381` to `0.033835`.
- The same candidate increases large area misses from `12` to `14`.
- The duration cap candidates (`1.5`, `2.0`, `3.0` minutes) do not change the
  manual truth metrics versus current settings in this dataset.
- All local-minimum candidates still show the same max RT outlier
  (`2.119168` minutes), so this run does not provide a clean preset update.
- The max RT outlier is target `Y` in the NoSplit run
  (`manual_rt=4.82`, `program_rt=6.939168`). The same target also has a large
  Split-run RT delta (`1.492037`). Because the focused parameter candidates do
  not change this behavior, it should be treated as a target/scoring follow-up,
  not as evidence for changing the global local-minimum preset.

Keep `legacy_savgol` as the default and keep the current `local_minimum` preset
until a candidate improves area agreement without increasing large misses.
