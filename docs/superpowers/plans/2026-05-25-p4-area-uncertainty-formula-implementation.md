# P4 Area Uncertainty Formula Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the audit-only `area_uncertainty` formula with baseline-residual noise propagation while preserving production area, scoring, alignment, and matrix decisions.

**Architecture:** Keep the formula inside `xic_extractor/peak_detection/baseline.py`, where area and uncertainty are already computed together. `build_cell_integration_audit_summary(...)` performs one per-trace AsLS noise fit and passes the cached baseline/residual MAD into linear-edge and optional AsLS audit integration so P4 does not add avoidable duplicate AsLS work. TSV writers emit additive provenance columns so downstream readers can distinguish the new formula from the legacy in-peak first-difference MAD formula.

**Tech Stack:** Python, NumPy, existing `asls_baseline`, pytest, PowerShell validation commands.

---

## Plan Review Log

- Initial plan status: drafted from `docs/superpowers/specs/2026-05-24-peak-pipeline-area-uncertainty-formula-spec.md` after CodeGraph/context inspection of `BaselineIntegration`, `CellIntegrationAuditSummary`, and `write_alignment_cell_integration_audit_tsv`.
- Plan review patch 1: added explicit noise-source provenance because the fallback path is not literally AsLS residual MAD; clarified that `area_uncertainty_noise_source` is additive audit provenance.
- Plan review patch 2: removed the implied `integrate_with_baseline(...)` cache-extension path. P4 should call `integrate_asls_baseline(..., baseline_values=asls_baseline_values)` directly from `integration_audit.py` when AsLS shadow output is requested.
- Plan review patch 3: replaced the vague real-data validation instruction with the exact P2/P4 evidence-spine and area-uncertainty commands used for the 8RAW validation surface.
- Post-implementation review patch 4: P4 provenance must also be emitted by targeted `peak_candidates.tsv` and `peak_candidate_boundaries.tsv` because they already expose `area_uncertainty` from the same integration helper.

## Scope Lock

- In scope: `area_uncertainty` numeric semantics, audit-side provenance fields, unit tests, schema tests, diagnostic compatibility tests, and a validation note.
- Not in scope: P2b promotion, AsLS production area promotion, scoring thresholds, selected peak boundaries, alignment grouping, matrix identity, Cleanup C-specs, pyOpenMS/OBI-Warp, or any production `.raw` input contract.
- Gate language: P4 can only be `audit_only` or `inconclusive`. Passing P4 does not make P2b production-ready by itself.

## Files

- Modify: `xic_extractor/peak_detection/baseline.py`
  - Add formula-version constant.
  - Add provenance fields to `BaselineIntegration`.
  - Replace `_area_uncertainty_counts_seconds(...)` with baseline-residual noise propagation.
  - Add a small AsLS residual MAD helper and a pre-peak fallback MAD helper.
- Modify: `xic_extractor/peak_detection/integration_audit.py`
  - Add provenance fields to `CellIntegrationAuditSummary`.
  - Compute/reuse one AsLS baseline + residual MAD per audit summary and pass it into linear-edge and optional AsLS shadow integration.
- Modify: `xic_extractor/alignment/tsv_writer.py`
  - Add TSV-local provenance columns: `area_uncertainty_formula_version`, `baseline_residual_mad`, and `area_uncertainty_noise_source`.
- Modify: `xic_extractor/peak_detection/hypotheses.py`
  - Carry the same provenance fields from `BaselineIntegration` into targeted `IntegrationResult`.
- Modify: `xic_extractor/extraction/peak_candidate_table.py`
  - Emit the same provenance columns next to targeted `area_uncertainty`.
- Modify: `xic_extractor/extraction/peak_candidate_boundaries.py`
  - Emit the same provenance columns next to boundary-audit `area_uncertainty`.
- Modify: `tests/test_baseline_integration.py`
  - Add formula behavior tests and update old assumptions.
