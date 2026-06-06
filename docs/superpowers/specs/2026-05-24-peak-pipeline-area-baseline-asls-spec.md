# P2 — Area Integration AsLS Baseline Spec

**Date:** 2026-05-24
**Status:** Historical implementation slice; superseded for current product
value selection
**Overview:** [Peak pipeline modernization overview](2026-05-24-peak-pipeline-modernization-overview-spec.md)
**Precondition:** P1 resolver default switch validated clean

## 2026-06-02 Retirement Correction

This spec describes the original shadow/audit introduction of AsLS and contains
historical language from the period when `linear_edge` still existed as the
production baseline. That language is no longer authoritative for current
product behavior.

Current product contract:

- `linear_edge` is retired and rejected as config, CLI, environment, integration
  audit, and writer method input;
- final matrix values must not use linear-edge or linear-edge-compatible area;
- the current final-matrix value contract is
  [AsLS primary matrix value policy](2026-06-02-asls-primary-matrix-value-policy-spec.md);
- remaining linear-edge references in diagnostics, fixtures, or old notes are
  historical comparison evidence only.

## Purpose

Add an Asymmetric Least Squares (Eilers & Boelens 2005) baseline path to the
area integration step, next to the existing linear-edge baseline. The reusable
`asls_baseline` function already exists at `xic_extractor/baseline.py:8-37` and
is currently used by S/N scoring only. The area path
(`peak_detection/baseline.py`) still uses linear-edge.

Matrix hump under a peak, drifting baseline, and tailing peaks whose right
edge has not returned to baseline are not protected by the linear-edge model.
These conditions are expected in biological matrix LC-MS data.

## Current State

- `xic_extractor/baseline.py:8-37` defines `asls_baseline(y, lam=1e5, p=0.01,
  n_iter=10)`. The formula is the standard Eilers & Boelens construction:
  iteratively reweighted least squares with second-difference penalty,
  asymmetric weighting toward points below the current baseline.
- `xic_extractor/peak_scoring.py:1006` uses it as `compute_local_sn_cache`:
  baseline plus residual MAD as the local noise estimate for the S/N severity
  gate.
- `xic_extractor/peak_detection/baseline.py:18-39` implements
  `integrate_linear_edge_baseline`, which interpolates a straight line between
  the left and right interval edges, subtracts, clips at zero, and integrates.
  This is the only baseline used for `area_baseline_corrected` in
  `CellIntegrationAuditSummary`.

## Required Change

Add a new function in `xic_extractor/peak_detection/baseline.py`:

```text
integrate_asls_baseline(intensity_values, rt_values, left, right, *,
                        lam=1e5, p=0.01, n_iter=10) -> BaselineIntegration
```

Behavior:

- call `asls_baseline` on the full trace `intensity_values` (not just the
  segment), so the penalty term sees the matrix context outside the peak
- slice the resulting baseline by `[left:right]`, subtract from the same slice
  of `intensity_values`, clip at zero, integrate trapezoidally and convert
  counts-minutes to counts-seconds
- return `BaselineIntegration(area_baseline_corrected=..., area_uncertainty=
  None, baseline_type="asls", baseline_score=...)`
- `baseline_score` definition follows linear-edge: corrected_area / raw_area
  clamped to `[0, 1]`

Add a selector function that takes a `baseline_method` argument and dispatches
to either linear-edge or AsLS:

```text
integrate_with_baseline(intensity_values, rt_values, left, right, *,
                         baseline_method="linear_edge") -> BaselineIntegration
```

Default remains `linear_edge`. The selector is the only call site that the
audit pipeline depends on after this change.

### Existing Call Sites

`integrate_linear_edge_baseline` is currently called from four places:

| Call site | Purpose | P2 action |
|-----------|---------|-----------|
| `peak_detection/integration_audit.py:55` | Cell integration audit summary writer | **Switch to selector.** This is the path that emits the new AsLS shadow column. |
| `peak_detection/region_safe_merge.py:275` | Safe-merge promoted-area recomputation | **Keep direct call to `integrate_linear_edge_baseline`.** P2 must not change production baseline semantics; the shadow column is emitted at the audit layer, not in the safe-merge path. |
| `peak_detection/hypotheses.py:269` | PeakHypothesis spine integration | **Keep direct call.** The hypothesis spine consumes the existing baseline contract; switching to the selector would change downstream `IntegrationResult.area_baseline_corrected` values. Migration belongs to a separate spec. |
| `extraction/peak_candidate_boundaries.py:182` | Per-boundary audit baseline | **Optional follow-up.** Switching the boundary audit emitter to the selector would also expose AsLS per-boundary area in `peak_candidate_boundaries.tsv`. Defer to v0.2 if reviewers want the comparison at boundary granularity. |

P2 v0.1 scope is limited to `peak_detection/integration_audit.py:55`. The
other call sites are documented here so reviewers can see the migration
horizon, but they are not part of v0.1.

## Shadow Activation

Add `baseline_method` to `CellIntegrationAuditSummary` plumbing
(`peak_detection/integration_audit.py:32-79`):

- when `baseline_method = "asls"`, the audit summary records both linear-edge
  and AsLS results in parallel
- TSV writer (`alignment/tsv_writer.py`) emits two additional columns:
  `area_baseline_corrected_asls` and `baseline_score_asls`
- production `area_baseline_corrected` continues to use `linear_edge` until a
  separate promotion spec lands:
  [P2b — Area integration AsLS promotion](2026-05-24-peak-pipeline-area-baseline-asls-promotion-spec.md)
- the writer must read those shadow values from
  `CellIntegrationAuditSummary` (or a nested shadow-result field on that
  summary). Do not model `baseline_score_asls` as a field on
  `BaselineIntegration`; `BaselineIntegration.baseline_score` remains the
  score for whichever single integration result it represents.

Configuration flag:

- `config/settings.example.csv` and the settings schema gain
  `baseline_audit_method,asls` or an equivalent opt-in flag (default empty so
  the shadow column is not emitted unless explicitly turned on)
- CLI flag `--emit-baseline-audit-asls` on `scripts/run_alignment.py`
- environment flag for one-shot diagnostics: `BASELINE_AUDIT_METHOD=asls`

## AsLS Cache Strategy (shared with P4)

Without coordination, AsLS will be fit three times per trace:

1. `peak_scoring.py:compute_local_sn_cache` for the S/N severity gate
2. `peak_detection/baseline.py:integrate_asls_baseline` (P2) for area
   integration
3. `peak_detection/integration_audit.py` (P4) for area uncertainty residual

AsLS is O(n) per iteration with a default of 10 iterations, so triple compute
is measurable on high-density traces (8RAW dataset roughly doubles per-trace
audit cost).

This spec defines a per-trace AsLS cache keyed by `id(intensity_values)` (or
a checksum if the same array is mutated upstream). The cache:

- lives on the trace processing scope; one entry per trace per resolver run
- stores `(baseline_array, residual_mad)` after the first AsLS fit
- is invalidated when the trace processing scope exits
- is consulted by all three call sites; whichever runs first populates the
  cache

P2 v0.1 ships the cache with `integrate_asls_baseline` only. P4 reuses it.
If `compute_local_sn_cache` is later refactored to consult the same cache,
the savings extend to the scoring path. Until then, scoring path keeps its
own AsLS call.

Implementation note: the cache lives at the same lifecycle as the
`ScoringContext` or the `CellIntegrationAuditSummary` builder, not as a
module-level singleton. Module-level caching would leak across files in
parallel-extraction mode.

## Reasonable Defaults

- `lam = 1e5` matches the function default and the Eilers & Boelens v2 paper
  for typical LC chromatographic widths
- `p = 0.01` is appropriate for LC peaks (small fraction of points are
  baseline)
- `n_iter = 10` is the documented stable iteration count

These defaults may need re-tuning for biological matrix RAW files; the spec
allows per-run override via the existing argument plumbing but does not change
defaults.

