# P5 CWT Evidence Honesty Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make current CWT evidence audit-honest without changing production peak selection, scoring, or region-first behavior.

**Architecture:** Keep `centwave_cwt`, `cwt_best_scale`, `cwt_ridge_persistence`, and `cwt_width` production inputs intact. Add documentation and audit-only markers so reviewers can see that legacy CWT numeric fields are presence guards, not real CWT scale/ridge metrics. Emit a single canonical boundary marker, `cwt_audit_filter_reason`, on source-only `cwt_width` boundary rows.

**Tech Stack:** Python dataclasses, existing boundary audit TSV builders, pytest, PowerShell validation commands.

---

## Plan Review Log

- Initial plan status: drafted from `docs/superpowers/specs/2026-05-24-peak-pipeline-cwt-evidence-honesty-spec.md` after CodeGraph/context inspection of `PeakCandidate`, `EvidenceVector`, `_has_same_apex_cwt_support`, and `build_peak_candidate_boundary_rows`.
- Plan review patch 1: kept `cwt_width` in production boundary enumeration, avoided `region_safe_merge.py`, and chose the single canonical `cwt_audit_filter_reason` marker rather than adding a second visibility flag.
- Plan review patch 2: replaced the generic test fixture instruction with concrete `dataclasses.replace(...)` usage matching the existing `tests/test_peak_scoring.py` helper.

## Scope Lock

- In scope: docstrings/comments for legacy CWT numeric fields, helper naming/documentation for the positive-finite CWT guard, additive boundary TSV marker, tests, and validation note.
- Not in scope: real PyWavelets CWT, changing `_CWT_SAME_APEX_SUPPORT_POINTS`, removing `centwave_cwt`, changing `enumerate_boundary_hypotheses` defaults, changing `region_safe_merge.py`, changing candidate scoring, or Cleanup C-specs.
- Gate language: P5 is `audit_only`. It cannot make P2b production-ready and cannot trigger Cleanup.

## Files

- Modify: `xic_extractor/peak_detection/models.py`
  - Add a class docstring to `PeakCandidate` stating `cwt_best_scale` and `cwt_ridge_persistence` are legacy audit-presence flags, not interpretable CWT scale/ridge metrics.
- Modify: `xic_extractor/peak_detection/hypotheses.py`
  - Add the same caveat to `EvidenceVector`, because the fields live there before `PeakHypothesis` wraps the evidence.
- Modify: `xic_extractor/peak_scoring.py`
  - Rename or document the positive-finite CWT metric helper so the code reads as a legacy CWT presence guard. Behavior must remain byte-equivalent for supported inputs.
- Modify: `xic_extractor/extraction/peak_candidate_boundaries.py`
  - Add `cwt_audit_filter_reason` to `PEAK_CANDIDATE_BOUNDARY_HEADERS`.
  - Mark source-only `cwt_width` boundary rows with `legacy_cwt_width_not_real_cwt`.
  - Do not remove rows, do not change boundary scores/ranks, and do not change production `boundaries.py`.
- Modify: `tests/test_peak_candidate_boundaries.py`
  - Assert source-only `cwt_width` rows are retained and marked.
- Modify: `tests/test_peak_scoring.py`
  - Keep same-apex CWT scoring behavior pinned.
- Create: `docs/superpowers/notes/2026-05-25-p5-cwt-evidence-honesty-validation-note.md`
  - Record tests, real 8RAW targeted refresh, row counts, hash/selection checks if run, and final verdict.

## Task 1: Legacy CWT Documentation Tests

**Files:**

- Modify: `tests/test_peak_scoring.py`

- [x] **Step 1: Add docstring and guard behavior assertions**

Add tests:

```python
def test_peak_candidate_documents_legacy_cwt_metric_semantics() -> None:
    from xic_extractor.peak_detection.models import PeakCandidate
    from xic_extractor.peak_detection.hypotheses import EvidenceVector

    assert PeakCandidate.__doc__ is not None
    assert "audit-presence flags" in PeakCandidate.__doc__
    assert "not interpretable as CWT scale or ridge metrics" in PeakCandidate.__doc__
    assert EvidenceVector.__doc__ is not None
    assert "audit-presence flags" in EvidenceVector.__doc__


def test_cwt_same_apex_support_keeps_legacy_positive_finite_guard() -> None:
    supported = replace(
        _make_candidate(apex_rt=8.0, apex_intensity=100.0),
        proposal_sources=("legacy_savgol", "centwave_cwt"),
        cwt_best_scale=4.0,
        cwt_ridge_persistence=0.0,
    )
    cwt_only = replace(
        _make_candidate(apex_rt=8.0, apex_intensity=100.0),
        proposal_sources=("centwave_cwt",),
        cwt_best_scale=4.0,
        cwt_ridge_persistence=0.5,
    )

    assert peak_scoring._has_same_apex_cwt_support(supported) is True
    assert peak_scoring._has_same_apex_cwt_support(cwt_only) is False
```

- [x] **Step 2: Run the tests and confirm the docstring assertion fails first**

Run:

```powershell
$env:PYTHONPATH = (Get-Location).Path
C:\Users\user\Desktop\XIC_Extractor\.venv\Scripts\python.exe -m pytest tests\test_peak_scoring.py::test_peak_candidate_documents_legacy_cwt_metric_semantics tests\test_peak_scoring.py::test_cwt_same_apex_support_keeps_legacy_positive_finite_guard -q
```

Expected before implementation: docstring assertion fails; scoring behavior should already pass or require only fixture adjustment.

## Task 2: CWT Model And Scoring Honesty

**Files:**

- Modify: `xic_extractor/peak_detection/models.py`
- Modify: `xic_extractor/peak_detection/hypotheses.py`
- Modify: `xic_extractor/peak_scoring.py`

- [x] **Step 1: Add model docstrings**

Add to `PeakCandidate`:

```python
"""Detected peak candidate.

The legacy CWT fields `cwt_best_scale` and `cwt_ridge_persistence` are
audit-presence flags only. Their numeric values are reverse-engineered from
non-CWT decisions and are not interpretable as CWT scale or ridge metrics.
"""
```

Add to `EvidenceVector`:

```python
"""Audit evidence attached to a peak hypothesis.

The legacy CWT fields mirror `PeakCandidate` audit-presence flags only and
are not interpretable as CWT scale or ridge metrics.
"""
```

- [x] **Step 2: Rename or wrap the positive-finite helper**

In `peak_scoring.py`, add:

```python
def _positive_finite_legacy_cwt_presence_metric(value: object) -> bool:
    return _positive_finite_metric(value)
```

Use it inside `_has_same_apex_cwt_support(...)`. Do not change `_positive_finite_metric(...)` itself because other scoring helpers may use it.

- [x] **Step 3: Run scoring tests**

Run:

```powershell
$env:PYTHONPATH = (Get-Location).Path
C:\Users\user\Desktop\XIC_Extractor\.venv\Scripts\python.exe -m pytest tests\test_peak_scoring.py -q
```

Expected: pass.

## Task 3: Boundary Audit Marker

**Files:**

- Modify: `xic_extractor/extraction/peak_candidate_boundaries.py`
- Modify: `tests/test_peak_candidate_boundaries.py`

- [x] **Step 1: Add a failing boundary marker test**

Add:

```python
def test_source_only_cwt_width_boundary_rows_are_marked_legacy_audit() -> None:
    candidate = _candidate(
        8.30,
        left=8.00,
        right=8.60,
        sources=("legacy_savgol", "centwave_cwt"),
        cwt_best_scale=3.0,
    )
    rows = build_peak_candidate_boundary_rows(
        sample_name="SampleA",
        target_label="Analyte",
        target_mz=258.1085,
        role="Analyte",
        istd_pair="ISTD",
        resolver_mode="arbitrated",
        peak_result=PeakDetectionResult(
            status="OK",
            peak=candidate.peak,
            n_points=11,
            max_smoothed=100.0,
            n_prominent_peaks=1,
            candidates=(candidate,),
        ),
        rt=np.asarray([8.0, 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 8.8, 8.9, 9.0]),
        intensity=np.asarray([10.0, 18.0, 70.0, 100.0, 70.0, 18.0, 10.0, 10.0, 10.0, 10.0, 10.0]),
    )

    cwt_rows = [row for row in rows if row["boundary_sources"] == "cwt_width"]
    assert cwt_rows
    assert {row["cwt_audit_filter_reason"] for row in cwt_rows} == {
        "legacy_cwt_width_not_real_cwt"
    }
```

