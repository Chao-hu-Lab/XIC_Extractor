# Mature Boundary Source Audit

**Date:** 2026-06-04
**Status:** design input, no product mutation
**Scope:** OpenMS, MZmine, XCMS/centWave, Skyline references for LC-MS chromatographic boundary and area behavior.

## Why This Audit Exists

The selected-full-envelope path reached the correct current-branch gate:
`externalize`, not `production_ready`. The blocker is not just baseline.
Representative 8RAW rows show boundary/peak-selection uncertainty:

- `selected_envelope_narrower_than_resolver`
- `split_supported_review_required`
- `stronger_context_apex_outside_envelope`

This means local threshold tuning is unlikely to close the decision. We need to
realign the boundary owner with mature LC-MS tool behavior before more product
wiring.

## External Source Signals

### OpenMS

Reference:

- https://openms.de/documentation/classOpenMS_1_1ElutionPeakDetection.html
- https://www.openms.org/doxygen/release/3.0.0/html/classOpenMS_1_1PeakIntegrator.html
- https://pyopenms.readthedocs.io/en/latest/apidocs/_autosummary/pyopenms/pyopenms.PeakIntegrator.html

Relevant behavior:

- `ElutionPeakDetection` treats a mass trace as potentially containing several
  partly overlapping chromatographic peaks.
- It smooths intensities, finds local maxima/minima on the smoothed trace, and
  outputs split mass traces as chromatographic peak units.
- It uses expected chromatographic FWHM, width filtering, and S/N as filters.
- `PeakIntegrator` then integrates a peak from explicit left/right boundaries.
  Integration and background estimation are separate steps.

Design implication:

OpenMS does not make a single selected apex expand indefinitely until residual
baseline return and call that the product boundary. It first creates an
elution-peak unit, then integrates inside explicit bounds.

### MZmine

References:

- https://mzmine.github.io/mzmine_documentation/module_docs/featdet_resolver_local_minimum/local-minimum-resolver.html
- https://github.com/mzmine/mzmine/blob/master/mzmine-community/src/main/java/io/github/mzmine/modules/dataprocessing/featdet_chromatogramdeconvolution/minimumsearch/MinimumSearchFeatureResolver.java
- https://github.com/mzmine/mzmine/blob/master/mzmine-community/src/main/java/io/github/mzmine/modules/dataprocessing/featdet_chromatogramdeconvolution/savitzkygolay/SavitzkyGolayFeatureResolver.java

Relevant behavior:

- Local minimum resolver explicitly says overlapping or partly co-eluting
  features can be retained as one EIC before chromatogram resolving, and local
  minima are used to split shoulder LC peaks into individual features.
- Source code thresholds low points, searches for local minima in a window,
  checks apex-to-edge ratio, minimum height, duration, and data-point count.
- The Savitzky-Golay resolver uses smoothed derivative behavior to locate peak
  ranges and handles overlapped-peak states explicitly.

Design implication:

MZmine's local minimum path is not a universal quantitation answer, and its own
docs frame it as best for cleaner traces. But it still confirms that the unit
before area integration should be a resolved chromatographic feature segment,
not a residual envelope glued onto whatever resolver interval happened first.

### XCMS / centWave

References:

- https://github.com/sneumann/xcms/blob/devel/R/do_findChromPeaks-functions.R
- https://sneumann.github.io/xcms/reference/findChromPeaks-centWave.html
- https://rdrr.io/bioc/xcms/man/peaksWithCentWave.html

Relevant behavior:

- centWave first builds ROIs, applies CWT at expected peak-width scales, detects
  ridge-supported peaks, then descends to minima / tolerance-based boundaries.
- It records both original integrated area (`into`) and baseline-corrected area
  (`intb`).
- The source has two integration modes: one based on wavelet coefficients for
  peak-limit discovery and one using raw intensity descent. It then narrows RT
  boundaries and integrates the selected range.

Design implication:

CWT is not "only support" in the abstract. It can be a peak-segment generator
when paired with ROI, width, S/N, and descent/boundary logic. What should not
happen is allowing CWT, local minima, or residual baseline to be a single
unchecked authority.

### Skyline

Reference:

- https://skyline.ms/home/software/Skyline/wiki-page.view?name=tip_peak_calc

Relevant behavior:

- Skyline uses smoothed curves to place automatically calculated peak
  boundaries.
- It does not use smoothed data to calculate AUC. It calculates peak area from
  raw interpolated points within the chosen boundaries and subtracts background.

Design implication:

This strongly supports our existing raw-vs-morphology split: Gaussian15 or
SG-like traces can support boundary decisions and review overlays, but product
area should be raw/original XIC with explicit baseline/background handling.

## What This Says About Our Dead End

The current selected-envelope implementation is valuable as a diagnostic, but
it is trying to answer too much at once:

1. Which chromatographic peak is the selected peak?
2. Is the selected region a single full peak, a shoulder, or mixed peaks?
3. Should neighboring signal be merged, split, or externalized?
4. What exact RT boundary should be integrated?
5. How should the final raw-area baseline be subtracted?

Mature tools generally answer these with staged objects:

```text
raw XIC / mass trace
  -> smoothed or morphology trace
  -> chromatographic peak segments / resolved features
  -> model/evidence selection of the selected segment
  -> raw trace integration over explicit selected bounds
  -> baseline/background subtraction
```

Our current dead end comes from using:

```text
selected candidate apex
  -> residual-to-baseline envelope expansion
  -> row gate
  -> candidate product area
```

That path can recover simple flanks, but it is fragile for context-apex
conflict, shoulder/split cases, and cases where a resolver interval is wider or
narrower for reasons unrelated to true chromatographic identity.

## Recommended Pivot

Do not keep tuning selected-envelope stop constants as the next product move.

Introduce a bounded `ChromPeakSegment` / elution-peak candidate layer:

- Input: raw XIC plus one or more morphology traces such as Gaussian15, SG, CWT,
  local minima, and resolver interval.
- Output: one or more explicit chromatographic peak segments with apex, left,
  right, width, S/N, split/shoulder/conflict labels, and evidence sources.
- Selection: target/untarget model-selection chooses the segment using product
  evidence such as paired ISTD RT, MS1 shape, NL/MS2 opportunity, sample-level
  consistency, and untargeted hypothesis support.
- Integration: AsLS/raw-area integration happens only after the segment is
  selected.

This keeps the useful part of selected-full-envelope as an evidence source, but
demotes it from product boundary owner.

## 2026-06-04 Slice Closeout

The diagnostic-first slice was completed and partially promoted into a scoped
candidate source:

- `ChromPeakSegment` now enumerates explicit segment intervals from Gaussian15
  morphology and raw/AsLS residual.
- `tools/diagnostics/selected_envelope_plot_review.py` overlays proposed segment
  intervals against resolver and selected-envelope intervals.
- scored `region_first_safe_merge` extraction now sees `chrom_peak_segment`
  candidates; unscored and direct resolver paths remain unchanged.
- same-apex resolver candidates are upgraded to the segment boundary, while
  proposal-source evidence is preserved.
- `chrom_peak_segment` is projected as `chrom_peak_segment_context` in evidence
  semantics. It is boundary morphology context, not standalone authority.

Exit rule:

- Replace `selected_full_envelope` promotion gates with a segment-native gate.
- Keep `selected_full_envelope` as diagnostic/review evidence only.
- Promote segment-selected integration only if changed-row plots show improved
  boundaries without false neighbor/shoulder/carryover picks.
- If segment-native review cannot distinguish full normal peaks from neighboring
  peaks, stop and require expert/manual boundary oracle instead of adding more
  constants.
