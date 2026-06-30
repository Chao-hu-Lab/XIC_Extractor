# Productization Goals

Doc placement: repo_support_doc
Doc kind: goal
Doc lifecycle: active
Repo owner: docs/product/productization.md
Doc exit rule: Update when productization goal routing changes or this directory no longer carries active goal indexes.

Status: routing index

Use this directory for executable, phase-sized goal contracts. A dated goal file
is not active just because it is in this directory.

## Active Reading Order

1. `docs/superpowers/plans/2026-06-15-productization-control-plane.md`
2. Productization status anchor:
   `docs/superpowers/productization/status/cc-framework-improvements-productization.md`
   only when working on the productization status-anchor workflow; otherwise
   use the branch-scoped current handoff named by the active goal or PR workflow.
3. `docs/superpowers/goals/XIC_Extractor_Productization_Roadmap_Review.md`
4. `docs/product/backfill.md`, `docs/product/quant-matrix.md`, and the current
   branch handoff for Backfill/quant-matrix work. The old Backfill
   quant-matrix blueprint has been retired to Obsidian and is no longer a repo
   execution surface.
5. The spec explicitly named by the current goal.

## Active Goal Surface

- `XIC_Extractor_Productization_Roadmap_Review.md` is the current Backfill /
  quant-matrix roadmap.
- The June 2026 Backfill evidence-reconciliation goal is historical
  diagnostic/gallery provenance and is superseded for future Backfill roadmap
  execution.

## Rule

Do not execute an old dated goal as current productization direction unless the
control plane, the productization status anchor, the active branch handoff, or
the user explicitly reactivates it.
