# XIC productization handoff

更新日期: 2026-06-17
分支: `cc/framework-improvements`
用途: 給下一個 agent/session 快速接手，不需要重讀整段聊天。

## 2026-06-17 白話結論

目前這個分支的非 GUI productization goal 有兩條主線已經能講清楚：
Backfill 有五個 explicit scoped writer 到 `production_ready`，Targeted MS1
limited rescue 的 headless default 也到 `production_ready`。其他 Backfill
probes 仍是正式的 `production_candidate`，但 writer 被 heldout oracle failure
或 expected-diff 缺口擋住。

策略修正：不要再把 `low-height-low-scan-clean-stable` 這類層層切片當成
長期產品規則。這些切片只證明 writer/audit/expected-diff 管線可以安全放行
一個小範圍；下一步應把 Backfill 收斂成短、可解釋、domain-meaningful 的
通用 gate，例如 standard-seeded family、預期 RT window、`0.1 min / 10% area`
oracle、write-ready / detected-flagged / blocked 分類，而不是繼續無限拆小。
最新修正正是在處理「TSV 白名單」風險：Backfill productization 現在有
generated policy path，CLI 收的是完整 source activation audit
`--backfill-policy-source-audit-tsv`，程式自己輸出
`standard_peak_backfill_policy.tsv`，把每個 candidate 分成 `write_ready`、
`detected_flagged`、或 `blocked`。writer 只重放 generated `write_ready`；
`detected_flagged` 和 `blocked` 留在 audit，不會改 matrix。白話說，TSV 不再是
人手動改了就能放行的名單，而是 policy engine 的報告和 replay 證據。這沒有
把 broad 4613 格推到 `production_ready`，但它把後續路徑改成「補 evidence
class」而不是「再加一個更窄、更巢狀的 writer flag」。最新真實 no-RAW 85RAW
replay 已跑過：4613 列全部進 policy，439 列是 current approved evidence 的
`write_ready`，72 列是有穩定訊號但缺 masked/product-writer oracle 的
`detected_flagged`，4102 列是 `blocked`；writer 只寫 439 格，expected-diff
439/439 pass。所以 generated policy replay 現在可以宣稱
`production_ready` for current approved evidence classes，但 broad 4613
仍是 `production_candidate`。
`AGENTS.md`、`docs/agent-subagent-routing.md`、`docs/agent/planning-workflows.md`
和 repo-local skills 已補規則：工具、plugins、subagents、CodeGraph、GitHub/gh
都要積極用；token/cost 不是主要限制。限制的是盲跑：每個長工具鏈或昂貴驗證
都要有 `question -> tool/evidence -> action if pass -> action if fail` 的
decision map。同等安全與證據下，一律走最簡單、最短、最容易維護的產品規則、
實作與驗證路徑。

本輪最新程式驗證：focused ruff 通過；`uv run pytest
tests\test_standard_peak_backfill_productization.py -q` 為 `22 passed`。新增測試
不是只放行某個特徵，而是用四種 row 同時驗證：既有 high-signal evidence 可
`write_ready`、低高度 reintegration-stable 可 `write_ready`、穩定但缺 writer
oracle 的 row 只能 `detected_flagged`、缺 writer-approved evidence 的 row
`blocked`，且 matrix 只寫前兩者。Subagent review 又抓到兩個有效缺口：
public package API 不應接受手寫 policy TSV、trace mismatch 不能被 clean status
蓋過；已修成 public API 只收 source audit，且 trace 不 matched 時 generated
policy 會 blocked 而不寫 matrix。修完後 full local gate 也過：
`ruff check xic_extractor tests`、`mypy xic_extractor`、
`pytest -v --tb=short -x` (`3759 passed, 1 skipped`)、以及
`scripts\check_diagnostics_index.py`。後續真實 no-RAW replay command 也過，
輸出在
`output/productization_realdata_seed_guard_85raw_20260617/generated_policy_no_raw_productization/`。

2026-06-17 規則檢討結果：三個 read-only subagent review 已完成。strategy
reviewer 和 implementation/contract reviewer 都無 blocker；docs-handoff
reviewer 找到 handoff PR/CI 狀態過期，已在「下一步建議」改成目前實況。
control plane 也補了硬 gate：未來 Backfill broadening 應優先把新的 broader
evidence class 接進 generated policy engine，說明它如何推進 broad 4613-row
decision；若只是再加一層 scoped/dataset 形容詞，只能留
`production_candidate`，不能宣稱 `production_ready`。

本次主線續推有兩個部分。第一，讀完並收進
`docs/deepresearch/Backfill Production Gate.md` 後，Backfill 的產品方向已
從「用 `height >= 2e6` 當硬門檻」改成「用 boundary-stability /
reintegration agreement 等可驗證證據來逐步放大」。第二，low-height heldout
oracle 新增 `expected_window_bounded` 觀察模式，用既有 85RAW trace 做 no-RAW
replay；再把通過的 bounded oracle 證據接到 explicit low-height scoped writer。
這輪沒有改 broad/default behavior、workbook schema、extraction default 或 RAW
artifact。low-height 現在是 `production_ready` only for the explicit 57-row
scoped writer。再下一步已把 low-height + low-scan 的交集也接成 explicit
69-row scoped writer：它只限 height <2e6、scan 7-9，且 shape/local/width/apex
都乾淨；bounded heldout oracle 20/20 pass，writer expected-diff 69/69 pass。
Targeted MS1 headless no-flag limited default 現在是
`production_ready` for
`5-hmdC + 5-medC` / `detected_flagged`。仍 blocked 的是 GUI、broader target
rescue、Backfill broad 4613-row 全量寫入、以及 ReviewAction
selected-candidate/manual-boundary 產品寫回。

第一個是 Backfill。`4613 rows` 不是什麼神秘 board 名字；它只是代表目前
broad standard-path bridge 如果全開，會寫進 matrix 的 4613 個候選格子。
現在我們仍不能說這 4613 格全部 ready；前面先把第四個安全切片推上去，
這輪又把第五個 low-height reintegration-stable 切片推上去。
原本的 72 格 high-signal clean 仍是 `production_ready`；這輪新增的
low-scan clean 是「其他證據都乾淨，只是邊界內 scan count 只有 7-9」。
新的 no-RAW heldout oracle 從既有 85RAW trace 找到 56 個候選、11 個 family
代表案例，11/11 通過 `0.1 min / 10% area`；activation scope audit 在 4613
格裡找到 42 格符合 low-scan clean，expected-diff 42/42 乾淨，opt-in writer
也只寫這 42 格並得到 `readiness_tier=production_ready`。接著 low-height
clean 也接到 explicit opt-in writer：它只寫 57 格，writer expected-diff 57/57
通過，`readiness_tier=production_ready`。接著 low-height + low-scan clean
也接到 explicit opt-in writer：這是低高度與低 scan 的交集，只寫 69 格；
bounded heldout oracle 有 210 個 eligible detected cases / 51 families，選
20 family cases 時 20/20 pass，最大 boundary error `4.80376e-05 min`、
最大 area relative error `0.00881912`；writer expected-diff 69/69 乾淨，
`readiness_tier=production_ready`。截至那一步 Backfill 有四個 explicit
scoped ready slices：72 格 high-signal clean + 42 格 low-scan clean + 57 格
low-height clean + 69 格 low-height-low-scan clean。你的產品方向也已落地成工作規則：這些只是示範/放行
slice，不是天花板；北極星仍是「只要證據足夠就補」，下一步要繼續用 named
evidence class + heldout oracle + expected-diff，把 broad 4613 類似格子逐步
推上去。

本輪下一步已先補第一個 broader evidence class：boundary-stability /
reintegration agreement。新工具
`standard_peak_reintegration_stability_audit.py` 不讀 RAW、不改 matrix；它對
activation scope audit 裡的每個 written row 重讀 stored trace，做 full-trace
和 expected-window-bounded 兩種再積分。只有兩種結果都和 stored reference
boundary/area 在 `0.1 min / 10% area` 內吻合，且兩種方法彼此也吻合，才標成
eligible。用既有 85RAW no-RAW artifact 跑完整 4613-row scope 後，結果是
299 eligible、3227 ineligible、1087 missing evidence；其中 271 eligible rows
不在目前四個 ready scoped writer 裡。review 後已把 summary 改成
`status=candidate_pool_blocked`、`writer_authority_status=blocked`，並記錄
上游 activation scope TSV 的 schema/source_run_id/hash，避免被誤讀成 pass
gate。白話說，這找到了一批比原本四個 slice 更廣的「邊界穩定候選」，但它
仍不是 writer approval，因為它只是 stored-trace self-consistency，還缺
masked/product-writer oracle 和 expected-diff。

這輪把其中一個能被證據支持的子集合正式推上去了：low-height +
reintegration-stable。先說清楚，不是把 299 個 stability eligible 或 broad
4613 格全部放行。快速 all-family check 在 20 個 family 代表案例裡有 1 個
area fail（`FAM000949/NormalBC2261_DNA`，area relative error 約 19.6%），
所以「全部 stability eligible 直接寫」仍 blocked。可放行的是更窄的交集：
stability eligible、activation row 仍是 written、且 `cell_height < 2e6`。
這個 writer scope 有 220 格 / 66 families；heldout oracle 是 family-level，
不是 row-identity oracle，因為這 220 格本身都是 rescued cells，沒有 original
detected cell 可做 masked-heldout。新的 summary 已明寫
`candidate_family_scope_match_level=family_id` 與
`candidate_family_scope_oracle_basis=detected_trace_rows_from_candidate_families`：
也就是從同 66 個 families 的 1520 個 detected trace candidates 裡選 20 個
family 代表案例，20/20 pass，最大 boundary error `0.0830019 min`、最大 area
relative error `0.0725986`。接著 explicit writer 只吃
`--low-height-reintegration-stable-activation-scope-audit-tsv` +
`--reintegration-stability-audit-tsv`，writer expected-diff 220/220 pass，
`readiness_tier=production_ready`，duplicate/missing/unexpected/non-eligible/
non-written/unchanged/blank 全是 0。這 220 格裡有 199 格不在既有四個 ready
writer scope，五個 ready scope 的 cell-level 聯集現在是 439 格。

這個第五個 writer 已經過兩輪 subagent review。`Bernoulli` 先擋下兩個有效
問題：oracle 其實是 family-level，不能寫成 220-row row-identity oracle；以及
product writer 原本只檢查 activation scope audit 有 `schema_version` 欄位，
但沒有驗值。兩者已修：summary 現在明寫 family-level oracle basis，docs
不再 overclaim row identity；writer 也驗
`standard_peak_activation_scope_audit_v1`，並新增同 family 混合高/低高度只寫
exact SHA 的 regression test。`Avicenna` follow-up review 確認 P1/P2 關閉，
沒有 blocking finding。

low-height clean 問的是：「其他形狀、RT、寬度、scan count 都乾淨，只是
peak height 低於 2e6 的格子，能不能也自動補？」現在答案是：可以，但只限
explicit 57-row scoped writer。舊 full-trace heldout oracle 曾經 19/20，失敗的
`FAM008651/TumorBC2312_DNA` boundary error 是 `1.16445 min`；這說明不能直接用
full-trace reintegration 放行低高度。新的 bounded-window oracle 改用 oracle
window 附近重積分，`padding=0.5 min` 時 20/20 通過，最大 boundary error
`0.0857986 min`、最大 area relative error `0.0564106`。接著 opt-in writer
用 `--low-height-clean-activation-scope-audit-tsv` 只寫 activation scope audit
裡 `low_height_clean_status=eligible` 的 57 格；真實 no-RAW 85RAW writer run
通過，duplicate/missing/unexpected/non-eligible/non-written/unchanged/blank 全是 0。

白話說，低高度這次不是靠降低 height 門檻硬闖，而是靠「區間要被穩定定義」
的 evidence gate。這也不代表所有低高度、所有 4613 格或所有非標準 peak
都可以寫；只代表這個已命名且有 oracle/expected-diff 的 57-row low-height
slice 可以正式當 explicit scoped product behavior。

low-height + low-scan clean 問的是：「如果一格同時低高度、scan count 只有
7-9，但 shape、local/global、boundary width、apex delta 都乾淨，能不能補？」
現在答案也是：可以，但只限 explicit 69-row scoped writer。這條沒有重跑 RAW，
只重用既有 85RAW trace artifact 做 `expected_window_bounded` no-RAW oracle；
activation scope audit 在 4613 格中找到 69 格，product writer 只吃
`low_height_low_scan_clean_status=eligible`，duplicate/missing/unexpected/
non-eligible/non-written/unchanged/blank 全是 0。這不是把「所有低 scan」或
「所有低高度」放大，而是把兩個已證明方向的交集正式化。

低 height + 低 scan 這段已經過 subagent reviewer `Parfit` 驗收，沒有 blocking
finding；它建議補的 P3 blocker table test 也已補上。最新 focused Backfill
shard 是 `39 passed`，full local gate 是 `3742 passed, 1 skipped`。後續又請
`Galileo` / `Feynman` 做 read-only audit，結論是：不要再用現有 predicates
硬切下一個 writer。剩下 broad Backfill 應先標成 `production_candidate` with
direct-writer blocked，下一步要設計新的 named evidence class，例如
boundary-stability / reintegration agreement、local S/N / selectivity、或
cohort-anchored expected-window consistency。

