# Docs cleanup current handoff

Branch: `codex/docs-cleanup`
Status: active branch-scoped handoff for documentation cleanup and Obsidian boundary work
Validation status: `diagnostic_only`

## Current Objective

Finish the safe documentation-management phase without tracked-file removal:
repo docs stay self-sufficient and public; long development history can live in
Obsidian only after stable claims are represented by repo owners or sanitized
same-path stubs.

## Current State

- Policy owner: `docs/agent/obsidian-handoff-contract.md`.
- High-frequency rule: `AGENTS.md`.
- Placement summary: `docs/project-layout.md`.
- Product-topic representative docs:
  `docs/product/README.md`. Current first-pass topics are Backfill, Discovery,
  Alignment, and Presets; this layer is extensible and not a complete taxonomy.
- Working inventory:
  `docs/superpowers/notes/2026-06-25-obsidian-migration-classification-inventory.md`.
- Completed phase archive:
  `docs/superpowers/handoffs/archive/2026-06-25_codex-docs-cleanup_direction-lock-review.md`.
- Productization status anchor remains
  `docs/superpowers/handoffs/current/cc-framework-improvements-productization.md`;
  it is not this branch handoff.
- Optional private Obsidian indexes created and read back:
  `[[XIC Docs Cleanup Direction Lock]]` and
  `[[XIC File Management Patch 1 Repo Stubs]]`.

## Active Decisions

- Repo is the public source-of-truth surface: formal rules, validation policy,
  product authority, compact decisions, machine-checkable state, and
  self-sufficient branch stubs stay in repo.
- Obsidian is the private lab notebook: long reasoning, command diaries,
  discarded hypotheses, review detail, and local context stay private.
- Important historical claims must be formalized into a canonical repo owner or
  same-path sanitized stub before the long source note is treated as private
  context.
- Related global product topics should be grouped into small representative
  repo docs when possible. Backfill, Discovery, Alignment, and Presets now have
  first-pass owners under `docs/product/`; future global topics can be added
  there instead of preserved as scattered dated notes.
- Same-path stubs are temporary unless the exact path is deliberately bound by a
  hash, checker, fixture, artifact contract, or compatibility reference.
- No `git rm`, archive move, bulk migration, tracked-file deletion, staging,
  commit, push, or PR action is authorized unless the user explicitly asks.

## Current Patch

File-management patch 1 replaced four long historical docs with self-sufficient
same-path public stubs:

- `docs/deepresearch/Backfill Production Gate.md`
- `docs/superpowers/notes/2026-05-24-resolver-default-switch-validation-note.md`
- `docs/superpowers/notes/2026-05-26-p2b-area-mismatch-triage-note.md`
- `docs/superpowers/notes/2026-05-26-p8b-85raw-superwindow-acceptance-note.md`

The long diaries already exist in the private vault and were read back before
the stubs were written. Existing repo referrers still point to these paths, so
the stubs stay tracked for now.

File-management patch 4 replaced three Backfill strategy/reset diaries with
self-sufficient same-path public stubs:

- `docs/superpowers/notes/2026-06-18-backfill-autowrite-ground-truth-critical-review.md`
- `docs/superpowers/notes/2026-06-18-backfill-autowrite-ground-truth-strategy-note.md`
- `docs/superpowers/notes/2026-06-18-chatgpt_reset_backfill_productization_objective.md`

The stable Backfill claims are already owned by the control plane, status index,
authority manifest, mechanical adjudication surfaces, and parked
broad-autowrite decision packet. Existing repo referrers still point to these
paths, so the stubs stay tracked for now.

Product-topic consolidation added `docs/product/` as the repo-readable entry
layer for durable topic summaries. It currently covers Backfill, Discovery,
Alignment, and Presets, while explicitly remaining extensible for other global
product topics.

Cleanup patch 2 reviewed those exact referrers. Active evidence owners,
validated command-profile docs, retained fixtures, and historical plans still
need the same paths as provenance/compatibility references. The patch records
those retention reasons in the inventory and sanitizes directly related
`d3-N6-medA` narrative sample-level details in `docs/diagnostic-ledger.md`.

File-management patch 3 replaced four validation/closeout diaries with
self-sufficient same-path public stubs:

- `docs/superpowers/notes/2026-05-28-qualitative-selection-acceptance-gate-note.md`
- `docs/superpowers/notes/2026-06-05-gaussian15-ms1-morphology-production-ready-closeout.md`
- `docs/superpowers/notes/2026-06-05-gaussian15-ms1-peak-group-nl-scope-production-ready-closeout.md`
- `docs/superpowers/notes/2026-06-15-replay-executor-validation-note.md`

