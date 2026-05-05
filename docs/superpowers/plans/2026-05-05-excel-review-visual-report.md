# Excel Review Semantics And Visual Report Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Clarify Excel review-health terminology and add an optional static HTML companion report while keeping Excel as the primary delivery artifact.

**Architecture:** Keep extraction, scoring, and workbook analytical values unchanged. First rename ambiguous workbook presentation fields and documentation, then add a report writer that consumes the same row data used by the workbook. The report is static HTML and opt-in through settings.

**Tech Stack:** Python 3.13, openpyxl, pytest, existing `uv run pytest` workflow, PowerShell on Windows.

---

## Background

`Score Breakdown` is a technical audit sheet, not a daily review surface. It exists to explain why a selected candidate received its confidence score.

`Summary` currently has confusing target-health labels:

- `Review Items`
- `Problem Rate`
- `NL Problems`
- `Low Confidence`

These should become:

- `Flagged Rows`
- `Flagged %`
- `MS2/NL Flags`
- `Low Confidence Rows`

This keeps `Detected %` separate from review workload.

## Task 1: Rename Summary Target-Health Fields

**Files:**

- Modify: `scripts/csv_to_excel.py`
- Test: `tests/test_csv_to_excel.py`
- Test: `tests/test_workbook_compare.py` if summary fixture headers assert old names

**Step 1: Write the failing test**

Update `tests/test_csv_to_excel.py::test_summary_sheet_includes_target_health_metrics`:

```python
assert "Flagged Rows" in data["headers"]
assert "Flagged %" in data["headers"]
assert "MS2/NL Flags" in data["headers"]
assert "Low Confidence Rows" in data["headers"]
assert "Review Items" not in data["headers"]
assert "Problem Rate" not in data["headers"]
assert "NL Problems" not in data["headers"]
assert "Low Confidence" not in data["headers"]
assert data["Analyte"]["Flagged Rows"] == 2
assert data["Analyte"]["Flagged %"] == "67%"
assert data["Analyte"]["MS2/NL Flags"] == 2
assert data["Analyte"]["Low Confidence Rows"] == 1
```

**Step 2: Run test to verify failure**

```powershell
$env:UV_CACHE_DIR='C:\Users\user\Desktop\XIC_Extractor\.worktrees\local-minimum-param-optimization\.uv-cache'
uv run pytest tests\test_csv_to_excel.py::test_summary_sheet_includes_target_health_metrics -v
```

Expected: FAIL because old headers still exist.

**Step 3: Implement minimal code**

In `scripts/csv_to_excel.py`, update `_SUMMARY_HEADERS`:

```python
"Flagged Rows",
"Flagged %",
"MS2/NL Flags",
"Low Confidence Rows",
```

Keep the underlying calculations unchanged.

**Step 4: Run tests**

```powershell
$env:UV_CACHE_DIR='C:\Users\user\Desktop\XIC_Extractor\.worktrees\local-minimum-param-optimization\.uv-cache'
uv run pytest tests\test_csv_to_excel.py tests\test_workbook_compare.py -v
```

Expected: PASS.

**Step 5: Commit**

```powershell
git add scripts\csv_to_excel.py tests\test_csv_to_excel.py tests\test_workbook_compare.py
git commit -m "refactor: clarify Excel target health labels"
```

## Task 2: Add Overview How-To-Read Copy

**Files:**

- Modify: `scripts/csv_to_excel.py`
- Test: `tests/test_csv_to_excel.py`

**Step 1: Write the failing test**

Add to `tests/test_csv_to_excel.py`:

```python
def test_overview_explains_detected_and_flagged_rates() -> None:
    rows = [_long_row("Tumor_1", "Analyte", "9.0", "10000", "OK")]
    wb = Workbook()
    ws = wb.active

    _build_overview_sheet(ws, rows, diagnostics=[], review_rows=[])

    values = [
        ws.cell(row=row_idx, column=1).value
        for row_idx in range(1, ws.max_row + 1)
    ]
    joined = "\n".join(str(value) for value in values if value)
    assert "Detected %" in joined
    assert "Flagged Rows" in joined
    assert "Flagged % is review workload" in joined
    assert "Score Breakdown is a technical audit sheet" in joined
```

