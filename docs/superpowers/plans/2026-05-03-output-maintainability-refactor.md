# Output 完整度與可維護性重構 — 執行計畫

**日期**：2026-05-03（v3，合併 phase 並補強 codex hand-off）
**對應 spec**：`docs/superpowers/specs/2026-05-03-output-maintainability-design.md`
**執行者**：Codex
**預估**：4 PR，總計約 12–18 小時

---

## 執行原則

1. **每個 PR 獨立 merge**，不可 squash 跨 PR 提交
2. **不動分析行為**：每 PR 跑 `uv run pytest --tb=short -q`，並用 `scripts/validate_migration.py` 對 baseline raw 檔做 byte-level 數值比對
3. **TDD**：契約測試與「破壞契約的修改」放同一 PR
4. **Schema 變動先 deprecate 再刪**：保留 re-export 一個版本後再移除
5. **使用者體驗變動透明**：PR2/PR3 任一改動會影響 default behaviour，必須在 PR description 截圖前後對比
6. **指令統一 PowerShell 7+ 語法**（pwsh），避免 cmd 工具如 `fc`、`findstr`

---

## 依賴圖

```
        ┌──────────────────────────┐
        │ PR1  internal refactor   │  純內部重構，行為等價
        │ extractor.py 1582 → ≤500 │
        └────────────┬─────────────┘
                     │ 序列依賴
                     ▼
        ┌──────────────────────────┐
        │ PR2  Excel-first output  │  default 行為改變
        │ in-memory CSV + Run Meta │
        └────────────┬─────────────┘
                     │ 序列依賴（PR3 要把 PR2 加的 setting 收進 GUI）
                     ▼
        ┌──────────────────────────┐
        │ PR3  GUI Advanced区      │  GUI 重排
        │ basic / advanced 兩區    │
        └────────────┬─────────────┘
                     │ 可同步進行（每 PR 各自帶 partial docs）
                     ▼
        ┌──────────────────────────┐
        │ PR4  docs final-sweep    │  整合 README / CLAUDE.md
        │ retrospective + 截圖     │
        └──────────────────────────┘
```

PR1 → PR2 → PR3 是序列；PR4 在 PR3 merge 後執行。**不可平行**。

---

## PR Description 通用模板

每個 PR 開啟時 description 必須含以下欄位：

```markdown
## What
（1–3 句話描述本 PR 改動）

## Why
- 對應 spec：`docs/superpowers/specs/2026-05-03-output-maintainability-design.md` §X.Y
- 對應 plan：`docs/superpowers/plans/2026-05-03-output-maintainability-refactor.md` PRn

## Files changed (high-level)
- `path/to/file.py` — 動作（搬遷 / 新增 / 刪除）

## How to verify locally
```powershell
uv run pytest tests/test_xxx.py -v
# 其他驗收指令...
```

## Behavior change
- [ ] None（純內部重構）
- [ ] Default behavior 改變：（描述前後差異 + 截圖）

## Rollback strategy
（若 merge 後出問題如何處理）

## Out of scope
- ...
```

---

# PR1 — 內部重構（schema / writers / messages / 死碼清除）

**Branch**：`refactor/output-internal`
**對應原始 phase**：0 + 1 + 2 + 3 + 4
**行為改變**：無，所有輸出 byte-level 等同重構前
**預估**：4–6 小時

## 1.0 Baseline snapshot 與契約測試（先做）

### 1.0.1 建立 baseline

```powershell
# 在 master HEAD 跑一次完整 extraction 作為 byte-level 對照
uv run python -m scripts.run_extraction --base-dir .
New-Item -ItemType Directory -Force -Path output\baseline | Out-Null
Copy-Item output\xic_results.csv         output\baseline\xic_results.csv
Copy-Item output\xic_results_long.csv    output\baseline\xic_results_long.csv
Copy-Item output\xic_diagnostics.csv     output\baseline\xic_diagnostics.csv
Copy-Item output\xic_score_breakdown.csv output\baseline\xic_score_breakdown.csv -ErrorAction SilentlyContinue
Get-ChildItem output\xic_results_*.xlsx |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1 |
    Copy-Item -Destination output\baseline\xic_results.xlsx
```

把 `output\baseline\` 加進 `.gitignore`（不應入 commit）。

### 1.0.2 新增 schema regression test

新增 `tests/test_output_schema_contract.py`，驗證以下契約：

```python
def test_long_schema_has_14_columns():
    from xic_extractor.output.schema import LONG_HEADERS  # 暫時會 ImportError，PR1.1 後可過
    assert len(LONG_HEADERS) == 14
    assert LONG_HEADERS[0] == "SampleName"
    assert LONG_HEADERS[-1] == "Reason"

def test_diagnostic_schema_has_4_columns():
    from xic_extractor.output.schema import DIAGNOSTIC_HEADERS
    assert DIAGNOSTIC_HEADERS == ("SampleName", "Target", "Issue", "Reason")

