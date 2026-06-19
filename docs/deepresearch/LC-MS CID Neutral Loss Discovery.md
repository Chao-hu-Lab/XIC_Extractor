# LC-MS/MS CID Neutral-Loss Discovery 的成熟作法研究與建議架構

## 研究結論摘要

把 **scan precursor m/z** 直接當成「唯一真 precursor identity」在 DDA/CID neutral-loss discovery 裡並不穩健。開放格式 mzML 本身就把 **selected ion m/z** 與 **isolation window target m/z** 分成不同概念；前者是被選中的離子 m/z，後者是 isolation window 的中心或參考 m/z。Thermo 官方文件更直接指出：在啟用 MIPS 時，**raw file 可寫入 monoisotopic peak m/z，但實際 isolation 仍可中心在 isotopic cluster 中最豐的峰**。也就是說，檔案中的 precursor 欄位、實際被四極桿隔離的目標、以及真正應該歸屬的 MS1 feature，不必然是同一個數值。citeturn22view0turn21view0turn34view0

成熟 untargeted 軟體的共同模式不是「用 MS2 決定 row」，而是 **先做 MS1 feature detection / grouping，再把 MS2 當作附屬證據掛回 feature**。MZmine 的 untargeted workflow 先由 MS1 chromatogram builder 與 resolver 建 feature list；之後才用 precursor m/z 與 RT 把 MS2 pair 回 feature。XCMS 先做 chromatographic peak detection 與 correspondence analysis 形成 feature definitions；`chromPeakSpectra()` / `featureSpectra()` 再把 MS2 依 RT 與 precursor m/z 掛到 peak/feature 上。OpenMS 也是先由 `FeatureFinderMetabo` 建 feature，再做 adduct grouping、feature linking 與 MS2 mapping。Compound Discoverer 亦明確分成 Detect Feature → Group Features → Assemble Compounds 三段。這些工具都在設計上把 **row creation** 與 **annotation/identification** 分離。citeturn27view1turn27view2turn27view0turn29view0turn29view1turn29view2turn30view0turn30view1turn16view0turn16view1

對你的情境，最穩健的 product-ready 設計不是 A 或 B 單一路徑，而是 **C 為主、D 為實作**：先用 MS1 建 row identity，再同時使用多條證據路徑把 MS2 掛回去，包括 scan precursor、isolation window、feature boundary、以及 `product + configured neutral loss` 回推得到的 candidate precursor。這條 `product + NL` 路徑很重要，因為它能補救 precursor 誤選 isotope、instrument target 偏移、co-isolation 或 monoisotopic assignment 失準所造成的漏抓；但它不應直接成為 matrix-writing authority。真正寫 row 的權威仍應回到 **可觀察的 MS1 chromatographic feature**。這個設計方向和 MZmine/XCMS/OpenMS/CD/GNPS 的 feature-first 思路一致，也和 OpenMS `HighResPrecursorMassCorrector` 會把「打在 isotope trace 上的 MS2」映回 monoisotopic precursor 的做法一致。citeturn30view1turn27view0turn29view2turn16view0turn39view0

你的實例裡，`184.113 + 116.0474 ≈ 300.160` 落在人工可見的 MS1 feature，而部分 scan/filter precursor 卻出現 `300.203 / 300.180 / 301.165`，這種現象在原理上完全合理：一部分可能是 isotope-related selection；一部分可能是 isolation/selection 層的目標值與 monoisotopic identity 不同；另一部分可能是 chimeric/co-isolated MS2。公開文獻與工具都顯示，DDA 的 precursor isotope misassignment 需要額外更正並會實際影響 downstream 結果；而 DDA MS2 也常出現 chimeric spectra。citeturn34view0turn31search0turn25search1turn3search2turn40search11

## 成熟軟體比較表

下表只聚焦你在意的 **Discovery row creation**、**MS2 掛載**、**neutral loss/product evidence 的角色**，不把 library score 當成 row authority。表中的「代表性做法」是根據公開文件整理出的高信心結論；若官方文件沒有明講某細節，我會明確標示。citeturn27view2turn29view2turn30view1turn16view0turn39view0

