# XIC Backfill 的 Production Gate 應該怎麼設

## 白話結論

我不建議把 `absolute peak height >= 2e6` 升格成 XIC backfill / gap filling / missing peak rescue 的**產品硬門檻**。成熟工具與方法普遍不是這樣做，而是用 **expected RT/m/z 視窗 + 局部峰證據 + 邊界穩定性 + 多證據整合** 來決定能不能補值。 citeturn14view3turn12view1turn15view0turn12view3turn23view0
在 LC-MS，絕對強度會被**化合物本身離子化效率、matrix effect、共洗脫、批次漂移、儀器狀態**強烈影響，所以跨樣本、跨批次、跨化合物用同一個高度 cutoff，移植性很差。 citeturn17view0turn26search5turn26search1turn16search0
監管與方法學對「可量化」的核心語言是 **accuracy、precision、selectivity、matrix effect、LLOQ/blank separation**，不是 universal peak height；LLOQ 也是 analyte- 與 method-specific。 citeturn12view7turn17view0turn37view3
XCMS、MZmine、OpenMS、Skyline/mProphet 都提供了很清楚的訊號：**高度可以是 feature 之一，但不應該是唯一、也不應該是跨資料集共用的 production gate**。 citeturn14view3turn13view5turn13view6turn12view3turn23view0turn31view0
如果目標是「只要 evidence 足夠就自動補值，但不能 silent rewrite」，最合理的 gate 是把決策拆成三層：**peak existence、quantification readiness、rewrite safety/provenance**。 citeturn13view7turn13view2turn37view0
對 low-height 而言，你的 `20 heldout = 19 pass + 1 boundary fail`，目前更像是**邊界與再積分一致性問題**，不是「low-height 類別整體不可用」。這樣的失敗型態，和文獻對 gap-filled/raw-baseline signal 在 baseline 或 co-elution 附近容易失真的警告一致。 citeturn36view1turn14view2
因此，`2e6` 最多應保留成**示範 slice / rollout guardrail**，不應成為產品定義；真正要上 production 的，是 **boundary stability、local S/N / local selectivity、cohort-anchored RT/m/z evidence、以及可追溯的 expected-diff / oracle 結果**。 citeturn20view0turn35view1turn21view0turn22view1turn23view0
你現在最值得做的，不是加更多人工 review，而是補三個可驗證 evidence class：**boundary-stability / reintegration-agreement、local selectivity / S/N、cohort-anchored expected-window consistency**。這三個都比 absolute height 更接近成熟實務。 citeturn12view1turn20view0turn35view1turn23view0

## Absolute height 與 relative stability evidence 比較表

| 證據類型 | 優點 | 主要缺點 | 更適合的定位 | 依據 |
|---|---|---|---|---|
| **Absolute peak height** | 容易理解、容易 rollout、對高訊號 slice 很保守 | 受 analyte 離子化效率、matrix effect、共洗脫、批次/儀器漂移影響；跨化合物與跨批次不可比；高峰也可能是錯峰，低峰也可能是對峰 | 可當 **暫時性 rollout guardrail** 或偵錯指標，不適合當產品硬門檻 | citeturn17view0turn12view7turn26search5turn26search1turn16search0turn23view0 |
| **S/N 與 local baseline noise** | 比 absolute height 更接近「峰是否脫離背景」；對低訊號更公平 | 仍受估噪方式影響；不同工具定義可能不同 | 很適合放進 auto-write gate；至少應取代單獨 height | citeturn20view0turn31view0turn23view0 |
| **Peak shape、local/global max ratio、minimum scans** | 直接檢查「這是不是像一個峰」；成熟工具常用 local apex、shape、minimum data points | 會受 scan density 與過度平滑影響；對寬峰/肩峰要小心 | 適合當 **peak existence** 的核心 gate | citeturn13view5turn13view6turn20view0turn35view1 |
| **Boundary stability / reintegration agreement** | 最接近你真正關心的「能不能可信寫 matrix」；能抓到 boundary fail、co-elution、baseline 問題 | 需要多跑一次 integration 或 perturbation；實作比 height 稍複雜 | 應成為 **quantification readiness** 的核心 gate | citeturn35view1turn36view1turn37view0 |
| **Cohort evidence 與 RT/m/z consistency** | 利用同 row 的已知訊號當錨點；對 backfill 特別自然；XCMS 甚至直接用 row 內峰界的分位數定義 integration area | 若 row 本身 anchor 不乾淨，會把偏差帶進去 | 很適合做 **expected-window** 與 auto-write 前提 | citeturn14view0turn14view3turn15view0 |
| **Isotope / adduct / MS2 / reference support** | 這些是正交證據，能大幅降低「錯峰卻高強度」的風險 | 不一定每個 cell 都有；不能要求為必要條件 | 適合當加分項，或低訊號但高風險時的補強 | citeturn13view9turn33view0turn33view1turn33view2 |

