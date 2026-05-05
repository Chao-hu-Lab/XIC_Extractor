# Excel Review Semantics And Visual Report Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Clarify Excel review-health terminology and add an optional static HTML companion report while keeping Excel as the primary delivery artifact.

**Architecture:** Keep extraction, scoring, and analytical values unchanged. Move review-health counting into a shared metrics module, then make both Excel and HTML consume that same module so the two artifacts cannot drift. The report is static HTML, opt-in through settings and GUI Advanced, and uses no server or external dependencies.

**Tech Stack:** Python 3.13, openpyxl, pytest, standard-library `html.escape`, existing `uv run pytest` workflow, PowerShell on Windows.

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

## Required Architecture Decision

Do not let Excel and HTML calculate review-health numbers separately.

Create:

```text
xic_extractor/output/review_metrics.py
```

Use it from:

- `scripts/csv_to_excel.py`
- `xic_extractor/output/review_report.py`

The shared helpers must receive `count_no_ms2_as_detected`, because detection semantics depend on that setting.

## v1 Surface Decisions

- `emit_review_report=false` is the default.
- GUI Advanced gets a checkbox: `輸出 Review Report HTML`.
- CLI gets no new flag in v1. CLI users enable the report through settings.
- HTML is static and non-interactive.
- No XIC or MS2 thumbnails in v1.
- Workbook field rename is accepted even though Summary headers change.

## Task 1: Extract Shared Review Metrics And Rename Summary Fields

**Files:**

- Create: `xic_extractor/output/review_metrics.py`
- Modify: `scripts/csv_to_excel.py`
- Test: `tests/test_review_metrics.py`
- Test: `tests/test_csv_to_excel.py`
- Test: `tests/test_workbook_compare.py` if summary fixture headers assert old names

**Step 1: Write failing metrics tests**

Create `tests/test_review_metrics.py`:

```python
from xic_extractor.output.review_metrics import build_review_metrics


def test_review_metrics_separates_detection_from_flagged_workload() -> None:
    rows = [
        {"SampleName": "S1", "Target": "A", "RT": "1.0", "Area": "100", "NL": "OK", "Confidence": "HIGH"},
        {"SampleName": "S2", "Target": "A", "RT": "1.1", "Area": "110", "NL": "NL_FAIL", "Confidence": "LOW"},
        {"SampleName": "S3", "Target": "A", "RT": "1.2", "Area": "120", "NL": "NO_MS2", "Confidence": "MEDIUM"},
    ]
    review_rows = [
        {"Priority": "1", "Sample": "S2", "Target": "A", "Status": "Review"},
        {"Priority": "2", "Sample": "S3", "Target": "A", "Status": "Check"},
    ]

    metrics = build_review_metrics(
        rows,
        diagnostics=[],
        review_rows=review_rows,
        count_no_ms2_as_detected=False,
    )

    target = metrics.targets["A"]
    assert target.detected == 2
    assert target.total == 3
    assert target.detected_percent == "67%"
    assert target.flagged_rows == 2
    assert target.flagged_percent == "67%"
    assert target.ms2_nl_flags == 2
    assert target.low_confidence_rows == 1
```

Add a `NO_MS2` policy test:

```python
def test_review_metrics_honors_count_no_ms2_as_detected() -> None:
    rows = [
        {"SampleName": "S1", "Target": "A", "RT": "1.0", "Area": "100", "NL": "NO_MS2", "Confidence": "HIGH"},
    ]

    strict = build_review_metrics(rows, diagnostics=[], review_rows=[], count_no_ms2_as_detected=False)
    permissive = build_review_metrics(rows, diagnostics=[], review_rows=[], count_no_ms2_as_detected=True)

    assert strict.targets["A"].detected == 0
    assert permissive.targets["A"].detected == 1
```

**Step 2: Update failing Summary header test**

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

**Step 3: Run tests to verify failure**

```powershell
$env:UV_CACHE_DIR='C:\Users\user\Desktop\XIC_Extractor\.worktrees\local-minimum-param-optimization\.uv-cache'
uv run pytest tests\test_review_metrics.py tests\test_csv_to_excel.py::test_summary_sheet_includes_target_health_metrics -v
```

