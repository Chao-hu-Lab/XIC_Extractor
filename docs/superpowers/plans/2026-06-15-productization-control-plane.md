# XIC Extractor productization control plane

日期: 2026-06-15
狀態: living plan / maintenance checklist
目前 readiness: `diagnostic_only` for this control document
主要依據: [current capability inventory](../reports/2026-06-15-current-capability-inventory-and-promotion-roadmap.md)
白話交接: [current productization handoff](../handoffs/current/cc-framework-improvements-productization.md)
可重用背景研究: [deepresearch notes](../../deepresearch/README.md)

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
Backfill standard-path activation 目前分成多個 release tier：72-row
high-signal-clean scoped writer、42-row low-scan-clean scoped writer、57-row
low-height-clean scoped writer、69-row low-height-low-scan-clean scoped
writer、以及 220-row low-height reintegration-stable scoped writer 都已用
explicit opt-in scope audit
filter 寫出 product matrix-only output，且各自的
`narrow_product_writer_expected_diff_acceptance.json` 通過並標
`readiness_tier=production_ready`。Low-height promotion 的前提不是降低
absolute height hard gate；舊的 full-trace heldout oracle 只有 19/20 pass，
`FAM008651/TumorBC2312_DNA` boundary error `1.16445 min` 超過 accepted
`0.1 min` ceiling。後續 diagnostic `expected_window_bounded` observed
reintegration mode 在既有 85RAW trace no-RAW replay 顯示 `padding=0.5 min`
可讓 selected 20/20 通過，最大 boundary error `0.0857986 min`、最大 area
relative error `0.0564106`；再接 explicit
`--low-height-clean-activation-scope-audit-tsv` writer，57/57 expected-diff
通過，duplicate/missing/unexpected/non-eligible/non-written/unchanged/blank
皆為 0。因此 low-height 只可宣稱 explicit 57-row scoped writer ready，不可
外推到 broad 4613-row 或 default behavior。
Low-height-low-scan promotion 是低高度與低 scan 的交集，不是 broadening by
height alone：`standard_low_height_low_scan_clean_trace` 要求
height <2e6、scan 7-9，且 shape/local-global/width/apex 都維持 clean。
既有 85RAW trace no-RAW bounded oracle 有 210 eligible rows / 51 families，
selected 20/20 pass，最大 boundary error `4.80376e-05 min`、最大 area
relative error `0.00881912`；再接
`--low-height-low-scan-clean-activation-scope-audit-tsv` writer，69/69
expected-diff 通過且 duplicate/missing/unexpected/non-eligible/non-written/
unchanged/blank 皆為 0。因此只能宣稱 explicit 69-row scoped writer ready。
擦邊的 apex-delta clean 也只到 `production_candidate`：heldout trace oracle
有 78 candidates / 27 families，selected 20 cases 只有 17/20 pass，最大
boundary error `2.19621 min`，所以也不得新增 apex-delta writer。
Width-only clean 也只到 `production_candidate`：heldout trace oracle 有
4 candidates / 3 families，selected 3 cases 只有 1/3 pass，最大 boundary
error `1.86561 min`、最大 area relative error `0.599229`，所以也不得新增
width-only writer。
Shape-margin clean 也只到 `production_candidate`：這個 probe 把 shape
similarity 降成 `0.93 <= shape < 0.95`，其他條件仍要乾淨；85RAW no-RAW
heldout trace oracle 有 18 candidates / 8 families，selected 8 cases 只有
6/8 pass，summary 最大 area relative error `0.198393`，所以也不得新增
shape-margin writer。
Broad 4613-row auto-write is now `parked` by
`backfill_broad_autowrite_feasibility_gate_v1`: 4613 is the candidate/audit
universe, not a writer pool. The durable next product asset is authority,
mechanical adjudication, structured review, truth acquisition, or trace-evidence
recovery. Do not open another broad Backfill scoped writer or diagnostic unless
a new independent truth source is named and a later goal explicitly adds
masked/product-writer oracle plus expected-diff.
新的 boundary-stability / reintegration-agreement diagnostic 已補上第一個
broader evidence class：`standard_peak_reintegration_stability_audit.py` 對同一
stored trace 做 full-trace 與 expected-window-bounded 兩種再積分，兩者都必須
在 `0.1 min / 10% area` 內吻合才算 eligible。既有 85RAW no-RAW consolidated
scope 實跑得到 299 eligible written rows、3227 ineligible、1087 missing
evidence，其中 271 eligible rows 不在四個既有 ready scoped writer envelope
內。This remains historical candidate evidence only. It does not reopen broad
Backfill auto-write after the 2026-06-18 park decision and must not be used as a
new writer predicate.
後續 low-height reintegration-stable promotion 把這個 candidate pool 的一個
可驗證子集合推到 ready：直接把 299 個 stability eligible rows 全部寫入仍被
formal all-stability family oracle 擋住。該 oracle
`standard_reintegration_stable_candidate_family_trace` 記錄 299 個
audit-intersection rows / 77 families，從同 family 的 1694 個 detected trace
candidates 選 20 個代表案例，結果 19/20；失敗的
`FAM000949/NormalBC2261_DNA` area relative error 是 `0.19621`，超過 accepted
10% ceiling。可放行的是 stability eligible、
activation row 仍 written、且 `cell_height <2e6` 的 220 rows / 66 families。
Formal no-RAW 85RAW heldout family oracle
`standard_low_height_reintegration_stable_candidate_family_trace` is explicitly
family-level, not a row-identity oracle: the summary records
`candidate_family_scope_match_level=family_id`,
`candidate_family_scope_oracle_basis=detected_trace_rows_from_candidate_families`,
220 audit-intersection rows, 66 families, and 1520 detected trace candidates
from those families. It selected 20 family cases and passed 20/20，最大
boundary error `0.0830019 min`、最大 area relative error `0.0725986`；再接
explicit
`--low-height-reintegration-stable-activation-scope-audit-tsv` +
`--reintegration-stability-audit-tsv` writer，220/220 expected-diff 通過且
duplicate/missing/unexpected/non-eligible/non-written/unchanged/blank 全為 0。
這個 fifth ready slice 新增 199 個不在前四個 writer scope 的 ready cells，
目前五個 ready scope 的 cell-level union 是 439 cells。
This is a release-safety boundary and a historical evidence trail, not a
license to keep broadening Backfill writer scope. The product direction is now
mechanical adjudication plus structured approval coverage, with automatic matrix
writes allowed only for explicitly authorized, expected-diff-passing scopes. The
72-row high-signal, 42-row low-scan, 57-row low-height, 69-row
low-height-low-scan, and 220-row low-height reintegration-stable slices remain
demonstrators for approved evidence classes, not templates for mining broader
writer predicates.
Shape-clean reintegration-stable is now a cleaner candidate evidence class, but
not a writer promotion. Formal target
`standard_shape_clean_reintegration_stable_candidate_family_trace` requires
reintegration-stability eligibility and activation-scope shape similarity
`>=0.95`; the no-RAW 85RAW family-level oracle under
`heldout_trace_reintegration_oracle_shape_clean_reintegration_stable_family/`
records 104 audit-intersection rows / 33 families, 334 available detected trace
candidates / 31 families, selected 20/20 pass, max boundary error
`0.0830019 min`, and max area relative error `0.0725986`. A temporary writer
probe was intentionally not retained because it found `matrix_cells_written=0`
and `unchanged_delta_row_count=104`: those rows already have baseline matrix
values, so this evidence can explain policy decisions but cannot claim a new
`production_ready` writer until it targets actual missing cells or another
explicit product contract. The generated policy engine now records this class in
`backfill_policy_candidate_evidence_class` only: the prior shape-clean
explanation replay, before the row-specific observed-oracle bridge, had
439 `write_ready`, 72 `detected_flagged`, and 4102 `blocked`, with 439/439
writer expected-diff pass; 104 rows carried `shape_clean_reintegration_stable`
candidate evidence. At that point, by authority/decision, 30 of those rows were
`review_only` / `detected_flagged`, while 74 were already `writer_approved` /
`write_ready` through existing approved evidence classes.
The Backfill writer path now has a generated policy-engine entry point:
`--backfill-policy-source-audit-tsv` consumes a broad activation scope audit,
optionally joins reintegration-stability evidence, writes
`standard_peak_backfill_policy.tsv`, and classifies every supplied candidate as
`write_ready`, `detected_flagged`, or `blocked`. The writer only replays
generated `write_ready` rows through the existing matrix-only activation and
expected-diff gate. This removes the manual-TSV/white-list failure mode for
already-approved evidence classes; it is not a broadening mechanism and must not
grant authority to new predicates without a later authority manifest update,
independent truth basis, and expected-diff contract. The first generated-policy replay over the
existing 4613-row consolidated source audit passed with 439 generated
`write_ready` rows, 72 `detected_flagged`, and 4102 `blocked`; the product
writer wrote exactly the 439 then-approved evidence rows and
`backfill_policy_write_ready_rows` expected-diff passed with zero blockers. The
latest observed-oracle replay extends that writer surface to 511 `write_ready`
rows and 0 `detected_flagged`, described below. The generated policy schema is
now
`standard_peak_backfill_policy_v2`: every row carries decision-basis,
candidate-evidence, blocker, and next-evidence fields. The generated policy
explanation replay had `0` rows missing explanation; after the observed-oracle
bridge, next-evidence counts are 511 already approved, 1087 needing trace
overlay or reintegration evidence, and 3015 needing a new approved evidence
class or passing oracle.
The same generated policy path now also accepts a machine-generated paired
`--policy-observed-oracle-tsv` / `--policy-observed-oracle-summary-json`
evidence packet. This is not a manual allowlist: the oracle TSV must use
`standard_peak_policy_observed_oracle_v1`, the summary must bind the oracle TSV
SHA, source activation-scope audit SHA, and base generated-policy SHA, row SHA
must match the source audit row, the oracle must be `pass` and
`included_in_product_acceptance=TRUE`, and the source row must still be written
and trace matched. The current no-RAW 85RAW oracle under
`policy_observed_oracle_detected_flagged_full_trace/` evaluated the 72 previous
`detected_flagged` rows by full stored-trace reintegration and passed 72/72
within `0.1 min / 10% area` (max boundary error `8.91875e-05 min`, max area
relative error `0.098218`). The follow-up generated-policy replay under
`generated_policy_policy_observed_oracle_no_raw_productization/` classified the
4613 source-audit rows as 511 `write_ready`, 0 `detected_flagged`, and 4102
`blocked`, wrote exactly 511 matrix cells, and
`backfill_policy_write_ready_rows` expected-diff passed 511/511 with zero
duplicate/missing/unexpected/non-eligible/non-written/unchanged/blank blockers.
This extends `production_ready` to the current approved evidence classes plus
`policy_observed_full_trace_reintegration`; it still does not claim broad
4613-row `production_ready`.
The latest generated-policy replay now also writes an explanation-only quality
sidecar,
`standard_peak_backfill_policy_quality_explanations.tsv`, under
`generated_policy_quality_explained_no_raw_productization/`. This sidecar keeps
the generated policy rows unchanged and does not add writer authority; it only
records source-audit quality blockers for human/debug review. The replay kept
the same product decision surface: 4613 policy rows, 511 `write_ready`, 0
`detected_flagged`, 4102 `blocked`, 511 matrix writes, and 511/511
expected-diff pass. The policy summary now records
`backfill_policy_quality_explanation_row_count=4613`, matching the sidecar TSV.
The most common blocked bucket remains the 1087 rows with missing overlay path,
and the remaining blocked rows mainly carry combined shape/height/width/scan/
apex-delta blockers or still need a new approved evidence class/passing oracle.
The Backfill Production Gate research input under `docs/deepresearch/` reviewed
on 2026-06-17 reinforces that `height >= 2e6` is only a high-signal
demonstrator / rollout guardrail, not a product hard gate. Low-height
`19/20 pass + 1 boundary fail` should be treated as boundary/reintegration risk
evidence. This research input is now background for future truth/review design,
not a prompt to create another broad writer slice.
The 2026-06-18 strategy reset under
`docs/superpowers/notes/2026-06-18-chatgpt_reset_backfill_productization_objective.md`,
`docs/superpowers/notes/2026-06-18-backfill-autowrite-ground-truth-strategy-note.md`,
and
`docs/superpowers/notes/2026-06-18-backfill-autowrite-ground-truth-critical-review.md`
supersedes any next step that would choose another writer slice directly from
`quality_blockers`. The Backfill north star is mechanical adjudication of all
4613 candidates, not claiming all 4613 as writable. Current writer authority
stays at 511 approved cells. The 3015 dirty-but-trace-matched rows are now a
truth/review/adjudication target, not an auto-write pool, and the 1087
`missing_overlay_path` rows stay blocked until trace evidence exists. The
read-only
`backfill_broad_autowrite_feasibility_gate_v1` packet now closes this branch as
`park_broad_backfill`: existing artifacts do not support a short defensible
broad auto-write gate, and ISTD evidence cannot prove analyte peak-choice or
area truth. No broader ProductWriter authority should be implemented, and no
new broad Backfill sidecars/diagnostics should be added unless a genuinely new
independent truth source is named. The current next asset is
`productization_authority_manifest_v1` plus
`mechanical_adjudication_schema_v1` / `mechanical_adjudication_index_v1`: a
fail-closed authority and classification layer that makes all 4613 rows
machine-adjudicated without granting new writer authority.
The next checkpoint adds Review Packet / Approval Workflow v1 as a structured
human-review asset, not ProductWriter authority: the 3015 trace-matched
unresolved rows become review packets, the 1087 missing-overlay rows remain
evidence-recovery work, and reviewer approval can only write a decision log.
Peak-Choice Truth Set / Lockbox v1 then adds the first independent truth-label
acquisition contract: 72 deterministic cases across approved controls,
unresolved review rows, missing-overlay evidence gaps, failed-oracle negatives,
and manual wrong-peak/no-peak fixtures. It is `production_candidate` as a
non-mutating truth/review asset only; no labels have been collected, agreement
metrics are null, and lockbox membership cannot grant ProductWriter authority.
Missing-Overlay Evidence Recovery v1 now links the 1087
`missing_overlay_path` rows back to existing family-level trace/overlay
artifacts and sample-level trace fields across 114 families. This moves the
evidence explanation from "artifact link missing" to "trace recovered but still
needs review/truth/reintegration decision"; it does not grant write authority.
Goal 5 machine status lane ids are tracked in
`docs/superpowers/validation/productization_status_index_v1.tsv`:
`backfill_current_write_ready_scope`, `broad_backfill_autowrite`,
`productization_authority_firewall_v1`, `mechanical_adjudication_contract_v1`,
`review_packet_workflow_v1`, `peak_choice_truth_lockbox_v1`,
`missing_overlay_evidence_recovery_v1`, `quality_explanation_sidecar_v1`,
`targeted_ms1_shape_identity_limited_rescue_v1`,
`targeted_ms1_shape_identity_broader_targets`,
`sample_metadata_order_projection_v1`, `sample_metadata_role_value_behavior`,
`review_action_candidate_sidecar_v1`, `review_action_selected_candidate_switch`,
`review_action_manual_boundary_area_writer`,
`calibration_normalization_activation`, and `gui_replay_parity`.
Targeted MS1 shape identity limited rescue 也已收斂成窄範圍
`production_ready`：headless explicit support-TSV workflow、headless
auto-limited CLI、以及 canonical no-flag normal CLI default 都可用，但都只限
`limited_5hmdc_5medc_v1`、`5-hmdC + 5-medC`、且產品輸出只能變成
`detected_flagged`。GUI wiring、以及其他 target 仍不在這個 ready claim 內。
ReviewAction selected candidate / manual boundary writer 已 parked for current
release claim；產品方向仍是減少人工審查，之後要用 stable IDs、
expected-diff、audit gate 重新開 lane，而不是要求使用者審完所有案例。
sample metadata cross-module
parity 的 no-output resolver slices 已收斂到 `production_ready` for
order projection only：extraction、instrument-QC、alignment、RT-normalization
anchor diagnostic 都可用同一個 `sample_metadata_v1` resolver 或 sidecar；
sample roles / blank / QC / batch / matrix / exclusion 仍 `blocked` for any
value-changing behavior，不可直接改 quant、counted detection、normalized value
或 main matrix。

