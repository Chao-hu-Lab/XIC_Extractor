# XIC Extractor 與成熟免費開源 LC-MS 工具的工程決策比較研究

## Executive conclusion

依照題示，XIC Extractor 的核心優勢不是 generic peak picking，而是把 **訊號** 轉成 **可審核的 assay-specific detection decision**：把 MS1 signal 與 counted detection 分離，對每個 candidate 記錄 Product State、Counted Detection、Reason、Review Queue、candidate-aligned MS2 / neutral-loss、paired ISTD RT / area relation，以及 reviewer-readable audit trail。這一點，與 Skyline、MS-DIAL、MZmine、XCMS 的主設計重心其實不同：Skyline 最強在 targeted quant 的日常操作成熟度；MS-DIAL、MZmine、XCMS 最強在 feature detection、alignment、gap filling、normalization、export、reproducible batch processing 這些「資料處理地板」。因此，XIC 最合理的方向不是變成另一個通用 LC-MS 平台，而是把 mature tools 已經證明必要的實用性底線補齊，再把自己的 evidence-adjudication ceiling 拉得更高。citeturn16search0turn19search0turn22view2turn42view2turn49view0turn50view0turn51view0

**我建議 XIC 必須追平的「實用性底線」有六個：** 第一，**可重播的 project / batch / CLI 模型**，因為 Skyline Batch、MZmine batch XML、MS-DIAL CUI、XCMS script 都把「同一流程可批次重跑」當成一等公民；第二，**結構化 sample metadata + QC/injection-order 模型**，因為 MS-DIAL、MZmine、XCMS 都把 alignment、normalization、drift correction 與 sample/QC metadata 綁在一起；第三，**跨樣本 target table 與 estimated / gap-filled state**，否則 reviewer 只能逐檔看 XIC，無法處理 missingness 與 batch consistency；第四，**ISTD / calibration / normalization 的內建資料模型**，不能只靠 area ratio 的 ad hoc 計算；第五，**規格化 export schema 與 provenance**，讓 reviewer、統計、LIMS、法規/QA 場景都能穩定接；第六，**至少一條 vendor-neutral mzML 路徑**，保留 Thermo RAW 最佳化，但不要把工具生存綁死在單一格式。citeturn19search0turn22view2turn23view0turn42view2turn42view3turn49view0turn50view0turn51view0

**我建議 XIC 應繼續放大的「差異化天花板」有五個：** 第一，**SignalObservation 與 DetectionDecision 分離**，把「看得到訊號」與「可計數」變成不同物件，而不是只存一個 integrated peak；第二，**candidate-level evidence graph**，把 precursor XIC、product ion、neutral loss、ISTD relation、RT agreement 放在同一裁決物件裡；第三，**reason grammar 與 reviewer queue**，讓系統輸出「為什麼不算」而不只是「area = 0」；第四，**審核後可回溯的 audit trail**，把 rule fire、manual override、final state 都保留下來；第五，**assay pack / rule pack**，把 DNA/RNA adduct 特定的判定邏輯變成可版本化、可驗證的組態，而不是藏在 UI 行為或 analyst 習慣裡。這些不是 Skyline / MS-DIAL / MZmine / XCMS 的主軸，因此最值得成為 XIC 的品牌核心。citeturn15view1turn14search7turn23view3turn47view0turn49view0

**XIC 不該盲目追的方向** 也很清楚：不要在短期內重造一個 MS-DIAL/MZmine/XCMS 級的 untargeted platform，不要把研發資源大量投入廣域 spectral annotation ecosystem、molecular networking、IMS / MSI breadth、或多 vendor 原生 reader 全覆蓋。成熟工具已經把這些做成龐大平台；XIC 若照單全收，最容易失去自己最難被取代的價值。尤其 MS-DIAL 官方文件甚至明講，MS-DIAL 主流程固定以 survey scan MS1 計算 peak intensity/area，而真正偏 targeted quant 的 MRM/SRM 資料則由另外的 MRMPROBS 處理；這正說明「untargeted workbench」與「assay-specific quant adjudication」在產品邏輯上原本就是兩條路。citeturn22view2turn22view0turn42view1turn49view1

## Capability matrix

