# Trigger Cases

## Should Trigger

- "Stop making expansion slices; use examples to define a rule and apply it to
  the full scope."
- "We have a demo set; turn it into a machine-checkable product rule."
- "This important workflow is getting patched case by case; reset the rhythm."
- "Only send ambiguous cases to human review."
- "Use representative examples to define a Backfill/Discovery/review/validation
  rule, then apply it broadly."
- "Before implementing the next major step, define the rule and full-scope
  contract."

## Should Not Trigger

- "Commit these already-finished changes."
- "Give me a status report."
- "Render Gallery overlays."
- "Run this exact validation command."
- "Fix this small typo or one-line bug."
- "Prepare PR closeout."

## Near Neighbors

- Use `xic-product-gate-advancement` when the main question is promotion,
  authority, readiness tier, or control-plane state.
- Use `xic-architecture-preflight` before changing implementation or activation
  code.
- Use `xic-human-review-gallery` when the main output is a review Gallery or
  overlay surface.
- Use `xic-raw-validation` when the main risk is RAW/85RAW command shape or
  validation tier.
