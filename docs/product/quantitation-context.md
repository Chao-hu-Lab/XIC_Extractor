# Quantitation Context

Document status: product-topic source-of-truth summary.
Evidence label: `diagnostic_only` for this documentation-governance patch; this
page does not change integration bounds, selected areas, workbook values,
matrix values, or product authority.

Quantitation context is the RT and trace context used to integrate the selected
peak. It is distinct from the narrow candidate proposal interval and from the
full search window.

## Answers

Use this page to answer:

- Why a candidate boundary is not always the full quantitation context.
- Which bounded context rules are public product candidates.
- How morphology, resolver, CWT, safe-merge, and local-minimum evidence relate
  to final area integration.
- Which old area or envelope specs can be stubbed after durable rules are owned.

## Does Not Answer

This page does not decide:

- The selected area for any specific row.
- Whether a candidate segment is production-ready.
- Backfill writer authority or matrix activation.
- Current maturity tier or active lane.

## Current Contract

- The selected peak apex or hypothesis anchors quantitation context.
- Candidate MS1 peak boundaries may be padded by a bounded quantitation-context
  margin when the candidate interval clips real peak flanks.
- The current documented product-candidate margin is capped at `0.40 min` and
  by the configured RT window limit. This is a candidate rule, not a universal
  final science claim.
- CWT, local minima, safe-merge, derivative, region-first logic, and morphology
  facts are proposal or model-selection evidence. No single evidence family
  silently becomes final integration authority.
- Selected-full-envelope evidence remains diagnostic/review context unless a
  later activation contract promotes it.

## Public Surfaces

| Surface | Role |
| --- | --- |
| Candidate boundary | Proposal interval and evidence context |
| Quantitation-context margin | Bounded candidate expansion policy |
| `ChromPeakSegment` | Scoped product-candidate boundary unit |
| Gaussian15 morphology facts | Shape/area evidence and current area-owner context |
| Integration result | Selected trace area and provenance |
| Expected-diff packet | Gate before area-impacting changes |

## Workflow

1. Candidate evidence proposes a peak interval.
2. Quantitation-context policy decides whether a bounded wider trace context is
   needed.
3. Boundary/model-selection evidence evaluates the selected segment.
4. Integration computes area over the selected context.
5. Product writers may publish values only through the relevant output and
   authority contract.

## Verification Gates

Before changing quantitation context, require the relevant subset of:

- focused tests for boundary padding, RT limits, and fallback behavior;
- plot-backed or row-level evidence for clipped-flank fixes and no over-merge;
- expected-diff packet for selected area, workbook, or matrix changes;
- RAW-tier validation that matches the product claim;
- evidence-rule update if the active area owner changes.

## Common Wrong Moves

- Treating the discovery candidate interval as the whole final trace context.
- Integrating every positive residual in a broad RT context.
- Letting safe-merge, local-minimum, CWT, or derivative signals become hidden
  product authority.
- Treating an 8RAW candidate result as broad production readiness.

## Source Owners

- [`docs/lcms-msms-evidence-rules.md`](../lcms-msms-evidence-rules.md)
- [`docs/product/targeted-selection.md`](targeted-selection.md)
- [`docs/product/evidence-spine.md`](evidence-spine.md)
- [`docs/product/quant-matrix.md`](quant-matrix.md)
- [`docs/superpowers/specs/2026-06-03-selected-full-envelope-quantitation-boundary-spec.md`](../superpowers/specs/2026-06-03-selected-full-envelope-quantitation-boundary-spec.md)

## Cleanup Rule

Area-policy and quantitation-context notes with sample-level examples can move
to private notes only after bounded context rules, active area-owner rules, and
expected-diff gates are represented here or in evidence-rule owners. Keep
same-path stubs only for exact refs to old closeout notes.

## When To Update

Update this page when the project changes boundary padding, selected segment
authority, fallback context rules, or integration-context validation gates.