| Slot | Lane | Owner | Allowed work | Stop rule |
|---|---|---|---|---|
| Primary | `backfill_standard_seed_guard_scope_v1` | none; 72-row high-signal, 42-row low-scan, 57-row low-height, 69-row low-height-low-scan, and 220-row low-height reintegration-stable narrow writer ready slices done; generated policy replay is now ready for current approved evidence classes plus 72 row-specific observed-oracle rows, with 511/511 expected-diff pass and 0 remaining `detected_flagged`; broad Backfill auto-write is parked by `backfill_broad_autowrite_feasibility_gate_v1`; apex-delta, width-only, and shape-margin probes are candidate only; all-stability remains blocked by 19/20 formal oracle; shape-clean reintegration-stable is `production_candidate` evidence only because its oracle passed but the writer probe found 0 new writes / 104 unchanged pre-existing values | maintain existing explicit scoped writer contracts and current 511-cell authority only; route blocked rows through authority/adjudication, structured review, truth, or evidence-recovery assets; no more broad Backfill sidecars/diagnostics unless a new independent truth source is named | stop if the next step would silently broaden matrix writes, derive predicates from `quality_blockers`, use round-trip reintegration as peak-choice truth, revive all-stability/apex-delta/width-only/shape-margin under a new name, include `missing_overlay_path` rows without trace evidence, or create another broad diagnostic backlog |
| Supporting | `sample_metadata_cross_module_parity_v1` | none; no-output order projection is `production_ready`; role/value behavior remains `blocked` | release smoke/docs only; no further role/value behavior without expected-diff | stop if sample role changes extraction output, counted detection, normalized value, or matrix value |
| Parked | `review_action_reintegration_v1` | parked for this release claim; candidate-sidecar verifier is now `production_candidate` | selected-candidate writer and manual boundary area recompute remain blocked until expected-diff/product apply contracts exist; long-term product direction is low-manual-intervention automation with audit/review sampling | stop if a manual action changes selected peak/area/counting without expected-diff |
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
| ReviewAction audited apply copy | `production_surface` for audited targeted-long copy; `production_candidate` for candidate-sidecar verification | `xic_extractor.review_actions`, `scripts/apply_review_action_changesets.py`, `scripts/plan_review_action_candidate_sidecars.py`, `review_action_apply_audit_v1`, `review_action_candidate_sidecar_v1` | accept/mark/reject 可寫 audited output copy；`select_candidate` candidate_id 現在可對 `peak_candidates.tsv` 做唯一性/SHA 驗證；selected candidate switch/manual boundary 仍 deferred | selected-candidate writer + manual boundary recompute writer only after expected-diff/product decision | none; audited apply and candidate-sidecar verifier slices done |
| Manual boundary / reintegration | `parked`; `production_candidate` for deferred changeset and candidate-sidecar verification only | candidate sidecar verifier + action schema + changeset rows | 沒有 area recompute writer；沒有 selected candidate switch writer；candidate sidecar 只驗證 id，不授權改 selected peak/area；需要產品決策確認是否可改 selected peak/area | `review_action_reintegration_v1` product decision | parked |
| `Run Metadata` | `production_surface` as workbook metadata | workbook sheet + manifest/schema reverse reference | 不是 full replay manifest；只反向記錄 targeted output schema 與 manifest schema/path/hash | workbook hash capture / release metadata docs | unassigned |
| `method_manifest.json` | `production_ready` for targeted CLI replay parity | `xic_extractor.output.method_manifest`, `output/method_manifest.json` | 8RAW/85RAW CSV + normalized workbook replay parity passed；artifact policy says CSV exact, workbook normalized compare, manifest provenance-only | full byte-exact workbook replay only if a future release needs it | unassigned |
| Headless targeted CLI | `production_ready` for targeted CLI replay parity | `xic-extractor-cli`, `--replay-manifest`, method manifest invocation context | replay rejects runtime overrides；GUI replay 未接主線 | GUI parity after mainline wiring | unassigned |
| GUI/CLI parity | `partial_internal` | shared `load_config` / `extractor.run` | 缺 fixture-level parity diff | narrow parity smoke | unassigned |
| `injection_order_source` | `production_ready` for order only | settings/config/extraction pipeline | 只處理 order，不是 sample metadata universe；role/value behavior 仍 blocked | `sample_metadata_contract_v1` | unassigned |
| Sample metadata roles | `production_ready` for no-output injection-order projection and instrument-QC manifest projection; `blocked` for role-aware value behavior | `xic_extractor.sample_metadata`, `scripts/validate_sample_metadata.py`, `resolve_injection_order`, `run_alignment --sample-column-injection-order`, `instrument_qc_sample_metadata.tsv`, `analyze_rt_normalization_anchors.py --sample-info` | extraction 可用 `sample_metadata_v1` 當 injection-order source；alignment 可用 `sample_metadata_v1` 排 final matrix sample columns；instrument-QC method-doc manifest 可輸出 `sample_metadata_v1` sidecar；RT-normalization anchor diagnostic 可用 `sample_metadata_v1` 投影 injection order；roles/batch/matrix/exclusion 仍不得改 product values、counted detection 或 normalized values | role-aware QC/blank/batch/matrix/exclusion behavior only with expected-diff gate and product decision | none; cross-module projection slices done |
| Instrument-QC trend sidecar | `production_surface` sidecar | `run_instrument_qc.py`, instrument_qc package, `instrument_qc_sample_metadata.tsv` | 不改 main matrix；sample metadata sidecar 只做 metadata projection | release smoke / downstream docs | none; projection slice done |
| Calibration preview | `shadow_ready` / `diagnostic_only` | instrument-QC calibration preview | 不可寫 main matrix；response transfer blocked | `normalization_calibration_activation_v1` | unassigned |
| Alignment workbook Matrix/Review/Audit | `production_surface` | `alignment_results.xlsx`, `xlsx_writer.py`, `alignment-results-v3` | output-level wording now matches runtime; keep release tests guarding sheet/schema shape | alignment release gate | unassigned |
| Alignment output-level contract | `production_surface` | `output_levels.py`, `--output-level`, output contract spec | `alignment_matrix.tsv` is machine/validation, not production default；`alignment_matrix_identity.tsv` is production-level identity handoff | keep production/machine/debug tests in release gate | none; contract slice done |
| `ProductionDecisionSet` | `production_surface` for alignment matrix decisions | `alignment/production_decisions.py` | release gate 尚未集中檢查 all writers use it | matrix writer gate | unassigned |
| Backfill product-authority sidecars | `production_ready` for generated policy replay of current approved evidence classes plus 72 row-specific observed-oracle rows, explicit 72-row high-signal-clean scoped writer, explicit 42-row low-scan-clean scoped writer, explicit 57-row low-height-clean scoped writer, explicit 69-row low-height-low-scan-clean scoped writer, and explicit 220-row low-height reintegration-stable scoped writer; `production_candidate` for apex-delta diagnostic probe, width-only diagnostic probe, shape-margin diagnostic probe, all-stability 299-row pool, and shape-clean reintegration-stable 104-row evidence class; `parked` for broad 4613-row auto-write | `standard_peak_backfill_policy.tsv`, `--backfill-policy-source-audit-tsv`, paired `--policy-observed-oracle-tsv` / `--policy-observed-oracle-summary-json`, `standard_peak_backfill_productization.py`, `standard_peak_policy_observed_oracle.py`, `standard_peak_activation_scope_audit.py`, `standard_peak_heldout_trace_oracle.py`, `standard_peak_reintegration_stability_audit.py`, `seed_guard_decisions.tsv`, no-RAW 85RAW artifact bridge, heldout trace oracle, activation scope audit, reintegration-stability audit, and scoped writer outputs under `output/productization_realdata_seed_guard_85raw_20260617/` | standard-path activation 先經 N-band seed guard 且 join `activation_value_delta.tsv`；generated policy path classifies every supplied source-audit row as `write_ready` / `detected_flagged` / `blocked` and replays only generated `write_ready` rows with `expected_scope=backfill_policy_write_ready_rows`; hand-authored policy TSV is not a public product input；latest real generated policy replay under `generated_policy_policy_observed_oracle_no_raw_productization/` classified all 4613 consolidated source-audit rows as 511 `write_ready`, 0 `detected_flagged`, and 4102 `blocked`, wrote exactly 511 matrix cells, passed writer expected-diff 511/511 with zero duplicate/missing/unexpected/non-eligible/non-written/unchanged/blank blockers, and records 72 accepted `policy_observed_full_trace_reintegration` rows from the SHA-bound `policy_observed_oracle_detected_flagged_full_trace/` packet; policy next-evidence counts are 511 already approved, 1087 needing trace overlay or reintegration evidence, and 3015 needing a new approved evidence class or passing oracle；既有 85RAW chunk `r1_120` no-RAW bridge passed with 2540 candidates, 1160 eligible writes, 1380 low-seed no-writes；既有 85RAW consolidated no-RAW bridge passed with 7307 candidates, 4613 eligible writes, 2694 low-seed no-writes；high-signal heldout trace oracle 有 20 個 originally detected、sample-local cases，20/20 pass、最大 boundary error 0.0820502 min、最大 area relative error 0.0762325；low-scan heldout trace oracle `heldout_trace_reintegration_oracle_low_scan_clean_probe/` 有 56 eligible candidates / 11 selected family cases，11/11 pass、最大 boundary error 4.86717e-05 min、最大 area relative error 0.038786；combined activation scope audit 證明目前 4613 writes 中 72 個 high-signal clean eligible、42 個 low-scan clean eligible、57 個 low-height clean eligible、69 個 low-height-low-scan clean eligible、1087 個 missing overlay path，broad scope 仍 not_ready；high-signal `narrow_product_writer_expected_diff_acceptance.json` 72/72 pass 且 `readiness_tier=production_ready`；low-scan `narrow_low_scan_clean_no_raw_productization/narrow_product_writer_expected_diff_acceptance.json` 42/42 pass、duplicate/missing/unexpected/non-eligible/non-written/unchanged/blank 都是 0，`expected_scope=low_scan_clean_eligible_activation_rows`、`product_surface_changed=TRUE`、`readiness_tier=production_ready`；low-height bounded oracle `heldout_trace_reintegration_oracle_low_height_bounded_probe_pad050/summary.json` 是 `status=pass`、20/20 pass、max boundary error `0.0857986 min`、max area relative error `0.0564106`，且 `narrow_low_height_clean_no_raw_productization/narrow_product_writer_expected_diff_acceptance.json` 57/57 pass、duplicate/missing/unexpected/non-eligible/non-written/unchanged/blank 都是 0，`expected_scope=low_height_clean_eligible_activation_rows`、`product_surface_changed=TRUE`、`readiness_tier=production_ready`；low-height-low-scan bounded oracle `heldout_trace_reintegration_oracle_low_height_low_scan_clean_probe/summary.json` 是 `status=pass`、210 eligible rows / 51 families、selected 20/20 pass、max boundary error `4.80376e-05 min`、max area relative error `0.00881912`，且 `narrow_low_height_low_scan_clean_no_raw_productization/narrow_product_writer_expected_diff_acceptance.json` 69/69 pass、duplicate/missing/unexpected/non-eligible/non-written/unchanged/blank 都是 0，`expected_scope=low_height_low_scan_clean_eligible_activation_rows`、`product_surface_changed=TRUE`、`readiness_tier=production_ready`；low-height reintegration-stable family oracle `heldout_trace_reintegration_oracle_low_height_reintegration_stable_family/summary.json` is `status=pass`; it records 220 audit-intersection rows / 66 families, `candidate_family_scope_match_level=family_id`, `candidate_family_scope_oracle_basis=detected_trace_rows_from_candidate_families`, 1520 available detected trace candidates from those families, selected 20/20 pass, max boundary error `0.0830019 min`, and max area relative error `0.0725986`; the matching writer `narrow_low_height_reintegration_stable_no_raw_productization/narrow_product_writer_expected_diff_acceptance.json` passes 220/220 with `expected_scope=low_height_reintegration_stable_eligible_activation_rows`, `product_surface_changed=TRUE`, `readiness_tier=production_ready`, and zero duplicate/missing/unexpected/non-eligible/non-written/unchanged/blank blockers；this fifth writer adds 199 cells outside the previous four ready scopes, making the five-scope cell-level union 439 cells before the policy-observed oracle adds 72 additional writer-approved rows；all-stability direct promotion remains blocked by formal target `standard_reintegration_stable_candidate_family_trace`: `heldout_trace_reintegration_oracle_all_stability_family/summary.json` records 299 audit-intersection rows / 77 families, 1694 available detected trace candidates, selected 20 family cases, and failed 19/20 because `FAM000949/NormalBC2261_DNA` has area relative error `0.19621` above the accepted 10% ceiling；shape-clean reintegration-stable oracle `heldout_trace_reintegration_oracle_shape_clean_reintegration_stable_family/summary.json` records 104 audit-intersection rows / 33 families, 334 available detected trace candidates / 31 families, selected 20/20 pass, max boundary error `0.0830019 min`, and max area relative error `0.0725986`, but a temporary writer probe found `matrix_cells_written=0` and `unchanged_delta_row_count=104`, so no public writer flag was retained；apex-delta probe `heldout_trace_reintegration_oracle_apex_delta_clean_probe/summary.json` 是 `status=fail`、17/20 pass、max boundary error `2.19621 min`、max area relative error `0.424518`，所以沒有 writer approval；width-only probe `heldout_trace_reintegration_oracle_width_clean_probe/summary.json` 是 `status=fail`、1/3 pass、max boundary error `1.86561 min`、max area relative error `0.599229`，所以沒有 writer approval；shape-margin probe `heldout_trace_reintegration_oracle_shape_margin_clean_probe/summary.json` 是 `status=fail`、6/8 pass、max boundary error `0.0625542 min`、summary max area relative error `0.198393`，所以沒有 writer approval；observed provenance contract 禁止 oracle/manual/review row 自抄；非標準 peak 仍不可自動 promotion | release docs must say generated policy is the current production-ready writer surface for approved evidence classes plus accepted observed-oracle rows; 72-row, 42-row, 57-row, 69-row, and 220-row scoped writers are historical safe demonstrators; apex-delta/width-only/shape-margin/all-stability/shape-clean-stability are only candidate or explanatory probes; broad 4613 auto-write is parked | none for generated policy replay over current approved evidence classes plus the 72 observed-oracle rows and the five scoped writers; apex-delta/width-only/shape-margin/all-stability need narrower rules or passing oracles before writer work; shape-clean stability needs a missing-cell product scope or policy-explanation-only contract before writer work; broad 4613 can reopen only with a new independent truth source plus observed/masked/product-writer oracle and expected-diff approval |
| Provisional production-candidate gate | `diagnostic_only` with no-promotion guard | production-candidate sidecar, `tests/test_provisional_backfill_candidate_gate_cli.py` | legacy artifact name is still potentially confusing, but summary/test contract says `readiness_label=diagnostic_only`, `production_ready=false`, `matrix_contract_changed=false`, and the CLI does not mutate `alignment_matrix.tsv` | rename only if future public UX needs it; do not promote from this sidecar alone | none; diagnostic guard done |

