# Overlay Figure Contract

## Review Lens

Choose one primary lens:

- Backfill context: does the current row/sample decision have reasonable MS1
  context near the expected RT window?
- Discovery identity: which row identity better explains the same samples?
- Authority boundary: what evidence can enter review versus product authority?
- QC/debug: why a plotted signal, extraction, smoothing, or annotation failed.
- Tutorial: how a human should learn to read the visual surface.

## Trace Semantics

Every plotted line should have meaning that can be stated without relying on
color alone:

- source/current hypothesis;
- successor/alternative hypothesis;
- nearby context signal;
- blank/control/reference;
- raw trace versus smoothed trace.

For each overlay, preserve or state sample identity, row/hypothesis identity,
m/z, RT window, smoothing, normalization, and provenance path.

Default review overlays should favor real sample traces over derived summaries.
Do not draw median/consensus traces by default for Backfill human review,
because they can look like primary evidence while hiding sample disagreement.
Use them only in an explicit QC/debug lens and label them as derived.

## Smoothing And Intensity

Smoothing is a reading aid, not evidence inflation. If the plot uses Gaussian15,
Savitzky-Golay, baseline correction, normalization, or max scaling, the guide or
legend must say so. Do not describe a smoothed curve as raw signal.

## Differential Overlay

For source/successor overlays:

- source and successor are different row identities;
- m/z does not need to match;
- compare how each identity explains the same samples;
- show sample pattern or provenance when the visual claim depends on batch-level
  support;
- avoid implying a single pretty peak proves mapping.

## Annotation Discipline

Annotations should clarify, not decorate:

- use high-contrast role colors, with context lines de-emphasized relative to
  the decision traces;
- place text near the feature it explains;
- avoid covering peak apex, RT window, axes, legend, or other labels;
- prefer direct labels and small callouts over detached numbered pins;
- move long counts, RT ranges, and instructions outside the axes;
- keep tutorial graphics clean enough that the intended pattern is visible.

## Authority Boundary

Overlay evidence can support review conclusions. It cannot directly create
ProductWriter authority, default matrix writes, activation changes, or row
promotion without an explicit product-gate contract.
