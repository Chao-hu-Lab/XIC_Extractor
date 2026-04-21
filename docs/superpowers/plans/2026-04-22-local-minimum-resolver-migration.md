# Local Minimum Resolver Migration Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the current Savitzky-Golay-based peak boundary model with an MZmine-inspired local-minimum resolver for targeted XIC extraction, without disturbing scoring/output plumbing.

**Architecture:** Keep `extractor.py`, scoring, RT prior logic, and output writers unchanged. Constrain the change to `config.py` plus `signal_processing.py`, introducing a resolver-mode dispatch so the new algorithm can be validated against real RAW data before becoming the default. The new resolver should segment a trace by local minima and validate candidate regions by height, duration, top/edge ratio, and scan count, then continue to use the existing candidate-selection/scoring pipeline.

**Tech Stack:** Python 3.13, `numpy`, `scipy.signal.find_peaks`, existing `pytest` suite, real RAW regression via `scripts/run_extraction.py`.

---

## Research Summary

1. **Current repo reality**
   - Current code is **not** using derivative zero-crossings. It already uses `scipy.signal.find_peaks(...)` on a Savitzky-Golay-smoothed trace, then estimates peak boundaries with `scipy.signal.peak_widths(...)`.
   - Relevant code:
     - `xic_extractor/signal_processing.py`
       - `find_peak_candidates()` smooths with `savgol_filter(...)`
       - `find_peaks(smoothed, prominence=...)` finds apex candidates
       - `_peak_bounds()` uses `peak_widths(...)` at `peak_rel_height`
   - Therefore, the meaningful migration is **from width-based boundary estimation to local-minimum region segmentation**, not “remove zero-crossing logic”.

2. **What MZmine Local Minimum Resolver actually does**
   - Official docs: MZmine describes LMR as a **chromatogram resolving** step that splits overlapping/co-eluting peaks by valleys/local minima, especially shoulder peaks.
   - It applies:
     - percentile-based low-intensity pruning (`Chromatographic threshold`)
     - local-minimum search inside a configurable search range
     - filters on minimum height, minimum scans, duration, and top/edge ratio
   - It is described as most suitable for **LC-MS data with little noise and nice peak shapes**.
   - Primary sources:
     - MZmine docs: https://mzmine.github.io/mzmine_documentation/module_docs/featdet_resolver_local_minimum/local-minimum-resolver.html
     - MZmine source:
       - `MinimumSearchFeatureResolver.java`
       - `MinimumSearchFeatureResolverParameters.java`

3. **Important mismatch to acknowledge**
   - MZmine LMR is designed as a **resolver after chromatogram building** in an untargeted workflow.
   - Our repo is doing **targeted XIC extraction** inside a pre-defined RT window.
   - So the correct plan is **MZmine-inspired adaptation**, not a blind one-to-one port.

4. **Why this is still a good fit here**
   - Your reported pain is exactly where width-based boundaries tend to fail:
     - low abundance
     - partial co-elution
     - messy baseline / complex matrix
     - RT drift making anchor-centric fallback brittle
   - A local-minimum resolver gives you an explicit valley model between adjacent candidate regions instead of inferring boundaries from smoothed width alone.

5. **What should not change in the first migration**
   - `extractor.py` orchestration
   - scoring severity logic in `peak_scoring.py`
   - confidence / reason output format
   - RT prior / rolling prior / ISTD propagation
   - CSV/XLSX writer schema

---

## Decision

Implement the new algorithm as **`resolver_mode=local_minimum`**, keep the current path as **`resolver_mode=legacy_savgol`** during validation, and only switch the default after real-data comparison is acceptable.

This is the smallest high-signal path:

- avoids a risky “big bang” rewrite
- preserves an exact A/B switch for real RAW evaluation
- isolates the algorithmic difference to the place that actually changed

---

## Proposed Parameter Model

### New settings to add

- `resolver_mode`
  - `legacy_savgol` | `local_minimum`