> 註：**XIC Extractor 欄位依題示背景判讀**，因缺少公開文件與原始碼，部分欄位標為 **不確定**。其餘四欄依官方文件、官方 tutorial、官方 repo/source、peer-reviewed 論文整理。
> 標記：**高** = 一等公民；**中** = 可用但較窄；**低** = 能力弱或需外部補足；**不確定** = 公開證據不足。

| 能力面向 | XIC Extractor | Skyline | MS-DIAL | MZmine | XCMS |
|---|---|---|---|---|---|
| raw/mzML/vendor input handling citeturn16search0turn22view0turn26view0turn42view1turn49view0 | **中**：Thermo RAW 核心；mzML 路徑未證實 | **高**：多 vendor small-molecule workflow | **高**：release 支援多 vendor；source-build 受授權限制 | **高**：支援多 raw format 與多平台 | **中**：依 R/Bioconductor 資料容器，實務上多走 mzML / netCDF / on-disk imports |
| chromatogram extraction/cache citeturn10view0turn34view0turn34view2turn42view3turn45view1turn49view0 | **高**：targeted XIC extraction 是核心 | **高**：有持久化 chromatogram cache | **中**：有流程化資料處理，但不是 targeted cache-first | **中**：EIC/feature 由 mass list 與 memory mapping 支撐 | **中**：on-disk/lazy extraction 強，但不是 persistent targeted cache |
| target/transition list model citeturn10view1turn10view2turn16search0turn33view0turn43view0turn51view2 | **中**：應已有 assay target list；公開結構不明 | **高**：molecule / transition / transition-group 是主模型 | **低**：以 project parameters 為主，非 transition-centric | **中**：有 targeted feature detection 與 MRM workflow，但 target model 較輕 | **低**：scriptable targeting 可做，但非一等公民 |
| peak picking and integration citeturn16search9turn21search6turn34view2turn45view1turn51view2 | **中**：足以支撐 targeted quant；非 generic 強項 | **中**：targeted quant 強，generic untargeted 弱於後三者 | **高**：peak picking + deconvolution + alignment 是主軸 | **高**：feature detection / resolver / alignment 模組完整 | **高**：findChromPeaks + 多種 param family 非常成熟 |
| manual peak boundary review citeturn14search7turn16search9turn23view3turn41search6turn51view3 | **高**：題示已含 review queue / reasons / audit | **高**：targeted quant 與 audit review 成熟 | **低到中**：可檢查結果，但官方 tutorial 顯示 refinement 能力有限；**版本狀態不確定** | **中**：可視覺檢查，且有 define manually 類行為，但 reviewer workflow 不如 Skyline | **低到中**：可用 manualChromPeaks / refineChromPeaks，主要是 script review，不是專門審核 UI |
| ISTD / isotope / calibration / normalization citeturn16search0turn23view0turn34view4turn45view4turn49view0 | **中到高**：paired ISTD RT/area relation 是優勢；calibration 內建程度不確定 | **高**：calibrated quantification、internal standards 完整 | **高**：internal standard、LOWESS/LOESS、stable isotope tracking 內建 | **中**：standard compound normalizer、isotope filters 可用，但 calibration curve 非核心 | **中**：scriptable，很強；但多靠 R workflow 組裝 |
| cross-sample alignment / gap filling citeturn16search9turn23view3turn37view0turn44view0turn50view0turn51view0turn51view1 | **低到中**：公開證據不足；若沒有，這是明顯 parity gap | **中**：targeted alignment 有，但非通用 gap-filling 平台 | **高**：alignment + representative file + gap-filling 是主流程 | **高**：join aligner + gap finder 明確成套 | **高**：groupChromPeaks + adjustRtime + fillChromPeaks 是經典主線 |
| MS2 / product ion / neutral loss evidence citeturn16search9turn23view3turn43view0turn42view1turn49view0 | **高**：candidate-aligned MS2 / neutral-loss 是主優勢 | **中到高**：transition / product ion 強，但 neutral-loss adjudication 非主設計 | **高**：deconvoluted MS/MS 與 annotation pipeline 很強 | **高**：MS2 pairing、DIA pseudo MS2、neutral loss filter、spectral search 很完整 | **中**：可抽 spectra、可做 downstream annotation，但 UI/decision layer 較弱 |
| QC and batch diagnostics citeturn23view0turn23view1turn42view2turn43view0turn50view0 | **低到中**：公開證據不足；若缺，會直接傷日常可用性 | **中**：核心 Skyline 可支援，但完整 QC 生態常依賴周邊工具 | **高**：QC sample、LOWESS、PCA、PLS/OPLS 內建 | **中到高**：batch mode、stats dashboard、QC-friendly workflow 完整 | **中**：在 R 腳本與生態系中很強，但 UI 不如 MS-DIAL / MZmine |
| report / export schema citeturn5view3turn22view2turn32view2turn42view2turn49view0 | **中**：若沒有 long-form evidence export，則不足 | **高**：custom reports / report-driven workflow 成熟 | **高**：表格與多種 spectral/export format 很完整 | **高**：feature/export modules 很多，易接外部工具 | **中到高**：scriptable export 很強，但較少 GUI report productization |
| reproducibility / provenance citeturn14search7turn19search0turn26view0turn42view2turn49view0 | **高潛力**：題示已有 reason strings / audit trail；project-level provenance 不確定 | **高**：audit log + repeatable reprocessing 很成熟 | **中**：project/parameter files 清楚，但 audit 粒度較弱 | **高**：batch XML 將步驟明確保存 | **高**：processHistory 與 script-level reproducibility 非常強 |
| automation / CLI / batch mode citeturn19search0turn24search2turn42view2turn42view3turn49view1 | **低到中**：若缺 headless replay，則是關鍵 parity gap | **高**：Skyline Batch/CLI 生態成熟 | **中到高**：有 CUI，但 sample metadata 自動化仍有缺口 | **高**：headless batch 與 CLI 明確 | **高**：R script / BiocParallel 是原生強項 |
| extensibility / plugin architecture citeturn19search19turn28view0turn29view0turn46search16turn47view0turn49view1 | **不確定**：公開插件/腳本 API 未知 | **中**：external tools 與 reports 強，但不是通用 module platform | **中**：source modular，但 public plugin API 不突出 | **高**：核心-模組分離、Module/Parameters/Task 開發模型清楚 | **高**：R/Bioconductor package ecosystem 擴充性最強 |

