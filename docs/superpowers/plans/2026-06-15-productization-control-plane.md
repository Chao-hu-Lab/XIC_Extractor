# XIC Extractor productization control plane

日期: 2026-06-15
狀態: living plan / maintenance checklist
目前 readiness: `diagnostic_only` for this control document
主要依據: [current capability inventory](../reports/2026-06-15-current-capability-inventory-and-promotion-roadmap.md)
白話交接: [current productization handoff](../handoffs/current/cc-framework-improvements-productization.md)

## Authority

這份 control plane 擁有產品化 tier、active lane、WIP limit、promotion
packet 的權威。白話 handoff 只負責讓下一個 agent/session 快速接手，不可
用「比較新」覆蓋本文件的 tier 判斷。若文件衝突，先停止並同步:

1. `git status` / `git diff` 決定目前工作樹實況。
2. 本文件決定 maturity tier、active lane、WIP owner、promotion gate。
3. named specs/plans 決定 schema、CLI/config/output 行為契約。
4. validation notes 決定 RAW/benchmark evidence。
5. handoff 只做白話摘要、接手順序、下一步建議。

Global skills such as `handoff` / `worktree-report` can remind agents how to
write this handoff, but they are local environment helpers. XIC's enforceable
handoff contract is the version-controlled combination of this document,
`docs/agent/codex-operating-system.md`, `.codex/hooks/*`, and hook fixtures.

## Purpose

這份文件是日常產品化控制板。它解決三個反覆發生的問題:

1. 把 `diagnostic_only`、`shadow_ready`、`production_candidate` 誤以為已經正式推到產品。
2. 每次產品化只推進一小片，沒有形成使用者可重跑、可審閱、可稽核的完整 workflow。
3. 同時開太多 spec/diagnostic，最後都卡在「有產物，但不敢當正式產品」。

本文件不是 behavior spec，也不是 implementation plan。它是每次開工、收尾、review、規劃下一步時要更新的控制台。

## Hook enforcement

這份控制台不是只靠人記得。Repo-local hooks 會在三個位置提醒:

- `UserPromptSubmit`: prompt 提到產品化、promotion、正式功能、maturity tier、`method_manifest`、`review_roundtrip` 等詞時，自動把本文件拉回上下文。
- `PreToolUse`: write-like 工具準備修改 product/public surface 時，提醒必須更新本文件，或明確說明沒有 maturity tier 變動。
- `PostToolUse`: patch/write 類工具執行後，若工作樹已有 product/public surface diff 但本文件沒有變更，提醒 closeout 前補 board/log 或明確記錄 no-tier-change；若 product/control-plane 狀態可能變了但白話 handoff 沒有同步，也提醒 closeout 前補 handoff 或明確記錄 handoff 仍有效。

Hooks 是 guardrails，不是語意裁判。它們負責把你和 agent 拉回控制台；
真正的 tier 判斷仍要寫在 promotion packet、spec closeout 或 maintenance
log 裡。Project-local hooks 也需要 Codex runtime trust；如果 hooks 沒有被
trust 或沒有載入，本文件和 handoff checklist 仍是人工 closeout gate。

## Current medium-term active lanes

這次 goal 已擴大到中期可收斂項目，但仍維持 WIP limit。已完成的
`method_manifest_v1`、`targeted_schema_versioning_v1`、ReviewAction audited
apply copy、以及 sample metadata injection-order parity 不再佔 active lane。
Backfill standard-path activation 目前分成兩個 release tier：72-row
high-signal-clean scoped writer 與 42-row low-scan-clean scoped writer 都已用
explicit opt-in scope audit filter 寫出 product matrix-only output，且各自的
`narrow_product_writer_expected_diff_acceptance.json` 通過並標
`readiness_tier=production_ready`。Low-height clean 目前只到
`production_candidate`：activation scope audit 找到 57 個 eligible writes，
且 diagnostic expected-diff 57/57 pass；但同類 heldout trace oracle 只有
19/20 pass，`FAM008651/TumorBC2312_DNA` boundary error `1.16445 min` 超過
accepted `0.1 min` ceiling，所以不得新增 low-height writer 或 claim ready。
擦邊的 apex-delta clean 也只到 `production_candidate`：heldout trace oracle
有 78 candidates / 27 families，selected 20 cases 只有 17/20 pass，最大
boundary error `2.19621 min`，所以也不得新增 apex-delta writer。
Width-only clean 也只到 `production_candidate`：heldout trace oracle 有
4 candidates / 3 families，selected 3 cases 只有 1/3 pass，最大 boundary
error `1.86561 min`、最大 area relative error `0.599229`，所以也不得新增
width-only writer。
Broad 4613-row consolidated activation 仍只有 `production_candidate`，因為
1087 個缺 overlay/trace evidence，其餘 trace-matched writes 還沒有全部落進
已命名、已 oracle-backed 的 ready envelope。若要把 broad scope 也推 ready，
下一個 checkpoint 必須補 broader masked/product-writer oracle，不能把 narrow
ready 外推到 4613-row，也不能把 low-height diagnostic expected-diff 當成
writer approval。
This is a release-safety boundary, not a product north-star limit: the product
direction is to backfill automatically whenever evidence is sufficient, using
the 72-row high-signal and 42-row low-scan slices as demonstrators before
broadening evidence.
Targeted MS1 shape identity limited rescue 也已收斂成窄範圍
`production_ready`：headless explicit support-TSV workflow、headless
auto-limited CLI、以及 canonical no-flag normal CLI default 都可用，但都只限
`limited_5hmdc_5medc_v1`、`5-hmdC + 5-medC`、且產品輸出只能變成
`detected_flagged`。GUI wiring、以及其他 target 仍不在這個 ready claim 內。
ReviewAction selected candidate / manual boundary writer 已 parked for current
release claim；產品方向仍是減少人工審查，之後要用 stable IDs、
expected-diff、audit gate 重新開 lane，而不是要求使用者審完所有案例。
sample metadata cross-module
parity 的 no-output resolver slices 已收斂到 extraction、instrument-QC、
alignment、RT-normalization anchor diagnostic，不可讓 sample role 直接改
main matrix。

| Slot | Lane | Owner | Allowed work | Stop rule |
|---|---|---|---|---|
| Primary | `backfill_standard_seed_guard_scope_v1` | none; 72-row high-signal and 42-row low-scan narrow writer ready slices done; low-height, apex-delta, and width-only probes are candidate only | maintain the explicit scoped activation writer contracts while actively broadening toward the full evidence-sufficient standard-path scope with broader masked/product-writer oracle evidence | stop if the next step would silently broaden matrix writes without expected-diff/oracle evidence, if low-height/apex-delta/width-only is promoted without resolving heldout oracle failures, or if a RAW rerun would not change the broad-scope decision |
| Supporting | `sample_metadata_cross_module_parity_v1` | none; extraction/instrument-QC/alignment/RT-normalization projection slices done | no further role/value behavior without expected-diff; release smoke/docs only | stop if sample role changes extraction output, counted detection, normalized value, or matrix value |
| Parked | `review_action_reintegration_v1` | parked for this release claim | candidate sidecar and manual boundary area recompute remain blocked until stable IDs, sidecar contract, and expected-diff gate exist; long-term product direction is low-manual-intervention automation with audit/review sampling | stop if a manual action changes selected peak/area/counting without expected-diff |
| Diagnostic-only | none | none | no new diagnostic sidecars in this window | stop any diagnostic request unless it directly closes Backfill scope acceptance |
| Frozen queue | calibration/normalization activation | none | classification and planning only | unfreeze only after active lanes are promoted, killed, or explicitly parked |

Hard gate: a lane without a `WIP owner`, productization intake packet, and stop
rule must not enter implementation. Hooks only remind; this table decides active
scope.

## Non-negotiable rule

任何功能不得被稱為 `production_surface`，除非同時滿足以下條件:

- 有明確 public surface: CLI flag、GUI control、config key、CSV/TSV/XLSX schema、report contract、或 downstream handoff。
- 有一個 domain authority owner: 例如 `EvidenceVector`、`PeakHypothesis`、`ProductionDecisionSet`、canonical projection adapter，而不是 writer/report 自己重算決策。
- 有 schema 或 output contract: 欄位、enum、sheet order、hidden state、metadata key、或 JSON schema 必須可檢查。
- 有 replay/provenance: 至少能說出 inputs、config/settings、target/sample metadata、runtime/backend、version/hash。
- 有 focused tests 或 validation gate: 不只 synthetic smoke；若會改 selected area、counted detection、primary matrix，必須有 expected-diff。
- 有 rollback/stop rule: 失敗時知道是退回 shadow、保留 diagnostic，還是 kill 掉。

少一項，最高只能叫 `production_candidate`。如果會改 primary matrix 但缺 expected-diff，最高只能叫 `shadow_ready`。

## Maturity labels

| Label | 可宣稱什麼 | 不可宣稱什麼 | Exit rule |
|---|---|---|---|
| `missing` | 需求存在，尚未有穩定實作。 | 不可寫進 user-facing feature list。 | 寫 spec 或明確 kill。 |
| `partial_internal` | 內部模型/helper 存在。 | 不可當 public contract。 | 收斂到 owner/adaptor，或保留內部。 |
| `diagnostic_only` | 可調查、比較、產出 evidence。 | 不可改 product output；不可當 release feature。 | promote to shadow、kill、或外部化為工具。 |
| `shadow_ready` | 可 side-by-side 比較；主輸出不變。 | 不可 silent promotion；不可改 counted detection/primary matrix。 | expected-diff + activation contract。 |
| `production_candidate` | code/tests 接近正式；可以做 gated rollout。 | 不可宣稱 fully production-ready。 | schema/replay/review gate 通過。 |
| `production_surface` | 使用者或下游可依賴的正式 surface。 | 不代表 science readiness 已滿；仍要標驗證範圍。 | 納入 regression/release gate。 |
| `production_ready` | 可作正式 release claim。 | 不可只靠單一小 fixture 或 docs。 | 至少通過指定 fixture、expected-diff、downstream smoke。 |

## Active productization board

每次狀態改變都更新這張表。不要只在聊天裡說「應該已經產品化」。

