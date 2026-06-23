# XIC handoffs

這裡只放開發交接文件，不放產品 spec、正式 validation note、或 release
contract。handoff 的用途是讓下一個 agent/session 快速知道最近在做什麼、
什麼真的可用、什麼還沒收掉、下一步先做哪裡。

## Current handoff

- [cc-framework-improvements productization](current/cc-framework-improvements-productization.md)

## Naming

- `current/<branch-slug>-<topic>.md`: 目前活躍分支的最新接手狀態，可定期覆寫維護。
- `archive/<timestamp>_<branch-slug>_<topic>_<shortsha>.md`: commit、PR、重大 RAW 驗證、或重要決策後才需要建立的快照，不覆寫。

不要使用只有 `current` 或 `handoff` 的泛名，避免不同分支或不同主題互相覆蓋。

## Authority

handoff 不是產品權威。若文件衝突:

1. `git status` / `git diff` 決定目前工作樹實況。
2. productization control plane 決定 maturity tier、active lane、WIP owner、promotion gate。
3. named specs/plans 決定 schema、CLI/config/output 行為契約。
4. validation notes 決定 RAW/benchmark evidence。
5. handoff 只做白話摘要、接手順序、下一步建議。
