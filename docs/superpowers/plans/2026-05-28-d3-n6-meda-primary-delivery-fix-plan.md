# d3-N6-medA Primary Delivery Fix Plan

**Date:** 2026-05-28
**Status:** superseded, do not execute as implementation plan

## Supersession

The earlier draft proposed relaxing `weak_seed_backfill_dependency` into a
warning for all rows with primary evidence and at least three detected
identity-support cells. Review found this is too broad: the current 8RAW
artifact has 25 rows matching that pattern, not only `FAM000264`.

Do not implement a broad weak-seed relaxation from this file.

The durable diagnostic memory and rerun policy now live in:

- `docs/diagnostic-ledger.md`

The replacement behavior attempt was folded into the Product Priority Reset
Phase 1 implementation plan after current row evidence showed a primary delivery
blocker. Post-implementation review hardened the trusted-seed contract and
converted the gate outcome to NO-GO rather than accepting the promotion.

## Current Decision

`d3-N6-medA` is already known as a severe RT-drift / same-surface-explained case.
The current `NO_GO` is not caused by standalone RT drift or area mismatch. The
remaining product blocker is primary delivery / ownership-consolidation:

- `FAM000264` is the plausible consolidated `d3-N6-medA` delivery family in the
  current 8RAW run.
- It is excluded from `alignment_matrix.tsv` because
  `identity_reason=weak_seed_backfill_dependency`.
- A future production change must keep collateral promotions explicit and must
  not hide false-positive pressure.

## Required Replacement Plan Shape

Before touching production code, write a new narrow plan that:

1. Reads `docs/diagnostic-ledger.md`.
2. States why the current change affects primary delivery / ownership-
   consolidation rather than re-proving RT drift.
3. Lists every row newly promoted by the proposed rule in a pre/post 8RAW
   collateral table.
4. Keeps `extreme_backfill_dependency` blocked.
5. Preserves machine-readable warning status for any accepted weak-seed row.
6. Runs focused unit tests plus 8RAW validation-minimal only.
7. Does not run 85RAW until 8RAW primary delivery is `GO` and a reviewed
   validation plan says 85RAW can change the decision.
