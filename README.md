# XIC Extractor

質譜分析 XIC（Extracted Ion Chromatogram）提取與報告工具。

XIC Extractor 會從 Thermo Xcalibur `.raw` 檔案批次提取多目標化合物的 MS1 XIC，寫出 apex RT、raw apex intensity、raw integrated area、peak boundary，並做 MS2 neutral-loss confirmation 與 diagnostics 報告。

---

## 下載與執行（一般使用者）

1. 前往 [Releases](../../releases) 下載最新版 `XIC_Extractor-Windows-vX.Y.Z.zip`
2. 解壓縮到任意資料夾
3. 雙擊 `XIC_Extractor.exe` 執行（不需自行安裝 Python）
4. 首次啟動時，`config/` 目錄會自動建立預設設定檔

系統需求：Windows 10/11、已安裝 Thermo Xcalibur / RawFileReader DLL。

---

## 使用說明

### Settings

`config/settings.csv` 是 GUI 與 CLI 共用的唯一 runtime 設定來源。

| key | 說明 |
| --- | --- |
| `data_dir` | `.raw` 檔案所在資料夾 |
| `dll_dir` | Thermo DLL 路徑，例如 `C:\Program Files (x86)\Thermo\Foundation` |
| `smooth_window` | Savitzky-Golay smoothing window，必須為奇數且 >= 3 |
| `smooth_polyorder` | Savitzky-Golay polynomial order，必須小於 `smooth_window` |
| `peak_rel_height` | scipy peak boundary 的 relative height |
| `peak_min_prominence_ratio` | peak prominence 門檻，使用 smoothed apex 的比例 |
| `ms2_precursor_tol_da` | MS2 precursor matching tolerance（Da） |
| `nl_min_intensity_ratio` | NL product ion intensity floor，相對 base peak 的比例 |
| `count_no_ms2_as_detected` | 是否將 `NO_MS2` 視為偵測到 |

舊版 `smooth_points` 會自動 migrate 成 `smooth_window`；`smooth_sigma` 已不再使用。

### Targets

在 Targets 表格中設定每個目標化合物：

| 欄位 | 說明 |
| --- | --- |
| `label` | 化合物標籤，會成為 CSV / Excel 欄位前綴 |
| `mz` | 目標 m/z 值 |
| `rt_min` / `rt_max` | 保留時間搜尋範圍（分鐘） |
| `ppm_tol` | MS1 m/z 容差（ppm） |
| `neutral_loss_da` | 中性丟失質量（Da）；空白表示不做 NL 驗證 |
| `nl_ppm_warn` / `nl_ppm_max` | NL warning / fail 閾值（ppm） |
| `is_istd` | 是否為 internal standard |
| `istd_pair` | analyte 對應的 ISTD label |

### 執行流程

1. 填寫 Settings 並儲存
2. 設定 Targets 並儲存
3. 點擊 Run 開始 extraction
4. Results 區會顯示每個 target 的 detection count、NL `✓/⚠/✗/—` counts、Median Area 與 Diagnostics count
5. CSV 與 Excel 報告自動儲存於 `output/`

---

## 輸出檔案

### `output/xic_results.csv`

每列是一個 sample，每個 target 會輸出：

| 欄位 | 意義 |
| --- | --- |
| `{label}_RT` | smoothed peak apex 的 RT（分鐘） |
| `{label}_Int` | apex scan 的 raw intensity |
| `{label}_Area` | 主要定量指標；使用 raw intensity 在 scipy peak boundary 內積分 |
| `{label}_PeakStart` / `{label}_PeakEnd` | peak integration boundary，主要供診斷使用 |
| `{label}_NL` | `OK`、`WARN_12.3ppm`、`NL_FAIL` 或 `NO_MS2`；無 NL target 不會有 `_NL` 欄位 |

`ND` 代表沒有可用 peak；`ERROR` 代表該 raw file 發生 file-level error。

### `output/xic_diagnostics.csv`

記錄非 OK 的 sample-target issue：

