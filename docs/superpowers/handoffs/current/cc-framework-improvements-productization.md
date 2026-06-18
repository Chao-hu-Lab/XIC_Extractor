# XIC productization handoff

Updated: 2026-06-19
Branch: `cc/framework-improvements`
Current checkpoint: Phase 3 `QuantMatrixVersion Activation v1` implemented;
sub-agent blockers closed and final focused verification passed.

This is the short current-state snapshot. Tier authority lives in
`docs/superpowers/plans/2026-06-15-productization-control-plane.md` plus the
machine-readable validation indexes.

## Current Objective

Phase 3 adds an explicit manifest-driven QuantMatrixVersion activation surface:
validated `ProductionAcceptanceManifest` rows plus an expected-diff TSV can
write additive activation outputs:

- `quant_matrix.tsv`;
- `cell_provenance.tsv`;
- `row_summary.tsv`;
- `expected_diff_summary.tsv`;
- `source_summary.tsv`.

It does not wire ProductWriter default extraction, workbooks, GUI, selected
peak, selected area, counted detection, review/replay behavior, current
511-cell writer authority, or broad Backfill authority.

Next executable phase after review/commit is Phase 4 Gallery/Report Alignment.

## Active Blueprint

- Active roadmap:
  `docs/superpowers/plans/2026-06-19-backfill-quant-matrix-product-blueprint.md`.
- Cleanup map:
  `docs/superpowers/notes/2026-06-19-backfill-quant-matrix-cleanup-map.md`.
- Phase 2 schema:
  `docs/superpowers/specs/production_acceptance_manifest_schema.v1.json`.
- Phase 3 schema:
  `docs/superpowers/specs/quant_matrix_version_schema.v1.json`.

## Current Product Direction

- Backfill values are accepted quantification values.
- Backfill values are not detections and not truth claims.
- Future default `quant_matrix` should include detected plus accepted Backfill
  values.
- Detection claims remain based on detected cells only.
- `quant_available_count = detected_count + accepted_backfilled_count`.
- Production write authority must come from `ProductionAcceptanceManifest`
  keyed by `peak_hypothesis_id + sample_stem`.
- Shadow/report/gallery/candidate artifacts remain non-authority.

## Current Lane State

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

## Phase 1 Result

`lockbox_shadow_automation_experiment_v1` is a shadow-only contract adapter:

- `shadow_decision={accept,flag,reject,not_scored}`;
- owner-clean rows are non-authoritative accept challenges;
- manual negatives are reject hard stops;
- row-level doublet/source/hash/manifest-sha fields are present;
- `shadow_only=true`, `write_authority=false`,
  `matrix_write_allowed=false`, `may_satisfy_reviewer_slot2=false`, and
  `single_owner_evidence_is_truth_completion=false`.

It does not feed ProductWriter, matrix/workbook output, selected peak/area,
counted detection, GUI, default extraction, reviewer slot 2, or broad Backfill
authority.

## Phase 2 Result

`ProductionAcceptanceManifest v1` has:

- schema: `docs/superpowers/specs/production_acceptance_manifest_schema.v1.json`;
- checker: `scripts/check_production_acceptance_manifest.py`;
- tests: `tests/test_production_acceptance_manifest_contract.py`.

The checker enforces primary key `peak_hypothesis_id + sample_stem`,
`feature_family_id` as context only, acceptance vocabulary, authority flags,
manual-negative and doublet hard stops, source path/hash containment, source
row hash, manifest sha, finite non-negative quant values, matching Backfill
fraction, and risk-specific closure.

## Phase 3 Result

New implementation:

- `xic_extractor/alignment/quant_matrix_version.py`;
- `scripts/build_quant_matrix_version.py`;
- `tests/test_quant_matrix_version_activation.py`;
- `docs/superpowers/specs/quant_matrix_version_schema.v1.json`.

The activation surface:

- validates the manifest with the Phase 2 checker;
- requires exact expected-diff rows for accepted Backfill writes;
- fills only blank sample cells;
- rejects detected-value overwrite;
- emits provenance for every non-empty quant matrix cell;
- marks detected cells `write_authority=FALSE`;
- marks accepted Backfill cells `write_authority=TRUE`;
- emits row-level detected/backfilled/available/missing counts;
- makes detected-only view reconstructable from `quant_matrix + cell_provenance`.

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

Latest completed checks:

- `uv run pytest tests/test_quant_matrix_version_activation.py -v --tb=short`
  - 5 passed.
- `uv run pytest tests/test_productization_state_index.py -v --tb=short`
  - 15 passed.
- `uv run ruff check xic_extractor/alignment/quant_matrix_version.py scripts/build_quant_matrix_version.py tests/test_quant_matrix_version_activation.py tests/test_productization_state_index.py`
  - pass.
- `uv run python scripts/build_quant_matrix_version.py --help`
  - pass.
- `uv run pytest tests/test_lockbox_shadow_automation_experiment_design.py tests/test_production_acceptance_manifest_contract.py tests/test_quant_matrix_version_activation.py tests/test_productization_state_index.py -v --tb=short`
  - 50 passed.
- `uv run python scripts/check_productization_state.py`
  - pass.
- `uv run python scripts/check_production_acceptance_manifest.py`
  - pass.
- `git diff --check`
  - pass; only Git CRLF warnings.

Sub-agent review:

- Implementation-contract reviewer found duplicate `matrix_row_index`
  provenance mislabel risk; fixed with identity validation and regression test.
- Docs/control-plane reviewer found incomplete public schema for
  `expected_diff_summary.tsv` and `source_summary.tsv`; fixed with schema
  columns, module constants, writer reuse, and schema guard test.
- Both reviewers re-checked blockers closed with no new blockers.

## Control Plane Note

Control plane was updated because Phase 3 adds a public output schema and
explicit activation script. No maturity tier, active lane, current matrix
authority, selected peak/area, counted detection, ProductWriter default
extraction, review/replay behavior, or broad Backfill state changed.

## Next Actions

1. Run sub-agent implementation-contract review and docs/control-plane review.
2. Fix blockers, rerun verification, and commit Phase 3 by purpose.
3. Prepare Phase 4 Gallery/Report Alignment; do not rebuild gallery unless a
   missing contract requires it.
