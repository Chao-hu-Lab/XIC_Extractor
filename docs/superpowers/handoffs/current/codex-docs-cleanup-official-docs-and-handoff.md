# Docs cleanup current handoff

Branch: `codex/docs-cleanup`
Status: PR opened; follow-up handoff-retention guardrail patch in progress
Validation status: `diagnostic_only`

## Current Verdict

This branch is a documentation governance and artifact-retention cleanup. It
does not change extraction, alignment, scoring, selected values, selected
area/counting, workbook output, matrix values, matrix authority, maturity tier,
or active productization lane. No productization control-plane tier update is
required.

The branch now has these committed groups:

- `b89850ed`, `3c4c460b`, `55741b48`, `e2bdcbe0`: formalize the public/private
  docs boundary and correct productization-impact wording.
- `634d568c`: establish the repo/Obsidian document flow and remove the two
  explicitly approved no-referrer private-history batches.
- `a1e43819`: harden docs-management health checks.
- `ead777bf`, `4ebf3c2d`, `1ea1c69a`: review, externalize, and finalize
  validation shrink candidates; current retention checker reports
  `249 retained`, `48 externalized`, and `0 shrink_later`.
- `20d90316`: finalize cleanup PR handoff, validation metadata hash/path
  normalization, and PR-ready closeout state.

Current uncommitted follow-up delta:

- `docs/superpowers/handoffs/RETENTION.tsv` now records retention decisions for
  current/archive handoff files.
- `tools/diagnostics/handoff_retention_audit.py` adds a read-only audit for
  missing retention rows, invalid decisions, oversized current handoffs, stale
  current wording, and post-PR cleanup/Obsidian-transfer candidates.
- `tools/diagnostics/docs_management_audit.py` now includes handoff retention in
  the overall docs-management health check.
- `.codex/hooks/xic_hook_policy.py` now recognizes POSIX shell combined
  command flags such as `bash -lc 'git commit -am docs'`, closing the PR review
  comment about autostage commit guard bypass.
- This is docs governance only. It does not change maturity tier, active lane,
  ProductWriter authority, matrix/workbook schema, selected area/counting, or
  product outputs; no productization control-plane update is needed.

## Routing State

Use this split when preparing the PR or continuing the branch:

| Content | Current destination | Reason |
| --- | --- | --- |
| Next safe actions and branch status | This current handoff | Self-sufficient resume stub. |
| PR body seed and reviewer narrative | `docs/superpowers/handoffs/archive/2026-06-26_codex-docs-cleanup_branch-closeout-summary.md` | Completed phase summary that can be condensed into a PR. |
| Exact deletion authorization, manifests, public-surface audits | Existing `docs/superpowers/handoffs/archive/2026-06-25_codex-docs-cleanup_*` evidence files | Public-safe audit trail for file-management decisions. |
| Handoff cleanup/transfer queue | `docs/superpowers/handoffs/RETENTION.tsv` | Read-only retention inventory; not deletion approval. |
| Long development diary, reviewer rationale, branch sequencing, private context | Obsidian private notes | Not repo authority and not PR body material. |
| Full generated validation TSVs not needed for clean checkout | `local_validation_artifacts/externalized_superpowers_validation/` | Ignored local storage; repo keeps summaries, manifests, hashes, and contract fixtures. |

Do not add another handoff system. The branch-scoped current handoff remains the
resume surface; the archive closeout summary is the PR body source; the
retention inventory is the cleanup queue.

## File-Management State

Tracked removals were performed only after exact user authorization:

- `634d568c`: 360 private-history paths from approved no-referrer manifests.
- `1ea1c69a`: two validation full TSVs externalized after exact-path approval:
  - `docs/superpowers/validation/quant_matrix_promotion_validation_packet_v2/artifacts/downstream_impact_inputs/quant_matrix.tsv`
  - `docs/superpowers/validation/quant_matrix_real_bundle_v1/source_artifacts/activation_value_delta.tsv`

The remaining reviewed source artifacts are not deletion candidates:

- `seed_guard_decisions.tsv` and `standard_peak_activation_values.tsv` are
  retained as `keep_contract` because retained contract artifacts reference
  their repo paths as provenance.
- `cell_provenance.tsv` and `standard_peak_activation_inputs.tsv` remain
  `keep_minimal_fixture`.

Stop before any further `git rm`, vault rebuild, push, PR update, merge, or
productization-tier change unless the user explicitly requests it.

## Latest Verification

Latest full PR validation before opening PR #98:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor tests
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -v --tb=short -x
python -m scripts.check_validation_artifact_retention --require-externalized-local
python -m scripts.check_productization_state
python -m scripts.check_productization_authority
python -m scripts.check_bounded_product_lanes
python tools/diagnostics/docs_management_audit.py
```

Observed results: ruff passed; mypy reported `Success: no issues found in 359
source files`; full pytest reported `4441 passed, 2 skipped`; retention checker
reported `249 retained`, `48 externalized`, `0 shrink_later`; productization
state, authority, and bounded-lane checkers passed; docs audit reported
`0 blockers` and `0 warnings`.

Follow-up handoff-retention patch still needs focused tests and docs audit
rerun before commit.

## Next Actions

1. Run focused tests for docs management and handoff retention.
2. Run `python tools/diagnostics/handoff_retention_audit.py` and
   `python tools/diagnostics/docs_management_audit.py`.
3. Stage only the handoff-retention follow-up patch, run staged guard checks,
   then commit/push as a PR #98 update when requested.
