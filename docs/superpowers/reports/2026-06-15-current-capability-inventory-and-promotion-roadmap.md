# XIC Extractor current capability inventory 與 promotion roadmap

日期: 2026-06-15
狀態: `diagnostic_only`
範圍: 只盤點現有 code/docs/tests 與前一輪 mature-tool 調研；不改 product code。
維護入口: [productization control plane](../plans/2026-06-15-productization-control-plane.md)。

## Executive verdict

你這次的質疑是對的: 前一版 roadmap 讀起來太像「這些都還沒做」。更精準的結論是:

> XIC Extractor 不是功能荒地；它已經有很多 mature-tool parity 的骨架與部分 product surface。真正的問題是 productization unevenness: 有些能力已經能影響正式輸出，有些只在 sidecar/diagnostic/shadow path，有些只有 spec 或測試護欄，還沒有形成使用者可重跑、可審閱、可稽核的產品契約。

所以後續規劃不該是「從零補齊 Skyline / MS-DIAL / MZmine / XCMS 的功能」，而是三件事:

1. **把已經存在的能力收斂成穩定 contract**: schema version、method manifest、review roundtrip、audit/replay。
2. **把 shadow/diagnostic 能力用 gate 推進，而不是直接宣稱 product-ready**: calibration、backfill product-authority、production-candidate gate、full PeakHypothesis matrix。
3. **把真正缺的 mature workflow surface 補上**: manual boundary import/reintegration、first-class sample metadata、batch replay manifest、normalization/calibration activation contract。

一句話: 目前不是「還沒做」，而是「很多已經做在 code 裡，但還沒全部升級成成熟軟體那種可交付、可重跑、可審計的產品面」。

## Maturity label authority

Canonical maturity definitions live in the
[productization control plane](../plans/2026-06-15-productization-control-plane.md).
This report is a dated inventory snapshot and must not be used as the authority
for promoting a feature. If this report and the control plane disagree, the
control plane wins.

## Top-level inventory

| 區域 | 已經很接近成熟的部分 | 主要落差 | 策略判斷 |
|---|---|---|---|
| Domain evidence / canonical detection | `EvidenceDecisionSemantics`、`EvidenceVector`、`PeakHypothesis`、`IntegrationResult`、targeted `Product State` / `Counted Detection` 已存在。 | repo-wide stable detection id、typed `ReviewAction`、durable user-visible audit trail 還沒完整。 | 不要重寫 evidence spine；要做的是 contract freeze 與 review/action/replay projection。 |
| Output / workbook / review | Targeted CSV/workbook schema、`Review Queue`、`Run Metadata`、HTML review report 已有 product surface。 | `Review Queue` 還不是可讀回的 review decision roundtrip；sidecar/report 多但權威邊界不一。 | 優先補 manual review roundtrip 與 schema version，而不是再加更多報表。 |
| Config / CLI / replay | typed config、`config_hash`、`target_config_hash`、headless CLI、validation harness、alignment metadata 已存在。 | 沒有完整 `method_manifest.json` / replay manifest；hash 不是 full method provenance。 | mature-tool parity 的第一優先是 manifest/replay，不是 peak picking。 |
| Sample metadata / QC / calibration | `injection_order_source`、ISTD rolling RT prior、instrument-QC sidecar、calibration maturity gate 已存在。 | first-class sample metadata schema、normalization/calibration primary-matrix activation 缺失。 | 先把 metadata/QC contract 補穩，再談 normalization/calibration 寫入正式 matrix。 |
| Alignment / cross-sample / matrix audit | `AlignmentCell` state、`ProductionDecisionSet`、`alignment_results.xlsx` Matrix/Review/Audit 已是 product surface。 | `alignment_matrix.tsv` output-level 與 spec wording 有 drift；production-candidate/backfill sidecar 不能 silent promotion。 | alignment 不是 docs-only；要做的是 surface naming 對齊與 promotion gate 收斂。 |

## 更正前一版規劃

前一版說「要建立 canonical detection model」容易誤導。更正如下:

- **不是新增一套模型取代現有 code**。現有 `EvidenceVector` / `PeakHypothesis` / `IntegrationResult` / `EvidenceDecisionSemantics` 已經是主要骨架。
- **真正要做的是 canonical product contract**: stable row/detection identity、狀態轉移、manual `ReviewAction`、audit record、replay manifest、matrix activation gate。
- **不是把所有 diagnostic sidecar 一口氣變正式產品**。所有會改 `selected peak`、`selected area`、`Counted Detection`、primary matrix 的功能，都要走 expected-diff 與 activation/export contract。

這也是 mature tools 給 XIC 的最大教訓: Skyline 強的不是某個 peak picker，而是 document/reintegrate/audit/report 的閉環；MZmine/MS-DIAL/XCMS 強的不是單一 gap filling，而是 feature list、metadata、batch/replay、export lifecycle。

## A. Domain evidence 與 detection decision

| Capability | Current tier | Already exists | Gap | Promotion move |
|---|---:|---|---|---|
| Shared decision semantics | `production_candidate` | `EvidenceDecisionSemantics` / `DecisionClass` 可輸出 accepted、review、not-counted、excluded、ambiguous；refs: `xic_extractor/evidence_semantics.py`, `tests/test_evidence_semantics.py`。 | 還不是所有 product outputs 的唯一 authority。 | 把 decision semantics 納入 canonical detection contract，列出哪些 writer 必須使用。 |
| `EvidenceVector` | `production_candidate` | `xic_extractor/peak_detection/hypotheses.py` 已集中 MS1/MS2/NL/quality/prior evidence。 | schema 還在演化，尚未 frozen 為 external contract。 | freeze internal v1，先文件化欄位語意與 provider 接入規則。 |
| `PeakHypothesis` | `production_candidate` | 可承載 candidate/integration/evidence/audit，且 result assembly 已使用。 | stable detection id / row identity 還沒有 repo-wide 全面一致。 | 以 adapter contract 定義 `Target -> Observation -> PeakHypothesis -> Decision -> Export`。 |
| `IntegrationResult` | `production_candidate` | selected integration 會影響 user-facing RT/Area；refs: `xic_extractor/extraction/result_assembly.py`。 | boundary override/reintegration 還沒有完整使用者 roundtrip。 | manual boundary import 必須重算 `IntegrationResult` 並寫 audit。 |
| `AuditTrail` | `partial_internal` | `hypotheses.py` 有 audit object，測試也有 selection/audit 概念。 | 不是 durable operation history；缺 user-visible `ReviewAction` log。 | 不要只加 reason string；要有 action log: who/what/source/before/after/hash。 |
| Targeted product projection | `production_surface` | `Product State`、`Counted Detection`、projection reason 已在 CSV/workbook/report；refs: `xic_extractor/peak_detection/targeted_product_projection.py`, `xic_extractor/output/csv_writers.py`, `xic_extractor/output/workbook_builder.py`。 | projection 是 targeted surface，不等於全部 repo 的 canonical decision state。 | 保留並上收成 canonical projection adapter；不要重造欄位。 |
| Model selection / expected-diff | `production_candidate` | `peak_detection/model_selection.py` 與測試鎖住 model choice 與 expected-diff。 | activation 規則散在不同 path。 | 把所有能改 matrix/area/counting 的 promotion 都掛到 expected-diff gate。 |
| Alignment/backfill activation | `shadow_ready` | shared-peak identity / activation sidecars 已可投影 product candidate。 | product-ready flag 仍未打開；不可直接進 primary matrix。 | 只能當 future activation input；需要獨立 export contract。 |

**白話結論**: 你的 domain evidence 優勢不是空談，很多核心件已經在。下一步不是「做一個 detection model」，而是把已有的 model 變成 repo-wide 共同語言，並讓人工審閱、replay、matrix activation 都必須通過它。

## B. Output、workbook、review、report