Subagent reviewer `Tesla` 已驗收這個 bounded-oracle diff，沒有 P1/P2 blocker，
也沒有發現 product overclaim。它提出兩個 P3：handoff 舊句子會讓人以為
「新 oracle pass」已解除 writer blocker，以及 edge tests 還缺 CLI negative
padding / no observed peak fail-closed。兩者已修；focused oracle suite 現在
`10 passed`。

最新 Backfill gate research 也支持這個解讀：低高度不是整類不可用，
`20 heldout = 19 pass + 1 boundary fail` 更像是 boundary/reintegration
一致性問題，不是 height 本身足以裁決產品安全。後續不要做「500k-2e6 writer」
或把 `2e6` 從 rollout guardrail 變成產品定義；下一個 broadening slice 應改用
三種更可辯證的 evidence：boundary-stability / reintegration agreement、
local S/N / local selectivity、cohort-anchored expected-window consistency。
這份 research 已經放進 repo 內 `docs/deepresearch/`，可作為後續 agent
重複使用的背景資訊；但它本身不是 product authority，真正放行仍要看
control plane、named spec、focused tests、expected-diff 和 oracle evidence。

再下一個 probe 是 apex-only clean。它問的是：「形狀、高度、寬度、scan count
都乾淨，只是 peak apex 離 family center 超過 0.15 min，能不能自動補？」
這個目前也不能開 writer。No-RAW 85RAW oracle 找到 78 個候選、27 個
families，選 20 個代表案例，結果 17/20 通過、3 個 boundary fail，最大
boundary error `2.19621 min`、最大 area relative error `0.424518`。更重要的是，
失敗案例裡有 apex delta 只有 `0.2493` 和 `0.273` 的 row，所以不是簡單把
apex delta 上限收窄到 0.5 min 就能解決。這個 probe 同樣只能記成
`production_candidate`，writer blocked because the heldout oracle failed：它幫我們知道 apex-offset 類別有風險，
但不能授權自動寫 matrix。

最新 probe 是 width-only clean。它問的是：「形狀、高度、apex 位置、scan
count 都乾淨，只是 peak boundary width 不在 0.30-0.65 min 內，能不能自動補？」
答案也是否定。No-RAW 85RAW oracle 只找到 4 個候選、3 個 families，選 3 個代表
案例後只有 1/3 通過；一個 area fail，另一個 boundary fail。最大 boundary error
`1.86561 min`，最大 area relative error `0.599229`。所以 width-only 也只能是
`production_candidate`，writer blocked because the heldout oracle failed，不能新增 writer。
Subagent code reviewer 後續指出 width selector 測試原本只鎖「太寬」案例，
沒有鎖「太窄」、0.30/0.65 邊界、以及其他品質條件髒掉時的 fail-closed；已補
predicate contract test，focused oracle suite 現在是 `5 passed`，full local gate
是 `3727 passed, 1 skipped`。

最新新增 probe 是 shape-margin clean。它問的是：「其他條件都乾淨，只是
shape similarity 沒到 0.95、但在 0.93-0.95 這個擦邊區間，能不能自動補？」
答案還是否定。No-RAW 85RAW oracle 找到 18 個候選、8 個 families，選 8 個代表
案例後只有 6/8 通過；兩個都卡在 area fail。最大 boundary error
`0.0625542 min` 還在 `0.1 min` 內，但 summary 最大 area relative error `0.198393`
超過你接受的 `10% area`。而且其中一個 fail case 的 shape 已經是
`0.949526`，所以不是把門檻從 0.95 改成 0.945 就能乾淨解決。這個 probe
只能記成 `production_candidate`，writer blocked because the heldout oracle failed，
不能新增 shape-margin writer。

第二個是 Targeted MS1 shape identity / `NL_FAIL` rescue。原本只有 explicit
support-TSV workflow ready；後來新增 headless auto-limited CLI：
`--targeted-ms1-shape-identity-auto-limited-default`。這輪再往前推一格：
canonical settings default / `settings.example.csv` 的
`targeted_ms1_shape_identity_activation_policy` 預設已改成
`limited_5hmdc_5medc_v1`。也就是 headless normal CLI 不加 flag 時，只要沒有
手動 support TSV，就會自動走同一條 baseline -> support TSV -> final_unverified
-> expected-diff gate -> final publish workflow。它仍只限 `5-hmdC + 5-medC`，
且只允許 `NL_FAIL/NO_MS2` rows 從 `not_counted/FALSE` 變成
`detected_flagged/TRUE`。既有 8RAW 真跑通過 1 row / 6 matrix cells；既有
85RAW 真跑通過 11 rows / 66 matrix cells；本輪重用既有 85RAW auto artifact
跑 no-RAW gate 仍通過 11/66，且 support TSV key set 完全一致。這個
headless no-flag limited default 現在也可以講 `production_ready`。GUI 仍 out
of scope，其他 target 也沒有被放行。

你最新的決策也已寫進接手語境：未來應該減少人工介入。也就是 Backfill 不應
要求你人工看完 4613 格，`NL_FAIL` rescue 不應永遠靠手動 support TSV，
ReviewAction 也不應要求你審所有案例。正確推進方式是：系統自動提出 bounded
候選、自動寫 expected-diff / audit evidence、只把少量高風險或代表性案例交給你
抽查。

Subagent reviewer `Cicero` 找到一個 P2：同一個 production-ready gate 原本
仍允許省略 `--support-tsv`，會退化成 output-only pass。這已修成
fail-closed：CLI 現在必須帶 `--support-tsv`，package evaluator 缺 support
rows 也會直接 raise；focused test 新增缺 support 的紅燈案例，Targeted MS1
gate suite 變成 `9 passed`。所以 ready claim 現在真的綁在 actual support TSV
key-set equality 上。

本輪後續自我判斷：使用者已接受 `NL_FAIL` limited default 的產品方向，而且
headless auto-limited workflow 已經有 8RAW/85RAW expected-diff evidence。
現在可安全宣稱的是三個 headless workflows：explicit support-TSV workflow、
明確加 `--targeted-ms1-shape-identity-auto-limited-default` 的 auto CLI，以及
canonical no-flag normal CLI default。三者都只限 `5-hmdC + 5-medC` /
`detected_flagged`，且 default path 仍走同一個 support TSV key-set
expected-diff gate。仍不能宣稱的是 GUI 或 broader target rescue。

Subagent review 不是直接 rubber-stamp。`Kant` 擋下一個 P1：manual
`--targeted-ms1-shape-identity-support-tsv` 會繼承新的 limited default，導致
手動 TSV 不是原本 explicit path；已修成只要 CLI 明確給 support TSV 且沒有
另指定 policy，就把本次 run 鎖回 `explicit_support_tsv`。`Socrates` 擋下
docs drift：ledger/handoff 有幾段仍把 no-flag default 說成 blocked；已改成
GUI/broader targets 才是 blocked。修後 focused default shard 是 `65 passed`，
focused ruff 也 passed；full local gate 也已通過：ruff、mypy、diagnostics
index 都 passed，`pytest -v --tb=short -x` 是 `3728 passed, 1 skipped`。

另外盤點了 `Provisional production-candidate gate`：沒有新 code change；現有
CLI/tests 已證明它是 guarded `diagnostic_only` sidecar，不改
`alignment_matrix.tsv`，summary 也固定 `production_ready=false` /
`matrix_contract_changed=false`。所以它不再是 active productization gap；
未來只有 UX rename 需求時才需要再碰。

接手狀態:

- Worktree: `C:\Users\user\Desktop\XIC_Extractor`
- Branch: `cc/framework-improvements`
- Latest productization code baseline before this handoff refresh:
  `11517c0 feat: add reintegration stability audit`. This handoff also
  describes the current low-height reintegration-stable writer diff; use
  `git log -1` after closeout for the exact committed hash.
- Git state after that product slice: branch was ahead of origin by 16 commits
  and worktree was clean before this docs consistency refresh. Run
  `git status --short --branch` for the exact current docs-only state.
- Current checkpoint scope: after five Backfill scoped writers and Targeted
  MS1 no-flag limited default. There is no apex-delta, width-only,
  shape-margin, or broad 4613-row Backfill product writer, no GUI wiring, no
  selected-candidate switch, and no manual boundary area recompute.
- 本輪 Backfill low-scan gate:
  - `standard_peak_heldout_trace_oracle.py` 是新的可重跑 oracle producer；
    low-scan clean 真實 no-RAW 85RAW artifact 在
    `output/productization_realdata_seed_guard_85raw_20260617/heldout_trace_reintegration_oracle_low_scan_clean_probe/`。
  - combined activation scope audit 仍在
    `output/productization_realdata_seed_guard_85raw_20260617/high_signal_clean_activation_scope_audit/`；
    summary 現在同時記 72 high-signal clean 與 42 low-scan clean。
  - low-scan writer 真實 no-RAW output 在
    `output/productization_realdata_seed_guard_85raw_20260617/narrow_low_scan_clean_no_raw_productization/`；
    `narrow_product_writer_expected_diff_acceptance.json` 是 pass /
    `readiness_tier=production_ready` / 42 rows。
  - focused gate 已跑：
    `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests\test_standard_peak_activation_scope_audit.py tests\test_standard_peak_backfill_productization.py tests\test_standard_peak_heldout_trace_oracle.py -q`
    -> `19 passed`，包含新增的 fail-closed coverage：同時給兩種
    scope audit、low-scan 沒有 eligible row、audit SHA 重複、audit 指到
    missing shadow SHA、shadow projection SHA 重複。
- 本輪 Backfill low-height probe:
  - `standard_peak_heldout_trace_oracle.py`  now supports
    `standard_low_height_clean_trace` as a diagnostic/oracle target class.
    This class keeps supported trace status, shape >=0.95, local/global >=0.95,
    width 0.30-0.65 min, apex delta <=0.15 min, and at least 10 boundary scans,
    but requires `cell_height < 2e6`.
  - no-RAW 85RAW heldout artifact:
    `output/productization_realdata_seed_guard_85raw_20260617/heldout_trace_reintegration_oracle_low_height_clean_probe/`;
    summary status is `fail`, with 230 eligible candidate rows / 54 families,
    20 selected family cases, 19 pass, 1 fail. The failing case is
    `HOLDOUT85TRACE001_FAM008651_TumorBC2312_DNA`, `fail_boundary`,
    boundary error `1.16445 min`, area relative error about `0.033`.
  - combined activation scope audit now also writes
    `low_height_clean_activation_value_delta.tsv` and
    `low_height_clean_activation_expected_diff_acceptance.json` under
    `output/productization_realdata_seed_guard_85raw_20260617/high_signal_clean_activation_scope_audit/`.
    It found 57 low-height clean eligible writes out of 4613 and the
    diagnostic expected-diff packet passed 57/57 with no duplicate/missing/
    unexpected/non-eligible/non-written/unchanged/blank rows.
  - Tier decision at that checkpoint was `production_candidate` only. This is
    now superseded by the later low-height bounded-window oracle plus explicit
    `--low-height-clean-activation-scope-audit-tsv` writer: 57/57 writer
    expected-diff passed and the explicit scoped writer can now claim
    `production_ready`.
- 本輪 Backfill low-height subagent review:
  - Reviewer `Jason` checked docs/control-plane/spec/index and found no P1/P2
    blocker. It raised a P3 that `tools/diagnostics/INDEX.md` did not carry the
    then-current 4613/72/42/57 tier boundary near the diagnostic entries; fixed
    by adding those counts and explicit `production_ready` vs
    `production_candidate` wording to the relevant index notes. The later
    low-height-low-scan slice added the fourth ready count, 69 rows.
  - Reviewer `Volta` checked code/tests/contracts and found no P1/P2 blocker.
    It raised a P3 that the CLI printed low-height expected-diff next to
    product-adjacent artifacts without naming it candidate-only; fixed by
    changing the CLI label to
    `Low-height clean diagnostic/candidate-only expected-diff acceptance JSON`
    and extending the CLI test to assert `product_surface_changed=FALSE` plus
    the low-height product-decision `next_action`.
- 本輪 Backfill low-height final gate:
  - `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests\test_standard_peak_heldout_trace_oracle.py tests\test_standard_peak_activation_scope_audit.py tests\test_standard_peak_backfill_productization.py -q`
    -> `22 passed`
  - `$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor tests tools scripts`
    -> pass
  - `$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor` -> pass
    (`Success: no issues found in 346 source files`)
  - `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -v --tb=short -x` ->
    `3724 passed, 1 skipped`
  - `$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts\check_diagnostics_index.py`
    -> `88 entry points, 167 total files`
  - `git diff --check` -> no whitespace errors; only Windows LF/CRLF warnings
- 本輪 Backfill apex-only probe:
  - `standard_peak_heldout_trace_oracle.py` now supports
    `standard_apex_delta_clean_trace` as a diagnostic/oracle target class.
    This class keeps supported trace status, shape >=0.95, local/global >=0.95,
    height >=2e6, width 0.30-0.65 min, and at least 10 boundary scans, but
    requires apex delta >0.15 min from the family center.
  - no-RAW 85RAW heldout artifact:
    `output/productization_realdata_seed_guard_85raw_20260617/heldout_trace_reintegration_oracle_apex_delta_clean_probe/`;
    summary status is `fail`, with 78 eligible candidate rows / 27 families,
    20 selected family cases, 17 pass, 3 fail. The max boundary error is
    `2.19621 min` and max area relative error is `0.424518`.
  - Tier decision: `production_candidate` only. No apex-delta product writer
    flag was added, and no matrix output should be claimed `production_ready`
    for this class. Do not try a quick threshold-only promotion without a new
    oracle packet, because failures include apex delta `0.2493` and `0.273`.
