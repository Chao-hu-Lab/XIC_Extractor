# C4 — peak_scoring Split Spec

**Date:** 2026-05-24
**Status:** Superseded-for-implementation v0.4 — replaced by evidence-decision
design; old package-split plan is historical rationale only
**Overview:** [Peak pipeline cleanup roadmap overview](2026-05-24-peak-pipeline-cleanup-roadmap-overview-spec.md)
**Current reassessment:** [Peak pipeline cleanup current-state reassessment](2026-06-01-peak-pipeline-cleanup-current-state-reassessment-spec.md)
**One-goal execution contract:** [Peak pipeline cleanup one-goal phase contract](2026-06-01-peak-pipeline-cleanup-one-goal-phase-contract-spec.md)
**Current C4 design:** [C4 peak scoring evidence-decision design](2026-06-01-c4-peak-scoring-evidence-decision-design.md)
**Precondition for any future implementation:** Phase 1 stable, C3 has a
parity-backed migration that actually reduces a legacy DTO dependency, and the
current C4 evidence-decision design has been accepted. A `diagnostic_only` C3
closeout does not unlock this implementation.

## 2026-06-01 Supersession Decision

Do not execute the package split below literally. Current direction is to
rethink C4 as an evidence-decision architecture:

```text
evidence extraction
  -> evidence interpretation / normalization
  -> decision policy
  -> reason / audit projection
```

The required brainstorming rewrite is captured by the current C4 design linked
above. Future agents should implement from that design, not from the historical
package layout below. The accepted design settles:

- whether `xic_extractor.peak_scoring` remains a module, becomes a package with
  a shim, or moves implementation under a different internal package;
- which responsibilities belong to evidence extraction versus decision policy;
- which score / confidence / reason outputs must be characterized before code
  movement;
- how CWT evidence and C3 handoff-spine fields enter the scorer without
  duplicating evidence semantics.

## Historical Purpose (Non-Executable)

Split `xic_extractor/peak_scoring.py` (1092 lines mixing scorer, evidence,
local S/N, severity gates, quality flags, and dataclasses) into a focused
package.

This historical refactor proposal introduces no behavioral change and used
behavioral parity as its validation framing. It is retained only for current
state inventory, public API lists, and parity surfaces. It must not be executed
because the evidence-decision design replaces the package-split framing.

## Historical C3 Dependency Assumption

The old package-split plan assumed the split is clean only if `PeakHypothesis`
is the single input type and the scorer can read from it directly. Today the
scorer accepts both legacy and hypothesis inputs via adapters, which means a
split would either duplicate adapter logic across modules or hide it in a shared
shim that defeats the purpose of splitting.

A future C4 rewrite must re-check this assumption against the actual C3
closeout. If C3 ends as inventory-only or `diagnostic_only`, this package split
remains blocked.

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

## Historical Non-Executable Implementation Sketch

Everything below this heading is historical. Future agents may reuse the file
inventory, public import list, and parity surfaces, but must not execute these
old migration steps. The accepted evidence-decision design only permits future
implementation from the C4-A / C4-B / C4-C slice contracts.

### Historical Target Package Structure

The old proposal converted `peak_scoring.py` into a
`xic_extractor/peak_scoring/` package with the following modules:

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

### Historical Migration Order - Do Not Execute

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
9. Retire the legacy `peak_scoring.py` file only after public import parity is
   proven

After each step, run the parity validation. Each step is one PR.

## Historical Parity Surfaces To Reuse

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

- Historical package-layout questions above are superseded. Current open
  questions live in the evidence-decision design and should be answered per
  C4-A / C4-B / C4-C, not by reopening a full package split.

## Acceptance Owner

Engineering owner uses the current C4 evidence-decision design as the
implementation source. This historical spec stays only as source inventory and
parity-surface rationale.
