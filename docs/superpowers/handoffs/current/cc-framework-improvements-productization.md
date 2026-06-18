# XIC productization handoff

Updated: 2026-06-18
Branch: `cc/framework-improvements`
Baseline before this six-goal sequence: `87c51c05`
Previous committed checkpoint before Goal 9: `dcd8878a`
Latest committed Goal 9 checkpoint: `84b4f423`
Latest committed Goal 9 boundary checkpoint: `2460ec4e`
Latest committed Goal 8 import checkpoint: `83412905`

This file is a short continuation snapshot. The control plane remains the tier
authority; generated validation/spec artifacts own their schemas and row counts.

## Current Objective

Execute the low-manual productization sequence toward mechanically adjudicated,
reviewable, non-black-box decisions, without granting new ProductWriter,
matrix, workbook, selected peak/area, counted-detection, default extraction, or
GUI authority.

Goal 0/1 through Goal 7 are complete for this sequence and committed through
`dcd8878a`. Goal 9 Lockbox Static Review UX v1 was committed at `84b4f423`; its
Gaussian-boundary follow-up was committed at `2460ec4e`. Goal 8 imported the
user's first manual pass at `83412905`. The active checkpoint now adds a
read-only next-action split for that imported batch: 53 cases need a second
independent reviewer, 6 are existing manual negative controls, 12 round-trip
oracle negatives stay parked as non-truth evidence, and 1 Gaussian boundary case
needs signal/evidence recovery or remains not assessable. This still adds no
writer authority.

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
  are ready for independent labels. Goal 7 now adds a structured
  label-collection pack around those cases: 72 Markdown packets, a 144-row
  empty label template with two reviewer slots per case, and a validator.
  Goal 9 adds a static review UX with 53 Gaussian15-smoothed plots that have
  Gaussian-derived review boundaries, 18 explicitly missing-evidence pages, and
  1 trace-present boundary-unavailable page. The current Goal 8 import adds a
  one-reviewer label log from the user's 2026-06-18 visual pass: 53 assessable
  Gaussian plots are labeled `correct` / `acceptable` / `acceptable`, and 19
  cases remain `insufficient_evidence` / `not_assessable`. The truth-summary
  decision is `truth_supports_review_only`, not automation or writer authority.
  The new next-action packet splits those 19 cases into 6 existing manual
  negative controls, 12 round-trip oracle negatives parked as non-truth, and 1
  Gaussian boundary-unavailable evidence gap. Labels cannot write matrix values
  and empty template rows are not truth.
- `missing_overlay_evidence_recovery_v1`: `production_candidate`; all 1087
  missing-overlay rows now link to existing trace/overlay/hypothesis evidence,
  but remain `evidence_required`.
- `productization_status_index_v1`: `production_candidate`; each active lane is
  listed once and `check_productization_state.py` rejects authority drift.
- `bounded_non_broad_lane_acceptance_v1`: `production_candidate`; the currently
  bounded non-broad lanes are machine-checked without adding writer authority:
  Targeted MS1 limited rescue, SampleMetadata no-output projection, and
  ReviewAction candidate-sidecar verification can progress only inside their
  named scopes; broader targets, role-driven value changes, selected-candidate
  switch, and manual-boundary area writer remain blocked or parked.
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
  - `docs/superpowers/specs/lockbox_label_schema_v1.json`
  - `docs/superpowers/validation/lockbox_review_packets_v1/packet_index.tsv`
  - `docs/superpowers/validation/lockbox_review_packets_v1/`
  - `docs/superpowers/validation/lockbox_label_template_v1.tsv`
  - `docs/superpowers/validation/lockbox_label_readme_v1.md`
  - `scripts/build_lockbox_label_collection_pack.py`
  - `scripts/check_lockbox_label_schema.py`
  - `docs/superpowers/validation/lockbox_static_review_v1/index.html`
  - `docs/superpowers/validation/lockbox_static_review_v1/bundle_index.tsv`
  - `docs/superpowers/validation/lockbox_static_review_v1/cases/`
  - `docs/superpowers/validation/lockbox_static_review_v1/plots/`
  - `scripts/build_lockbox_static_review_bundle.py`
  - `docs/superpowers/validation/lockbox_reviewer_label_log_v1.tsv`
  - `docs/superpowers/validation/lockbox_truth_summary_v1.json`
  - `docs/superpowers/validation/lockbox_truth_confusion_table_v1.tsv`
  - `docs/superpowers/validation/lockbox_failure_modes_v1.tsv`
  - `docs/superpowers/validation/lockbox_next_action_plan_v1.tsv`
  - `docs/superpowers/validation/lockbox_next_action_summary_v1.json`
  - `scripts/import_lockbox_labels.py`
  - `scripts/build_lockbox_next_action_plan.py`
