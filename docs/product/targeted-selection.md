# Targeted Selection

Targeted selection is the product-facing decision path for known targets. It turns candidate evidence, region boundaries, paired standards, RT context, and reason projection into targeted output decisions. Diagnostic proposals must pass through explicit policy before becoming product truth.

## Contract

- Product targeted output is a workflow-owned projection from evidence and selection decisions. Shared evidence providers inform but do not choose targeted product state.
- Region, boundary, and selected-envelope logic are candidate and model-selection surfaces. They require expected-diff review before changing selected peak, area, confidence, reason, product state, counted detection, workbook, or matrix values.
- Selected-hypothesis public behavior must preserve compatibility projections unless an explicit schema/versioning plan changes downstream contracts.
- MS1 shape-identity limited rescue is production-ready only for the headless limited `5-hmdC + 5-medC` policy and only writes `detected_flagged` under its expected-diff gate. Broader targets, GUI wiring, and default broad NL_FAIL rescue remain blocked without a new target-family evidence gate.
- Target-pair RT auto-reselection and calibration artifacts are activation-gated selection aids, not default authority unless the control plane and focused tests say so.
- Targeted expected-diff approvals must reference runtime product
  `PeakHypothesis` candidate IDs. Overlay-only or audit-table candidate IDs can
  explain support, but they are not valid product-switch inputs.
- Product action or verdict tables are review/reason surfaces; they must not hide the evidence chain or grant writer authority.

## Retained Validation Anchors

- The 2026-06-04 `BenignfatBC1055_DNA / 8-oxodG` closeout is a row-specific
  expected-diff activation, not a general target-pair RT auto-reselection rule.
  It changed one targeted product row after the approved successor existed in
  runtime product hypotheses and had role-aware RT, paired-area-ratio, MS1, and
  trace support.
- The visible product decision surface for that slice is `Product State`,
  `Counted Detection`, `Review State`, and projection-backed `Reason`. Legacy
  `Confidence`, score, and cap evidence remain technical audit material while
  this projection contract is active.
- The observed 8RAW count change for that slice was `8-oxodG: 3/8 -> 4/8`,
  with all other target labels unchanged. Treat it as a validation anchor for
  the activation gate, not as broad target-pair policy.

## Surfaces

| Surface | Role |
| --- | --- |
| Targeted CSV/workbook fields | Public output for target decisions |
| `Product State` / `Counted Detection` | User-facing product projection |
| Confidence and reason strings | Reviewable decision explanation |
| Region and selected-envelope candidates | Boundary and model-selection evidence |
| Target-pair RT calibration artifacts | Activation-gated selection support |
| Expected-diff packets | Required gate for output-changing behavior |

## Boundaries

- **Owns:** targeted product projection (selected peak, area, confidence, reason, product state, counted detection), MS1 rescue policy scope, target-pair RT rules.
- **Does not own:** Backfill/Discovery writer scope, specific target's current selected peak, full review-action apply behavior, or maturity tier decisions.
- Targeted authority does not extend to untargeted pipelines, and untargeted authority does not extend back.

## Verification

- Focused tests for selected peak, area, confidence, reason, product state, and counted detection.
- Expected-diff packet for workbook/CSV or matrix-impacting changes.
- Schema/versioning review when output fields or compatibility projection change.
- RAW-tier evidence label matching the product claim.
- Control-plane update when maturity, lane, or authority changes.

## Pitfalls

- Treating diagnostic boundary proposals as final selected boundaries.
- Promoting target-pair RT support without explicit activation.
- Letting selected-hypothesis refactors silently change public reason or counted-detection behavior.
- Reusing Backfill or Discovery authority for targeted selection.

## See Also

- [LC-MS/MS evidence rules](../lcms-msms-evidence-rules.md) | [Evidence spine](evidence-spine.md)
- [Quantitation context](quantitation-context.md) | [Review roundtrip](review-roundtrip.md)
- [Product priority reset spec](../superpowers/specs/2026-05-28-product-priority-reset-decision-spec.md)
- [Selected-hypothesis behavior addendum](../superpowers/specs/2026-06-02-selected-hypothesis-evidence-decision-public-behavior-addendum.md)
- [Region-boundary behavior addendum](../superpowers/specs/2026-06-02-region-boundary-public-behavior-addendum.md)
- [Target-pair RT auto-reselection spec](../superpowers/specs/2026-06-03-target-pair-rt-auto-reselection-spec.md)