| Lane | Current tier | Current owner / artifact | Product gap | Next checkpoint | WIP owner |
|---|---:|---|---|---|---|
| Targeted product projection: `Product State`, `Counted Detection`, `Reason` | `production_surface` | `targeted_product_projection.py`, CSV/workbook writers | schema version 已鎖；缺 canonical projection adapter 文檔 | `canonical_detection_contract_v1` | unassigned |
| Targeted MS1 shape identity limited rescue | `production_ready` for headless explicit support-TSV workflow, headless auto-limited CLI, and canonical no-flag normal CLI default; GUI still off | `targeted_ms1_shape_identity_activation_policy=limited_5hmdc_5medc_v1`, `--targeted-ms1-shape-identity-support-tsv`, `--targeted-ms1-shape-identity-auto-limited-default`, `xic_extractor.diagnostics.targeted_ms1_shape_identity_support_producer`, `targeted_ms1_shape_identity_auto_diff`, expected-diff gate, 8RAW/85RAW auto artifacts | default no-flag CLI now runs the same support-TSV key-set expected-diff gate when no support TSV is configured；limited policy `limited_5hmdc_5medc_v1` 限 `5-hmdC + 5-medC` 且只能寫 `detected_flagged`；explicit support TSV mode remains available with `explicit_support_tsv`; GUI 仍 out of scope | broaden beyond `5-hmdC + 5-medC` only with new expected-diff/RAW evidence; GUI wiring waits for main GUI reconnect | none for headless limited workflows |
| Targeted output schema versioning | `production_surface` | `output/schema.py`, manifest `output_schema`, workbook `Run Metadata` | CSV 欄位形狀未改；version 目前透過 manifest/metadata 暴露，不是每列 CSV 欄位 | schema snapshot / downstream handoff profile | none; slice done |
| `EvidenceVector` / `PeakHypothesis` / `IntegrationResult` spine | `production_candidate` | `peak_detection/hypotheses.py`, result assembly | 缺 stable detection id、typed `ReviewAction`、durable audit transition | `canonical_detection_contract_v1` | unassigned |
| `AuditTrail` | `partial_internal` | `PeakHypothesis.audit` | 不是 user-visible operation history | `review_roundtrip_v1` | unassigned |
| `Review Queue` | `production_surface` as worklist | workbook `Review Queue` sheet | 不能讀回 decision；不能 reintegrate | `review_roundtrip_v1` | unassigned |
| ReviewAction audited apply copy | `production_surface` for audited targeted-long copy | `xic_extractor.review_actions`, `scripts/apply_review_action_changesets.py`, `review_action_apply_audit_v1` | accept/mark/reject 可寫 audited output copy；select candidate/manual boundary 仍 deferred | candidate sidecar + manual boundary recompute writer | none; audited apply slice done |
| Manual boundary / reintegration | `parked`; `production_candidate` for deferred changeset only | candidate/boundary sidecars + action schema + changeset rows | 沒有 area recompute writer；沒有 selected candidate switch writer；需要產品決策確認是否可改 selected peak/area | `review_action_reintegration_v1` product decision | parked |
| `Run Metadata` | `production_surface` as workbook metadata | workbook sheet + manifest/schema reverse reference | 不是 full replay manifest；只反向記錄 targeted output schema 與 manifest schema/path/hash | workbook hash capture / release metadata docs | unassigned |
| `method_manifest.json` | `production_ready` for targeted CLI replay parity | `xic_extractor.output.method_manifest`, `output/method_manifest.json` | 8RAW/85RAW CSV + normalized workbook replay parity passed；artifact policy says CSV exact, workbook normalized compare, manifest provenance-only | full byte-exact workbook replay only if a future release needs it | unassigned |
| Headless targeted CLI | `production_ready` for targeted CLI replay parity | `xic-extractor-cli`, `--replay-manifest`, method manifest invocation context | replay rejects runtime overrides；GUI replay 未接主線 | GUI parity after mainline wiring | unassigned |
| GUI/CLI parity | `partial_internal` | shared `load_config` / `extractor.run` | 缺 fixture-level parity diff | narrow parity smoke | unassigned |
| `injection_order_source` | `production_surface` | settings/config/extraction pipeline | 只處理 order，不是 sample metadata universe | `sample_metadata_contract_v1` | unassigned |
| Sample metadata roles | `production_surface` for extraction/alignment/RT-normalization injection-order parity and instrument-QC manifest projection; `production_candidate` for roles | `xic_extractor.sample_metadata`, `scripts/validate_sample_metadata.py`, `resolve_injection_order`, `run_alignment --sample-column-injection-order`, `instrument_qc_sample_metadata.tsv`, `analyze_rt_normalization_anchors.py --sample-info` | extraction 可用 `sample_metadata_v1` 當 injection-order source；alignment 可用 `sample_metadata_v1` 排 final matrix sample columns；instrument-QC method-doc manifest 可輸出 `sample_metadata_v1` sidecar；RT-normalization anchor diagnostic 可用 `sample_metadata_v1` 投影 injection order；roles/batch/matrix/exclusion 尚不改 product values 或 normalized values | role-aware QC/blank/batch behavior only with expected-diff gate | none; cross-module projection slices done |
| Instrument-QC trend sidecar | `production_surface` sidecar | `run_instrument_qc.py`, instrument_qc package, `instrument_qc_sample_metadata.tsv` | 不改 main matrix；sample metadata sidecar 只做 metadata projection | release smoke / downstream docs | none; projection slice done |
| Calibration preview | `shadow_ready` / `diagnostic_only` | instrument-QC calibration preview | 不可寫 main matrix；response transfer blocked | `normalization_calibration_activation_v1` | unassigned |
| Alignment workbook Matrix/Review/Audit | `production_surface` | `alignment_results.xlsx`, `xlsx_writer.py`, `alignment-results-v3` | output-level wording now matches runtime; keep release tests guarding sheet/schema shape | alignment release gate | unassigned |
| Alignment output-level contract | `production_surface` | `output_levels.py`, `--output-level`, output contract spec | `alignment_matrix.tsv` is machine/validation, not production default；`alignment_matrix_identity.tsv` is production-level identity handoff | keep production/machine/debug tests in release gate | none; contract slice done |
| `ProductionDecisionSet` | `production_surface` for alignment matrix decisions | `alignment/production_decisions.py` | release gate 尚未集中檢查 all writers use it | matrix writer gate | unassigned |
| Backfill product-authority sidecars | `production_ready` for explicit 72-row high-signal-clean scoped writer and explicit 42-row low-scan-clean scoped writer; `production_candidate` for the 57-row low-height diagnostic slice, apex-delta diagnostic probe, width-only diagnostic probe, and broad 4613-row standard-path seed guard | allowlist/projection sidecars, `standard_peak_backfill_productization.py`, `standard_peak_activation_scope_audit.py`, `standard_peak_heldout_trace_oracle.py`, `seed_guard_decisions.tsv`, no-RAW 85RAW artifact bridge, heldout trace oracle, activation scope audit, and scoped writer outputs under `output/productization_realdata_seed_guard_85raw_20260617/` | standard-path activation 先經 N-band seed guard 且 join `activation_value_delta.tsv`；既有 85RAW chunk `r1_120` no-RAW bridge passed with 2540 candidates, 1160 eligible writes, 1380 low-seed no-writes；既有 85RAW consolidated no-RAW bridge passed with 7307 candidates, 4613 eligible writes, 2694 low-seed no-writes；high-signal heldout trace oracle 有 20 個 originally detected、sample-local cases，20/20 pass、最大 boundary error 0.0820502 min、最大 area relative error 0.0762325；low-scan heldout trace oracle `heldout_trace_reintegration_oracle_low_scan_clean_probe/` 有 56 eligible candidates / 11 selected family cases，11/11 pass、最大 boundary error 4.86717e-05 min、最大 area relative error 0.038786；combined activation scope audit 證明目前 4613 writes 中 72 個 high-signal clean eligible、42 個 low-scan clean eligible、57 個 low-height clean eligible、1087 個 missing overlay path，broad scope 仍 not_ready；high-signal `narrow_product_writer_expected_diff_acceptance.json` 72/72 pass 且 `readiness_tier=production_ready`；low-scan `narrow_low_scan_clean_no_raw_productization/narrow_product_writer_expected_diff_acceptance.json` 42/42 pass、duplicate/missing/unexpected/non-eligible/non-written/unchanged/blank 都是 0，`expected_scope=low_scan_clean_eligible_activation_rows`、`product_surface_changed=TRUE`、`readiness_tier=production_ready`；low-height `low_height_clean_activation_expected_diff_acceptance.json` 57/57 pass 但 `product_surface_changed=FALSE`，同類 `heldout_trace_reintegration_oracle_low_height_clean_probe/summary.json` 是 `status=fail`、19/20 pass、max boundary error `1.16445 min`，所以沒有 writer approval；apex-delta probe `heldout_trace_reintegration_oracle_apex_delta_clean_probe/summary.json` 是 `status=fail`、17/20 pass、max boundary error `2.19621 min`、max area relative error `0.424518`，所以沒有 writer approval；width-only probe `heldout_trace_reintegration_oracle_width_clean_probe/summary.json` 是 `status=fail`、1/3 pass、max boundary error `1.86561 min`、max area relative error `0.599229`，所以沒有 writer approval；observed provenance contract 禁止 oracle/manual/review row 自抄；非標準 peak 仍不可自動 promotion | release docs must say 72-row and 42-row scopes are current safe demonstrators, low-height/apex-delta/width-only are only candidate probes, and none of these are the product ceiling; next broadening step needs another named evidence class with masked/product-writer observed oracle and expected-diff approval | none for the two scoped writers; low-height/apex-delta/width-only need narrower rules or passing oracles before writer work; broad 4613 still needs additional evidence class/oracle coverage |
| Provisional production-candidate gate | `diagnostic_only` with no-promotion guard | production-candidate sidecar, `tests/test_provisional_backfill_candidate_gate_cli.py` | legacy artifact name is still potentially confusing, but summary/test contract says `readiness_label=diagnostic_only`, `production_ready=false`, `matrix_contract_changed=false`, and the CLI does not mutate `alignment_matrix.tsv` | rename only if future public UX needs it; do not promote from this sidecar alone | none; diagnostic guard done |

## WIP limits

目前開發節奏拖慢的主因不是缺想法，而是同時開太多 diagnostic/spec，沒有把其中少數推完。

每個 2 週維護週期最多允許:

- 1 個 primary productization lane。
- 1 個 supporting infrastructure lane。
- 1 個 diagnostic-only lane。

若要新增 lane，必須先把現有 lane 之一改成:

- `production_surface`
- `shadow_ready` with explicit next gate
- `diagnostic_only` archived with kill/externalize decision
- abandoned with reason

## Weekly maintenance checklist

建議每週固定一次，或每次重大 PR 收尾後執行。

### 1. Board hygiene

- [ ] `Active productization board` 每一列的 tier 是否仍準確。
- [ ] 有沒有功能在聊天、README、報告、PR 中被過度宣稱。
- [ ] 新增的 diagnostic/report/sidecar 是否有 exit rule。
- [ ] `WIP owner` 是否明確；沒有 owner 的 lane 不應進入 active implementation。
- [ ] 有沒有超過 WIP limit。

### 2. Contract hygiene

- [ ] Public surface 是否有 schema/version/required columns。
- [ ] Workbook/CSV/TSV/JSON 欄位變更是否同步 tests。
- [ ] Config key / CLI flag / GUI setting 是否同步 docs。
- [ ] Downstream handoff 是否明確 owner 與 pass-through/exclusion rule。
- [ ] Report 是否只 render，不重新計算 domain decision。

### 3. Promotion hygiene

- [ ] 這週是否有任何 selected peak、area、confidence、reason、counted detection、matrix value 會改變。
- [ ] 若會改變，是否有 expected-diff artifact。
- [ ] 若只在 sidecar，主輸出是否被測試確認不變。
- [ ] 是否有 rollback/stop rule。
- [ ] 是否有 reviewer/audit trail 記錄。

### 4. Validation hygiene

- [ ] 本週 claims 使用的是 synthetic、8RAW、85RAW、targeted benchmark、manual EIC/MS2 review，還是 docs-only。
- [ ] 是否把 tests passing 誤寫成 production readiness。
- [ ] 是否有 large RAW gate 被偷偷跳過。
- [ ] 是否有 downstream workbook/TSV smoke。
- [ ] 是否有 stale output 被當成新 evidence。

### 5. Drift cleanup

- [ ] 舊 spec 是否仍和 runtime reality 一致。
- [ ] 有沒有多份 docs 對同一能力給不同 tier。
- [ ] 有沒有命名造成誤會，例如 `production_candidate_gate` 被誤認為 production promotion。
- [ ] 有沒有 legacy name 應保留為 compatibility，而不是立刻 rename。
- [ ] 是否需要把本週結論回寫到這份 control plane。
- [ ] 是否已同步更新白話交接文件 `docs/superpowers/handoffs/current/cc-framework-improvements-productization.md`。
- [ ] `git status --short -- docs/superpowers/handoffs/current/cc-framework-improvements-productization.md docs/superpowers/plans/2026-06-15-productization-control-plane.md` 是否符合預期；若 handoff 是接手必需品，必須 tracked/ staged/ committed，或明確標成 local-only/non-authoritative。

## Pre-work checklist

任何產品化 task 開始前先填。

```markdown
## Productization intake

- Feature/lane:
- Current tier:
- Desired tier this PR:
- Product surface touched:
- Domain authority owner:
- Files/modules likely touched:
- Public contract affected:
- Expected output change:
- Expected-diff needed: yes/no
- Validation fixture: synthetic / 8RAW / 85RAW / targeted benchmark / manual review / docs-only
- Stop rule:
- Rollback rule:
- Downstream consumer:
```

如果 `Desired tier this PR` 是 `production_surface` 或 `production_ready`，但 `Expected-diff needed` 是空白，停止。

## Promotion packet template

每次要把功能從 lower tier 推到 higher tier，必須有一份 promotion packet。可以寫在 PR description、spec closeout note，或本檔下方 append。

```markdown
## Promotion packet

### Capability

- Name:
- Previous tier:
- Proposed tier:
- Owner:

### Public surface

- CLI/config/GUI/output/report:
- Schema/version:
- Downstream consumer:

### Domain authority

- Decision owner:
- Evidence source:
- Why writer/report is not recomputing domain logic:

### Behavior delta

- What changes:
- What must not change:
- Expected-diff artifact:
- Rows/targets/samples affected:

### Validation

- Synthetic tests:
- Focused unit/integration tests:
- 8RAW:
- 85RAW:
- Manual review:
- Downstream smoke:

### Audit and replay

- Metadata/provenance:
- Manifest/replay support:
- Review/action log:

### Stop/rollback

- Stop if:
- Roll back by:
- Residual risk:
```

## Definition of done by tier change

### `missing` -> `partial_internal`

- [ ] Internal owner named.
- [ ] Scope kept out of public docs/README.
- [ ] Tests prove helper behavior or parser behavior.
- [ ] Exit rule named.

### `partial_internal` -> `diagnostic_only`

- [ ] CLI/tool/report can run without changing product outputs.
- [ ] Output path under `output/` or documented diagnostic location.
- [ ] Summary labels itself `diagnostic_only`.
- [ ] No writer/import cycle from diagnostics back into domain/product code.
- [ ] Clear next decision: promote, kill, or externalize.

### `diagnostic_only` -> `shadow_ready`

- [ ] Shadow artifact is rejoinable to product rows/samples/targets.
- [ ] Product outputs are tested unchanged.
- [ ] Shadow schema has required columns and version.
- [ ] Summary states `shadow_ready`, not product-ready.
- [ ] Comparison report explains expected product impact if activated.

### `shadow_ready` -> `production_candidate`

- [ ] Activation/export contract exists.
- [ ] Domain authority owner is named.
- [ ] Expected-diff is produced and reviewed.
- [ ] Focused tests cover accepted/rejected/blocked cases.
- [ ] Downstream schema impact is documented.
- [ ] Rollback path is explicit.

### `production_candidate` -> `production_surface`

- [ ] Public surface is stable and documented.
- [ ] Schema/version is locked by tests.
- [ ] CLI/GUI/config/report docs are synchronized.
- [ ] Replay/provenance is available.
- [ ] Main output and audit output agree.
- [ ] Release gate includes this behavior.

### `production_surface` -> `production_ready`

- [ ] Validation fixture tier is named and sufficient for claim.
- [ ] 8RAW/85RAW or targeted benchmark requirement is met, if applicable.
- [ ] Manual EIC/MS2 review is documented when science judgment is required.
- [ ] Downstream consumer smoke passes.
- [ ] Known residual risks are documented.

## Monthly reset checklist

每月做一次，避免拖沓變成常態。

- [ ] Count active lanes. If >3, freeze new work.
- [ ] Pick exactly one lane to push to next tier.
- [ ] Pick exactly one lane to kill/archive/externalize.
- [ ] Review all `diagnostic_only` artifacts older than 30 days.
- [ ] Review all specs/plans with no owner.
- [ ] Update this board with actual tier, not aspirational tier.
- [ ] Write one closeout note summarizing what changed in product surface.

