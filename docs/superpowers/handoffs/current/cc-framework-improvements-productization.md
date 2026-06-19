# XIC productization handoff

Updated: 2026-06-19
Branch: `cc/framework-improvements`
Checkpoint: Phase 0-5 Backfill quant-matrix product spine is complete;
`QuantMatrix Promotion Validation Packet v1` exists but remains science-inconclusive.

Tier authority lives in `docs/superpowers/plans/2026-06-15-productization-control-plane.md`
plus the machine-readable validation indexes.

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

No scorer was run. No RAW/85RAW was run in this sequence.

## Active References

- Product blueprint:
  `docs/superpowers/plans/2026-06-19-backfill-quant-matrix-product-blueprint.md`.
- Cleanup map:
  `docs/superpowers/notes/2026-06-19-backfill-quant-matrix-cleanup-map.md`.
- Schemas:
  `production_acceptance_manifest_schema.v1.json`,
  `quant_matrix_version_schema.v1.json`,
  `quant_matrix_review_report_schema.v1.json`,
  `quant_matrix_promotion_readiness_schema.v1.json`, and
  `quant_matrix_validation_evidence_schema.v1.json`.

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

## Current Validation Packet

`QuantMatrix Promotion Validation Packet v1` lives at
`docs/superpowers/validation/quant_matrix_promotion_validation_packet_v1/`.

- `quant_matrix_validation_evidence_v1.json`
- `quant_matrix_validation_evidence_rows.tsv`
- `quant_matrix_validation_evidence_summary.json`
- copied `artifacts/*`
- `readiness_integration_fixture/*`

Current packet status:

- large-cohort evidence: `pass`, bound to the existing no-RAW 85RAW
  consolidated standard-peak activation input summary.
- heldout-oracle evidence: `pass`, bound to the existing 20-case heldout trace
  reintegration oracle smoke summary.
- downstream-impact evidence: `missing`.
- Phase 5 fixture readiness: `contract_ready_science_inconclusive`.
- `production_ready=false`.
- `may_promote_default_quant_matrix=false`.

The readiness fixture is synthetic contract input used to prove checker
integration only. It is not a real `QuantMatrixVersion` production bundle.

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
  matrix-value blockers; they are prevalence/claim uncertainty flags.
- Do not overwrite detected values with Backfill values.

## Validation Status

Current checks in this goal:

- `uv run pytest tests/test_quant_matrix_validation_packet.py -v --tb=short`:
  11 passed.
- `uv run pytest tests/test_quant_matrix_promotion_readiness.py -v --tb=short`:
  10 passed.
- `uv run pytest tests/test_productization_state_index.py -v --tb=short`:
  21 passed.
- `uv run ruff check xic_extractor/alignment/quant_matrix_validation_packet.py scripts/build_quant_matrix_promotion_validation_packet.py tests/test_quant_matrix_validation_packet.py`:
  pass.
- `uv run mypy xic_extractor/alignment/quant_matrix_validation_packet.py xic_extractor/alignment/quant_matrix_promotion.py`:
  pass.
- `uv run python scripts/build_quant_matrix_promotion_validation_packet.py --write-readiness-fixture`:
  pass.
- `uv run python scripts/build_quant_matrix_promotion_validation_packet.py --check-only`:
  pass.
- Repo-external `uv run --project ... build_quant_matrix_promotion_validation_packet.py --check-only`:
  pass.

Remaining closeout checks before commit:

- productization state check after final edits.
- `git diff --check`.

Sub-agent review:

- Product/control-plane reviewer found no blockers and confirmed this does not
  change maturity tier, active lane, ProductWriter/default matrix authority,
  review/replay behavior, selected peak/area/counting, or production readiness.
- Implementation reviewer found three blockers, fixed with tests: check-only
  now rejects top-level authority drift, resolves source artifacts relative to
  a source root instead of cwd, and validates rows TSV, summary hashes, and any
  readiness fixture inputs/outputs against a fresh checker rerun.
- Final focused re-review found no code-level blocker; the only remaining note
  was that untracked fixture outputs must be staged/committed with this goal.

## Control Plane Note

Control plane was updated because this goal adds a public validation evidence
packet schema, builder/checker script, and durable validation packet. No
maturity tier, active lane, current matrix authority, selected peak/area,
counted detection, ProductWriter default extraction, review/replay behavior, or
broad Backfill state changed.

## Next Actions

1. Define the downstream-impact evidence source for accepted Backfill values.
2. Bind that downstream artifact into the validation packet.
3. Re-run Phase 5 readiness on a real `QuantMatrixVersion` bundle before any
   default-matrix promotion claim.