Extend `_candidate(...)` with optional `cwt_best_scale`.

- [x] **Step 2: Implement the marker**

In `PEAK_CANDIDATE_BOUNDARY_HEADERS`, add:

```python
"cwt_audit_filter_reason",
```

Add:

```python
CWT_LEGACY_AUDIT_FILTER_REASON = "legacy_cwt_width_not_real_cwt"


def _cwt_audit_filter_reason(boundary: BoundaryHypothesis) -> str:
    return (
        CWT_LEGACY_AUDIT_FILTER_REASON
        if boundary.sources == ("cwt_width",)
        else ""
    )
```

In `_row_from_boundary(...)`, emit:

```python
"cwt_audit_filter_reason": _cwt_audit_filter_reason(boundary),
```

- [x] **Step 3: Run boundary tests**

Run:

```powershell
$env:PYTHONPATH = (Get-Location).Path
C:\Users\user\Desktop\XIC_Extractor\.venv\Scripts\python.exe -m pytest tests\test_peak_candidate_boundaries.py -q
```

Expected: pass.

## Task 4: Validation And Note

**Files:**

- Create: `docs/superpowers/notes/2026-05-25-p5-cwt-evidence-honesty-validation-note.md`
- Modify: `docs/superpowers/specs/2026-05-24-peak-pipeline-cwt-evidence-honesty-spec.md`
- Modify: `docs/superpowers/specs/2026-05-24-peak-pipeline-modernization-overview-spec.md`

- [x] **Step 1: Run focused tests**

Run:

```powershell
$env:PYTHONPATH = (Get-Location).Path
C:\Users\user\Desktop\XIC_Extractor\.venv\Scripts\python.exe -m pytest tests\test_peak_scoring.py tests\test_peak_candidate_boundaries.py tests\test_peak_candidate_table.py tests\test_peak_candidate_audit.py -q
```

Expected: pass.

- [x] **Step 2: Refresh targeted 8RAW region-first output**

Run:

```powershell
$env:PYTHONPATH = (Get-Location).Path
C:\Users\user\Desktop\XIC_Extractor\.venv\Scripts\python.exe -m scripts.validation_harness --suite tissue-8raw --output-root output\phase1_p1_resolver_default_validation\targeted --run-id region_first_safe_merge --resolver-mode region_first_safe_merge --setting emit_peak_candidates=true --setting keep_intermediate_csv=true
```

Expected: exit `0`, `peak_candidates.tsv` row count unchanged from the latest P4 refresh (`172`), and `peak_candidate_boundaries.tsv` row count unchanged from the latest P4 refresh (`529`). Rows with `boundary_sources == cwt_width` have non-empty `cwt_audit_filter_reason`.

- [x] **Step 3: Create validation note**

Record:

- exact tests and results
- targeted 8RAW command and result
- `peak_candidates.tsv` row count
- `peak_candidate_boundaries.tsv` row count
- count of rows where `cwt_audit_filter_reason == legacy_cwt_width_not_real_cwt`
- statement that production scoring and `region_safe_merge.py` were not changed

- [x] **Step 4: Update spec statuses**

Mark the P5 spec as audit-only implemented and update the overview P5 bullet with the `cwt_audit_filter_reason` marker.

## Post-Implementation Review Checklist

- [x] `enumerate_boundary_hypotheses` defaults still include `cwt_width`.
- [x] `region_safe_merge.py` is untouched.
- [x] `_has_same_apex_cwt_support(...)` returns the same truth values.
- [x] No TSV exposes `cwt_best_scale` or `cwt_ridge_persistence` as named columns.
- [x] Source-only `cwt_width` audit rows are retained and marked, not silently deleted.
- [x] Validation note states P5 is `audit_only`.
