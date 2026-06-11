# Biological ISTD RT Envelope And Drift-Aware Backfill Review Spec

Date: 2026-05-21

## Summary

This spec defines an audit-only biological ISTD RT envelope diagnostic and its
use as context for RT x MS1 backfill cross-evidence.

The goal is to quantify normal RT movement in the biological matrix before
calling a rescued-heavy family true neighboring interference. RT variation alone
must not be a one-strike blocker.

## Scope

In scope:

- Build empirical RT envelopes from biological-sample ISTD rows.
- Use injection-order-aware, target-specific RT models.
- Report per-target residual envelopes and row-level residual status.
- Feed ISTD envelope context into RT x MS1 backfill cross-evidence.
- Split neighboring-interference review into drift-explainable C1 and
  unresolved C2.

Out of scope:

- No production matrix mutation.
- No targeted reliability change.
- No scoring, resolver, or backfill behavior change.
- No RT correction of raw matrices.
- No DNP normalization change.

## Biological ISTD RT Envelope

Input:

- `biological_qc_istd_drift_rows.tsv`

Required columns:

- `sample_name`
- `injection_order`
- `target_label`
- `rt_min`
- `reliability_state`

Output:

- `biological_istd_rt_envelope_rows.tsv`
- `biological_istd_rt_envelope_targets.tsv`
- `biological_istd_rt_envelope_summary.tsv`
- `biological_istd_rt_envelope.json`
- `biological_istd_rt_envelope.md`

Stable ISTD anchor requirements:

- at least 5 usable benchmark-eligible RT points;
- eligible fraction at least 0.80;
- no hard manual false-positive / wrong-peak / targeted-negative marker on any
  row for that target;
- target-specific RT model can be fit.

RT model:

- Use a robust Theil-Sen-style slope estimate over injection order.
- Use residuals after the robust target-specific model.
- Use robust residual limits to avoid a single bad point widening the normal
  envelope.

Interpretation:

- Large raw RT range is a warning, not a failure.
- A feature can have high raw RT drift but small residuals after
  injection-order modeling.
- Normal RT should be defined from biological ISTD residual behavior, not from a
  single fixed tolerance.

## Drift-Aware Cross-Evidence

The RT x MS1 cross-evidence diagnostic may accept
`biological_istd_rt_envelope_targets.tsv` as optional input.

When the seed-aware MS1 layer says `neighbor_interference_review`:

- If local RT support is dominant, no RT transfer conflict exists, and the
  supporting ISTD has a stable biological residual envelope, classify as
  `rt_supported_ms1_interference_drift_explainable_review` and grade as
  `C1_drift_explainable_interference_review`.
- If local RT support is absent or no supporting ISTD envelope exists, keep it
  as `C2_manual_review_interference`.

Dominant RT support means support has concentration, not just one positive cell:

- `rt_supported_cell_count >= 3`;
- `rt_supported_cell_count / rt_total_cell_count >= 0.10`;
- `rt_conflict_cell_count == 0`.

`high_raw_drift` is an annotation, not the C1 gate. C1 requires a residual
envelope (`normal_abs_residual_min` and `warning_abs_residual_min`) because the
point is to avoid treating normal biological RT movement as a one-strike
interference blocker.

C1 does not mean production-approved. It means the interference label should be
treated as review context rather than a one-strike blocker.

## Current 85RAW Evidence

The 2026-05-21 85RAW run shows:

- 7 stable biological ISTD anchors.
- All stable ISTD anchors have high raw RT drift (`rt_range_min >= 0.60`).
- `d3-N6-medA` has raw RT range about 2.119 min but remains a stable anchor
  after injection-order modeling.
- RT x MS1 cross-evidence with envelope context splits previous Grade C:
  - `C1_drift_explainable_interference_review`: 2 families.
  - `C2_manual_review_interference`: 3 families.

## Product Implication

Future production-gate planning can consider Grade A/B first. C1 may become a
manual-review promotion candidate only after overlay review confirms that the
interference is drift-explainable rather than true neighboring peak overlap.

Grade C2 remains blocked from automatic production escalation.
