# Candidate-Level MS2 Evidence Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Separate broad MS2 trigger evidence from strict neutral-loss evidence, then attach both to the selected peak candidate instead of the whole target RT window.

**Architecture:** Keep Thermo `.raw` direct reading and existing resolver/scoring flow. Add a small MS2 evidence layer in `neutral_loss.py` that computes scan-level observed neutral loss and candidate-aligned support. Feed candidate-level evidence into `ScoringContext`, selection, reasons, and optional score breakdown without changing workbook default columns.

**Tech Stack:** Python 3.13, NumPy, pytest, Thermo RawFileReader via pythonnet, existing `uv run pytest` workflow.

---

## Background

The `BC1165_control.raw` urine audit exposed a real contract bug:

- Current `check_nl()` accepts an MS2 scan when `abs(scan.precursor_mz - target.mz) <= ms2_precursor_tol_da`, currently `1.6 Da`.
- It then checks product ion ppm against `target.mz - neutral_loss_da`.
- It does **not** verify that `scan.precursor_mz - product_mz` equals the specified `neutral_loss_da`.

Concrete false-positive example from:

`output/urine_bc1165_hmdc_ms2_candidate_audit.xlsx`

```text
target: d3-5-hmdC
scan RT: 8.939027
target mz: 261.127276
scan precursor mz: 262.156006
product mz: 145.079849

current product ppm vs target-derived product: 0.18 ppm -> NL OK today
observed loss: 262.156006 - 145.079849 = 117.076157
expected loss: 116.0474
loss delta: +1.028757 Da -> not the requested neutral loss
```

This means current `NL OK` can really mean "there is a product ion near target-derived product m/z inside a wide isolation window", not "this scan observed the configured neutral loss".

## Target Contract

### Evidence Layers

| Evidence | Precursor tolerance | Product / loss rule | Meaning | Scoring role |
|---|---:|---|---|---|
| `ms2_trigger_support` | existing broad `ms2_precursor_tol_da` | none | DDA likely triggered near the target precursor | soft positive evidence |
| `nl_product_support` | existing broad `ms2_precursor_tol_da` for scan discovery | product must satisfy observed-loss check | configured neutral loss was actually observed | strong positive evidence |

### Strict NL Rule

For each MS2 scan and candidate product ion:

```text
observed_loss_da = scan.precursor_mz - product_mz
loss_error_da = abs(observed_loss_da - neutral_loss_da)
loss_error_ppm = loss_error_da / neutral_loss_da * 1_000_000
```

`NL OK` requires:

- precursor within `ms2_precursor_tol_da`, so the scan is a plausible trigger for the target isolation window.
- product ion above `nl_min_intensity_ratio * scan.base_peak`.
- product m/z within diagnostic search ppm so the scan can be inspected.
- **observed loss ppm <= nl_ppm_max**.
- `WARN` when `nl_ppm_warn < observed loss ppm <= nl_ppm_max`.

`target.mz - neutral_loss_da` can remain useful for diagnostics, but it must not be the only `NL OK` condition.

### Candidate Alignment

Candidate-level support uses each `PeakCandidate` integration region:

```text
candidate peak_start <= scan.rt <= candidate peak_end
```

If no scan falls inside the candidate region, allow a small apex-neighborhood fallback:

```text
abs(scan.rt - candidate.selection_apex_rt) <= 0.08 min
```

The fallback handles sparse DDA scheduling where the MS2 scan lands just outside the local-minimum edge. It must be documented and tested.

### Non-Goals

- Do not change resolver defaults.
- Do not change area integration.
- Do not add GUI/config knobs in v1.
- Do not convert `.raw` to `.mzML`.
- Do not add workbook default columns.
- Do not make MS2 trigger or NL a hard ND gate.

## What Already Exists

- `xic_extractor/raw_reader.py`
  - `RawFileHandle.iter_ms2_scans()` yields scan RT, precursor m/z, masses, intensities, and base peak.
  - Reuse this. Do not add another raw reader path.

- `xic_extractor/neutral_loss.py`
  - `NLResult`, `check_nl()`, `find_nl_anchor_rt()`, and `_best_product_ppm()`.
  - Extend this module rather than creating a parallel MS2 utility.

- `xic_extractor/signal_processing.py`
  - `PeakCandidate` already has peak start/end, apex RT, quality flags, and metadata.
  - Reuse candidates for MS2 alignment.

- `xic_extractor/peak_scoring.py`
  - `ScoringContext` already has `ms2_present` and `nl_match`.
  - Preserve public scoring shape if possible, but redefine these values to come from candidate-aligned evidence.