## Validation Contract

Pre-promotion validation runs against the same 8RAW dataset already used for
P1:

1. Generate `alignment_cell_integration_audit.tsv` with the AsLS shadow column
   enabled.
2. Compare per-ISTD `area_baseline_corrected_asls` against
   `area_baseline_corrected` (linear-edge):
   - record the median absolute relative difference per ISTD
   - record the count of cells where the difference exceeds 5%
   - record the count of cells where AsLS reduces area (matrix hump
     over-subtraction by linear-edge is one expected cause)
3. Compare per-ISTD area RSD under each method:
   - AsLS area RSD must be lower than or within +0.3 percentage points of the
     linear-edge area RSD for the strict ISTD set
4. Re-run the area integration uncertainty audit
   (`tools/diagnostics/area_integration_uncertainty_audit.py`) to confirm
   `unexplained_area_mismatch` remains 0

If validation reproduces the `d3-N6-medA` mismatch under one method but not
the other, that is decision evidence and must be recorded in the validation
note.

## Rollback Condition

Shadow can be disabled at any time by removing the CLI / env flag. Promotion
to default production baseline is not in this spec; that decision is owned by
a follow-up spec.

If, during shadow runs, AsLS produces:

- areas that violate `area_baseline_corrected_asls <= raw_area`, treat as a
  bug in the new function and revert by removing the column
- areas that diverge by more than 50% from linear-edge with no matrix-hump
  pattern visible in the diagnostic, hold shadow runs and investigate

## What This Spec Does Not Change

- production `area_raw_counts_seconds`
- production `area_baseline_corrected` (still linear-edge until promotion spec)
- `compute_local_sn_cache` in `peak_scoring.py` (already AsLS)
- targeted reliability decisions
- resolver behavior
- alignment / matrix identity logic

## Open Questions

- Should AsLS be invoked once per trace and reused for multiple peak intervals
  on the same trace? Current `integrate_linear_edge_baseline` recomputes per
  interval. AsLS is O(n) per iteration so per-trace caching is a measurable
  optimization for high-density traces.
- Should the AsLS audit column be emitted by default for all detected and
  rescued cells, or only when the linear-edge `baseline_score` falls below a
  threshold? The first option is cleaner; the second saves writer cost.
- Should P2 also produce an `airPLS` shadow column for comparison
  (Zhang, Chen, Liang 2010)? `pybaselines` provides it but introduces a
  dependency. Default answer: no for v0.1, revisit if matrix hump cases still
  evade AsLS.

## Cleanup Hook

Implementation should leave the following structure intact so Phase 2 C1a
(baseline module relocation) and C5 (area integration single entry) can land
without rework. C1b linear-edge retirement is now explicitly blocked until a
separate AsLS truth-validation spec proves accuracy/linearity/blank behavior or
an equivalent known-baseline benchmark.

- `integrate_with_baseline` selector is a **thin wrapper** that only
  dispatches between `linear_edge` and `asls`. Do not add other dispatch
  logic (e.g. baseline-aware caching, per-trace overrides) inside the
  selector. Cache strategy belongs in the AsLS-using function or a shared
  cache layer, not in the selector. C1b may delete the selector only after C5
  has migrated callers and the AsLS truth-validation blocker is cleared.
- keep `asls_baseline` importable from `xic_extractor.baseline` for now;
  C1a may relocate it only after Phase 1 is stable and P2b has clarified the
  conditional audit-promotion surface. Do not pre-emptively move the function,
  and do not treat P2b as permission to retire linear-edge.
- the new `CellIntegrationAuditSummary` shadow fields
  `area_baseline_corrected_asls` and `baseline_score_asls` use the same
  formatting and ratio convention as the existing production fields. Keep
  `BaselineIntegration` focused on one integration method; do not overload it
  with method-specific shadow columns.

## Acceptance Owner

Same protocol as P1. Validation outputs reviewed, go / no-go recorded under
`docs/superpowers/notes/`.
