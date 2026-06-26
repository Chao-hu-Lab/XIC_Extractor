# Deepresearch Same-Path Stub Drafts

Status: draft/control artifact only.
Validation status: `diagnostic_only`.

These drafts have now been applied as same-path public stubs for the five
Deepresearch sources. They do not authorize moving, deleting, or `git rm`-ing
anything.

Obsidian status: full private source copies and five staged distilled notes were
written and read back on 2026-06-25. Repo-side same-path stubs were then applied
without moving paths or running `git rm`.

## Referrer Scan Result

The five Deepresearch candidates are referenced by:

- `docs/deepresearch/README.md` through relative links;
- `docs/superpowers/notes/2026-06-19-backfill-quant-matrix-cleanup-map.md`
  for `LCMS_Backfill_Design_Notes.md`, `software backfill.md`, and
  `Resolver.md`;
- cleanup-control artifacts created during this Phase 2 review.

`Resolver` as a plain word is too generic to use as a blocker. Use
`Resolver.md` or the full repo path when checking exact referrers.

## `docs/deepresearch/Compair.md`

Status: `repo_stub_plus_obsidian`
Validation status: `diagnostic_only`

Public summary:

- XIC should not try to become a general LC-MS platform replacement.
- The public product-floor gaps are replayable project/batch/CLI behavior,
  sample metadata and QC, cross-sample target tables, estimated or gap-filled
  state, calibration/ISTD data model, export schema, provenance, and a future
  vendor-neutral path.
- The durable differentiation claim is assay-specific evidence adjudication:
  separate signal from counted detection, preserve reason grammar, reviewer
  queue, and audit-grade decision traceability.

Repo sources of truth:

- `docs/product/productization.md`
- `docs/product/discovery.md`
- `docs/product/alignment.md`
- `docs/product/evidence-spine.md`

Next safe action:

1. Keep only this public positioning in repo.
2. Put the long tool-by-tool research narrative in Obsidian staging.
3. Retarget `docs/deepresearch/README.md` to this stub or the product topics.

## `docs/deepresearch/LC-MS targeted research.md`

Status: `repo_stub_plus_obsidian`
Validation status: `diagnostic_only`

Public summary:

- Stable-isotope ISTD co-elution is a hard prior for targeted small-molecule
  quantitation, with explicit exceptions only for known isotope effects or
  strong reproducible confirmatory evidence.
- Peak boundaries should be shared or compatible at the pair/group level; fully
  independent analyte/ISTD boundaries can create false ratios.
- The useful public state model is `counted`, `flagged`, and `not-counted`, not
  merely integrated versus not integrated.
- Area ratio is a post-selection sanity check and QC signal. It should not be
  the first peak selector.

Repo sources of truth:

- `docs/lcms-msms-evidence-rules.md`
- `docs/product/targeted-selection.md`
- `docs/product/quantitation-context.md`
- `docs/product/review-roundtrip.md`

Next safe action:

1. Keep the stable SIL-IS decision rules in the repo owners.
2. Move vendor-by-vendor research detail to Obsidian staging.
3. Keep this path as a short public context stub while relative README links
   remain.

## `docs/deepresearch/LCMS_Backfill_Design_Notes.md`

Status: `repo_stub_plus_obsidian`
Validation status: `diagnostic_only`

Public summary:

- Backfill is evidence recovery, not forced value replacement.
- Candidate evidence, approved evidence, manual integration, imputation, and
  final matrix export are separate layers.
- Final quantitative matrix writing requires versioned export policy and
  mechanically traceable authority.
- Imputed values belong downstream and must not masquerade as detected peak
  area.

Repo sources of truth:

- `docs/product/backfill.md`
- `docs/product/quant-matrix.md`
- `docs/product/run-provenance.md`
- `docs/superpowers/plans/2026-06-19-backfill-quant-matrix-product-blueprint.md`

Next safe action:

1. Preserve the public evidence-lifecycle rule in repo owners.
2. Move the long RFC and implementation prompt material to Obsidian staging.
3. Update or preserve cleanup-map refs before replacing tracked content.

## `docs/deepresearch/Resolver.md`

Status: `repo_stub_plus_obsidian`
Validation status: `diagnostic_only`

Public summary:

- Resolver means signal separation, peak splitting, or deconvolution depending
  on tool context; it is not a single universal product feature name.
- Resolver behavior is a pipeline decision point, not a final acceptance
  authority by itself.
- Raw/profile conversion, centroiding, smoothing, and thresholds can determine
  whether resolving succeeds; failures should not be attributed only to the
  resolver algorithm.

Repo sources of truth:

- `docs/product/presets.md`
- `docs/lcms-msms-evidence-rules.md`
- `docs/product/quantitation-context.md`

Next safe action:

1. Keep resolver public behavior in preset and evidence owners.
2. Move broad tool comparison and resolver taxonomy to Obsidian staging.
3. Preserve this path as a stub only while cleanup-map refs remain.

## `docs/deepresearch/software backfill.md`

Status: `repo_stub_plus_obsidian`
Validation status: `diagnostic_only`

Public summary:

- Mature backfill systems separate source discovery, re-entrant execution, and
  result observability.
- Durable backfill work needs input snapshots, idempotency, retry classes,
  resume/cache behavior, and execution artifacts.
- Backfill orchestration is not matrix write authority. It plans and runs work;
  product authority still belongs to the accepted evidence and export policy.

Repo sources of truth:

- `docs/product/backfill.md`
- `docs/product/run-provenance.md`
- `docs/product/productization.md`

Next safe action:

1. Keep system-design lessons in Backfill and run-provenance topics.
2. Move the long mature-tool case study to Obsidian staging.
3. Update or preserve cleanup-map refs before replacing tracked content.

## Shared Replacement Checklist

Before replacing any original Deepresearch file with a stub:

1. Copy the full source narrative to Obsidian staging.
2. Read back the staged note and verify title, summary, provenance, and source
   repo path.
3. Re-run exact path, relative link, and basename scans.
4. Confirm all stable public claims are present in the repo owners above.
5. Ask for explicit approval before tracked content replacement.