- `xic_extractor/extraction/scoring_factory.py`
  - Currently maps target-window `NLResult` into every candidate.
  - This is the main place where candidate evidence must replace target-window evidence.

## Data Flow

```text
RAW MS2 scans
    |
    v
scan-level MS2 evidence
    |       \
    |        -> broad trigger support
    |
    v
strict observed-loss NL evidence
    |
    v
candidate alignment by peak region / apex fallback
    |
    v
ScoringContext per PeakCandidate
    |
    v
selection, confidence, reason, optional Score Breakdown
```

## Implementation Tasks

### Task 1: Add observed-loss scan evidence

**Files:**

- Modify: `xic_extractor/neutral_loss.py`
- Test: `tests/test_neutral_loss.py`

**Step 1: Write failing tests**

Add tests covering:

```python
def test_check_nl_rejects_target_product_when_observed_loss_is_wrong():
    # target mz 261.127276, neutral loss 116.0474
    # scan precursor 262.156006, product 145.079849
    # product is near target mz - loss, but observed loss is 117.076157
    # Expected: NL_FAIL, not OK
```

```python
def test_check_nl_accepts_observed_loss_within_threshold():
    # scan precursor 258.110077, product 142.061813, loss ~= 116.048264
    # Expected: OK for 116.0474 with nl_ppm_max=50
```

```python
def test_check_nl_warns_on_observed_loss_between_warn_and_max():
    # Construct a product ion where observed loss ppm is > warn and <= max.
    # Expected: WARN
```

**Step 2: Run red tests**

```powershell
uv run pytest tests/test_neutral_loss.py -v
```

Expected: first test fails because current implementation accepts target-derived product ppm without observed-loss validation.

**Step 3: Implement minimal scan evidence**

In `neutral_loss.py`:

- Add a frozen dataclass:

```python
@dataclass(frozen=True)
class MS2ProductEvidence:
    scan_rt: float
    precursor_mz: float
    product_mz: float
    product_intensity: float
    product_base_ratio: float
    target_product_ppm: float
    observed_loss_da: float
    observed_loss_error_ppm: float
```

- Replace or extend `_best_product_ppm()` with a helper that returns `MS2ProductEvidence | None`.
- Make `check_nl()` classify using `observed_loss_error_ppm`, not target-derived product ppm.
- Keep `best_ppm` as observed-loss ppm for backward compatibility of messages.

**Step 4: Run green tests**

```powershell
uv run pytest tests/test_neutral_loss.py -v
```

Expected: PASS.

**Step 5: Commit**

```powershell
git add xic_extractor/neutral_loss.py tests/test_neutral_loss.py
git commit -m "fix: validate neutral loss by observed product loss"
```

### Task 2: Keep NL anchor strict

**Files:**

- Modify: `xic_extractor/neutral_loss.py`
- Test: `tests/test_neutral_loss.py`

**Step 1: Write failing tests**

Add tests:

```python
def test_find_nl_anchor_rt_ignores_wrong_observed_loss_even_with_matching_target_product():
    # Same false-positive pattern as Task 1.
    # Expected: no anchor RT.
```

```python
def test_find_nl_anchor_rt_selects_highest_base_peak_among_strict_nl_matches():
    # Multiple strict matches, no reference RT.
    # Expected: highest base_peak scan.
```

```python
def test_find_nl_anchor_rt_selects_nearest_reference_among_strict_nl_matches():
    # Multiple strict matches, reference RT supplied.
    # Expected: nearest scan, tie-break by base peak.
```

**Step 2: Run red tests**

```powershell
uv run pytest tests/test_neutral_loss.py -v
```

Expected: anchor test fails before `find_nl_anchor_rt()` uses strict observed-loss evidence.

**Step 3: Implement minimal anchor update**

Use the same scan evidence helper from Task 1 inside `find_nl_anchor_rt()`.

**Step 4: Run green tests**

```powershell
uv run pytest tests/test_neutral_loss.py -v
```

Expected: PASS.

**Step 5: Commit**

```powershell
git add xic_extractor/neutral_loss.py tests/test_neutral_loss.py
git commit -m "fix: use strict neutral loss anchors"
```

### Task 3: Add candidate-aligned MS2 evidence

**Files:**

- Modify: `xic_extractor/neutral_loss.py`
- Test: `tests/test_neutral_loss.py`

**Step 1: Write failing tests**

Add tests for a new function:

```python
def collect_candidate_ms2_evidence(
    raw,
    *,
    candidate,
    precursor_mz,
    neutral_loss_da,
    nl_ppm_warn,
    nl_ppm_max,
    ms2_precursor_tol_da,
    nl_min_intensity_ratio,
) -> CandidateMS2Evidence:
    ...
```

