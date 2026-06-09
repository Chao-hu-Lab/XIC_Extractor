# Backfill Evidence Reconciliation Productization Note

Date: 2026-06-07

Status: `shadow_ready` for Slice 0/1 diagnostic review surface and the manually
reviewed top14 PeakHypothesis promotion sidecar smoke. Activation has only been
tested and accepted as an 8RAW/current-writer diagnostic copy on rebuilt matrix
artifacts. The 85RAW current-writer artifact refresh passed as
`artifact_refresh_only`; no production matrix write has been promoted.

## Verdict

Implemented the backfill evidence reconciliation machine index and human gallery
surface. This closes diagnostic/review observability for family/seed-group
backfill evidence chains, but it does not promote product behavior.

No product promotion was attempted. The implementation does not mutate
`alignment_review.tsv`, `alignment_cells.tsv`, `alignment_matrix.tsv`, workbook
schemas, selected cells, product decisions, RAW/DLL paths, or downstream matrix
handoff.

## New Surfaces

- `tools/diagnostics/backfill_evidence_reconciliation_gallery.py`
- `xic_extractor/diagnostics/backfill_reconciliation_gallery.py`
- `tests/test_backfill_evidence_reconciliation_gallery.py`
- `backfill_evidence_reconciliation_groups.tsv`
- `backfill_evidence_reconciliation_representative_cells.tsv`
- `backfill_evidence_reconciliation_summary.json`
- `backfill_evidence_reconciliation_gallery.html`

The HTML gallery is table-first, uses collapsed row details, exposes source
artifact links, and keeps PNG links usable as direct anchors with a JS lightbox
enhancement.

Post-review hardening fixed:

- candidate-gate source hash mismatches and missing source hashes fail closed;
- malformed `production_candidate` rows with blockers do not count as
  product-grade support;
- `detected=0` families are excluded from the backfill review queue and counted
  separately because they do not have a detected seed/owner to backfill from;
- review output ordering is disagreement-first;
- PNG, input, and generated artifact links are rebased relative to the gallery
  HTML path;
- dangerous PNG href schemes are rejected before `href` or lightbox dataset
  rendering;
- HTML uses the exact run `validation_label`.

## Evidence-Authority Boundary

The gallery keeps these categories separate:

- product behavior from alignment/product artifacts;
- product-grade support from candidate-gate / Tier 2 evidence rows;
- review-only visual support from seed-aware or overlay rows;
- dependent context from seed/request provenance;
- blockers, missing evidence, stale source, and join gaps.

It does not compute a composite `backfill_score`.

## Existing-Artifact Smoke

Command:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run python tools/diagnostics/backfill_evidence_reconciliation_gallery.py --alignment-review-tsv output/backfill_evidence_gate_8raw_20260605/projected_alignment/alignment_review.tsv --alignment-cells-tsv output/backfill_evidence_gate_8raw_20260605/projected_alignment/alignment_cells.tsv --alignment-matrix-tsv output/backfill_evidence_gate_8raw_20260605/projected_alignment/alignment_matrix.tsv --overlay-batch-summary-tsv output/backfill_evidence_gate_8raw_20260605/changed_row_ms1_overlay_review_20260605/family_ms1_overlay_batch_summary.tsv --output-dir output/backfill_evidence_reconciliation_20260607 --source-run-id backfill_evidence_gate_8raw_20260605
```

Observed output:

- `output/backfill_evidence_reconciliation_20260607/backfill_evidence_reconciliation_groups.tsv`
- `output/backfill_evidence_reconciliation_20260607/backfill_evidence_reconciliation_representative_cells.tsv`
- `output/backfill_evidence_reconciliation_20260607/backfill_evidence_reconciliation_summary.json`
- `output/backfill_evidence_reconciliation_20260607/backfill_evidence_reconciliation_gallery.html`

Summary:

- `group_count`: 850
- `representative_cell_count`: 1237
- `excluded_family_counts`: `detected_zero_family=110`
- `validation_label`: `diagnostic_only`
- `matrix_contract_changed`: false
- `product_behavior_changed`: false
- `missing_evidence_counts`: `missing_seed_provenance=850`
- `reconciliation_class_counts`: `not_assessable_missing_seed_provenance=850`

Interpretation: this 8RAW root contains projected alignment and overlay summary
artifacts, but no `alignment_owner_backfill_seed_audit.tsv` or
`alignment_production_candidate_gate.tsv` in the same root. The gallery therefore
fails closed and reports missing seed provenance instead of treating overlay
presence as product-grade support.

## Browser Smoke

Headless Chromium smoke checked:

- desktop 1440x900;
- mobile 390x844;
- desktop with 200 percent zoom;
- `lang="zh-Hant"`;
- sticky table header;
- horizontal scroll wrapper;
- collapsed details by default;
- direct PNG anchor fallback;
- accessible lightbox marker `aria-modal="true"`;
- PNG href resolves to an existing file from the gallery directory;
- direct PNG image loads inside the lightbox;
- lightbox opens via Enter and Space, focuses close button, closes on Esc, and
  restores focus;
- Tab and Shift+Tab remain inside the modal while it is open;
- search filter targets only main table rows, not nested representative rows.

Observed top-level gallery rows: 850.

## Verification

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests/test_backfill_evidence_reconciliation_gallery.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools/diagnostics/backfill_evidence_reconciliation_gallery.py xic_extractor/diagnostics/backfill_reconciliation_gallery.py tests/test_backfill_evidence_reconciliation_gallery.py
```

Observed:

- `12 passed`
- `All checks passed!`

## Remaining Gaps

- Product promotion remains unattempted.
- Initial smoke did not prove production readiness because the representative
  8RAW artifact root lacked seed audit and candidate-gate sidecars.
- A future allowlisted product-promotion slice still needs a reviewed promotion
  sub-contract, product-grade machine evidence, production-transfer activation
  acceptance, and validation-evidence reviewer acceptance. The 85RAW
  current-writer refresh now exists as a baseline artifact, but it did not carry
  an activation/matrix-diff production-transfer gate.

## Follow-up: Top14 Activation Drift

The user-reviewed top14 standard PeakHypothesis/sample rows were projected into
`backfill_peakhypothesis_promotion_cells.tsv` with 11
`promote_matrix_write` rows. A public-matrix preflight against the 2026-06-07
alignment root initially suppressed all 11 rows because the old public
`alignment_matrix.tsv` already contained values.

Root-cause check rebuilt `alignment_matrix.tsv` and
`alignment_matrix_identity.tsv` from the same
`alignment_review.tsv` / `alignment_cells.tsv` using the current writer. The
rebuilt matrix keeps the same 343 rows but blanks all 11 top14 promotion cells.
Whole-matrix presence drift between the old public matrix and the current writer
was larger than the top14 set: 406 cells were old-written/current-blank and 35
cells were old-blank/current-written.

The activation bridge now writes `activation_matrix_preflight.tsv` and reports
this exact state as
`public_matrix_conflicts_with_projection_current_snapshot`, with
`next_action=rebuild_alignment_matrix_with_current_writer_before_activation`.
When the bridge is run against the current-writer rebuilt matrix, it emits 11
activation decisions. A diagnostic activation copy then reports
`canonical_row_identity_ready=TRUE`, `matrix_cells_written=11`, and all 11
value-delta rows as `written, TRUE`.

The post-activation acceptance gate compares the before/after public matrices
with their identity sidecars and consumes promotion cells, bridge preflight,
activation decisions, activation value delta, and application summary. For the
top14 current-writer diagnostic run it reports:

- `validation_scope=8raw_current_writer_matrix_diff`;
- `promotion_row_count=11`;
- `activation_decision_row_count=11`;
- `preflight_needs_activation_count=11`;
- `changed_matrix_cell_count=11`;
- `unexpected_matrix_diff_count=0`;
- `missing_matrix_diff_count=0`;
- `value_mismatch_count=0`;
- `acceptance_status=pass`.

Interpretation: gallery plus evidence-chain promotion can route the reviewed
true-signal backfill rows through the existing activation owner, but only after
using coherent current-writer matrix artifacts. The old 2026-06-07 public matrix
must not be used as the activation oracle for this slice. This closes the
projection/public-matrix drift blocker for the reviewed top14 standard rows by
identifying the root cause as a stale public-matrix artifact and proving the
current-writer path with matrix-diff acceptance. It does not by itself promote a
production matrix write.

## Follow-up: 85RAW Launch Preflight

Command:

```powershell
.venv\Scripts\python.exe -m scripts.run_alignment --discovery-batch-index local_validation_artifacts\discovery\accepted_p8b\85raw\discovery_batch_index.csv --raw-dir C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R --dll-dir C:\Xcalibur\system\programs --output-dir output\backfill_peakhypothesis_promotion_85raw_20260609\preflight_current_contract --expected-sample-count 85 --output-level validation-minimal --backfill-scope production-equivalent --audit-evidence-mode none --performance-profile validation-fast --raw-workers 11 --owner-backfill-window-strategy super-window --owner-backfill-superwindow-span-factor 2 --timing-output output\backfill_peakhypothesis_promotion_85raw_20260609\preflight_current_contract\timing.json --timing-live-output output\backfill_peakhypothesis_promotion_85raw_20260609\preflight_current_contract\timing.live.json --preflight-only
```

Observed:

- discovery batch samples: 85;
- candidate CSVs found: 85;
- RAW paths found: 85;
- expected sample count: 85;
- 85RAW canonical contract: enforced;
- output level: `validation-minimal`;
- backfill scope: `production-equivalent`;
- audit evidence mode: `none`;
- performance profile: `validation-fast`;
- owner backfill window strategy: `super-window`;
- timing output and live timing heartbeat paths are configured.

Interpretation: this closes the launch-readiness gate only. The preflight did
not load candidate CSV rows, open RAW files, run alignment, mutate product
matrices, or prove 85RAW acceptance. The next production-readiness step, if the
RAW cost is accepted, is the same foreground command without `--preflight-only`,
followed by matrix-diff and no-regression review for the allowlisted slice.

## Follow-up: 85RAW Artifact Refresh

The foreground 85RAW current-writer artifact refresh completed with the same
canonical command shape, omitting `--preflight-only` and writing to:

- `output/backfill_peakhypothesis_promotion_85raw_20260609/artifact_refresh_current_writer/`

Observed artifacts:

- `alignment_review.tsv`
- `alignment_matrix.tsv`
- `alignment_matrix_identity.tsv`
- `alignment_cells.tsv`
- `skipped_evidence_ledger.tsv`
- `alignment_run_metadata.json`
- `timing.json`
- `timing.live.json`

Observed artifact counts:

- `alignment_matrix.tsv`: 685 data rows and 85 sample columns;
- `alignment_review.tsv`: 21,151 data rows;
- `alignment_cells.tsv`: 1,797,835 data rows, matching 21,151 review rows x 85
  samples;
- `skipped_evidence_ledger.tsv`: 38,976 data rows.

Metadata confirms:

- `output_level=validation-minimal`;
- `backfill_scope=production-equivalent`;
- `audit_evidence_mode=none`;
- `matrix_value_policy=gaussian15_positive_asls_residual_primary`;
- `owner_backfill_xic_backend=raw`;
- `schema_version=alignment-results-v3`.

Timing summary:

- timing records: 354;
- summed stage elapsed: about 1,470 seconds;
- heaviest stages: `alignment.owner_backfill` about 409 seconds,
  `alignment.write_outputs` about 220 seconds,
  `alignment.cluster_owners` about 119 seconds.

Validation-evidence reviewer acceptance:

- `run_ok=true`;
- `gate_ok=true` for `artifact_refresh_only`;
- `gate_ok=false` if interpreted as `production_transfer_gate`;
- `production_ready=false`;
- production readiness remains `inconclusive`.

Interpretation: this closes the 85RAW current-writer artifact refresh only. It
does not close top14 production promotion, because the known
projection/public-matrix drift and missing activation matrix-diff/no-regression
acceptance remain product blockers. Do not rerun 85RAW for this slice unless a
fix changes matrix writer behavior or RAW-backed materialization.

## Follow-up: Transfer Readiness Surface

Implemented a final decision surface for the reviewed top14 standard slice:

- `tools/diagnostics/backfill_peakhypothesis_transfer_readiness.py`
- `xic_extractor/diagnostics/backfill_peakhypothesis_transfer_readiness.py`
- `tests/test_backfill_peakhypothesis_transfer_readiness.py`

Correction, 2026-06-09: the earlier 85RAW slice gate incorrectly treated
cross-run `feature_family_id` values as stable identity. That made the
`FAM000572 / Breast_Cancer_Tissue_pooled_QC5` row look absent in 85RAW. This was
wrong. The current gate uses the reviewed promotion seed m/z/RT anchor plus
sample to find the corresponding 85RAW PeakHypothesis candidate. Under that
corrected hypothesis-anchor match, the 8RAW `FAM000572` row maps to 85RAW
`FAM005540`, with `status=rescued` and
`primary_matrix_area=48462.2`. The old winner-remap artifact generated from the
pre-correction slice gate is obsolete and must not be used as product evidence.

The tool consumes only existing artifacts:

- promotion summary from
  `projection_top14_user_standard/backfill_peakhypothesis_promotion_summary.json`;
- 8RAW/current-writer activation acceptance from
  `activation_acceptance_top14_user_standard_current_writer/backfill_peakhypothesis_activation_acceptance.tsv`;
- 85RAW current-writer metadata and TSV counts from
  `output/backfill_peakhypothesis_promotion_85raw_20260609/artifact_refresh_current_writer/`;
- corrected 85RAW hypothesis-anchor slice gate summary from
  `raw85_slice_gate_top14_user_standard/backfill_peakhypothesis_raw85_slice_gate_summary.json`;
- optional manual same-peak verdict summary from
  `raw85_hypothesis_manual_review_top14_user_standard/backfill_peakhypothesis_raw85_manual_verdict_summary.json`.

Observed output:

- `output/backfill_peakhypothesis_promotion_8raw_20260608/transfer_readiness_top14_user_standard/backfill_peakhypothesis_transfer_readiness.tsv`
- `output/backfill_peakhypothesis_promotion_8raw_20260608/transfer_readiness_top14_user_standard/backfill_peakhypothesis_transfer_readiness_summary.json`

Observed readiness row:

- `promotion_matrix_write_count=11`;
- `activation_acceptance_status=pass`;
- `eight_raw_gate_status=pass`;
- `raw85_artifact_status=pass`;
- `raw85_metadata_contract_status=pass`;
- `raw85_sample_column_count=85`;
- `manual_review_scope=observed_8raw_top14_standard_cells`;
- `raw85_slice_gate_status=partial`;
- `raw85_slice_gate_hypothesis_candidate_review_count=11`;
- `raw85_slice_gate_blocked_count=0`;
- `raw85_slice_gate_candidate_no_regression_count=0`;
- `raw85_slice_gate_primary_loser_count=9`;
- `raw85_slice_gate_duplicate_assigned_count=0`;
- `raw85_slice_gate_absent_count=0`;
- `raw85_winner_remap_status=not_assessed`;
- `raw85_peak_shape_review_status=manual_same_peak_supported_all_review_candidates`;
- `area_generalization_status=manual_same_peak_reviewed_area_policy_pending`;
- `readiness_label=production_candidate`;
- `production_ready=FALSE`;
- `hard_fail_reasons=` empty;
- `remaining_blockers=explicit_product_transfer_decision_required;raw85_consolidation_policy_not_productized`;
- `next_action=define_raw85_consolidation_policy_for_same_peak_non_primary_candidates`.

