# Quant Matrix

Document status: product-topic source-of-truth summary.
Evidence label: `diagnostic_only` for this documentation-governance patch; this
page does not change ProductWriter defaults, workbook output, selected peak,
selected area, counted detection, or matrix authority.

The quant matrix is the product-facing numeric matrix contract. It must separate
detected values, accepted Backfill quantification values, provenance sidecars,
review surfaces, and writer authority.

## Answers

Use this page to answer:

- What belongs in the primary product matrix versus sidecars.
- Why accepted Backfill values are quantification values, not detections or
  truth claims.
- Which artifacts can grant matrix-writing authority.
- Which older matrix/spec notes can become private history after stable claims
  are preserved.

## Does Not Answer

This page does not decide:

- Current accepted Backfill cell set.
- Current maturity tier or active productization lane.
- Whether a future activation packet is accepted.
- Per-row scientific confidence for unresolved Backfill candidates.

## Current Contract

- The primary matrix should expose numeric product values and stable user-facing
  row/sample structure, not diagnostic evidence columns.
- Detected values and accepted Backfill values are different product states.
  Accepted Backfill values may enter a quant matrix only through explicit
  authority and provenance.
- `ProductionAcceptanceManifest` is the authority boundary for accepted Backfill
  values. Candidate sidecars, review packets, galleries, lockbox labels, and
  diagnostics do not grant authority by themselves.
- `QuantMatrixVersion` and default activation artifacts are activation surfaces,
  not proof that broad Backfill is generally production-ready.
- Approved activation packets may write a versioned matrix bundle without
  re-reading or rewriting the full `alignment_cells.tsv` ledger only when the
  productization status index and authority manifest define the exact accepted
  scope. The full ledger remains the audit/debug source for full activation and
  evidence projection, not the only legal input to a bounded default-matrix
  activation.
- Matrix-only activation still needs explicit provenance and replay artifacts:
  acceptance manifest or expected-diff packet, `QuantMatrixVersion`, cell
  provenance, row/source summary, value-delta record, and application summary.
  These artifacts must prove the written values and their source scope without
  confusing accepted Backfill values with primary detected values.
- Identity, row-basis, source, evidence, and review details belong in sidecars
  or review reports unless an explicit public schema says otherwise.
- Historical AsLS primary-matrix policy is superseded for current final area
  ownership by LC-MS/MS evidence rules and morphology-aware area policy. Keep it
  as historical evidence until exact referrers are stubbed or retargeted.
- Row-completion confidence and downstream-impact benchmarks are review and
  readiness evidence; they do not change default matrix authority without a
  separate activation decision.

## Public Surfaces

| Surface | Role |
| --- | --- |
| `alignment_matrix.tsv` / workbook `Matrix` | Primary product-facing numeric matrix |
| `cell_provenance.tsv` | Cell-level provenance for accepted matrix values |
| `row_summary.tsv` | Matrix row identity and summary sidecar |
| `expected_diff_summary` | Review gate for behavior-changing activation |
| `ProductionAcceptanceManifest` | Accepted Backfill authority record |
| `QuantMatrixVersion` | Versioned activation bundle |
| Productization status index and authority manifest | Current state and writer scope |

## Workflow

1. Detection, alignment, or Backfill surfaces produce candidate values and
   evidence.
2. Product authority decides which Backfill values are accepted.
3. A versioned activation bundle writes matrix values plus provenance sidecars.
4. Review/readiness artifacts explain what changed and what remains blocked.
5. Default product activation remains a separate explicit step.

## Verification Gates

Before changing matrix behavior, require the relevant subset of:

- expected-diff packet for changed values or schema;
- focused output tests for matrix, provenance, row summary, and source summary;
- productization state and authority checker pass;
- downstream-impact smoke when downstream consumers depend on the matrix;
- heldout/manual/oracle evidence when making production-readiness claims.

## Common Wrong Moves

- Treating candidate Backfill rows as accepted matrix values.
- Treating review-only labels or diagnostic sidecars as writer authority.
- Adding diagnostic evidence columns to the primary matrix.
- Treating historical AsLS-vs-raw policy as current area authority.
- Claiming `production_ready` from contract fixtures or 8RAW smoke alone.
- Updating topic prose while leaving status index or authority manifest stale
  after a real authority change.

## Source Owners

- [`docs/product/backfill.md`](backfill.md)
- [`docs/product/alignment.md`](alignment.md)
- [`docs/product/productization.md`](productization.md)
- [`docs/superpowers/plans/2026-06-15-productization-control-plane.md`](../superpowers/plans/2026-06-15-productization-control-plane.md)
- [`docs/superpowers/plans/2026-06-19-backfill-quant-matrix-product-blueprint.md`](../superpowers/plans/2026-06-19-backfill-quant-matrix-product-blueprint.md)
- [`docs/superpowers/validation/productization_status_index_v1.tsv`](../superpowers/validation/productization_status_index_v1.tsv)
- [`docs/superpowers/specs/productization_authority_manifest.v1.json`](../superpowers/specs/productization_authority_manifest.v1.json)
- [`docs/superpowers/specs/2026-05-30-sidecar-to-product-label-activation-contract.md`](../superpowers/specs/2026-05-30-sidecar-to-product-label-activation-contract.md)
- [`docs/superpowers/specs/2026-06-03-full-untarget-peak-hypothesis-final-matrix-contract.md`](../superpowers/specs/2026-06-03-full-untarget-peak-hypothesis-final-matrix-contract.md)

## Cleanup Rule

Long matrix activation plans and dated final-matrix debates can move to private
notes after the durable matrix authority, primary-surface, sidecar, and
expected-diff rules are represented here or in the machine-readable authority
owners.

## When To Update

Update this page when the primary matrix surface, matrix sidecars, activation
bundle, authority boundary, or downstream-impact gate changes.
