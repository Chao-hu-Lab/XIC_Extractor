# XIC productization handoff

Updated: 2026-06-24
Branch: `codex/pr05-backfill-clean-target-rebuild-20260624`
Status: #88, #93, #94, and #95 are merged on `master`; #89 was closed as
superseded by #95, and the stale stacked #90 was closed as superseded by #96.
The remaining stack is being rebuilt one PR at a time from the current
`master` so CI and review do not depend on ignored local artifacts.
#96 is the active replacement PR. Its local clean-checkout portability fix has
passed focused Backfill tests, productization/retention gates, and the full
local CI-equivalent gate. A GitHub CI failure on the previously published #96
head was traced to the same clean-checkout artifact boundary in the selective
activation validator; the local fix now covers the provenance, default
activation, and clean-target selective activation validators. The next step is
to publish the amended branch and wait for GitHub CI/review before normal
merge. A follow-up CI failure exposed a local-output-polluted hash-binding test;
the test now points at retained clean-checkout artifacts before forcing a bad
hash. A later CI failure exposed the same `cells_tsv` output coupling in full
evidence-chain style validators; the shared helper now covers declared
externalized cells artifacts for full evidence chain, peak-mode decomposition,
selective shift-aware gate, and clean-target replay while retained cells still
fail closed.

This is a compact current-state snapshot. Tier authority lives in
`docs/superpowers/plans/2026-06-15-productization-control-plane.md`,
`docs/superpowers/specs/productization_authority_manifest.v1.json`, and
`docs/superpowers/validation/productization_status_index_v1.tsv`.

## Current Objective

Rebuild and close #96, then #91-#92, without carrying old stacked output,
artifact, or global-ledger coupling:

- #96: clean-target Backfill expansion activation replacement for old #90.
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
- #96 introduces `backfill_expansion_default_product_activation_v1` as a
  bounded 666-cell Backfill expansion packet, not broad Backfill authority.
- Backfill Expansion Clean-Target Selective Default Activation v1 is the #96
  writer scope for the 84-cell clean-target subset.
- Broad Backfill auto-write remains parked.
- Diagnostics, galleries, review packets, and retained summaries are evidence
  surfaces only unless a ProductWriter scope, expected diff, and authority
  manifest entry bind them.

## Boundaries

- Do not put full matrices, full opportunity maps, cell provenance dumps, or
  generated overlay bundles into git.
- Do not use ignored `output/` or `local_validation_artifacts/` as clean-checkout
  CI prerequisites.
- Missing externalized artifacts may be absent only when the retained summary
  declares that exact artifact as externalized; retained artifacts must still
  fail closed.
- Do not expand CID-NL beyond 95 cells or Backfill expansion beyond 666 cells
  without a new expected-diff and authority update.
- Do not change workbook/GUI behavior, selected peak, selected area, counted
  detection, or broad Backfill authority in #96.
- Any CI red must be diagnosed from logs and stack boundary first, then fixed at
  the owner boundary.

## Required Gates

For #96 before ready/merge:

- Backfill expansion focused checkers and tests: passed locally
  (`134 passed`).
- `uv run python scripts/check_productization_state.py`: passed locally.
- `uv run python scripts/check_productization_authority.py`: passed locally.
- `uv run python scripts/check_validation_artifact_retention.py`: passed
  locally with the existing 6 `shrink_later` warnings.
- `uv run python scripts/check_cid_nl_discovery_release_slice.py`: passed
  locally.
- CI-equivalent local gate:
  - `$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor tests`:
    passed.
  - `$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor`: passed.
  - `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -v --tb=short -x`: passed
    (`4294 passed, 1 skipped`).
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

1. Amend the local #96 commit with the clean-checkout artifact portability fix.
2. API-update the #96 branch and refresh the PR description if verification
   wording changed.
3. Wait for GitHub CI and review, normal-merge #96 only if green/clear.
4. Rebuild or retarget #91 from updated `master`; do not reuse the stale stacked
   base blindly.
5. Repeat the same boundary-first process for #92 after #91 is clean.
