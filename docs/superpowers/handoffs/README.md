# XIC handoffs

這裡只放開發交接文件，不放產品 spec、正式 validation note、或 release
contract。handoff 的用途是讓下一個 agent/session 快速知道最近在做什麼、
什麼真的可用、什麼還沒收掉、下一步先做哪裡。

## Productization status anchor

- [cc-framework-improvements productization](current/cc-framework-improvements-productization.md)

This file is a productization status anchor used by productization checks and
older productization planning surfaces. It is not the default handoff for every
branch.

## Naming

- `current/<branch-slug>-<topic>.md`: 目前活躍分支的最新接手狀態，可定期覆寫維護。
- `archive/<timestamp>_<branch-slug>_<topic>_<shortsha>.md`: commit、PR、重大 RAW 驗證、或重要決策後才需要建立的快照，不覆寫。
- Long logs, scratch analysis, and temporary exploration notes belong in
  `docs/superpowers/notes/` when they are worth keeping. Do not put raw logs in
  current handoff or archive.

不要使用只有 `current` 或 `handoff` 的泛名，避免不同分支或不同主題互相覆蓋。
不要把某個分支的 handoff 當作全 repo 預設；若檔內 `Branch:` 或 `Status:`
明顯屬於另一個分支，該檔只能讀，不能覆寫。

The global `$handoff` skill writes a temporary conversation handoff outside the
workspace. Use it for cross-session context transfer when a repo-tracked branch
handoff is not appropriate. Do not confuse that temporary output with the
branch-scoped repo handoff files in this directory.

If long-form context moves to Obsidian, the repo handoff still keeps a
self-sufficient sanitized stub. The stub may point to an optional Obsidian note
title or alias, but it must contain enough current objective, decisions,
validation, blockers, and next actions for an agent to resume without private
vault access. See `docs/agent/obsidian-handoff-contract.md`.

Repo handoffs are public-summary surfaces, not private lab notebooks. Do not
copy private Obsidian reasoning, command transcripts, local absolute paths,
sample-level investigation detail, or private data placement into a current
handoff, archive, or PR body. Distill the approved public decision and leave the
long reasoning in Obsidian.

## Maintenance

- Current handoff should stay short enough to read every time, normally under
  about 200 lines.
- Rewrite and prune current handoff instead of appending chronological updates.
- Archive only completed phase summaries: completed work, important decisions,
  rejected paths, and final validation.
- Use `[active]`, `[blocked]`, `[done]`, and `[superseded]` labels when helpful;
  remove `[done]` and `[superseded]` from current handoff during the next prune
  unless they prevent repeated mistakes.
- Every file under `current/` or `archive/` must have one row in
  `RETENTION.tsv`. Adding, moving, or deleting a handoff file without updating
  that inventory is a workflow bug.

## Retention inventory

`RETENTION.tsv` is the machine-readable cleanup queue for this directory. It is
not deletion approval. It records which files are active, which are public
evidence, which should move to Obsidian after PR review, and which may later be
removed only through an exact manifest plus explicit approval.

Allowed `retention_decision` values:

- `active_current`: active branch resume stub. Keep in `current/` only while
  the branch or PR workflow is live.
- `productization_anchor`: shared status anchor used by productization checks.
- `keep_repo_public_evidence`: compact public evidence that should remain in
  repo until the owning policy changes.
- `keep_repo_closeout_summary`: compact branch narrative or PR body seed.
- `keep_repo_until_referrers_removed`: exact manifest, referrer audit, or
  public cleanup evidence that may still be referenced by repo docs or PR
  review.
- `move_to_obsidian_after_pr`: useful branch/review history that should not
  live in repo indefinitely after PR review.
- `superseded_by_pr`: repo archive content already replaced by the PR body.
- `remove_after_merge_approval`: candidate for tracked removal after merge or
  closeout, but still requires a concrete manifest and explicit user approval.

Allowed `next_review_event` values are `active_branch_change`,
`pr_open_update`, `pr_merge_or_close`, `referrer_audit`,
`validation_cleanup`, `productization_policy_change`, and `manual_review`.

Run the read-only audit before PR closeout or whenever this directory changes:

```powershell
python tools/diagnostics/handoff_retention_audit.py
python tools/diagnostics/docs_management_audit.py
```

The audit can report candidates, but it must not auto-delete. `git rm`,
archive moves, or repo-tracked deletion still require exact paths, referrer
audit, and explicit user approval.

## PR closeout lifecycle

Current handoff is an input to closeout, not the durable endpoint.

1. During branch work, maintain only the branch-scoped current handoff named by
   the goal, PR workflow, or `current/<branch-slug>-<topic>.md`.
2. When opening or updating a PR, condense the current handoff into the PR body:
   problem, solution, verification actually run, residual risk, and next
   action. Do not paste the whole handoff or private Obsidian-only context.
3. If the completed phase must remain in repo history after PR closeout, write a
   compact archive summary under `archive/`.
4. After the PR is closed or merged, run the retention audit. Move
   `move_to_obsidian_after_pr` material into the private vault if it is still
   useful, mark PR-superseded material as `superseded_by_pr`, and prepare an
   exact cleanup manifest for any `remove_after_merge_approval` candidates.
5. Stop maintaining that branch current handoff unless a follow-up branch
   explicitly reuses it. Do not remove it from repo without the same manifest
   and explicit-approval flow used for other tracked deletions.

## Authority

handoff 不是產品權威。若文件衝突:

1. `git status` / `git diff` 決定目前工作樹實況。
2. productization control plane 決定 maturity tier、active lane、WIP owner、promotion gate。
3. named specs/plans 決定 schema、CLI/config/output 行為契約。
4. validation notes 決定 RAW/benchmark evidence。
5. handoff 只做白話摘要、接手順序、下一步建議。