Backfill row update, 2026-06-18: the long table row above is historical for the
approved 511-cell writer surface and prior probes. The broad 4613-row
auto-write branch is now superseded by
`backfill_broad_autowrite_feasibility_gate_v1` and is `parked`; do not follow
the older "next broadening step" wording without a new independent truth source.

Backfill row update, 2026-06-17: the low-height evidence is no longer only the
old full-trace 19/20 failure. The diagnostic heldout oracle now has an
`expected_window_bounded` observed reintegration mode; no-RAW replay on the
same 85RAW trace artifacts shows `padding=0.5 min` passes selected 20/20 with
max boundary error `0.0857986 min` and max area relative error `0.0564106`.
That evidence has now been connected to an explicit low-height writer flag:
`narrow_low_height_clean_no_raw_productization/narrow_product_writer_expected_diff_acceptance.json`
passes 57/57 with `readiness_tier=production_ready`. This authorizes only the
explicit 57-row low-height scoped writer, not broad 4613-row activation or
default extraction behavior.

Backfill row update, 2026-06-17: the low-height-low-scan intersection is now a
separate explicit scoped writer. This class requires height <2e6, scan count
7-9, and otherwise clean shape/local-global/width/apex evidence. The formal
no-RAW 85RAW bounded heldout oracle
`heldout_trace_reintegration_oracle_low_height_low_scan_clean_probe/summary.json`
passes selected 20/20 from 210 eligible rows / 51 families, with max boundary
error `4.80376e-05 min` and max area relative error `0.00881912`. The explicit
writer run
`narrow_low_height_low_scan_clean_no_raw_productization/narrow_product_writer_expected_diff_acceptance.json`
passes 69/69 with `readiness_tier=production_ready`. This authorizes only the
explicit 69-row low-height-low-scan scoped writer, not broad 4613-row activation
or default extraction behavior.

Backfill row update, 2026-06-17: boundary-stability / reintegration-agreement is
now a named broader diagnostic evidence class. The first full no-RAW 85RAW run
`reintegration_stability_audit/` scans the committed 4613-row activation scope
and reports 299 eligible written rows, 3227 ineligible written rows, and 1087
missing-evidence rows. Of those 299 eligible rows, 271 are outside the four
currently production-ready scoped writer envelopes. This is stronger broad
`production_candidate` evidence only: no writer flag exists, no matrix output is
changed, and masked/product-writer oracle plus expected-diff approval are still
required before any activation claim. Subagent review caught that `status=pass`
was too easy to misread as writer approval; the summary now fails closed with
`status=candidate_pool_blocked`, `writer_authority_status=blocked`, and upstream
activation-scope schema/source_run_id/SHA provenance.

Backfill row update, 2026-06-17: low-height reintegration-stable is now the
fifth explicit scoped writer. It is not the full 299-row stability pool. The
formal family-scope heldout oracle
`heldout_trace_reintegration_oracle_low_height_reintegration_stable_family/`
uses the 299-row stability audit plus the current combined activation scope
audit to select only stability-eligible written rows with `cell_height <2e6`;
that gives 220 audit-intersection rows / 66 families. The oracle then expands
only to detected trace rows from those same families
(`candidate_family_scope_match_level=family_id`; 1520 available candidates),
selected 20 family cases, and passed 20/20 under the accepted
`0.1 min / 10% area` ceiling, with
max boundary error `0.0830019 min` and max area relative error `0.0725986`.
The explicit writer
`narrow_low_height_reintegration_stable_no_raw_productization/` then selected
and wrote exactly 220 cells from the pre-standard-backfill matrix and passed
`narrow_product_writer_expected_diff_acceptance.json` 220/220 with
`readiness_tier=production_ready`. This adds 199 cells outside the previous
four ready scopes; the five-scope ready union is now 439 cells. The broad
4613-row activation and the all-stability 299-row pool remain
`production_candidate` / writer-blocked because the formal all-stability
family oracle failed one selected case above the accepted area tolerance.

Backfill row update, 2026-06-17: shape-clean reintegration-stable is now
recorded as a `production_candidate` evidence class, not a writer. The formal
target `standard_shape_clean_reintegration_stable_candidate_family_trace`
filters the stability/activation intersection to rows with
`apex_aligned_shape_similarity >=0.95`; the real no-RAW 85RAW oracle
`heldout_trace_reintegration_oracle_shape_clean_reintegration_stable_family/`
records 104 audit-intersection rows / 33 families, 334 available detected trace
candidates / 31 families, and selected 20/20 pass with max boundary error
`0.0830019 min` and max area relative error `0.0725986`. A local writer probe
with temporary wiring was intentionally removed before commit because it found
0 new matrix writes and 104 unchanged/pre-existing matrix values. This scope can
inform generated-policy explanation or a future missing-cell scope, but it is
not product writer authority.

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

## Historical immediate 2026-06 queue snapshot

This section is retained as a historical queue from the original 2026-06
planning pass. It is not the current WIP table; use `Current medium-term active
lanes` and `Active productization board` above for current owner/tier decisions.
Items below that say `primary lane` or `supporting lane` describe their status
at that older checkpoint, not the latest release claim.

依照 current capability inventory 與當時 replay executor closeout，當時順序為:

1. `method_manifest_v1` - done
   - Result: `production_ready` for targeted CLI replay parity.
   - Evidence: focused tests, 8RAW CSV/workbook replay parity, and one targeted 85RAW initial+replay sequence.
   - Residual: no timestamped workbook hash capture; GUI replay not wired to mainline.

2. `targeted_schema_versioning_v1` - done
   - Reason: mature-tool parity 需要 output schema version，不然下游與 replay 只能猜欄位語意。
   - Result: `production_surface` for additive schema/version contract.
   - Scope: `output/schema.py` constants, manifest `output_schema`, workbook `Run Metadata`; no CSV data-column changes.

3. `review_action_apply_v1` - historical primary lane at this checkpoint
   - Reason: 解決 Review Queue 不能回寫，這是 Skyline parity floor。
   - Current baseline: `production_candidate` for action schema/import validator and dry-run application plan only.
   - Next target: audit/apply loop with expected-diff before touching selected outputs.

4. `sample_metadata_runtime_parity_v1` - historical supporting lane at this checkpoint
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

### 2026-06-17 - review_action_candidate_sidecar_verifier_v1

- Lane: `review_action_reintegration_v1`.
- Previous tier: selected-candidate switch was `parked`; candidate identity could
  only appear as a free `candidate_id` string inside ReviewAction/expected-diff
  rows.
- New tier: `production_candidate` for candidate-sidecar verification only.
  Selected-candidate switch and manual-boundary area recompute remain parked.
