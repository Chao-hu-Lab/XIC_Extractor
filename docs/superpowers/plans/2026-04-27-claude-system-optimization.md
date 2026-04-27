# Claude 系統級使用優化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 透過修改全域 `~/.claude/` 設定，減少 Claude 搶先行動與 lint bug 未被即時發現兩類摩擦，並建立可重用的 pipeline 與 submodule 提交 skills。

**Architecture:** 四個獨立變更：(1) CLAUDE.md 置頂行為約束規則；(2) ruff-hook.js 從純 format 強化為 format + lint + warn；(3) `/pre-run` custom skill；(4) `/commit-sub` custom skill + CLAUDE.md ECC 路由更新。每個任務可獨立完成並驗證。

**Tech Stack:** Node.js（hooks）、Markdown（CLAUDE.md / skills）、ruff（linter）

---

## Task 1：CLAUDE.md 插入 `## 行為約束` 區塊

**Files:**
- Modify: `C:/Users/user/.claude/CLAUDE.md`（在 `## 語言` 與 `## 終端環境` 之間插入新區塊）

- [ ] **Step 1：確認插入位置**

  在 `~/.claude/CLAUDE.md` 中找到以下兩行之間的位置：
  ```
  ## 語言
  永遠以繁體中文回應。...
  
  ## 終端環境       ← 新內容插在這行之前
  ```

- [ ] **Step 2：插入 `## 行為約束` 區塊**

  在 `## 終端環境` 之前插入以下內容（保留空行）：

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

- [ ] **Step 3：驗證**

  讀取 `~/.claude/CLAUDE.md`，確認：
  - `## 行為約束` 出現在 `## 語言` 之後、`## 終端環境` 之前
  - 兩條規則都有 ❌/✅ 範例
  - 其餘內容未被改動

- [ ] **Step 4：Commit**

  ```bash
  cd C:/Users/user/.claude
  git add CLAUDE.md
  git commit -m "chore(claude): add behavior-constraint rules at top of CLAUDE.md"
  ```

---

## Task 2：ruff-hook.js 強化（format + lint + warn）

**Files:**
- Modify: `C:/Users/user/.claude/scripts/ruff-hook.js`（完整替換）
- Modify: `C:/Users/user/.claude/settings.json`（移除 `async: true`，更新 `statusMessage`）

- [ ] **Step 1：完整替換 ruff-hook.js**

  將 `~/.claude/scripts/ruff-hook.js` 內容替換為：

  ```javascript
  // PostToolUse hook: format then lint Python files after Edit/Write/MultiEdit
  const d = JSON.parse(require('fs').readFileSync(0, 'utf8'));
  const f = (d.tool_input && d.tool_input.file_path) ||
            (d.tool_response && d.tool_response.filePath);

  if (!f || !f.endsWith('.py')) process.exit(0);

  const { spawnSync } = require('child_process');

  // 1. Auto-format (always silent)
  spawnSync('ruff', ['format', f], { stdio: 'pipe' });

  // 2. Auto-fix lint issues
  spawnSync('ruff', ['check', '--fix', f], { stdio: 'pipe' });

  // 3. Check for remaining unfixable issues
  const check = spawnSync('ruff', ['check', f], { encoding: 'utf8' });
  if (check.status !== 0) {
    const msg = ((check.stdout || '') + (check.stderr || '')).trim();
    process.stdout.write(JSON.stringify({
      decision: 'warn',
      message: `ruff: lint issues remain after auto-fix — fix before committing:\n${msg}`
    }));
  }
  ```

- [ ] **Step 2：更新 settings.json 的 PostToolUse hook**

  在 `~/.claude/settings.json` 中，將 `PostToolUse` hook 從：
  ```json
  {
    "type": "command",
    "command": "node C:/Users/user/.claude/scripts/ruff-hook.js",
    "timeout": 15,
    "statusMessage": "ruff formatting...",
    "async": true
  }
  ```
  改為：
  ```json
  {
    "type": "command",
    "command": "node C:/Users/user/.claude/scripts/ruff-hook.js",
    "timeout": 20,
    "statusMessage": "ruff format + lint..."
  }
  ```
  （移除 `async: true`；`timeout` 從 15 升至 20 以容納兩次 ruff 呼叫；更新 `statusMessage`）

