# P2 Baseline Truth Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a diagnostic-only baseline truth audit for the P2 AsLS shadow NO-GO targets so reviewers can judge whether linear-edge is over-subtracting, AsLS is under-subtracting, or the difference is biologically/technically plausible.

**Architecture:** Add a standalone diagnostic CLI under `tools/diagnostics/` that reads existing P2 artifacts, re-extracts RAW XIC traces for selected failed ISTD families, recomputes linear-edge and AsLS baseline curves on the same trace window, and emits TSV/JSON/Markdown plus PNG overlays. The diagnostic must not feed production alignment, workbook, scoring, or Cleanup paths.

**Tech Stack:** Python, NumPy, matplotlib Agg backend, existing `xic_extractor.raw_reader.open_raw`, existing `integrate_linear_edge_baseline`, `integrate_asls_baseline`, pytest.

---

## Plan Review Log

- Initial plan status: reviewed and patched before implementation.
- Scope lock: P2 diagnostic only. Do not change `area_baseline_corrected`, `p2_asls_shadow_gate`, P2b, P3, P4, P5, P6, or Cleanup C-specs in this plan.
- Stop condition: if the audit requires changing public TSV schemas outside its own new sidecar files, stop and write a note instead of implementing.
- Patch 1: removed placeholder note text and replaced it with exact fields that must be filled from current outputs.
- Patch 2: kept the diagnostic output isolated under `output/phase1_p2_baseline_truth_audit/` so existing alignment TSV contracts do not change.

## Current Evidence To Preserve

- P2 AsLS shadow gate failed with `overall_status=FAIL`, `failed_count=3`, `max_area_rsd_delta_pct=3.85879`.
- Failing strict ISTD families:
  - `d3-5-hmdC` / `FAM000153`
  - `d4-N6-2HE-dA` / `FAM000807`
  - `d3-dG-C8-MeIQx` / `FAM001878`
- `max_asls_exceeds_raw_area_count=0`, so the observed failure is not an obvious `AsLS area > raw area` hard bug.
- Existing evidence suggests AsLS often returns area close to raw area while linear-edge subtracts 5-24%, which may indicate linear-edge over-subtraction or AsLS under-subtraction. This audit must make that visually and quantitatively reviewable.

## Files

- Create: `tools/diagnostics/p2_baseline_truth_audit.py`
- Create: `tests/test_p2_baseline_truth_audit.py`
- Create: `docs/superpowers/notes/2026-05-25-p2-baseline-truth-audit-note.md`
- Write runtime outputs under: `output/phase1_p2_baseline_truth_audit/`

## Outputs

The new CLI writes:

- `baseline_truth_audit_rows.tsv`: one row per target/sample cell.
- `baseline_truth_audit_summary.tsv`: one row per target/family.
- `baseline_truth_audit.json`: machine-readable rows and summary.
- `baseline_truth_audit.md`: compact human review index with top blocker rows and linked plot paths.
- `plots/<target_label>__<feature_family_id>.png`: 8RAW trace overlay panel for each selected family.

Rows must include:

- `target_label`
- `feature_family_id`
- `sample_stem`
- `status`
- `raw_area`
- `linear_area`
- `asls_area`
- `linear_raw_pct`
- `asls_raw_pct`
- `asls_vs_linear_pct`
- `linear_baseline_subtracted_pct`
- `asls_baseline_subtracted_pct`
- `linear_edge_delta_pct`
- `outside_background_pct`
- `peak_start_rt`
- `apex_rt`
- `peak_end_rt`
- `trace_point_count`
- `classification`
- `review_reason`
- `plot_path`

Classification values:

- `linear_edge_over_subtraction_plausible`
- `asls_under_subtraction_plausible`
- `methods_similar`
- `mixed_or_review_required`
- `not_assessable`

## Task 1: Calculation Tests And Data Model

**Files:**

- Create: `tests/test_p2_baseline_truth_audit.py`
- Create: `tools/diagnostics/p2_baseline_truth_audit.py`

- [x] **Step 1: Add failing tests for cell-level metrics and classification**

Create `tests/test_p2_baseline_truth_audit.py` with:

```python
from __future__ import annotations

import pytest

from tools.diagnostics.p2_baseline_truth_audit import (
    classify_baseline_truth_row,
    compute_area_metrics,
)


def test_compute_area_metrics_reports_method_differences() -> None:
    metrics = compute_area_metrics(raw_area=100.0, linear_area=80.0, asls_area=98.0)

    assert metrics.linear_raw_pct == pytest.approx(80.0)
    assert metrics.asls_raw_pct == pytest.approx(98.0)
    assert metrics.asls_vs_linear_pct == pytest.approx(22.5)
    assert metrics.linear_baseline_subtracted_pct == pytest.approx(20.0)
    assert metrics.asls_baseline_subtracted_pct == pytest.approx(2.0)


def test_classifies_linear_edge_over_subtraction_plausible() -> None:
    metrics = compute_area_metrics(raw_area=100.0, linear_area=78.0, asls_area=99.0)

    classification, reason = classify_baseline_truth_row(
        metrics,
        trace_point_count=20,
        linear_edge_delta_pct=18.0,
    )

    assert classification == "linear_edge_over_subtraction_plausible"
    assert "linear_subtracts_gt_10pct" in reason
    assert "asls_near_raw" in reason


def test_classifies_asls_under_subtraction_plausible() -> None:
    metrics = compute_area_metrics(raw_area=100.0, linear_area=82.0, asls_area=99.5)

    classification, reason = classify_baseline_truth_row(
        metrics,
        trace_point_count=20,
        linear_edge_delta_pct=1.0,
    )

    assert classification == "asls_under_subtraction_plausible"
    assert "asls_near_raw" in reason
    assert "linear_edge_not_elevated" in reason


def test_classifies_methods_similar() -> None:
    metrics = compute_area_metrics(raw_area=100.0, linear_area=94.0, asls_area=96.0)

    classification, reason = classify_baseline_truth_row(
        metrics,
        trace_point_count=20,
        linear_edge_delta_pct=2.0,
    )

    assert classification == "methods_similar"
    assert "asls_vs_linear_within_5pct" in reason
```

- [x] **Step 2: Run tests and confirm they fail**

Run:

```powershell
$env:PYTHONPATH = (Get-Location).Path
C:\Users\user\Desktop\XIC_Extractor\.venv\Scripts\python.exe -m pytest tests\test_p2_baseline_truth_audit.py -q
```

Expected: import failure because the diagnostic module does not exist.

- [x] **Step 3: Implement metric dataclass and classifier**

In `tools/diagnostics/p2_baseline_truth_audit.py`, add:

```python
from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class AreaMetrics:
    linear_raw_pct: float | None
    asls_raw_pct: float | None
    asls_vs_linear_pct: float | None
    linear_baseline_subtracted_pct: float | None
    asls_baseline_subtracted_pct: float | None


def compute_area_metrics(
    *,
    raw_area: float | None,
    linear_area: float | None,
    asls_area: float | None,
) -> AreaMetrics:
    linear_raw_pct = _ratio_pct(linear_area, raw_area)
    asls_raw_pct = _ratio_pct(asls_area, raw_area)
    asls_vs_linear_pct = (
        None
        if linear_area is None or linear_area <= 0 or asls_area is None
        else (asls_area - linear_area) / linear_area * 100.0
    )
    return AreaMetrics(
        linear_raw_pct=linear_raw_pct,
        asls_raw_pct=asls_raw_pct,
        asls_vs_linear_pct=asls_vs_linear_pct,
        linear_baseline_subtracted_pct=(
            None if linear_raw_pct is None else 100.0 - linear_raw_pct
        ),
        asls_baseline_subtracted_pct=(
            None if asls_raw_pct is None else 100.0 - asls_raw_pct
        ),
    )


def classify_baseline_truth_row(
    metrics: AreaMetrics,
    *,
    trace_point_count: int,
    linear_edge_delta_pct: float | None,
) -> tuple[str, str]:
    reasons: list[str] = []
    if trace_point_count < 3:
        return "not_assessable", "trace_point_count_lt_3"
    if metrics.asls_vs_linear_pct is None:
        return "not_assessable", "area_metric_unavailable"
    if abs(metrics.asls_vs_linear_pct) <= 5.0:
        return "methods_similar", "asls_vs_linear_within_5pct"
    if metrics.asls_raw_pct is not None and metrics.asls_raw_pct >= 98.0:
        reasons.append("asls_near_raw")
    if (
        metrics.linear_baseline_subtracted_pct is not None
        and metrics.linear_baseline_subtracted_pct >= 10.0
    ):
        reasons.append("linear_subtracts_gt_10pct")
    if linear_edge_delta_pct is not None and abs(linear_edge_delta_pct) >= 10.0:
        reasons.append("linear_edge_elevated")
    elif linear_edge_delta_pct is not None:
        reasons.append("linear_edge_not_elevated")
    if {"asls_near_raw", "linear_subtracts_gt_10pct", "linear_edge_elevated"} <= set(
        reasons
    ):
        return "linear_edge_over_subtraction_plausible", ";".join(reasons)
    if "asls_near_raw" in reasons and "linear_edge_not_elevated" in reasons:
        return "asls_under_subtraction_plausible", ";".join(reasons)
    return "mixed_or_review_required", ";".join(reasons)


def _ratio_pct(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator is None or denominator <= 0:
        return None
    value = numerator / denominator * 100.0
    return value if math.isfinite(value) else None
```

