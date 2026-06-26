# Deep research background notes

This folder now keeps public-safe stubs for research notes that have been moved
into private Obsidian storage. The repo should retain only durable rules,
reviewed method summaries, and source-of-truth routing. Long vendor-by-vendor
research narrative, development history, and exploratory reasoning belong in
Obsidian.

## Migrated Background Themes

The old same-path research-note files are migration stubs, not public reading
surfaces. Their durable public takeaways have been folded into the repo sources
of truth below.

- Mature LC-MS tool comparison: XIC should catch up to the operational floor of
  established tools while preserving assay-specific evidence adjudication as
  the product ceiling.
- Targeted small-molecule quantification: rank analyte/ISTD peak groups and
  separate counted, flagged, and not-counted decisions.
- Backfill evidence lifecycle: backfill recovers evidence; versioned export
  owns final matrix write authority.
- Resolver terminology and placement: resolver is software-level signal
  separation/deconvolution and must be validated by quantitative and
  qualitative outcomes.
- Mature MS software backfill/reimport/rerun patterns: robust backfill needs
  source discovery, snapshots, idempotency, retry classes, resume/cache
  behavior, and execution artifacts.
- Backfill product-gate research: height >= 2e6 is a high-signal demonstrator
  or rollout guardrail, not a universal product hard gate.

## Repo sources of truth

- docs/product/backfill.md
- docs/product/targeted-selection.md
- docs/product/evidence-spine.md
- docs/product/quant-matrix.md
- docs/product/quantitation-context.md
- docs/product/review-roundtrip.md
- docs/product/run-provenance.md
- docs/product/productization.md
- docs/lcms-msms-evidence-rules.md
- docs/architecture-contract.md

## How to use

1. Treat files in this folder as routing stubs and historical context, not
   product authority.
2. Before changing product behavior, connect the idea to a repo source of truth,
   a named spec, a test, and validated output evidence.
3. If a stub conflicts with the current control plane or a product doc, stop and
   update the repo source of truth instead of expanding the stub.
4. Do not paste private Obsidian research narrative back into this folder unless
   it has been reviewed and rewritten as public method documentation.
