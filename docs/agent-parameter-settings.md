# Agent Parameter Settings

本檔只記錄 XIC Extractor 常用、穩定、跨任務會重複踩到的本機設定。任務特定
artifact，例如某個 Phase 的 benchmark summary、一次性 gate output、plot/report，
不放在這裡；請查當前 spec、plan、validation note 或本輪 `output/` index。
跨 worktree 會重複使用的 accepted validation inputs 例外：必須放在
`local_validation_artifacts/`，不能依賴某個 `.worktrees/<branch>/output/`。

這份文件是 operational memory，不是一次性備忘錄。當某個 RAW / validation
命令實際跑通，或某個啟動方式反覆失敗，應把穩定參數形狀與教訓更新到本檔。
不要只把教訓留在單次 conversation 或 phase note。

跨 worktree 會重複遇到的診斷結論放在
`docs/diagnostic-ledger.md`。在重跑昂貴 RAW validation 或把已知 target
重新標成 blocker 前，先讀 ledger；只有 current code 或 artifact freshness
足以改變結論時才重跑。

維護規則：

- 只固定跨任務會重複使用的 runner、資料根目錄、DLL 目錄、validation tier、
  command shape、preflight check、以及反覆踩雷的 anti-pattern。
- 任務特定 output path、phase-specific discovery index、一次性 benchmark 結論
  留在 validation note；本檔只引用該 note 作為 evidence。
- accepted reusable discovery inputs 若要跨分支使用，先複製到
  `C:\Users\user\Desktop\XIC_Extractor\local_validation_artifacts\...` 並重寫
  `discovery_batch_index.csv` 裡的 `candidate_csv` / `review_csv` 絕對路徑。
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
- 在 worktree 內跑正式 85RAW 時，`scripts.run_alignment
  --expected-sample-count 85` 會要求 Python executable 位於該 worktree 的
  `.venv` 底下。不要用 root repo 的絕對路徑
  `C:\Users\user\Desktop\XIC_Extractor\.venv\Scripts\python.exe` 直接啟動
  worktree 的 85RAW；這會被 canonical guard 拒絕。
- 若 active worktree 沒有 `.venv`，且 root repo `.venv` 是要共用的 RAW
  runtime，先確認沒有既有 `.venv` 後建立 junction：

```powershell
New-Item -ItemType Junction -Path .venv -Target C:\Users\user\Desktop\XIC_Extractor\.venv
```

  然後使用 `.venv\Scripts\python.exe` 啟動 preflight / validation。

## Stable Local Paths

| 用途 | 路徑 | 備註 |
| --- | --- | --- |
| Thermo RAW root，85RAW tissue set | `C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R` | Full tissue validation。 |
| Thermo RAW validation subset | `C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation` | Historical 8RAW validation subset。 |
| Thermo RawFileReader DLL dir | `C:\Xcalibur\system\programs` | RAW commands 必須使用這個 DLL dir。 |
| manual 2RAW truth data | `C:\Xcalibur\data\20251219_need process data\XIC test` | Resolver / manual-truth calibration。 |
| accepted P8b 8RAW discovery input | `C:\Users\user\Desktop\XIC_Extractor\local_validation_artifacts\discovery\accepted_p8b\8raw\discovery_batch_index.csv` | Cross-worktree reusable validation input；內部 `candidate_csv` / `review_csv` 已重寫到同一 artifact store。 |
| accepted P8b 85RAW discovery input | `C:\Users\user\Desktop\XIC_Extractor\local_validation_artifacts\discovery\accepted_p8b\85raw\discovery_batch_index.csv` | Cross-worktree reusable validation input；正式 85RAW 前仍需 `--expected-sample-count 85` preflight。 |
| targeted GT 8RAW default workbook | `C:\Users\user\Desktop\XIC_Extractor\local_validation_artifacts\targeted_gt_workbooks\8raw\xic_results_20260512_1151.xlsx` | SHA256 `788892188C8419C82DC4618C98E160B90AC6C44C38676C53609248AA529889F7`；`targeted_gt_alignment_audit.py` 的 8RAW default positive checkpoint workbook；不要用 85-sample workbook 對 8RAW alignment，否則會產生 off-scope `MISS`。 |

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

對 sandbox、PowerShell、approval、RAW runner、或 output 路徑不確定時，先跑
repo-local doctor。它只分類命令，不執行命令，也不讀 RAW：

```powershell
python -m scripts.agent_sandbox_doctor --command "<command-to-check>"
```

長時間或昂貴命令可加 `--strict`，讓 blocker/review finding 以 non-zero exit
code 先停下來：

```powershell
python -m scripts.agent_sandbox_doctor --strict --command ".venv\Scripts\python.exe -m scripts.run_alignment --expected-sample-count 85 ..."
```

## Sandbox Friction Playbook

