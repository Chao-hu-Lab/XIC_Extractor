# Agent Parameter Settings

本檔只記錄 XIC Extractor 常用、穩定、跨任務會重複踩到的本機設定。任務特定
artifact，例如某個 Phase 的 `discovery_batch_index.csv`、benchmark summary、
一次性 gate output、plot/report，不放在這裡；請查當前 spec、plan、
validation note 或本輪 `output/` index。

這份文件是 operational memory，不是一次性備忘錄。當某個 RAW / validation
命令實際跑通，或某個啟動方式反覆失敗，應把穩定參數形狀與教訓更新到本檔。
不要只把教訓留在單次 conversation 或 phase note。

維護規則：

- 只固定跨任務會重複使用的 runner、資料根目錄、DLL 目錄、validation tier、
  command shape、preflight check、以及反覆踩雷的 anti-pattern。
- 任務特定 output path、phase-specific discovery index、一次性 benchmark 結論
  留在 validation note；本檔只引用該 note 作為 evidence。
- 成功 run 要記錄「可重用的參數形狀」與 evidence note；失敗 run 要記錄
  「不可再用的啟動方式」與替代做法。
- 若後續 P-spec / C-spec 改變正式驗收形狀，先更新本檔再開長時間 RAW run。

## Python Runner

這台 Windows 機器目前有兩個常用 Python 入口，但用途不同：

| Runner | 用途 | 已觀察狀態 |
| --- | --- | --- |
| `python` | no-RAW 的窄範圍 pytest shard | `C:\Python314\python.exe`；有 `pytest`；沒有 `pythonnet` |
| `.venv\Scripts\python.exe` | Thermo RAW / RawFileReader / `pythonnet` run | Python 3.13.7；有 `pythonnet`；沒有 `pytest` |

專案契約是 Python `>=3.11,<3.14`。Python 3.14 不是有效 RAW runtime，因為
目前沒有可用的 `pythonnet`。

規則：

- 會讀 `.raw`、呼叫 Thermo DLL、或 import `xic_extractor.raw_reader` 的命令，
  一律用 `.venv\Scripts\python.exe`。
- no-RAW 的窄範圍 pytest shard 可以用 `python -m pytest ...`。
- 不要用 bare `python` 跑 RAW validation，即使命令看起來能啟動。
- 如果 `.venv` 之後補上 pytest，優先用 `.venv\Scripts\python.exe -m pytest`
  讓測試與 RAW runtime 一致。

## Stable Local Paths

| 用途 | 路徑 | 備註 |
| --- | --- | --- |
| Thermo RAW root，85RAW tissue set | `C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R` | Full tissue validation。 |
| Thermo RAW validation subset | `C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation` | Historical 8RAW validation subset。 |
| Thermo RawFileReader DLL dir | `C:\Xcalibur\system\programs` | RAW commands 必須使用這個 DLL dir。 |
| manual 2RAW truth data | `C:\Xcalibur\data\20251219_need process data\XIC test` | Resolver / manual-truth calibration。 |

實驗性 mzML 路徑不列為常用 setting。即使本機有 mzML，production premise 仍是
直接讀 `.raw`，不轉檔。只有使用者明確要求 external-reference audit 時才查
mzML 相關路徑。

## Preflight

涉及本機 Python、RAW、DLL 或 validation data 時，先用這組最小檢查：

```powershell
Get-Command python | Select-Object -ExpandProperty Source
python --version
.venv\Scripts\python.exe --version
.venv\Scripts\python.exe -c "import importlib.util; print('pythonnet', importlib.util.find_spec('pythonnet') is not None); print('pytest', importlib.util.find_spec('pytest') is not None)"
Test-Path "C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R"
Test-Path "C:\Xcalibur\system\programs"
```

如果本檔列出的 stable path 存在，就使用它。除非 `Test-Path` 失敗或使用者
提供更新路徑，否則不要重新搜尋，也不要自行替換成 sibling directory。