## Immediate 2026-06 queue

依照 current capability inventory 與本輪 replay executor closeout，目前順序改成:

1. `method_manifest_v1` - done
   - Result: `production_ready` for targeted CLI replay parity.
   - Evidence: focused tests, 8RAW CSV/workbook replay parity, and one targeted 85RAW initial+replay sequence.
   - Residual: no timestamped workbook hash capture; GUI replay not wired to mainline.

2. `targeted_schema_versioning_v1` - done
   - Reason: mature-tool parity 需要 output schema version，不然下游與 replay 只能猜欄位語意。
   - Result: `production_surface` for additive schema/version contract.
   - Scope: `output/schema.py` constants, manifest `output_schema`, workbook `Run Metadata`; no CSV data-column changes.

3. `review_action_apply_v1` - primary lane
   - Reason: 解決 Review Queue 不能回寫，這是 Skyline parity floor。
   - Current baseline: `production_candidate` for action schema/import validator and dry-run application plan only.
   - Next target: audit/apply loop with expected-diff before touching selected outputs.

4. `sample_metadata_runtime_parity_v1` - supporting lane
   - Reason: normalization/QC/alignment 都需要 sample type、QC、blank、batch、injection order。
   - Current baseline: `production_candidate` for schema/validator only.
   - Next target: project current legacy injection order behavior into the shared resolver with output parity; do not let sample role change matrix behavior in this slice.

5. `alignment_output_contract_v1` - done as contract/docs alignment
   - Reason: `alignment_results.xlsx` 已成熟，但 TSV production/machine wording 需要對齊。
   - Result: `production_surface` for output-level contract.
   - Guard: `alignment_matrix.tsv` remains machine/validation, while `alignment_matrix_identity.tsv` is a production-level identity handoff.

暫時不要優先做:

- 新 peak picker。
- 新 diagnostic gallery。
- 新 shadow sidecar。
- normalization/calibration main-matrix write。
- backfill product-authority primary matrix activation。

除非 `Current medium-term active lanes` 先把其中一個 lane 解凍，且該 lane 已經有 owner、spec、promotion packet，否則新增這些只會增加未收斂面積。

## Maintenance log

新增產品化狀態變更時，在這裡 append。格式:

```markdown
### YYYY-MM-DD - <lane>

- Previous tier:
- New tier:
- Evidence:
- Product surface changed:
- Validation:
- Remaining blocker:
```

### 2026-06-15 - Control plane initialized

- Previous tier: none
- New tier: living maintenance checklist
- Evidence: current capability inventory and five-area read-only review
- Product surface changed: none
- Validation: document smoke only
- Remaining blocker: no active owner assigned to the first four June focus specs

### 2026-06-15 - method_manifest_v1

- Previous tier: `missing`
- New tier: `production_ready` for targeted CLI replay parity; not full exact artifact replay
- Evidence: `docs/superpowers/specs/2026-06-15-method-manifest-v1-spec.md`; `docs/superpowers/notes/2026-06-15-replay-executor-validation-note.md`; `xic_extractor.output.method_manifest`; `xic-extractor-cli --replay-manifest`; focused manifest/output metadata/CLI replay tests; targeted 8RAW and 85RAW CSV/workbook replay parity; post-review test that replay rejects settings/targets artifact paths that do not bind to `invocation.config_dir`
- Product surface changed: additive `output/method_manifest.json`; additive workbook `Run Metadata` rows `method_manifest_schema`, `method_manifest_path`, `method_manifest_sha256`; additive `--replay-manifest` CLI mode
- Validation: synthetic/focused unit, output contract, CLI replay tests, targeted 8RAW CSV-only replay byte parity, targeted 8RAW Excel-mode workbook compare, and one targeted 85RAW initial+replay sequence with CSV byte parity plus workbook compare
- Remaining blocker: no timestamped workbook hash capture for full exact artifact replay; GUI parity intentionally skipped because GUI replay is not yet wired to mainline

### 2026-06-15 - targeted_schema_versioning_v1

- Previous tier: `missing` as an explicit targeted output schema contract
- New tier: `production_surface` for additive schema/version metadata
- Evidence: `xic_extractor.output.schema` version constants; `method_manifest.json` `output_schema`; workbook `Run Metadata` row `targeted_output_schema_version`
- Product surface changed: additive `targeted_output_schema_version` metadata row and additive manifest `output_schema` block; no CSV data-column changes
- Validation: `python -m pytest tests\test_output_schema_contract.py tests\test_output_metadata.py tests\test_method_manifest.py -q`
- Remaining blocker: downstream export profiles still need a handoff profile; schema version is surfaced through manifest/metadata, not embedded as a row-level CSV column

### 2026-06-15 - review_action_import_and_application_plan_v1

- Previous tier: `missing`
- New tier: `production_candidate` for ReviewAction import validation, dry-run application plan, expected-diff approval template/loader, apply-readiness planning, and changeset planning only
- Evidence: `docs/superpowers/specs/2026-06-15-review-roundtrip-v1-spec.md`; `xic_extractor.review_actions`; `scripts/validate_review_actions.py`; `scripts/plan_review_action_applications.py`; `scripts/validate_review_action_expected_diffs.py`; `scripts/plan_review_action_apply_readiness.py`; `scripts/plan_review_action_apply_changesets.py`; post-review stale-approval guard that blocks expected-diff approvals when the current targeted row no longer matches the approved baseline state
- Product surface changed: additive `review_action_v1` TSV/CSV schema, validator CLI, additive `review_action_application_plan_v1` dry-run TSV, optional `review_action_expected_diff_v1` template TSV with baseline target-state columns, expected-diff approval loader, approval validator CLI, additive `review_action_apply_readiness_v1` TSV planner, and additive `review_action_apply_changeset_v1` TSV planner; no extraction output mutation
- Validation: `python -m pytest tests\test_review_actions.py -q`; `$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor\review_actions.py scripts\validate_review_actions.py scripts\plan_review_action_applications.py scripts\validate_review_action_expected_diffs.py scripts\plan_review_action_apply_readiness.py scripts\plan_review_action_apply_changesets.py tests\test_review_actions.py`; `$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor\review_actions.py scripts\validate_review_actions.py scripts\plan_review_action_applications.py scripts\validate_review_action_expected_diffs.py scripts\plan_review_action_apply_readiness.py scripts\plan_review_action_apply_changesets.py`
- Remaining blocker: no product-writing action application/reintegration loop, no manual boundary recompute, no selected candidate switch writer, no audited output writer that consumes changeset rows

### 2026-06-15 - sample_metadata_contract_v1

- Previous tier: `partial_internal`
- New tier: `production_candidate` for shared schema/validator only
- Evidence: `docs/superpowers/specs/2026-06-15-sample-metadata-contract-v1-spec.md`; `xic_extractor.sample_metadata`; `scripts/validate_sample_metadata.py`; post-review alias-collision tests for shared `sample_name`/`raw_stem` injection-order namespace
- Product surface changed: additive `sample_metadata_v1` TSV/CSV schema and validator CLI; no extraction/QC/alignment runtime change
- Validation: `python -m pytest tests\test_sample_metadata.py -q`; `$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor\sample_metadata.py scripts\validate_sample_metadata.py tests\test_sample_metadata.py`; `$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor\sample_metadata.py scripts\validate_sample_metadata.py`
- Remaining blocker: extraction still reads legacy `injection_order_source`; instrument-QC sequence manifest is not yet projected into `sample_metadata_v1`; alignment and normalization do not consume this resolver; sample roles cannot alter matrix values without expected-diff gates

### 2026-06-16 - review_action_audited_apply_copy_v1

- Previous tier: `production_candidate` for import/apply-readiness/changeset planning only
- New tier: `production_surface` for audited targeted-long output copy and `review_action_apply_audit_v1`
- Evidence: `xic_extractor.review_actions`; `scripts/apply_review_action_changesets.py`; `tests/test_review_actions.py`
- Product surface changed: additive CLI that consumes `review_action_apply_changeset_v1` and writes an audited targeted-long copy plus audit TSV. The command refuses input overwrite and rejects blocked changesets by default.
- Safe behavior boundary: `accept_current` is audit-only; `mark_unresolved` writes only `Review State = unresolved_by_review`; `reject_current` may write `Product State = rejected_by_review`, `Counted Detection = FALSE`, and `Review State = rejected_by_review` only after approved expected-diff. `select_candidate` and `set_manual_boundary` remain deferred because they need candidate sidecar or area recompute.
- Validation: `python -m pytest tests\test_review_actions.py -q`
- Remaining blocker: no selected-candidate switch writer, no manual-boundary area recompute writer, no workbook or primary matrix rewrite.

### 2026-06-16 - sample_metadata_runtime_parity_v1

- Previous tier: `production_candidate` for schema/validator only
- New tier: `production_surface` for extraction injection-order parity; `production_candidate` for roles/batch/matrix/exclusion semantics
- Evidence: `xic_extractor.sample_metadata`; `xic_extractor.extraction.pipeline.resolve_injection_order`; `tests/test_sample_metadata.py`; `tests/test_extractor_run.py`
- Product surface changed: existing `injection_order_source` can now point to a `sample_metadata_v1` CSV/TSV. Legacy `Sample_Name,Injection_Order` files still use the legacy parser.
- Safe behavior boundary: only injection-order mapping is projected; `sample_role`, batch, matrix, group, and exclusion fields do not alter extraction output, counted detection, or matrix values.
- Validation: `python -m pytest tests\test_sample_metadata.py tests\test_injection_rolling.py tests\test_extractor_run.py -q`
- Remaining blocker: instrument-QC, alignment, and normalization do not yet consume the shared sample metadata resolver.

### 2026-06-16 - review_action_reintegration_v1

- Previous tier: `production_candidate` for deferred changeset rows; selected-candidate switch and manual-boundary area recompute deferred
- New tier: `parked`; audited apply copy remains `production_surface`, deferred changesets remain `production_candidate`
- Evidence: `docs/superpowers/specs/2026-06-15-review-roundtrip-v1-spec.md`; current `xic_extractor.review_actions` apply path records `select_candidate` and `set_manual_boundary` as deferred operations only
- Product surface changed: none this round
- Validation: no code path changed in this lane this round
- Remaining blocker: human product decision and expected-diff acceptance are required before any writer may change selected peak, selected area, workbook, primary matrix, or counted detection for these actions

### 2026-06-16 - sample_metadata_instrument_qc_projection_v1

- Previous tier: `production_candidate` for roles/batch/matrix metadata outside extraction
- New tier: `production_surface` for additive instrument-QC `sample_metadata_v1` sidecar; roles remain non-mutating metadata only
- Evidence: `xic_extractor.instrument_qc.sequence_manifest_writers.write_sample_metadata_tsv`; `scripts/run_instrument_qc.py --method-doc`; `tests/test_instrument_qc_sequence_manifest.py`; `tests/test_run_instrument_qc.py`
- Product surface changed: additive `instrument_qc_sample_metadata.tsv` written next to `instrument_qc_sequence_manifest.tsv` and `instrument_qc_injection_order.csv` when `--method-doc` is used. It includes actual matched RAW rows and raw-dir-only instrument-QC rows, maps instrument-QC class to `sample_role`, and does not feed role metadata into quant behavior.
- Validation: `python -m pytest tests\test_instrument_qc_sequence_manifest.py tests\test_run_instrument_qc.py -q`; touched-file ruff/mypy passed
- Remaining blocker: alignment and normalization still do not consume the shared resolver; sample roles/exclusions must not alter matrix values without a separate expected-diff gate

### 2026-06-17 - sample_metadata_alignment_column_order_v1

- Previous tier: `production_surface` for extraction injection-order parity and instrument-QC sidecar; alignment remained a resolver-parity blocker
- New tier: `production_surface` for alignment sample-column injection-order parity; roles remain non-mutating metadata only
- Evidence: `xic_extractor.alignment.pipeline.run_alignment`; `scripts/run_alignment.py --sample-column-injection-order`; `tests/test_alignment_pipeline_outputs.py`
- Product surface changed: `--sample-column-injection-order` may now receive a `sample_metadata_v1` CSV/TSV in addition to legacy `Sample_Name,Injection_Order` CSV/XLSX. The shared metadata parser projects `sample_name`/`raw_stem` aliases into the same injection-order mapping used for final matrix/status sample-column ordering.
- Safe behavior boundary: this reorders output sample columns only when the user explicitly supplies the input path. Sample roles, exclusions, batch, matrix type, and group still do not alter matrix values, counted detection, feature acceptance, or backfill activation.
- Validation: `python -m pytest tests\test_alignment_pipeline_outputs.py::test_pipeline_orders_sample_columns_by_sample_metadata_v1 tests\test_alignment_pipeline_outputs.py::test_pipeline_orders_sample_columns_by_injection_order tests\test_alignment_pipeline_outputs.py::test_pipeline_keeps_input_sample_order_without_injection_source -q`; touched-file ruff passed
- Remaining blocker: normalization still does not consume the shared resolver; sample roles/exclusions must not alter matrix values without a separate expected-diff gate

### 2026-06-17 - sample_metadata_rt_normalization_anchor_resolver_v1