def test_score_breakdown_schema_has_15_columns():
    from xic_extractor.output.schema import SCORE_BREAKDOWN_HEADERS
    assert len(SCORE_BREAKDOWN_HEADERS) == 15
```

此測試在 PR1.1 完成後必須通過，並在後續 PR 持續綠燈。

### 1.0.3 列舉現有 schema 引用點

```powershell
Get-ChildItem -Recurse -Include *.py -Path . |
    Where-Object { $_.FullName -notmatch '\\\.venv\\' } |
    Select-String -Pattern '_LONG_OUTPUT_FIELDS|_LONG_HEADERS|_DIAGNOSTIC_FIELDS|_DIAGNOSTIC_HEADERS|_SCORE_BREAKDOWN_FIELDS|_MS1_SUFFIXES' |
    Select-Object -ExpandProperty Path -Unique
```

把命中的檔案清單放進 PR description（用於 1.1 reviewer cross-check）。

## 1.1 抽出 schema（單一事實來源）

### 新增 `xic_extractor/output/__init__.py`（空檔）

### 新增 `xic_extractor/output/schema.py`

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class OutputColumn:
    name: str
    advanced: bool = False
    description: str = ""


# Wide format 每個 target 重複的後綴
MS1_SUFFIXES: tuple[str, ...] = (
    "RT", "Int", "Area", "PeakStart", "PeakEnd", "PeakWidth"
)

# Long format 主 schema（14 欄，與重構前完全相同）
LONG_COLUMNS: tuple[OutputColumn, ...] = (
    OutputColumn("SampleName"),
    OutputColumn("Group"),
    OutputColumn("Target"),
    OutputColumn("Role"),
    OutputColumn("ISTD Pair"),
    OutputColumn("RT", description="smoothed peak apex RT (min)"),
    OutputColumn("Area", description="raw integrated area"),
    OutputColumn("NL"),
    OutputColumn("Int", advanced=True, description="raw apex intensity"),
    OutputColumn("PeakStart", advanced=True),
    OutputColumn("PeakEnd", advanced=True),
    OutputColumn("PeakWidth", advanced=True),
    OutputColumn("Confidence"),
    OutputColumn("Reason"),
)
LONG_HEADERS: tuple[str, ...] = tuple(c.name for c in LONG_COLUMNS)
LONG_ADVANCED_HEADERS: frozenset[str] = frozenset(
    c.name for c in LONG_COLUMNS if c.advanced
)

# Diagnostic
DIAGNOSTIC_HEADERS: tuple[str, ...] = (
    "SampleName", "Target", "Issue", "Reason"
)

# Score breakdown（advanced，僅在 emit_score_breakdown=True 時使用）
SCORE_BREAKDOWN_HEADERS: tuple[str, ...] = (
    "SampleName", "Target",
    "symmetry", "local_sn", "nl_support", "rt_prior",
    "rt_centrality", "noise_shape", "peak_width",
    "Quality Penalty", "Quality Flags", "Total Severity",
    "Confidence", "Prior RT", "Prior Source",
)
```

### 改 `xic_extractor/extractor.py`：以 re-export 維持向後相容

```python
from xic_extractor.output.schema import (
    LONG_HEADERS as _LONG_OUTPUT_FIELDS,
    DIAGNOSTIC_HEADERS as _DIAGNOSTIC_FIELDS,
    SCORE_BREAKDOWN_HEADERS as _SCORE_BREAKDOWN_FIELDS,
    MS1_SUFFIXES as _MS1_SUFFIXES,
)
```

刪除原本的常數定義（`extractor.py:56-90` 範圍內的常數宣告）。

### 改 `scripts/csv_to_excel.py`

```python
from xic_extractor.output.schema import (
    LONG_HEADERS as _LONG_HEADERS,
    LONG_ADVANCED_HEADERS as _ADVANCED_HEADERS,
    DIAGNOSTIC_HEADERS as _DIAGNOSTIC_HEADERS,
)
```

刪除 `csv_to_excel.py:37-87` 範圍的本地常數。

## 1.2 抽出 CSV writers

### 搬遷清單（從 `extractor.py` 搬到新建的 `xic_extractor/output/csv_writers.py`）

| 函式 | extractor.py 行號 |
|---|---|
| `_write_output_csv` | 940 |
| `_write_diagnostics_csv` | 952 |
| `_write_long_output_csv` | 970 |
| `_write_score_breakdown_csv` | 1020 |
| `_long_output_rows` | 982 |
| `_set_long_ms1_values` | 1072 |
| `_set_long_peak_values` | 1081 |
| `_output_fieldnames` | 1095 |
| `_target_fieldnames` | 1102 |
| `_output_row` | 1109 |
| `_set_target_values` | 1123 |
| `_set_peak_values` | 1130 |
| `_format_peak_width` | 1152 |
| `_format_optional_number` | 1156 |
| `_format_optional_severity` | 1066 |

