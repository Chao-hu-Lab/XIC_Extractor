# Local Minimum Parameter Optimization — Spec

**Date:** 2026-05-04
**Status:** Draft
**Implementation plan:** `docs/superpowers/plans/2026-05-04-local-minimum-parameter-optimization.md`

---

## 1. Background

XIC Extractor now exposes two resolver profiles:

| Resolver | Status | Purpose |
|---|---|---|
| `legacy_savgol` | Default | Current trusted production path; closest to prior manual integration behavior. |
| `local_minimum` | Opt-in | Candidate method for low-abundance, complex-matrix samples. |

The GUI can switch methods, but the shipped `local_minimum` preset is still preliminary. The previous defaults were developed against the legacy Savitzky-Golay path, so direct reuse is not a reliable parameter choice for local-minimum integration.

The immediate goal is not to rewrite the peak algorithm again. The goal is to build a reproducible truth-aware parameter sweep that compares local-minimum settings against the manual integration workbook the user trusts:

`C:\Xcalibur\data\20251219_need process data\XIC test\20260112 UPLC splitting_forXIC.xlsx`

This workbook contains two manually reviewed standard runs:

| Raw file | Target file |
|---|---|
| `20251219_HESI_NoSplit_25ppb_ISTDs-1_60min_1_02.raw` | `combined_targets_file1.csv` |
| `20260104_Split_NSI_w-75um-50cm_25ppb_ISTDs-1_60min_1_02.raw` | `combined_targets_file2.csv` |

The workbook has `DNA` and `RNA` sheets. Each sheet stores manual `RT`, `Peak height`, `Peak area`, `Peak width`, and `Shape` for both raw files.

## 2. Goals

1. Parse the manual integration workbook into a stable truth table.
2. Run `legacy_savgol` and multiple `local_minimum` parameter sets on the same two raw files.
3. Score each run against manual truth using peak area as the primary metric.
4. Produce a human-readable Excel report for parameter comparison.
5. Recommend a local-minimum preset only when it beats the current preset without violating RT/missing-peak guardrails.
6. Keep `legacy_savgol` as default unless a later full validation explicitly justifies changing it.

## 3. Non-Goals

- Do not change peak picking algorithm internals in this stage.
- Do not change output workbook schema.
- Do not switch default resolver.
- Do not tune target-specific exceptions.
- Do not use `manual_ground_truth_DNA.csv` or `manual_ground_truth_RNA.csv`; the Excel workbook is the truth source for this stage.
- Do not run the full 85-raw tissue batch for every sweep.

## 4. Truth Data Contract

### 4.1 Workbook layout

The parser must support the current manual workbook layout:

- Sheet names: `DNA`, `RNA`
- Row 1:
  - columns A-C: metadata
  - first raw stem at column D
  - second raw stem at column I
- Row 2:
  - repeated metric headers: `RT\n(min)`, `Peak height`, `Peak area`, `Peak width\n(min)`, `Shape`
- Rows 3+:
  - `Name` column contains target label
  - each raw block contains the manual metrics

### 4.2 Parsed row shape

Each parsed truth row represents one sample-target observation:

| Field | Meaning |
|---|---|
| `sheet` | `DNA` or `RNA` |
| `sample_name` | raw stem without `.raw` |
| `target` | manual target name |
| `manual_rt` | manual RT in minutes, nullable |
| `manual_height` | manual peak height, nullable |
| `manual_area` | manual peak area, nullable |
| `manual_width` | manual width in minutes, nullable |
| `manual_shape` | manual shape label, e.g. `正常`, `拖尾` |

Rows with no manual RT and no manual area are ignored for scoring.

## 5. Parameter Sweep Contract

### 5.1 Compared methods

Every sweep includes:

1. `legacy_savgol` baseline with current canonical settings.
2. Current `local_minimum` preset.
3. Candidate `local_minimum` parameter sets.

The candidate grid should stay small enough to run on the two raw files during development. A recommended initial grid:

| Key | Values |
|---|---|
| `resolver_chrom_threshold` | `0.03`, `0.05`, `0.08` |
| `resolver_min_search_range_min` | `0.05`, `0.08`, `0.12` |
| `resolver_min_ratio_top_edge` | `1.3`, `1.5`, `1.7`, `2.0` |
| `resolver_min_scans` | `3`, `5` |
| `resolver_peak_duration_min` | `0.0` |
| `resolver_peak_duration_max` | `2.0` |
| `resolver_min_relative_height` | `0.0` |
| `resolver_min_absolute_height` | `25.0` |

This is 72 local-minimum combinations plus baselines. If runtime is too high, the script should allow a named quick grid.

For preset calibration v1, the sweep also exposes a focused `calibration-v1`
grid. This grid is intentionally smaller than `standard` and targets the two
highest-risk preset questions identified after the first real-data checks:

| Question | Starting value | Candidate values |
|---|---:|---|
| Maximum local-minimum region duration | `10.0` min | `1.5`, `2.0`, `3.0` min |
| Minimum valley search range | `0.08` min | `0.04`, `0.05` min |

The focused grid may combine these with the current edge-ratio setting and one
moderately relaxed edge-ratio candidate. Calibration v1 found no observed
manual-truth cost for shrinking the duration cap, so the shipped preset uses
`resolver_peak_duration_max=2.0`. Search-range remains `0.08` because the
`0.04-0.05` candidates increased large area misses.

