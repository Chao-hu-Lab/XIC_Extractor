# XIC productization handoff

Updated: 2026-06-19
Branch: `cc/framework-improvements`
Checkpoint: Phase 0-7 Backfill quant-matrix product spine is complete.
The current real `QuantMatrixVersion` bundle validates, but default-matrix
promotion remains science-inconclusive until Phase 8 binds a packet v2.

Tier authority lives in
`docs/superpowers/plans/2026-06-15-productization-control-plane.md` plus the
machine-readable validation indexes.

## Current Objective

Backfill productization is moving toward a default quant matrix that includes
detected values plus accepted Backfill values, while keeping detection claims,
truth claims, scientific confidence, and write authority separate.

Completed spine:

- Phase 0: cleanup map and blueprint alignment.
- Phase 1: shadow-only lockbox contract adapter.
- Phase 2: `ProductionAcceptanceManifest v1` schema/checker.
- Phase 3: explicit `QuantMatrixVersion v1` activation outputs.
- Phase 4: review-only `QuantMatrixVersion` report/gallery alignment.
- Phase 5: read-only promotion readiness checker.
- Phase 5 follow-up: no-RAW artifact-bound validation evidence packet.
- Phase 6: no-RAW downstream-impact smoke contract and content validator.
- Phase 7: real 511-cell `QuantMatrixVersion` bundle assembly.

No scorer was run. No RAW/85RAW was run in this sequence.

## Active References

- Product blueprint:
  `docs/superpowers/plans/2026-06-19-backfill-quant-matrix-product-blueprint.md`.
- Cleanup map:
  `docs/superpowers/notes/2026-06-19-backfill-quant-matrix-cleanup-map.md`.
- Control plane:
  `docs/superpowers/plans/2026-06-15-productization-control-plane.md`.
- Current real bundle:
  `docs/superpowers/validation/quant_matrix_real_bundle_v1/`.
- Current promotion packet v1:
  `docs/superpowers/validation/quant_matrix_promotion_validation_packet_v1/`.

## Product Contract

- Backfill values are accepted quantification values, not detections or truth
  claims.
- Future default `quant_matrix` should include detected plus accepted Backfill
  values.
- Detection claims remain based on detected cells only.
- `quant_available_count = detected_count + accepted_backfilled_count`.
- Production write authority must come from `ProductionAcceptanceManifest`
  keyed by `peak_hypothesis_id + sample_stem`.
- Shadow/report/gallery/readiness/validation artifacts remain non-authority
  unless a later expected-diff promotion packet explicitly grants authority.

## Lane State

- Current Backfill product authority remains exactly 511 cells.
- Broad Backfill auto-write remains parked.
- `4613` remains the candidate/audit universe, not a writable pool.
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

## Current Real Bundle

`QuantMatrix Real Bundle v1` lives at
`docs/superpowers/validation/quant_matrix_real_bundle_v1/`.

It was generated from source run
`seed-guard-realdata-85raw-generated-policy-policy-observed-oracle-20260617`
with `downstream_scope=current_511_authority_replay`.

Bundle contents:

- copied source artifacts under `source_artifacts/`;
- `inputs/production_acceptance_manifest.tsv`;
- `inputs/expected_diff.tsv`;
- `quant_matrix_version/quant_matrix.tsv`;
- `quant_matrix_version/cell_provenance.tsv`;
- `quant_matrix_version/row_summary.tsv`;
- `review/quant_matrix_review_summary.json`;
- `downstream_impact/quant_matrix_downstream_impact_smoke.json`;
- `readiness/quant_matrix_promotion_readiness_summary.json`;
- `quant_matrix_real_bundle_summary.json`.

Current result:

- accepted Backfill count: `511`;
- expected diff: `511` expected, `511` written, `0` unused;
- cell provenance: `18000` rows, `511` accepted Backfill, `17489` detected;
- downstream-impact smoke: `pass`;
- readiness: `contract_ready_science_inconclusive`;
- `production_ready=false`;
- `may_promote_default_quant_matrix=false`.

Default Phase 7 `--check-only` fail-closes to the current source run,
`downstream_scope=current_511_authority_replay`, and exactly `511` accepted
Backfill cells. Synthetic or partial bundles need explicit test overrides and
cannot satisfy the default Phase 7 artifact check.

## Current Promotion Packet

`QuantMatrix Promotion Validation Packet v1` remains at
`docs/superpowers/validation/quant_matrix_promotion_validation_packet_v1/`.

Current packet status:

- large-cohort evidence: `pass`;
- heldout-oracle evidence: `pass`;
- downstream-impact evidence: `missing`;
- readiness fixture: `contract_ready_science_inconclusive`;
- `production_ready=false`;
- `may_promote_default_quant_matrix=false`.