Expected: FAIL because `review_metrics.py` does not exist and old Summary headers still exist.

**Step 4: Implement shared metrics**

Create `xic_extractor/output/review_metrics.py`.

Suggested shape:

```python
from dataclasses import dataclass, field


@dataclass(frozen=True)
class TargetReviewMetrics:
    target: str
    total: int
    detected: int
    detected_percent: str
    flagged_rows: int
    flagged_percent: str
    ms2_nl_flags: int
    low_confidence_rows: int
    priority_counts: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class ReviewMetrics:
    sample_count: int
    target_count: int
    flagged_rows: int
    diagnostics_count: int
    detected_rows: int
    targets: dict[str, TargetReviewMetrics]
    heatmap: dict[tuple[str, str], str]
```

Implement:

```python
def build_review_metrics(
    rows: list[dict[str, str]],
    *,
    diagnostics: list[dict[str, str]],
    review_rows: list[dict[str, str]],
    count_no_ms2_as_detected: bool,
) -> ReviewMetrics:
    ...
```

Heatmap states:

- `clean-detected`
- `flagged-detected`
- `not-detected`
- `error`

**Step 5: Wire Summary to shared metrics**

In `scripts/csv_to_excel.py`:

- Import `build_review_metrics`.
- Rename `_SUMMARY_HEADERS` to use `Flagged Rows`, `Flagged %`, `MS2/NL Flags`, `Low Confidence Rows`.
- Change `_build_summary_sheet()` to compute `metrics = build_review_metrics(...)`.
- Use `metrics.targets[target]` for the four renamed fields.
- Keep existing RT, area, ratio, NL count, and confidence count helpers unless they are already covered by the shared metrics.

**Step 6: Run tests**

```powershell
$env:UV_CACHE_DIR='C:\Users\user\Desktop\XIC_Extractor\.worktrees\local-minimum-param-optimization\.uv-cache'
uv run pytest tests\test_review_metrics.py tests\test_csv_to_excel.py tests\test_workbook_compare.py -v
```

Expected: PASS.

**Step 7: Commit**