- Evidence: `xic_extractor.review_actions` now defines
  `review_action_candidate_sidecar_v1`; `scripts/plan_review_action_candidate_sidecars.py`
  reads `review_action_v1` plus targeted `peak_candidates.tsv`, verifies that
  each `select_candidate` action's `candidate_id` is present and unique for the
  same sample/target, records a candidate row SHA-256 plus RT/area/confidence
  audit fields, and fails closed for multiple `select_candidate` actions on the
  same target, missing target rows, missing candidates, or duplicate candidate
  ids.
- Product surface changed: additive CLI and additive TSV schema only. No
  selected peak, selected area, counted detection, workbook, primary matrix, or
  extraction output is changed.
- Validation: `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests\test_review_actions.py -q`
  (`32 passed`); focused ruff/mypy for `xic_extractor\review_actions.py`,
  `scripts\plan_review_action_candidate_sidecars.py`, and
  `tests\test_review_actions.py`.
- Remaining blocker: a future product-writing selected-candidate switch still
  needs an explicit expected-diff/apply contract that consumes the verified
  candidate sidecar row. Manual boundary still needs an area recompute writer and
  product decision.
- Next checkpoint: if reopening ReviewAction mutation, consume
  `review_action_candidate_sidecar_v1` together with approved expected-diff; do
  not infer candidate identity from workbook display text.

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
- Remaining blocker: none for the explicit 42-row low-scan release slice. The
  old broad-scope expansion language is historical and superseded by the later
  `park_broad_backfill` decision.
- Next checkpoint: superseded. Later low-height, apex-delta, and width-only
  probes all failed closed, and broad auto-write is now parked; do not use this
  entry to justify another scoped writer.

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
- Previous tier at the time: broad 4613-row standard-path activation was still
  unresolved under the pre-park framing; the next proposed single-blocker class
  was height-only or apex-delta-only.
- New tier at this checkpoint: low-height clean was `production_candidate` only.
  The explicit
  72-row high-signal-clean and 42-row low-scan-clean scoped writers remained
  `production_ready`; the broad-scope statement is superseded by the later
  `park_broad_backfill` decision.
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
- Remaining blocker: superseded by
  `standard_peak_low_height_bounded_reintegration_probe_v1` and
  `standard_peak_low_height_scoped_writer_v1`. Low-height later passed a
  bounded-window oracle packet and the explicit 57-row writer expected-diff
  gate.
- Next checkpoint: see `standard_peak_low_height_scoped_writer_v1`; apex-delta
  and width-only were evaluated after this entry and still failed closed.

### 2026-06-17 - standard_peak_apex_delta_probe_v1

- Lane: Backfill product-authority sidecars /
  `backfill_standard_seed_guard_scope_v1`.
- Previous tier at the time: broad 4613-row standard-path activation was still
  unresolved under the pre-park framing; apex-delta-only was the next small
  single-blocker class after low-height failed its oracle.
- New tier: apex-delta clean is `production_candidate` only. The explicit
  72-row high-signal-clean and 42-row low-scan-clean scoped writers remained
  `production_ready`; the broad-scope statement is superseded by the later
  `park_broad_backfill` decision.
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
- Previous tier at the time: broad 4613-row standard-path activation was still
  unresolved under the pre-park framing; width-only was the smallest remaining
  single-blocker class after low-height and apex-delta failed their oracles.
- New tier: width-only clean is `production_candidate` only. The explicit
  72-row high-signal-clean and 42-row low-scan-clean scoped writers remained
  `production_ready`; the broad-scope statement is superseded by the later
  `park_broad_backfill` decision.
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

### 2026-06-17 - standard_peak_shape_margin_probe_v1

- Lane: Backfill product-authority sidecars /
  `backfill_standard_seed_guard_scope_v1`.
- Previous tier at the time: broad 4613-row standard-path activation was still
  unresolved under the pre-park framing; high-signal and low-scan scoped writers
  were already `production_ready`; low-height, apex-delta, and width-only probes
  were candidate-only after failing heldout oracles.
- New tier: shape-margin clean is `production_candidate` only. The explicit
  72-row high-signal-clean and 42-row low-scan-clean scoped writers remained
  `production_ready`; the broad-scope statement is superseded by the later
  `park_broad_backfill` decision.
- Evidence:
  `tools/diagnostics/standard_peak_heldout_trace_oracle.py` now accepts
  `--target-shape-class standard_shape_margin_clean_trace`, where supported
  trace status, local/global >=0.95, height >=2e6, boundary width 0.30-0.65
  min, apex delta <=0.15 min, and at least 10 boundary scans remain required,
  but shape similarity is limited to the near-threshold band
  `0.93 <= shape < 0.95`. The no-RAW 85RAW heldout packet under
  `output/productization_realdata_seed_guard_85raw_20260617/heldout_trace_reintegration_oracle_shape_margin_clean_probe/`
  found 18 eligible candidate rows across 8 families and selected 8
  family-representative cases. It failed closed with 6/8 pass and two
  `fail_area` cases. Max boundary error was `0.0625542 min`; max area relative
  error was `0.198393`.
- Product surface changed: no matrix writer was added for shape-margin; no
  activation scope audit columns, default extraction behavior, workbook schema,
  GUI behavior, non-standard promotion, matrix identity, selected peak,
  selected area, or broad activation behavior changed.
- Validation:
  `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests\test_standard_peak_heldout_trace_oracle.py -q`
  (`7 passed`); focused ruff for the oracle module and test passed. Subagent
  reviewers `Herschel` and `Kuhn` found no P1/P2 blockers. Their P3 findings
  were fixed by adding the shape-margin upper-width exclusion test and aligning
  docs to the summary JSON max area value. The no-RAW heldout oracle command
  exited `1` by design because the summary status is `fail`. Full local gate
  passed: `ruff check xic_extractor tests tools scripts`, `mypy
  xic_extractor`, `pytest -v --tb=short -x` (`3730 passed, 1 skipped`),
  diagnostics index, and `git diff --check`.
- Remaining blocker: shape-margin cannot be promoted to `production_ready`
  until a narrower fail-closed evidence rule or a new accepted oracle packet
  passes the `0.1 min / 10% area` gate. The failures do not reduce to a simple
  shape-threshold tweak because one failed case had shape `0.949526`.
- Next checkpoint: do not add a shape-margin writer. Continue broadening only
  with another named evidence class that can pass heldout oracle and
  expected-diff writer acceptance.

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
- Next checkpoint: historical. Targeted MS1 may broaden only with separate
  evidence for more targets. The Backfill broadening clause is superseded by
  `park_broad_backfill` and must not be used as a current next step.

### 2026-06-17 - backfill_production_gate_research_input_v1

- Lane: Backfill product-authority sidecars /
  `backfill_standard_seed_guard_scope_v1`.
- Previous tier: unchanged. Explicit 72-row high-signal-clean and 42-row
  low-scan-clean scoped writers remain `production_ready`; broad 4613-row
  standard-path activation plus low-height/apex-delta/width-only/shape-margin
  probes remain `production_candidate`.
- New tier: unchanged; this is design input and product-gate framing, not a
  behavior promotion.
- Evidence: reviewed
  `docs/deepresearch/Backfill Production Gate.md`. The conclusion is that
  absolute `height >= 2e6` should not become a universal Backfill product hard
  gate because LC-MS height depends on analyte response, matrix effect, batch
  state, local background, and co-elution. The low-height heldout result
  `19/20 pass + 1 boundary fail` points to boundary/reintegration consistency,
  not a proof that low-height cells are globally unusable.
- Product surface changed: docs/control-plane/handoff only. No writer, matrix,
  schema, CLI flag, workbook, RAW artifact, or expected-diff output changed.
- Validation: docs-only targeted grep and `git diff --check` for this refresh.
- Remaining blocker: no new low-height or moderate-height writer may be added
  just because expected-diff is clean. This entry is now background for future
  truth/review/evidence design, not a writer prompt.
- Next checkpoint: superseded by the later park decision. Future work should
  predeclare truth/review/evidence assets before any new writer authority is
  considered.

### 2026-06-17 - product_direction_low_manual_intervention_v1

- Previous tier at the time: unchanged. Backfill narrow 72-row writer was
  `production_ready`; broad 4613-row standard-path activation was still
  unresolved under the pre-park framing; headless Targeted MS1 auto-limited CLI
  was `production_ready`; ReviewAction selected-candidate/manual-boundary apply
  remained parked for this release claim.
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

### 2026-06-17 - standard_peak_low_height_bounded_reintegration_probe_v1

- Lane: Backfill product-authority sidecars /
  `backfill_standard_seed_guard_scope_v1`.
- Previous tier: low-height clean Backfill slice was `production_candidate`.
  Activation scope audit had 57 eligible low-height writes and diagnostic
  expected-diff 57/57 pass, but full-trace heldout oracle failed 19/20 because
  `FAM008651/TumorBC2312_DNA` had boundary drift over the accepted `0.1 min`
  ceiling.
- New tier: still `production_candidate`; evidence improved, but no writer
  approval and no `production_ready` claim.
- Evidence: `standard_peak_heldout_trace_oracle.py` now supports diagnostic
  `--observed-reintegration-mode expected_window_bounded` with
  `--expected-window-padding-min`. Default observed reintegration remains
  `full_trace`, so existing oracle behavior is preserved unless the new mode is
  explicit. Existing 85RAW trace artifacts were reused; no RAW files were
  reopened. Low-height bounded replay at `padding=0.1/0.2/0.3 min` still failed
  19/20 because `FAM000883/NormalBC2292_DNA` exceeded the 10% area ceiling, but
  `padding=0.5 min` passed 20/20 with max boundary error `0.0857986 min` and
  max area relative error `0.0564106`.
- Product surface changed: diagnostic CLI and summary fields only:
  `observed_reintegration_mode` and `expected_window_padding_min`. No product
  writer, primary matrix, workbook schema, selected peak/area, counted
  detection, extraction default, or RAW artifact changed.
- Validation: `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest
  tests\test_standard_peak_heldout_trace_oracle.py -q` passed `10`. Subagent
  reviewer `Tesla` found no blocking issue and no product overclaim; its P3
  stale-handoff wording and edge-test findings were fixed by clarifying that
  bounded oracle pass does not authorize a writer, adding CLI negative-padding
  coverage, and adding a bounded-mode missing-observed-result fail-closed test.
- Remaining blocker: superseded by
  `standard_peak_low_height_scoped_writer_v1`, which added the explicit
  low-height writer flag and passed the writer expected-diff gate. The bounded
  replay still cannot be silently converted into broad matrix writes.
- Next checkpoint: see `standard_peak_low_height_scoped_writer_v1`.

### 2026-06-17 - standard_peak_low_height_scoped_writer_v1

- Lane: Backfill product-authority sidecars /
  `backfill_standard_seed_guard_scope_v1`.
- Previous tier: low-height clean was a strong `production_candidate` after
  bounded-window heldout oracle evidence passed selected 20/20, but there was
  no explicit product writer flag or writer expected-diff approval.
- New tier: `production_ready` for the explicit 57-row low-height-clean scoped
  writer only. Broad 4613-row standard-path activation remains
  `production_candidate`; apex-delta, width-only, and shape-margin remain
  candidate-only probes.
- Evidence: `standard_peak_backfill_productization.py` now accepts
  `--low-height-clean-activation-scope-audit-tsv`, which fail-closed filters
  matrix-only activation to audit rows with
  `low_height_clean_status=eligible`. The real no-RAW 85RAW run under
  `output/productization_realdata_seed_guard_85raw_20260617/narrow_low_height_clean_no_raw_productization/`
  reports `status=pass`, `activation_scope_contract=low_height_clean_eligible_activation_rows`,
  57 selected/written rows, and `narrow_product_writer_expected_diff_acceptance.json`
  reports `acceptance_status=pass`, `readiness_tier=production_ready`,
  `product_surface_changed=TRUE`, duplicate/missing/unexpected/non-eligible/
  non-written/unchanged/blank all `0`.
- Product surface changed: additive explicit CLI flag and additive scoped
  writer behavior. No default extraction behavior, workbook schema, broad
  Backfill activation, GUI wiring, selected peak/area, or non-standard peak
  policy changed.
- Validation: `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest
  tests\test_standard_peak_backfill_productization.py -q` passed `12`; touched
  ruff for productization package/CLI/test passed; real no-RAW writer command
  exited `0`.
- Remaining blocker: none for the explicit 57-row low-height scoped writer.
  Broad 4613-row activation still needs additional named evidence classes and
  expected-diff approval before it can claim `production_ready`.
- Next checkpoint: request subagent review of this writer promotion, then run
  the combined Backfill focused shard and PR gate before commit.

### 2026-06-17 - standard_peak_low_height_low_scan_scoped_writer_v1

- Lane: Backfill product-authority sidecars /
  `backfill_standard_seed_guard_scope_v1`.