- Missing-overlay recovery:
  - `docs/superpowers/specs/trace_overlay_recovery_contract.v1.json`
  - `docs/superpowers/validation/trace_overlay_recovery_report_v1.tsv`
  - `docs/superpowers/validation/missing_overlay_resolution_summary_v1.json`
- Productization state:
  - `docs/superpowers/specs/productization_control_plane_schema.v1.json`
  - `docs/superpowers/validation/productization_status_index_v1.tsv`
  - `scripts/check_productization_state.py`
- Bounded non-broad lanes:
  - `docs/superpowers/specs/bounded_non_broad_product_lanes.v1.json`
  - `docs/superpowers/validation/bounded_non_broad_lane_acceptance_v1.tsv`
  - `scripts/check_bounded_product_lanes.py`

## Active Decisions

- Authority stays fail-closed. Current write authority is only the 511-cell
  manifest scope.
- Broad Backfill can reopen only with independent peak-choice / area truth plus
  a later expected-diff authority update.
- `quality_blockers`, round-trip oracle, all-stability, apex-delta, width-only,
  shape-margin, and shape-clean variants cannot be renamed into a writer rule.
- Review packets and future truth labels are approval/evidence surfaces, not
  automatic matrix write authority.
- Lockbox label packets are collection infrastructure only. Codex must not
  invent labels, treat blank template rows as labels, or use reviewer labels as
  immediate ProductWriter authority.
- Static review UX plots are Gaussian15 review/morphology views only. The teal
  shaded boundary is now Gaussian-derived; candidate/raw boundaries are orange
  reference lines only. The plots help humans label peak choice/area/boundary,
  but they are not area truth, ProductWriter input, or matrix authority.
- The first imported lockbox label log is a one-reviewer user batch review. It
  supports review workflow confidence for the 53 assessable plots and records
  19 non-assessable labels, but it is not enough to run an automation/writer
  gate. The next-action split is now more precise: second-review only the 53
  plotted clean cases first; keep the 12 round-trip oracle negatives parked as
  non-truth; treat the 6 manual wrong-peak/no-peak rows as existing negative
  controls only; recover or park the 1 boundary-unavailable case.
- Recovered trace/overlay links reduce evidence gaps but do not make the 1087
  rows writable.
- ISTD is a limited reference anchor only. It is not analyte peak-choice truth
  or area truth.
- RAW/85RAW was skipped for Goals 0/1 through 6 because these checkpoints are
  no-RAW contract/index transforms over existing artifacts.

## Rejected Paths

- Treating 4613 candidate/audit rows as approved writes.
- Promoting broad Backfill from blocker-token distributions or nested
  threshold families.
- Letting reviewers free-form fill values.
- Letting review approval, lockbox membership, or recovered overlays directly
  mutate ProductWriter, matrix, workbook, selected peak/area, or counted
  detection.
- Treating Goal 7 packets, the empty label template, or future reviewer labels
  as direct write approval without a later import/summary gate plus
  expected-diff authority update.
- Treating Goal 9 Gaussian15 plots as product integration, matrix area, or
  automatic peak-choice truth.
- Treating the older candidate/raw boundary as the primary review boundary in
  Goal 9 plots.