- [x] **Step 4: Verify Task 1**

Run:

```powershell
$env:PYTHONPATH = (Get-Location).Path
C:\Users\user\Desktop\XIC_Extractor\.venv\Scripts\python.exe -m pytest tests\test_p2_baseline_truth_audit.py -q
```

Expected: Task 1 tests pass.

## Task 2: Trace Re-Extraction And Row Builder

**Files:**

- Modify: `tests/test_p2_baseline_truth_audit.py`
- Modify: `tools/diagnostics/p2_baseline_truth_audit.py`

- [x] **Step 1: Add failing tests for row construction from trace arrays**

Append to `tests/test_p2_baseline_truth_audit.py`:

```python
import numpy as np

from tools.diagnostics.p2_baseline_truth_audit import (
    build_baseline_truth_row,
)


def test_build_baseline_truth_row_recomputes_trace_baselines() -> None:
    rt = np.asarray([9.8, 9.9, 10.0, 10.1, 10.2, 10.3, 10.4])
    intensity = np.asarray([10.0, 20.0, 120.0, 200.0, 130.0, 25.0, 10.0])

    row = build_baseline_truth_row(
        target_label="ISTD-A",
        feature_family_id="FAM001",
        sample_stem="S1",
        status="detected",
        raw_area=1000.0,
        linear_area=800.0,
        asls_area=980.0,
        mz=245.0,
        peak_start_rt=10.0,
        apex_rt=10.1,
        peak_end_rt=10.3,
        rt=rt,
        intensity=intensity,
        plot_path="plots/istd.png",
    )

    assert row.target_label == "ISTD-A"
    assert row.feature_family_id == "FAM001"
    assert row.sample_stem == "S1"
    assert row.trace_point_count >= 3
    assert row.linear_raw_pct == pytest.approx(80.0)
    assert row.asls_raw_pct == pytest.approx(98.0)
    assert row.plot_path == "plots/istd.png"
```

- [x] **Step 2: Run tests and confirm failure**

Run:

```powershell
$env:PYTHONPATH = (Get-Location).Path
C:\Users\user\Desktop\XIC_Extractor\.venv\Scripts\python.exe -m pytest tests\test_p2_baseline_truth_audit.py -q
```

Expected: failure because `build_baseline_truth_row` is missing.

- [x] **Step 3: Implement row dataclass and trace row builder**

Add to `tools/diagnostics/p2_baseline_truth_audit.py`:

```python
from dataclasses import asdict
from typing import Any

import numpy as np

from xic_extractor.peak_detection.baseline import (
    bounded_trace_interval,
    integrate_asls_baseline,
    integrate_linear_edge_baseline,
)


@dataclass(frozen=True)
class BaselineTruthRow:
    target_label: str
    feature_family_id: str
    sample_stem: str
    status: str
    raw_area: float | None
    linear_area: float | None
    asls_area: float | None
    linear_raw_pct: float | None
    asls_raw_pct: float | None
    asls_vs_linear_pct: float | None
    linear_baseline_subtracted_pct: float | None
    asls_baseline_subtracted_pct: float | None
    linear_edge_delta_pct: float | None
    peak_start_rt: float | None
    apex_rt: float | None
    peak_end_rt: float | None
    trace_point_count: int
    classification: str
    review_reason: str
    plot_path: str


def build_baseline_truth_row(
    *,
    target_label: str,
    feature_family_id: str,
    sample_stem: str,
    status: str,
    raw_area: float | None,
    linear_area: float | None,
    asls_area: float | None,
    mz: float,
    peak_start_rt: float | None,
    apex_rt: float | None,
    peak_end_rt: float | None,
    rt: object,
    intensity: object,
    plot_path: str,
) -> BaselineTruthRow:
    rt_array = np.asarray(rt, dtype=float)
    intensity_array = np.asarray(intensity, dtype=float)
    left, right = _rt_window_indices(rt_array, peak_start_rt, peak_end_rt)
    linear_delta = _linear_edge_delta_pct(intensity_array, left, right)
    metrics = compute_area_metrics(
        raw_area=raw_area,
        linear_area=linear_area,
        asls_area=asls_area,
    )
    classification, reason = classify_baseline_truth_row(
        metrics,
        trace_point_count=len(rt_array[left:right]),
        linear_edge_delta_pct=linear_delta,
    )
    return BaselineTruthRow(
        target_label=target_label,
        feature_family_id=feature_family_id,
        sample_stem=sample_stem,
        status=status,
        raw_area=raw_area,
        linear_area=linear_area,
        asls_area=asls_area,
        linear_raw_pct=metrics.linear_raw_pct,
        asls_raw_pct=metrics.asls_raw_pct,
        asls_vs_linear_pct=metrics.asls_vs_linear_pct,
        linear_baseline_subtracted_pct=metrics.linear_baseline_subtracted_pct,
        asls_baseline_subtracted_pct=metrics.asls_baseline_subtracted_pct,
        linear_edge_delta_pct=linear_delta,
        peak_start_rt=peak_start_rt,
        apex_rt=apex_rt,
        peak_end_rt=peak_end_rt,
        trace_point_count=len(rt_array[left:right]),
        classification=classification,
        review_reason=reason,
        plot_path=plot_path,
    )


def _rt_window_indices(
    rt: np.ndarray,
    peak_start_rt: float | None,
    peak_end_rt: float | None,
) -> tuple[int, int]:
    if rt.ndim != 1 or len(rt) < 2:
        raise ValueError("rt must be a one-dimensional array with at least 2 points")
    if peak_start_rt is None or peak_end_rt is None:
        return 0, len(rt)
    left = int(np.searchsorted(rt, peak_start_rt, side="left"))
    right = int(np.searchsorted(rt, peak_end_rt, side="right"))
    return bounded_trace_interval(left, right, len(rt))


def _linear_edge_delta_pct(
    intensity: np.ndarray,
    left: int,
    right: int,
) -> float | None:
    if right - left < 2:
        return None
    segment = intensity[left:right]
    edge_mean = (float(segment[0]) + float(segment[-1])) / 2.0
    apex = float(np.max(segment))
    if apex <= 0:
        return None
    return edge_mean / apex * 100.0
```

- [x] **Step 4: Verify Task 2**

Run:

```powershell
$env:PYTHONPATH = (Get-Location).Path
C:\Users\user\Desktop\XIC_Extractor\.venv\Scripts\python.exe -m pytest tests\test_p2_baseline_truth_audit.py -q
```

Expected: Task 1 and Task 2 tests pass.

## Task 3: CLI, Writers, And PNG Overlays

**Files:**

- Modify: `tests/test_p2_baseline_truth_audit.py`
- Modify: `tools/diagnostics/p2_baseline_truth_audit.py`

- [x] **Step 1: Add failing test for audit outputs with injected traces**

Append to `tests/test_p2_baseline_truth_audit.py`:

```python
import csv
from pathlib import Path

from tools.diagnostics.p2_baseline_truth_audit import run_p2_baseline_truth_audit


def _write_tsv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def test_run_p2_baseline_truth_audit_writes_review_outputs(tmp_path: Path) -> None:
    gate_rows = tmp_path / "p2_gate_rows.tsv"
    audit = tmp_path / "alignment_cell_integration_audit.tsv"
    _write_tsv(
        gate_rows,
        [
            {
                "target_label": "ISTD-A",
                "selected_feature_id": "FAM001",
                "status": "FAIL",
                "failure_reasons": "area_rsd_regression",
            }
        ],
    )
    _write_tsv(
        audit,
        [
            {
                "feature_family_id": "FAM001",
                "sample_stem": "S1",
                "status": "detected",
                "area": "1000",
                "area_baseline_corrected": "800",
                "area_baseline_corrected_asls": "980",
                "family_center_mz": "245",
                "peak_start_rt": "10.0",
                "apex_rt": "10.1",
                "peak_end_rt": "10.3",
            }
        ],
    )

    def fake_trace_loader(sample_stem, mz, rt_min, rt_max, ppm):
        return (
            np.asarray([9.8, 9.9, 10.0, 10.1, 10.2, 10.3, 10.4]),
            np.asarray([10.0, 20.0, 120.0, 200.0, 130.0, 25.0, 10.0]),
        )

    outputs, result = run_p2_baseline_truth_audit(
        p2_gate_rows_tsv=gate_rows,
        alignment_integration_audit_tsv=audit,
        output_dir=tmp_path / "truth",
        trace_loader=fake_trace_loader,
    )

    assert result.row_count == 1
    assert outputs.rows_tsv.exists()
    assert outputs.summary_tsv.exists()
    assert outputs.markdown_path.exists()
    assert outputs.json_path.exists()
    assert outputs.plot_dir.exists()
```

- [x] **Step 2: Run tests and confirm failure**

Run:

```powershell
$env:PYTHONPATH = (Get-Location).Path
C:\Users\user\Desktop\XIC_Extractor\.venv\Scripts\python.exe -m pytest tests\test_p2_baseline_truth_audit.py -q
```

Expected: failure because `run_p2_baseline_truth_audit` is missing.

- [x] **Step 3: Implement CLI runner and writers**

Implement in `tools/diagnostics/p2_baseline_truth_audit.py`:

- `BaselineTruthOutputs`
- `BaselineTruthResult`
- `run_p2_baseline_truth_audit(...)`
- `main(argv=None)`
- `_read_failed_gate_targets(...)`
- `_read_alignment_audit_rows(...)`
- `_default_trace_loader(raw_dir, dll_dir)`
- `_write_rows_tsv(...)`
- `_write_summary_tsv(...)`
- `_write_json(...)`
- `_write_markdown(...)`
- `_write_family_plot(...)`

CLI arguments:

```text
--p2-gate-rows-tsv
--alignment-integration-audit-tsv
--raw-dir
--dll-dir
--output-dir
--ppm default 10
--rt-margin-min default 0.4
```

Runner behavior:

- Select only gate rows where `status == "FAIL"` by default.
- Join gate rows to integration audit rows by `selected_feature_id == feature_family_id`.
- For each row, extract a trace over `[peak_start_rt - margin, peak_end_rt + margin]`.
- Compute metrics from existing audit areas.
- Recompute baseline curves only for plotting; do not overwrite audit areas.
- Write one family PNG containing one subplot per sample.
- Return exit code `0` if outputs were written, `2` for missing columns or missing RAW input.

- [x] **Step 4: Verify Task 3**

Run:

```powershell
$env:PYTHONPATH = (Get-Location).Path
C:\Users\user\Desktop\XIC_Extractor\.venv\Scripts\python.exe -m pytest tests\test_p2_baseline_truth_audit.py -q
```

Expected: all baseline truth audit unit tests pass.

## Task 4: Real 8RAW Baseline Truth Audit

**Files:**

- Create: `docs/superpowers/notes/2026-05-25-p2-baseline-truth-audit-note.md`
- Write outputs under: `output/phase1_p2_baseline_truth_audit/`

- [x] **Step 1: Run the real audit**

Run:

```powershell
$env:PYTHONPATH = (Get-Location).Path
C:\Users\user\Desktop\XIC_Extractor\.venv\Scripts\python.exe -m tools.diagnostics.p2_baseline_truth_audit `
  --p2-gate-rows-tsv output\phase1_p2_asls_shadow_validation\diagnostics\p2_asls_shadow_gate\p2_asls_shadow_gate_rows.tsv `
  --alignment-integration-audit-tsv output\phase1_p2_asls_shadow_validation\alignment\asls_shadow\alignment_cell_integration_audit.tsv `
  --raw-dir "C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation" `
  --dll-dir "C:\Xcalibur\system\programs" `
  --output-dir output\phase1_p2_baseline_truth_audit
