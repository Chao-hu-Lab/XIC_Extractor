# Targeted Selection

Document status: product-topic source-of-truth summary.
Evidence label: `diagnostic_only` for this documentation-governance patch; this
page does not change targeted extraction behavior, selected peaks, selected
areas, counted detections, workbook output, or matrix authority.

Targeted selection is the product-facing decision path for known targets. It
turns candidate evidence, region or segment boundaries, paired standards, RT
context, and reason projection into targeted output decisions without letting a
diagnostic proposal silently become product truth.

## Answers

Use this page to answer:

- Which targeted selection surfaces are public behavior.
- Where region, selected-hypothesis, selected-envelope, and target-pair RT rules
  belong.
- What evidence is required before targeted candidate switches or manual
  boundary changes can affect outputs.
- Which dated targeted specs can become private history after their durable
  claims are represented.

## Does Not Answer

This page does not decide:

- A specific target's current selected peak or area.
- Backfill or Discovery writer scope.
- Full review-action apply behavior.
- Current maturity tier or active productization lane.

## Current Contract

- Product targeted output is a workflow-owned projection from evidence and
  selection decisions. Shared evidence providers may inform targeted selection,
  but they do not choose targeted product state by themselves.
- Region, boundary, and selected-envelope logic are candidate and
  model-selection surfaces. They require expected-diff review before they change
  selected peak, selected area, confidence, reason, product state, counted
  detection, workbook values, or matrix values.
- Selected-hypothesis public behavior must preserve compatibility projections
  unless an explicit schema/versioning plan changes downstream contracts.
- Current targeted MS1 shape-identity limited rescue is production-ready only
  for the headless limited `5-hmdC + 5-medC` policy and only writes
  `detected_flagged` support under its expected-diff gate. Broader targets, GUI
  wiring, and default broad NL_FAIL rescue remain blocked without a new
  target-family evidence gate.
- Target-pair RT auto-reselection and calibration artifacts are activation-gated
  selection aids, not default authority unless the control plane and focused
  tests say so.
- Product action or verdict tables are review/reason surfaces. They must not
  hide the evidence chain or grant writer authority.

## Public Surfaces

| Surface | Role |
| --- | --- |
| Targeted CSV/workbook fields | Public output behavior for target decisions |
| `Product State` and `Counted Detection` | User-facing product projection |
| Confidence and reason strings | Reviewable explanation of targeted decision |
| Region and selected-envelope candidates | Boundary and model-selection evidence |
| Target-pair RT calibration artifacts | Activation-gated selection support |
| Expected-diff packets | Required gate for output-changing behavior |

## Workflow

1. Targeted extraction builds candidate evidence for known targets.
2. Evidence providers propose or evaluate peak hypotheses, regions, boundaries,
   RT context, and paired standard support.
3. Selection logic chooses a product candidate only through an explicit targeted
   policy.
4. Output writers project compatibility fields, reasons, confidence, product
   state, counted detection, and workbook surfaces.
5. Any behavior-changing activation requires expected-diff evidence and owner
   updates.

## Verification Gates

Before changing targeted selection behavior, require the relevant subset of:

- focused tests for selected peak, selected area, confidence, reason, product
  state, and counted detection;
- expected-diff packet for workbook/CSV or matrix-impacting changes;
- schema/versioning review when output fields or compatibility projection
  change;
- RAW-tier evidence label that matches the product claim;
- productization control-plane update when maturity, active lane, or authority
  changes.

## Common Wrong Moves

- Treating diagnostic boundary proposals as final selected boundaries.
- Promoting target-pair RT support without explicit activation.
- Letting selected-hypothesis refactors silently change public reason or
  counted-detection behavior.
- Reusing Backfill or Discovery authority for targeted selection.
- Moving targeted specs to private notes before their public behavior is owned
  here or in a named spec.

## Source Owners

- [`docs/lcms-msms-evidence-rules.md`](../lcms-msms-evidence-rules.md)
- [`docs/product/evidence-spine.md`](evidence-spine.md)
- [`docs/product/quantitation-context.md`](quantitation-context.md)
- [`docs/product/review-roundtrip.md`](review-roundtrip.md)
- [`docs/superpowers/specs/2026-05-28-product-priority-reset-decision-spec.md`](../superpowers/specs/2026-05-28-product-priority-reset-decision-spec.md)
- [`docs/superpowers/specs/2026-06-02-selected-hypothesis-evidence-decision-public-behavior-addendum.md`](../superpowers/specs/2026-06-02-selected-hypothesis-evidence-decision-public-behavior-addendum.md)
- [`docs/superpowers/specs/2026-06-02-region-boundary-public-behavior-addendum.md`](../superpowers/specs/2026-06-02-region-boundary-public-behavior-addendum.md)
- [`docs/superpowers/specs/2026-06-03-target-pair-rt-auto-reselection-spec.md`](../superpowers/specs/2026-06-03-target-pair-rt-auto-reselection-spec.md)

## Cleanup Rule

Targeted public-behavior specs can shrink to stubs only after their stable
selection, boundary, reason, and activation rules are represented here or in the
named source owners. Private debug cases and command transcripts belong in
Obsidian after public claims are preserved.

## When To Update

Update this page when targeted selection gains or retires a durable boundary,
selection, reason-projection, RT calibration, or output-compatibility rule.
