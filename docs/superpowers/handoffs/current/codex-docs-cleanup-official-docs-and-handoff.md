# Docs cleanup current handoff

Branch: `codex/docs-cleanup`
Status: PR gate passed; ready for local closeout commit, push, and PR creation
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

Current uncommitted closeout delta:

- Handoff and branch closeout summary were pruned into the branch-current resume
  surface plus PR-body seed.
- PR gate exposed stale retained-validation JSON path/hash bindings; those were
  normalized to repo-relative forward-slash JSON paths and synchronized through
  the validation inventory, productization status index, bounded lane acceptance
  packet, authority manifest, and lockbox summaries.
- Two ruff-only test formatting issues were fixed without changing test intent.

## Routing State

Use this split when preparing the PR or continuing the branch:

| Content | Current destination | Reason |
| --- | --- | --- |
| Next safe actions and branch status | This current handoff | Self-sufficient resume stub. |
| PR body seed and reviewer narrative | `docs/superpowers/handoffs/archive/2026-06-26_codex-docs-cleanup_branch-closeout-summary.md` | Completed phase summary that can be condensed into a PR. |
| Exact deletion authorization, manifests, public-surface audits | Existing `docs/superpowers/handoffs/archive/2026-06-25_codex-docs-cleanup_*` evidence files | Public-safe audit trail for file-management decisions. |
| Long development diary, reviewer rationale, branch sequencing, private context | Obsidian private notes | Not repo authority and not PR body material. |
| Full generated validation TSVs not needed for clean checkout | `local_validation_artifacts/externalized_superpowers_validation/` | Ignored local storage; repo keeps summaries, manifests, hashes, and contract fixtures. |

Do not add another handoff system. The branch-scoped current handoff remains the
resume surface; the archive closeout summary is the PR body source.

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

Stop before any further `git rm`, vault rebuild, push, PR creation, merge, or
productization-tier change unless the user explicitly requests it.

## Latest Verification

Latest validation in this worktree:

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

## Next Actions

1. Stage only this closeout delta and run staged guard checks.
2. Commit the closeout patch.
3. Push `codex/docs-cleanup` and open the PR as workflow-only /
   diagnostic-only documentation governance cleanup; preserve branch history and
   local ignored artifacts until merge closeout is complete.
