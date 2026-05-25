# P4 — Area Uncertainty Formula Correction Spec

**Date:** 2026-05-24
**Status:** Audit-only correction implemented and 8RAW-validated on 2026-05-25
**Overview:** [Peak pipeline modernization overview](2026-05-24-peak-pipeline-modernization-overview-spec.md)
**Parallel to:** P3, P5

## Purpose

Replace the in-peak first-difference MAD formula used for `area_uncertainty`
with a baseline-residual noise propagation formula. The current formula
conflates real signal slope with measurement noise, so clean tall peaks
report higher uncertainty than noisy short peaks, which is the inverse of
the intended semantics.

This is an audit-only correction. No production area or matrix decision
depends on `area_uncertainty`.

## Current State

`xic_extractor/peak_detection/baseline.py:67-79` computes:

```text
diffs = np.diff(segment)
mad   = median(|diffs - median(diffs)|)
return mad * duration_seconds
```

`segment` is the peak interval slice of `intensity_values`. On the rising and
falling edges, `diffs` is dominated by the true signal slope, not by noise.
A tall narrow Gaussian gives a large MAD, so `area_uncertainty` grows with
peak height even when the underlying baseline noise is identical.

`area_uncertainty` is consumed by `peak_detection/integration_audit.py:64-77`
as `uncertainty_fraction = area_uncertainty / raw_area` and emitted in
`alignment_cell_integration_audit.tsv` plus the area uncertainty diagnostic
report.

`area_uncertainty` is not consumed by:

- `peak_scoring.py` severity gates
- selection / candidate ranking
- matrix identity / alignment decisions
- targeted reliability state

## Required Change

Replace the formula with baseline-residual noise propagation:

```text
noise_per_scan = baseline_residual_mad           # estimated from the trace
scan_period_s  = median_rt_step_minutes * 60.0   # already computed elsewhere
n_points       = right_index - left_index
area_uncertainty = noise_per_scan * scan_period_s * sqrt(n_points)
```

`baseline_residual_mad` source options (default first):

1. **Default — audit self-compute.** Inside the integration audit summary
   builder, compute AsLS baseline on the trace using
   `xic_extractor/baseline.py:asls_baseline`, then compute residual MAD as
   `median(|residual - median(residual)|)` where `residual = intensity -
   baseline`. This is the cheapest reliable path: integration_audit already
   has access to `rt_values` and `intensity_values`, and AsLS is O(n) per
   iteration.