### 暴露 public API

```python
# xic_extractor/output/csv_writers.py

def write_all(
    config: ExtractionConfig,
    targets: list[Target],
    file_results: list[FileResult],
    diagnostics: list[DiagnosticRecord],
    *,
    emit_score_breakdown: bool,
) -> None:
    """寫四個 CSV 到 config 指定路徑。PR1 階段預設仍呼叫，PR2 才改為可選。"""
    write_wide_csv(config, targets, file_results)
    write_long_csv(config, targets, file_results)
    write_diagnostics_csv(config, diagnostics)
    if emit_score_breakdown:
        write_score_breakdown_csv(config, file_results)
```

### 改 `extractor.run()`

```python
from xic_extractor.output import csv_writers

def run(...) -> RunOutput:
    ...
    output = RunOutput(file_results=file_results, diagnostics=diagnostics)
    csv_writers.write_all(
        config, targets, file_results, diagnostics,
        emit_score_breakdown=config.emit_score_breakdown,
    )
    return output
```

> **注意**：本 PR 仍寫 4 個 CSV（行為等價）。PR2 才改為預設 in-memory。

### 新增 `tests/test_csv_writers.py`

直接測 `write_long_csv`，不再透過 `run()`。原本 `tests/test_extractor.py` 中對 CSV 內容的檢驗保留（黑箱整合測試）。

## 1.3 抽出 diagnostic messages 與 scoring factory

### 新增 `xic_extractor/output/messages.py`

從 `extractor.py` 搬：

| 函式 | extractor.py 行號 |
|---|---|
| `_peak_reason` | 825 |
| `_nl_reason` | 846 |
| `_multi_peak_reason` | 882 |
| `_tailing_reason` | 895 |
| `_istd_confidence_diagnostic` | 906 |
| `_build_diagnostics` | 768 |

API：

```python
def build_diagnostic_records(
    sample_name: str,
    target: Target,
    result: ExtractionResult,
    config: ExtractionConfig,
) -> list[DiagnosticRecord]: ...
```

### 新增 `xic_extractor/extraction/__init__.py`（空檔）

### 新增 `xic_extractor/extraction/scoring_factory.py`

從 `extractor.py` 搬：

| 函式 | extractor.py 行號 |
|---|---|
| `_build_scoring_context_factory` | 1403 |
| `_make_scoring_context_factory` | 1506 |
| `_compute_shape_metrics` | 1521 |
| `_selected_shape_metrics` | 1539 |
| `_selected_candidate` | 1549 |
| `_allow_prepass_anchor` | 1558 |
| `_paired_istd_fwhm` | 1565 |

### 移除 `try/except TypeError` 死碼

`extractor.py:392-405` 與 `633-648`：直接呼叫 `find_peak_and_area(rt, intensity, config, preferred_rt=..., strict_preferred_rt=..., scoring_context_builder=..., istd_confidence_note=...)`，不再 fallback。

新增測試 `tests/test_messages.py`、`tests/test_scoring_factory.py`。

## 1.4 移除 test-only `_write_xlsx`

### 確認唯一 caller

```powershell
Get-ChildItem -Recurse -Include *.py -Path . |
    Where-Object { $_.FullName -notmatch '\\\.venv\\' } |
    Select-String -Pattern '_write_xlsx' |
    Select-Object Path, LineNumber, Line
```

預期結果：只命中 `tests/test_output_columns.py` 與 `extractor.py` 自身。

### 把 `tests/test_output_columns.py` 改為直接測 `csv_to_excel.run`

或拆成兩個測試檔：

- `tests/test_output_schema.py` 測 schema 不變（已在 1.0.2 建立）
- `tests/test_csv_to_excel.py` 既有，保留

### 從 `extractor.py` 移除

| 函式 | extractor.py 行號 |
|---|---|
| `_write_xlsx` | 1166 |
| `_write_xic_results_sheet` | 1189 |
| `_write_summary_sheet` | 1235 |
| `_write_score_breakdown_sheet` | 1270 |
| `_iter_output_rows` | 1316 |

## 1.5 PR1 驗收條件（必須全綠才 merge）

```powershell
# 1. extractor.py 行數
$lines = (Get-Content xic_extractor\extractor.py | Measure-Object -Line).Lines
if ($lines -gt 500) { throw "extractor.py has $lines lines, expected <= 500" }

# 2. schema 唯一來源
$hits = Get-ChildItem -Recurse -Include *.py -Path . |
    Where-Object { $_.FullName -notmatch '\\\.venv\\' } |
    Select-String -Pattern '_LONG_OUTPUT_FIELDS|_LONG_HEADERS' |
    Select-Object -ExpandProperty Path -Unique
# 預期：只命中 output\schema.py、extractor.py（re-export shim）、csv_to_excel.py（re-export）
Write-Host "Schema referenced in:`n$($hits -join "`n")"