| Capability | Current tier | Already exists | Gap | Promotion move |
|---|---:|---|---|---|
| Targeted long CSV schema | `production_surface` | `output/schema.py` 已包含 product projection headers；tests 鎖欄位。 | 缺 schema version / machine-readable schema artifact。 | 加 `schema_version` 與 schema snapshot test。 |
| `Reason` precedence | `production_surface` | CSV writer 與 confidence reason precedence docs 已鎖定 display reason。 | display reason 不等於完整 audit trail。 | 保留 display reason；另建 machine-readable audit/action log。 |
| `Product State` / `Counted Detection` visibility | `production_surface` | workbook/CSV/report 都可見，測試鎖住欄位。 | 欄位權威來源需與 canonical decision contract 對齊。 | 讓 writer 接受 canonical projection，而不是各 writer 自判斷。 |
| Workbook sheet contract | `production_surface` | `Overview`、`Review Queue`、`XIC Results`、`Summary`、`Targets`、`Diagnostics`、`Run Metadata` 已是日常 surface。 | sheet schema growth 需要 versioning；部分 advanced sheets 是 technical audit。 | 定義 workbook contract v1: sheet order、hidden policy、required columns、schema version。 |
| `Review Queue` | `production_surface` | one-row-per-sample-target worklist 已存在；refs: `output/review_queue_model.py`, `output/sheet_review_queue.py`。 | 還不能讀回 reviewer decision，不能重算 boundary/area/counting。 | 做 review roundtrip: import decision -> reintegrate -> update decision/audit。 |
| Review decision roundtrip | `missing` | 目前只看到 workbook input helpers，沒有完整 review loader。 | 缺 `ReviewAction` schema、manual boundary import、candidate switch、audit persist。 | 這是 Skyline parity floor，應列 0-1 month priority。 |
| `Run Metadata` | `production_surface` | workbook 已記錄 `config_hash`、`app_version`、`generated_at`、resolver/smoothing/scoring settings。 | 不是完整 replay manifest；缺 input hashes、CLI flags、RAW/sample manifest、runtime details。 | `Run Metadata` 保持人讀；另寫 JSON `method_manifest.json`。 |
| HTML review report | `production_candidate` | report 可呈現 review burden / product state / confidence。 | 報表是 presentation，不是 decision authority。 | 報表只消費 canonical projection，不重新計算 domain logic。 |
| Candidate/boundary TSV sidecars | `partial_internal` | peak candidate、candidate boundaries、selected envelope diagnostics 已存在。 | 多為 diagnostic/technical audit，權威邊界不穩。 | 先分清 `machine`、`validation`、`debug` output level。 |

**白話結論**: Output 面不是弱，而是已經有不少成熟面。真正要補的是「審閱後能回寫並重算」與「輸出 schema 可版本化」，否則 Review Queue 只是漂亮的 worklist，不是成熟 quantified workflow。

## C. Config、CLI、batch replay、manifest

| Capability | Current tier | Already exists | Gap | Promotion move |
|---|---:|---|---|---|
| Typed config loading | `production_surface` | `ExtractionConfig`、settings parser、GUI advanced settings、tests 都在。 | 缺 public machine-readable settings schema version。 | 加 `settings_schema_version`，但不要大改 config loader。 |
| `config_hash` | `production_candidate` | target CSV + settings bytes hash，CLI overrides 會納入。 | 名稱容易被誤讀成 full method hash；不涵蓋 RAW manifest、sample metadata、runtime、all CLI flags。 | 文件上改成 input-config hash；manifest v1 內引用。 |
| `target_config_hash` | `production_candidate` | target CSV bytes hash，校準/auto-reselection 會用 hash mismatch block。 | 不是 assay/target schema manifest。 | manifest v1 include target hash、schema version、source path。 |
| Headless targeted CLI | `production_surface` | `xic-extractor-cli`、`scripts/run_extraction.py`、expected-diff approvals 已存在。 | 沒有 `--manifest` / `--replay` contract。 | 先定 manifest，再加 replay CLI。 |
| Discovery/alignment CLI | `production_candidate` | `xic-discovery-cli` / `xic-align-cli`、batch index、preflight、85RAW launch guard 已存在。 | batch replay 還是 pipeline-specific，不是 unified project replay。 | 用 `batch_replay.yml/json` 包 raw roots、batch index、flags、expected outputs。 |
| Validation harness / workbook diff | `shadow_ready` | harness 可跑 extraction、compare baseline workbook，忽略 volatile metadata。 | 這是開發 oracle，不是 user-facing replay product。 | 等 manifest v1 後，轉成 golden project replay test。 |
| GUI/CLI parity | `partial_internal` | GUI/CLI 共享 `load_config` 與 `extractor.run`。 | 沒有 fixture 證明同設定產同 workbook/result。 | 加 narrow fake-RAW parity smoke，不先跑大型 GUI e2e。 |
| `method_manifest.json` | `missing` | 目前只有 run metadata、config hashes、alignment metadata fragments。 | 缺完整 method snapshot / input hashes / sample metadata / CLI argv / schema versions。 | 下一個核心 spec: `method_manifest_v1`。 |

