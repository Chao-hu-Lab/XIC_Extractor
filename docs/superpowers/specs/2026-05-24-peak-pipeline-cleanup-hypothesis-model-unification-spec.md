# C3 — Hypothesis Model Unification Spec

**Date:** 2026-05-24
**Status:** Cleanup slice draft v0.1
**Overview:** [Peak pipeline cleanup roadmap overview](2026-05-24-peak-pipeline-cleanup-roadmap-overview-spec.md)
**Precondition:** C1a (baseline module relocation), C2 (resolver collapse),
C5 (area integration single entry), and C1b (linear edge retirement) all
landed and validated. C1b is included because the post-C1b state finalizes
the `BaselineIntegration` shape that the hypothesis spine `IntegrationResult`
mirrors.

## Purpose

Eliminate the parallel data models. The handoff vision defines one peak
data spine (`PeakHypothesis` + `EvidenceVector` + `IntegrationResult` +
`AuditTrail`), but the legacy spine (`PeakCandidate` + `PeakResult` +
`PeakDetectionResult`) still exists in parallel. Every consumer goes
through an adapter.

This is the largest refactor in the cleanup roadmap. It touches the most
files. It also unlocks C4 (peak_scoring split).

This refactor introduces no behavioral change. Validation is behavioral
parity.

## Current State

Two model layers exist:

### Legacy spine

- `xic_extractor/peak_detection/models.py`:
  - `PeakResult` — selected peak coordinates and area
  - `PeakCandidate` — candidate + selection metadata
  - `PeakCandidatesResult` — wrapper with status/n_points
  - `PeakDetectionResult` — final detection output
  - `PeakCandidateScore` — score breakdown
  - `LocalMinimumRegionQuality` — region quality metadata

### Handoff spine

- `xic_extractor/peak_detection/hypotheses.py`:
  - `PeakHypothesis` — candidate + selected flag + reason
  - `EvidenceVector` — multi-source evidence
  - `IntegrationResult` — integration output
  - `AuditTrail` — audit metadata

The two spines are connected via adapters in `hypotheses.py` that wrap
legacy results. Every downstream consumer (scoring, alignment, output) reads
from legacy types. Adding a new evidence dimension or audit field requires
touching both layers.

## Required Change

### Step 1 — Inventory legacy consumers

Run a grep for every reference to `PeakResult`, `PeakCandidate`,
`PeakCandidatesResult`, `PeakDetectionResult`, `PeakCandidateScore`. Catalog
each as one of:

- (a) producer site (where the legacy object is constructed)
- (b) reader site (where the legacy object is consumed)
- (c) audit site (where the legacy object is serialized to TSV)
- (d) re-export shim (where the legacy object is exposed under a different
  import path)

Expected sites (verify at refactor time):

- producers: `local_minimum.py`, `legacy_savgol.py` (after C2 retirement
  this should be gone), `cwt.py`, `recovery.py`, `region_safe_merge.py`,
  `facade.py`
- readers: `peak_scoring.py`, `alignment/ownership.py`,
  `alignment/owner_backfill.py`, `extraction/*`
- audit: `extraction/peak_candidate_table.py`,
  `extraction/peak_candidate_boundaries.py`, `alignment/tsv_writer.py`
- re-export shim: `xic_extractor/signal_processing.py` re-exports
  `LocalMinimumQualityFlag`, `LocalMinimumRegionQuality`, `PeakCandidate`,
  `PeakCandidateScore`, `PeakCandidatesResult`, `PeakDetectionResult`,
  `PeakResult`, `PeakStatus`, `find_peak_and_area`, `find_peak_candidates`
  via its `__all__`. Many callers (e.g.
  `extraction/istd_recovery.py:from xic_extractor.signal_processing import
  PeakCandidate, PeakDetectionResult`) use the shim instead of importing
  from `peak_detection.models` directly. C3 must either update the shim
  to re-export the hypothesis spine, or delete the shim and migrate every
  shim consumer.

### Step 2 — Replace producers with hypothesis spine

Every producer site that currently returns `PeakCandidate` /
`PeakCandidatesResult` returns the hypothesis spine instead:

- `find_peak_candidates_local_minimum` → returns
  `tuple[PeakHypothesis, ...]`
- `find_peak_and_area` → returns a `PeakHypothesis` with `selected = True`
- `region_safe_merge` → produces and promotes `PeakHypothesis` directly

The fields previously on `PeakCandidate` (selection_apex_rt,
selection_apex_intensity, region_scan_count, quality_flags, prominence,
proposal_sources, source_apex_rank, region_*) move into `PeakHypothesis` or
its embedded `AuditTrail`. Field-by-field mapping is recorded in this spec
at implementation time.

### Step 3 — Replace readers with hypothesis spine

Every reader site reads `PeakHypothesis` instead of `PeakCandidate`. Field
name changes are mechanical; semantic differences (if any are found during
mapping) are recorded as discrepancies and resolved before landing.

