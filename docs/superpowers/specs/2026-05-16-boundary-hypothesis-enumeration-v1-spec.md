# Boundary Hypothesis Enumeration v1 Spec

**Date:** 2026-05-16
**Status:** Implementation slice
**Branch:** `codex/targeted-benchmark-reliability`
**Worktree:** `C:\Users\user\Desktop\XIC_Extractor\.worktrees\targeted-benchmark-reliability`
**Source memo:** `C:\Users\user\Downloads\lcms_gcms_peak_pipeline_handoff.md`

## Summary

Candidate table v1 exposes which apex/interval candidates existed. Peak
Hypothesis Spine v1 gives those candidates a domain model. The next safe step is
to make boundary alternatives explicit without letting them change the selected
peak.

This phase adds a `BoundaryHypothesis` enumerator. It produces raw-data
integration candidates for one existing apex using multiple boundary sources.
The current selected interval remains the production interval; extra boundary
hypotheses are audit/research inputs only.

The follow-up audit slice writes these hypotheses to
`peak_candidate_boundaries.tsv` and the focused
`peak_candidate_boundary_summary.tsv` when `emit_peak_candidates=true`. These
artifacts are TSV-only and debug-only; they do not change `peak_candidates.tsv`,
`XIC Results`, or any workbook schema.

## Contract

This phase must:

- keep `XIC Results` unchanged;
- keep `peak_candidates.tsv` schema unchanged;
- keep current `legacy_savgol`, `local_minimum`, and `arbitrated` selection
  behavior unchanged;
- integrate each boundary hypothesis from raw intensity and RT arrays;
- preserve source provenance for duplicated intervals;
- provide deterministic IDs for future audit output. When a full upstream
  `candidate_id` is available, boundary IDs must include it to avoid
  sample/target collisions.
- write `peak_candidate_boundaries.tsv` beside `peak_candidates.tsv` when
  candidate audit output is enabled.
- write `peak_candidate_boundary_summary.tsv` beside the full boundary table so
  manual review can start from each candidate's top-ranked boundary instead of
  scanning every boundary alternative.
- build candidate rows and boundary rows from the same audit peak result so CWT
  proposal enumeration is not duplicated.
- use the recovered wider RT trace for ISTD recovery audit rows when recovery
  replaces the original narrow-window peak.
- include `target_mz` in boundary review artifacts because target label alone is
  not sufficient for EIC review.

This phase must not:

- make local minimum, half-height, or baseline-return the final boundary
  authority;
- make CWT or ML a final authority;
- change targeted benchmark/reliability states;
- change untargeted alignment matrix logic.

## Boundary Sources In v1

V1 supports five deterministic/audit sources:

- `candidate_interval`: the interval already attached to the current
  `PeakCandidate`.
- `half_height`: an apex-centered interval where raw intensity falls below
  half of the apex-over-local-edge dynamic range.
- `baseline_return`: an apex-centered interval where raw intensity returns near
  the local edge baseline.
- `derivative_zero_crossing`: an apex-centered monotonic ascent/descent interval
  bounded by neighboring raw derivative sign changes.
- `cwt_width`: an apex-centered interval derived from candidate CWT scale when
  CWT evidence exists. It is absent for candidates without CWT scale evidence.

These are not scientific acceptance rules. They are proposal sources for audit,
integration sensitivity analysis, and future model selection.

## Data Model

`BoundaryHypothesis` fields:

- `boundary_id`
- `sources`
- `left_index`
- `right_index`
- `rt_left_min`
- `rt_apex_min`
- `rt_right_min`
- `width_min`
- `area_raw_counts_seconds`
- `scan_count`

`right_index` is exclusive, matching existing raw trapezoid integration helpers.

## Audit Output

`peak_candidate_boundaries.tsv` has one row per candidate boundary hypothesis.
Rows preserve the candidate context, proposal provenance, selected-candidate
flag, boundary provenance, raw integrated area, scan count, and deltas versus
the current `candidate_interval` boundary.

Required `peak_candidate_boundaries.tsv` row groups:

- run/target context: `sample_name`, `group`, `target_label`, `target_mz`, `role`,
  `istd_pair`, `analysis_mode`, `resolver_mode`;
