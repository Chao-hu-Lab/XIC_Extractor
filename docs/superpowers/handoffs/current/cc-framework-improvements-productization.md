# XIC productization handoff

Updated: 2026-06-24
Branch: `codex/pr-artifact-retention-boundary-20260624`

This is the short current-state snapshot. Tier authority lives in
`docs/superpowers/plans/2026-06-15-productization-control-plane.md` plus the
machine-readable validation indexes.

## Current Objective

Phase 1 is closed: the lockbox shadow automation artifact is a shadow-only
contract adapter/checker, not a scorer run and not product writer authority.

Immediate operational objective: land the artifact-retention prerequisite before
resuming product PR merges. Default CI must not depend on ignored `output/` or
`local_validation_artifacts/`, and global ledger updates must be owned by a
prerequisite or final rollup PR rather than every stacked product PR.

Next productization phase after the stack boundary is stable: Phase 2,
`ProductionAcceptanceManifest v1`. Phase 2 must define the only future Backfill
`write_authority=true` decision artifact, still without writing the default
matrix until Phase 3 expected-diff activation exists.

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
- Future default `quant_matrix` should include detected plus accepted Backfill
  values.
- Detection claims remain based on `detected_count` only.
- `quant_available_count` is detected plus accepted Backfill.
- Production write authority must come from `ProductionAcceptanceManifest`
  keyed by `peak_hypothesis_id + sample_stem`.
- Shadow/report/gallery/candidate artifacts remain non-authority.

## Current State

- Current Backfill product authority remains exactly 511 cells.
- Broad Backfill auto-write remains parked.
- `4613` remains the candidate/audit universe, not a writable pool.
- `3015` trace-matched unresolved rows remain review/adjudication targets, not
  writer rows.
- `1087` missing-overlay rows remain evidence gaps, not negative truth.
- Lockbox/owner-clean evidence remains non-authoritative challenge evidence.
- Manual wrong-peak/no-peak controls remain negative controls.
- No ProductWriter, matrix, workbook, selected peak/area, counted detection,
  GUI, default extraction, authority manifest, or broad Backfill behavior
  changes are introduced by the PR-stack governance work.

## Current Lane State

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

These exact phrases are retained for `check_productization_state.py` anchors:

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

1. Land or base on the artifact-retention boundary prerequisite.
2. Rebuild PR88 as QuantMatrix foundation only.
3. Move discovery row identity hardening to its own PR or to the CID-NL
   discovery PR where the contract belongs.
4. Retarget PR89-PR92 one at a time.
5. Use a final rollup PR for broad productization ledgers and handoff updates.

## Rejected Paths

- Do not run or revive a scorer as productization authority.
- Do not create a second independent lockbox case manifest.
- Do not treat owner-clean challenge rows, AI challenge evidence, manual
  negative controls, missing-overlay rows, or summary scores as truth
  completion.
- Do not let shadow artifacts feed ProductWriter, matrix/workbook output,
  selected peak/area, counted detection, GUI, default extraction, reviewer slot
  2, or broad Backfill authority.
- Do not write accepted Backfill into the default matrix before Phase 2
  production acceptance manifest and Phase 3 expected-diff activation exist.

## Validation Snapshot

Most recent Phase 1 validation, before the PR-stack incident:

- `scripts/build_lockbox_shadow_automation_experiment_design.py --check-only`
  passed.
- Focused lockbox shadow automation tests passed.
- `tests/test_productization_state_index.py` passed.
- `scripts/check_productization_state.py` passed.
- Scoped ruff, `git diff --check`, and secret/local-path scans passed.

Current artifact-retention prerequisite evidence:

- `scripts/build_lockbox_static_review_bundle.py --check-only` passed.
- `scripts/import_lockbox_labels.py --check-only` passed.
- `scripts/build_lockbox_next_action_plan.py --check-only` passed.
- `scripts/build_lockbox_ai_challenge_pack.py --check-only` passed.
- `scripts/check_lockbox_ai_challenge_results.py` passed with 72 cases and zero
  owner-recheck flags.
- `scripts/build_lockbox_second_review_pack.py --check-only` passed.
- `scripts/build_lockbox_single_owner_ai_challenge_gate.py --check-only`
  passed.
- `scripts/build_lockbox_shadow_automation_experiment_design.py --check-only`
  passed after regenerating the shadow-only manifest from updated upstream
  artifact hashes.
- `scripts/check_validation_artifact_retention.py` passed with 108 retained
  validation files and no tracked rendered-artifact dependency. The checker now
  hard-fails tracked rendered HTML/PNG even if marked `shrink_later`, and
  validates retained file size/line metadata against the clean checkout.

Hook smoke, sandbox doctor, diff check, PR gate, and secret/local-path scan
remain required before closeout.

## Control Plane Note

No control-plane tier or authority update is needed for this governance work
because maturity tier, active lane, matrix authority, selected area/counting
behavior, review/replay behavior, ProductWriter authority, and broad
uncontracted Backfill state did not change.

## Next Actions

Immediate PR-stack action: create/land the artifact-retention prerequisite, then
rebuild or retarget PR88-PR92 so each PR has one owner surface and can pass CI
from a clean checkout of its base.

Next productization phase after the stack boundary is stable: Phase 2,
`ProductionAcceptanceManifest v1`; do not start default quant matrix activation
until Phase 3.
