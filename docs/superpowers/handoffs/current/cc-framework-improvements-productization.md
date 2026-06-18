# XIC productization handoff

Updated: 2026-06-19
Branch: `cc/framework-improvements`
Checkpoint: Phase 0-5 Backfill quant-matrix product spine is complete.

Next work is an explicit validation packet, not another scoring/backlog loop.
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
- Phase 5: read-only promotion readiness checker separating contract
  correctness from scientific confidence.

No scorer was run. No RAW/85RAW was run in this Phase 0-5 sequence.

## Active References

- Product blueprint:
  `docs/superpowers/plans/2026-06-19-backfill-quant-matrix-product-blueprint.md`.
- Cleanup map:
  `docs/superpowers/notes/2026-06-19-backfill-quant-matrix-cleanup-map.md`.
- Schemas:
  `production_acceptance_manifest_schema.v1.json`,
  `quant_matrix_version_schema.v1.json`,
  `quant_matrix_review_report_schema.v1.json`,
  `quant_matrix_promotion_readiness_schema.v1.json`.

## Product Contract

- Backfill values are accepted quantification values, not detections or truth
  claims.
- Future default `quant_matrix` should include detected plus accepted Backfill
  values.
- Detection claims remain based on detected cells only.
- `quant_available_count = detected_count + accepted_backfilled_count`.
- Production write authority must come from `ProductionAcceptanceManifest`
  keyed by `peak_hypothesis_id + sample_stem`.
- Shadow/report/gallery/readiness/candidate artifacts remain non-authority
  unless a later expected-diff promotion packet explicitly grants authority.

## Lane State

- Current Backfill product authority remains exactly 511 cells.
- Broad Backfill auto-write remains parked.
- `4613` remains the candidate/audit universe, not a writable pool.
- `3015` trace-matched unresolved rows remain review/adjudication targets.
- `1087` missing-overlay rows remain evidence gaps, not negative truth.
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

## Phase 5 Contract

`QuantMatrix Promotion Readiness v1` writes
`quant_matrix_promotion_readiness_summary.json` and
`quant_matrix_promotion_readiness_checks.tsv`.

Required guards:

- separate `contract_correctness_status` from
  `scientific_confidence_status`;
- focused tests and 8RAW smoke evidence cannot claim `production_ready`;
- required science pass rows must bind artifact relpath, artifact SHA, and
  tier-specific provenance such as cohort/run, oracle packet, or downstream
  scope;
- duplicate validation tiers fail closed;
- accepted-cell source/row/manifest hashes must be 64-hex;
- no ProductWriter, workbook, GUI, selected peak/area, counted detection,
  review/replay behavior, broad Backfill, or matrix-authority change.

## Rejected Paths

- Do not run or revive a scorer as productization authority.
- Do not create a second independent lockbox case manifest.
- Do not treat owner-clean challenge rows, AI challenge evidence, manual
  negative controls, missing-overlay rows, or summary scores as truth
  completion.
- Do not let shadow/report/gallery/readiness/candidate artifacts feed
  ProductWriter, matrix/workbook output, selected peak/area, counted detection,
  GUI, default extraction, reviewer slot 2, or broad Backfill authority.
- Do not treat low detected support or high Backfill dependency as standalone
  matrix-value blockers; they are prevalence/claim uncertainty flags.
- Do not overwrite detected values with Backfill values.

## Validation Status

Latest Phase 5 final checks:

- Shadow design check-only: pass.
- Phase 1-5 focused shard: 73 passed.
- Phase 3-5 focused shard after typing cleanup: 43 passed.
- Changed-file ruff: pass.
- `uv run mypy xic_extractor/alignment/quant_matrix_promotion.py`: pass.
- `uv run python scripts/check_productization_state.py`: pass.
- `uv run python scripts/check_quant_matrix_promotion_readiness.py --help`:
  pass.
- `git diff --check`: pass with only Git CRLF warnings.
- Scoped changed-files secret/local-path scan: no matches after excluding the
  literal verification phrase.

Sub-agent review:

- Docs/control-plane reviewer found no blockers and confirmed Phase 5 does not
  overclaim production readiness.
- Implementation reviewer found three blockers, all fixed and re-checked:
  unauthenticated tier/status strings, duplicate validation tiers, and
  non-validated accepted-cell hash formats.

## Control Plane Note

Control plane was updated because Phase 5 adds a public readiness schema and
checker script. No maturity tier, active lane, current matrix authority,
selected peak/area, counted detection, ProductWriter default extraction,
review/replay behavior, or broad Backfill state changed.

## Next Actions

1. Commit Phase 5 by purpose.
2. Prepare the next goal as a named validation packet only if it names the
   validation tier and evidence source up front.