**Step 2: Run test to verify failure**

```powershell
$env:UV_CACHE_DIR='C:\Users\user\Desktop\XIC_Extractor\.worktrees\local-minimum-param-optimization\.uv-cache'
uv run pytest tests\test_csv_to_excel.py::test_overview_explains_detected_and_flagged_rates -v
```

Expected: FAIL because Overview has no explanatory copy.

**Step 3: Implement minimal code**

In `_build_overview_sheet()`, append a compact section after Top Samples:

```text
How to read
Detected % = rows with usable RT and area.
Flagged Rows = rows sent to Review Queue for manual attention.
Flagged % is review workload, not detection failure.
Score Breakdown is a technical audit sheet when enabled.
```

Use `_excel_text()` for user-controlled text only. These static strings do not need formula escaping.

**Step 4: Run tests**

```powershell
$env:UV_CACHE_DIR='C:\Users\user\Desktop\XIC_Extractor\.worktrees\local-minimum-param-optimization\.uv-cache'
uv run pytest tests\test_csv_to_excel.py -v
```

Expected: PASS.

**Step 5: Commit**

```powershell
git add scripts\csv_to_excel.py tests\test_csv_to_excel.py
git commit -m "docs: explain Excel review metrics in overview"
```

## Task 3: Document Score Breakdown And Metric Semantics

**Files:**

- Modify: `README.md`
- Modify: `docs/superpowers/notes/2026-05-03-output-refactor-retrospective.md`

**Step 1: Write docs smoke expectation**

Use `rg` as the verification target:

```powershell
rg -n "Flagged Rows|Flagged %|MS2/NL Flags|Score Breakdown.*technical audit|Detected %.*Flagged %" README.md docs\superpowers\notes\2026-05-03-output-refactor-retrospective.md
```

Expected before edit: missing at least some terms.

**Step 2: Update README**

In the Excel workbook section, update Summary copy:

```text
Summary: one row per target, including Flagged Rows, Flagged %, MS2/NL Flags,
Low Confidence Rows, Detection %, Mean RT, Median Area, QC-only Area / ISTD ratio,
NL counts, RT delta, and confidence counts.
```

Add a short note:

```text
Detected % answers whether a target produced usable RT/area rows.
Flagged % answers how often rows require manual review.
These are different: a target can be frequently detected and still frequently flagged.
```

Clarify:

```text
Score Breakdown is a technical audit sheet for scoring signals and should not be treated
as the primary manual review queue.
```

**Step 3: Update retrospective**

Replace old field names with new names and mention the renamed semantics.

**Step 4: Run docs smoke**

```powershell
rg -n "Flagged Rows|Flagged %|MS2/NL Flags|Score Breakdown.*technical audit|Detected %.*Flagged %" README.md docs\superpowers\notes\2026-05-03-output-refactor-retrospective.md
```

Expected: all terms found.

**Step 5: Commit**

```powershell
git add README.md docs\superpowers\notes\2026-05-03-output-refactor-retrospective.md
git commit -m "docs: clarify Excel review metric semantics"
```

## Task 4: Add Review Report Setting Surface

**Files:**

- Modify: `xic_extractor/config.py`
- Modify: `xic_extractor/settings_schema.py`
- Modify: `config/settings.example.csv`
- Modify: `README.md`
- Test: relevant config/settings tests discovered with `rg -n "emit_score_breakdown|settings_schema|settings.example" tests xic_extractor`

**Step 1: Write failing config test**

Add a test near existing settings tests:

```python
def test_emit_review_report_defaults_false() -> None:
    config = load_settings(...)
    assert config.emit_review_report is False
```

Add a parser test that `emit_review_report,true` maps to `True`.

**Step 2: Run narrow test**

```powershell
$env:UV_CACHE_DIR='C:\Users\user\Desktop\XIC_Extractor\.worktrees\local-minimum-param-optimization\.uv-cache'
uv run pytest <discovered_settings_test_path> -v
```

Expected: FAIL because field does not exist.

**Step 3: Implement setting**

Add `emit_review_report: bool = False` to the config dataclass and settings schema using the same pattern as `emit_score_breakdown`.