表裡最重要的結論是：**absolute height 的資訊價值並不是零，但它最容易被誤用成跨情境的假共通尺度**。相反地，成熟工具與文獻更偏向使用「局部相對證據」與「再積分穩定度」來判斷 peak rescue 是否可信。XCMS 用 feature 內的 peak 邊界分布來決定補值區域；MZmine 的 gap finder 看 local maximum、shape 與 minimum scans；Skyline/mProphet 則把 intensity 放在多特徵模型裡，而不是單獨裁決。 citeturn14view3turn12view1turn15view0turn23view0turn31view0

## 建議的 production gate

### 為什麼不應該把 2e6 當硬門檻

先講最核心的一句：**在 LC-MS 世界裡，「高」不是可移植概念**。同一個 height，在不同 analyte 可能代表完全不同的濃度與可信度，因為 response 受 ionization efficiency、matrix effect、co-eluting interferents、sample prep、instrument drift 與 batch effect 共同決定。ICH M10 直接把 matrix effect 定義成由樣品基質中的干擾成分造成的 analyte response 改變；EMA 與 FDA 對 LLOQ 的語言也是「可接受的 accuracy/precision」與 blank separation，而不是通用 intensity。 citeturn17view0turn12view7turn37view3turn26search5turn26search1turn16search0

成熟工具文件也幾乎沒有支持「跨樣本/跨批次/跨化合物共用一個絕對高度 gate」這件事。XCMS 的 `fillChromPeaks` 不是用 universal intensity cutoff，而是用 feature 的 m/z-RT 區域去整合訊號；而且官方還明說舊的 `FillChromPeaksParam` 會低估 peak area，不建議用，較新作法是用 feature 內其他已檢出的 chromatographic peaks 之分位數來界定 integration area。若該區域內根本沒有訊號，XCMS 仍保留 `NA`。 citeturn14view2turn14view3turn13view2

MZmine 的推薦 gap-filling 演算法也是回到預期的 m/z 與 RT 區域，找 local maximum、檢查 shape，並要求 minimum data points；填到的 feature 也被明確標成 `ESTIMATED`，沒有證據就保持空白。這個設計其實非常符合你的產品方向：**可以自動補，但不能 silent rewrite**。 citeturn12view1turn13view5turn13view6turn13view7

MS-DIAL 的文件更能說明風險面：它甚至提供「gap filling by compulsion」，在 chromatogram 中**沒有 local maximum**時，仍可用其他樣本的平均 peak width 去補；但同一份官方教學也同時強調，自動 identification 仍有 false positives，應結合 retention time、precursor m/z、isotopic ratios、MS/MS spectrum 等多證據，必要時要 curate。這正好說明：**自動補值可以很積極，但 production gate 不能只靠單一強度數字。** citeturn12view2turn13view8turn13view9

OpenMS 的 EICExtractor 也不是以 height 做通用 gate，而是以給定位置的 `rt_tol` 與 `mz_tol` 去定點定量；Skyline/mProphet 則明確把 intensity score 視為眾多 peak-group feature 之一，與 co-elution、shape、relative intensity correlation、reference correlation 等共同形成 discriminant score 與 error-rate model。就連 Skyline 官方支援回覆也指出，signal-to-noise、precursor-product shape、standard intensity、retention-time-related scores 都可能是重要特徵。 citeturn12view3turn13view10turn23view0turn31view0

### 自動寫 matrix 的 evidence

我建議把 auto-write 的門檻拆成三個層次：**峰存在證據、可量化證據、寫入安全證據**。只有三者都過，才進 matrix；否則不是 flagged，就是 block。

| 決策層 | 建議必要 evidence | 為什麼 |
|---|---|---|
| **峰存在證據** | 在 expected RT/m/z window 內有 local apex；m/z 誤差在 extraction tolerance 內；scan count 達到最低要求；peak 不是明顯雙峰/肩峰/平台 | 這些是 MZmine/XIC 式 gap fill 最基本的「有沒有峰」判準；沒有這層就不該寫任何值。 citeturn12view1turn13view5turn13view6 |
| **可量化證據** | local S/N 或 apex-vs-baseline 明顯脫離噪音；用兩種邊界法或 window perturbation 再積分時，boundary 與 area 一致；area 不對 minor boundary jitter 過度敏感 | 這層才是 quantification readiness。文獻與工具都顯示 raw signal、baseline、co-elution 對補值區域很敏感。 citeturn36view1turn35view1turn20view0 |
| **寫入安全證據** | row-level cohort anchors 乾淨、RT 一致；expected-diff 合理；blank / background / nearby interference 無紅旗；cell 被標記為 backfilled-estimated 且保留 evidence bits | 這層是產品化關鍵：不是只有「測到」，而是「值得改寫 matrix，而且可回溯」。成熟工具會保留 estimated 狀態；FDA 也要求原始與 re-integration chromatograms 的完整留存。 citeturn13view7turn13view2turn37view0 |