Interpretation: the reviewed top14 standard slice has a clean
8RAW/current-writer matrix-diff gate and a clean 85RAW current-writer artifact
baseline. It no longer shows 85RAW absence for the reviewed cells: all 11
reviewed PeakHypothesis/sample cells have a detected or rescued m/z/RT-anchored
85RAW candidate with a positive Gaussian15 primary area. Manual overlay review
then confirmed all 11 candidates as selected on the correct same peak. The
remaining blocker is no longer peak shape; it is productizing how same-peak
PeakHypothesis evidence should override or coexist with broad family
consolidation / non-primary-row ownership. Nine rows are `primary_loser` rows
and two are primary-winner rows that still carry family consolidation context.
The stale winner-remap route is not a product authority.

The corresponding 85RAW hypothesis review queue was then emitted:

- `output/backfill_peakhypothesis_promotion_8raw_20260608/raw85_hypothesis_review_top14_user_standard/backfill_peakhypothesis_raw85_hypothesis_review_queue.tsv`
- `output/backfill_peakhypothesis_promotion_8raw_20260608/raw85_hypothesis_review_top14_user_standard/backfill_peakhypothesis_raw85_hypothesis_review_summary.json`

Observed review queue summary:

- `review_queue_status=manual_review_required`;
- `candidate_queue_count=11`;
- `non_primary_candidate_count=9`;
- `primary_row_consolidation_context_count=2`;
- `next_action=manual_review_85raw_hypothesis_candidates`.

This queue is review-only. It keeps the corrected source-to-85RAW
PeakHypothesis anchor mapping visible, but it does not judge peak S/N, choose
integration policy, or mutate product matrices.

The queue was then rendered as RAW-backed overlay plots:

- `output/backfill_peakhypothesis_promotion_8raw_20260608/raw85_hypothesis_overlay_top14_user_standard/backfill_peakhypothesis_raw85_overlay_gallery.html`
- `output/backfill_peakhypothesis_promotion_8raw_20260608/raw85_hypothesis_overlay_top14_user_standard/backfill_peakhypothesis_raw85_overlay_index.tsv`
- `output/backfill_peakhypothesis_promotion_8raw_20260608/raw85_hypothesis_overlay_top14_user_standard/plots/`

Observed overlay summary:

- `overlay_count=11`;
- `smooth_method=gaussian15_asls_residual`;
- `smooth_window_points=15`;
- `matrix_contract_changed=false`;
- `product_behavior_changed=false`;
- `next_action=review_overlay_pngs_for_same_peak_candidate_status`.

Representative visual QA uses raw XIC plus `gaussian15_asls_residual` smooth:
`FAM000572 -> FAM005540` has a visible candidate-window peak while the winner RT
sits later; `FAM000808 -> FAM007718` shows a large candidate-vs-winner RT
disagreement. The overlay surface is therefore the right next review surface for
same-peak judgment; family winner text alone is not.

Follow-up manual review, 2026-06-09:

- `output/backfill_peakhypothesis_promotion_8raw_20260608/raw85_hypothesis_manual_review_top14_user_standard/backfill_peakhypothesis_raw85_manual_verdicts.tsv`
- `output/backfill_peakhypothesis_promotion_8raw_20260608/raw85_hypothesis_manual_review_top14_user_standard/backfill_peakhypothesis_raw85_manual_verdict_summary.json`

Observed manual review summary:

- `reviewed_candidate_count=11`;
- `same_peak_supported_count=11`;
- `same_peak_conflict_count=0`;
- `unreviewed_candidate_count=0`;
- `raw85_peak_shape_review_status=manual_same_peak_supported_all_review_candidates`;
- `next_action=define_raw85_consolidation_policy_for_same_peak_non_primary_candidates`.

Follow-up normal-peak decision surface, 2026-06-09:

- `output/backfill_peakhypothesis_promotion_8raw_20260608/normal_peak_decision_top14_user_standard/backfill_peakhypothesis_normal_peak_decisions.tsv`
- `output/backfill_peakhypothesis_promotion_8raw_20260608/normal_peak_decision_top14_user_standard/backfill_peakhypothesis_normal_peak_decision_summary.json`

Normal-peak definition from user review:

- `normal_peak_shape_definition=gaussian15_asls_residual_selected_segment_single_complete_unimodal_peak;raw_spikes_neighbor_contact_family_multiplet_not_blockers`;
- broad/flat to sharp/peaked complete one-peak distributions count as normal;
- the selected segment's Gaussian15 positive AsLS residual morphology is the
  peak-shape boundary;
- raw XIC spikes, neighboring peak contact, family/window-level multiplets, and
  family consolidation/non-primary ownership are not peak-shape hard blockers
  by themselves.

Observed normal-peak decision summary:

- `row_count=11`;
- `normal_peak_candidate_count=11`;
- `required_backfill_count=11`;
- `review_only_nonstandard_count=0`;
- `blocked_count=0`;
- `consolidation_override_count=11`;
- `normal_peak_policy_status=normal_peak_backfill_required_all_reviewed_candidates`;
- `decision_counts.require_backfill=11`.

Interpretation: the normal-peak decision problem for this reviewed top14 slice
is no longer ambiguous. All 11 reviewed normal same-peak PeakHypothesis/sample
cells are `require_backfill`. Nonstandard peaks remain outside this goal.

Follow-up normal-peak activation bridge and matrix diff, 2026-06-09:

- `output/backfill_peakhypothesis_promotion_8raw_20260608/activation_bridge_top14_user_standard_normal_peak_checked/backfill_peakhypothesis_activation_bridge_summary.json`
- `output/backfill_peakhypothesis_promotion_8raw_20260608/activation_acceptance_top14_user_standard_normal_peak_checked/backfill_peakhypothesis_activation_acceptance_summary.json`

Observed activation bridge summary:

- `normal_peak_decision_input_count=11`;
- `normal_peak_required_backfill_count=11`;
- `normal_peak_decision_blocked_count=0`;
- `activation_decision_row_count=11`;
- `public_matrix_projection_conflict_count=0`.

Observed matrix diff acceptance summary:

- `acceptance_status=pass`;
- `changed_matrix_cell_count=11`;
- `expected_written_count=11`;
- `application_matrix_cells_written=11`;
- `unexpected_matrix_diff_count=0`;
- `missing_matrix_diff_count=0`;
- `value_mismatch_count=0`.

Interpretation: the reviewed normal-peak top14 slice is now wired through the
activation bridge and exact matrix-diff acceptance. This proves the reviewed
normal-peak cells can be activated without unrelated public matrix changes. It
does not settle nonstandard peak integration policy or full 85RAW production
readiness.

Follow-up 85RAW artifact-only activation trial, 2026-06-09:

- `output/backfill_peakhypothesis_normal_peak_override_85raw_20260609/preflight_current_contract/`
- `output/backfill_peakhypothesis_normal_peak_override_85raw_20260609/activation_trial_artifact_only/backfill_peakhypothesis_85raw_activation_trial.tsv`
- `output/backfill_peakhypothesis_normal_peak_override_85raw_20260609/activation_trial_artifact_only/backfill_peakhypothesis_85raw_activation_trial_summary.json`

