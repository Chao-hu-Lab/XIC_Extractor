# XIC productization handoff

Updated: 2026-06-19
Branch: `cc/framework-improvements`
Latest committed checkpoint: `224a93cb Add lockbox shadow automation design`
Active working-tree checkpoint: Phase 1 Shadow Scoring Contract Adapter v1

This is the short current-state snapshot. Tier authority lives in
`docs/superpowers/plans/2026-06-15-productization-control-plane.md` plus the
machine-readable validation indexes.

## Current Objective

Phase 1 is implemented: the lockbox shadow automation artifact is now a
shadow-only contract adapter/checker, not a scorer run and not product writer
authority.

Next executable productization phase is Phase 2:
`ProductionAcceptanceManifest v1`. Phase 2 must define the only future
Backfill `write_authority=true` decision artifact, still without writing the
default matrix until Phase 3 expected-diff activation exists.

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
  GUI, default extraction, authority manifest, or broad Backfill behavior
  changed in Phase 1.

## Phase 1 Result

Updated artifact:
`docs/superpowers/validation/lockbox_shadow_automation_experiment_v1.json`.

Updated source manifest:
`docs/superpowers/validation/lockbox_shadow_automation_cases_v1.tsv`.

The single 72-case manifest now carries:

- `shadow_decision={accept,flag,reject,not_scored}`;
- truth/status enum with owner-clean as `not_truth_claimed` and
  `non_authoritative_challenge`;
- manual negative controls as `reject` hard stops;
- row-level doublet status, reference side, allowed flag, and source;
- source paths/hashes and manifest sha in the JSON summary;
- `shadow_only=true`, `write_authority=false`, and
  `matrix_write_allowed=false`;
- `may_satisfy_reviewer_slot2=false`;
- `single_owner_evidence_is_truth_completion=false`.

`lockbox_shadow_automation_experiment_v1` remains a shadow-only public surface.
It does not feed ProductWriter, matrix/workbook output, selected peak/area,
counted detection, GUI, default extraction, reviewer slot 2, or broad Backfill
authority.

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
- manual-boundary area recompute remain parked.
- calibration/normalization activation remains classification and planning only.
- GUI and broader targets remain blocked.

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
- Do not write accepted Backfill into the default matrix before Phase 2
  production acceptance manifest and Phase 3 expected-diff activation exist.

## Files Changed In Phase 1

- `scripts/build_lockbox_shadow_automation_experiment_design.py`
  - upgraded the existing builder/checker to a Phase 1 shadow contract adapter.
- `docs/superpowers/validation/lockbox_shadow_automation_cases_v1.tsv`
  - same 72-case source manifest, enriched with shadow/truth/doublet/authority
    contract fields.
- `docs/superpowers/validation/lockbox_shadow_automation_experiment_v1.json`
  - updated decision, source/hash/manifest-sha, enum, and authority contract.
- `tests/test_lockbox_shadow_automation_experiment_design.py`
  - added focused checker tests for hard stops and authority invariants.
- `docs/superpowers/validation/productization_status_index_v1.tsv` and
  `tests/test_productization_state_index.py`
  - synchronized artifact hash, non-authority status-index wording, and
    control-plane freshness assertion.
- `docs/superpowers/validation/lockbox_label_readme_v1.md`
  - updated the plain-language lockbox shadow contract description.
- `docs/superpowers/plans/2026-06-15-productization-control-plane.md`
  - refreshed lockbox wording to Phase 1 contract-adapter status and Phase 2
    `ProductionAcceptanceManifest v1` next checkpoint without changing tier or
    authority.
- `docs/superpowers/notes/2026-06-19-backfill-quant-matrix-cleanup-map.md` and
  `docs/superpowers/goals/XIC_Extractor_Productization_Roadmap_Review.md`
  - marked Phase 1 adapter work as complete/current and removed stale
    future-Phase-1 wording.
- `docs/superpowers/handoffs/current/cc-framework-improvements-productization.md`
  - pruned to this current-state snapshot.

Phase 0 blueprint/routing docs remain dirty in the working tree from the
previous reset and are still part of the same productization direction update.
User-provided deepresearch inputs remain unmodified.

## Validation Status

Latest completed checks:

- `uv run python scripts/build_lockbox_shadow_automation_experiment_design.py --check-only`
  - pass.
- `uv run pytest tests/test_lockbox_shadow_automation_experiment_design.py -v --tb=short`
  - 14 passed.
- `uv run pytest tests/test_lockbox_shadow_automation_experiment_design.py -k "manual_negative_accept or blocked_doublet or owner_clean_truth_completion or missing_source_hashes" -v --tb=short`
  - 4 passed, 9 deselected.
- `uv run pytest tests/test_productization_state_index.py -v --tb=short`
  - 10 passed.
- `uv run pytest tests/test_lockbox_shadow_automation_experiment_design.py tests/test_productization_state_index.py -v --tb=short`
  - 25 passed.
- `uv run python scripts/check_productization_state.py`
  - pass after productization status index hash update.
- `uv run ruff check scripts/build_lockbox_shadow_automation_experiment_design.py tests/test_lockbox_shadow_automation_experiment_design.py tests/test_productization_state_index.py`
  - pass.
- `uv run python scripts/check_productization_state.py`;
  - pass after handoff rewrite.
- `git diff --check`;
  - pass; only Git CRLF warnings.
- secret/local-path scan on changed docs/scripts/tests;
  - no matches.

## Control Plane Note

No control-plane tier or authority update is needed for Phase 1 because
maturity tier, active lane, matrix authority, selected area/counting behavior,
review/replay behavior, ProductWriter authority, and broad uncontracted
Backfill state did not change. The control-plane prose was refreshed only to
remove stale scorer wording and point the next checkpoint to Phase 2.

## Next Actions

1. Close Phase 1 as `shadow_ready`.
2. Next goal should be Phase 2, `ProductionAcceptanceManifest v1`; do not start
   default quant matrix activation until Phase 3.
