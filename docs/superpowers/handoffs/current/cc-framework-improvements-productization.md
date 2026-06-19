# XIC productization handoff

Updated: 2026-06-19
Branch: `cc/framework-improvements`
Checkpoint: Phase 11 explicit ProductWriter/default output activation is
implemented. Focused activation tests pass; full closeout verification is still
in progress in the current session.

Tier authority lives in
`docs/superpowers/plans/2026-06-15-productization-control-plane.md`. This
handoff is a current-state continuation snapshot, not the tier source of truth.

## Objective

Make the default quant matrix contain detected values plus the current accepted
Backfill values, while keeping Backfill separate from detection, truth,
selected peak/area, and counted-detection behavior.

## Active References

- Blueprint:
  `docs/superpowers/plans/2026-06-19-backfill-quant-matrix-product-blueprint.md`.
- Control plane:
  `docs/superpowers/plans/2026-06-15-productization-control-plane.md`.
- Default ProductWriter activation:
  `docs/superpowers/validation/quant_matrix_default_product_activation_v1/`.
- Product Ready closeout:
  `docs/superpowers/validation/quant_matrix_product_ready_closeout_v1/`.
- Real 511-cell bundle:
  `docs/superpowers/validation/quant_matrix_real_bundle_v1/`.

## Product Contract

- `product_ready_default_matrix_activated` is the current default-output
  activation label.
- Default `quant_matrix.tsv` now contains detected values plus 511 accepted
  Backfill quantification values.
- Backfill values are not detections, truth claims, or counted detections.
- Detected-only claims remain reconstructable from `cell_provenance`.
- `quant_available_count = detected_count + accepted_backfilled_count`.
- Product authority scope remains `backfill_policy_write_ready_rows`.
- Broad Backfill remains parked.

## Current Lane State

- Current Backfill product authority remains exactly 511 cells.
- Status-index writer row now points to
  `docs/superpowers/validation/quant_matrix_default_product_activation_v1/quant_matrix_default_product_activation_summary.json`.
- Authority row still has `row_count=511`,
  `write_authority=TRUE`, `may_touch_matrix=TRUE`, and
  `may_change_quant_output=TRUE`.
- Registered authority scope remains `backfill_policy_write_ready_rows`.
- `4613` remains candidate/audit universe, not a writable pool.
- `3015` trace-matched unresolved rows remain review/adjudication targets.
- `1087` missing-overlay rows remain evidence gaps.
- Lockbox/owner-clean evidence remains non-authoritative challenge evidence.

Status-index anchors retained:

- Broad Backfill auto-write remains parked.
- Goal 0/1 hardening added.
- machine-adjudicated without granting new writer authority.
- Goal 2 added Review Packet / Approval Workflow v1.
- lockbox_shadow_automation_experiment_v1.
- Goal 4 added Missing-Overlay Evidence Recovery v1.
- keep only as explanation/triage.
- Targeted MS1 shape identity limited rescue remains production-ready.
- GUI and broader targets remain blocked.
- `sample_metadata_v1` remains production-ready for no-output ordering.
- roles/batch/matrix/exclusion must not alter quant output.
- ReviewAction selected-candidate switch and manual-boundary area recompute remain parked.
- manual-boundary area recompute remain parked.
- classification and planning only.

## Completed Spine

- Phase 1: shadow-only lockbox contract adapter.
- Phase 2: `ProductionAcceptanceManifest v1` schema/checker.
- Phase 3: explicit `QuantMatrixVersion v1` activation outputs.
- Phase 4: review-only `QuantMatrixVersion` report/gallery alignment.
- Phase 5: read-only promotion readiness checker plus validation packet v1.
- Phase 6: no-RAW downstream-impact smoke contract.
- Phase 7: real 511-cell `QuantMatrixVersion` bundle assembly.
- Phase 8: promotion packet v2 / real-bundle readiness candidate.
- Phase 9: default activation dry-run expected-diff gate.
- Phase 10: Product Ready closeout packet.
- Phase 11: explicit default ProductWriter/output activation.

No scorer was run. No RAW/85RAW was run in this activation sequence.

## Current Evidence

Phase 11 activation:

- output dir:
  `docs/superpowers/validation/quant_matrix_default_product_activation_v1/`;
- `source_run_id=seed-guard-realdata-85raw-generated-policy-policy-observed-oracle-20260617`;
- `downstream_scope=current_511_authority_replay`;
- expected diff: `511` expected, `511` written, `0` unused;
- cell provenance: `18000` rows, `17489` detected,
  `511` accepted Backfill;
- output hashes for `quant_matrix`, `cell_provenance`, `row_summary`, and
  `expected_diff_summary` match the Phase 7 reference bundle;
- `source_summary` binds baseline matrix, identity, manifest, and expected-diff
  hashes;
- `workbook_or_gui_changed=false`;
- `selected_peak_area_or_counting_changed=false`;
- `broad_backfill_unparked=false`.

Default output files:

- `default_output/quant_matrix.tsv`;
- `default_output/cell_provenance.tsv`;
- `default_output/row_summary.tsv`;
- `default_output/expected_diff_summary.tsv`;
- `default_output/source_summary.tsv`;
- `default_product_activation_checks.tsv`;
- `quant_matrix_default_product_activation_summary.json`.

## Still Out Of Scope

- no workbook or GUI activation;
- no selected peak, selected area, or counted-detection change;
- no new matrix authority beyond the current 511 cells;
- no broad Backfill revival;
- no scorer and no RAW/85RAW run.

## Verification Status

Already passed in this session:

- `uv run pytest tests/test_quant_matrix_default_product_activation.py -v --tb=short`.

Still to run before commit:

- activation `--check-only`;
- focused productization state tests;
- broader quant-matrix regression tests;
- `uv run python scripts/check_productization_state.py`;
- `uv run ruff check` on changed Python/tests;
- `uv run mypy` if the changed Python surface needs it;
- `git diff --check`;
- sub-agent review and repair if needed.

## Next Actions

1. Finish verification for Phase 11.
2. Run sub-agent review focused on default output activation/public surface.
3. Fix any review findings.
4. Commit the activation as one purpose-scoped commit.