Observed 85RAW preflight:

- `Alignment launch preflight OK`;
- discovery batch samples: `85`;
- candidate CSVs found: `85`;
- RAW paths found: `85`;
- canonical 85RAW contract: enforced;
- no candidate CSVs loaded and no RAW files opened.

Observed no-RAW trial summary:

- `trial_status=pass`;
- `validation_mode=artifact_only_no_raw`;
- `candidate_count=30289`;
- `sample_count=85`;
- `matrix_row_count=685`;
- `normal_peak_required_count=11`;
- `nonstandard_blocked_count=0`;
- `same_peak_supported_count=11`;
- `same_peak_conflict_count=0`;
- `primary_loser_count=9`;
- `primary_winner_count=2`;
- `consolidation_override_count=9`;
- `already_primary_matrix_written_count=0`;
- `expected_matrix_diff_count=11`;
- `unexpected_diff_count=0`;
- `owner_backfill_elapsed_sec=408.9423352999984`;
- `build_matrix_elapsed_sec=60.98443249999946`;
- `claim_registry_elapsed_sec=57.67576149999877`;
- `primary_consolidation_elapsed_sec=89.63260999999875`;
- `write_outputs_elapsed_sec=219.65262780000012`.

Subagent review synthesis:

- strategy/policy: normal same-peak `require_backfill` may override
  consolidation/non-primary only as a PeakHypothesis/sample-scoped rule with
  fail-closed matrix diff acceptance;
- code impact: place the behavior in the shared-peak activation owner, not in
  primary consolidation, claim registry, owner matrix, or the base writer;
- validation: do not rerun full 85RAW before the override path exists, because a
  plain rerun would recreate current artifacts and not close the policy question.

Interpretation: the reviewed normal-peak 85RAW transfer trial expects 11 matrix
cell writes. The two `primary_winner` review-context candidates are still blank
in the current public matrix for their reviewed sample cells, so they also need
activation writes. The transfer key is `raw85_matched_peak_hypothesis_id +
sample`, not the 8RAW source FAM ID. The next implementation slice is a
normal-peak transfer activation path plus matrix-diff acceptance; full RAW
rerun comes after that path exists.

85RAW transfer activation closure, 2026-06-09:

- transfer outputs:
  `output/backfill_peakhypothesis_normal_peak_override_85raw_20260609/activation_transfer_artifact_only/backfill_peakhypothesis_85raw_transfer_promotion_cells.tsv`,
  `output/backfill_peakhypothesis_normal_peak_override_85raw_20260609/activation_transfer_artifact_only/backfill_peakhypothesis_85raw_activation_transfer_summary.json`;
- bridge outputs:
  `output/backfill_peakhypothesis_normal_peak_override_85raw_20260609/activation_bridge_transfer_artifact_only/activation_decisions.tsv`,
  `output/backfill_peakhypothesis_normal_peak_override_85raw_20260609/activation_bridge_transfer_artifact_only/backfill_peakhypothesis_activation_bridge_summary.json`;
- diagnostic activation copy:
  `output/backfill_peakhypothesis_normal_peak_override_85raw_20260609/activation_transfer_diagnostic/activation_application_summary.tsv`,
  `output/backfill_peakhypothesis_normal_peak_override_85raw_20260609/activation_transfer_diagnostic/alignment_matrix.tsv`,
  `output/backfill_peakhypothesis_normal_peak_override_85raw_20260609/activation_transfer_diagnostic/alignment_matrix_identity.tsv`;
- post-activation acceptance:
  `output/backfill_peakhypothesis_normal_peak_override_85raw_20260609/activation_acceptance_transfer_artifact_only/backfill_peakhypothesis_activation_acceptance_summary.json`.

Observed closure summary:

- transfer `promotion_row_count=11`;
- transfer `activation_key_authority=raw85_matched_peak_hypothesis_id`;
- transfer `source_peak_hypothesis_id_authority=audit_only_not_activation_key`;
- bridge `activation_decision_row_count=11`;
- bridge `public_matrix_projection_conflict_count=0`;
- application `matrix_cells_written=11`;
- application `families_added_to_matrix=9`;
- application `matrix_value_conflict_cells=0`;
- acceptance `validation_scope=85raw_current_writer_matrix_diff`;
- acceptance `acceptance_status=pass`;
- acceptance `changed_matrix_cell_count=11`;
- acceptance `unexpected_matrix_diff_count=0`;
- acceptance `missing_matrix_diff_count=0`;
- acceptance `value_mismatch_count=0`;
- acceptance `next_action=ready_for_85raw_reviewed_activation_acceptance`.

Interpretation: the reviewed normal-peak transfer path now passes exact
matrix-diff acceptance on current 85RAW artifacts. This still does not settle
nonstandard peak integration policy or full automatic production activation, but
it closes the specific normal-peak reviewed slice: if a cell is a reviewed
standard-assessable selected segment, same-peak supported, Gaussian15-positive,
and blocker-free except for consolidation/non-primary policy bookkeeping, it can
be activated through the existing activation owner without unrelated matrix
changes.

Matrix-only activation architecture closure, 2026-06-09:

- output:
  `output/backfill_peakhypothesis_normal_peak_override_85raw_20260609/activation_transfer_matrix_only/`;
- post-activation acceptance:
  `output/backfill_peakhypothesis_normal_peak_override_85raw_20260609/activation_acceptance_matrix_only/backfill_peakhypothesis_activation_acceptance_summary.json`;
- application `activation_output_mode=matrix-only`;
- application `matrix_cells_written=11`;
- application `canonical_row_identity_ready=TRUE`;
- output includes `alignment_matrix.tsv`, `alignment_matrix_identity.tsv`,
  `activation_hypothesis_identity.tsv`, `activation_value_delta.tsv`, and
  `activation_application_summary.tsv`;
- output intentionally does not write `alignment_cells.tsv` or
  `alignment_review.tsv`;
- acceptance `acceptance_status=pass`;
- acceptance `changed_matrix_cell_count=11`;
- acceptance `unexpected_matrix_diff_count=0`;
- acceptance `missing_matrix_diff_count=0`;
- acceptance `value_mismatch_count=0`.

Architecture interpretation: the earlier full diagnostic activation copy proved
the same matrix diff, but it unnecessarily read and rewrote the 85RAW
`alignment_cells.tsv` audit ledger. Reviewed normal-peak activation can now use
product-authorized activation values as the quantity source and update only the
public matrix plus identity/delta/summary artifacts. Keep `alignment_cells.tsv`
for audit/debug, evidence projection, and full-copy diagnostics; do not make it
a required dependency for this normal-peak matrix activation slice.

Provenance update: `activation_value_delta.tsv` now uses schema v3 and records
matrix value provenance fields, including source artifact schema/hash and source
row hash. Matrix-only written cells are explicitly tagged as
`matrix_value_kind=backfill_activation` with source
`activation_values_tsv/projected_matrix_value`. In product terms, same-peak
normal-peak evidence can still trigger backfill, but the filled value remains
distinguishable from primary detected values through the sidecar.

Source-bundle provenance rerun, 2026-06-09:

- transfer:
  `output/backfill_peakhypothesis_normal_peak_override_85raw_20260609/activation_transfer_artifact_only_source_bundle/`;
- matrix-only application:
  `output/backfill_peakhypothesis_normal_peak_override_85raw_20260609/activation_transfer_matrix_only_source_bundle/`;
- acceptance:
  `output/backfill_peakhypothesis_normal_peak_override_85raw_20260609/activation_acceptance_matrix_only_source_bundle/`.

