# Local Minimum Parameter Optimization Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task.

**Goal:** Build a reproducible truth-aware parameter sweep for `local_minimum` and use it to decide whether the local-minimum preset should change.

**Architecture:** Add a developer script that parses the manual integration workbook, stages each raw/target-file case in an isolated temp config, runs baseline and candidate resolver settings through the existing extractor, computes truth metrics, and writes an Excel summary. Keep algorithm behavior and output schema unchanged unless the sweep evidence justifies a later preset-only update.

**Tech Stack:** Python 3.13, `openpyxl`, `pytest`, `uv`, existing `xic_extractor.config`, `xic_extractor.extractor`, and `xic_extractor.output` patterns.

**Spec:** `docs/superpowers/specs/2026-05-04-local-minimum-parameter-optimization-spec.md`

---

## Execution Rules

1. Use TDD for every code behavior.
2. Do not change resolver internals in this plan.
3. Do not change workbook output schema.
4. Do not switch default resolver.
5. Do not mutate tracked `config/settings.example.csv` or `config/targets.example.csv` during sweep runs.
6. Unit tests must not require Thermo RAW files.
7. Real-data sweep is a final manual validation step and may require local machine access.
8. Commit after each completed task.

---

## Phase 1 — Manual Truth Workbook Parser

### Task 1.1 — RED: parse two-block manual workbook rows

**Files:**

- Create: `tests/test_local_minimum_param_sweep.py`
- Create: `scripts/local_minimum_param_sweep.py`

**Step 1: Write failing test**

Create a small in-memory workbook fixture with `DNA` and `RNA` sheets:

```python
from pathlib import Path

from openpyxl import Workbook

from scripts.local_minimum_param_sweep import read_manual_truth


def test_read_manual_truth_parses_dna_rna_two_raw_blocks(tmp_path: Path) -> None:
    workbook = tmp_path / "manual.xlsx"
    wb = Workbook()
    header_1 = [
        "No.",
        "Name",
        "m/z",
        "NoSplit",
        None,
        None,
        None,
        None,
        "Split",
        None,
        None,
        None,
        None,
    ]
    header_2 = [
        None,
        None,
        None,
        "RT\n(min)",
        "Peak height",
        "Peak area",
        "Peak width\n(min)",
        "Shape",
        "RT\n(min)",
        "Peak height",
        "Peak area",
        "Peak width\n(min)",
        "Shape",
    ]
    ws = wb.active
    ws.title = "DNA"
    ws.append(header_1)
    ws.append(header_2)
    ws.append([1, "5-hmdC", 258.1085, 8.55, 3430000, 67300000, 1.0, "正常", 9.05, 85900, 2270000, 0.95, "正常"])
    ws_rna = wb.create_sheet("RNA")
    ws_rna.append(header_1)
    ws_rna.append(header_2)
    ws_rna.append([1, "m6A", 282.1197, 24.8, 1000, 20000, 0.8, "正常", None, None, None, None, None])
    wb.save(workbook)

    rows = read_manual_truth(workbook)

    assert [(row.sheet, row.sample_name, row.target) for row in rows] == [
        ("DNA", "NoSplit", "5-hmdC"),
        ("DNA", "Split", "5-hmdC"),
        ("RNA", "NoSplit", "m6A"),
    ]
    assert rows[0].manual_rt == 8.55
    assert rows[0].manual_area == 67300000
    assert rows[1].manual_width == 0.95
    assert rows[2].manual_shape == "正常"
```

**Step 2: Run failing test**

```powershell
uv run pytest tests\test_local_minimum_param_sweep.py::test_read_manual_truth_parses_dna_rna_two_raw_blocks -v
```

Expected: FAIL because `scripts.local_minimum_param_sweep` does not exist.

### Task 1.2 — GREEN: implement parser

**Files:**

- Create: `scripts/local_minimum_param_sweep.py`

**Implementation:**

Add:

- `ManualTruthRow` dataclass
- `read_manual_truth(path: Path) -> list[ManualTruthRow]`
- `_iter_raw_blocks(ws) -> list[tuple[str, int]]`
- `_safe_float(value) -> float | None`

