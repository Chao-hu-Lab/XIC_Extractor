# Untargeted Method Current Report

Date: 2026-05-14

Worktree: `C:\Users\user\Desktop\XIC_Extractor\.worktrees\algorithm-performance-optimization`

Branch: `codex/algorithm-performance-optimization`

## Executive Summary

目前 untargeted 方法的核心方向已經從「把所有 candidate 都盡量放進 final matrix」改成「production matrix 只保留通過 primary identity / family gate 的代表 row；其餘資訊保留在 Audit / Review」。這是它開始貼近舊 pipeline 乾淨矩陣型態的關鍵。

舊 pipeline 的優點是 final matrix 乾淨，通常不會出現大量重複 m/z / RT row；但它太依賴前段 peak detection 與 feature filtering，一旦穩定內標因靈敏度、批次處理、峰選錯誤或 upstream feature collapse 被漏掉，後面沒有足夠機制把它補回來。這就是舊 pipeline 在 ISTD 上會出現不合理 missingness 的根本問題。

新 pipeline 的目標不是複製舊 pipeline 的每一列輸出，而是保留舊 pipeline 的「乾淨 primary matrix」產品形狀，同時用 targeted benchmark、owner-centered backfill、duplicate claim control、pre-backfill family consolidation 來解決舊 pipeline 對穩定訊號漏檢的問題。

目前 8 RAW 與 85 RAW 的驗證結果顯示，新流程已經接近預期型態：

- 8 RAW strict DNA ISTD benchmark 通過。
- 85 RAW strict DNA ISTD benchmark 只剩 `d3-N6-medA` area mismatch，而這個 mismatch 也出現在 baseline，且已被判斷高度可能是 targeted workbook 本身抓錯低 area peak，不是 untargeted 新流程造成的新錯誤。
- 85 RAW preconsolidation + recenter 後，runtime 從先前約 35 分鐘降到約 16.8 分鐘，且 strict benchmark 的 RT drift false positive 已消失。
- Production matrix 的 duplicate / rescue-only / identity-anchor-lost 類型風險下降，Audit / Review 仍保留完整候選資訊。

結論：目前應該把新 pipeline 視為「candidate production direction」。下一步不是回到舊式 exact equality，而是用 corrected targeted benchmark 與少數 WARN case 確認 primary matrix promotion gate 是否可以正式升級為預設。

## Old Pipeline

這裡的舊 pipeline 指的是舊的 upstream feature table / final matrix 產生流程，包含前段 peak picking、feature alignment / merge、feature filtering，以及最後輸出乾淨 feature matrix 的流程。

### Old Pipeline Flow

```text
RAW / mzML
  -> upstream peak picking / feature detection
  -> feature alignment / merge
  -> feature filtering
  -> final matrix
```

### Old Pipeline Strength

舊 pipeline 最大優點是 final matrix 乾淨。

它通常會把同一個 feature 的多個近似 row 收斂掉，因此最終矩陣比較像下游統計需要的 feature table：

- 每個 row 比較接近一個 final feature identity。
- 不會把大量單樣本候選、backfill candidate、近似 m/z / RT 重複資訊直接塞進 matrix。
- 對下游統計、人工檢查與報告輸出而言，表面上比較容易使用。

### Old Pipeline Weakness

舊 pipeline 的問題是「乾淨」主要來自 upstream feature detection / filtering 的結果，而不是來自可被 targeted benchmark 驗證的 signal recovery 邏輯。

因此它有幾個核心風險：

1. 前段沒抓到的訊號，後段很難補回。
2. 若某個 ISTD 因靈敏度、峰型、局部 noise、RT drift 或 batch variation 被 upstream 漏掉，final matrix 可能直接缺失。
3. 它缺少 sample-level targeted benchmark gate，不能只靠 final matrix 形狀判斷 RT / area 趨勢是否合理。
4. 它比較像「產生乾淨表格」，但不一定保證「穩定內標應該被穩定檢出」。

這就是為什麼舊 pipeline 雖然矩陣乾淨，但在 ISTD 上反而不可信。內標是後添加，理論上 DNA active tag 的 ISTD 應該高度穩定檢出；如果連 ISTD 都缺失，就不能合理相信其他 feature 的 missingness 是生物或化學現象。

## New Untargeted Pipeline

新 pipeline 的核心設計是把「發現候選」、「建立 primary matrix identity」、「補回 missing samples」、「保留 audit evidence」拆開。

它不再把所有資訊混在 final matrix，而是明確區分：