- 本輪 Backfill width-only probe:
  - `standard_peak_heldout_trace_oracle.py` now supports
    `standard_width_clean_trace` as a diagnostic/oracle target class. This
    class keeps supported trace status, shape >=0.95, local/global >=0.95,
    height >=2e6, apex delta <=0.15 min, and at least 10 boundary scans, but
    requires boundary width outside 0.30-0.65 min.
  - no-RAW 85RAW heldout artifact:
    `output/productization_realdata_seed_guard_85raw_20260617/heldout_trace_reintegration_oracle_width_clean_probe/`;
    summary status is `fail`, with 4 eligible candidate rows / 3 families,
    3 selected family cases, 1 pass, 2 fail. The max boundary error is
    `1.86561 min` and max area relative error is `0.599229`.
  - Tier decision: `production_candidate` only. No width-only product writer,
    activation scope audit column, or matrix output should be claimed
    `production_ready` for this class.
- 本輪 Backfill width-only subagent review:
  - Reviewer `Ohm` checked code/tests/contracts and found one P2 test-strength
    issue: the width-only test proved the over-wide happy path, but did not
    lock the narrow-width branch, inclusive `0.30` / `0.65` boundaries, or
    dirty shape/local-global/height/apex/scan sentinels. Fixed by adding
    `test_width_target_shape_class_matches_only_outside_clean_width_band`.
  - Reviewer `Hubble` checked handoff/control-plane/spec/index and found no
    P1/P2 docs/product-claim blocker.
- 本輪 Backfill width-only final gate:
  - `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests\test_standard_peak_heldout_trace_oracle.py -q`
    -> `5 passed`
  - `$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor tests tools scripts`
    -> pass
  - `$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor` -> pass
    (`Success: no issues found in 346 source files`)
  - `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -v --tb=short -x` ->
    `3727 passed, 1 skipped`
  - `$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts\check_diagnostics_index.py`
    -> `88 entry points, 167 total files`
  - `git diff --check` -> no whitespace errors; only Windows LF/CRLF warnings
- 本輪 Backfill shape-margin probe:
  - `standard_peak_heldout_trace_oracle.py` now supports
    `standard_shape_margin_clean_trace` as a diagnostic/oracle target class.
    This class keeps supported trace status, local/global >=0.95, height >=2e6,
    boundary width 0.30-0.65 min, apex delta <=0.15 min, and at least 10
    boundary scans, but requires near-threshold shape similarity
    `0.93 <= shape < 0.95`.
  - no-RAW 85RAW heldout artifact:
    `output/productization_realdata_seed_guard_85raw_20260617/heldout_trace_reintegration_oracle_shape_margin_clean_probe/`;
    summary status is `fail`, with 18 eligible candidate rows / 8 families,
    8 selected family cases, 6 pass, 2 fail. The max boundary error is
    `0.0625542 min` and summary max area relative error is `0.198393`.
  - Tier decision: `production_candidate` only. No shape-margin product writer,
    activation scope audit column, or matrix output should be claimed
    `production_ready` for this class. Do not narrow by shape threshold alone:
    one failed case has shape `0.949526`.
  - Subagent review: `Herschel` / `Kuhn` found no P1/P2 blocker. P3 fixes were
    applied: shape-margin predicate tests now cover width upper-bound
    exclusion and docs now quote the summary JSON area max (`0.198393`).
  - Final gate: `pytest tests\test_standard_peak_heldout_trace_oracle.py -q`
    -> `7 passed`; `ruff check xic_extractor tests tools scripts` -> pass;
    `mypy xic_extractor` -> pass; `pytest -v --tb=short -x` ->
    `3730 passed, 1 skipped`; diagnostics index -> pass; `git diff --check`
    -> no whitespace errors, only Windows LF/CRLF warnings.
- 前一輪 Backfill low-scan subagent review:
  - `Mendel` / `Meitner` 沒有找到 P1/P2 blocking issue。
  - P3 docs drift 已修：control-plane/spec/handoff 現在都明講 72-row
    high-signal 與 42-row low-scan 是兩個 explicit scoped
    `production_ready` slices，broad 4613-row 仍只是
    `production_candidate`。
- 前一輪完整 local gate 已跑完:
  - `$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor tests tools scripts` -> pass
  - `$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor` -> pass (`Success: no issues found in 346 source files`)
  - `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -v --tb=short -x` -> `3721 passed, 1 skipped`
  - `$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/check_diagnostics_index.py` -> `88 entry points, 167 total files`
  - `git diff --check` -> no whitespace errors; only Windows LF/CRLF warnings
- 本輪後續 focused gate:
  - `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests\test_targeted_ms1_shape_identity_expected_diff_gate.py -q` -> `9 passed`
  - `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests\test_standard_peak_backfill_productization.py -q` -> `5 passed`
  - `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests\test_provisional_backfill_candidate_gate_cli.py -q` -> `8 passed`
  - `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests\test_settings_new_fields.py tests\test_extractor_run.py::test_run_applies_targeted_ms1_shape_identity_support_tsv tests\test_extractor_run.py::test_run_limited_shape_identity_policy_without_support_tsv_keeps_output tests\test_run_extraction.py::test_cli_passes_targeted_ms1_shape_identity_support_override tests\test_run_extraction.py::test_cli_passes_targeted_ms1_shape_identity_activation_policy_override tests\test_run_extraction.py::test_cli_replay_rejects_targeted_ms1_shape_identity_support_override tests\test_run_extraction.py::test_cli_replay_rejects_targeted_ms1_shape_identity_activation_policy_override tests\test_targeted_ms1_shape_identity_projection.py -q` -> `18 passed`
  - existing 85RAW generic support expected-diff gate rerun with `--support-tsv` -> `pass`, 11 long rows, 66 matrix cells, 11 supported support rows
  - `$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor\diagnostics\targeted_ms1_shape_identity_expected_diff.py tools\diagnostics\targeted_ms1_shape_identity_expected_diff_gate.py tests\test_targeted_ms1_shape_identity_expected_diff_gate.py` -> pass
  - `$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor\diagnostics\targeted_ms1_shape_identity_expected_diff.py` -> pass
- 本輪 auto-limited CLI focused / RAW gate:
  - changed-file ruff -> pass
  - targeted auto suite before review fixes -> `29 passed`; after fail-closed
    staging/error fix -> `30 passed`
  - existing 85RAW no-RAW auto gate mirror -> `pass`, 11 long rows, 66 matrix cells
  - 8RAW auto CLI real run -> pass, 1 support row, 1 long row, 6 matrix cells
  - 85RAW auto CLI real run -> pass, 11 support rows, 11 long rows, 66 matrix cells, wall-clock `369.2 s`
  - final full local gate after subagent fixes:
    - `$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor tests tools scripts` -> pass
    - `$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor` -> pass (`Success: no issues found in 345 source files`)
    - `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -v --tb=short -x` -> `3712 passed, 1 skipped`
    - `$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/check_diagnostics_index.py` -> `87 entry points, 166 total files`
    - `git diff --check` -> no whitespace errors; only Windows LF/CRLF warnings
- 2026-06-17 subagent review: reviewers `Faraday`, `Raman`, and `Euler`
  checked the current auto-limited CLI/docs slice. Blocking issues found:
  stale handoff wording could imply auto CLI was still blocked; support/gate
  failures could traceback instead of a clean CLI error; final CSVs could be
  left under product-shaped `final/output` before the gate passed. Fixes:
  handoff wording now separates explicit auto CLI ready from no-flag default
  still-off; auto workflow writes second extraction to
  `final_unverified/output`, runs expected-diff gate there, publishes to
  `final/output` only after pass, writes final manifest after publish, and
  returns exit code `2` with concise stderr if support/gate/schema errors occur.
- 2026-06-17 subagent review: reviewer `Cicero` found the Targeted MS1
  expected-diff CLI/package gate could still pass without `--support-tsv`.
  Fixed by making `--support-tsv` required and by making the package evaluator
  raise when support rows are missing; added focused red/green coverage.
- 2026-06-17 subagent review: reviewer `Dirac` found one P3 docs drift where
  the shared peak-identity spec still used old output-only support-gate wording.
  Fixed the wording to require the actual support TSV; focused gate remains
  `9 passed`.
- 2026-06-17 subagent review: reviewer `Maxwell` 驗收目前 dirty diff，
  沒有發現 blocking issue。Reviewer 實際重跑 `git diff --check`，抽查
  8RAW/85RAW opt-in artifact path 存在；ruff/mypy/full pytest/diagnostics
  index 結果採主 agent 已跑過的 gate 紀錄，沒有重跑 RAW。
- 2026-06-17 subagent review: reviewer `Peirce` 針對後續 seed-guard /
  heldout-oracle delta 找到兩個 blocking contract issue 和一個 fail-closed
  hardening issue：heldout oracle manifest schema 沒強制完整欄位、
  duplicate/extra observed oracle rows 可被忽略、`blocked_unattributed_write`
  沒升成 productization failure。這三點已修，並補了紅燈轉綠測試。
- 2026-06-17 subagent review: reviewer `Euclid` 驗修後 diff，沒有 blocking
  issue；它指出 heldout manifest 只鎖欄位、未鎖 schema version。已補
  `standard_peak_seed_guard_heldout_oracle_manifest_v1` value guard 和測試。
- 2026-06-17 subagent review: reviewer `Noether` 最後驗收 dirty diff，
  沒有 P1/P2 blocking issue；它指出 direct package evaluator 只鎖
  schema version，完整 manifest 欄位保護主要在 CLI 讀檔層。已補
  package-level required-column guard 和 direct helper 測試。
- 2026-06-17 繼續推進: alignment 的 `--sample-column-injection-order`
  現在也可吃 `sample_metadata_v1` CSV/TSV，投影成相同 injection-order
  mapping 來排序 final matrix/status sample columns。這是 no-output-value
  slice：不讀 role/batch/matrix/exclusion 來改 matrix values、counted
  detection、feature acceptance 或 backfill activation。
- 2026-06-17 繼續推進: RT-normalization anchor diagnostic 的
  `--sample-info` 現在也可吃 `sample_metadata_v1` CSV/TSV，用同一個 shared
  resolver 投影 injection order 給 `injection-local-median` /
  `injection-loess` reference lookup。這仍是 no-output-value slice：
  role/batch/matrix/exclusion 不改 normalized values、matrix values、
  counted detection 或 calibration/main-matrix writes。
- 2026-06-17 subagent review: reviewer `Descartes` 驗收 RT-normalization
  resolver slice，沒有 P1/P2 blocker；它指出 parity test 只覆蓋
  `injection-local-median`，已補成同時覆蓋 `injection-loess`，focused suite
  現在 `16 passed`。
- 2026-06-17 繼續推進: 新增
  `tools/diagnostics/standard_peak_heldout_oracle_results.py`，把已存在的
  heldout oracle evaluator 變成可執行 CLI gate。它只讀 deterministic
  manifest + observed boundary/area rows 並寫 `heldout_oracle_results.tsv`，
  不跑 RAW、不產生 reviewed oracle、不改 matrix、不授權 non-standard peak。
  Peirce/Euclid/Noether review 後，CLI 和 package evaluator 會強制 spec
  要求的完整 manifest 欄位與 manifest schema version，且 observed result
  rows 若 duplicate 或帶有 manifest 外的 stale case 會 fail-closed。
- 2026-06-17 真實資料最小驗證: 沒有重跑 RAW，而是重用既有
  `standard_peak_backfill_preset_85raw_20260610` 的 85RAW
  validation-minimal matrix/review/shadow projection，跑新的
  standard-path seed-guard productization bridge。輸出在
  `output/productization_realdata_seed_guard_85raw_20260617/r1_120_no_raw_productization/`；
  2540 個 standard-path candidates 中，1160 個通過
  `eligible_continue_existing_gates` 並寫入 `activation_value_delta.tsv`，
  1380 個被 `blocked_low_seed_support` 擋下。這補強
  `production_candidate`，但不是 `production_ready`。
- 2026-06-17 consolidated no-RAW 驗證: 同樣沒有開 RAW，重用既有 85RAW
  consolidated shadow projection 和 pre-standard-backfill matrix/identity，
  跑到
  `output/productization_realdata_seed_guard_85raw_20260617/consolidated_no_raw_productization/`。
  7307 個 standard-path candidates 中，4613 個通過
  `eligible_continue_existing_gates` 並寫入 `activation_value_delta.tsv`，
  2694 個被 `blocked_low_seed_support` 擋下；`write_authority_status`
  只有 `cohort_scale_standard_backfill` 和 `no_write`，沒有
  `blocked_unattributed_write`。這把 candidate evidence 從 chunk smoke 擴到
  完整既有 85RAW consolidated artifact，但仍不是 reviewed oracle。
- 2026-06-17 subagent review: reviewer `Popper` 驗收 consolidated no-RAW
  Backfill evidence/docs，沒有 blocking issue；它重新檢查 summary/TSV counts，
  確認 7307 candidates、4613 writes、2694 low-seed no-writes、
  `blocked_unattributed_write=0`，且 docs 沒有把這段 overclaim 成
  `production_ready` 或 reviewed oracle。