- Treating the one-reviewer Goal 8 batch labels as complete lockbox truth,
  expected-diff evidence, ProductWriter input, or broad Backfill reactivation.
- Treating round-trip oracle negatives as peak-choice/area truth, or treating
  existing manual negative controls as missing-evidence unknowns.
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

Latest Goal 6 focused verification:

- `$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/check_bounded_product_lanes.py`
  returned `Bounded non-broad product lanes are consistent and fail-closed.`
- `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_bounded_product_lanes_contract.py -v --tb=short`
  passed `12`.
- `$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check scripts/check_bounded_product_lanes.py tests/test_bounded_product_lanes_contract.py`
  passed.
- Subagent Goal 6 review: Hubble found no findings. Feynman found P1 gaps where
  custom status-index paths, status-index extra/risk rows, and coordinated
  schema+TSV+status promotion could self-attest. Fixed by chaining
  `check_productization_state.py`, binding hashes to the supplied status index,
  moving ready/candidate/blocked/parked lane sets into code-level invariants,
  and adding three focused negative tests. The `current_bounded_surface` field
  is now documented as a bounded progress surface, not product authority.
- Post-fix subagent review: Feynman re-ran the original mutation probes and
  found no P0/P1/P2/P3 findings.
- Final full local gate passed:
  - `$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor tests scripts/build_trace_overlay_recovery_report.py scripts/build_peak_choice_truth_lockbox.py scripts/check_productization_authority.py scripts/check_productization_state.py scripts/check_bounded_product_lanes.py`
  - `$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor`
  - `$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/check_productization_authority.py`
  - `$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/check_productization_state.py`
  - `$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/check_bounded_product_lanes.py`
  - `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -v --tb=short -x`
    (`3825 passed, 1 skipped`)
  - `$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/check_diagnostics_index.py`
  - `git diff --check` passed with LF/CRLF warnings only.

Latest Goal 7 focused verification:

- `$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/build_lockbox_label_collection_pack.py`
  built 72 case packets and 144 empty label-template rows.
- `$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/check_lockbox_label_schema.py`
  returned `Lockbox label collection pack is structurally valid and non-authoritative.`
- `$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/check_lockbox_label_schema.py --verify-evidence-files`
  also passed on this machine, confirming the referenced local `output/`
  evidence files still match recorded hashes. The default checker remains
  hermetic for clean checkouts and does not require ignored `output/` files.
- `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_lockbox_label_collection_pack.py -v --tb=short`
  passed `15`.
- `$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check scripts/build_lockbox_label_collection_pack.py scripts/check_lockbox_label_schema.py tests/test_lockbox_label_collection_pack.py`
  passed.
- Subagent review: Jason found no product-authority or lane-boundary findings.
  Ptolemy found one P1 and three P2 data-contract findings: non-hermetic
  evidence-file validation, completed-label evidence/hash binding gap,
  free-form reason codes, and noncanonical packet path acceptance. Those were
  fixed by adding structural vs `--verify-evidence-files` modes, binding
  completed labels to source hashes, adding reason/evidence enums, enforcing
  canonical packet paths, and adding regression tests. A follow-up P3 identity
  drift finding was fixed by requiring label `row_id`, `family_id`,
  `sample_id`, and `analyte` to match the packet row. Final post-fix subagent
  review found no P0/P1/P2/P3 findings.
- Final full local gate passed:
  - `$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/build_lockbox_label_collection_pack.py`
  - `$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/check_lockbox_label_schema.py`
  - `$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/check_lockbox_label_schema.py --verify-evidence-files`
  - `$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor tests scripts/build_trace_overlay_recovery_report.py scripts/build_peak_choice_truth_lockbox.py scripts/check_productization_authority.py scripts/check_productization_state.py scripts/check_bounded_product_lanes.py scripts/build_lockbox_label_collection_pack.py scripts/check_lockbox_label_schema.py`
  - `$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor`
  - `$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/check_productization_authority.py`
  - `$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/check_productization_state.py`
  - `$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/check_bounded_product_lanes.py`
  - `$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/check_diagnostics_index.py`
  - `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -v --tb=short -x`
    (`3840 passed, 1 skipped`)
  - `git diff --check` passed with LF/CRLF warnings only.