這張矩陣的核心結論很簡單：**如果比的是「targeted adduct evidence adjudication」的 domain fit，XIC 有機會贏；如果比的是「日常上手、批次處理、跨樣本整理、可重跑、可輸出、可 QC」的 operational floor，成熟工具目前大多更完整。** Skyline 對 targeted quant 的日常操作成熟度特別強；MS-DIAL、MZmine、XCMS 對 alignment / gap filling / normalization / automation 更強。這正是 XIC 的產品策略分界線。citeturn16search9turn22view2turn42view2turn49view0turn50view0turn51view0

## Source-code and architecture lessons by tool

### Skyline

從架構上看，Skyline 最值得學的不是某個 peak picking 演算法，而是 **typed targeted document model + persistent results cache + auditability**。Skyline 的 2014 架構論文明確描述它採用 **immutable document tree**，根節點是 `SrmDocument`，並以 model-view-controller 組織 UI；原始碼中也可直接看到 `pwiz_tools/Skyline/Model/SrmDocument.cs`、`pwiz_tools/Skyline/Model/TransitionDocNode.cs`、`pwiz_tools/Skyline/Model/Results/ChromatogramCache.cs`、`pwiz_tools/Skyline/Model/AuditLog/AuditLogEntry.cs` 等核心類別。這種設計讓「targets / transitions / settings / results / edits」都能掛在一個穩定、可比較、可記錄的模型上。citeturn15view1turn10view1turn10view2turn10view0turn10view3

對 XIC 而言，最可移植的 lesson 有三個。第一，**persistent extraction cache**：Skyline 把昂貴的 chromatogram extraction 與 UI 互動分開，讓 reviewer 不必每次重新抽圖；XIC 若要支撐 review queue，這是必要條件。第二，**typed target hierarchy**：Skyline 在 small-molecule 擴充後，仍保留一個清楚的 molecule-centric / transition-centric 模型，這比把 target、signal、evidence 混在鬆散表格裡更容易保證一致性。第三，**audit log 是產品能力，不是附屬功能**：Skyline 專門做了完整 audit trail，這與 XIC 的 reviewer-readable reason / adjudication workflow 非常相容。citeturn16search0turn16search9turn14search7turn19search0

