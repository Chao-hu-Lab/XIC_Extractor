# Output 完整度與可維護性重構 — 設計大綱

**日期**：2026-05-03（v2，依使用者 review 修訂）
**狀態**：Draft
**作者**：Claude（Opus 4.7）
**對應計畫**：`docs/superpowers/plans/2026-05-03-output-maintainability-refactor.md`

---

## 1. 背景

XIC_Extractor 目前的輸出層由兩個位置維護：

- `xic_extractor/extractor.py`（1582 行）寫四個 CSV：`xic_results.csv`、`xic_results_long.csv`、`xic_diagnostics.csv`、`xic_score_breakdown.csv`
- `scripts/csv_to_excel.py`（782 行）讀回上述 CSV，組合 Excel，最後 `unlink` 砍掉 CSV

實際使用者需求（已澄清）：

- **Excel 是唯一日常交付**；CSV 對使用者交互性差，不是審閱介面
- **可讀性優先於完整度**：日常輸出必須乾淨簡潔
- **Advanced 模式分離**：除錯 / 方法開發者需要的詳盡資訊應在 GUI 進階設定區明確開啟，不污染日常輸出
- **下游分析也走 Excel**：不需要把 CSV 當交付保留

本 spec 將上述使用者需求與既有 round-trip pipeline 的維護性問題一併處理。

## 2. 問題定義（What & Why）

### 2.1 Schema 重複定義

| 概念 | 位置 A | 位置 B |
|---|---|---|
| Long output 欄位（14 個） | `extractor.py` `_LONG_OUTPUT_FIELDS` | `csv_to_excel.py` `_LONG_HEADERS` |
| Diagnostic 欄位 | `extractor.py` `_DIAGNOSTIC_FIELDS` | `csv_to_excel.py` `_DIAGNOSTIC_HEADERS` |
| Score breakdown 欄位 | `extractor.py` `_SCORE_BREAKDOWN_FIELDS` | `csv_to_excel.py` 動態從 row keys 推導 |
| Wide format 欄位 | `extractor.py` `_MS1_SUFFIXES` | `csv_to_excel.py` 字串拼 `f"{label}_Area"` |

**風險**：任一處改動沒同步另一處 → 直接 KeyError 或欄位漏寫，且 type checker 抓不到。

### 2.2 `extractor.py` 職責爆炸

單一檔案承擔：orchestration、RT window 計算、ISTD recovery、sample drift 估計、diagnostic 文字組合、severity 應用、scoring context factory、CSV 寫入 ×4、XLSX 寫入 ×4、format helpers。

至少四個獨立關注點被混合，**單一職責原則被打破**。後果：

- 任何小修改都要載入 1582 行上下文
- 測試必須 mock 多個 IO；`run()` 同時做副作用與回傳
- 新進維護者難以建立心智模型

### 2.3 重現性追溯斷鏈

`ExtractionConfig.config_hash`（SHA-256[:8]）已在 `config.py:31` 計算並存入 config，但**沒有任何輸出檔記錄它**。一個月後拿到 `xic_results_20260403_1530.xlsx` 無法回推當時的 settings/targets。

### 2.4 `_write_xlsx` 是 test-only dead-ish code

`extractor.py:1166` 的 `_write_xlsx` 只在 `tests/test_output_columns.py` 被呼叫；pipeline 從未呼叫。它與 `csv_to_excel.py` 構成**第二條 Excel 寫入路徑**，邏輯較簡陋，會誤導維護者。

### 2.5 `try/except TypeError` 把 signature 演進當 fallback

`extractor.py:392-405` 與 `633-648` 兩處用 `try/except TypeError` 接住 `find_peak_and_area` 不接受新參數的情況。`signal_processing` 是同 repo 模組，這層 fallback 從首次合入就是死碼，但讀起來像「支援外部 plugin」的相容層。

### 2.6 CSV 中介層常駐輸出，污染交付區

- `extractor` 寫 4 個 CSV → `csv_to_excel` 讀 CSV → 寫 Excel → `unlink` CSV
- 但 `unlink` 行為不直觀：失敗時 CSV 會留下，且使用者沒有 opt-out 機制保留 CSV 做除錯
- 這條設計實際上把 CSV 當「臨時 IPC 格式」用，但它在 `output/` 目錄的露出讓使用者誤以為是交付物

