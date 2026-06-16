# XIC productization handoff

更新日期: 2026-06-16
分支: `cc/framework-improvements`
用途: 給下一個 agent/session 快速接手，不需要重讀整段聊天。

## 目前可接手狀態

- Branch: `cc/framework-improvements`。
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
- 最新 no-RAW 驗證: focused productization tests `61 passed`，broader related suite `263 passed`，`uv run ruff check xic_extractor tests tools scripts` passed，`uv run mypy xic_extractor` passed，`python -m scripts.check_diagnostics_index` passed，`git diff --check` 只有 CRLF warnings、無 whitespace error。8RAW 和 85RAW explicit opt-in smoke 都已跑。
- 8RAW explicit opt-in smoke artifact: `output/ms1_shape_identity_optin_8raw_20260616/expected_diff_summary.tsv`。baseline/opt-in 都用 validation 8RAW、CSV-only；只改到 `TumorBC2263_DNA / 5-hmdC` 一列，從 `not_counted / FALSE / RT=ND / Area=ND` 變 `detected_flagged / TRUE / RT=9.1705 / Area=145695.76`，support 多了 `own_max_same_peak_support`，`analyte_nl_fail_requires_policy` 被移除。
- 第一輪 85RAW manual-support opt-in smoke artifact: `output/ms1_shape_identity_optin_85raw_20260616/expected_diff_summary.tsv` 和 `matrix_diff_summary.tsv`。baseline/opt-in 都用 full tissue 85RAW、CSV-only；只改到 reviewed support TSV 的 5 個 `5-hmdC` rows，全部從 `not_counted / FALSE` 變 `detected_flagged / TRUE`。unexpected changed rows = 0，support_not_changed = 0，wide matrix 只改 30 個 5-hmdC value cells。
- 使用者指出「不應該只有 5 rows」。這個判斷是對的：5-row 是因為上游 support TSV 只餵了手動 review 的 5 cases，不是 product gate 只能吃 5 rows。
- 已新增 generic RAW-backed support producer: `tools/diagnostics/build_targeted_ms1_shape_identity_supports.py`，核心 helper 在 `xic_extractor/diagnostics/targeted_ms1_shape_identity_support_builder.py`，測試在 `tests/test_targeted_ms1_shape_identity_support_builder.py` 和 `tests/test_build_targeted_ms1_shape_identity_supports.py`。它會從 baseline `xic_results_long.csv` 自動挑出 analyte `NL_FAIL/NO_MS2`、已被 `analyte_nl_fail_requires_policy` 擋住、且已有 `paired_area_ratio_support` 的 rows，再用 Gaussian-smoothed local own-max same-peak gate 產 support TSV。
- Generic producer 85RAW artifact: `output/ms1_shape_identity_generic_support_85raw_20260616/targeted_ms1_shape_identity_v0.tsv`。它找到 11 個候選 support rows：10 個 `5-hmdC` 加 1 個 `5-medC`，全部 `own_max_same_peak_supported=TRUE`。
- 2026-06-16 修後重跑 generic producer：仍是 11 candidate rows / 11 evidence rows / 13 trace requests。support TSV keys 跟既有 generic 85RAW `expected_diff_summary.tsv` 的 11 個 changed rows 完全一致；baseline state 全部 `not_counted / FALSE`，opt-in state 全部 `detected_flagged / TRUE`。這次沒有重跑 85RAW extraction。
- 已用 generic TSV 跑一次 85RAW opt-in（沒有重跑 baseline，baseline 沿用 `output/ms1_shape_identity_optin_85raw_20260616/baseline`）：`output/ms1_shape_identity_generic_support_85raw_20260616/optin/output/xic_results_long.csv`。diff summary 在 `output/ms1_shape_identity_generic_support_85raw_20260616/expected_diff_summary.tsv` 和 `matrix_diff_summary.tsv`。
- Generic 85RAW opt-in 結果：剛好 11 rows 從 `not_counted / FALSE` 變 `detected_flagged / TRUE`，wide matrix 66 cells changed，`xic_diagnostics.csv` SHA256 與 baseline 完全相同。新增 rows 包含 `BenignfatBC0980_DNA / 5-hmdC`、`NormalBC2259_DNA / 5-hmdC`、`NormalBC2270_DNA / 5-hmdC`、`NormalBC2272_DNA / 5-hmdC`、`NormalBC2294_DNA / 5-hmdC`、`NormalBC2264_DNA / 5-medC`，所以不再只限原本 5 rows。
- 給使用者 review 的整理包: `docs/superpowers/reports/2026-06-16-5hmdc-own-max-optin-review.md`。先看這份，不要直接從一堆 output CSV 開始翻。
- 使用者已接受「backfill/rescue 只能算 `detected_flagged`，不能算乾淨 `detected`」，並授權跑 85RAW。五列手動 TSV smoke 和 11-row generic TSV smoke 都已跑完；下一個安全點是決定是否接受 generic producer 的候選篩選政策並把 explicit opt-in workflow 標成 `production_candidate`。還不能說整體 GUI/default product path production-ready。
- Current debug note: `output/debug_tumorbc2294_5hmdc_current_code_20260616_110408/root_cause_note.md`。
- 剛剛的 subagent 驗收不是直接 pass: reviewer 擋下 hook fixture 可信度、manifest replay config 綁定、expected-diff stale approval、sample metadata alias collision。這些已在 follow-up 修正並用 focused tests/hook fixture 重跑。
- 本輪產品化變更已依目的拆 commit；接手時先看 `git log --oneline -10` 和 `git status --short --branch`，不要只相信這份 handoff 的時間點描述。
- Commit 後預期工作樹只剩一個明確排除的既有 untracked file: `docs/superpowers/specs/2026-06-13-backfill-integration-policy-spec.md`。
- 目前 productization 權威不是這份 handoff: tier、active lane、WIP limit 以 `docs/superpowers/plans/2026-06-15-productization-control-plane.md` 為準。
- 這份 handoff 只回答「最近做了什麼、什麼真的可用、下一步怎麼接」，不能用「比較新」覆蓋 control plane 或 named spec。
- 若後續還要 commit/stage，要整包檢查，不要只 stage 修改檔。
- 本輪有一個不要誤 stage 的既有 untracked file: `docs/superpowers/specs/2026-06-13-backfill-integration-policy-spec.md`。
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