- Previous tier: low-height-low-scan clean was not a named product slice; broad
  4613-row standard-path activation remained `production_candidate`.
- New tier: `production_ready` for the explicit 69-row
  low-height-low-scan-clean scoped writer only. Broad 4613-row activation
  remains `production_candidate`; apex-delta, width-only, and shape-margin
  remain candidate-only probes.
- Evidence: `standard_peak_heldout_trace_oracle.py` now supports
  `standard_low_height_low_scan_clean_trace`, which requires height <2e6,
  scan count 7-9, shape >=0.95, local/global >=0.95, width 0.30-0.65 min, and
  apex delta <=0.15 min. The formal no-RAW 85RAW bounded oracle under
  `heldout_trace_reintegration_oracle_low_height_low_scan_clean_probe/` found
  210 eligible rows / 51 families, selected 20 family cases, and passed 20/20
  with max boundary error `4.80376e-05 min` and max area relative error
  `0.00881912`. `standard_peak_activation_scope_audit.py` now emits
  `low_height_low_scan_clean_status` and found 69 eligible writes in the
  consolidated 4613-row bridge. `standard_peak_backfill_productization.py` now
  accepts `--low-height-low-scan-clean-activation-scope-audit-tsv`, and the
  real no-RAW writer run under
  `narrow_low_height_low_scan_clean_no_raw_productization/` passed 69/69 with
  `readiness_tier=production_ready`, `product_surface_changed=TRUE`, and
  duplicate/missing/unexpected/non-eligible/non-written/unchanged/blank all
  `0`.
- Product surface changed: additive heldout oracle target class, additive audit
  TSV/summary/expected-diff fields and sidecars, additive explicit CLI flag,
  and additive scoped writer behavior. No default extraction behavior,
  workbook schema, broad Backfill activation, GUI wiring, selected peak/area,
  or non-standard peak policy changed.
- Validation: focused Backfill shard
  `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests\test_standard_peak_heldout_trace_oracle.py tests\test_standard_peak_activation_scope_audit.py tests\test_standard_peak_backfill_productization.py -q`
  passed `39` after the reviewer-requested low-height-low-scan blocker table
  test was added; full PR gate passed with `ruff`, `mypy`, `pytest -v
  --tb=short -x` (`3742 passed, 1 skipped`), diagnostics index, and
  `git diff --check`; formal no-RAW oracle/audit/writer commands exited `0`.
- Remaining blocker: none for the explicit 69-row low-height-low-scan scoped
  writer. Broad 4613-row activation still needs additional named evidence
  classes and expected-diff approval before it can claim `production_ready`.
- Next checkpoint: done for this scoped writer. Subagent reviewer `Parfit`
  found no blocking finding; remaining Backfill work should move to a new named
  evidence class rather than another existing-predicate writer.

### 2026-06-17 - backfill_remaining_scope_evidence_class_blocker_v1

- Lane: Backfill product-authority sidecars /
  `backfill_standard_seed_guard_scope_v1`.
- Previous tier at the time: broad 4613-row standard-path activation was still
  unresolved under the pre-park framing; direct writer work was tempting because
  four narrow scoped writers had reached `production_ready`.
- New tier at the time: direct promotion from the existing
  high-signal/low-scan/low-height/apex/width/shape predicates was blocked. The
  stronger-evidence-class framing is superseded by the later
  `park_broad_backfill` decision and the authority/adjudication contract.
- Evidence: read-only Backfill subagent review confirmed the current safe
  demonstrators are 72 high-signal, 42 low-scan, 57 low-height, and 69
  low-height-low-scan rows. The broad bridge remains 4613 selected writes out
  of 7307 seed-guard candidates, with 2694 low-seed no-writes and 1087 writes
  missing trace/overlay evidence in the activation scope audit. Existing
  candidate probes are not writer-ready: apex-delta is 17/20 with max boundary
  error `2.19621 min`, width-only is 1/3 with max boundary error `1.86561 min`
  and max area relative error `0.599229`, and shape-margin is 6/8 with max
  area relative error `0.198393`.
- Product surface changed: docs/control-plane and handoff wording only. No CLI,
  schema, matrix, workbook, GUI, or extraction default changed.
- Validation: read-only subagent audits `Galileo` and `Feynman`; artifact
  spot-checks of the committed no-RAW 85RAW summaries; no RAW rerun because
  the existing failed probes already answer the direct-writer decision.
- Remaining blocker: superseded for broad auto-write. These ideas can only be
  background for future truth/review/evidence assets unless a later goal names a
  new independent truth source.
- Next checkpoint: historical. Do not design another broad writer evidence
  class from this entry; use the authority/adjudication index to decide whether
  a row needs review, truth labels, or recovered trace evidence.

### 2026-06-17 - standard_peak_reintegration_stability_audit_v1

- Lane: Backfill product-authority sidecars /
  `backfill_standard_seed_guard_scope_v1`.
- Previous tier: broad 4613-row standard-path activation was
  `production_candidate`, blocked on a new named evidence class beyond the four
  explicit scoped writers.
- New tier: still `production_candidate` for broad activation, now with a
  boundary-stability / reintegration-agreement candidate pool. No
  `production_ready` writer is claimed.
- Evidence: new package/CLI diagnostic
  `standard_peak_reintegration_stability_audit.py` consumes
  `activation_high_signal_clean_scope_audit.tsv`, reloads referenced trace
  JSON, and reintegrates each written trace twice: full trace and
  expected-window-bounded (`padding=0.5 min`). A row is eligible only if both
  reintegration views match the stored reference boundary within `0.1 min`,
  match area within `10%`, and agree with each other within the same boundary
  and area tolerances. The real no-RAW 85RAW run under
  `output/productization_realdata_seed_guard_85raw_20260617/reintegration_stability_audit/`
  reports 4613 written rows, 299 eligible, 3227 ineligible, and 1087 missing
  trace/overlay evidence. 271 eligible rows are outside the existing four ready
  scoped writer envelopes. The summary is intentionally not pass-like:
  `status=candidate_pool_blocked`, `writer_authority_status=blocked`, and
  `production_ready=FALSE`; it also records the upstream activation scope TSV
  SHA and source run id.
- Product surface changed: additive diagnostic CLI/package and additive
  diagnostic TSV/JSON output only. No writer flag, default extraction behavior,
  workbook schema, broad Backfill activation, GUI wiring, selected peak/area,
  or non-standard peak policy changed.
- Validation: TDD red/green focused tests
  `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests\test_standard_peak_reintegration_stability_audit.py -q`
  now pass `8`; related Backfill shard
  `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests\test_standard_peak_reintegration_stability_audit.py tests\test_standard_peak_heldout_trace_oracle.py tests\test_standard_peak_activation_scope_audit.py tests\test_standard_peak_backfill_productization.py -q`
  passes `47`; focused ruff and focused mypy passed; subagent reviewer `Hypatia`
  flagged status/provenance/padding fail-closed gaps and they were fixed; real
  no-RAW 85RAW artifact command exited `0` in about 31 seconds.
- Remaining blocker: this is stored-trace self-consistency evidence, not a
  masked product-writer oracle. Before any writer or `production_ready` claim,
  this candidate pool needs masked/product-writer observed results and
  expected-diff approval.
- Next checkpoint: build the masked/product-writer oracle for the 299-row
  candidate pool, or add another independent evidence class before any writer
  claim.

### 2026-06-17 - standard_peak_low_height_reintegration_stable_writer_v1

- Lane: Backfill product-authority sidecars /
  `backfill_standard_seed_guard_scope_v1`.
- Previous tier: reintegration-stability audit had promoted a 299-row broader
  candidate pool to stronger `production_candidate`, but writer authority was
  blocked because stored-trace self-consistency alone is not product approval.
- New tier: `production_ready` for the explicit 220-row low-height
  reintegration-stable scoped writer only. Broad 4613-row activation and the
  full 299-row all-stability pool remain `production_candidate`.
- Evidence: the all-stability family check was intentionally not promoted; it
  was later formalized as target
  `standard_reintegration_stable_candidate_family_trace` and confirmed one
  `fail_area` case
  (`FAM000949/NormalBC2261_DNA`, area relative error `0.19621`). The promoted
  scope is narrower: stability-eligible written rows whose activation audit
  `cell_height` is below `2e6`. Formal no-RAW 85RAW heldout trace oracle
  target `standard_low_height_reintegration_stable_candidate_family_trace`
  found 220 audit-intersection rows across 66 families, then evaluated detected
  trace candidates from those same families (`match_level=family_id`,
  1520 available candidates), selected 20 family cases, and passed 20/20 with
  max boundary error `0.0830019 min` and max area relative error `0.0725986`.
  The real no-RAW writer under
  `output/productization_realdata_seed_guard_85raw_20260617/narrow_low_height_reintegration_stable_no_raw_productization/`
  selected and wrote 220 cells from the pre-standard-backfill matrix.
  `narrow_product_writer_expected_diff_acceptance.json` reports
  `acceptance_status=pass`, `readiness_tier=production_ready`,
  `expected_scope=low_height_reintegration_stable_eligible_activation_rows`,
  and zero duplicate/missing/unexpected/non-eligible/non-written/unchanged/blank
  blockers. This adds 199 ready cells outside the previous four ready scopes;
  the five-scope ready union is 439 cells.
- Product surface changed: additive CLI/package flags only:
  `standard_peak_heldout_trace_oracle.py --reintegration-stability-audit-tsv`
  / `--activation-scope-audit-tsv` for the family-scope oracle and
  `standard_peak_backfill_productization.py --low-height-reintegration-stable-activation-scope-audit-tsv`
  / `--reintegration-stability-audit-tsv` for the writer. No default
  extraction behavior, workbook schema, GUI, broad Backfill activation,
  selected peak/area, or non-standard peak policy changed.
- Validation: TDD/focused gates passed:
  `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests\test_standard_peak_heldout_trace_oracle.py::test_heldout_trace_oracle_cli_writes_low_height_stability_family_packet tests\test_standard_peak_heldout_trace_oracle.py::test_low_height_stability_family_scope_requires_scope_inputs -q`
  (`2 passed`);
  `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests\test_standard_peak_heldout_trace_oracle.py -q`
  (`14 passed`);
  `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests\test_standard_peak_backfill_productization.py::test_standard_peak_productization_can_limit_writer_to_low_height_stability_scope tests\test_standard_peak_backfill_productization.py::test_low_height_stability_scope_filters_rows_not_whole_family tests\test_standard_peak_backfill_productization.py::test_standard_peak_productization_rejects_wrong_activation_scope_schema tests\test_standard_peak_backfill_productization.py::test_standard_peak_productization_rejects_wrong_stability_schema -q`
  (`4 passed`);
  `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests\test_standard_peak_backfill_productization.py -q`
  (`19 passed`);
  `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests\test_standard_peak_reintegration_stability_audit.py tests\test_standard_peak_heldout_trace_oracle.py tests\test_standard_peak_activation_scope_audit.py tests\test_standard_peak_backfill_productization.py -q`
  (`52 passed`); focused ruff and focused mypy passed for the touched Backfill
  modules and tests. The real no-RAW oracle and writer commands exited `0`;
  no RAW/85RAW rerun was needed because existing 85RAW trace/productization
  artifacts answered this scope decision. Subagent reviewer `Bernoulli` found
  two blockers before closeout: the oracle wording overclaimed row identity and
  the writer lacked activation-scope schema-version validation. Both were
  fixed. Follow-up reviewer `Avicenna` found no blocking finding; it confirmed
  the claim is now limited to the explicit 220-row writer while all-stability
  299 and broad 4613 remain candidate/blocked.
- Remaining blocker: all-stability direct writer remains blocked by the
  family-check area failure; broad 4613-row activation still needs broader
  masked/product-writer oracle and expected-diff approval. Apex-delta,
  width-only, and shape-margin probes remain blocked by their failed heldout
  oracles.
- Next checkpoint: run the remaining PR gate before commit. The next
  productization slice should broaden by a new evidence class or masked
  product-writer oracle, not by silently widening the new 220-row writer.

### 2026-06-17 - standard_peak_all_stability_family_oracle_v1

- Lane: Backfill product-authority sidecars /
  `backfill_standard_seed_guard_scope_v1`.
- Previous tier: all-stability 299-row reintegration-stable candidate pool was
  `production_candidate` / writer-blocked based on a quick family check.
- New tier: still `production_candidate` / writer-blocked, now with a formal
  fail-closed oracle artifact. No writer, matrix, workbook, GUI, selected
  peak/area, or default extraction behavior changed.