目前建議姿態是 `workspace-write + on-request`。這不是最順的模式，但對這個
repo 是合理預設：agent 可以寫工作樹與 `C:\tmp`，讀外部 RAW / DLL / reference
data，遇到外部寫入、network、GUI、或高風險命令時才升權。

常見 friction 不要全部用放寬 sandbox 解決：

| 症狀 | 先做什麼 | 不要做什麼 |
| --- | --- | --- |
| 寫入 `C:\Xcalibur`、桌面資料夾、`$CODEX_HOME` / `%USERPROFILE%\.codex` 失敗 | 把 output / cache / sidecar 改到目前 worktree 的 `output\...` 或 `C:\tmp`；若真的要改全域 Codex 設定，先明確取得使用者要求 | 不要切 `danger-full-access` 或擴大 writable root 只為了省一次路徑修正 |
| package install、`npx`、下載文件、GitHub/網路失敗 | 確認這是任務必要條件後，用 narrow approval / prefix；成功後記錄穩定命令或替代離線路徑 | 不要把 network access 永久打開當預設 |
| pytest / Python 產生 cache 被擋 | 在 worktree 內跑；必要時加 `$env:PYTHONDONTWRITEBYTECODE='1'` 和 `-p no:cacheprovider`；tester role 可 workspace-write 只為 verification side effects，驗證後要回報 `git status` 是否只剩預期 side effects | 不要把 tester 當 implementation worker 讓它改 source |
| RAW / DLL 讀不到 | 先跑本檔 Preflight 的 `Test-Path` 與 Python runner check；RAW 命令用 `.venv\Scripts\python.exe` | 不要用 bare `python` 重試 RAW，也不要掃 sibling directory 猜路徑 |
| PowerShell 語法錯誤 | 改成 PowerShell 語法；多行命令用 backtick；inline Python 用 `python -c` 或 PowerShell here-string pipe；不確定時先跑 `scripts.agent_sandbox_doctor` | 不要貼 Bash heredoc、`export`、`&&` |
| 長時間 85RAW 卡住 | 用 foreground command + `--timing-live-output`；先看 heartbeat / timing artifact 再重跑 | 不要背景 `Start-Process` 後回來輪詢 |

只有在「失敗模式重複、doctor 或現有 preflight 無法降低風險、且人工 approval
本身變成主要摩擦」時，才考慮新增 project-local execpolicy 或 hook。新增前
必須回答：

1. 這個規則是否只允許一個可預期、可重複的安全命令形狀？
2. 它是否會允許任意 Python / shell / deletion / network access？
3. 它是否比把 output 改到 worktree、固定 runner、或更新本檔更好？
4. 它是否有 smoke check，且不會把使用者真正該審的決策藏起來？

目前不建議新增 repo-local `.codex/config.toml` 或 active hooks。先把重複失敗
收斂到本檔、`docs/agent-subagent-routing.md`、或 CLI preflight；等 passive hook
能證明它真的擋住反覆失敗，再考慮 blocking hook。

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
  --expected-sample-count 85 `
  --output-level validation-minimal `
  --backfill-scope production-equivalent `
  --audit-evidence-mode none `
  --performance-profile validation-fast `
  --raw-workers 11 `
  --owner-backfill-window-strategy super-window `
  --owner-backfill-superwindow-span-factor 2 `
  --timing-output <task-specific-output-dir>\timing.json `
  --timing-live-output <task-specific-output-dir>\timing.live.json
```

`validation-minimal` writes the primary machine gate surface:

- `alignment_matrix.tsv`: downstream correction / statistics handoff.
- `alignment_review.tsv`: targeted benchmark and decision diagnostics.
- `alignment_cells.tsv`: targeted benchmark and scoped audit diagnostics.

It does not write `.xlsx`, HTML, owner-edge, status-matrix, event-owner, or
ambiguous-owner debug outputs. Use fuller output levels only when a human
review surface or debug artifact is explicitly required. In `auto` audit mode,
`validation-minimal` resolves to no heavy audit evidence unless an explicit
integration audit destination is requested. Some lightweight sidecars, such as
`skipped_evidence_ledger.tsv` and `alignment_run_metadata.json`, may still be
emitted when backfill scope needs machine-readable skip provenance.

Before starting 85RAW, verify the batch index actually contains 85 samples. Do
not reuse the historical 8RAW index by path similarity. Prefer the CLI preflight
guard because it uses the same discovery-batch parser, checks candidate CSV
existence and RAW path existence, and prints the launch contract without loading
candidate CSV rows or opening RAW files:

```powershell
.venv\Scripts\python.exe -m scripts.run_alignment `
  --discovery-batch-index <current-spec-discovery-batch-index.csv> `
  --raw-dir C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R `
  --dll-dir C:\Xcalibur\system\programs `
  --output-dir <task-specific-output-dir> `
  --expected-sample-count 85 `
  --output-level validation-minimal `
  --backfill-scope production-equivalent `
  --audit-evidence-mode none `
  --performance-profile validation-fast `
  --raw-workers 11 `
  --owner-backfill-window-strategy super-window `
  --owner-backfill-superwindow-span-factor 2 `
  --timing-output <task-specific-output-dir>\timing.json `
  --timing-live-output <task-specific-output-dir>\timing.live.json `
  --preflight-only