| 軟體 | Row creation 的主體 | MS2 如何掛回 row | Neutral loss / product-ion 在系統中的角色 | 重複 MS2 / same peak 處理 | 對你的 pipeline 啟示 | 來源 |
|---|---|---|---|---|---|---|
| **MZmine** | 先用 **MS1 chromatogram builder** 建 EIC，再用 resolver 切成 feature；feature list row 是中心資料結構。 | `Assign MS2 to feature` 以 **feature m/z + RT** 去配 MS2 precursor；可要求 **feature edges** 內才接受；同一 MS2 可配到多個 feature；另有 relative-height filter 避免弱共洗脫 feature 搶到主峰 MS2。 | 有 **Diagnostic Fragmentation Filter**，可用 product ion / neutral loss 篩 MS/MS；它是 **post-acquisition spectral filter**，不是原生 row-creation authority。 | 一個 feature 可收多張 MS2；pairing 後用 feature apex distance 等 metadata；對 overlapping features 以 relative-height refinement 降低誤掛。 | 很接近你要的模式：**先建 MS1 row，再掛 MS2**；NL 應做成「找證據 / rescue」，不是直接寫 row。 | citeturn27view1turn27view2turn27view0turn37view0turn42search1 |
| **MS-DIAL** | `Peak spot` 是 detected peak / precursor-ion feature；`Alignment spot` 是跨樣本對齊後的 row，含 RT、accurate mass、intensity 與 MS/MS。 | 文件強調 alignment spot 帶有 MS/MS，並會為對齊結果選 **representative spectrum**；公開文件對「單一 peak 下多次 DDA」的 collapse 細節沒有像 MZmine 那樣明講。 | 內建 **product ion / neutral loss search**，可對 peak spot 與 alignment spot 搜尋具特定 product/NL 的 precursor。 | alignment 層會保留 representative spectrum；若未辨識，代表譜通常取最高豐度樣本。 | MS-DIAL 也把 **peak spot / alignment spot** 當 row 主體；product/NL 搜尋是 **row 之上的查詢與註解工具**。 | citeturn28view0turn28view1turn28view2turn32search3turn41search0turn41search12turn41search13 |
| **XCMS** | 先做 **chromatographic peak detection**，再做 **groupChromPeaks** 形成 mz-rt feature；featureDefinitions 是 grouped peaks within/across samples。 | `chromPeakSpectra()` 取 peak 內所有 MS2；條件是 **RT 落在 peak 範圍內且 precursor m/z 落在 peak m/z 範圍**。`featureSpectra()` 再提升到 feature 層。 | XCMS 本體重點是 preprocessing；MS2 是掛在 peak/feature 上。NL 本身不是 row-creation 主軸。 | 一個 feature 可含多個 chromatographic peaks；`featureValues()` 可用 `medret`/`maxint`/`sum` 解決同一 sample 多 peak 對同一 feature 的整併。 | 對你的設計最重要的訊息是：**row = chromatographic feature**，MS2 是依 RT/mz 掛上去；同一 sample 多 evidence 必須有明確 collapse policy。 | citeturn29view0turn29view1turn29view2turn38search1 |
| **CAMERA** | 不自己做 row creation；它吃 xcms 輸出的 peak list。 | 不主導 MS2 pairing。 | 主要做 **isotope / adduct / fragment annotation**，並以 `groupFWHM` / `groupCorr` 形成 pseudospectra。 | 以 peak shape / correlation / FWHM 做 annotation grouping。 | 很適合當作你的「**annotation layer**」概念參考，不適合作為 row authority。 | citeturn6search0turn6search1turn6search5 |
| **OpenMS** | `FeatureFinderMetabo` 把 mass traces 組成 feature，並可聚合同位素 traces。跨樣本再 link 成 consensus features。 | 文件明示 untargeted metabolomics workflow 先做 feature detection/linking，**MS2 spectra 再 map 到 feature**；`HighResPrecursorMassCorrector` 可把打在 isotope trace 上的 MS2 映回 monoisotopic precursor。 | 官方文件重點放在先有 feature，再把 MS2、adduct、formula/structure annotation 掛上。 | feature mapping 與 consensus linking 是主軸；對 precursor misassignment 有專門 correction。 | 對你的需求最直接：你必須支援 **precursor correction / isotope-to-mono remap**，否則會漏掉真 feature。 | citeturn30view0turn30view1turn9search1 |
| **Skyline** | 本質是 **targeted / hypothesis-driven** 文件導向分析，不是典型 untargeted feature discovery engine。 | 以已知 precursor / transition / molecule list 為核心去抽取 chromatograms。 | product ion、precursor、library score 都是對既有 target 的量化與審查，不適合作為 unsupervised row-creation 規範。 | 會在 target 框架下整合多 transitions / replicates，但不是你這題的主要參考對象。 | 可借鏡其 audit/review 觀念，但**不應拿 Skyline 當 untargeted CID-NL row creation 的主典範**。 | citeturn14search0turn14search1turn14search5 |
| **Thermo Compound Discoverer** | 官方明示：**Detect Feature** 先在每檔做 untargeted feature detection；**Group Features** 再跨檔 grouping 成 Features table；之後 **Assemble Compounds** 才組 ions / compounds / MS1 fragments。 | `Group Features` 會選 representative MS1/MS2 scans；`Assemble Compounds` 用 feature 為輸入，進一步組 adducts、MS1 fragments，並供 search/ID 使用。 | NL/product evidence 屬於 compound assembly / identification 證據，不是 feature table 的初始 authority。 | `Max MS Trees`、`Consolidate MS Tree`、peak rating、remove singlets，都顯示它會先把 feature 層整理穩，再往 annotation 前進。 | 這是商業軟體中最清楚支持你需求的證據：**Features table 先於 compounds/IDs**。 | citeturn16view0turn16view1turn16view2 |
| **Thermo TraceFinder** | 主要是 **targeted screening / routine quantitation / unknown screening** 平台，不是最典型的 untargeted LC-MS feature table builder。 | 搜尋核心圍繞 RT、fragment ions、isotopic pattern、library match。 | product / fragment evidence 是 method-driven screening 核心。 | 偏 method / assay review，不是你要的 discovery-row dedup 中心。 | 可參考其 review fields，但不建議當主要 discovery architecture 範本。 | citeturn17search0turn17search6turn17search12 |
| **GNPS FBMN / IIMN** | 不自己做原始 row creation；它要求先由 MZmine/OpenMS/MS-DIAL/XCMS 等生成 **feature table + MS/MS spectral summary**。 | FBMN 連的是 feature table 與 spectra summary；IIMN 另依 **RT、peak shape、user-defined parameters** 連同一 neutral molecule 的不同 ion species。 | product/NL 不負責原始 row creation；GNPS 假定 row 已由 preprocessing tool 建好。 | IIMN 會把同一中性分子的不同 ions 連起來，但不是把錯誤 precursor 直接寫成新 feature。 | GNPS 的設計再次支持：**先有 feature row，再談 MS2/network/ion identity**。 | citeturn39view0turn39view2 |

