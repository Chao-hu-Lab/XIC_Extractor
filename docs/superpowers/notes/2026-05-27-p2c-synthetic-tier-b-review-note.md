# P2c Synthetic Tier B Review

**Date:** 2026-05-27  
**Scope:** Review the locked synthetic Tier B benchmark after P2c smoke produced
`NO_GO_KEEP_LINEAR_EDGE`.

## Verdict

The current Tier B result should be treated as **synthetic gate design failure /
fixture-scope mismatch**, not as proof that AsLS is scientifically worse than
linear-edge on the real selected ISTD evidence.

The diagnostic implementation is doing what the current spec asks, but the spec
and fixture design are over-scoped for the actual P2c question.

## Reproduced Evidence

Current P2c c1b-plan smoke:

- `gate_decision=NO_GO_KEEP_LINEAR_EDGE`
- `benchmark_status=FAIL`
- `heldout_row_count=275`
- `hard_blocker_count=30`
- `coverage_status=PASS`
- `max_asls_raw_area_exceedance_count=0`
- `max_negative_nonblank_area_count=0`
- `blank_false_positive_rate=0.542857`

Row-level hard blockers are narrow:

- 19 rows have `failure_reasons=blank_false_positive`
- all 19 are `blank_noise_control`
- no row-level `asls_exceeds_raw_area`
- no row-level `asls_negative_nonblank_area`

The other 29 hard blockers are aggregate synthetic rules, not row-level physical
impossibility findings.

## Main Findings

### 1. Tier B Uses Classes That Tier A Did Not Observe

Tier A selected-family evidence maps
`linear_edge_over_subtraction_plausible` to:

- `sloped_baseline_peak`
- `hump_baseline_peak`
- `tailing_peak`
- `adjacent_shoulder`
- `flat_peak_control`

But Tier B hard-blocks C1b planning on all heldout classes, including:

- `coeluting_interference`
- `heteroscedastic_noise_peak`
- `local_baseline_dip`
- `low_sn_peak`
- `saturated_or_clipped_apex`
- `blank_noise_control`

Those may be useful stress tests, but they are not all Tier A-observed selected
ISTD failure modes. They should not automatically block C1b planning for the
specific baseline-retirement question.

### 2. Synthetic Bounds Are Too Wide And Not Production-Like

Tier A real selected ISTD audit:

- boundary width min/median/max: `0.1963 / 0.4157 / 1.8689 min`
- trace points min/median/max: `4 / 11 / 45`

Tier B heldout synthetic fixtures:

- every heldout row uses `64` integration points
- boundary width min/median/max: `0.32 / 0.704 / 1.28 min`
- median boundary width is about `15 sigma`

This overexposes every synthetic integration to baseline, noise, blank humps, and
transients. It especially inflates blank and low-S/N failures. The synthetic
lock should derive bounds from the observed Tier A point-count/width
distribution instead of using fixed 64-point windows.

### 3. `coeluting_interference` Tests Deconvolution, Not Baseline

For `gaussian_with_interference_v1`, the synthetic generator sets:

- target truth = main Gaussian only
- interference peak = nuisance
- observed intensity = target + nuisance + baseline + noise

Baseline integration does not deconvolve coeluting peaks. Expecting AsLS to match
main-peak-only truth in this class is testing peak purity/deconvolution, not
baseline correction. This class should be moved to a boundary/peak-purity audit
or have truth defined as the full integrated signal inside the accepted boundary
when used for baseline validation.

### 4. Low-S/N Narrow Rows Dominate Several Aggregate Failures

Heldout low/narrow rows often have only about `1.57` sigma per scan. Those rows
drive large p95 relative-error failures across otherwise relevant classes. This
is a useful stress condition, but it should not be mixed into the same hard gate
as production-like selected ISTD evidence unless real Tier A/Tier C evidence
shows comparable under-sampled peaks are in scope.

### 5. Blank Safety Is Real, But Current Synthetic Blank Gate Is Too Strong For C1b

Synthetic blank false positives are real in the current benchmark:

- 19 / 35 blank rows are false-positive by the current threshold
- heldout blank false-positive rate is `54.2857%`
- failures concentrate in `hump_blank`, `carryover_like_blank`,
  `high_noise_blank`, and some `sloped_blank`

This should block linear-edge retirement until real blank/carryover safety is
resolved. It should not by itself block a C1b planning step whose real Tier A
evidence did not include blanks and whose current purpose is baseline method
replacement for selected ISTD peaks.

## Recommended Redesign

Split Tier B into two layers.

### Tier B1: Relevance Gate For C1b Planning

Use only fixture classes justified by Tier A selected-family evidence:

- `flat_peak_control`
- `sloped_baseline_peak`
- `hump_baseline_peak` only after confirming the synthetic hump matches the real
  observed morphology
- `tailing_peak`
- `adjacent_shoulder`

Use production-like bounds:

- point-count and RT-width strata derived from Tier A selected ISTD quantiles
- no fixed 64-point heldout windows
- explicit scan-density strata; under-sampled rows can be retained as stress
  rows but should not silently dominate the hard gate

Hard blockers should stay strict for physical impossibilities:

- AsLS area exceeds raw area
- negative nonblank corrected area
- wrong RT identity or unacceptable boundary expansion

Relative-error thresholds should be applied to production-like strata first,
then reported separately for stress strata.

### Tier B2: Stress / Retirement Safety Audit

Keep these classes as diagnostic/stress evidence, not C1b planning blockers:

- `blank_noise_control`
- `coeluting_interference`
- `local_baseline_dip`
- `heteroscedastic_noise_peak`
- `low_sn_peak`
- `saturated_or_clipped_apex`

Use them to decide what Tier C evidence is required before retirement:

- real blank/carryover review for blank safety
- boundary/peak-purity review for coelution
- low-S/N or clipping review only if real data shows these are common selected
  integration states

## Practical Conclusion

Current P2c `NO_GO_KEEP_LINEAR_EDGE` is deletion-safe, but scientifically too
broad. It should not be used to argue that linear-edge is better than AsLS on the
reviewed ISTD peaks.

Next action: revise the P2c spec/fixture lock into a two-layer Tier B gate before
using it as a C1b planning blocker.