### 2.7 GUI 設定無 advanced/basic 區分

目前 `gui/sections/settings_section.py` 把所有 settings 平鋪呈現。
日常使用者只需要設 `data_dir`、`dll_dir`、`smooth_window` 等基本項，但畫面上同時顯示 `dirty_matrix_mode`、`rt_prior_library_path`、`injection_order_source`、`emit_score_breakdown`、`resolver_*` 等進階參數，**新使用者認知負荷高**。

## 3. 目標（What we want）

### 3.1 可維護性目標

1. **Single source of truth**：所有輸出欄位定義集中於一處。
2. **`extractor.py` 拆分**：純 orchestration ≤ 500 行，IO 分離。
3. **死碼清除**：移除 `_write_xlsx` 與 `try/except TypeError` fallback。
4. **`run()` 純運算可選 IO**：caller 決定是否寫檔。

### 3.2 完整度目標（精簡版）

只保留一個核心需求：**重現性追溯** — 任何時間點拿到 xlsx 都能回推產生它的 config_hash、app_version、generated_at、resolver_mode。

> 與前版差異：移除「3 個 advanced 欄位寫入 long format」「emit_score_breakdown 預設改 true」等需求 — 這些屬於 advanced 模式，不入日常輸出。

### 3.3 不變動項目

- 分析行為（peak detection、scoring、NL confirmation）一律不動
- Excel 視覺樣式（色彩、合併儲存格、欄寬）不動
- Settings/Targets schema 不動
- **Long format 欄位數保持 14 欄**（不增不減）
- **Wide format 欄位定義不動**

### 3.4 使用者體驗目標（新增）

對應使用者「降低使用負擔」的核心訴求：

1. **預設 output/ 只有 1 個 xlsx**：CSV 為內部中介，預設不留檔
2. **xlsx 內 sheet 數量分層**：
   - 日常 sheet（一律產出）：`XIC Results` / `Summary` / `Diagnostics`
   - 方法資訊 sheet（一律產出）：`Targets` / `Run Metadata`
   - Advanced sheet（GUI toggle 開啟才有）：`Score Breakdown`
3. **Landing sheet = `XIC Results`**：移除「有 Diagnostics 時自動跳到 Diagnostics」這個會打擾審閱節奏的行為，改為 `XIC Results` 為一律 landing
4. **Long format 欄位數不增加**：使用者要更詳細資訊時走 Advanced sheet 或 Score Breakdown，不擴張主表
5. **GUI Advanced settings 區**：所有 debug / 方法開發 flag 集中於可摺疊區塊，預設摺疊

## 4. 解決方案概觀

### 4.1 新增模組（內部重構）

```
xic_extractor/
├── output/
│   ├── __init__.py
│   ├── schema.py          ← 唯一 schema 定義來源
│   ├── csv_writers.py     ← 從 extractor.py 搬來
│   ├── metadata.py        ← config_hash / version / timestamp 組成（給 xlsx 用）
│   └── messages.py        ← _xxx_reason 系列搬來
├── extraction/
│   └── scoring_factory.py ← 從 extractor.py 搬來
```

`scripts/csv_to_excel.py` 改成 `import xic_extractor.output.schema`，移除自己那份 `_LONG_HEADERS` 等常數。

### 4.2 Schema 定義範例

```python
# xic_extractor/output/schema.py
from dataclasses import dataclass

@dataclass(frozen=True)
class OutputColumn:
    name: str
    advanced: bool = False
    description: str = ""

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
```

> 14 欄維持不變。`advanced=True` 的 4 欄延續既有 Excel hidden / outline 行為，不另外加新欄位。

### 4.3 重現性 metadata：xlsx `Run Metadata` sheet

不在 CSV header 寫 metadata（避免污染下游 CSV consumer）。改為在 xlsx 新增一個 `Run Metadata` sheet，欄位：

