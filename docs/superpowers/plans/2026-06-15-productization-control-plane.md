# XIC Extractor productization control plane

日期: 2026-06-15
狀態: living plan / maintenance checklist
目前 readiness: `diagnostic_only` for this control document
主要依據: [current capability inventory](../reports/2026-06-15-current-capability-inventory-and-promotion-roadmap.md)

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
- `PostToolUse`: patch/write 類工具執行後，若工作樹已有 product/public surface diff 但本文件沒有變更，提醒 closeout 前補 board/log 或明確記錄 no-tier-change。

Hooks 是 guardrails，不是語意裁判。它們負責把你和 agent 拉回控制台；真正的 tier 判斷仍要寫在 promotion packet、spec closeout 或 maintenance log 裡。

## Current 2-week active lanes

這是目前唯一可推進的 2 週產品化窗口。其他 lane 留在 inventory，不得開始 implementation。

| Slot | Lane | Owner | Allowed work | Stop rule |
|---|---|---|---|---|
| Primary | `method_manifest_v1` | main agent until assigned otherwise | spec + promotion packet only; no product code before intake packet is reviewed | stop if manifest scope expands beyond targeted extraction provenance/replay |
| Supporting | none | none | only schema/provenance support needed by `method_manifest_v1` after the primary packet names it | stop if it becomes a second product lane |
| Diagnostic-only | none | none | no new diagnostic sidecars in this window | stop any diagnostic request unless it directly closes `method_manifest_v1` |
| Frozen queue | `review_roundtrip_v1`, `sample_metadata_contract_v1`, `alignment_output_contract_v1` | none | planning notes only; no implementation | unfreeze only after primary lane is promoted, killed, or explicitly parked |

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
| Targeted product projection: `Product State`, `Counted Detection`, `Reason` | `production_surface` | `targeted_product_projection.py`, CSV/workbook writers | 缺 schema version 與 canonical projection adapter 文檔 | `canonical_detection_contract_v1` | unassigned |
| `EvidenceVector` / `PeakHypothesis` / `IntegrationResult` spine | `production_candidate` | `peak_detection/hypotheses.py`, result assembly | 缺 stable detection id、typed `ReviewAction`、durable audit transition | `canonical_detection_contract_v1` | unassigned |
| `AuditTrail` | `partial_internal` | `PeakHypothesis.audit` | 不是 user-visible operation history | `review_roundtrip_v1` | unassigned |
| `Review Queue` | `production_surface` as worklist | workbook `Review Queue` sheet | 不能讀回 decision；不能 reintegrate | `review_roundtrip_v1` | unassigned |
| Manual boundary / reintegration | `missing` | candidate/boundary sidecars only | 沒有 import -> recompute -> audit loop | `review_roundtrip_v1` | frozen queue |
| `Run Metadata` | `production_surface` as workbook metadata | workbook sheet | 不是 full replay manifest | `method_manifest_v1` | main agent (active spec only) |
| `method_manifest.json` | `missing` | none | 缺 input hashes、sample metadata、CLI argv、schema versions | `method_manifest_v1` | main agent (active spec only) |
| Headless targeted CLI | `production_surface` | `xic-extractor-cli` | 沒有 manifest-driven replay | `method_manifest_v1` then replay CLI | main agent (active spec only) |
| GUI/CLI parity | `partial_internal` | shared `load_config` / `extractor.run` | 缺 fixture-level parity diff | narrow parity smoke | unassigned |
| `injection_order_source` | `production_surface` | settings/config/extraction pipeline | 只處理 order，不是 sample metadata universe | `sample_metadata_contract_v1` | unassigned |
| Sample metadata roles | `partial_internal` | instrument-QC manifest, settings fragments | 缺 sample type/QC/blank/calibrator/batch schema | `sample_metadata_contract_v1` | frozen queue |
| Instrument-QC trend sidecar | `production_surface` sidecar | `run_instrument_qc.py`, instrument_qc package | 不改 main matrix；未接 shared sample metadata | sample metadata resolver | unassigned |
| Calibration preview | `shadow_ready` / `diagnostic_only` | instrument-QC calibration preview | 不可寫 main matrix；response transfer blocked | `normalization_calibration_activation_v1` | unassigned |
| Alignment workbook Matrix/Review/Audit | `production_surface` | `alignment_results.xlsx`, `xlsx_writer.py` | schema version / output-level wording | `alignment_output_contract_v1` | unassigned |
| Alignment TSV outputs | `production_candidate` | output levels | spec/runtime 對 `alignment_matrix.tsv` primary status 不一致 | `alignment_output_contract_v1` | frozen queue |
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

依照 current capability inventory，目前最有效的順序是:

1. `method_manifest_v1`
   - Reason: 解決 replay/provenance，讓 CLI、Run Metadata、validation harness 能串成成熟工作流。
   - Target tier: `missing` -> `production_candidate`。

2. `review_roundtrip_v1`
   - Reason: 解決 Review Queue 不能回寫，這是 Skyline parity floor。
   - Target tier: `missing` -> `production_candidate`。

3. `sample_metadata_contract_v1`
   - Reason: normalization/QC/alignment 都需要 sample type、QC、blank、batch、injection order。
   - Target tier: `partial_internal` -> `production_candidate`。

4. `alignment_output_contract_v1`
   - Reason: `alignment_results.xlsx` 已成熟，但 TSV production/machine wording 需要對齊。
   - Target tier: `production_candidate` -> `production_surface` for selected output contract。

暫時不要優先做:

- 新 peak picker。
- 新 diagnostic gallery。
- 新 shadow sidecar。
- normalization/calibration main-matrix write。
- backfill product-authority primary matrix activation。

除非 `Current 2-week active lanes` 先把其中一個 lane 解凍，且該 lane 已經有 owner、spec、promotion packet，否則新增這些只會增加未收斂面積。

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