## Validation Tiers

| Tier | 使用時機 | 常用資料 | Gate 意義 |
| --- | --- | --- | --- |
| synthetic/unit tests | code behavior、schema、CLI parsing | none | regression only，不代表 production readiness |
| manual-2raw | resolver calibration 對 manual truth | manual 2RAW truth data | manual truth / calibration evidence |
| 8RAW | smoke、parity、benchmark gate，先於昂貴的大規模 run | validation subset 或當前 spec 指定的 8RAW artifacts | 只有 gate docs 通過後，才可說 `shadow_ready` 或 `production_candidate` |
| 85RAW | full tissue validation | 85RAW tissue root | 昂貴 gate；只有 8RAW gate 通過後才跑 |

如果 8RAW gate 是 `inconclusive`，不要為了「看看結果」直接開 85RAW。先說明
blocker，修正或重訂 gate 後再進下一層。

## Common Command Shapes

No-RAW tests:

```powershell
python -m pytest <narrow-test-shard> -q
```

Validation / downstream handoff alignment should use the minimal machine gate
surface by default. For 85RAW validation, the current canonical shape is
`validation-minimal + production-equivalent + validation-fast + super-window +
timing heartbeat`:

```powershell
.venv\Scripts\python.exe -m scripts.run_alignment `
  --discovery-batch-index <current-spec-discovery-batch-index.csv> `
  --raw-dir C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R `
  --dll-dir C:\Xcalibur\system\programs `
  --output-dir <task-specific-output-dir> `
  --output-level validation-minimal `
  --backfill-scope production-equivalent `
  --audit-evidence-mode none `
  --performance-profile validation-fast `
  --owner-backfill-window-strategy super-window `
  --owner-backfill-superwindow-span-factor 2 `
  --timing-output <task-specific-output-dir>\timing.json `
  --timing-live-output <task-specific-output-dir>\timing.live.json
```

`validation-minimal` writes the machine gate surface:

- `alignment_matrix.tsv`: downstream correction / statistics handoff.
- `alignment_review.tsv`: targeted benchmark and decision diagnostics.
- `alignment_cells.tsv`: targeted benchmark and scoped audit diagnostics.

It does not write `.xlsx`, HTML, owner-edge, status-matrix, event-owner, or
ambiguous-owner debug outputs. Use fuller output levels only when a human
review surface or debug artifact is explicitly required. In `auto` audit mode,
`validation-minimal` resolves to no heavy audit evidence unless an explicit
integration audit destination is requested.

Before starting 85RAW, verify the batch index actually contains 85 rows. Do not
reuse the historical 8RAW index by path similarity:

```powershell
(Import-Csv <current-spec-discovery-batch-index.csv>).Count
```

If this prints `8`, stop and locate the current 85RAW discovery artifact from
the active spec or validation note before running alignment.

## Validated Command Profiles

| Profile | Status | Reusable parameters | Evidence |
| --- | --- | --- | --- |
| 85RAW validation-minimal super-window | Verified foreground run, exit code `0`, wall-clock `620.9 s` | `.venv\Scripts\python.exe`, 85RAW RAW root, `--output-level validation-minimal`, `--backfill-scope production-equivalent`, `--audit-evidence-mode none`, `--performance-profile validation-fast`, `--owner-backfill-window-strategy super-window`, `--owner-backfill-superwindow-span-factor 2`, timing output + live heartbeat | `docs\superpowers\notes\2026-05-26-p8b-85raw-superwindow-acceptance-note.md` |

Do not treat `--performance-profile validation-fast` alone as the full 85RAW
validation profile. It only sets RAW worker count and XIC batch size; the formal
85RAW shape also needs output thinning, production-equivalent backfill,
audit-evidence cutoff, super-window, and heartbeat output.

RAW / alignment commands:

```powershell
.venv\Scripts\python.exe -m scripts.run_alignment `
  --discovery-batch-index <current-spec-discovery-batch-index.csv> `
  --raw-dir C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R `
  --dll-dir C:\Xcalibur\system\programs `
  --output-dir <task-specific-output-dir>
```

Long RAW alignment runs should be observable while they are running:

```powershell
.venv\Scripts\python.exe -m scripts.run_alignment `
  --discovery-batch-index <current-spec-discovery-batch-index.csv> `
  --raw-dir C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R `
  --dll-dir C:\Xcalibur\system\programs `
  --output-dir <task-specific-output-dir> `
  --timing-output <task-specific-output-dir>\timing.json `
  --timing-live-output <task-specific-output-dir>\timing.live.json
```

`--timing-live-output` is the heartbeat artifact for timeout-prone 85RAW runs.
It is overwritten after each timing record, including per-sample process-worker
completion records. If the process is killed by an external timeout, use this
file to identify the last completed stage/sample before rerunning anything.

Do not launch 85RAW from the Codex shell with `Start-Process` / background mode
and then let the shell command return. In this environment, background launch
attempts have repeatedly exited or been cleaned up without completing, sometimes
with empty stdout/stderr. The verified 85RAW acceptance run used a foreground
process with heartbeat sidecars. If background execution is required, it must be
an explicitly user-approved external terminal / automation, and the heartbeat
artifact must still be polled.

For micro-profiling, start with 8RAW or a scoped 85RAW diagnostic:

```powershell
.venv\Scripts\python.exe -m scripts.run_alignment `
  --discovery-batch-index <current-spec-discovery-batch-index.csv> `
  --raw-dir C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R `
  --dll-dir C:\Xcalibur\system\programs `
  --output-dir <task-specific-output-dir> `
  --profile cprofile `
  --profile-output-dir <task-specific-output-dir>\profile
```

`--profile cprofile` writes `profile.prof` and `profile_top.txt` only when the
Python process exits cleanly. For a likely timeout, rely on
`--timing-live-output` first.

Validation harness details live in [`docs/validation-harness.md`](validation-harness.md).

## Agent Rules

1. 選 Python runner 前，先判斷命令是否讀 RAW。RAW 用
   `.venv\Scripts\python.exe`；no-RAW pytest 才可用 `python`。
2. 選 RAW / DLL 目錄前，先查本檔並 `Test-Path`。不要先掃 filesystem。
3. phase-specific artifacts 不要寫進本檔；查當前 spec、plan、validation note
   或 task output index。
4. `.mzML` 不是 production input。除非使用者明確要求，否則不要把 mzML 當成
   fallback 或替代資料源。
5. 如果 stable path 缺失，停止並回報缺失路徑與失敗命令。不要靜默換成另一份
   資料。
6. gate 回 non-zero 時，先讀 JSON/TSV status。不要在 status 還沒釐清時進入
   更大的 validation tier。
7. 85RAW 或任何可能超過 30 分鐘的 RAW run 必須加 `--timing-live-output`；
   沒有 heartbeat artifact 就不要宣稱已完成可審計 profiling。
8. validation / downstream handoff 預設用 `--output-level validation-minimal`。
   `.xlsx` 和 HTML 不是正式交付契約；只有明確需要人工檢視或 debug 時才產生。
9. 85RAW 正式驗收預設加 `--performance-profile validation-fast` 與
   `--owner-backfill-window-strategy super-window`。如果刻意不用，必須在
   validation note 說明原因。
10. 85RAW 開跑前先檢查 discovery index row count；8RAW index 不可拿來跑
    full tissue validation。
11. 不要用 Codex shell 的 background `Start-Process` 跑 85RAW 後就回來輪詢；
    這個模式已反覆失敗。用前景 run 搭配足夠 timeout，或先取得使用者同意
    轉到外部 terminal / automation。
12. 每次長時間 RAW run 後，若發現新的穩定參數或反覆失敗模式，更新本檔；
    不要只把教訓留在聊天紀錄。