- [ ] **Step 3：本地驗證（手動）**

  建立一個含 lint 錯誤的測試檔，確認 hook 行為：

  ```bash
  # 建立含 lint 問題的暫存 Python 檔
  echo "import os\nimport sys\nx=1" > C:/Temp/ruff_test.py

  # 直接執行 hook 腳本，模擬 Claude 的 tool_input
  echo '{"tool_input":{"file_path":"C:/Temp/ruff_test.py"}}' | node C:/Users/user/.claude/scripts/ruff-hook.js
  ```

  預期結果：
  - 若 `import os` 未被使用，輸出應包含 `"decision":"warn"` 和 ruff 錯誤訊息
  - 若所有問題均被 `--fix` 修復，無輸出（靜默退出）

  ```bash
  # 清理暫存檔
  rm C:/Temp/ruff_test.py
  ```

- [ ] **Step 4：Commit**

  ```bash
  cd C:/Users/user/.claude
  git add scripts/ruff-hook.js settings.json
  git commit -m "chore(hooks): add ruff check+fix with warn fallback, remove async"
  ```

---

## Task 3：建立 `/pre-run` Custom Skill

**Files:**
- Create: `C:/Users/user/.claude/skills/pre-run/SKILL.md`

- [ ] **Step 1：建立目錄**

  ```bash
  mkdir -p C:/Users/user/.claude/skills/pre-run
  ```

- [ ] **Step 2：建立 SKILL.md**

  建立 `C:/Users/user/.claude/skills/pre-run/SKILL.md`，內容如下：

  ```markdown
  # /pre-run — Pipeline 執行前確認清單

  執行此 skill 時，依序完成以下確認。
  **任何一項不通過，停止並等待使用者確認，不自動繼續。**

  ## 執行步驟

  - [ ] **工作目錄** — 執行 `pwd`，顯示結果，確認是預期的專案路徑
  - [ ] **Branch** — 執行 `git branch --show-current`，確認在正確 branch
  - [ ] **Config 選擇** — 列出所有 `*.yaml` / `*.yml` 檔案，等使用者選擇（不自動假設）
  - [ ] **輸出路徑** — 詢問輸出資料夾名稱，建議加上日期 suffix（例：`results_YYYY-MM-DD`）
  - [ ] **覆蓋檢查** — 確認目標輸出路徑是否已存在；若存在，強制加 suffix，不覆蓋現有資料
  - [ ] **執行摘要** — 逐項列出以上確認結果，等待使用者輸入 OK 後再繼續
  ```

- [ ] **Step 3：驗證**

  讀取剛建立的檔案，確認六個 checklist 項目均在，且路徑正確：
  ```bash
  cat C:/Users/user/.claude/skills/pre-run/SKILL.md
  ```

- [ ] **Step 4：Commit**

  ```bash
  cd C:/Users/user/.claude
  git add skills/pre-run/SKILL.md
  git commit -m "feat(skills): add /pre-run pipeline pre-flight checklist skill"
  ```

---

## Task 4：建立 `/commit-sub` Custom Skill 並更新 CLAUDE.md

**Files:**
- Create: `C:/Users/user/.claude/skills/commit-sub/SKILL.md`
- Modify: `C:/Users/user/.claude/CLAUDE.md`（ECC 指令表 + skill 路由規則）

- [ ] **Step 1：建立目錄**

  ```bash
  mkdir -p C:/Users/user/.claude/skills/commit-sub
  ```

