# XIC productization handoff

Updated: 2026-06-19
Branch: `cc/framework-improvements`
Current checkpoint: Phase 4 `Gallery/Report Alignment` implemented; Phase 5
`Validation/Promotion Readiness` is next.

This is the short current-state snapshot. Tier authority lives in
`docs/superpowers/plans/2026-06-15-productization-control-plane.md` plus the
machine-readable validation indexes.

## Current Objective

Backfill productization is moving toward a default quant matrix that includes
detected values plus accepted Backfill values, while keeping detection claims,
truth claims, and write authority separate.

Completed spine so far:

- Phase 1: shadow-only lockbox contract adapter.
- Phase 2: `ProductionAcceptanceManifest v1` schema/checker.
- Phase 3: explicit `QuantMatrixVersion v1` activation outputs.
- Phase 4: review-only `QuantMatrixVersion` report/gallery alignment.

Phase 5 must separate contract correctness from scientific promotion readiness.
No RAW/85RAW has been run in this sequence.

## Active Blueprint

- Active roadmap:
  `docs/superpowers/plans/2026-06-19-backfill-quant-matrix-product-blueprint.md`.
- Cleanup map:
  `docs/superpowers/notes/2026-06-19-backfill-quant-matrix-cleanup-map.md`.
- Phase 2 schema:
  `docs/superpowers/specs/production_acceptance_manifest_schema.v1.json`.
- Phase 3 schema:
  `docs/superpowers/specs/quant_matrix_version_schema.v1.json`.
- Phase 4 schema:
  `docs/superpowers/specs/quant_matrix_review_report_schema.v1.json`.

## Product Direction

- Backfill values are accepted quantification values.
- Backfill values are not detections and not truth claims.
- Future default `quant_matrix` should include detected plus accepted Backfill
  values.
- Detection claims remain based on detected cells only.
- `quant_available_count = detected_count + accepted_backfilled_count`.
- Production write authority must come from `ProductionAcceptanceManifest`
  keyed by `peak_hypothesis_id + sample_stem`.
- Shadow/report/gallery/candidate artifacts remain non-authority.

## Lane State

- Current Backfill product authority remains exactly 511 cells.
- Broad Backfill auto-write remains parked.
- `4613` remains the candidate/audit universe, not a writable pool.
- `3015` trace-matched unresolved rows remain review/adjudication targets.
- `1087` missing-overlay rows remain evidence gaps, not negative truth.
- Lockbox/owner-clean evidence remains non-authoritative challenge evidence.
- Manual wrong-peak/no-peak controls remain negative controls.
- No scorer was run. No RAW/85RAW was run.

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

## Phase Results

Phase 1 `lockbox_shadow_automation_experiment_v1`:

- `shadow_decision={accept,flag,reject,not_scored}`;
- owner-clean rows are non-authoritative accept challenges;
- manual negatives are reject hard stops;
- row-level doublet/source/hash/manifest-sha fields are present;
- `shadow_only=true`, `write_authority=false`,
  `matrix_write_allowed=false`, `may_satisfy_reviewer_slot2=false`, and
  `single_owner_evidence_is_truth_completion=false`.

Phase 2 `ProductionAcceptanceManifest v1`:

- schema: `docs/superpowers/specs/production_acceptance_manifest_schema.v1.json`;
- checker: `scripts/check_production_acceptance_manifest.py`;
- tests: `tests/test_production_acceptance_manifest_contract.py`;
- authority key is `peak_hypothesis_id + sample_stem`;
- `feature_family_id` is context/provenance only;
- manual-negative and blocked doublet states are hard stops.

Phase 3 `QuantMatrixVersion v1`:

- module: `xic_extractor/alignment/quant_matrix_version.py`;
- CLI: `scripts/build_quant_matrix_version.py`;
- tests: `tests/test_quant_matrix_version_activation.py`;
- schema: `docs/superpowers/specs/quant_matrix_version_schema.v1.json`;
- outputs: `quant_matrix.tsv`, `cell_provenance.tsv`,
  `row_summary.tsv`, `expected_diff_summary.tsv`, `source_summary.tsv`;