Observed: all 11 promotion rows, transfer rows, and value-delta rows carry the
same actual `normal_peak_decisions_tsv + activation_trial_tsv` content bundle
hash. The acceptance summary reports `acceptance_status=pass`,
`changed_matrix_cell_count=11`, `unexpected_matrix_diff_count=0`,
`missing_matrix_diff_count=0`, `value_mismatch_count=0`, and
`value_delta_mismatch_count=0`.

## Follow-up: Peak / Backfill Outside-Frame Research

Bounded literature and source-code research was summarized in:

- `docs/superpowers/notes/2026-06-09-peak-backfill-outside-frame-research-note.md`

The research input supports separating identity confidence, fill/backfill
provenance, and quantitative integration confidence. Mature tools and recent
peak-quality literature do not support treating a single peak picker,
same-peak visual match, or Gaussian-style area as standalone product authority
for nonstandard peaks. The recommended next design slice is diagnostic-only:
emit PeakHypothesis-level integration-quality and fill-provenance rows, validate
them first with masked-positive detected-cell recovery, then decide whether any
area policy can be promoted.

## Follow-up: 8RAW Seed Chain

After reviewing the first gallery, `detected=0` families were confirmed as
out-of-scope for backfill review because they have no detected seed/owner to
backfill from. The gallery now excludes those families from the main review
queue and reports them separately.

New 8RAW alignment with seed audit:

```powershell
.venv\Scripts\python.exe -m scripts.run_alignment --discovery-batch-index local_validation_artifacts\discovery\accepted_p8b\8raw\discovery_batch_index.csv --raw-dir C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation --dll-dir C:\Xcalibur\system\programs --output-dir output\backfill_evidence_chain_8raw_seed_audit_20260607\alignment --expected-sample-count 8 --output-level validation-minimal --backfill-scope production-equivalent --audit-evidence-mode none --performance-profile validation-fast --owner-backfill-window-strategy super-window --owner-backfill-superwindow-span-factor 2 --emit-alignment-cells --emit-alignment-backfill-seed-audit --timing-output output\backfill_evidence_chain_8raw_seed_audit_20260607\alignment\timing.json --timing-live-output output\backfill_evidence_chain_8raw_seed_audit_20260607\alignment\timing.live.json
```

Observed alignment outputs:

- `output/backfill_evidence_chain_8raw_seed_audit_20260607/alignment/alignment_review.tsv`
- `output/backfill_evidence_chain_8raw_seed_audit_20260607/alignment/alignment_cells.tsv`
- `output/backfill_evidence_chain_8raw_seed_audit_20260607/alignment/alignment_matrix.tsv`
- `output/backfill_evidence_chain_8raw_seed_audit_20260607/alignment/alignment_owner_backfill_seed_audit.tsv`

Seed audit summary:

- `SeedRows`: 2280
- `SeedFamilies`: 960

Updated reconciliation with seed audit + overlay:

- `output/backfill_evidence_chain_8raw_seed_audit_20260607/reconciliation_seed_overlay/backfill_evidence_reconciliation_gallery.html`
- `group_count`: 974 seed groups
- `excluded_family_counts`: `detected_zero_family=110`
- `missing_evidence_counts`: none
- `reconciliation_class_counts`:
  `evidence_inconclusive=908`,
  `product_accepts_but_evidence_conflicts=39`,
  `product_accepts_and_visual_supports=27`

Updated reconciliation with seed audit + same-source candidate gate + overlay:

- `output/backfill_evidence_chain_8raw_seed_audit_20260607/reconciliation_seed_gate_overlay/backfill_evidence_reconciliation_gallery.html`
- `group_count`: 974 seed groups
- `excluded_family_counts`: `detected_zero_family=110`
- stale source warnings: 0

The candidate gate sidecar for this new alignment root is same-source but has
`row_count=0`, because `provisional_backfill_candidate_gate.py` still targets
the older `provisional_retention_candidate` scope. The current product path
labels many relevant rows as `production_family` with
`backfill_cell_evidence_required` /
`missing_independent_backfill_identity_evidence`, so the next design issue is a
product-authority evidence gate for actual retained/backfilled product rows, not
another provisional-only gate.

## Follow-up: Retained Product Backfill Gate

Implemented a diagnostic-only sidecar for actual product-retained backfill rows:

- `tools/diagnostics/retained_backfill_evidence_gate.py`
- `xic_extractor/diagnostics/retained_backfill_evidence_gate.py`
- `tests/test_retained_backfill_evidence_gate.py`
- `alignment_retained_backfill_evidence_gate.tsv`
- `alignment_retained_backfill_evidence_gate.json`
- `alignment_retained_backfill_missing_overlay_queue.tsv`

This gate targets rows with product-retained backfill behavior:

- `include_in_primary_matrix=TRUE`
- `identity_decision=production_family`
- detected count greater than zero
- quantifiable, accepted, review-only, or cell-level rescue/backfill context

It excludes `detected=0` families from main rows and counts them separately.
It does not read RAW/DLL, generate overlays, recompute similarity, mutate
alignment artifacts, mutate workbook schemas, or claim production readiness.

