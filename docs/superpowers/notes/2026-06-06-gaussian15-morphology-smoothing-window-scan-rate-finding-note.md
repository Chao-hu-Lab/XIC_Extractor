# Gaussian15 MS1 Morphology — Fixed-Point Smoothing Window Is Not Cross-Batch Time-Comparable

**Date:** 2026-06-06
**Status:** Finding / investigation input — **no code change.** Empirical caveat to
the 2026-06-05 gaussian15-ms1-morphology `production_ready` closeout; input for a
future deliberate, gated iteration.
**Relation:** confirms (with measurement) the window sub-claim of **S1** in
`2026-06-05-target-untargeted-method-scientific-review-note.md`.

## Finding

The product-facing primary area (`area_ms1_morphology` =
`gaussian15_positive_asls_residual`), promoted to `production_ready` on 2026-06-05,
integrates a Gaussian-smoothed positive AsLS residual using a **fixed 15-point
smoothing window** (`DEFAULT_GAUSSIAN15_WINDOW_POINTS = 15`, `ms1_morphology.py:9`;
kernel σ = window/6 in **points**, `_gaussian_kernel`, `ms1_morphology.py:151-161`).
A point-count window applies a **different temporal smoothing** to acquisitions with
different MS1 scan cadence.

Measured MS1 cadence (median Δrt between consecutive points of the extracted MS1 XIC
traces):

| Batch | median Δrt | ≈ rate | 15-pt window spans |
|---|---|---|---|
| 8RAW | 2.47 s | 0.41 Hz | **37.0 s** |
| 85RAW | 1.91 s | 0.52 Hz | **28.7 s** |

So the same reported-area definition smooths over **~37 s on 8RAW vs ~29 s on
85RAW** — a ~29% difference in smoothing time-width that comes purely from
acquisition cadence, not chemistry. Cross-batch area magnitudes therefore carry a
batch-dependent smoothing footprint.

Additionally, the cadence is **highly irregular within a single run** (observed Δrt
range ~0.23–2.5 s), consistent with a DDA method whose MS1 cadence varies with MS2
triggering. A fixed-point window therefore also spans a variable time-width
**within** a run, depending on where a peak sits relative to DDA activity.

## What this is and is not

- **Is:** an empirical confirmation that the just-promoted morphology area's
  smoothing time-width is not comparable across batches (and varies within a run).
  This is the measurable half of science-review S1's window sub-claim.
- **Is not:** a claim that the morphology area is biased in magnitude or "wrong."
  There is no concentration series / ground truth here to judge accuracy. Whether
  37 s vs 29 s smoothing materially changes integrated areas, and by how much, is
  **not** measured in this note.
- The 2026-06-05 closeout validated the morphology ↔ legacy-AsLS **ownership**
  transition (candidate gate + 8RAW boundary oracle + test suites). It did **not**
  test the window's cross-batch time-width consistency. This finding is orthogonal
  to that promotion's claims, not a refutation of them.

## Design tension to resolve before any change

`gaussian15_morphology_trace` is documented as **"Xcalibur-like Gaussian15"**
(`ms1_morphology.py:36`). Xcalibur/Genesis Gaussian smoothing is itself
**points-based**. So the intent matters:

- If the intent is **parity with Xcalibur's points-based 15G smoother**, the
  fixed-point window is faithful, and converting to a time-based window would
  *diverge* from Xcalibur. The cross-batch inconsistency would then be an inherited
  property of matching the instrument software.
- If the intent is **cross-batch-consistent internal smoothing**, a time-based
  window (σ in seconds → points = round(σ / local Δrt)) removes the cadence
  dependence by construction; given the within-run DDA irregularity, this should use
  **local** Δrt around each peak, not a global median.

This intent question is the fork, and it is the method owner's call.

## Why no code change now

`area_ms1_morphology` is the current, deliberately-promoted product area
(2026-06-05). Changing the smoothing window changes those just-gated values, so any
change must (a) resolve the Xcalibur-parity-vs-consistency intent above, and
(b) re-validate through the same boundary oracle + 8RAW/85RAW alignment gate the
promotion passed. That is a deliberate gated iteration, not a casual fix — out of
scope for this finding.

## Measurement provenance / limitations

- Δrt measured from the `rt` arrays of existing overlay `trace_data.json` artifacts:
  one representative file per batch — 8RAW
  `output/backfill_evidence_gate_8raw_20260605/changed_row_ms1_overlay_review_20260605/01_FAM000087_..._trace_data.json`
  (n=453 deltas); 85RAW
  `output/shared_peak_identity_v2_85raw_risk_closeout/family_ms1_overlay_fam005937_85raw/fam005937_85raw_trace_data.json`
  (n=6335 deltas). **Indicative, not exhaustive** — a fuller characterization would
  sample more files per batch and per RT region. The median difference and the
  within-run spread are robust enough to establish the cross-batch and within-run
  inconsistency qualitatively, not to quantify a per-peak area impact.

## Recommended next step (deferred)

If/when taken up: decide the Xcalibur-parity intent; if going time-based, implement
local-Δrt σ scaling; characterize the resulting area delta vs the current
fixed-point area on real data; re-run the boundary oracle + alignment gate; then
decide promotion. Ideally pair with a real dilution series to also settle the deeper
S1 question (smoothed-residual-as-area vs integrate-raw accuracy), which the current
single-concentration ISTD data cannot.

## Key files
- `xic_extractor/peak_detection/ms1_morphology.py:9` (`DEFAULT_GAUSSIAN15_WINDOW_POINTS=15`),
  `:36` ("Xcalibur-like Gaussian15"), `:51-66` (`positive_residual_area`, negative clip),
  `:151-161` (`_gaussian_kernel`, σ in points)
- `xic_extractor/extractor.py:108-115` (`reported_peak_area` prefers `area_ms1_morphology`)
- `docs/superpowers/notes/2026-06-05-gaussian15-ms1-morphology-production-ready-closeout.md` (the promotion)
- `docs/superpowers/specs/2026-04-13-area-support-design.md:265-268` (original raw-area rationale: "smoothed would underestimate")
- `docs/superpowers/notes/2026-06-05-target-untargeted-method-scientific-review-note.md` (S1)