- 2026-06-17 heldout oracle source audit: 沒找到現成
  `heldout_oracle_manifest.tsv`、observed oracle TSV、或
  `heldout_oracle_results.tsv`。我把 raw85 manual verdict 11 rows 對 current
  consolidated seed-guard candidates 做 crosswalk，輸出在
  `output/productization_realdata_seed_guard_85raw_20260617/heldout_oracle_source_audit/`：
  11 rows 都有 oracle boundary/area source，但只有 2 rows 對得上 current
  seed-guard candidate；那 2 rows 有 observed area，但缺 independent observed
  start/end boundary。剩下 9 rows 沒有 current seed-guard key match。所以
  Backfill 要升 `production_ready` 不是少跑一條命令，而是缺 observed
  boundary/area result source；這個 source 必須符合下面的 observed-result
  provenance contract。
- 2026-06-17 繼續推進: Backfill 的 boundary-observation contract 已經收斂成
  `heldout_observed_results.tsv` provenance schema。Observed rows 不能只放
  start/end/area，還必須寫 `observed_result_source`、
  `observed_boundary_source`、`observed_area_source`、
  `observed_independence_basis`；允許的 independence basis 只有
  `product_writer_observed_result`、`masked_rerun_observed_result`、
  `independent_boundary_reintegration_result`。明顯來自 oracle/manual
  review/review queue 的自抄 row 會 fail-closed。這把 contract gap 關掉，
  但還沒有產生真正 reviewed observed rows，所以 Backfill 仍是
  `production_candidate`。
- 2026-06-17 subagent review: reviewer `Gibbs` 驗收 observed-result provenance
  slice，找到兩個 blocker：source-copy detector 只抓 underscore token，
  容易被 `manual review` / `manual-review` / `review queue` / `oracle-source`
  這類字串繞過；另外 `result_source_artifact` 不存在時會寫空 SHA。已修：
  source label 現在會 canonicalize whitespace/punctuation 後再判斷，且
  `result_source_artifact_path` 必須存在且是檔案，否則 fail-closed。
- 2026-06-17 繼續推進: 我又檢查了現有 trace artifact，發現目前能 match
  current seed-guard candidate 的兩筆 raw85 reviewed rows
  (`FAM002634 / Breast_Cancer_Tissue_pooled_QC3`、`FAM017068 /
  Breast_Cancer_Tissue_pooled_QC5`) 在 trace data 裡是 `status=rescued`，
  不是 originally detected quantifiable cells。已把這點鎖進
  `heldout_oracle_manifest.tsv` schema：新增 required
  `heldout_original_cell_status`，只接受 `detected`、`detected_seed`、
  `quantifiable_detected`、`accepted_detected`；`rescued` 會 fail-closed。
  所以這兩筆仍可作 manual same-peak support，但不能當
  `production_ready` heldout oracle cases。
- 2026-06-17 subagent review: reviewer `Ptolemy` 又找到 observed provenance
  的 P2：如果 observed source 用中性 label 自抄 manifest `oracle_source`，
  舊 token detector 可能看不出來。已修：observed row validation 會帶入
  matching manifest，canonicalized source label 不能等於該 row 的
  `oracle_source`；也補齊 original-cell-status allowlist、blank/unknown、
  neutral source-copy tests。Focused heldout-oracle suite 現在 `25 passed`；
  Backfill + shadow activation focused suite 現在 `42 passed`。
- 2026-06-17 Backfill heldout trace oracle: 沒有重跑 RAW，而是重用既有
  `standard_peak_backfill_preset_85raw_20260610` validation-minimal trace
  arrays 和 `alignment_backfill_cell_evidence.tsv`，產生
  `output/productization_realdata_seed_guard_85raw_20260617/heldout_trace_reintegration_oracle/`。
  這組 artifact 選 20 個 originally detected、sample-local、高訊號、
  clean standard trace cases，跨 20 個 family；observed rows 用 current
  `local_minimum` `find_peak_and_area` + `integration_from_peak_trace` 對
  stored trace arrays 重新算 start/end/area，並標成
  `independent_boundary_reintegration_result`。正式
  `standard_peak_heldout_oracle_results.py` gate 結果是 20/20
  `oracle_case_status=pass`、20/20 included，最大 boundary error
  0.0820502 min、最大 area relative error 0.0762325，低於使用者接受的
  `0.1 min / 10% area`。同目錄也有
  `heldout_trace_reintegration_full_eligible_pool.tsv`，保存 80 個
  pre-observed eligible rows、quality rank、selected flag、未選原因；未選 rows
  不帶 observed reintegration outcome。這證明 high-signal clean standard
  trace slice，但不等於目前 4613 個 eligible activation writes 全部都 broad
  `production_ready`。
- 2026-06-17 Backfill activation scope audit: 新增
  `tools/diagnostics/standard_peak_activation_scope_audit.py` 和
  `xic_extractor/diagnostics/standard_peak_activation_scope_audit.py`，用既有
  consolidated no-RAW `activation_value_delta.tsv`、consolidated
  `consolidated_shadow_projection_cells.tsv`、以及 sibling `*_trace_data.json`
  產生
  `output/productization_realdata_seed_guard_85raw_20260617/high_signal_clean_activation_scope_audit/`。
  這不是 RAW rerun，也不改 matrix；它只是問 actual writes 是否落在剛通過
  heldout oracle 的 high-signal clean envelope。結果：
  `written_activation_row_count=4613`、`projection_matched_written_count=4613`、
  `trace_matched_written_count=3526`、`missing_overlay_path_written_count=1087`、
  `high_signal_clean_eligible_written_count=72`、
  `high_signal_clean_ineligible_written_count=3454`、
  `broad_activation_scope_status=not_ready`。因此 high-signal clean 72-row
  subset 可以當下一個明確 product-scope decision，但不能把 broad 4613-row
  bridge 直接升 `production_ready`。
- 2026-06-17 Backfill narrow expected-diff acceptance: 同一個
  `standard_peak_activation_scope_audit.py` 現在也寫
  `narrow_activation_expected_diff_acceptance.tsv/json`。真實 no-RAW artifact
  結果是 `acceptance_status=pass`、`full_written_delta_row_count=4613`、
  `eligible_audit_row_count=72`、`eligible_delta_row_count=72`，且
  duplicate/missing/unexpected/non-eligible/non-written/unchanged/blank 都是
  0。這證明 72-row subset 是乾淨的 expected-diff candidate；但 summary
  也寫 `product_surface_changed=FALSE` 和
  `next_action=product_decision_required_before_writing_narrow_activation_output`，
  所以還不能說 narrow product behavior 已啟用。
- 2026-06-17 Backfill narrow product writer: 已把上一段的 72-row scope 接到
  `tools/diagnostics/standard_peak_backfill_productization.py` 的 explicit opt-in
  writer flag：`--high-signal-clean-activation-scope-audit-tsv`。新真實 no-RAW
  85RAW consolidated run 寫在
  `output/productization_realdata_seed_guard_85raw_20260617/narrow_high_signal_clean_no_raw_productization/`；
  summary 是 `status=pass`、`activation_scope_filter_status=applied`、
  `selected_activation_row_count=72`、`matrix_cells_written=72`、
  `activation_value_delta_written_count=72`。新的
  `narrow_product_writer_expected_diff_acceptance.json` 是
  `acceptance_status=pass`、`readiness_tier=production_ready`、
  `product_surface_changed=TRUE`，且 duplicate/missing/unexpected/non-eligible/
  non-written/unchanged/blank 都是 0。這讓 Backfill 的「explicit 72-row
  high-signal-clean scoped writer」升到 `production_ready`；broad 4613-row
  activation 仍維持 `production_candidate`。
- 2026-06-17 subagent review: reviewer `Russell` 驗收 Backfill activation
  scope audit slice，沒有 P1/P2 blocker。它指出三個 P3：測試應鎖住
  provenance SHA join、threshold blockers 覆蓋不足、handoff 底部下一步
  framing 過期。已補 SHA-only join 測試、threshold blocker 測試；後續也
  已補上 72-row narrow product writer，所以目前下一步不再是 72-row
  scope decision，而是 broad 4613-row evidence decision。
- 2026-06-17 subagent review: reviewer `Mill` 驗收 Backfill narrow product
  writer slice，找到一個 P2：productization summary 新增 public 欄位但仍
  報 `standard_peak_backfill_productization_v0`。已修成
  `standard_peak_backfill_productization_v1`，補 focused schema assertion，
  更新 spec，並重跑 narrow no-RAW artifact；summary JSON 現在是 v1，
  72/72 writer acceptance 仍 pass。
- 2026-06-17 產品決策: 使用者已接受 Backfill heldout oracle 第一版 gate
  使用 boundary error `<=0.1 min`、area relative error `<=10%`；也接受
  `NL_FAIL/NO_MS2` limited opt-in policy 的第一版範圍先限 `5-hmdC + 5-medC`，
  且產品輸出只能寫 `detected_flagged`，不能寫乾淨 `detected`。這是
  policy acceptance，還不是 runtime default 已啟用。
- 2026-06-17 繼續推進: Backfill heldout oracle manifest 現在會 fail-closed
  拒絕比 `0.1 min / 10% area` 更鬆的 tolerance；reviewed row 可以更嚴格，
  但不能偷偷放寬 acceptance gate。這只鎖 oracle gate，不改 matrix writer。
- 2026-06-17 subagent review: reviewer `Linnaeus` 找到 tolerance-ceiling slice
  的 exact-threshold float compare P2：數學上剛好 `0.1 min` 或 `10% area`
  可能被浮點誤差打成 fail。已補 exact-boundary tests 和 shared comparison
  helper；focused backfill suite 現在 `27 passed`。
- 2026-06-17 繼續推進: `NL_FAIL/NO_MS2` 的 accepted limited scope 已有
  opt-in activation policy guard：新增 settings key
  `targeted_ms1_shape_identity_activation_policy`，CLI flag
  `--targeted-ms1-shape-identity-activation-policy`，以及
  `limited_5hmdc_5medc_v1`。這個 policy 只允許 support TSV 內的 supported
  rows 落在 `5-hmdC/5-medC`；當時 default 仍是 `explicit_support_tsv`，
  所以沒有啟用自動 rescue。後續本輪已把 canonical no-flag CLI default 接到
  同一個 auto gate。
- 2026-06-17 繼續推進: 新增 headless auto-limited CLI
  `--targeted-ms1-shape-identity-auto-limited-default`。當時它不是無旗標 default；
  使用者必須明確加這個 flag。加 flag 後 workflow 會先跑 baseline CSV、
  自動產 limited support TSV、再跑 final extraction，並輸出
  `expected_diff_summary.tsv`、`matrix_diff_summary.tsv`、以及
  `limited_default_expected_diff_gate_summary.tsv`。8RAW real run 通過 1 row，
  85RAW real run 通過 11 rows / 66 matrix cells，所以這個 headless auto CLI
  也可列為 `production_ready` for `5-hmdC + 5-medC` / `detected_flagged`。
  後續本輪已把 canonical no-flag CLI default 改成重用這個 workflow。
- 2026-06-17 85RAW expected-diff gate: 新增
  `tools/diagnostics/targeted_ms1_shape_identity_expected_diff_gate.py`，並重用
  既有 `output/ms1_shape_identity_generic_support_85raw_20260616/` artifact
  跑 gate。結果寫在
  `output/ms1_shape_identity_generic_support_85raw_20260616/limited_default_expected_diff_gate_summary.tsv`：
  `gate_status=pass`、11 個 long rows、66 個 matrix cells，全部只限
  `5-hmdC/5-medC`，product output 全部是 `detected_flagged`，且 gate
  現在會要求 long-row diff 與 matrix diff 的 sample/target key set 一致。
- 2026-06-17 subagent review: reviewer `Ampere`
  implementation-contract review 無 P1/P2 blocker；當時確認 default 仍是
  `explicit_support_tsv`、沒有 support TSV 時不會消費 shape identity、
  replay 會拒絕新 override、manifest 有記錄 activation policy。
- 2026-06-17 subagent review: reviewer `Averroes`
  validation-evidence review 無 blocker；接受目前 evidence 只支援
  explicit/limited opt-in `production_candidate`，不支援
  `production_ready` 或 no-flag default rescue。它建議的 key-set equality
  與 policy-alone no-output-change hardening 已補，focused tests `7 passed`，
  既有 85RAW gate 重跑仍 `pass`。
- 2026-06-17 繼續推進: Targeted MS1 limited expected-diff gate 現在必須帶
  `--support-tsv`，會重用正式 support TSV loader，要求 accepted support
  sample/target keys 和 long-row product diff keys 完全一致。既有
  85RAW generic artifact 以 no-RAW 方式重跑通過：
  `long_changed_rows=11`、`matrix_changed_cells=66`、
  `support_tsv_supported_rows=11`、target split
  `5-hmdC=10;5-medC=1`。這把 headless explicit limited support-TSV
  workflow 從 `production_candidate` 推到 `production_ready`；當時無旗標
  normal-extraction rescue 仍 `blocked`，後續已新增 explicit auto CLI，且本輪
  已把 canonical no-flag CLI default 接到同一個 auto gate。
  本輪 full local gate 也已重跑通過：
  ruff、mypy、full pytest `3705 passed, 1 skipped`、diagnostics index、
  `git diff --check`。

目前 tier 結論:

- `method_manifest` / headless targeted CLI replay parity: `production_ready`
  for targeted CLI replay parity only；不是 GUI replay，也不是 workbook
  byte-exact replay。
- `ReviewAction` audited apply copy: usable as audited output copy；selected
  candidate switch 與 manual-boundary area recompute 已 `parked`，因為會改
  selected peak/area/counting，需要產品決策和 expected-diff。
