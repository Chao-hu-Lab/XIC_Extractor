# Validation Harness

This repo keeps real-data validation explicit and tiered. The default CI test
suite does not require Thermo RAW files.

## Validation Tiers

| Suite | Purpose | Default data | Output contract |
| --- | --- | --- | --- |
| `manual-2raw` | Manual truth area/RT comparison for resolver development | `C:\Xcalibur\data\20251219_need process data\XIC test` | `local_minimum_param_sweep_summary.xlsx` |
| `tissue-8raw` | Daily real-data smoke and workbook A/B comparison | `C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation` | `xic_results_process_w4.xlsx` |
| `tissue-85raw` | Full tissue release gate only | `C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R` | `xic_results_process_w4.xlsx` |

All tiers write a `validation_summary.csv` under the selected run directory.
The 8-raw and 85-raw tiers validate the expected `.raw` count before running:
8 and 85 respectively.

## Daily Method Validation

Run the manual truth sweep plus the 8-raw validation subset:

```powershell
uv run python scripts\validation_harness.py `
  --run-id method_dev `
  --output-root output\validation_harness
```

Defaults:

- `resolver_mode=local_minimum`
- `parallel_mode=process`
- `parallel_workers=4`
- suites: `manual-2raw`, `tissue-8raw`
- manual sweep grid: `quick`

`manual-2raw` uses the same worker setting, but the quick grid is still mostly
sequential because NoSplit and Split use different target CSVs and are staged as
single-RAW runs. `parallel_workers=4` matters most for `tissue-8raw` and
`tissue-85raw`, where each extraction run contains multiple RAW files.

For local-minimum preset calibration, use the focused grid instead of the daily
quick grid:

```powershell
uv run python scripts\validation_harness.py `
  --suite manual-2raw `
  --grid calibration-v1 `
  --run-id local_minimum_calibration_v1 `
  --output-root output\validation_harness
```

`calibration-v1` keeps the sweep small and targets the current method questions:
whether the historical `resolver_peak_duration_max=10.0` was too permissive, and whether
`resolver_min_search_range_min=0.08` should move toward `0.04-0.05` minutes.
If a candidate is equivalent on clean-matrix manual truth and improves parameter
semantics, it may justify a preset-only change even without a large metric gain.

After `calibration-v1`, use `calibration-v2` to test the next permissive
parameters:

```powershell
uv run python scripts\validation_harness.py `
  --suite manual-2raw `
  --grid calibration-v2 `
  --run-id local_minimum_calibration_v2 `
  --output-root output\validation_harness
```

`calibration-v2` focuses on `resolver_peak_duration_min` and
`resolver_min_relative_height`. The manual 2-raw tier is pure standard material:
it is the first gate for integration behavior. Within that tier, NoSplit STD
has higher decision weight than Split STD because its acquisition method is
closer to the real tissue samples when matrix effects are ignored. Tissue 8-raw
is the next real-sample smoke test. Urine and other complex matrices are later
robustness stress tests, not the source of the first clean-model preset.

The first `calibration-v2` run found that positive
`resolver_min_relative_height` values improved NoSplit STD area agreement, but
also narrowed tissue candidate regions enough to flip candidate-aligned MS2/NL
status for several 5-medC rows. Treat this as evidence to review the boundary
and MS2 alignment contract before changing the preset.

## Inspect Exact Commands

Dry-run prints the exact commands without touching RAW files:

```powershell
uv run python scripts\validation_harness.py `
  --suite all `
  --dry-run `
  --confirm-full-run `
  --run-id method_dev `
  --output-root output\validation_harness
```

## Baseline Compare

Create a baseline run once:

```powershell
uv run python scripts\validation_harness.py `
  --suite tissue-8raw `
  --run-id current `
  --output-root output\validation_baselines
```

Compare a later run against that baseline by keeping the same `run-id` and
pointing `--baseline-root` at the baseline root:

```powershell
uv run python scripts\validation_harness.py `
  --suite tissue-8raw `
  --run-id current `
  --output-root output\validation_harness `
  --baseline-root output\validation_baselines
```

The compare target is exact:

```text
output\validation_baselines\<run-id>\tissue_8raw_<resolver>\xic_results_process_w4.xlsx
```

Workbook comparison uses `scripts\compare_workbooks.py`, which ignores runtime
metadata such as timestamps and output paths but compares analytical workbook
sheets.

## Full 85-raw Gate

The full run is intentionally opt-in:

```powershell
uv run python scripts\validation_harness.py `
  --suite tissue-85raw `
  --confirm-full-run `
  --run-id full_tissue_gate `
  --output-root output\validation_harness
```

Do not use the 85-raw suite for routine PR checks. Use it for release gates,
major scoring/resolver changes, or when the 8-raw subset shows a result that
needs cohort-level confirmation.
