# Excel Review UX Redesign Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Turn the Excel workbook from a technically complete output dump into a clear review workflow where users can open one sheet, see batch health, and know which peaks need manual inspection first.

**Architecture:** Keep extraction, scoring, CSV schema, and existing analytical values unchanged. Rework only workbook presentation in `scripts/csv_to_excel.py` and `xic_extractor/output/excel_pipeline.py` by adding an active `Overview` sheet, simplifying `Review Queue`, improving target-level summary metrics, and visually separating daily review sheets from technical/debug sheets.

**Tech Stack:** Python 3.13, openpyxl, pytest, existing `uv run pytest` workflow, PowerShell on Windows.

---

## Background

The current workbook is complete but still not friendly enough for daily manual review:

- `XIC Results`, `Review Queue`, and `Diagnostics` all expose sample-target issues with similar table shapes.
- `Review Queue` is useful, but still reads like a filtered diagnostics table.
- `XIC Results` is still the active sheet, so users start in dense raw output rather than batch-level orientation.
- `Summary` is statistically useful but does not answer "which target needs review first?"
- Technical sheets are peer-level tabs even though they are not daily review surfaces.

The target experience:

```text
Open workbook
    |
    v
Overview
    |-- "Can I trust this batch?"
    |-- "Which targets/samples need attention?"
    |
    +--> Review Queue
    |       |-- manual peak review worklist
    |
    +--> XIC Results / Summary
    |       |-- full result lookup and target health
    |
    +--> Technical sheets
            |-- Diagnostics / Score Breakdown / Run Metadata / Targets
```

## Target Workbook Contract

Default workbook sheets:

```text
Overview
Review Queue
XIC Results
Summary
Targets
Diagnostics
Run Metadata
```

When `emit_score_breakdown=true`, append:

```text
Score Breakdown
```

`Overview` becomes the active sheet. `XIC Results` remains the complete row-based result table but is no longer the first thing users see.

## UX Contract

### Overview

Purpose: batch orientation.

Must answer:

- How many samples and targets were processed?
- How many review items exist?
- How many diagnostics were emitted?
- Which targets have the most review pressure?
- Which samples have the most review pressure?

No formulas in v1. Write fixed values from the same row data used by existing sheets.

### Review Queue

Purpose: manual review worklist.

One row per sample-target, not one row per diagnostic. Multiple diagnostics for the same sample-target are aggregated.

Columns:

```text
Priority
Sample
Target
Role
Status
Why
RT
Area
Action
Issue Count
Evidence
```

Reading rule:

- `Priority`: 1 first, 2 second, 3 optional.
- `Status`: short user-facing state, not raw internal issue.
- `Why`: short human-readable reason.
- `Evidence`: long diagnostic/scoring detail, placed last and optionally narrower/hidden only if Excel readability demands it.

### Summary

Keep the sheet name `Summary` to avoid unnecessary public surface churn, but change it toward target health.

Add these fields near the front:

```text
Review Items
Problem Rate
NL Problems
Low Confidence
```

Keep existing useful metrics such as detection count, median area, NL counts, RT delta, and confidence counts.

### Technical Sheets

Keep `Targets`, `Diagnostics`, `Run Metadata`, and optional `Score Breakdown`.

Use tab color and README copy to communicate role:

- `Overview`, `Review Queue`: daily review.
- `XIC Results`, `Summary`: result lookup / target health.
- `Targets`, `Diagnostics`, `Run Metadata`, `Score Breakdown`: technical traceability.

## NOT In Scope

- Peak selection, scoring, NL/MS2 evidence, and area integration changes.
- CSV schema changes.
- GUI changes.
- New config keys.
- Charts or formulas.
- Removing `Diagnostics` or `Score Breakdown`.
- Renaming `Summary` in this phase.

## What Already Exists

- `scripts/csv_to_excel.py`
  - Owns workbook construction from CSV files.
  - Already has sheet builders for `XIC Results`, `Summary`, `Review Queue`, `Targets`, `Diagnostics`, `Run Metadata`, and `Score Breakdown`.
  - Reuse this file. Do not create a parallel workbook writer.