**總結一句話：** 我沒有在成熟軟體中找到「把 `observed product + configured NL` 直接當成 row-creation authority」的主流實作；主流模式幾乎都是 **MS1 feature row 先建立，MS2/NL 再作為 feature 的 evidence 或 annotation layer**。citeturn27view2turn29view2turn30view1turn16view0turn39view0

## Scan precursor 與 true precursor identity 的概念釐清

### 這幾個欄位不是同一件事

在資料模型上，至少要分清楚四層。mzML 的 **selected ion m/z** 是「被選中的離子 m/z」；**isolation window target m/z** 是 isolation window 的中心或參考 m/z；Thermo 的 MIPS 文件又額外說明，raw file 可寫入 monoisotopic peak m/z，但 isolation 可中心在 isotopic cluster 中強度最高的峰。這代表「scan 裡記錄的 precursor m/z」和「實際隔離中心」本來就可能不同，更不要說它們與「真正應歸屬的 MS1 chromatographic feature apex m/z」還隔了一層 feature interpretation。citeturn22view0turn21view0turn34view0

因此，在你的系統裡，**scan precursor** 應被視為 acquisition-layer evidence，而不是 row identity。本質上它比較像「儀器當下認為值得 fragment 的 target 訊號」，不是最後資料表中 feature 的法律身份。成熟工具也幾乎都把 feature detection 與 MS2 assignment 分階段實作，而非讓單一 MS2 header 決定 row。citeturn27view0turn29view2turn30view1turn16view0