- `sample_metadata_v1`: extraction injection-order parity 已可用；
  instrument-QC method-doc workflow 會輸出 additive
  `instrument_qc_sample_metadata.tsv`；alignment sample-column ordering 也可
  consume `sample_metadata_v1`；RT-normalization anchor diagnostic 的
  injection-based reference lookup 也可 consume `sample_metadata_v1`；
  roles/batch/matrix/exclusion 不改 quant output 或 normalized values。
- Targeted MS1 shape identity / `NL_FAIL` explicit support TSV workflow:
  `production_ready` for headless explicit limited support-TSV workflow、
  explicit auto-limited CLI、以及 canonical no-flag normal CLI default。
  `limited_5hmdc_5medc_v1` 已有 settings/CLI guard、manifest provenance、
  replay override rejection、85RAW expected-diff gate，以及 support TSV
  key-set equality gate；範圍只限 `5-hmdC + 5-medC` 且只能寫
  `detected_flagged`。GUI automatic rescue 仍沒有啟用，broader targets 也還沒有
  expected-diff evidence。
- Standard-path backfill seed guard: broad lane 仍是 `production_candidate`；
  high-signal clean standard trace heldout oracle slice 已有可重跑 passing
  evidence。既有能力包含
  `seed_guard_decisions.tsv`、N-band seed support、candidate coverage、
  `activation_value_delta.tsv` write attribution、可執行 heldout oracle result
  CLI gate，並已在既有 85RAW chunk `r1_120` artifact 上跑過 no-RAW bridge。
  也已在既有 85RAW consolidated artifact 上跑過 no-RAW bridge：
  7307 candidates、4613 writes、2694 low-seed no-writes、0 個
  `blocked_unattributed_write`。
  若 post-apply attribution 看到 `blocked_unattributed_write`，productization
  summary 現在會 `status=fail` 並要求 review seed-guard write attribution。
  使用者已接受 heldout oracle 第一版 tolerance: boundary error `<=0.1 min`
  與 area relative error `<=10%`，且 code 現在拒絕更鬆的 manifest
  tolerance；剛好等於門檻的 float 邊界會視為通過。新的 heldout trace
  oracle 已補上 high-signal clean standard scope 的 originally detected
  observed rows 並 20/20 pass。後續 activation scope audit 證明目前 4613
  writes 中只有 72 個符合這個 envelope、1087 個 missing overlay/trace
  evidence、3454 個不符合 high-signal clean 條件。72-row subset 的
  delta-level expected-diff acceptance 已 pass，且新的 explicit writer 已
  收窄到這 72 rows 並跑出 `readiness_tier=production_ready`。目前 blocker
  只剩 broad 4613-row activation：若要承認整個 consolidated bridge，就需要
  覆蓋目前 4613-row activation scope 的 broader masked/product-writer
  observed oracle。

下一個最安全動作:

1. 若要收 PR，先檢查 diff scope、整理 commit/PR description，然後看遠端 CI。
2. 若要繼續產品化，Backfill 下一步不是再找「有沒有 heldout case」：
   high-signal clean trace 的 20-case oracle 已通過，且 activation scope
   audit 已證明只有 72/4613 writes 符合同一 envelope。72-row high-signal
   clean subset 的 writer 已收窄並通過 expected-diff；如果要承認目前
   consolidated bridge 的 4613 writes，就需要
   broader masked/product-writer observed oracle，而不是用這 20 筆代表全部。
3. `NL_FAIL` headless default 行為已完成到 bounded limited scope。現在可
   claim `production_ready` 的是 headless explicit support-TSV workflow、
   headless auto-limited CLI、以及 canonical no-flag normal CLI default；三者
   都只限 `5-hmdC + 5-medC` 且只能寫 `detected_flagged`。仍不能 claim GUI
   或 broader target default rescue。
4. `Provisional production-candidate gate` 已記成 guarded `diagnostic_only`；
   不要把 `alignment_production_candidate_gate.tsv` 當 product authority。
5. Sample metadata 的 no-output resolver parity 已接到
   extraction、instrument-QC、alignment、RT-normalization anchor diagnostic；
   下一步若碰 QC/blank/batch/matrix role，必須先有 expected-diff gate，
   不能直接改 normalized values 或 matrix values。

## 目前可接手狀態

- Branch: `cc/framework-improvements`。
- 2026-06-16 本輪 `/goal` 收斂結果:
  - `sample_metadata_v1` 已投射到 instrument-QC method-doc workflow:
    `run_instrument_qc.py --method-doc` 會新增
    `instrument_qc_sample_metadata.tsv`。這是 additive metadata sidecar，
    pipeline 仍用 `instrument_qc_injection_order.csv` 做 order parity；
    role/batch/matrix/exclusion 不改 trend、quant、counted detection 或矩陣。
  - Standard-path backfill seed guard 已到 `production_candidate`:
    `standard_peak_backfill_productization.py` 會在 activation 前用
    pre-backfill matrix/review 計算 N-band seed support，並輸出
    `seed_guard_decisions.tsv`。Productization apply 後會把
    `activation_value_delta.tsv` 寫回同一 artifact，證明 actual writes 是
    cohort-scale 或 per-cell attribution。這還不是 `production_ready`：
    source audit 已證明現有 raw85 manual verdict 只有 2 筆對得上 current
    seed-guard candidate，且那兩筆是 `rescued`、不能當 originally detected
    heldout；後續已補 high-signal clean trace 20-case heldout oracle 並
    20/20 pass。Broad activation 仍需 scope decision / expected-diff gate。
  - Targeted MS1 shape identity 的 explicit support-TSV workflow 當時先標
    `production_candidate`，沿用既有 8RAW/85RAW opt-in artifacts；後續已補
    `--support-tsv` key-set gate，把 headless explicit
    `limited_5hmdc_5medc_v1` workflow 升到 `production_ready`。再後續已把
    headless auto-limited CLI 和 canonical no-flag normal CLI default 也推到
    `production_ready` for `5-hmdC + 5-medC` / `detected_flagged`。GUI 和
    broader targets 仍未啟用。
  - ReviewAction selected-candidate switch 與 manual-boundary area recompute
    已明確 `parked`：它們會改 selected peak/area/workbook/matrix，需要人類產品
    決策與 expected-diff gate，不能在本輪偷做。
- 2026-06-16 修後驗收已針對 subagent 擋下的 productization blockers 收尾：support TSV 進 manifest hash/replay 驗證、support ingestion 改成 full evidence-bearing schema、strong competing peak fail-closed、support builder 需要 paired RT support、壞 support TSV 會回報 `ConfigError`、settings/example/docs/handoff 已同步。修後想再派 subagent 時工具回報 thread limit reached，所以這輪最後驗收由主 agent 本地完成。
- 2026-06-16 正在追 `TumorBC2294_DNA / 5-hmdC` 這類 `NL_FAIL` 但 MS1 trace 有峰的 rescue/backfill activation policy。這不是 replay executor 主線；目前已有一個 fail-closed product projection gate 變更，但還沒有 RAW-backed evidence provider 會自動發補值 token。
- 目前結論: 舊 top-level `output/xic_results_long.csv` 是 2026-05-22 舊 artifact，不能代表 current HEAD。current HEAD 單一 RAW repro 內部選到約 `9.11708 min` candidate，但產品輸出仍 `not_counted`，因為缺正式 activation policy。
- 新增必須保留的 gate: `NL_FAIL` analyte 要自動補值，除了 MS1/ISTD/area-ratio 支持外，還必須通過 Gaussian-smoothed own-max normalized same-peak similarity。這是 identity gate，不是拿 normalized intensity 當定量值。
- 已產出 5-case own-max diagnostic: `output/ms1_rescue_5hmdc_own_max_similarity_20260616/own_max_similarity_summary.tsv` 和 `5hmdc_own_max_similarity_diagnostic.png`。結果支持 9.04-9.17 這組 same-peak mode；`TumorBC2294_DNA` 的 9.1171 own-max r = 0.95388，舊 artifact 的 9.7142 competing ratio = 0.20005，低於 provisional review line 0.25。
- 程式接點已改成 fail-closed: `xic_extractor/extraction/paired_area_ratio_projection.py` 仍只會加 `paired_area_ratio_support` / paired RT support；`xic_extractor/extraction/result_assembly.py` 現在還要求 `own_max_same_peak_support`，才會解除 analyte `NL_FAIL` / `NO_MS2` 的 not-counted policy。
- 已新增 shared target/untarget peak identity spine spec: `docs/superpowers/specs/2026-06-16-shared-target-untarget-peak-identity-spine-spec.md`。它把這條線定義成「共享 identity evidence provider + workflow-owned product projection」；untargeted 的 own-max/anchor/competing-peak 方法可移植，targeted 仍保留 pair RT、area ratio、role/applicability、NL policy 與 expected-diff gate。
- 已新增第一個 no-behavior-change shared helper: `xic_extractor/peak_detection/ms1_shape_identity.py`，測試在 `tests/test_ms1_shape_identity.py`。它只處理 Gaussian smooth、own-max normalization、local shape similarity、competing peak summary；目前沒有任何 product projection 使用它。
- 已把一個既有 untargeted diagnostic caller 接到 shared helper: `tools/diagnostics/family_ms1_overlay_evidence.py` 的 `_gaussian_smooth_values(...)` 現在委派給 `ms1_shape_identity.gaussian_smooth_values(...)`，保留原 wrapper/import surface，不改輸出 schema。
- 已新增 targeted diagnostic adapter: `xic_extractor/diagnostics/targeted_ms1_shape_identity.py`，測試在 `tests/test_targeted_ms1_shape_identity.py`。它會把 candidate/reference MS1 traces 轉成 `targeted_ms1_shape_identity_v0` 診斷 rows，包含 own-max same-peak similarity、paired ISTD RT delta、target-window status、competing peak warning；仍然是 `diagnostic_only_no_product_write`，不會自動補 `NL_FAIL`、不會切 candidate、不會改 workbook/matrix。
- 已新增正式 converter CLI: `tools/diagnostics/targeted_ms1_shape_identity_from_grid.py`，測試在 `tests/test_targeted_ms1_shape_identity_from_grid.py`。它取代一次性 inline script，讀 `own_max_similarity_summary.tsv` + `own_max_similarity_trace_grid.tsv`，輸出 `targeted_ms1_shape_identity_v0`。
- 已用正式 CLI 對 5-case trace grid 重跑本地 ignored artifact: `output/ms1_rescue_5hmdc_own_max_similarity_20260616/targeted_ms1_shape_identity_v0.tsv`。五個 row 都是 `own_max_same_peak_supported`，而且 `own_max_same_peak_support_reason=own_max_same_peak_support`；但這份 projection 用的是整理後 trace grid，competing-peak 權威仍看原 `own_max_similarity_summary.tsv` 的欄位。
- 已新增 fail-closed product projection gate: `xic_extractor/extraction/result_assembly.py` 現在要求 `own_max_same_peak_support`，否則 `paired_area_ratio_support` 不能解除 analyte `NL_FAIL` / `NO_MS2` 的 not-counted policy。常數放在 `xic_extractor/extraction/targeted_projection_reasons.py`。
- `paired_area_ratio_projection.py` 不會自己產生 own-max token；它只補 run-level paired RT / area ratio。換句話說，正常 extraction 只有在上游 evidence/provider 已明確帶 `own_max_same_peak_support` 時才可能補值。
- 已新增 explicit opt-in ingestion 入口: settings key `targeted_ms1_shape_identity_support_tsv` 和 CLI flag `--targeted-ms1-shape-identity-support-tsv`。預設空值，不會自動補值；只有使用者明確提供 reviewed `targeted_ms1_shape_identity_v0` TSV 時，normal extraction pipeline 才會把 `own_max_same_peak_support` 投進 projection。GUI 尚未接。
- Synthetic expected-diff fixture: `docs/superpowers/fixtures/targeted_nl_fail_own_max_gate_expected_diff_v0.tsv`。這只負責 unit contract；8RAW/85RAW product diff 證據看下面的 explicit opt-in smoke artifacts。
- 2026-06-16 targeted MS1 no-RAW 驗證: focused productization tests `61 passed`，broader related suite `263 passed`，`uv run ruff check xic_extractor tests tools scripts` passed，`uv run mypy xic_extractor` passed，`python -m scripts.check_diagnostics_index` passed，`git diff --check` 只有 CRLF warnings、無 whitespace error。8RAW 和 85RAW explicit opt-in smoke 都已跑；2026-06-17 最新全 repo gate 見後面的驗證段落。
- 8RAW explicit opt-in smoke artifact: `output/ms1_shape_identity_optin_8raw_20260616/expected_diff_summary.tsv`。baseline/opt-in 都用 validation 8RAW、CSV-only；只改到 `TumorBC2263_DNA / 5-hmdC` 一列，從 `not_counted / FALSE / RT=ND / Area=ND` 變 `detected_flagged / TRUE / RT=9.1705 / Area=145695.76`，support 多了 `own_max_same_peak_support`，`analyte_nl_fail_requires_policy` 被移除。
- 第一輪 85RAW manual-support opt-in smoke artifact: `output/ms1_shape_identity_optin_85raw_20260616/expected_diff_summary.tsv` 和 `matrix_diff_summary.tsv`。baseline/opt-in 都用 full tissue 85RAW、CSV-only；只改到 reviewed support TSV 的 5 個 `5-hmdC` rows，全部從 `not_counted / FALSE` 變 `detected_flagged / TRUE`。unexpected changed rows = 0，support_not_changed = 0，wide matrix 只改 30 個 5-hmdC value cells。
- 使用者指出「不應該只有 5 rows」。這個判斷是對的：5-row 是因為上游 support TSV 只餵了手動 review 的 5 cases，不是 product gate 只能吃 5 rows。
- 已新增 generic RAW-backed support producer: `tools/diagnostics/build_targeted_ms1_shape_identity_supports.py`，核心 helper 在 `xic_extractor/diagnostics/targeted_ms1_shape_identity_support_builder.py`，測試在 `tests/test_targeted_ms1_shape_identity_support_builder.py` 和 `tests/test_build_targeted_ms1_shape_identity_supports.py`。它會從 baseline `xic_results_long.csv` 自動挑出 analyte `NL_FAIL/NO_MS2`、已被 `analyte_nl_fail_requires_policy` 擋住、且已有 `paired_area_ratio_support` 的 rows，再用 Gaussian-smoothed local own-max same-peak gate 產 support TSV。
- Generic producer 85RAW artifact: `output/ms1_shape_identity_generic_support_85raw_20260616/targeted_ms1_shape_identity_v0.tsv`。它找到 11 個候選 support rows：10 個 `5-hmdC` 加 1 個 `5-medC`，全部 `own_max_same_peak_supported=TRUE`。
- 2026-06-16 修後重跑 generic producer：仍是 11 candidate rows / 11 evidence rows / 13 trace requests。support TSV keys 跟既有 generic 85RAW `expected_diff_summary.tsv` 的 11 個 changed rows 完全一致；baseline state 全部 `not_counted / FALSE`，opt-in state 全部 `detected_flagged / TRUE`。這次沒有重跑 85RAW extraction。
- 已用 generic TSV 跑一次 85RAW opt-in（沒有重跑 baseline，baseline 沿用 `output/ms1_shape_identity_optin_85raw_20260616/baseline`）：`output/ms1_shape_identity_generic_support_85raw_20260616/optin/output/xic_results_long.csv`。diff summary 在 `output/ms1_shape_identity_generic_support_85raw_20260616/expected_diff_summary.tsv` 和 `matrix_diff_summary.tsv`。
- Generic 85RAW opt-in 結果：剛好 11 rows 從 `not_counted / FALSE` 變 `detected_flagged / TRUE`，wide matrix 66 cells changed，`xic_diagnostics.csv` SHA256 與 baseline 完全相同。新增 rows 包含 `BenignfatBC0980_DNA / 5-hmdC`、`NormalBC2259_DNA / 5-hmdC`、`NormalBC2270_DNA / 5-hmdC`、`NormalBC2272_DNA / 5-hmdC`、`NormalBC2294_DNA / 5-hmdC`、`NormalBC2264_DNA / 5-medC`，所以不再只限原本 5 rows。
- 給使用者 review 的整理包: `docs/superpowers/reports/2026-06-16-5hmdc-own-max-optin-review.md`。先看這份，不要直接從一堆 output CSV 開始翻。
- 使用者已接受第一版 limited opt-in 政策：先限 `5-hmdC + 5-medC`，且 rescue 只能寫 `detected_flagged`，不能寫乾淨 `detected`。五列手動 TSV smoke 和 11-row generic TSV smoke 都已跑完；settings/CLI guard、replay override rejection、manifest provenance、expected-diff gate 也已補上。當時的下一個安全點是決定是否把 support producer/consumer 接到自動 workflow；後續本輪已完成 explicit auto CLI 和 canonical no-flag headless CLI default。GUI 仍不是 production-ready。
- 2026-06-17 後續更新: 上面的「下一個安全點」已完成到 headless auto CLI：
  `--targeted-ms1-shape-identity-auto-limited-default` 會在同一個 run 裡建立
  support TSV、rerun final extraction、並跑 expected-diff gate。後續本輪又把
  canonical no-flag headless CLI default 接到同一 workflow；目前仍沒有 GUI
  wiring，也沒有 broader target default。
