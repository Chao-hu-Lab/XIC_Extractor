# P6 — RT Correction OBI-Warp Shadow Spec

**Date:** 2026-05-24
**Status:** Diagnostic slice draft v0.1
**Overview:** [Peak pipeline modernization overview](2026-05-24-peak-pipeline-modernization-overview-spec.md)
**Precondition:** A broader RT diagnostic or redesigned external-reference audit
indicates that anchor-based LOESS / current RT correction is the bottleneck with
a quantitative gate. The preferred trigger is internal evidence: anchor-sparse
rows show materially higher RT residuals, selected-family RT errors exceed the
same-peak tolerance, or RT residual explains a meaningful share of boundary /
match disagreement. P3 may contribute evidence, but P3 is not required and does
not automatically schedule P6. Without a recorded threshold, P6 is not
scheduled.

## Purpose

If triggered, introduce pyOpenMS OBI-Warp (Prince & Marcotte 2006) as a shadow
non-linear RT correction path. The current production RT correction is
anchor-based:
ISTDs and known targets feed `rt_normalization.fit_sample_rt_models`, which
produces a per-sample linear / piecewise / LOESS-interpolated model. Outside
the anchor density region the model degrades to extrapolation.

OBI-Warp performs dynamic time warping on chromatographic landmarks across
samples, producing a non-linear warp that does not depend on labeled
anchors. In anchor-sparse RT regions OBI-Warp is expected to outperform the
LOESS path.

This spec keeps OBI-Warp shadow-only: it produces an audit table comparing
LOESS and OBI-Warp predicted RTs against observed RTs, without touching
production alignment.

## Current State

- `xic_extractor/alignment/rt_normalization.py:9-50` defines the dataclasses
  `AnchorPoint`, `RtKnot`, `SampleRtModel`, and `AnchorResidual`
- `xic_extractor/alignment/rt_normalization.py:53-98` implements
  `apply_anchor_reference_source` (entry point for normalizing anchor
  references by `target-window`, `observed-median`, `injection-local-median`,
  or `injection-loess` source)
- `xic_extractor/alignment/rt_normalization.py:243-306` implements
  `fit_sample_rt_models` (fits a `SampleRtModel` per sample)
- fitted `SampleRtModel.model_type` values in current code are `shift`
  (one-anchor model), `affine` (normal linear fit), and `piecewise`.
  `injection-loess` is a reference-source mode accepted by
  `apply_anchor_reference_source`, not a fitted model type.
- consumers: `alignment/pipeline.py`, alignment cluster compatibility checks,
  family RT centering
- there is no chromatogram-level warping (DTW-style); RT correction is a
  per-sample scalar transform applied to peak coordinates

## Required Adapter

Add `tools/diagnostics/rt_correction_obiwarp_shadow.py`:

- accept the same input as alignment: discovery candidates, raw paths, the
  anchor manifest
- for each pair of (sample, reference), run pyOpenMS
  `MapAlignmentAlgorithmOBIWarp` against the corresponding mzML or in-memory
  feature map
- collect per-sample `(observed_rt -> warped_rt)` mapping
- apply the warp to each `AnchorPoint` and each rescued cell's `apex_rt`
- emit `output/rt_correction_shadow_<dataset>.tsv` with columns:
  - `sample_stem`
  - `target_label`
  - `rt_observed_min`
  - `rt_loess_corrected_min` (current production output)
  - `rt_obiwarp_corrected_min` (shadow)
  - `rt_reference_min`
  - `rt_residual_loess_min`
  - `rt_residual_obiwarp_min`
  - `residual_delta_sec` (loess residual - obiwarp residual, in seconds)
  - `anchor_density_around_rt` (number of anchors within +/- 1 min)

## Validation Use

Decision evidence per target / per sample:

- `residual_delta_sec > 0` means OBI-Warp is closer to reference than LOESS
- `residual_delta_sec < 0` means LOESS is closer
- group rows by `anchor_density_around_rt` band to see whether OBI-Warp's
  advantage is concentrated in anchor-sparse zones (the predicted failure
  mode for LOESS)

The diagnostic produces a summary report with these aggregates, recorded
under `docs/superpowers/notes/2026-MM-DD-rt-correction-obiwarp-shadow-findings.md`:

- median absolute residual per method, overall and per anchor-density band
- count of `loess_better`, `obiwarp_better`, `tied_within_1_sec` rows
- worst-case residuals per method

## Promotion Decision

Promotion of OBI-Warp to production is not in this spec. Promotion needs:

- a separate spec under `2026-MM-DD-peak-pipeline-rt-correction-obi-warp-promotion-spec.md`
- evidence from this shadow run that OBI-Warp residual is consistently lower
  in anchor-sparse zones
- a compatibility plan for the existing `SampleRtModel` consumer surface
  (alignment cluster compatibility checks use `rt_min` directly; the warp
  result needs to be expressed through the same model contract)

## Dependency Plan

- `pyopenms` is the only new dependency. It has prebuilt wheels for Windows /
  macOS / Linux on Python 3.9-3.13.
- install in an isolated diagnostics venv by default, or declare an optional
  diagnostics extra with import guards. Do not add pyOpenMS to the mandatory
  production environment in P6.
- the diagnostic script must fail with an actionable message when pyOpenMS is
  unavailable, while normal production imports and runs continue to work
  without pyOpenMS installed.

## What This Spec Does Not Change

- production RT correction model fit
- alignment cluster compatibility behavior
- targeted reliability state
- matrix identity output
- any TSV schema other than the new diagnostic file
- the `AnchorPoint` / `SampleRtModel` / `apply_anchor_reference_source` API

## Rollback / Removal

Remove the diagnostic script and delete the isolated diagnostics venv (or
remove the optional diagnostics extra). No production change to revert.

## Open Questions

- pyOpenMS OBI-Warp consumes feature maps or MS1 maps. The in-house pipeline
  works with discovery candidates plus on-demand XIC. The adapter needs to
  decide: (a) export sample-level feature maps from internal data and feed
  those, or (b) re-run pyOpenMS feature finding from mzML. Option (b) is
  simpler but more expensive.
- How dense should the OBI-Warp pre-feature map be? Sparse maps yield poor
  warps; dense maps reproduce vendor centroiding artifacts. Default plan:
  use pyOpenMS `FeatureFindingMetabo` with default parameters, document the
  choice, do not tune in v0.1.
- Reference sample selection: which sample is the warp reference? Options:
  - pooled QC if available
  - injection-order median
  - manually selected anchor sample
  Default: injection-order median; record the choice in the diagnostic
  report.
- For samples where OBI-Warp fails to produce a finite warp (e.g., very
  sparse feature maps), emit `rt_obiwarp_corrected_min = None` and label
  the row `obiwarp_unavailable` in the diagnostic; do not drop the row.

## Cleanup Hook

Same constraints as P3 — diagnostic code isolation:

- pyOpenMS OBI-Warp adapter lives under `tools/diagnostics/`. Production
  `xic_extractor/alignment/` does not import from it.
- the shadow output TSV is consumed only by humans / methodology reviewers;
  no production module reads it.
- pyOpenMS must remain optional in P6. A later promotion or shared-tooling
  spec may decide to add it to the main dependency set, but this shadow
  diagnostic should not widen the production install footprint.

## Acceptance Owner

Diagnostic report reviewed by methodology owner. Findings note recorded.
Promotion decision (yes / no) is a separate spec.