Phase 8 should build packet v2 by binding the real bundle's downstream-impact
artifact into the validation packet with the existing large-cohort and
heldout-oracle evidence.

## Phase Artifacts

- Phase 1:
  `docs/superpowers/validation/lockbox_shadow_automation_experiment_v1.json`,
  `scripts/build_lockbox_shadow_automation_experiment_design.py`, and
  `tests/test_lockbox_shadow_automation_experiment_design.py`.
- Phase 2:
  `docs/superpowers/specs/production_acceptance_manifest_schema.v1.json`,
  `scripts/check_production_acceptance_manifest.py`, and
  `tests/test_production_acceptance_manifest_contract.py`.
- Phase 3:
  `xic_extractor/alignment/quant_matrix_version.py`,
  `scripts/build_quant_matrix_version.py`, and
  `tests/test_quant_matrix_version_activation.py`.
- Phase 4:
  `xic_extractor/alignment/quant_matrix_report.py`,
  `scripts/build_quant_matrix_version_report.py`, and
  `tests/test_quant_matrix_version_report.py`.
- Phase 5:
  `xic_extractor/alignment/quant_matrix_promotion.py`,
  `scripts/check_quant_matrix_promotion_readiness.py`, and
  `tests/test_quant_matrix_promotion_readiness.py`.
- Validation packet:
  `xic_extractor/alignment/quant_matrix_validation_packet.py`,
  `scripts/build_quant_matrix_promotion_validation_packet.py`, and
  `tests/test_quant_matrix_validation_packet.py`.
- Phase 6:
  `xic_extractor/alignment/quant_matrix_downstream_impact.py`,
  `scripts/build_quant_matrix_downstream_impact_smoke.py`, and
  `tests/test_quant_matrix_downstream_impact_smoke.py`.
- Phase 7:
  `scripts/build_quant_matrix_real_bundle.py`,
  `tests/test_quant_matrix_real_bundle.py`,
  `docs/superpowers/specs/quant_matrix_real_bundle_schema.v1.json`, and
  `docs/superpowers/validation/quant_matrix_real_bundle_v1/`.

## Rejected Paths

- Do not run or revive a scorer as productization authority.
- Do not create a second independent lockbox case manifest.
- Do not treat owner-clean challenge rows, AI challenge evidence, manual
  negative controls, missing-overlay rows, or summary scores as truth
  completion.
- Do not let shadow/report/gallery/readiness/validation artifacts feed
  ProductWriter, matrix/workbook output, selected peak/area, counted detection,
  GUI, default extraction, reviewer slot 2, or broad Backfill authority.
- Do not treat low detected support or high Backfill dependency as standalone
  matrix-value blockers.
- Do not overwrite detected values with Backfill values.

## Validation Status

Current Phase 7 checks:

- `uv run python scripts/build_quant_matrix_real_bundle.py --check-only`:
  `real_bundle_status: pass`.
- `uv run pytest tests/test_quant_matrix_real_bundle.py -v --tb=short`:
  6 passed.
- `uv run pytest tests/test_quant_matrix_real_bundle.py tests/test_quant_matrix_downstream_impact_smoke.py tests/test_quant_matrix_promotion_readiness.py -v --tb=short`:
  24 passed.
- `uv run ruff check scripts/build_quant_matrix_real_bundle.py tests/test_quant_matrix_real_bundle.py`:
  pass.
- `uv run mypy scripts/build_quant_matrix_real_bundle.py`:
  pass.
- `uv run python scripts/check_productization_state.py`:
  consistent and fail-closed.
- `git diff --check`:
  pass.
- secret scan:
  no credential patterns found; ordinary words such as `tokens` in older
  control-plane prose are false positives.
- local-path scan:
  no Windows absolute paths remain in the Phase 7 changed surface.

## Control Plane Note

Control plane was updated for Phase 7 because this goal adds a public
real-bundle schema, builder/checker script, and durable validation artifact.
No maturity tier, active lane, current 511-cell authority, selected peak/area,
counted detection, ProductWriter default extraction, review/replay behavior,
workbook/GUI behavior, or broad Backfill state changed.

Phase 7 reviewer P1 was fixed: default `--check-only` now rejects non-current
or partial bundles unless explicit test overrides are provided.

## Next Actions

1. Phase 8: build QuantMatrix promotion validation packet v2 using the real
   downstream-impact smoke artifact.
2. Run promotion readiness against the real bundle and packet v2.
3. Keep ProductWriter/default matrix activation out of scope until the
   promotion packet is production-ready.
