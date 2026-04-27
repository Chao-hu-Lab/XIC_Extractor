# Claude 系統級使用優化設計

**日期：** 2026-04-27  
**範圍：** 全域（`~/.claude/`），適用所有專案  
**觸發：** Claude Code Insights 報告識別的三大系統級摩擦點

---

## 背景與動機

Insights 分析 66 個 sessions（134h）後，識別出三大摩擦類型：

| 摩擦類型 | 代表事件 |
|---------|---------|
| Claude 搶先行動 | 「改 Top N default 為 0」→ Claude 直接移除整個功能；被問 branch lineage → 直接建 config |
| 程式碼有 bug 才被發現 | ruff 只 format 不 lint，bug 要到 commit 前的 pytest-guard 才被攔截 |
| 探索方向錯誤 | 搜 ms-core 卻應搜 DNP；安裝 173 個 skills 而非過濾後的子集 |

本設計解決第一和第二類（第三類為使用者端 prompt 習慣，不在此次範圍）。

---

## 設計方案 B：置頂規則 + Hook 強化 + Custom Skills

### 1. CLAUDE.md `## 行為約束` 區塊

**位置：** 全域 `~/.claude/CLAUDE.md` 第三行之後（`## 語言` 與 `## 終端環境` 之間）

**目的：** CLAUDE.md 越早出現的規則權重越高，置頂確保每次 session 都優先載入。

**內容：**

```markdown
## 行為約束

### 先回答，再行動
被問到問題時（「這個 branch 從哪來？」「這個參數什麼意思？」），
必須先用文字回答，才能進行任何工具呼叫。
❌ 錯誤：被問 branch lineage → 直接建立 config 檔
✅ 正確：先解釋 branch 來源 → 等使用者確認再動手

### 只改被要求的部分
「把 default 改成 0」= 只改那一個預設值。
不重構、不刪功能、不新增抽象層。
❌ 錯誤：「改 Top N default 為 0」→ 直接移除整個 Top N 功能
✅ 正確：只修改 default 參數值，其餘不動
```

---

### 2. `ruff-hook.js` 強化

**檔案：** `~/.claude/scripts/ruff-hook.js`

**現有流程：**
```
Edit/Write → ruff format（靜默，async）
```

**新流程：**
```
Edit/Write → ruff format → ruff check --fix → 若仍有問題 → 回傳警告給 Claude
```

**行為規格：**
- 非 `.py` 檔案：直接跳過（保留現有邏輯）
- `ruff format`：自動修正格式（保留）
- `ruff check --fix`：自動修正可修的 lint 問題（新增）
- 若 `ruff check` 執行後仍有殘餘問題：回傳 `{ "decision": "warn", "message": "ruff: N issues remain\n<output>" }`
- 無殘餘問題：靜默退出（不打擾使用者）

**關鍵決定：** 移除 `async: true`（改為同步）。`async` hook 的輸出不會回傳給 Claude，warn 訊息會被丟棄。同步執行對小 Python 檔案影響可忽略（< 1s）。

---

### 3. Custom Skills

**位置：** `~/.claude/skills/pre-run/` 和 `~/.claude/skills/commit-sub/`  
**調用方式：** `/pre-run`、`/commit-sub`（加入 CLAUDE.md 的 ECC 常用指令表）

#### Skill 1：`/pre-run`（執行前確認清單）

呼叫後 Claude 依序確認以下清單，逐一執行並列出結果。**任何一項不通過必須停下等確認，不自動繼續。**

```
[ ] pwd — 確認工作目錄（必須是預期的專案路徑）
[ ] git branch --show-current — 確認在正確 branch
[ ] 列出可用 config YAML，等使用者選擇（不自動假設）
[ ] 確認輸出資料夾名稱 + suffix（例：results_2026-04-27）
[ ] 確認目標路徑是否已存在（存在則強制加 suffix，不覆蓋）
[ ] 顯示執行摘要，等待使用者 OK
```

#### Skill 2：`/commit-sub`（submodule + parent 提交流程）

強制執行正確提交順序：

```
[ ] 確認目前在 submodule（ms-core）路徑
[ ] git status 確認 submodule 有變更
[ ] commit ms-core（conventional commits 格式）
[ ] 切回 parent repo（ms-toolkit）
[ ] git status 確認 submodule pointer 已更新
[ ] commit parent repo
[ ] 驗證：submodule pointer hash == ms-core HEAD hash
```

**新增至 CLAUDE.md `## ECC 常用指令`：**
```
- `/pre-run`  — 執行 pipeline 前的強制確認清單
- `/commit-sub` — submodule + parent 正確提交流程
```

---

## 實作順序

1. **CLAUDE.md** — 在 `## 語言` 後插入 `## 行為約束`（最高優先，最先實作）
2. **ruff-hook.js** — 加入 `ruff check --fix` 邏輯與 warn 回傳
3. **Skill 檔案** — 建立 `~/.claude/skills/pre-run/SKILL.md` 和 `~/.claude/skills/commit-sub/SKILL.md`
4. **CLAUDE.md ECC 指令表** — 加入兩個新 skill 的條目

## 不在範圍內

- PreToolUse hook 攔截（使用者偏好行為指引，非硬性攔截）
- 探索方向錯誤（屬使用者端 prompt 習慣，非系統設定可解決）
- 專案級 pipeline 規則（domain-specific，應放在各專案 CLAUDE.md）
