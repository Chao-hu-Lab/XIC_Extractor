# C5 — Area Integration Single Entry Spec

**Date:** 2026-05-24
**Status:** Cleanup slice draft v0.3 — METHOD-PRESERVING after design correction
**Overview:** [Peak pipeline cleanup roadmap overview](2026-05-24-peak-pipeline-cleanup-roadmap-overview-spec.md)
**Precondition:** C3a/C3b hypothesis-spine scaffold is accepted or explicitly
deferred, C1a baseline relocation landed if needed, and Phase 1 conditional
blockers are documented. P2b conditional audit promotion is enough to preserve
AsLS audit support, but not enough to make this entry AsLS-only.

## Purpose

Collapse four baseline-corrected area integration call sites onto one
method-preserving entry point with thin adapters for production / audit /
hypothesis-spine variants.

This refactor introduces no behavioral change. Validation is behavioral
parity.

## Current State (assumed after design correction)

This section describes the working-tree state C5 expects when it runs.
The 2026-05-26 design correction rejects an AsLS-only C5 unless the P2c
truth-validation closeout explicitly reaches `GO_FOR_LINEAR_EDGE_RETIREMENT`
and cleanup owner approval names C5 as retirement-ready. C5 should unify
mechanics and provenance while preserving method selection. It must not force all
callers to AsLS only because P2b reached conditional audit promotion or because
P2c only reaches `GO_FOR_C1B_PLAN_SYNTHETIC_ONLY`.

The four current call sites, each with its own surrounding wrapper logic:

| Caller | Purpose | Surrounding logic |
|--------|---------|-------------------|
| `peak_detection/integration_audit.py:55` | Audit summary | Computes `uncertainty_fraction`, `baseline_fraction`, `integration_scan_count` |
| `peak_detection/region_safe_merge.py:275` | Safe-merge promoted area | Reuses bounds from the merged decision |
| `peak_detection/hypotheses.py:269` | Hypothesis spine `IntegrationResult` | Wraps in the spine dataclass |
| `extraction/peak_candidate_boundaries.py:182` | Per-boundary audit | One row per `BoundaryHypothesis` |

Each caller does its own bounds-validation, error-handling, and
`BaselineIntegration` post-processing. The same logic is repeated in
four shapes.

## Required Change

### Step 1 — Define a single integration entry

Define one function in `xic_extractor/peak_detection/integration.py`:

```text
integrate_peak_region(
    rt_values, intensity_values, *,
    left_index, right_index,
    baseline_method,
    asls_cache=None,
) -> AreaIntegrationResult
```

Behavior:

- compute the raw trapezoid area
- compute the selected baseline method (`asls` or `linear_edge`) and record it
  explicitly
- compute baseline-corrected area
- compute residual MAD and area uncertainty per P4 formula
- return one local DTO, `AreaIntegrationResult`, containing all of:
  - `area_raw_counts_seconds`
  - `area_baseline_corrected`
  - `area_uncertainty`
  - `baseline_score`
  - `baseline_type`
  - `integration_scan_count`
  - `residual_mad`

`AreaIntegrationResult` should be shaped to map cleanly into the hypothesis
spine `IntegrationResult`. If C3a/C3b has already defined the spine contract,
C5 should use that contract rather than inventing a second DTO shape.

### Step 2 — Thin adapters at each call site

Each existing caller becomes a thin adapter:

- `integration_audit.py` — wraps `integrate_peak_region` and translates to
  `CellIntegrationAuditSummary` (audit-only fields like
  `uncertainty_fraction`, `baseline_fraction`)
- `region_safe_merge.py` — wraps `integrate_peak_region` and applies the
  safe-merge area-ratio gate
- `hypotheses.py` — calls `integrate_peak_region` directly, no wrapping
  needed once C3 maps the local DTO into the hypothesis spine
- `peak_candidate_boundaries.py` — wraps `integrate_peak_region` per
  boundary hypothesis

Adapters carry no integration logic; they only translate
`AreaIntegrationResult` to the output shape that each consumer expects.

### Step 3 — Remove duplicate bounds-validation

Each caller currently re-validates `left_index < right_index` and clamps
to trace bounds. After the refactor, this happens once inside
`integrate_peak_region`. Callers only need to supply candidate bounds; the
entry handles the rest.

## Validation Contract

Behavioral parity required:

1. Run 8RAW with Phase 1 final state + C1a
2. Apply C5 refactor
3. Re-run 8RAW
4. `peak_candidates.tsv`, `peak_candidate_boundaries.tsv`,
   `alignment_cell_integration_audit.tsv`, `alignment_matrix.tsv`,
   `alignment_review.tsv`, `alignment_cells.tsv` must hash-match
5. `region_safe_merge` promotion decisions must match (the safe-merge
   area-ratio gate runs against the same area values)
6. Adapter output shapes derived from `AreaIntegrationResult` must hash-match
   their pre-refactor values. If the hypothesis spine still emits its own
   `IntegrationResult`, the adapter mapping from `AreaIntegrationResult` to
   that type must also hash-match.

## Rollback Condition

Revert the refactor if any of:

- hash mismatch on parity TSVs
- a previously-undetected adapter discrepancy surfaces (e.g. one caller
  rounded differently than another)
- `safe_merge` promotion count changes by more than 0 (it should be
  identical)

## What This Spec Does Not Change

- AsLS baseline computation (frozen after C1a; linear-edge removal is
  C1b's concern, which runs after C5)
- area uncertainty formula (frozen after P4)
- safe-merge gate thresholds
- production area values

## Open Questions

- Should `integrate_peak_region` accept `left_rt` / `right_rt` instead of
  `left_index` / `right_index`? RT-based bounds are more semantically
  meaningful but require an extra `np.searchsorted` per call. Current code
  is index-based; keep index-based for parity, revisit after C3 if RT-based
  is cleaner with the hypothesis spine.
- Should the function accept a `BoundaryHypothesis` directly instead of
  raw bounds? After C3 the spine carries the boundary; the function could
  unpack the boundary internally. Decision deferred to refactor time.
- Should the audit summary's `uncertainty_fraction` and `baseline_fraction`
  move to `AreaIntegrationResult` so audit no longer recomputes them? Lean
  yes, but only if it does not bloat the integration result for non-audit
  callers. C3 can decide later whether those fields belong on the hypothesis
  spine `IntegrationResult`.

## Acceptance Owner

Engineering owner runs parity validation, records under
`docs/superpowers/notes/`. PR includes the parity report and the
caller-by-caller adapter sketch.