# 3. 全部測試
uv run pytest --tb=short -q

# 4. baseline byte-level 等同
uv run python -m scripts.run_extraction --base-dir .
$current  = (Get-FileHash output\xic_results_long.csv).Hash
$baseline = (Get-FileHash output\baseline\xic_results_long.csv).Hash
if ($current -ne $baseline) { throw "long CSV diverged from baseline" }

# 5. validate_migration.py（若有 raw 檔可用）
# uv run python scripts\validate_migration.py --strict ...
```

---

# PR2 — Excel-first output（in-memory CSV + Run Metadata sheet）

**Branch**：`feat/excel-first-output`
**對應原始 phase**：5 + 5.5 + 6.5（contract test 與引入它的修改同 PR）
**行為改變**：是 — `output/` 預設只剩 1 個 xlsx
**預估**：4–6 小時
**前置**：PR1 已 merge

## 2.1 新增 `xic_extractor/output/metadata.py`

```python
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version

from xic_extractor.config import ExtractionConfig


def app_version() -> str:
    try:
        return version("xic-extractor")
    except PackageNotFoundError:
        return "unknown"


def build_metadata_rows(
    config: ExtractionConfig,
) -> list[tuple[str, object]]:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return [
        ("config_hash", config.config_hash),
        ("app_version", app_version()),
        ("generated_at", ts),
        ("resolver_mode", config.resolver_mode),
        ("smooth_window", config.smooth_window),
        ("smooth_polyorder", config.smooth_polyorder),
        ("peak_min_prominence_ratio", config.peak_min_prominence_ratio),
        ("nl_min_intensity_ratio", config.nl_min_intensity_ratio),
        ("ms2_precursor_tol_da", config.ms2_precursor_tol_da),
    ]
```

## 2.2 新增 `xic_extractor/output/excel_pipeline.py`

新模組承擔「從 RunOutput 直接產 xlsx」的核心邏輯。函式簽章：

```python
from pathlib import Path

from openpyxl import Workbook

from xic_extractor.config import ExtractionConfig, Target
from xic_extractor.extractor import RunOutput


def write_excel_from_run_output(
    config: ExtractionConfig,
    targets: list[Target],
    run_output: RunOutput,
    *,
    output_path: Path,
) -> Path:
    """從 in-memory RunOutput 產 xlsx，不依賴 CSV 落地。

    內部呼叫 csv_to_excel 既有的 sheet builders，但餵的是 dict iterator
    而非從 CSV 讀回。
    """
    rows = _run_output_to_long_rows(run_output, targets)
    diagnostic_rows = _diagnostics_to_rows(run_output.diagnostics)
    score_breakdown_rows = (
        _run_output_to_score_breakdown_rows(run_output)
        if config.emit_score_breakdown
        else []
    )

    wb = Workbook()
    ws_data = wb.active
    ws_data.title = "XIC Results"
    _build_data_sheet(ws_data, rows)  # 從 csv_to_excel 引入

    ws_summary = wb.create_sheet("Summary")
    _build_summary_sheet(
        ws_summary, rows,
        count_no_ms2_as_detected=config.count_no_ms2_as_detected,
    )

    ws_targets = wb.create_sheet("Targets")
    _build_targets_sheet(ws_targets, targets)

    ws_diagnostics = wb.create_sheet("Diagnostics")
    _build_diagnostics_sheet(ws_diagnostics, diagnostic_rows)

    ws_metadata = wb.create_sheet("Run Metadata")
    _build_metadata_sheet(ws_metadata, config)  # 新增於 csv_to_excel

    if config.emit_score_breakdown and score_breakdown_rows:
        ws_breakdown = wb.create_sheet("Score Breakdown")
        _build_score_breakdown_sheet(ws_breakdown, score_breakdown_rows)

    # 永遠 landing 在 XIC Results（移除 auto-jump to Diagnostics）
    wb.active = wb.index(ws_data)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(output_path)
    wb.close()
    return output_path


def _run_output_to_long_rows(
    run_output: RunOutput, targets: list[Target]
) -> list[dict[str, str]]:
    """把 RunOutput 物件轉成與 csv_to_excel `_read_long_results` 同 shape 的
    dict list，使下游 sheet builder 可重用。"""
    # 邏輯與 extractor._long_output_rows + csv_to_excel._wide_to_long_rows
    # 兩者重疊；統一以 RunOutput 為單一來源。
    ...


def _diagnostics_to_rows(
    diagnostics: list[DiagnosticRecord],
) -> list[dict[str, str]]:
    return [
        {
            "SampleName": d.sample_name,
            "Target": d.target_label,
            "Issue": d.issue,
            "Reason": d.reason,
        }
        for d in diagnostics
    ]