- Previous tier: `production_surface` for extraction/alignment injection-order parity and instrument-QC sidecar; RT-normalization anchor diagnostic remained a resolver-parity blocker
- New tier: `production_surface` for RT-normalization anchor diagnostic injection-order parity; roles remain non-mutating metadata only
- Evidence: `tools/diagnostics/rt_normalization_anchor_loaders.py`; `tools/diagnostics/analyze_rt_normalization_anchors.py --sample-info`; `tests/test_rt_normalization_anchors.py`
- Product surface changed: `--sample-info` for injection-based RT-normalization anchor references may now receive a `sample_metadata_v1` CSV/TSV in addition to legacy `Sample_Name,Injection_Order` input. The diagnostic projects `sample_name`/`raw_stem` aliases into the same injection-order mapping used by legacy rolling-anchor references.
- Safe behavior boundary: this affects only injection-order lookup for `injection-local-median` and `injection-loess` RT-normalization anchor diagnostics. Sample roles, exclusions, batch, matrix type, and group do not alter normalized values, matrix values, counted detection, feature acceptance, or calibration/main-matrix writes.
- Validation: `uv run pytest tests\test_rt_normalization_anchors.py -q` (`16 passed`); `uv run ruff check tools\diagnostics\rt_normalization_anchor_loaders.py tests\test_rt_normalization_anchors.py` (`All checks passed!`); `uv run mypy tools\diagnostics\rt_normalization_anchor_loaders.py` (`Success: no issues found in 1 source file`); subagent reviewer `Descartes` found no P1/P2 blocker and the P3 request to cover `injection-loess` parity was fixed.
- Remaining blocker: role-aware QC/blank/batch/matrix behavior and calibration/normalization writes remain blocked until a separate expected-diff gate and product decision exist.

### 2026-06-16 - targeted_ms1_shape_identity_explicit_optin_v1

- Previous tier: `diagnostic_only` for shared MS1 shape evidence; explicit opt-in workflow pending tier decision
- New tier: `production_candidate` for explicit support-TSV workflow only
- Evidence: `docs/superpowers/specs/2026-06-16-shared-target-untarget-peak-identity-spine-spec.md`; 8RAW expected-diff artifact `output/ms1_shape_identity_optin_8raw_20260616/expected_diff_summary.tsv`; 85RAW manual-support and generic-support artifacts under `output/ms1_shape_identity_optin_85raw_20260616/` and `output/ms1_shape_identity_generic_support_85raw_20260616/`
- Product surface changed: none this round; existing explicit config/CLI support path remains opt-in
- Validation: reused existing 8RAW/85RAW artifacts; no new 85RAW run because the existing artifacts already answer the candidate-tier decision
- Remaining blocker: default automatic support generation/consumption remains
  off. Broader target expansion, default extraction, and GUI rescue remain not
  production-ready.

### 2026-06-16 - standard_peak_seed_guard_v1

- Previous tier: `shadow_ready` for backfill product-authority sidecars; seed guard spec was `implementation_candidate`
- New tier: `production_candidate` for standard-path seed guard slice only
- Evidence: `xic_extractor.diagnostics.standard_peak_shadow_activation_inputs`; `xic_extractor.diagnostics.standard_peak_backfill_productization`; additive `seed_guard_decisions.tsv`; heldout oracle result schema/evaluator; `tests/test_standard_peak_shadow_activation_inputs.py`; `tests/test_standard_peak_backfill_productization.py`
- Product surface changed: standard-peak matrix activation now evaluates standard-path promotion candidates against N-band seed support before writing activation decisions. The acceptance artifact proves candidate coverage, low-seed no-write expectations, and actual write attribution through `activation_value_delta.tsv`. No workbook schema, review-row enum, primary alignment schema, or non-standard peak policy changed.
- Validation: `python -m pytest tests\test_standard_peak_shadow_activation_inputs.py tests\test_standard_peak_backfill_productization.py -q`; touched-file ruff/mypy passed
- Remaining blocker: production-ready still needs heldout oracle result rows from real/reviewed cases plus an 85RAW expected-diff gate. Non-standard peak automatic promotion remains out of scope.

### 2026-06-17 - standard_peak_heldout_oracle_results_cli_v1

- Previous tier: `production_candidate` for standard-path seed guard with package-level heldout oracle evaluator
- New tier: still `production_candidate`; heldout oracle result gate is now executable, but not satisfied by real/reviewed rows
- Evidence: `tools/diagnostics/standard_peak_heldout_oracle_results.py`; `xic_extractor.diagnostics.standard_peak_shadow_activation_inputs.build_heldout_oracle_results`; `tests/test_standard_peak_shadow_activation_inputs.py`
- Product surface changed: additive diagnostic CLI that reads deterministic `heldout_oracle_manifest.tsv` plus observed boundary/area result rows and writes `heldout_oracle_results.tsv` with source artifact SHA. It does not run RAW, generate reviewed oracle rows, mutate matrices, or authorize non-standard peaks.
- Validation: `python -m pytest tests\test_standard_peak_shadow_activation_inputs.py::test_standard_peak_heldout_oracle_results_cli_writes_contract_tsv tests\test_standard_peak_shadow_activation_inputs.py::test_standard_peak_heldout_oracle_results_classify_boundary_and_area -q`; touched-file ruff passed
- Remaining blocker at this checkpoint: production-ready still needed
  real/reviewed heldout oracle rows and a bounded 85RAW expected-diff gate.
  Later `standard_peak_heldout_trace_reintegration_oracle_v1` supplies a
  high-signal clean heldout slice; broad activation still needs scope/expected
  diff acceptance.

### 2026-06-17 - standard_peak_seed_guard_realdata_85raw_artifact_v1

- Previous tier: `production_candidate` for standard-path seed guard with synthetic/focused coverage and executable heldout-oracle CLI
- New tier: still `production_candidate`; real-data artifact evidence now covers seed guard/write attribution on one existing 85RAW chunk without rerunning RAW
- Evidence: `output/productization_realdata_seed_guard_85raw_20260617/r1_120_no_raw_productization/standard_peak_backfill_productization_summary.json`; `standard_peak_activation_inputs/seed_guard_decisions.tsv`; `activated_matrix/activation_value_delta.tsv`
- Product surface changed: none beyond the existing explicit productization bridge. The run reused `output/standard_peak_backfill_preset_85raw_20260610/alignment_preset_dna_dr_85raw_validation_minimal` pre-backfill matrix, identity, review, and chunk `r1_120` shadow projection; it did not open RAW files, rewrite workbook schema, or enable non-standard promotion.
- Validation: `uv run python -m tools.diagnostics.standard_peak_backfill_productization ... --source-run-id seed-guard-realdata-85raw-r1-120-20260617`; status `pass`; 2540 seed-guard candidate rows; 1160 `eligible_continue_existing_gates` rows; 1380 `blocked_low_seed_support` rows; `activation_value_delta.tsv` has 1160 rows and summary reports `matrix_cells_written=1160`.
- Remaining blocker at this checkpoint: production-ready still needed
  real/reviewed heldout oracle rows and a bounded expected-diff acceptance that
  explicitly approves the 85RAW product value changes. Later high-signal clean
  heldout trace evidence narrows, but does not remove, the broad activation
  scope blocker.

### 2026-06-17 - standard_peak_seed_guard_realdata_85raw_consolidated_no_raw_v1

- Previous tier: `production_candidate` for standard-path seed guard with synthetic/focused coverage and one existing 85RAW chunk no-RAW bridge
- New tier: still `production_candidate`; real-data artifact evidence now covers seed guard/write attribution on the existing 85RAW consolidated shadow projection without rerunning RAW
- Evidence: `output/productization_realdata_seed_guard_85raw_20260617/consolidated_no_raw_productization/standard_peak_backfill_productization_summary.json`; `standard_peak_activation_inputs/seed_guard_decisions.tsv`; `activated_matrix/activation_value_delta.tsv`
- Product surface changed: none beyond the existing explicit productization bridge. The run reused `output/standard_peak_backfill_preset_85raw_20260610/alignment_preset_dna_dr_85raw_validation_minimal/standard_peak_backfill_preset/consolidated/consolidated_shadow_projection_cells.tsv` plus pre-standard-backfill matrix/identity inputs; it did not open RAW files, rewrite workbook schema, or enable non-standard promotion.
- Validation: `uv run python -m tools.diagnostics.standard_peak_backfill_productization ... --source-run-id seed-guard-realdata-85raw-consolidated-20260617`; elapsed about 6.93 s; status `pass`; 7307 seed-guard candidate rows; 4613 `eligible_continue_existing_gates` rows; 2694 `blocked_low_seed_support` rows; `activation_value_delta.tsv` has 4613 rows and summary reports `matrix_cells_written=4613`; `write_authority_status` counts are 4613 `cohort_scale_standard_backfill` and 2694 `no_write`, with zero `blocked_unattributed_write`. Subagent reviewer `Popper` found no blocking issue and confirmed the docs keep this as `production_candidate` evidence, not `production_ready` or reviewed-oracle evidence.
- Remaining blocker at this checkpoint: production-ready still needed
  real/reviewed heldout oracle rows and a bounded expected-diff acceptance that
  explicitly approves the 85RAW product value changes. Later high-signal clean
  heldout trace evidence narrows, but does not remove, the broad activation
  scope blocker.

### 2026-06-17 - standard_peak_heldout_oracle_source_audit_v1

- Previous tier: `production_candidate` for standard-path seed guard with no-RAW 85RAW consolidated evidence
- New tier: still `production_candidate`; `production_ready` checkpoint is explicitly blocked on independent observed boundary evidence
- Evidence: `output/productization_realdata_seed_guard_85raw_20260617/heldout_oracle_source_audit/summary.json`; `raw85_manual_verdict_seed_guard_crosswalk.tsv`; source manual verdicts under `output/backfill_peakhypothesis_promotion_8raw_20260608/raw85_hypothesis_manual_review_top14_user_standard/`
- Product surface changed: none. This is a source audit only; it did not open RAW, generate heldout oracle manifest/results, mutate matrices, or promote non-standard peaks.
- Validation: no existing `heldout_oracle_manifest.tsv`, observed oracle TSV, or `heldout_oracle_results.tsv` was found under `output/`. The audit reviewed 11 raw85 manual verdict rows and 11 matching review-queue rows: all 11 have oracle boundary/area source values, but only 2 match current consolidated seed-guard candidate keys; those 2 have observed area through `activation_value_delta.tsv` but lack an independent observed start/end boundary artifact. The remaining 9 rows do not match the current seed-guard candidate keys.
- Remaining blocker: provide or generate `observed_start_rt`, `observed_end_rt`, and `observed_area` for matched reviewed cases from an independent implementation result source; the observed-result provenance contract is defined in the following log entry and must be satisfied before the oracle gate can count for production readiness.

### 2026-06-17 - standard_peak_heldout_oracle_observed_provenance_contract_v1

- Previous tier: `production_candidate` for standard-path seed guard with no-RAW 85RAW consolidated evidence and source-audit blocker
- New tier: still `production_candidate`; observed-result contract gap is closed.
  At this checkpoint no reviewed observed rows had been generated yet; later
  `standard_peak_heldout_trace_reintegration_oracle_v1` supplies a high-signal
  clean independent reintegration slice.
- Evidence: `xic_extractor.diagnostics.standard_peak_shadow_activation_inputs`; `tools/diagnostics/standard_peak_heldout_oracle_results.py`; `tests/test_standard_peak_shadow_activation_inputs.py`; `docs/superpowers/specs/2026-06-13-backfill-integration-policy-spec.md`
- Product surface changed: `heldout_observed_results.tsv` now requires observed provenance columns: `observed_result_source`, `observed_boundary_source`, `observed_area_source`, and `observed_independence_basis`. Allowed independence bases are `product_writer_observed_result`, `masked_rerun_observed_result`, and `independent_boundary_reintegration_result`; oracle/manual/review-queue source copies fail closed after source-label canonicalization. `heldout_oracle_results.tsv` now carries those provenance columns forward for auditability, and `result_source_artifact_path` must exist so the output SHA cannot be blank. No RAW, matrix writer, workbook schema, default extraction, or non-standard peak policy changed.
- Validation: red/green focused tests proved missing provenance, oracle/manual/review-queue source-copy variants, and missing result-source artifact rows failed after implementation; `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests\test_standard_peak_shadow_activation_inputs.py -k heldout_oracle -q` (`20 passed` at that checkpoint; later `25 passed` after original-cell-status and source-cross-check guards); `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests\test_standard_peak_shadow_activation_inputs.py tests\test_standard_peak_backfill_productization.py -q` (`37 passed` at that checkpoint; later `42 passed` after the same guards); latest full local gate after the source-cross-check guard also passed: ruff, mypy, `pytest -v --tb=short -x` (`3698 passed, 1 skipped`), diagnostics index, and `git diff --check` with LF/CRLF warnings only. Subagent reviewer `Gibbs` found the source-label and missing-artifact gaps; both were fixed.
- Remaining blocker: production-ready still needs observed start/end/area rows for reviewed heldout cases from an allowed independent source, plus bounded 85RAW expected-diff approval.

### 2026-06-17 - standard_peak_heldout_original_detected_guard_v1