- Evidence: `standard_peak_heldout_trace_oracle.py` now supports formal target
  class `standard_reintegration_stable_candidate_family_trace`. The real
  no-RAW 85RAW oracle packet under
  `output/productization_realdata_seed_guard_85raw_20260617/heldout_trace_reintegration_oracle_all_stability_family/`
  records 299 audit-intersection rows across 77 families, expands to 1694
  available detected trace candidates from those families, selects 20 family
  cases, and reports `status=fail`: 19 pass and 1 `fail_area`.
  `FAM000949/NormalBC2261_DNA` has boundary error `0.0626 min` but area
  relative error `0.19621`, above the accepted `0.10` ceiling. This confirms
  that all-stability rows cannot be promoted directly.
- Validation: focused oracle tests
  `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests\test_standard_peak_heldout_trace_oracle.py -q`
  passed `16` after reviewer `Franklin` requested the high-height/low-height
  boundary regression test; focused ruff and mypy passed for the touched oracle
  module/test. Docs/evidence reviewer `Archimedes` found no blocker and
  confirmed the artifact counts/status/failing case match the docs. The real
  no-RAW oracle command intentionally exited `1` because the artifact failed
  the product oracle, not because the command crashed.
- Remaining blocker: all-stability direct writer needs a narrower
  product-meaningful evidence class, a different independent oracle, or a
  writer contract that can explain and exclude the failing family before any
  matrix write. Broad 4613-row activation still needs broader generated-policy
  evidence with oracle + expected-diff approval.
- Next checkpoint: do not retry direct all-stability writer work. Either add a
  simpler evidence class that explains the 19 pass / 1 fail split, or move the
  next Backfill expansion through the generated policy engine with a separate
  passing oracle and expected-diff gate.

### 2026-06-17 - standard_peak_generated_backfill_policy_explanation_v2

- Lane: Backfill product-authority sidecars /
  `backfill_standard_seed_guard_scope_v1`.
- Previous tier: generated policy replay over current approved evidence classes
  was `production_ready`, but blocked/detected rows still relied on coarse
  reason strings and the policy summary did not say what evidence each row
  still needed.
- New tier: remains `production_ready` for generated policy replay of current
  approved evidence classes; the policy explanation contract is now
  `standard_peak_backfill_policy_v2`. No broad 4613-row tier promotion.
- Evidence: `standard_peak_backfill_policy.tsv` now requires
  `backfill_policy_decision_basis`, `backfill_policy_next_evidence`, and
  `backfill_policy_candidate_evidence_class` for every generated row. Missing
  explanation fields fail closed before matrix activation. The real no-RAW
  85RAW replay under
  `output/productization_realdata_seed_guard_85raw_20260617/generated_policy_explained_no_raw_productization/`
  produced 4613 explained policy rows with `0` missing explanation rows:
  439 `write_ready`, 72 `detected_flagged`, and 4102 `blocked`. The
  next-evidence distribution is 439 already current-scope approved, 72 needing
  masked/product-writer oracle, 1087 needing trace overlay or reintegration
  evidence, and 3015 needing a new approved evidence class or passing oracle.
  The writer still wrote exactly 439 matrix cells and expected-diff passed
  439/439 with zero blockers.
- Validation: `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests\test_standard_peak_backfill_productization.py -q`
  passed with `22 passed`; the no-RAW 85RAW generated-policy explanation replay
  exited `0` in about 2.36 sec.
- Remaining blocker: the explanation contract makes every current candidate
  accountable, but broad 4613, all-stability 299, apex-delta, width-only, and
  shape-margin still need their own oracle/expected-diff evidence before
  writer authority.
- Next checkpoint: add one new product evidence class to policy v2 only when it
  has a passing oracle/expected-diff gate; otherwise leave the row explained as
  blocked or `detected_flagged`.

### 2026-06-17 - standard_peak_policy_observed_oracle_writer_v1

- Lane: Backfill product-authority sidecars /
  `backfill_standard_seed_guard_scope_v1`.
- Previous tier: generated policy replay was `production_ready` for 439 current
  approved-evidence rows; 72 boundary-stable rows remained
  `detected_flagged` because they lacked a row-specific product-writer oracle.
- New tier: `production_ready` for generated policy replay of current approved
  evidence classes plus `policy_observed_full_trace_reintegration`. No broad
  4613-row tier promotion.
- Evidence: `standard_peak_policy_observed_oracle.py` evaluates generated
  `detected_flagged` rows against their source activation-scope audit row,
  reloads the full stored trace, recomputes peak boundaries/area, and only
  accepts rows that pass `0.1 min / 10% area`, have
  `included_in_product_acceptance=TRUE`, keep the same row SHA/family/sample,
  remain trace matched/written, and are bound by companion summary JSON to the
  oracle TSV SHA, source audit SHA, and base generated-policy SHA. The real
  no-RAW 85RAW oracle packet under
  `output/productization_realdata_seed_guard_85raw_20260617/policy_observed_oracle_detected_flagged_full_trace/`
  passed 72/72 with max boundary error `8.91875e-05 min` and max area relative
  error `0.098218`. The follow-up generated-policy replay under
  `output/productization_realdata_seed_guard_85raw_20260617/generated_policy_policy_observed_oracle_no_raw_productization/`
  classified 4613 source-audit rows as 511 `write_ready`, 0
  `detected_flagged`, and 4102 `blocked`; writer expected-diff passed 511/511
  with `readiness_tier=production_ready` and zero duplicate/missing/unexpected/
  non-eligible/non-written/unchanged/blank blockers.
- Validation: focused TDD red/green for the new oracle producer and product
  policy connection; `uv run pytest tests\test_standard_peak_policy_observed_oracle.py -q`
  passed with `2 passed`; `uv run pytest tests\test_standard_peak_backfill_productization.py -q`
  passed with `29 passed`; focused ruff and mypy passed for the touched
  diagnostics/CLI modules. After subagent review found the bare-TSV allowlist
  gap, the productization consumer now requires
  `--policy-observed-oracle-summary-json` and verifies the oracle/source/base
  policy hashes before promotion. The refreshed no-RAW oracle command exited
  `0` in about 2.08 s and the refreshed no-RAW replay command exited `0` in
  about 3.08 s.
- Remaining blocker at the time: the remaining 4102 blocked rows still needed
  trace overlay / reintegration evidence or another approved evidence class and
  oracle before they could write. The old broad-scope
  `production_candidate` framing is superseded by the 2026-06-18
  `park_broad_backfill` decision.
- Next checkpoint: superseded. Do not use this entry to continue broad
  Backfill broadening; route unresolved rows through authority/adjudication,
  structured review, truth acquisition, or trace-evidence recovery.

### 2026-06-17 - standard_peak_shape_clean_policy_explanation_v1

- Lane: Backfill product-authority sidecars /
  `backfill_standard_seed_guard_scope_v1`.
- Previous tier: shape-clean reintegration-stable was `production_candidate`
  oracle evidence only; generated policy v2 did not identify it separately from
  generic `reintegration_stable` candidate evidence.
- New tier: still `production_candidate` / explanation evidence only. Generated
  policy replay remains `production_ready` for current approved evidence
  classes, with no broad 4613-row tier promotion and no shape-clean writer
  authority.
- Evidence: `standard_peak_backfill_productization.py` now treats
  `apex_aligned_shape_similarity` as part of the source activation-scope audit
  contract and records `shape_clean_reintegration_stable` in
  `backfill_policy_candidate_evidence_class` when the row is reintegration
  stable, has `matrix_value_effect=written`, is trace matched and family
  matched, and shape similarity is `>=0.95`. This class is never added to
  `backfill_policy_evidence_class` or
  `ready_evidence_classes` by itself. The real no-RAW 85RAW replay under
  `output/productization_realdata_seed_guard_85raw_20260617/generated_policy_shape_clean_explained_no_raw_productization/`
  still classifies 4613 rows as 439 `write_ready`, 72 `detected_flagged`, and
  4102 `blocked`; the writer still selected/wrote 439 cells and
  `backfill_policy_write_ready_rows` expected-diff passed 439/439. Candidate
  evidence distribution now shows 104 rows containing
  `shape_clean_reintegration_stable`: by authority/decision, 30 are
  `review_only` / `detected_flagged` and 74 are already `writer_approved` /
  `write_ready`; by candidate-evidence string, 76 are
  `shape_clean_reintegration_stable,reintegration_stable`, 21 overlap
  `low_height_clean`, and 7 overlap `high_signal_clean`.
- Validation: focused productization tests
  `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests\test_standard_peak_backfill_productization.py -q`
  passed after reviewer fixes; focused ruff and mypy passed for the
  productization module/test; the real no-RAW replay exited `0` in about
  2.45 sec. Subagent review found no blocker: Erdos requested negative guard
  tests for trace/shape fail-closed behavior, and Aquinas found the original
  104-row split wording was wrong; both were fixed. Full local gate passed:
  ruff, mypy, pytest `3767 passed, 1 skipped`, diagnostics index, and
  `git diff --check` with Windows LF/CRLF warnings only.
- Remaining blocker: shape-clean stability is explanation evidence until a
  missing-cell scope or masked/product-writer oracle proves nonzero product
  delta. It must not become a public writer flag or a ready evidence class from
  this change alone.
- Next checkpoint: superseded for broad Backfill. Future work should use
  authority/adjudication, structured review, truth acquisition, or trace
  evidence recovery rather than new nested writer flags.

### 2026-06-17 - standard_peak_shape_clean_reintegration_stable_oracle_v1

- Lane: Backfill product-authority sidecars /
  `backfill_standard_seed_guard_scope_v1`.
- Previous tier at the time: shape-clean stability was not a named Backfill
  evidence class; all-stability 299 and broad 4613 were still unresolved /
  writer-blocked under the pre-park framing.
- New tier: `production_candidate` evidence class only. No public writer flag,
  no matrix write, no workbook/schema/GUI/default extraction behavior change.
- Evidence: `standard_peak_heldout_trace_oracle.py` now supports
  `standard_shape_clean_reintegration_stable_candidate_family_trace`, requiring
  reintegration-stability eligible written rows plus activation-scope
  `apex_aligned_shape_similarity >=0.95`. The real no-RAW 85RAW oracle packet
  under
  `output/productization_realdata_seed_guard_85raw_20260617/heldout_trace_reintegration_oracle_shape_clean_reintegration_stable_family/`
  reports `status=pass`, 104 audit-intersection rows / 33 families, 334
  available detected trace candidates / 31 families, selected 20/20 pass, max
  boundary error `0.0830019 min`, and max area relative error `0.0725986`.
  A local temporary writer probe under
  `output/productization_realdata_seed_guard_85raw_20260617/narrow_shape_clean_reintegration_stable_no_raw_productization/`
  was not retained as product code because it failed expected-diff:
  `matrix_cells_written=0`, `product_written_delta_row_count=0`,
  `not_written_delta_row_count=104`, and `unchanged_delta_row_count=104`.
- Validation: real no-RAW oracle command exited `0` in about 7.84 sec. Focused
  oracle tests passed with `19 passed` after reviewer `Sartre` requested an
  explicit missing-`apex_aligned_shape_similarity` fail-closed regression test.
  Docs/evidence reviewer `Heisenberg` found no overclaim blocker and requested
  the WIP-table stop rule now reflected above. Full local gate passed:
  `$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor tests`;
  `$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor`;
  `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -v --tb=short -x`
  (`3764 passed, 1 skipped`);
  `$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts\check_diagnostics_index.py`;
  `git diff --check` had no whitespace errors, only Windows LF/CRLF warnings.
- Remaining blocker: this shape-clean class currently proves that already
  detected/pre-existing matrix-value families reintegrate cleanly. It does not
  prove a missing-cell writer effect. To promote it, route it through generated
  policy as explanation-only evidence or build a missing-cell candidate scope
  with nonzero expected-diff and the same oracle/expected-diff acceptance.
- Next checkpoint: do not add a shape-clean public writer flag. The broadening
  clause is superseded; shape-clean evidence can remain explanatory candidate
  context only unless a future authority/truth/expected-diff goal reopens it.

### 2026-06-17 - standard_peak_generated_backfill_policy_path_v1

- Lane: Backfill product-authority sidecars /
  `backfill_standard_seed_guard_scope_v1`.
- Previous tier: five explicit scoped writers were `production_ready`; broad
  4613-row activation and the all-stability 299-row pool remained
  `production_candidate` / writer-blocked. The implementation path was drifting
  toward more nested scoped writer flags.
- New tier: `production_ready` for generated policy replay of the current
  approved evidence classes. No broad 4613-row tier promotion: rows outside the
  approved evidence classes remain `detected_flagged` or `blocked` until their
  own oracle and expected-diff evidence exists.