Rules:

- Read with `openpyxl.load_workbook(read_only=True, data_only=True)`.
- Parse only `DNA` and `RNA` sheets.
- Identify raw blocks by non-empty row-1 cells from column D onward.
- Each block is five columns wide.
- Skip rows where both manual RT and manual area are missing.

**Step 4: Run test**

```powershell
uv run pytest tests\test_local_minimum_param_sweep.py -v
```

Expected: PASS.

**Commit:**

```powershell
git add scripts/local_minimum_param_sweep.py tests/test_local_minimum_param_sweep.py
git commit -m "test: parse manual integration truth workbook"
```

---

## Phase 2 — Truth Metric Calculation

### Task 2.1 — RED: compute area and RT metrics

**Files:**

- Modify: `tests/test_local_minimum_param_sweep.py`
- Modify: `scripts/local_minimum_param_sweep.py`

**Step 1: Write failing test**

Add:

```python
from scripts.local_minimum_param_sweep import (
    ManualTruthRow,
    ProgramPeakRow,
    score_parameter_set,
)


def test_score_parameter_set_ranks_by_area_mape_and_tracks_guardrails() -> None:
    truth = [
        ManualTruthRow("DNA", "SampleA", "ISTD", 10.0, 1000.0, 10000.0, 0.8, "正常"),
        ManualTruthRow("DNA", "SampleA", "Analyte", 11.0, 2000.0, 20000.0, 1.0, "正常"),
        ManualTruthRow("DNA", "SampleA", "Missing", 12.0, 3000.0, 30000.0, 1.0, "正常"),
    ]
    peaks = [
        ProgramPeakRow("SampleA", "ISTD", True, 10.02, 900.0, 9000.0, True),
        ProgramPeakRow("SampleA", "Analyte", False, 11.10, 2300.0, 26000.0, False),
    ]

    score = score_parameter_set("candidate", {}, truth, peaks)

    assert score.area_median_abs_pct_error == 0.2
    assert score.area_within_10pct == 1
    assert score.area_within_20pct == 1
    assert score.missing_manual_peaks == 1
    assert score.istd_misses == 0
    assert score.rt_median_abs_delta_min == 0.06
    assert score.rt_max_abs_delta_min == 0.10
    assert score.large_area_misses == 1
```

**Step 2: Run failing test**

```powershell
uv run pytest tests\test_local_minimum_param_sweep.py::test_score_parameter_set_ranks_by_area_mape_and_tracks_guardrails -v
```

Expected: FAIL because scoring objects/functions do not exist.

### Task 2.2 — GREEN: implement scoring

**Files:**

- Modify: `scripts/local_minimum_param_sweep.py`

**Implementation:**

Add:

- `ProgramPeakRow`
- `ParameterSetScore`
- `PerTargetScoreRow`
- `score_parameter_set(name, params, truth_rows, program_rows)`

Metrics:

- `area_abs_pct_error`
- `height_abs_pct_error`
- `rt_abs_delta_min`
- `area_median_abs_pct_error`
- `height_median_abs_pct_error`
- `area_within_10pct`
- `area_within_20pct`
- `large_area_misses`
- `missing_manual_peaks`
- `istd_misses`

Use `statistics.median` and round summary metrics to stable precision.

**Step 4: Run test**

```powershell
uv run pytest tests\test_local_minimum_param_sweep.py -v
```

Expected: PASS.

**Commit:**

```powershell
git add scripts/local_minimum_param_sweep.py tests/test_local_minimum_param_sweep.py
git commit -m "feat: score local minimum sweep against manual truth"
```

---

## Phase 3 — Parameter Grid And Fake Runner

### Task 3.1 — RED: build compact parameter grid

**Files:**

- Modify: `tests/test_local_minimum_param_sweep.py`
- Modify: `scripts/local_minimum_param_sweep.py`

**Step 1: Write failing test**

Add:

```python
from scripts.local_minimum_param_sweep import build_parameter_sets


def test_build_parameter_sets_includes_legacy_current_and_candidate_grid() -> None:
    sets = build_parameter_sets(grid="quick")

    names = [item.name for item in sets]
    assert names[0] == "legacy_savgol"
    assert names[1] == "local_minimum_current"
    assert any(name.startswith("local_minimum_grid_") for name in names)
    assert sets[0].settings_overrides["resolver_mode"] == "legacy_savgol"
    assert sets[1].settings_overrides["resolver_mode"] == "local_minimum"
```

**Step 2: Run failing test**

```powershell
uv run pytest tests\test_local_minimum_param_sweep.py::test_build_parameter_sets_includes_legacy_current_and_candidate_grid -v
```

Expected: FAIL because `build_parameter_sets` does not exist.

### Task 3.2 — GREEN: implement parameter sets

**Files:**

- Modify: `scripts/local_minimum_param_sweep.py`

**Implementation:**

Add:

- `ParameterSet` dataclass with `name` and `settings_overrides`
- `build_parameter_sets(grid: str) -> list[ParameterSet]`

Supported grids:

- `quick`: small deterministic grid for development and tests
- `standard`: spec grid
- `calibration-v1`: focused preset-calibration grid for
  `resolver_peak_duration_max` and `resolver_min_search_range_min`

**Step 4: Run test**

```powershell
uv run pytest tests\test_local_minimum_param_sweep.py -v
```

Expected: PASS.

**Commit:**

```powershell
git add scripts/local_minimum_param_sweep.py tests/test_local_minimum_param_sweep.py
git commit -m "feat: define local minimum parameter sweep grid"
```

---

## Phase 4 — Sweep Orchestration Without RAW Dependency

### Task 4.1 — RED: fake runner produces scored sweep result

**Files:**

- Modify: `tests/test_local_minimum_param_sweep.py`
- Modify: `scripts/local_minimum_param_sweep.py`

**Step 1: Write failing test**

Add:

```python
from scripts.local_minimum_param_sweep import ParameterSet, run_sweep


def test_run_sweep_scores_each_parameter_set_with_injected_runner() -> None:
    truth = [
        ManualTruthRow("DNA", "SampleA", "TargetA", 10.0, 1000.0, 10000.0, 1.0, "正常")
    ]
    parameter_sets = [
        ParameterSet("legacy_savgol", {"resolver_mode": "legacy_savgol"}),
        ParameterSet("local_minimum_current", {"resolver_mode": "local_minimum"}),
    ]

    def fake_runner(parameter_set):
        area = 10000.0 if parameter_set.name == "legacy_savgol" else 12000.0
        return [ProgramPeakRow("SampleA", "TargetA", False, 10.01, 1000.0, area, False)]

    result = run_sweep(truth, parameter_sets, fake_runner)

    assert [score.name for score in result.scores] == [
        "legacy_savgol",
        "local_minimum_current",
    ]
    assert result.scores[0].area_median_abs_pct_error == 0.0
    assert result.scores[1].area_median_abs_pct_error == 0.2
```

**Step 2: Run failing test**

```powershell
uv run pytest tests\test_local_minimum_param_sweep.py::test_run_sweep_scores_each_parameter_set_with_injected_runner -v
```

Expected: FAIL because `run_sweep` does not exist.

### Task 4.2 — GREEN: implement orchestrator core

**Files:**

- Modify: `scripts/local_minimum_param_sweep.py`

**Implementation:**

Add:

- `SweepResult` dataclass
- `run_sweep(truth_rows, parameter_sets, runner)`

This layer must know nothing about Thermo RAW files. It only calls an injected runner and scores returned `ProgramPeakRow` values.

**Step 4: Run test**

```powershell
uv run pytest tests\test_local_minimum_param_sweep.py -v
```

Expected: PASS.

**Commit:**

```powershell
git add scripts/local_minimum_param_sweep.py tests/test_local_minimum_param_sweep.py
git commit -m "feat: orchestrate local minimum parameter sweep"
```

---

## Phase 5 — Excel Report Writer

### Task 5.1 — RED: write report workbook sheets

