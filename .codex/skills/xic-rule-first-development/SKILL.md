---
name: xic-rule-first-development
description: Use when a major XIC workflow, product gate, algorithm, validation path, review process, or artifact pipeline risks becoming repeated small slices, ad hoc patches, or mixed responsibilities. Guides an example-to-rule rhythm: calibrate on representative cases, freeze the rule/contract, apply it to the full relevant scope, review only ambiguous cases, then deliver one bounded accepted set.
---

# XIC Rule-First Development

Use this for important XIC work where a few examples should teach a durable
rule before scaling. This includes Discovery, Backfill, product gates, review
actions, artifact workflows, validation strategy, and algorithm behavior.

Do not use this for tiny bug fixes, one-off reports, plain status updates,
simple commits, or work whose rule and full scope are already obvious.

## Core Rule

Do not let "next small slice" become the default delivery rhythm. Slices are
calibration tools; the product rhythm should move toward a rule that can be
applied to the full relevant scope.

Preferred rhythm:

1. choose a representative demonstration set;
2. extract the simplest machine-checkable rule;
3. freeze the rule, contract, and acceptance oracle;
4. apply it to the full relevant scope;
5. send only ambiguous or failing cases to human/AI review;
6. deliver one bounded accepted set with explicit evidence.

## Before Work Starts

State this compact contract:

```markdown
Work question:
Demonstration evidence:
Proposed rule:
Full relevant scope:
Ambiguous bucket:
Expected output/change:
Near-neighbor work excluded:
Stop rule:
```

If the current work only stabilizes an already accepted release slice, say that
explicitly and run the relevant release/checker instead of inventing another
slice.

## Required Boundaries

- Examples prove calibration, not product authority by themselves.
- The rule must be human-explainable before it is applied broadly.
- Public-surface changes still need expected diff, provenance, artifact
  retention, and control-plane updates when authority, schema, tier, or active
  lane changes.
- Keep responsibilities separated. Do not mix Discovery, Backfill, GUI,
  workbook, review, and validation decisions in one rule unless the full scope
  explicitly requires it.
- Do not ask humans to review obvious pass/fail rows; route only ambiguity,
  conflict, or rule failures.

## Use With

- Use `xic-architecture-preflight` before changing implementation or activation
  paths.
- Use `xic-product-gate-advancement` when the result might change readiness
  tier, active lane, matrix authority, ProductWriter behavior, or public
  surface.
- Use domain-specific skills such as `xic-human-review-gallery`,
  `xic-raw-validation`, or `xic-validation-artifact-retention` when those
  surfaces are the actual output.

## Output

Produce one of these:

- a rule-first implementation plan;
- a full-scope classification contract;
- a bounded activation/delivery contract;
- a release-slice stabilization report;
- a kill/hold decision explaining why the rule is not mature enough.

Never end with "continue with another expansion slice" unless the slice is
explicitly framed as rule calibration and has an exit rule to full-scope
classification or delivery.

## References

- Rule-first workflow details:
  `references/rule-first-development-workflow.md`
- Trigger and near-neighbor cases:
  `evals/trigger-cases.md`
- Portable skill interface metadata:
  `agents/interface.yaml`