```powershell
git add xic_extractor\output\review_metrics.py scripts\csv_to_excel.py tests\test_review_metrics.py tests\test_csv_to_excel.py tests\test_workbook_compare.py
git commit -m "refactor: share Excel review metrics"
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

**Step 1: Run docs smoke before edit**

```powershell
rg -n "Flagged Rows|Flagged %|MS2/NL Flags|Score Breakdown.*technical audit|Detected %.*Flagged %" README.md docs\superpowers\notes\2026-05-03-output-refactor-retrospective.md
```

Expected: missing at least some terms.

**Step 2: Update README**

In the Excel workbook section, update Summary copy:

```text
Summary: one row per target, including Flagged Rows, Flagged %, MS2/NL Flags,
Low Confidence Rows, Detection %, Mean RT, Median Area, QC-only Area / ISTD ratio,
NL counts, RT delta, and confidence counts.
```

Add:

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

## Task 4: Add Review Report Setting Surface And GUI Toggle

**Files:**

- Modify: `xic_extractor/config.py`
- Modify: `xic_extractor/settings_schema.py`
- Modify: `config/settings.csv`
- Modify: `config/settings.example.csv`
- Modify: `gui/sections/settings_section.py`
- Modify: `README.md`
- Test: `tests/test_config.py`
- Test: `tests/test_settings_new_fields.py`
- Test: `tests/test_settings_section_advanced.py`

**Step 1: Write failing config tests**

In `tests/test_settings_new_fields.py`, add `emit_review_report` to the defaults and parsed boolean assertions.

Example expectations:

```python
assert CANONICAL_SETTINGS_DEFAULTS["emit_review_report"] == "false"
assert config.emit_review_report is True
```

In `tests/test_config.py`, update example coverage so both tracked config files contain `emit_review_report`.

**Step 2: Write failing GUI round-trip test**

In `tests/test_settings_section_advanced.py`, assert:

```python
assert "emit_review_report" in values
section._emit_review_report_checkbox.setChecked(True)
assert section.get_values()["emit_review_report"] == "true"
```

**Step 3: Run tests to verify failure**

```powershell
$env:UV_CACHE_DIR='C:\Users\user\Desktop\XIC_Extractor\.worktrees\local-minimum-param-optimization\.uv-cache'
uv run pytest tests\test_settings_new_fields.py tests\test_config.py tests\test_settings_section_advanced.py -v
```

Expected: FAIL because field and checkbox do not exist.

**Step 4: Implement setting**

Add `emit_review_report: bool = False` to `ExtractionConfig`.

Parse it in `load_config()` using the same boolean parser pattern as `emit_score_breakdown`.

Add defaults and description in `settings_schema.py`:

```python
"emit_review_report": "false"
"emit_review_report": "是否輸出 Review Report HTML（預設關閉）"
```

Add rows to both tracked files:

```csv
emit_review_report,false,是否輸出 Review Report HTML（預設關閉）
```

**Step 5: Implement GUI Advanced checkbox**

In `gui/sections/settings_section.py`:

- Add `emit_review_report` to `_ADVANCED_SETTING_KEYS`.
- Add `_emit_review_report_checkbox = QCheckBox("輸出 Review Report HTML")`.
- Include it in `load()`, `get_values()`, dirty tracking, and the Advanced debug flags row.

Do not add a CLI flag in v1.

**Step 6: Run tests**

```powershell
$env:UV_CACHE_DIR='C:\Users\user\Desktop\XIC_Extractor\.worktrees\local-minimum-param-optimization\.uv-cache'
uv run pytest tests\test_settings_new_fields.py tests\test_config.py tests\test_settings_section_advanced.py -v
```

Expected: PASS.

**Step 7: Commit**

```powershell
git add xic_extractor\config.py xic_extractor\settings_schema.py config\settings.csv config\settings.example.csv gui\sections\settings_section.py README.md tests\test_config.py tests\test_settings_new_fields.py tests\test_settings_section_advanced.py
git commit -m "feat: add optional review report setting"
```

## Task 5: Add Static HTML Report Writer

**Files:**

- Create: `xic_extractor/output/review_report.py`
- Test: `tests/test_review_report.py`

**Step 1: Write failing tests**

Create `tests/test_review_report.py`:

```python
from xic_extractor.output.review_report import write_review_report


def test_write_review_report_contains_batch_counts_target_health_and_legend(tmp_path: Path) -> None:
    rows = [
        {"SampleName": "S1", "Target": "A", "RT": "1.0", "Area": "100", "NL": "OK", "Confidence": "HIGH"},
        {"SampleName": "S2", "Target": "A", "RT": "ND", "Area": "ND", "NL": "NL_FAIL", "Confidence": "LOW"},
    ]
    review_rows = [
        {"Priority": "1", "Sample": "S2", "Target": "A", "Status": "Review", "Why": "NL support failed", "Action": "Check MS2 / NL evidence near selected RT", "Issue Count": "1", "Evidence": "strict observed neutral loss missing"}
    ]

    path = write_review_report(
        tmp_path / "review_report.html",
        rows,
        diagnostics=[],
        review_rows=review_rows,
        count_no_ms2_as_detected=False,
    )

    html = path.read_text(encoding="utf-8")
    assert "XIC Review Report" in html
    assert "Flagged Rows" in html
    assert "Detected %" in html
    assert "Flagged %" in html
    assert "clean-detected" in html
    assert "not-detected" in html
    assert "Review Queue" in html
```

Add escaping coverage for all user-controlled table fields:

```python
def test_write_review_report_escapes_user_controlled_text(tmp_path: Path) -> None:
    rows = [{"SampleName": "<script>alert(1)</script>", "Target": "=A", "RT": "1", "Area": "1", "NL": "OK", "Confidence": "HIGH"}]
    review_rows = [{"Priority": "1", "Sample": "<script>alert(1)</script>", "Target": "=A", "Status": "Review", "Why": "<b>bad</b>", "Action": "Check", "Issue Count": "1", "Evidence": "<img src=x>"}]

    path = write_review_report(
        tmp_path / "review_report.html",
        rows,
        diagnostics=[],
        review_rows=review_rows,
        count_no_ms2_as_detected=False,
    )

    html = path.read_text(encoding="utf-8")
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "&lt;b&gt;bad&lt;/b&gt;" in html
    assert "&lt;img src=x&gt;" in html