- Evidence: `standard_peak_backfill_productization.py` now accepts
  `--backfill-policy-source-audit-tsv`, generates
  `standard_peak_backfill_policy.tsv` plus summary, and classifies each source
  audit row as `write_ready`, `detected_flagged`, or `blocked`. The generated
  policy schema is now `standard_peak_backfill_policy_v2`; every row must carry
  `backfill_policy_decision_basis`, `backfill_policy_next_evidence`, and
  `backfill_policy_candidate_evidence_class`. The CLI does not expose a
  human-authored activation policy TSV, and the public package API does not
  accept `activation_policy_tsv`. `write_ready` rows fail closed unless they are
  written rows with matched trace evidence, a nonblank evidence class, and
  `writer_approved` authority; every policy row fails closed if explanation
  fields are blank. Focused tests prove a four-row broad source audit produces
  one high-signal `write_ready`, one low-height stability `write_ready`, one
  `detected_flagged`, and one `blocked`, and only the two `write_ready` rows
  alter the matrix. Additional negative tests cover trace-mismatch clean-status
  contradictions and the missing public manual policy TSV entry point. The real
  no-RAW 85RAW replay under
  `output/productization_realdata_seed_guard_85raw_20260617/generated_policy_explained_no_raw_productization/`
  consumed the existing 4613-row consolidated source audit plus the
  reintegration-stability audit, generated 439 `write_ready`, 72
  `detected_flagged`, and 4102 `blocked` policy rows, selected/wrote 439 matrix
  cells, passed `backfill_policy_write_ready_rows` expected-diff with zero
  blockers, and had `0` missing explanation rows. Its next-evidence counts are
  439 `none_current_scope_writer_approved`, 72
  `masked_or_product_writer_oracle_required`, 1087
  `trace_overlay_or_reintegration_evidence_required`, and 3015
  `approved_evidence_class_or_passing_oracle_required`.
- Validation: `$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor\diagnostics\standard_peak_backfill_productization.py tools\diagnostics\standard_peak_backfill_productization.py tests\test_standard_peak_backfill_productization.py`
  passed; `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests\test_standard_peak_backfill_productization.py -q`
  passed with `22 passed`. Subagent reviewers `Faraday` and `Meitner` found
  policy/manual-allowlist, trace-evidence, stale acceptance-scope, stale board,
  and next-action wording gaps; all were fixed before closeout. Full local gate
  then passed: `$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor tests`;
  `$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor`; `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -v --tb=short -x`
  (`3759 passed, 1 skipped`); `$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts\check_diagnostics_index.py`;
  and the latest no-RAW generated-policy explanation replay command exited `0`
  in about 2.36 sec.
- Remaining blocker: generated policy currently only unifies existing approved
  evidence classes. It does not make apex-delta, width-only, shape-margin,
  all-stability, or broad 4613 rows production-ready without their own oracle
  and expected-diff approval.
- Next checkpoint: superseded for broad Backfill. Future evidence classes may be
  considered only under a new independent truth-source / expected-diff goal;
  this entry must not be used as permission to mine another writer slice.

### 2026-06-18 - productization_status_index_v1

- Lane: Productization control-plane cleanup / machine-checkable lane status.
- Previous tier: the handoff and control plane contained current lane status in
  prose, but there was no compact machine-readable index that could reject
  authority drift.
- New tier: `production_candidate` control-plane guard. This does not change
  product behavior or writer authority.
- Evidence: `docs/superpowers/specs/productization_control_plane_schema.v1.json`
  defines the status-index schema and allowed readiness states.
  `docs/superpowers/validation/productization_status_index_v1.tsv` records each
  current lane exactly once, including parked broad Backfill, the 511-cell
  current writer scope, review/truth/recovery assets, targeted MS1 limited
  rescue, sample metadata no-output projection, ReviewAction parked writebacks,
  calibration freeze, and GUI out-of-scope state.
  `scripts/check_productization_state.py` validates lane uniqueness, required
  lanes, artifact hashes, doc anchors, authority-manifest alignment, and that
  parked/blocked/diagnostic/frozen/out-of-scope/review/truth/evidence lanes
  cannot write.
- Product surface changed: docs/spec/validation/test/helper script only. No
  ProductWriter, matrix, workbook, selected peak/area, counted detection,
  workbook schema, CLI/config, extraction default, or GUI behavior changed.
- Validation:
  `$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/check_productization_state.py`
  returned `Productization state index is consistent and fail-closed.` Focused
  tests passed:
  `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_productization_state_index.py -v --tb=short`
  (`9 passed`). Focused ruff passed for `scripts/check_productization_state.py`
  and `tests/test_productization_state_index.py`. Subagent review findings were
  fixed by adding workbook/selected-peak/selected-area flags, rejecting
  non-writer authority scopes and product-output changes, and requiring
  handoff/control-plane anchors. Full local gate also passed:
  `$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor tests scripts/build_trace_overlay_recovery_report.py scripts/build_peak_choice_truth_lockbox.py scripts/check_productization_authority.py scripts/check_productization_state.py`;
  `$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor`;
  `$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/check_productization_authority.py`;
  `$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/check_productization_state.py`;
  `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -v --tb=short -x`
  (`3813 passed, 1 skipped`);
  `$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/check_diagnostics_index.py`;
  `git diff --check` passed with LF/CRLF warnings only.
- Remaining blocker: this is a guardrail, not product behavior. It does not
  collect lockbox labels, recover new RAW evidence, or promote any parked lane.
- Next checkpoint: Goal 6 bounded non-broad lane hardening. Keep the status
  index in future productization gates.

### 2026-06-18 - missing_overlay_evidence_recovery_v1

- Lane: Missing-overlay evidence recovery / low-manual review infrastructure.
- Previous tier: 1087 rows were `evidence_required` because the source audit had
  `missing_overlay_path` and no trace/overlay links.
- New tier: `production_candidate` evidence-recovery asset. The rows remain
  `evidence_required`; no writer authority changes.
- Evidence: `scripts/build_trace_overlay_recovery_report.py` links all 1087
  missing-overlay rows from `mechanical_adjudication_index_v1.tsv` to existing
  family-level trace JSON, overlay PNG, hypothesis PNG, and sample-level trace
  fields across 114 families. The generated
  `docs/superpowers/validation/trace_overlay_recovery_report_v1.tsv` records
  `recovery_status=family_trace_overlay_recovered`, `sample_trace_present=TRUE`,
  and `post_recovery_evidence_grade=C_trace_recovered` for all 1087 rows.
  `docs/superpowers/validation/missing_overlay_resolution_summary_v1.json`
  records `status=all_existing_family_trace_overlays_recovered`.
- Product surface changed: docs/spec/validation/test/helper script only. No
  ProductWriter, matrix, workbook, selected peak/area, counted detection,
  workbook schema, CLI/config, extraction default, or GUI behavior changed.
- Validation:
  `$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/build_trace_overlay_recovery_report.py`
  generated the recovery report. Focused tests passed:
  `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_trace_overlay_recovery_contract.py -v --tb=short`
  (`5 passed`). Focused ruff passed for
  `scripts/build_trace_overlay_recovery_report.py` and
  `tests/test_trace_overlay_recovery_contract.py`. JSON parse passed for the
  recovery schema and summary.
- Remaining blocker: recovered trace/overlay evidence is not peak-choice truth
  and not area approval. These rows need structured review, truth labels, or a
  later reintegration/expected-diff authority goal before any product write can
  be considered.
- Next checkpoint: Goal 5 productization control-plane cleanup. Do not use this
  recovery report as ProductWriter input.

### 2026-06-18 - peak_choice_truth_lockbox_v1

- Lane: Peak-choice truth acquisition / low-manual review infrastructure.
- Previous tier: Review Packet / Approval Workflow v1 made the 3015
  trace-matched unresolved rows reviewable, but there was no independent
  truth-label protocol or family-split lockbox.
- New tier: `production_candidate` for a non-mutating truth acquisition
  contract. This does not change writer authority.
- Evidence: `docs/superpowers/specs/peak_choice_truth_protocol.v1.md` defines
  the truth-lockbox protocol. `docs/superpowers/specs/truth_label_schema.v1.json`
  defines the sampling manifest and label-log schema. The generated
  `docs/superpowers/validation/lockbox_sampling_manifest_v1.tsv` contains 72
  deterministic cases: 18 approved write-ready controls, 24 unresolved
  review-ready rows split across high-signal dirty / low-height / apex-delta /
  shape-width-scan contexts, 12 missing-overlay evidence-gap rows, 12 failed
  heldout-oracle negative cases, and 6 manual wrong-peak/no-peak fixtures.
  `docs/superpowers/validation/reviewer_label_log_v1.tsv` is intentionally
  header-only, and
  `docs/superpowers/validation/inter_reviewer_agreement_summary_v1.json`
  records `status=no_labels_collected`. Missing-overlay evidence-gap rows are
  not forced into fake area labels: they have `area_label_required=FALSE`, and
  all rows allow `not_assessed` / `unavailable`.
- Product surface changed: docs/spec/validation/test/helper script only. No
  ProductWriter, matrix, workbook, selected peak/area, counted detection,
  workbook schema, CLI/config, extraction default, or GUI behavior changed.
- Validation:
  `$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/build_peak_choice_truth_lockbox.py`
  generated the 72-case lockbox. Focused tests passed:
  `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_peak_choice_truth_lockbox_contract.py -v --tb=short`
  (`6 passed`). Focused ruff passed for
  `scripts/build_peak_choice_truth_lockbox.py` and
  `tests/test_peak_choice_truth_lockbox_contract.py`. JSON parse passed for the
  truth schema and agreement summary. Subagent review found one P2 issue where
  missing-overlay rows could be forced into area labels; the generated manifest
  and tests now require honest `not_assessed` / `unavailable` handling.
- Remaining blocker: no reviewer labels or agreement metrics exist yet; lockbox
  membership and future labels cannot grant ProductWriter authority without a
  later authority manifest plus expected-diff goal.
- Next checkpoint: Goal 4 missing-overlay evidence recovery. Do not make the
  1087 missing-overlay rows writable simply because they are sampled here.

### 2026-06-18 - productization_review_packet_v1

- Lane: Backfill product-authority control plane /
  low-manual review workflow.
- Previous tier: Goal 0/1 authority/adjudication contract existed as a
  `production_candidate` control asset, but unresolved rows had no structured
  human approval packet.
- New tier: `production_candidate` for Review Packet / Approval Workflow v1 as
  a non-mutating review contract. This does not change writer authority.
- Evidence: `docs/superpowers/specs/review_packet_schema.v1.json` defines
  packet/log schemas and forbids free-form value entry, matrix touch, and
  product authority from review approval.
  `docs/superpowers/validation/review_queue_v1.tsv` contains 3015
  trace-matched unresolved rows as `review_ready`; each row has candidate value,
  area/height/RT fields, trace JSON path, overlay PNG path, one review question,
  and allowed actions
  `approve_candidate;reject_candidate;escalate_unresolved`.
  `docs/superpowers/validation/review_decision_log_v1.tsv` is a structured
  header-only decision log template. The 1087 missing-overlay rows are not in
  this review queue and remain Goal 4 evidence-recovery work.
- Product surface changed: docs/spec/validation/test only. No ProductWriter,
  matrix, workbook, selected peak/area, counted detection, workbook schema,
  CLI/config, extraction default, or GUI behavior changed.
- Validation: focused checkpoint shard passed:
  `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_review_packet_contract.py tests/test_check_productization_authority.py tests/test_productization_authority_mechanical_adjudication.py -v --tb=short`
  (`12 passed`); focused ruff passed for the checker/tests; authority checker
  passed; review packet schema JSON parse passed. Full local gate passed:
  `ruff check xic_extractor tests`, `mypy xic_extractor`,
  `pytest -v --tb=short -x` (`3792 passed, 1 skipped`), and
  `scripts/check_diagnostics_index.py`.
- Remaining blocker: this checkpoint does not implement truth labels, review UI,
  ProductWriter integration, or trace overlay recovery.
- Next checkpoint: after review/commit, proceed to Peak-Choice Truth Set /
  Lockbox v1. Do not treat review approval as ProductWriter authority.

### 2026-06-18 - productization_authority_checker_v1

- Lane: Productization authority firewall / Goal 0-1 hardening.
- Previous tier: `productization_authority_manifest_v1` and
  `mechanical_adjudication_index_v1` were `production_candidate` control
  assets validated by focused pytest only.
- New tier: unchanged, but the authority firewall now has a reusable checker
  entry point.
- Evidence: `scripts/check_productization_authority.py` validates the manifest,
  mechanical adjudication schema, and 4613-row index. It checks fail-closed
  unregistered scope behavior, the 511/4102 authority split, 3015/1087 evidence
  classes, parked broad Backfill, negative-evidence scopes, explanation-only
  sources, and source hashes. `tests/test_check_productization_authority.py`
  adds a forbidden-scope regression test by mutating a non-write row to
  `all_stability`.