**白話結論**: CLI/config 不是沒做；相反地，基礎已經可以支撐成熟 replay。缺的是把一次 run 封成可重建的 manifest。這是成熟軟體感的關鍵，不是演算法問題。

## D. Sample metadata、QC、normalization、calibration

| Capability | Current tier | Already exists | Gap | Promotion move |
|---|---:|---|---|---|
| `injection_order_source` | `production_surface` | settings schema、GUI、config parser、extraction pipeline 都已接入；fallback 是 RAW mtime。 | sample metadata source/hash/status 尚未穩定寫入 provenance。 | manifest/Run Metadata 記錄 path/hash/columns/resolution status。 |
| ISTD rolling RT prior | `production_surface` | injection-order aware rolling prior 已影響 scoring factory。 | 只解決 RT prior，不解決 sample metadata universe。 | 保留；下一步接 sample metadata schema。 |
| First-class sample metadata | `partial_internal` | 現有設定可讀 injection order，instrument-QC 可讀 sequence manifest。 | 缺 `sample_type`、`batch_id`、`matrix_type`、`prep_batch`、QC/blank/calibrator roles。 | `sample_metadata_v1` spec 是 mature parity 0-1 month item。 |
| Instrument-QC sequence manifest | `production_candidate` | `scripts/run_instrument_qc.py`、`instrument_qc/sequence_manifest.py`、writers/tests 已存在。 | 還不是主 extraction project 的 shared metadata contract。 | 抽出 shared sample manifest resolver，避免 QC 與 extraction 各講各的。 |
| Instrument-QC SDOLEK trend sidecar | `production_surface` | opt-in QC sidecar/workbook/report 已存在。 | 不直接改 main matrix。 | 保留為 QC product surface；activation 另定。 |
| Calibration evidence bundle | `diagnostic_only` | level0 bundle 與 manifest 明確 `diagnostic_only`。 | 不可作 correction authority。 | 保留 diagnostic；只用來設計 promotion gates。 |
| Matrix RT calibration preview | `shadow_ready` | rejoinable preview sidecar；測試確認 input matrix bytes 不變。 | 尚未可寫回 main matrix。 | promote 前需要 expected-diff、coverage/extrapolation、blocked-row gate。 |
| Response/intensity calibration | `diagnostic_only` | preview/status blocked。 | biological response transfer gate 缺失。 | 不要短期 productize；先補 QC/sample metadata 與 transfer oracle。 |
| Native normalization/calibration main-matrix write | `missing` | docs 已承認 intensity drift/native normalization 尚未解。 | 沒有正式 activation/export contract。 | 成熟功能要補，但必須最後進 primary matrix。先 shadow、再 candidate、再 expected-diff。 |

**白話結論**: mature tools 的 normalization/QC 是 XIC 現在最容易被踩頭的地方，但不是完全沒基礎。你已經有 injection order、rolling prior、instrument QC、calibration gate；下一步要補的是 sample metadata contract 與「什麼條件下允許改正式 matrix」。

## E. Alignment、cross-sample state、matrix/review/audit