Required cases:

```python
def test_candidate_evidence_counts_trigger_inside_peak_region():
    # MS2 precursor within tolerance and RT inside candidate peak_start/end.
    # Expected: ms2_trigger_count == 1, ms2_present True.
```

```python
def test_candidate_evidence_does_not_borrow_trigger_from_other_candidate_region():
    # MS2 scan within target window but outside candidate region and outside apex fallback.
    # Expected: ms2_present False for this candidate.
```

```python
def test_candidate_evidence_uses_apex_fallback_for_sparse_ms2():
    # Scan just outside peak edge but within 0.08 min of apex.
    # Expected: ms2_present True and alignment_source == "apex_fallback".
```

```python
def test_candidate_evidence_reports_strict_nl_match():
    # Trigger scan has observed-loss ppm <= max.
    # Expected: nl_match True, best_loss_ppm populated.
```

```python
def test_candidate_evidence_separates_trigger_from_failed_nl():
    # Trigger scan exists but observed loss is wrong.
    # Expected: ms2_present True, nl_match False.
```

**Step 2: Run red tests**

```powershell
uv run pytest tests/test_neutral_loss.py -v
```

Expected: FAIL because `CandidateMS2Evidence` and collector do not exist.

**Step 3: Implement minimal candidate evidence**

Add:

```python
@dataclass(frozen=True)
class CandidateMS2Evidence:
    ms2_present: bool
    nl_match: bool
    nl_status: NLStatus
    trigger_scan_count: int
    strict_nl_scan_count: int
    best_loss_ppm: float | None
    best_scan_rt: float | None
    best_product_base_ratio: float | None
    alignment_source: Literal["region", "apex_fallback", "none"]
```

Candidate inclusion rule:

```python
inside_region = candidate.peak.peak_start <= scan.rt <= candidate.peak.peak_end
near_apex = abs(scan.rt - candidate.selection_apex_rt) <= 0.08
```

Prefer `region` over `apex_fallback` when both exist.

**Step 4: Run green tests**

```powershell
uv run pytest tests/test_neutral_loss.py -v
```

Expected: PASS.

**Step 5: Commit**

```powershell
git add xic_extractor/neutral_loss.py tests/test_neutral_loss.py
git commit -m "feat: add candidate-level ms2 evidence"
```

### Task 4: Feed candidate evidence into scoring

**Files:**

- Modify: `xic_extractor/extraction/scoring_factory.py`
- Modify: `xic_extractor/peak_scoring.py`
- Test: `tests/test_peak_scoring.py`
- Test: `tests/test_signal_processing_selection.py` or `tests/test_extractor.py`

**Step 1: Write failing tests**

Add tests:

```python
def test_scoring_context_uses_candidate_ms2_evidence_not_target_window_nl():
    # Candidate A has no candidate-aligned MS2.
    # Target-window NL exists elsewhere.
    # Expected: A context has ms2_present False, nl_match False.
```

```python
def test_candidate_with_trigger_but_failed_nl_gets_ms2_present_without_nl_match():
    # Expected: severity/reason reflects MS2 trigger without strict NL.
```

```python
def test_strict_nl_candidate_beats_unaligned_target_window_nl_candidate():
    # Candidate A selected by MS1 only, Candidate B has aligned strict NL.
    # Expected: selector prefers B when confidence tier and RT constraints allow it.
```

**Step 2: Run red tests**

```powershell
uv run pytest tests/test_peak_scoring.py tests/test_signal_processing_selection.py -v
```

Expected: FAIL because scoring still reads target-window `NLResult` for every candidate.

**Step 3: Implement minimal scoring integration**

Change `build_scoring_context_factory()` so its per-candidate builder accepts or computes `CandidateMS2Evidence`.

Recommended minimal route:

- Keep target-window `NLResult` for diagnostics and messages.
- Add optional callable or evidence lookup to the scoring factory:

```python
candidate_ms2_evidence_builder: Callable[[PeakCandidate], CandidateMS2Evidence | None] | None
```

- In the `builder(candidate)`:

```python
candidate_ms2 = candidate_ms2_evidence_builder(candidate) if candidate_ms2_evidence_builder else None
ms2_present = candidate_ms2.ms2_present if candidate_ms2 else target_window_ms2_present
nl_match = candidate_ms2.nl_match if candidate_ms2 else target_window_nl_match
```

Fallback to target-window result only when no candidate-level builder is supplied, preserving unit-test helpers and non-raw paths.

**Step 4: Run green tests**

```powershell
uv run pytest tests/test_peak_scoring.py tests/test_signal_processing_selection.py -v
```