**Files:**

- Modify: `tests/test_local_minimum_param_sweep.py`
- Modify: `scripts/local_minimum_param_sweep.py`

**Step 1: Write failing test**

Add:

```python
from openpyxl import load_workbook

from scripts.local_minimum_param_sweep import write_sweep_workbook


def test_write_sweep_workbook_contains_required_sheets(tmp_path: Path) -> None:
    truth = [
        ManualTruthRow("DNA", "SampleA", "TargetA", 10.0, 1000.0, 10000.0, 1.0, "正常")
    ]
    peaks = [ProgramPeakRow("SampleA", "TargetA", False, 10.01, 1000.0, 10000.0, False)]
    score = score_parameter_set("legacy_savgol", {"resolver_mode": "legacy_savgol"}, truth, peaks)
    output = tmp_path / "summary.xlsx"

    write_sweep_workbook(output, [score])

    wb = load_workbook(output, read_only=True, data_only=True)
    assert wb.sheetnames == ["Summary", "PerTarget", "Failures", "RunConfig"]
    assert wb["Summary"]["A1"].value == "Rank"
```

**Step 2: Run failing test**

```powershell
uv run pytest tests\test_local_minimum_param_sweep.py::test_write_sweep_workbook_contains_required_sheets -v
```

Expected: FAIL because writer does not exist.

### Task 5.2 — GREEN: implement workbook writer

**Files:**

- Modify: `scripts/local_minimum_param_sweep.py`

**Implementation:**

Use `openpyxl` and existing simple report conventions:

- Arial font
- frozen headers
- autosized columns
- `Summary`, `PerTarget`, `Failures`, `RunConfig`

Sort Summary by:

1. guardrail pass before fail
2. `missing_manual_peaks`
3. `area_median_abs_pct_error`
4. `rt_median_abs_delta_min`

**Step 4: Run test**

```powershell
uv run pytest tests\test_local_minimum_param_sweep.py -v
```

Expected: PASS.

**Commit:**

```powershell
git add scripts/local_minimum_param_sweep.py tests/test_local_minimum_param_sweep.py
git commit -m "feat: write local minimum sweep workbook"
```

---

## Phase 6 — Real Extractor Runner And CLI

### Task 6.1 — RED: CLI wires arguments without running real RAW in tests

**Files:**

- Modify: `tests/test_local_minimum_param_sweep.py`
- Modify: `scripts/local_minimum_param_sweep.py`

**Step 1: Write failing test**

Use monkeypatch to replace the real extraction runner and assert:

- `--manual-workbook`
- `--nosplit-raw`
- `--split-raw`
- `--nosplit-targets`
- `--split-targets`
- `--output-dir`
- `--grid quick`

produce a workbook.

**Step 2: Run failing test**

```powershell
uv run pytest tests\test_local_minimum_param_sweep.py::test_main_writes_workbook_with_injected_runner -v
```

Expected: FAIL until CLI exists.

### Task 6.2 — GREEN: implement real runner and CLI

**Files:**

- Modify: `scripts/local_minimum_param_sweep.py`

**Implementation:**

Add CLI:

```powershell
uv run python scripts\local_minimum_param_sweep.py `
  --manual-workbook "C:\Xcalibur\data\20251219_need process data\XIC test\20260112 UPLC splitting_forXIC.xlsx" `
  --nosplit-raw "C:\Xcalibur\data\20251219_need process data\XIC test\20251219_HESI_NoSplit_25ppb_ISTDs-1_60min_1_02.raw" `
  --split-raw "C:\Xcalibur\data\20251219_need process data\XIC test\20260104_Split_NSI_w-75um-50cm_25ppb_ISTDs-1_60min_1_02.raw" `
  --nosplit-targets "C:\Xcalibur\data\20251219_need process data\XIC test\combined_targets_file1.csv" `
  --split-targets "C:\Xcalibur\data\20251219_need process data\XIC test\combined_targets_file2.csv" `
  --output-dir output\local_minimum_param_sweep_manual `
  --grid calibration-v1 `
  --parallel-mode process `
  --parallel-workers 4
