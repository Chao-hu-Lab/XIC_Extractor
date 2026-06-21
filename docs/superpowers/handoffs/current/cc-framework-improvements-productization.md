# XIC productization handoff

Updated: 2026-06-24
Branch: `codex/pr05-backfill-clean-target-rebuild-20260624`
Status: #88, #93, #94, and #95 are merged on `master`; #89 was closed as
superseded by #95. The remaining stack is being rebuilt one PR at a time from
the current `master` so CI and review do not depend on ignored local artifacts.

This is a compact current-state snapshot. Tier authority lives in
`docs/superpowers/plans/2026-06-15-productization-control-plane.md`,
`docs/superpowers/specs/productization_authority_manifest.v1.json`, and
`docs/superpowers/validation/productization_status_index_v1.tsv`.

## Current Objective

Rebuild and close #90-#92 without carrying old stacked output, artifact, or
global-ledger coupling:

- #90: clean-target Backfill expansion activation.
- #91: DNA-dR product-ready preset performance.
- #92: row-completion confidence shadow gate.

Each PR must have a clean base, CI-visible retained artifacts, accurate PR
description, and no required dependency on ignored `output/` or
`local_validation_artifacts/`.

## Product State

- `backfill_current_write_ready_scope` remains the existing 511-cell Backfill
  authority from #88.
- `cid_nl_default_product_activation_v1` remains the 95-cell CID-NL Discovery
  authority from #95.
- #90 introduces `backfill_expansion_default_product_activation_v1` as a
  bounded 666-cell Backfill expansion packet, not broad Backfill authority.
- Broad Backfill auto-write remains parked.
- Diagnostics, galleries, review packets, and retained summaries are evidence
  surfaces only unless a ProductWriter scope, expected diff, and authority
  manifest entry bind them.

## Boundaries

- Do not put full matrices, full opportunity maps, cell provenance dumps, or
  generated overlay bundles into git.
- Do not use ignored `output/` or `local_validation_artifacts/` as clean-checkout
  CI prerequisites.
- Do not expand CID-NL beyond 95 cells or Backfill expansion beyond 666 cells
  without a new expected-diff and authority update.
- Do not change workbook/GUI behavior, selected peak, selected area, counted
  detection, or broad Backfill authority in #90.
- Any CI red must be diagnosed from logs and stack boundary first, then fixed at
  the owner boundary.

## Required Gates

For #90 before ready/merge:

- Backfill expansion focused checkers and tests.
- `uv run python scripts/check_productization_state.py`
- `uv run python scripts/check_productization_authority.py`
- `uv run python scripts/check_validation_artifact_retention.py`
- CI-equivalent local gate:
  - `$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor tests`
  - `$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor`
  - `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -v --tb=short -x`
- GitHub CI green and review clear before normal merge.

## Status Index Anchors

Retain these anchor phrases for productization state checks:

- `product_ready_default_matrix_activated`
- `CID-NL default product activation v1`
- `Backfill Expansion Default Product Activation v1`
- Broad Backfill auto-write remains parked
- Goal 0/1 hardening added
- machine-adjudicated without granting new writer authority
- Goal 2 added Review Packet / Approval Workflow v1
- lockbox_shadow_automation_experiment_v1
- Goal 4 added Missing-Overlay Evidence Recovery v1
- keep only as explanation/triage
- Targeted MS1 shape identity limited rescue remains production-ready
- GUI and broader targets remain blocked
- `sample_metadata_v1` remains production-ready for no-output ordering
- roles/batch/matrix/exclusion must not alter quant output
- ReviewAction selected-candidate switch and manual-boundary area recompute remain parked
- manual-boundary area recompute remain parked
- classification and planning only

## Next Actions

1. Finish #90 rebuild conflict resolution on current `master`.
2. Run focused Backfill/productization/retention gates.
3. Run full local CI-equivalent gate.
4. Push or API-create a clean replacement PR if old #90 remains stacked-dirty.
5. Wait for GitHub CI and review, normal-merge if green.
6. Repeat the same boundary-first process for #91 and #92.
