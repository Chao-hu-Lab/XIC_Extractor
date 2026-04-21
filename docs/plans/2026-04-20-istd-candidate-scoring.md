# ISTD Candidate Scoring Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make ISTD peak selection explainable and more tolerant of dirty urine matrices without rewriting analyte selection.

**Architecture:** Add MS1 candidate enumeration under `signal_processing` and keep `find_peak_and_area()` as the compatible winner wrapper. Use the new candidate metadata for ISTD-focused scoring and diagnostics in `extractor`, while analytes continue to consume the selected ISTD anchor only.

**Tech Stack:** Python, NumPy, SciPy peak detection, pytest, uv.

---

### Task 1: Candidate Enumeration And Raw Apex Reporting

**Files:**
- Modify: `xic_extractor/signal_processing.py`
- Test: `tests/test_signal_processing.py`

**Steps:**
1. Write failing tests for multi-peak candidate listing and raw apex reporting.
2. Verify the tests fail because candidate enumeration does not exist and smoothed/raw apex handling is still coupled.
3. Add a `PeakCandidate` dataclass and `find_peak_candidates()` helper.
4. Make `find_peak_and_area()` select from candidates while preserving its existing return type.
5. Run `uv run pytest -q tests/test_signal_processing.py`.

### Task 2: ISTD Scoring Diagnostics

**Files:**
- Modify: `xic_extractor/extractor.py`
- Test: `tests/test_extractor.py`

**Steps:**
1. Write failing tests showing ISTD with `NO_MS2` remains detected and emits confidence/flag diagnostics instead of becoming ND.
2. Add minimal ISTD confidence/flag diagnostics without changing analyte selection.
3. Keep `NL_FAIL` and `NO_MS2` as soft evidence for ISTD; keep existing NL output token behavior.
4. Run `uv run pytest -q tests/test_extractor.py`.

### Task 3: Verification

**Files:**
- Test: `tests/test_signal_processing.py`
- Test: `tests/test_extractor.py`
- Test: `tests/test_neutral_loss.py`

**Steps:**
1. Run `uv run pytest -q tests/test_signal_processing.py tests/test_extractor.py tests/test_neutral_loss.py`.
2. Run the full suite if the focused tests pass.
3. Confirm no `Int=0`/`Area>0` behavior remains in synthetic apex mismatch coverage.