- `xic_extractor/output/excel_pipeline.py`
  - Writes workbook directly from in-memory `RunOutput`.
  - Must call the same sheet builders as `scripts/csv_to_excel.py`.
- `tests/test_csv_to_excel.py`
  - Main unit tests for sheet builders.
- `tests/test_excel_pipeline.py`
  - Contract tests for in-memory workbook writing.
- `tests/test_excel_sheets_contract.py`
  - End-to-end sheet count/order/active sheet tests.
- `tests/test_workbook_compare.py`
  - Workbook A/B compare contract.
- `README.md`
  - Public workbook behavior documentation.

## Implementation Notes

Use these helper shapes unless the existing code suggests a cleaner local pattern:

```python
_OVERVIEW_HEADER_FILL = "1F4E5F"
_DAILY_REVIEW_TAB = "1F4E5F"
_RESULT_TAB = "5B7C99"
_TECHNICAL_TAB = "B0BEC5"

def _build_overview_sheet(
    ws,
    rows: list[dict[str, str]],
    diagnostics: list[dict[str, str]],
    review_rows: list[dict[str, str]],
) -> None:
    ...

def _review_queue_rows(
    rows: list[dict[str, str]],
    diagnostics: list[dict[str, str]],
) -> list[dict[str, str]]:
    ...

def _summary_row_values(
    target_row: dict[str, str],
    rows: list[dict[str, str]],
    count_no_ms2_as_detected: bool,
    review_rows_by_target: dict[str, list[dict[str, str]]],
) -> list[object]:
    ...
```

Avoid Excel formulas. Avoid adding dependencies. Keep `_excel_text()` sanitization for all user-controlled text fields.

---

## Task 1: Add Active Overview Sheet

**Files:**

- Modify: `scripts/csv_to_excel.py`
- Modify: `xic_extractor/output/excel_pipeline.py`
- Test: `tests/test_csv_to_excel.py`
- Test: `tests/test_excel_pipeline.py`
- Test: `tests/test_excel_sheets_contract.py`
- Test: `tests/test_workbook_compare.py`

**Step 1: Write failing tests**

Add to `tests/test_csv_to_excel.py`:

```python
def test_build_overview_sheet_summarizes_batch_review_health() -> None:
    rows = [
        _long_row("Tumor_1", "AnalyteA", "9.0", "10000", "OK"),
        _long_row(
            "Tumor_2",
            "AnalyteA",
            "ND",
            "ND",
            "NL_FAIL",
            confidence="VERY_LOW",
            reason="concerns: nl_support (major)",
        ),
        _long_row(
            "Tumor_2",
            "AnalyteB",
            "12.0",
            "20000",
            "NO_MS2",
            confidence="MEDIUM",
        ),
    ]
    diagnostics = [
        {
            "SampleName": "Tumor_2",
            "Target": "AnalyteA",
            "Issue": "NL_FAIL",
            "Reason": "strict observed neutral loss missing",
        }
    ]
    review_rows = _review_queue_rows(rows, diagnostics)
    wb = Workbook()
    ws = wb.active

    _build_overview_sheet(ws, rows, diagnostics, review_rows)

    assert ws.title == "Overview"
    assert ws["A1"].value == "XIC Review Overview"
    assert ws["A3"].value == "Samples"
    assert ws["B3"].value == 2
    assert ws["A5"].value == "Review Items"
    assert ws["B5"].value == 2
    assert "Top Targets" in [ws.cell(row=r, column=1).value for r in range(1, ws.max_row + 1)]
    assert "Top Samples" in [ws.cell(row=r, column=1).value for r in range(1, ws.max_row + 1)]
```

Update existing sheet contract tests:

```python
assert wb.sheetnames == [
    "Overview",
    "Review Queue",
    "XIC Results",
    "Summary",
    "Targets",
    "Diagnostics",
    "Run Metadata",
]
assert wb.active.title == "Overview"
```

