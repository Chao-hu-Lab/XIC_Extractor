# Peak Selection Refactor Plan

**Date:** 2026-05-04  
**Branch:** `codex/local-minimum-param-optimization`  
**Executor:** Codex  
**Reviewer:** manual review after each phase  

---

## Background

This plan captures actionable refactors identified during a code review of the
peak selection logic. The codebase uses a three-layer pipeline:

1. **Candidate generation** — `signal_processing.py` (`legacy_savgol` or `local_minimum` mode)
2. **Scoring** — `peak_scoring.py` (7 severity signals → `Confidence` enum)
3. **Selection** — `peak_scoring.select_candidate_with_confidence()`

The overall design philosophy ("candidate generation 寬進, ranking 嚴出") is
correct. The issues below are maintainability and correctness hazards, not
architectural changes.

---

## Issue 1 — MEDIUM: `smoothed_apex_*` fields are misnamed for `local_minimum` mode

**File:** `xic_extractor/signal_processing.py`  
**Function:** `_build_local_minimum_candidate`

In `local_minimum` mode, `PeakCandidate.smoothed_apex_intensity` and
`smoothed_apex_index` are set to raw apex values — no Savitzky-Golay smoothing
is applied. The field names imply smoothing, which is misleading.
Downstream code using these fields cannot tell which mode produced the candidate.

**Required change:**

Rename fields in `PeakCandidate` (and all usages across the codebase):

| Old name | New name |
|---|---|
| `smoothed_apex_rt` | `selection_apex_rt` |
| `smoothed_apex_intensity` | `selection_apex_intensity` |
| `smoothed_apex_index` | `selection_apex_index` |

Update every usage site:
- `xic_extractor/signal_processing.py` — dataclass definition and all references
- `xic_extractor/peak_scoring.py` — `score_candidate`, `select_candidate_with_confidence`
- `xic_extractor/extraction/scoring_factory.py` — `compute_shape_metrics`, `selected_candidate`
- `xic_extractor/extractor.py` — `reported_rt`, `_extract_one_target`
- All test files under `tests/`

No behavioural change — pure rename. Run `grep -r "smoothed_apex" xic_extractor/ tests/`
after the change; must return zero results.

---

## Issue 2 — MEDIUM: `_preferred_rt_recovery` runs selection logic twice with different `selection_rt`

**File:** `xic_extractor/signal_processing.py`  
**Function:** `find_peak_and_area`

When `scoring_context_builder` is present and recovery triggers, the code calls
`select_candidate_with_confidence` twice:

1. First call (inside the `status == "OK"` block): selects from original candidates → `chosen`
2. Second call: re-selects from `[chosen, scored_recovery]` using `preferred_rt`

These two calls use different values for `selection_rt`. The same `prior_rt` can
influence the outcome inconsistently depending on the path taken.

**Required change:**

Merge the recovery candidate into the original candidate list and run selection
once:

```python
# Pseudocode — replace the two-step recovery logic
all_candidates = list(candidates_result.candidates)
if recovery_candidate is not None:
    all_candidates.append(recovery_candidate)

if scoring_context_builder is not None:
    scored_all = [
        _score_with_context(c, scoring_context_builder(c),
                            istd_confidence_note=istd_confidence_note)
        for c in all_candidates
    ]
    chosen = select_candidate_with_confidence(
        scored_all,
        selection_rt=selection_rt,
        strict_selection_rt=strict_preferred_rt,
    )
else:
    best_candidate = _select_candidate(
        tuple(all_candidates),
        preferred_rt=preferred_rt,
        strict_preferred_rt=strict_preferred_rt,
    )
```

Keep the gating condition in `_preferred_rt_recovery` (only triggers when the
current best candidate is farther than `_PREFERRED_RT_RECOVERY_MAX_DELTA_MIN`
from `preferred_rt`). Remove the second `select_candidate_with_confidence` call.
The `PeakCandidatesResult` used for high-level metadata (`n_points`,
`max_smoothed`, `n_prominent_peaks`) should keep the original
`candidates_result` values. If the recovery candidate wins, the returned
candidate list must still include the selected recovery candidate so diagnostics
and downstream debug output are not internally inconsistent.

