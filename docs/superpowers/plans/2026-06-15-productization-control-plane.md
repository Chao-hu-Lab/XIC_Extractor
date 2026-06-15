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
`method_manifest_v1` 和 `targeted_schema_versioning_v1` 不再佔 active lane。
下一個 primary lane 是 ReviewAction apply/reintegration；supporting lane 只
允許做 sample metadata runtime parity，不可讓 sample role 直接改 main
matrix。

| Slot | Lane | Owner | Allowed work | Stop rule |
|---|---|---|---|---|
| Primary | `review_action_apply_v1` | active branch maintainer: `cc/framework-improvements` | dry-run application plan exists; next slice may add audit/apply only with expected-diff | stop if a manual action changes selected peak/area/counting without expected-diff |
| Supporting | `sample_metadata_runtime_parity_v1` | active branch maintainer: `cc/framework-improvements` | project `sample_metadata_v1` into current injection-order behavior and prove output parity | stop if sample role changes extraction output, counted detection, or matrix value |
| Diagnostic-only | none | none | no new diagnostic sidecars in this window | stop any diagnostic request unless it directly closes active lane acceptance |
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
| Targeted output schema versioning | `production_surface` | `output/schema.py`, manifest `output_schema`, workbook `Run Metadata` | CSV 欄位形狀未改；version 目前透過 manifest/metadata 暴露，不是每列 CSV 欄位 | schema snapshot / downstream handoff profile | none; slice done |
| `EvidenceVector` / `PeakHypothesis` / `IntegrationResult` spine | `production_candidate` | `peak_detection/hypotheses.py`, result assembly | 缺 stable detection id、typed `ReviewAction`、durable audit transition | `canonical_detection_contract_v1` | unassigned |
| `AuditTrail` | `partial_internal` | `PeakHypothesis.audit` | 不是 user-visible operation history | `review_roundtrip_v1` | unassigned |
| `Review Queue` | `production_surface` as worklist | workbook `Review Queue` sheet | 不能讀回 decision；不能 reintegrate | `review_roundtrip_v1` | unassigned |
| ReviewAction import/application plan | `production_candidate` | `xic_extractor.review_actions`, `scripts/validate_review_actions.py`, `scripts/plan_review_action_applications.py`, `scripts/validate_review_action_expected_diffs.py`, `scripts/plan_review_action_apply_readiness.py`, `scripts/plan_review_action_apply_changesets.py` | 可驗證 action、產生 dry-run application plan、產生/驗證 expected-diff approval、產生 apply-readiness/changeset plan；尚未 product-writing apply/recompute/write audit | review action audit/apply loop writes audited outputs | active branch maintainer: `cc/framework-improvements` |
| Manual boundary / reintegration | `missing` | candidate/boundary sidecars + action schema only | 沒有 import -> recompute -> audit loop | `review_action_apply_v1` | active branch maintainer: `cc/framework-improvements` |
| `Run Metadata` | `production_surface` as workbook metadata | workbook sheet + manifest/schema reverse reference | 不是 full replay manifest；只反向記錄 targeted output schema 與 manifest schema/path/hash | workbook hash capture / release metadata docs | unassigned |
| `method_manifest.json` | `production_ready` for targeted CLI replay parity | `xic_extractor.output.method_manifest`, `output/method_manifest.json` | 8RAW/85RAW CSV + workbook replay parity passed；timestamped workbook hash intentionally excluded；包含 targeted output schema artifact | workbook hash capture for full exact artifact replay | unassigned |
| Headless targeted CLI | `production_ready` for targeted CLI replay parity | `xic-extractor-cli`, `--replay-manifest`, method manifest invocation context | replay rejects runtime overrides；GUI replay 未接主線 | GUI parity after mainline wiring | unassigned |
| GUI/CLI parity | `partial_internal` | shared `load_config` / `extractor.run` | 缺 fixture-level parity diff | narrow parity smoke | unassigned |
| `injection_order_source` | `production_surface` | settings/config/extraction pipeline | 只處理 order，不是 sample metadata universe | `sample_metadata_contract_v1` | unassigned |
| Sample metadata roles | `production_candidate` for schema/validator only | `xic_extractor.sample_metadata`, `scripts/validate_sample_metadata.py` | runtime 尚未接 extraction/QC/alignment；sample role 不可改 matrix | shared sample metadata resolver adoption | active branch maintainer: `cc/framework-improvements` |
| Instrument-QC trend sidecar | `production_surface` sidecar | `run_instrument_qc.py`, instrument_qc package | 不改 main matrix；未接 shared sample metadata | sample metadata resolver | unassigned |
| Calibration preview | `shadow_ready` / `diagnostic_only` | instrument-QC calibration preview | 不可寫 main matrix；response transfer blocked | `normalization_calibration_activation_v1` | unassigned |
| Alignment workbook Matrix/Review/Audit | `production_surface` | `alignment_results.xlsx`, `xlsx_writer.py`, `alignment-results-v3` | output-level wording now matches runtime; keep release tests guarding sheet/schema shape | alignment release gate | unassigned |
| Alignment output-level contract | `production_surface` | `output_levels.py`, `--output-level`, output contract spec | `alignment_matrix.tsv` is machine/validation, not production default；`alignment_matrix_identity.tsv` is production-level identity handoff | keep production/machine/debug tests in release gate | none; contract slice done |
| `ProductionDecisionSet` | `production_surface` for alignment matrix decisions | `alignment/production_decisions.py` | release gate 尚未集中檢查 all writers use it | matrix writer gate | unassigned |
| Backfill product-authority sidecars | `shadow_ready` | allowlist/projection sidecars | `product_ready=False`；不可改 primary matrix | activation/export contract | unassigned |
| Provisional production-candidate gate | `diagnostic_only` | production-candidate sidecar | 名稱容易誤導，不是 promotion | wording guard + no-promotion test | unassigned |

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

### 2026-06-15 - alignment_output_contract_v1

- Previous tier: `production_candidate` / wording drift in control plane
- New tier: `production_surface` for output-level contract
- Evidence: `docs/superpowers/specs/2026-05-11-untargeted-alignment-output-contract.md`; `xic_extractor.alignment.output_levels`; `scripts/run_alignment.py --output-level`; focused output-level tests
- Product surface changed: docs wording only; production level is `alignment_results.xlsx`, `alignment_matrix_identity.tsv`, and `review_report.html`; `alignment_matrix.tsv` remains machine/validation
- Validation: `python -m pytest tests\test_alignment_output_levels.py tests\test_alignment_pipeline_outputs.py::test_run_alignment_production_level_writes_user_artifacts_and_identity_tsv tests\test_alignment_pipeline_outputs.py::test_run_alignment_default_stays_machine_until_owner_validation_acceptance tests\test_run_alignment.py::test_run_alignment_cli_accepts_output_level_debug tests\test_run_alignment.py::test_run_alignment_cli_accepts_validation_minimal_output_level -q`
- Remaining blocker: release gate should continue guarding production/machine/debug/validation artifact separation; this does not claim full untargeted scientific production readiness
