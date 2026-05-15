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