- 目前最新討論已暫時切到 `NL_FAIL` analyte MS1 rescue: 以 `TumorBC2294_DNA / 5-hmdC` 為 debug case，釐清為什麼 trace 有峰但產品仍不能補值。
- 共享 own-max evidence 目前仍是 `diagnostic_only`；product projection 端已先 fail-closed。意思是 own-max normalized same-peak similarity 必須和 paired ISTD / area-ratio / boundary policy 一起過，才有資格補進產品矩陣。5-case own-max diagnostic 只證明這五個 NL_FAIL analyte traces 彼此像同一組峰，還不等於 accepted analyte anchor authority。
- 2026-06-16 已把 owner framing 釘成 shared target/untarget peak identity spine: shared 層只產生峰身份 evidence，targeted/untargeted 各自決定產品輸出；不要把 untargeted backfill authority 原封不動搬成 targeted counted detection。
- 同日已補第一個 shared helper + no-RAW tests，讓一個既有 overlay diagnostic 使用 shared smoothing helper，並新增 targeted diagnostic adapter 輸出 same-peak evidence rows；接著把 product projection 改成 fail-closed，需要 `own_max_same_peak_support` 才能讓 area-ratio/paired-RT 解除 `NL_FAIL` not-counted policy。現在有 explicit opt-in settings/CLI 入口能把已審閱 TSV support row 投進 projection，但預設仍關閉，所以這還沒有讓 `5-hmdC` 在一般 run 裡自動補值。
- 8RAW 和 85RAW explicit opt-in smoke 都已跑過，不是只停在 unit test。第一輪 85RAW 5-row 手動 support TSV 只改到 5 個 reviewed rows；後續 generic RAW-backed producer 產出 11 個 support rows，85RAW opt-in 也剛好改到 11 rows。這支持 explicit opt-in workflow 進 `production_candidate`，但 default extraction/GUI 仍未 production-ready。
- 這個分支正在補 XIC 的產品化地板，不是在重寫 peak picking 演算法。
- 最近完成的主軸是 replay executor: `method_manifest.json` + `--replay-manifest`，已跑過 8RAW 和一次 85RAW replay parity。
- 接著補了三個中期 contract: targeted output schema version、ReviewAction import/application plan/expected-diff/apply-readiness/changeset gate、SampleMetadata schema。
- 2026-06-16 進一步把 ReviewAction changeset 接到 audited output copy，把 `sample_metadata_v1` 接成 extraction `injection_order_source` parity input，並在 manifest 寫清楚 artifact replay policy。
- Alignment 這邊沒有重寫 runtime，只是把文件和 test name 改到符合現況: `alignment_matrix.tsv` 是 machine/validation，不是 production default。
- 目前還不能誤會成完成的是 GUI replay、selected-candidate switch、manual-boundary area recompute、workbook rewrite、primary matrix rewrite、sample role 影響 quant output。
- 下一個最安全的實作點若繼續往 ReviewAction 走，是 candidate sidecar writer 或 manual-boundary recompute writer；兩者都必須保留 expected-diff gate。

