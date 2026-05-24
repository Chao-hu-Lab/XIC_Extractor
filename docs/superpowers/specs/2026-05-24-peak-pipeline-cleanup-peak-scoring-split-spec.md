# C4 — peak_scoring Split Spec

**Date:** 2026-05-24
**Status:** Cleanup slice draft v0.2 — ON HOLD until Phase 1 complete
**Overview:** [Peak pipeline cleanup roadmap overview](2026-05-24-peak-pipeline-cleanup-roadmap-overview-spec.md)
**Precondition:** Phase 1 stable, and C3 (hypothesis model unification)
landed and validated.

## Purpose

Split `xic_extractor/peak_scoring.py` (1092 lines mixing scorer, evidence,
local S/N, severity gates, quality flags, and dataclasses) into a focused
package.

This refactor introduces no behavioral change. Validation is behavioral
parity.

## Why This Spec Has to Wait for C3

The split is clean only if `PeakHypothesis` is the single input type and the
scorer can read from it directly. Today the scorer accepts both legacy and
hypothesis inputs via adapters, which means a split would either duplicate
adapter logic across modules or hide it in a shared shim that defeats the
purpose of splitting.

After C3, the scorer reads `PeakHypothesis` only. Each split module then
imports the hypothesis spine and not the legacy spine.

## Current State

`xic_extractor/peak_scoring.py` (~1000 lines) contains:

- `Confidence` enum
- `ScoredCandidate`, `ScoringContext` dataclasses
- `score_candidate` main routine
- `select_candidate_with_confidence` selection wrapper
- `score_breakdown_fields` audit utility
- `compute_local_sn_cache` (AsLS-based local S/N)
- `local_sn_severity`
- `nl_support_severity`
- `rt_prior_severity`
- `rt_centrality_severity`
- `shape_severity`
- `noise_shape_severity`
- `peak_width_severity`
- `_has_cwt_chemical_support`, `_has_same_apex_cwt_support` helpers
- ADAP-like flag handling
- low-scan demotion logic
- dominant strict NL handling
- MS2 trace selection points
- numerous private helpers

The module imports `asls_baseline`, `MS2TraceStrength`, and types from
`peak_scoring_evidence.py`. `peak_scoring_evidence.py` is already an extracted
evidence module, not a new target to recreate. After C1 the AsLS import path
changes; after C3 the input types change.

## Required Change

### Target Package Structure

Convert `peak_scoring.py` into `xic_extractor/peak_scoring/` package with
the following modules:

```text
xic_extractor/peak_scoring/
  __init__.py                # re-export public API
  context.py                 # ScoringContext dataclass
  result.py                  # ScoredCandidate, Confidence enum
  scorer.py                  # score_candidate main routine + selection wrapper
  local_sn.py                # compute_local_sn_cache, local_sn_severity
  severities/
    __init__.py
    nl_support.py            # nl_support_severity
    rt_prior.py              # rt_prior_severity, rt_centrality_severity
    shape.py                 # shape_severity
    noise_shape.py           # noise_shape_severity
    peak_width.py            # peak_width_severity
  evidence/
    __init__.py
    cwt_support.py           # _has_cwt_chemical_support, _has_same_apex_cwt_support
    adap_flags.py            # ADAP-like flag handling
    ms2_trace.py             # wraps or moves existing peak_scoring_evidence.py logic
  quality/
    __init__.py
    low_scan_demotion.py     # low-scan demotion logic
    dominant_nl.py           # dominant strict NL handling
```

Each module less than ~250 lines (the hard cap reviewers can read in one
sitting).

Do not create a second evidence abstraction beside `peak_scoring_evidence.py`.
At refactor time choose one of:

- keep `peak_scoring_evidence.py` as a compatibility sibling and import it
  from the new package modules
- move its contents into `peak_scoring/evidence/ms2_trace.py` and leave a
  re-export shim at the old path

Either option must preserve existing import paths and evidence semantics.

### Public API Preservation

A grep of `from xic_extractor.peak_scoring import` shows the following
symbols are imported by external modules:

- `Confidence`
- `ScoredCandidate` (imported by `extraction/peak_candidate_table.py:20`)
- `ScoringContext` (imported by `peak_detection/facade.py:27`,
  `extraction/peak_candidate_table.py:20`, `extraction/scoring_factory.py:10`)
- `score_candidate` (imported by `peak_detection/facade.py:27`,
  `extraction/peak_candidate_table.py:20`)
- `select_candidate_with_confidence` (imported by
  `peak_detection/facade.py:27`)
- `score_breakdown_fields` (imported by `peak_detection/facade.py:27`)
- `candidate_quality_penalty` (imported by
  `extraction/result_assembly.py:7`, `extraction/istd_recovery.py:16`)
- `candidate_selection_quality_penalty` (imported by
  `extraction/istd_recovery.py:16`)
- `compute_local_sn_cache` (imported by
  `extraction/scoring_factory.py:10`)
- `hard_quality_flags` (imported by
  `extraction/scoring_factory.py:10`)

The new `__init__.py` re-exports all ten symbols from their new locations
so existing callers do not need to change their import paths.

If the inventory grep at refactor time finds additional callers, extend
the re-export list before deleting the legacy `peak_scoring.py` file.

### Migration Order

1. Create the package directory and empty modules
2. Move dataclasses (`context.py`, `result.py`) first
3. Move severity functions one at a time, each with parity validation
4. Move evidence helpers (cwt_support, adap_flags) and either wrap or migrate
   existing `peak_scoring_evidence.py` without duplicating it
5. Move quality logic (low_scan_demotion, dominant_nl)
6. Move `compute_local_sn_cache` to `local_sn.py`
7. Move `score_candidate` main routine to `scorer.py` last, since it
   imports from all the others
8. Add re-exports in `__init__.py`
9. Delete the legacy `peak_scoring.py` file

After each step, run the parity validation. Each step is one PR.

## Validation Contract

Behavioral parity required at every step:

1. `ScoredCandidate.evidence_score.raw_score` byte-identical pre/post
2. `ScoredCandidate.confidence` value identical
3. `ScoredCandidate.reason` string identical
4. `ScoredCandidate.severities` tuple identical
5. `ScoredCandidate.quality_penalty` identical
6. All scoring-driven outputs in `peak_candidates.tsv` and
   `peak_candidate_table.py` byte-identical
7. `alignment_matrix.tsv`, `alignment_review.tsv`, `alignment_cells.tsv`
   hash-identical
8. Identity coherence verdicts unchanged (run
   `scripts/validate_identity_coherence_8raw.py` or its successor; controls
   and decoy outcomes must match pre-refactor)

## What This Spec Does Not Change

- scoring weights, thresholds, or severity ranks
- confidence calculation
- evidence vector semantics
- TSV outputs
- alignment / matrix decisions

## Open Questions

- The legacy `peak_scoring.py` filename is widely referenced in
  documentation and notes. After the split, should we keep `peak_scoring.py`
  as a thin re-export shim, or delete it entirely? Lean toward keeping the
  shim until 2027 to avoid breaking external references; remove in a later
  spec.
- Should `peak_scoring_evidence.py` (already a separate file) move into
  the new `peak_scoring/evidence/` directory as `peak_scoring/evidence/__init__.py`?
  Decision deferred to refactor time. Likely yes, for symmetry.
- Some severity functions consume both `ScoringContext` and the candidate
  object. After C3 the candidate is a `PeakHypothesis`. Verify the function
  signatures are clean (single hypothesis input) before splitting; if
  cross-cutting concerns surface, defer the affected function to a later
  split sub-PR.
- The constants (`_SYMMETRY_SOFT_LOW`, `_SN_DIRTY_HARD_THRESHOLD`, etc.)
  are spread across the file head. Group them by domain (`severities/_constants.py`)
  or keep them in the function module that uses each? Lean toward keeping
  them next to the function that uses each.

## Acceptance Owner

Engineering owner runs parity validation after each sub-PR. Each sub-PR is
small and self-contained. Final landing note recorded.