但 Skyline 也有不適合直接照抄的地方。它的心智模型本質上仍偏 **targeted transition quant environment**；即使支援 small molecules，它的主資料結構仍不是為「signal 存在但不 counted」、「candidate A/B 的 evidence conflict」、「neutral-loss 只對某類 adduct 有效」這類 assay-specific決策而設計。換句話說，XIC 應該學 Skyline 的 **document rigor、cache、audit、automation、reportability**，而不是把自己的 decision object 硬塞回 transition-centric 模型。citeturn15view1turn16search9turn14search7

### MS-DIAL

MS-DIAL 的原始碼提供了很明確的工程 lesson：**common core + modality-specific API + parameter objects + process orchestrator**。repo 結構顯示 `src/MSDIAL5/MsdialCore` 下有 `Algorithm`、`Normalize`、`Export`、`Parameter` 等 shared layers，而 `src/MSDIAL5/MsdialLcMsApi`、`MsdialGcMsApi`、`MsdialLcImMsApi` 等則承接 modality-specific 行為。`MsdialLcmsParameter.cs` 直接繼承 `ParameterBase` 並標記為 `MessagePackObject`；`FileProcess.cs` 以 orchestrator 方式組合 `PeakPickProcess`、`SpectrumDeconvolutionProcess`、`PeakAnnotationProcess`；`Algorithm/Alignment` 下則有 `PeakAligner.cs`、`GapFiller.cs`、`AlignmentProcessFactory.cs`；`Normalize/Normalization.cs` 把 internal standard、LOWESS、IS+LOWESS、TIC 等策略明確封裝成方法入口。這是一個很乾淨的「核心能力共用、流程按 modality 分層」設計。citeturn28view0turn29view0turn30view0turn31view0turn32view0turn32view1turn33view0turn34view0turn34view1turn34view2turn34view4

對 XIC 最值得抄的，不是 untargeted breadth，而是 **parameterization discipline**。MS-DIAL 的 project / parameter model、QC file / reference file / injection order / normalization settings 都是明確組態，而不是 UI 暗知識；其 tutorial 也顯示 QC、alignment、gap-filling、internal standard normalization、LOWESS、PCA/PLS 直接與 sample metadata 相連。這種「所有關鍵步驟必須能落盤、能重播」的設計，正是 XIC 補 practical floor 時最值得借鏡的地方。citeturn22view2turn23view0turn23view1turn23view2turn23view3

MS-DIAL 同時也提供了一個反面教材：**不要為了追 breadth 而模糊產品邏輯**。官方 tutorial 明說，MS-DIAL 主流程總是用 survey scan MS1 計算 intensity/area，而真正針對 MRM/SRM/DIA quant 的需求又另有 MRMPROBS；這其實反映出「untargeted discovery workbench」與「assay-specific quant engine」應該解決不同問題。如果 XIC 把研發重心放到 generic deconvolution、annotation breadth、multi-omics breadth，很可能反而掉進 MS-DIAL 已經走過、而且用另一個產品線分流的領域。citeturn22view2turn22view0

另外要特別註明一個 **uncertain**：MS-DIAL release 版支援多 vendor proprietary format，但 source-distributed “vendor unsupported” build 只支援 abf / cdf / mzML；近期 issue 也顯示 `RawDataHandler` 之類元件會影響某些 CLI/非 Windows 場景。因此，如果 XIC 要學「多 vendor」這件事，最安全的做法不是重造閉源 vendor adapters，而是 **先保留 Thermo RAW 最佳化，再補一條 vendor-neutral mzML 路徑**。citeturn26view0turn38search0

### MZmine

