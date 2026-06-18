# XIC productization handoff

Updated: 2026-06-19
Branch: `cc/framework-improvements`
Recent committed checkpoints: `239d5e52` blueprint; `7c229332` Phase 1 adapter.
Current checkpoint: Phase 2 `ProductionAcceptanceManifest v1` implemented;
Phase 3 not started.

This is the short current-state snapshot. Tier authority lives in
`docs/superpowers/plans/2026-06-15-productization-control-plane.md` plus the
machine-readable validation indexes.

## Current Objective

Phase 2 is implemented: `ProductionAcceptanceManifest v1` now has an additive
schema artifact and fail-closed checker. This defines the only future Backfill
row artifact that may grant `write_authority=true`, but it still does not write
the default matrix.

Next executable productization phase is Phase 3: QuantMatrixVersion Activation
with expected-diff, `cell_provenance`, and focused output tests.

## Active Blueprint

- Active roadmap:
  `docs/superpowers/plans/2026-06-19-backfill-quant-matrix-product-blueprint.md`.
- Cleanup map:
  `docs/superpowers/notes/2026-06-19-backfill-quant-matrix-cleanup-map.md`.
- Superseded/adapt source:
  `docs/superpowers/plans/2026-06-18-backfill-evidence-lifecycle-blueprint.md`.

## Current Product Direction

- Backfill values are accepted quantification values.
- Backfill values are not detections.
- Backfill values are not truth claims.
- The future default `quant_matrix` should include detected plus accepted
  Backfill values.
- Detection claims remain based on `detected_count` only.
- `quant_available_count` is detected plus accepted Backfill.
- Production write authority must come from `ProductionAcceptanceManifest`
  keyed by `peak_hypothesis_id + sample_stem`.
- Shadow/report/gallery/candidate artifacts remain non-authority.

## Current State

- Current Backfill product authority remains exactly 511 cells.
- Broad Backfill auto-write remains parked.
- The parked item is broad uncontracted writer behavior, not the product goal
  of accepted Backfill entering a future default quant matrix.
- `4613` remains the candidate/audit universe, not a writable pool.
- `3015` trace-matched unresolved rows remain review/adjudication targets, not
  writer rows.
- `1087` missing-overlay rows remain evidence gaps, not negative truth.
- Lockbox/owner-clean evidence remains non-authoritative challenge evidence.
- Manual wrong-peak/no-peak controls remain negative controls.
- No scorer was run. No RAW/85RAW was run.
- No ProductWriter, matrix, workbook, selected peak/area, counted detection,
  GUI, default extraction, actual authority rows, or broad Backfill behavior
  changed in Phases 1-2.

## Phase 1 Result

Updated artifact: `docs/superpowers/validation/lockbox_shadow_automation_experiment_v1.json`.
Source manifest: `docs/superpowers/validation/lockbox_shadow_automation_cases_v1.tsv`.
The single 72-case manifest carries:

- `shadow_decision={accept,flag,reject,not_scored}`;
- owner-clean as `not_truth_claimed` / `non_authoritative_challenge`;
- manual negatives as `reject` hard stops;
- row-level doublet/source/hash/manifest-sha fields;
- `shadow_only=true`, `write_authority=false`,
  `matrix_write_allowed=false`, `may_satisfy_reviewer_slot2=false`, and
  `single_owner_evidence_is_truth_completion=false`.

`lockbox_shadow_automation_experiment_v1` remains a shadow-only public surface.
It does not feed ProductWriter, matrix/workbook output, selected peak/area,
counted detection, GUI, default extraction, reviewer slot 2, or broad Backfill
authority.

## Phase 2 Result

New schema: `docs/superpowers/specs/production_acceptance_manifest_schema.v1.json`.
New checker: `scripts/check_production_acceptance_manifest.py`.

The checker enforces:

- primary key `peak_hypothesis_id + sample_stem`;
- `feature_family_id` as context/provenance only;
- acceptance vocabulary and basis rules;
- `shadow_only=false`, `write_authority=true`, and
  `matrix_write_allowed=true` only for accepted production rows;
