# Backfill Expansion Peak-Mode Decomposition v1

Status: `diagnostic_only_peak_mode_decomposition`.

This artifact decomposes the current 666-cell Backfill expansion packet by
sample-local apex RT relative to the detected/reference mode for each feature
family. It is intended to catch cases where one provenance family actually spans
multiple visible MS1 peak modes.

## Method

For each family:

1. Use detected overlay traces to estimate a reference mode center RT.
2. Classify candidate cells as:
   - `target_mode`: apex within +/- `0.30 min` of the reference mode center;
   - `off_target_early`: apex before that target window;
   - `off_target_late`: apex after that target window;
   - `missing_apex`: no sample-local apex evidence.
3. Flag boundaries that cross into the target window from another mode.
4. Add diagnostic sample-subtype context from filename prefixes
   (`Tumor`, `Normal`, `Benignfat`, `QC`). Same-subtype apex RT span above
   `0.50 min` is flagged as `review_same_subtype_rt_incoherence`.

This is a diagnostic decomposition, not a product gate. It does not decide
matrix write authority.

Important interpretation rule: this global RT-mode screen is only the first
layer. For the same `PeakHypothesis`, RT should usually be tighter within a
sample subtype than across different subtypes. A same-subtype outlier is more
suspicious for wrong-peak or boundary failure. A Tumor/Normal/Benignfat shift
can be biologically or matrix-context plausible, but it still needs its own MS1
peak, same-peak support, boundary, tag/source provenance, and later
expected-diff authority before writing.

## Current 666-Cell Result

- target-mode cells: 602;
- off-target early cells: 48;
- off-target late cells: 16;
- boundary-bridge cells: 133;
- same-subtype RT-incoherent cells at the `0.50 min` diagnostic window: 178;
- mixed target/off-target families: 16;
- off-target-only families: 1;
- target-mode-with-boundary-bridge families: 3.
- families with same-subtype RT incoherence: 11;
- families without same-subtype RT incoherence under this screen: 9.

These counts are intentionally screening-oriented. They say where hypothesis
split/remap is needed before product authority; they do not say every mixed
family is wrong.

## Subtype-Aware Full-Scope Result

Applying the subtype-aware rule to all 20 families does work as a triage screen,
but the observed pattern is not a clean Tumor-vs-Normal-vs-Benignfat shift. At
the `0.50 min` same-subtype window, 11 families still contain large RT spread
inside at least one subtype:

`FAM000736`, `FAM009739`, `FAM016144`, `FAM016893`, `FAM017098`,
`FAM020411`, `FAM021673`, `FAM021983`, `FAM026285`, `FAM027946`, and
`FAM030550`.

The remaining 9 families are subtype-context-only in this screen:

`FAM003973`, `FAM009937`, `FAM012491`, `FAM015713`, `FAM018996`,
`FAM025210`, `FAM027885`, `FAM028502`, and `FAM030972`.

The compact subtype split review queue is
`backfill_expansion_peak_mode_decomposition_subtype_split_review.tsv`. It
collapses the 178 flagged cells into 18 `family + sample_subtype` review
groups:

- 16 groups: `review_split_modes_and_boundaries`;
- 2 groups: `review_split_same_subtype_modes`.

The compact split decision packet is
`backfill_expansion_peak_mode_decomposition_split_decisions.tsv`. It routes
the same 178 flagged cells into product-relevant diagnostic buckets:

- 112 cells: clean `target_mode` candidates that can only feed the later full
  evidence chain;
- 37 cells: `target_mode` cells with boundary-bridge review still required;
- 29 cells: off-target cells that must be held or remapped;
- 0 cells: missing or unclassified in this screen.

Decision status distribution:

- 13 groups: `split_hold_off_target_and_review_boundaries`;
- 5 groups: `split_hold_off_target_keep_clean_target_candidates`.

Interpretation: this rule can split other families in the same way as
`FAM017098`, but it is still not an automatic rescue. Clean target candidates
must pass the full evidence chain; boundary-bridged target cells and off-target
cells cannot become ProductWriter authority from this artifact.

## FAM017098 Interpretation

`FAM017098` is not a simple threshold failure. It contains two visible RT
regions:

- early/off-target apex cells around 14.67-14.91 min;
- target-mode apex cells around the detected/reference mode centered at
  15.3255 min.

Current decomposition:

- target-mode cells: 7;
- off-target early cells: 4;
- off-target late cells: 0;
- boundary-bridge cells: 3.

Manual Xcalibur review on 2026-06-22 adds a reviewer overlay in
`fam017098_peak_mode_manual_review.tsv`:

- `TumorBC2264_DNA`, `TumorBC2294_DNA`, `TumorBC2290_DNA`, and
  `BenignfatBC0980_DNA` are left/early peak cells and should be held or split
  to a left-peak hypothesis, not promoted as the 15.3 min target mode.
- `BenignfatBC1108_DNA` is a right/target peak case, but the current boundary
  spans the left region and needs boundary review before activation.
- `BenignfatBC1152_DNA` and `NormalBC2287_DNA` are right/target peak cases;
  `BenignfatBC1152_DNA` still needs boundary attention because nearby earlier
  peaks exist.

This explains why the selective shift-aware gate held the family: the current
sample-local provenance bucket does not separate the 14.x and 15.3 min
hypotheses. The next method step is not automatic activation; it is remapping
or splitting the candidate evidence, plus boundary correction and
subtype-aware RT-coherence review, so only review-supported target-mode cells
can feed the later selective gate.

Diagnostic plot:
`output/validation/backfill_expansion_peak_mode_decomposition_v1/FAM017098_peak_mode_decomposition.png`

## Authority Boundary

This artifact writes compact summary/checks/manifest files under
`docs/superpowers/validation/` and the full cell map under `output/validation/`.
It does not change:

- default matrix;
- ProductWriter authority;
- workbook or GUI;
- selected peak, selected area, or counted detection;
- active product tier or active lane.