MZmine 給 XIC 的最大啟發是：**把處理流程做成模組化、可保存、可 headless replay 的任務序列**。官方文件把 batch mode 定義為一串 XML tasks；任何方法都能放進 batch file，並可從 GUI 或 CLI 重播。CLI 文件還明確說明 headless batch、input/output override、memory mapping、temp directory 管理。這代表 MZmine 的「可用性」很大一部分不是演算法本身，而是 **workflow-as-artifact**：step list、parameters、intermediate result handling、execution mode 都可保存。citeturn42view2turn42view3

從開發架構看，MZmine 明確推廣 **Module + Parameters + Task** 的模組樣板；module development 文件甚至直接要求新模組建立這三類 class，並指出可從 `java/io/github/mzmine/modules/example` 複製範例。另有開發頁面強調 **application core 與 data processing / visualization modules 的嚴格分離**。這種架構對 XIC 很有價值，因為 XIC 未來極可能同時需要 extraction、evidence scoring、decision rendering、review UI、export、QC 等子系統；若一開始沒有 module/task 邊界，後面很難維護。citeturn47view0turn46search16turn41search1

在資料處理層面，MZmine 的中心物件是 **feature list**。官方 docs 顯示 chromatogram builder 先從 mass lists 建 EIC，再交給 resolver；targeted feature detection 則是以 CSV 中的 m/z / RT 目標，在指定 window 裡找最佳 candidate 並檢查 RT shape；join aligner 以 m/z / RT match score 對跨樣本 features 對齊；peak finder 則回到 mass lists 做 back-filling，並把 gap-filled features 明確標成 `ESTIMATED`。這幾個點都很值得 XIC 移植：特別是 **estimated state**、**back-fill 但不自動視為 counted**、以及 **把 target search 視作第一級模組而不是土炮小工具**。citeturn45view1turn43view0turn44view0turn45view2

不過，XIC 不該複製 MZmine 的整體產品邏輯。MZmine 的目標是成為 **large, flexible, extendable MS workflow platform**，而不是 reviewer-centered adjudication system。它的 feature lists、targeted detection、normalizer、dashboard、networking 都很強，但「為什麼這個 peak 不算」不是它的第一語言。XIC 應該借 MZmine 的 **batch artifact、module/task boundary、estimated state、export discipline**，而不是在短期內追逐它的 100+ modules breadth。citeturn42view0turn42view1turn47view0

### XCMS

XCMS 最值得借鏡的是 **object model + explicit parameter classes + process history + script-first reproducibility**。`XCMSnExp` 官方文件直接說它是儲存 peak detection、alignment、correspondence 結果的 container，並保留 `processHistory()` 以追蹤每個 processing step 與所用設定；它還直接繼承 `MSnbase::OnDiskMSnExp`，因此 raw data 取用在整個流程中都保留下來。repo README 也說 version 4 進一步支援 `Spectra`、`MsExperiment`、`XcmsExperiment`，讓前處理能與更多 Bioconductor 套件自然互通。citeturn49view0turn49view1

XCMS 的方法鏈本身就是一個很清楚的工程分層：`findChromPeaks()` 做 peak detection，`groupChromPeaks()` 做跨樣本 grouping/correspondence，`adjustRtime()` 做 retention-time correction，`fillChromPeaks()` 做 missing peak integration。更重要的是，這些步驟都不是靠大量布林旗標控制，而是靠 `CentWaveParam`、`PeakDensityParam`、`PeakGroupsParam`、`ObiwarpParam`、`FillChromPeaksParam`、`ChromPeakAreaParam` 等 parameter objects 來選演算法與設定。這對 XIC 很有啟發：如果未來要把 adduct-specific rules 做成可驗證工件，**parameter object / rule object** 會比散落 UI preferences 更可靠。citeturn51view2turn51view1turn50view0turn51view0

XCMS 也提醒了一件事：成熟工具的差異化有時能被 script 近似。`findChromPeaks()` 文件明列 `refineChromPeaks()` 與 `manualChromPeaks()`；`XCMSnExp` 又保有 process history 與原始數據可回溯性。這表示如果 XIC 的某些判讀規則只是「自定義峰濾除 + 加欄位 + 匯出」，那麼成熟工具其實能用 R script 近似。XIC 真正應該守住的是 **標準化 reviewer UX、reason grammar、decision object、auditability**；這些不是單靠 R script 就能優雅複製的。citeturn51view3turn49view0