### 為什麼 scan precursor 會和真實 feature 不一致

最常見的原因之一是 **同位素相關的 precursor selection / monoisotopic assignment 問題**。Thermo 官方說得很清楚：啟用 MIPS 時，raw file 可寫入 monoisotopic peak m/z，但 isolation 仍可能對準 isotopic cluster 最強的峰；OpenMS 之所以提供 `HighResPrecursorMassCorrector`，也是為了把「量到 isotope trace 上的 MS2」重新映射到 monoisotopic precursor。外部研究也顯示，precursor isotope misassignment 在 Orbitrap 資料上是實際存在且足以影響 downstream identification 的。citeturn34view0turn30view1turn31search0turn25search1

另一個大宗原因是 **co-isolation / chimeric spectra**。即使 DDA 使用相對窄的 isolation window，公開研究仍指出 chimeric MS2 很常見，且近年的文獻甚至用「超過一半的 DDA spectra 是 chimeric」來描述這個問題。這會導致 product ion 與 scan precursor 並不屬於同一個中性分子，也就會出現你看到的 `product + NL` 回推到某 MS1 feature，但 scan precursor header 卻偏去另一個值的現象。citeturn3search2turn23search3turn23search20turn40search11

再來是 **實際 feature apex m/z 與 scan-level target m/z 的時間差/取樣差**。DDA 是以 cycle-based、即時排序去打碎 precursor，不一定正好發生在該 feature 的 apex；而成熟工具的 row identity多半用 feature 的整個 chromatographic trace、peak edges、apex RT 與 feature-level m/z 統合後定義，而不是直接沿用某一張 MS2 的 header。這也是為什麼 MZmine 用 feature edges、XCMS 用 peak RT/mz range、Compound Discoverer 用 Detect/Group Features 先形成 Features table。citeturn37view0turn29view2turn16view0turn16view1

### 你應該怎麼定義 true precursor identity

對 discovery row creation 而言，**true precursor identity 最合理的 operational definition 不是 scan header，而是可重建的 MS1 chromatographic feature identity**：至少包含 `sample/file`、`feature apex m/z`、`mz range`、`RT apex`、`RT start/end`、以及必要時的 isotope/adduct state。MS2 只提供對這個 feature 的 supporting evidence，包括 fragment ions、neutral loss、representative MS2、purity/chimeric 狀態。這與 XCMS、MZmine、OpenMS、Compound Discoverer、GNPS 的共同設計方向一致。citeturn27view2turn29view1turn29view2turn30view1turn16view0turn39view0

## CID-NL Discovery 的建議架構

### 設計原則

我建議你的系統採取 **MS1-first, evidence-late** 架構：**row identity 由 MS1 feature 決定；scan precursor 與 `product + NL` 都只扮演 evidence path**。這不是保守而已，而是最符合成熟軟體現況的設計：MZmine、XCMS、OpenMS、Compound Discoverer、GNPS 都先有 feature table / feature row，再掛 MS2 或 annotation。citeturn27view2turn29view2turn30view1turn16view0turn39view0

在這個前提下，你的 CID neutral-loss discovery 不應只靠 `scan precursor - NL` 去找 product，也不應讓 `product + NL inferred precursor` 直接寫成 row。最成熟的做法是同時跑兩條路，再回到 MS1 feature table 收斂：第一條是 **scan-anchored path**，利用 scan precursor / isolation window 去檢查 product 是否支持指定 NL；第二條是 **product-anchored rescue path**，從 observed product + configured NL 回推出 candidate precursor，再到 MS1 feature table 找是否存在合理 feature。最終 row 是否成立，要由 MS1 feature 是否存在、是否形成清楚 chromatographic peak、以及該 feature 是否吸收多張相關 MS2 來決定。citeturn27view0turn30view1turn16view0turn42search1

### 建議的資料流程