把它落成你可實作的規則，我會建議：

**直接 auto-write 的條件**
對單一 cell，至少要同時滿足：
第一，該 row 有足夠乾淨的 cohort anchors，用來定 expected RT/m/z/width；XCMS 的 `ChromPeakAreaParam` 本質上就是在做這種 cohort-informed boundary 定義。 citeturn14view0turn14view3
第二，目標樣本在 expected window 內有明確的 local apex，且 minimum scans 過線。MZmine 的推薦 gap filler 明確要求 local maximum 與 minimum data points；這比單純看 height 更貼近真峰。 citeturn13view5turn13view6
第三，local S/N 與峰形過線。Kumler 等人只用兩個從 raw EIC 算出的簡單指標——自訂 S/N 與 bell-curve 相似度——就把 false positives 從 70–80% 降到 1–5%，說明「局部品質指標」比只看強度有效得多。 citeturn20view0
第四，boundary stability 過線：例如對同一 cell 做兩次再積分（不同 baseline、不同平滑、或 expected RT window ± 小擾動），若邊界移動與 area 變化都仍在你已接受的 oracle tolerance 內，才寫 matrix。CPC 與其他 peak-quality 文獻都把 boundary、shape、tailing、S/N 當成核心品質特徵。 citeturn35view1
第五，寫入不是 silent 的：cell metadata 至少要有 `source=backfill`, `state=estimated`, `evidence_score`, `boundary_stable=yes/no`, `method_version`, `expected_window_version`。這跟 MZmine 的 `ESTIMATED` 標記與 FDA 對 reintegration 追溯的精神一致。 citeturn13view7turn37view0

在數值起點上，我會把 **height** 降格成**輔助特徵**，而不是門檻本體。比較實用的起手式是：
若 local S/N 很低、沒有 local apex、scan 數太少、或 boundary 對微小擾動極敏感，就算 height 很高也不要 auto-write；
反過來說，只要 local S/N、shape、min scans、RT consistency、boundary stability 都過，height 本身偏低也可以 auto-write。這跟 mProphet 的精神一致：intensity 是一個分數，但不是裁決者。 citeturn23view0turn31view0

### 只能 detected flagged 或進 review queue 的 evidence

這一層的用途，不是「多做人工 review」，而是**把不夠穩但有真實訊號跡象的 cell 從 auto-write 與 hard-block 中間切出來**。

我會把下列情況放進 `detected_flagged`：
有 in-window apex，也有 reasonable RT/m/z match，但 local S/N 只在邊界附近；
或 scan count 勉強；
或 area 看起來合理，但 boundaries 對小擾動不夠穩；
或 cohort anchors 很乾淨，但該樣本附近存在局部干擾峰，使 local/global max ratio 不夠漂亮；
或只有 isotope/adduct/MS2 其中一項補強，沒有全部。這種 cell 不該直接改 matrix 的主值，但可以輸出成 `detected_flagged`、進後續批次驗證，或在 matrix 中以明確 provenance 形式寫入次級欄位。這樣做的好處，是你可以持續累積 expected-diff / oracle 證據，而不必被 `2e6` 封死低訊號發展空間。 citeturn33view0turn33view1turn33view2turn13view9turn20view0

### 必須 block 的 evidence

我會把這些情況直接 block：

在 expected window 內**沒有 local maximum**；
有訊號，但 shape 非單峰、明顯被鄰峰拉扯、或 minimum scans 明顯不足；
boundary 對輕微 perturbation 極度敏感，導致 area 變化已超過你的 oracle tolerance；
blank/background 與 sample 的局部訊號不可區分；
RT 離 row 的 cohort anchors 太遠，或落在不合理的 tail；
MS2 / isotope / adduct 證據若存在，卻與主峰候選相互矛盾。這些情況的共同點是：**你不是在面對一個低峰，而是在面對一個不可信的 peak assignment**。 gap fill / fillPeaks 文獻也提醒，直接拿 raw 或 baseline signal 去代替真實濃度，在 baseline 未校正或有 co-eluters 時可能不準。 citeturn12view1turn13view5turn13view6turn36view1

