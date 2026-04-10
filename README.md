# XIC Extractor

質譜分析 XIC（Extracted Ion Chromatogram）提取與報告工具。

從 Xcalibur `.raw` 檔案批次提取多目標化合物的 XIC，並自動生成格式化 Excel 報告，支援 MS1 偵測率統計與 MS2 中性丟失（Neutral Loss）驗證。

---

## 下載與執行（一般使用者）

1. 前往 [Releases](../../releases) 下載最新版 `XIC_Extractor-Windows-vX.Y.Z.zip`
2. 解壓縮到任意資料夾
3. 雙擊 `XIC_Extractor.exe` 執行（**不需安裝 Python**）
4. 首次啟動時，`config/` 目錄會自動建立預設設定檔

> **系統需求：** Windows 10/11、PowerShell 5.1+、已安裝 Thermo Xcalibur

---

## 使用說明

### 設定頁（Settings）

| 欄位 | 說明 |
|------|------|
| `data_dir` | `.raw` 檔案所在資料夾，**每次換批次只需更改此處** |
| `dll_dir` | Xcalibur DLL 路徑（預設 `C:\Xcalibur\system\programs`，通常不需更改） |
| `smooth_points` | Gaussian 平滑點數（預設 15） |
| `smooth_sigma` | Gaussian sigma 值（預設 3.0，對齊 Xcalibur EIC 顯示） |

### 目標清單（Targets）

在 Targets 表格中設定每個目標化合物：

| 欄位 | 說明 |
|------|------|
| `label` | 化合物標籤（作為 Excel 欄位名稱） |
| `mz` | 目標 m/z 值（精確質量） |
| `rt_min` / `rt_max` | 保留時間搜尋範圍（分鐘） |
| `ppm_tol` | MS1 m/z 容差（ppm） |
| `neutral_loss_da` | 中性丟失質量（Da），填 0 表示不做 NL 驗證 |
| `nl_ppm_warn` / `nl_ppm_max` | NL 驗證警告 / 失敗閾值（ppm） |

### 執行流程

1. 填寫 Settings 並點擊 **Save**
2. 設定 Targets 並點擊 **Save**
3. 點擊 **Run** 開始 pipeline
4. 完成後在 Results 區查看偵測率摘要
5. Excel 報告自動儲存於 `output/` 資料夾

---

## 開發者安裝

```bash
# 需要 Python 3.10+ 與 uv（https://docs.astral.sh/uv/）
git clone https://github.com/Chao-hu-Lab/XIC_Extractor.git
cd XIC_Extractor

# 建立虛擬環境並安裝依賴
uv venv
uv pip install -e .

# 啟動 GUI
launch_gui.bat
# 或
uv run python -m gui.main

# 執行測試
uv run pytest --tb=short -q
```

---

## 專案架構

```
XIC_Extractor/
├── assets/                      # 應用程式圖示
├── config/
│   ├── settings.example.csv     # 預設設定範本（版控）
│   └── targets.example.csv      # 目標清單範本（版控）
├── gui/
│   ├── config_io.py             # 設定檔讀寫（含首次啟動 fallback 邏輯）
│   ├── main_window.py           # 主視窗
│   ├── sections/                # UI 區塊（Settings / Targets / Run / Results）
│   └── workers/                 # 後台執行緒（PipelineWorker）
├── scripts/
│   ├── 01_extract_xic.ps1       # XIC 提取（Xcalibur PowerShell 介面）
│   └── csv_to_excel.py          # CSV → 格式化 Excel 報告
├── tests/                       # pytest 測試套件
├── xic_extractor.spec           # PyInstaller 打包設定
└── pyproject.toml               # 專案元資料與依賴
```

---

## 版本紀錄

詳見 [GitHub Releases](../../releases)。