| Key | Value 範例 |
|---|---|
| config_hash | `abc12345` |
| app_version | `0.2.0` |
| generated_at | `2026-05-03T11:23:00Z`（ISO 8601 UTC） |
| resolver_mode | `local_minimum` |
| smooth_window | `7` |
| smooth_polyorder | `2` |
| peak_min_prominence_ratio | `0.05` |
| nl_min_intensity_ratio | `0.05` |
| ms2_precursor_tol_da | `0.5` |

xlsx 檔名同時保留 timestamp（既有），但**不**加 hash（避免檔名過長）。

### 4.4 CSV 改為 debug-only 中介格式

- `extractor.run()` 預設**直接** in-memory 把 `RunOutput` 交給 `csv_to_excel` 流程，不落地 CSV
- 新增 setting `keep_intermediate_csv: bool = False`（屬於 GUI Advanced 區）
  - `False`（預設）：完全不寫 CSV
  - `True`：保留所有 4 個 CSV 在 `output/` 旁邊 xlsx
- 移除 `csv_to_excel.py:_run_with_config` 末尾的 `_csv.unlink(missing_ok=True)`（不再需要，因為預設不寫）

### 4.5 GUI Advanced settings 區

`gui/sections/settings_section.py` 重構成：

```
┌─ Settings ─────────────────────────┐
│ [基本區]                            │
│ data_dir          [browse...]       │
│ dll_dir           [browse...]       │
│ smooth_window     [7]               │
│ smooth_polyorder  [2]               │
│ peak_rel_height   [0.5]             │
│ peak_min_prominence_ratio [0.05]    │
│ ms2_precursor_tol_da [0.5]          │
│ nl_min_intensity_ratio [0.05]       │
│ count_no_ms2_as_detected [☐]        │
│                                     │
│ ▼ Advanced（預設摺疊）              │
│   ⚙ Debug / 方法開發者使用          │
│   keep_intermediate_csv [☐]         │
│   emit_score_breakdown   [☐]        │
│   dirty_matrix_mode      [☐]        │
│   rt_prior_library_path  [...]      │
│   injection_order_source [...]      │
│   resolver_mode          [...]      │
│   nl_rt_anchor_*         [...]      │
└─────────────────────────────────────┘
```

- Advanced 區用 `QGroupBox` + `setCheckable(True)` 或可摺疊 widget 實作
- 區塊頂部一行說明：「下列選項僅在除錯或方法開發時需要。日常使用請保持預設值。」
- 設定值仍走同一份 `settings.csv`，只是 GUI 視覺上分區

### 4.6 Diagnostics 不再 auto-jump

目前 `csv_to_excel.py:655-656`：

```python
if diagnostics:
    wb.active = wb.index(ws_diagnostics)
```

移除此行。Excel 一律落在 `XIC Results`。Diagnostics 透過 sheet tab 切換，不打擾主審閱動線。

## 5. 範圍邊界

### In scope

- 上述 `xic_extractor/output/`、`xic_extractor/extraction/scoring_factory.py` 新模組
- `extractor.py` 縮減至 orchestration（不含 CSV/XLSX 寫入）
- `scripts/csv_to_excel.py` 改用共享 schema、串接 in-memory 路徑、新增 `Run Metadata` sheet、移除 auto-jump
- 移除 `_write_xlsx`（test 移轉到 csv_to_excel）與 `try/except TypeError` 死碼
- 新增 `keep_intermediate_csv` setting
- GUI `settings_section.py` 拆分基本 / Advanced 兩區
- 對應的單元測試與 schema regression test

### Out of scope（延後）

- Peak scoring 邏輯改動
- 新增分析行為相關欄位（如觀測 m/z）— 需 `raw_reader` API 變更
- `SUMMARY_HEADERS` 欄位精簡（目前 18 欄，可審視，但本次保持不動）
- Parquet / Arrow 輸出格式選項
- xlsx 開啟時自動展開 Group/合併儲存格的 UX 微調

## 6. 風險評估