Expected: PASS.

**Step 5: Commit**

```powershell
git add xic_extractor/extraction/scoring_factory.py xic_extractor/peak_scoring.py tests/test_peak_scoring.py tests/test_signal_processing_selection.py
git commit -m "feat: score peaks with candidate-level ms2 evidence"
```

### Task 5: Wire candidate evidence in extraction

**Files:**

- Modify: `xic_extractor/extractor.py`
- Test: `tests/test_extractor.py`
- Test: `tests/test_extractor_run.py`

**Step 1: Write failing tests**

Add fake raw tests:

```python
def test_extractor_does_not_borrow_nl_from_other_candidate_region():
    # One target has two candidates.
    # MS2 strict NL scan aligns with candidate 1.
    # Candidate 2 has higher MS1 but no MS2.
    # Expected diagnostics/reason/selection reflect candidate 1 evidence only.
```

```python
def test_extractor_preserves_target_window_nl_diagnostics():
    # Target-window NLResult still emitted for diagnostics/output message compatibility.
```

**Step 2: Run red tests**

```powershell
uv run pytest tests/test_extractor.py tests/test_extractor_run.py -v
```

Expected: FAIL because extraction does not build candidate-aligned MS2 evidence.

**Step 3: Implement minimal extraction wiring**

In the raw-processing target path:

- Keep `_check_target_nl()` for diagnostics.
- Build a candidate evidence function using `raw`, `target`, and `config`.
- Pass it into scoring context factory.

Avoid re-reading all MS2 scans once per candidate if possible:

- First implementation may call `raw.iter_ms2_scans()` per candidate for correctness.
- If performance is poor in validation, refactor to cache target-window MS2 events once per target.
- Do not prematurely optimize before tests are green.

**Step 4: Run green tests**

```powershell
uv run pytest tests/test_extractor.py tests/test_extractor_run.py -v
```

Expected: PASS.

**Step 5: Commit**

```powershell
git add xic_extractor/extractor.py tests/test_extractor.py tests/test_extractor_run.py
git commit -m "feat: align ms2 evidence during extraction"
```

### Task 6: Update messages and score breakdown labels

**Files:**

- Modify: `xic_extractor/output/messages.py`
- Modify: `xic_extractor/peak_scoring.py`
- Test: `tests/test_output_messages.py`
- Test: `tests/test_score_breakdown.py` if present, otherwise nearest score-breakdown test

**Step 1: Write failing tests**

Add tests for reason text:

```python
def test_reason_distinguishes_ms2_trigger_from_strict_nl_match():
    # Expected text includes "MS2 trigger present; strict NL not matched"
```

```python
def test_reason_reports_strict_candidate_nl_support():
    # Expected text includes strict NL support wording, not generic target-window NL.
```

**Step 2: Run red tests**

```powershell
uv run pytest tests/test_output_messages.py tests/test_peak_scoring.py -v
```

Expected: FAIL until messages distinguish trigger and strict NL.

**Step 3: Implement minimal wording**

Use concise user-facing wording:

- `MS2 trigger near candidate; strict NL not matched`
- `strict NL matched near candidate`
- `no candidate-aligned MS2 trigger`

Do not add default workbook columns.

**Step 4: Run green tests**

```powershell
uv run pytest tests/test_output_messages.py tests/test_peak_scoring.py -v
```

Expected: PASS.

**Step 5: Commit**

```powershell
git add xic_extractor/output/messages.py xic_extractor/peak_scoring.py tests/test_output_messages.py tests/test_peak_scoring.py
git commit -m "docs: clarify candidate ms2 evidence reasons"
```

### Task 7: Documentation

**Files:**

- Modify: `README.md`
- Modify: `docs/superpowers/specs/2026-05-04-adap-like-trace-quality-scoring-spec.md` if present, otherwise create `docs/superpowers/specs/2026-05-05-candidate-ms2-evidence-spec.md`

**Step 1: Write doc contract checks**

If repo has README/doc smoke tests, extend them. Otherwise use `rg` verification in the task log.

Required docs wording:

- MS2 trigger evidence is broad isolation-window evidence.
- Strict NL evidence uses observed precursor-product loss.
- Candidate-level evidence does not add workbook default columns.
- `count_no_ms2_as_detected` remains a DDA missing-trigger accommodation, not an NL override.

**Step 2: Run relevant checks**

```powershell
uv run pytest tests/test_readme_examples.py -v
```

If that test file does not exist:

```powershell
rg -n "MS2 trigger|strict NL|observed loss|candidate-level" README.md docs/superpowers
```

**Step 3: Commit**