- Previous tier: `production_candidate` for standard-path seed guard with observed-result provenance contract
- New tier: still `production_candidate`; invalid reviewed/rescued rows are now blocked from serving as heldout oracle product-readiness evidence
- Evidence: `xic_extractor.diagnostics.standard_peak_shadow_activation_inputs`; `tests/test_standard_peak_shadow_activation_inputs.py`; `docs/superpowers/specs/2026-06-13-backfill-integration-policy-spec.md`; exploratory read of existing trace artifacts for `FAM002634 / Breast_Cancer_Tissue_pooled_QC3` and `FAM017068 / Breast_Cancer_Tissue_pooled_QC5`
- Product surface changed: `heldout_oracle_manifest.tsv` now requires `heldout_original_cell_status`. Accepted values are `detected`, `detected_seed`, `quantifiable_detected`, and `accepted_detected`; `rescued` and unknown statuses fail before result evaluation. No RAW, matrix writer, workbook schema, default extraction, or non-standard peak policy changed.
- Validation: red/green focused test `test_standard_peak_heldout_oracle_results_requires_original_detected_cell_status`; `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests\test_standard_peak_shadow_activation_inputs.py -k heldout_oracle -q` (`21 passed` at that checkpoint; later `25 passed` after the observed-source cross-check guard); `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests\test_standard_peak_shadow_activation_inputs.py tests\test_standard_peak_backfill_productization.py -q` (`38 passed` at that checkpoint; later `42 passed` after the observed-source cross-check guard)
- Remaining blocker at this checkpoint: production-ready needed true originally
  detected heldout cases, not the current two matched reviewed rows, plus
  independent observed start/end/area rows and bounded 85RAW expected-diff
  approval. Later high-signal clean heldout trace evidence supplies that slice;
  broad activation still needs scope/expected-diff acceptance.

### 2026-06-17 - standard_peak_heldout_observed_source_crosscheck_v1

- Previous tier: `production_candidate` for standard-path seed guard with observed-result provenance and original-cell-status guard
- New tier: still `production_candidate`; the heldout oracle gate is harder to
  spoof. At this checkpoint the valid observed heldout artifact was still
  pending; later `standard_peak_heldout_trace_reintegration_oracle_v1` supplies
  a high-signal clean independent reintegration slice.
- Evidence: subagent reviewer `Ptolemy` found that neutral observed source labels could still copy the manifest `oracle_source`; fix landed in `xic_extractor.diagnostics.standard_peak_shadow_activation_inputs` plus tests
- Product surface changed: fail-closed validation only. Observed provenance source labels are still additive TSV inputs, but now each observed row is validated against its matching manifest row and `observed_result_source`, `observed_boundary_source`, or `observed_area_source` cannot canonicalize to the same label as manifest `oracle_source`. Source-label canonicalization also collapses repeated punctuation/whitespace separators. No RAW, matrix writer, workbook schema, default extraction, or non-standard peak policy changed.
- Validation: red/green neutral oracle-source self-copy test; original-cell-status allowlist/blank/unknown coverage; `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests\test_standard_peak_shadow_activation_inputs.py -k heldout_oracle -q` (`25 passed`); `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests\test_standard_peak_shadow_activation_inputs.py tests\test_standard_peak_backfill_productization.py -q` (`42 passed`); touched-file ruff/mypy passed.
- Remaining blocker at this checkpoint: production-ready still needed true
  originally detected heldout cases with independent observed start/end/area
  rows and bounded 85RAW expected-diff approval. Later high-signal clean
  heldout trace evidence supplies that slice; broad activation still needs
  scope/expected-diff acceptance.

### 2026-06-17 - standard_peak_oracle_gate_review_hardening_v1

- Previous tier: `production_candidate` for standard-path seed guard with executable oracle gate and no-RAW 85RAW artifact bridge
- New tier: still `production_candidate`; review blockers were fixed without expanding product authority
- Evidence: subagent reviewer `Peirce` found heldout-oracle manifest schema enforcement gaps, duplicate/extra observed result ambiguity, and missing hard failure for `blocked_unattributed_write`; reviewer `Euclid` found a non-blocking schema-version value hardening gap; reviewer `Noether` found a package-evaluator direct-call required-column hardening gap. Fixes landed in `tools/diagnostics/standard_peak_heldout_oracle_results.py`, `xic_extractor.diagnostics.standard_peak_shadow_activation_inputs`, `xic_extractor.diagnostics.standard_peak_backfill_productization`, and focused tests.
- Product surface changed: fail-closed behavior only. Heldout oracle CLI and package evaluator now require the full spec manifest schema and manifest schema-version value, reject duplicate/stale observed oracle rows, and productization now reports `status=fail` if post-apply seed-guard attribution marks `blocked_unattributed_write`.
- Validation: new red/green tests plus `uv run pytest tests\test_standard_peak_shadow_activation_inputs.py tests\test_standard_peak_backfill_productization.py -q` (`27 passed` after tolerance-ceiling and exact-threshold tests); focused ruff/mypy passed; no-RAW 85RAW artifact bridge rerun still `pass` with 1160 writes and zero `blocked_unattributed_write`.
- Remaining blocker at this checkpoint: production-ready still needed
  real/reviewed heldout oracle rows and a bounded expected-diff acceptance that
  explicitly approves the 85RAW product value changes. Later high-signal clean
  heldout trace evidence narrows, but does not remove, the broad activation
  scope blocker.

### 2026-06-17 - product_decision_backfill_oracle_and_nlfail_limited_optin_v1

- Previous tier: `production_candidate` for standard-path seed guard and targeted MS1 shape explicit opt-in
- New tier: unchanged; product decisions accepted, runtime defaults not changed
- Evidence: user accepted Backfill heldout oracle first-gate tolerance of boundary error `<=0.1 min` and area relative error `<=10%`; user also accepted `NL_FAIL/NO_MS2` limited opt-in first scope as `5-hmdC + 5-medC` only, with product output limited to `detected_flagged`
- Product surface changed: docs/control-plane decision only. No default extraction, GUI rescue, matrix writer, workbook schema, or primary matrix behavior changed in this entry.
- Validation: docs-only decision record; prior gates remain `ruff`, `mypy`, full `pytest`, diagnostics index, `git diff --check`, and no-RAW 85RAW bridge.
- Remaining blocker: Backfill still needs real/reviewed heldout oracle rows generated under the accepted tolerance plus bounded 85RAW expected-diff approval. `NL_FAIL` limited opt-in still needs implementation evidence before it can be treated as no-flag default rescue.

### 2026-06-17 - standard_peak_oracle_tolerance_ceiling_v1

- Previous tier: `production_candidate` for standard-path seed guard and executable heldout oracle result gate
- New tier: still `production_candidate`; oracle manifest guard now enforces the accepted first-gate tolerance ceiling
- Evidence: `xic_extractor.diagnostics.standard_peak_shadow_activation_inputs`; `tests/test_standard_peak_shadow_activation_inputs.py`
- Product surface changed: fail-closed gate only. Heldout oracle manifest rows may specify stricter tolerance, but values looser than boundary error `0.1 min` or area relative error `0.10` now raise before result evaluation. No default extraction, matrix writer, workbook schema, or non-standard promotion changed.
- Validation: `uv run pytest tests\test_standard_peak_shadow_activation_inputs.py::test_standard_peak_heldout_oracle_results_rejects_loose_tolerances tests\test_standard_peak_shadow_activation_inputs.py::test_standard_peak_heldout_oracle_results_accepts_strict_tolerances -q` (`2 passed`); `uv run pytest tests\test_standard_peak_shadow_activation_inputs.py tests\test_standard_peak_backfill_productization.py -q` (`25 passed`)
- Remaining blocker at this checkpoint: production-ready still needed
  real/reviewed heldout oracle rows under this ceiling and bounded 85RAW
  expected-diff approval. Later high-signal clean heldout trace evidence
  narrows, but does not remove, the broad activation scope blocker.

### 2026-06-17 - standard_peak_oracle_exact_threshold_float_fix_v1

- Previous tier: `production_candidate` for standard-path seed guard and heldout oracle tolerance ceiling
- New tier: still `production_candidate`; subagent review blocker fixed
- Evidence: reviewer `Linnaeus` identified exact-threshold float comparison risk; `xic_extractor.diagnostics.standard_peak_shadow_activation_inputs`; `tests/test_standard_peak_shadow_activation_inputs.py`
- Product surface changed: comparison helper only. Mathematically exact boundary error `0.1 min` and area relative error `0.10` are now accepted despite binary float representation; values meaningfully above the ceiling still fail. No runtime default, matrix writer, workbook schema, or non-standard promotion changed.
- Validation: exact-boundary tests `2 passed`; `uv run pytest tests\test_standard_peak_shadow_activation_inputs.py tests\test_standard_peak_backfill_productization.py -q` (`27 passed`)
- Remaining blocker at this checkpoint: production-ready still needed
  real/reviewed heldout oracle rows under this ceiling and bounded 85RAW
  expected-diff approval. Later high-signal clean heldout trace evidence
  narrows, but does not remove, the broad activation scope blocker.

### 2026-06-17 - standard_peak_heldout_trace_reintegration_oracle_v1

- Previous tier: `production_candidate` for broad standard-path seed guard with
  an executable heldout oracle gate but no valid originally detected observed
  rows.
- New tier: still `production_candidate` for broad standard-path activation;
  bounded high-signal clean standard trace heldout oracle evidence now passes.
- Evidence:
  `output/productization_realdata_seed_guard_85raw_20260617/heldout_trace_reintegration_oracle/summary.json`;
  `heldout_oracle_manifest.tsv`; `heldout_observed_results.tsv`;
  `heldout_oracle_results.tsv`;
  `heldout_trace_reintegration_full_eligible_pool.tsv`; source 85RAW
  validation-minimal trace/evidence artifacts under
  `output/standard_peak_backfill_preset_85raw_20260610/alignment_preset_dna_dr_85raw_validation_minimal/`.
- Product surface changed: none. The artifact reuses existing stored 85RAW trace
  arrays and existing package helpers (`find_peak_and_area` with
  `resolver_mode=local_minimum`, `integration_from_peak_trace` with AsLS /
  gaussian15 morphology area). It does not open RAW, mutate matrices, rewrite
  workbook schema, enable default rescue, or authorize non-standard promotion.
- Validation: deterministic selection produced 20 originally detected,
  sample-local, high-signal clean standard trace cases across 20 families
  (`cell_height>=2e6`, width 0.30-0.65 min, shape similarity >=0.95,
  local/global max ratio >=0.95, apex within 0.15 min of family center, at
  least 10 scans, one case per family). The formal heldout oracle CLI wrote
  20 rows; all 20 have `oracle_case_status=pass` and
  `included_in_product_acceptance=TRUE`. Maximum boundary error is 0.0820502
  min and maximum area relative error is 0.0762325, inside the accepted
  `0.1 min / 10% area` ceiling. The full eligible pool artifact persists all
  80 pre-observed eligible rows with quality rank, selected flag, and rejection
  reason; unselected rows do not carry observed reintegration outcomes.
- Remaining blocker: this evidence supports only the high-signal clean standard
  trace slice. The existing consolidated productization bridge still emits
  4613 eligible activation writes and is not scoped by those high-signal clean
  eligibility thresholds. To claim broad `production_ready`, either narrow the
  activation contract to this eligible scope and run an expected-diff
  acceptance, or generate a broader masked/product-writer observed oracle that
  covers the full activation scope.

### 2026-06-17 - standard_peak_activation_scope_audit_v1

- Previous tier: `production_candidate` for broad standard-path seed guard with
  passing high-signal clean heldout trace oracle, but no quantified bridge from
  that oracle envelope to the actual consolidated activation writes.
- New tier: still `production_candidate` for broad 4613-row standard-path
  activation; explicit high-signal clean scoped activation is now a bounded
  product-decision candidate, not an implicit broad ready claim.
- Evidence:
  `tools/diagnostics/standard_peak_activation_scope_audit.py`;
  `xic_extractor/diagnostics/standard_peak_activation_scope_audit.py`;
  `output/productization_realdata_seed_guard_85raw_20260617/high_signal_clean_activation_scope_audit/activation_high_signal_clean_scope_summary.json`;
  `activation_high_signal_clean_scope_audit.tsv`;
  `eligible_activation_value_delta.tsv`.
- Product surface changed: none. The audit reads existing
  `activation_value_delta.tsv`, consolidated
  `consolidated_shadow_projection_cells.tsv`, and sibling
  `*_trace_data.json` artifacts. It does not open RAW, mutate matrices, rewrite
  workbooks, change default extraction, or enable non-standard promotion.
- Validation: focused TDD test
  `uv run pytest tests\test_standard_peak_activation_scope_audit.py -q`
  passed. The real no-RAW audit found 4613 written activation rows, all joined
  to projection rows; 3526 joined to trace JSON, 1087 had missing overlay path,
  72 were high-signal clean eligible, 3454 were trace-matched but outside the
  high-signal clean envelope, and broad scope status is `not_ready`.
- Remaining blocker: choosing the first release product scope. To claim
  `production_ready`, either make the activation contract explicitly write only
  the 72 high-signal-clean eligible rows and run expected-diff acceptance, or
  produce a broader masked/product-writer observed oracle for the full 4613-row
  activation scope.
- Next checkpoint: ask the product-scope decision before changing matrix-writing
  behavior; do not silently convert the 4613-row broad bridge into a 72-row
  product output.

### 2026-06-17 - standard_peak_narrow_expected_diff_acceptance_v1

- Previous tier: `production_candidate` for broad standard-path seed guard;
  high-signal-clean 72-row subset was quantified but did not yet have a
  delta-level expected-diff acceptance gate.
- New tier: still `production_candidate` for broad 4613-row standard-path
  activation. The 72-row high-signal-clean subset now has passing narrow
  expected-diff acceptance, but it is not product output until a writer contract
  explicitly limits activation to that scope.
- Evidence:
  `output/productization_realdata_seed_guard_85raw_20260617/high_signal_clean_activation_scope_audit/narrow_activation_expected_diff_acceptance.json`;
  `narrow_activation_expected_diff_acceptance.tsv`;
  `eligible_activation_value_delta.tsv`.
- Product surface changed: none. The gate reads existing activation delta,
  scope audit, and filtered eligible delta. It writes only diagnostic acceptance
  artifacts and records `product_surface_changed=FALSE`.