Add or update a test in `tests/test_signal_processing_selection.py` that verifies:
recovery candidate wins when it is closer to `preferred_rt` and scores at least
as well as the original best candidate.

---

## Issue 3 — LOW: `_should_split_local_region` does not re-anchor left boundary after split

**File:** `xic_extractor/signal_processing.py`  
**Function:** `_local_minimum_regions`

When a split occurs between two peaks, the next region starts at `valley_idx`
(the split point). `_left_threshold_boundary` is not called for the new region.
If there is a flat, sub-threshold segment between the valley and the next peak,
that noise is absorbed into the new region, inflating its area.

**Required change:**

After a split, re-anchor the left boundary to the first point after the valley.
This prevents the next region from overlapping the split valley while keeping
the fix conservative enough not to reshape weak real-data peaks:

```python
if _should_split_local_region(...):
    regions.append((region_left, valley_idx + 1))
    region_left = min(valley_idx + 1, peak_idx)
```

`peak_idx` here is the loop variable (the right-side peak of the pair being
evaluated), not the valley.

**Add a unit test before implementing the fix** covering: two peaks separated by
a flat sub-threshold valley (e.g., `[0, 50, 100, 5, 0, 5, 80, 50, 0]`).
Verify the left boundary of the second region is at or after the valley, not at
the valley itself.

---

## Issue 4 — LOW: Confusing constant names (`_PREFERRED_RT_*_RATIO` ×2)

**File:** `xic_extractor/signal_processing.py`  
**Lines:** constants block near the top of the file

Two constants share the `_PREFERRED_RT_*_INTENSITY_RATIO` prefix but gate very
different thresholds (0.2 vs 0.03):

```python
_PREFERRED_RT_MIN_INTENSITY_RATIO          = 0.2   # regular selection
_PREFERRED_RT_RECOVERY_MIN_INTENSITY_RATIO = 0.03  # recovery selection
```

The 7× difference is intentional but the naming suggests they are the same
threshold in different contexts.

**Required change:**

Rename to make intent explicit:

```python
_ANCHOR_SELECTION_MIN_INTENSITY_RATIO   = 0.2   # anchor candidate must reach 20% of apex
_RECOVERY_CANDIDATE_MIN_INTENSITY_RATIO = 0.03  # recovery candidate floor (very permissive)
```

Update all usages in:
- `_select_candidate`
- `_selection_rt_for_scored_candidates`
- `_select_preferred_recovery_candidate`

Run `grep -r "_PREFERRED_RT_MIN_INTENSITY_RATIO\|_PREFERRED_RT_RECOVERY_MIN_INTENSITY" xic_extractor/ tests/`
after the change; must return zero results.

---

## Execution order

Complete the issues in this order to minimise merge conflicts:

1. **Issue 4** (constant rename) — smallest diff, sets clean context for reading
2. **Issue 1** (field rename) — large but mechanical; can be done with a
   project-wide replace
3. **Issue 3** (boundary fix) — write test first, then implement
4. **Issue 2** (recovery merge) — depends on Issue 1 being renamed first

---

## Validation requirements

After all issues are resolved:

1. `uv run pytest --tb=short -q` — all tests must pass with zero failures.
2. `rg "smoothed_apex" xic_extractor tests` — zero production/test code usages.
   Historical mentions in this plan are allowed.
3. `grep -r "_PREFERRED_RT_MIN_INTENSITY_RATIO\|_PREFERRED_RT_RECOVERY_MIN_INTENSITY" xic_extractor/ tests/` — zero results.
4. No new public API changes — `PeakCandidate` field renames are the only
   breaking change; verify no external callers exist outside `xic_extractor/`
   and `tests/`.

---

## Out of scope for this plan

The following items from the review were intentionally deferred:

- `select_candidate_with_confidence` 4-path key function — requires design
  discussion before refactoring.
- `confidence_from_total` weighting for `nl_support` — requires chemistry review
  to determine if `nl_support` severity warrants a confidence floor.
- AsLS baseline window scope — methodology decision, not a code defect.
- `prior_rt` double-counting in selection — may be intentional; needs
  documentation before any change.
- `selection_trace` audit field — nice-to-have enhancement, not a correctness
  issue.