- candidate context: `candidate_id`, `proposal_sources`, `selected_candidate`;
- boundary context: `boundary_id`, `boundary_sources`, `rt_left_min`,
  `rt_apex_min`, `rt_right_min`, `rt_width_min`, `area_raw_counts_seconds`,
  `area_baseline_corrected`, `area_uncertainty`, `baseline_type`,
  `baseline_score`, `boundary_audit_score`, `boundary_audit_rank`,
  `boundary_audit_top`, `boundary_nonoverlap_selected`,
  `boundary_nonoverlap_note`, `boundary_nonoverlap_blocker_id`,
  `boundary_support_labels`, `boundary_concern_labels`, `scan_count`,
  `is_candidate_interval`;
- sensitivity context: `area_delta_vs_candidate_interval`,
  `area_ratio_vs_candidate_interval`, `width_delta_vs_candidate_interval`.

This output answers the audit question:

```text
If the apex is held fixed, how much would area change under alternate
boundaries?
```

Baseline correction in this slice uses a deterministic `linear_edge` audit
model: the boundary edge intensities define a local linear baseline, corrected
area integrates `max(raw - baseline, 0)` from raw intensity, and uncertainty is a
local noise-derived area estimate. This remains evidence only; it must not
change selected peaks, scoring thresholds, or production matrix values.

Boundary scoring is an audit-only summary over currently available evidence:
baseline-corrected signal fraction, trace continuity, scan support, and width
shift versus the current `candidate_interval`. It is not a boundary selector.
`boundary_audit_rank` and `boundary_audit_top` only rank alternatives inside the
same candidate for manual review; they do not change row order or production
integration.
`boundary_nonoverlap_selected` is a weighted interval scheduling audit proposal
over each target trace: it considers only each candidate's top-ranked boundary
and marks the highest total-score non-overlapping review set. It must not be
used as production peak selection.
WIS is a model-selection/review helper, not an `EvidenceScore` input: it can
explain overlapping boundary choices, but it must not add support or concern
labels to candidate scoring in this slice.
When a top-ranked candidate boundary is rejected because it overlaps an already
selected higher-priority audit boundary, `boundary_nonoverlap_blocker_id` records
the blocking boundary id(s). `overlaps_weighted_selection` means a wider
boundary lost to multiple lower-score non-overlapping intervals whose total
audit score was higher.
Coelution-specific evidence remains future work because this targeted trace
slice does not yet carry a separate coeluting-trace model.

`peak_candidate_boundary_summary.tsv` has one row per candidate top boundary
where `boundary_audit_top=TRUE`. It copies the review context, `target_mz`,
top-boundary score/labels, RT/area fields, and non-overlap blocker fields from
the full table. It is the first manual review surface; the full boundary TSV
remains the drill-down artifact.

## Acceptance Criteria

1. Candidate interval source reproduces the current candidate RT bounds.
2. Half-height and baseline-return can produce distinct intervals on synthetic
   traces.
3. Duplicate intervals merge source provenance instead of producing duplicate
   boundary rows.
4. Mismatched RT/intensity arrays fail clearly.
5. `IntegrationResult` records that current production integration comes from
   `candidate_interval`.
6. Optional `peak_candidate_boundaries.tsv` is written when
   `emit_peak_candidates=true`.
7. `peak_candidates.tsv` headers remain unchanged.
8. CWT audit proposals are enumerated once and reused by candidate and boundary
   audit row builders.
9. ISTD wider-recovery boundary rows use recovered RT bounds rather than the
   original narrow anchor window.
10. Boundary rows include linear-edge baseline corrected area, uncertainty,
   baseline type, and baseline score.
11. Derivative and CWT-width sources remain audit-only and can be absent or
    merged with duplicate intervals without changing selected peaks.
12. Boundary rows include audit score, support labels, and concern labels.
13. Boundary rows include audit rank and a single top-ranked audit boundary per
    candidate without changing selected peaks or row order.
14. Boundary rows include non-overlap audit proposal markers, with non-top rows
    explicitly marked as review-only context.
15. Boundary review artifacts include `target_mz`.
16. `peak_candidate_boundary_summary.tsv` is written when
    `emit_peak_candidates=true` and contains only top-ranked candidate boundary
    rows.
17. Non-overlap audit selection uses weighted interval scheduling, not greedy
    first-fit selection.
18. Narrow tests, `ruff`, and `mypy` pass.

## Future Work

After v1:

1. Add coelution-specific boundary evidence once trace groups include multiple
   coeluting traces.
2. Evaluate whether weighted interval scheduling should remain review-only or
   feed a future production model-selection gate after real-data validation.
3. Add a mixture model selection experiment if weighted intervals still cannot
   explain coeluting or shoulder-peak cases.
