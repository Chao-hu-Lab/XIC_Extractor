# XIC productization handoff

Updated: 2026-06-24
Branch: `codex/pr04-cid-nl-rebuild-20260624`
Status: PR #88, #93, and #94 are merged on `master`; old PR #89 was closed as
superseded; replacement PR #95 is the clean CID-NL discovery activation slice
rebuilt from `origin/master`.

This is a compact current-state snapshot. Tier authority lives in
`docs/superpowers/plans/2026-06-15-productization-control-plane.md` and the
machine-readable validation indexes. Handoff text is routing context only.

## Current Objective

Rebuild and retarget #89-#92 one at a time so each PR can be reviewed and
tested from a clean base without depending on ignored `output/` or
`local_validation_artifacts/`.

Current #95 scope is CID-NL discovery activation only:

- The immediate product direction is Discovery first.
- accepted_discovery_cell_count=95.
- keep Discovery precursor inference, candidate row identity, and alignment
  replay fail-closed behavior;
- keep CID-NL feature-inclusion/default-activation/release/85RAW closure gates;
- exclude old QuantMatrix commits already represented by #88;
- exclude artifact-retention cleanup already represented by #94;
- exclude `.codex/skills` packaging, broad lockbox drift, and `output/`
  deletions from #95.

## Product State

- `product_ready_default_matrix_activated` remains the current default
  QuantMatrix state for the bounded 511-cell Backfill authority from #88.
- CID-NL default product activation v1 is the #95 candidate authority slice for
  the explicit 95-cell CID-NL activation contract.
- Broad Backfill auto-write remains parked.
- CID-NL discovery row-identity evidence is being promoted through explicit
  gates; Discovery/MS2 evidence must not directly become ProductWriter authority
  outside the activation contract.
- Shadow/report/gallery/candidate artifacts remain non-authority unless a
  product activation checker binds them into the current authority manifest.

## Boundaries

- No selected peak, selected area, counted-detection, workbook schema, GUI,
  broad Backfill, or unrelated default extraction behavior changes are allowed
  in #95.
- Default CI must stay hermetic and must not require ignored local artifacts.
- Do not reopen broad Backfill while the active goal is Discovery productization.
- PR #90, #91, and #92 wait until their predecessor is merged or cleanly
  retargeted to the updated `master`.

## Required Gates

Before #95 is ready:

- CID-NL/discovery focused tests and productization checkers must pass locally.
- The repo PR gate must pass locally unless a clear external blocker is recorded.
- GitHub CI must be green and review must be clear before normal merge.
- Any CI red must be diagnosed from logs before code changes.
- CID-NL Discovery full-scope classification v1.
- CID-NL 85RAW Universe Closure v1.

## Status Index Anchors

These phrases are retained for `scripts/check_productization_state.py`:

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

## Next Actions

1. Finish #95 CI/review remediation without changing tier or authority scope.
2. Rerun focused CID-NL gates, then full local PR gate.
3. Update #95 body with final verification and mark ready only after CI/review
   are clear.
4. Normal-merge #95 only after CI and review pass, then repeat for #90-#92.
