# Discovery

Document status: product-topic source-of-truth summary.
Evidence label: `diagnostic_only` for this documentation-governance patch; this
page does not change discovery output schemas or product authority.

Discovery is the untargeted feature-discovery lane: it turns seed evidence and
MS1 traces into reviewable candidates. It does not directly publish product
matrices.

This topic file gives repo readers a stable entry point before they read dated
discovery plans, specs, or private implementation history.

## Answers

Use this page to answer:

- What discovery is allowed to produce.
- Whether discovery outputs can publish product matrices.
- Which files form the standard per-sample and batch handoff surfaces.
- Where to look before changing discovery evidence semantics or output shape.

## Does Not Answer

This page does not decide:

- ProductWriter authority or Backfill promotion. Use Backfill and
  productization owners.
- Final evidence truth for a candidate feature. Use evidence rules and
  validation packets.
- Exact current release-slice readiness. Use productization status artifacts and
  release-slice checkers.

## Current Contract

- Discovery produces candidate and review surfaces, not final product authority.
- Seed evidence can include MS2 neutral loss, precursor inference, MS1 trace
  support, and future evidence providers, but matrix publication requires the
  separate Backfill/ProductWriter authority path.
- Standard per-sample outputs are `discovery_candidates.csv` for archival or
  alignment-ready detail and `discovery_review.csv` for compact human review.
- Batch discovery handoff uses explicit index files. Do not depend on old
  worktree-local output directories as durable inputs.
- Minimal output modes are for fast inspection; standard outputs are the public
  machine handoff surfaces.
- Discovery UX and review surfaces are public handoffs when they define
  filenames, columns, row identity, output level, or downstream consumption.
  Dated implementation plans can move to private history only if those stable
  output and review-surface claims remain represented here, in named specs, and
  in tests.
- The current CID-NL Discovery product lane is separate from Backfill. A
  Discovery slice must use Discovery vocabulary and authority; it must not
  reopen broad Backfill or expand the Backfill authority manifest by accident.
- The current CID-NL Discovery scope is a bounded accepted slice. Future
  Discovery-only expansion needs successor-level tag context, MS1/quant support,
  provenance, value-delta framing, expected matrix effect, and explicit
  expected-diff review.
- RAW locality and request batching are performance/product constraints. Do not
  introduce vendor RAW to mzML conversion as an implicit product dependency
  without a separate public contract.

## Public Surfaces

| Surface | Role |
| --- | --- |
| `xic_extractor/discovery/` | Discovery domain package |
| `scripts/run_discovery.py` | Discovery CLI entry point |
| `discovery_candidates.csv` | Detailed candidate table for archival or downstream handoff |
| `discovery_review.csv` | Compact review table |
| `discovery_batch_index.csv` | Batch handoff index for downstream alignment |

## Workflow

1. Seed evidence identifies candidate features for a sample.
2. Discovery builds per-sample candidate rows and compact review rows.
3. Standard outputs preserve both detailed candidate data and reviewable
   summaries.
4. Batch runs produce an explicit handoff index for downstream alignment.
5. Alignment or Backfill may consume discovery surfaces, but product publication
   still goes through the separate authority path.

## Verification Gates

Before changing discovery behavior, require the relevant subset of:

- schema or snapshot tests for candidate, review, and batch-index outputs;
- focused tests for seed evidence and MS1 trace handoff behavior;
- performance/output-level review if a minimal or standard mode changes;
- evidence-rule review if a new evidence provider changes candidate meaning;
- downstream alignment handoff check when filenames or columns change.

## Common Wrong Moves

- Treating `discovery_review.csv` as a product matrix.
- Depending on old worktree output directories instead of explicit batch index
  files.
- Hiding discovery output-contract changes in dated implementation notes.
- Treating a new evidence provider as ProductWriter authority without Backfill
  activation.
- Dragging CID-NL Discovery decisions into the Backfill lane.
- Starting untargeted performance implementation before timing/locality evidence
  identifies the bottleneck and correctness gate.

## Source Owners

- This file owns the durable public Discovery method, output, review-surface,
  and performance direction. Dated Discovery specs are migration/history stubs
  after their stable claims are absorbed here.
- [`docs/architecture-contract.md`](../architecture-contract.md) owns package
  ownership, dependency direction, and diagnostic-vs-production boundaries.
- [`alignment.md`](alignment.md) for the cross-sample handoff boundary.
- [`docs/lcms-msms-evidence-rules.md`](../lcms-msms-evidence-rules.md) for
  evidence semantics.
- [`docs/superpowers/plans/2026-06-21-cid-nl-discovery-product-roadmap.md`](../superpowers/plans/2026-06-21-cid-nl-discovery-product-roadmap.md)
  for the current CID-NL Discovery product lane boundary.
- [`docs/superpowers/specs/2026-05-12-untargeted-performance-architecture-spec.md`](../superpowers/specs/2026-05-12-untargeted-performance-architecture-spec.md)
  for RAW-locality and request-batching performance direction.

## Cleanup Rule

Dated discovery implementation plans can move to private notes only after their
stable output, evidence, and handoff claims are reflected here or in the source
owners above. Do not leave repo readers dependent on private Obsidian notes to
understand what discovery writes or what alignment may consume.

## When To Update

Update this page when discovery gains a durable output, public evidence provider,
batch handoff rule, or recurring wrong-move rule. If candidate/review schemas,
public filenames, or downstream handoff behavior change, update the owning spec,
tests, and this page together.
