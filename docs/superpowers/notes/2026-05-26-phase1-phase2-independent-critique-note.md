# Phase 1 / Phase 2 Independent Critique Note

**Date:** 2026-05-26
**Authors:** Claude Sonnet 4.6（第一輪）+ Claude Opus 4.7（獨立第二輪）
**Purpose:** 以反面評審角度整合兩輪獨立批判，供 Codex review 及工程師自省使用
**Status:** 批判意見，非 GO/NO-GO 決策

---

## 前言

本文整合了兩輪獨立技術評審：Sonnet 針對計畫自洽性的局部批判，以及 Opus 4.7 針對計畫是否真正朝 handoff 願景前進的根本質疑。兩輪批判在幾個核心問題上有重疊，但 Opus 提出了更根本的架構層批評。

---

## 一、Resolver 設計缺陷

### 1.1 `region_first_safe_merge` 命名不誠實

這個 resolver 的實際執行邏輯是：

```
先 local_minimum 決定邊界 → 再用 4 道 gate 判斷要不要合併
```

正確的名稱應該是 `local_minimum_with_wis_merge_v1`。Handoff 願景說的 region-first 是「先從 trace 的 region 結構（連續訊號、WIS 區段、curvature flow）枚舉候選，local_minimum 只是其中一個 evidence source」。現在的設計仍然讓 local_minimum 當裁判，只是事後給它一張否決票。這是換名字，不是換邏輯。

### 1.2 四道 gate 的科學依據不足

| Gate | 問題 |
|---|---|
| `APEX_DELTA < 0.03 min` | 數字來源不明，是 8RAW 調出來的嗎？ |
| `AREA_RATIO 1.0–1.20` | 「只能長，不能縮，最多 20%」是哪個物理/統計模型推出來的？像是政治性 gate（不想動到 production 太多），不是科學 gate |
| `GAP < 0.08 min` | 與 APEX_DELTA 資訊重疊，互動關係沒有說明 |
| `decision source` 必須是特定 string | 這是 protocol 防呆，不是 evidence gate，不應列為「科學 gate」 |

有效的嚴格 gate 只有 2 道（APEX_DELTA、AREA_RATIO），其餘是包裝。

### 1.3 Targeted 與 Alignment 長期雙軌，沒有收斂計畫

Phase 1 之後：
- targeted extraction → `region_first_safe_merge`（production）
- alignment production quantification → `local_minimum`（保留）

**使用者拿到的最終定量數字，仍然由 local_minimum 決定。** region_first 只是裝飾性的 audit context。兩條路徑長期分歧，未來 alignment 切過去時會爆出大量「為什麼跟之前不一樣」的 regression，且計畫沒有 alignment 切換的 timeline。

### 1.4 驗收 metric 刻意挑寬鬆的

- **ISTD RSD median 不退步 >0.5 個百分點**：region_first_safe_merge 的風險在「合併錯邊界的少數 outlier」，這要看 **P95 / MAD**，不是 median。用 median 等於刻意挑一個會通過的 metric。
- **RT residual median 不移 >0.5 sec**：同樣問題，median 對尾端不敏感。

---

## 二、AsLS 面積積分的科學依據與 P2b 決策

### 2.1 P2b gate 語義改動是 post-hoc rationalization

原始嚴格 gate 說 NO-GO（AsLS RSD 比 linear-edge 差）。修改後的 gate 加入三條 escape hatch：

1. baseline truth 顯示 `linear_edge_over_subtraction_plausible`
2. RT/boundary 顯示 same-peak support
3. target-level RT drift 解釋 RT delta

每一條都是「AsLS 沒贏，但我們有理由說它其實贏了」的邏輯。這是先有結論再找理由。

正確的回應有兩種：
- **承認 AsLS 在這個資料集沒有明顯優勢**（很可能是 λ/p 參數沒調對，或 8RAW 的 baseline 本來就不難）
- **拿出 ground truth 證明 AsLS 更接近真值**：需要 spike-in 已知濃度、blank 注入、或合成 dataset 比較絕對誤差，而不是 RSD

`linear_edge_over_subtraction_plausible` 這個詞本身有問題——plausible 不是 evidence。要證明 over-subtraction 需要 baseline ground truth，不是推測。

### 2.2 RSD 不是 baseline correction 的正確驗收 metric

RSD 衡量**重複性**，baseline correction 改善的是**準確性（accuracy）和線性（linearity）**，兩者不必然相關。如果 linear-edge 系統性低估 10%，RSD 還是可以很漂亮。

正確的 P2b validation 應該包含：
- **Spike-in recovery**（標準濃度系列回算誤差）
- **Linearity（R²、residual pattern）**
- **Blank subtraction 驗證**
- 然後才看 RSD 是否惡化

目前計畫只看 RSD + escape hatch，是 metric mismatch。