Latest Goal 9 focused verification:

- `$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/build_lockbox_static_review_bundle.py`
  built 72 case pages and 53 Gaussian15 review plots with Gaussian-derived
  boundaries. The remaining cases are 18 explicit `missing_evidence_recorded`
  pages and 1 `gaussian_review_boundary_unavailable` page for a trace file with
  no positive signal.
- `$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/build_lockbox_static_review_bundle.py --check-only`
  returned `Lockbox static review bundle is valid and non-authoritative.`
  The checker now binds the bundle to the current packet index hash, label
  template hash, source artifact hashes, and visible row identity fields so
  stale HTML/PNG review surfaces fail closed.
- `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_lockbox_static_review_bundle.py -v --tb=short`
  passed `11`, including stale packet-index, label-template, source-hash,
  browser-case Gaussian-boundary, and synthetic zero-signal regression tests.
- `$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check scripts/build_lockbox_static_review_bundle.py tests/test_lockbox_static_review_bundle.py`
  passed.
- Subagent review: Lagrange found one P2 stale-bundle checker gap and one P3
  stale control-plane checkpoint wording. Both were fixed. Lagrange found no
  product-authority drift, no label-collection behavior in the HTML, and no
  alternate smoothing path.
- Follow-up subagent review: Wegener found no P1/P2/P3 findings for the
  Gaussian-boundary display fix. Its residual suggestion to add a synthetic
  zero-signal regression was implemented.
- Final local gate passed:
  - `$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor tests scripts/build_lockbox_static_review_bundle.py`
  - `$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor`
  - `$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/check_productization_authority.py`
  - `$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/check_productization_state.py`
  - `$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/check_bounded_product_lanes.py`
  - `$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/build_lockbox_static_review_bundle.py --check-only`
  - `$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/check_diagnostics_index.py`
  - `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -v --tb=short -x`
    (`3851 passed, 1 skipped`)
  - `git diff --check` passed with LF/CRLF warnings only.
- This closes the Goal 9 boundary-display fix.

Latest Goal 8 focused verification:

- `$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/import_lockbox_labels.py --generate-user-batch-log`
  built `docs/superpowers/validation/lockbox_reviewer_label_log_v1.tsv`,
  `lockbox_truth_summary_v1.json`,
  `lockbox_truth_confusion_table_v1.tsv`, and
  `lockbox_failure_modes_v1.tsv`. The summary imports 72 one-reviewer labels:
  53 assessable Gaussian15 static review plots are `correct` /
  `acceptable` / `acceptable`; 19 are `insufficient_evidence` /
  `not_assessable`. The decision is `truth_supports_review_only`.
- `$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/import_lockbox_labels.py --check-only`
  returned `Lockbox truth summary gate is valid and non-authoritative.`
- `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_lockbox_truth_summary.py -v --tb=short`
  passed `8`, including stale source-hash, authority-flag, duplicate-reviewer,
  and two-reviewer clean-label future-path regression tests.
- `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_productization_state_index.py -v --tb=short`
  passed with the status index now pointing `peak_choice_truth_lockbox_v1` at
  `lockbox_truth_summary_v1.json` instead of the older sampling manifest.
- `$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check scripts/import_lockbox_labels.py tests/test_lockbox_truth_summary.py`
  passed.
- Subagent review: Gibbs found one P2 status-index binding gap and one P3
  two-reviewer import-path gap. Both were fixed by binding the productization
  status index to `lockbox_truth_summary_v1.json`, adding a status-index
  regression test, allowing multiple reviewer rows per case while rejecting
  duplicate reviewer IDs, and adding a two-reviewer clean-label gate test.