```powershell
git add README.md docs/superpowers
git commit -m "docs: document candidate-level ms2 evidence"
```

### Task 8: Real-data validation

**Files:**

- Create output artifacts under `output/`.
- Do not commit generated validation workbooks unless explicitly requested.

**Step 1: Re-run targeted urine audit**

Use `BC1165_control.raw` from:

```text
C:\Xcalibur\data\20260105_CSMU_NAA_Urine
```

Targets:

- `d3-5-hmdC`
- `5-hmdC`

Expected:

- `d3-5-hmdC` scans where observed loss is ~117 Da no longer produce strict `NL OK`.
- Candidate reason distinguishes trigger-only evidence from strict NL evidence.
- No candidate borrows NL support from another candidate region.

**Step 2: Run 8-raw validation subset if targeted audit is stable**

Use the existing validation subset, not the full 85 raws:

```text
C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation
```

Set:

```text
resolver_mode=local_minimum
parallel_mode=process
parallel_workers=4
```

Expected:

- Detection loss is explainable and caused by removing false NL support, not random selection drift.
- Any new changed rows have reason text that explains trigger-only vs strict NL evidence.

**Step 3: Run related tests and full suite**

```powershell
uv run pytest tests/test_neutral_loss.py tests/test_peak_scoring.py tests/test_signal_processing_selection.py tests/test_extractor.py -v
uv run pytest --tb=short -q
```

**Step 4: Commit validation docs only if needed**

If docs or fixtures change:

```powershell
git add <changed-doc-or-fixture-files>
git commit -m "test: validate candidate-level ms2 evidence"
```

## Failure Modes

| Failure mode | Expected handling | Test coverage |
|---|---|---|
| Product ion near `target.mz - loss` but observed scan loss is wrong | `NL_FAIL`, optional trigger-only evidence | Task 1 |
| Strict NL anchor uses false-positive target-derived product | no anchor | Task 2 |
| MS2 scan in target window belongs to a different candidate | not counted for current candidate | Task 3 |
| Sparse MS2 scan just outside peak edge | counted only through 0.08 min apex fallback | Task 3 |
| Candidate-level builder unavailable in old tests/helpers | fallback to existing target-window behavior | Task 4 |
| Real raw has many candidates and many MS2 scans | correctness first, cache later if validation shows slowdown | Task 8 |

## Parallelization Strategy

Sequential implementation is preferred.

Reason: Tasks 1-3 define the evidence contract in `neutral_loss.py`; Tasks 4-6 depend on that exact dataclass/API. Parallelizing before the evidence contract lands would create merge churn in `peak_scoring.py`, `scoring_factory.py`, and `extractor.py`.

After Task 3 is merged, docs Task 7 can run in parallel with extraction wiring Task 5, but only if the doc writer treats names as provisional and the main agent reconciles final wording.

## NOT in Scope

- Local-minimum parameter tuning: deferred because the issue is evidence attribution, not peak splitting.
- Area integration changes: deferred because MS2 evidence should select/score candidates, not change raw area math.
- New GUI controls: deferred until real-data validation proves thresholds need user control.
- mzML conversion or MZmine parity: deferred because this repo intentionally reads Thermo `.raw` directly.
- Hard MS2/NL gates: deferred because DDA triggering is stochastic and missing MS2 can be false negative.

## Engineering Review

### Review Result

Status: **approved with implementation guardrails**

### Findings

1. **Observed-loss validation is mandatory.**
   Current `NL OK` can pass when product ppm is excellent against `target.mz - neutral_loss_da` but the actual scan precursor implies the wrong neutral loss. Task 1 and Task 2 address this directly.

2. **Candidate-level alignment must precede weighting changes.**
   Increasing MS2 weight before attribution is fixed would make the wrong evidence more influential. The plan therefore changes evidence ownership before changing selector behavior.

3. **Do not collapse trigger-only and strict NL into one boolean.**
   The urine example shows MS2 trigger intensity can be useful even without strict NL. Keeping `ms2_present` and `nl_match` separate preserves that signal.

4. **Apex fallback needs a fixed v1 constant and tests.**
   The `0.08 min` fallback is intentionally conservative and matches the existing local-minimum search scale. It must not become a hidden wide RT anchor.

5. **Performance risk is acceptable for v1 but must be watched.**
   Per-candidate MS2 scanning can be slow if implemented naively. The plan allows correctness-first implementation, but real-data validation should note runtime and add caching if needed.

### Review Verdict

The plan is ready to implement. The key acceptance gate is the `BC1165_control / d3-5-hmdC` false-positive case: scans with observed loss around `117.076 Da` must no longer produce strict `NL OK` for configured `116.0474 Da`.
