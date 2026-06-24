# XIC productization handoff

Updated: 2026-06-24
Branch: `codex/pr07-row-completion-confidence-rebuild-20260624`
Status: #88, #93, #94, #95, #96, and #91 are merged on `master`;
#89 was closed as superseded by #95; #90 was closed as superseded by #96.
#92 is the active remaining stack PR and has been rebuilt from current
`master` so it no longer depends on the old stacked base or ignored local
artifacts.

This is a compact current-state snapshot. Durable tier authority lives in
`docs/superpowers/plans/2026-06-15-productization-control-plane.md`,
`docs/superpowers/specs/productization_authority_manifest.v1.json`, and
`docs/superpowers/validation/productization_status_index_v1.tsv`.

## Current Objective

Close #92 as an independently reviewable row-completion confidence shadow gate:

- base it on current `master`;
- keep only row-completion diagnostic code, tests, specs, and retained fixtures;
- exclude stale stack commits and broad output/artifact/global-ledger refreshes;
- retarget the PR to `master`;
- merge only after CI is green and review is clear.

## Product State

- The default product tier remains `product_ready_default_matrix_activated`.
- `backfill_current_write_ready_scope` remains the existing 511-cell Backfill
  authority from #88.
- `cid_nl_default_product_activation_v1` remains the 95-cell CID-NL Discovery
  authority from #95.
- `backfill_expansion_clean_target_selective_product_activation_v1` remains the
  bounded 84-cell Backfill expansion authority from #96.
- Broad Backfill auto-write remains parked.
- #92 adds row-completion confidence product-gate mode as a non-mutating
  `shadow_ready` gate only. It does not change matrix values, workbook/GUI
  behavior, selected peak, selected area, counted detection, ProductWriter
  authority, Backfill authority, active lane, default preset behavior, or
  persisted identifiers.

## Boundary Decisions

- Do not bring back the stale stacked #91/#92 history.
- Do not merge the old `tests: refresh productization gate artifacts` commit as
  a broad artifact refresh.
- Keep only the two row-completion canonical panel inventory rows and the
  matching retention-count test update required for a clean checkout.
- Keep `.superpowers/sdd` task reports out of #92; they are execution notes, not
  retained validation fixtures or product artifacts.
- Do not expand CID-NL beyond 95 cells without a new expected-diff and
  authority update.
- Any CI red must be diagnosed from logs and stack boundary first, then fixed at
  the owner boundary.

## Validation Status

Local validation on the rebuilt #92 branch:

- Row-completion focused suite: 52 passed.
- Productization state checker: passed.
- Productization authority checker: passed.
- Validation artifact retention checker: passed with the existing 6
  `shrink_later` warnings.
- Diagnostics index checker: passed.
- Hook fixture smoke: passed.
- `uv run ruff check xic_extractor tests`: passed.
- `uv run mypy xic_extractor`: passed with existing untyped-function notes.
- `uv run pytest -v --tb=short -x`: 4418 passed, 1 skipped.

## Status Index Anchors

Retain these anchor phrases for productization state checks:

- `product_ready_default_matrix_activated`
- `CID-NL default product activation v1`
- `Backfill Expansion Default Product Activation v1`
- `Backfill Expansion Full Evidence Chain v1`
- `Backfill Expansion Clean-Target Selective Default Activation v1`
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

1. Run subagent review on rebuilt #92.
2. Fix any grounded findings and rerun the relevant gates.
3. Publish the rebuilt #92 branch, retarget #92 to `master`, and update the PR
   body with actual scope, verification, and residual risk.
4. Wait for GitHub CI. If CI is red, diagnose logs and fix the root boundary
   issue before committing.
5. Normal-merge #92 only after CI is green and review is clear, then sync local
   `master` and audit #88-#92 completion.
