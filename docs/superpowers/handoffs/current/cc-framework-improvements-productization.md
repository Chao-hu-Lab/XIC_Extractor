# XIC productization handoff

Updated: 2026-06-19
Branch: `cc/framework-improvements`
Checkpoint: Phase 8 complete. The real 511-cell bundle is now bound into
promotion packet v2; next checkpoint is Phase 9 default-matrix activation
dry-run expected-diff gate.

Tier authority lives in
`docs/superpowers/plans/2026-06-15-productization-control-plane.md`. This
handoff is only the current continuation snapshot.

## Current Objective

Move Backfill productization toward a default quant matrix that includes
detected values plus accepted Backfill values, while keeping detection claims,
truth claims, scientific confidence, and write authority separate.

Active goal scope: finish Phases 8-10 with per-phase focused verification,
sub-agent review, fixes, commit, and handoff/control-plane updates.

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

## Completed Spine

- Phase 1: shadow-only lockbox contract adapter.
- Phase 2: `ProductionAcceptanceManifest v1` schema/checker.
- Phase 3: explicit `QuantMatrixVersion v1` activation outputs.
- Phase 4: review-only `QuantMatrixVersion` report/gallery alignment.
- Phase 5: read-only promotion readiness checker plus validation packet v1.
- Phase 6: no-RAW downstream-impact smoke contract and content validator.
- Phase 7: real 511-cell `QuantMatrixVersion` bundle assembly.
- Phase 8: promotion packet v2 / real-bundle readiness candidate.

No scorer was run. No RAW/85RAW was run in this sequence.

## Current Real Bundle

`docs/superpowers/validation/quant_matrix_real_bundle_v1/` was generated from
source run
`seed-guard-realdata-85raw-generated-policy-policy-observed-oracle-20260617`
with `downstream_scope=current_511_authority_replay`.

Current result:

- accepted Backfill count: `511`;
- expected diff: `511` expected, `511` written, `0` unused;
- cell provenance: `18000` rows, `511` accepted Backfill, `17489` detected;
- downstream-impact smoke: `pass`;
- readiness: `contract_ready_science_inconclusive`;
- `production_ready=false`;
- `may_promote_default_quant_matrix=false`.

Default Phase 7 `--check-only` fail-closes to that source run,
`downstream_scope=current_511_authority_replay`, and exactly `511` accepted
Backfill cells. Synthetic or partial bundles need explicit test overrides.

## Current Promotion Packet v2

`docs/superpowers/validation/quant_matrix_promotion_validation_packet_v2/`
binds the Phase 7 real downstream-impact smoke artifact with existing
large-cohort and heldout-oracle evidence, then runs promotion readiness against
the real bundle inputs.

Current result:

- `quant_matrix_validation_evidence_v1.json` with three passing science tiers;
- `real_bundle_readiness/quant_matrix_promotion_readiness_summary.json`;
- readiness label `production_ready_candidate_packet`;
- `production_ready=true` and `may_promote_default_quant_matrix=true` only for
  the candidate packet;
- accepted Backfill count remains `511`;
- `write_authority=false`;
- `default_quant_matrix_changed=false`;
- `raw_or_85raw_ran=false`;
- `product_writer_changed=false`.

Still out of scope:

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

Phase 8 validation passed:

- `uv run pytest tests/test_quant_matrix_promotion_packet_v2.py tests/test_quant_matrix_validation_packet.py tests/test_quant_matrix_real_bundle.py tests/test_quant_matrix_downstream_impact_smoke.py tests/test_quant_matrix_promotion_readiness.py tests/test_productization_state_index.py -v --tb=short`;
- `uv run ruff check scripts/build_quant_matrix_promotion_packet_v2.py tests/test_quant_matrix_promotion_packet_v2.py tests/test_productization_state_index.py`;
- `uv run mypy scripts/build_quant_matrix_promotion_packet_v2.py`;
- `uv run python scripts/build_quant_matrix_promotion_packet_v2.py --check-only`;
- `uv run python scripts/check_productization_state.py`;
- `git diff --check`;
- credential/local-path scans found no Phase 8 issues.

Sub-agent review found no P1/P2 blockers. Residual risk: Phase 8 is no-RAW
artifact-bound validation; it is not default matrix activation or a new truth
source.

## Next Actions

1. Phase 9: build default-matrix activation dry-run expected-diff gate.
2. Keep ProductWriter/default behavior unchanged until the dry-run gate closes.
3. After Phase 9, run sub-agent review, fix blockers, commit, then proceed to
   Phase 10 Product Ready closeout.