def _run_output_to_score_breakdown_rows(
    run_output: RunOutput,
) -> list[dict[str, str]]:
    """對應既有 _write_score_breakdown_csv 的邏輯，但回傳 dict list。"""
    ...
```

## 2.3 在 `csv_to_excel.py` 加 `_build_metadata_sheet`

```python
def _build_metadata_sheet(ws, config: ExtractionConfig) -> None:
    ws.append(["Key", "Value"])
    _apply(ws.cell(row=1, column=1), **_header_style(_SAMPLE_HEADER))
    _apply(ws.cell(row=1, column=2), **_header_style(_SAMPLE_HEADER))
    for row_idx, (key, value) in enumerate(
        metadata.build_metadata_rows(config), start=2
    ):
        ws.cell(row=row_idx, column=1, value=key)
        ws.cell(row=row_idx, column=2, value=value)
    ws.column_dimensions["A"].width = 28
    ws.column_dimensions["B"].width = 48
    ws.freeze_panes = "A2"
```

## 2.4 移除 Diagnostics auto-jump

`csv_to_excel.py:655-656` 刪除：

```python
# 刪除：
# if diagnostics:
#     wb.active = wb.index(ws_diagnostics)
```

`excel_pipeline.write_excel_from_run_output` 已明確設 `wb.active = wb.index(ws_data)`。

## 2.5 加 setting `keep_intermediate_csv`

### `xic_extractor/config.py` `ExtractionConfig` dataclass 加欄位

```python
@dataclass(frozen=True)
class ExtractionConfig:
    ...
    keep_intermediate_csv: bool = False
```

### `xic_extractor/settings_schema.py` `CANONICAL_SETTINGS_DEFAULTS` 加

```python
"keep_intermediate_csv": "false",
```

### `_parse_settings_values` 加 `keep_intermediate_csv` 解析

仿照既有 `_parse_bool` 模式。

### `config/settings.example.csv` 加對應行

```
keep_intermediate_csv,false
```

## 2.6 改 `extractor.run()`：CSV 改為可選

```python
def run(...) -> RunOutput:
    ...
    output = RunOutput(file_results=file_results, diagnostics=diagnostics)
    if config.keep_intermediate_csv:
        csv_writers.write_all(
            config, targets, file_results, diagnostics,
            emit_score_breakdown=config.emit_score_breakdown,
        )
    return output
```

## 2.7 改 `scripts/run_extraction.py`：xlsx 直接從 RunOutput 產

```python
from xic_extractor import extractor
from xic_extractor.output.excel_pipeline import write_excel_from_run_output

def main():
    config, targets = load_config(...)
    run_output = extractor.run(config, targets, ...)

    excel_path = output_dir / f"xic_results_{timestamp}.xlsx"
    write_excel_from_run_output(
        config, targets, run_output, output_path=excel_path,
    )
```

同時新增 CLI-only 的 `--data-dir` override，供 real-data validation subset 使用。
這個 override 只影響本次 run，不回寫 `config/settings.csv`：

```powershell
uv run python -m scripts.run_extraction --base-dir . --data-dir C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation
```

`--skip-excel` 仍保留舊語意：跳過 xlsx，但要強制保留 CSV-only 輸出。

## 2.8 改 `gui/workers/pipeline_worker.py`

把現行透過 `csv_to_excel.run(base_dir)` 的呼叫改為走 `write_excel_from_run_output(config, targets, run_output, output_path=...)`。worker 從 `extractor.run` 拿到 `RunOutput`，直接傳給新 pipeline，不經 CSV。

## 2.9 移除 `csv_to_excel._run_with_config` 的 unlink

```python
# 刪除：
# for _csv in [...]:
#     _csv.unlink(missing_ok=True)
```

預設不寫 CSV，無需清理；若 `keep_intermediate_csv=True` 則使用者明確要求保留。

`csv_to_excel.run(base_dir)` 仍保留，作為「從 CSV 重組 xlsx」的獨立工具（可用於 debug 場景）。

## 2.10 契約測試（與本 PR 同步引入）

新增 `tests/test_excel_sheets_contract.py`：

```python
from openpyxl import load_workbook


def test_default_output_only_has_one_xlsx(tmp_run_dir):
    """預設執行後 output/ 只有 1 個 xlsx 檔。"""
    _run_pipeline(tmp_run_dir, keep_intermediate_csv=False)
    output_dir = tmp_run_dir / "output"
    csvs = list(output_dir.glob("*.csv"))
    xlsx = list(output_dir.glob("*.xlsx"))
    assert len(csvs) == 0, f"unexpected CSVs: {[p.name for p in csvs]}"
    assert len(xlsx) == 1