- fills only blank sample cells and rejects detected-value overwrite;
- detected-only view is reconstructable from `quant_matrix + cell_provenance`.

Phase 4 `QuantMatrixVersion Review Report v1`:

- module: `xic_extractor/alignment/quant_matrix_report.py`;
- CLI: `scripts/build_quant_matrix_version_report.py`;
- tests: `tests/test_quant_matrix_version_report.py`;
- schema: `docs/superpowers/specs/quant_matrix_review_report_schema.v1.json`;
- outputs: `quant_matrix_review_rows.tsv`,
  `quant_matrix_review_summary.json`, and
  `quant_matrix_review_report.html`;
- exposes accepted Backfill versus detected cells, prevalence uncertainty,
  manifest/source hashes, manual-negative closure, doublet closure, and the
  Gaussian-smoothed trace-primary/raw-trace-auxiliary convention;
- fails closed when accepted Backfill cells cannot join back to the manifest;
- accepted-cell manifest join is hash/authority-bound: `manifest_sha256`,
  `source_row_sha256`, accepted decision, `write_authority=TRUE`,
  `matrix_write_allowed=TRUE`, and `shadow_only=FALSE` must agree;
- `source_summary.production_acceptance_manifest_sha256` must also match the
  current manifest file hash before report enrichment;
- review/report only, no authority promotion.

## Rejected Paths

- Do not run or revive a scorer as productization authority.
- Do not create a second independent lockbox case manifest.
- Do not treat owner-clean challenge rows, AI challenge evidence, manual
  negative controls, missing-overlay rows, or summary scores as truth completion.
- Do not let shadow/report/gallery/candidate artifacts feed ProductWriter,
  matrix/workbook output, selected peak/area, counted detection, GUI, default
  extraction, reviewer slot 2, or broad Backfill authority.
- Do not treat low detected support or high Backfill dependency as standalone
  matrix-value blockers; they are prevalence/claim uncertainty flags.
- Do not overwrite detected values with Backfill values.

## Validation Status

Latest completed Phase 4 checks:

- `uv run pytest tests/test_quant_matrix_version_report.py -v --tb=short`
  - 9 passed.
- `uv run pytest tests/test_quant_matrix_version_report.py tests/test_productization_state_index.py -v --tb=short`
  - 26 passed.
- `uv run ruff check xic_extractor/alignment/quant_matrix_report.py scripts/build_quant_matrix_version_report.py tests/test_quant_matrix_version_report.py tests/test_productization_state_index.py`
  - pass before the final hash-bound join regression addition.
- `uv run python scripts/check_productization_state.py`
  - pass.
- `uv run pytest tests/test_lockbox_shadow_automation_experiment_design.py tests/test_production_acceptance_manifest_contract.py tests/test_quant_matrix_version_activation.py tests/test_quant_matrix_version_report.py tests/test_productization_state_index.py -v --tb=short`
  - 61 passed.
- `uv run python scripts/build_quant_matrix_version_report.py --help`
  - pass.
- `git diff --check`
  - pass; only Git CRLF warnings.
- Scoped secret/local-path scan over changed Phase 4 files
  - no matches.

Latest completed Phase 3/contract checks retained as baseline:

- `uv run python scripts/check_production_acceptance_manifest.py`
  - pass before Phase 4 updates.

Sub-agent review:

- Docs/control-plane reviewer found no blockers and confirmed Phase 4 is
  additive review/report surface only.
- Implementation-contract reviewer found a stale same-key manifest join blocker;
  fixed with source-summary manifest file-hash validation plus hash/authority-
  bound join validation and regression tests. The reviewer re-checked both P1
  findings closed with no new blocker.

## Control Plane Note

Control plane was updated because Phase 4 adds a public review/report schema and
explicit report script. No maturity tier, active lane, current matrix authority,
selected peak/area, counted detection, ProductWriter default extraction,
review/replay behavior, or broad Backfill state changed.

## Next Actions

1. Commit Phase 4 by purpose.
2. Proceed directly to Phase 5 `Validation/Promotion Readiness`.