Update `tests/test_workbook_compare.py` fixture sheet order to include `Overview`.

**Step 2: Run tests to verify failure**

```powershell
$env:UV_CACHE_DIR='C:\Users\user\Desktop\XIC_Extractor\.worktrees\local-minimum-param-optimization\.uv-cache'
uv run pytest tests\test_csv_to_excel.py::test_build_overview_sheet_summarizes_batch_review_health tests\test_excel_sheets_contract.py::test_landing_sheet_when_diagnostics_empty -v
```

Expected: FAIL because `_build_overview_sheet` does not exist and workbook active sheet is still `XIC Results`.

**Step 3: Implement minimal code**

In `scripts/csv_to_excel.py`:

- Add `_build_overview_sheet()`.
- In `_run_with_config()`, compute `review_rows = _review_queue_rows(rows, diagnostics)` once.
- Create sheets in this order:

```python
ws_overview = wb.active
ws_overview.title = "Overview"
_build_overview_sheet(ws_overview, rows, diagnostics, review_rows)

ws_review = wb.create_sheet("Review Queue")
_build_review_queue_sheet(ws_review, review_rows)

ws_data = wb.create_sheet("XIC Results")
_build_data_sheet(ws_data, rows)
```

In `xic_extractor/output/excel_pipeline.py`, mirror the same order and reuse the same sheet builders.

**Step 4: Run tests to verify pass**

```powershell
$env:UV_CACHE_DIR='C:\Users\user\Desktop\XIC_Extractor\.worktrees\local-minimum-param-optimization\.uv-cache'
uv run pytest tests\test_csv_to_excel.py tests\test_excel_pipeline.py tests\test_excel_sheets_contract.py tests\test_workbook_compare.py -v
```

Expected: PASS.

**Step 5: Commit**

```powershell
git add scripts\csv_to_excel.py xic_extractor\output\excel_pipeline.py tests\test_csv_to_excel.py tests\test_excel_pipeline.py tests\test_excel_sheets_contract.py tests\test_workbook_compare.py
git commit -m "feat: add Excel overview sheet"
```

---

## Task 2: Simplify Review Queue Into A Worklist

**Files:**

- Modify: `scripts/csv_to_excel.py`
- Modify: `xic_extractor/output/excel_pipeline.py` only if the builder signature changes
- Test: `tests/test_csv_to_excel.py`
- Test: `tests/test_excel_pipeline.py`

**Step 1: Write failing tests**

Replace or add a test in `tests/test_csv_to_excel.py`:

```python
def test_review_queue_aggregates_diagnostics_by_sample_target() -> None:
    rows = [
        _long_row(
            "Tumor_1",
            "Analyte",
            "9.0",
            "10000",
            "NL_FAIL",
            confidence="LOW",
            reason="concerns: nl_support (major); local_sn (minor)",
        )
    ]
    diagnostics = [
        {
            "SampleName": "Tumor_1",
            "Target": "Analyte",
            "Issue": "NL_FAIL",
            "Reason": "strict observed neutral loss missing",
        },
        {
            "SampleName": "Tumor_1",
            "Target": "Analyte",
            "Issue": "ANCHOR_MISMATCH",
            "Reason": "selected RT is far from anchor",
        },
    ]

    review_rows = _review_queue_rows(rows, diagnostics)

    assert len(review_rows) == 1
    assert review_rows[0]["Priority"] == "1"
    assert review_rows[0]["Sample"] == "Tumor_1"
    assert review_rows[0]["Target"] == "Analyte"
    assert review_rows[0]["Status"] == "Review"
    assert review_rows[0]["Why"] == "NL support failed"
    assert review_rows[0]["Action"] == "Check MS2 / NL evidence near selected RT"
    assert review_rows[0]["Issue Count"] == "2"
    assert "strict observed neutral loss missing" in review_rows[0]["Evidence"]
    assert "selected RT is far from anchor" in review_rows[0]["Evidence"]
```

Add sheet layout assertion:

```python
def test_review_queue_sheet_uses_worklist_columns() -> None:
    rows = [
        {
            "Priority": "1",
            "Sample": "Tumor_1",
            "Target": "Analyte",
            "Role": "Analyte",
            "Status": "Review",
            "Why": "NL support failed",
            "RT": "9.0",
            "Area": "10000",
            "Action": "Check MS2 / NL evidence near selected RT",
            "Issue Count": "2",
            "Evidence": "strict observed neutral loss missing",
        }
    ]
    wb = Workbook()
    ws = wb.active

    _build_review_queue_sheet(ws, rows)

    assert [ws.cell(row=1, column=i).value for i in range(1, ws.max_column + 1)] == [
        "Priority",
        "Sample",
        "Target",
        "Role",
        "Status",
        "Why",
        "RT",
        "Area",
        "Action",
        "Issue Count",
        "Evidence",
    ]
    assert ws["E2"].value == "Review"
    assert ws["F2"].value == "NL support failed"
```

**Step 2: Run tests to verify failure**

```powershell
$env:UV_CACHE_DIR='C:\Users\user\Desktop\XIC_Extractor\.worktrees\local-minimum-param-optimization\.uv-cache'
uv run pytest tests\test_csv_to_excel.py::test_review_queue_aggregates_diagnostics_by_sample_target tests\test_csv_to_excel.py::test_review_queue_sheet_uses_worklist_columns -v
```

Expected: FAIL because current review rows use `SampleName`, `Issue`, `Primary Concern`, `Suggested Action`, and `Detail`.

**Step 3: Implement minimal code**

Update `_REVIEW_HEADERS`:

```python
_REVIEW_HEADERS = [
    "Priority",
    "Sample",
    "Target",
    "Role",
    "Status",
    "Why",
    "RT",
    "Area",
    "Action",
    "Issue Count",
    "Evidence",
]
```

Refactor `_diagnostics_by_key()` into `_diagnostics_grouped_by_key()`:

```python
def _diagnostics_grouped_by_key(
    diagnostics: list[dict[str, str]],
) -> dict[tuple[str, str], list[dict[str, str]]]:
    grouped: dict[tuple[str, str], list[dict[str, str]]] = {}
    for row in diagnostics:
        key = (row.get("SampleName", ""), row.get("Target", ""))
        grouped.setdefault(key, []).append(row)
    return grouped
```

Add short status/why mapping:

```python
def _review_status(issue: str, confidence: str) -> str:
    if issue in {"NL_FAIL", "PEAK_NOT_FOUND", "NO_SIGNAL", "FILE_ERROR"}:
        return "Review"
    if issue in {"NO_MS2", "NL_WARN"} or confidence in {"LOW", "VERY_LOW"}:
        return "Check"
    return "Info"

def _review_why(issue: str, reason: str) -> str:
    if issue == "NL_FAIL":
        return "NL support failed"
    if issue == "NO_MS2":
        return "MS2 trigger missing"
    if issue == "NL_WARN":
        return "NL support is borderline"
    if issue in {"PEAK_NOT_FOUND", "NO_SIGNAL"}:
        return "Peak not found"
    parsed = _first_concern(reason)
    return parsed if parsed and parsed != "all checks passed" else issue
```

**Step 4: Run tests to verify pass**

```powershell
$env:UV_CACHE_DIR='C:\Users\user\Desktop\XIC_Extractor\.worktrees\local-minimum-param-optimization\.uv-cache'
uv run pytest tests\test_csv_to_excel.py tests\test_excel_pipeline.py -v
```

Expected: PASS.

**Step 5: Commit**

```powershell
git add scripts\csv_to_excel.py xic_extractor\output\excel_pipeline.py tests\test_csv_to_excel.py tests\test_excel_pipeline.py
git commit -m "refactor: simplify Excel review queue"
```

---

## Task 3: Add Target Health Metrics To Summary

**Files:**

- Modify: `scripts/csv_to_excel.py`
- Test: `tests/test_csv_to_excel.py`
- Test: `tests/test_output_columns.py` if it asserts summary columns

**Step 1: Write failing test**

