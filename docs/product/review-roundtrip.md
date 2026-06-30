# Review Roundtrip

Review roundtrip is the path from machine-produced review worklists to typed
human actions, dry-run application plans, expected-diff review, and only then
approved product changes.

## Contract

- Review queues, candidate tables, lockbox packets, and labels are review
  evidence. They do not change product outputs by themselves.
- Typed review actions must be validated and planned before any mutation.
  Apply steps require stable identifiers, recompute rules, sidecar contracts,
  and approved expected-diff evidence.
- Current review-action support is limited to identity verification and
  candidate-sidecar planning. Selected-candidate switching and
  manual-boundary area recomputation are parked until stable IDs, recompute
  rules, and expected-diff apply contracts exist.
- Peak-choice truth labels are separate from product authority. They can
  inform future automation only through a later goal with authority and
  expected-diff gates.
- Lockbox labels and shadow scoring are evidence acquisition only. They do
  not change selected peak, selected area, counted detection, workbook
  output, matrix values, or GUI behavior.
- Reviewer rationale and dispute discussion are private notes unless a
  compact public verdict or checker-readable artifact is required.

## Surfaces

| Surface | Role |
| --- | --- |
| Review Queue | Worklist and triage surface |
| `review_action_v1` | Typed action import schema |
| Dry-run application plan | Non-mutating audit of possible changes |
| Expected-diff approval rows | Gate before product-impacting changes |
| Lockbox sampling and label logs | Structured evidence-acquisition artifacts |
| Inter-reviewer agreement summary | Evidence quality and disagreement surface |

## Boundaries

- Owns: review queue generation, typed action import/validation, dry-run
  planning, lockbox sampling, and label log structure.
- Does not own: the current label truth for a specific lockbox case, whether
  a reviewer action is approved for product mutation, backfill writer
  authority, matrix activation scope, or GUI review UX details.
- Checker-backed lockbox queues, templates, and logs stay in-repo (not
  Obsidian). Private reviewer rationale belongs in Obsidian unless a compact
  public verdict is required.

## Verification

- Schema validation tests for actions or labels.
- Stale-source/hash checks for imported review artifacts.
- Expected-diff packet for any selected peak, area, counted detection,
  workbook, or matrix change.
- Productization authority review before writer behavior changes.

## Pitfalls

- Treating review labels as direct writer predicates.
- Applying manual boundaries or candidate switches without stable IDs and
  approved expected diffs.
- Moving checker-backed lockbox queues/templates/logs to Obsidian.
- Keeping private reviewer rationale in public repo because it came from a
  validation folder.

## See Also

- [Validation retention](../superpowers/validation/RETENTION.md)
- [Backfill](backfill.md)
- [Quant matrix](quant-matrix.md)
- [Productization](productization.md)
