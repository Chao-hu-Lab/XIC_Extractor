# Project Layout

本檔案是 XIC Extractor 的**目錄收納規則單一可信來源**。新檔案要放哪、暫存目錄何時可清、哪些路徑被外部約束鎖死，都查這裡。

## § 1 三份規則文件的職責分工

| 文件 | 給誰看 | 內容 |
|------|--------|------|
| [`README.md`](../README.md) | 使用者 | 下載、執行、Settings / Targets 欄位說明、輸出格式 |
| [`AGENTS.md`](../AGENTS.md) | 寫程式碼的人 | 設計原則、所有權地圖、依賴規則、紅旗、重構紀律、測試結構規則、公開契約 |
| **本檔** | 想知道「檔案放哪」的人 | 目錄地圖、外部約束、新檔決策樹、暫存目錄清理規則、命名慣例 |

三份檔案職責不重疊。本檔**不**描述「程式怎麼寫」（那是 AGENTS.md），**不**描述「軟體怎麼用」（那是 README.md）。

## § 2 目錄地圖

第一層完整清單。「PyInstaller」欄位指該目錄是否被打進 release bundle（由 `xic_extractor.spec` 決定）。

### 根層檔案

| 檔案 | 用途 | Git |
|------|------|-----|
| `pyproject.toml` | 專案 metadata、依賴、CLI entry points、setuptools.packages.find、pytest 設定 | 追蹤 |
| `uv.lock` | uv 套件鎖定檔 | 追蹤 |
| `xic_extractor.spec` | PyInstaller 打包設定 | 追蹤 |
| `.gitignore` | git 忽略規則 | 追蹤 |
| `.python-version` | Python 版本 (3.13) | 追蹤 |
| `mypy.ini` | mypy 設定 | 追蹤 |
| `README.md` | 使用者文件 | 追蹤 |
| `AGENTS.md` | 開發契約與程式設計規則 | 追蹤 |
| `test.md` | 測試架構指南 | 追蹤 |
| `launch_gui.bat` | Windows GUI 啟動批次檔 | 追蹤 |

### 第一層子目錄（追蹤）

| 目錄 | 用途 | PyInstaller |
|------|------|------|
| `xic_extractor/` | 主程式庫（domain logic、所有 pipeline 階段） | 經由 `packages.find` |
| `gui/` | PyQt6 GUI 層；entry: `gui/main.py` | entry script |
| `scripts/` | CLI 入口（`run_*.py`）+ 開發 / 驗證腳本 | 經由 `datas` |
| `tools/diagnostics/` | 一次性診斷工具，**不打包** | 否 |
| `tests/` | pytest 測試（扁平結構 + `fixtures/`） | 否，exclude |
| `docs/` | 文件、規格（`docs/superpowers/specs/`）、計畫（`docs/superpowers/plans/`） | 否 |
| `assets/` | `app_icon.png`、`screenshots/` | 經由 `datas` |
| `config/` | runtime 設定；**只 `*.example.csv` 與固定列表（如 `RNA.csv`）被追蹤** | 範本 CSV |
| `.github/` | GitHub Actions workflows + dependabot | 否 |

### 第一層子目錄（忽略）

| 目錄 | 用途 |
|------|------|
| `.venv/` | uv 建立的 Python 虛擬環境 |
| `.uv-cache/` | uv 套件下載快取 |
| `.mypy_cache/` | mypy 型別檢查快取 |
| `.pytest_cache/` | pytest 快取 |
| `.ruff_cache/` | ruff linter 快取 |
| `.tmp/` | pip / pytest 臨時檔 |
| `output/` | pipeline 執行產物（xlsx / tsv / html） |
| `tmp_runtime/` | pipeline 與 validation_harness 產生的 pickle 快取 |
| `.worktrees/` | git worktrees（superpowers/using-git-worktrees skill 建立） |
| `.superpowers/` | Claude superpowers 工件（brainstorm 快照等） |
| `.remember/` | Claude 代理記憶日誌 |
| `local_raw_samples/`、`local_validation_raw/` | 本地測試 RAW 樣本（私人資料） |
| `xic_extractor.egg-info/` | setuptools 安裝元資料 |