### 2.3 `GO_FOR_PRODUCTION_CANDIDATE` 是有害的半通過狀態

計畫自己寫「不是 production_ready，85RAW 未重跑」，但仍然發 GO note。這種半通過狀態詞會傳遞錯誤訊號——下一個工程師看到 GO note 會以為 P2b 已完成。

狀態應該二擇一：
- **明確 NO-GO**（等 85RAW 跑完再說）
- **CONDITIONAL-GO with explicit blockers**（列出 85RAW 作為硬性前置，不允許 Phase 2 C-specs 以此 note 作為依據）

### 2.4 AsLS 參數沒有針對資料調校

```python
asls_baseline(y, lam=1e5, p=0.01, n_iter=10)
```

這是 Eilers & Boelens 2005 論文對「典型 LC 色層寬度」的建議值。生物基質 LC-MS 的 matrix hump、tailing peak、drifting baseline 需要：
- `lam` 掃描實驗（stiffness 對不同 peak 寬度的敏感度分析）
- multi-peak trace 下的干擾分析（高強度鄰近峰會拉高當前峰的 baseline 估計，導致面積低估）

計畫把參數調校推遲到「shadow 觀察期再決定」，但 P2b GO note 已先發出。

---

## 三、Phase 1 → Phase 2 依賴鏈風險

### 3.1 P7 是真正的 critical path，但計畫把它當雜項

實際的 blocking chain：

```
P7（evidence chain cost control）
  → 85RAW 才能實際跑完
    → P2b 85RAW validation
      → P2b 正式 GO
        → C1b（刪除 linear-edge）
        → C5（單一積分入口）
          → C3（資料模型統一）
```

P7 被列為「P5 後面的效能雜項」，但它是整個 Phase 2 清理鏈能不能推動的 hard prerequisite，應該升格為 critical path。

### 3.2 P2b 85RAW 未過，整個 Phase 2 baseline 清理鏈懸空

C1a、C5、C1b 的設計前提都是「AsLS 是 production baseline」。若 85RAW P2b 結果是 NO-GO：
- C1b 的「刪除 linear-edge」目標消失
- C5 的「單一積分入口」要決定是否支援 linear-edge fallback
- 整個 baseline 清理序列要重新設計

計畫應該明確說明 P2b NO-GO 時的 fallback plan。

### 3.3 C2 清理 resolver 範圍不完整

C2 要清 `discovery/models.py:117` 和 `instrument_qc/pipeline_extraction.py:126` 的 hardcoded `local_minimum`，但 alignment 路徑的 hardcoded `local_minimum` 在哪？沒有說明。Phase 2 結束後可能仍有未清理的 `local_minimum` 路徑。

### 3.4 C6 抽 grouping primitives 缺少保護機制

10+ 個 alignment 模組各自有微妙不同的 tolerance/tie-break/eject 邏輯。「Scope A only，不改演算法」是很難保證的承諾，除非：
- 每個 call site 有 golden test 鎖住現行行為
- 抽 primitive 時有 parameter sweep 確認 byte-identical

計畫沒有這兩者。C6 是「靜靜引入 regression」的高風險清理。

---

## 四、C3 時機問題：把最重要的事排到最後

### 4.1 C3 是 Phase 2 的真正主菜，但被放在最末端

`PeakCandidate / PeakResult / PeakDetectionResult` → `PeakHypothesis / EvidenceVector / IntegrationResult / AuditTrail` 的遷移，才是 handoff 願景的核心。C1a/C1b/C2/C4/C5/C6 全部是周邊清理。

依賴鏈問題：
- **C5 先設計 `AreaIntegrationResult` DTO**，但 C3 的 `IntegrationResult` 還沒定義 → C5 的 DTO 等於先猜形狀，C3 時還要改一次
- **C4 在 legacy spine 基礎上拆 `peak_scoring.py`** → C3 時又要動一次
- 正確順序應該是 **C3 (3a/3b 加欄位 + dual-write) 先做，其他清理在 hypothesis spine 上進行**

### 4.2 Dual-write 期沒有 timebox 也沒有 abort criteria

C3 的 7 個 sub-PR（3a→3g）中，dual-write 橫跨 3b 到 3e。這期間：
- legacy 和 handoff 兩套都要同時維護
- 任何 bug fix 要動兩個地方
- 若 P2b 85RAW 期間有問題，要同時改兩條 spine

計畫沒有給 dual-write 期的 timebox，也沒有 abort criteria。

### 4.3 `signal_processing.py` shim 可能永久存活

「向下相容 shim」沒有 deprecation timeline 和 sunset date，外部使用者沒有遷移壓力，shim 會變成永久技術債。應訂下 sunset date 和 migration notice 機制。

---

## 五、計畫是否真的朝 handoff 願景前進？

### 5.1 對照表