- Final local gate passed:
  - `$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor tests scripts/import_lockbox_labels.py`
  - `$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor`
  - `$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/check_productization_authority.py`
  - `$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/check_productization_state.py`
  - `$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/check_bounded_product_lanes.py`
  - `$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/check_lockbox_label_schema.py`
  - `$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/build_lockbox_static_review_bundle.py --check-only`
  - `$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/import_lockbox_labels.py --check-only`
  - `$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/check_diagnostics_index.py`
  - `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -v --tb=short -x`
    (`3860 passed, 1 skipped`)

Current Goal 8 next-action focused verification:

- `$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/build_lockbox_next_action_plan.py`
  built `lockbox_next_action_plan_v1.tsv` and
  `lockbox_next_action_summary_v1.json`.
- `$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/build_lockbox_next_action_plan.py --check-only`
  returned `Lockbox next-action plan is valid and non-authoritative.`
- `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_lockbox_next_action_plan.py -v --tb=short`
  passed `13`, including manual-negative separation, round-trip-oracle parking,
  second-review routing, boundary-unavailable routing, stale-plan, stale-summary,
  summary-authority, extra-summary-authority-key, parked-flag, and
  row-authority regressions.
- `$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check scripts/build_lockbox_next_action_plan.py tests/test_lockbox_next_action_plan.py`
  passed.
- `productization_status_index_v1.tsv` now points
  `peak_choice_truth_lockbox_v1` at
  `lockbox_next_action_summary_v1.json`, so future state checks see the
  53/6/12/1 split instead of only the older 19-case coarse blocker.
- Subagent review: Popper found two P2 fail-closed gaps and one follow-up P3.
  Dewey found two P3 data-flow/test gaps. All were fixed by deriving
  decision/reason text from action counts, checking summary authority rules,
  rejecting truthy extra authority keys, constraining
  `parked_for_broad_backfill` to the oracle-negative bucket, and adding focused
  regression tests. Final post-fix review found no P0/P1/P2/P3 findings.
- Final local gate after review fixes passed:
  - `$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor tests scripts/build_lockbox_next_action_plan.py`
  - `$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor`
  - `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -v --tb=short -x`
    (`3873 passed, 1 skipped`)
  - `$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/check_diagnostics_index.py`
  - `$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/check_productization_authority.py`
  - `$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/check_productization_state.py`
  - `$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/check_bounded_product_lanes.py`
  - `$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/build_lockbox_next_action_plan.py --check-only`

## Remaining Work

- Goal 9 has a committed checkpoint at `84b4f423` plus committed
  boundary-display fix `2460ec4e`. Review windows are now Gaussian-derived
  rather than raw/candidate-derived.
- Goal 8 now has a one-reviewer truth-summary gate plus a next-action split.
  It closes the "first manual pass" loop, but the result is still review-only:
  53 cases are ready for a second independent reviewer, 6 are existing manual
  negative controls, 12 round-trip oracle negatives remain parked as non-truth,
  and 1 Gaussian boundary-unavailable case needs signal/evidence recovery or
  stays not assessable.
- No new writer authority, GUI work, matrix/workbook mutation, selected
  peak/area mutation, counted-detection mutation, or broad Backfill revival was
  added.
- The next real product decision is not another Backfill rule. It is to collect
  a second independent reviewer pass for the 53 plotted clean cases, then decide
  if a later truth-backed automation experiment is justified. The other three
  buckets already have current routing: 6 manual negatives are controls, 12
  oracle negatives stay parked, and 1 boundary-unavailable case needs recovery
  or remains not assessable.
- Other remaining decisions stay separate future goals: turn review packets
  into structured human approval UX, decide if and when bounded Targeted MS1
  can expand beyond 5-hmdC/5-medC, decide if SampleMetadata roles may ever
  change values, and decide whether ReviewAction selected-candidate/
  manual-boundary writeback gets an expected-diff writer.

## Next Actions

1. Run subagent review on the next-action split before commit.
2. If review passes, commit the next-action packet/checker/docs.
3. Next product step after that is second-review collection for the 53 plotted
   clean cases, not broad Backfill heuristic mining.