- Current debug note: `output/debug_tumorbc2294_5hmdc_current_code_20260616_110408/root_cause_note.md`。
- 剛剛的 subagent 驗收不是直接 pass: reviewer 擋下 hook fixture 可信度、manifest replay config 綁定、expected-diff stale approval、sample metadata alias collision。這些已在 follow-up 修正並用 focused tests/hook fixture 重跑。
- 目前這批 productization 變更已分批 commit；接手時仍先看
  `git status --short --branch` 和本文件最上方的目前 HEAD / clean-state
  註記。
- 目前 productization 權威不是這份 handoff: tier、active lane、WIP limit 以 `docs/superpowers/plans/2026-06-15-productization-control-plane.md` 為準。本輪已同步 control plane maintenance log；若衝突，以 control plane 為準。
- 這份 handoff 只回答「最近做了什麼、什麼真的可用、下一步怎麼接」，不能用「比較新」覆蓋 control plane 或 named spec。
- 若後續還要 commit/stage，要整包檢查，不要只 stage 修改檔。
- 此 handoff refresh 當下沒有未追蹤 productization 檔案；若後續又出現
  untracked files，仍以 `git status --short --branch` 為準，並按 lane 檢查
  不要只 stage modified files。
- Hook/交接設計剛被 critical review 挑戰過；目前已補 repo-local hook guardrail，且 2026-06-16 local closeout 已重跑 hook fixture smoke。

本輪 commit scope 內新增 files:

- `docs/superpowers/handoffs/README.md`
- `docs/superpowers/notes/2026-06-15-replay-executor-validation-note.md`
- `docs/superpowers/handoffs/current/cc-framework-improvements-productization.md`
- `docs/superpowers/specs/2026-06-15-method-manifest-v1-spec.md`
- `docs/superpowers/specs/2026-06-15-review-roundtrip-v1-spec.md`
- `docs/superpowers/specs/2026-06-15-sample-metadata-contract-v1-spec.md`
- `scripts/validate_review_actions.py`
- `scripts/plan_review_action_applications.py`
- `scripts/validate_review_action_expected_diffs.py`
- `scripts/plan_review_action_apply_readiness.py`
- `scripts/plan_review_action_apply_changesets.py`
- `scripts/apply_review_action_changesets.py`
- `scripts/validate_sample_metadata.py`
- `tests/test_method_manifest.py`
- `tests/test_review_actions.py`
- `tests/test_sample_metadata.py`
- `xic_extractor/output/method_manifest.py`
- `xic_extractor/review_actions.py`
- `xic_extractor/sample_metadata.py`

## Commit 拆分計畫

這輪不要用 `git add .`。目前依目的拆成五包:

1. `305b97e feat: add targeted replay manifest`
   - 包含 manifest module、`--replay-manifest`、schema metadata、workbook compare、相關 tests/spec/validation note。
2. `6915e48 feat: add review action roundtrip gates`
   - 包含 action import、application plan、expected-diff approval、apply-readiness、changeset dry-run CLI/module/tests/spec。
3. `865bad3 feat: add sample metadata contract`
   - 包含 sample metadata module、validator CLI、tests/spec。
4. `386a5fd docs: clarify alignment output levels`
   - 包含 alignment output contract doc 和對應 test wording。
5. Agent handoff/hook operating-system docs。
   - 包含 `.codex/hooks/*`、handoff README/current handoff、Codex operating-system doc、productization control plane。
   - 這包會包含本 handoff 更新；實際 hash 請看 `git log --oneline -8`。

排除:

- `docs/superpowers/specs/2026-06-13-backfill-integration-policy-spec.md`
  不是本輪新增，不要誤 stage。

## 權威順序

如果文件之間衝突，不要用檔案修改時間決定誰對。照這個順序停下來同步:

1. `git status` / `git diff` 決定目前工作樹實況。
2. `docs/superpowers/plans/2026-06-15-productization-control-plane.md` 決定 maturity tier、active lane、WIP owner、promotion gate。
3. named specs/plans 決定 schema、CLI/config/output 行為契約。
4. validation notes 決定 RAW/benchmark evidence。
5. 這份 handoff 只做白話摘要、接手順序、下一步建議。

## 最近在做什麼

- `NL_FAIL` analyte MS1 rescue 已從 `TumorBC2294_DNA / 5-hmdC` debug case
  收斂到 limited headless product path：現在 no-flag CLI default 只在
  `5-hmdC + 5-medC` / `detected_flagged` 範圍內自動跑 support/gate。
- 共享 own-max evidence 目前仍是 `diagnostic_only`；product projection 端已先 fail-closed。意思是 own-max normalized same-peak similarity 必須和 paired ISTD / area-ratio / boundary policy 一起過，才有資格補進產品矩陣。5-case own-max diagnostic 只證明這五個 NL_FAIL analyte traces 彼此像同一組峰，還不等於 accepted analyte anchor authority。
- 2026-06-16 已把 owner framing 釘成 shared target/untarget peak identity spine: shared 層只產生峰身份 evidence，targeted/untargeted 各自決定產品輸出；不要把 untargeted backfill authority 原封不動搬成 targeted counted detection。
- 同日已補第一個 shared helper + no-RAW tests，讓一個既有 overlay diagnostic 使用 shared smoothing helper，並新增 targeted diagnostic adapter 輸出 same-peak evidence rows；接著把 product projection 改成 fail-closed，需要 `own_max_same_peak_support` 才能讓 area-ratio/paired-RT 解除 `NL_FAIL` not-counted policy。後續已新增 explicit support-TSV、headless auto-limited CLI、以及 canonical no-flag normal CLI default；全部仍只限 `5-hmdC + 5-medC` / `detected_flagged`。
- 8RAW 和 85RAW explicit opt-in smoke 都已跑過，不是只停在 unit test。第一輪 85RAW 5-row 手動 support TSV 只改到 5 個 reviewed rows；後續 generic RAW-backed producer 產出 11 個 support rows，85RAW opt-in 也剛好改到 11 rows。這原本支持 explicit opt-in workflow 進 `production_candidate`；2026-06-17 補上 support TSV key-set gate 後，headless explicit limited support-TSV workflow 已可標 `production_ready`。後續本輪又把 explicit auto CLI 和 canonical no-flag headless CLI default 推到 `production_ready`；GUI 仍未 production-ready。
- 這個分支正在補 XIC 的產品化地板，不是在重寫 peak picking 演算法。
- 最近完成的主軸是 replay executor: `method_manifest.json` + `--replay-manifest`，已跑過 8RAW 和一次 85RAW replay parity。
- 接著補了三個中期 contract: targeted output schema version、ReviewAction import/application plan/expected-diff/apply-readiness/changeset gate、SampleMetadata schema。
- 2026-06-16 進一步把 ReviewAction changeset 接到 audited output copy，把 `sample_metadata_v1` 接成 extraction `injection_order_source` parity input，並在 manifest 寫清楚 artifact replay policy。
- 本輪再把 `sample_metadata_v1` 投射到 instrument-QC method-doc sidecar、alignment sample-column ordering、RT-normalization anchor diagnostic injection-order lookup，並把 standard-path backfill seed guard 接進 productization bridge。這些都沒有啟用 sample-role matrix behavior、non-standard peak promotion、GUI rescue、或 broader targeted `NL_FAIL` rescue。
- Alignment 這邊沒有重寫 runtime，只是把文件和 test name 改到符合現況: `alignment_matrix.tsv` 是 machine/validation，不是 production default。
- 目前還不能誤會成完成的是 GUI replay、selected-candidate switch、manual-boundary area recompute、workbook rewrite、primary matrix rewrite、sample role 影響 quant output、GUI/broader targeted `NL_FAIL` rescue、或 broad non-standard peak promotion。
- 下一個最安全的實作點不是 ReviewAction selected/manual writer；那條已 parked。下一個 agent 應先補 Backfill heldout oracle 的 independent observed boundary/area source，或先定義 boundary-observation contract；sample metadata resolver parity 的 no-output slices 已接到 RT-normalization anchor diagnostic，後續 role-aware 行為必須先有 expected-diff gate。

## 先講人話

這輪不是在做新演算法，而是在補「成熟工具該有的產品化地板」:

- 跑完一次後，要能知道當時用了什麼設定、什麼 targets、什麼 runtime，並能照 manifest 重跑。
- 輸出要有 schema version，不然下游不知道自己吃的是哪一版欄位語意。
- 人工 review 不能永遠只停在 Excel worklist，至少要先有正式的 review action import schema 和 dry-run apply plan。
- 人工 review 現在已經能從 changeset 寫成 audited targeted-long copy 和 `review_action_apply_audit_v1`，但還不會重算 area 或切 candidate。
- sample metadata 不能每個模組各自猜 QC、blank、batch、matrix；目前 extraction、alignment、RT-normalization anchor diagnostic 已能用 `sample_metadata_v1` 產生既有 injection-order 行為，instrument-QC method-doc workflow 也會輸出 `sample_metadata_v1` sidecar，但 role 還不能改矩陣或 normalized values。
- alignment 的 production / machine output wording 要跟 runtime 一致，不然會一直誤會 `alignment_matrix.tsv` 是 production default。

目前狀態: replay executor 已經真正跑過 8RAW 和一次 85RAW；ReviewAction 已能安全寫 audited copy；sample metadata 已能接 extraction injection order、instrument-QC metadata sidecar、alignment sample-column ordering、RT-normalization anchor diagnostic injection-order lookup；standard-path backfill seed guard 已是 `production_candidate` 且 heldout oracle result gate 可執行；Targeted MS1 headless no-flag limited default 已可用於 `5-hmdC + 5-medC` / `detected_flagged`；仍沒有改 peak area、selected candidate、workbook、GUI rescue、broader target rescue、normalized value 寫回、或 broad primary matrix semantics。

