# Docs cleanup branch closeout summary

Branch: `codex/docs-cleanup`
Date: 2026-06-26
Status: committed baseline plus follow-up documentation-health hardening
Validation status: `diagnostic_only`

## Purpose

This branch changes the documentation model, not product behavior. The target
shape is:

- repo keeps formal source-of-truth docs, public-safe migration indexes,
  checker-readable fixtures, and compact active handoffs;
- Obsidian keeps private development history, branch diaries, long review
  rationale, research drafts, and local/private context;
- ignored artifact storage keeps generated bulk validation outputs with repo
  summaries, hashes, row counts, and regeneration metadata.

The motivation is privacy and maintainability. A public repo should expose the
durable method, contracts, validation policy, and reviewable migration evidence;
it should not expose the full development diary, command narrative, local branch
sequencing, or private reviewer reasoning.

## What Changed

Formal repo docs were added or strengthened so removed private-history files do
not leave product knowledge behind:

- `docs/product/`: product-topic source-of-truth pages for Backfill, Discovery,
  Alignment, Presets, Productization, Evidence Spine, Quant Matrix, Run
  Provenance, Review Roundtrip, Sample Metadata/QC, Targeted Selection,
  Quantitation Context, Instrument QC/Calibration, and Peak Model Selection.
- `docs/agent/obsidian-handoff-contract.md`: public/private boundary,
  handoff/Obsidian rules, placement marker taxonomy, validation/lockbox
  handling, manifest fields, and future-doc classification rules.
- `docs/project-layout.md`, `docs/deepresearch/README.md`, and
  `docs/superpowers/README.md`: public-safe routing for long research,
  superpowers history, artifact retention, and branch cleanup.
- `tools/diagnostics/docs_placement_guard.py` and `.codex/hooks/*`: real
  commit-time guardrail for staged Markdown placement. Shell `git add` reports
  risky staged docs early, shell `git commit` blocks risky staged docs,
  auto-stage/pathspec commit forms are blocked, formal owner docs pass, and
  tracked deletions stay outside this checker.
- `tools/diagnostics/docs_management_audit.py`: repeatable read-only
  repo/vault health audit for stale post-commit wording, manifest drift,
  pending vault intake, missing wiki metadata, approximate broken links, and
  local-path exposure.

Referrer hygiene was completed before deletion:

- public prose now points to formal repo owners;
- diagnostic provenance and historical-only references use opaque
  `retired-provenance:*` identifiers instead of readable private-history paths;
- retained fixture provenance was rewritten away from exact retired note paths;
- branch-story HTML links now target formal product docs rather than retired
  private-history stubs.

Obsidian was organized as the private notebook layer:

- private archive subtree: `XIC/`;
- compiled project wiki subtree: `projects/xic-extractor/`;
- root imports were deduplicated into redirect stubs under
  `XIC/00 Inbox/Root Import Review/Merged Redirects/`;
- canonical curated notes remain in topic folders;
- promoted project wiki pages live under `projects/xic-extractor/`.

## File-Management State

The user authorized `git rm` only for two exact no-referrer manifest batches:

- original `removal_candidate_no_repo_referrers` batch: 254 paths;
- refreshed `removal_candidate_no_repo_referrers` batch from
  `docs/superpowers/handoffs/archive/2026-06-25_codex-docs-cleanup_git-rm-candidate-manifest.tsv`:
  106 paths.

Those 360 tracked removals were included in commit `634d568c docs: establish
repo and Obsidian document flow`. The 106-path batch required `git rm -f`
because those candidate stubs had local cleanup modifications, but the path set
remained exactly the manifest-scoped approved group.

No further `git rm`, archive move, push, PR, merge, or commit is authorized by
this closeout summary.

## Evidence Map

- Current-state handoff:
  `docs/superpowers/handoffs/current/codex-docs-cleanup-official-docs-and-handoff.md`
- File-management approval record:
  `docs/superpowers/handoffs/archive/2026-06-25_codex-docs-cleanup_file-management-approval-plan.md`
- Public-surface audit:
  `docs/superpowers/handoffs/archive/2026-06-25_codex-docs-cleanup_public-surface-stub-audit.md`
- Git-rm candidate manifest:
  `docs/superpowers/handoffs/archive/2026-06-25_codex-docs-cleanup_git-rm-candidate-manifest.md`
