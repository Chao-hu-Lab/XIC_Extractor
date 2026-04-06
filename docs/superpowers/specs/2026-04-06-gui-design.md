# XIC Extractor GUI — Design Spec
**Date:** 2026-04-06  
**Status:** Approved  
**Technology:** PyQt6 (Python 3.10+)

---

## Overview

A PyQt6 desktop GUI that wraps the existing two-script pipeline:
- `scripts/01_extract_xic.ps1` — PowerShell: reads Thermo `.raw` files, outputs `xic_results.csv`
- `scripts/02_csv_to_excel.py` — Python: converts CSV to formatted Excel

The GUI replaces manual CSV editing and `run_pipeline.bat` with a single-window application. It does **not** rewrite the core extraction logic — it orchestrates the existing scripts.

---

## Decisions

| Question | Choice |
|----------|--------|
| Layout | Single-page vertical scroll |
| Theme | Light (white background, blue accent `#0969da`, green run `#1a7f37`) |
| Target editing | Inline table editing (click cell to edit) |
| Framework | PyQt6 |

---

## Architecture

### Files

```
XIC_Extractor/
├── gui/
│   ├── main.py           # Entry point — creates QApplication, launches MainWindow
│   ├── main_window.py    # MainWindow: QWidget with QScrollArea, assembles sections
│   ├── sections/
│   │   ├── settings_section.py   # Section ①: settings.csv editor
│   │   ├── targets_section.py    # Section ②: targets.csv inline table editor
│   │   ├── run_section.py        # Section ③: Run button + progress bar
│   │   └── results_section.py   # Section ④: Summary cards + open Excel button
│   ├── workers/
│   │   └── pipeline_worker.py   # QThread: runs PS1 then Python script, emits signals
│   ├── config_io.py              # Read/write settings.csv and targets.csv
│   └── styles.py                 # Qt stylesheet constants
└── ... (existing files unchanged)
```

### Component Responsibilities

**`main_window.py`**
- Top-level `QWidget` containing a `QScrollArea`
- Instantiates and stacks the four sections vertically
- Owns the `PipelineWorker` instance
- Connects worker signals → UI updates (progress bar, results section)

**`config_io.py`**
- `read_settings() -> dict` / `write_settings(dict)`
- `read_targets() -> list[dict]` / `write_targets(list[dict])`
- All file I/O goes through this module; sections never access CSV files directly

**`PipelineWorker(QThread)`**
- `run()` executes Step 1 (PowerShell) then Step 2 (Python) as subprocesses
- Emits:
  - `progress(int current, int total, str filename)` — parsed from PS1 stdout
  - `finished(dict summary)` — parsed summary stats after Step 2
  - `error(str message)` — on non-zero exit code

---

## UI Sections

### Section ① — 執行設定 (Settings)
- Fields: `data_dir`, `dll_dir`, `smooth_points` (int), `smooth_sigma` (float)
- `data_dir` and `dll_dir` have a 📁 Browse button → `QFileDialog.getExistingDirectory`
- Unsaved changes show a "💾 儲存設定" button; saved state shows "✓ 已儲存" in status bar
- Saves to `config/settings.csv` via `config_io.write_settings()`

### Section ② — 分析目標 (Targets Table)
- `QTableWidget` with columns: `Label`, `m/z`, `RT min`, `RT max`, `ppm`, `MS level`, `NL (Da)`, `[delete]`
- **Inline editing**: all cells are directly editable via `QTableWidget` item delegates
- `MS level` column uses a `QComboBox` delegate (MS1 / MS2)
- `NL (Da)` cell is editable only when `MS level == MS2`; otherwise shown as "—" and read-only
- Row colour: MS1 rows have blue-tinted badge, MS2 rows yellow-tinted badge (CSS-style via delegates)
- Toolbar buttons: "＋ 新增目標" (appends empty row), "⬆ 匯入 CSV" (replaces all rows from file picker)
- "💾 儲存目標" button appears when there are unsaved changes; saves to `config/targets.csv`
- Delete button (✕) on each row removes that row immediately

### Section ③ — 執行 (Run)
- "▶ 開始提取 XIC" button: full-width, green
- During run: button text becomes "⛔ 停止", clicking sends `SIGTERM` to subprocess
- `QProgressBar`: displays `{current}/{total} — {filename}`
- Disables settings + targets sections during run to prevent mid-run edits

### Section ④ — 結果摘要 (Results Summary)
- Hidden until first successful run; shown/updated after each run
- 2×2 summary card grid:
  - Per MS1 target: detected count (NL-confirmed if NL target exists)
  - NL WARN count
  - Total files processed
- "📂 開啟 Excel 結果" button: calls `os.startfile(excel_path)` (Windows)
- On run error: section shows red error message instead of cards

---

## Data Flow

```
User edits settings/targets
        ↓
config_io.write_*()  →  config/settings.csv, config/targets.csv
        ↓
User clicks "開始提取 XIC"
        ↓
PipelineWorker.run()
  → subprocess: powershell 01_extract_xic.ps1   (reads config, writes output/xic_results.csv)
     emit progress() per file parsed from stdout
  → subprocess: python 02_csv_to_excel.py        (reads csv, writes output/xic_results.xlsx)
     emit finished(summary)
     # summary dict structure:
     # {
     #   "total_files": int,
     #   "targets": [
     #     {"label": str, "detected": int, "total": int, "nl_confirmed": bool},
     #     ...
     #   ],
     #   "nl_warn_count": int,
     #   "excel_path": str
     # }
     # Parsed from 02_csv_to_excel.py stdout (e.g. "258.1085_RT detected (NL confirmed): 18/24")
        ↓
MainWindow receives finished signal
  → ResultsSection.update(summary)
  → ProgressBar shows 100%
  → Run button re-enabled
```

---

## Error Handling

| Scenario | Behaviour |
|----------|-----------|
| `data_dir` does not exist | Red border on field; "開始" button disabled |
| DLL not found (PS1 fails) | Error shown in results section; full stderr logged |
| No `.raw` files in dir | PS1 exits with warning; results section shows "0 files processed" |
| Python step fails | Error shown; CSV preserved for inspection |
| User clicks Stop | subprocess killed; partial CSV preserved; status shows "已中止" |

---

## Packaging (Future)

- PyInstaller single-file `.exe` via `gui/main.py` as entry point
- Icons and stylesheets bundled as resources
- Not in scope for initial implementation; structure is designed to support it

---

## Dependencies

```
PyQt6>=6.6
openpyxl>=3.1   # already used by 02_csv_to_excel.py
```

Python 3.10+ required (uses `X | Y` union type syntax).  
Install: `uv pip install PyQt6`

---

## Out of Scope

- macOS / Linux support (Windows-only: PowerShell + `os.startfile`)
- Plot/chart of XIC traces
- Multi-batch queue
- Authentication or network features