## 目前 case 的判讀

你的 low-height probe 是 `20 個 heldout oracle case，19 pass，1 fail_boundary`。**這個結果不支持把 low-height 類別整體宣判不可用。** 相反地，它更像是：低高度並不是主要失敗來源，真正的 failure mode 是**boundary inference**。如果 low-height 本身不可用，典型現象通常會是大量「沒有 local apex、area 大偏差、RT 飄掉、或整體 S/N 不足」；你現在看到的是 19 個通過、1 個 boundary fail，這比較接近「峰存在，量也大致可積分，但邊界有時不穩」。這和 XCMS 與 missing-value 文獻對 gap filling / fillPeaks 的風險描述相符：補值最脆弱的地方往往不是有沒有訊號，而是 integration boundary 在 baseline 與 co-elution 附近是否可靠。 citeturn14view2turn36view1turn35view1

但另一面也要講清楚：**20 個 case 還太少，不足以支撐 production_ready。** 以 19/20 的結果來看，粗略的 95% Wilson 區間下限大約只有 0.76 左右；也就是說，你目前能說的是「low-height slice 很有希望，值得繼續」，還不能說「這個 slice 已被充分驗證」。所以正確動作不是把 low-height 類別封殺，而是把它升級成一個明確的驗證 slice，專門加上 **boundary-stability / reintegration-agreement gate** 後再擴大 heldout。這是比 `2e6` 更準確也更不保守的方向。

如果要把目前觀察翻成產品判斷，我的結論是：
**不是 low-height 類別不可用；是你需要一個比 height 更敏感地抓 boundary risk 的 gate。**
而這個 gate 最可能是「再積分一致性」而不是「更高的高度 cutoff」。

## 建議的 validation protocol

你的產品問題本質上不是「演算法是否能跑」，而是「在什麼 evidence 下可以改寫 matrix」。因此 validation protocol 要驗證的是 **write decision**，不是單純 peak detection。

首先，heldout oracle 的抽樣不應只按高度分層，至少要同時覆蓋：
低/中/高 signal；
scan count 高/低；
有無共洗脫風險；
不同 batch；
不同 RT 區段；
有無 isotope/adduct/MS2 support。
如果只從「看起來乾淨」的 slice 抽樣，就會把真實 production 風險洗掉。gap filling 與 missing-value 文獻早就指出，缺值來源混雜了 under-LOQ、前處理參數、共洗脫、alignment 與隨機技術誤差；不同 failure mode 的 validation 不該混成一鍋。 citeturn12view1turn36view1

其次，acceptance threshold 應該分成**cell-level**與**slice-level**。
cell-level 你已經有很好的 oracle 定義：`boundary error <= 0.1 min`、`area relative error <= 10%`。這應保留。
slice-level 則應再加三件事：
其一，auto-write precision 要達到預先宣告門檻；
其二，不同 strata 不能只看 aggregate，要看最弱 strata；
其三，要報告 fail mode 組成，而不是只報 pass rate。FDA 文件明確要求保存 original 與 re-integrated chromatograms、列出 passed 與 failed runs，並保存 selectivity、sensitivity、precision、accuracy、matrix effect 等驗證資料；對你的產品來說，對應到的就是 **不能只看 sidecar summary，必須保留原始/再積分與 pass/fail 理由**。 citeturn37view0turn37view2turn37view3

第三，避免 cherry-picking 的方法要事先寫死。我的建議是：
把 slice 定義、sample stratification、oracle tolerance、以及 auto-write / flagged / block 的規則先鎖住；
開發資料與 lockbox 資料分開；
holdout 以 row 或 row×batch 為單位切分，避免同一 feature 的相近案例同時落在 train 與 test；
發表結果時必報所有 strata，不得只報 high-signal clean 與 low-scan clean 這類漂亮 slice。這個做法也更接近 ICH/FDA 對 validation、partial validation、與 failed run reporting 的精神。 citeturn17view0turn37view2

至於 `production_candidate` 與 `production_ready`，我會這樣分：

| 狀態 | 我建議的最低標準 | 意義 |
|---|---|---|
| **production_candidate** | 有明確 slice 定義；locked holdout 上 aggregate pass 夠高；failure mode 已知且可被 gate 捕捉；expected-diff 沒有出現大面積異常 rewrite；所有 writes 都有 provenance | 可以進行受控 rollout，但還不能擴大到一般 case |
| **production_ready** | 除了 aggregate 過線，低高度/低scan/高干擾等弱 strata 也過線；boundary fail 已被新 gate 顯著壓低；lockbox 與新 batch 重現；expected-diff 與 oracle 結果一致；報告包含通過與失敗案例 | 可以把這個 evidence class 當正式產品規則的一部分 |