Command:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run python -m tools.diagnostics.retained_backfill_evidence_gate --alignment-dir output/backfill_evidence_chain_8raw_seed_audit_20260607/alignment --overlay-batch-summary-tsv output/backfill_evidence_gate_8raw_20260605/changed_row_ms1_overlay_review_20260605/family_ms1_overlay_batch_summary.tsv --output-dir output/backfill_evidence_chain_8raw_seed_audit_20260607/retained_backfill_evidence_gate --source-run-id 8raw_seed_audit_20260607
```

Observed output:

- `output/backfill_evidence_chain_8raw_seed_audit_20260607/retained_backfill_evidence_gate/alignment_retained_backfill_evidence_gate.tsv`
- `output/backfill_evidence_chain_8raw_seed_audit_20260607/retained_backfill_evidence_gate/alignment_retained_backfill_evidence_gate.json`

Summary:

- `family_count`: 271 product-retained backfill families
- `row_count` / `seed_group_count`: 377 family/seed rows
- `excluded_family_counts`: `detected_zero_family=110`
- main rows with detected count zero: 0
- `status_counts`:
  `evidence_missing=311`,
  `evidence_conflict=39`,
  `visual_support=27`
- `production_ready`: false
- `matrix_contract_changed`: false

Interpretation: the current product-retained backfill path has 27 visual
support rows and 39 direct visual conflict rows from the old overlay summary.
The dominant remaining gap is missing overlay evidence for 311 product-retained
family/seed rows. This sidecar is a stable machine input for the next
product-authority decision, but it remains `diagnostic_only`.

Subagent review found no blocker and one P3 hardening item: if
`alignment_review.tsv` reports detected count greater than zero but the joined
`alignment_cells.tsv` rows contain no `status=detected`, the retained gate could
otherwise emit a main row with `detected_cell_count=0`. The gate now fails that
source-drift case closed by excluding the row from the main TSV and counting it
under `excluded_family_counts.detected_cell_join_mismatch`. The 8RAW retained
gate rerun did not hit this new exclusion; counts remained unchanged and main
rows with `detected_cell_count=0` remained 0.

The retained gate now also writes a missing-overlay queue for rows where seed
provenance exists but overlay evidence is missing. The queue is directly
consumable by `family_ms1_overlay_batch.py` and includes `seed_group_id`,
seed m/z, seed RT window, ppm, product behavior, and suggested overlay command
arguments. `family_ms1_overlay_batch.py` now preserves optional `seed_group_id`
in `family_ms1_overlay_batch_summary.tsv`, and retained-gate overlay joins
prefer exact `seed_group_id` matches. Legacy overlay summaries without
`seed_group_id` remain family-level fallback evidence.

Top 30 missing-overlay RAW-backed batch:

```powershell
.venv\Scripts\python.exe -m tools.diagnostics.family_ms1_overlay_batch --review-queue-tsv output\backfill_evidence_chain_8raw_seed_audit_20260607\retained_backfill_evidence_gate\alignment_retained_backfill_missing_overlay_queue.tsv --alignment-cells output\backfill_evidence_chain_8raw_seed_audit_20260607\alignment\alignment_cells.tsv --raw-dir C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation --dll-dir C:\Xcalibur\system\programs --output-dir output\backfill_evidence_chain_8raw_seed_audit_20260607\retained_backfill_evidence_gate\missing_overlay_top30 --limit 30 --ppm 10
```

Observed top30 overlay result:

- output summary:
  `output/backfill_evidence_chain_8raw_seed_audit_20260607/retained_backfill_evidence_gate/missing_overlay_top30/family_ms1_overlay_batch_summary.tsv`
- requested rows: 30
- succeeded: 30
- failed: 0
- PNG missing after success: 0
- `ms1_shape_supports_family_backfill`: 18
- `review_required_neighboring_ms1_interference`: 12
- top30 expansion gate: `blocked`

Combined retained gate with the old overlay summary plus the new top30
seed-specific overlay summary:

- output:
  `output/backfill_evidence_chain_8raw_seed_audit_20260607/retained_backfill_evidence_gate_with_top30_overlay/alignment_retained_backfill_evidence_gate.json`
- `family_count`: 271
- `row_count` / `seed_group_count`: 377
- `excluded_family_counts`: `detected_zero_family=110`
- `status_counts`:
  `evidence_missing=281`,
  `evidence_conflict=51`,
  `visual_support=45`
- `missing_overlay_queue_count`: 281
- `production_ready`: false
- `matrix_contract_changed`: false

Additional missing-overlay RAW-backed batches were generated from the same
queue, preserving exact `seed_group_id` provenance:

- ranks 31-60:
  `output/backfill_evidence_chain_8raw_seed_audit_20260607/retained_backfill_evidence_gate/missing_overlay_031_060/family_ms1_overlay_batch_summary.tsv`
  - requested rows: 30
  - succeeded: 30
  - failed: 0
  - `ms1_shape_supports_family_backfill`: 16
  - `review_required_neighboring_ms1_interference`: 12
  - `review_required_uncertain_ms1_shape`: 2
- ranks 61-90:
  `output/backfill_evidence_chain_8raw_seed_audit_20260607/retained_backfill_evidence_gate/missing_overlay_061_090/family_ms1_overlay_batch_summary.tsv`
  - requested rows: 30
  - succeeded: 30
  - failed: 0
  - `ms1_shape_supports_family_backfill`: 8
  - `review_required_neighboring_ms1_interference`: 19
  - `review_required_uncertain_ms1_shape`: 3
- ranks 91-120:
  `output/backfill_evidence_chain_8raw_seed_audit_20260607/retained_backfill_evidence_gate/missing_overlay_091_120/family_ms1_overlay_batch_summary.tsv`
  - requested rows: 30
  - succeeded: 30
  - failed: 0
  - `ms1_shape_supports_family_backfill`: 25
  - `review_required_neighboring_ms1_interference`: 5

Aggregated top120 missing-overlay result:

- requested rows: 120
- succeeded: 120
- failed: 0
- PNG missing after success: 0
- `ms1_shape_supports_family_backfill`: 67
- `review_required_neighboring_ms1_interference`: 48
- `review_required_uncertain_ms1_shape`: 5

Combined retained gate with the old overlay summary plus top120 seed-specific
overlay summaries:

- output:
  `output/backfill_evidence_chain_8raw_seed_audit_20260607/retained_backfill_evidence_gate_with_top120_overlay/alignment_retained_backfill_evidence_gate.json`
- `family_count`: 271
- `row_count` / `seed_group_count`: 377
- `excluded_family_counts`: `detected_zero_family=110`
- `status_counts`:
  `evidence_missing=191`,
  `evidence_conflict=92`,
  `visual_support=94`
- `missing_overlay_queue_count`: 191
- `production_ready`: false
- `matrix_contract_changed`: false

Interpretation: top120 overlay generation converted 120 previously missing
rows into visual evidence rows. Supported rows increased from 27 to 94, and
conflict/review rows increased from 39 to 92. The remaining 191 rows are still
`evidence_missing`; the 92 conflict rows are intentionally left for manual
review rather than being treated as product-ready support.

## Follow-up: Full Missing-Overlay Completion

The remaining missing-overlay queue was completed from the original 311-row
queue:

- ranks 121-150:
  - requested rows: 30
  - succeeded: 30
  - `ms1_shape_supports_family_backfill`: 25
  - `review_required_neighboring_ms1_interference`: 5
- ranks 151-180:
  - requested rows: 30
  - succeeded: 30
  - `ms1_shape_supports_family_backfill`: 20
  - `review_required_neighboring_ms1_interference`: 10
- ranks 181-210:
  - requested rows: 30
  - succeeded: 30
  - `ms1_shape_supports_family_backfill`: 26
  - `review_required_neighboring_ms1_interference`: 2
  - `review_required_uncertain_ms1_shape`: 2
- ranks 211-240:
  - requested rows: 30
  - succeeded: 30
  - `ms1_shape_supports_family_backfill`: 20
  - `review_required_neighboring_ms1_interference`: 9
  - `review_required_uncertain_ms1_shape`: 1
- ranks 241-270:
  - requested rows: 30
  - succeeded: 30
  - `ms1_shape_supports_family_backfill`: 25
  - `review_required_neighboring_ms1_interference`: 4
  - `review_required_uncertain_ms1_shape`: 1
- ranks 271-300:
  - requested rows: 30
  - succeeded: 30
  - `ms1_shape_supports_family_backfill`: 21
  - `review_required_neighboring_ms1_interference`: 6
  - `review_required_uncertain_ms1_shape`: 3
- ranks 301-311:
  - requested rows: 11
  - succeeded: 11
  - `ms1_shape_supports_family_backfill`: 8
  - `review_required_neighboring_ms1_interference`: 2
  - `review_required_uncertain_ms1_shape`: 1

Full generated missing-overlay result:

- requested rows: 311
- succeeded: 311
- failed: 0
- PNG/PDF missing after success: 0
- `ms1_shape_supports_family_backfill`: 212
- `review_required_neighboring_ms1_interference`: 86
- `review_required_uncertain_ms1_shape`: 13

Combined retained gate with the old overlay summary plus all 311 generated
seed-specific overlay summaries:

- output:
  `output/backfill_evidence_chain_8raw_seed_audit_20260607/retained_backfill_evidence_gate_with_full_missing_overlay/alignment_retained_backfill_evidence_gate.json`
- `family_count`: 271
- `row_count` / `seed_group_count`: 377
- `excluded_family_counts`: `detected_zero_family=110`
- `status_counts`:
  `evidence_conflict=138`,
  `visual_support=239`
- `missing_overlay_queue_count`: 0
- `production_ready`: false
- `readiness_label`: `diagnostic_only`
- `matrix_contract_changed`: false

Interpretation: the evidence-chain gap is no longer missing overlay generation.
All product-retained backfill family/seed rows now have visual overlay evidence.
The remaining work is human review of the 138 conflict/review rows and deciding
whether any supported subset can be promoted through an explicit production
policy. No promotion was attempted in this slice.

## Follow-up: Gallery Family-First UX Correction

Manual review of `FAM000087` in
`output/backfill_evidence_chain_8raw_seed_audit_20260607/reconciliation_seed_gate_overlay/backfill_evidence_reconciliation_gallery.html`
showed that the HTML main table was misleading: the same family appeared twice
because the renderer used family/seed-group rows as the primary table surface.
The two seed groups were near-identical aliases (`mz=254.097/254.098`,
`rt=13.3525/13.1836`) and shared the same legacy family-level overlay PNG.

The renderer was corrected so the HTML gallery is family-first:

- each family appears once in the main review table;
- seed groups, seed m/z/RT/window, per-seed evidence state, and representative
  cells live under collapsed details;
- duplicate main-row links to the same legacy family-level overlay PNG are
  de-duplicated;
- `review_required_*` overlay verdicts are classified as
  `human_visual_judgment_only` instead of `evidence_blocks_backfill`, because
  neighboring MS1 interference is a human review point rather than a hard veto.

The machine TSV remains a family/seed-group index. Product behavior remains
unchanged and no backfill promotion was attempted. The same HTML output path was
regenerated with the full overlay summary set:

- `output/backfill_evidence_chain_8raw_seed_audit_20260607/reconciliation_seed_gate_overlay/backfill_evidence_reconciliation_gallery.html`
- `FAM000087` main HTML row count: 1
- `group_count`: 974 family/seed groups
- `representative_cell_count`: 1424
- `reconciliation_class_counts`:
  `evidence_inconclusive=739`,
  `product_accepts_and_visual_supports=235`

Verification:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests/test_retained_backfill_evidence_gate.py tests/test_family_ms1_overlay_batch.py tests/test_backfill_evidence_reconciliation_gallery.py tests/test_provisional_backfill_candidate_gate_cli.py tests/test_production_candidate_gate.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor/diagnostics/retained_backfill_evidence_gate.py tools/diagnostics/retained_backfill_evidence_gate.py tools/diagnostics/family_ms1_overlay_batch.py tests/test_retained_backfill_evidence_gate.py tests/test_family_ms1_overlay_batch.py xic_extractor/diagnostics/backfill_reconciliation_gallery.py tools/diagnostics/backfill_evidence_reconciliation_gallery.py tests/test_backfill_evidence_reconciliation_gallery.py tools/diagnostics/provisional_backfill_candidate_gate.py tests/test_provisional_backfill_candidate_gate_cli.py tools/diagnostics/INDEX.md
```