建議流程如下。先在每個 sample 做 **MS1 feature detection**，取得平滑後 trace、peak boundaries、apex、area、height、mz range 與 isotope/adduct candidates。這一步就是 row 候選池。之後把每張 DDA MS2 視為「要指派給哪一個既有 feature」的問題，而不是「要不要新生一個 row」的問題。這與 MZmine 的 `Assign MS2 to feature`、XCMS 的 `chromPeakSpectra()` / `featureSpectra()`、OpenMS 的 feature mapping、CD 的 Detect/Group Features 都一致。citeturn37view0turn29view2turn30view1turn16view0

MS2 指派時，先抓取 acquisition-layer metadata：`selectedIonMz`、`isolationWindowTargetMz`、`isolationWindowLower/UpperOffset`、charge、若有則 `monoisotopicMz`、scan RT、activation type/energy。之後跑兩個 matcher。**Matcher A** 用 scan precursor / isolation window 與 feature m/z/RT bounds 對上候選 feature。**Matcher B** 在該 MS2 裡找符合 neutral loss tag 的 product ion，從每個命中的 product 算出 `inferred_precursor_mz = product_mz + NL_da`，再把這個 candidate 回查 MS1 feature pool；若候選 feature 的 apex/trace 存在且 RT 合理，就把它記成 rescue evidence，而不是直接建新 row。Thermo MIPS、mzML 的 selected ion vs isolation target 分離、以及 OpenMS 的 precursor mass correction，都支持你必須同時保留這兩條路。citeturn34view0turn22view0turn21view0turn30view1

### Row identity 應由什麼決定

**單樣本內 row identity** 應由 `MS1 feature ID` 決定，而不是由 scan ID 決定。實作上，最少要以 `feature_apex_mz + feature_rt_apex + feature_rt_bounds + sample_id` 唯一化；若你有 isotope/adduct decomposition，建議把 `ion_state` 也納入。理由很直接：成熟工具都以 chromatographic feature 作為核心，MS2 只是歸屬到 feature 的額外資訊。citeturn27view2turn29view1turn30view0turn16view0

**跨樣本 row identity** 則應是 alignment 後的 consensus feature / aligned spot / grouped feature，依 m/z 與 RT（必要時再加 adduct/isotope state）形成共識。這和 MS-DIAL alignment spot、XCMS featureDefinitions、OpenMS consensus features、Compound Discoverer Group Features 的概念相同。citeturn28view1turn29view1turn30view1turn16view1

### Scan precursor 應扮演什麼角色

scan precursor 最適合扮演 **primary assignment hint** 與 **audit field**。換句話說，它應優先提供「這張 MS2 原本想打哪個 precursor cluster」，方便做候選 feature 檢索、purity/chimeric 判斷與後續 review；但它不應單獨決定 row identity。對 Thermo，尤其要把 `selectedIonMz` 與 `isolationWindowTargetMz` 分開存，因為官方已明示 monoisotopic m/z 與隔離中心可不同。citeturn22view0turn21view0turn34view0

### Product + NL inferred precursor 應扮演什麼角色

`product + configured NL` 最適合扮演 **recall rescue evidence**。它的用途是：當 scan precursor path 找不到合理 feature，或找到的 feature 明顯不是人工可見主峰時，用 product evidence 反推出 candidate precursor，再去看 MS1 裡是否存在一個真實 feature 可以承接。這能補救 isotope-trigger、instrument target offset、co-isolation 下真正帶有 tag evidence 的 feature 被漏建。OpenMS 的 isotope-to-mono remap 與成熟工具的 feature-first 模式，都強烈支持把這條路徑設計為「救援與降級判斷」而不是「直接寫 row」。citeturn30view1turn27view0turn29view2turn16view0

但這條路一定要有限制：如果 `product + NL` 只回推出一個 m/z，**卻在 MS1 沒有形成可辨識 chromatographic trace**，那它只能進 review / audit，不能直接進 matrix。否則你很容易把 noise、chimeric product、in-source / co-isolated fragments 變成大量假 row。這個限制和 mature software 的 feature-first 原則完全一致。citeturn27view2turn29view2turn39view0

### Repeated MS2 events under same peak 怎麼 collapse