2. **Optional optimization — reuse cached AsLS.** If the AsLS Cache Strategy
   (see below) has already produced a per-trace AsLS baseline (because
   `compute_local_sn_cache` or P2's `integrate_asls_baseline` ran first),
   reuse it. The cache key is per-trace; the cache lookup is the only
   coupling between scoring path and audit path.
3. **Fallback — pre-peak window MAD.** If AsLS fails (trace has fewer than
   five finite points, or `spsolve` raises), estimate noise from the MAD of
   intensity values in a baseline-only window adjacent to the peak (e.g. 10
   scans before `peak_start_rt`). Do not use in-peak `diff` MAD as a
   fallback; that is the broken formula this spec removes.

Plumbing note: option 1 keeps the audit path self-contained. Option 2 is a
performance optimization, not a correctness requirement. Option 3 is
documented for completeness; it should fire on less than 1% of cells in
typical LC-MS data.

### AsLS Cache Strategy (shared with P2)

P4 and P2 fit AsLS on the same trace. Without coordination, AsLS would be
recomputed for every audit row. P2 defines a per-trace AsLS cache (see P2
spec, "AsLS Cache Strategy" section). P4 must consult that cache before
falling back to its own AsLS fit:

- if the cache contains `(baseline_array, residual_mad)` for the current
  trace, use the cached `residual_mad` and skip the AsLS fit in P4
- if the cache is empty, P4 computes AsLS (option 1 above) and populates the
  cache so any later P2 call on the same trace can reuse it
- the cache lifetime is the same scope as the `CellIntegrationAuditSummary`
  builder; do not introduce a module-level singleton

The implementation must:

- not raise on traces too short to fit AsLS (return `area_uncertainty = None`)
- not raise on `scan_period_s <= 0` (return `area_uncertainty = None`)
- preserve the `BaselineIntegration` and `CellIntegrationAuditSummary`
  field names — only the value semantics changes
- emit enough provenance for downstream readers to distinguish the new formula
  from the legacy in-peak-diff formula. This provenance must be TSV-local
  because `alignment_cell_integration_audit.tsv`, `peak_candidates.tsv`, and
  `peak_candidate_boundaries.tsv` have no run-metadata channel today.
  Required additive fields next to any emitted `area_uncertainty` value:
  - `area_uncertainty_formula_version`
  - `baseline_residual_mad` or an equivalent reproducibility field
  The validation note must state the exact formula version string and columns
  emitted.

## Validation Contract

Run the area integration uncertainty audit on 8RAW before and after the
change:

1. Compute the per-ISTD distribution of `area_uncertainty` and
   `uncertainty_fraction` under both formulas
2. Confirm that the new `area_uncertainty` is monotonically related to
   `peak_above_baseline / mad` and not to apex height
3. The audit classification labels (`area_consistent_low_uncertainty`,
   `boundary_sensitive`, `high_uncertainty`, etc.) may shift counts; record
   the before / after counts in the validation note
4. `unexplained_area_mismatch` must remain 0

## Backward Compatibility

`area_uncertainty` consumers downstream of the audit TSV may have hardcoded
thresholds. Known consumers:

- `tools/diagnostics/area_integration_uncertainty_audit.py` classification
  thresholds — review and adjust thresholds with the new formula
- `docs/superpowers/specs/2026-05-18-area-integration-uncertainty-decision.md`
  — record that the formula changed; the prior decision's evidence labels
  are now interpreted under the new scale

The TSV column itself is a public contract. Keeping the name
`area_uncertainty` is a compatibility decision, not proof that the change is
internal. P4 must include a formula-version / compatibility note and must
review known downstream thresholds before landing.

## What This Spec Does Not Change

- `area_raw_counts_seconds`
- `area_baseline_corrected`
- `baseline_score`
- existing required field names in TSV output; additive TSV-local provenance
  columns are allowed as described above
- scoring, selection, alignment, or matrix decisions

## Rollback Condition

Revert the formula change by restoring the prior `np.diff` based computation
if:

- the audit classification thresholds cannot be re-tuned to give actionable
  labels under the new scale (i.e. all rows classify into one bucket)
- the new formula returns `None` for more than 30% of detected cells

## Open Questions

- Should the `noise_per_scan` be sampled per-trace (one AsLS fit per
  chromatogram) or per-interval (one fit per peak interval)? The first is
  cheaper and correct in principle; the second is what the current code does
  for `compute_local_sn_cache`.
- Should the spec also emit a per-cell `baseline_residual_mad` audit column
  so the new uncertainty value can be reproduced by review?
- Is `sqrt(n_points)` the right propagation? It assumes scan-to-scan noise
  independence. For high-density mass traces with vendor smoothing already
  applied, neighbor scans are correlated. The spec records this assumption
  but does not try to estimate the correlation length in v0.1.

## Cleanup Hook

Implementation should keep the formula change self-contained so Phase 2 C5
(area integration single entry) can absorb it cleanly:

- the new uncertainty formula must live inside whatever helper computes
  area + uncertainty together. Do not split residual_mad computation across
  multiple modules. C5 will merge this into `integrate_peak_region`; a
  scattered implementation makes C5 harder.
- do not rename `BaselineIntegration.area_uncertainty`. C5 expects the same
  semantic field on the unified return type, even if the implementation later
  carries it through a local DTO before C3's hypothesis spine owns the final
  model.
- if a new `residual_mad` field is added (Open Question option 1), put it
  on `BaselineIntegration`, `CellIntegrationAuditSummary`, or the C5 local
  integration DTO. The key is that diagnostic writers receive the value from
  the integration/audit boundary and do not recompute the noise estimate.

## Acceptance Owner

Same protocol as P1 / P2. Validation outputs reviewed, before / after audit
classification counts recorded, go / no-go note under
`docs/superpowers/notes/`.
