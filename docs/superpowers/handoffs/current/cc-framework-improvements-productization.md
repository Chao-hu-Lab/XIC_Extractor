# XIC productization handoff

Updated: 2026-06-18
Branch: `cc/framework-improvements`
Latest committed checkpoint: `c000d59a Add lockbox next-action gate`
Active checkpoint: `lockbox_second_review_pack_v1` is implemented,
subagent-reviewed, fully locally verified, and ready to commit.

This is the current-state snapshot only. The tier authority is
`docs/superpowers/plans/2026-06-15-productization-control-plane.md` plus the
machine-readable status indexes.

## Current Objective

Continue the low-manual productization path by making every candidate reviewable
and auditable, without turning labels, diagnostics, quality blockers, ISTD, or
round-trip oracle evidence into ProductWriter authority.

Current focus: finish and verify the second independent review collection pack
for the 53 plotted Gaussian15 lockbox cases. This is truth acquisition only; it
does not change matrix, workbook, selected peak, selected area, counted
detection, default extraction, GUI, or broad Backfill.

## What Changed This Round

- Added `scripts/build_lockbox_second_review_pack.py`.
- Added `tests/test_lockbox_second_review_pack.py`.
- Generated:
  - `docs/superpowers/validation/lockbox_second_review_queue_v1.tsv`
  - `docs/superpowers/validation/lockbox_second_review_template_v1.tsv`
  - `docs/superpowers/validation/lockbox_second_review_summary_v1.json`
  - `docs/superpowers/validation/lockbox_second_review_v1/index.html`
- Updated `productization_status_index_v1.tsv` so
  `peak_choice_truth_lockbox_v1` now points to the second-review summary.
- Updated `bounded_non_broad_lane_acceptance_v1.tsv` only to refresh the source
  status-index hash.
- Updated `lockbox_label_readme_v1.md` and the control-plane maintenance log.

## Current Lane State

- `backfill_current_write_ready_scope`: `production_ready`, exactly 511
  generated-policy `write_ready` cells. This is still the only current Backfill
  writer authority.
- `broad_backfill_autowrite`: `parked`. The 4613 rows are a candidate/audit
  universe, not writable cells.
- `peak_choice_truth_lockbox_v1`: `production_candidate`.
  Current artifact is
  `docs/superpowers/validation/lockbox_second_review_summary_v1.json`.
  It says 53 cases are ready for reviewer slot 2, 19 non-ready cases stay out
  of this collection pack, labels are blank, and no product authority is
  granted.
- `review_packet_workflow_v1`: `production_candidate`, structured review only.
  Review approval is not ProductWriter approval.
- `missing_overlay_evidence_recovery_v1`: `production_candidate`, evidence link
  recovery only; recovered evidence is not writer authority.
- `productization_authority_firewall_v1`,
  `mechanical_adjudication_contract_v1`, `productization_status_index_v1`, and
  `bounded_non_broad_lane_acceptance_v1`: `production_candidate` guardrails.
- `targeted_ms1_shape_identity_limited_rescue_v1`: `production_ready` only for
  the explicit headless 5-hmdC + 5-medC limited workflow writing
  `detected_flagged`; broader targets remain blocked.
- `sample_metadata_order_projection_v1`: `production_ready` for no-output
  ordering/projection only.
- `review_action_candidate_sidecar_v1`: `production_candidate` for identity
  verification only.
- ReviewAction selected-candidate switch, manual-boundary area writer,
  SampleMetadata output-affecting role/value behavior, broader targeted MS1
  rescue, calibration/normalization writeback, and GUI replay remain parked,
  blocked, frozen, or out of scope.

## Machine-Check Anchors

- Current Backfill product authority remains exactly 511.
- Broad Backfill auto-write remains parked.
- Goal 0/1 hardening added.
- Goal 2 added Review Packet / Approval Workflow v1.
- Goal 4 added Missing-Overlay Evidence Recovery v1.
- `sample_metadata_v1` remains production-ready for no-output ordering.
- keep only as explanation/triage.
- Targeted MS1 shape identity limited rescue remains production-ready.
- GUI and broader targets remain blocked.
- roles/batch/matrix/exclusion must not alter quant output.
- ReviewAction selected-candidate switch and manual-boundary area recompute remain parked.
- manual-boundary area recompute remain parked.
- classification and planning only.

## Second-Review Pack Contract

- Inputs: `lockbox_next_action_plan_v1.tsv`,
  `lockbox_static_review_v1/bundle_index.tsv`, and
  `lockbox_reviewer_label_log_v1.tsv`.
- Included rows: exactly the 53
  `ready_for_second_independent_review` cases.
- Excluded rows: 6 manual negative controls, 12 round-trip-oracle negatives,
  and 1 Gaussian boundary-unavailable case.
- Reviewer surface: existing Gaussian15 static review HTML/PNG links; no plots
  are regenerated.
- Template semantics: one blank `reviewer_slot=2` row per case. No labels are
  prefilled or invented.
- Boundary basis: the existing Gaussian15-smoothed review boundary shown in the
  static review bundle.
- Authority: all ProductWriter/matrix/workbook/selected peak/selected
  area/counted detection/broad Backfill flags remain false.

## Validation So Far

Passed:

- `$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/build_lockbox_second_review_pack.py`
- `$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/build_lockbox_second_review_pack.py --check-only`
- `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_lockbox_second_review_pack.py -v --tb=short`
  (`11 passed`)
- `$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check scripts/build_lockbox_second_review_pack.py tests/test_lockbox_second_review_pack.py`
- `$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/check_productization_state.py`
- `$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/check_bounded_product_lanes.py`
- `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_productization_state_index.py tests/test_lockbox_second_review_pack.py -v --tb=short`
  (`21 passed`)
- Full gate: `ruff check xic_extractor tests scripts/build_lockbox_second_review_pack.py`,
  `mypy xic_extractor`, `pytest -v --tb=short -x` (`3884 passed, 1 skipped`),
  diagnostics index, productization authority, productization state, bounded
  lanes, and second-review `--check-only`.
- Subagent review found and we fixed: actual linked PNG hash anchoring, plus
  the broken HTML template link. Post-fix re-review found no P0/P1/P2/P3
  findings.

## Rejected Paths

- Do not unpark broad Backfill or derive new write rules from the 19 excluded
  cases.
- Do not treat ISTD or round-trip oracle results as analyte peak-choice or area
  truth.
- Do not prefill reviewer-slot-2 labels.
- Do not let completed labels feed ProductWriter without a later explicit
  authority manifest, expected-diff, and product goal.
- Do not run 85RAW for this checkpoint; the decision is entirely artifact and
  review-surface based.

## Next Actions

1. Commit the second-review pack checkpoint.
2. Later: have a second independent reviewer fill
   `docs/superpowers/validation/lockbox_second_review_template_v1.tsv`, then
   import those labels and rerun the truth summary gate.