建議以 **MS1 feature boundary 為第一優先的 collapse domain**。只要多張 MS2 的 RT 都落在同一 feature 的 `rt_start–rt_end` 內，而且它們的 scan-anchored 或 product-anchored candidate 最終都指向同一個 feature，就應 collapse 到同一 row。這基本上就是把「同峰多次觸發」視為同一 row 的多筆 evidence，而不是多個 row。MZmine 直接推薦使用 feature edges 來接受 MS2；XCMS 也是將 RT 在 chromatographic peak 範圍內、且 precursor 落在 peak m/z range 內的 MS2 掛回 peak/feature。citeturn37view0turn29view2

collapse 內部可以再用三層整理。第一層，保留 **all evidence scans**；第二層，挑 **representative MS2**，建議優先順序為 `高 purity / 非 chimeric`、`product/NL 最完整`、`距離 feature apex 最近`、`總訊號或診斷離子強度最高`；第三層，必要時產生 **consensus spectrum** 供後續 annotation，但 consensus 不得反過來覆寫 row identity。Compound Discoverer 的 representative MS1/MS2 scans、Consolidate MS Tree，以及 MS-DIAL representative spectrum 的概念都和這個方向一致。citeturn16view1turn16view0turn28view1turn28view2

### 哪些情況可以建 row，哪些情況只能 review

**可以建 row** 的最低條件，我建議是：存在一個可觀察的 MS1 chromatographic feature，且至少有一條 MS2 evidence path 能合理掛回這個 feature。這條 evidence path 可以是 scan-anchored 命中，也可以是 product+NL rescue 命中，只要最後都回到同一個真實 feature。citeturn27view0turn29view2turn30view1

**只能 review / audit** 的情況包括：只有 product+NL 命中但找不到對應 MS1 feature；同一張 MS2 對兩個以上 feature 同樣合理；scan precursor 與 product+NL 分別指向不同 feature 且沒有明顯主峰；chimeric/co-isolated 程度高；或僅命中 isotope/adduct/non-mono 候選卻無法穩定映回 monoisotopic feature。這些情況不該直接擴張 row 數量，而應降級為 ambiguous evidence。MZmine 允許一張 MS2 配多個 feature，且用 relative-height filter 降低弱峰搶譜；這正好支持你應保留 ambiguous 狀態，而不是硬切成多 row。citeturn37view0turn42search4

### 最少需要哪些 audit fields

最少 audit fields 我建議分成五群。**Feature fields**：`feature_id`、`sample_id`、`apex_mz`、`mzmin/mzmax`、`rt_apex`、`rt_start/rt_end`、`height`、`area`、`isotope/adduct state`。**MS2 acquisition fields**：`scan_id`、`selectedIonMz`、`isolationWindowTargetMz`、`isolationWindowLowerOffset`、`isolationWindowUpperOffset`、`charge`、`monoisotopicMz if available`、`activation type`、`collision energy`。這些欄位對應 mzML 的 selected ion / isolation window 概念與 Thermo 的 monoisotopic/isolation 分離。citeturn22view0turn21view0turn34view0

**Evidence fields**：`diagnostic_product_mz`、`diagnostic_product_intensity`、`configured_neutral_loss_da`、`inferred_precursor_mz`、`ppm_to_feature_apex`、`rt_distance_to_feature_apex`。**Quality / ambiguity fields**：`precursor_purity` 或替代 purity metric、`chimeric_flag`、`multi_feature_match_count`、`isotope_trigger_flag`、`rescue_mode_flag`。**Decision fields**：`decision = accepted / rescued / ambiguous / review_only / rejected`，以及 `decision_reason_code`。如果你沒有這些 audit 欄位，日後會很難回答「這個 row 為什麼建了」或「為什麼沒建」這兩個最重要的產品問題。citeturn42search4turn23search3turn30view1turn37view0

## Failure modes 與稽核清單

下表是依你的使用情境整理出的 **高風險 failure modes checklist**。它的重點不是把所有例外都拒掉，而是避免「漏抓真 tag feature」與「把 isotope/co-isolated/noise 亂建成 row」這兩個方向同時失控。這些失敗型態大多都能在成熟工具或文獻中找到對應問題設定。citeturn34view0turn31search0turn3search2turn37view0turn30view1

