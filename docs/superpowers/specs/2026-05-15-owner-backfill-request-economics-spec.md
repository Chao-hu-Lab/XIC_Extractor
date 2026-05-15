# Owner Backfill Request Economics Spec

**Status:** Phase A diagnostic implemented first.
**Date:** 2026-05-15
**Branch:** `codex/owner-backfill-request-economics`

## Context

After the owner-clustering Tier 0 fix, `alignment.cluster_owners` is no longer
the dominant 85-RAW multi-tag stage. The next measured bottleneck is
`alignment.owner_backfill`, which is dominated by RAW XIC extraction I/O.

Do not change backfill gates or switch backend defaults before measuring which
request classes consume the work.

## Phase A: Request Economics Diagnostic

Add an offline diagnostic:

```text
alignment_review.tsv + alignment_cells.tsv
  -> reconstruct owner-backfill request target classes
  -> group by final identity_decision, primary-matrix inclusion, tag, and outcome
  -> report where request cost is production-critical vs provisional/audit cost
```

Outputs:

- `owner_backfill_request_economics_summary.tsv`
- `owner_backfill_request_economics_features.tsv`
- `owner_backfill_request_economics.json`
- `owner_backfill_request_economics.md`

The diagnostic estimates request targets from final artifacts. It is not a
replacement for pipeline timing; it is the first pass that answers where
backfill effort lands after final identity decisions.

## Interpretation

- High production request cost means backfill is still product-critical.
- High non-primary or provisional/audit request cost means the next optimization
  should consider staged or optional audit backfill.
- High absent-target count with low rescued-target count suggests a candidate
  gate may be wasting RAW I/O.
- Pre-backfill consolidated rows estimate two seed centers because production
  currently caps preserved seed centers at two.

## Stop Conditions

Stop before changing production gates if:

- request cost is mostly production matrix work;
- the diagnostic depends on missing `alignment_cells.tsv`;
- the dominant cost cannot be tied to final identity tiers or tags.

## Phase B: Exact-Safe Detected Owner Confirmation Gate

The 85RAW multi-tag diagnostic showed production work dominates current
owner-backfill cost:

- `request_target_count`: 94,593 before the confirmation gate estimate.
- `production_request_target_count`: 87,556.
- `non_primary_request_target_count`: 7,037.

Therefore delaying provisional/audit backfill alone is not the main lever.

For pre-backfill consolidated families, the existing Matrix writer only lets a
backfilled trace supersede a detected local owner when the local owner is
already area-weak relative to the family median. Move that existing necessary
condition ahead of RAW extraction:

```text
if detected owner area > median detected owner area * 0.25:
    skip detected-owner confirmation backfill
```

This does not change the supersede threshold. It only avoids XIC extraction for
detected owners that cannot change the final cell under the current Matrix
contract. Missing-sample rescue remains unchanged.

Validation evidence:

- 8RAW multi-tag Matrix/Review/Cells TSV hashes match the pre-gate output.
- 85RAW multi-tag Matrix/Review/Cells TSV hashes match the pre-gate output.
- 85RAW strict ISTD benchmark remains unchanged: only the known targeted-side
  `d3-N6-medA` `AREA_MISMATCH` fails.
- Post-gate 85RAW request economics:
  - `request_target_count`: 86,234.
  - `request_extract_count_estimate`: 120,970.
  - `confirmation_target_count`: 492.
  - `production_request_target_count`: 79,341.

The gate removes most detected-owner confirmation requests while preserving
primary-matrix output equivalence on the real 8RAW and 85RAW validations.

## Phase C: Exact Duplicate Request De-Duplication

Within a single sample, identical `XICRequest` objects can safely share one RAW
trace. The runtime now de-duplicates exact request objects before calling
`extract_xic_many`, then fans the trace back out to the original feature/sample
request order.

This is intentionally narrow:

- only exact same `mz`, `rt_min`, `rt_max`, and `ppm_tol` are shared;
- output order and feature/sample assignment are preserved;
- no approximate m/z or RT merging is introduced.

Validation evidence:

- 8RAW multi-tag Matrix/Review/Cells TSV hashes match the previous output.
- 85RAW multi-tag Matrix/Review/Cells TSV hashes match the previous output.
- 85RAW strict ISTD benchmark remains unchanged: only the known targeted-side
  `d3-N6-medA` `AREA_MISMATCH` fails.
- 85RAW owner_backfill time changed from `550.03s` to `545.36s`.

Conclusion: this is worth keeping as an exact-safe cleanup, but it is not the
main performance lever.