Observed:

- `86 passed`
- `All checks passed!`

## Follow-up: Scaled-to-own-max Evidence Correction

Manual review of `FAM000540` showed that the bottom-left overlay panel
(`Absolute RT context: each trace scaled to its own max`) was stronger evidence
than the apex-aligned panel for that family. The old overlay verdict only used
the apex-aligned shape support fraction plus local/global-apex checks, so
`FAM000540` stayed at `review_required_neighboring_ms1_interference` even though
the absolute RT own-max shapes were visually coherent.

The MS1 overlay evidence summary now keeps the original
`shape_supported_fraction` meaning and adds separate own-max evidence:

- `absolute_own_max_shape_supported_fraction`
- `absolute_trace_apex_cluster_fraction`
- `absolute_trace_apex_delta_abs_median_min`

These metrics do not create a composite `backfill_score`. They allow
`ms1_shape_supports_family_backfill` when coverage is sufficient, own-max shape
support and absolute apex clustering are both strong, and the selected peak is
not dominated by a much larger off-target global max.

For `FAM000540`, refreshed evidence is:

- `family_verdict=ms1_shape_supports_family_backfill`
- `shape_supported_fraction=0.625`
- `absolute_own_max_shape_supported_fraction=0.875`
- `absolute_trace_apex_cluster_fraction=0.75`
- `global_apex_interference_fraction=0.25`
- `low_selected_peak_dominance_fraction=0`

The overlay batch summaries, trace JSON/TSV, PNG/PDF overlays, retained gate,
and family-first gallery were regenerated from existing trace JSONs; no RAW
re-read or product matrix mutation was performed. The current HTML remains:

- `output/backfill_evidence_chain_8raw_seed_audit_20260607/reconciliation_seed_gate_overlay/backfill_evidence_reconciliation_gallery.html`
- `FAM000540` main HTML label count: 1
- `FAM000540` seed-group rows in machine TSV: 2
- `FAM000540` evidence state: `review_only_visual_support`
- `FAM000540` reconciliation class: `product_accepts_and_visual_supports`

Subagent review found that the reconciliation gallery still grouped overlay
evidence by family only, which could broadcast seed-specific overlay verdicts
and own-max notes to sibling seed groups. The join was corrected:

- nonblank overlay `seed_group_id` rows now match only the same seed group;
- blank legacy overlay rows remain family-level fallback only when no
  seed-specific overlay exists for the current seed group;
- the machine groups TSV schema is unchanged.

The current regenerated reconciliation summary after this fix is:

- `group_count`: 974
- `representative_cell_count`: 1424
- `evidence_authority_state`:
  `dependent_context_only=597`,
  `human_visual_judgment_only=60`,
  `review_only_visual_support=317`
- `reconciliation_class_counts`:
  `evidence_inconclusive=657`,
  `product_accepts_and_visual_supports=317`

The older one-off changed-row HTML was also refreshed from the updated
`family_ms1_overlay_batch_summary.tsv` to avoid stale manual-review display:

- `output/backfill_evidence_gate_8raw_20260605/changed_row_ms1_overlay_review_20260605/review_gallery.html`
- `FAM000540` now displays
  `family_verdict=ms1_shape_supports_family_backfill`
  with own-max/absolute-apex metrics.

## Follow-up: PeakHypothesis Backfill Promotion Smoke, 2026-06-08

The promotion policy was implemented as a diagnostic-only projection path with
PeakHypothesis/sample-cell allowlist keys. The current smoke did not promote or
activate any matrix value.

Nonstandard but assessable peak-shape rows remain review-only in this slice.
They may carry same-peak own-max identity evidence and area-uncertainty notes,
but they are blocked from matrix-write promotion until a separate integration
policy is approved.

Smoke outputs:

- `output/backfill_peakhypothesis_promotion_8raw_20260608/shadow_projection_refresh/shadow_production_projection_cells.tsv`
- `output/backfill_peakhypothesis_promotion_8raw_20260608/shadow_projection_refresh/shadow_production_projection_summary.json`
- `output/backfill_peakhypothesis_promotion_8raw_20260608/backfill_peakhypothesis_review_queue.tsv`
- `output/backfill_peakhypothesis_promotion_8raw_20260608/backfill_peakhypothesis_promotion_smoke_summary.json`

Current refreshed projection from the same 8RAW source artifacts has
PeakHypothesis identity and row-hash coverage for all 803 rows, but no accepted
promotion candidates:

- refreshed `decision_counts`: `accept=0`, `block=454`, `context=349`
- refreshed rows with `peak_hypothesis_id` and `activation_unit_scope`: 803
- refreshed rows with `shadow_projection_row_sha256`: 803
- review queue row count: 0

The older `reconciliation_seed_gate_overlay` shadow artifact still has 163
legacy accept/projected-new-write rows, but it predates the PeakHypothesis
identity/hash schema and now conflicts with the current projection policy. Those
legacy rows were not converted to `product_authorized` allowlist rows.

Readiness remains `diagnostic_only`. A manually reviewed
`product_authorized` allowlist is still required before the promotion CLI may
produce `shadow_ready` projection outputs; activation, 8RAW matrix diff,
targeted benchmark check, and 85RAW validation remain unrun.