Add to `config/settings.example.csv`:

```csv
emit_review_report,false
```

Do not add GUI controls in this task.

**Step 4: Run tests**

```powershell
$env:UV_CACHE_DIR='C:\Users\user\Desktop\XIC_Extractor\.worktrees\local-minimum-param-optimization\.uv-cache'
uv run pytest <discovered_settings_test_path> -v
```

Expected: PASS.

**Step 5: Commit**

```powershell
git add xic_extractor\config.py xic_extractor\settings_schema.py config\settings.example.csv README.md <test_path>
git commit -m "feat: add optional review report setting"
```

## Task 5: Add Static HTML Report Writer

**Files:**

- Create: `xic_extractor/output/review_report.py`
- Modify: `xic_extractor/output/excel_pipeline.py` only if shared helpers are useful
- Test: `tests/test_review_report.py`

**Step 1: Write failing tests**

Create `tests/test_review_report.py`:

```python
from xic_extractor.output.review_report import write_review_report


def test_write_review_report_contains_batch_counts_and_target_health(tmp_path: Path) -> None:
    rows = [
        {"SampleName": "S1", "Target": "A", "RT": "1.0", "Area": "100", "NL": "OK", "Confidence": "HIGH"},
        {"SampleName": "S2", "Target": "A", "RT": "ND", "Area": "ND", "NL": "NL_FAIL", "Confidence": "LOW"},
    ]
    review_rows = [
        {"Priority": "1", "Sample": "S2", "Target": "A", "Status": "Review", "Why": "NL support failed", "Action": "Check MS2 / NL evidence near selected RT", "Issue Count": "1", "Evidence": "strict observed neutral loss missing"}
    ]

    path = write_review_report(tmp_path / "review_report.html", rows, diagnostics=[], review_rows=review_rows)

    html = path.read_text(encoding="utf-8")
    assert "XIC Review Report" in html
    assert "Samples" in html
    assert "Targets" in html
    assert "Flagged Rows" in html
    assert "Detected %" in html
    assert "Flagged %" in html
```

Add escaping test:

```python
def test_write_review_report_escapes_user_controlled_text(tmp_path: Path) -> None:
    rows = [{"SampleName": "<script>alert(1)</script>", "Target": "=A", "RT": "1", "Area": "1", "NL": "OK", "Confidence": "HIGH"}]

    path = write_review_report(tmp_path / "review_report.html", rows, diagnostics=[], review_rows=[])

    html = path.read_text(encoding="utf-8")
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
```

**Step 2: Run tests to verify failure**

```powershell
$env:UV_CACHE_DIR='C:\Users\user\Desktop\XIC_Extractor\.worktrees\local-minimum-param-optimization\.uv-cache'
uv run pytest tests\test_review_report.py -v
```

Expected: FAIL because module does not exist.

**Step 3: Implement minimal report writer**

Implement `write_review_report(path, rows, diagnostics, review_rows) -> Path`.

Use only the standard library:

- `html.escape`
- `pathlib.Path`
- small string templates

Include:

- Batch Overview cards
- Target Health table
- Detection / flag heatmap table
- Review Queue table

Do not include external CSS/JS. Use inline `<style>`.

**Step 4: Run tests**

```powershell
$env:UV_CACHE_DIR='C:\Users\user\Desktop\XIC_Extractor\.worktrees\local-minimum-param-optimization\.uv-cache'
uv run pytest tests\test_review_report.py -v
```

Expected: PASS.

**Step 5: Commit**

```powershell
git add xic_extractor\output\review_report.py tests\test_review_report.py
git commit -m "feat: add static Excel companion review report"
```

## Task 6: Wire Optional Report Generation Into Run Output

**Files:**

- Modify: `scripts/csv_to_excel.py`
- Modify: `xic_extractor/output/excel_pipeline.py` if in-memory run output owns final output artifacts
- Test: `tests/test_csv_to_excel.py`
- Test: `tests/test_excel_pipeline.py` if applicable

**Step 1: Write failing integration test**

Add to `tests/test_csv_to_excel.py`:

```python
def test_run_emits_review_report_when_enabled(tmp_path: Path) -> None:
    config = _config(tmp_path)
    config.emit_review_report = True
    targets = [_target("Analyte")]
    config.output_csv.parent.mkdir(parents=True)
    _write_csv(
        config.output_csv.with_name("xic_results_long.csv"),
        [_long_row("Tumor_1", "Analyte", "9.1", "10000", "OK")],
    )
    _write_empty_diagnostics_csv(config.diagnostics_csv)

    excel_path = run(config, targets)

    report_path = excel_path.with_name(excel_path.name.replace("xic_results_", "review_report_")).with_suffix(".html")
    assert report_path.exists()
    assert "XIC Review Report" in report_path.read_text(encoding="utf-8")
```

**Step 2: Run test to verify failure**

```powershell
$env:UV_CACHE_DIR='C:\Users\user\Desktop\XIC_Extractor\.worktrees\local-minimum-param-optimization\.uv-cache'
uv run pytest tests\test_csv_to_excel.py::test_run_emits_review_report_when_enabled -v
```

Expected: FAIL because no report is written.

**Step 3: Implement wiring**

After workbook save succeeds, if `config.emit_review_report` is true:

```python
report_path = excel_path.with_name(
    excel_path.name.replace("xic_results_", "review_report_")
).with_suffix(".html")
write_review_report(report_path, rows, diagnostics, review_rows)
```

Do not write the report when workbook conversion exits early because rows are empty unless the codebase already writes empty workbooks.

**Step 4: Run tests**

```powershell
$env:UV_CACHE_DIR='C:\Users\user\Desktop\XIC_Extractor\.worktrees\local-minimum-param-optimization\.uv-cache'
uv run pytest tests\test_csv_to_excel.py tests\test_review_report.py -v
```

Expected: PASS.

**Step 5: Commit**

```powershell
git add scripts\csv_to_excel.py xic_extractor\output\review_report.py tests\test_csv_to_excel.py tests\test_review_report.py
git commit -m "feat: emit optional review report"
```

## Task 7: Focused And Real-Data Validation

**Files:**

- No production code changes expected.
- Generated files under `output/excel_review_validation/`.

**Step 1: Run focused suite**

```powershell
$env:UV_CACHE_DIR='C:\Users\user\Desktop\XIC_Extractor\.worktrees\local-minimum-param-optimization\.uv-cache'
uv run ruff check scripts\csv_to_excel.py xic_extractor\output\excel_pipeline.py xic_extractor\output\review_report.py tests\test_csv_to_excel.py tests\test_review_report.py
uv run pytest tests\test_csv_to_excel.py tests\test_excel_pipeline.py tests\test_excel_sheets_contract.py tests\test_output_columns.py tests\test_workbook_compare.py tests\test_review_report.py -v
```

Expected: PASS.

**Step 2: Run broad suite excluding known sandbox-only process spawn if needed**

```powershell
$env:UV_CACHE_DIR='C:\Users\user\Desktop\XIC_Extractor\.worktrees\local-minimum-param-optimization\.uv-cache'
uv run pytest --tb=short -q -k 'not process_pool_spawn_can_run_importable_no_raw_worker'
```

Expected: PASS.

**Step 3: Run tissue 8-raw validation**

Use `C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation`, `resolver_mode=local_minimum`, `emit_score_breakdown=true`, `emit_review_report=true`, and `parallel_workers=4`.

Expected:

- Workbook exists.
- Review report exists.
- Workbook active sheet is `Overview`.
- Overview `Flagged Rows` equals HTML report flagged count.

**Step 4: Inspect report smoke**

Use a small script to verify:

```powershell
rg -n "XIC Review Report|Flagged Rows|Detected %|Flagged %|Review Queue" output\excel_review_validation
```

Expected: new HTML report contains all terms.

**Step 5: Commit only if validation required code/docs changes**

No empty commit.

## Review Gate

Before implementation, confirm these decisions:

- `emit_review_report` default remains `false`.
- First HTML report version is static and non-interactive.
- No XIC thumbnails in v1.
- Workbook field rename is acceptable despite public workbook header drift.

If any of these changes, update this plan before coding.