Add to `tests/test_csv_to_excel.py`:

```python
def test_summary_sheet_includes_target_health_metrics() -> None:
    rows = [
        _long_row("Tumor_1", "Analyte", "9.0", "10000", "OK", confidence="HIGH"),
        _long_row("Tumor_2", "Analyte", "9.1", "11000", "NL_FAIL", confidence="LOW"),
        _long_row("Tumor_3", "Analyte", "9.2", "12000", "NO_MS2", confidence="MEDIUM"),
    ]
    diagnostics = [
        {
            "SampleName": "Tumor_2",
            "Target": "Analyte",
            "Issue": "NL_FAIL",
            "Reason": "strict observed neutral loss missing",
        }
    ]
    review_rows = _review_queue_rows(rows, diagnostics)
    wb = Workbook()
    ws = wb.active

    _build_summary_sheet(
        ws,
        rows,
        count_no_ms2_as_detected=False,
        review_rows=review_rows,
    )
    data = _summary_rows(ws)

    assert "Review Items" in data["headers"]
    assert "Problem Rate" in data["headers"]
    assert "NL Problems" in data["headers"]
    assert "Low Confidence" in data["headers"]
    assert data["Analyte"]["Review Items"] == 2
    assert data["Analyte"]["Problem Rate"] == "67%"
    assert data["Analyte"]["NL Problems"] == 2
    assert data["Analyte"]["Low Confidence"] == 1
```

**Step 2: Run test to verify failure**

```powershell
$env:UV_CACHE_DIR='C:\Users\user\Desktop\XIC_Extractor\.worktrees\local-minimum-param-optimization\.uv-cache'
uv run pytest tests\test_csv_to_excel.py::test_summary_sheet_includes_target_health_metrics -v
```

Expected: FAIL because `_build_summary_sheet()` does not accept `review_rows` and summary lacks target health columns.

**Step 3: Implement minimal code**

Update `_SUMMARY_HEADERS` to include the new metrics near the front:

```python
_SUMMARY_HEADERS = [
    "Target",
    "Role",
    "ISTD Pair",
    "Review Items",
    "Problem Rate",
    "NL Problems",
    "Low Confidence",
    "Detected",
    "Total",
    ...
]
```

Add helper:

```python
def _review_rows_by_target(
    review_rows: list[dict[str, str]],
) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in review_rows:
        grouped.setdefault(row.get("Target", ""), []).append(row)
    return grouped
```

Derive:

- `Review Items`: count review rows for target.
- `Problem Rate`: `Review Items / total sample rows`.
- `NL Problems`: rows whose NL token is `NL_FAIL`, `NO_MS2`, or `WARN_*`.
- `Low Confidence`: confidence `LOW` or `VERY_LOW`.

**Step 4: Run tests to verify pass**

```powershell
$env:UV_CACHE_DIR='C:\Users\user\Desktop\XIC_Extractor\.worktrees\local-minimum-param-optimization\.uv-cache'
uv run pytest tests\test_csv_to_excel.py tests\test_output_columns.py -v
```

Expected: PASS.

**Step 5: Commit**

```powershell
git add scripts\csv_to_excel.py tests\test_csv_to_excel.py tests\test_output_columns.py
git commit -m "feat: add target health metrics to Excel summary"
```

---

## Task 4: Add Sheet Role Styling And Technical Sheet Downgrade

**Files:**

- Modify: `scripts/csv_to_excel.py`
- Modify: `xic_extractor/output/excel_pipeline.py` only if helper is shared there
- Test: `tests/test_csv_to_excel.py`
- Test: `tests/test_excel_pipeline.py`

**Step 1: Write failing tests**

Add to `tests/test_csv_to_excel.py`:

```python
def test_workbook_sheet_tabs_signal_review_and_technical_roles(tmp_path: Path) -> None:
    config = _config(tmp_path, emit_score_breakdown=True)
    targets = [_target("Analyte")]
    config.output_csv.parent.mkdir(parents=True)
    _write_csv(
        config.output_csv.with_name("xic_results_long.csv"),
        [_long_row("Tumor_1", "Analyte", "ND", "ND", "NL_FAIL")],
    )
    _write_csv(
        config.output_csv.with_name("xic_score_breakdown.csv"),
        [{
            "SampleName": "Tumor_1",
            "Target": "Analyte",
            "symmetry": "0",
            "local_sn": "1",
            "nl_support": "2",
            "rt_prior": "0",
            "rt_centrality": "0",
            "noise_shape": "0",
            "peak_width": "0",
            "Quality Penalty": "0",
            "Quality Flags": "",
            "Total Severity": "3",
            "Confidence": "LOW",
            "Prior RT": "NA",
            "Prior Source": "",
        }],
    )
    _write_empty_diagnostics_csv(config.diagnostics_csv)

    excel_path = run(config, targets)

    wb = load_workbook(excel_path)
    assert wb["Overview"].sheet_properties.tabColor.rgb.endswith("1F4E5F")
    assert wb["Review Queue"].sheet_properties.tabColor.rgb.endswith("1F4E5F")
    assert wb["Diagnostics"].sheet_properties.tabColor.rgb.endswith("B0BEC5")
    assert wb["Score Breakdown"].sheet_properties.tabColor.rgb.endswith("B0BEC5")
```

**Step 2: Run test to verify failure**

```powershell
$env:UV_CACHE_DIR='C:\Users\user\Desktop\XIC_Extractor\.worktrees\local-minimum-param-optimization\.uv-cache'
uv run pytest tests\test_csv_to_excel.py::test_workbook_sheet_tabs_signal_review_and_technical_roles -v
```

Expected: FAIL because tab colors are not assigned.

**Step 3: Implement minimal code**

Add:

```python
def _apply_sheet_role_styles(wb: Workbook) -> None:
    role_colors = {
        "Overview": _DAILY_REVIEW_TAB,
        "Review Queue": _DAILY_REVIEW_TAB,
        "XIC Results": _RESULT_TAB,
        "Summary": _RESULT_TAB,
        "Targets": _TECHNICAL_TAB,
        "Diagnostics": _TECHNICAL_TAB,
        "Run Metadata": _TECHNICAL_TAB,
        "Score Breakdown": _TECHNICAL_TAB,
    }
    for name, color in role_colors.items():
        if name in wb.sheetnames:
            wb[name].sheet_properties.tabColor = color
```

Call `_apply_sheet_role_styles(wb)` before saving in both workbook paths.

**Step 4: Run tests to verify pass**

```powershell
$env:UV_CACHE_DIR='C:\Users\user\Desktop\XIC_Extractor\.worktrees\local-minimum-param-optimization\.uv-cache'
uv run pytest tests\test_csv_to_excel.py tests\test_excel_pipeline.py -v
```

Expected: PASS.

**Step 5: Commit**

```powershell
git add scripts\csv_to_excel.py xic_extractor\output\excel_pipeline.py tests\test_csv_to_excel.py tests\test_excel_pipeline.py
git commit -m "style: clarify Excel sheet roles"
```

---

## Task 5: Update Workbook Compare And Documentation

**Files:**

- Modify: `scripts/compare_workbooks.py`
- Modify: `README.md`
- Modify: `docs/superpowers/notes/2026-05-03-output-refactor-retrospective.md`
- Test: `tests/test_workbook_compare.py`

**Step 1: Write failing tests**

Update `tests/test_workbook_compare.py` to expect:

```python
sheet_order: tuple[str, ...] = (
    "Overview",
    "Review Queue",
    "XIC Results",
    "Summary",
    "Targets",
    "Diagnostics",
    "Run Metadata",
)
```

Add a compare test:

```python
def test_compare_workbooks_compares_overview_sheet(tmp_path: Path) -> None:
    left = tmp_path / "left.xlsx"
    right = tmp_path / "right.xlsx"
    _write_workbook(left, overview_review_items=1)
    _write_workbook(right, overview_review_items=2)

    result = compare_workbooks(left, right)

    assert not result.matched
    assert any("Overview" in diff for diff in result.differences)
```