- Product surface changed: checker/test only. It does not modify or call
  ProductWriter.
- Validation: focused checker tests passed and
  `$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/check_productization_authority.py`
  returned `Productization authority contract is fail-closed.` Full local gate
  passed with the review-packet checkpoint.
- Remaining blocker: none for the current non-mutating checker contract; it must
  be kept in future productization authority gates.
- Next checkpoint: keep this checker in the PR/local gate set for future
  productization authority changes.

### 2026-06-18 - productization_authority_mechanical_adjudication_v1

- Lane: Backfill product-authority control plane /
  `backfill_standard_seed_guard_scope_v1`.
- Previous tier: broad Backfill auto-write was `parked`; generated policy replay
  remained `production_ready` only for 511 current `write_ready` cells.
- New tier: unchanged for writer authority. The authority/adjudication control
  asset is `production_candidate`: it classifies the current 4613-row
  candidate/audit universe without adding ProductWriter authority.
- Evidence:
  `docs/superpowers/specs/productization_authority_manifest.v1.json` freezes
  current product authority at `backfill_policy_write_ready_rows` / 511 cells
  and marks broad Backfill, quality explanations, quality blockers, and known
  negative-evidence scopes as non-authority. `docs/superpowers/specs/mechanical_adjudication_schema.v1.json`
  defines fail-closed row decisions. `docs/superpowers/validation/mechanical_adjudication_index_v1.tsv`
  classifies all 4613 rows as 511 `write_ready`, 3015 requiring independent
  peak-choice/area truth, and 1087 requiring trace/overlay or reintegration
  evidence.
- Product surface changed: docs/spec/validation/test only. No ProductWriter,
  matrix, workbook, selected peak/area, counted detection, workbook schema,
  CLI/config, extraction default, or GUI behavior changed.
- Validation: focused contract shard passed:
  `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_productization_authority_mechanical_adjudication.py -v --tb=short`
  (`5 passed`), focused ruff passed for the new test file, full ruff passed,
  mypy passed, diagnostics index passed, `git diff --check` passed with only
  LF/CRLF warnings, and full pytest passed (`3785 passed, 1 skipped`).
  Subagent review found stale broad-Backfill wording; current-summary and
  historical-log entries were fixed so broad auto-write is `parked` and future
  work routes through authority/adjudication, structured review, truth, or trace
  evidence.
- Remaining blocker: none for the authority/adjudication contract itself. This
  contract does not implement review packets, truth lockbox labels, or trace
  overlay recovery.
- Next checkpoint: run review/validation, then build structured review packets
  or peak-choice truth/lockbox assets. Do not convert the 3015 or 1087 classes
  into writer pools without a later authority manifest update plus expected-diff
  gate.

### 2026-06-18 - backfill_broad_autowrite_feasibility_gate_v1

- Lane: Backfill product-authority sidecars /
  `backfill_standard_seed_guard_scope_v1`.
- Previous tier: broad Backfill was on implementation hold pending one read-only
  feasibility gate; current writer authority remained 511 `write_ready` cells.
- New tier: `parked` for broad Backfill auto-write. Current 511-cell
  `production_ready` writer authority is unchanged.
- Evidence:
  `docs/superpowers/notes/backfill_broad_autowrite_feasibility_gate_v1.md`
  revalidated artifact hashes and counts, assessed ISTD reference semantics,
  compared the 3015 unresolved trace-matched rows against the 511 approved rows,
  and output exactly `park_broad_backfill`.
- Product surface changed: docs/control-plane only. No ProductWriter, matrix,
  workbook, selected area, counted detection, workbook schema, CLI/config, or
  TSV schema behavior changed.
- Validation: no-RAW artifact inspection only; no 85RAW rerun because existing
  artifacts were sufficient to decide the gate. `git diff --check` passed with
  only LF/CRLF warnings.
- Remaining blocker: broad Backfill can reopen only with a new independent
  truth source for peak-choice / family identity. `quality_blockers`,
  round-trip reintegration, all-stability, apex-delta, width-only, and
  shape-margin cannot be repackaged as a new broad writer path.
- Next checkpoint: stop broad Backfill diagnostics. Continue only existing
  511-cell release hardening or non-broad lanes unless the user approves a new
  independent truth-source proposal.

### 2026-06-18 - backfill_autowrite_ground_truth_strategy_reset_v1

- Lane: Backfill product-authority sidecars /
  `backfill_standard_seed_guard_scope_v1`.
- Previous tier: generated policy replay was `production_ready` for 511 current
  approved-evidence / observed-oracle rows; broad 4613-row Backfill remained
  `production_candidate`, with handoff wording still nudging the next step
  toward choosing another evidence class from blocker-token distribution.
- New tier: unchanged for writer authority. Broad Backfill expansion is on
  implementation hold until a read-only ground-truth packet is reviewed. This is
  a strategy reset, not a product behavior change.
- Evidence: reviewed the 2026-06-18 ChatGPT reset note and Backfill auto-write
  ground-truth strategy note, then recorded the blocking critique in
  `docs/superpowers/notes/2026-06-18-backfill-autowrite-ground-truth-critical-review.md`.
  Revalidated key no-RAW facts: Backfill promotes only MS1 morphology
  `primary_matrix_area`; existing replay artifacts still report 4613 policy
  rows, 511 `write_ready`, 0 `detected_flagged`, 4102 `blocked`, and 511/511
  writer expected-diff pass; targeted ISTD benchmark maps six active ISTDs to
  selected family IDs with 85/85 untargeted positives; a small matrix check over
  those six families found no `>3x median` high outliers and low-side outliers
  in every family.
- Validation: docs/no-RAW artifact inspection only; no RAW or 85RAW rerun.
  `git diff --check` passed with only LF/CRLF warnings.
- Remaining blocker: superseded by
  `backfill_broad_autowrite_feasibility_gate_v1`, which outputs
  `park_broad_backfill`.
- Next checkpoint: do not derive a writer predicate directly from
  `quality_blockers`; do not train/approve rows from the current round-trip
  reintegration oracle alone; do not include `missing_overlay_path` rows without
  regenerated trace evidence; if the gate cannot stay simple, park broad
  Backfill instead of adding more diagnostics.

### 2026-06-17 - sample_metadata_no_output_parity_tier_closeout_v1

- Lane: `sample_metadata_cross_module_parity_v1`.
- Previous tier: `production_surface` for extraction/alignment/
  RT-normalization injection-order parity and instrument-QC sidecar projection;
  `production_candidate` wording for roles.
- New tier: `production_ready` for no-output injection-order projection and
  additive instrument-QC metadata sidecar; `blocked` for any role/batch/matrix/
  exclusion behavior that would change quant output, counted detection,
  normalized values, workbook values, or primary matrix values.
- Evidence: the existing shared resolver in `xic_extractor.sample_metadata` is
  consumed by extraction `injection_order_source`, alignment
  `--sample-column-injection-order`, RT-normalization anchor `--sample-info`,
  and instrument-QC method-doc sidecar projection. The latest full local gate
  after the ReviewAction sidecar slice passed with `3779 passed, 1 skipped`,
  covering these parity tests without changing product values.
- Product surface changed: docs/tier wording only in this closeout. No CLI flag,
  schema column, workbook sheet, matrix schema, selected peak, selected area, or
  counted detection behavior changed.
- Validation: focused sample-metadata parity tests were rerun for this docs
  closeout:
  `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests\test_sample_metadata.py tests\test_injection_rolling.py tests\test_extractor_run.py tests\test_instrument_qc_sequence_manifest.py tests\test_run_instrument_qc.py tests\test_alignment_pipeline_outputs.py::test_pipeline_orders_sample_columns_by_sample_metadata_v1 tests\test_alignment_pipeline_outputs.py::test_pipeline_orders_sample_columns_by_injection_order tests\test_alignment_pipeline_outputs.py::test_pipeline_keeps_input_sample_order_without_injection_source tests\test_rt_normalization_anchors.py::test_injection_reference_accepts_sample_metadata_without_value_effect -q`
  (`63 passed`). No RAW/85RAW rerun is needed because this lane only projects
  metadata into existing order lookup behavior.
- Remaining blocker: role-aware QC/blank/batch/matrix/exclusion behavior still
  needs a separate expected-diff gate and product decision before any value can
  change.
- Next checkpoint: keep role metadata as pass-through context only unless a new
  product contract names the exact output values allowed to change.

### 2026-06-17 - standard_peak_generated_policy_quality_explanation_sidecar_v1

- Lane: Backfill product-authority sidecars /
  `backfill_standard_seed_guard_scope_v1`.
- Previous tier: generated policy replay was `production_ready` for the 511
  current approved-evidence / observed-oracle rows, but the 4102 blocked rows
  were still hard to explain beyond coarse `next_evidence` buckets.
- New tier at the time: unchanged for writer authority. Generated policy replay
  remained `production_ready` only for 511 `write_ready` rows; broad 4613-row
  Backfill was still described as `production_candidate`. This broad-scope tier
  statement is superseded by the 2026-06-18 `park_broad_backfill` decision; the
  sidecar itself remains explanation-only.
- Evidence: `standard_peak_backfill_productization.py` now writes
  `standard_peak_backfill_policy_quality_explanations.tsv` beside
  `standard_peak_backfill_policy.tsv` and records its path/SHA/row count in
  `standard_peak_backfill_policy_summary.json`. The sidecar has one row per
  generated policy row,
  `schema_version=standard_peak_backfill_policy_quality_explanation_v1`,
  `explanation_only=TRUE`, quality blocker count/tokens, and source clean-status
  summary. It does not modify policy row hashes, evidence classes, writer
  authority, expected-diff scope, workbook output, selected peak/area, counted
  detection, or primary matrix semantics.
- Real-data replay: no new RAW run. Existing 85RAW artifacts were replayed
  no-RAW under
  `output/productization_realdata_seed_guard_85raw_20260617/generated_policy_quality_explained_no_raw_productization/`.
  The replay classified 4613 rows as 511 `write_ready`, 0 `detected_flagged`,
  and 4102 `blocked`; writer expected-diff remained 511/511 pass. The
  summary records `backfill_policy_quality_explanation_row_count=4613`, and the
  explanation sidecar has 4613 rows. The top explanation bucket is 1087
  `missing_overlay_path` rows, followed by combined shape/height/width/scan or
  apex-delta blocker combinations.
- Validation: `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests\test_standard_peak_backfill_productization.py -q`
  passed `31`; focused ruff and mypy passed for the productization module/test;
  the no-RAW real-data replay command exited `0`.
- Remaining blocker: this sidecar explains blocked rows; it does not make them
  writable. The old broadening checkpoint is superseded; do not use blocker
  distribution to choose another writer slice.
- Next checkpoint: superseded by
  `backfill_broad_autowrite_feasibility_gate_v1` and
  `productization_authority_mechanical_adjudication_v1`. Future work should
  build review/truth/evidence assets, not a new broad Backfill writer.

### 2026-06-17 - handoff_state_refresh_after_shape_margin_commit_v1

Historical checkpoint before `standard_peak_low_height_scoped_writer_v1`; keep
the later low-height writer entry above as the current tier source.

- Lane: documentation/control-plane closeout for the non-GUI productization
  goal.
- Previous tier: unchanged. Backfill high-signal and low-scan scoped writers
  remained `production_ready`; broad 4613-row standard-path activation and the
  low-height/apex-delta/width-only/shape-margin probes remained
  `production_candidate`; Targeted MS1 headless no-flag limited default
  remained `production_ready`; ReviewAction mutation remained parked.
- New tier: unchanged; this is a handoff drift correction, not a behavior
  promotion.
- Evidence: `cc-framework-improvements-productization.md` still had current
  state wording implying the shape-margin probe was uncommitted, the worktree
  still contained productization diff/untracked files, and no-flag `NL_FAIL`
  default rescue was still unavailable. The handoff now points at committed
  HEAD `3581a9e`, records that productization code/output scope was clean and
  the branch was ahead 12 before this docs-only refresh, and separates the ready
  Targeted MS1 headless default from the still-blocked GUI/broader-target
  surfaces. During this refresh, the only intended dirty scope is the
  handoff/control-plane docs diff.
- Validation: targeted stale-wording grep over the handoff after edit; docs-only
  diff, so no RAW rerun and no matrix/product output validation needed.
- Remaining blocker: none for this handoff drift. Product blockers remain the
  same except broad Backfill is now parked by the later 2026-06-18 feasibility
  gate; ReviewAction mutation needs stable IDs/sidecar/expected-diff approval,
  and GUI/broader Targeted MS1 rescue remain out of this ready claim.
- Next checkpoint: historical. Use the later authority/adjudication handoff as
  the current baseline; do not treat this entry as a prompt for a Backfill
  broadening slice.

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