| 風險 | 機率 | 影響 | 緩解 |
|---|---|---|---|
| Schema 拆出後現有 import path 壞掉 | 高 | 中 | 保留 `extractor.py` 內舊常數作為 re-export，標記 `# DEPRECATED` |
| `_write_xlsx` 移除導致 `test_output_columns` 壞 | 高 | 低 | 同步遷移測試到 `csv_to_excel` 路徑 |
| 取消 CSV 落地後，使用者要 debug 找不到中間檔 | 中 | 中 | 提供 `keep_intermediate_csv` flag；GUI Advanced 區明確標示 |
| Advanced section UX 偏離既有使用者習慣 | 中 | 中 | 現有 settings.csv key 完全保留；只動 GUI 視覺分區；release notes 截圖示意 |
| 移除 Diagnostics auto-jump 讓使用者沒注意到問題 | 低 | 中 | `Summary` sheet 已含 detection 計數；GUI Results 區已顯示 diagnostics count |
| `Run Metadata` sheet 多一頁讓使用者誤點 | 低 | 低 | 放在 sheet tab 最右側；`hidden` 不設，但不是 default |

### 6.1 Real-data validation 分層

完整 tissue batch（目前 85 個 `.raw`）耗時高，不應作為每次 PR 或小改動的
預設驗證。後續 real-data validation 分為三層：

1. **PR / 日常 smoke**：預設使用固定 validation subset：
   `C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation`。此資料夾由使用者維護，
   目前含 8 個代表性 `.raw`，用來快速驗證 pipeline 可跑完、output contract
   正確、sheet/CSV 行為正確。
2. **方法學變更**：peak picking、scoring、NL/RT anchoring 等行為改動，先跑
   validation subset；若 subset 顯示回歸或結果需要 cohort-level 判斷，再升級跑
   完整 tissue batch。
3. **Release / merge 前重大 gate**：只有在 release、重大算法變更、或需要建立
   byte-level baseline 時，才跑完整 85 `.raw`。

CLI 必須支援不修改 `config/settings.csv` 的資料夾覆寫：

```powershell
uv run python -m scripts.run_extraction --base-dir . --data-dir C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation
```

## 7. 驗收條件

### 可維護性（內部）

1. `xic_extractor/extractor.py` 行數 ≤ 500
2. `grep -r "_LONG_OUTPUT_FIELDS\|_LONG_HEADERS"` 只命中 `output/schema.py` 與 re-export shim
3. `pytest` 全綠（含新增 schema regression test 與 metadata test）
4. `scripts/validate_migration.py --strict` 對 baseline raw 通過

### 完整度（重現性）

5. xlsx 內含 `Run Metadata` sheet，欄位至少含 `config_hash`、`app_version`、`generated_at`、`resolver_mode`
6. 同一份 settings + targets + raw 跑前後，`XIC Results` sheet 數值欄位 byte-level 等同
7. PR-level real-data smoke 使用 validation subset，除非本次變更屬 release gate 或重大算法改動，否則不要求每次跑完整 85 `.raw`

### 使用者體驗

8. 預設執行後 `output/` 目錄**僅含 1 個** xlsx 檔（無 CSV）
9. xlsx 開啟時 active sheet 為 `XIC Results`，不論 diagnostics 是否為空
10. xlsx 含且僅含 5 個日常 sheet：`XIC Results` / `Summary` / `Diagnostics` / `Targets` / `Run Metadata`
11. `emit_score_breakdown=true` 時才額外含 `Score Breakdown` sheet
12. `keep_intermediate_csv=true` 時才額外輸出 4 個 CSV
13. `Long format` sheet 欄位數 = 14（與重構前相同）
14. CLI 支援 `--data-dir` 作為本次 run 的 validation subset 覆寫，不修改 `settings.csv`
15. GUI Settings 畫面有可摺疊 `Advanced` 區，預設摺疊
16. Advanced 區至少包含 `keep_intermediate_csv`、`emit_score_breakdown`、`dirty_matrix_mode`、`rt_prior_library_path`、`injection_order_source`

## 8. 參考

- 現況分析：本次 session 對 `extractor.py`、`csv_to_excel.py`、`signal_processing.py`、`config.py` 的逐行檢視
- UX pattern：progressive disclosure / advanced settings panel（見 Skyline、TraceFinder、MZmine 介面慣例）
- 重構模式：Hexagonal Architecture — Output Adapter 拆分；Parallel Change（schema re-export）
