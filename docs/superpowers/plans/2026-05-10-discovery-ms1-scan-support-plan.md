# Discovery MS1 Scan Support Scoring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a numeric MS1 scan-support signal to discovery candidates and scoring without pretending it is full chromatographic trace quality.

**Architecture:** Compute `ms1_scan_support_score` from the number of XIC scan points inside the selected MS1 peak boundary. Store it as a provenance field and use it as a scoring input through the evidence profile thresholds. Keep the existing string `ms1_trace_quality` as a display/backward-compat field.

**Tech Stack:** Python, numpy boolean masks, pytest, existing `xic_extractor.discovery.ms1_backfill` and `evidence_score` modules.

---

## File Structure Map

- Modify `xic_extractor/discovery/models.py`
  - Add `ms1_scan_support_score: float | None`.
  - Append `ms1_scan_support_score` to provenance columns.
- Modify `xic_extractor/discovery/ms1_backfill.py`
  - Add `compute_ms1_scan_support_score()`.
  - Populate the score for detected and missing peaks.
- Modify `xic_extractor/discovery/evidence_score.py`
  - Prefer numeric scan support for scoring and `ms1_support` classification.
  - Fall back to `ms1_trace_quality` only when numeric score is `None`.
- Tests:
  - `tests/test_discovery_scan_support.py`
  - `tests/test_discovery_csv.py`
  - `tests/test_discovery_pipeline.py`
  - `tests/test_discovery_evidence.py`

## Naming Contract

Use `ms1_scan_support_score`, not `ms1_trace_quality_score`.

Reason: the v1 metric is scan-count support only:

```text
min(1.0, scans_inside_peak / scan_support_target)
```

It does not measure continuity, edge recovery, or baseline recovery.

## Task 1: Add Candidate Field And CSV Provenance Column

**Files:**
- Modify: `xic_extractor/discovery/models.py`
- Modify: `tests/test_discovery_csv.py`

- [ ] **Step 1: Write failing tests**

Add tests that verify:

- `DiscoveryCandidate` has `ms1_scan_support_score`.
- Default value is `None`.
- `DISCOVERY_PROVENANCE_COLUMNS[-1] == "ms1_scan_support_score"`.
- Existing full CSV review columns are not shifted.

- [ ] **Step 2: Run the red tests**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_discovery_csv.py -v -k scan_support
```

Expected: FAIL because the field does not exist.

- [ ] **Step 3: Implement model field**

Add `ms1_scan_support_score: float | None = None` after `ms1_trace_quality` and before feature-family default fields.

Update `DiscoveryCandidate.from_values()` to accept and forward the new keyword.

Append `ms1_scan_support_score` to `DISCOVERY_PROVENANCE_COLUMNS`.

- [ ] **Step 4: Run focused tests**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_discovery_csv.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add xic_extractor/discovery/models.py tests/test_discovery_csv.py
git commit -m "feat(discovery): add MS1 scan support provenance field"
```

## Task 2: Implement Scan Support Pure Function

**Files:**
- Modify: `xic_extractor/discovery/ms1_backfill.py`
- Create: `tests/test_discovery_scan_support.py`

- [ ] **Step 1: Write failing tests**

Create tests for `compute_ms1_scan_support_score(rt, peak, *, scans_target)`:

- Empty RT returns `0.0`.
- No scans inside peak bounds returns `0.0`.
- Three scans inside a peak with target ten returns `0.3`.
- More scans than target caps at `1.0`.
- `scans_target <= 0` raises `ValueError`.

- [ ] **Step 2: Run the red tests**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_discovery_scan_support.py -v
```

Expected: FAIL because the function does not exist.

- [ ] **Step 3: Implement pure function**

In `ms1_backfill.py`, implement:

```python
def compute_ms1_scan_support_score(
    rt: np.ndarray,
    peak: PeakResult,
    *,
    scans_target: int,
) -> float:
    if scans_target <= 0:
        raise ValueError("scans_target must be greater than 0")
    if rt.size == 0:
        return 0.0
    mask = (rt >= peak.peak_start) & (rt <= peak.peak_end)
    return min(1.0, float(np.count_nonzero(mask)) / float(scans_target))
```

- [ ] **Step 4: Run focused tests**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_discovery_scan_support.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add xic_extractor/discovery/ms1_backfill.py tests/test_discovery_scan_support.py
git commit -m "feat(discovery): compute MS1 scan support score"
```

## Task 3: Populate Scan Support During MS1 Backfill

**Files:**
- Modify: `xic_extractor/discovery/ms1_backfill.py`
- Modify: `tests/test_discovery_pipeline.py`

- [ ] **Step 1: Write failing integration tests**

Add tests that verify:

- A detected MS1 peak writes a numeric `ms1_scan_support_score`.
- A missing peak writes `0` or an explicitly chosen empty value; choose `0` for v1 because missing scan support is known absence.
- The score uses `settings.evidence_profile.thresholds.scan_support_target`.

- [ ] **Step 2: Run the red tests**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_discovery_pipeline.py -v -k scan_support
```

Expected: FAIL because backfill does not populate the field.

- [ ] **Step 3: Implement backfill propagation**

Extend `_Ms1Fields` with `scan_support_score`.

In `_detect_ms1_peak()`, compute it from RT array and selected peak.

In missing peak fields, set `scan_support_score=0.0`.

Pass `ms1_scan_support_score=ms1_fields.scan_support_score` into `DiscoveryCandidate.from_values()`.

- [ ] **Step 4: Run focused tests**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_discovery_pipeline.py tests/test_discovery_scan_support.py tests/test_discovery_csv.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add xic_extractor/discovery/ms1_backfill.py tests/test_discovery_pipeline.py
git commit -m "feat(discovery): populate MS1 scan support in candidates"
```

## Task 4: Use Scan Support In Evidence Scoring

**Files:**
- Modify: `xic_extractor/discovery/evidence_score.py`
- Modify: `tests/test_discovery_evidence.py`

- [ ] **Step 1: Write failing tests**

Add tests that verify:

- High numeric scan support adds the configured positive support.
- Low numeric scan support applies the configured penalty.
- Mid scan support does not get high or low trace points.
- Numeric score takes precedence over legacy `ms1_trace_quality`.
- Legacy string fallback still works when `ms1_scan_support_score is None`.

- [ ] **Step 2: Run the red tests**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_discovery_evidence.py -v -k scan_support
```

Expected: FAIL because scoring ignores the numeric field.

- [ ] **Step 3: Implement scoring integration**

Update scoring helper logic:

- Use `candidate.ms1_scan_support_score` when present.
- Compare against evidence profile thresholds.
- Fall back to `ms1_trace_quality` only when numeric score is `None`.

Update `classify_ms1_support()` so `strong` / `moderate` considers numeric scan support plus area, not only legacy strings.

- [ ] **Step 4: Run focused tests**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_discovery_evidence.py tests/test_discovery_pipeline.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add xic_extractor/discovery/evidence_score.py tests/test_discovery_evidence.py
git commit -m "feat(discovery): score MS1 scan support evidence"
```

## Final Validation

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_discovery_scan_support.py tests/test_discovery_evidence.py tests/test_discovery_pipeline.py tests/test_discovery_csv.py -v
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor tests scripts
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor
```

Optional real-data smoke after all three plans:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run xic-discovery-cli --raw-dir "C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation" --dll-dir "C:\Xcalibur\system\programs" --output-dir "output\discovery\tissue8_review_evidence_scan_support" --neutral-loss-tag DNA_dR --neutral-loss-da 116.0474 --resolver-mode local_minimum
```