| Capability | Current tier | Already exists | Gap | Promotion move |
|---|---:|---|---|---|
| Cross-sample cell state vocabulary | `production_surface` | `AlignedCell` 有 `group_hypothesis_id`、`gap_fill_state`、`missing_observation_state`、`group_claim_state`；status 包含 detected/rescued/absent/unchecked/ambiguous/duplicate。 | 沒有正式 `estimated` state。 | 不要硬加 `estimated` alias；若要對齊 MZmine 語言，先做 schema migration。 |
| Observed/filled/missing/unchecked semantics | `production_surface` | detected/rescued/absent/unchecked 已投影到 matrix/review/audit。 | pre-backfill/optional path 要持續驗證不繞過 projection。 | 加 release gate: all paths through projection writer。 |
| Matrix numeric value contract | `production_surface` | `ProductionDecisionSet` 控制 include/write/blank reason；primary matrix blanking 有測試。 | runtime config/writer 若分叉可能 drift。 | 所有 matrix writer 只吃 `ProductionDecisionSet`，不要 writer 自判斷。 |
| `alignment_results.xlsx` | `production_surface` | Matrix/Review/Audit/Metadata workbook 已有測試；公式注入防護也有測試。 | schema growth 需 version/ordering contract。 | 可視為 alignment human/operator product surface。 |
| TSV output levels | `production_candidate` | `production` level 包 `alignment_results.xlsx`、`alignment_matrix_identity.tsv`、`review_report.html`；`machine` 才加 `alignment_matrix.tsv` / `alignment_review.tsv`。 | 有 spec 把 `alignment_matrix.tsv` 寫成 primary product output，與 runtime output level drift。 | 先決定 TSV 是否進 production level；未決前不要對下游宣稱 TSV 是唯一 primary output。 |
| Review/Audit TSV sidecars | `shadow_ready` | machine/validation sidecar 有欄位測試。 | 下游不能依賴 sidecar 才理解 matrix。 | 若要 downstream contract，升 output level 並加 schema version。 |
| Owner/backfill gap-fill semantics | `production_candidate` | metadata 已把 legacy owner_backfill 解釋為 gap-fill materialization。 | CLI/config 名稱仍可能誤導。 | 不急著 rename；docs/output metadata 持續用 gap-fill 語意。 |
| Provisional production-candidate gate | `diagnostic_only` | deterministic sidecar 可標 `production_candidate/keep/audit/excluded`，但 summary 明確 not product-ready。 | 不可進 `alignment_matrix.tsv` 或 counted detection。 | 保留為 future promotion input。 |
| Backfill product-authority allowlist sidecar | `shadow_ready` | allowlist/hash/provenance checks 存在。 | summary 仍 `product_ready=False`。 | 只能 challenge/audit；進 primary matrix 前要 activation contract。 |
| Full PeakHypothesis final matrix identity | `partial_internal` | spec/code 有 product row identity 與 projection block。 | no-RAW audit snapshot 仍 `canonical_row_identity_ready=FALSE`，science readiness 未證明。 | 不宣稱 all-family split production-ready。 |

**白話結論**: Alignment 已經比「計畫」成熟很多；不是 docs-only。真正要修的是 output contract 與 promotion wording，尤其避免把 diagnostic gate 或 sidecar 直接說成正式 matrix authority。

## Mature-tool parity 重新定位

成熟軟體給 XIC 的壓力，不是要你複製所有演算法，而是要你補幾個使用者會每天碰到的 product floor。

| Mature-tool pattern | Skyline / MS-DIAL / MZmine / XCMS 給的壓力 | XIC 現況 | 應補方向 |
|---|---|---|---|
| Manual boundary / reintegration | Skyline 有 boundary import、reintegration、audit/report loop。 | XIC 有 Review Queue、candidate/boundary sidecar，但缺讀回與重算。 | `ReviewAction` + boundary import + recompute area + audit trail。 |
| Project/method reproducibility | 成熟工具有 project/document/batch object lifecycle。 | XIC 有 config hashes、Run Metadata、CLI、harness。 | `method_manifest.json` + replay CLI + golden project diff。 |
| Sample metadata/QC roles | MS-DIAL/MZmine/XCMS 都把 QC/sample metadata 放在 workflow 地基。 | XIC 有 injection order 與 QC sidecar。 | first-class sample metadata schema，包含 QC/blank/calibrator/batch roles。 |
| Cross-sample state | MZmine/XCMS gap filling 不會只是空白表；會保留估補/填補狀態。 | XIC 已有 detected/rescued/absent/unchecked 等狀態。 | 鎖定 vocabulary，不新增模糊 alias；把 output-level contract 對齊。 |
| Normalization/calibration | 成熟工具有 normalization/QC correction surface。 | XIC 有 calibration preview/gates，但 main matrix activation missing。 | 先 shadow + expected-diff，再正式 activation。 |
| Audit/history | Skyline 對 audit log 很成熟。 | XIC 有 `AuditTrail` 概念與 reason columns。 | 升級為 durable user-visible operation history。 |

