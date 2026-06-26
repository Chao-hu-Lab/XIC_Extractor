# Instrument QC And Calibration

Document status: product-topic source-of-truth summary.
Evidence label: `diagnostic_only` for this documentation-governance patch; this
page does not change QC outputs, calibration behavior, selected values,
normalization, matrix values, or product authority.

Instrument QC and calibration artifacts diagnose method and instrument behavior.
They are evidence and review surfaces until a separate activation contract
promotes a correction or gate.

## Answers

Use this page to answer:

- How clean-standard QC differs from biological QC ISTD evidence.
- Whether HCD/product-ion support is a hard gate.
- Why Level 3 RT calibration remains `NO-GO`.
- Which calibration/QC history can move to private notes after durable claims
  are represented.

## Does Not Answer

This page does not decide:

- A specific run's QC acceptance.
- RT correction, response correction, or normalization activation.
- DNP or downstream normalization behavior.
- ProductWriter authority or matrix activation.

## Current Contract

- Clean standards diagnose clean-matrix instrument/method behavior. They cannot
  alone represent biological matrix effects.
- Biological QC ISTDs are the primary anchors for real-matrix RT/response
  transfer evidence when they exist.
- HCD/product-ion audit is a human review and plausibility surface. It must not
  become a hard pass/fail production gate without an explicit activation
  contract.
- Level 3 RT calibration remains `NO-GO` because leave-one-anchor-out residuals,
  transfer support, extrapolated rows, and blocked rows do not yet support
  production correction.
- RT-aware midterm preview artifacts are shadow/readiness evidence only. They do
  not activate RT correction, response correction, normalization, matrix
  mutation, or default gating.
- The next safe calibration direction is shadow/readiness evidence, not value
  mutation.

## Public Surfaces

| Surface | Role |
| --- | --- |
| Instrument QC trend TSV/workbook | Clean-standard and biological QC review surface |
| HCD audit TSV/JSON/workbook sheet | Product-ion audit evidence |
| Calibration maturity gate | Readiness and blocker summary |
| Biological ISTD transfer audit | Real-matrix transfer evidence |
| Calibration preview outputs | Shadow or diagnostic evidence only |

## Workflow

1. Clean standards and biological QC ISTDs are evaluated separately.
2. QC artifacts report RT, area/intensity, HCD/product-ion, and transfer
   evidence.
3. Calibration gates classify readiness and blockers.
4. Shadow previews may propose correction effects.
5. Any value-changing correction requires a later activation/export contract.

## Verification Gates

Before changing QC or calibration behavior, require the relevant subset of:

- schema tests for QC and HCD audit outputs;
- parity tests when adding metadata or sidecars;
- blocker/readiness tests for calibration gates;
- expected-diff packet for value-changing corrections;
- productization owner update before production correction or normalization
  activation.

## Common Wrong Moves

- Treating clean-standard behavior as proof of biological matrix performance.
- Making HCD support a hard gate from audit evidence alone.
- Applying Level 3 RT correction while maturity gate remains `NO-GO`.
- Hiding calibration assumptions in private notes without a repo owner.

## Source Owners

- This file owns durable public Instrument QC and calibration boundaries. Dated
  QC/calibration notes and specs are migration/history stubs after their stable
  claims are absorbed here.
- [`docs/product/sample-metadata-qc.md`](sample-metadata-qc.md)
- [`docs/lcms-msms-evidence-rules.md`](../lcms-msms-evidence-rules.md)
- [`docs/product/evidence-spine.md`](evidence-spine.md)
- [`docs/product/review-roundtrip.md`](review-roundtrip.md)
- [`docs/product/productization.md`](productization.md)
- [`docs/superpowers/plans/2026-06-15-productization-control-plane.md`](../superpowers/plans/2026-06-15-productization-control-plane.md)

## Cleanup Rule

QC/calibration command diaries and run-specific interpretation notes can move to
private notes after clean-vs-biological evidence roles, HCD audit limits, and
calibration no-go gates are represented here or in the productization owners.

## When To Update

Update this page when QC outputs, HCD audit semantics, calibration maturity
gates, transfer evidence, or activation boundaries change.