```

**Step 2: Run tests to verify failure**

```powershell
$env:UV_CACHE_DIR='C:\Users\user\Desktop\XIC_Extractor\.worktrees\local-minimum-param-optimization\.uv-cache'
uv run pytest tests\test_review_report.py -v
```

Expected: FAIL because module does not exist.

**Step 3: Implement minimal report writer**

Implement:

```python
def write_review_report(
    path: Path,
    rows: list[dict[str, str]],
    *,
    diagnostics: list[dict[str, str]],
    review_rows: list[dict[str, str]],
    count_no_ms2_as_detected: bool,
) -> Path:
    ...
```

Implementation rules:

- Use `build_review_metrics()` from `review_metrics.py`.
- Use `html.escape()` for all user-controlled text.
- Use inline CSS only.
- Include sections in this order:
  1. Batch Overview
  2. Top Flagged Targets
  3. Detection / Flag Heatmap with legend
  4. Target Health Table
  5. Review Queue

**Step 4: Run tests**

```powershell
$env:UV_CACHE_DIR='C:\Users\user\Desktop\XIC_Extractor\.worktrees\local-minimum-param-optimization\.uv-cache'
uv run pytest tests\test_review_report.py tests\test_review_metrics.py -v
```

Expected: PASS.

**Step 5: Commit**

```powershell
git add xic_extractor\output\review_report.py tests\test_review_report.py
git commit -m "feat: add static Excel companion review report"
```

## Task 6: Wire Optional Report Generation Into Both Workbook Paths

**Files:**

- Modify: `scripts/csv_to_excel.py`
- Modify: `xic_extractor/output/excel_pipeline.py`
- Test: `tests/test_csv_to_excel.py`
- Test: `tests/test_excel_pipeline.py`
- Test: `tests/test_run_extraction.py`

**Step 1: Write failing CSV conversion test**

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

**Step 2: Write failing in-memory pipeline test**

Add to `tests/test_excel_pipeline.py`:

```python
def test_write_excel_from_run_output_emits_review_report_when_enabled(tmp_path: Path) -> None:
    config = _config(tmp_path)
    config.emit_review_report = True
    output_path = tmp_path / "output" / "xic_results_20260505_1200.xlsx"

    write_excel_from_run_output(config, [_target("Analyte")], _run_output(), output_path=output_path)

    report_path = output_path.with_name("review_report_20260505_1200.html")
    assert report_path.exists()
