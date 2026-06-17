# XIC productization handoff

Updated: 2026-06-18
Branch: `cc/framework-improvements`
Baseline before this six-goal sequence: `87c51c05`
Latest committed checkpoint before Goal 5: `00c241cf`

This file is a short continuation snapshot. The control plane remains the tier
authority; generated validation/spec artifacts own their schemas and row counts.

## Current Objective

Execute the low-manual productization sequence toward mechanically adjudicated,
reviewable, non-black-box decisions, without granting new ProductWriter,
matrix, workbook, selected peak/area, counted-detection, default extraction, or
GUI authority.

Goal 0/1, Goal 2, Goal 3, and Goal 4 are committed. Goal 5 is verified and
ready to commit. Goal 6 is next: bounded non-broad lane hardening.

## Current State

- `backfill_current_write_ready_scope`: `production_ready`; current Backfill
  authority remains exactly 511 generated-policy `write_ready` cells.
- `broad_backfill_autowrite`: `parked`; the 4613 rows are the candidate/audit
  universe, not writable cells.
- `productization_authority_firewall_v1`: `production_candidate`; fail-closed
  manifest/checker blocks unregistered authority and known negative broad
  Backfill rule families.
- `mechanical_adjudication_contract_v1`: `production_candidate`; all 4613
  Backfill candidate/audit rows have machine decisions without adding writer
  authority.
- `review_packet_workflow_v1`: `production_candidate`; 3015 unresolved
  trace-matched rows have structured review packets. Review approval is not
  ProductWriter approval.
- `peak_choice_truth_lockbox_v1`: `production_candidate`; 72 stratified cases
  are ready for independent labels. Labels cannot write matrix values.
- `missing_overlay_evidence_recovery_v1`: `production_candidate`; all 1087
  missing-overlay rows now link to existing trace/overlay/hypothesis evidence,
  but remain `evidence_required`.
- `productization_status_index_v1`: `production_candidate`; each active lane is
  listed once and `check_productization_state.py` rejects authority drift.
- `quality_explanation_sidecar_v1`: `diagnostic_only`; quality blocker/explainer
  rows cannot grant write authority; keep only as explanation/triage.
- `targeted_ms1_shape_identity_limited_rescue_v1`: `production_ready` only for
  the explicit headless 5-hmdC + 5-medC limited workflow writing
  `detected_flagged`. GUI and broader targets remain blocked.
- `sample_metadata_order_projection_v1`: `production_ready`; `sample_metadata_v1`
  remains production-ready for no-output ordering and metadata projection only.
- `sample_metadata_role_value_behavior`: `blocked`; roles/batch/matrix/exclusion
  must not alter quant output without a separate expected-diff gate.
- `review_action_candidate_sidecar_v1`: `production_candidate` for identity
  verification only.
- `review_action_selected_candidate_switch`: `parked`; ReviewAction
  selected-candidate switch and manual-boundary area recompute remain parked.
- `review_action_manual_boundary_area_writer`: `parked`; manual-boundary area
  recompute remain parked.
- `calibration_normalization_activation`: `frozen`; classification and planning
  only, with no writeback to the primary matrix.
- `gui_replay_parity`: `out_of_scope`; GUI replay / GUI parity is out of scope.
- `targeted_ms1_shape_identity_broader_targets`,
  ISTD-as-truth, and any other non-indexed authority path remain blocked,
  parked, frozen, or out of scope as recorded in the status index.

## Current Artifacts

- Authority/adjudication:
  - `docs/superpowers/specs/productization_authority_manifest.v1.json`
  - `docs/superpowers/specs/mechanical_adjudication_schema.v1.json`
  - `docs/superpowers/validation/mechanical_adjudication_index_v1.tsv`
  - `scripts/check_productization_authority.py`
- Review packets:
  - `docs/superpowers/specs/review_packet_schema.v1.json`
  - `docs/superpowers/validation/review_queue_v1.tsv`
  - `docs/superpowers/validation/review_decision_log_v1.tsv`
- Truth lockbox:
  - `docs/superpowers/specs/peak_choice_truth_protocol.v1.md`
  - `docs/superpowers/specs/truth_label_schema.v1.json`
  - `docs/superpowers/validation/lockbox_sampling_manifest_v1.tsv`
  - `docs/superpowers/validation/reviewer_label_log_v1.tsv`
  - `docs/superpowers/validation/inter_reviewer_agreement_summary_v1.json`
- Missing-overlay recovery:
  - `docs/superpowers/specs/trace_overlay_recovery_contract.v1.json`
  - `docs/superpowers/validation/trace_overlay_recovery_report_v1.tsv`
  - `docs/superpowers/validation/missing_overlay_resolution_summary_v1.json`
- Productization state:
  - `docs/superpowers/specs/productization_control_plane_schema.v1.json`
  - `docs/superpowers/validation/productization_status_index_v1.tsv`
  - `scripts/check_productization_state.py`

## Active Decisions

- Authority stays fail-closed. Current write authority is only the 511-cell
  manifest scope.
- Broad Backfill can reopen only with independent peak-choice / area truth plus
  a later expected-diff authority update.
- `quality_blockers`, round-trip oracle, all-stability, apex-delta, width-only,
  shape-margin, and shape-clean variants cannot be renamed into a writer rule.
- Review packets and future truth labels are approval/evidence surfaces, not
  automatic matrix write authority.
- Recovered trace/overlay links reduce evidence gaps but do not make the 1087
  rows writable.
- ISTD is a limited reference anchor only. It is not analyte peak-choice truth
  or area truth.
- RAW/85RAW was skipped for Goals 0/1 through 5 because these checkpoints are
  no-RAW contract/index transforms over existing artifacts.

## Rejected Paths

- Treating 4613 candidate/audit rows as approved writes.
- Promoting broad Backfill from blocker-token distributions or nested
  threshold families.
- Letting reviewers free-form fill values.
- Letting review approval, lockbox membership, or recovered overlays directly
  mutate ProductWriter, matrix, workbook, selected peak/area, or counted
  detection.
- Treating the status index itself as authority beyond the scope it records.

## Tests / Validation

Latest Goal 5 verification:

- `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_productization_state_index.py -v --tb=short`
  passed `9`.
- `$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check scripts/check_productization_state.py tests/test_productization_state_index.py`
  passed.
- `$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/check_productization_state.py`
  returned `Productization state index is consistent and fail-closed.`
- Subagent Goal 5 review completed. Beauvoir found two P2 checker/schema gaps
  and one P3 anchor gap; Curie found one P3 status-wording drift. All were
  fixed.
- Full local gate passed:
  - `$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor tests scripts/build_trace_overlay_recovery_report.py scripts/build_peak_choice_truth_lockbox.py scripts/check_productization_authority.py scripts/check_productization_state.py`
  - `$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor`
  - `$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/check_productization_authority.py`
  - `$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/check_productization_state.py`
  - `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -v --tb=short -x`
    (`3813 passed, 1 skipped`)
  - `$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/check_diagnostics_index.py`
  - `git diff --check` passed with LF/CRLF warnings only.

## Remaining Work

- Commit Goal 5.
- Implement Goal 6 bounded non-broad lane hardening. This should make the
  already-bounded Targeted MS1, SampleMetadata, and ReviewAction lanes more
  mechanically guarded without changing product output or reviving broad
  Backfill.

## Next Actions

1. Commit Goal 5.
2. Add Goal 6 bounded-lane contract/index/checker/tests.
3. Run subagent review, fix findings, run full gate, and commit Goal 6.