- Modify: `tests/test_alignment_tsv_writer.py`
  - Update audit TSV schema expectations and add provenance-column assertions.
- Modify: `tests/test_area_integration_uncertainty_audit.py`
  - Add a compatibility test showing the diagnostic still reads alignment audit TSVs with P4 provenance columns.
- Modify: `tests/test_peak_candidate_table.py`
  - Add targeted candidate provenance assertions.
- Modify: `tests/test_peak_candidate_boundaries.py`
  - Add boundary-audit provenance assertions.
- Modify: `tests/test_peak_candidate_audit.py`
  - Add append-path provenance assertions.
- Modify: `docs/superpowers/specs/2026-05-18-area-integration-uncertainty-decision.md`
  - Record that any prior thresholds/counts predate `baseline_residual_mad_v1`.
- Create: `docs/superpowers/notes/2026-05-25-p4-area-uncertainty-formula-validation-note.md`
  - Record unit-test verification, 8RAW validation commands, before/after bucket counts if available, and the final P4 verdict.

## Formula Contract

Use this formula version string everywhere:

```text
baseline_residual_mad_v1
```

The formula is:

```text
noise_per_scan = baseline_residual_mad
scan_period_s = median(diff(rt_values_minutes)) * 60.0
n_points = right_index - left_index
area_uncertainty = noise_per_scan * scan_period_s * sqrt(n_points)
```

Return `None` for `area_uncertainty` when:

- fewer than 2 integration scans are available
- scan period is missing, non-finite, or `<= 0`
- no AsLS residual MAD or pre-peak fallback MAD can be computed
- the noise MAD is non-finite

Do not use in-peak first-difference MAD as any fallback. When the fallback
fires, `baseline_residual_mad` stores the MAD value used by the formula and
`area_uncertainty_noise_source` records `pre_peak_mad`, so reviewers can tell
that the value did not come from an AsLS residual.

## Task 1: Baseline Formula Tests

**Files:**

- Modify: `tests/test_baseline_integration.py`

- [x] **Step 1: Add a test proving equal baseline noise gives similar uncertainty for short/tall peaks**

Add this test near the existing baseline integration tests:

```python
def test_area_uncertainty_uses_baseline_residual_noise_not_peak_height(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rt = np.linspace(0.0, 0.9, 10)
    low_peak = np.asarray([10, 10, 10, 12, 18, 12, 10, 10, 10, 10], dtype=float)
    high_peak = np.asarray([10, 10, 10, 20, 90, 20, 10, 10, 10, 10], dtype=float)
    shared_baseline = np.full_like(rt, 10.0)

    monkeypatch.setattr(
        "xic_extractor.peak_detection.baseline.asls_baseline",
        lambda values, **_kwargs: shared_baseline,
    )

    low = integrate_linear_edge_baseline(low_peak, rt, 3, 6)
    high = integrate_linear_edge_baseline(high_peak, rt, 3, 6)

    assert low.area_uncertainty_formula_version == "baseline_residual_mad_v1"
    assert high.area_uncertainty_formula_version == "baseline_residual_mad_v1"
    assert low.area_uncertainty == pytest.approx(high.area_uncertainty)
    assert high.area_baseline_corrected > low.area_baseline_corrected
```

- [x] **Step 2: Run the narrow test and confirm it fails before implementation**

Run:

```powershell
$env:PYTHONPATH = (Get-Location).Path
C:\Users\user\Desktop\XIC_Extractor\.venv\Scripts\python.exe -m pytest tests\test_baseline_integration.py::test_area_uncertainty_uses_baseline_residual_noise_not_peak_height -q
```

Expected before implementation: fail because `BaselineIntegration` does not yet expose `area_uncertainty_formula_version`, or because the uncertainty still uses in-peak first differences.

- [x] **Step 3: Add invalid/fallback behavior tests**

Add tests covering:

```python
def test_area_uncertainty_returns_none_for_non_positive_scan_period() -> None:
    rt = np.asarray([0.1, 0.1, 0.1, 0.1])
    intensity = np.asarray([10.0, 20.0, 25.0, 12.0])

    result = integrate_linear_edge_baseline(intensity, rt, 0, 4)

    assert result.area_uncertainty is None
    assert result.baseline_residual_mad is None


def test_area_uncertainty_can_fallback_to_pre_peak_mad(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rt = np.linspace(0.0, 0.9, 10)
    intensity = np.asarray([9, 11, 10, 9, 20, 80, 25, 10, 11, 9], dtype=float)

    def _raise_asls(_values: np.ndarray, **_kwargs: object) -> np.ndarray:
        raise ValueError("fit failed")

    monkeypatch.setattr(
        "xic_extractor.peak_detection.baseline.asls_baseline",
        _raise_asls,
    )

    result = integrate_linear_edge_baseline(intensity, rt, 4, 7)

    assert result.area_uncertainty is not None
    assert result.baseline_residual_mad is not None
    assert result.area_uncertainty_noise_source == "pre_peak_mad"
```

Expected before implementation: fail because fallback/provenance does not exist.

## Task 2: Baseline Formula Implementation

**Files:**

- Modify: `xic_extractor/peak_detection/baseline.py`

- [x] **Step 1: Add provenance fields and the version constant**

Add:

```python
AREA_UNCERTAINTY_FORMULA_VERSION = "baseline_residual_mad_v1"
```

Extend `BaselineIntegration`:

```python
@dataclass(frozen=True)
class BaselineIntegration:
    area_baseline_corrected: float
    area_uncertainty: float | None
    baseline_type: str
    baseline_score: float | None
    area_uncertainty_formula_version: str = ""
    baseline_residual_mad: float | None = None
    area_uncertainty_noise_source: str = ""
```

- [x] **Step 2: Replace the legacy uncertainty helper**

Replace `_area_uncertainty_counts_seconds(...)` with helpers shaped like:

```python
def compute_asls_residual_mad(
    intensity_values: np.ndarray,
    *,
    baseline_values: np.ndarray | None = None,
) -> tuple[np.ndarray | None, float | None]:
    values = np.asarray(intensity_values, dtype=float)
    if len(values) < 5 or not np.all(np.isfinite(values)):
        return None, None
    try:
        baseline = (
            np.asarray(baseline_values, dtype=float)
            if baseline_values is not None
            else asls_baseline(values)
        )
    except (ValueError, FloatingPointError):
        return None, None
    if baseline.shape != values.shape:
        return None, None
    residual = values - baseline
    residual_mad = float(np.median(np.abs(residual - np.median(residual))))
    if not np.isfinite(residual_mad):
        return baseline, None
    return baseline, residual_mad


def _area_uncertainty_counts_seconds(
    rt_values: np.ndarray,
    intensity_values: np.ndarray,
    left_index: int,
    right_index: int,
    *,
    baseline_residual_mad: float | None = None,
) -> float | None:
    noise = baseline_residual_mad
    if noise is None or not np.isfinite(noise):
        return None
    scan_period_s = _median_scan_period_seconds(rt_values)
    if scan_period_s is None:
        return None
    n_points = right_index - left_index
    if n_points < 2:
        return None
    return float(noise * scan_period_s * np.sqrt(n_points))
```

Also add `_median_scan_period_seconds(...)` and `_pre_peak_mad(...)`. `_pre_peak_mad(...)` must only inspect scans before `left_index` and must return `None` when fewer than three finite baseline-window points are available.

- [x] **Step 3: Wire linear-edge integration to the new helper**

Update `integrate_linear_edge_baseline(...)` to accept optional cached AsLS inputs:

```python
def integrate_linear_edge_baseline(
    intensity_values: np.ndarray,
    rt_values: np.ndarray,
    left: int,
    right: int,
    *,
    uncertainty_baseline_values: np.ndarray | None = None,
    baseline_residual_mad: float | None = None,
) -> BaselineIntegration:
```

Inside the function:

```python
residual_mad = baseline_residual_mad
if residual_mad is None:
    _asls_values, residual_mad = compute_asls_residual_mad(
        intensity,
        baseline_values=uncertainty_baseline_values,
    )
noise_source = "asls_residual" if residual_mad is not None else ""
if residual_mad is None:
    residual_mad = _pre_peak_mad(intensity, left_index)
    noise_source = "pre_peak_mad" if residual_mad is not None else ""
uncertainty = _area_uncertainty_counts_seconds(
    rt,
    intensity,
    left_index,
    right_index,
    baseline_residual_mad=residual_mad,
)
```

Return the new provenance fields. Do not call `asls_baseline(...)` when a
valid `baseline_residual_mad` was provided by the audit summary builder.

- [x] **Step 4: Preserve AsLS integration behavior**

Update `integrate_asls_baseline(...)` return values so its new provenance fields are explicitly blank/`None`. Do not change `area_baseline_corrected`, `baseline_type`, or `baseline_score`.

- [x] **Step 5: Run baseline tests**

Run:

```powershell
$env:PYTHONPATH = (Get-Location).Path
C:\Users\user\Desktop\XIC_Extractor\.venv\Scripts\python.exe -m pytest tests\test_baseline_integration.py -q
```

Expected after implementation: pass.

## Task 3: Integration Audit Reuse And Provenance

**Files:**

- Modify: `xic_extractor/peak_detection/integration_audit.py`
- Modify: `tests/test_baseline_integration.py`

- [x] **Step 1: Add summary-level provenance assertions**

Extend `test_cell_integration_audit_reports_baseline_corrected_area`:

```python
assert summary.area_uncertainty_formula_version == "baseline_residual_mad_v1"
assert summary.baseline_residual_mad is not None
assert summary.area_uncertainty_noise_source in {"asls_residual", "pre_peak_mad"}
```

- [x] **Step 2: Add a reuse test for AsLS shadow mode**

Add:

```python
def test_cell_integration_audit_reuses_asls_fit_for_uncertainty_and_shadow(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rt = np.linspace(0.0, 0.5, 6)
    intensity = np.asarray([8.0, 12.0, 70.0, 65.0, 20.0, 12.0])
    calls = 0

    def _fake_asls(values: np.ndarray, **_kwargs: object) -> np.ndarray:
        nonlocal calls
        calls += 1
        return np.full_like(values, 8.0)

    monkeypatch.setattr(
        "xic_extractor.peak_detection.baseline.asls_baseline",
        _fake_asls,
    )

    summary = build_cell_integration_audit_summary(
        rt,
        intensity,
        peak_start_rt=0.1,
        peak_end_rt=0.4,
        raw_area=60.0 * float(np.trapezoid(intensity[1:5], rt[1:5])),
        baseline_audit_method="asls",
    )

    assert calls == 1
    assert summary.area_baseline_corrected_asls is not None
    assert summary.baseline_residual_mad is not None
```

- [x] **Step 3: Implement reuse in `integration_audit.py`**

Import:

```python
from xic_extractor.peak_detection.baseline import (
    compute_asls_residual_mad,
    integrate_asls_baseline,
)
```

Extend `CellIntegrationAuditSummary` with:

```python
area_uncertainty_formula_version: str = ""
baseline_residual_mad: float | None = None
area_uncertainty_noise_source: str = ""
```

Before calling `integrate_linear_edge_baseline(...)`, compute:

```python
asls_baseline_values, residual_mad = compute_asls_residual_mad(intensity)
```

Pass `asls_baseline_values` and `residual_mad` to
`integrate_linear_edge_baseline(...)`. When `baseline_audit_method == "asls"`,
call `integrate_asls_baseline(...)` directly with
`baseline_values=asls_baseline_values`:

```python
asls_shadow = (
    integrate_asls_baseline(
        intensity,
        rt,
        left_index,
        right_index,
        baseline_values=asls_baseline_values,
    )
    if baseline_audit_method == "asls" and asls_baseline_values is not None
    else None
)
```

- [x] **Step 4: Run targeted integration audit tests**

Run:

```powershell
$env:PYTHONPATH = (Get-Location).Path
C:\Users\user\Desktop\XIC_Extractor\.venv\Scripts\python.exe -m pytest tests\test_baseline_integration.py -q
```

Expected: pass.

## Task 4: TSV Schema And Diagnostic Compatibility

**Files:**

- Modify: `xic_extractor/alignment/tsv_writer.py`
- Modify: `tests/test_alignment_tsv_writer.py`
- Modify: `tests/test_area_integration_uncertainty_audit.py`

- [x] **Step 1: Update TSV schema tests**

In `test_write_alignment_cell_integration_audit_tsv_is_sidecar`, assert:

```python
assert audit[0]["area_uncertainty_formula_version"] == "baseline_residual_mad_v1"
assert audit[0]["baseline_residual_mad"] != ""
assert audit[0]["area_uncertainty_noise_source"] != ""
```

Rename `test_write_alignment_cell_integration_audit_tsv_default_schema_is_unchanged` to:

```python
def test_write_alignment_cell_integration_audit_tsv_default_schema_includes_p4_provenance(
```

and expect the new columns to be part of `ALIGNMENT_CELL_INTEGRATION_AUDIT_COLUMNS`.

- [x] **Step 2: Add the TSV columns**

In `ALIGNMENT_CELL_INTEGRATION_AUDIT_COLUMNS`, insert these after `area_uncertainty`:

```python
"area_uncertainty_formula_version",
"baseline_residual_mad",
"area_uncertainty_noise_source",
```

In `write_alignment_cell_integration_audit_tsv(...)`, write:

```python
"area_uncertainty_formula_version": audit.area_uncertainty_formula_version,
"baseline_residual_mad": format_value(audit.baseline_residual_mad),
"area_uncertainty_noise_source": audit.area_uncertainty_noise_source,
```

- [x] **Step 3: Add diagnostic compatibility coverage**

Add an alignment-row fixture in `tests/test_area_integration_uncertainty_audit.py` that includes the three new P4 columns and proves `run_area_integration_uncertainty_audit(...)` still succeeds and keeps old bucket logic based on `uncertainty_fraction`.

- [x] **Step 4: Run writer and diagnostic tests**

Run:

```powershell
$env:PYTHONPATH = (Get-Location).Path
C:\Users\user\Desktop\XIC_Extractor\.venv\Scripts\python.exe -m pytest tests\test_alignment_tsv_writer.py tests\test_area_integration_uncertainty_audit.py -q
```

Expected: pass.

## Task 5: Documentation And Validation Note

**Files:**

- Modify: `docs/superpowers/specs/2026-05-18-area-integration-uncertainty-decision.md`
- Create: `docs/superpowers/notes/2026-05-25-p4-area-uncertainty-formula-validation-note.md`

- [x] **Step 1: Document compatibility**

Add a short note to the 2026-05-18 decision spec:

```markdown
## 2026-05-25 P4 Formula Compatibility Note

The original decision used the legacy in-peak first-difference MAD
`area_uncertainty` formula. P4 changes the audit TSV value to
`baseline_residual_mad_v1` and emits TSV-local provenance columns. Prior
bucket counts and thresholds should not be compared numerically without
re-running the area uncertainty diagnostic.
```

- [x] **Step 2: Create the validation note skeleton**

Create the P4 validation note with:

```markdown
# P4 Area Uncertainty Formula Validation Note

Gate status: `audit_only`.

Formula version: `baseline_residual_mad_v1`.

## Verification

- Unit tests:
- TSV schema/diagnostic compatibility:
- 8RAW area uncertainty audit:

## Decision

P4 changes audit-field semantics only. It does not change production area,
scoring, alignment, matrix identity, P2b, or Cleanup readiness.
```

- [x] **Step 3: Run narrow test set**

Run:

```powershell
$env:PYTHONPATH = (Get-Location).Path
C:\Users\user\Desktop\XIC_Extractor\.venv\Scripts\python.exe -m pytest tests\test_baseline_integration.py tests\test_alignment_tsv_writer.py tests\test_area_integration_uncertainty_audit.py -q
```

Expected: pass.

- [x] **Step 4: Run broader P2/P4 safety set**

Run:

```powershell
$env:PYTHONPATH = (Get-Location).Path
C:\Users\user\Desktop\XIC_Extractor\.venv\Scripts\python.exe -m pytest tests\test_alignment_pipeline_outputs.py tests\test_alignment_process_backend.py tests\test_alignment_tsv_writer.py tests\test_baseline_integration.py tests\test_p2_asls_shadow_gate.py tests\test_p2_baseline_truth_audit.py tests\test_area_integration_uncertainty_audit.py -q
```

Expected: pass.

- [x] **Step 5: Real-data validation**

First rerun the evidence-spine comparison against the P2/P4 alignment output:

```powershell
$env:PYTHONPATH = (Get-Location).Path
C:\Users\user\Desktop\XIC_Extractor\.venv\Scripts\python.exe -m tools.diagnostics.evidence_spine_consistency `
  --targeted-dir output\phase1_p1_resolver_default_validation\targeted\region_first_safe_merge\tissue_8raw_region_first_safe_merge `
  --alignment-dir output\phase1_p2_asls_shadow_validation\alignment\asls_shadow `
  --output-dir output\phase1_p4_area_uncertainty_formula\diagnostics\evidence_spine_consistency
```

Then rerun the area integration uncertainty diagnostic:

```powershell
$env:PYTHONPATH = (Get-Location).Path
C:\Users\user\Desktop\XIC_Extractor\.venv\Scripts\python.exe -m tools.diagnostics.area_integration_uncertainty_audit `
  --evidence-spine-rows-tsv output\phase1_p4_area_uncertainty_formula\diagnostics\evidence_spine_consistency\evidence_spine_consistency_rows.tsv `
  --targeted-peak-candidates-tsv output\phase1_p1_resolver_default_validation\targeted\region_first_safe_merge\tissue_8raw_region_first_safe_merge\peak_candidates.tsv `
  --targeted-boundaries-tsv output\phase1_p1_resolver_default_validation\targeted\region_first_safe_merge\tissue_8raw_region_first_safe_merge\peak_candidate_boundaries.tsv `
  --alignment-integration-audit-tsv output\phase1_p2_asls_shadow_validation\alignment\asls_shadow\alignment_cell_integration_audit.tsv `
  --output-dir output\phase1_p4_area_uncertainty_formula\diagnostics\area_integration_uncertainty
```

Record exact result paths, bucket counts, and whether
`unexplained_area_mismatch_count` remains `0`. Stop and mark P4
`inconclusive` if the required real-data artifacts are missing or stale; do
not fabricate before/after counts.

## Post-Implementation Review Checklist

- [x] `area_uncertainty` no longer uses in-peak first differences.
- [x] P4 provenance columns are TSV-local and additive.
- [x] Targeted candidate and boundary audit TSVs also carry P4 provenance.
- [x] Production area fields and scoring decisions are unchanged by code path.
- [x] AsLS is reused inside `build_cell_integration_audit_summary(...)` when P2 shadow columns are requested.
- [x] The area uncertainty diagnostic still consumes existing required columns.
- [x] Validation note states formula version, commands, outputs, and remaining risk.
