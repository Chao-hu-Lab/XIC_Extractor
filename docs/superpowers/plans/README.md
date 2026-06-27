# Productization Plans

Status: routing index

This directory contains a mix of active control-plane documents, current
blueprints, completed implementation plans, and historical provenance. A dated
plan is not active by default.

## Active Reading Order

1. `2026-06-15-productization-control-plane.md` for tier, active lane, writer
   authority, and current broad uncontracted Backfill parked state.
2. The branch-specific current handoff named by the goal or PR workflow for
   continuation state. Use
   `../productization/status/cc-framework-improvements-productization.md` only when
   working on that productization status-anchor branch.
3. `2026-06-19-backfill-quant-matrix-product-blueprint.md` for Backfill /
   quant-matrix phase execution.
4. Older dated plans only when the active goal names them as provenance.

## Current Backfill Direction

Backfill values are accepted quantification values, not detections and not truth
claims. The future default quant matrix should include detected plus accepted
Backfill values. Production write authority must come from a
`ProductionAcceptanceManifest`; shadow, report, gallery, and candidate artifacts
remain non-authority. Old plans that discuss broad promotion, sidecar-driven
promotion, or productization gates are historical unless explicitly reactivated.

## Rule

Do not treat old implementation checklists as open work. First check the control
plane and current handoff; then create a fresh goal for any reactivation.