## 先講人話

這輪不是在做新演算法，而是在補「成熟工具該有的產品化地板」:

- 跑完一次後，要能知道當時用了什麼設定、什麼 targets、什麼 runtime，並能照 manifest 重跑。
- 輸出要有 schema version，不然下游不知道自己吃的是哪一版欄位語意。
- 人工 review 不能永遠只停在 Excel worklist，至少要先有正式的 review action import schema 和 dry-run apply plan。
- 人工 review 現在已經能從 changeset 寫成 audited targeted-long copy 和 `review_action_apply_audit_v1`，但還不會重算 area 或切 candidate。
- sample metadata 不能每個模組各自猜 QC、blank、batch、matrix；目前 extraction 已能用 `sample_metadata_v1` 產生舊 injection-order mapping，但 role 還不能改矩陣。
- alignment 的 production / machine output wording 要跟 runtime 一致，不然會一直誤會 `alignment_matrix.tsv` 是 production default。

目前狀態: replay executor 已經真正跑過 8RAW 和一次 85RAW；ReviewAction 已能安全寫 audited copy；sample metadata 已能接 extraction injection order；仍沒有改 peak area、selected candidate、workbook、或 primary matrix。

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

還沒做:

- Instrument-QC sequence manifest 還沒轉成 `sample_metadata_v1`。
- Alignment / normalization 還沒 consume 這個 resolver。
- Sample role 還不能拿來改 matrix value 或排除 row。

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

結果: pass, `Success: no issues found in 335 source files`。只剩既有 `annotation-unchecked` notes，沒有 type error。

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -v --tb=short -x
```

結果: `3616 passed, 1 skipped in 62.85s (0:01:02)`

```powershell
python .codex\hooks\fixtures\assert_hook_outputs.py
```

結果: pass

```powershell
git diff --check
```

結果: 沒有 whitespace error，只有 LF/CRLF warning。

RAW-backed 驗證:

- 8RAW 已跑。
- 85RAW 已集中跑一次。
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
   - Local PR closeout gate 已在 2026-06-16 跑過。
   - 尚未 push、尚未看 GitHub CI、尚未開或更新 PR。
   - 注意有一個既有 untracked file: `docs/superpowers/specs/2026-06-13-backfill-integration-policy-spec.md`。這個不是本輪新增，不要誤 stage。

2. 若繼續做 ReviewAction，下一個實作點是 candidate sidecar writer 或 manual-boundary area recompute writer。
   - 現在 audited apply copy 已能消費 changeset rows。
   - `select_candidate` 和 `set_manual_boundary` 仍是 deferred，不能假裝已回寫 selected peak/area。
   - 任何會改 selected peak/area/counting 的下一刀仍要 expected-diff。

3. 第二順位是 sample metadata cross-module parity。
   - Extraction injection-order parity 已接好。
   - Instrument-QC / alignment / normalization 還沒共用這個 resolver。
   - 不要讓 QC/blank/batch role 直接改 quant output。

4. GUI replay 等 GUI 接主線後再做。
   - 現在不要為了 GUI replay 去改未接主線的 GUI 測試。

## 每次收尾要更新這份文件

請用白話更新，不要只丟檔名:

- 今天真正變成可用的是什麼？
- 哪些只是 schema/validator/diagnostic，不是產品行為？
- 哪些測試或 RAW fixture 跑過？
- 哪些大事還沒做？
- 下一個 agent 第一件事應該做什麼？

如果這份文件和 control plane 衝突，control plane 的 tier/active-lane 判斷優先；這份文件要改成摘要 control plane，而不是覆蓋它。若衝突牽涉到 schema 或 RAW evidence，回到 named spec 或 validation note 查證後再同步。