- Exact candidate TSV:
  `docs/superpowers/handoffs/archive/2026-06-25_codex-docs-cleanup_git-rm-candidate-manifest.tsv`
- Obsidian dedup audit:
  `docs/superpowers/handoffs/archive/2026-06-25_codex-docs-cleanup_obsidian-vault-dedup-audit.md`
- Source-of-truth queue:
  `docs/superpowers/handoffs/archive/2026-06-25_codex-docs-cleanup_source-of-truth-queue.md`
- Docs placement guard:
  `tools/diagnostics/docs_placement_guard.py`,
  `.codex/hooks/xic_hook_policy.py`,
  `.codex/hooks/xic_pre_tool_guard.py`,
  `.codex/hooks/xic_post_tool_guard.py`
- Docs management audit:
  `tools/diagnostics/docs_management_audit.py`
- Stub readiness and batch evidence:
  `docs/superpowers/handoffs/archive/2026-06-25_codex-docs-cleanup_phase2-stub-readiness.md`,
  `docs/superpowers/handoffs/archive/2026-06-25_codex-docs-cleanup_bulk-private-history-stub-batch.md`,
  `docs/superpowers/handoffs/archive/2026-06-25_codex-docs-cleanup_non-notes-formalized-stub-batch.md`,
  `docs/superpowers/handoffs/archive/2026-06-25_codex-docs-cleanup_remaining-notes-plans-stub-batch.md`

## Verification

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

Subagent review found blocker guardrail gaps and the smallest fixes were
applied:

- auto-stage and pathspec commit forms could bypass a staged-only checker; these
  forms are now blocked, including `--pathspec-from-file`;
- the placement guard reads staged blobs from the index so unstaged marker edits
  cannot make a bad staged doc pass;
- raw regex command detection was replaced with shell-token parsing to reduce
  false positives while preserving `git add` / `git commit` coverage;
- `docs/superpowers/handoffs/archive/` is no longer broadly canonical; only
  explicit public cleanup evidence filename patterns pass without placement
  markers;
- `docs/project-layout.md` routes active execution context to
  `repo_active_stub`, while long reasoning and branch sequencing go to Obsidian
  staged draft.

## Productization Impact

No productization control-plane tier or active-lane update is required. This
branch does not change maturity tier, active lane, writer authority, output
schema, review/replay behavior, selected values, selected area/counting, matrix
values, or matrix authority. It changes documentation governance,
public/private placement, migration evidence, and docs-health guardrails.

## Residual Risk

- The placement guard reduces obvious future mistakes but does not prove a
  marker is semantically true. Human review, referrer audit, secret/local-path
  scan, and explicit destructive approval remain required.
- Validation local-path exposure still needs a focused retention/privacy review.
  Some affected TSVs are checker-backed contracts, so they must not be
  sanitized by blind global replacement.
- Obsidian remains a private notebook. Its health metadata can improve
  retrieval, but it must not become the only source for repo behavior,
  validation policy, or next safe actions.
- No long RAW validation was run because this branch does not change
  extraction, alignment, scoring, matrix output, or product behavior.

## PR Body Seed

Problem:

The repository had accumulated private development diaries, superseded plans,
review rationale, and branch-local research history as versioned docs. That made
the public repo look transparent while mixing durable product knowledge with
private process history.

Solution:

This branch separates durable public docs from private history. It adds formal
source-of-truth docs under `docs/product/`, defines the repo/Obsidian/handoff
boundary and placement marker taxonomy, adds a real staged-doc placement guard
for shell `git add` / `git commit`, blocks auto-stage/pathspec commit bypasses,
organizes Obsidian as the private notebook layer, rewrites public referrers to
formal owners or opaque retired-provenance IDs, includes the two explicitly
approved no-referrer private-history cleanup batches in commit `634d568c`, and
adds a read-only docs-management audit for future health checks.

Verification:

Focused docs/contract tests passed, focused docs-placement tests passed, focused
ruff passed, hook fixture smoke passed, subagent blocker fixes were applied,
added-line secret/local-path scan passed, and diff whitespace checks passed. The
refreshed public-surface audit found 0 public, diagnostic-provenance, or
historical blockers before the second approved deletion batch.

Residual risk:

This is docs governance cleanup, not product behavior validation. Review should
focus on whether durable source-of-truth docs and migration evidence are
sufficient, whether the approved 360 removals preserve public claims, and
whether validation local-path exposure should be handled in a later focused
retention/privacy cleanup.