- `resolver_chrom_threshold`
  - Percentile of low-intensity datapoints to prune before minimum search
- `resolver_min_search_range_min`
  - Local minimum search window in minutes
- `resolver_min_relative_height`
  - Region apex / trace max filter
- `resolver_min_absolute_height`
  - Region apex absolute intensity filter
- `resolver_min_ratio_top_edge`
  - Apex must exceed both region edges by this ratio
- `resolver_peak_duration_min`
- `resolver_peak_duration_max`
- `resolver_min_scans`

### Existing settings to keep temporarily

- `smooth_window`
- `smooth_polyorder`
- `peak_rel_height`
- `peak_min_prominence_ratio`

These remain active only for `legacy_savgol`.

### Why not overload old settings

Do **not** silently reinterpret `peak_rel_height` or `smooth_window` as local-minimum parameters. That would make configs lie about what the pipeline is doing and break reproducibility.

---

## Algorithm Shape

### `legacy_savgol` (existing)

1. Smooth trace with `savgol_filter`
2. Detect apex candidates with `find_peaks(..., prominence=...)`
3. Estimate boundaries with `peak_widths(..., rel_height=peak_rel_height)`
4. Build `PeakCandidate`
5. Run existing selector / scoring / preferred-RT recovery

### `local_minimum` (new)

1. Use raw intensity trace as the segmentation basis
2. Compute percentile threshold and zero/prune datapoints below it
3. Walk the trace left-to-right and identify local minima using `resolver_min_search_range_min`
4. Split the trace into candidate regions between accepted minima
5. For each region:
   - region apex = raw maximum inside region
   - apply:
     - min absolute height
     - min relative height
     - min scans
     - peak duration range
     - top/edge ratio
6. Convert each valid region into `PeakCandidate`
   - `peak.rt` from raw apex RT
   - `area` from raw integration over the region
   - `peak_start` / `peak_end` from region borders
7. Reuse:
   - `_select_candidate(...)`
   - `_preferred_rt_recovery(...)` (possibly with local-minimum-specific fallback later)
   - scoring and output logic unchanged

### Important design constraint

`PeakCandidate` and `PeakDetectionResult` should stay structurally unchanged. Only the candidate-generation backend changes.

---

## Plan

### Task 1: Freeze the migration boundary in tests

**Files:**
- Modify: `tests/test_signal_processing.py`
- Modify: `tests/test_signal_processing_selection.py`

**Goal:**
Add tests that make the intended behavior explicit before any implementation:

- `legacy_savgol` path remains unchanged
- `local_minimum` can split shoulder peaks by valley
- `local_minimum` uses region minima as peak borders, not rel-height width
- selection/scoring still works on candidates from either resolver

**Key tests to add:**
- shoulder peak with visible valley should produce 2 candidates in `local_minimum`
- broad/flat composite peak without valid valley should remain 1 candidate
- low-abundance analyte near a strong neighbor should retain a local-minimum region if top/edge ratio passes
- `preferred_rt` selection still chooses the correct region under `local_minimum`

**Verification:**
- `uv run pytest tests\test_signal_processing.py tests\test_signal_processing_selection.py -v`


### Task 2: Add config/schema support for resolver mode

**Files:**
- Modify: `xic_extractor/config.py`
- Modify: `xic_extractor/settings_schema.py`
- Modify: `config/settings.example.csv`
- Test: `tests/test_config.py`

**Goal:**
Introduce explicit resolver settings without changing current default behavior.

**Decision:**
- Default stays `legacy_savgol` for now
- New local-minimum parameters must validate independently

**Verification:**
- `uv run pytest tests\test_config.py -v`


### Task 3: Extract candidate-generation backends behind a resolver dispatch

**Files:**
- Modify: `xic_extractor/signal_processing.py`
- Test: `tests/test_signal_processing.py`

**Goal:**
Refactor `find_peak_candidates()` into:

- `_find_peak_candidates_legacy_savgol(...)`
- `_find_peak_candidates_local_minimum(...)`
- `find_peak_candidates(...)` dispatch

This should be a pure refactor first for the legacy path, before adding the new backend.

**Verification:**
- `uv run pytest tests\test_signal_processing.py -v -k \"legacy or gaussian or area or preferred\"`


### Task 4: Implement the MZmine-inspired local minimum resolver

**Files:**
- Modify: `xic_extractor/signal_processing.py`
- Test: `tests/test_signal_processing.py`

**Goal:**
Implement the new candidate-generation backend with:

- threshold pruning
- local minimum search over an absolute RT window
- region finalization
- filters:
  - absolute height
  - relative height
  - top/edge ratio
  - peak duration min/max
  - min scans

**Non-goals in this task:**
- changing scorer logic
- changing extractor orchestration
- changing outputs

**Verification:**
- `uv run pytest tests\test_signal_processing.py -v`


### Task 5: Make `find_peak_and_area()` resolver-agnostic

**Files:**
- Modify: `xic_extractor/signal_processing.py`
- Modify: `tests/test_signal_processing_selection.py`

**Goal:**
Ensure candidate selection, preferred RT recovery, and scoring operate identically regardless of backend.

**Important question to answer in code:**
Should `_preferred_rt_recovery(...)` remain the same for `local_minimum`, or should it gain a backend-specific relaxed search path? Start by keeping it unchanged unless tests prove it inadequate.

**Verification:**
- `uv run pytest tests\test_signal_processing_selection.py -v`


### Task 6: Real-data A/B harness for resolver comparison

**Files:**
- Create: `scripts/compare_resolvers.py`
- Test: light smoke test only if practical, otherwise verify manually

**Goal:**
Run the same config/targets/raw set under:

- `resolver_mode=legacy_savgol`
- `resolver_mode=local_minimum`

Produce a compact diff report for:

- detected ↔ ND flips
- RT drift
- area changes
- ISTD-specific regressions
- confidence distribution changes

**Required focus cohorts:**
- `d3-N6-medA`
- `d3-5-hmdC`
- `8-oxo-Guo`
- `8-oxodG`

This script is what will let you judge “better chemistry” vs “regression”.


### Task 7: Real-data acceptance gate

**Files:**
- Modify: `tests/test_tissue_regression.py` only if new mode becomes the default
- Optional: add a second baseline fixture for local-minimum mode later

**Goal:**
Do not switch the default until these are true:

- the two example cases you already manually validated stay improved
- `d3-N6-medA` is reviewed on real data and accepted
- no unexpected catastrophe in ISTD detection across the 85-sample tissue set
- output schema remains stable except for already-shipped scoring columns

**Acceptance recommendation:**
- keep `resolver_mode=legacy_savgol` as default until manual review of the `d3-N6-medA` cluster is finished
- after review, switch default in a dedicated small follow-up PR

---

## Risks

1. **User expectation risk**
   - The user described the current algorithm as zero-crossing-based, but the repo is already `find_peaks`-based.
   - If we optimize the wrong thing, we will change code without solving the actual failure mode.

2. **Semantic migration risk**
   - MZmine LMR is a resolver in an untargeted workflow, not a drop-in targeted XIC detector.
   - A blind port would create incorrect assumptions about thresholds and region semantics.

3. **Config reproducibility risk**
   - Reusing old Savitzky-Golay settings names for the new resolver would make historical outputs irreproducible.

4. **RT-drift masking risk**
   - A better resolver may expose upstream RT prior / anchor issues more clearly rather than “fix” them.
   - This is especially relevant for `d3-N6-medA`.

---

## Recommendation

Proceed with a **two-mode migration**:

1. Add `local_minimum` as opt-in
2. Build the A/B comparison tool
3. Review the real-data cluster you already flagged (`d3-N6-medA`)
4. Only then decide whether to switch the default

Do **not** do a direct default swap in the same change that introduces the new resolver.