- `Matrix`: 下游可使用的 primary feature matrix。
- `Review`: 值得人工檢查的候選與 flags。
- `Audit / Cells`: sample-level evidence、backfill、rescued、duplicate claim、absent 等細節。

### Current High-Level Flow

```text
RAW files
  -> untargeted discovery
  -> sample-local owner finding
  -> owner feature construction
  -> optional pre-backfill identity-family consolidation
  -> owner-centered backfill
  -> duplicate claim / primary promotion control
  -> recenter from present cells
  -> Matrix + Review + Cells + benchmark outputs
```

### 1. Untargeted Discovery

目前 DNA-only flow 的 active tag 是 DNA neutral loss tag：

- active NL: `116.0474 ± 0.01`
- RNA tag `[13C,15N2]-8-oxo-Guo` / `132.0423` 是 inactive，在 DNA-only matrix 不應被檢出。

Discovery 階段負責從 RAW 中找出可能的 tagged candidates，包含 precursor m/z、product m/z、observed loss、RT 等訊息。這一層只回答「哪裡可能有東西」，不直接決定 final matrix identity。

### 2. Sample-Local Owner Finding

每個 candidate 會回到對應 sample 的 vendor XIC / trace 找 local owner。這一步的重點是用原始訊號確認該 sample 是否真的有可量化峰，而不是只相信 discovery event。

Owner evidence 通常包含：

- apex RT
- area
- peak boundaries
- local quality / ambiguity
- sample identity
- tag / m/z / product / observed loss evidence

這一步解決了舊 pipeline 太依賴 upstream feature table 的問題。新方法會回到 RAW / XIC 層級確認 sample-local evidence。

### 3. Owner Feature Construction

Owner features 會依據 identity-compatible 條件被組成 feature family。核心 identity evidence 包含：

- same neutral loss tag
- precursor m/z tolerance
- RT candidate window
- product m/z tolerance
- observed neutral loss tolerance
- sample ownership / duplicate relationship

這一層的目標是避免把每個 sample 的 local owner 都當成獨立 final row。它先嘗試判斷哪些 owner 其實屬於同一個 feature identity。

### 4. Pre-Backfill Identity-Family Consolidation

這是目前新 pipeline 最重要的 algorithm change。

在舊版新 pipeline 中，很多 single-sample local owners 會太早進入 backfill。結果是同一個 feature identity 的多個近似 row 各自去 backfill，造成大量重複 vendor XIC calls，也讓 final matrix 出現太多不重要的近似資訊。

新的 pre-backfill consolidation 在 backfill 前先做一次 identity-compatible family merge：

```text
single-sample owner rows
  -> group by tag / m/z / RT / product / observed loss compatibility
  -> choose one primary representative
  -> merge compatible sample owners
  -> mark loser rows review_only
  -> keep loser evidence in audit/review
```

目前實作的關鍵行為：

- 只合併 identity-compatible rows。
- 同一 sample 的互相衝突 owner 不會被無條件合併。
- primary row 使用 family median m/z / RT / product / observed loss。
- loser row 不進 production matrix，但保留 Review / Audit。
- 每個 consolidated family 最多保留 early / late seed RT centers 供 backfill 使用。
- detected owner samples 會被 backfill seed 再確認，避免單一 local owner 偏峰。

這一步直接解決「新 pipeline matrix 很矯情，出現一堆不重要資訊」的問題：不重要的近似候選不刪掉，但不再讓它們全部成為 production matrix row。

### 5. Owner-Centered Backfill

Backfill 的任務是把已建立 identity 的 feature family 回填到 missing samples。

目前 backfill 的基本邏輯：

- 只對非 review-only primary feature backfill。
- 若 feature detected sample 數不足 `owner_backfill_min_detected_samples`，就不做昂貴 backfill。
- 對 missing samples 以 family seed m/z / RT window 抽 XIC。
- preconsolidated family 可使用 early / late seed centers，避免 RT window 只卡在單一偏移位置。
- 若同一 sample 多個 seed 都找到 rescued peak，保留最佳 rescued cell。

這一步解決舊 pipeline 的 missingness 問題。舊 pipeline 前段沒抓到的 sample，final matrix 通常就缺了；新 pipeline 只要 feature identity 已經有足夠 owner support，就會回到 RAW 層級對 missing samples 做 targeted-like rescue。

### 6. Duplicate Claim And Primary Promotion

新 pipeline 不只要把訊號補回來，也要避免同一個 sample / same peak 被多個 row 重複 claim。

因此它有 duplicate claim / primary promotion 控制：