## Gap analysis for XIC

### Parity gaps

如果 XIC 今天缺少 **可重播的 project manifest、batch/CLI、sample metadata/QC、cross-sample target table、estimated/gap-filled state、calibration/ISTD engine、規格化 export**，那這些都屬於 **parity gaps**，不是 nice-to-have。因為 Skyline、MS-DIAL、MZmine、XCMS 雖然設計哲學不同，但都已經把「分析不只是抽一條圖，而是能批次、跨樣本、帶 metadata、可重跑、可匯出」做成基線能力。若 XIC 沒補這一層，它在日常使用上就會被成熟工具直接踩過。citeturn19search0turn22view2turn42view2turn42view3turn49view0turn50view0turn51view0

其中最急迫的 parity gap 是 **跨樣本視角**。MS-DIAL 有 alignment navigator、reference/QC file、gap filling；MZmine 有 join aligner、peak finder 並把 back-filled value 標成 `ESTIMATED`；XCMS 更把 group / adjust / fill 變成 canonical pipeline。若 XIC 仍主要以單檔 targeted XIC 審核為主，就算 evidence layer 很強，也會在 batch consistency、missingness triage、longitudinal drift、review prioritization 上輸掉。citeturn23view3turn44view0turn51view0turn51view1turn50view0

第二個急迫的 parity gap 是 **automation + export**。Skyline Batch 與 audit log、MS-DIAL CUI、MZmine batch XML + CLI、XCMS scripts 都讓資料處理能被版本化與重播。XIC 若沒有 headless replay，就很難做 regression test、golden dataset 驗證、CI、或多批次穩定重算。對一個走向 assay-grade adjudication 的工具來說，這不是工程品味問題，而是可信度問題。citeturn19search0turn24search2turn42view2turn42view3turn49view0

### Differentiation gaps

真正能把 XIC 拉開差距的，不是再做一個更花俏的 peak picker，而是把 **evidence adjudication** 做到成熟工具很難自然達到的程度。第一個 differentiation gap 是 **decision object 不夠顯式**：若系統最後只產出一個 integrated area 與一個 pass/fail，XIC 的優勢就會蒸發。它應該把 `SignalObservation`、`CandidateEvidence`、`DetectionDecision`、`ReviewAction` 明確拆開，讓「看到什麼」與「最後算不算」是兩個可追溯步驟。這和 Skyline 的 immutable document + audit、XCMS 的 process history 一樣，都是把狀態變更變成正式資料。citeturn15view1turn14search7turn49view0

第二個 differentiation gap 是 **reason grammar 與 queueing semantics**。MS-DIAL、MZmine、XCMS 都能表現很多處理結果，但它們的主語言多半仍是 feature、peak、annotation，而不是「counted detection 被否決，因為 ISTD RT mismatch + product ion missing + neutral-loss only weakly supportive」。XIC 若能把這類 reason composition 做成 reviewer 可讀且可篩選的第一級結構，就會比單純 report/export 更難被近似。citeturn23view3turn44view0turn49view0

第三個 differentiation gap 是 **assay-pack 化**。MZmine 與 XCMS 都非常 extensible，但 extensibility 本身不是產品。XIC 最該做的是把 nucleoside/nucleotide DNA/RNA adduct assay 的 RT / ISTD / neutral loss / candidate MS2 / counted detection rules，封裝成可版本化的 assay pack，讓更新規則時能留下差異、驗證結果與影響範圍。這會比開放一個過早、過寬的 plugin API 更符合目前產品定位。citeturn47view0turn49view1

### Traps

最大的陷阱是 **追 generic untargeted parity 到失焦**。MS-DIAL、MZmine、XCMS 的強項是多年累積的 feature detection、alignment、deconvolution、annotation 與 downstream integration；你不可能在短期內把這些平台級能力補齊，而且就算補齊，也未必能提升 XIC 在 adduct adjudication 場景的不可替代性。對 XIC 來說，最危險的不是功能少，而是把工程資源花在錯的方向。citeturn22view0turn42view0turn49view1