- [ ] **Step 2：建立 SKILL.md**

  建立 `C:/Users/user/.claude/skills/commit-sub/SKILL.md`，內容如下：

  ```markdown
  # /commit-sub — Submodule + Parent Repo 提交流程

  強制執行正確提交順序，避免 submodule pointer 不一致。

  ## 執行步驟

  - [ ] **確認位置** — 執行 `pwd`，確認目前在 submodule（ms-core）路徑
  - [ ] **檢查 submodule 變更** — 執行 `git status`，確認有待提交的變更
  - [ ] **Commit submodule** — 依 conventional commits 格式 commit ms-core（`feat:`/`fix:`/`refactor:` 等）
  - [ ] **切回 parent repo** — 切換到 ms-toolkit（parent repo）路徑
  - [ ] **確認 pointer 更新** — 執行 `git status`，確認 submodule pointer 顯示為 modified
  - [ ] **Commit parent repo** — Commit ms-toolkit，訊息說明更新了 submodule（例：`chore: bump ms-core to <hash>`）
  - [ ] **驗證一致性** — 執行 `git submodule status`，確認 pointer hash == ms-core HEAD hash
  ```

- [ ] **Step 3：更新 CLAUDE.md — ECC 常用指令表**

  在 `~/.claude/CLAUDE.md` 的 `## ECC 常用指令` 區塊，將現有內容：
  ```markdown
  - `/plan` — 建立實作計畫
  - `/tdd` — TDD 工作流
  - `/code-review` — 程式碼品質審查
  - `/security-review` — 安全掃描
  - `/e2e` — 端對端測試
  ```
  改為：
  ```markdown
  - `/plan` — 建立實作計畫
  - `/tdd` — TDD 工作流
  - `/code-review` — 程式碼品質審查
  - `/security-review` — 安全掃描
  - `/e2e` — 端對端測試
  - `/pre-run` — 執行 pipeline 前的強制確認清單
  - `/commit-sub` — submodule + parent 正確提交流程
  ```

- [ ] **Step 4：更新 CLAUDE.md — 新增 skill 路由規則**

  在 `## ECC 常用指令` 區塊末尾（`/commit-sub` 條目之後）追加以下說明，讓 Claude 知道如何找到這些 skill：

  ```markdown

  > 當使用者輸入 `/pre-run` 或 `/commit-sub`，使用 Read 工具讀取對應 skill 檔案並依其指示執行：
  > - `/pre-run` → `C:/Users/user/.claude/skills/pre-run/SKILL.md`
  > - `/commit-sub` → `C:/Users/user/.claude/skills/commit-sub/SKILL.md`
  ```

- [ ] **Step 5：端對端驗證**

  讀取 `~/.claude/CLAUDE.md`，確認：
  - ECC 指令表有 `/pre-run` 和 `/commit-sub` 兩條新條目
  - skill 路由說明區塊存在且路徑正確
  - `## 行為約束`（Task 1 的變更）仍在正確位置

  ```bash
  grep -n "pre-run\|commit-sub\|行為約束" C:/Users/user/.claude/CLAUDE.md
  ```

  預期輸出：至少 4 行，包含行為約束區塊標題與兩個 skill 條目各兩處引用。

- [ ] **Step 6：Commit**

  ```bash
  cd C:/Users/user/.claude
  git add skills/commit-sub/SKILL.md CLAUDE.md
  git commit -m "feat(skills): add /commit-sub skill and update CLAUDE.md ECC routing"
  ```

---

## 驗收標準

完成後，以下情境應有不同的行為：

| 情境 | 舊行為 | 新行為 |
|------|--------|--------|
| 使用者問「這個參數是什麼意思？」 | Claude 直接改檔案 | Claude 先回答問題，等確認再動手 |
| 「把 Top N default 改成 0」 | Claude 重構或刪除功能 | Claude 只改那一行預設值 |
| Edit Python 檔案後有 lint 問題 | 靜默通過，commit 前才被 pytest-guard 攔 | 立即顯示 ruff warn，Claude 當下修復 |
| 輸入 `/pre-run` | 無反應 | Claude 讀取 SKILL.md，執行六項確認清單 |
| 輸入 `/commit-sub` | 無反應 | Claude 讀取 SKILL.md，依序完成七步驟提交流程 |
