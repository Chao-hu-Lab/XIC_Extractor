# Docs cleanup current handoff

Branch: `codex/docs-cleanup`
Status: repo/Obsidian split mostly complete; two approved no-referrer deletion
batches are staged; no commit has been made.
Validation status: `diagnostic_only`

## Current Verdict

The branch changes documentation governance and private-history placement only.
It does not change maturity tier, active lane, writer authority, output schema,
review/replay behavior, selected values, selected area/counting, matrix values,
or matrix authority. No productization tier/lane update is required.

The user authorized `git rm` for exactly two manifest-scoped no-referrer
batches:

- Original approved batch: 254 paths, staged for removal.
- Refreshed `removal_candidate_no_repo_referrers` batch:
  `docs/superpowers/handoffs/archive/2026-06-25_codex-docs-cleanup_git-rm-candidate-manifest.tsv`,
  106 paths, staged for removal with `git rm -f` because the candidate stubs had
  local cleanup modifications.

Total staged deletions are now 360. No further path move, deletion, `git rm`,
push, PR, merge, or commit is authorized.

## Repo Shape

Repo source-of-truth docs added or updated:

- `docs/product/*.md`: Backfill, Discovery, Alignment, Presets,
  Productization, Evidence Spine, Quant Matrix, Run Provenance, Review
  Roundtrip, Sample Metadata/QC, Targeted Selection, Quantitation Context,
  Instrument QC/Calibration, and Peak Model Selection.
- `docs/agent/obsidian-handoff-contract.md`: repo/Obsidian/handoff contract,
  validation/lockbox boundaries, placement marker taxonomy, manifest rules, and
  same-path stub policy.
- `docs/project-layout.md`, `docs/deepresearch/README.md`,
  `docs/superpowers/README.md`, and relevant formal docs now route readers to
  durable repo owners instead of private-history paths.
- `tools/diagnostics/docs_placement_guard.py` plus `.codex/hooks/*` now enforce
  staged Markdown placement: shell `git add` reports risky docs early, shell
  `git commit` blocks risky staged docs, `git commit -a/--all/-am` and pathspec
  commits are blocked, and deletions remain governed by manifest/referrer/
  explicit approval.
- Cleanup manifests, source-of-truth queues, vault audits, and public-surface
  reports live under
  `docs/superpowers/handoffs/archive/*docs-cleanup*`.
- Branch-level narrative and PR-body seed:
  `docs/superpowers/handoffs/archive/2026-06-26_codex-docs-cleanup_branch-closeout-summary.md`.

Public referrer hygiene is clean for the approved deletion set:

- Public prose docs now point to formal owners.
- `tools/diagnostics/INDEX.md`, historical plans/specs, fixture provenance, and
  branch-story HTML use formal owner links or opaque `retired-provenance:*`
  identifiers instead of readable private-history paths.
- Pre-removal audit reported 0 public blockers, 0 diagnostic-provenance blockers,
  and 0 historical-referrer blockers for the refreshed 106-path batch.

## Obsidian State

Private archive subtree: `XIC/`. Compiled project wiki subtree:
`projects/xic-extractor/`.

- Raw root-import duplicates were converted to redirect stubs under
  `XIC/00 Inbox/Root Import Review/Merged Redirects/`.
- Canonical curated notes remain in topic folders.
- Promoted project wiki pages live under `projects/xic-extractor/`.
- `OBSIDIAN_SOURCES_DIR` now points at the vault raw inbox, not repo `docs/`, so
  formal public docs are not treated as automatic private-wiki ingest backlog.
- Vault manifest hygiene: 97/97 source keys exist; 96 private-history sources
  now point at vault `Source.md` copies, with original repo paths retained as
  provenance. Backup:
  `_archives/manifest-backups/manifest-before-source-key-rewrite-2026-06-26T033500Z.json`.
- Vault health after cleanup: broken redirect stubs 0, redirect chains 0,
  broken wikilinks in non-stub XIC notes 0, duplicate source groups outside Root
  Import Review 0, effective-body duplicates outside Root Import Review 0.
- QMD refresh was skipped because `QMD_WIKI_COLLECTION` is unset.

Vault audit:
`docs/superpowers/handoffs/archive/2026-06-25_codex-docs-cleanup_obsidian-vault-dedup-audit.md`.

## Boundaries

Keep in repo:

- Formal product/method docs, compact public migration indexes, active handoffs,
  machine-checkable fixtures/schemas/status indexes, authority manifests,
  inventories, hashes, retained review packets, and checker-readable README/JSON/TSV.
- Product/user-facing HTML reading artifacts when they are useful complete
  public docs.
- `docs/superpowers/notes/backfill_broad_autowrite_feasibility_gate_v1.md`,
  because it has exact status-index/authority-manifest hash binding and is
  classified as `repo_keep_current`.

Keep in Obsidian:

- Private reviewer rationale, command diaries, superseded plan narrative,
  exploratory interpretation, branch sequencing, and local/private context after
  stable public claims are repo-owned.

Externalize to ignored storage:

- Generated bulk artifacts marked `externalize`, while keeping repo summaries,
  hashes, row counts, source script, and regeneration metadata.

## Latest Verification

Already run before the 106-path `git rm`:

```powershell
python .codex\hooks\fixtures\assert_hook_outputs.py
python output/codex-docs-cleanup/public_surface_stub_audit.py
python output/codex-docs-cleanup/inspect_historical_candidate_referrers.py
python -m py_compile output/codex-docs-cleanup/*.py
python output/codex-docs-cleanup/scan_added_lines_for_sensitive_paths.py
$env:UV_CACHE_DIR=".uv-cache"; uv run pytest -q tests/test_handoff_phase_closeout_contract.py tests/alignment/identity_coherence/test_schema_contract.py
git diff --check
```

Results: focused tests 83 passed; hook fixture smoke passed; helper scripts
compiled; added-line secret/local-path scan passed; `git diff --check` passed
with only LF/CRLF warnings.

After the authorized 106-path `git rm`:

- Manifest count: 106.
- Authorized paths staged as deleted: 106.
- Authorized paths still on disk: 0.
- Total staged deletions: 360.
- `git diff --check` still exits 0 with LF/CRLF warnings only.

After the placement-guard implementation:

```powershell
$env:UV_CACHE_DIR=".uv-cache"; uv run pytest -q tests/test_docs_placement_guard.py tests/test_handoff_phase_closeout_contract.py
$env:UV_CACHE_DIR=".uv-cache"; uv run ruff check tools/diagnostics/docs_placement_guard.py tests/test_docs_placement_guard.py tests/test_handoff_phase_closeout_contract.py .codex/hooks/xic_hook_policy.py .codex/hooks/xic_pre_tool_guard.py .codex/hooks/xic_post_tool_guard.py .codex/hooks/fixtures/assert_hook_outputs.py
python .codex/hooks/fixtures/assert_hook_outputs.py
python tools/diagnostics/docs_placement_guard.py --staged
python output/codex-docs-cleanup/scan_added_lines_for_sensitive_paths.py
git diff --check
```

Results: focused pytest 16 passed; focused ruff passed; hook fixture smoke
passed; placement guard passed and ignored the 360 staged deletions;
added-line secret/local-path scan passed; `git diff --check` passed with
LF/CRLF warnings only. `python -m py_compile` hit a Windows pycache write ACL,
so the same hook/checker files were syntax-checked with Python `compile()`
without writing `.pyc`; syntax compile passed.

Subagent review found blocker guardrail gaps and the smallest fixes were
applied:

- `git commit -a/--all/-am` and `git commit <pathspec>` could bypass a
  staged-only checker; these forms are now blocked, including
  `--pathspec-from-file`.
- The placement guard previously read the working tree after discovering staged
  paths; it now reads the staged blob from the index so unstaged marker edits
  cannot make a bad staged doc pass.
- Raw regex command detection could false-positive on text searches and quoted
  commit messages; commit/add detection now uses shell-token parsing and
  preserves the `git add` / `git commit` guard intent.
- `docs/superpowers/handoffs/archive/` was too broadly canonical; only explicit
  public cleanup evidence filename patterns pass without placement markers.
- `docs/project-layout.md` no longer tells agents to create dated
  implementation plans under `docs/superpowers/plans/`; active execution context
  routes to a `repo_active_stub`, while long reasoning and branch sequencing go
  to Obsidian staged draft.

## Next Actions

1. Do not run additional `git rm` without a new exact user-approved path set.
2. Before commit review, re-run hook fixture smoke, docs placement guard,
   secret/local-path scan, focused tests, and `git diff --check`.
3. If desired for final audit artifacts, re-run the public-surface audit after
   the staged deletions; note that this may refresh the pre-removal manifest.
4. Review staged diff for accidental public-surface loss before any commit.
