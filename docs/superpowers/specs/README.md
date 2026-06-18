# Productization Specs

Status: routing index

Specs define contracts, background, or historical designs. They are not
automatic implementation goals.

## Active Reading Order

1. Control plane for authority and maturity state.
2. Current handoff for continuation state.
3. Current roadmap/blueprint for phase order.
4. The specific spec named by the active goal.

## Current Public Schemas

- `production_acceptance_manifest_schema.v1.json`: Phase 2 Backfill
  `ProductionAcceptanceManifest v1` contract. This defines/checks the only
  future Backfill row artifact that may grant `write_authority=true`; it does
  not activate ProductWriter or the default quant matrix.

## Rule

If a spec conflicts with the control plane, current handoff, or current
Backfill quant-matrix product blueprint, stop and resolve the conflict instead
of silently following the older spec.
