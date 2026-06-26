# Review Roundtrip

Document status: product-topic source-of-truth summary.
Evidence label: `diagnostic_only` for this documentation-governance patch; this
page does not import review actions, apply manual decisions, change selected
peaks, recompute areas, or write matrix values.

Review roundtrip is the path from machine-produced review worklists to typed
human actions, dry-run application plans, expected-diff review, and only then
approved product changes.

## Answers

Use this page to answer:

- What review artifacts can do today.
- Why review worklists, lockbox labels, or action files are not product
  authority by themselves.
- Which repo owners must remain readable after private review notes move to
  Obsidian.
- What evidence is required before review output can change product values.

## Does Not Answer

This page does not decide:

- The current label truth for a specific lockbox case.
- Whether a reviewer action is approved for product mutation.
- Backfill writer authority or matrix activation scope.
- GUI review UX details.

## Current Contract

- Review queues, candidate tables, lockbox packets, and labels are review
  evidence. They do not change product outputs by themselves.
- Typed review actions may be validated and planned before any mutation. Apply
  steps require stable identifiers, recompute rules, sidecar contracts, and
  approved expected-diff evidence.
- Current review-action support is limited to identity verification and
  candidate-sidecar planning. Selected-candidate switching and manual-boundary
  area recomputation are parked until stable IDs, recompute rules, and
  expected-diff apply contracts exist.
- Peak-choice truth labels are separate from product authority. They can inform
  future automation only through a later goal with authority and expected-diff
  gates.
- Lockbox labels and shadow scoring are evidence acquisition only. They do not
  change selected peak, selected area, counted detection, workbook output,
  matrix values, GUI behavior, or ProductWriter authority.
- Reviewer rationale and dispute discussion are private notes unless a compact
  public verdict or checker-readable artifact is required.

## Public Surfaces

| Surface | Role |
| --- | --- |
| Review Queue | Worklist and triage surface |
| `review_action_v1` | Typed action import schema |
| Dry-run application plan | Non-mutating audit of possible changes |
| Expected-diff approval rows | Gate before product-impacting changes |
| Lockbox sampling and label logs | Structured evidence-acquisition artifacts |
| Inter-reviewer agreement summary | Evidence quality and disagreement surface |

## Workflow

1. Product or diagnostic code emits review candidates or lockbox cases.
2. Humans label or propose typed actions.
3. Validators reject malformed, ambiguous, stale, or under-identified actions.
4. Planners produce non-mutating application/readiness/changeset outputs.
5. Product changes require a later activation path with expected-diff approval.

## Verification Gates

Before changing review roundtrip behavior, require the relevant subset of:

- schema validation tests for actions or labels;
- stale-source/hash checks for imported review artifacts;
- expected-diff packet for any selected peak, selected area, counted detection,
  workbook, or matrix change;
- productization authority review before writer behavior changes.

## Common Wrong Moves

- Treating review labels as direct writer predicates.
- Applying manual boundaries or candidate switches without stable IDs and
  approved expected diffs.
- Moving checker-backed lockbox queues/templates/logs to Obsidian.
- Keeping private reviewer rationale in public repo just because it came from a
  validation folder.

## Source Owners

- [`docs/superpowers/specs/2026-06-15-review-roundtrip-v1-spec.md`](../superpowers/specs/2026-06-15-review-roundtrip-v1-spec.md)
- [`docs/superpowers/specs/peak_choice_truth_protocol.v1.md`](../superpowers/specs/peak_choice_truth_protocol.v1.md)
- [`docs/superpowers/validation/RETENTION.md`](../superpowers/validation/RETENTION.md)
- [`docs/product/backfill.md`](backfill.md)
- [`docs/product/quant-matrix.md`](quant-matrix.md)
- [`docs/product/productization.md`](productization.md)

## Cleanup Rule

Private reviewer reasoning, rejected-label debate, and long review narratives
belong in Obsidian. Checker inputs, schemas, label logs, compact summaries, and
public verdicts stay in repo or ignored artifact storage according to retention
policy.

## When To Update

Update this page when review import, label semantics, lockbox evidence,
expected-diff review, or apply-readiness behavior changes.