- Validation: focused tests
  `uv run pytest tests\test_standard_peak_activation_scope_audit.py -q` now
  pass 5 tests, including provenance-SHA join and fail-closed non-eligible
  delta coverage. Real no-RAW acceptance on the 85RAW consolidated artifact
  reports `acceptance_status=pass`, `full_written_delta_row_count=4613`,
  `eligible_audit_row_count=72`, `eligible_delta_row_count=72`,
  `duplicate_delta_key_count=0`, `missing_delta_row_count=0`,
  `unexpected_delta_row_count=0`, `non_eligible_delta_row_count=0`,
  `not_written_delta_row_count=0`, `unchanged_delta_row_count=0`, and
  `blank_activated_value_count=0`. Closeout gates also passed:
  `uv run ruff check xic_extractor tests tools scripts`,
  `uv run mypy xic_extractor` (`343 source files`),
  `uv run pytest -v --tb=short -x` (`3704 passed, 1 skipped`),
  `uv run python scripts\check_diagnostics_index.py` (`87 entry points, 166
  total files`), and `git diff --check` with only LF/CRLF warnings.
- Remaining blocker: product-scope decision and writer contract. If the first
  release uses the 72-row scope, the writer must be explicitly narrowed and
  gated before any formal matrix output is produced. If the release uses broad
  4613-row scope, this acceptance is insufficient and a broader oracle is still
  required.
- Next checkpoint: choose narrow writer contract versus broad oracle. Do not
  rerun RAW unless it will decide that checkpoint.

### 2026-06-17 - standard_peak_narrow_product_writer_v1

- Previous tier: 72-row high-signal-clean Backfill subset had passing
  delta-level expected-diff acceptance, but no product writer was limited to
  that scope. Broad 4613-row standard-path activation remained
  `production_candidate`.
- New tier: `production_ready` for the explicit 72-row high-signal-clean scoped
  writer; broad 4613-row standard-path activation remains
  `production_candidate`.
- Evidence:
  `output/productization_realdata_seed_guard_85raw_20260617/narrow_high_signal_clean_no_raw_productization/standard_peak_backfill_productization_summary.json`;
  `narrow_product_writer_expected_diff_acceptance.json`;
  `activated_matrix/activation_value_delta.tsv`.
- Product surface changed: additive opt-in CLI surface
  `standard_peak_backfill_productization.py --high-signal-clean-activation-scope-audit-tsv`.
  It filters productization input to audit rows with
  `high_signal_clean_status=eligible`, then writes the existing matrix-only
  activated-matrix output under the task output directory. It does not change
  default extraction, workbook schema, GUI behavior, non-standard promotion, or
  the broad activation bridge. The additive summary fields bump the
  productization summary schema to `standard_peak_backfill_productization_v1`;
  reviewer `Mill` found the missing schema bump as P2, and the fix was verified
  with a focused schema assertion plus a rerun of the narrow no-RAW artifact.
- Validation: focused tests
  `uv run pytest tests\test_standard_peak_activation_scope_audit.py tests\test_standard_peak_backfill_productization.py -q`
  passed 10 tests at implementation checkpoint. Touched-file ruff and mypy
  passed. The real no-RAW 85RAW consolidated artifact run selected 72 eligible
  shadow rows, wrote 72 matrix cells and 72 activation-delta rows, and
  `narrow_product_writer_expected_diff_acceptance.json` reports
  `acceptance_status=pass`, `readiness_tier=production_ready`,
  `eligible_audit_row_count=72`, `product_written_delta_row_count=72`,
  `duplicate_delta_key_count=0`, `missing_delta_row_count=0`,
  `unexpected_delta_row_count=0`, `non_eligible_delta_row_count=0`,
  `not_written_delta_row_count=0`, `unchanged_delta_row_count=0`, and
  `blank_activated_value_count=0`.
- Remaining blocker: none for the 72-row narrow release slice. Broad 4613-row
  activation still needs broader masked/product-writer observed oracle evidence
  before it can claim `production_ready`.
- Next checkpoint: preserve the 72-row scope as an explicit release claim; do
  not broaden the writer without a new expected-diff/oracle packet.

### 2026-06-17 - standard_peak_low_scan_trace_oracle_v1

- Previous tier: broad 4613-row Backfill activation remained
  `production_candidate`; 72-row high-signal clean scoped writer was
  `production_ready`.
- New tier: still `production_candidate` for broad activation; low-scan clean
  trace evidence now has a passing held-out oracle packet.
- Evidence:
  `xic_extractor/diagnostics/standard_peak_heldout_trace_oracle.py`;
  `tools/diagnostics/standard_peak_heldout_trace_oracle.py`;
  `output/productization_realdata_seed_guard_85raw_20260617/heldout_trace_reintegration_oracle_low_scan_clean_probe/summary.json`;
  `heldout_oracle_results.tsv`.
- Product surface changed: additive diagnostic CLI that builds reproducible
  held-out trace oracle packets from existing detected cell evidence and stored
  trace JSON. It does not open RAW, mutate matrices, change workbook schema,
  authorize non-standard peaks, or broaden the Backfill writer by itself.
- Validation: focused test
  `uv run pytest tests\test_standard_peak_heldout_trace_oracle.py -q`
  passed. The real no-RAW 85RAW low-scan run found 56 eligible candidates
  across 11 families, selected 11 cases, and `heldout_oracle_results.tsv`
  reports 11/11 `pass`, 11/11 `included_in_product_acceptance=TRUE`, max
  boundary error `4.86717e-05` min, and max area relative error `0.038786`
  under the accepted `0.1 min / 10% area` ceiling.
- Remaining blocker: this oracle only supports the explicit low-scan clean
  trace class; a writer scope and expected-diff packet are still required
  before product claims.
- Next checkpoint: connect low-scan clean eligibility to activation scope audit
  and a scoped product writer.

### 2026-06-17 - standard_peak_low_scan_scoped_writer_v1

- Previous tier: low-scan clean Backfill trace class had a passing held-out
  oracle but no product writer limited to that scope.
- New tier: `production_ready` for the explicit 42-row low-scan-clean scoped
  writer; broad 4613-row standard-path activation remains
  `production_candidate`.
- Evidence:
  `output/productization_realdata_seed_guard_85raw_20260617/high_signal_clean_activation_scope_audit/activation_high_signal_clean_scope_summary.json`;
  `low_scan_clean_activation_expected_diff_acceptance.json`;
  `output/productization_realdata_seed_guard_85raw_20260617/narrow_low_scan_clean_no_raw_productization/standard_peak_backfill_productization_summary.json`;
  `narrow_product_writer_expected_diff_acceptance.json`;
  `activated_matrix/activation_value_delta.tsv`.
- Product surface changed: additive opt-in CLI surface
  `standard_peak_backfill_productization.py --low-scan-clean-activation-scope-audit-tsv`.
  It filters productization input to audit rows with
  `low_scan_clean_status=eligible` and writes the existing matrix-only
  activated-matrix output under the task output directory. Only one scoped
  audit flag may be supplied at a time. No default extraction, workbook schema,
  GUI behavior, non-standard promotion, or broad activation bridge changed.
- Validation: focused tests
  `uv run pytest tests\test_standard_peak_activation_scope_audit.py tests\test_standard_peak_backfill_productization.py tests\test_standard_peak_heldout_trace_oracle.py -q`
  passed 19 tests after fail-closed scope hardening; touched-file ruff/mypy
  passed. The real combined-scope
  audit found 42 low-scan clean eligible writes out of 4613 and
  `low_scan_clean_activation_expected_diff_acceptance.json` reports
  `acceptance_status=pass`, 42/42 eligible rows, and zero duplicate, missing,
  unexpected, non-eligible, non-written, unchanged, or blank-value rows. The
  real no-RAW scoped writer selected 42 shadow rows, wrote 42 matrix cells and
  42 activation-delta rows, and `narrow_product_writer_expected_diff_acceptance.json`
  reports `acceptance_status=pass`, `readiness_tier=production_ready`,
  `expected_scope=low_scan_clean_eligible_activation_rows`, and zero blockers.
- Remaining blocker: none for the explicit 42-row low-scan release slice. Broad
  4613-row activation still needs additional named evidence classes and
  expected-diff approval before broad `production_ready`.
- Next checkpoint: later low-height, apex-delta, and width-only probes all
  failed closed, so do not add writers for those classes. The next broadening
  step needs a narrower explainable rule or failure-family split before another
  scoped writer can be justified.

### 2026-06-17 - standard_peak_low_scan_review_fix_v1

- Previous tier: explicit 42-row low-scan-clean scoped writer was
  `production_ready`, with broad 4613-row standard-path activation still
  `production_candidate`.
- New tier: unchanged; the 42-row low-scan-clean scoped writer remains
  `production_ready`, and broad 4613-row activation remains
  `production_candidate`.
- Evidence: subagent reviewers found no P1/P2 issue. Review feedback identified
  P3 docs drift where the control-plane intro and spec residual-blocker text
  still emphasized only the 72-row high-signal slice. The docs now explicitly
  name both release-ready slices: 72-row high-signal clean and 42-row low-scan
  clean. Focused tests now cover the low-scan scope writer's fail-closed paths:
  multiple scope audit flags, no eligible low-scan rows, duplicate eligible
  audit SHA, audit SHA missing from shadow projection, and duplicate shadow
  projection SHA.
- Product surface changed: none. This is docs/test hardening only; no default
  extraction, workbook schema, GUI behavior, non-standard promotion, matrix
  identity, selected peak, selected area, or broad activation behavior changed.
- Validation: `uv run pytest tests\test_standard_peak_activation_scope_audit.py tests\test_standard_peak_backfill_productization.py tests\test_standard_peak_heldout_trace_oracle.py -q`
  (`19 passed`); `uv run ruff check xic_extractor tests tools scripts`
  (pass); `uv run mypy xic_extractor` (pass, 346 source files);
  `uv run pytest -v --tb=short -x` (`3721 passed, 1 skipped`);
  `uv run python scripts\check_diagnostics_index.py`
  (`88 entry points, 167 total files`); `git diff --check` (no whitespace
  errors; Windows LF/CRLF warnings only).
- Remaining blocker: none for the explicit 42-row low-scan release slice. Broad
  4613-row activation still needs additional named evidence classes and
  expected-diff approval before broad `production_ready`.
- Next checkpoint: choose one additional evidence-sufficient class, produce or
  reuse a matching held-out oracle packet, then connect it through activation
  scope audit and scoped writer expected-diff before adding more automatic
  writes.

### 2026-06-17 - standard_peak_low_height_probe_v1

- Lane: Backfill product-authority sidecars /
  `backfill_standard_seed_guard_scope_v1`.
- Previous tier: broad 4613-row standard-path activation remained
  `production_candidate`; the next proposed single-blocker class was
  height-only or apex-delta-only.
- New tier: low-height clean is `production_candidate` only. The explicit
  72-row high-signal-clean and 42-row low-scan-clean scoped writers remain
  `production_ready`; broad 4613-row activation remains `production_candidate`.
- Evidence:
  `tools/diagnostics/standard_peak_heldout_trace_oracle.py` now accepts
  `--target-shape-class standard_low_height_clean_trace`, where all clean
  thresholds remain in force except cell height must be below `2e6`.
  The no-RAW 85RAW heldout packet under
  `output/productization_realdata_seed_guard_85raw_20260617/heldout_trace_reintegration_oracle_low_height_clean_probe/`
  found 230 eligible candidate rows across 54 families and selected 20
  family-representative cases. It failed closed with 19/20 pass and one
  `fail_boundary` case:
  `HOLDOUT85TRACE001_FAM008651_TumorBC2312_DNA`, boundary error
  `1.16445 min`, area relative error about `0.033`.
- Additional audit evidence:
  `standard_peak_activation_scope_audit.py` now writes
  `low_height_clean_activation_value_delta.tsv` and
  `low_height_clean_activation_expected_diff_acceptance.tsv/json`. The real
  combined audit found 57 low-height clean eligible writes out of 4613; the
  diagnostic expected-diff packet passed 57/57 with zero duplicate, missing,
  unexpected, non-eligible, non-written, unchanged, or blank rows, and
  `product_surface_changed=FALSE`.
- Product surface changed: no matrix writer was added for low-height; no
  default extraction behavior, workbook schema, GUI behavior, non-standard
  promotion, matrix identity, selected peak, selected area, or broad activation
  behavior changed.
- Review: subagent reviewers `Jason` and `Volta` found no P1/P2 blockers. P3
  docs/index wording and CLI labeling gaps were fixed so low-height is visibly
  diagnostic/candidate-only and not product writer approval.
- Validation:
  `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests\test_standard_peak_heldout_trace_oracle.py tests\test_standard_peak_activation_scope_audit.py tests\test_standard_peak_backfill_productization.py -q`
  (`22 passed`); `$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor tests tools scripts`
  (pass); `$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor` (pass,
  346 source files); `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -v --tb=short -x`
  (`3724 passed, 1 skipped`);
  `$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts\check_diagnostics_index.py`
  (`88 entry points, 167 total files`); `git diff --check` (no whitespace
  errors; Windows LF/CRLF warnings only). The no-RAW heldout oracle command
  exited `1` by design because the summary status is `fail`; the activation
  scope audit rerun exited `0` and emitted the 57-row expected-diff packet
  above.
- Remaining blocker: low-height cannot be promoted to `production_ready` until
  the 19/20 heldout failure is explained by a narrower fail-closed evidence
  rule or a new accepted oracle packet passes the `0.1 min / 10% area` gate.
- Next checkpoint: apex-delta and width-only were evaluated after this entry and
  also failed closed. Treat low-height as candidate-only unless a narrower
  fail-closed rule explains the failed boundary case and passes a new oracle.

