# XIC Extractor 對成熟 LC-MS 軟體的 source-grounded parity 與差異化調研

日期: 2026-06-15
狀態: `diagnostic_only`
範圍: 不改 product code；只根據官方文件、公開 source code、本 repo 現況整理策略與 roadmap。

## Executive verdict

前一份結論「XIC Extractor 的差異化在 adduct assay 的 evidence semantics」是對的，但只對一半。真正的產品策略應該是雙層:

1. **Parity floor**: 跟上成熟工具的基本日常能力。沒有 project/method reproducibility、manual boundary/reintegration、batch preset、normalization/QC、export/report contract，再強的 evidence scoring 都會在實用性上被 Skyline、MS-DIAL、MZmine、XCMS 壓過。
2. **Differentiation ceiling**: 把 nucleoside/nucleotide DNA/RNA adduct assay 的化學與定量判斷做成通用工具難以表達的決策層。也就是 `Product State`、`Counted Detection`、`Reason`、candidate-aligned MS2/NL、paired ISTD RT/area relation、RNA applicability、review queue、audit trail 這些不只是報表欄位，而是 assay-aware model selection system。

最重要的戰略修正:

- **不要把自己定位成 generic LC-MS platform 的替代品**。這會輸，因為成熟工具已經有十年以上的 batch engine、GUI、資料格式、社群與測試面。
- **也不要只做 FH replacement**。FH 是下限，不是 benchmark。
- **應定位成 targeted adduct assay workbench**: 在成熟工具該有的 reproducibility/review/export/normalization 上至少不難用，同時在 adduct evidence adjudication 上明顯比通用工具更懂 assay。

一句話: XIC Extractor 要補的不是更多 commodity peak picking，而是 mature workflow surface；要強化的不是「我也有 MS2/NL」，而是「我能把 MS1/MS2/NL/ISTD/RT/RNA applicability 轉成可審閱、可稽核、可被下游信任的定量決策」。

## Evidence base

本次調研使用兩類來源:

- 官方文件: 用來確認公開功能、使用者工作流、CLI/batch/report 等可見能力。
- Source code: 用來看成熟工具如何組織參數、pipeline、feature list、normalization、manual review、audit、export 與 object lifecycle。

