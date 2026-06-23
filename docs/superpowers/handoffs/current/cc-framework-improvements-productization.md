# XIC productization handoff

Updated: 2026-06-24
Branch: `codex/pr03-quant-matrix-foundation`
Status: PR #88 rebuilt on `master`; local gates passed, GitHub CI/review pending.

This is a compact current-state snapshot. Tier authority lives in
`docs/superpowers/plans/2026-06-15-productization-control-plane.md` plus the
machine-readable validation indexes. Handoff text is routing context only.

## Current Objective

Phase 1 is closed: `lockbox_shadow_automation_experiment_v1` is a
shadow-only contract adapter/checker, not a scorer run and not product writer
authority.

Phase 2/3 QuantMatrix foundation is reintroduced on clean PR #88:

- `ProductionAcceptanceManifest v1` defines the accepted Backfill row authority
  artifact and fail-closed checker.
- `QuantMatrixVersion v1` is the manifest-driven activation surface for
  additive quant matrix outputs, gated by expected-diff checks.
- QuantMatrix review, promotion, downstream-impact, real-bundle, packet,
  dry-run, and closeout checks are product-evidence surfaces, not ProductWriter
  authority by themselves.
- `product_ready_default_matrix_activated` is the current 511-cell default
  QuantMatrix activation state and must remain tied to expected-diff and the
  authority manifest.

This rebuild must not create broad production rows, change selected
peak/area/counting, change review/replay behavior, or broaden Backfill
authority. Default CI must not depend on ignored `output/` or
`local_validation_artifacts/`.

## Active References

- Productization control plane:
  `docs/superpowers/plans/2026-06-15-productization-control-plane.md`
- Active roadmap:
  `docs/superpowers/plans/2026-06-19-backfill-quant-matrix-product-blueprint.md`
- Cleanup map:
  `docs/superpowers/notes/2026-06-19-backfill-quant-matrix-cleanup-map.md`
- PR stack incident note:
  `docs/superpowers/notes/2026-06-24-pr88-stack-artifact-boundary-retrospective.md`

## Product Direction

- Backfill values are accepted quantification values, not detections and not
  truth claims.
- Default `quant_matrix` includes detected plus accepted Backfill values only
  for the current 511-cell expected-diff-passing scope.
- Detection claims remain based on `detected_count` only.
- `quant_available_count` is detected plus accepted Backfill.
- Production write authority must come from `ProductionAcceptanceManifest`
  keyed by `peak_hypothesis_id + sample_stem`.
- Shadow/report/gallery/candidate artifacts remain non-authority.

## Current Lane State

- Current Backfill product authority remains exactly 511 cells.
- Broad Backfill auto-write remains parked.
- `4613` remains the candidate/audit universe, not a writable pool.
- `3015` trace-matched unresolved rows remain review/adjudication targets, not
  writer rows.
- `1087` missing-overlay rows remain evidence gaps, not negative truth.
- Lockbox/owner-clean evidence remains non-authoritative challenge evidence.
- Manual wrong-peak/no-peak controls remain negative controls.
- `peak_choice_truth_lockbox_v1` remains `production_candidate`.
- Mechanical adjudication, Review Packet / Approval Workflow v1,
  Missing-Overlay Evidence Recovery v1, and lockbox assets remain
  non-authority review/evidence infrastructure.
- Targeted MS1 shape identity limited rescue remains production-ready only for
  the explicit 5-hmdC + 5-medC headless workflow; GUI and broader targets remain
  blocked.
- `sample_metadata_v1` remains production-ready for no-output ordering.
- Roles/batch/matrix/exclusion must not alter quant output.
- ReviewAction selected-candidate switch and manual-boundary area recompute
  remain parked.
- Calibration/normalization activation remains classification and planning only.

## Status Index Anchors

These phrases are retained for `check_productization_state.py` anchors:

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

## PR Stack Interlock

Do not continue patching PR88 red checks one by one. Recovery order:

1. Base on the already-merged artifact-retention boundary prerequisite.
2. Rebuild PR #88 as QuantMatrix foundation only.
3. Move discovery row identity hardening to the CID-NL discovery PR.
4. Retarget PR #89-#92 one at a time after each predecessor is clean.
5. Use a final rollup PR only for unavoidable broad productization ledger and
   handoff updates.

## Rejected Paths

- Do not run or revive a scorer as productization authority.
- Do not create a second independent lockbox case manifest.
- Do not treat owner-clean challenge rows, AI challenge evidence, manual
  negative controls, missing-overlay rows, or summary scores as truth
  completion.
- Do not let shadow artifacts feed ProductWriter, matrix/workbook output,
  selected peak/area, counted detection, GUI, default extraction, reviewer slot
  2, or broad Backfill authority.
- Do not treat low detected support or high Backfill dependency as a standalone
  matrix-value blocker; they are prevalence/claim uncertainty flags.
- Do not expand default quant matrix output beyond the current 511-cell scope
  without a new authority manifest and expected-diff gate.

## Validation Snapshot

- PR #94 artifact-retention prerequisite passed local PR gate and GitHub CI
  before normal merge.
- PR #88 clean rebuild passed focused QuantMatrix checks, retention and
  productization checkers, bounded-lane checker, and the repo PR gate locally.
- Validation status for local rebuild is `production_ready` only for the bounded
  511-cell QuantMatrix default-output contract; GitHub CI/review must still pass
  before normal merge.

## Control Plane Note

The default QuantMatrix activation status-index change is paired with the
control-plane updates in this rebuild. No extra control-plane update is needed
for the handoff conflict resolution itself.

## Next Actions

Mark PR #88 ready, wait for GitHub CI/review, normal-merge only after green,
then handle #89-#92 sequentially with the same artifact-boundary discipline.