**Step 2: Run tests to verify failure**

```powershell
$env:UV_CACHE_DIR='C:\Users\user\Desktop\XIC_Extractor\.worktrees\local-minimum-param-optimization\.uv-cache'
uv run pytest tests\test_workbook_compare.py -v
```

Expected: FAIL until `COMPARE_SHEETS` includes `Overview` and test fixtures are updated.

**Step 3: Implement minimal code/docs**

Update `scripts/compare_workbooks.py`:

```python
COMPARE_SHEETS = (
    "Overview",
    "Review Queue",
    "XIC Results",
    "Summary",
    "Targets",
    "Diagnostics",
    "Run Metadata",
)
```

Update README Excel workbook section:

- `Overview`: active landing sheet for batch health and review priorities.
- `Review Queue`: human worklist, one row per sample-target needing review.
- `XIC Results`: complete result lookup.
- `Summary`: target health and statistics.
- Technical sheets are traceability/debug.

Update retrospective sheet count:

```text
Default: 7 sheets
emit_score_breakdown=true: 8 sheets
```

**Step 4: Run tests/docs smoke**

```powershell
$env:UV_CACHE_DIR='C:\Users\user\Desktop\XIC_Extractor\.worktrees\local-minimum-param-optimization\.uv-cache'
uv run pytest tests\test_workbook_compare.py tests\test_excel_sheets_contract.py -v
rg -n "Overview|Review Queue|Score Breakdown|Default \\| 7" README.md docs\superpowers\notes\2026-05-03-output-refactor-retrospective.md
```

Expected: tests PASS, docs contain updated sheet contract.

**Step 5: Commit**

```powershell
git add scripts\compare_workbooks.py tests\test_workbook_compare.py tests\test_excel_sheets_contract.py README.md docs\superpowers\notes\2026-05-03-output-refactor-retrospective.md
git commit -m "docs: document Excel review workflow"
```

---

## Task 6: Real Workbook Validation

**Files:**

- No production code changes expected.
- Generated workbook under `output/excel_review_validation/`.

**Step 1: Run focused test suite**

```powershell
$env:UV_CACHE_DIR='C:\Users\user\Desktop\XIC_Extractor\.worktrees\local-minimum-param-optimization\.uv-cache'
uv run ruff check scripts\csv_to_excel.py xic_extractor\output\excel_pipeline.py tests\test_csv_to_excel.py tests\test_excel_pipeline.py tests\test_excel_sheets_contract.py tests\test_workbook_compare.py
uv run pytest tests\test_csv_to_excel.py tests\test_excel_pipeline.py tests\test_excel_sheets_contract.py tests\test_output_columns.py tests\test_workbook_compare.py -v
```

Expected: PASS.

**Step 2: Run full suite excluding known sandbox-only process spawn if needed**

```powershell
$env:UV_CACHE_DIR='C:\Users\user\Desktop\XIC_Extractor\.worktrees\local-minimum-param-optimization\.uv-cache'
uv run pytest --tb=short -q -k 'not process_pool_spawn_can_run_importable_no_raw_worker'
```

Expected: PASS. If full `uv run pytest --tb=short -q` is also run, the known Windows sandbox failure may remain:

```text
tests/test_parallel_execution.py::test_process_pool_spawn_can_run_importable_no_raw_worker
PermissionError: [WinError 5] 存取被拒
```

Do not hide this failure. Report it as sandbox-specific if reproduced.

**Step 3: Generate tissue 8-raw validation workbook**

Use the CLI file entry point, not `python -`, because Windows `process` spawn cannot use `<stdin>` as `__main__`.