第二個陷阱是 **把 differentiation 誤判成「成熟工具做不到」**。事實並非如此。Skyline 已經有 strong targeted quant、audit trail、reprocessing、custom reporting；XCMS 則有 process history、manual/refine hooks、任意腳本邏輯。也就是說，若 XIC 的差異化只是「多幾個欄位、多一份報表、多一個 script」，成熟工具其實能近似。XIC 必須把差異化放在 **資料模型與 reviewer workflow 本身**，而不是放在報表的表面形狀。citeturn14search7turn19search0turn49view0turn51view3

第三個陷阱是 **原生多 vendor 支援先行於 decision-layer 穩定**。MS-DIAL 的 source/release 差異已明確提醒，vendor reader 會牽涉授權、封裝、相容性與跨平台維運成本。對 XIC 來說，更合理的順序是：先保留 Thermo RAW 最佳路徑，再補 mzML 通路確保 portability；等 decision-layer 與 assay-pack 穩定後，再評估是否值得加更多 native adapters。citeturn26view0turn38search0

## Recommended roadmap

| 時程 | 建議項目 | Source inspiration | User value | Implementation risk | Validation strategy | 性質 |
|---|---|---|---|---|---|---|
| 0–1 month | **Project manifest + provenance log**：把 target list version、mass tolerance、RT window、ISTD mapping、decision rules、review overrides、export schema 版本全部落成單一 manifest | Skyline audit log；XCMS `processHistory()`；MZmine batch artifact。citeturn14search7turn49view0turn42view2 | reviewer 與開發都能重播分析 | 低 | 用 golden project 重跑比對 manifest hash、decision diff、export diff | both |
| 0–1 month | **Headless batch / CLI replay**：至少能用 JSON/YAML project file 重跑 extraction、decision、export | Skyline Batch；MS-DIAL CUI；MZmine CLI。citeturn19search0turn24search2turn42view3 | 立刻提升日常可用性、CI、批次重算能力 | 低到中 | 用同一資料集在 GUI / CLI 對比 area、state、reason 完全一致 | parity |
| 0–1 month | **Sample metadata + QC/injection order model**：讓 QC、blank、calibrator、study sample 成為正式型別 | MS-DIAL QC / LOWESS；XCMS subset-based alignment；MZmine batch workflows。citeturn23view0turn23view1turn50view0turn42view2 | 直接改善 batch triage 與 drift 檢查 | 低 | 用含 QC/blank 的 benchmark batch 驗證 metadata 驅動的規則與圖表 | parity |
| 1–3 months | **Canonical detection model**：`Target → EvidenceChannel → SignalObservation → DetectionDecision → ReviewAction`，把 signal 與 counted detection 明確拆開 | Skyline immutable document thinking；XCMS object + param thinking。citeturn15view1turn49view0turn51view2 | 把 XIC 的真正優勢變成穩定資料模型 | 中 | 寫 object-level regression tests；比對 manual review 前後 state transition 合法性 | differentiation |
| 1–3 months | **Persistent targeted extraction cache / pre-index**：對 Thermo RAW 保留最佳化快取；對 mzML 做同型介面 | Skyline `ChromatogramCache`；MZmine memory mapping / temp strategy。citeturn10view0turn42view3turn45view1 | review queue 與多輪重審會快很多 | 中到高 | 大批次測試 cold/warm runtime、cache invalidation、raw/derived parity | both |
| 1–3 months | **Calibration / ISTD engine**：把 calibrator、curve、paired ISTD RT/area expectation、fail reasons 做成正式模組 | Skyline calibrated quant；MS-DIAL internal standard / LOWESS；MZmine standard compound normalizer。citeturn16search0turn23view1turn45view4 | 把 XIC 從「抽圖工具」升級為真正 quant engine | 中 | 以 calibrator series 驗證 R²、back-calculated accuracy、ISTD mismatch reason correctness | both |
| 1–3 months | **Cross-sample target table with estimated state**：允許 expected m/z / RT / ISTD anchor 做 back-fill，但預設不直接 counted | MZmine `ESTIMATED`；XCMS `fillChromPeaks()`；MS-DIAL gap-filling。citeturn44view0turn51view0turn23view3 | reviewer 可快速處理 missingness 與 weak positive | 中 | 比較 filled vs non-filled 對最終 counted detection 的影響；禁止 silent promotion | both |
| 3–6 months | **Evidence package for candidate-aligned MS2 / neutral-loss / ISTD checks**：讓每個 rule 都能給 reason string 與 evidence blob | MS-DIAL annotation/deconvolution viewers；MZmine targeted/neutral-loss modules；XCMS feature/spectra access。citeturn23view3turn43view0turn49view0 | 大幅放大 XIC 的不可替代性 | 中到高 | 建立 reviewer adjudication benchmark；量測 inter-reviewer agreement 是否提升 | differentiation |
| 3–6 months | **Vendor-neutral mzML path under the same decision layer**：不要改 decision model，只換 data source adapter | MS-DIAL source/release split；XCMS / MZmine 的 open-format friendliness。citeturn26view0turn42view1turn49view1 | 降低單一 vendor 風險，擴大可驗證性 | 高 | 同一 raw 經 native path 與 mzML path 比對 XIC、area、state、reason 差異 | parity |
| 3–6 months | **Assay-pack / rule-pack versioning**：把 adduct-specific 判讀規則做成可版本化配置，而不是寫死在 UI | XCMS param classes；MZmine module/task discipline；MS-DIAL parameter model。citeturn50view0turn47view0turn33view0 | 長期維護、法規/QA、跨專案複用都會更穩 | 中到高 | 對同一 dataset 跑不同 pack version，輸出 rule-diff 與 result-diff 報告 | differentiation |

