# Instrument QC and Calibration

Instrument QC and calibration artifacts diagnose method and instrument
behavior. They are evidence and review surfaces until a separate activation
contract promotes a correction or gate.

## Contract

- Clean standards diagnose clean-matrix instrument/method behavior. They
  cannot alone represent biological matrix effects.
- Biological QC ISTDs are the primary anchors for real-matrix RT/response
  transfer evidence when they exist.
- HCD/product-ion audit is a human review and plausibility surface. It must
  not become a hard pass/fail production gate without an explicit activation
  contract.
- Level 3 RT calibration remains `NO-GO`: leave-one-anchor-out residuals,
  transfer support, extrapolated rows, and blocked rows do not yet support
  production correction.
- RT-aware midterm preview artifacts are shadow/readiness evidence only.
  They do not activate RT correction, response correction, normalization,
  matrix mutation, or default gating.
- The next safe calibration direction is shadow/readiness evidence, not
  value mutation.

## Surfaces

| Surface | Role |
| --- | --- |
| Instrument QC trend TSV/workbook | Clean-standard and biological QC review surface |
| HCD audit TSV/JSON/workbook sheet | Product-ion audit evidence |
| Calibration maturity gate | Readiness and blocker summary |
| Biological ISTD transfer audit | Real-matrix transfer evidence |
| Calibration preview outputs | Shadow or diagnostic evidence only |

## Boundaries

- Owns: clean-vs-biological QC evidence roles, HCD audit output format,
  calibration maturity gate classification, and transfer audit structure.
- Does not own: a specific run's QC acceptance, RT/response/normalization
  activation, DNP or downstream normalization behavior, or matrix activation.
- Dated QC/calibration notes and specs become history stubs after their
  stable claims are absorbed here.

## Verification

- Schema tests for QC and HCD audit outputs.
- Parity tests when adding metadata or sidecars.
- Blocker/readiness tests for calibration gates.
- Expected-diff packet for value-changing corrections.

## Pitfalls

- Treating clean-standard behavior as proof of biological matrix performance.
- Making HCD support a hard gate from audit evidence alone.
- Applying Level 3 RT correction while maturity gate remains `NO-GO`.
- Hiding calibration assumptions in private notes without a repo owner.

## See Also

- [Sample metadata and QC](sample-metadata-qc.md)
- [LC-MS/MS evidence rules](../lcms-msms-evidence-rules.md)
- [Evidence spine](evidence-spine.md)
- [Review roundtrip](review-roundtrip.md)
- [Productization](productization.md)
- [Productization control plane](../superpowers/plans/2026-06-15-productization-control-plane.md)