## Follow-up: Activation Gate Decision, 2026-06-08

The existing activation owner remains
`tools/diagnostics/apply_shared_peak_identity_activation.py` and
`xic_extractor.alignment.shared_peak_identity_explanation.product_activation`.
That path expects explicit activation decision and acceptance sidecars, while
the new PeakHypothesis promotion path currently produces only diagnostic review
queue and smoke-summary artifacts.

No activation bridge was added in this slice because the refreshed
PeakHypothesis projection produced zero accepted rows and there is no reviewed
`product_authorized` allowlist. The public `alignment_matrix.tsv` surface
therefore remains unchanged by this work, and the expected matrix diff is
`none` for the current 8RAW smoke.

The next production-transfer slice should only be opened after manually
reviewed promotion rows exist. That slice should convert reviewed
PeakHypothesis promotions into the existing activation decision/acceptance
contract, preserve PeakHypothesis identity in the activation sidecars, and add a
focused matrix-diff oracle before any product activation run.

## Follow-up: Identity-Supported Top14 Calibration, 2026-06-09

The projection now separates formal product-authorized MS1 support from strong
review identity support:

- formal product-authorized support can still reach `shadow_decision=accept`
  and `projected_matrix_written=TRUE`;
- seed provenance plus MS1 same-peak visual support without formal product
  authority is emitted as `shadow_decision=context`,
  `shadow_reasons=identity_supported_review`, and
  `projected_matrix_written=FALSE`;
- those context rows keep the positive projected area so a reviewed allowlist can
  test a narrow sidecar promotion path without changing production behavior.

Refreshed 8RAW projection from the same source artifacts:

- output:
  `output/backfill_peakhypothesis_promotion_8raw_20260608/shadow_projection_identity_support_refresh/shadow_production_projection_summary.json`
- `decision_counts`: `block=454`, `context=349`
- `shadow_reason_counts.identity_supported_review`: 185
- `projected_new_write_count`: 0
- `matrix_contract_changed`: false
- `product_behavior_changed`: false

Manual top14 review was encoded only for user-standard rows
`01,02,03,04,05,06,07,08,09,10,13`. Rows `11` and `14` were excluded as
nonstandard/review-only, and row `12` was left out as borderline. The reviewed
allowlist and sidecar projection are:

- `output/backfill_peakhypothesis_promotion_8raw_20260608/top14_user_standard_allowlist.tsv`
- `output/backfill_peakhypothesis_promotion_8raw_20260608/projection_top14_user_standard/backfill_peakhypothesis_promotion_cells.tsv`
- `output/backfill_peakhypothesis_promotion_8raw_20260608/projection_top14_user_standard/backfill_peakhypothesis_area_uncertainty.tsv`
- `output/backfill_peakhypothesis_promotion_8raw_20260608/projection_top14_user_standard/backfill_peakhypothesis_promotion_summary.json`

Observed top14 sidecar summary:

- `readiness_label`: `shadow_ready`
- `allowlist_row_count`: 11
- `decision_counts.promote_matrix_write`: 11
- `area_uncertainty_counts.standard_assessable`: 11
- `matrix_contract_changed`: false
- `product_behavior_changed`: false

Interpretation: this closes the narrow cost/feasibility question for standard
same-peak user-reviewed rows. It does not activate the rows, write the public
matrix, validate 8RAW matrix diffs, or prove 85RAW readiness. The next step is
an activation planning gate that consumes this sidecar through the existing
activation owner instead of creating a parallel matrix writer.

## Follow-up: Activation Bridge Preflight, 2026-06-09

Implemented a small bridge from reviewed backfill PeakHypothesis promotions into
the existing shared-peak activation sidecar contract:

- `tools/diagnostics/backfill_peakhypothesis_activation_bridge.py`
- `xic_extractor/diagnostics/backfill_peakhypothesis_activation_bridge.py`
- `tests/test_backfill_peakhypothesis_activation_bridge.py`

The bridge writes:

- `activation_decisions.tsv`
- `activation_acceptance.tsv`
- `backfill_peakhypothesis_activation_bridge_summary.json`

It does not apply activation or write matrices. Acceptance defaults to `fail`
with `next_action=run_activation_matrix_diff_smoke`, so the output cannot be
used as production approval by accident.

Initial top14 bridge runs were produced:

- without matrix preflight:
  `output/backfill_peakhypothesis_promotion_8raw_20260608/activation_bridge_top14_user_standard/backfill_peakhypothesis_activation_bridge_summary.json`
  - `activation_decision_row_count`: 11
  - `acceptance_status`: `fail`
  - `hard_fail_reasons`:
    `activation_acceptance_requires_matrix_diff_validation`
- with the stale public matrix + identity preflight:
  `output/backfill_peakhypothesis_promotion_8raw_20260608/activation_bridge_top14_user_standard_matrix_checked/backfill_peakhypothesis_activation_bridge_summary.json`
  - `promotion_row_count`: 11
  - `public_matrix_already_written_count`: 11
  - `activation_decision_row_count`: 0
  - `hard_fail_reasons`:
    `public_matrix_conflicts_with_projection_current_snapshot`
  - `next_action`: `rebuild_alignment_matrix_with_current_writer_before_activation`

A diagnostic-only activation copy was also run with
`--allow-non-passing-acceptance` to measure the would-be matrix effect through
the existing activation owner:

- output:
  `output/backfill_peakhypothesis_promotion_8raw_20260608/activation_top14_user_standard_diagnostic/activation_application_summary.tsv`
- `acceptance_status`: `fail`
- `canonical_row_identity_ready`: `TRUE`
- `auto_activate_count`: 11
- `matrix_cells_written`: 0
- `activation_value_delta.tsv`: 11 `unchanged` rows

Superseding closure run:

- current-writer public matrix + identity preflight:
  `output/backfill_peakhypothesis_promotion_8raw_20260608/activation_bridge_top14_user_standard_current_writer_checked/backfill_peakhypothesis_activation_bridge_summary.json`
  - `promotion_row_count`: 11
  - `public_matrix_already_written_count`: 0
  - `public_matrix_projection_conflict_count`: 0
  - `activation_decision_row_count`: 11
  - `hard_fail_reasons`:
    `activation_acceptance_requires_matrix_diff_validation`
  - `next_action`: `run_activation_matrix_diff_smoke`
- current-writer diagnostic activation copy:
  `output/backfill_peakhypothesis_promotion_8raw_20260608/activation_top14_user_standard_current_writer_diagnostic/activation_application_summary.tsv`
  - `canonical_row_identity_ready`: `TRUE`
  - `matrix_cells_written`: 11
  - `matrix_value_conflict_cells`: 0
- current-writer post-activation acceptance:
  `output/backfill_peakhypothesis_promotion_8raw_20260608/activation_acceptance_top14_user_standard_current_writer/backfill_peakhypothesis_activation_acceptance.tsv`
  - `acceptance_status`: `pass`
  - `changed_matrix_cell_count`: 11
  - `unexpected_matrix_diff_count`: 0
  - `missing_matrix_diff_count`: 0
  - `value_mismatch_count`: 0
  - `next_action`: `ready_for_8raw_reviewed_activation_acceptance`

Interpretation: the original blocker was a stale 2026-06-07 public matrix
artifact, not a live activation-owner or current-writer contradiction. The
bridge correctly fails closed on the stale matrix. Rebuilding the matrix with
the current writer removes the conflict, emits the 11 activation decisions, and
passes the post-activation matrix-diff gate. This closes the
projection/public-matrix drift blocker for the reviewed top14 standard slice.