### `xic_extractor/` subpackage 分工

由 `AGENTS.md § Ownership Map` 規範。一句話摘要：

| Subpackage | 用途 |
|------------|------|
| `alignment/` | 跨樣本對齊、ownership clustering、primary consolidation |
| `discovery/` | Untargeted feature discovery（MS2 NL seed → MS1 backfill） |
| `extraction/` | Targeted XIC 提取、anchor windowing、pipeline orchestration |
| `peak_detection/` | Resolver-specific peak finding（`legacy_savgol`, `local_minimum`） |
| `configuration/` | Settings schema、CSV IO、validation |
| `output/` | Workbook sheet rendering、Excel / TSV / HTML 輸出 |
| `diagnostics/` | Audit 與診斷模組 |
| 根層 `extractor.py` `peak_scoring.py` 等 | Facade 與跨 subpackage 公開介面 |

詳細所有權邊界查 `AGENTS.md § Ownership Map`。

## § 3 三道不可動的約束

這 3 處外部約束鎖死了目錄結構。**動之前必讀**。

### (a) `pyproject.toml` packages.find

```toml
[tool.setuptools.packages.find]
include = ["gui*", "scripts*", "xic_extractor*"]
exclude = ["tests*"]
```

→ `gui/`、`scripts/`、`xic_extractor/` **必須在根目錄**，不能搬進 `src/` 或任何子目錄。
→ 違反後果：5 個 CLI entry point（`xic-extractor`、`xic-extractor-cli`、`xic-discovery-cli`、`xic-align-cli`、`xic-align-validate-cli`）全失敗。

### (b) `xic_extractor.spec` 寫死的相對路徑

```python
datas=[
    ("assets", "assets"),
    ("config/settings.example.csv", "config"),
    ("config/targets.example.csv", "config"),
    ("scripts", "scripts"),
]
entry: ["gui/main.py"]
icon: "assets/app_icon.png"
```

→ 移動或重命名 `assets/`、`config/settings.example.csv`、`config/targets.example.csv`、`scripts/`、`gui/main.py`、`assets/app_icon.png` 之中任何一個 → CI build workflow 失敗。
→ 若要動，必須同時更新 `xic_extractor.spec` 與 `.github/workflows/build.yml`。

### (c) `xic_extractor/configuration/loader.py:29` 寫死 config-output 同級

```python
output_dir = config_dir.parent / "output"
```

→ `config/` 與 `output/` **必須是同一級的目錄**（都在根目錄）。
→ 若要動位置，必須改 `loader.py` 邏輯，並驗證 GUI（`gui/config_io.py:7-12`）、CLI（`scripts/run_extraction.py:20-21`）的對應路徑導航。

### Bonus：frozen vs dev 雙模式

`gui/config_io.py` 與 `gui/main_window.py` 都用：
```python
if getattr(sys, "frozen", False):
    ROOT = Path(sys.executable).parent      # 用戶可寫
    _BUNDLE = Path(sys._MEIPASS)            # PyInstaller bundle，唯讀
else:
    ROOT = Path(__file__).resolve().parent.parent
    _BUNDLE = ROOT
```

意思是：打包後 `config/`、`output/` 在執行檔旁（用戶可改），但 `assets/`、`scripts/` 在 bundle 內（唯讀）。動這些目錄時要兩種模式都驗證。

## § 4 新檔案該放哪？