```powershell
$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$base = Join-Path (Get-Location) "output\excel_review_validation\${stamp}_tissue8_base"
$configDir = Join-Path $base 'config'
New-Item -ItemType Directory -Force -Path $configDir | Out-Null
Copy-Item -Path config\targets.csv -Destination (Join-Path $configDir 'targets.csv') -Force
$settings = Import-Csv config\settings.csv
foreach ($row in $settings) {
    if ($row.key -eq 'data_dir') { $row.value = 'C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation' }
    if ($row.key -eq 'dll_dir') { $row.value = 'C:\Xcalibur\system\programs' }
    if ($row.key -eq 'resolver_mode') { $row.value = 'local_minimum' }
    if ($row.key -eq 'emit_score_breakdown') { $row.value = 'true' }
    if ($row.key -eq 'keep_intermediate_csv') { $row.value = 'true' }
    if ($row.key -eq 'parallel_mode') { $row.value = 'process' }
    if ($row.key -eq 'parallel_workers') { $row.value = '4' }
}
$settings | Export-Csv -Path (Join-Path $configDir 'settings.csv') -NoTypeInformation -Encoding UTF8
uv run python scripts\run_extraction.py --base-dir $base --parallel-mode process --parallel-workers 4
```

Expected:

- Processed files: `8`
- Workbook includes `Overview`
- Active sheet is `Overview`
- `Review Queue` row count is non-zero for current tissue validation set
- `Score Breakdown` exists because `emit_score_breakdown=true`

**Step 4: Generate urine BC1165 validation workbook**

Use the same pattern but create a one-file subset from:

```text
C:\Xcalibur\data\20260105_CSMU_NAA_Urine\BC1165_control.raw
```

Expected:

- Processed files: `1`
- Workbook includes `Overview`
- `Review Queue` preserves strict NL evidence text for user inspection

**Step 5: Inspect workbook smoke with openpyxl**

```powershell
$env:UV_CACHE_DIR='C:\Users\user\Desktop\XIC_Extractor\.worktrees\local-minimum-param-optimization\.uv-cache'
@'
from pathlib import Path
from openpyxl import load_workbook

for path in Path("output/excel_review_validation").glob("**/*.xlsx"):
    wb = load_workbook(path, data_only=True)
    if "Overview" not in wb.sheetnames:
        continue
    print(path.resolve())
    print("active=", wb.active.title)
    print("sheets=", wb.sheetnames)
    print("review_rows=", wb["Review Queue"].max_row - 1)
    print("overview_title=", wb["Overview"]["A1"].value)
'@ | uv run python -
```

Expected: both new validation workbooks print active `Overview`.

**Step 6: Commit only if code/docs changed after validation**

If validation required no code changes, do not create an empty commit.

---

## Failure Modes

| Failure mode | Test coverage | Error handling/user visibility |
|---|---|---|
| `Overview` counts disagree with `Review Queue` | `test_build_overview_sheet_summarizes_batch_review_health` | Visible as incorrect workbook summary; no runtime error |
| Multiple diagnostics for same sample-target are silently dropped | `test_review_queue_aggregates_diagnostics_by_sample_target` | Fixed by aggregation and `Issue Count` |
| Active sheet remains dense `XIC Results` | `tests/test_excel_sheets_contract.py` active sheet assertions | User sees wrong landing sheet immediately |
| Workbook compare misses Overview drift | `test_compare_workbooks_compares_overview_sheet` | A/B validation catches review workflow drift |
| Formula-like sample/target text becomes Excel formula | Existing formula injection tests plus preserve `_excel_text()` in new fields | Excel opens safely as literal text |
| Technical sheets become hard to find | Manual workbook smoke and tab color tests | User can still access all sheets |

No critical gap is acceptable for `Overview` active sheet, review queue aggregation, or workbook compare coverage.

## Parallelization Strategy

Sequential implementation, no parallelization opportunity.

Reason: every task touches `scripts/csv_to_excel.py` and related workbook contract tests. Parallel edits would create merge conflicts and make public workbook contract review harder.

## Review Gate Before Implementation

Before starting implementation, review this plan for:

- Whether `Overview` should be the active sheet.
- Whether `Review Queue` columns are short enough for daily manual review.
- Whether `Summary` should keep its name in this PR.
- Whether `Evidence` should be visible or hidden by default.

If any of those decisions changes, update this plan before coding.

