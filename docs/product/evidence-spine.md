# Evidence Spine

Document status: product-topic source-of-truth summary.
Evidence label: `diagnostic_only` for this documentation-governance patch; this
page does not change evidence rules, selected peaks, selected areas, counted
detections, writer authority, or matrix values.

The evidence spine is the shared layer that turns chromatographic observations
into auditable peak hypotheses and workflow-owned product decisions. Targeted
and untargeted workflows may share identity facts, but they must not share final
product authority by accident.

## Answers

Use this page to answer:

- Which concepts are shared across targeted extraction and untargeted
  discovery/alignment.
- Where workflow-neutral evidence ends and workflow-specific product projection
  begins.
- Which owner docs decide evidence semantics and matrix authority.
- Whether a diagnostic evidence provider may write product outputs.

## Does Not Answer

This page does not decide:

- Backfill writer scope or accepted cells.
- Targeted rescue activation policy for a specific assay.
- Current maturity tier, active lane, or promotion packet status.
- The exact implementation plan for a future evidence-provider slice.

## Current Contract

- Evidence providers are inputs to `EvidenceVector`, `PeakHypothesis`,
  `IntegrationResult`, model selection, audit, or activation contracts. They do
  not write product matrices directly.
- Shared peak identity should own workflow-neutral facts such as trace shape,
  candidate-to-anchor RT delta, competing-peak summaries, boundary
  assessability, and provenance validation.
- Targeted workflows add known-target policy such as analyte/ISTD role,
  paired-ISTD RT support, target RT windows, NL/MS2 opportunity, paired area
  ratio, and targeted expected-diff activation.
- Untargeted workflows add alignment/Backfill policy such as owner construction,
  same-peak anchor support, cell-level Backfill decision, authority manifest,
  and quant-matrix activation.
- A shared evidence provider may support both workflows only if its output is a
  typed fact, not a hidden product decision.
- The shared evidence-spine direction is to preserve and adapt existing typed
  evidence objects rather than replace workflow policies. Adoption notes and
  slice plans are private development history once this shared-vs-owned-product
  boundary remains repo-readable here and in `docs/lcms-msms-evidence-rules.md`.

## Public Surfaces

| Surface | Role |
| --- | --- |
| `EvidenceVector` and `EvidenceDecisionSemantics` | Shared typed evidence vocabulary |
| `PeakHypothesis` | Candidate chromatographic identity unit |
| `IntegrationResult` | Integrated signal and boundary result used by workflows |
| `AuditTrail` / reason strings | Human-readable explanation and review evidence |
| Targeted product projection | Workflow-owned targeted output decision |
| Backfill / alignment projection | Workflow-owned untargeted or matrix decision |

## Workflow

1. A trace, trace group, candidate table row, or alignment cell exposes raw
   evidence.
2. Workflow-neutral evidence providers produce typed identity facts.
3. The evidence spine represents candidate hypotheses and integration results.
4. Each workflow applies its own product policy.
5. Product-facing outputs are written only by the relevant authority path.

## Verification Gates

Before changing evidence-spine behavior, require the relevant subset of:

- characterization tests for existing evidence semantics;
- focused tests for new typed evidence facts;
- expected-diff framing if selected peak, selected area, counted detection,
  confidence, reason, workbook, TSV, or matrix values can change;
- RAW-tier evidence label that matches the claim;
- productization owner update if product authority changes.

## Common Wrong Moves

- Treating shared evidence as shared product authority.
- Letting untargeted Backfill rules silently become targeted rescue rules.
- Letting targeted analyte/ISTD rules silently become Backfill writer rules.
- Counting multiple typed facts as independent observations when they describe
  the same physical evidence.
- Promoting review-only, diagnostic-only, or shadow evidence into matrix values.

## Source Owners

- [`docs/lcms-msms-evidence-rules.md`](../lcms-msms-evidence-rules.md)
- [`docs/architecture-contract.md`](../architecture-contract.md)
- [`docs/product/backfill.md`](backfill.md)
- [`docs/product/discovery.md`](discovery.md)
- [`docs/product/alignment.md`](alignment.md)
- [`docs/product/productization.md`](productization.md)

## Cleanup Rule

Detailed debug cases and branch-specific evidence-spine debates can move to
private notes after the durable shared-vs-workflow-owned boundary is represented
here and in `docs/lcms-msms-evidence-rules.md`. Keep same-path stubs while exact
referrers still need old spec paths, including the superseded shared-spine spec.

## When To Update

Update this page when the project adds or retires a shared evidence carrier,
evidence provider, workflow projection boundary, or recurring evidence
authority mistake.
