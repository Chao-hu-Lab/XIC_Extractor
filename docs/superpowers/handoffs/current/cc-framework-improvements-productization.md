# XIC productization handoff

Updated: 2026-06-19
Branch: `cc/framework-improvements`
Checkpoint: Phase 10 complete pending commit. Product Ready closeout artifact
is generated, focused verification passed, and sub-agent review found one P2
handoff-staleness issue that this update resolves.

Tier authority lives in
`docs/superpowers/plans/2026-06-15-productization-control-plane.md`. This
handoff is the current continuation snapshot, not the tier source of truth.

## Objective

Move Backfill productization toward a default quant matrix containing detected
values plus accepted Backfill values, while keeping detection claims, truth
claims, scientific confidence, and write authority separate.

Active goal scope: finish Phases 8-10 with per-phase focused verification,
sub-agent review, fixes, commit, and handoff/control-plane updates.

## Active References

- Blueprint:
  `docs/superpowers/plans/2026-06-19-backfill-quant-matrix-product-blueprint.md`.
- Control plane:
  `docs/superpowers/plans/2026-06-15-productization-control-plane.md`.
- Current real bundle:
  `docs/superpowers/validation/quant_matrix_real_bundle_v1/`.
- Promotion packet v2:
  `docs/superpowers/validation/quant_matrix_promotion_validation_packet_v2/`.
- Default activation dry-run:
  `docs/superpowers/validation/quant_matrix_default_activation_dry_run_v1/`.
- Product Ready closeout:
  `docs/superpowers/validation/quant_matrix_product_ready_closeout_v1/`.

## Product Contract

- Backfill values are accepted quantification values, not detections or truth.
- Future default `quant_matrix` should include detected plus accepted Backfill
  values.
- Detection claims remain based on detected cells only.
- `quant_available_count = detected_count + accepted_backfilled_count`.
- Production write authority must come from `ProductionAcceptanceManifest`
  keyed by `peak_hypothesis_id + sample_stem`.
- Shadow/report/gallery/readiness/validation artifacts remain non-authority
  unless a later expected-diff activation explicitly grants authority.

## Lane State

- Current Backfill product authority remains exactly 511 cells.
- Broad Backfill auto-write remains parked.
- `4613` remains candidate/audit universe, not a writable pool.
- `3015` trace-matched unresolved rows remain review/adjudication targets.
- `1087` missing-overlay rows remain evidence gaps, not negative truth.
- Low seed/high Backfill dependency are report-only prevalence uncertainty
  flags, not standalone cell-value blockers.
- Lockbox/owner-clean evidence remains non-authoritative challenge evidence.
- Manual wrong-peak/no-peak controls remain negative controls.
- Contract-ready does not mean science-ready.

Status-index anchors retained for `check_productization_state.py`:

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
- Phase 6: no-RAW downstream-impact smoke contract and content validator.
- Phase 7: real 511-cell `QuantMatrixVersion` bundle assembly.
- Phase 8: promotion packet v2 / real-bundle readiness candidate.
- Phase 9: default activation dry-run expected-diff gate.
- Phase 10: Product Ready closeout packet.

No scorer was run. No RAW/85RAW was run in this sequence.

## Current Evidence Chain

Phase 7 real bundle:

- source run:
  `seed-guard-realdata-85raw-generated-policy-policy-observed-oracle-20260617`;
- `downstream_scope=current_511_authority_replay`;
- expected diff: `511` expected, `511` written, `0` unused;
- cell provenance: `18000` rows, `511` accepted Backfill, `17489` detected;
- downstream-impact smoke: `pass`;
- readiness before rebound: `contract_ready_science_inconclusive`.

Phase 8 promotion packet v2:

- readiness label: `production_ready_candidate_packet`;
- `production_ready=true`;
- `may_promote_default_quant_matrix=true`;
- three science tiers pass: large cohort, heldout oracle, downstream impact;
- `write_authority=false`;
- `default_quant_matrix_changed=false`.

Phase 9 default activation dry-run:

- `default_activation_dry_run_gate_status=pass`;
- expected diff: `511` expected, `511` written, `0` unused;
- reference hashes match for `quant_matrix`, `cell_provenance`, `row_summary`,
  and `expected_diff_summary`;
- `dry_run_only=true`;
- `default_matrix_files_written=false`;
- `may_enter_product_ready_closeout=true`.

Phase 10 Product Ready closeout:

- closeout label: `product_ready_default_matrix_candidate`;
- six closeout checks pass;
- `product_ready_candidate=true`;
- `default_quant_matrix_product_ready_candidate=true`;
- `may_activate_default_quant_matrix_with_explicit_contract=true`;
- `requires_product_writer_activation_commit=true`;
- `explicit_activation_not_in_this_commit=true`;
- `write_authority=false`;
- `default_matrix_files_written=false`.

## Still Out Of Scope

- no ProductWriter/default extraction activation;
- no workbook/GUI/selected peak/selected area/counting changes;
- no new matrix authority beyond the current 511-cell source run;
- no broad Backfill revival;
- no scorer and no RAW/85RAW run.

## Rejected Paths

- Do not use scoring weights as write authority.
- Do not treat Backfill as detection or truth.
- Do not grant write authority from shadow/report/gallery/review/readiness
  artifacts alone.
- Do not overwrite detected values with Backfill values.
- Do not create another independent lockbox case manifest.

## Last Verified State

Phase 10 validation passed:

- `uv run pytest tests/test_quant_matrix_product_ready_closeout.py -v --tb=short`;
- `uv run pytest tests/test_quant_matrix_product_ready_closeout.py tests/test_productization_state_index.py -v --tb=short`;
- `uv run pytest tests/test_quant_matrix_product_ready_closeout.py tests/test_quant_matrix_default_activation_dry_run.py tests/test_quant_matrix_promotion_packet_v2.py tests/test_quant_matrix_validation_packet.py tests/test_quant_matrix_real_bundle.py tests/test_quant_matrix_downstream_impact_smoke.py tests/test_quant_matrix_promotion_readiness.py tests/test_productization_state_index.py -v --tb=short`;
- `uv run ruff check scripts/build_quant_matrix_product_ready_closeout.py tests/test_quant_matrix_product_ready_closeout.py`;
- `uv run ruff check scripts/build_quant_matrix_product_ready_closeout.py tests/test_quant_matrix_product_ready_closeout.py tests/test_productization_state_index.py`;
- `uv run mypy scripts/build_quant_matrix_product_ready_closeout.py`;
- `uv run python scripts/build_quant_matrix_promotion_packet_v2.py --check-only`;
- `uv run python scripts/build_quant_matrix_default_activation_dry_run.py --check-only`;
- `uv run python scripts/build_quant_matrix_product_ready_closeout.py --check-only`;
- `uv run python scripts/check_productization_state.py`;
- `git diff --check`;
- local-path and secret scans found no Phase 10 issues.

Latest sub-agent review found one P2 handoff-staleness blocker and no code or
authority blockers. This handoff update resolves that blocker. Residual risk:
Phase 10 remains no-RAW closeout evidence; actual ProductWriter/default output
activation still needs a separate expected-diff-backed commit and public-surface
review.

## Next Actions

1. Rerun focused handoff/state checks after this P2 fix.
2. Commit Phase 10.
3. Next development phase is the explicit ProductWriter/default output
   activation commit, only if requested.