```

When `--expected-sample-count 85` is present, `scripts.run_alignment` also
enforces the canonical 85RAW launch contract: `validation-minimal`,
`production-equivalent`, `audit-evidence-mode none`, `validation-fast`,
`super-window`, timing JSON + live heartbeat, and a Python executable under this
worktree's `.venv`.

Manual fallback:

```powershell
(Import-Csv <current-spec-discovery-batch-index.csv>).Count
```

If this prints `8`, stop and locate the current 85RAW discovery artifact from
the active spec or validation note before running alignment.

## Validated Command Profiles

| Profile | Status | Reusable parameters | Evidence |
| --- | --- | --- | --- |
| 85RAW validation-minimal super-window | Verified foreground run, exit code `0`, wall-clock `620.9 s` | `.venv\Scripts\python.exe`, 85RAW RAW root, `--output-level validation-minimal`, `--backfill-scope production-equivalent`, `--audit-evidence-mode none`, `--performance-profile validation-fast`, `--raw-workers 11`, `--owner-backfill-window-strategy super-window`, `--owner-backfill-superwindow-span-factor 2`, timing output + live heartbeat | `docs\superpowers\notes\2026-05-26-p8b-85raw-superwindow-acceptance-note.md` |
| 85RAW primary-delivery validation | Verified foreground run, exit code `0`, wall-clock `596.6 s`; worktree `.venv` junction required before launch | same canonical 85RAW shape plus `--expected-sample-count 85`; output hashes and diagnostics fixed in durable fixtures | `docs\superpowers\notes\2026-05-28-qualitative-selection-acceptance-gate-note.md`; `docs\superpowers\fixtures\diagnostic_ledger_2026_05_28\85raw_primary_delivery_fix_summary.tsv` |

The cited `620.9 s` run predates the `--expected-sample-count 85` guard. The
guard is a later test-covered launch safety check and should be included in new
85RAW commands, but it is not part of that historical runtime evidence.

Do not treat `--performance-profile validation-fast` alone as the full 85RAW
validation profile. It sets RAW worker count and XIC batch size, and new 85RAW
commands should pin `--raw-workers 11` explicitly for this machine. The formal
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

Targeted extraction / workbook harness details live in
[`docs/validation-harness.md`](validation-harness.md). That harness is not the
canonical 85RAW alignment acceptance runner unless it is explicitly updated to
emit the same minimal machine contract and heartbeat shape documented here.

## Syntax Anti-patterns

- This repo is normally operated from PowerShell. Do not paste Bash heredocs such
  as `python - <<'PY'`; PowerShell treats `<` as redirection and fails before
  Python starts. Use `python -c "..."`, a short PowerShell loop, or a temporary
  checked-in helper when the logic is worth keeping.
- For multiline PowerShell commands, use backtick continuations exactly as shown
  in this file, or split the command into separate lines in the shell. Do not use
  `&&` or Unix-style `export`.
- For Markdown edits, run a cheap fence check before finishing when code blocks
  were added or removed.

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
9. 85RAW 正式驗收預設加 `--performance-profile validation-fast`,
   `--raw-workers 11` 與
   `--owner-backfill-window-strategy super-window`。如果刻意不用，必須在
   validation note 說明原因。
10. 85RAW 開跑前先檢查 discovery index sample count、candidate CSV path、
    RAW path；8RAW index 不可拿來跑 full tissue validation。正式 alignment
    run 用 `--expected-sample-count 85` 固化 sample-count 檢查。
11. 不要把 `.worktrees\<branch>\output\...` 當成 reusable validation input。
    若只有某個 worktree 有 accepted discovery artifact，先移到
    `local_validation_artifacts/` 並重寫 index 內部絕對路徑，再跑 preflight。
12. 不要用 Codex shell 的 background `Start-Process` 跑 85RAW 後就回來輪詢；
    這個模式已反覆失敗。用前景 run 搭配足夠 timeout，或先取得使用者同意
    轉到外部 terminal / automation。
13. 每次長時間 RAW run 後，若發現新的穩定參數或反覆失敗模式，更新本檔；
    不要只把教訓留在聊天紀錄。
14. PowerShell 語法錯誤、ruff E501、Markdown fence mismatch 這類可重複避免
    的錯誤，修完後要把穩定教訓寫回本檔或相關 repo-local contract。
15. 遇到已知 target 或 failure mode，例如 `d3-N6-medA` RT drift / primary
    delivery 問題，先讀 `docs/diagnostic-ledger.md`。不要把 ledger 已經
    解釋過的 RT drift、area mismatch、或 mixed-surface warning 當成新的
    hard blocker；除非 current artifact 與 ledger 明確矛盾。