## Roadmap: 從「功能清單」改成「promotion pipeline」

### Phase 0: 現況 freeze，不急著改 code

目標: 停止把已存在能力當缺口重做。

Deliverables:

- 這份 current-state inventory。
- 一份短版 `current_state_contract_map`，列出每個 public surface 的 authority: writer、domain source、tests、maturity tier。
- 對齊前一份 mature-tool report，把 roadmap wording 改成 promotion/replay/roundtrip，而不是 rebuild。

### Phase 1: Contract specs first

優先寫 spec，不先動 product code。

1. `canonical_detection_contract_v1`
   - 不是重寫 `EvidenceVector`。
   - 定義現有 `EvidenceDecisionSemantics` / `EvidenceVector` / `PeakHypothesis` / `IntegrationResult` / `AuditTrail` 怎麼投影成 product decision。
   - 定義 stable ids、state transition、manual `ReviewAction`、matrix activation authority。

2. `method_manifest_v1`
   - 包 settings snapshot、target snapshot/hash、sample metadata path/hash、CLI args、resolver/model version、export schema version、runtime/backend/DLL info。
   - workbook `Run Metadata` 保持人讀；JSON manifest 給 replay/CI/downstream。

3. `review_roundtrip_v1`
   - import Excel/TSV review decisions。
   - manual boundary -> recompute area。
   - candidate switch -> update selected hypothesis。
   - every action writes audit, and output reason/counting must be expected-diff gated。

4. `sample_metadata_contract_v1`
   - sample id、sample type、QC/blank/calibrator role、batch、prep batch、matrix type、injection order。
   - extraction、instrument QC、alignment 共用 resolver。

5. `alignment_output_contract_v1`
   - 決定 `alignment_matrix.tsv` 是 production 還是 machine。
   - 明確 `alignment_results.xlsx`、`alignment_matrix_identity.tsv`、`review_report.html`、sidecar TSV 的責任。

6. `normalization_calibration_activation_v1`
   - 定義 shadow -> production_candidate -> production_ready 的 promotion gates。
   - 沒有 gate 前不改 main matrix。

### Phase 2: 0-6 週 product floor

這階段不做大演算法，只補成熟工作流最痛的缺口。

| Work item | Why now | Existing base | Done when |
|---|---|---|---|
| `method_manifest.json` always emit | replay 與下游信任地基 | config hashes、Run Metadata、alignment metadata | 同一 manifest 可重跑 fixture，並產生可比較 outputs。 |
| Review decision import | Skyline parity floor | Review Queue、candidate/boundary sidecars | 一個人工 boundary fixture 能重算 area 並留 audit。 |
| Schema versioning | 下游 contract | CSV/workbook/output schema tests | CSV/workbook/TSV 都能說出 schema version。 |
| Sample metadata resolver | QC/normalization/cross-sample 地基 | `injection_order_source`、instrument QC manifest | extraction/QC/alignment 讀同一 metadata contract。 |
| GUI/CLI parity smoke | 避免 product surface 分叉 | shared `load_config` / `extractor.run` | 同 fixture 的 CLI/GUI path 產出同 structured result 或 workbook diff。 |
| Alignment output wording fix | 避免 downstream contract drift | output levels + workbook contract | docs/runtime/tests 對 production vs machine output 一致。 |

### Phase 3: 6-12 週 workflow maturation

目標是讓 XIC 在「日常可用性」上不輸成熟套件太多。

- Golden project replay: manifest + RAW fixture + expected workbook/matrix diff。
- Review/reintegration loop: reviewer actions can be applied repeatedly without losing provenance。
- QC role-aware reporting: blank/QC/calibrator/sample 不再只是外部表格文字。
- Calibration/normalization shadow comparison: primary matrix unchanged, sidecar explains expected changes。
- Report/export profiles: 固定下游欄位與 review/audit 欄位分層，降低 Excel 手工整理成本。