| Failure mode | 典型症狀 | 最可能原因 | 應檢查的 audit fields | 建議系統反應 | 依據 |
|---|---|---|---|---|---|
| **Isotope trigger** | `scan precursor` 比人工 MS1 feature 高一個 isotope step；`product + NL` 卻回到主 feature | instrument 在 isotope trace 上觸發或 mono assignment 不穩 | selectedIonMz、monoisotopicMz、charge、isotope flag、inferred_precursor_mz | **Rescue 到 monoisotopic MS1 feature**，不要新建第二 row | citeturn34view0turn30view1turn31search0 |
| **Isolation center ≠ monoisotopic value** | raw precursor 能看起來合理，但 feature apex m/z 不完全對齊 | Thermo MIPS 可把 mono m/z 寫到 raw file，但 isolation 仍在最豐 isotope | selectedIonMz、isolationWindowTargetMz、offsets、monoisotopicMz | 以 feature 與 window 共同判讀，不要只看單一 precursor 欄位 | citeturn34view0turn21view0turn22view0 |
| **Chimeric MS2** | product ion 命中、scan precursor 也有候選，但對應到多個共洗脫 feature | co-isolation / 窄窗仍夾雜多前驅物 | purity/chimeric flag、multi_feature_match_count、feature heights | 保留 evidence，**標 ambiguous / lower confidence**，避免 row 爆炸 | citeturn3search2turn23search3turn23search20turn37view0 |
| **Wrong-feature write** | `scan precursor - NL` 命中某 product，但人工看真正 feature 是另一個 MS1 peak | 單靠 scan precursor path 導致錯窗搜尋 | inferred_precursor_mz、feature RT bounds、ppm to feature | 啟用 `product + NL` rescue；row authority 回到 MS1 feature | citeturn30view1turn27view0turn29view2 |
| **Noise-derived pseudo feature** | product+NL 可回推 m/z，但 MS1 無實際 chromatographic peak | 噪音、低強度干擾、偶發 fragment | feature existence、peak shape、S/N、repeat support | **Review-only，不建 row** | citeturn27view1turn30view0turn16view2 |
| **Same peak duplicated into multiple rows** | 同一 chromatographic peak 下多張 DDA 各自變成一 row | 以 scan 為中心而非 feature 為中心 | feature_id、rt_start/rt_end、assigned_scan_ids | 以 feature boundary collapse；保留多 scan evidence、單一 row | citeturn37view0turn29view2 |
| **Weak co-eluter steals spectrum** | 低強度共洗脫 feature 也拿到同一張 MS2 | overlap feature pairing 無二次過濾 | co-assigned features、relative feature height | 套用 dominant-feature / relative-height filter | citeturn37view0 |
| **MS1-only annotation 被誤當作 MS2-confirmed** | feature 有 suggested identity，但沒有可靠 MS2 | 把 annotation score 當成 row authority | annotation source、has_ms2、representative_spectrum | 清楚區分 **MS1-only suggested** vs **MS2-supported** | citeturn28view3turn28view1 |
| **Compound-level grouping 反向覆蓋 feature identity** | adduct/compound assembly 將多 feature 合併後，row 身份混亂 | 把 compound grouping 誤當 row creation | feature_id、compound_id、ion_state | feature row 保留，compound 僅為上層 annotation | citeturn16view0turn16view1turn39view2 |

## 可轉成程式測試的 acceptance criteria

下面的 acceptance criteria 只針對 **Discovery row creation**，不涵蓋 cross-sample backfill policy。每一條都可以直接轉成 integration tests 或 scenario tests。其邏輯核心完全對齊成熟工具的 feature-first 設計。citeturn27view0turn29view2turn30view1turn16view0