### 2026-06-17 - standard_peak_apex_delta_probe_v1

- Lane: Backfill product-authority sidecars /
  `backfill_standard_seed_guard_scope_v1`.
- Previous tier: broad 4613-row standard-path activation remained
  `production_candidate`; apex-delta-only was the next small single-blocker
  class after low-height failed its oracle.
- New tier: apex-delta clean is `production_candidate` only. The explicit
  72-row high-signal-clean and 42-row low-scan-clean scoped writers remain
  `production_ready`; broad 4613-row activation remains `production_candidate`.
- Evidence:
  `tools/diagnostics/standard_peak_heldout_trace_oracle.py` now accepts
  `--target-shape-class standard_apex_delta_clean_trace`, where supported trace
  status, shape >=0.95, local/global >=0.95, height >=2e6, width 0.30-0.65 min,
  and at least 10 boundary scans remain required, but apex delta from family
  center must exceed 0.15 min. The no-RAW 85RAW heldout packet under
  `output/productization_realdata_seed_guard_85raw_20260617/heldout_trace_reintegration_oracle_apex_delta_clean_probe/`
  found 78 eligible candidate rows across 27 families and selected 20
  family-representative cases. It failed closed with 17/20 pass and three
  `fail_boundary` cases. Max boundary error was `2.19621 min`; max area
  relative error was `0.424518`.
- Product surface changed: no matrix writer was added for apex-delta; no
  activation scope audit columns, default extraction behavior, workbook schema,
  GUI behavior, non-standard promotion, matrix identity, selected peak,
  selected area, or broad activation behavior changed.
- Validation:
  `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests\test_standard_peak_heldout_trace_oracle.py -q`
  (`3 passed`); the no-RAW heldout oracle command exited `1` by design because
  the summary status is `fail`.
- Remaining blocker: apex-delta cannot be promoted to `production_ready` until
  a narrower fail-closed evidence rule or a new accepted oracle packet passes
  the `0.1 min / 10% area` gate. Current failures include apex deltas around
  `0.2493` and `0.273`, so a broad threshold-only promotion is not justified.
- Next checkpoint: do not add an apex-delta writer. Width-only was evaluated in
  the following entry and also failed its oracle; remaining single-blocker
  classes should be parked candidate-only unless a stronger evidence model
  exists.

### 2026-06-17 - standard_peak_width_probe_v1

- Lane: Backfill product-authority sidecars /
  `backfill_standard_seed_guard_scope_v1`.
- Previous tier: broad 4613-row standard-path activation remained
  `production_candidate`; width-only was the smallest remaining single-blocker
  class after low-height and apex-delta failed their oracles.
- New tier: width-only clean is `production_candidate` only. The explicit
  72-row high-signal-clean and 42-row low-scan-clean scoped writers remain
  `production_ready`; broad 4613-row activation remains `production_candidate`.
- Evidence:
  `tools/diagnostics/standard_peak_heldout_trace_oracle.py` now accepts
  `--target-shape-class standard_width_clean_trace`, where supported trace
  status, shape >=0.95, local/global >=0.95, height >=2e6, apex delta <=0.15
  min, and at least 10 boundary scans remain required, but boundary width must
  fall outside 0.30-0.65 min. The no-RAW 85RAW heldout packet under
  `output/productization_realdata_seed_guard_85raw_20260617/heldout_trace_reintegration_oracle_width_clean_probe/`
  found 4 eligible candidate rows across 3 families and selected 3
  family-representative cases. It failed closed with 1/3 pass, one `fail_area`
  case, and one `fail_boundary` case. Max boundary error was `1.86561 min`;
  max area relative error was `0.599229`.
- Product surface changed: no matrix writer was added for width-only; no
  activation scope audit columns, default extraction behavior, workbook schema,
  GUI behavior, non-standard promotion, matrix identity, selected peak,
  selected area, or broad activation behavior changed.
- Review: subagent reviewer `Ohm` found one P2 test-strength issue: the
  initial width-only test only locked the over-wide happy path and not the
  narrow-width branch, inclusive `0.30` / `0.65` boundaries, or dirty
  shape/local-global/height/apex/scan sentinels. This was fixed with a direct
  selector contract test. Subagent reviewer `Hubble` found no P1/P2
  docs/product-claim blocker.
- Validation:
  `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests\test_standard_peak_heldout_trace_oracle.py -q`
  (`5 passed`); `$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor tests tools scripts`
  (pass); `$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor` (pass,
  346 source files); `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -v --tb=short -x`
  (`3727 passed, 1 skipped`);
  `$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts\check_diagnostics_index.py`
  (`88 entry points, 167 total files`); `git diff --check` (no whitespace
  errors; Windows LF/CRLF warnings only). The no-RAW heldout oracle command
  exited `1` by design because the summary status is `fail`.
- Remaining blocker: width-only cannot be promoted to `production_ready` until
  a narrower fail-closed evidence rule or a new accepted oracle packet passes
  the `0.1 min / 10% area` gate. Current evidence is too weak for a writer
  because only one of three selected family cases passed.
- Next checkpoint: park low-height, apex-delta, and width-only as
  candidate-only. Do not add writers for these single-blocker classes without a
  stronger evidence model or a new passing oracle packet.

### 2026-06-17 - targeted_ms1_shape_identity_limited_policy_gate_v1

- Previous tier: `production_candidate` for explicit support-TSV workflow only; limited opt-in policy was accepted by user but still missing implementation gate
- New tier: `production_candidate` for explicit/limited opt-in support-TSV workflow; no-flag default rescue remains off
- Evidence: `targeted_ms1_shape_identity_activation_policy`; CLI flag `--targeted-ms1-shape-identity-activation-policy`; `xic_extractor.targeted_ms1_shape_identity_policy`; `xic_extractor.diagnostics.targeted_ms1_shape_identity_expected_diff`; `tools/diagnostics/targeted_ms1_shape_identity_expected_diff_gate.py`; existing 85RAW gate summary `output/ms1_shape_identity_generic_support_85raw_20260616/limited_default_expected_diff_gate_summary.tsv`
- Product surface changed: additive settings key, additive CLI override, manifest provenance field, and additive expected-diff gate. Replay mode rejects the new runtime override. Default settings stay `explicit_support_tsv`; no GUI, workbook schema, selected-candidate switch, manual boundary, or default automatic support producer changed.
- Safe behavior boundary: limited policy accepts supported rows only for `5-hmdC` and `5-medC`; expected-diff gate requires analyte `NL_FAIL` rows to move from `not_counted/FALSE` to `detected_flagged/TRUE` with `own_max_same_peak_support`; matrix diffs are limited to those target measurement columns and must have the same sample/target key set as the long-row diff.
- Validation: `uv run pytest tests\test_targeted_ms1_shape_identity_expected_diff_gate.py tests\test_extractor_run.py::test_run_limited_shape_identity_policy_without_support_tsv_keeps_output -q` (`7 passed`); existing 85RAW generic artifact gate rerun `pass` with 11 long-row changes and 66 matrix cells; checkpoint full local gate `ruff`, `mypy`, `pytest -v --tb=short -x` (`3693 passed, 1 skipped`), diagnostics index, and `git diff --check` passed. Latest repo full gate after the later Backfill source-cross-check guard is recorded above.
- Remaining blocker: production-ready/default behavior still needs a separate decision and evidence to auto-build or auto-consume supports during normal extraction; GUI remains out of scope; broader targets need their own expected-diff evidence.

### 2026-06-17 - targeted_ms1_shape_identity_support_keyset_gate_v1

- Previous tier: `production_candidate` for explicit/limited opt-in support-TSV workflow.
- New tier: `production_ready` for the headless explicit limited support-TSV workflow only; unflagged normal-extraction rescue remained `blocked` at this checkpoint.
- Evidence: `tools/diagnostics/targeted_ms1_shape_identity_expected_diff_gate.py` now requires `--support-tsv`; `xic_extractor.diagnostics.targeted_ms1_shape_identity_expected_diff` validates that accepted support TSV sample/target keys exactly match the long-row expected diff; the existing 85RAW generic support artifact still gates at 11 long rows and 66 matrix cells, with 11 supported support-TSV rows and target counts `5-hmdC=10;5-medC=1`.
- Product surface changed: additive CLI gate input and additive summary metrics (`support_tsv_supported_rows`, `support_tsv_target_counts`). No default settings, normal extraction behavior, GUI, workbook schema, selected candidate, area recompute, or target scope changed.
- Validation: `uv run pytest tests\test_targeted_ms1_shape_identity_expected_diff_gate.py -q` (`9 passed` after the later support-required hardening); no-RAW 85RAW artifact gate rerun with `--support-tsv output\ms1_shape_identity_generic_support_85raw_20260616\targeted_ms1_shape_identity_v0.tsv`, status `pass`, `long_changed_rows=11`, `matrix_changed_cells=66`, `support_tsv_supported_rows=11`; latest full local gate after support-required hardening passed with `ruff`, `mypy`, `pytest -v --tb=short -x` (`3707 passed, 1 skipped`), diagnostics index, and `git diff --check`.
- Remaining blocker: unflagged normal-extraction rescue still needed a separate activation/call-cost/product contract before support generation could run without an explicit auto/support flag. Broader targets beyond `5-hmdC + 5-medC` need separate expected-diff evidence.
- Next checkpoint: keep release wording to "headless explicit limited support-TSV workflow" for this entry; do not call no-flag default extraction, GUI, or broader target rescue production-ready.

### 2026-06-17 - targeted_ms1_shape_identity_default_rescue_blocker_audit_v1

- Previous tier: `blocked` for unflagged default `NL_FAIL` rescue; `production_ready` only for the headless explicit limited support-TSV workflow.
- New tier: still `blocked` for unflagged default rescue at this checkpoint; explicit limited support-TSV workflow remains `production_ready`.
- Evidence: user accepted the limited default product direction (`5-hmdC + 5-medC`, `detected_flagged` only), but at this checkpoint the implementation had no automatic support producer or default support input contract. Normal extraction consumed `targeted_ms1_shape_identity_support_tsv` only when explicitly configured, and default settings remained `explicit_support_tsv` with an empty support TSV. A later entry adds an explicit headless auto CLI, but no-flag default behavior remains separate.
- Product surface changed: docs/control-plane wording only. No default settings, normal extraction behavior, GUI, workbook schema, matrix identity, counted detection, selected candidate, or manual boundary behavior changed.
- Validation: focused gates rerun after the audit: `uv run pytest tests\test_targeted_ms1_shape_identity_expected_diff_gate.py -q` (`9 passed` after the later support-required hardening); `uv run pytest tests\test_standard_peak_backfill_productization.py -q` (`5 passed`); `uv run pytest tests\test_provisional_backfill_candidate_gate_cli.py -q` (`8 passed`); `uv run pytest tests\test_settings_new_fields.py tests\test_extractor_run.py::test_run_applies_targeted_ms1_shape_identity_support_tsv tests\test_extractor_run.py::test_run_limited_shape_identity_policy_without_support_tsv_keeps_output tests\test_run_extraction.py::test_cli_passes_targeted_ms1_shape_identity_support_override tests\test_run_extraction.py::test_cli_passes_targeted_ms1_shape_identity_activation_policy_override tests\test_run_extraction.py::test_cli_replay_rejects_targeted_ms1_shape_identity_support_override tests\test_run_extraction.py::test_cli_replay_rejects_targeted_ms1_shape_identity_activation_policy_override tests\test_targeted_ms1_shape_identity_projection.py -q` (`18 passed`); existing 85RAW generic support expected-diff gate rerun with `--support-tsv` still `pass`, 11 long rows, 66 matrix cells, 11 supported support rows.
- Remaining blocker: to promote no-flag default rescue, implement and review an activation/call-cost/default-UX contract for automatically producing or selecting support rows during normal extraction, then provide expected-diff evidence for that default path. Do not promote by merely changing the default activation policy.
- Next checkpoint: design no-flag default activation only if it can be bounded by foreground RAW cost, expected-diff evidence, and a user-readable activation packet.

### 2026-06-17 - targeted_ms1_shape_identity_support_tsv_required_gate_review_fix_v1

- Previous tier: `production_ready` for the headless explicit limited support-TSV workflow, but subagent reviewer `Cicero` found the CLI/package gate still allowed an output-only pass when `--support-tsv` was omitted.
- New tier: still `production_ready` for the same narrow workflow after fail-closed gate hardening; unflagged normal-extraction rescue remained `blocked` at this checkpoint.
- Evidence: `tools/diagnostics/targeted_ms1_shape_identity_expected_diff_gate.py --support-tsv` is now required; `xic_extractor.diagnostics.targeted_ms1_shape_identity_expected_diff` raises when support rows are missing, so the release gate cannot pass without proving support TSV key-set equality.
- Product surface changed: diagnostic gate contract tightened. No default settings, normal extraction behavior, GUI, workbook schema, matrix identity, counted detection, selected candidate, or manual boundary behavior changed.
- Validation: focused tests added for missing support rows and missing CLI `--support-tsv`; `uv run pytest tests\test_targeted_ms1_shape_identity_expected_diff_gate.py -q` (`9 passed`); focused `ruff` and `mypy` passed; existing 85RAW generic support expected-diff gate rerun with required `--support-tsv` still `pass`; full local gate passed with `ruff`, `mypy`, `pytest -v --tb=short -x` (`3707 passed, 1 skipped`), diagnostics index, and `git diff --check`.
- Remaining blocker: none for the explicit limited release gate. Unflagged normal-extraction rescue still needed a separate activation/call-cost/default-support contract at this checkpoint.
- Next checkpoint: keep any future output-only diff check under a separate `diagnostic_only` name if it is ever needed; do not share the production-ready gate pass wording.