### Step 4 — Replace audit serialization

The TSV writers serialize from the hypothesis spine. Column names in the
emitted TSVs must remain identical to current production (this is a hard
constraint from the validation contract).

If a TSV column has no direct equivalent on the hypothesis spine, add the
corresponding field to `AuditTrail` rather than reviving a legacy type.

### Step 5 — Resolve the signal_processing shim

Two options:

- (a) **Keep the shim, update `__all__`**: replace the legacy symbols with
  re-exports of the hypothesis spine (`PeakHypothesis`, `EvidenceVector`,
  `IntegrationResult`, `AuditTrail`). External callers continue to import
  from `xic_extractor.signal_processing` but receive the new types.
- (b) **Delete the shim**: migrate every caller of
  `xic_extractor.signal_processing` to import directly from
  `xic_extractor.peak_detection.hypotheses` (or wherever the type lives).

Decision: lean toward (a). The shim has historically been the "external
import surface" and callers depend on its stability. Updating `__all__` is
mechanical. Deletion would be a wider change that competes for review
attention with the model unification itself.

Document the decision in `xic_extractor/signal_processing.py` docstring at
implementation time.

### Step 6 — Delete the legacy module

After all producer, reader, and audit sites consume the hypothesis spine,
and after Step 5 resolves the shim, delete `PeakResult`, `PeakCandidate`,
`PeakCandidatesResult`, `PeakDetectionResult`, and `PeakCandidateScore`
from `xic_extractor/peak_detection/models.py`. The file may still contain
shared support types (`LocalMinimumRegionQuality`, `LocalMinimumQualityFlag`,
`PeakStatus`); keep those.

## Validation Contract

Behavioral parity required:

1. Run 8RAW after Phase 1 + C1a + C2 + C5 + C1b (i.e. the cleanup interim state)
2. Apply C3 refactor
3. Re-run 8RAW
4. All production TSV outputs hash-identical:
   - `peak_candidates.tsv`
   - `peak_candidate_boundaries.tsv`
   - `alignment_matrix.tsv`
   - `alignment_review.tsv`
   - `alignment_cells.tsv`
   - `alignment_cell_integration_audit.tsv`
5. Strict ISTD benchmark identical
6. Identity coherence verdicts unchanged
7. `peak_scoring.py` outputs (`ScoredCandidate.evidence_score.raw_score`,
   `confidence`, `reason`) byte-identical to pre-refactor

## Implementation Strategy

Recommended split across multiple PRs:

| PR | Scope | Validation |
|----|-------|------------|
| 3a | Add new fields to `PeakHypothesis` / `AuditTrail` so they can express everything legacy fields express. Compile only; no behavior change. | unit tests for new fields |
| 3b | Switch producers to emit both legacy and hypothesis spine (dual write). | parity TSV check |
| 3c | Switch readers one consumer at a time to the hypothesis spine. | parity TSV check after each consumer |
| 3d | Switch audit serializers to read from hypothesis spine. | parity TSV check |
| 3e | Delete dual-write code paths; only hypothesis spine remains. | parity TSV check |
| 3f | Update `signal_processing.py` shim `__all__` to re-export hypothesis spine. | compile + tests + import smoke |
| 3g | Delete legacy types from `models.py`. | compile + tests |

This staging keeps each PR reviewable. The intermediate dual-write state
adds memory cost but is safe to revert at any step.

## Rollback Condition

Roll back any individual PR (3a-3f) if:

- compile fails or tests regress (unit-level rollback)
- parity TSV check fails (rollback to dual-write state)
- a previously-undetected field semantic difference between legacy and
  hypothesis spine surfaces (resolve in spec, then continue)

## What This Spec Does Not Change

- TSV column names or contents
- production scoring values
- alignment / matrix decisions
- resolver behavior
- baseline / area computation

## Open Questions

- Does `PeakCandidate` carry any field that has no semantic equivalent on
  `PeakHypothesis` today? Catalog at refactor time; the spec assumes the
  catalog is buildable but does not commit to a specific mapping.
- Should `PeakHypothesis` gain optional fields to absorb the
  `LocalMinimumRegionQuality` data, or should that stay as a separate
  embedded type? Keep separate for now; revisit if it complicates audit.
- The hypothesis spine currently uses `selected: bool`. After unification,
  does the selection decision logic move to a dedicated method on
  `PeakHypothesis`, or stay in `selection.py`? Defer the API choice to
  refactor time.
- Adapter functions in `hypotheses.py` that wrap legacy types can be
  deleted after Step 5. Confirm no external caller imports them.

## Acceptance Owner

Engineering owner runs parity validation after each sub-PR. Final landing
note recorded under `docs/superpowers/notes/`. Final PR removes the legacy
types and triggers C4 (peak_scoring split) as a follow-up.