```

Expected:

- exit code `0`
- `baseline_truth_audit_rows.tsv` exists
- `baseline_truth_audit_summary.tsv` exists
- `baseline_truth_audit.md` exists
- 3 PNG plots exist, one per failed ISTD family

- [x] **Step 2: Inspect summary**

Run:

```powershell
Get-Content output\phase1_p2_baseline_truth_audit\baseline_truth_audit_summary.tsv
```

Record:

- classification counts
- median `linear_baseline_subtracted_pct`
- median `asls_baseline_subtracted_pct`
- target/family rows needing manual EIC review

- [x] **Step 3: Write audit note**

Create `docs/superpowers/notes/2026-05-25-p2-baseline-truth-audit-note.md` with:

```markdown
# P2 Baseline Truth Audit Note

**Date:** 2026-05-25
**Branch:** codex/peak-pipeline-modernization
**Worktree:** .worktrees/peak-pipeline-modernization
**Gate status:** diagnostic_only

## Decision

- Baseline truth audit status: diagnostic evidence generated from 8RAW P2 AsLS shadow artifacts.
- P2 AsLS remains shadow-only.
- This audit does not promote AsLS and does not change production `area_baseline_corrected`.

## Artifacts

- Rows: `output/phase1_p2_baseline_truth_audit/baseline_truth_audit_rows.tsv`
- Summary: `output/phase1_p2_baseline_truth_audit/baseline_truth_audit_summary.tsv`
- Report: `output/phase1_p2_baseline_truth_audit/baseline_truth_audit.md`
- Plots: `output/phase1_p2_baseline_truth_audit/plots/`

## Findings

| Target | Family | Dominant classification | Median linear subtraction % | Median AsLS subtraction % | Review interpretation |
|---|---|---|---:|---:|---|
| d3-5-hmdC | FAM000153 | fill from `baseline_truth_audit_summary.tsv` | fill from `baseline_truth_audit_summary.tsv` | fill from `baseline_truth_audit_summary.tsv` | fill after inspecting plot |
| d4-N6-2HE-dA | FAM000807 | fill from `baseline_truth_audit_summary.tsv` | fill from `baseline_truth_audit_summary.tsv` | fill from `baseline_truth_audit_summary.tsv` | fill after inspecting plot |
| d3-dG-C8-MeIQx | FAM001878 | fill from `baseline_truth_audit_summary.tsv` | fill from `baseline_truth_audit_summary.tsv` | fill from `baseline_truth_audit_summary.tsv` | fill after inspecting plot |

## Next Recommendation

Choose exactly one recommendation after reading the rows and plots:

- `revise_p2_gate_semantics`: use when plots support linear-edge over-subtraction and AsLS remains plausible shadow evidence.
- `retune_asls_parameters`: use when AsLS baseline is directionally plausible but too close to raw area.
- `compare_alternate_baseline`: use when neither linear-edge nor current AsLS is credible across the failed ISTDs.
- `keep_linear_edge_for_production`: use when plots show AsLS under-subtraction or unstable behavior.
```

Do not save the note until every `fill from ...` and `fill after ...` cell is
replaced with observed values from the current audit outputs.

## Task 5: Final Verification

**Files:**

- No new files unless verification uncovers a defect.

- [x] **Step 1: Run focused tests**

Run:

```powershell
$env:PYTHONPATH = (Get-Location).Path
C:\Users\user\Desktop\XIC_Extractor\.venv\Scripts\python.exe -m pytest tests\test_p2_baseline_truth_audit.py tests\test_p2_asls_shadow_gate.py tests\test_baseline_integration.py -q
```

Expected: all tests pass.

- [x] **Step 2: Run compile smoke**

Run:

```powershell
C:\Users\user\Desktop\XIC_Extractor\.venv\Scripts\python.exe -m py_compile tools\diagnostics\p2_baseline_truth_audit.py tools\diagnostics\p2_asls_shadow_gate.py xic_extractor\peak_detection\baseline.py
```

Expected: exit code `0`.

- [x] **Step 3: Run diff hygiene**

Run:

```powershell
git diff --check
```

Expected: exit code `0`; LF-to-CRLF warnings are acceptable on this Windows worktree.

## Stop Conditions

Stop and ask before continuing if:

- generating this audit requires changing production `area_baseline_corrected`
- RAW trace extraction cannot reproduce the audit rows
- plots show the AsLS baseline is visibly impossible for most samples
- the new diagnostic needs a breaking change to existing alignment TSV schemas
- any implementation step touches Cleanup C-spec scope