這個 roadmap 的設計原則是：**先補 practical floor，再把 differentiation 變成 hard-to-copy data model。** 也就是說，短期內不要先做更複雜的 generic algorithm，而要先把 replayability、metadata、export、cache、cross-sample states 補齊；等這些底盤穩了，再把 candidate-level evidence packages 與 assay packs 推上去。這樣才能同時縮小實用功能差距，又不會變成「什麼都做一點、但沒有一件做成產品核心」。citeturn19search0turn42view2turn49view0turn50view0

## Open questions and limitations

這份研究有一個重要限制：**XIC Extractor 的分析主要根據題示背景，而不是公開文件或公開原始碼**。因此，凡是涉及 XIC 目前是否已經具備 project manifest、batch mode、multi-sample alignment、calibration schema、export schema 的地方，我都只能從題示強項反推，並把缺乏公開證據的欄位標成 **不確定**。citeturn49view0

另外，**Skyline 的 document grid / custom reports / manual review UI 的原始碼路徑**，在本次可取得的公開頁面中沒有像 `SrmDocument.cs`、`ChromatogramCache.cs` 那樣直接定位到最有代表性的 class，因此對這部分的原始碼級描述，我刻意比其他工具保守；對 **MS-DIAL 手動 refine 能力**，官方 tutorial 文字與當前版本 UI 可能有落差，因此也標了部分 **uncertain**；對 **MZmine manual boundary editing**，本次掌握到的證據顯示它有 visual inspection 與 define manually 類行為，但明顯不是 Skyline 式 reviewer workflow。citeturn23view3turn41search6turn14search7

## Final strategic positioning

**一句話定位：XIC Extractor 應被重新定位為「專為 nucleoside/nucleotide DNA/RNA adduct 定量而設計，能把 LC-MS 訊號轉成可審核 counted detection 決策的 targeted evidence-adjudication workbench」，而不是 Skyline、MS-DIAL、MZmine、XCMS 的 general replacement。** citeturn16search9turn22view2turn42view1turn49view0

更直白地說：Skyline / MS-DIAL / MZmine / XCMS 已經很擅長處理 **「資料怎麼抽、怎麼對齊、怎麼補點、怎麼輸出」**；XIC 不應去和它們全面競逐，而應該在 **「這個訊號在 DNA/RNA adduct assay 中到底算不算 counted detection，為什麼算、為什麼不算、誰改過、根據什麼改」** 這個工作流上做到不可替代。只要 practical floor 補齊，XIC 的真正護城河就不會是「另一套 peak picker」，而會是 **assay-specific evidence adjudication + reviewer-readable reasoning + audit-grade decision traceability**。citeturn14search7turn19search0turn23view3turn49view0
