# Preflight Contract

## North Star

XIC Extractor is not a single-dataset tool and not a CID-NL-only pipeline.

- 8RAW and 85RAW are validation fixtures and cost/stress oracles, not product
  boundaries.
- CID-NL, HCD-PI, Delta Mass, MS1 isotope/adduct pattern, RT/iRT, shape,
  library matches, standards, and future models are evidence providers.
- Evidence providers feed `EvidenceVector` / model selection. They must not
  directly become permanent matrix-writing authority without an explicit product
  contract.

## Product Spine

Name the layer:

- `Trace` / `TraceGroup`
- `PeakHypothesis`
- `EvidenceVector`
- `IntegrationResult`
- model selection
- `AuditTrail`
- cleanup-only

## Owner And Helper

- Domain behavior belongs in `xic_extractor/...`.
- `tools/diagnostics/...` should orchestrate, not own reusable logic.
- Writers render; they do not recompute evidence or re-read RAW.
- Search `tools/diagnostics/INDEX.md`, `docs/architecture-contract.md`, and
  existing package modules before adding a local helper.
- Prefer `xic_extractor/tabular_io.py` before new TSV/parser/scalar helpers.
- Prefer shared overlay/evidence selectors before one-off row selection.

## Product Rule And Cost

If a rule needs nested dataset-specific qualifiers, treat it as a temporary
validation slice, not product policy. Name the simple gate it approximates.

Call-cost model includes RAW opens, XIC extraction calls, batch size, locality,
repeated TSV scans, smoothing/curve normalization, and per-row versus
per-family/per-sample cache boundaries.

Public contract risk includes CLI flags, config keys, TSV/CSV/workbook schema,
matrix identity, activation decisions, value delta, output path, and artifact
naming.

Validation tiers include synthetic/focused tests, no-RAW artifact parity, 8RAW,
85RAW, targeted benchmark, and manual EIC/MS2 review.
