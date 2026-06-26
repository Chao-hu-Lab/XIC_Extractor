# Docs cleanup current handoff

Branch: `codex/docs-cleanup`
Status: committed docs-governance cleanup; follow-up health fixes in progress
Validation status: `diagnostic_only`

## Current Verdict

The docs cleanup branch now has a committed repo/Obsidian split baseline:

- commit: `634d568c docs: establish repo and Obsidian document flow`;
- repo keeps formal source-of-truth docs, compact public migration evidence,
  checker-readable validation artifacts, and active handoff stubs;
- Obsidian keeps private development history, long branch diaries, review
  rationale, research drafts, and local/private context;
- ignored artifact storage keeps bulky generated validation outputs with repo
  summaries, hashes, and regeneration metadata.

This branch changes documentation governance and private-history placement only.
It does not change maturity tier, active lane, writer authority, output schema,
review/replay behavior, selected values, selected area/counting, matrix values,
or matrix authority. No productization control-plane tier update is required.

## File-Management State

The user authorized `git rm` only for two exact no-referrer manifest batches:

- original approved no-referrer batch: 254 paths;
- refreshed no-referrer batch from
  `docs/superpowers/handoffs/archive/2026-06-25_codex-docs-cleanup_git-rm-candidate-manifest.tsv`:
  106 paths.

Those 360 tracked removals were included in commit `634d568c`. No additional
path move, archive move, `git rm`, push, PR, merge, or commit is authorized by
this handoff.

## Repo Shape

Repo source-of-truth docs added or updated:

- `docs/product/*.md`: product-topic source-of-truth pages for Backfill,
  Discovery, Alignment, Presets, Productization, Evidence Spine, Quant Matrix,
  Run Provenance, Review Roundtrip, Sample Metadata/QC, Targeted Selection,
  Quantitation Context, Instrument QC/Calibration, and Peak Model Selection.
- `docs/agent/obsidian-handoff-contract.md`: repo/Obsidian/handoff contract,
  validation/lockbox boundaries, placement marker taxonomy, manifest rules, and
  same-path stub policy.
- `docs/project-layout.md`, `docs/deepresearch/README.md`,
  `docs/superpowers/README.md`, and relevant formal docs now route readers to
  durable repo owners instead of private-history paths.
- `tools/diagnostics/docs_placement_guard.py` plus `.codex/hooks/*` enforce
  staged Markdown placement for shell `git add` / `git commit` flows.
- `tools/diagnostics/docs_management_audit.py` audits post-cleanup repo/vault
  health: stale handoff wording, vault manifest drift, pending `_raw` or
  `_staging`, missing vault metadata, broken wikilinks, and local path exposure.
- Branch-level narrative and PR-body seed:
  `docs/superpowers/handoffs/archive/2026-06-26_codex-docs-cleanup_branch-closeout-summary.md`.

## Obsidian State

Private archive subtree: `XIC/`. Compiled project wiki subtree:
`projects/xic-extractor/`.

- `OBSIDIAN_VAULT_PATH` resolves to `$env:OBSIDIAN_VAULT_PATH`.
- `OBSIDIAN_SOURCES_DIR` points at the vault `_raw` inbox, not repo `docs/`.
- `_staging/` and `_raw/` are currently intended as review/intake lanes, not
  repo authority.
- Manifest source keys were previously rewritten so private-history sources
  point at vault `Source.md` copies, with original repo paths retained as
  provenance.

## Boundaries

Keep in repo:

- formal product/method docs, active handoffs, compact public migration
  indexes, machine-checkable fixtures/schemas/status indexes, authority
  manifests, inventories, hashes, retained review packets, and checker-readable
  README/JSON/TSV;
- product/user-facing HTML reading artifacts when they are useful complete
  public docs;
- `docs/superpowers/notes/backfill_broad_autowrite_feasibility_gate_v1.md`,
  because it has exact status-index/authority-manifest hash binding and is
  classified as `repo_keep_current`.

Keep in Obsidian:

- private reviewer rationale, command diaries, superseded plan narrative,
  exploratory interpretation, branch sequencing, and local/private context
  after stable public claims are repo-owned.

Externalize to ignored storage:

- generated bulk artifacts marked `externalize`, while keeping repo summaries,
  hashes, row counts, source script, and regeneration metadata.

## Latest Verification

Commit `634d568c` was created after:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests/test_docs_placement_guard.py tests/test_handoff_phase_closeout_contract.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools/diagnostics/docs_placement_guard.py tests/test_docs_placement_guard.py tests/test_handoff_phase_closeout_contract.py .codex/hooks/xic_hook_policy.py .codex/hooks/xic_pre_tool_guard.py .codex/hooks/xic_post_tool_guard.py .codex/hooks/fixtures/assert_hook_outputs.py
python .codex/hooks/fixtures/assert_hook_outputs.py
python tools/diagnostics/docs_placement_guard.py --staged
python output/codex-docs-cleanup/scan_added_lines_for_sensitive_paths.py
git diff --cached --check
```

Recorded results: focused pytest 17 passed; focused ruff passed; hook fixture
smoke passed; placement guard passed; added-line secret/local-path scan passed;
diff whitespace check passed. After commit, `git status --short --branch`
reported a clean worktree.

## Current Follow-Up

The remaining work is docs-management health hardening, not another file-removal
batch:

1. keep this handoff and the closeout summary aligned with post-commit state;
2. repair Obsidian manifest/index/frontmatter health metadata without moving
   repo authority into the vault;
3. use `tools/diagnostics/docs_management_audit.py` as the repeatable health
   check;
4. treat validation local-path exposure as a focused retention/privacy review,
   because several affected TSVs are checker-backed contracts.

Stop before any further tracked deletion, vault rebuild, PR, push, or
productization-tier change unless the user explicitly requests it.