- 一個 sample peak 不應該被多個 production family 同時當作 primary evidence。
- duplicate claim pressure 會被標記。
- winner row 進 Matrix。
- loser row 留在 Review / Audit。
- backfill 只能補既有 family，不能單獨創造 final row identity。

這是新方法貼近舊 pipeline final matrix 形狀的主要原因。Matrix 只留下 primary identity，完整候選資訊留在 Audit，不再污染 production matrix。

### 7. Recenter From Present Cells

preconsolidation 會把 early / late single-sample owner 合成同一個 family。如果 family center 還停在合併前的某一個 seed RT，strict benchmark 可能看到 false DRIFT。

因此目前新增 recenter 步驟：

```text
present cells = detected + rescued cells
family center RT = mean(apex RT of present cells)
rt_delta_sec = sample apex RT - recentered family RT
```

這一步已經解決 85 RAW strict ISTD benchmark 中原本出現的 false RT drift。

## Targeted ISTD Benchmark Gate

新 pipeline 的驗收核心不是 old pipeline exact equality，而是 targeted ISTD benchmark。

Targeted workbook 被當成 benchmark，不被 production alignment code 讀取 target label。這是刻意的設計：targeted evidence 用來驗證結果，不用來偷渡 identity。

### Active ISTD Selection

Benchmark 只選 DNA active tag 的 ISTD：

- `Role == ISTD`
- `NL (Da)` within `116.0474 ± 0.01`
- 排除 RNA tag `[13C,15N2]-8-oxo-Guo` / `132.0423`

### Strict Pass Rule

每個 active DNA ISTD 必須符合：

- exactly one primary matrix hit
- no hit = `MISS`
- multiple primary hits = `SPLIT`
- RT mean delta <= `0.15 min`
- sample-level RT median abs delta <= `0.15 min`
- sample-level RT p95 <= `0.30 min`
- log-area Spearman >= `0.90`
- log-area Pearson >= `0.80`
- coverage >= targeted positive count - `max(1, 2%)`

這個 gate 的意義是：不只看有沒有檢出，也看 RT 與 area 是否跟 targeted trend 一致。

## How The New Pipeline Solves The Old Problems

| Problem | Old pipeline behavior | New pipeline behavior |
| --- | --- | --- |
| ISTD missingness | 前段沒抓到就可能從 final matrix 消失 | owner-centered backfill 從 RAW / XIC 回填 missing samples |
| final matrix 太髒 | 舊 pipeline 乾淨，但新舊早期方法容易把候選塞進 matrix | primary matrix / Review / Audit 分層，loser 不進 Matrix |
| 同一 feature 多 row | 舊 pipeline 多半靠 upstream merge / filtering 壓掉 | pre-backfill identity-family consolidation 先合併 compatible family |
| same peak duplicate claim | 舊 pipeline final table 不一定揭露 claim conflict | duplicate claim pressure 被標記，winner 進 Matrix，loser 留 Audit |
| RT trend 不可信 | 缺少 sample-level targeted trend gate | strict targeted ISTD benchmark 檢查 mean / median / p95 RT delta |
| area trend 不可信 | final matrix 不保證 target-like area correlation | benchmark 檢查 log-area Spearman / Pearson |
| performance 太慢 | 舊流程與早期新流程都有大量重複運算 | preconsolidation + min detected gate 減少 redundant backfill XIC calls |
| target bug 混淆 | 無明確 benchmark 分層 | benchmark 可指出 baseline 與 candidate 都 fail 的 target-side anomaly |

## Validation Evidence

### 8 RAW

Representative run: `phase_l_preconsolidate_seed2_recenter_min2_8raw`

Key result:

- strict DNA ISTD benchmark: PASS
- stage sum: `184.723 sec`
- backfill XIC time: `76.387 sec`
- backfill raw calls: `3,755`
- backfill extract count: `7,413`

Guardrail comparison against baseline:

| Metric | Baseline | Candidate | Delta |
| --- | ---: | ---: | ---: |
| duplicate_only_families | 1721 | 1652 | -69 |
| zero_present_families | 1943 | 1931 | -12 |
| review_rescue_count | 2268 | 98 | -2170 |
| rescue_only_review_families | 844 | 49 | -795 |
| identity_anchor_lost_families | 116 | 6 | -110 |
| duplicate_claim_pressure_families | 1721 | 1656 | -65 |
| negative_checkpoint_production | 0 | 0 | 0 |

Interpretation:

8 RAW 上，新流程同時維持 strict ISTD benchmark pass，並大幅降低 rescue-only / identity-anchor-lost 這類 audit noise。這表示 preconsolidation 不是單純刪資訊，而是把資訊從 production matrix 移到更正確的 Review / Audit 層。

### 85 RAW

Representative run: `phase_l_preconsolidate_seed2_recenter_min2_85raw`

Performance comparison:

| Metric | Baseline | Candidate | Change |
| --- | ---: | ---: | ---: |
| stage_sum_sec | 13651.029 | 4623.367 | -66.1% |
| build_xic_sec | 601.557 | 655.418 | +9.0% |
| owner_backfill_sec | 1573.977 | 502.943 | -68.0% |
| backfill_xic_sec | 10922.026 | 2969.499 | -72.8% |
| backfill_raw_calls | 560030 | 144780 | -74.1% |
| backfill_extract_count | 1736390 | 220660 | -87.3% |
| recenter_sec | 0.000 | 0.977 | +0.977 sec |

Wall-clock interpretation:

- Earlier 8-worker 85 RAW run was around 35 minutes.
- Current preconsolidation + recenter candidate was around 16.8 minutes.
- The largest win comes from reducing redundant owner-backfill XIC extraction, not from micro-optimizing Python loops.

Strict benchmark result:

| ISTD | Candidate status | Interpretation |
| --- | --- | --- |
| `d3-5-hmdC` | PASS | target trend matched |
| `d3-5-medC` | PASS | target trend matched |
| `d4-N6-2HE-dA` | PASS | target trend matched |
| `15N5-8-oxodG` | PASS | target trend matched |
| `d3-dG-C8-MeIQx` | PASS | target trend matched |
| RNA inactive tag | PASS / inactive | DNA-only flow should not detect it |
| `d3-N6-medA` | AREA_MISMATCH | also fails in baseline; likely targeted peak bug / wrong low-area peak |

Guardrail comparison:

| Metric | Baseline | Candidate | Delta |
| --- | ---: | ---: | ---: |
| duplicate_only_families | 19419 | 18795 | -624 |
| zero_present_families | 20041 | 19994 | -47 |
| review_rescue_count | 85955 | 6352 | -79603 |
| rescue_only_review_families | 8198 | 446 | -7752 |
| identity_anchor_lost_families | 2527 | 126 | -2401 |
| duplicate_claim_pressure_families | 19419 | 18814 | -605 |
| negative_checkpoint_production | 0 | 0 | 0 |

Additional 85 RAW checkpoint:

- accepted quantitative cells: `49,747`
- accepted rescue cells: `33,583`
- accepted rescue rate: `0.6751`
- high backfill dependency families: `127`
- Case 1: PASS
- Case 2: PASS
- Case 3: WARN
- Case 4: WARN

Interpretation:

85 RAW 上，新 pipeline 已經達到兩個重要目標：

1. Matrix 形狀更乾淨，重複與 rescue-only 類型大幅下降。
2. Runtime 明顯下降，且主要 benchmark 沒有出現新的 untargeted-side failure。

目前唯一 strict failure 是 `d3-N6-medA AREA_MISMATCH`，但它不是 candidate-specific regression。這點很重要，因為它說明 strict benchmark 不只是替新 pipeline 背書，也能反過來暴露 targeted benchmark 自身的峰選問題。

## New Pipeline Advantages

### 1. More Scientifically Defensible

舊 pipeline 的 final matrix 乾淨，但不能證明穩定內標真的被合理檢出。新 pipeline 用 DNA ISTD strict gate 當 benchmark，直接要求：

- 內標要出現在 primary matrix。
- 每個 ISTD 只能有一個 primary hit。
- RT trend 要與 targeted 一致。
- area trend 要與 targeted 一致。
- inactive RNA tag 不應出現在 DNA-only result。

這比只看 final matrix row 數或人工感覺乾淨更可靠。

### 2. Keeps Old Matrix Shape Without Losing Audit Evidence

新 pipeline 不再把所有候選資訊都丟進 production matrix。它把輸出分成：

- Matrix: primary features only。
- Review: 需要檢查的候選。
- Cells / Audit: sample-level evidence 與 rescue / duplicate / absent details。

這樣 final matrix 可以接近舊 pipeline 的乾淨形狀，但不會像舊 pipeline 一樣把被排除的證據完全消失。

### 3. Better ISTD Recovery

ISTD 是判斷流程是否可信的穩定標竿。新 pipeline 用 owner-centered backfill 補回 missing samples，理論上比舊 pipeline 更符合 ISTD 應有行為。

