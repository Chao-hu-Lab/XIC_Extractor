# Sample Metadata and QC

Sample metadata and QC describe sample identity, injection order, roles,
batches, exclusions, and instrument/QC context. They are public behavior
surfaces because they affect ordering, grouping, review interpretation, and
future activation gates.

## Contract

- `sample_metadata_v1` is production-ready only for no-output-change sample
  identity, injection-order projection, and lookup parity.
- Sample metadata may act as an injection-order and sample-identity
  projection surface when it preserves existing output values.
- Role, batch, matrix type, exclusion, calibrator, blank, QC, or
  normalization behavior must not alter extraction, QC, alignment, counted,
  workbook, or matrix values without an explicit activation/export contract.
- Instrument-QC and calibration sidecars are evidence and observability
  surfaces unless promoted through productization authority.
- Sample metadata is part of run provenance but does not replace method
  manifests or output schemas.

## Surfaces

| Surface | Role |
| --- | --- |
| `sample_metadata_v1` CSV/TSV | Shared sample identity, order, role, batch, matrix, group, exclusion schema |
| `injection_order_source` | Current no-value-change ordering projection |
| Instrument-QC sidecars | QC context and trend evidence |
| Calibration/normalization previews | Shadow or gated evidence surfaces |
| Run metadata / method manifest | Provenance links to sample metadata inputs |

## Boundaries

- Owns: sample identity schema, injection-order projection, role/batch/
  exclusion field definitions, and QC sidecar structure.
- Does not own: a specific sample's role or exclusion decision,
  normalization/calibration activation policy, or matrix activation scope.
- Any value-changing role behavior requires a separate activation contract
  and expected-diff review.

## Verification

- Schema validation tests for metadata fields and role values.
- Parity tests proving no value change when metadata is only an
  order/lookup source.
- Expected-diff packet for any role-aware value behavior.
- Downstream matrix/workbook tests if outputs can change.

## Pitfalls

- Treating sample roles as value-changing policy before activation.
- Using exclusions to silently remove product rows or cells.
- Treating QC sidecars or calibration previews as matrix authority.
- Hiding sample identity or batch assumptions only in private notes.

## See Also

- [Sample metadata contract v1 spec](../superpowers/specs/2026-06-15-sample-metadata-contract-v1-spec.md)
- [Run provenance](run-provenance.md)
- [Productization](productization.md)
- [Product validation contract](../agent/product-validation-contract.md)
- [Productization status index](../superpowers/validation/productization_status_index_v1.tsv)