```

**Step 3: Run tests to verify failure**

```powershell
$env:UV_CACHE_DIR='C:\Users\user\Desktop\XIC_Extractor\.worktrees\local-minimum-param-optimization\.uv-cache'
uv run pytest tests\test_csv_to_excel.py::test_run_emits_review_report_when_enabled tests\test_excel_pipeline.py::test_write_excel_from_run_output_emits_review_report_when_enabled -v
```

Expected: FAIL because no report is written.

**Step 4: Implement wiring**

After workbook save succeeds, if `config.emit_review_report` is true:

```python
report_path = excel_path.with_name(
    excel_path.name.replace("xic_results_", "review_report_")
).with_suffix(".html")
write_review_report(
    report_path,
    rows,
    diagnostics=diagnostics,
    review_rows=review_rows,
    count_no_ms2_as_detected=config.count_no_ms2_as_detected,
)
```

Do this in both:

- `scripts/csv_to_excel.py`
- `xic_extractor/output/excel_pipeline.py`

Do not add a CLI flag. Add or update `tests/test_run_extraction.py` only to assert settings-driven behavior remains enough and no new flag is documented.

**Step 5: Run tests**

```powershell
$env:UV_CACHE_DIR='C:\Users\user\Desktop\XIC_Extractor\.worktrees\local-minimum-param-optimization\.uv-cache'
uv run pytest tests\test_csv_to_excel.py tests\test_excel_pipeline.py tests\test_review_report.py tests\test_review_metrics.py tests\test_run_extraction.py -v
```

Expected: PASS.

**Step 6: Commit**

```powershell
git add scripts\csv_to_excel.py xic_extractor\output\excel_pipeline.py tests\test_csv_to_excel.py tests\test_excel_pipeline.py tests\test_run_extraction.py
git commit -m "feat: emit optional review report"
```

## Task 7: Focused And Real-Data Validation

**Files:**

- No production code changes expected.
- Generated files under `output/excel_review_validation/`.

**Step 1: Run focused suite**

```powershell
$env:UV_CACHE_DIR='C:\Users\user\Desktop\XIC_Extractor\.worktrees\local-minimum-param-optimization\.uv-cache'
uv run ruff check scripts\csv_to_excel.py xic_extractor\output\excel_pipeline.py xic_extractor\output\review_metrics.py xic_extractor\output\review_report.py tests\test_csv_to_excel.py tests\test_excel_pipeline.py tests\test_review_metrics.py tests\test_review_report.py
uv run pytest tests\test_csv_to_excel.py tests\test_excel_pipeline.py tests\test_excel_sheets_contract.py tests\test_output_columns.py tests\test_workbook_compare.py tests\test_review_metrics.py tests\test_review_report.py -v
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
- HTML report contains `XIC Review Report`.
- HTML `Flagged Rows` count equals workbook Overview flagged row count.

**Step 4: Inspect report smoke**

Use a small script or `rg`:

```powershell
rg -n "XIC Review Report|Flagged Rows|Detected %|Flagged %|Review Queue|clean-detected|flagged-detected|not-detected" output\excel_review_validation
```

Expected: new HTML report contains all terms.

**Step 5: Commit only if validation required code/docs changes**

No empty commit.

## Failure Modes

| Failure mode | Test coverage | User impact |
|---|---|---|
| Excel and HTML flagged counts diverge | Shared `review_metrics.py` unit tests plus real-data workbook/report comparison | User sees conflicting batch health |
| `NO_MS2` detection differs between workbook and report | `count_no_ms2_as_detected` metrics test | Heatmap disagrees with Excel `Detected %` |
| User-controlled text injects HTML | report escaping tests for sample, target, why, evidence | Browser renders unsafe or misleading content |
| GUI saves settings but drops `emit_review_report` | GUI Advanced round-trip tests | User enables report but no file appears |
| CLI users cannot discover setting | README docs smoke | Feature exists but is hard to use |

## What Already Exists

- `scripts/csv_to_excel.py` already builds `Overview`, `Review Queue`, and `Summary`.
- `xic_extractor/output/excel_pipeline.py` is the GUI and normal CLI workbook writer.
- `settings_schema.py` owns canonical defaults and descriptions.
- Both `config/settings.csv` and `config/settings.example.csv` are tracked and must stay in sync.
- GUI Advanced already has checkbox patterns for `keep_intermediate_csv` and `emit_score_breakdown`.

## NOT In Scope

- XIC thumbnails: deferred until trace image generation and file count are designed.
- MS2 spectrum thumbnails: deferred for the same reason.
- Interactive dashboard/server: not needed for v1 and harder to package.
- Peak selection/scoring/integration changes: this is output UX only.
- New CLI flag: settings and GUI are enough for v1.

## Parallelization Strategy

Sequential implementation, no parallelization opportunity.

Reason: every task touches the same output and settings contract, especially `scripts/csv_to_excel.py`, `excel_pipeline.py`, settings schema, and README. Parallel edits would create avoidable conflicts.

## Review Gate

Before implementation, confirm these decisions:

- `emit_review_report` default remains `false`.
- GUI Advanced checkbox is included in v1.
- CLI flag is explicitly not included in v1.
- First HTML report version is static and non-interactive.
- No XIC thumbnails in v1.
- Workbook field rename is acceptable despite public workbook header drift.