```
要加新檔
├── 程式碼
│   ├── GUI（PyQt6 widget、worker、styles）
│   │   └→ gui/                       （子目錄：sections/、workers/）
│   ├── CLI 入口
│   │   └→ scripts/run_<purpose>.py   （需在 pyproject.toml.[project.scripts] 註冊）
│   ├── 開發 / 驗證腳本（會被 PyInstaller 打包）
│   │   └→ scripts/<purpose>.py
│   ├── 一次性診斷工具（不進 bundle）
│   │   └→ tools/diagnostics/<purpose>.py
│   └── Domain 邏輯
│       └→ xic_extractor/<subpackage>/
│           └─ 不確定哪個 subpackage？查 AGENTS.md § Ownership Map
│
├── 測試
│   └→ tests/test_<module>_<behavior>.py
│       （扁平結構，不鏡像 xic_extractor/ 子目錄）
│       共用 fixture → tests/conftest.py 或 tests/fixtures/
│
├── 規格 / 計畫文件
│   ├── 設計規格 → docs/superpowers/specs/YYYY-MM-DD-<kebab-description>.md
│   └── 實作計畫 → docs/superpowers/plans/YYYY-MM-DD-<kebab-description>.md
│
├── 執行產物（自動忽略）
│   └→ output/
│
├── pickle 快取（自動忽略）
│   └→ tmp_runtime/
│
├── 設定範本（只 example 才被追蹤）
│   └→ config/<name>.example.csv
│
└── 資源檔（icon、screenshot）
    └→ assets/
```

## § 5 暫存目錄定義與安全清理

「暫存目錄」= 在 `.gitignore` 中、由工具或執行時自動產生、可被安全重建的目錄。本節給每個暫存目錄訂出（i）誰建的、（ii）何時可清、（iii）安全清理指令。

> 本檔不主動執行清理。下列指令請在你確認時機合適時自行跑。

### `.mypy_cache/`

- **誰建**：`mypy` 第一次跑時自動建立
- **何時可清**：任何時候（會自動重建）
- **指令**：
  ```powershell
  Remove-Item -Recurse -Force .mypy_cache
  ```

### `.pytest_cache/` `.ruff_cache/` `.uv-cache/` `.tmp/`

- **誰建**：對應工具第一次執行時
- **何時可清**：任何時候（會自動重建）
- **指令**（按需擇一）：
  ```powershell
  Remove-Item -Recurse -Force .pytest_cache, .ruff_cache, .tmp
  ```
  `.uv-cache/` 較大但跨專案共享 uv 套件快取，刪除後下次 `uv sync` 會重抓所有套件，視磁碟空間決定。

### `tmp_runtime/`

- **誰建**：`scripts/validation_harness.py`、`scripts/local_minimum_param_sweep.py`、pipeline 執行時產生的 pickle 快取（`case_*` 子目錄）
- **何時可清**：所有 alignment / discovery 任務跑完且結果已寫到 `output/` 後
- **風險**：清掉後重跑會慢（需重算 pickle）
- **現況**：截至 2026-05-16，548 個 `case_*` 子目錄共 2.28 GB
- **指令**：
  ```powershell
  Remove-Item -Recurse -Force tmp_runtime\case_*
  ```

### `.worktrees/`

- **誰建**：`git worktree add ...`，或 superpowers/using-git-worktrees skill 自動建立
- **何時可清**：個別 worktree 的分支已合入 `master`，且 worktree 內無未提交修改
- **風險**：盲清會丟失未合的工作分支；目前 24 個活躍 worktree、20.2 GB
- **安全步驟**：
  ```powershell
  # 1. 列出所有 worktree
  git worktree list

  # 2. 對每個 worktree，確認無未提交修改
  git -C .worktrees\<name> status

  # 3. 確認該分支已合入 master
  git -C .worktrees\<name> branch --show-current
  git log master..<branch-name> --oneline   # 若空輸出代表已合

  # 4. 移除個別 worktree
  git worktree remove .worktrees\<name>

  # 5. 清剩餘元資料
  git worktree prune
  ```

### `output/`

- **誰建**：pipeline 寫入結果（`xlsx`、`tsv`、`html`、中間 CSV）
- **何時可清**：結果已備份 / 驗收後
- **現況**：截至 2026-05-16，340 MB，含 2026-04-07 到 2026-05-14 的舊輸出
- **指令**：依檔案需求手動刪除子集，不一鍵全清

### `local_raw_samples/` `local_validation_raw/`

- **誰建**：手動放入本地 RAW 樣本
- **何時可清**：依本地驗證需求，無自動規則
- **規則**：被 `.gitignore` 忽略，避免私人 RAW 資料進入 git

