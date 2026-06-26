# Docs cleanup direction-lock review archive

Branch: `codex/docs-cleanup`
Status: completed phase summary
Validation status: `diagnostic_only`

## Summary

This phase settled the XIC docs cleanup policy:

- repo is the public source-of-truth and self-sufficient stub surface;
- Obsidian is the private long-form lab notebook;
- stable historical claims must be formalized into canonical repo owners or
  same-path public stubs before long original notes are treated as private
  context;
- destructive cleanup remains blocked until concrete paths, replacement owners,
  exact referrers, and user approval are all present.

## Completed Work

- Added the high-frequency repo/Obsidian rule to `AGENTS.md`.
- Made `docs/agent/obsidian-handoff-contract.md` the full policy owner.
- Updated `docs/project-layout.md` to route new docs and historical claims.
- Updated the classification inventory with direction-lock status and stub exit
  rule.
- Converted four exact-path referenced historical docs into self-sufficient
  same-path public stubs:
  - `docs/deepresearch/Backfill Production Gate.md`
  - `docs/superpowers/notes/2026-05-24-resolver-default-switch-validation-note.md`
  - `docs/superpowers/notes/2026-05-26-p2b-area-mismatch-triage-note.md`
  - `docs/superpowers/notes/2026-05-26-p8b-85raw-superwindow-acceptance-note.md`
- Created and read back optional private Obsidian indexes:
  `[[XIC File Management Patch 1 Repo Stubs]]` and
  `[[XIC Docs Cleanup Direction Lock]]`.

## Review Outcome

- `strategy-challenger`: no blocker; recommended treating same-path stubs as
  temporary unless exact-path retention is bound by hash, checker, fixture,
  artifact contract, or compatibility reference.
- `docs-handoff-reviewer`: found one blocker, a concrete sample-level identifier
  in the resolver stub. The current handoff records that the stub was sanitized
  and needs re-check before final acceptance.

## Non-Changes

No productization maturity tier, active lane, writer authority, validation
verdict, workbook schema, output behavior, selected area/counting, or matrix
authority changed in this phase.
