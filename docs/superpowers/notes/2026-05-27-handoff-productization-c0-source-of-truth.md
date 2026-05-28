# Handoff Productization C0 Source Of Truth

**Date:** 2026-05-27
**Status:** `handoff_spine_scaffold_ready` / `shadow_ready`; scaffold and
contract only, not product behavior readiness

**Current source of truth:** This note is the historical C0 scaffold rationale.
Current handoff productization status, legacy retirement readiness, and the next
PR direction are owned by
`docs/superpowers/notes/2026-05-28-handoff-productization-phase-closeout.md`.

**Inputs:**

- `C:\Users\user\Downloads\lcms_gcms_peak_pipeline_handoff.md`
- `2026-05-26-phase1-phase2-independent-critique-note.md`
- `2026-05-26-phase1-phase2-design-correction-note.md`
- `2026-05-27-asls-minimal-closeout-note.md`

## Current Product Direction

This repo should move toward an explainable LC-MS/MS RAW trace evidence engine:

```text
TraceGroup -> PeakHypothesis -> EvidenceVector -> IntegrationResult
  -> AuditTrail -> downstream matrix
```

The product value is not a larger report surface or another one-off resolver. It
is a stable hypothesis/evidence/audit spine that can support targeted first, then
untargeted, while preserving the current output contracts until a separate
behavior spec approves a production change.

The downstream delivery surface for correction and statistics is
`alignment_matrix.tsv`. Human-facing HTML/XLSX reports may summarize decisions,
but they are not the primary downstream machine contract.

## Projection And Schema Contracts

`peak_candidates.tsv` is a schema-frozen debug/audit TSV projection of selected
`TraceGroup -> PeakHypothesis -> EvidenceVector -> IntegrationResult ->
AuditTrail` fields into the existing candidate-table columns.

It is not:

- the canonical domain model;
- a production quantitative matrix;
- a new downstream handoff contract.

The current `peak_candidates.tsv` schema source of truth is
`xic_extractor.extraction.peak_candidate_table.PEAK_CANDIDATE_HEADERS`. Emitted
order is writer-defined and must be pinned by tests. Older v1 specs remain
historical rationale and constraints; they are not the complete current header
manifest.

Step 1 must not add a TSV column, version column, metadata row, emitted sidecar,
or schema migration. If a future machine-readable manifest is needed, it should
be planned separately and should not silently change emitted artifacts.

## What This Step Closes

This C0 step closes only the scaffold contract:

- docs now distinguish historical checklist inventory from current planning
  source of truth;
- one synthetic targeted path proves the current spine can carry
  `TraceGroup -> PeakHypothesis -> EvidenceVector -> IntegrationResult ->
  AuditTrail` into the existing `peak_candidates.tsv` projection;
- candidate and boundary TSV projections now expose explicit
  `*_from_hypotheses` builders so future migrated consumers can bypass legacy
  `PeakCandidate` / `PeakDetectionResult` row projection;
- writer tests pin full header order, extra-key exclusion, and blank defaults for
  missing known columns;
- no production selection, resolver, baseline, matrix, or real-data output
  behavior changes.

This does not close:

- true multi-source hypothesis enumeration;
- production model selection;
- linear-edge retirement;
- AsLS absolute baseline truth;
- untargeted consumer migration.

## First Consumer Migration Target

The first concrete consumer migration target is
`xic_extractor/extraction/peak_candidate_boundaries.py` because it is an audit TSV
surface and can move without changing production selection or matrix behavior.
This branch migrates boundary row projection to consume `PeakHypothesis` while
leaving the public `build_peak_candidate_boundary_rows(...)` entry point
compatible with existing callers.

The lower-level boundary enumerator now accepts a minimal
`BoundaryCandidateContext` so legacy `PeakCandidate` callers can continue to
work while migrated consumers pass hypothesis-derived context.

Parity surface:

- `peak_candidates.tsv` header/order unchanged;
- `peak_candidate_boundaries.tsv` header/order unchanged;
- synthetic boundary tests unchanged except for import/model wiring;
- focused 8RAW validation only if the migration touches emitted boundary rows in
  a way not covered by synthetic tests.

Rollback condition:

- if a field on `peak_candidate_boundaries.tsv` cannot be expressed through
  `PeakHypothesis`, `EvidenceVector`, `IntegrationResult`, or `AuditTrail`
  without semantic loss, stop and add the missing field or mapping contract
  first; do not revive a legacy model just for the writer.

Next consumer migrations should follow the same rule: migrate one reader at a
time, pin public TSV parity, and stop when the target requires a semantic field
the spine cannot yet express.

## Current Milestone Status

This table is preserved as the C0 scaffold snapshot. For the current phase
closeout and legacy retirement decision, use
`2026-05-28-handoff-productization-phase-closeout.md`.

| Milestone | Current status |
|---|---|
| M1 TraceGroup wrapper | Minimal wrapper exists for targeted/audit paths; not a universal engine |
| M2 Multi-source hypothesis enumeration | Partial audit-only boundary hypotheses exist |
| M3 EvidenceVector schema freeze | Partial targeted adapter exists; schema is not yet authoritative |
| M4 Model selection criterion | WIS/region logic is audit/helper context, not production selection |
| M5 End-to-end AuditTrail case | One synthetic targeted scaffold path, explicit candidate/boundary projection builders, and one boundary-audit consumer migration are contract-tested; not productized |
