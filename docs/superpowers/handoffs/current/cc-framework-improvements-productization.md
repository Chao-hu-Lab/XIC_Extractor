# XIC productization handoff

更新日期: 2026-06-15
分支: `cc/framework-improvements`
用途: 給下一個 agent/session 快速接手，不需要重讀整段聊天。

## 目前可接手狀態

- Branch: `cc/framework-improvements`。
- 剛剛的 subagent 驗收不是直接 pass: reviewer 擋下 hook fixture 可信度、manifest replay config 綁定、expected-diff stale approval、sample metadata alias collision。這些已在 follow-up 修正並用 focused tests/hook fixture 重跑。
- 本輪產品化變更已依目的拆 commit；接手時先看 `git log --oneline -8` 和 `git status --short --branch`，不要只相信這份 handoff 的時間點描述。
- Commit 後預期工作樹只剩一個明確排除的既有 untracked file: `docs/superpowers/specs/2026-06-13-backfill-integration-policy-spec.md`。
- 目前 productization 權威不是這份 handoff: tier、active lane、WIP limit 以 `docs/superpowers/plans/2026-06-15-productization-control-plane.md` 為準。
- 這份 handoff 只回答「最近做了什麼、什麼真的可用、下一步怎麼接」，不能用「比較新」覆蓋 control plane 或 named spec。
- 若後續還要 commit/stage，要整包檢查，不要只 stage 修改檔。
- 本輪有一個不要誤 stage 的既有 untracked file: `docs/superpowers/specs/2026-06-13-backfill-integration-policy-spec.md`。
- Hook/交接設計剛被 critical review 挑戰過；目前已補 repo-local hook guardrail，但 PR closeout 前仍要跑 hook fixture smoke。

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

- 這個分支正在補 XIC 的產品化地板，不是在重寫 peak picking 演算法。
- 最近完成的主軸是 replay executor: `method_manifest.json` + `--replay-manifest`，已跑過 8RAW 和一次 85RAW replay parity。
- 接著補了三個中期 contract: targeted output schema version、ReviewAction import/application plan/expected-diff/apply-readiness/changeset gate、SampleMetadata schema。
- Alignment 這邊沒有重寫 runtime，只是把文件和 test name 改到符合現況: `alignment_matrix.tsv` 是 machine/validation，不是 production default。
- 目前還不能誤會成完成的是 GUI replay、full exact artifact replay、ReviewAction product-writing apply/recompute、sample metadata runtime adoption。
- 下一個最安全的實作點是 ReviewAction audit/apply loop，現在 expected-diff template、approval loader、apply-readiness plan、changeset plan 已有雛形；下一刀要讓 product-writing loop 消費 changeset rows，但不能直接大範圍改 selected peak/area。

## 先講人話

這輪不是在做新演算法，而是在補「成熟工具該有的產品化地板」:

- 跑完一次後，要能知道當時用了什麼設定、什麼 targets、什麼 runtime，並能照 manifest 重跑。
- 輸出要有 schema version，不然下游不知道自己吃的是哪一版欄位語意。
- 人工 review 不能永遠只停在 Excel worklist，至少要先有正式的 review action import schema 和 dry-run apply plan。
- sample metadata 不能每個模組各自猜 QC、blank、batch、matrix，要先有共同格式。
- alignment 的 production / machine output wording 要跟 runtime 一致，不然會一直誤會 `alignment_matrix.tsv` 是 production default。

目前狀態: replay executor 已經真正跑過 8RAW 和一次 85RAW；其他中期項目先做到 schema/validator/dry-run plan/contract 層，沒有改 peak、area、counted detection 或 matrix value。

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

已驗證:

- 8RAW CSV-only replay: `xic_results.csv`、`xic_results_long.csv`、`xic_diagnostics.csv` byte parity。
- 8RAW Excel-mode replay: workbook compare passed。
- 85RAW initial + replay: 85 RAW、1715 diagnostics，CSV byte parity + workbook compare passed。

白話結論:

可以說「targeted CLI replay parity 已經做到」。不能說「整個 GUI 或所有 artifact 都 exact replay-ready」。

還沒做:

- GUI replay 尚未接回主線。
- Timestamped workbook hash 還沒納入 manifest，所以還不是 full exact artifact replay。

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
- `scripts/plan_review_action_apply_changesets.py` 會把 ready rows 轉成未來 product writer 需要執行的 operation 和 output scope，例如 `select_candidate`、`set_manual_boundary`、`reject_current`。
- changeset 會明確標 `requires_area_recompute` 或 `requires_candidate_sidecar`，但不會真的重算或切換。
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

現在有正式「人工 review action 檔案長什麼樣」的入口，也能產生 dry-run apply plan，還能把需要人工核准的 expected-diff 模板吐出來。reviewer 改完模板後，有 CLI 可以驗證是否真的成為 approved expected-diff；再下一步可產生 apply-readiness plan，最後產生 changeset plan，告訴未來 writer 要做什麼 operation、會碰哪些 output、還缺 recompute 或 sidecar。這仍不是完整回寫。

還沒做:

- 還不能把 action 寫回 extraction output。
- 還不能因人工 boundary 重算 area。
- 還不能切換 selected candidate。
- 還沒有 applied action 的 audit trail export。
- 還沒有 product-writing loop 消費 changeset row。

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

白話結論:

現在有共同 sample metadata 語言了。QC、blank、batch、matrix 不必每個模組自己猜。

還沒做:

- Extraction 還是讀舊的 `injection_order_source`。
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
- Full exact artifact replay 沒做完。
- Review roundtrip 只做到 action import validation + dry-run application plan，還沒 product-writing apply/recompute。
- Sample metadata 只做到 schema/validator，還沒接 runtime。
- Canonical detection contract 還沒正式寫完。
- ReviewAction apply loop 還沒寫。
- Manual boundary recompute 還沒寫。
- Calibration/normalization 還不能寫回 main matrix。
- Backfill product-authority sidecars 仍不能直接改 primary matrix。
- 本輪變更應拆成目的 commits；接手時用 `git log --oneline -8` 確認實際 commit hash。

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

注意: 以上是 replay/schema/review/sample metadata/alignment 的 focused validation，不是 PR closeout gate。PR 前仍需照 `AGENTS.md` 跑 repo-local CI-equivalent commands。

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

1. 先整理 commit scope。
   - 注意有一個既有 untracked file:
     `docs/superpowers/specs/2026-06-13-backfill-integration-policy-spec.md`
   - 這個不是本輪新增，不要誤 stage。

2. 若繼續做產品化，下一個實作點應該是 ReviewAction audit/apply loop。
   - 目前有 dry-run application plan、expected-diff template、approval validator、apply-readiness plan、changeset plan。
   - 下一刀必須讓 product-writing loop 消費 changeset rows。
   - 不要直接大範圍改 selected peak/area。

3. 第二順位是 sample metadata runtime adoption。
   - 先把 `sample_metadata_v1` 投影成現有 `injection_order_source` 等價行為。
   - 先證明 output 不變，再讓 QC/blank/batch role 參與別的 decision。

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
