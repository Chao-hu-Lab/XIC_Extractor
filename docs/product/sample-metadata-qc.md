# Sample Metadata And QC

Document status: product-topic source-of-truth summary.
Evidence label: `diagnostic_only` for this documentation-governance patch; this
page does not change extraction values, QC values, alignment values,
normalization, counted detections, workbook output, or matrix values.

Sample metadata and QC describe sample identity, injection order, roles,
batches, exclusions, and instrument/QC context. They are public behavior
surfaces because they can affect ordering, grouping, review interpretation, and
future activation gates.

## Answers

Use this page to answer:

- What `sample_metadata_v1` may safely own today.
- Which role-aware behavior is still blocked from changing product values.
- How QC sidecars relate to product authority.
- Which historical QC/calibration notes can become private after stable claims
  are represented.

## Does Not Answer

This page does not decide:

- A specific sample's role, exclusion, or correction.
- Normalization/calibration activation policy.
- ProductWriter authority or matrix activation scope.
- Current productization tier for sample metadata beyond the owning status
  index/control plane.

## Current Contract

- Sample metadata may act as an injection-order and sample-identity projection
  surface when it preserves existing output values.
- `sample_metadata_v1` is production-ready only for no-output-change sample
  identity, injection-order projection, and lookup parity.
- Role, batch, matrix type, exclusion, calibrator, blank, QC, or normalization
  behavior must not alter extraction, QC, alignment, counted, workbook, or
  matrix values without an explicit activation/export contract.
- Instrument-QC and calibration sidecars are evidence and observability
  surfaces unless promoted through productization authority.
- Sample metadata is part of run provenance, but it does not replace method
  manifests or output schemas.

## Public Surfaces

| Surface | Role |
| --- | --- |
| `sample_metadata_v1` CSV/TSV | Shared sample identity, order, role, batch, matrix, group, exclusion schema |
| `injection_order_source` | Current no-value-change ordering projection |
| Instrument-QC sidecars | QC context and trend evidence |
| Calibration/normalization previews | Shadow or gated evidence surfaces |
| Run metadata / method manifest | Provenance links to sample metadata inputs |

## Workflow

1. A run may provide sample metadata with identity, raw stem, injection order,
   role, batch, and exclusion fields.
2. Current safe use projects injection order or sample-column lookup without
   changing values.
3. QC/calibration/normalization features may consume metadata as evidence.
4. Any value-changing role behavior requires a separate activation contract and
   expected-diff review.

## Verification Gates

Before changing sample metadata or QC behavior, require the relevant subset of:

- schema validation tests for metadata fields and role values;
- parity tests proving no value change when metadata is only an order/lookup
  source;
- expected-diff packet for any role-aware value behavior;
- downstream matrix/workbook tests if outputs can change;
- productization owner update when activation authority changes.

## Common Wrong Moves

- Treating sample roles as value-changing policy before activation.
- Using exclusions to silently remove product rows or cells.
- Treating QC sidecars or calibration previews as matrix authority.
- Hiding sample identity or batch assumptions only in private notes.

## Source Owners

- [`docs/superpowers/specs/2026-06-15-sample-metadata-contract-v1-spec.md`](../superpowers/specs/2026-06-15-sample-metadata-contract-v1-spec.md)
- [`docs/product/run-provenance.md`](run-provenance.md)
- [`docs/product/productization.md`](productization.md)
- [`docs/agent/product-validation-contract.md`](../agent/product-validation-contract.md)
- [`docs/superpowers/validation/productization_status_index_v1.tsv`](../superpowers/validation/productization_status_index_v1.tsv)

## Cleanup Rule

QC trend notes, calibration experiments, and sample-role debates can move to
private notes after the durable schema, safe-current-use boundary, and
activation gates are represented here or in the productization owners.

## When To Update

Update this page when sample metadata gains a new public field, role, allowed
consumer, QC sidecar, calibration gate, or value-changing activation policy.