def test_keep_intermediate_csv_emits_csvs(tmp_run_dir):
    _run_pipeline(tmp_run_dir, keep_intermediate_csv=True)
    output_dir = tmp_run_dir / "output"
    expected = {"xic_results.csv", "xic_results_long.csv", "xic_diagnostics.csv"}
    actual = {p.name for p in output_dir.glob("*.csv")}
    assert expected.issubset(actual)


def test_default_xlsx_has_5_sheets(tmp_run_dir):
    xlsx_path = _run_pipeline(tmp_run_dir, emit_score_breakdown=False)
    wb = load_workbook(xlsx_path)
    assert set(wb.sheetnames) == {
        "XIC Results", "Summary", "Diagnostics", "Targets", "Run Metadata"
    }


def test_score_breakdown_appears_when_enabled(tmp_run_dir):
    xlsx_path = _run_pipeline(tmp_run_dir, emit_score_breakdown=True)
    wb = load_workbook(xlsx_path)
    assert "Score Breakdown" in wb.sheetnames


def test_landing_sheet_when_diagnostics_empty(tmp_run_dir):
    xlsx_path = _run_pipeline(tmp_run_dir, force_no_diagnostics=True)
    wb = load_workbook(xlsx_path)
    assert wb.active.title == "XIC Results"


def test_landing_sheet_when_diagnostics_present(tmp_run_dir):
    xlsx_path = _run_pipeline(tmp_run_dir, force_diagnostics=True)
    wb = load_workbook(xlsx_path)
    assert wb.active.title == "XIC Results"


def test_run_metadata_sheet_has_required_keys(tmp_run_dir):
    xlsx_path = _run_pipeline(tmp_run_dir)
    wb = load_workbook(xlsx_path)
    ws = wb["Run Metadata"]
    keys = {ws.cell(row=r, column=1).value for r in range(2, ws.max_row + 1)}
    for required in {"config_hash", "app_version", "generated_at", "resolver_mode"}:
        assert required in keys
```

## 2.11 PR2 驗收條件

### 2.11.0 Real-data validation 分層

除非本 PR 是 release gate、重大算法改動，或需要建立 byte-level baseline，否則
不要每次跑完整 tissue batch（85 個 `.raw`）。PR-level real-data smoke 使用：

```powershell
uv run python -m scripts.run_extraction --base-dir . --data-dir C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation
```

目前 validation subset 由使用者維護，位於
`C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation`，含 8 個代表性 `.raw`。
驗收重點是 pipeline 能跑完、預設輸出 0 CSV + 1 xlsx、sheet contract 正確。

```powershell
# 1. 跑全部測試
uv run pytest --tb=short -q

# 2. validation subset 預設執行 output 只有 1 xlsx
Remove-Item output\xic_*.csv, output\xic_results_*.xlsx -ErrorAction SilentlyContinue
uv run python -m scripts.run_extraction --base-dir . --data-dir C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation
$csv_count  = (Get-ChildItem output\*.csv).Count
$xlsx_count = (Get-ChildItem output\*.xlsx).Count
if ($csv_count -ne 0)  { throw "expected 0 CSV, got $csv_count" }
if ($xlsx_count -ne 1) { throw "expected 1 xlsx, got $xlsx_count" }

# 3. xlsx sheet 集合正確
$py = @"
from openpyxl import load_workbook
import glob
wb = load_workbook(sorted(glob.glob('output/xic_results_*.xlsx'))[-1])
expected = {'XIC Results','Summary','Diagnostics','Targets','Run Metadata'}
actual = set(wb.sheetnames)
assert actual == expected, f'expected {expected}, got {actual}'
assert wb.active.title == 'XIC Results', f'landing = {wb.active.title}'
print('OK')
"@
$py | uv run python

# 4. keep_intermediate_csv=True 時 CSV 與 baseline 等同
# 暫改 settings.csv 跑一次後比對
# (Get-FileHash output\xic_results_long.csv).Hash 對 baseline
```

完整 85 `.raw` 驗證只在 release、重大算法變更、或明確需要 cohort-level
regression 時執行；不要作為 PR2 之後每次小改動的預設驗收。

---

# PR3 — GUI Advanced settings 區

**Branch**：`feat/gui-advanced-settings`
**對應原始 phase**：6
**行為改變**：UI 重排，所有 settings.csv key 完全相容
**預估**：3–4 小時
**前置**：PR2 已 merge（要把 PR2 加的 `keep_intermediate_csv` 收進 GUI Advanced）

## 3.1 重構 `gui/sections/settings_section.py`

### 兩區設計

**基本區（一律展開）**：

- `data_dir`, `dll_dir`
- `smooth_window`, `smooth_polyorder`
- `peak_rel_height`, `peak_min_prominence_ratio`
- `ms2_precursor_tol_da`, `nl_min_intensity_ratio`
- `count_no_ms2_as_detected`

**Advanced 區（預設摺疊）**：

- 區塊標題：「⚙ Advanced — debug 與方法開發專用」
- 區塊頂部說明 label：「下列選項僅在除錯或方法開發時需要。日常使用請保持預設值。」
- `keep_intermediate_csv`（PR2 新增）
- `emit_score_breakdown`
- `dirty_matrix_mode`
- `rolling_window_size`
- `rt_prior_library_path`
- `injection_order_source`
- `resolver_mode` 與 `resolver_*` 系列（共 8 個）
- `nl_rt_anchor_search_margin_min` / `nl_rt_anchor_half_window_min` / `nl_fallback_half_window_min`

## 3.2 Collapsible widget 實作（可靠版本）

不要用 `findChildren(QWidget).setVisible()`（會 traverse 過頭，把容器自身也藏掉）。改用「獨立 inner container」模式：

```python
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame, QToolButton, QVBoxLayout, QWidget,
)


