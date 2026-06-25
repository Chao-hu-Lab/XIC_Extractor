# Docs cleanup official-docs and handoff snapshot

Branch: `codex/docs-cleanup`
Status: active branch-scoped handoff for documentation cleanup, Obsidian migration rules, and handoff mechanism repair
Validation status: `diagnostic_only`

## Current Objective

Complete the safe documentation-management phase before any tracked-file
removal: repo formal docs and branch handoff stubs stay self-sufficient, while
long private development history can later move to Obsidian only after a
verified pilot and explicit file-management approval.

## Current State

- The repo now has a formal hybrid contract at
  `docs/agent/obsidian-handoff-contract.md`.
- `AGENTS.md`, `docs/project-layout.md`,
  `docs/agent/communication-review.md`,
  `docs/superpowers/handoffs/README.md`, and
  `docs/superpowers/plans/2026-06-15-productization-control-plane.md` route
  future agents back to the contract.
- The working classification inventory is
  `docs/superpowers/notes/2026-06-25-obsidian-migration-classification-inventory.md`.
  It is not a deletion list; every row currently has
  `Destructive allowed now = no`.
- The productization status anchor remains
  `docs/superpowers/handoffs/current/cc-framework-improvements-productization.md`.
  It is not the current branch handoff.
- This file is the branch-scoped handoff for `codex/docs-cleanup`.

## Active Decisions

- Formal source-of-truth docs, public contracts, validation policy, product
  maturity state, and machine-checkable authority stay in repo.
- Long scratch history, raw development narrative, command transcripts, and
  private/local context belong in Obsidian or ignored artifacts, not public repo
  history.
- Treat repo docs as the public documentation surface: publish formal rules,
  compact decisions, and sanitized stubs; keep the full private development
  history in Obsidian like a lab notebook.
- Any repo stub that points to Obsidian must still support the next 1-3 safe
  actions when Obsidian is unavailable.
- If a tracked file is still exact-path referenced, do not remove it merely
  because the long detail was copied or routed to Obsidian. Keep a sanitized
  same-path stub or update every repo referrer to a formal owner first.
- PR body should be the durable closeout surface after merge preparation; do
  not paste raw handoff or private Obsidian-only context into it.

## Obsidian Pilot

- `Get-Command obsidian` found an Obsidian CLI shim on `PATH`.
- Sandboxed CLI calls could not reach Obsidian IPC, but approved external CLI
  execution can read the running app and a user-approved private vault.
- No callable Obsidian MCP tool was available in this Codex session; only local
  Obsidian skills were available as instructions.
- Pilot note `[[XIC Docs Cleanup Hybrid Handoff]]` was created in the
  confirmed private vault, linked from `[[XIC Extractor Handoffs Index]]`,
  overwritten once to fix PowerShell escaping, and read back through the
  Obsidian CLI.
- Vault write/readback is `readback_verified` for this one-note pilot. Bulk
  migration and repo file removal remain blocked until a concrete migration
  batch is approved.

## Review Status

- Strategy review initially flagged over-aggressive movement for the current
  capability inventory, exact-path referenced validation notes, and missing
  authority-owner rows. The inventory now keeps the capability inventory in repo,
  marks referenced historical notes as `repo_stub_plus_obsidian`, and includes
  productization authority / mechanical adjudication owner artifacts. Backfill
  history rows that can move only after a stub now also name the same-path
  stub/referrer-update requirement.
- Handoff/docs review flagged that new canonical docs were still untracked and
  that the productization control plane did not list the Obsidian contract.
  The control plane now lists `docs/agent/obsidian-handoff-contract.md`, and
  those branch docs were included in commit `b89850ed`.
- Cleanup review batch 1 manually checked five
  `needs_link_update_or_stub_before_repo_removal` rows against repo source,
  Obsidian copies, exact referrers, and current authority owners. Four remain
  `repo_stub_plus_obsidian`; `docs/superpowers/notes/backfill_broad_autowrite_feasibility_gate_v1.md`
  stays `keep_repo` because the status index and authority manifest still point
  to it as a hashed decision packet. The vault note is
  `[[XIC Cleanup Review Batch 1 Link Stub Rows]]`. No repo files were removed.
- The public/private publication boundary is now explicit in
  `docs/agent/obsidian-handoff-contract.md`, `docs/project-layout.md`,
  `docs/agent/communication-review.md`, and `docs/superpowers/handoffs/README.md`.
  This is documentation-governance only. It does not change productization
  maturity tier, active lane, writer authority, validation verdict, workbook
  schema, or output behavior; therefore the productization control plane does
  not need a state update for this patch.
- Read-only reviewer found no blocking issue in the docs-governance patch. The
  only non-blocking privacy finding was public repo exposure of the private
  vault name; repo text now uses generic private-vault wording instead.

## Important Touched Surfaces

- `.codex/hooks/xic_hook_policy.py`
- `.codex/hooks/xic_prompt_router.py`
- `.codex/hooks/xic_post_tool_guard.py`
- `.codex/hooks/fixtures/assert_hook_outputs.py`
- `.codex/skills/xic-goal-execution/SKILL.md`
- `.codex/skills/xic-productization-pulse/SKILL.md`
- `AGENTS.md`
- `docs/agent/obsidian-handoff-contract.md`
- `docs/agent/codex-operating-system.md`
- `docs/agent/communication-review.md`
- `docs/project-layout.md`
- `docs/superpowers/handoffs/README.md`
- `docs/superpowers/handoffs/current/cc-framework-improvements-productization.md`
- `docs/superpowers/handoffs/current/codex-docs-cleanup-official-docs-and-handoff.md`
- `docs/superpowers/notes/2026-06-25-obsidian-migration-classification-inventory.md`
- `docs/superpowers/plans/2026-06-15-productization-control-plane.md`
- `scripts/check_productization_state.py`
- `scripts/check_cid_nl_discovery_release_slice.py`

## Validation

Latest focused documentation checks passed on 2026-06-25 with `pwsh` 7 after
the public/private boundary update and reviewer privacy wording fix:

- `python .codex\hooks\fixtures\assert_hook_outputs.py`
- `python -m scripts.check_productization_state`
- `python -m scripts.check_productization_authority`
- `git diff --check`
- added-line secret/local-path/private-vault scan over the current diff

`git diff --check` and the secret/local-path scan emitted Git LF/CRLF warnings
only; the scan found no secret, API key, private key, absolute user path, or
absolute vault path/private vault name in added lines.

Not run for this documentation phase:

- PR CI-equivalent full gate;
- RAW-backed validation;
- bulk Obsidian migration or repo file removal.

Known unrelated residual:

- The release-slice checker still has a known source-hash mismatch for
`docs/superpowers/validation/productization_status_index_v1.tsv`; this goal does
not attempt to repair that unrelated source-hash mismatch.

## Next Actions

1. Close this goal as a documentation and workflow phase after final status
   inspection.
2. When the user explicitly approves file management, run the pilot/migration
   order in the classification inventory.
3. Do not `git rm`, archive, bulk migrate, stage, commit, push, or open a PR
   unless the user explicitly asks.