```

Real runner responsibilities:

1. Create a temp run directory under the selected output directory.
2. Copy or stage one raw per case.
3. Write a temporary `config/settings.csv` from canonical defaults with:
   - `data_dir`
   - `dll_dir`
   - parameter set overrides
4. Copy the case-specific target CSV to `config/targets.csv`.
5. Call `load_config(temp_config_dir, settings_overrides=...)` or write full temp config, whichever preserves config hash behavior best.
6. Call `extractor.run(config, targets)`.
7. Convert `RunOutput` to `ProgramPeakRow`.

**Step 4: Run tests**

```powershell
uv run pytest tests\test_local_minimum_param_sweep.py -v
```

Expected: PASS.

**Commit:**

```powershell
git add scripts/local_minimum_param_sweep.py tests/test_local_minimum_param_sweep.py
git commit -m "feat: add local minimum parameter sweep CLI"
```

---

## Phase 7 — Real-Data Sweep Checkpoint

### Task 7.1 — Run quick grid on manual truth files

**Command:**

```powershell
uv run python scripts\local_minimum_param_sweep.py `
  --manual-workbook "C:\Xcalibur\data\20251219_need process data\XIC test\20260112 UPLC splitting_forXIC.xlsx" `
  --nosplit-raw "C:\Xcalibur\data\20251219_need process data\XIC test\20251219_HESI_NoSplit_25ppb_ISTDs-1_60min_1_02.raw" `
  --split-raw "C:\Xcalibur\data\20251219_need process data\XIC test\20260104_Split_NSI_w-75um-50cm_25ppb_ISTDs-1_60min_1_02.raw" `
  --nosplit-targets "C:\Xcalibur\data\20251219_need process data\XIC test\combined_targets_file1.csv" `
  --split-targets "C:\Xcalibur\data\20251219_need process data\XIC test\combined_targets_file2.csv" `
  --output-dir output\local_minimum_param_sweep_manual `
  --grid quick
```

Expected:

- workbook path printed
- `Summary` sheet ranks all quick parameter sets
- no unhandled RAW/config errors

### Task 7.2 — Decide whether standard grid is justified

If quick grid shows a plausible candidate:

```powershell
uv run python scripts\local_minimum_param_sweep.py ... --grid standard
```

If `calibration-v1` does not improve current local-minimum preset, stop and
report that evidence. Use `standard` only when the focused grid produces a
plausible candidate but leaves the exact setting ambiguous.

### Task 7.3 — Report checkpoint

Report:

- summary workbook path
- best candidate by area median absolute percent error
- whether guardrails passed
- comparison against `legacy_savgol`
- whether a preset change is justified

No code or default-setting changes in this task unless explicitly confirmed after reviewing the sweep evidence.

---

## Phase 8 — Optional Preset Update

Only enter this phase if the user confirms a candidate preset.

### Task 8.1 — RED: update canonical preset expectations

**Files:**

- Modify: `tests/test_config.py`
- Modify: `tests/test_settings_section_advanced.py`

Write tests asserting the new confirmed local-minimum preset values.

### Task 8.2 — GREEN: update preset/default docs

**Files:**

- Modify: `xic_extractor/settings_schema.py`
- Modify: `config/settings.example.csv`
- Modify: `gui/sections/settings_section.py`
- Modify: `README.md`
- Modify: `docs/superpowers/specs/2026-05-04-resolver-profile-gui-spec.md`

Keep:

- `resolver_mode=legacy_savgol`

Update only local-minimum parameter values.

**Verification:**

```powershell
uv run pytest tests\test_config.py tests\test_settings_section_advanced.py -v
uv run pytest --tb=short -q
```

**Commit:**

```powershell
git add xic_extractor/settings_schema.py config/settings.example.csv gui/sections/settings_section.py README.md docs/superpowers/specs/2026-05-04-resolver-profile-gui-spec.md tests/test_config.py tests/test_settings_section_advanced.py
git commit -m "feat(config): update local minimum preset from manual sweep"
```
