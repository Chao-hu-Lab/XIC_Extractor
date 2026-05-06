# Excel Visual Dashboard And Debug Surfaces Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Excel easier to review, turn the optional HTML into a visual batch QA dashboard, demote debug-only surfaces, and make user-provided injection order work with real sample naming.

**Architecture:** Keep extraction and scoring decisions unchanged. Rework only output presentation, review evidence wording, injection-order name matching, and user-facing configuration/docs. Excel remains the deliverable artifact; HTML becomes an optional visual companion that shows charts and RT drift patterns instead of duplicating workbook tables.

**Tech Stack:** Python 3.13, openpyxl, standard-library HTML/SVG generation, pytest, existing `uv run pytest` workflow, PowerShell on Windows.

---

## Background

The current `emit_review_report=true` HTML is too close to Excel: it repeats overview counts, target health, heatmap, and review queue as tables. It does not provide enough new value for manual review.

The workbook also mixes daily-review surfaces and debug surfaces:

- `Summary` has `Detection %` after review workload columns, even though detection rate is a primary review metric.
- `Diagnostics` creates many rows per sample-target and reads like a verbose debug log.
- `Review Queue` is the correct daily review entry point, but its `Evidence` cells currently copy long diagnostic prose.
- `RT prior library` is not first-run compatible. It requires previously verified results, so it should be treated as developer/research/debug support, not a normal user-facing workflow.
- `injection_order_source` is first-run compatible and valuable. It should support real sample naming differences so CLI/GUI/HTML can use user-provided `SampleInfo.xlsx`.

## Required Surface Contract

Do not change extraction, scoring, area integration, candidate selection, workbook result schema for `XIC Results`, or default setting values.

Allowed changes:

- Reorder `Summary` columns.
- Hide `Diagnostics` by default while keeping the sheet.
- Shorten `Diagnostics` and `Review Queue` wording.
- Add static visual sections to HTML.
- Pass optional injection order data into HTML generation.
- Add sample-name canonicalization for injection-order lookup.
- Demote `rt_prior_library_path` from daily user docs/GUI copy.

## Files And Responsibilities

- `xic_extractor/injection_rolling.py`
  - Read CSV/XLSX injection order.
  - Add canonical sample-name aliases so `SampleInfo.xlsx` names can map to `.raw` stems.

- `tests/test_injection_rolling.py`
  - Unit tests for canonical alias behavior and ambiguous-name protection.

- `scripts/csv_to_excel.py`
  - Reorder `Summary`.
  - Hide `Diagnostics`.
  - Produce concise `Diagnostics` and `Review Queue` evidence.
  - Pass optional injection order into HTML writer.

- `tests/test_csv_to_excel.py`
  - Workbook contract tests for Summary order, hidden Diagnostics, concise Review Queue evidence, and HTML writer call inputs.

- `xic_extractor/output/review_report.py`
  - Add static visual sections: detection-rate bars, flag-burden bars, sorted heatmap, and ISTD RT injection trend.

- `tests/test_review_report.py`
  - HTML content tests for visual chart output, escaping, sorted targets, and RT trend omission/presence.

- `xic_extractor/settings_schema.py`, `gui/sections/settings_section.py`, `README.md`, `config/settings.example.csv`
  - Demote `rt_prior_library_path` wording to developer-only/advanced optional.
  - Keep the key available for backward compatibility.

---

## Task 1: Support Real SampleInfo Name Matching For Injection Order

**Files:**

- Modify: `xic_extractor/injection_rolling.py`
- Test: `tests/test_injection_rolling.py`

- [ ] **Step 1: Write failing tests**

Add these tests to `tests/test_injection_rolling.py`:

```python
def test_read_xlsx_adds_canonical_aliases_for_tissue_sampleinfo(tmp_path: Path) -> None:
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.append(["Sample_Name", "Injection_Order"])
    ws.append(["Tumor tissue BC2257_DNA ", 2])
    ws.append(["Normal tissue BC2257_DNA ", 36])
    ws.append(["Benign fat BC1055_DNA ", 76])
    ws.append(["Tumor tissue BC2286* DNA +RNA", 20])
    ws.append(["Breast Cancer Tissue_ pooled_QC_1 ", 1])
    ws.append(["Breast Cancer Tissue_pooled_QC_4", 49])
    path = tmp_path / "SampleInfo.xlsx"
    wb.save(path)

    order = read_injection_order(path)

    assert order["Tumor tissue BC2257_DNA"] == 2
    assert order["TumorBC2257_DNA"] == 2
    assert order["NormalBC2257_DNA"] == 36
    assert order["BenignfatBC1055_DNA"] == 76
    assert order["TumorBC2286_DNAandRNA"] == 20
    assert order["Breast_Cancer_Tissue_pooled_QC1"] == 1
    assert order["Breast_Cancer_Tissue_pooled_QC_4"] == 49
```

Add a collision test so aliases never silently overwrite a different injection order:

```python
def test_canonical_alias_collision_raises(tmp_path: Path) -> None:
    p = tmp_path / "info.csv"
    p.write_text(
        "Sample_Name,Injection_Order\n"
        "Tumor tissue BC2257_DNA,2\n"
        "TumorBC2257_DNA,3\n",
        encoding="utf-8",
    )

    try:
        read_injection_order(p)
    except ValueError as exc:
        assert "Conflicting injection order" in str(exc)
    else:
        raise AssertionError("expected conflicting alias to raise")
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```powershell
$env:UV_CACHE_DIR='C:\Users\user\Desktop\XIC_Extractor\.worktrees\local-minimum-param-optimization\.uv-cache'
uv run pytest tests\test_injection_rolling.py::test_read_xlsx_adds_canonical_aliases_for_tissue_sampleinfo tests\test_injection_rolling.py::test_canonical_alias_collision_raises -v
```

Expected: FAIL because aliases are not added and collisions are not detected.

- [ ] **Step 3: Implement canonical alias insertion**

In `xic_extractor/injection_rolling.py`, replace direct assignments in `_read_csv()` and `_read_xlsx()` with `_add_sample_order(out, name, order)`.

Add these helpers near the readers:

```python
def _add_sample_order(out: dict[str, int], raw_name: object, raw_order: object) -> None:
    name = str(raw_name).strip()
    order = int(str(raw_order).strip())
    if not name:
        return
    aliases = [name]
    canonical = _canonical_sample_name(name)
    if canonical and canonical not in aliases:
        aliases.append(canonical)
    for alias in aliases:
        existing = out.get(alias)
        if existing is not None and existing != order:
            raise ValueError(
                "Conflicting injection order for sample alias "
                f"{alias!r}: {existing} vs {order}"
            )
        out[alias] = order


