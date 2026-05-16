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

This phase must not:

- make local minimum, half-height, or baseline-return the final boundary
  authority;
- add CWT or ML;
- add baseline-corrected area;
- change targeted benchmark/reliability states;
- change untargeted alignment matrix logic.

## Boundary Sources In v1

V1 supports three deterministic sources:

- `candidate_interval`: the interval already attached to the current
  `PeakCandidate`.
- `half_height`: an apex-centered interval where raw intensity falls below
  half of the apex-over-local-edge dynamic range.
- `baseline_return`: an apex-centered interval where raw intensity returns near
  the local edge baseline.

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

## Acceptance Criteria

1. Candidate interval source reproduces the current candidate RT bounds.
2. Half-height and baseline-return can produce distinct intervals on synthetic
   traces.
3. Duplicate intervals merge source provenance instead of producing duplicate
   boundary rows.
4. Mismatched RT/intensity arrays fail clearly.
5. `IntegrationResult` records that current production integration comes from
   `candidate_interval`.
6. Narrow tests, `ruff`, and `mypy` pass.

## Future Work

After v1:

1. Write boundary hypotheses into an optional audit TSV.
2. Add CWT-width and derivative-zero-crossing boundary sources.
3. Score boundary hypotheses using baseline quality, trace continuity, and
   coelution evidence.
4. Add non-overlap or mixture model selection over scored hypotheses.