## 這輪已經做了什麼

### 1. `method_manifest_v1` / replay executor

已做:

- 每次 targeted extraction 會寫 `output/method_manifest.json`。
- Manifest 會記錄設定檔、targets、RAW/DLL path、optional artifacts、runtime、parallel backend、CLI argv、output artifacts。
- 新增 `xic-extractor-cli --replay-manifest <path>`。
- Replay mode 會拒絕覆蓋 runtime 的 CLI flags，例如 `--skip-excel`、`--parallel-workers`。
- Replay loader 會確認 manifest 驗證的 `settings.csv` / `targets.csv` 就是 `invocation.config_dir` 下面實際要執行的檔案；不能驗證 A config、執行 B config。
- Workbook `Run Metadata` 會反查 manifest schema/path/hash。
- `scripts.compare_workbooks` 已忽略 manifest path/hash 這種 replay 時會自然不同的 metadata，但仍比較 manifest schema。
- Manifest 現在有 `artifact_replay_policy`: CSV 是 byte-exact replay artifact，timestamped workbook 走 normalized compare，manifest 本身是 provenance-only。

已驗證:

- 8RAW CSV-only replay: `xic_results.csv`、`xic_results_long.csv`、`xic_diagnostics.csv` byte parity。
- 8RAW Excel-mode replay: workbook compare passed。
- 85RAW initial + replay: 85 RAW、1715 diagnostics，CSV byte parity + workbook compare passed。

白話結論:

可以說「targeted CLI replay parity 已經做到，而且 artifact policy 已寫清楚」。不能說「GUI replay 已完成」或「timestamped workbook byte-exact replay 已完成」。

還沒做:

- GUI replay 尚未接回主線。
- Timestamped workbook 目前刻意走 normalized compare，不是 byte-exact workbook hash replay。

### 2. Targeted output schema versioning

已做:

- 新增 targeted output schema version constants:
  - `targeted_output_v1`
  - `targeted_long_csv_v1`
  - `targeted_diagnostics_csv_v1`
  - `targeted_score_breakdown_csv_v1`
- Manifest 新增 `output_schema` block，列出 long CSV / diagnostics CSV / score breakdown CSV 的版本和 headers。
- Workbook `Run Metadata` 新增 `targeted_output_schema_version`。

白話結論:

下游現在可以從 manifest 或 workbook metadata 知道這份 targeted output 是哪一版 schema。這次沒有把 schema version 加進每一列 CSV，避免破壞既有 downstream。

還沒做:

- 還沒有 downstream export profile。
- CSV row-level schema 欄位沒有新增，這是刻意的。

### 3. `review_action_v1` / application plan / expected-diff / apply-readiness / changeset

已做:

- 新增 `xic_extractor.review_actions`。
- 新增 `scripts/validate_review_actions.py`。
- 新增 `scripts/plan_review_action_applications.py`。
- 新增 `scripts/plan_review_action_apply_readiness.py`。
- 新增 `scripts/plan_review_action_apply_changesets.py`。
- 定義 review action import TSV/CSV schema。
- 定義 `review_action_application_plan_v1` dry-run TSV。
- 定義 `review_action_expected_diff_v1` template TSV。
- 定義 `review_action_apply_readiness_v1` dry-run TSV。
- 定義 `review_action_apply_changeset_v1` dry-run TSV。
- `scripts/plan_review_action_applications.py` 可用 `--expected-diff-template-tsv` 輸出被擋住的 product-mutating action 審核模板。
- 新增 `scripts/validate_review_action_expected_diffs.py`，讓 reviewer 改完 expected-diff TSV 後可以先驗證它是不是真的能授權後續 apply。
- 新增 expected-diff approval loader，只接受 `approved + expected_diff + 已驗證 + evidence 完整 + stable id 對得上` 的 row。
- expected-diff approval 會記住核准時 targeted row 的 `Product State`、`Counted Detection`、`Review State`。
- `scripts/plan_review_action_apply_readiness.py` 會把 approved expected-diff row 對回 ReviewAction，輸出哪些 action 已經 ready、哪些仍 blocked。
- Product-mutating action 要 ready 時，current targeted row 也必須有 `Product State`、`Counted Detection`、`Review State`；空 baseline 不算 approval。
- 如果 current targeted row 缺少 baseline state，會變成 `blocked_expected_diff_baseline_missing`；如果已經和 approved baseline 不同，會變成 `blocked_expected_diff_baseline_mismatch`，不能偷用舊 approval。
- apply-readiness CLI 預設會拒絕 unused approval row，避免舊核准檔被靜默混進新 action set。
- `scripts/plan_review_action_apply_changesets.py` 會把 ready rows 轉成 operation 和 output scope，例如 `select_candidate`、`set_manual_boundary`、`reject_current`。
- 新增 `scripts/apply_review_action_changesets.py`，可以讀 changeset TSV 和 targeted long CSV，輸出 audited targeted-long copy 和 `review_action_apply_audit_v1` TSV。
- `mark_unresolved` 現在可把 audited copy 的 `Review State` 改成 `unresolved_by_review`。
- `reject_current` 在 approved expected-diff 後可把 audited copy 的 `Product State` / `Counted Detection` / `Review State` 改成 reject 狀態。
- `select_candidate` 和 `set_manual_boundary` 仍只會寫 deferred audit，因為還缺 candidate sidecar writer 或 area recompute writer。
- 支援 action:
  - `accept_current`
  - `mark_unresolved`
  - `reject_current`
  - `select_candidate`
  - `set_manual_boundary`
- 會擋掉危險 action，例如:
  - `select_candidate` 沒有 `candidate_id`
  - `set_manual_boundary` 沒有完整 RT 邊界
  - mutating action 沒有 `expected_diff_required=TRUE`
- application plan 會把 action 對到目前 targeted long output 的 `SampleName` / `Target`，並把 product-mutating action 標成 `blocked_expected_diff_review`。

白話結論:

現在有正式「人工 review action 檔案長什麼樣」的入口，也能產生 apply-readiness/changeset，並把 changeset 寫成 audited targeted-long copy 和 audit TSV。這已經不是純 dry-run，但仍不是完整 reintegration: selected candidate switch 和 manual boundary area recompute 還沒做。

還沒做:

- 還不能因人工 boundary 重算 area。
- 還不能切換 selected candidate。
- 還不能直接覆蓋原 extraction output、workbook、或 primary matrix。

### 4. `sample_metadata_v1`

已做:

- 新增 `xic_extractor.sample_metadata`。
- 新增 `scripts/validate_sample_metadata.py`。
- 定義 sample metadata TSV/CSV schema:
  - sample name
  - raw stem
  - injection order
  - sample role
  - batch / prep batch
  - matrix type
  - group
  - excluded / exclusion reason
- 支援 sample roles:
  - `study_sample`
  - `qc`
  - `pooled_qc`
  - `blank`
  - `calibrator`
  - `solvent`
  - `system_suitability`
  - `unknown`
- 可把 sample metadata 投影成 injection-order mapping。
- `sample_name` 和 `raw_stem` 共用同一個 injection-order alias namespace；跨列撞名會在 parse 階段被拒絕。
- Extraction 的 `injection_order_source` 現在可以指向 `sample_metadata_v1` CSV/TSV；legacy `Sample_Name,Injection_Order` 仍走舊 parser。

白話結論:

現在有共同 sample metadata 語言了，而且 extraction 已經能用它產生既有 injection-order 行為。QC、blank、batch、matrix 欄位目前只是 contract，還不能改 quant output。

後續已補:

- Instrument-QC method-doc workflow 現在會額外輸出
  `instrument_qc_sample_metadata.tsv`，但只做 metadata sidecar。
- Alignment `--sample-column-injection-order` 現在可 consume
  `sample_metadata_v1` 來排序 sample columns，但只做 order projection。
- RT-normalization anchor diagnostic `--sample-info` 現在可 consume
  `sample_metadata_v1` 來投影 injection order，但只做 reference lookup。
- Sample role 還不能拿來改 matrix value、normalized value 或排除 row。

### 5. Alignment output contract

已做:

- 對齊 `docs/superpowers/specs/2026-05-11-untargeted-alignment-output-contract.md` 和 runtime。
- 明確寫清楚:
  - `alignment_results.xlsx` 是 production workbook。
  - `review_report.html` 是 user/developer review surface。
  - `alignment_matrix_identity.tsv` 是 production-level identity handoff。
  - `alignment_matrix.tsv` 是 machine/validation artifact，不是 production default。
- 修改一個 test name，讓名字不要再暗示 production 只有 xlsx/html。

白話結論:

這一項主要是「把話講正確」，不是新功能。Runtime 本來就已經分 production/machine/debug/validation levels。

還沒做:

- 這不代表 untargeted science readiness 全部完成。
- Release gate 仍要守住 production/machine/debug/validation artifact separation。

## 還沒做的大事

這些不要誤會成已完成:

- GUI replay 沒接主線。
- Timestamped workbook byte-exact replay 沒做；目前是 normalized workbook compare policy。
- Review roundtrip 還沒做 selected candidate switch 或 manual boundary area recompute。
- Sample metadata roles 還不能改 extraction/QC/alignment/normalization 或 matrix values。
- Canonical detection contract 還沒正式寫完。
- Manual boundary recompute 還沒寫。
- Calibration/normalization 還不能寫回 main matrix。
- Backfill product-authority sidecars 仍不能直接改 primary matrix。
- 本輪變更應拆成目的 commits；接手時用 `git log --oneline -10` 確認實際 commit hash。

## 驗證狀態

已跑:

```powershell
python -m pytest tests\test_method_manifest.py tests\test_run_extraction.py tests\test_output_schema_contract.py tests\test_output_metadata.py tests\test_excel_pipeline.py tests\test_excel_sheets_contract.py tests\test_csv_to_excel.py tests\test_workbook_compare.py tests\test_extractor.py tests\test_extractor_run.py tests\test_parallel_execution.py tests\test_review_actions.py tests\test_sample_metadata.py tests\test_alignment_output_levels.py tests\test_alignment_pipeline_outputs.py::test_run_alignment_production_level_writes_user_artifacts_and_identity_tsv tests\test_alignment_pipeline_outputs.py::test_run_alignment_default_stays_machine_until_owner_validation_acceptance tests\test_run_alignment.py::test_run_alignment_cli_accepts_output_level_debug tests\test_run_alignment.py::test_run_alignment_cli_accepts_validation_minimal_output_level -q
```

結果: `174 passed`

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor scripts\run_extraction.py scripts\compare_workbooks.py scripts\validate_review_actions.py scripts\validate_sample_metadata.py tests\test_method_manifest.py tests\test_run_extraction.py tests\test_output_schema_contract.py tests\test_output_metadata.py tests\test_workbook_compare.py tests\test_review_actions.py tests\test_sample_metadata.py tests\test_alignment_pipeline_outputs.py
```

結果: pass

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor scripts\run_extraction.py scripts\compare_workbooks.py scripts\validate_review_actions.py scripts\validate_sample_metadata.py
```

結果: pass, `339 source files`

```powershell
git diff --check
```

結果: 沒有 whitespace error，只有 CRLF warning。

注意: 以上是 replay/schema/review/sample metadata/alignment 的 focused validation；完整 local PR closeout gate 見本節後面的 2026-06-16 紀錄。

回到主線後另跑:

```powershell
python -m pytest tests\test_review_actions.py -q
```

結果: `22 passed`

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor\review_actions.py scripts\validate_review_actions.py scripts\plan_review_action_applications.py scripts\validate_review_action_expected_diffs.py scripts\plan_review_action_apply_readiness.py scripts\plan_review_action_apply_changesets.py tests\test_review_actions.py
```

結果: pass

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor\review_actions.py scripts\validate_review_actions.py scripts\plan_review_action_applications.py scripts\validate_review_action_expected_diffs.py scripts\plan_review_action_apply_readiness.py scripts\plan_review_action_apply_changesets.py
```

結果: pass

```powershell
python .codex\hooks\fixtures\assert_hook_outputs.py
```

結果: pass

Subagent review follow-up 另跑:

```powershell
python -m pytest tests\test_method_manifest.py tests\test_review_actions.py tests\test_sample_metadata.py -q
```

結果: `40 passed`

```powershell
python -m pytest tests\test_method_manifest.py tests\test_run_extraction.py tests\test_review_actions.py tests\test_sample_metadata.py -q
```

結果: `62 passed`

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor\output\method_manifest.py xic_extractor\review_actions.py xic_extractor\sample_metadata.py .codex\hooks\xic_post_tool_guard.py tests\test_method_manifest.py tests\test_review_actions.py tests\test_sample_metadata.py
```

結果: pass

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor\output\method_manifest.py xic_extractor\review_actions.py xic_extractor\sample_metadata.py
```

結果: pass

```powershell
python .codex\hooks\fixtures\assert_hook_outputs.py
```

結果: pass

Local PR closeout gate 另跑（2026-06-16）:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor tests
```

結果: pass, `All checks passed!`

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor
```

結果: pass, `Success: no issues found in 335 source files`。只剩 `annotation-unchecked` notes，沒有 type error。

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -v --tb=short -x
```

結果: `3611 passed, 1 skipped in 67.41s (0:01:07)`

```powershell
python .codex\hooks\fixtures\assert_hook_outputs.py
```

結果: pass

本輪 goal 中途另跑（2026-06-16）:

```powershell
python -m pytest tests\test_review_actions.py -q
```

結果: `27 passed`

```powershell
python -m pytest tests\test_sample_metadata.py tests\test_injection_rolling.py tests\test_extractor_run.py -q
```

結果: `33 passed`

```powershell
python -m pytest tests\test_method_manifest.py tests\test_workbook_compare.py -q
```

結果: `18 passed`

本輪 goal 最終 gate 另跑（2026-06-16）:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor tests
```