### Phase 4: 3-6 個月 differentiation ceiling

這階段才強化真正比成熟工具難模仿的東西。

- Assay/rule pack versioning: adduct-specific rules 可版本化、可 diff、可 replay。
- Multi-evidence provider plug-in internal protocol: CID-NL、HCD-PI、delta mass、RT/iRT、MS1 pattern、standards/library evidence 都 feeding `EvidenceVector`，不直接寫 matrix。
- mzML path through same decision layer: 不把 vendor-neutral reader 當差異化，但降低 Thermo-only 風險。
- Learned model 只能當 evidence provider，不可繞過 interpretable decision/audit。

## What not to rebuild

這些不要重做，否則會浪費已經有的優勢:

- 不要重寫 `EvidenceVector` / `PeakHypothesis` / `IntegrationResult`。要 freeze/adapt，不是替換。
- 不要把 `Review Queue` 改成另一套報表。要補 import/reintegration/audit。
- 不要把 `config_hash` 假裝成 full method hash。要新增 manifest。
- 不要新增 `estimated` state 只為了像 MZmine。現有 `rescued/gap_fill_rescued/queried_and_detected/unchecked` 比較精確。
- 不要直接 productize `production_candidate_gate` 或 backfill product-authority sidecar。
- 不要在 sample metadata/QC gate 還沒穩之前把 normalization/calibration 寫回 main matrix。
- 不要突然 rename `owner_backfill` public CLI/config；先用 docs/metadata 解釋 gap-fill 語意。

## Concrete promotion matrix

| Existing artifact | Current role | Risk if overclaimed | Next promotion step |
|---|---|---|---|
| `Product State` / `Counted Detection` | product output | 若各 writer 自行判斷，decision 會 drift。 | canonical projection adapter + schema version。 |
| `Review Queue` | human review worklist | 不能回寫，會被 Skyline reintegration 踩頭。 | `ReviewAction` import + audit + recompute。 |
| `Run Metadata` | human-readable provenance | 被誤當 full replay manifest。 | JSON method manifest sidecar。 |
| `config_hash` / `target_config_hash` | input hash fragments | 被誤解成 method hash。 | manifest 中明確命名與 scope。 |
| validation harness | dev oracle | 被當成 user replay product。 | manifest-driven golden replay。 |
| instrument-QC reports | QC product sidecar | 被誤認可直接 correction matrix。 | sample metadata + calibration activation gates。 |
| calibration preview | shadow output | silent correction primary matrix。 | expected-diff + transfer oracle + blocked-row gate。 |
| `ProductionDecisionSet` | alignment matrix authority | writer 繞過就 silent promotion。 | release gate 確認 all matrix writes through it。 |
| `production_candidate_gate` | diagnostic sidecar | 名稱讓人誤以為可進 product matrix。 | rename/wording guard: candidate only, not promotion。 |
| backfill product-authority sidecar | challenge/audit input | 未 product-ready 卻改 matrix。 | activation/export contract before matrix write。 |

## Immediate recommended next action

我建議下一步不是立刻改 code，而是把這份盤點拆成 4 份短 spec，每份都能直接變成 implementation PR:

1. `method_manifest_v1`
2. `review_roundtrip_v1`
3. `sample_metadata_contract_v1`
4. `alignment_output_contract_v1`

原因很直接: 這四個 spec 會把現有半成熟能力往 product surface 推進，而且每個都能被成熟工具對比驗證。相反地，如果現在直接寫更多 peak scoring 或 diagnostic sidecar，會繼續累積「其實做了，但使用者感受不到成熟」的問題。

## Subagent review coverage

本盤點整合了五個 read-only 分區複查:

- Domain evidence / canonical detection model。
- Output / workbook / review / report。
- Configuration / CLI / batch replay / manifest。
- Sample metadata / injection order / instrument QC / normalization-calibration。
- Alignment / cross-sample state / matrix-review-audit。

所有分區結論都指向同一件事: XIC 現在最大的工程任務不是補齊一堆從未存在的功能，而是把已存在的 internal/shadow/diagnostic pieces 推成穩定、可重跑、可審閱、可稽核的產品契約。