| Handoff 願景核心元素 | 計畫對應 | 真實狀態 |
|---|---|---|
| Trace / TraceGroup 抽象層 | 無 | **完全沒做** |
| PeakHypothesis enumeration（多來源） | C3 末端做 | 延後到最後 |
| EvidenceVector（多來源 converge） | P5 只加 audit 欄位 | Evidence 沒有真正 converge |
| Model selection（WIS + mixture model） | 無 | **完全沒做** |
| Raw baseline-corrected integration 分離 | P2 shadow | 部分，production 仍 linear-edge |
| AuditTrail | C3 末端 | 延後 |

**Phase 1 + Phase 2 全部完成後，仍然沒有 hypothesis enumeration、沒有 evidence convergence、沒有 model selection。**

### 5.2 缺失的 Vision Milestone

要驗證計畫是否真的朝願景走，roadmap 應該有以下 milestone（目前全部缺失）：

| Milestone | 定義 |
|---|---|
| **M1 TraceGroup 落地** | 哪怕是 wrapper，能從 ROI/EIC 走到 group 結構 |
| **M2 Multi-source hypothesis enumeration** | 真實案例從 local_min、CWT、curvature、derivative ≥2 個 source 產出多組 boundary candidate |
| **M3 EvidenceVector schema 凍結** | 至少 3 個獨立 source contribute，有 schema 文件 |
| **M4 Model selection criterion 實作** | AIC/BIC/WIS-weighted，有 spike-in 驗證 |
| **M5 End-to-end case** | 從 trace 到 AuditTrail 完整跑通一個 case |

每個 P-spec 和 C-spec 都應該能說明它推進了哪個 milestone。目前沒有任何 step 對應上述 milestone。

### 5.3 計畫受政治考量影響的跡象

以下幾個訊號放在一起，計畫看起來像是「為了 ship 而設計，不是為了正確而設計」：

- P2b gate 語義被修改以避免 NO-GO 結論
- region_first_safe_merge 的 gate 設計像是「不想動到 production 太多」
- Alignment 繼續用 local_minimum（production 定量數字不動）
- `GO_FOR_PRODUCTION_CANDIDATE` 半通過狀態詞
- 大量 audit-only / shadow / diagnostic-only 標籤

這些不是技術錯誤，而是「選擇讓每一步變動最小化」的結果。這樣的計畫永遠無法真正跨越到 handoff 願景的架構，因為它每一步都在避免打破現狀。

---

## 六、建議的調整方向（優先序）

1. **P2b 補做正確的驗收實驗**：spike-in recovery、linearity、blank 驗證。不接受用鬆動 gate 過關；若 AsLS 確實沒贏 linear-edge，誠實寫 NO-GO 並重新調參。

2. **`region_first_safe_merge` 改名**為 `local_minimum_with_wis_merge_v1`，並在 roadmap 上明確標記「真正的 region-first（多來源 boundary enumeration）」是尚未開始的 v2 工作。

3. **P7 升格為 critical path**，在 Phase 2 kick-off 前確認 P7 已 validated。

4. **P2b NO-GO fallback plan 寫進 spec**：明確說明 85RAW 結果為 NO-GO 時 C1a/C1b/C5 的重新設計路徑。

5. **C3 提前到 Phase 2 最前面**（至少 3a/3b），讓其他清理 C-spec 在 hypothesis spine 上進行，而不是在 legacy spine 做完再遷移一次。

6. **驗收 metric 加入 P95/MAD 和 spike-in recovery**，不要只依賴 median RSD。

7. **在 roadmap 上加入 Vision Milestone 層**（M1–M5），讓每個 spec 的貢獻能對應到真實的架構進展。

8. **`signal_processing.py` shim 訂 sunset date**，記錄 migration notice 機制。

---

## 七、給 Codex 的審查重點

請 Codex 針對以下問題做獨立評估：

1. 目前 `region_first_safe_merge` 的實作（`peak_detection/region_safe_merge.py:54-186`）是否真的改變了 boundary decision 的來源，還是只是在 local_minimum 的結果上加後處理？

2. `asls_baseline` 的參數（lam=1e5, p=0.01）在什麼 peak width 和 baseline slope 的組合下會出現 over-subtraction 或 under-subtraction？有沒有針對目前資料集做過 sensitivity 分析？

3. Phase 2 的 C spec 執行順序（C1a → C2 → C5 → C1b → C3 → C4 → C6）是否合理？如果 C3 提前到 C1a 之後，會有什麼技術上的障礙？

4. `xic_extractor/signal_processing.py` 的 re-export shim 目前規模有多大？外部 caller 有多少？若永久保留，對架構有何實質影響？

5. Handoff 願景中的 WIS (Weighted Interval Scheduling) model selection，在目前程式碼架構中最接近的實作是哪裡？距離完整實現還有多遠？