結果: pass, `All checks passed!`

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor
```

結果: pass, `Success: no issues found in 340 source files`。只剩既有 `annotation-unchecked` notes，沒有 type error。

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -v --tb=short -x
```

結果: `3657 passed, 1 skipped in 55.03s`

```powershell
python .codex\hooks\fixtures\assert_hook_outputs.py
```

結果: pass

```powershell
git diff --check
```

結果: 沒有 whitespace error，只有 LF/CRLF warning。

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/check_diagnostics_index.py
```

結果: pass, `INDEX.md in sync: 84 entry points, 163 total files.`

2026-06-17 繼續推進後最新 gate:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor tests tools scripts
```

結果: pass, `All checks passed!`

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor
```

結果: pass, `Success: no issues found in 342 source files`。只剩既有 `annotation-unchecked` notes，沒有 type error。

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -v --tb=short -x
```

結果: `3698 passed, 1 skipped in 64.04s`

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts\check_diagnostics_index.py
```

結果: pass, `INDEX.md in sync: 86 entry points, 165 total files.`

```powershell
git diff --check
```

結果: 沒有 whitespace error，只有 LF/CRLF warning。

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run python -m tools.diagnostics.standard_peak_backfill_productization --shadow-projection-cells-tsv output\standard_peak_backfill_preset_85raw_20260610\alignment_preset_dna_dr_85raw_validation_minimal\standard_peak_backfill_preset\chunks\r1_120\shadow_projection\shadow_production_projection_cells.tsv --alignment-matrix-tsv output\standard_peak_backfill_preset_85raw_20260610\alignment_preset_dna_dr_85raw_validation_minimal\alignment_matrix.pre_standard_peak_backfill.tsv --alignment-matrix-identity-tsv output\standard_peak_backfill_preset_85raw_20260610\alignment_preset_dna_dr_85raw_validation_minimal\alignment_matrix_identity.pre_standard_peak_backfill.tsv --alignment-review-tsv output\standard_peak_backfill_preset_85raw_20260610\alignment_preset_dna_dr_85raw_validation_minimal\alignment_review.tsv --output-dir output\productization_realdata_seed_guard_85raw_20260617\r1_120_no_raw_productization --source-run-id seed-guard-realdata-85raw-r1-120-20260617
```

結果: pass。輸出 `standard_peak_backfill_productization_summary.json`、
`standard_peak_activation_inputs/seed_guard_decisions.tsv`、
`activated_matrix/activation_value_delta.tsv`。2540 candidates 中 1160 eligible
writes、1380 low-seed no-writes；`activation_value_delta.tsv` 1160 rows。
Peirce review hardening 後已重跑，仍是 `status=pass`，且
`blocked_unattributed_write=0`。

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run python -m tools.diagnostics.standard_peak_backfill_productization --shadow-projection-cells-tsv output\standard_peak_backfill_preset_85raw_20260610\alignment_preset_dna_dr_85raw_validation_minimal\standard_peak_backfill_preset\consolidated\consolidated_shadow_projection_cells.tsv --alignment-matrix-tsv output\standard_peak_backfill_preset_85raw_20260610\alignment_preset_dna_dr_85raw_validation_minimal\alignment_matrix.pre_standard_peak_backfill.tsv --alignment-matrix-identity-tsv output\standard_peak_backfill_preset_85raw_20260610\alignment_preset_dna_dr_85raw_validation_minimal\alignment_matrix_identity.pre_standard_peak_backfill.tsv --alignment-review-tsv output\standard_peak_backfill_preset_85raw_20260610\alignment_preset_dna_dr_85raw_validation_minimal\alignment_review.tsv --output-dir output\productization_realdata_seed_guard_85raw_20260617\consolidated_no_raw_productization --source-run-id seed-guard-realdata-85raw-consolidated-20260617
```

結果: pass，約 6.93 秒。輸出同樣是
`standard_peak_backfill_productization_summary.json`、
`standard_peak_activation_inputs/seed_guard_decisions.tsv`、
`activated_matrix/activation_value_delta.tsv`。7307 candidates 中 4613 eligible
writes、2694 low-seed no-writes；`activation_value_delta.tsv` 4613 rows；
`blocked_unattributed_write=0`。這沒有開 RAW，也不取代 reviewed oracle。

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests\test_standard_peak_shadow_activation_inputs.py tests\test_standard_peak_backfill_productization.py -q
```

結果: `42 passed`。包含 Peirce/Euclid/Noether review 後新增的五個
fail-closed cases: CLI full manifest schema enforcement、package evaluator
manifest required-column enforcement、manifest schema-version enforcement、
duplicate/extra observed oracle rows、以及 `blocked_unattributed_write`
productization failure；另含使用者接受 tolerance 後新增的
loose-tolerance rejection、strict-tolerance acceptance、以及 Linnaeus review
後新增的 exact-boundary / exact-area tolerance tests；也包含 Gibbs review
後新增的 observed provenance source-copy variants 與 missing
`result_source_artifact` fail-closed tests；以及 current matched reviewed rows
其實是 `rescued` cell 後新增的 `heldout_original_cell_status` required-column
與 `rescued` fail-closed tests；另含 Ptolemy review 後新增的 neutral
`oracle_source` self-copy cross-check、original-cell-status allowlist、blank、
unknown status tests。

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools\diagnostics\standard_peak_heldout_oracle_results.py xic_extractor\diagnostics\standard_peak_shadow_activation_inputs.py xic_extractor\diagnostics\standard_peak_backfill_productization.py tests\test_standard_peak_shadow_activation_inputs.py tests\test_standard_peak_backfill_productization.py
```

結果: pass, `All checks passed!`

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor\diagnostics\standard_peak_shadow_activation_inputs.py xic_extractor\diagnostics\standard_peak_backfill_productization.py tools\diagnostics\standard_peak_heldout_oracle_results.py
```

結果: pass, `Success: no issues found in 3 source files`。

RAW-backed 驗證:

- 8RAW 已跑。
- 85RAW 已集中跑一次。
- Backfill 2026-06-17 沒有重跑 RAW；只用既有 85RAW artifact 做 no-RAW
  productization bridge。
- Targeted MS1 auto-limited CLI 2026-06-17 已為新的 readiness decision 跑過
  一次 8RAW 和一次 foreground 85RAW；85RAW 結果是 11 support rows、11 long
  rows、66 matrix cells、wall-clock `369.2 s`。
- 不要在沒有新 production-readiness decision 的情況下再跑一次 85RAW。

詳細 RAW 證據在:

- `docs/superpowers/notes/2026-06-15-replay-executor-validation-note.md`

## 下一個 agent/session 應該先看

1. `docs/superpowers/plans/2026-06-15-productization-control-plane.md`
2. `docs/superpowers/specs/2026-06-15-review-roundtrip-v1-spec.md`
3. `docs/superpowers/notes/2026-06-15-replay-executor-validation-note.md`
4. `docs/superpowers/specs/2026-06-15-method-manifest-v1-spec.md`
5. `docs/superpowers/specs/2026-06-15-sample-metadata-contract-v1-spec.md`
6. `docs/superpowers/specs/2026-05-11-untargeted-alignment-output-contract.md`

## 下一步建議

優先順序:

1. 若要進 PR/merge，下一步是處理 remote/PR 層級。
   - PR #85 已存在：`https://github.com/Chao-hu-Lab/XIC_Extractor/pull/85`，
     base 是 `master`，head 是 `cc/framework-improvements`。
   - Remote CI 對 pushed head `3b10731745865731482a9da62cd49e951f7dcc65`
     曾是綠的：lint、typecheck、Python 3.11 tests、Python 3.12 tests 都
     success；但本機現在已超前，PR CI 需要在 push 後重看。
   - Local `HEAD` 是 `55f9e4b8`，branch 目前 ahead 20，且這輪 generated
     Backfill policy path 還是 dirty diff。另有
     `docs/agent-subagent-routing.md` dirty diff 是前一輪/其他 agent 留下的
     workflow-rule 變更，commit 時不要不小心混入除非刻意收它。

2. 若繼續推 productization，第一順位是 Backfill broad-scope evidence，而不是再做已完成 scoped writer。
   - 目前 explicit 72-row high-signal-clean scoped writer 是 `production_ready`。
   - 目前 explicit 42-row low-scan-clean scoped writer 也是 `production_ready`。
   - 目前 explicit 57-row low-height-clean scoped writer 也是 `production_ready`。
   - 目前 explicit 69-row low-height-low-scan-clean scoped writer 也是 `production_ready`。
   - 目前 explicit 220-row low-height reintegration-stable scoped writer 也是
     `production_ready`；它新增 199 個不在前四個 writer scope 的 ready
     cells，五個 ready scope 聯集為 439 cells。
   - 這輪新增 generated Backfill policy path：
     `--backfill-policy-source-audit-tsv` 會對完整 source audit 產出
     `standard_peak_backfill_policy.tsv`，每列自動分成 `write_ready`、
     `detected_flagged`、或 `blocked`；writer 只寫 generated `write_ready`。
     這是後續 broadening 的共同入口，不是人工 TSV 白名單。真實 no-RAW
     85RAW replay 已證明 current approved evidence classes 可用這條路徑一次
     寫出 439 格且 expected-diff 439/439 pass；但這仍不是 broad 4613-row
     ready 宣稱。
   - broad 4613-row standard-path seed guard 仍是 `production_candidate`。
   - 新增 boundary-stability / reintegration-agreement diagnostic 後，broad
     scope 有 299 個 written rows 通過 dual-reintegration stability gate，其中
     271 個不在既有四個 ready scoped writer 內；這只是下一個 candidate pool，
     不是 writer-ready。Subagent review 已要求它 fail closed；summary 現在寫
     `status=candidate_pool_blocked` 與 `writer_authority_status=blocked`。
   - High-signal clean 20-case heldout oracle 已通過；low-scan clean 11-case
     heldout oracle 也已通過；low-height bounded-window 20-case oracle 已用
     `padding=0.5 min` 通過；low-height-low-scan bounded-window 20-case oracle
     也已通過。combined activation scope audit 已證明目前
     broad 4613 writes 中有 72 個 high-signal clean、42 個 low-scan clean、
     57 個 low-height clean、69 個 low-height-low-scan clean。
   - 299-row stability candidate pool 不能直接接 writer。快速 all-family
     check 已看到 `FAM000949/NormalBC2261_DNA` area fail；可寫的是
     low-height + stability 的 220-row 子集合，因為它有 per-row
     reintegration-stability audit、family-level detected-trace oracle
     20/20 pass、以及 writer expected-diff 220/220 pass。
   - 若要承認 broad 4613-row writes，才需要 broader masked/product-writer
     observed oracle 和 full-scope expected-diff gate。若要穩步推進，下一刀
     不應重做已完成的 high-signal/low-scan/low-height/low-height-low-scan scoped
     writers，也不應重做這次已完成的 low-height reintegration-stable writer。
     apex-delta、width-only、shape-margin 仍要先解 oracle failures。下一個
     Backfill gate 應把這 299-row pool 送進 masked/product-writer oracle，或再
     補 local S/N / selectivity、cohort-anchored expected window，並把通過的
     evidence class 接進 generated policy engine；同時用預先宣告的 strata +
     lockbox 防止 cherry-picking。
   - 新 broadening 不能只靠再加一層資料集形容詞來宣稱 ready。它必須說明
     自己驗證的 broader evidence class、如何讓 policy engine 自動分類整個
     source audit、如何推進 broad 4613-row decision，以及通過哪個
     heldout/masked/product-writer oracle 和 expected-diff。
   - 非標準 peak automatic promotion 仍不可啟用。

3. 第二順位原本是 sample metadata cross-module parity；no-output resolver slices 已收斂。
   - Extraction injection-order parity 已接好。
   - Instrument-QC method-doc 已輸出 additive `instrument_qc_sample_metadata.tsv` sidecar。
   - Alignment sample-column ordering 已可 consume `sample_metadata_v1`。
   - RT-normalization anchor diagnostic `--sample-info` 已可 consume `sample_metadata_v1`。
   - 不要讓 QC/blank/batch role 直接改 quant output、normalized values 或 matrix values。

4. ReviewAction selected-candidate switch 和 manual-boundary area recompute 已 parked。
   - 現在 audited apply copy 已能消費 changeset rows。
   - `select_candidate` 和 `set_manual_boundary` 仍是 deferred，不能假裝已回寫 selected peak/area。
   - 任何會改 selected peak/area/counting 的下一刀仍要 expected-diff 和人類產品決策。

5. GUI replay 等 GUI 接主線後再做。
   - 現在不要為了 GUI replay 去改未接主線的 GUI 測試。

## 每次收尾要更新這份文件

請用白話更新，不要只丟檔名:

- 今天真正變成可用的是什麼？
- 哪些只是 schema/validator/diagnostic，不是產品行為？
- 哪些測試或 RAW fixture 跑過？
- 哪些大事還沒做？
- 下一個 agent 第一件事應該做什麼？

如果這份文件和 control plane 衝突，control plane 的 tier/active-lane 判斷優先；這份文件要改成摘要 control plane，而不是覆蓋它。若衝突牽涉到 schema 或 RAW evidence，回到 named spec 或 validation note 查證後再同步。