- manual-negative, hard-blocker, blocked-doublet, and missing-provenance stops;
- source path/hash, source row hash, and canonical manifest sha;
- source/doublet artifact path containment, existence, and file-hash match;
- finite non-negative accepted quant value and matching Backfill fraction;
- low seed / high Backfill dependency as report-only prevalence risk;
- strict risk closure via `closure_rule_ids`.

It does not create production rows from the lockbox shadow manifest and does not
write ProductWriter/default matrix outputs.

## Current Lane State

- `peak_choice_truth_lockbox_v1` remains `production_candidate`.
- `mechanical_adjudication_index_v1`, Review Packet / Approval Workflow v1,
  Missing-Overlay Evidence Recovery v1, and lockbox assets remain
  non-authority review/evidence infrastructure.
- Targeted MS1 shape identity limited rescue remains production-ready only for
  the explicit 5-hmdC + 5-medC headless workflow; GUI and broader targets remain
  blocked.
- `sample_metadata_v1` remains production-ready for no-output ordering.
- roles/batch/matrix/exclusion must not alter quant output.
- ReviewAction selected-candidate switch and manual-boundary area recompute
  remain parked.
- calibration/normalization activation remains classification and planning only.

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

## Rejected Paths

- Do not run or revive a scorer as productization authority.
- Do not create a second independent lockbox case manifest.
- Do not treat owner-clean challenge rows, AI challenge evidence, manual
  negative controls, missing-overlay rows, or any future summary score as truth
  completion.
- Do not let any shadow artifact feed ProductWriter, matrix/workbook output,
  selected peak/area, counted detection, GUI, default extraction, reviewer slot
  2, or broad Backfill authority.
- Do not treat low detected support or high Backfill dependency as a standalone
  matrix-value blocker; they are prevalence/claim uncertainty flags.
- Do not write accepted Backfill into the default matrix before Phase 3
  expected-diff activation exists.

## Current Files Changed

- Phase 1: lockbox shadow adapter script/tests and generated 72-case shadow
  artifact remain current.
- Phase 2: production acceptance manifest schema/checker/tests were added.
- `docs/superpowers/plans/2026-06-15-productization-control-plane.md`,
  `docs/superpowers/specs/README.md`, `tests/test_productization_state_index.py`,
  and this handoff were updated for the Phase 2 contract surface.

Phase 0 blueprint and Phase 1 adapter changes are committed. User-provided
deepresearch inputs and separate cleanup inventory notes remain untracked and
unmodified.

## Validation Status

Latest completed checks:

- `uv run python scripts/build_lockbox_shadow_automation_experiment_design.py --check-only`
  - pass.
- `uv run pytest tests/test_lockbox_shadow_automation_experiment_design.py -v --tb=short`
  - 14 passed.
- `uv run pytest tests/test_lockbox_shadow_automation_experiment_design.py -k "manual_negative_accept or blocked_doublet or owner_clean_truth_completion or missing_source_hashes or actual_case_manifest_path" -v --tb=short`
  - 5 passed, 9 deselected.
- `uv run pytest tests/test_productization_state_index.py -v --tb=short`
  - 13 passed.
- `uv run python scripts/check_production_acceptance_manifest.py`
  - pass.
- `uv run pytest tests/test_production_acceptance_manifest_contract.py -v --tb=short`
  - 16 passed.
- `uv run python scripts/check_productization_state.py`
  - pass.
- `uv run pytest tests/test_lockbox_shadow_automation_experiment_design.py tests/test_production_acceptance_manifest_contract.py tests/test_productization_state_index.py -v --tb=short`
  - 43 passed.
- `uv run ruff check scripts/check_production_acceptance_manifest.py tests/test_production_acceptance_manifest_contract.py tests/test_productization_state_index.py`
  - pass.
- `git diff --check`;
  - pass; only Git CRLF warnings.
- secret/local-path scan on changed docs/scripts/tests;
  - no matches.

## Control Plane Note

No control-plane tier or authority update is needed for Phase 2 because
maturity tier, active lane, matrix authority, selected area/counting behavior,
review/replay behavior, ProductWriter authority, and broad uncontracted
Backfill state did not change. The control-plane prose was updated only because
Phase 2 adds a public schema/checker surface.

## Next Actions

Next goal: Phase 3 QuantMatrixVersion Activation; do not start default quant
matrix writing without an expected-diff contract and focused output tests.