實務上，我會把 `production_candidate` 的門檻設得偏向**知道風險、可受控寫入**；
把 `production_ready` 的門檻設得偏向**跨批次、跨 slice、可重現**。
也就是說，candidate 是「可以上路但有欄杆」；ready 是「欄杆可以放寬，但規則已證明穩定」。

## 下一步最小實驗設計

你要的不是大工程，而是一個**最小、可驗證、能直接回答 2e6 是否該退位**的實驗。我會做下面這個四步版本。

### 實驗目標

用最小代價比較兩種產品 gate：

一種是你現在直覺上的 `height >= 2e6` guardrail；
另一種是我建議的 **low-height friendly gate**：`local apex + S/N + boundary stability + cohort RT consistency`。

目標不是證明低高度永遠沒問題，而是比較：**哪一種 gate 對「可安全改寫 matrix」更有辨識力。**

### 樣本設計

從現有 broad candidate writes 的 4613 cells 中，事先分層抽出 **60 個新 oracle cases**，不要重用那 20 個。

分層方式只要三維就夠了：
第一維是 height：低、中、較高，但都在 `2e6` 附近上下與以下要有覆蓋；
第二維是 scan count：低與非低；
第三維是風險：有明顯鄰近峰/可能共洗脫，與乾淨背景各半。

這 60 個 case 再分成兩半：
30 個做 threshold tuning；
30 個完全 lockbox，只做最後判斷。
這樣可以避免你在同一組 low-height case 上反覆調 boundary 規則，最後得到看似漂亮、其實已經 overfit 的結果。

### 只加兩個新 evidence class

第一個新 evidence class 是 **boundary-stability / reintegration-agreement**。
對每個 candidate cell，至少跑兩次 integration：
一次用標準 expected window；
一次做小擾動，例如 RT 視窗 ± 一點點、或 baseline / smoothing 換一種安全的替代法。
輸出兩個數：`max boundary shift` 與 `relative area disagreement`。
如果這兩個數都在你既有 oracle tolerance 內，就視為 boundary-stable；否則至少降級成 flagged。這會直接對準你目前唯一明顯的失敗型態。 citeturn35view1turn37view0

第二個新 evidence class 是 **local selectivity / S/N**。
不要再看絕對 height，而是算：
局部 baseline noise；
Apex 與局部噪音的比值；
以及 expected window 內 apex 對附近次高峰的 dominance。
Kumler 的結果已經很清楚：用 raw EIC 上的簡單 S/N 與 bell-curve similarity，就足以大幅壓低 false positives。Asari 與 MZmine 也都把 peak quality / selectivity / minimum data-point 這類局部證據放在核心位置。 citeturn20view0turn21view0turn22view1turn13view5turn13view6

如果你願意再多做一點點，我會加第三個 evidence class：**cohort-anchored expected-window consistency**。
也就是讓每個 row 的 confident anchors 產生一個 expected RT center、RT spread、expected width；候選 cell 若明顯偏離這個 cohort window，就算 height 高也不能 auto-write。這基本上把 XCMS 的 feature-aware 補值精神產品化。 citeturn14view0turn14view3

### 判斷標準

這個最小實驗只看三個輸出：

第一，`2e6 gate` 與 `new evidence gate` 在 30 個 lockbox 上，誰的 **auto-write precision** 較高。
第二，對於未通過 auto-write 的 case，`new evidence gate` 能不能把它們大部分合理地落到 **flagged**，而不是全都 block。
第三，唯一或主要失敗是否仍集中在 boundary fail；如果是，代表你真的找到了正確 failure mode，而不是誤把 low-height 當成問題本身。

### 我會接受的成功條件

如果新 gate 在 lockbox 上滿足下面三件事，我就會建議你正式把 `2e6` 從產品硬門檻降格：

auto-write 的 oracle pass rate 不低於你目前 high-signal clean slice 的可接受水位；
boundary fail 的比例明顯下降，或至少都被正確降級到 flagged；
expected-diff 沒有出現「大量無峰卻被寫值」的異常 pattern。

### 這個實驗回答什麼

它會直接回答你最重要的產品問題：
**low-height 類別是不是不能上 production？**
如果答案是「不是，只是 boundary-stability 還沒 gate 好」，那你就不用再讓 `2e6` 主導產品定義；
你只需要讓 `2e6` 退回到 rollout guardrail，而把真正的 production gate 建立在更可轉移、也更可驗證的 evidence 上。