| 工具 | 本地 source 快照 | commit | 官方/公開來源 |
|---|---:|---:|---|
| Skyline / ProteoWizard | `output/source_research/pwiz/pwiz_tools/Skyline` | `2f833b1` | [Skyline tutorials](https://skyline.ms/tutorials/25-1/SmallMoleculeQuantification/en/), [ProteoWizard source](https://github.com/ProteoWizard/pwiz/tree/master/pwiz_tools/Skyline) |
| MS-DIAL | `output/source_research/MsdialWorkbench` | `82e9b1d` | [MS-DIAL docs](https://systemsomicslab.github.io/compms/msdial/main.html), [MS-DIAL source](https://github.com/systemsomicslab/MsdialWorkbench) |
| MZmine | `output/source_research/mzmine` | `986640b` | [MZmine docs](https://mzmine.github.io/mzmine_documentation/index.html), [MZmine source](https://github.com/mzmine/mzmine) |
| XCMS | `output/source_research/xcms` | `161fe37` | [Bioconductor xcms](https://bioconductor.org/packages/release/bioc/html/xcms.html), [xcms vignette](https://sneumann.github.io/xcms/articles/xcms.html), [xcms source](https://github.com/sneumann/xcms) |
| XIC Extractor | current workspace | local working tree | `docs/architecture-contract.md`, `xic_extractor/evidence_semantics.py`, `xic_extractor/extraction/result_assembly.py`, `xic_extractor/peak_detection/*`, `xic_extractor/output/workbook_builder.py` |

## Deep Research cross-check

使用者另提供 `<user Downloads>\Compair.md` 作為 ChatGPT Deep Research 結果。本報告把它視為 external cross-check，不把其中 ChatGPT 內部 citation token 當成可直接驗證來源；XIC 現況仍以本 repo source/docs 為準。

Deep Research 與本報告高度一致的地方:

- XIC 的核心不是 generic peak picking，而是把 LC-MS signal 轉成 assay-specific counted detection decision。
- 成熟工具的強項是 operational floor: batch/replay、sample metadata、alignment/gap filling、normalization、export、provenance。
- XIC 不應短期重造 MS-DIAL/MZmine/XCMS 的 untargeted platform，也不應把多 vendor native reader 放在 decision-layer 之前。
- 差異化若只是「多幾欄報表」會被 Skyline/XCMS script 近似；必須落在 data model、review workflow、audit semantics。

Deep Research 補強並修正本報告優先序的地方:

- **Sample metadata + QC/injection order** 應提高到 0-1 個月，而不是只放在 normalization/QC 設計裡。沒有 sample type、QC、blank、calibrator、injection order，cross-sample triage 與 drift correction 沒有地基。
- **Headless batch / CLI replay** 應提高到 0-1 個月。這是 regression testing、golden dataset、CI、批次重算的前提。
- **Cross-sample target table with estimated/gap-filled state** 應成為 1-3 個月核心目標。MZmine 的 `ESTIMATED`、XCMS `fillChromPeaks()`、MS-DIAL gap filling 都提醒: back-fill 可以存在，但不能 silent promotion 成 counted detection。
- **Canonical detection model** 應顯式命名: `Target -> EvidenceChannel -> SignalObservation -> DetectionDecision -> ReviewAction`。這比只說 `EvidenceVector` 更接近產品資料模型。
- **Assay pack / rule pack versioning** 應加入 3-6 個月 roadmap。不要先做過寬 plugin API；先把 adduct-specific rules 版本化、可 diff、可驗證。
- **Vendor-neutral mzML path** 不應是短期主軸，但應明確列為 3-6 個月 parity item: 保留 Thermo RAW best path，同時讓 mzML 經同一 decision layer 跑過，降低單一 vendor 風險。

## Source-level findings by mature tool

### Skyline

Skyline 對 XIC Extractor 最有戰略參考價值，因為它不是只做 untargeted feature detection，而是長期服務 targeted quantitation。

Source/doc 觀察:

- `pwiz_tools/Skyline/CommandArgs.cs` 與 `CommandLine.cs` 顯示 Skyline 的 CLI surface 很成熟: import results、import peak boundaries、export reports、reintegrate、scoring model 等都能被 command line 驅動。
- `CommandArgs.cs` 內至少有 CV refinement normalization-related options，例如 global standards、equalize medians、TIC、isotope label normalization；這支撐「normalization 是 Skyline product surface 的一部分」，但不應單靠這一處 source 宣稱所有 normalization workflow 都完整由 CLI 驅動。
- `CommandLine.cs` 有 peak boundary import、mProphet scoring model、reintegration、report export 等路徑；成熟點不是單一演算法，而是「review -> boundary -> reintegrate -> export」的閉環。
- `Controls/AuditLog/*`、`Model/AuditLog/*` 顯示 audit log 是產品級 surface，不只是 debug log。
- `FileUI/InsertTransitionListDlg.cs`、transition settings、report/export UI 顯示 transition list/method representation 是核心物件。

XIC 應該學:

- **Peak boundary import/export 是 parity floor**。如果 reviewer 在 Excel 或 GUI 裡判斷某個 peak boundary 錯，XIC 必須能把人工 boundary 作為 product contract 讀回、重算 area、留下 audit，而不是只在報表中標注。
- **Reintegration loop 是 parity floor**。成熟 targeted quant 工具不是一次 peak picking 結束；它允許 scoring model/parameter/manual boundary 迭代，且每次輸出可追溯。
- **Report templates / custom reports 是 parity floor**。XIC 目前 workbook 很有 domain value，但若每次下游都綁固定欄位，使用者很快會回到 Skyline custom reports 或手工整理。
- **Audit log 要從「概念」升級為 user-visible history**。XIC 已經有 `AuditTrail` 概念，但要變成 usable workflow，需要記錄 input target、settings hash、boundary override、candidate switch、normalization method、matrix export decision。

XIC 不應該直接學:

- 短期不要 clone mProphet 黑箱統計體系。Skyline 的 mProphet 對 peptide/small molecule transition scoring 很成熟，但 XIC 的差異化應該是 assay-aware interpretable evidence vector。可以借鑑 scoring feature exposure 與 reintegration workflow，而不是把 domain reason 字串換成不可解釋分數。

### MS-DIAL

MS-DIAL 對 XIC 的參考價值在 pipeline decomposition、normalization model、alignment/gap filling 與 annotation/export surface。

Source/doc 觀察:

- `src/MSDIAL5/MsdialLcMsApi/Process/PeakPickProcess.cs`、`Algorithm/PeakSpotting.cs` 顯示 LC-MS peak picking 是 process/pipeline 化的，不是 scattered helper。
- `LcmsPeakJoiner.cs`、`LcmsGapFiller.cs`、`LcmsAlignmentRefiner.cs`、`LcmsAlignmentProcessFactory.cs` 顯示 alignment/gap-fill/refinement 是明確 stage。
- `Parameter/MsdialLcmsParameter.cs` 代表 LC-MS pipeline 使用集中式 parameter object。
- `Model/Statistics/TicNormalizeModel.cs`、`LowessNormalizeModel.cs`、`InternalStandardNormalizeModel.cs`、`InternalStandardLowessNormalizeModel.cs` 顯示 normalization/QC correction 是獨立 model surface。
- `ViewModel/Export/*` 有多種 export model，包括 alignment result、matched product ion、mztab-M、GNPS 等；export 不是最後隨手寫 CSV，而是 workflow-level feature。

XIC 應該學:

- **Normalization/QC 應該成為 first-class stage**。XIC 的 paired ISTD evidence 是強項，但 mature parity 要能明確區分 raw area、ISTD ratio、global standard/TIC、batch/QC correction、normalized export。這不是要立刻實作所有方法，而是先建立 method contract。
- **Alignment/gap-fill 要有 stage identity 與 validation contract**。XIC 現在已經有 evidence-driven selection 方向，但若跨樣本對齊、missing/backfill、target health 只是 diagnostic/output sidecar，實用性仍弱。
- **Parameter object 與 process factory 值得借鑑**。XIC 應把 target assay settings、MS2/NL thresholds、paired ISTD rules、normalization rules、review overrides 組成可保存 method manifest，而不是散在 CLI/config/workbook。
- **Export surface 要多層**: human review workbook、machine-readable TSV/CSV、method/run metadata、evidence vector、normalized matrix 應該各自有 contract。

XIC 不應該直接學:

- 不要追 MS-DIAL 的全域 metabolomics/lipidomics library annotation surface。XIC 的核心不是最大化 compound annotation breadth，而是把 targeted assay 的候選 peak 決策做乾淨。
- 多 vendor support 不該直接拿 MS-DIAL source build 當簡單 oracle。Deep Research 指出 release/source-distributed build 與 CLI/RawDataHandler 場景可能有差異；XIC 比較穩的路線是保留 Thermo RAW best path，再補 vendor-neutral mzML adapter。

### MZmine

MZmine 對 XIC 的參考價值在 modular processing step、typed parameters、batch reproducibility、wizard/preset、feature list lifecycle。

Source/doc 觀察:

- `MZmineProcessingStep.java`、`MZmineProcessingStepImpl`、`SimpleParameterSet`、`ParameterUtils.java` 顯示 MZmine 有非常明確的 module + parameter schema。
- `parameters/parametertypes/*` 有 MZ tolerance、RT tolerance、scan selection、raw file selection、feature list selection、optional module parameter 等 typed parameter surface。
- `modules/tools/batchwizard/builders/BaseWizardBatchBuilder.java` 把 import、mass detection、ADAP chromatogram builder、minimum-search resolver、duplicate filter、isotope grouping、join aligner、gap filling、export/autosave 等組成 batch；ADAP resolver 另作為 MZmine module 存在，但不是這個 builder claim 的直接 grounding。
- `TargetedFeatureDetectionModule`、`JoinAlignerModule`、`MultiThreadPeakFinderModule`、`NeutralLossFilterModule`、`LegacyCSVExportModule` 顯示 targeted detection、alignment、gap filling、neutral loss、export 都是可組合 module。

XIC 應該學:

- **Batch/preset 可重現性是 parity floor**。XIC 應能把一個 assay method 保存成 manifest: raw input set、target table、tolerances、peak detection settings、MS2/NL rules、ISTD pairing rules、normalization/export settings、software version/hash。
- **Typed tolerance/parameter object 很重要**。`mz_tolerance_ppm`、`rt_window_sec`、`nl_tolerance_da`、`isotope_label_type`、`rna_applicability`、`istd_pair_rule` 應被視為 typed method fields，而不是散落的 dict/string。
- **Feature list lifecycle 值得仿照但要縮小**。XIC 不需要 generic feature list universe，但需要 `TargetList -> RawTraceSet -> CandidatePeakSet -> EvidenceVector -> SelectedQuant -> ExportMatrix` 這種 lifecycle。
- **Batch wizard/preset 的精神比 GUI 本身重要**。對使用者而言，能選「adduct targeted quant v1 preset」並重跑，比漂亮 dashboard 更有價值。

XIC 不應該直接學:

- 不要變成模組過多的 generic framework。MZmine 的 module architecture 很強，但 XIC 若完全模仿，會把小團隊維護成本拖垮。應保留少量 domain-specific stages。

### XCMS

XCMS 對 XIC 的參考價值在 scriptable object lifecycle、manual peaks API、RT correction/group/fill 的清楚分層，以及大型資料 on-disk representation 的長期方向。

Source/doc 觀察:

- `R/do_findChromPeaks-functions.R`、`do_adjustRtime-functions.R`、`do_groupChromPeaks-functions.R`、`fillChromPeaks.Rd` 顯示 XCMS 把 peak detection、retention time correction、grouping、missing peak filling 分成明確 steps。
- `R/XcmsExperiment.R`、`R/XcmsExperiment-functions.R`、`R/XcmsExperimentHdf5.R` 顯示 analysis state 是 object lifecycle，不是只有檔案輸出。
- `manualChromPeaks.Rd`、`featureChromatograms.Rd`、`chromPeakSpectra.Rd` 顯示 manual peak 與 chromatogram/spectra extraction 是 API surface。

XIC 應該學:

- **Scriptable API 要和 GUI/report 同權**。成熟科研工具的長壽命通常來自可重跑、可 script、可追蹤的 object API。XIC 的 GUI/Excel review 不應成為唯一 workflow。
- **Manual peak contract 很值得學**。XIC 的 reviewer override 應該像 API 一樣可保存、可重放、可測試，而不是只存在使用者腦中或 Excel 註記。
- **on-disk result object 是中期設計參考**。XCMS 的 `XcmsExperimentHdf5` 支撐 on-disk preprocessing result object / HDF5 storage 的方向；XIC 需要的 chromatogram/evidence cache shape 仍是產品設計推論，不能直接說 XCMS 已給出同型答案。

XIC 不應該直接學:

- 不要把 XCMS 的 untargeted-first RT correction/grouping 全搬進來。XIC 是 target/ISTD/evidence-first，alignment/gap-fill 應服務 target assay，而不是擴張成 untargeted discovery engine。

## XIC Extractor 現況對照

本 repo 現有優勢不是空的，source/doc 已經有明確方向:

- `docs/architecture-contract.md` 已定義 `EvidenceVector`、`PeakHypothesis`、model selection、`AuditTrail`，並說明 evidence provider 不應直接寫入 matrix。
- `xic_extractor/evidence_semantics.py` 有 decision class 與 reason semantics，例如 candidate-aligned MS2/NL support/conflict、paired area ratio support、review semantics。
- `xic_extractor/extraction/result_assembly.py` 已在 result assembly 中整合 paired area ratio、candidate-aligned MS2/NL conflict/support 等 evidence。
- `xic_extractor/peak_detection/model_selection.py`、`hypotheses.py`、`evidence_facts.py` 顯示 peak hypothesis、audit trail、decision class、evidence text 已有雛形。
- `xic_extractor/output/workbook_builder.py` 與既有報告已把 `Product State`、`Counted Detection`、`Reason`、review queue 方向推向 human-reviewable output。

但成熟度缺口也很清楚:

| 面向 | 成熟工具標準 | XIC 現況判斷 | 風險 |
|---|---|---|---|
| Method/project reproducibility | Skyline document、MZmine batch、XCMS object lifecycle、MS-DIAL parameter object | 有 config/run metadata，但還不像 method manifest/project bundle | 實驗室要重跑或審稿時，設定與輸出可追溯性不夠直覺 |
| Manual boundary / reintegration | Skyline peak boundary import/reintegrate、XCMS manual peaks | 有 review queue 與 audit concept，但人工 boundary 讀回與重算閉環仍需強化 | 使用者一旦要修 peak，只能手工處理或離開工具 |
| Normalization/QC | Skyline ratios/normalization、MS-DIAL TIC/LOWESS/ISTD models | paired ISTD evidence 強，但 normalization method surface 仍不夠 mature | 會被成熟工具在日常 quant workflow 上壓過 |
| Batch/preset | MZmine batch wizard、Skyline CLI、MS-DIAL console | 有 CLI/config，但缺少面向 assay 的 named preset/run bundle | 多批資料重跑成本高，難建立 SOP |
| Export/report templates | Skyline custom reports、MS-DIAL 多種 export、MZmine CSV/export | Workbook domain 強，但 machine-readable/report-template 還要產品化 | 下游整合需要改 Excel 或寫 adhoc parser |
| Alignment/gap fill | MS-DIAL/MZmine/XCMS 都是明確 stage | XIC 有方向與 diagnostics，但需明確產品 contract | missing/backfill/selected peak 跨樣本一致性會被質疑 |
| Audit trail | Skyline user-visible audit log | XIC 有 `AuditTrail` 概念，但 user-visible 操作歷史仍需產品化 | 人工審閱與下游 matrix decision 缺稽核閉環 |
| Evidence differentiation | 通用工具可做 transition/product ion/neutral loss，但不是 adduct-specific decision grammar | XIC 明顯較強 | 這是護城河，但要和 mature workflow surface 綁在一起才有產品價值 |

## Capability matrix: parity floor vs differentiation ceiling

下表的「強 / 中 / 很強」是本次 reviewer synthesis，不是 benchmark score。Local source grounding 主要證明能力、模組或 API surface 存在；不代表在同一資料集、同一 assay、同一使用者流程上的量化優劣。Manual review workflow 的最強 parity oracle 是 Skyline；MS-DIAL/MZmine 的 manual/refine surface 應保守視為較不確定。MS-DIAL 的多 vendor 能力也要區分 release build、source-distributed build 與 CLI/runtime caveat。

| Capability | Skyline | MS-DIAL | MZmine | XCMS | XIC 應對 |
|---|---:|---:|---:|---:|---|
| Vendor/mzML input | 強 | 強，但 release/source/CLI caveat 要保留 | 強 | mzML/on-disk 強 | 不把 `.raw` 當護城河；保留 Thermo RAW fidelity，同時讓 importer adapter 化 |
| Target/method model | 很強 | 中-強 | 中 | script-based | 建立 adduct assay method manifest |
| Peak picking/integration | 強 | 強 | 強 | 強 | commodity，不要主打；重點在 candidate decision |
| Manual review/boundary | 很強 | 中 | 中 | API 強 | 必須補，且綁定 evidence/audit |
| Reintegration | 很強 | 中 | 中 | script 重跑 | 必須補，支撐 reviewer override |
| ISTD/normalization | 強 | 強 | 中 | 需 script | 建立 normalization stage，不只 reason 欄位 |
| Alignment/gap filling | targeted 方式強 | 強 | 強 | 很強 | 補 target/ISTD-aware alignment/gap fill，不追 generic untargeted |
| MS2/library/annotation | 中-強 | 很強 | 強 | 中 | 不追廣度；強化 candidate-aligned MS2/NL evidence grammar |
| Neutral loss | 可透過 transition/report/filters 表達 | 有 MS/MS annotation context | 有 NeutralLossFilterModule | 可 script | XIC 應做成 quantified decision evidence，而非單純 filter |
| Custom export | 很強 | 強 | 中-強 | script 強 | 補 report templates 與 machine-readable evidence exports |
| Audit/reproducibility | 很強 | 中 | batch 強 | script 強 | 補 user-visible audit/run bundle |
| Domain-specific adduct decision | 弱-中，可 custom 但非內建 | 弱-中 | 弱-中 | 弱-中 | 這是 XIC ceiling |

## Roadmap: 先補實用性，再加深護城河

### 0-1 個月: 先建立 parity contract，不急著大改演算法

1. **Canonical detection model v1**
   - 類型: differentiation + public contract prerequisite
   - 借鑑: Skyline document rigor、XCMS object/process-history thinking、本 repo 既有 `EvidenceVector` / `PeakHypothesis` / `AuditTrail`
   - 內容: 先以 spec-only 鎖定 `Target -> EvidenceChannel -> SignalObservation -> CandidateEvidence -> DetectionDecision -> ReviewAction`、stable IDs、state transition、review action semantics。
   - 驗證: object-level regression tests 鎖合法 state transition；在此 spec 前，不應先固化 batch replay/export schema。

2. **Assay method manifest v1**
   - 類型: parity + differentiation
   - 借鑑: Skyline document/CLI args、MZmine typed parameter/batch、MS-DIAL parameter object
   - 內容: target table path/hash、RAW/mzML inputs、mz/RT/NL tolerances、peak settings、MS2/NL evidence settings、ISTD pairing、RNA applicability、normalization/export mode、software version。
   - 驗證: 同一 manifest 重跑產生相同 run metadata 與 schema；manifest diff 能解釋輸出差異。

3. **Headless batch / CLI replay**
   - 類型: parity
   - 借鑑: Skyline Batch/CLI、MS-DIAL CUI、MZmine headless batch、XCMS script-first workflow
   - 內容: 至少能用 JSON/YAML project file 重跑 extraction、decision、export；GUI 與 CLI 的 area、state、reason 必須一致。
   - 驗證: golden project 用相同 manifest 重跑，輸出 manifest hash、decision diff、export diff；CLI/GUI parity test 鎖住。

4. **Sample metadata + QC/injection order model**
   - 類型: parity
   - 借鑑: MS-DIAL QC/LOWESS/sample class、XCMS subset-based processing、MZmine batch workflows
   - 內容: sample type、QC、blank、calibrator、study sample、batch id、injection order、replicate/group、exclusion flag 成為正式 metadata。
   - 驗證: 含 QC/blank/calibrator 的 benchmark batch 能驅動 review queue、normalization design、target health summary；metadata 缺失時要明確 fail 或降級。

5. **Peak boundary override import/export design**
   - 類型: parity floor，並可放大 XIC review queue 優勢
   - 借鑑: Skyline peak boundary import/reintegration、XCMS manualChromPeaks
   - 內容: target/sample/candidate id、manual start/end RT、reviewer、reason、timestamp、override scope；boundary override 只負責區間與 area recompute，不得直接強制 `counted_detection`。
   - 驗證: 一個人工 boundary fixture 能重算 area，產生 `ReviewAction` 與 `AuditTrail`；若要改變 counted detection 或 matrix authority，必須另走 expected-diff / activation contract。

6. **Evidence vector export v1**
   - 類型: differentiation
   - 借鑑: Skyline scoring features/report export，但保留 XIC interpretable evidence
   - 內容: 每個 candidate 的 MS1 shape、RT relation、ISTD relation、MS2/NL support/conflict、RNA applicability、decision class、selected/not-selected reason。
   - 驗證: Workbook selected row 可追溯到 candidate-level evidence row。

7. **Report schema / custom export minimal contract**
   - 類型: parity
   - 借鑑: Skyline custom reports、MS-DIAL exports、MZmine CSV export
   - 內容: human review workbook、machine matrix、candidate evidence TSV、run metadata JSON、method manifest copy。
   - 驗證: schema tests 鎖欄位、型別、必填欄；下游 repo 不需要猜欄位語意。

8. **Normalization/QC design note**
   - 類型: parity planning
   - 借鑑: MS-DIAL normalization models、Skyline normalization methods
   - 內容: 明確區分 raw area、paired ISTD ratio、normalization provenance、global standard/TIC、QC LOWESS、batch correction、calibrator curve。先寫 contract，不急著讓 correction 影響 production matrix。
   - 驗證: 每個 output column 都能回答「是否 normalized、用什麼 method、參考物是誰」。

### 1-3 個月: 讓 review/reintegration 成為真正 workflow

1. **Review roundtrip**
   - 讓 Excel/TSV review decision 能讀回 XIC，重算 selected quant，保留 audit。
   - 產品價值: method developer 可以在 XIC 內完成審閱閉環，不必回到手工 Excel。

2. **Target assay project bundle**
   - 包含 manifest、run metadata、candidate evidence、review overrides、exported matrices、logs。
   - 產品價值: SOP、審稿、跨批次追蹤、重跑都可用同一包交付。

3. **Persistent targeted extraction cache / pre-index**
   - 對 Thermo RAW 保留最佳化快取；未來 mzML adapter 使用同型介面。
   - 產品價值: review queue、多輪重審、boundary override/reintegration 不必每次昂貴重掃。
   - 驗證: cold/warm runtime、cache invalidation、settings hash、RAW path parity 都要測。

4. **Calibration / ISTD surface**
   - 先 productionize raw area、paired ISTD ratio、normalization provenance columns；calibrator curve、global correction、batch correction 先列 `spec + shadow_only`。
   - 產品價值: 補 Skyline/MS-DIAL 在日常定量上的成熟度，但不讓 correction 早於 evidence authority。
   - 驗證: paired ISTD ratio correctness 先用 focused fixtures；calibrator series / R2 / back-calculated accuracy 只作 shadow report，不改 counted detection 或 final matrix authority。

5. **Cross-sample target table with estimated/gap-filled state**
   - 允許 expected m/z、RT、ISTD anchor 做 back-fill，但預設不直接 counted。
   - 產品價值: reviewer 可處理 missingness、weak positive、batch consistency，而不是逐檔看 XIC。
   - 驗證: filled vs non-filled 對 final counted detection 的影響必須可解釋；禁止 silent promotion。

6. **Normalization stage v1**
   - 優先順序: paired ISTD ratio + provenance columns 作為 production candidate；global/TIC、QC LOWESS、batch correction 先做 `spec + shadow_only`。
   - 重要限制: normalization 不能掩蓋 evidence conflict；normalized output 必須保留 raw evidence decision。

7. **Target/ISTD-aware alignment/gap-fill contract**
   - 不追 generic untargeted alignment；只服務 target assay 的 selected candidate consistency、missing/backfill、ISTD relation。
   - 驗證: 8RAW/85RAW fixture 中 missing/backfill 的 expected diff 必須可解釋。

### 3-6 個月: 擴大成熟度，但不丟掉 domain focus

1. **Assay-pack / rule-pack versioning**
   - 把 adduct-specific RT、ISTD、neutral loss、candidate MS2、counted detection rules 做成可版本化配置。
   - 驗證: 同一 dataset 跑不同 pack version，輸出 rule-diff 與 result-diff report。

2. **Evidence package for candidate-aligned MS2 / neutral-loss / ISTD checks**
   - 每個 rule 都輸出 reason string 與 evidence blob，而不是只把結果寫成單欄 pass/fail。
   - 驗證: 建立 reviewer adjudication benchmark，測 inter-reviewer agreement 是否改善。

3. **Internal evidence provider protocol**
   - 讓 CID-NL、HCD-PI、Delta Mass、RT/iRT、MS1 isotope pattern、shape、standards/library match 都是 provider。
   - 重要原則: 先從 assay-pack needs 抽 internal protocol；不要先公開 plugin API。Provider feeding `EvidenceVector`，不直接寫 matrix。

4. **Vendor-neutral mzML path under the same decision layer**
   - 保留 Thermo RAW best path；mzML 只替換 data source adapter，不改 decision model。
   - 驗證: 同一 RAW native path 與 mzML-converted path 比對 XIC、area、state、reason 差異。

5. **Interoperability exports**
   - 匯出可給 Skyline/MZmine/XCMS/R 使用的 target/evidence/matrix 表。
   - 目的: 不跟成熟工具完全對立；讓 XIC 成為 adduct evidence decision layer。

## Promotion gate matrix

後續每個 spec 必須標明 `Owner module`、`Forbidden dependencies`、`Public contract touched`、`Initial tier`、`Promotion gate`、`Fail-fast / inconclusive path`。最低要求如下:

| Item | Owner candidate | Public surface | Initial tier | Promotion gate |
|---|---|---|---|---|
| Canonical detection model | `peak_detection` / domain model | IDs, state transitions, review action semantics | `spec_only` | object-level regression + no direct matrix authority |
| Method manifest / batch replay | `configuration` / CLI orchestration | config, CLI, run metadata | `diagnostic_only` | golden project replay diff + GUI/CLI parity |
| Sample metadata | `configuration` / run model | metadata TSV/schema, workbook summaries | `diagnostic_only` | QC/blank/calibrator fixture + explicit missing-metadata behavior |
| Boundary override / review roundtrip | `peak_detection` + `output` boundary | override TSV, review TSV, audit log | `shadow_ready` | area recompute parity + `ReviewAction` audit + expected-diff contract before matrix change |
| Evidence vector export | `peak_detection` / `output` | candidate evidence TSV/schema | `diagnostic_only` | selected workbook row traceable to candidate-level evidence |
| Cross-sample estimated state | `alignment` / selection summaries | target x sample table, state labels | `diagnostic_only` | filled vs non-filled expected diff; no silent promotion |
| Normalization / calibration | output normalization layer | normalized columns, provenance report | `shadow_only` except paired ISTD ratio | raw/ISTD provenance tests before production; QC/LOWESS/calibrator require separate GO/NO-GO |
| Assay pack / provider protocol | domain configuration | rule-pack version, rule diff, evidence blobs | `spec_only` | same dataset pack-version result diff + rule coverage report |

## 最高優先級的 13 個產品補課

這 13 個比新增 peak picking trick 更重要:

1. `canonical_detection_model.md`: stable IDs、state transition、`ReviewAction` semantics。
2. `method_manifest.json`: 每次 run 的 assay method snapshot。
3. `batch_replay.yml/json`: headless extraction/decision/export replay，不依賴 GUI 暗狀態。
4. `sample_metadata.tsv`: sample type、QC、blank、calibrator、batch、injection order、group/exclusion flag。
5. `run_bundle/`: manifest + metadata + logs + candidate evidence + review workbook + machine matrix。
6. `candidate_evidence.tsv`: selected 與 rejected candidate 都要可追溯。
7. `boundary_overrides.tsv`: 人工 boundary/import/reintegration contract，只負責區間與 area recompute。
8. `review_decisions.tsv`: reviewer decision 可讀回，產生 `ReviewAction`，不直接覆蓋 counted detection。
9. `cross_sample_target_table.tsv`: target x sample 狀態表，含 observed/estimated/missing/review-required。
10. `normalization_report.tsv`: raw area、ISTD ratio、normalized area、normalization method、reference source 分清楚。
11. `audit_log.tsv/jsonl`: candidate switch、manual override、normalization/export decision 都要留痕。
12. `assay_pack.yml`: adduct-specific RT/ISTD/MS2/NL/counting rules 的版本化 rule pack。
13. `data_source_adapter_contract`: Thermo RAW 與 mzML 未來必須進入同一 decision layer。

## 不該優先做的事

1. **不要短期追全廠牌 vendor support**。`.raw` direct 的 scoping 合理；mzML support 可作 interoperability，但不是目前最大缺口。
2. **不要追 generic untargeted discovery**。MZmine/XCMS/MS-DIAL 會贏。XIC 的 alignment/gap-fill 應是 target/ISTD-aware。
3. **不要先做漂亮 GUI/dashboard**。成熟度的核心是 review/reintegration/audit/export，不是更豐富的首頁。
4. **不要把 mProphet 式黑箱分數當差異化**。可以學 feature exposure 與 reintegration workflow，但 XIC 應保留 interpretable assay evidence。
5. **不要讓 normalization 先於 evidence contract**。一旦 normalized value 被輸出但 raw evidence conflict 不清楚，產品會變得更危險。
6. **不要把 diagnostic artifacts 說成 production behavior**。TSV、sidecar、report 只能證明 observability；要能讀回、重算、稽核，才是 workflow。
7. **不要把「成熟工具做不到」講太滿**。Skyline/XCMS script/custom report 可以近似很多表面功能；XIC 的差異化必須落在 canonical data model、review semantics、assay-pack decision trace，而不是只有欄位名稱。

## Strategic positioning

建議定位文字:

> XIC Extractor is a Thermo RAW-backed targeted adduct assay workbench for nucleoside/nucleotide DNA/RNA adduct quantitation. It does not try to replace generic LC-MS platforms. Its parity goal is reproducible method execution, headless batch replay, sample metadata/QC support, reviewable peak boundaries, normalization/QC-aware exports, cross-sample target states, and auditable batch processing. Its differentiation is assay-aware evidence adjudication: candidate-aligned MS2/neutral-loss support, paired ISTD RT/area relation, RNA applicability, product-state semantics, counted detection, assay-pack rules, and transparent reasoned decisions.

中文版本:

> XIC Extractor 不是 generic LC-MS 平台的重造，而是 nucleoside/nucleotide DNA/RNA adduct targeted quantitation 的 assay workbench。它必須補齊成熟工具的 method reproducibility、headless batch replay、sample metadata/QC、manual review/reintegration、normalization/QC、cross-sample target state、export/audit 能力；真正差異化則是把 MS1、MS2/NL、paired ISTD、RT、RNA applicability 與 assay-pack rules 轉成可審閱、可稽核、可被下游信任的定量決策。

## 建議下一步

下一步不要直接改 code。先做一組短 spec:

1. `docs/specs/canonical-detection-model-v1.md`
2. `docs/specs/assay-method-manifest-v1.md`
3. `docs/specs/headless-batch-replay-v1.md`
4. `docs/specs/sample-metadata-qc-injection-order-v1.md`
5. `docs/specs/review-roundtrip-and-boundary-overrides-v1.md`
6. `docs/specs/evidence-vector-export-v1.md`
7. `docs/specs/cross-sample-target-table-estimated-state-v1.md`
8. `docs/specs/normalization-qc-surface-v1.md`

每份 spec 開頭必須列 `Owner module`、`Forbidden dependencies`、`Public contract touched`、`Validation tier`、`Promotion gate`。若只能先做第一批，我會做 **canonical detection model + method manifest + headless batch replay + sample metadata/QC**；這四個是後續 review roundtrip、normalization、cross-sample state、evidence export 的共同地基。下一批才是 **boundary override + evidence vector export**。