| 欄位 | 意義 |
| --- | --- |
| `SampleName` | sample name |
| `Target` | target label |
| `Issue` | `PEAK_NOT_FOUND`、`NO_SIGNAL`、`WINDOW_TOO_SHORT`、`NL_FAIL`、`NO_MS2` 或 `FILE_ERROR` |
| `Reason` | 可操作的原因說明 |

### Excel 報告

`scripts/csv_to_excel.py` 會建立包含三張表的 workbook：

| Sheet | 內容 |
| --- | --- |
| `XIC Results` | 格式化後的 main data |
| `Summary` | detection rate、Mean RT、Median Area、Area / ISTD ratio、NL counts、RT delta |
| `Diagnostics` | issue rows；若有 diagnostics，workbook 開啟時會落在此 sheet |

---

## CLI

GUI 與 CLI 都呼叫同一條 Python pipeline。

```powershell
uv run python -m scripts.run_extraction --base-dir .
```

安裝 entry point 後也可使用：

```powershell
uv run xic-extractor-cli --base-dir .
```

常用參數：

| 參數 | 說明 |
| --- | --- |
| `--base-dir` | 專案資料夾，底下需有 `config/` 與 `output/` |
| `--skip-excel` | 只輸出 CSV，跳過 Excel conversion |
| `--excel` | 保留作相容旗標；Excel conversion 是預設行為 |

`scripts/01_extract_xic.ps1` 已不再是支援的 extraction entry point。

---

## 常見錯誤

| 訊息類型 | 處理方式 |
| --- | --- |
| `settings.csv` / `targets.csv` 格式錯誤 | 依錯誤訊息中的 file、row、column 修正設定 |
| `data_dir` 不存在 | 到 Settings 指向含 `.raw` 檔案的資料夾 |
| `dll_dir` 不存在或缺 Thermo DLL | 到 Settings 指向含 `ThermoFisher.CommonCore.Data.dll` 與 `ThermoFisher.CommonCore.RawFileReader.dll` 的資料夾 |
| 缺 pythonnet / .NET runtime | 重新安裝 packaged app，或在開發環境執行 `uv sync --extra dev` |
| 單一 `.raw` 無法讀取 | pipeline 會繼續處理其他檔案，並在 Diagnostics 寫入 `FILE_ERROR` |

---

## 開發者安裝

```powershell
git clone https://github.com/Chao-hu-Lab/XIC_Extractor.git
cd XIC_Extractor

uv venv
uv sync --extra dev

uv run python -m gui.main
uv run pytest
```

Migration validation（merge-time only）：

```powershell
uv run python scripts\validate_migration.py `
  --old-worktree ..\validation-old-reference `
  --new-worktree . `
  --raw-file local_raw_samples\TumorBC2312_DNA.raw `
  --strict
```

此 validation workbook 是開發者 merge gate，不會出現在一般 GUI workflow。

---

## 專案架構

```text
XIC_Extractor/
├── assets/                      # 應用程式圖示
├── config/
│   ├── settings.example.csv     # 預設設定範本（版控）
│   └── targets.example.csv      # 目標清單範本（版控）
├── gui/
│   ├── config_io.py             # 設定檔讀寫與 first-run migration
│   ├── main_window.py           # 主視窗
│   ├── sections/                # Settings / Targets / Run / Results
│   └── workers/                 # PipelineWorker
├── scripts/
│   ├── run_extraction.py        # Python CLI entry point
│   ├── csv_to_excel.py          # CSV → Excel 報告
│   └── validate_migration.py    # developer-only migration gate
├── xic_extractor/
│   ├── config.py                # typed config loading / migration / validation
│   ├── raw_reader.py            # Thermo RawFileReader wrapper
│   ├── signal_processing.py     # peak detection and area integration
│   ├── neutral_loss.py          # MS2 NL confirmation
│   └── extractor.py             # shared extraction orchestrator
├── tests/
├── xic_extractor.spec
└── pyproject.toml
```

---

## 版本紀錄

詳見 [GitHub Releases](../../releases)。
