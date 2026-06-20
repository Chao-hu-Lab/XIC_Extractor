---
name: xic-overlay-visualization
description: Use when designing, generating, reviewing, or fixing XIC/LC-MS overlay plots, chromatogram overlays, source-successor differential figures, smoothing/trace visuals, annotation layers, or PNG/HTML visual evidence used for Backfill, Discovery, review, or product-gate interpretation.
---

# XIC Overlay Visualization

Use for the overlay figure itself, before Gallery layout or product-gate claims:
make XIC/MS1/MS2 evidence readable without turning diagnostics into authority.

## Overlay Contract

Before drawing, state:

- review lens: Backfill context, Discovery identity, Authority boundary,
  QC/debug, tutorial, or product-gate evidence;
- trace semantics: what each color/line represents;
- coordinate identity: sample, row/hypothesis, m/z, RT window, smoothing, and
  normalization;
- expected comparison: same row, source versus successor, same samples, or
  nearby context;
- authority boundary: diagnostic, review support, or product-gate evidence.

## Drawing Rules

- Use high-contrast role colors; quiet context traces below decision traces.
- Label trace meaning, not just color.
- Disclose smoothing: raw trace, Gaussian15, Savitzky-Golay, baseline, or
  normalized intensity.
- Keep plot text sparse; move long counts, RT ranges, paths, and instructions
  outside the axes.
- Keep annotations close to the visual feature they explain; do not cover peaks.
- Avoid floating pins that detach under zoom, browser comments, or mobile width.
- Do not show derived summary traces such as rescued medians by default in
  Backfill review overlays. If a summary trace is useful, make it a QC/debug
  view and label it as derived, not sample evidence.
- For Discovery differential overlays, source/successor m/z need not match; the
  comparison is row identity explaining the same samples.
- Do not mix MS1 visual context, CID/MS2 tag evidence, candidate state, and
  matrix authority into one visual conclusion.

## Verification

After generation, inspect the actual artifact:

- image is nonblank and uses the intended assets/data;
- legend/trace count/labels match plotted lines;
- annotations do not overlap key peaks, axes, legend, or each other;
- desktop and mobile/browser screenshots have no horizontal overflow or covered
  content when embedded in HTML;
- retained artifacts follow `xic-validation-artifact-retention`.

## Calibration Loop

First real use of this skill must be treated as calibration. Generate one real
overlay, review it against this contract, record which checks failed, then
tighten this skill or the plotting owner. Do not assume this v1 guidance is
enough until it has survived a real overlay review.

## References

- Trace semantics, smoothing, differential overlay, and annotation rules:
  `references/overlay-figure-contract.md`
- Verification and calibration checklist:
  `references/overlay-verification.md`
- Trigger and near-neighbor cases:
  `evals/trigger-cases.md`
- Portable skill interface metadata:
  `agents/interface.yaml`