目前 8 RAW strict gate 已通過；85 RAW 除了 baseline 也失敗的 `d3-N6-medA` targeted area anomaly 外，其餘 DNA ISTD 都符合 target trend。

### 4. Faster At The Real Bottleneck

這次效能改善不是只做 batch size 或 loop micro-tuning，而是減少不必要的 backfill work。

pre-backfill consolidation 先把 identity-compatible rows 合成 family，讓 backfill 不再對大量近似 row 重複抽 XIC。

結果在 85 RAW 上：

- backfill raw calls 減少約 74%
- backfill extract count 減少約 87%
- owner_backfill stage 減少約 68%
- backfill_xic time 減少約 73%
- wall time 從約 35 分鐘降到約 16.8 分鐘

### 5. Easier To Debug

新 pipeline 的輸出可以回答更具體的問題：

- 是 `MISS` 還是 `SPLIT`？
- 是 RT drift 還是 area mismatch？
- 是 production matrix 問題還是 targeted benchmark 問題？
- 是 single-sample local owner 太早 promotion，還是 backfill 沒補到？
- 是 inactive RNA tag false positive，還是 DNA active tag 合理檢出？

這讓後續演算法修正有明確方向，不會只停在「矩陣看起來怪」。

## Current Limitations

### 1. `d3-N6-medA` Needs Corrected Targeted Evidence

85 RAW candidate 仍會被 strict benchmark 標為 `AREA_MISMATCH`，但 baseline 也有同樣問題，且 observed targeted area 很低，符合使用者指出的 targeted bug：targeted 很可能抓錯峰。

因此這不是新 pipeline 的失敗，但在 corrected targeted workbook 出來前，strict gate 會保留這個紅燈。

### 2. Preconsolidation Still Needs Productization Decision

目前 `--preconsolidate-owner-families` 是 explicit candidate mode，不應靜默變成所有流程預設。原因是它改變 row identity 與 matrix shape，雖然目前 evidence 支持它，但仍屬 public behavior change。

建議接下來做：

- 用 corrected targeted workbook 重跑 85 RAW strict benchmark。
- 檢查 Case 3 / Case 4 WARN 的代表 features。
- 若沒有新的 false merge / false loss，再把此 mode 升級為 production default 或 default recommendation。

### 3. Exact Equality Is No Longer The Success Definition

新 pipeline 不應追求與舊 pipeline 或 baseline untargeted output 完全等價。

原因：

- 舊 pipeline missingness 不是 ground truth。
- baseline 新 pipeline 早期矩陣太髒，也不是 ground truth。
- 成功定義應是 primary matrix clean、ISTD trend target-like、Audit evidence complete、runtime acceptable。

Exact equality 只能當 regression debugging guard，不能當產品成功標準。

## Recommended Current Operating Mode

目前最合理的 candidate run mode：

```powershell
uv run python scripts/run_xic.py validation-fast `
  --emit-alignment-cells `
  --preconsolidate-owner-families `
  --owner-backfill-min-detected-samples 2
```

搭配 strict targeted ISTD benchmark：

```powershell
uv run python tools/diagnostics/targeted_istd_benchmark.py `
  --targeted-workbook "C:\Users\user\Desktop\XIC_Extractor\output\xic_results_20260512_1200.xlsx" `
  --alignment-run-dir "<alignment output dir>" `
  --strict
```

Acceptance should be:

- Six active DNA ISTD exactly one primary hit。
- Inactive RNA tag not detected。
- RT mean / median / p95 within strict limits。
- log-area Spearman / Pearson pass, except known targeted-side anomaly until corrected。
- No increase in production duplicate / zero-present / identity-anchor-lost guardrails。
- Runtime remains close to current 85 RAW candidate performance.

## Final Direction

目前的方向不是回到舊 pipeline，也不是繼續修 micro-performance。正確方向是：

1. 保留舊 pipeline 的 clean primary matrix 產品形狀。
2. 用 new pipeline 的 owner-centered backfill 解決舊 pipeline missingness。
3. 用 pre-backfill identity-family consolidation 防止同一 feature 被拆成多個 final rows。
4. 用 strict targeted ISTD benchmark 驗證 RT / area trend，而不是只看有沒有檢出。
5. 把不該進 matrix 的候選留在 Audit / Review，不刪 evidence。

這套新 pipeline 的優勢是：更像 targeted 的可信度、更像舊 pipeline 的乾淨矩陣、又保留 untargeted 的探索能力與完整 audit trail。