def _canonical_sample_name(name: str) -> str:
    normalized = " ".join(name.replace("*", "").strip().split())
    normalized = normalized.replace(" DNA +RNA", "_DNAandRNA")
    normalized = normalized.replace("_ DNA +RNA", "_DNAandRNA")
    normalized = normalized.replace("DNA +RNA", "DNAandRNA")
    normalized = normalized.replace("Tumor tissue ", "Tumor")
    normalized = normalized.replace("Normal tissue ", "Normal")
    normalized = normalized.replace("Benign fat ", "Benignfat")
    normalized = normalized.replace("Breast Cancer Tissue_", "Breast_Cancer_Tissue_")
    normalized = normalized.replace("Breast Cancer Tissue ", "Breast_Cancer_Tissue_")
    normalized = normalized.replace("pooled_QC_", "pooled_QC")
    normalized = "_".join(part for part in normalized.split(" ") if part)
    if normalized.endswith("_QC4"):
        normalized = normalized.removesuffix("_QC4") + "_QC_4"
    return normalized
```

Update `_read_csv()`:

```python
def _read_csv(path: Path) -> dict[str, int]:
    out: dict[str, int] = {}
    with path.open(encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            name = (row.get("Sample_Name") or "").strip()
            order = row.get("Injection_Order")
            if not name or order in (None, ""):
                continue
            _add_sample_order(out, name, order)
    return out
```

Update `_read_xlsx()` loop:

```python
        for row in rows:
            name = row[name_i]
            order = row[order_i]
            if name is None or order is None:
                continue
            _add_sample_order(out, name, order)
```

- [ ] **Step 4: Run tests to verify pass**

Run:

```powershell
$env:UV_CACHE_DIR='C:\Users\user\Desktop\XIC_Extractor\.worktrees\local-minimum-param-optimization\.uv-cache'
uv run pytest tests\test_injection_rolling.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```powershell
git add xic_extractor\injection_rolling.py tests\test_injection_rolling.py
git commit -m "fix: match SampleInfo injection order names"
```

---

## Task 2: Reorder Summary Around Detection Rate

**Files:**

- Modify: `scripts/csv_to_excel.py`
- Test: `tests/test_csv_to_excel.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_csv_to_excel.py`:

```python
def test_summary_puts_detection_rate_before_review_workload() -> None:
    rows = [
        _long_row("S1", "Analyte", "9.0", "100", "OK", istd_pair="ISTD"),
        _long_row("S1", "ISTD", "8.9", "50", "OK", role="ISTD"),
        _long_row("S2", "Analyte", "ND", "ND", "ND", istd_pair="ISTD"),
        _long_row("S2", "ISTD", "8.8", "50", "OK", role="ISTD"),
    ]
    wb = Workbook()
    ws = wb.active

    _build_summary_sheet(ws, rows, count_no_ms2_as_detected=False, review_rows=[])

    headers = [ws.cell(row=1, column=i).value for i in range(1, ws.max_column + 1)]
    assert headers[:10] == [
        "Target",
        "Role",
        "ISTD Pair",
        "Detected",
        "Total",
        "Detection %",
        "Median Area (detected)",
        "Mean RT",
        "Area / ISTD ratio (paired detected)",
        "RT Delta vs ISTD",
    ]
    assert headers.index("Flagged Rows") > headers.index("Confidence VERY_LOW")
```

- [ ] **Step 2: Run test to verify failure**

Run:

```powershell
$env:UV_CACHE_DIR='C:\Users\user\Desktop\XIC_Extractor\.worktrees\local-minimum-param-optimization\.uv-cache'
uv run pytest tests\test_csv_to_excel.py::test_summary_puts_detection_rate_before_review_workload -v
```

Expected: FAIL because `Flagged Rows` is currently before `Detected`.

- [ ] **Step 3: Reorder Summary headers and values**

In `scripts/csv_to_excel.py`, replace `_SUMMARY_HEADERS` with:

```python
_SUMMARY_HEADERS = [
    "Target",
    "Role",
    "ISTD Pair",
    "Detected",
    "Total",
    "Detection %",
    "Median Area (detected)",
    "Mean RT",
    "Area / ISTD ratio (paired detected)",
    "RT Delta vs ISTD",
    "NL OK",
    "NL WARN",
    "NL FAIL",
    "NO MS2",
    "Confidence HIGH",
    "Confidence MEDIUM",
    "Confidence LOW",
    "Confidence VERY_LOW",
    "Flagged Rows",
    "Flagged %",
    "MS2/NL Flags",
    "Low Confidence Rows",
]
```

Update `_summary_row_values()` return order:

```python
    return [
        _excel_text(target),
        target_row.get("Role", ""),
        _excel_text(target_row.get("ISTD Pair", "")),
        detected,
        total,
        f"{detected / total * 100:.0f}%" if total else "0%",
        _long_median_area(detected_rows),
        _long_mean_rt(detected_rows),
        _long_area_ratio(target_row, rows, count_no_ms2_as_detected),
        _long_rt_delta(target_row, rows, count_no_ms2_as_detected),
        nl_counts["OK"],
        nl_counts["WARN"],
        nl_counts["NL_FAIL"],
        nl_counts["NO_MS2"],
        confidence_counts["HIGH"],
        confidence_counts["MEDIUM"],
        confidence_counts["LOW"],
        confidence_counts["VERY_LOW"],
        target_metrics.flagged_rows,
        target_metrics.flagged_percent,
        target_metrics.ms2_nl_flags,
        target_metrics.low_confidence_rows,
    ]
```

Update `widths` in `_build_summary_sheet()` to match the same 22 columns:

```python
    widths = [
        24, 12, 24, 12, 10, 12, 16, 12, 24, 22, 10,
        10, 10, 10, 14, 16, 12, 14, 14, 14, 12, 14,
    ]
```

- [ ] **Step 4: Run related tests**

Run:

```powershell
$env:UV_CACHE_DIR='C:\Users\user\Desktop\XIC_Extractor\.worktrees\local-minimum-param-optimization\.uv-cache'
uv run pytest tests\test_csv_to_excel.py::test_summary_puts_detection_rate_before_review_workload tests\test_csv_to_excel.py::test_summary_sheet_includes_detection_metrics tests\test_csv_to_excel.py::test_summary_sheet_includes_target_health_metrics -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```powershell
git add scripts\csv_to_excel.py tests\test_csv_to_excel.py
git commit -m "refactor: prioritize detection rate in Summary"
```

---

## Task 3: Make Diagnostics A Hidden Technical Log And Shorten Review Evidence

**Files:**

- Modify: `scripts/csv_to_excel.py`
- Test: `tests/test_csv_to_excel.py`

- [ ] **Step 1: Write failing workbook tests**

Add to `tests/test_csv_to_excel.py`:

```python
def test_run_hides_diagnostics_as_technical_log(tmp_path: Path) -> None:
    config = _config(tmp_path)
    config.output_csv.parent.mkdir(parents=True, exist_ok=True)
    _write_csv(
        config.output_csv,
        [_wide_row("S1", [_target("Analyte")])],
    )
    _write_empty_diagnostics_csv(config.diagnostics_csv)

    out = run(config, [_target("Analyte")])
    wb = load_workbook(out)

    assert wb["Diagnostics"].sheet_state == "hidden"
    assert wb["Review Queue"].sheet_state == "visible"
```

Add a short-evidence test:

```python
def test_review_queue_evidence_uses_short_tags() -> None:
    rows = [
        _long_row(
            "BenignfatBC1055_DNA",
            "8-oxodG",
            "17.177",
            "1850221.22",
            "NL_FAIL",
            confidence="LOW",
            reason="concerns: rt_prior (major); weak candidate: too_broad",
        )
    ]
    diagnostics = [
        {
            "SampleName": "BenignfatBC1055_DNA",
            "Target": "8-oxodG",
            "Issue": "NL_FAIL",
            "Reason": (
                "selected candidate has 2 candidate-aligned MS2 trigger scans; "
                "strict observed neutral loss 116.047 Da not detected in any aligned scan; "
                "alignment=region"
            ),
        },
        {
            "SampleName": "BenignfatBC1055_DNA",
            "Target": "8-oxodG",
            "Issue": "ANCHOR_RT_MISMATCH",
            "Reason": (
                "Paired analyte peak RT 17.177 min deviates 0.71 min from "
                "ISTD anchor at 16.470 min (allowed ±0.50 min)"
            ),
        },
        {
            "SampleName": "BenignfatBC1055_DNA",
            "Target": "8-oxodG",
            "Issue": "MULTI_PEAK",
            "Reason": "4 prominent peaks detected in window [16.0, 18.0]",
        },
    ]

    queue = _review_queue_rows(rows, diagnostics)

    assert queue[0]["Evidence"] == "NL_FAIL; anchor dRT=0.71 min; multi_peak=4"
    assert "selected candidate has" not in queue[0]["Evidence"]
    assert len(queue[0]["Evidence"]) < 80
```

Add a concise diagnostics text test:

```python
def test_diagnostics_sheet_uses_short_reason_text() -> None:
    rows = [
        {
            "SampleName": "S1",
            "Target": "A",
            "Issue": "NL_FAIL",
            "Reason": "selected candidate has 2 candidate-aligned MS2 trigger scans; strict observed neutral loss 116.047 Da not detected in any aligned scan; alignment=region",
        }
    ]
    wb = Workbook()
    ws = wb.active

    _build_diagnostics_sheet(ws, rows)

    assert ws["D2"].value == "selected candidate lacks strict NL match"
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```powershell
$env:UV_CACHE_DIR='C:\Users\user\Desktop\XIC_Extractor\.worktrees\local-minimum-param-optimization\.uv-cache'
uv run pytest tests\test_csv_to_excel.py::test_run_hides_diagnostics_as_technical_log tests\test_csv_to_excel.py::test_review_queue_evidence_uses_short_tags tests\test_csv_to_excel.py::test_diagnostics_sheet_uses_short_reason_text -v
```

Expected: FAIL because `Diagnostics` is visible and evidence is long prose.

- [ ] **Step 3: Add concise evidence helpers**

In `scripts/csv_to_excel.py`, replace `_review_evidence()` with:

```python
def _review_evidence(
    row: dict[str, str], diagnostics: list[dict[str, str]]
) -> str:
    if diagnostics:
        tags = [_diagnostic_tag(diagnostic) for diagnostic in diagnostics]
    else:
        tags = [_row_review_issue(row) or row.get("Reason", "")]
    return "; ".join(_dedupe_text(tag for tag in tags if tag))
```

Add helper functions:

```python
def _diagnostic_tag(diagnostic: dict[str, str]) -> str:
    issue = diagnostic.get("Issue", "")
    reason = diagnostic.get("Reason", "")
    if issue == "NL_FAIL":
        return "NL_FAIL"
    if issue == "NO_MS2":
        return "NO_MS2"
    if issue == "NL_ANCHOR_FALLBACK":
        return "NL_anchor_fallback"
    if issue == "ANCHOR_RT_MISMATCH":
        delta = _first_regex_group(reason, r"deviates ([0-9.]+) min")
        return f"anchor dRT={delta} min" if delta else "anchor_mismatch"
    if issue == "MULTI_PEAK":
        count = _first_regex_group(reason, r"(\d+) prominent peaks")
        return f"multi_peak={count}" if count else "multi_peak"
    if issue in {"PEAK_NOT_FOUND", "NO_SIGNAL"}:
        return "peak_not_found"
    return issue


def _first_regex_group(text: str, pattern: str) -> str:
    match = re.search(pattern, text)
    return match.group(1) if match else ""
```

Add `import re` at the top of `scripts/csv_to_excel.py`.

- [ ] **Step 4: Shorten Diagnostics sheet wording**

In `_build_diagnostics_sheet()`, replace the `Reason` value branch with `_diagnostic_reason_for_sheet(row)`:

```python
            value = (
                _excel_text(_diagnostic_reason_for_sheet(row))
                if header == "Reason"
                else _excel_text(raw)
                if header in {"SampleName", "Target"}
                else raw
            )
```

Add:

```python
def _diagnostic_reason_for_sheet(row: dict[str, str]) -> str:
    issue = row.get("Issue", "")
    reason = row.get("Reason", "")
    if issue == "NL_FAIL":
        return "selected candidate lacks strict NL match"
    if issue == "NO_MS2":
        return "no aligned MS2 trigger"
    if issue == "NL_ANCHOR_FALLBACK":
        return "no candidate-aligned NL anchor"
    if issue == "ANCHOR_RT_MISMATCH":
        delta = _first_regex_group(reason, r"deviates ([0-9.]+) min")
        return f"anchor RT mismatch ({delta} min)" if delta else "anchor RT mismatch"
    if issue == "MULTI_PEAK":
        count = _first_regex_group(reason, r"(\d+) prominent peaks")
        return f"{count} prominent peaks" if count else "multiple prominent peaks"
    if issue in {"PEAK_NOT_FOUND", "NO_SIGNAL"}:
        return "peak not found"
    return reason or issue
```

- [ ] **Step 5: Hide Diagnostics by default**

In `_run_with_config()`, after `_build_diagnostics_sheet(ws_diagnostics, diagnostics)`, add:

```python
    ws_diagnostics.sheet_state = "hidden"
```

Keep the sheet name `Diagnostics` for backward compatibility.

- [ ] **Step 6: Run tests**

Run:

```powershell
$env:UV_CACHE_DIR='C:\Users\user\Desktop\XIC_Extractor\.worktrees\local-minimum-param-optimization\.uv-cache'
uv run pytest tests\test_csv_to_excel.py -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

Run:

```powershell
git add scripts\csv_to_excel.py tests\test_csv_to_excel.py
git commit -m "refactor: demote Diagnostics to technical log"
```

---

## Task 4: Turn HTML Into A Visual Dashboard

**Files:**

- Modify: `xic_extractor/output/review_report.py`
- Test: `tests/test_review_report.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_review_report.py`:

```python
def test_review_report_contains_visual_detection_and_flag_charts(tmp_path: Path) -> None:
    rows = [
        {"SampleName": "S1", "Target": "A", "RT": "1.0", "Area": "100", "NL": "OK", "Confidence": "HIGH"},
        {"SampleName": "S2", "Target": "A", "RT": "ND", "Area": "ND", "NL": "ND", "Confidence": "LOW"},
        {"SampleName": "S1", "Target": "B", "RT": "2.0", "Area": "200", "NL": "OK", "Confidence": "HIGH"},
        {"SampleName": "S2", "Target": "B", "RT": "2.1", "Area": "210", "NL": "NL_FAIL", "Confidence": "LOW"},
    ]
    review_rows = [
        {"Priority": "1", "Sample": "S2", "Target": "B", "Status": "Review", "Why": "NL support failed", "Action": "Check", "Issue Count": "1", "Evidence": "NL_FAIL"},
    ]

    path = write_review_report(
        tmp_path / "review_report.html",
        rows,
        diagnostics=[],
        review_rows=review_rows,
        count_no_ms2_as_detected=False,
    )

    html = path.read_text(encoding="utf-8")
    assert "<h2>Detection Rate By Target</h2>" in html
    assert "<h2>Flag Burden By Target</h2>" in html
    assert 'class="bar-fill detection"' in html
    assert 'class="bar-fill flagged"' in html
    assert "A</td><td>50%</td>" in html
    assert "B</td><td>50%</td>" not in html
```

Add a sorted heatmap test:

```python
def test_review_report_heatmap_sorts_low_detection_targets_first(tmp_path: Path) -> None:
    rows = [
        {"SampleName": "S1", "Target": "High", "RT": "1", "Area": "1", "NL": "OK", "Confidence": "HIGH"},
        {"SampleName": "S2", "Target": "High", "RT": "2", "Area": "1", "NL": "OK", "Confidence": "HIGH"},
        {"SampleName": "S1", "Target": "Low", "RT": "ND", "Area": "ND", "NL": "ND", "Confidence": "LOW"},
        {"SampleName": "S2", "Target": "Low", "RT": "2", "Area": "1", "NL": "OK", "Confidence": "HIGH"},
    ]

    path = write_review_report(
        tmp_path / "review_report.html",
        rows,
        diagnostics=[],
        review_rows=[],
        count_no_ms2_as_detected=False,
    )

    html = path.read_text(encoding="utf-8")
    assert html.index("<th>Low</th>") < html.index("<th>High</th>")
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```powershell
$env:UV_CACHE_DIR='C:\Users\user\Desktop\XIC_Extractor\.worktrees\local-minimum-param-optimization\.uv-cache'
uv run pytest tests\test_review_report.py::test_review_report_contains_visual_detection_and_flag_charts tests\test_review_report.py::test_review_report_heatmap_sorts_low_detection_targets_first -v
```

Expected: FAIL because HTML has tables but no bar-chart sections and heatmap uses input target order.

- [ ] **Step 3: Add chart CSS**

In `xic_extractor/output/review_report.py`, add CSS:

```python
.bar-table td:nth-child(2){width:90px;font-weight:700}
.bar-track{height:14px;background:#eaeef2;border:1px solid #d0d7de}
.bar-fill{height:100%}
.bar-fill.detection{background:#2da44e}
.bar-fill.flagged{background:#cf222e}
.dashboard-note{color:#57606a;font-size:13px;margin:4px 0 14px}
```

- [ ] **Step 4: Sort targets by detection rate**

Add:

```python
def _targets_by_detection(metrics: ReviewMetrics) -> list[str]:
    return [
        item.target
        for item in sorted(
            metrics.targets.values(),
            key=lambda item: (_percent_value(item.detected_percent), item.target),
        )
    ]


def _percent_value(text: str) -> int:
    try:
        return int(text.strip().removesuffix("%"))
    except ValueError:
        return 0
```

In `write_review_report()`, replace:

```python
    targets = _ordered_values(rows, "Target")
```

with:

```python
    targets = _targets_by_detection(metrics)
```

- [ ] **Step 5: Add visual sections**

Add:

```python
def _detection_rate_chart(metrics: ReviewMetrics, targets: list[str]) -> str:
    rows = []
    for target in targets:
        item = metrics.targets[target]
        pct = _percent_value(item.detected_percent)
        rows.append(
            "<tr>"
            f"<td>{escape(target)}</td><td>{item.detected_percent}</td>"
            '<td><div class="bar-track">'
            f'<div class="bar-fill detection" style="width:{pct}%"></div>'
            "</div></td>"
            "</tr>"
        )
    body = "".join(rows) or '<tr><td colspan="3">None</td></tr>'
    return (
        "<section><h2>Detection Rate By Target</h2>"
        '<p class="dashboard-note">Lowest detection targets are listed first.</p>'
        '<table class="bar-table"><thead><tr><th>Target</th><th>Detected %</th>'
        "<th>Rate</th></tr></thead>"
        f"<tbody>{body}</tbody></table></section>"
    )


def _flag_burden_chart(metrics: ReviewMetrics, targets: list[str]) -> str:
    flagged = [
        metrics.targets[target]
        for target in targets
        if metrics.targets[target].flagged_rows > 0
    ]
    flagged.sort(key=lambda item: (-_percent_value(item.flagged_percent), item.target))
    rows = []
    for item in flagged:
        pct = _percent_value(item.flagged_percent)
        rows.append(
            "<tr>"
            f"<td>{escape(item.target)}</td><td>{item.flagged_percent}</td>"
            f"<td>{item.flagged_rows}</td>"
            '<td><div class="bar-track">'
            f'<div class="bar-fill flagged" style="width:{pct}%"></div>'
            "</div></td>"
            "</tr>"
        )
    body = "".join(rows) or '<tr><td colspan="4">None</td></tr>'
    return (
        "<section><h2>Flag Burden By Target</h2>"
        '<p class="dashboard-note">Flagged % is review workload, not detection failure.</p>'
        '<table class="bar-table"><thead><tr><th>Target</th><th>Flagged %</th>'
        "<th>Rows</th><th>Burden</th></tr></thead>"
        f"<tbody>{body}</tbody></table></section>"
    )
```

In `write_review_report()`, replace `_top_flagged_targets(metrics)` and `_target_health_table(metrics, targets)` in the HTML list with:

```python
                _detection_rate_chart(metrics, targets),
                _flag_burden_chart(metrics, targets),
```

Keep `_heatmap(metrics, samples, targets)` and `_review_queue(review_rows)`.

- [ ] **Step 6: Run tests**

Run:

```powershell
$env:UV_CACHE_DIR='C:\Users\user\Desktop\XIC_Extractor\.worktrees\local-minimum-param-optimization\.uv-cache'
uv run pytest tests\test_review_report.py -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

Run:

```powershell
git add xic_extractor\output\review_report.py tests\test_review_report.py
git commit -m "feat: make review report visual"
```

---

## Task 5: Add ISTD RT Injection Trend To HTML

**Files:**

- Modify: `scripts/csv_to_excel.py`
- Modify: `xic_extractor/output/review_report.py`
- Test: `tests/test_review_report.py`
- Test: `tests/test_csv_to_excel.py`

- [ ] **Step 1: Write failing HTML tests**

Add to `tests/test_review_report.py`:

```python
def test_review_report_draws_istd_rt_injection_trend(tmp_path: Path) -> None:
    rows = [
        {"SampleName": "S1", "Target": "d3-A", "Role": "ISTD", "RT": "8.90", "Area": "100", "NL": "OK", "Confidence": "HIGH"},
        {"SampleName": "S2", "Target": "d3-A", "Role": "ISTD", "RT": "9.10", "Area": "100", "NL": "OK", "Confidence": "HIGH"},
        {"SampleName": "S1", "Target": "A", "Role": "Analyte", "RT": "9.00", "Area": "50", "NL": "OK", "Confidence": "HIGH"},
    ]

    path = write_review_report(
        tmp_path / "review_report.html",
        rows,
        diagnostics=[],
        review_rows=[],
        count_no_ms2_as_detected=False,
        injection_order={"S1": 1, "S2": 2},
    )

    html = path.read_text(encoding="utf-8")
    assert "<h2>ISTD RT Injection Trend</h2>" in html
    assert "<svg" in html
    assert "d3-A" in html
    assert "RT 8.9000 min" in html
    assert "Injection 1" in html
```

Add omission behavior:

```python
def test_review_report_omits_istd_trend_without_injection_order(tmp_path: Path) -> None:
    rows = [
        {"SampleName": "S1", "Target": "d3-A", "Role": "ISTD", "RT": "8.90", "Area": "100", "NL": "OK", "Confidence": "HIGH"},
    ]

    path = write_review_report(
        tmp_path / "review_report.html",
        rows,
        diagnostics=[],
        review_rows=[],
        count_no_ms2_as_detected=False,
    )

    html = path.read_text(encoding="utf-8")
    assert "ISTD RT Injection Trend" not in html
```

- [ ] **Step 2: Write failing wiring test**

Add to `tests/test_csv_to_excel.py`:

```python
def test_run_passes_injection_order_to_review_report(tmp_path: Path, monkeypatch) -> None:
    config = _config(tmp_path, emit_review_report=True)
    config.injection_order_source = tmp_path / "SampleInfo.csv"
    config.injection_order_source.write_text(
        "Sample_Name,Injection_Order\nS1,1\n",
        encoding="utf-8",
    )
    config.output_csv.parent.mkdir(parents=True, exist_ok=True)
    _write_csv(config.output_csv, [_wide_row("S1", [_target("Analyte")])])
    _write_empty_diagnostics_csv(config.diagnostics_csv)
    calls = {}

    def _fake_write_review_report(path, rows, **kwargs):
        calls["injection_order"] = kwargs["injection_order"]
        path.write_text("<html></html>", encoding="utf-8")
        return path

    monkeypatch.setattr(
        "scripts.csv_to_excel.write_review_report",
        _fake_write_review_report,
    )

    run(config, [_target("Analyte")])

    assert calls["injection_order"] == {"S1": 1}
```

- [ ] **Step 3: Run tests to verify failure**

Run:

```powershell
$env:UV_CACHE_DIR='C:\Users\user\Desktop\XIC_Extractor\.worktrees\local-minimum-param-optimization\.uv-cache'
uv run pytest tests\test_review_report.py::test_review_report_draws_istd_rt_injection_trend tests\test_review_report.py::test_review_report_omits_istd_trend_without_injection_order tests\test_csv_to_excel.py::test_run_passes_injection_order_to_review_report -v
```

Expected: FAIL because `write_review_report()` does not accept `injection_order` and `run()` does not pass it.

- [ ] **Step 4: Extend HTML writer signature**

In `xic_extractor/output/review_report.py`, change the signature:

```python
def write_review_report(
    path: Path,
    rows: list[dict[str, str]],
    *,
    diagnostics: list[dict[str, str]],
    review_rows: list[dict[str, str]],
    count_no_ms2_as_detected: bool,
    injection_order: dict[str, int] | None = None,
) -> Path:
```

Add `_istd_rt_trend(rows, injection_order)` in the HTML list after `_flag_burden_chart(...)`:

```python
                _istd_rt_trend(rows, injection_order),
```

- [ ] **Step 5: Implement static SVG trend**

Add to `xic_extractor/output/review_report.py`:

```python
def _istd_rt_trend(
    rows: list[dict[str, str]],
    injection_order: dict[str, int] | None,
) -> str:
    if not injection_order:
        return ""
    points: list[tuple[str, int, float]] = []
    for row in rows:
        if row.get("Role") != "ISTD":
            continue
        sample = row.get("SampleName", "")
        order = injection_order.get(sample)
        rt = _float_value(row.get("RT", ""))
        if order is None or rt is None:
            continue
        points.append((row.get("Target", ""), order, rt))
    if len(points) < 2:
        return ""
    orders = [order for _, order, _ in points]
    rts = [rt for _, _, rt in points]
    min_order, max_order = min(orders), max(orders)
    min_rt, max_rt = min(rts), max(rts)
    if min_order == max_order or min_rt == max_rt:
        return ""
    width, height = 900, 260
    left, top, right, bottom = 56, 20, 20, 42
    plot_w = width - left - right
    plot_h = height - top - bottom

    def x(order: int) -> float:
        return left + (order - min_order) / (max_order - min_order) * plot_w

    def y(rt: float) -> float:
        return top + (max_rt - rt) / (max_rt - min_rt) * plot_h

    palette = ["#0969da", "#1a7f37", "#cf222e", "#8250df", "#9a6700", "#57606a"]
    targets = _ordered_unique([target for target, _, _ in points])
    circles = []
    legends = []
    for idx, target in enumerate(targets):
        color = palette[idx % len(palette)]
        target_points = [
            (order, rt)
            for point_target, order, rt in points
            if point_target == target
        ]
        target_points.sort()
        polyline = " ".join(f"{x(order):.1f},{y(rt):.1f}" for order, rt in target_points)
        circles.append(
            f'<polyline points="{polyline}" fill="none" stroke="{color}" stroke-width="2"/>'
        )
        for order, rt in target_points:
            circles.append(
                f'<circle cx="{x(order):.1f}" cy="{y(rt):.1f}" r="3" fill="{color}">'
                f"<title>{escape(target)}: Injection {order}, RT {rt:.4f} min</title>"
                "</circle>"
            )
        legends.append(
            f'<span class="chip"><span class="box" style="background:{color}"></span>'
            f"{escape(target)}</span>"
        )
    return (
        "<section><h2>ISTD RT Injection Trend</h2>"
        '<p class="dashboard-note">Uses injection_order_source when configured; omitted when injection order is unavailable.</p>'
        f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="ISTD RT injection trend">'
        f'<line x1="{left}" y1="{height-bottom}" x2="{width-right}" y2="{height-bottom}" stroke="#8c959f"/>'
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{height-bottom}" stroke="#8c959f"/>'
        f'<text x="{left}" y="{height-10}" font-size="12">Injection {min_order}</text>'
        f'<text x="{width-right-80}" y="{height-10}" font-size="12">Injection {max_order}</text>'
        f'<text x="4" y="{top+10}" font-size="12">RT {max_rt:.4f}</text>'
        f'<text x="4" y="{height-bottom}" font-size="12">RT {min_rt:.4f}</text>'
        f"{''.join(circles)}"
        "</svg>"
        f'<div class="legend">{"".join(legends)}</div>'
        "</section>"
    )


def _float_value(value: str) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _ordered_unique(values: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out
```

- [ ] **Step 6: Pass injection order from Excel pipeline**

In `scripts/csv_to_excel.py`, import:

```python
from xic_extractor.injection_rolling import read_injection_order
```

In `_run_with_config()`, before `write_review_report(...)`, compute:

```python
        injection_order = (
            read_injection_order(config.injection_order_source)
            if config.injection_order_source is not None
            else None
        )
```

Then call:

```python
        write_review_report(
            review_report_path_for_excel(excel_path),
            rows,
            diagnostics=diagnostics,
            review_rows=review_rows,
            count_no_ms2_as_detected=config.count_no_ms2_as_detected,
            injection_order=injection_order,
        )
```

- [ ] **Step 7: Run tests**

Run:

```powershell
$env:UV_CACHE_DIR='C:\Users\user\Desktop\XIC_Extractor\.worktrees\local-minimum-param-optimization\.uv-cache'
uv run pytest tests\test_review_report.py tests\test_csv_to_excel.py::test_run_passes_injection_order_to_review_report -v
```

Expected: PASS.

- [ ] **Step 8: Commit**

Run:

```powershell
git add scripts\csv_to_excel.py xic_extractor\output\review_report.py tests\test_review_report.py tests\test_csv_to_excel.py
git commit -m "feat: add ISTD RT trend to review report"
```

---

## Task 6: Demote RT Prior Library From Daily User Surface

**Files:**

- Modify: `README.md`
- Modify: `xic_extractor/settings_schema.py`
- Modify: `config/settings.example.csv`
- Modify: `gui/sections/settings_section.py`
- Test: `tests/test_settings_new_fields.py`
- Test: `tests/test_settings_section_advanced.py`

- [ ] **Step 1: Write failing tests**

Update `tests/test_settings_new_fields.py::test_new_settings_are_in_canonical_defaults_and_descriptions` assertions for RT prior wording:

```python
    assert "developer/debug" in CANONICAL_SETTINGS_DESCRIPTIONS["rt_prior_library_path"]
    assert "leave empty" in CANONICAL_SETTINGS_DESCRIPTIONS["rt_prior_library_path"]
```

Add to `tests/test_settings_section_advanced.py`:

```python
def test_rt_prior_library_gui_label_marks_developer_debug(qtbot) -> None:
    section = SettingsSection()
    qtbot.addWidget(section)
    section.load(_settings_values())

    labels = section.findChildren(QLabel)
    text = "\n".join(label.text() for label in labels)

    assert "RT prior library" in text
    assert "developer/debug" in text
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```powershell
$env:UV_CACHE_DIR='C:\Users\user\Desktop\XIC_Extractor\.worktrees\local-minimum-param-optimization\.uv-cache'
uv run pytest tests\test_settings_new_fields.py::test_new_settings_are_in_canonical_defaults_and_descriptions tests\test_settings_section_advanced.py::test_rt_prior_library_gui_label_marks_developer_debug -v
```

Expected: FAIL because current wording says only external RT prior library path.

- [ ] **Step 3: Update canonical description**

In `xic_extractor/settings_schema.py`, set:

```python
    "rt_prior_library_path": (
        "Developer/debug RT prior library CSV path; leave empty for normal use"
    ),
```

In `config/settings.example.csv`, update the `rt_prior_library_path` description row to:

```csv
rt_prior_library_path,,Developer/debug RT prior library CSV path; leave empty for normal use
```

- [ ] **Step 4: Update GUI label**

In `gui/sections/settings_section.py`, find the RT prior library field label and change its text to:

```python
"RT prior library (developer/debug)"
```

Keep the input field and browse behavior. Do not remove the config key.

- [ ] **Step 5: Update README**

In `README.md`, update the settings table row for `rt_prior_library_path`:

```markdown
| `rt_prior_library_path` | Developer/debug RT prior library CSV path. Leave empty for normal use; this is not a first-run feature. |
```

Add one short note near advanced settings:

```markdown
`rt_prior_library_path` is intentionally not part of the normal workflow. A prior library requires previously verified results and can bias future peak selection if built from incorrect peaks.
```

- [ ] **Step 6: Run tests**

Run:

```powershell
$env:UV_CACHE_DIR='C:\Users\user\Desktop\XIC_Extractor\.worktrees\local-minimum-param-optimization\.uv-cache'
uv run pytest tests\test_settings_new_fields.py tests\test_settings_section_advanced.py -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

Run:

```powershell
git add README.md xic_extractor\settings_schema.py config\settings.example.csv gui\sections\settings_section.py tests\test_settings_new_fields.py tests\test_settings_section_advanced.py
git commit -m "docs: demote RT prior library to debug surface"
```

---

## Task 7: Update Workbook Overview Copy And Contracts

**Files:**

- Modify: `scripts/csv_to_excel.py`
- Modify: `tests/test_csv_to_excel.py`
- Modify: `tests/test_excel_sheets_contract.py`

- [ ] **Step 1: Write failing copy test**

Update `tests/test_csv_to_excel.py::test_overview_explains_detected_and_flagged_rates` to assert these notes:

```python
    assert "Start with Summary Detection %" in joined
    assert "Review Queue has one row per sample-target needing attention" in joined
    assert "Diagnostics is a hidden technical log" in joined
    assert "HTML Review Report is for visual batch QA" in joined
```

Add a workbook contract assertion in the existing full workbook test:

```python
    assert wb["Diagnostics"].sheet_state == "hidden"
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```powershell
$env:UV_CACHE_DIR='C:\Users\user\Desktop\XIC_Extractor\.worktrees\local-minimum-param-optimization\.uv-cache'
uv run pytest tests\test_csv_to_excel.py::test_overview_explains_detected_and_flagged_rates tests\test_excel_sheets_contract.py -v
```

Expected: FAIL until overview copy and contract expectations are updated.

- [ ] **Step 3: Update overview copy**

In `_write_overview_how_to_read()`, replace `notes` with:

```python
    notes = [
        "Start with Summary Detection % to find targets with systematic detection loss.",
        "Review Queue has one row per sample-target needing attention.",
        "Flagged % is review workload, not detection failure.",
        "Numeric NL_FAIL rows can be detected-but-flagged for review but excluded from Summary analytical aggregates.",
        "Diagnostics is a hidden technical log for debugging verbose evidence.",
        "Score Breakdown is a technical audit sheet when enabled.",
        "HTML Review Report is for visual batch QA when enabled.",
    ]
```

- [ ] **Step 4: Update sheet contract tests**

Keep sheet names unchanged:

```python
[
    "Overview",
    "Review Queue",
    "XIC Results",
    "Summary",
    "Targets",
    "Diagnostics",
    "Run Metadata",
]
```

Add only hidden-state assertions for `Diagnostics`. Do not expect a sheet rename.

- [ ] **Step 5: Run tests**

Run:

```powershell
$env:UV_CACHE_DIR='C:\Users\user\Desktop\XIC_Extractor\.worktrees\local-minimum-param-optimization\.uv-cache'
uv run pytest tests\test_csv_to_excel.py tests\test_excel_sheets_contract.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

Run:

```powershell
git add scripts\csv_to_excel.py tests\test_csv_to_excel.py tests\test_excel_sheets_contract.py
git commit -m "docs: clarify workbook review flow"
```

---

## Task 8: Real Workbook Validation

**Files:**

- No code files expected.
- Use output path under `output\excel_review_validation\`.

- [ ] **Step 1: Run focused tests before real data**

Run:

```powershell
$env:UV_CACHE_DIR='C:\Users\user\Desktop\XIC_Extractor\.worktrees\local-minimum-param-optimization\.uv-cache'
uv run pytest tests\test_injection_rolling.py tests\test_csv_to_excel.py tests\test_review_report.py tests\test_settings_new_fields.py tests\test_settings_section_advanced.py -v
```

Expected: PASS.

- [ ] **Step 2: Run broad test suite**

Run:

```powershell
$env:UV_CACHE_DIR='C:\Users\user\Desktop\XIC_Extractor\.worktrees\local-minimum-param-optimization\.uv-cache'
uv run pytest --tb=short -q
```

Expected: PASS.

- [ ] **Step 3: Run 8-raw validation with review report and injection order**

Use a copied validation base directory so local config files do not leak into the repo. Configure:

```csv
data_dir,C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation
injection_order_source,C:\Users\user\Desktop\NTU cancer\Processed Data\DNA\Mzmine\new_test\SampleInfo.xlsx
resolver_mode,local_minimum
emit_score_breakdown,true
emit_review_report,true
parallel_mode,process
parallel_workers,4
rt_prior_library_path,
```

Run:

```powershell
$env:UV_CACHE_DIR='C:\Users\user\Desktop\XIC_Extractor\.worktrees\local-minimum-param-optimization\.uv-cache'
uv run python scripts\run_extraction.py --base-dir output\excel_review_validation\20260506_tissue8_visual --parallel-mode process --parallel-workers 4
```

Expected:

- Workbook is created under the validation base `output\` directory.
- HTML `review_report_*.html` is created.
- Workbook active sheet is `Overview`.
- `Diagnostics` sheet is hidden.
- `Summary` first columns are `Target`, `Role`, `ISTD Pair`, `Detected`, `Total`, `Detection %`.
- HTML contains `Detection Rate By Target`, `Flag Burden By Target`, `Detection / Flag Heatmap`, and `ISTD RT Injection Trend`.

If sandboxed process mode fails with Windows multiprocessing pipe `PermissionError [WinError 5]`, rerun the same command with approved escalation. Do not switch to serial mode for this validation unless the user explicitly permits it.

- [ ] **Step 4: Inspect generated workbook and HTML**

Run:

```powershell
$env:UV_CACHE_DIR='C:\Users\user\Desktop\XIC_Extractor\.worktrees\local-minimum-param-optimization\.uv-cache'
uv run python -c "from openpyxl import load_workbook; from pathlib import Path; p=next(Path('output/excel_review_validation').glob('**/xic_results_*.xlsx')); wb=load_workbook(p, read_only=True, data_only=True); print(p); print(wb.active.title); print(wb['Diagnostics'].sheet_state); print([wb['Summary'].cell(1,c).value for c in range(1,7)])"
```

Expected output includes:

```text
Overview
hidden
['Target', 'Role', 'ISTD Pair', 'Detected', 'Total', 'Detection %']
```

Find HTML sections:

```powershell
rg --no-ignore "Detection Rate By Target|Flag Burden By Target|ISTD RT Injection Trend|<svg" output\excel_review_validation
```

Expected: all four patterns are found in the generated HTML.

- [ ] **Step 5: Commit validation notes only if a tracked doc is updated**

If adding a brief validation note to the plan or retrospective, run:

```powershell
git add docs\superpowers\plans\2026-05-06-excel-visual-dashboard-and-debug-surfaces.md
git commit -m "docs: record visual dashboard validation"
```

If no tracked files change, do not create an empty commit.

---

## Final Review Checklist

Run before opening or updating a PR:

```powershell
$env:UV_CACHE_DIR='C:\Users\user\Desktop\XIC_Extractor\.worktrees\local-minimum-param-optimization\.uv-cache'
uv run ruff check scripts\csv_to_excel.py xic_extractor\injection_rolling.py xic_extractor\output\review_report.py tests\test_injection_rolling.py tests\test_csv_to_excel.py tests\test_review_report.py
uv run pytest tests\test_injection_rolling.py tests\test_csv_to_excel.py tests\test_review_report.py tests\test_settings_new_fields.py tests\test_settings_section_advanced.py -v
uv run pytest --tb=short -q
```

Expected:

- Ruff PASS.
- Focused tests PASS.
- Full suite PASS.
- Real validation workbook and HTML created.
- No changes to extraction/scoring selection logic.
- No tracked `config/settings.csv`.
- `rt_prior_library_path` remains available but clearly developer/debug-only.
