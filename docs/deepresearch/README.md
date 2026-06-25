# Deep research background notes

This folder stores reusable deep-research context for product and architecture
decisions. These notes are background inputs, not product authority by
themselves. Product tier, public contracts, writer behavior, matrix semantics,
and release claims still live in the control plane, named specs, tests, and
validated output artifacts.

## Current notes

- [LCMS_Backfill_Design_Notes.md](LCMS_Backfill_Design_Notes.md): LC-MS /
  metabolomics backfill architecture RFC. Main takeaway: Backfill can be an
  accepted quantification value when evidence and provenance close; it remains
  distinct from detection and truth claims.
- [software backfill.md](<software backfill.md>): mature mass-spectrometry
  software backfill/reimport/rerun patterns. Main takeaway: robust backfill
  needs source discovery, input snapshots, idempotency, retry classes,
  resume/cache behavior, and execution artifacts.
- [Backfill Production Gate.md](<Backfill Production Gate.md>): sanitized repo
  stub for Backfill / gap-filling product-gate research. Main takeaway:
  `height >= 2e6` is a high-signal demonstrator or rollout guardrail, not a
  universal product hard gate. The full research diary lives in private
  Obsidian; the repo stub keeps only the public decision and owner links.
- [Compair.md](Compair.md): XIC Extractor compared with mature free/open LC-MS
  tools. Use it to separate the product floor XIC should catch up to from the
  assay-specific evidence-adjudication ceiling XIC should preserve.
- [LC-MS targeted research.md](<LC-MS targeted research.md>): targeted
  small-molecule LC-MS quantification with stable isotope-labeled internal
  standards. Use it for analyte/ISTD pairing, peak-group ranking, co-elution,
  shared/compatible boundaries, and counted/flagged/not-counted decision
  framing.

## Current synthesis

- [Backfill Quant Matrix Product Blueprint](../superpowers/plans/2026-06-19-backfill-quant-matrix-product-blueprint.md):
  read-first synthesis that translates the research notes into XIC engineering
  phases, authority lanes, cleanup rules, and quant-matrix activation path.

## How to use

1. Treat these notes as design input and terminology background.
2. Before changing product behavior, connect the idea to a named spec or
   control-plane entry.
3. Before changing matrix/product output, require focused tests, expected-diff
   evidence, and the relevant real-data/oracle gate.
4. If a note conflicts with the current control plane or a named spec, stop and
   resolve the conflict instead of silently choosing the newer wording.