### `.superpowers/` `.remember/`

- **誰建**：Claude superpowers / 代理工具
- **何時可清**：任何時候（會自動重建）
- **指令**：除非有明確記錄需求，否則可保留

## § 6 既有命名慣例（從現況歸納）

| 類別 | 慣例 | 範例 |
|------|------|------|
| 規格檔 | `docs/superpowers/specs/YYYY-MM-DD-<kebab>.md` | `2026-05-13-untargeted-duplicate-drift-soft-edge-design.md` |
| 計畫檔 | `docs/superpowers/plans/YYYY-MM-DD-<kebab>.md` | `2026-05-03-output-maintainability-refactor.md` |
| 測試檔 | `tests/test_<module>_<behavior>.py`，**扁平結構，不鏡像 src** | `test_alignment_owner_clustering.py` |
| CLI 入口 | `scripts/run_<purpose>.py` | `scripts/run_extraction.py` |
| CLI 輔助 | `scripts/<verb>_<noun>.py` 或 `<purpose>.py` | `scripts/csv_to_excel.py` |
| 診斷工具 | `tools/diagnostics/<purpose>.py` | `tools/diagnostics/alignment_decision_report.py` |
| Subpackage `__init__.py` | 對外公開模組才導出 `__all__`（目前部分缺失，見 § 7） | `xic_extractor/alignment/__init__.py` |

關於「測試為何不鏡像 src 結構」：`AGENTS.md § Test Structure Rules` 明文採用「按 ownership 切，命名 `test_<module>_<behavior>`」的策略，避免 `tests/alignment/test_*.py` vs `xic_extractor/alignment/` 的雙層維護。

## § 7 已知內部重構狀態（指向後續工作，不在本檔範圍）

下列問題已被識別但**不屬於目錄收納規則**，由 `AGENTS.md § Current Decomposition Targets` 與既有 spec 接手。

- `xic_extractor/alignment/` 內 `_ppm()` 在 10 處重複定義（待抽 utils）
- `extraction/`、`output/`、`configuration/`、`peak_detection/` 4 個 subpackage 缺 `__all__` 公開 API 宣告
- `xic_extractor/peak_scoring.py`（1014 行）→ `AGENTS.md § Current Decomposition Targets` 已列名
- `xic_extractor/extractor.py` 與 `xic_extractor/signal_processing.py` 的 facade 化重構（待處理）
- `xic_extractor/alignment/primary_consolidation.py` 的 characterization-first 拆分（待處理）

已完成的責任切分：

- `tools/diagnostics/alignment_decision_report.py`、`single_dr_production_gate_decision_report.py`、`targeted_istd_benchmark.py` 已拆出 loading / report model / rendering 或 writing helpers。
- `xic_extractor/alignment/pipeline.py` 已拆出 `pipeline_outputs.py` 與 `raw_sources.py`，保留 `run_alignment(...)` 作 orchestration facade。

相關 spec：

- [`docs/superpowers/specs/2026-05-06-workbook-and-extraction-module-decomposition-spec.md`](superpowers/specs/2026-05-06-workbook-and-extraction-module-decomposition-spec.md)
- [`docs/superpowers/specs/2026-05-16-module-responsibility-inventory.md`](superpowers/specs/2026-05-16-module-responsibility-inventory.md)
- [`docs/superpowers/specs/2026-05-16-alignment-module-responsibility-contract.md`](superpowers/specs/2026-05-16-alignment-module-responsibility-contract.md)

## § 8 維護本檔的時機

本檔需要更新當且僅當：

1. 第一層目錄新增 / 移除 / 改名 → 更新 § 2
2. `pyproject.toml.packages.find`、`xic_extractor.spec`、`configuration/loader.py:29` 任一處被改 → 更新 § 3
3. 既有暫存目錄被改名或新增 → 更新 § 5
4. 命名慣例改變 → 更新 § 6

僅內部 subpackage 結構調整（例如 `alignment/` 內檔案移動）→ **不需**更新本檔，由 `AGENTS.md § Ownership Map` 負責。