class CollapsibleSection(QWidget):
    """可摺疊區塊。標題列為 QToolButton，內容為獨立 QFrame，
    透過 setVisible 切換整個 inner frame 顯示。"""

    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._toggle = QToolButton(self)
        self._toggle.setText(title)
        self._toggle.setCheckable(True)
        self._toggle.setChecked(False)  # 預設摺疊
        self._toggle.setArrowType(Qt.ArrowType.RightArrow)
        self._toggle.setToolButtonStyle(
            Qt.ToolButtonStyle.ToolButtonTextBesideIcon
        )
        self._toggle.toggled.connect(self._on_toggled)

        self._content = QFrame(self)
        self._content_layout = QVBoxLayout(self._content)
        self._content.setVisible(False)

        outer = QVBoxLayout(self)
        outer.addWidget(self._toggle)
        outer.addWidget(self._content)
        outer.setContentsMargins(0, 0, 0, 0)

    def add_row(self, widget: QWidget) -> None:
        self._content_layout.addWidget(widget)

    def _on_toggled(self, checked: bool) -> None:
        self._content.setVisible(checked)
        self._toggle.setArrowType(
            Qt.ArrowType.DownArrow if checked else Qt.ArrowType.RightArrow
        )
```

把 advanced 區塊內所有控件 `addWidget` 到 `CollapsibleSection._content_layout`，避免 `findChildren` 風險。

## 3.3 載入 / 儲存設定不變

`gui/config_io.py` 不動 — 所有 settings key 仍走同一個 `settings.csv`，只是 GUI 視覺分區。

## 3.4 測試

新增 `tests/test_settings_section_advanced.py`：

```python
def test_advanced_section_collapsed_by_default(qtbot):
    section = SettingsSection(...)
    qtbot.addWidget(section)
    assert section.advanced_section.isVisible()  # widget 自身顯示
    assert not section.advanced_section._content.isVisible()  # 內容摺疊


def test_advanced_section_expands_on_click(qtbot):
    section = SettingsSection(...)
    qtbot.addWidget(section)
    qtbot.mouseClick(section.advanced_section._toggle, Qt.MouseButton.LeftButton)
    assert section.advanced_section._content.isVisible()


def test_advanced_section_contains_required_flags(qtbot):
    section = SettingsSection(...)
    qtbot.addWidget(section)
    advanced_keys = section.advanced_section_field_keys()
    assert "keep_intermediate_csv" in advanced_keys
    assert "emit_score_breakdown" in advanced_keys
    assert "dirty_matrix_mode" in advanced_keys
    assert "rt_prior_library_path" in advanced_keys
    assert "injection_order_source" in advanced_keys


def test_settings_csv_round_trip_unchanged(qtbot, tmp_path):
    """確保 GUI 視覺分區後，settings.csv 載入/儲存內容與舊版相容。"""
    ...
```

## 3.5 README 同步

`README.md` 的 `Settings` 章節：

- 把 settings 表格分為「基本」與「進階」兩段
- 加註：「進階設定預設摺疊；除錯或方法開發者需要時展開」
- 加 GUI Advanced 區截圖（截圖檔放 `assets/screenshots/`）

## 3.6 PR3 驗收條件

```powershell
# 1. 全部測試
uv run pytest --tb=short -q

# 2. 啟動 GUI 視覺驗證（手動）
uv run python -m gui.main
# Checklist：
# [ ] Settings 區頂部為基本控件（9 個）
# [ ] 下方有「⚙ Advanced」可摺疊區塊
# [ ] 預設摺疊狀態（看不到 Advanced 內容）
# [ ] 點擊展開後可看到 keep_intermediate_csv 等控件
# [ ] 改 Advanced 區的值後儲存，重開 GUI 值仍正確

