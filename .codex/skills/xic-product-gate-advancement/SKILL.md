---
name: xic-product-gate-advancement
description: Use when deciding whether XIC diagnostic, shadow, RAW, review, expected-diff, Gallery, or artifact evidence can advance a product gate, readiness tier, active lane, activation bundle, ProductWriter authority, or control-plane state.
---

# XIC Product Gate Advancement

Use when evidence might change product readiness or authority. The job is to
separate diagnostic observability from product behavior before updating any
control plane, matrix authority, or default lane.

## Gate Contract

Before advancing a gate, state:

- current tier/lane and proposed tier/lane;
- exact product decision the evidence can close;
- strongest evidence tier inspected;
- expected diff and public-surface risk;
- whether ProductWriter, default matrix, workbook, GUI, or activation authority
  changes;
- exit rule for any `diagnostic_only`, `shadow_ready`, or temporary adapter path.

If the evidence cannot change the next product action, do not promote. Convert
the work into a diagnostic note, follow-up goal, or kill decision.

## Promotion Boundaries

- Diagnostic TSVs, sidecars, wrappers, guides, and reports prove observability,
  not product behavior.
- CID-NL/MS2 evidence is evidence-provider input; it does not directly become
  ProductWriter authority.
- Candidates are not matrix rows.
- Control plane updates are required only when maturity tier, active lane,
  authority, product gate, or public contract state actually changes.

## References

- Evidence tiers, expected diff, and update boundaries:
  `references/product-gate-contract.md`
- Trigger and near-neighbor cases:
  `evals/trigger-cases.md`
- Portable skill interface metadata:
  `agents/interface.yaml`
