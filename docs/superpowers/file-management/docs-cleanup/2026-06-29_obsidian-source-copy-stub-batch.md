# Obsidian Source-Copy / Stub Batch 1

Doc placement: repo_support_doc
Doc kind: manifest
Doc lifecycle: active
Repo owner: docs/agent/obsidian-handoff-contract.md
Doc exit rule: Retire after every listed source is promoted, rejected, or
explicitly deferred through the wiki staged-write flow, any repo body is reduced
to a compact self-sufficient stub, and a fresh docs audit/referrer scan is clean.

Status: `batch_complete`
Validation status: `diagnostic_only`

This batch opens the next docs-cleanup phase after support-retention
classification. It is intentionally small: only sources whose stable public
claims were already absorbed into repo owners are eligible. The batch does not
authorize `git rm`, archive moves, or direct writes into final Obsidian pages.

## Boundary

Use the staged wiki workflow:

1. Query the vault for `source_repo_path:<repo path>` before writing.
2. Create or update staged source-copy notes through `wiki-ingest` /
   `wiki-update`, preserving manifest/index/log/hot bookkeeping.
3. Read back staged notes before changing repo bodies.
4. Convert repo sources to compact same-path stubs only after the source copy
   exists or the source is explicitly rejected.
5. Rerun docs audit and exact referrer scan before proposing any tracked-file
   removal.

Do not include Backfill/Quant authority-bound support in this batch. That topic
currently has 88 `authority_or_status_anchor` rows and 2
`active_support_surface` rows; those belong to validation retention,
productization-status checks, or declared exit rules, not this source-copy stub
batch.

## Source List

| Source path | Topic | Repo owner now carrying stable claim | Vault lane hint | Repo action after staged readback |
| --- | --- | --- | --- | --- |
| `docs/superpowers/notes/2026-06-04-targeted-expected-diff-bc1055-closeout.md` | Targeted selection | `docs/product/targeted-selection.md` | `XIC/20 Archived Plans And Specs/Topic Archives/Targeted Selection/` | Replace long closeout with compact same-path support stub retaining row-specific verdict, runtime candidate-ID rule, count impact, and `source_repo_path` lookup key. |
| `docs/superpowers/productization/evidence/2026-06-22_cc-framework-improvements_dna-dr-performance-pass.md` | Presets / performance | `docs/product/presets.md` | `XIC/20 Archived Plans And Specs/Topic Archives/Presets/` | Replace long archive with compact same-path support stub retaining timing headline, exact-output-preserving lesson, and product non-change. |
| `docs/superpowers/fixtures/diagnostic_ledger_2026_05_28/targeted_gt_alignment_audit_default_5medc_current_8raw_failure_mode_report.md` | Alignment | `docs/product/alignment.md` | `XIC/20 Archived Plans And Specs/Topic Archives/Alignment Evidence/` | Replace report body with compact fixture stub retaining `5-medC`, 8RAW validation-minimal slice, `PASS 8/8`, and non-authority warning. |
| `docs/superpowers/fixtures/diagnostic_ledger_2026_05_28/targeted_gt_alignment_audit_default_5medc_primary_delivery_fix_failure_mode_report.md` | Alignment | `docs/product/alignment.md` | `XIC/20 Archived Plans And Specs/Topic Archives/Alignment Evidence/` | Replace report body with compact fixture stub retaining `5-medC`, primary-delivery-fix slice, `PASS 8/8`, and non-authority warning. |

## Completion

Completed on 2026-06-29.

- All four source paths were copied into Obsidian through staged writes, read
  back, promoted to live vault paths, and registered in the vault manifest.
- The same four repo files were reduced to compact same-path stubs that retain
  the stable claim, repo owner, validation status, and `source_repo_path` lookup
  key.
- No tracked file was removed or archive-moved in this source-copy batch.
- No productization control-plane update is needed: this work did not change a
  maturity tier, active lane, output schema, review/replay behavior, selected
  area/counting, matrix authority, or runtime behavior.

Post-approval deletion applied on 2026-06-30:

- The four first-batch repo stubs listed above were removed after explicit user
  approval in
  `docs/superpowers/file-management/docs-cleanup/2026-06-30_source-copy-stub-removal-approval-packet.md`.
- Their Obsidian source copies remain the private original-history surface.
- Do not recreate same-path stubs for these four files unless a future exact
  referrer or compatibility gate explicitly requires it.

Live Obsidian source notes:

- `XIC Targeted Expected-Diff BC1055 Closeout Source`
- `XIC DNA DR Product Ready Performance Pass Source`
- `XIC Targeted GT Alignment 5-medC Current 8RAW Source`
- `XIC Targeted GT Alignment 5-medC Primary Delivery Fix Source`
- `XIC Docs Cleanup Branch Closeout Source`
- `XIC Docs Cleanup Source-Of-Truth Queue Source`

Verification:

- Docs management audit: blockers `[]`, messages `[]`, Vault staging `0`,
  broken wikilinks `0`.
- Focused docs tests: `67 passed`.
- Ruff docs/tools slice: passed.
- Diagnostics index check: passed.

## Explicit Deferrals

- `docs/superpowers/plans/2026-06-28-family-abstraction-removal.md` is already a
  compact same-path stub with a live Obsidian source note. It should not be
  reprocessed as a new source-copy batch.
- `docs/superpowers/notes/2026-06-02-selected-hypothesis-model-selection-characterization-map.md`
  was removed in the 2026-06-30 approved deletion batch after its durable rules
  were formalized in `docs/product/peak-model-selection.md`.
- Docs-workflow closeout and source-of-truth queue historical stubs were removed
  in the 2026-06-30 approved deletion batch after source-copy handling. Do not
  recreate them unless their formal owner docs need a new source-of-truth
  correction.

## Stop Rule

Stop before stubbing if any source has exact repo referrers, status/authority
anchors, missing source-copy readback, broken wiki frontmatter, or a product
owner gap. A compact stub must explain the retained public meaning without
requiring private Obsidian access.