Preset calibration v2 tests the next permissive parameters after the duration
cap:

| Question | Starting value | Candidate values |
|---|---:|---|
| Minimum local-minimum region duration | `0.0` min | `0.02`, `0.03` min |
| Minimum relative apex height | `0.0` | `0.01`, `0.02`, `0.03` |

The data hierarchy matters for decisions:

1. The two manual-truth RAW files are pure standard material. They are the
   first gate for area/RT behavior. The NoSplit STD method is closer to the
   real tissue method when matrix effects are ignored, so NoSplit evidence has
   higher decision weight than the Split method-development run.
2. The 8-raw tissue subset is the daily real-sample smoke test across selected
   tissue groups.
3. The 85-raw tissue run is the full release gate for the same tissue batch.
4. Urine and other complex matrices are robustness stress tests after the clean
    standard/tissue model is stable; they should not drive the first preset.

Calibration v2 result:

- `resolver_peak_duration_min=0.02-0.03` had no meaningful effect on the
  two-raw manual truth sweep.
- `resolver_min_relative_height=0.01-0.03` improved pure STD area agreement,
  especially for NoSplit STD, but all tested positive values narrowed selected
  tissue peak regions enough to change candidate-aligned MS2/NL status for
  several 5-medC rows without moving the apex. Keep the shipped preset at
  `resolver_min_relative_height=0.0` until the boundary/MS2 alignment contract
  is reviewed.

### 5.2 Case execution

The two raw files require different target CSVs because their methods have different RT windows. The sweep must stage and run each case separately:

| Case | Data dir | Target CSV |
|---|---|---|
| `nosplit` | temp folder containing the NoSplit raw only | `combined_targets_file1.csv` |
| `split` | temp folder containing the Split raw only | `combined_targets_file2.csv` |

The runner must not mutate repo `config/settings.example.csv` or tracked target examples.

## 6. Scoring Contract

### 6.1 Primary metric

The primary score is peak area agreement:

```text
area_abs_pct_error = abs(program_area - manual_area) / manual_area
```

The main ranking metric is:

```text
area_median_abs_pct_error
```

Only rows with `manual_area > 0` and a detected program peak contribute to the median. Missing peaks are counted separately and used as a guardrail.

### 6.2 Guardrails

A candidate preset is not acceptable if it violates any of these guardrails compared with the current local-minimum preset:

| Guardrail | Rule |
|---|---|
| Missing peaks | Must not increase missing manual peaks. |
| RT drift | `rt_median_abs_delta_min <= 0.05` and `rt_max_abs_delta_min <= 0.20` on detected manual rows. |
| Large area misses | Count of rows with `area_abs_pct_error > 0.20` must not increase. |
| ISTD misses | Must not lose ISTD peaks present in manual truth. |

These thresholds are development gates, not clinical or production acceptance limits. They exist to prevent picking a parameter set that improves the median by sacrificing obvious peaks.

### 6.3 Secondary metrics

The report should include:

- `area_within_10pct`
- `area_within_20pct`
- `height_median_abs_pct_error`
- `rt_median_abs_delta_min`
- `rt_max_abs_delta_min`
- `missing_manual_peaks`
- `detected_rows`
- `scored_rows`

`Peak width` is informational only. The user has stated manual width has high subjective error, so it must not be used as a hard gate.

## 7. Report Contract

The sweep writes an Excel workbook under:

`output/local_minimum_param_sweep_<timestamp>/local_minimum_param_sweep_summary.xlsx`

Required sheets:

| Sheet | Purpose |
|---|---|
| `Summary` | One row per method/parameter set with ranking metrics and guardrail status. |
| `PerTarget` | One row per method/sample/target with manual and program RT/height/area/width plus errors. |
| `Failures` | Rows that violate missing peak, RT, or area guardrails. |
| `RunConfig` | Parameter set definitions and source file paths. |

The workbook should be readable in Excel and use the repo's existing plain report style where practical.

## 8. Acceptance Criteria

This stage is complete when:

1. The manual workbook parser has unit tests for the two-block DNA/RNA layout.
2. Metric calculation has unit tests for area MAPE, missing peaks, RT guardrails, and ISTD misses.
3. The sweep runner has unit tests using a fake extraction runner, so CI does not require Thermo RAW files.
4. A real-data sweep has been run on the two manual raw files.
5. The generated summary workbook path is reported to the user.
6. Any proposed preset change is backed by the summary workbook, not by visual inspection alone.
7. `legacy_savgol` remains default unless a later full validation stage says otherwise.

## 9. Decision Gate

After the two-raw manual sweep:

- If no local-minimum candidate beats the current preset on `area_median_abs_pct_error` without guardrail failures, keep the current local-minimum preset.
- If one candidate clearly beats the current preset and passes guardrails, update only the local-minimum preset values and docs.
- If a candidate is equivalent on clean-matrix manual truth and improves parameter semantics or removes an overly broad placeholder value, a preset-only update is allowed when it does not increase missing peaks or large area misses.
- If results are mixed, do not update defaults; keep the sweep report as evidence and run the 8-raw validation subset before making a preset decision.

The 8-raw validation subset is:

`C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation`

Full 85-raw validation is deferred until a candidate shows real improvement on both the manual standard runs and the 8-raw subset.