### 2026-06-17 - targeted_ms1_shape_identity_support_tsv_required_spec_drift_fix_v1

- Previous tier: `production_ready` for the headless explicit limited support-TSV workflow after support-required gate hardening.
- New tier: unchanged; no product tier movement.
- Evidence: subagent reviewer `Dirac` found one P3 docs drift in `docs/superpowers/specs/2026-06-16-shared-target-untarget-peak-identity-spine-spec.md` where the gate still used old output-only support-gate wording.
- Product surface changed: docs wording only; the spec now says the gate requires the actual support TSV.
- Validation: `uv run pytest tests\test_targeted_ms1_shape_identity_expected_diff_gate.py -q` (`9 passed`); support-optional wording grep no longer finds Targeted MS1 support-TSV contract drift; `git diff --check` has only LF/CRLF warnings.
- Remaining blocker: none for this docs drift. Unflagged normal-extraction rescue remained blocked separately at this checkpoint.
- Next checkpoint: commit this checkpoint after staging only the reviewed 9-file productization diff.

### 2026-06-17 - targeted_ms1_shape_identity_auto_limited_cli_v1

- Previous tier: `blocked` for automatic `NL_FAIL/NO_MS2` rescue beyond explicit support TSV; `production_ready` only for headless explicit limited support-TSV workflow.
- New tier: `production_ready` for the headless auto-limited CLI workflow; at
  that checkpoint unflagged normal extraction and GUI rescue remained off.
- Evidence: new CLI flag `--targeted-ms1-shape-identity-auto-limited-default`; package support producer `xic_extractor.diagnostics.targeted_ms1_shape_identity_support_producer`; auto diff/gate helper `xic_extractor.diagnostics.targeted_ms1_shape_identity_auto_diff`; 8RAW auto smoke at `output/ms1_shape_identity_auto_limited_8raw_20260617/`; 85RAW auto smoke at `output/ms1_shape_identity_auto_limited_85raw_20260617/`; existing 85RAW no-RAW gate mirror at `output/ms1_shape_identity_auto_limited_existing_85raw_gate_20260617/`.
- Product surface changed: additive CLI flag and additive auto output artifact layout (`baseline/output`, `support/targeted_ms1_shape_identity_v0.tsv`, `final_unverified/output` staging before the gate, `final/output` only after the expected-diff gate passes, expected-diff summaries). At that checkpoint, default settings, no-flag extraction behavior, GUI, workbook schema, selected candidate, manual boundary, and broader target scope did not change.
- Safe behavior boundary: auto workflow always builds support only for `5-hmdC + 5-medC`, applies `limited_5hmdc_5medc_v1`, and fails closed through the same support-TSV key-set expected-diff gate. Accepted changes remain `not_counted/FALSE` to `detected_flagged/TRUE`; clean `detected` is not allowed.
- Validation: focused lint passed for changed files; focused tests passed (`tests/test_targeted_ms1_shape_identity_auto_diff.py`, support builder, projection, expected-diff gate, and new CLI auto tests; latest focused command reported `29 passed`). 8RAW auto real run passed with `1` support row, `1` long-row change, `6` matrix cells. Existing 85RAW artifact no-RAW auto diff gate passed with `11`/`66`. One foreground 85RAW auto run passed with `11` support rows, `11` long-row changes, `66` matrix cells, diagnostics SHA256 unchanged between baseline/final, and wall-clock `369.2 s`.
- Remaining blocker: none for headless limited auto CLI. At this checkpoint,
  broader targets still needed their own evidence, and making auto rescue run
  when the user provides no flag remained a separate product/default UX
  decision. The later `targeted_ms1_shape_identity_no_flag_default_v1` entry
  records that default decision and guard. GUI remains out of scope.
- Next checkpoint: after subagent review and full local gate, commit this slice. Do not rerun 85RAW again for this lane unless support production/projection/matrix semantics change.

### 2026-06-17 - targeted_ms1_shape_identity_auto_limited_review_fix_v1

- Previous tier: `production_ready` for headless auto-limited CLI, pending
  subagent review fixes.
- New tier: unchanged; review blockers fixed.
- Evidence: subagent reviewers found stale handoff wording and a CLI
  fail-closed gap where support/gate failures could traceback and leave
  product-shaped `final/output` CSVs before the expected-diff gate passed.
- Product surface changed: fail-closed CLI behavior only. The auto workflow now
  writes the second extraction to `final_unverified/output`, runs the support
  TSV expected-diff gate there, publishes to `final/output` only after pass, and
  writes the final method manifest after publish. Support/gate/schema failures
  return CLI exit code `2` with a concise stderr message and do not publish
  verified final output.
- Validation: focused auto CLI tests now include gate-failure clean error and
  unpublished-final assertions; targeted auto/support focused suite reports
  `30 passed`. Full local gate is recorded in the handoff after this entry.
- Remaining blocker: none for explicit headless auto-limited CLI. No-flag
  default extraction, GUI, and broader target rescue remain separate decisions.
- Next checkpoint: commit after final subagent acceptance and full local gate.

### 2026-06-17 - targeted_ms1_shape_identity_no_flag_default_v1

- Previous tier: `production_ready` for headless explicit support-TSV workflow
  and explicit auto-limited CLI; no-flag normal extraction remained blocked.
- New tier: `production_ready` for canonical no-flag headless normal CLI
  default, limited to `limited_5hmdc_5medc_v1`, `5-hmdC + 5-medC`, and
  `detected_flagged` product output. GUI and broader targets remain out of
  scope.
- Evidence: canonical settings defaults, `config/settings.example.csv`, and
  `CANONICAL_SETTINGS_DEFAULTS` now default
  `targeted_ms1_shape_identity_activation_policy` to
  `limited_5hmdc_5medc_v1`. `scripts/run_extraction.py` dispatches the same
  auto workflow when the effective config has this policy and no
  `targeted_ms1_shape_identity_support_tsv`; explicit support TSV or
  `explicit_support_tsv` keeps the old manual/normal path. The no-RAW 85RAW
  existing auto artifact gate was rerun at
  `output/ms1_shape_identity_default_no_flag_existing_85raw_gate_20260617/limited_default_expected_diff_gate_summary.tsv`
  and passed with `long_changed_rows=11`, `matrix_changed_cells=66`,
  `support_tsv_supported_rows=11`, `target_counts=5-hmdC=10;5-medC=1`, and
  `matrix_target_counts=5-hmdC=60;5-medC=6`.
- Product surface changed: canonical settings default and config/example
  default changed; no new workbook schema, GUI behavior, selected candidate,
  manual boundary, target scope, or expected-diff semantics changed. The
  default still publishes final output only after the support TSV key-set
  expected-diff gate passes.
- Validation: focused no-flag/default shard
  `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests\test_settings_new_fields.py tests\test_settings_section.py tests\test_run_extraction.py tests\test_extractor_run.py::test_run_applies_targeted_ms1_shape_identity_support_tsv tests\test_extractor_run.py::test_run_limited_shape_identity_policy_without_support_tsv_keeps_output tests\test_targeted_ms1_shape_identity_projection.py tests\test_targeted_ms1_shape_identity_expected_diff_gate.py tests\test_targeted_ms1_shape_identity_auto_diff.py -q`
  passed `65` tests after review fixes. Focused ruff for changed code/tests
  passed. Subagent reviewers `Kant` and `Socrates` found that manual
  `--targeted-ms1-shape-identity-support-tsv` could inherit the limited default
  instead of preserving the explicit path, and that docs still had stale
  no-flag blocked wording. Both findings were fixed before commit. Full local
  gate passed: `ruff check xic_extractor tests tools scripts`, `mypy
  xic_extractor`, `pytest -v --tb=short -x` (`3728 passed, 1 skipped`), and
  `python scripts\check_diagnostics_index.py`.
- Remaining blocker: none for headless no-flag limited default after final
  review/gate. GUI rescue and any target beyond `5-hmdC + 5-medC` still need
  separate expected-diff evidence and UX/product contract.
- Next checkpoint: commit this slice, then broaden Targeted MS1 only with
  separate evidence for more targets or continue Backfill broadening by named
  evidence class.

### 2026-06-17 - product_direction_low_manual_intervention_v1

- Previous tier: unchanged. Backfill narrow 72-row writer is
  `production_ready`; broad 4613-row standard-path activation remains
  `production_candidate`; headless Targeted MS1 auto-limited CLI is
  `production_ready`; ReviewAction selected-candidate/manual-boundary apply
  remains parked for this release claim.
- New tier: unchanged; this entry records product direction, not a new behavior
  promotion.
- Evidence: user decision on 2026-06-17: Backfill north star is to fill whenever
  evidence is sufficient, with the 72-row writer as a demonstrator rather than
  a permanent scope cap; `NL_FAIL` limited rescue should move toward automatic
  low-manual operation, initially `5-hmdC + 5-medC` and `detected_flagged`
  only; ReviewAction/reintegration should eventually minimize manual review,
  with the system responsible for alertness and auditability while the user
  reviews only a small number of obvious/representative cases.
- Product surface changed: docs/control-plane wording only. The later
  `targeted_ms1_shape_identity_no_flag_default_v1` entry changes headless
  no-flag CLI default behavior under the bounded `limited_5hmdc_5medc_v1`
  contract; this direction entry itself does not change GUI wiring, workbook
  schema, matrix schema, selected-candidate switch, manual boundary area
  recompute, or broad Backfill write scope.
- Remaining blocker: broad Backfill still needs broader masked/product-writer
  oracle and expected-diff evidence for any added writes beyond the current
  scoped ready slices. Headless no-flag `NL_FAIL` limited rescue is now covered
  by `targeted_ms1_shape_identity_no_flag_default_v1`; GUI rescue and targets
  beyond `5-hmdC + 5-medC` still need separate expected-diff evidence and UX
  contract. ReviewAction mutation still needs stable IDs, sidecar contracts,
  expected-diff approval, and audited apply output before it can write selected
  peak/area/counting changes.
- Next checkpoint: prioritize bounded automation packets that reduce manual
  review without broad silent writes: broaden Backfill evidence by evidence
  class, extend Targeted MS1 only after separate evidence for more targets, and
  reopen ReviewAction mutation only after the ID/expected-diff contract is
  concrete.

### 2026-06-17 - provisional_production_candidate_gate_guard_audit_v1

- Previous tier: `diagnostic_only` with wording/no-promotion guard listed as next checkpoint.
- New tier: still `diagnostic_only`, now recorded as guarded; no product tier promotion.
- Evidence: existing CLI contract in `tools/diagnostics/provisional_backfill_candidate_gate.py` writes `alignment_production_candidate_gate.tsv/json` only; `tests/test_provisional_backfill_candidate_gate_cli.py` verifies the source matrix hash is unchanged and summary fields stay `readiness_label=diagnostic_only`, `production_ready=false`, and `matrix_contract_changed=false`.
- Product surface changed: docs/control-plane wording only. No CLI/schema/output behavior changed in this round.
- Validation: covered by full local gate `pytest -v --tb=short -x` (`3705 passed, 1 skipped`) plus `ruff`, `mypy`, diagnostics index, and `git diff --check`.
- Remaining blocker: none for diagnostic-only guard status. Any future rename is UX cleanup, not a product promotion.
- Next checkpoint: do not consume `alignment_production_candidate_gate.tsv` as product authority without a separate activation contract and expected-diff gate.

### 2026-06-16 - method_manifest_artifact_replay_policy_v1

- Previous tier: `production_ready` for targeted CLI replay parity, with ambiguous full-artifact wording
- New tier: `production_ready` for targeted CLI replay parity with explicit artifact policy; not full byte-exact workbook replay
- Evidence: `xic_extractor.output.method_manifest`; `tests/test_method_manifest.py`; `tests/test_workbook_compare.py`
- Product surface changed: additive `artifact_replay_policy` block in `method_manifest.json`.
- Safe behavior boundary: CSV artifacts are byte-exact replay artifacts; timestamped workbook parity is normalized through `scripts.compare_workbooks`; `method_manifest.json` is provenance-only because each run emits a new manifest.
- Validation: `python -m pytest tests\test_method_manifest.py tests\test_workbook_compare.py -q`
- Remaining blocker: full byte-exact workbook hash replay remains intentionally out of scope unless a future release needs stable workbook file identity.

### 2026-06-15 - alignment_output_contract_v1

- Previous tier: `production_candidate` / wording drift in control plane
- New tier: `production_surface` for output-level contract
- Evidence: `docs/superpowers/specs/2026-05-11-untargeted-alignment-output-contract.md`; `xic_extractor.alignment.output_levels`; `scripts/run_alignment.py --output-level`; focused output-level tests
- Product surface changed: docs wording only; production level is `alignment_results.xlsx`, `alignment_matrix_identity.tsv`, and `review_report.html`; `alignment_matrix.tsv` remains machine/validation
- Validation: `python -m pytest tests\test_alignment_output_levels.py tests\test_alignment_pipeline_outputs.py::test_run_alignment_production_level_writes_user_artifacts_and_identity_tsv tests\test_alignment_pipeline_outputs.py::test_run_alignment_default_stays_machine_until_owner_validation_acceptance tests\test_run_alignment.py::test_run_alignment_cli_accepts_output_level_debug tests\test_run_alignment.py::test_run_alignment_cli_accepts_validation_minimal_output_level -q`
- Remaining blocker: release gate should continue guarding production/machine/debug/validation artifact separation; this does not claim full untargeted scientific production readiness