The long diaries already exist in the private vault and were read back before
the stubs were written. Existing repo referrers still point to these paths, so
the stubs stay tracked for now.

## Acceptance Review

- `docs-handoff-reviewer` found one blocker: the resolver stub exposed a
  concrete sample-level identifier. Fixed by keeping only sanitized
  same-surface `d3-N6-medA` probe wording.
- `strategy-challenger` found no blocker and recommended making same-path stubs
  explicitly temporary unless exact-path retention is justified. The policy and
  inventory now include that exit rule.
- Original `docs-handoff-reviewer` re-check passed: the sample-level identifier
  is gone from the resolver stub, current handoff, and archive summary; no
  blocking finding remains.
- Patch 3 `strategy-challenger` found no blocker. It accepted same-path stubs
  while exact referrers remain and recommended tightening the replay stub status
  to a single validation tier; fixed.
- Patch 3 `docs-handoff-reviewer` found no blocker. Stubs are repo-readable
  without private vault access, no destructive action is authorized, and no
  control-plane tier/lane update is needed.
- Patch 4 read-only docs/strategy review found no blocker. The Backfill
  strategy stubs are self-contained, keep Obsidian optional, preserve the
  current `park_broad_backfill` / 511-cell authority state, and do not need a
  control-plane update.
- Product-topic docs read-only review found no blocker. Two precision findings
  were fixed: `alignment_run_metadata.json` is conditional provenance output,
  not a fixed validation-minimal output; built-in preset TOML resources live
  under `xic_extractor/presets/data/`.
- Critical artifact review then found two document-quality blockers for the
  new `docs/product/` layer: status wording mixed document status with product
  evidence, and topic pages did not state what questions they answer. Fixed by
  adding a topic-page contract and aligning Backfill, Discovery, Alignment, and
  Presets to `Answers`, `Does Not Answer`, public surfaces, workflow,
  verification gates, wrong moves, owners, and update triggers.

## Productization Impact

This patch does not change productization maturity tier, active lane, writer
authority, validation verdict, workbook schema, output behavior, selected
area/counting, or matrix authority. No productization control-plane state update
is needed for this documentation-governance patch.

Patch 4 also does not require a productization control-plane update: it only
externalizes private strategy history and leaves the current `park_broad_backfill`
decision, 511-cell authority, mechanical adjudication status, and Backfill lane
state unchanged.

The `docs/product/` additions also do not require a productization control-plane
update: they are routing/source-of-truth summaries and do not replace the
control plane, status index, authority manifest, evidence rules, architecture
contract, or runner settings.

The topic-page contract cleanup also does not require a productization
control-plane update: it clarifies documentation status, evidence labels,
question coverage, owner routing, and update triggers. It does not change
maturity tier, active lane, writer authority, output schema, review/replay
behavior, selected area/counting, matrix values, or matrix authority.

## Verification

Latest checks passed after the blocker fix and handoff prune:

- `python .codex\hooks\fixtures\assert_hook_outputs.py`
- `python -m scripts.check_productization_state`
- `python -m scripts.check_productization_authority`
- `git diff --check` with LF/CRLF warnings only
- added-line secret/local-path/private-data/sample-id scan
- sample-id scan for the fixed blocker
- exact referrer scan for the four stubbed paths
- Obsidian CLI write/readback for `[[XIC Docs Cleanup Direction Lock]]`
- Obsidian CLI write/readback for `[[XIC Exact Referrer Review Patch 2]]`
- Obsidian CLI readback for the four patch-3 private history notes
- Obsidian CLI readback for the three patch-4 private history notes
- read-only subagent review by `docs-handoff-reviewer` and
  `strategy-challenger`
- read-only subagent review for the `docs/product/` representative-doc layer

## Residual Risk

- Optional Obsidian note titles remain in repo text. Current policy allows
  title/alias pointers, but they should remain optional and non-sensitive.
- Full PR CI and RAW-backed validation are intentionally not run for this docs
  governance phase.
- Known unrelated residual: release-slice checker still has a source-hash
  mismatch for `docs/superpowers/validation/productization_status_index_v1.tsv`.
- Commit closeout note: the handoff references
  `docs/superpowers/handoffs/archive/2026-06-25_codex-docs-cleanup_direction-lock-review.md`,
  which is currently untracked. If this patch is staged later, include that
  archive file or remove the reference before committing.

## Next Actions

1. Report acceptance status and leave the patch unstaged unless the
   user asks to stage or commit.
2. Continue future cleanup in small batches: read source note, formalize stable
   claims, update exact referrers or justify same-path stub retention, then
   update optional Obsidian metadata.