| 測試情境 | 給定條件 | 預期結果 | 驗收理由 |
|---|---|---|---|
| **同峰多次 DDA 不得重複建 row** | 多張 MS2 的 RT 都落在同一 MS1 feature boundary 內，且最終都配到同一 feature | 只建立 **一個 row**；row 內保留多個 `assigned_scan_ids` | feature boundary-based pairing / collapse 是成熟作法 | citeturn37view0turn29view2 |
| **scan precursor path 可正常掛譜** | MS2 precursor 與 feature apex m/z 在容差內，RT 在 feature edges 內，且 product 符合 NL | 建 row 或掛到既有 row；evidence state = `accepted` | 這是主流程、不是 rescue | citeturn37view0turn27view0 |
| **product+NL rescue 可補救 isotope trigger** | MS2 scan precursor 不命中 monoisotopic feature，但 `product + NL` 命中該 feature，且 isotope/mono 資訊支持 remap | 不建立新 row；把 evidence 掛到既有 monoisotopic feature，state = `rescued` | OpenMS / Thermo 都承認 isotope-to-mono remap 的必要性 | citeturn30view1turn34view0 |
| **沒有真實 MS1 peak 時不得建 row** | `product + NL` 可回推出 precursor m/z，但查無清楚 MS1 chromatographic feature | 不建 row；state = `review_only` | feature-first 原則避免 noise rows | citeturn27view2turn29view2turn39view0 |
| **雙 feature 競爭同一 MS2 時要降級** | 同一張 MS2 同時合理配到兩個共洗脫 features，且無單一顯著主峰 | 不得自動新增兩個 confirmed rows；至少其中一方或兩方標 ambiguous | MZmine 明確允許一張 MS2 配多 feature，需再 refinement | citeturn37view0 |
| **弱共洗脫 feature 不得搶走主峰 MS2** | 一張 MS2 同配到高、低兩個 feature，但低峰高度低於設定比例 | 低峰 assignment 被去除或降級 | relative-height refinement 是成熟保護機制 | citeturn37view0 |
| **scan precursor 與 inferred precursor 不一致時要保留雙欄位** | `selectedIonMz != inferred_precursor_mz` | row 仍可成立，但 audit 必須同時保存兩者與差值 | 這是 review 與後續 debug 的必要條件 | citeturn21view0turn22view0turn34view0 |
| **代表譜不得覆蓋 row identity** | 同一 row 有多張 MS2，系統選出 representative spectrum | row identity 不變；只更新 `representative_scan_id` / consensus spectrum | 成熟軟體把 representative spectrum 當 annotation 資產，不當 row authority | citeturn16view1turn28view1turn28view2 |
| **MS1-only suggested identity 不能升格成 MS2-supported row** | feature 只有 MS1-based suggestion，沒有可靠 MS2 | row 可存在，但 `identification_support = MS1_only` | 必須明確區分 detection 與 identification | citeturn28view3turn6search0 |
| **compound/adduct grouping 不能消滅原始 feature row** | 多個 ions/adducts 被上層 compound grouping 串起來 | 原始 feature rows 仍存在；compound 只是上層 annotation relationship | 避免把 annotation layer 反向寫成 matrix authority | citeturn16view0turn39view2 |

## 研究限制與未決問題

公開文件足以支持「**feature-first, MS2-assignment-second**」這個主結論，但有兩類細節的公開程度仍不一致。第一，**不同 Thermo 機型、方法模板、RAW 轉 mzML 的軟體路徑**，實際把哪些 precursor-related 欄位寫到哪裡，公開文件並不完全統一；因此你的系統不應假設只有一個 precursor 欄位是真相，而應同時保存 `selected ion`、`isolation target`、`offsets`、以及若可取得的 `monoisotopic m/z`。citeturn21view0turn22view0turn34view0

第二，像 MS-DIAL 這類 GUI 軟體，公開文件較清楚描述 **peak spot / alignment spot / representative spectrum**，但沒有像 MZmine 那麼明確地公開所有「同峰多次 DDA collapse」的內部規則。因此我對 MS-DIAL 的結論採用較保守表述：它明顯是 feature-first，但單峰多 scan 的具體 collapse 細節，官方公開文件沒有完全展開。這不影響你最重要的產品決策，因為各家工具的共同方向已經足夠一致。citeturn28view0turn28view1turn28view2turn27view0

**最終建議只保留一句：**
你的 CID-NL discovery pipeline 應該採用 **「MS1 feature 決定 row identity；scan precursor 與 product+NL 只作為多路 evidence；同峰多次 MS2 collapse 到同一 row；遇到 mismatch 先保留 evidence 與 ambiguity，不要直接爆 row」**。這是目前最接近成熟軟體共識、也最能同時兼顧 **高 recall** 與 **低 row inflation** 的做法。citeturn27view0turn29view2turn30view1turn16view0turn39view0