# 3. settings.csv 相容性
$old = Get-Content config\settings.csv
# 用舊格式 settings 啟動 GUI，確認可正常載入
```

---

# PR4 — 文件 final-sweep

**Branch**：`docs/output-refactor-followup`
**對應原始 phase**：7
**行為改變**：無
**預估**：1–2 小時
**前置**：PR1+PR2+PR3 全部 merge

## 4.1 README 整體掃描

確認以下章節已在 PR1–3 過程更新；若有遺漏在此補：

- `輸出檔案` 章節：說明預設只有 1 個 xlsx，5 sheet 各自用途，`Run Metadata` 內容
- `Settings` 章節：基本 / 進階兩段表格
- `常見錯誤` 章節：`keep_intermediate_csv` 與 `emit_score_breakdown` 何時開啟
- 截圖：GUI Advanced 區位置（`assets/screenshots/gui-advanced.png`）

## 4.2 更新 CLAUDE.md（若有專案級）

加入新進維護者守則：

- 「輸出 schema 改動只能在 `xic_extractor/output/schema.py`」
- 「新增 setting 預設應先放 GUI Advanced 區，待證實使用者頻繁需要才升級到基本區」
- 「不要再加 CSV header；重現性 metadata 走 xlsx `Run Metadata` sheet」

## 4.3 撰寫 retrospective

新增 `docs/superpowers/notes/2026-05-XX-output-refactor-retrospective.md`：

- 行數變化（before / after）
- 測試新增量（依 PR 列表）
- xlsx sheet 數量變化
- output/ 預設檔案數量變化（5 → 1）
- 過程中發現的非預期收穫 / 副作用

## 4.4 PR4 驗收條件

```powershell
# 1. README 內無過時敘述
Select-String -Path README.md -Pattern 'xic_results.csv|xic_results_long.csv|xic_diagnostics.csv'
# 預期：每處 mention CSV 都搭配 keep_intermediate_csv 說明

# 2. retrospective 與 CLAUDE.md（若有）已 commit
git status
```

---

## 整體最終驗收門檻（PR4 merge 前）

### 內部品質

- [ ] `xic_extractor/extractor.py` 行數 ≤ 500（用 `(Get-Content ... | Measure-Object -Line).Lines` 計）
- [ ] `Select-String -Pattern '_LONG_OUTPUT_FIELDS|_LONG_HEADERS'` 只命中 `output/schema.py` 與 re-export shim
- [ ] `uv run pytest --tb=short -q` 全綠
- [ ] `scripts/validate_migration.py --strict` 對 baseline raw 通過

### 行為等價

- [ ] xlsx 內 `XIC Results` sheet 數值欄位 byte-level 等同 PR1.0 baseline
- [ ] `keep_intermediate_csv=true` 時 4 CSV byte-level 等同 baseline
- [ ] long format 欄位數 = 14（與重構前相同）

### 使用者體驗

- [ ] 預設執行後 `output/` 目錄僅含 1 個 xlsx 檔
- [ ] xlsx 開啟時 active sheet 為 `XIC Results`，不論 diagnostics 是否為空
- [ ] xlsx 含且僅含 5 sheet：`XIC Results` / `Summary` / `Diagnostics` / `Targets` / `Run Metadata`
- [ ] `emit_score_breakdown=true` 才有 `Score Breakdown` 第 6 sheet
- [ ] `Run Metadata` sheet 含 `config_hash`、`app_version`、`generated_at`、`resolver_mode`
- [ ] GUI Settings 畫面有可摺疊 `Advanced` 區，預設摺疊
- [ ] Advanced 區包含 `keep_intermediate_csv`、`emit_score_breakdown`、`dirty_matrix_mode`、`rt_prior_library_path`、`injection_order_source`、resolver_*

### CI

- [ ] CI（self-hosted runner Windows）綠燈

---

## 回滾策略

| PR | 回滾方式 | 副作用 |
|---|---|---|
| PR1 | `git revert`；re-export shim 確保舊 import 不壞 | 無 |
| PR2 | `git revert` 或設 `keep_intermediate_csv=true`（暫時恢復 CSV） | revert 後 xlsx 少 `Run Metadata` sheet |
| PR3 | `git revert`；settings.csv 內容仍相容，GUI 退回平鋪 | 無 |
| PR4 | `git revert`（純文件） | 無 |

最壞情況：PR2/PR3 在 release 前發現使用者體驗變動造成困擾 → 透過 settings 預設值翻轉即可（不需 code revert），留待下個 minor release 整合反饋。

---

## 不在本計畫的後續議題

- 觀測 m/z / ppm 偏差欄位（需 `raw_reader` 改 API）
- `Summary` sheet 18 欄精簡（待使用者實際使用一輪後再決定哪幾欄是雜訊）
- Parquet / Arrow 輸出格式選項
- xlsx 開啟自動展開合併儲存格的 UX 微調
- GUI Advanced 區內子分組（debug / 方法開發 / experimental）— 等 advanced flag 數量 > 10 再考慮
