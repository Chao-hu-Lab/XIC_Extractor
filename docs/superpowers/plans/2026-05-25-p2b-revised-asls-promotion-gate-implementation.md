# P2b Revised AsLS Promotion Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the old P2b "AsLS RSD must match linear-edge" blocker with a revised promotion gate that treats linear-edge RSD as evidence, not truth, when baseline truth audit supports old-method over-subtraction.

**Architecture:** Keep production area integration unchanged in this plan. Add a focused diagnostic gate that consumes the existing P2 AsLS shadow rows, P2 baseline truth summary, and P4 area-uncertainty summary, then emits a machine-readable GO/NO-GO decision for the revised P2b promotion path. Update the P2b spec and notes to distinguish old-gate NO-GO from revised-gate GO.

**Tech Stack:** Python stdlib CSV/JSON/dataclasses, existing `tools/diagnostics/` style, pytest, PowerShell validation commands.

---

## Plan Review Log

- Initial plan status: drafted after reviewing `2026-05-24-peak-pipeline-area-baseline-asls-promotion-spec.md`, `p2_asls_shadow_gate.py`, `p2_baseline_truth_audit.py`, current P2/P4 notes, and real 8RAW artifacts.
- Plan review patch 1: keep this plan to revised gate + decision note only. Do not switch production `area_baseline_corrected` to AsLS in this same step.
- Plan review patch 2: revised gate status is `GO_FOR_PRODUCTION_CANDIDATE`, not `production_ready`, because 85RAW is still not rerun in this worktree.
- Plan review patch 3: expanded Task 2 writer/helper instructions into concrete code so implementation does not rely on a vague "use existing style" placeholder.

## Scope Lock

- In scope: revised P2b gate semantics, diagnostic CLI, tests, spec update, decision note, overview/closeout wording.
- Not in scope: direct production switch to AsLS, 85RAW rerun, Cleanup C-spec implementation, new baseline algorithm tuning, or removing linear-edge production code.
- Gate language: this implementation can make P2b `GO_FOR_PRODUCTION_CANDIDATE` on 8RAW evidence. It cannot claim `production_ready` without a later 85RAW run or explicit owner acceptance.

## Files

- Create: `tools/diagnostics/p2b_asls_promotion_gate.py`
  - Reads P2 shadow gate rows, baseline truth summary rows, and P4 area-uncertainty summary.
  - Emits `p2b_asls_promotion_gate_rows.tsv`, `p2b_asls_promotion_gate_summary.tsv`, `p2b_asls_promotion_gate.json`, and `p2b_asls_promotion_gate.md`.
  - Exits `0` when revised gate status is `GO_FOR_PRODUCTION_CANDIDATE`; exits `1` on `NO_GO`; exits `2` on invalid input.
- Create: `tests/test_p2b_asls_promotion_gate.py`
  - Covers revised semantics and CLI exit codes.
- Modify: `docs/superpowers/specs/2026-05-24-peak-pipeline-area-baseline-asls-promotion-spec.md`
  - Reframe the old RSD comparator as superseded by the revised gate.
- Create: `docs/superpowers/notes/2026-05-25-p2b-revised-asls-promotion-gate-note.md`
  - Record real 8RAW revised-gate command/result and remaining production-readiness limits.
- Modify: `docs/superpowers/specs/2026-05-24-peak-pipeline-modernization-overview-spec.md`
  - Replace the blanket P2b NO-GO wording with "old gate NO-GO; revised 8RAW candidate gate GO" if the real run passes.
- Modify: `docs/superpowers/notes/2026-05-25-phase1-modernization-closeout-note.md`
  - Same wording update as the overview.

## Revised Gate Semantics

Hard blockers:

- Missing or unreadable input.
- P2 row has `sample_count_lt_2`, `shadow_coverage_incomplete`, or `area_rsd_unavailable`.
- P2 row has `asls_area_exceeds_raw_area` or `asls_exceeds_raw_area_count > 0`.
- P2 row has non-RSD failure reasons that the revised gate does not understand.
- A row with `area_rsd_regression` lacks a matching baseline truth summary row.
- A row with `area_rsd_regression` has baseline truth `review_status` other than `linear_edge_over_subtraction_plausible`.
- P4 area uncertainty summary has `unexplained_area_mismatch_count > 0` or `integration_context_incomplete_count > 0`.

Accepted review evidence:

- A P2 row with only `area_rsd_regression` is accepted when baseline truth summary says `review_status == linear_edge_over_subtraction_plausible`.
- P2 rows that already passed the old shadow gate remain passed.

Overall status:

- `GO_FOR_PRODUCTION_CANDIDATE` when every row is either pass or accepted review evidence and P4 area uncertainty has no hard blockers.
- `NO_GO` when any hard blocker exists.

## Task 1: Revised Gate Tests

**Files:**

- Create: `tests/test_p2b_asls_promotion_gate.py`

- [x] **Step 1: Add test fixtures and the accepted-RSD test**

Add:

```python
from __future__ import annotations

import csv
from pathlib import Path

from tools.diagnostics.p2b_asls_promotion_gate import (
    main as p2b_asls_promotion_gate_main,
)
from tools.diagnostics.p2b_asls_promotion_gate import run_p2b_asls_promotion_gate


def _write_tsv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def _write_clean_area_uncertainty(path: Path) -> None:
    _write_tsv(
        path,
        [
            {
                "rows_checked": "72",
                "bucket_counts": "area_consistent_low_uncertainty:36",
                "missing_alignment_match_count": "16",
                "integration_context_incomplete_count": "0",
                "unexplained_area_mismatch_count": "0",
            }
        ],
    )
```

Then add:

```python
def test_revised_gate_accepts_rsd_regression_when_truth_supports_old_bias(
    tmp_path: Path,
) -> None:
    p2_rows = tmp_path / "p2_rows.tsv"
    truth = tmp_path / "truth.tsv"
    uncertainty = tmp_path / "uncertainty.tsv"
    _write_tsv(
        p2_rows,
        [
            {
                "target_label": "d3-5-hmdC",
                "selected_feature_id": "FAM000153",
                "sample_count": "8",
                "linear_area_rsd_pct": "11.2581",
                "asls_area_rsd_pct": "15.1169",
                "area_rsd_delta_pct": "3.85879",
                "median_abs_relative_diff_pct": "9.4024",
                "diff_gt_5pct_count": "6",
                "asls_reduced_area_count": "2",
                "asls_exceeds_raw_area_count": "0",
                "status": "FAIL",
                "failure_reasons": "area_rsd_regression",
            }
        ],
    )
    _write_tsv(
        truth,
        [
            {
                "target_label": "d3-5-hmdC",
                "feature_family_id": "FAM000153",
                "row_count": "8",
                "dominant_classification": "linear_edge_over_subtraction_plausible",
                "classification_counts": "linear_edge_over_subtraction_plausible:6;methods_similar:2",
                "median_linear_baseline_subtracted_pct": "8.85423",
                "median_asls_baseline_subtracted_pct": "0.264858",
                "median_asls_vs_linear_pct": "9.4024",
                "max_asls_vs_linear_pct": "26.4931",
                "median_linear_edge_delta_pct": "6.01194",
                "median_outside_background_pct": "0",
                "review_status": "linear_edge_over_subtraction_plausible",
                "plot_path": "plots/d3-5-hmdC__FAM000153.png",
            }
        ],
    )
    _write_clean_area_uncertainty(uncertainty)

    outputs, result = run_p2b_asls_promotion_gate(
        p2_gate_rows_tsv=p2_rows,
        baseline_truth_summary_tsv=truth,
        area_uncertainty_summary_tsv=uncertainty,
        output_dir=tmp_path / "gate",
    )

    assert result.overall_status == "GO_FOR_PRODUCTION_CANDIDATE"
    assert result.hard_blocker_count == 0
    assert result.review_accepted_count == 1
    assert result.rows[0].revised_status == "ACCEPTED_REVIEW"
    assert "baseline_truth_supports_linear_edge_over_subtraction" in result.rows[0].accepted_reasons
    assert outputs.summary_tsv.exists()
```

- [x] **Step 2: Run the new accepted-RSD test and confirm it fails**

Run:

```powershell
$env:PYTHONPATH = (Get-Location).Path
C:\Users\user\Desktop\XIC_Extractor\.venv\Scripts\python.exe -m pytest tests\test_p2b_asls_promotion_gate.py::test_revised_gate_accepts_rsd_regression_when_truth_supports_old_bias -q
```

Expected before implementation: import failure for `tools.diagnostics.p2b_asls_promotion_gate`.

- [x] **Step 3: Add raw-area, missing-truth, area-uncertainty, and CLI tests**

Add tests:

```python
def test_revised_gate_keeps_raw_area_violation_as_hard_blocker(tmp_path: Path) -> None:
    p2_rows = tmp_path / "p2_rows.tsv"
    truth = tmp_path / "truth.tsv"
    uncertainty = tmp_path / "uncertainty.tsv"
    _write_tsv(
        p2_rows,
        [
            {
                "target_label": "ISTD-A",
                "selected_feature_id": "FAM001",
                "sample_count": "8",
                "linear_area_rsd_pct": "10",
                "asls_area_rsd_pct": "11",
                "area_rsd_delta_pct": "1",
                "median_abs_relative_diff_pct": "10",
                "diff_gt_5pct_count": "8",
                "asls_reduced_area_count": "0",
                "asls_exceeds_raw_area_count": "1",
                "status": "FAIL",
                "failure_reasons": "area_rsd_regression;asls_area_exceeds_raw_area",
            }
        ],
    )
    _write_tsv(
        truth,
        [
            {
                "target_label": "ISTD-A",
                "feature_family_id": "FAM001",
                "row_count": "8",
                "dominant_classification": "linear_edge_over_subtraction_plausible",
                "classification_counts": "linear_edge_over_subtraction_plausible:8",
                "median_linear_baseline_subtracted_pct": "8",
                "median_asls_baseline_subtracted_pct": "0.2",
                "median_asls_vs_linear_pct": "10",
                "max_asls_vs_linear_pct": "12",
                "median_linear_edge_delta_pct": "8",
                "median_outside_background_pct": "0",
                "review_status": "linear_edge_over_subtraction_plausible",
                "plot_path": "plots/ISTD-A__FAM001.png",
            }
        ],
    )
    _write_clean_area_uncertainty(uncertainty)

    _outputs, result = run_p2b_asls_promotion_gate(
        p2_gate_rows_tsv=p2_rows,
        baseline_truth_summary_tsv=truth,
        area_uncertainty_summary_tsv=uncertainty,
        output_dir=tmp_path / "gate",
    )

    assert result.overall_status == "NO_GO"
    assert result.hard_blocker_count == 1
    assert "asls_area_exceeds_raw_area" in result.rows[0].hard_blockers


def test_revised_gate_blocks_rsd_regression_without_truth_support(tmp_path: Path) -> None:
    p2_rows = tmp_path / "p2_rows.tsv"
    truth = tmp_path / "truth.tsv"
    uncertainty = tmp_path / "uncertainty.tsv"
    _write_tsv(
        p2_rows,
        [
            {
                "target_label": "ISTD-A",
                "selected_feature_id": "FAM001",
                "sample_count": "8",
                "linear_area_rsd_pct": "10",
                "asls_area_rsd_pct": "11",
                "area_rsd_delta_pct": "1",
                "median_abs_relative_diff_pct": "10",
                "diff_gt_5pct_count": "8",
                "asls_reduced_area_count": "0",
                "asls_exceeds_raw_area_count": "0",
                "status": "FAIL",
                "failure_reasons": "area_rsd_regression",
            }
        ],
    )
    _write_tsv(
        truth,
        [
            {
                "target_label": "ISTD-A",
                "feature_family_id": "FAM001",
                "row_count": "8",
                "dominant_classification": "mixed_or_review_required",
                "classification_counts": "mixed_or_review_required:8",
                "median_linear_baseline_subtracted_pct": "8",
                "median_asls_baseline_subtracted_pct": "0.2",
                "median_asls_vs_linear_pct": "10",
                "max_asls_vs_linear_pct": "12",
                "median_linear_edge_delta_pct": "8",
                "median_outside_background_pct": "12",
                "review_status": "manual_review_required",
                "plot_path": "plots/ISTD-A__FAM001.png",
            }
        ],
    )
    _write_clean_area_uncertainty(uncertainty)

    _outputs, result = run_p2b_asls_promotion_gate(
        p2_gate_rows_tsv=p2_rows,
        baseline_truth_summary_tsv=truth,
        area_uncertainty_summary_tsv=uncertainty,
        output_dir=tmp_path / "gate",
    )

    assert result.overall_status == "NO_GO"
    assert "baseline_truth_not_supportive" in result.rows[0].hard_blockers


def test_revised_gate_blocks_unclean_area_uncertainty_summary(tmp_path: Path) -> None:
    p2_rows = tmp_path / "p2_rows.tsv"
    truth = tmp_path / "truth.tsv"
    uncertainty = tmp_path / "uncertainty.tsv"
    _write_tsv(
        p2_rows,
        [
            {
                "target_label": "ISTD-A",
                "selected_feature_id": "FAM001",
                "sample_count": "8",
                "linear_area_rsd_pct": "10",
                "asls_area_rsd_pct": "9",
                "area_rsd_delta_pct": "-1",
                "median_abs_relative_diff_pct": "3",
                "diff_gt_5pct_count": "0",
                "asls_reduced_area_count": "0",
                "asls_exceeds_raw_area_count": "0",
                "status": "PASS",
                "failure_reasons": "",
            }
        ],
    )
    _write_tsv(
        truth,
        [
            {
                "target_label": "ISTD-A",
                "feature_family_id": "FAM001",
                "row_count": "8",
                "dominant_classification": "methods_similar",
                "classification_counts": "methods_similar:8",
                "median_linear_baseline_subtracted_pct": "5",
                "median_asls_baseline_subtracted_pct": "4",
                "median_asls_vs_linear_pct": "1",
                "max_asls_vs_linear_pct": "2",
                "median_linear_edge_delta_pct": "1",
                "median_outside_background_pct": "0",
                "review_status": "methods_similar",
                "plot_path": "plots/ISTD-A__FAM001.png",
            }
        ],
    )
    _write_tsv(
        uncertainty,
        [
            {
                "rows_checked": "72",
                "bucket_counts": "unexplained_area_mismatch:1",
                "missing_alignment_match_count": "0",
                "integration_context_incomplete_count": "0",
                "unexplained_area_mismatch_count": "1",
            }
        ],
    )

    _outputs, result = run_p2b_asls_promotion_gate(
        p2_gate_rows_tsv=p2_rows,
        baseline_truth_summary_tsv=truth,
        area_uncertainty_summary_tsv=uncertainty,
        output_dir=tmp_path / "gate",
    )

    assert result.overall_status == "NO_GO"
    assert "area_uncertainty_unexplained_mismatch" in result.global_blockers


def test_revised_gate_cli_exit_codes(tmp_path: Path) -> None:
    p2_rows = tmp_path / "p2_rows.tsv"
    truth = tmp_path / "truth.tsv"
    uncertainty = tmp_path / "uncertainty.tsv"
    _write_tsv(
        p2_rows,
        [
            {
                "target_label": "ISTD-A",
                "selected_feature_id": "FAM001",
                "sample_count": "8",
                "linear_area_rsd_pct": "10",
                "asls_area_rsd_pct": "9",
                "area_rsd_delta_pct": "-1",
                "median_abs_relative_diff_pct": "3",
                "diff_gt_5pct_count": "0",
                "asls_reduced_area_count": "0",
                "asls_exceeds_raw_area_count": "0",
                "status": "PASS",
                "failure_reasons": "",
            }
        ],
    )
    _write_tsv(
        truth,
        [
            {
                "target_label": "ISTD-A",
                "feature_family_id": "FAM001",
                "row_count": "8",
                "dominant_classification": "methods_similar",
                "classification_counts": "methods_similar:8",
                "median_linear_baseline_subtracted_pct": "5",
                "median_asls_baseline_subtracted_pct": "4",
                "median_asls_vs_linear_pct": "1",
                "max_asls_vs_linear_pct": "2",
                "median_linear_edge_delta_pct": "1",
                "median_outside_background_pct": "0",
                "review_status": "methods_similar",
                "plot_path": "plots/ISTD-A__FAM001.png",
            }
        ],
    )
    _write_clean_area_uncertainty(uncertainty)

    pass_code = p2b_asls_promotion_gate_main(
        [
            "--p2-gate-rows-tsv",
            str(p2_rows),
            "--baseline-truth-summary-tsv",
            str(truth),
            "--area-uncertainty-summary-tsv",
            str(uncertainty),
            "--output-dir",
            str(tmp_path / "pass_gate"),
        ]
    )
    invalid_code = p2b_asls_promotion_gate_main(
        [
            "--p2-gate-rows-tsv",
            str(tmp_path / "missing.tsv"),
            "--baseline-truth-summary-tsv",
            str(truth),
            "--area-uncertainty-summary-tsv",
            str(uncertainty),
            "--output-dir",
            str(tmp_path / "invalid_gate"),
        ]
    )

    assert pass_code == 0
    assert invalid_code == 2
```

## Task 2: Revised Gate Implementation

**Files:**

- Create: `tools/diagnostics/p2b_asls_promotion_gate.py`

- [x] **Step 1: Implement dataclasses and TSV readers**

Create the module with:

```python
"""P2b revised AsLS promotion gate."""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

ROW_FIELDS = (
    "target_label",
    "selected_feature_id",
    "old_status",
    "old_failure_reasons",
    "linear_area_rsd_pct",
    "asls_area_rsd_pct",
    "area_rsd_delta_pct",
    "asls_exceeds_raw_area_count",
    "baseline_truth_review_status",
    "baseline_truth_dominant_classification",
    "revised_status",
    "hard_blockers",
    "accepted_reasons",
)

SUMMARY_FIELDS = (
    "overall_status",
    "target_count",
    "hard_blocker_count",
    "review_accepted_count",
    "global_blockers",
    "area_uncertainty_unexplained_area_mismatch_count",
    "area_uncertainty_integration_context_incomplete_count",
)

_P2_REQUIRED_COLUMNS = {
    "target_label",
    "selected_feature_id",
    "status",
    "failure_reasons",
    "linear_area_rsd_pct",
    "asls_area_rsd_pct",
    "area_rsd_delta_pct",
    "asls_exceeds_raw_area_count",
}
_TRUTH_REQUIRED_COLUMNS = {
    "feature_family_id",
    "review_status",
    "dominant_classification",
}
_UNCERTAINTY_REQUIRED_COLUMNS = {
    "unexplained_area_mismatch_count",
    "integration_context_incomplete_count",
}
_HARD_FAILURE_REASONS = {
    "sample_count_lt_2",
    "shadow_coverage_incomplete",
    "area_rsd_unavailable",
    "asls_area_exceeds_raw_area",
}


@dataclass(frozen=True)
class P2bAslsPromotionGateOutputs:
    rows_tsv: Path
    summary_tsv: Path
    json_path: Path
    markdown_path: Path


@dataclass(frozen=True)
class P2bAslsPromotionGateRow:
    target_label: str
    selected_feature_id: str
    old_status: str
    old_failure_reasons: tuple[str, ...]
    linear_area_rsd_pct: float | None
    asls_area_rsd_pct: float | None
    area_rsd_delta_pct: float | None
    asls_exceeds_raw_area_count: int
    baseline_truth_review_status: str
    baseline_truth_dominant_classification: str
    revised_status: str
    hard_blockers: tuple[str, ...]
    accepted_reasons: tuple[str, ...]


@dataclass(frozen=True)
class P2bAslsPromotionGateResult:
    overall_status: str
    target_count: int
    hard_blocker_count: int
    review_accepted_count: int
    global_blockers: tuple[str, ...]
    area_uncertainty_unexplained_area_mismatch_count: int
    area_uncertainty_integration_context_incomplete_count: int
    rows: tuple[P2bAslsPromotionGateRow, ...]
```

- [x] **Step 2: Implement gate evaluation**

Add:

```python
def run_p2b_asls_promotion_gate(
    *,
    p2_gate_rows_tsv: Path,
    baseline_truth_summary_tsv: Path,
    area_uncertainty_summary_tsv: Path,
    output_dir: Path,
) -> tuple[P2bAslsPromotionGateOutputs, P2bAslsPromotionGateResult]:
    p2_rows = _read_tsv(p2_gate_rows_tsv, _P2_REQUIRED_COLUMNS)
    truth_rows = _read_tsv(baseline_truth_summary_tsv, _TRUTH_REQUIRED_COLUMNS)
    uncertainty_row = _single_row(
        _read_tsv(area_uncertainty_summary_tsv, _UNCERTAINTY_REQUIRED_COLUMNS),
        area_uncertainty_summary_tsv,
    )
    truth_by_family = {
        row["feature_family_id"].strip(): row
        for row in truth_rows
        if row.get("feature_family_id", "").strip()
    }
    rows = tuple(_build_row(row, truth_by_family=truth_by_family) for row in p2_rows)
    unexplained = _parse_non_negative_int(
        uncertainty_row.get("unexplained_area_mismatch_count", ""),
        "unexplained_area_mismatch_count",
    )
    incomplete = _parse_non_negative_int(
        uncertainty_row.get("integration_context_incomplete_count", ""),
        "integration_context_incomplete_count",
    )
    global_blockers: list[str] = []
    if unexplained > 0:
        global_blockers.append("area_uncertainty_unexplained_mismatch")
    if incomplete > 0:
        global_blockers.append("area_uncertainty_context_incomplete")
    hard_blocker_count = sum(1 for row in rows if row.hard_blockers)
    result = P2bAslsPromotionGateResult(
        overall_status=(
            "NO_GO" if hard_blocker_count or global_blockers else "GO_FOR_PRODUCTION_CANDIDATE"
        ),
        target_count=len(rows),
        hard_blocker_count=hard_blocker_count,
        review_accepted_count=sum(row.revised_status == "ACCEPTED_REVIEW" for row in rows),
        global_blockers=tuple(global_blockers),
        area_uncertainty_unexplained_area_mismatch_count=unexplained,
        area_uncertainty_integration_context_incomplete_count=incomplete,
        rows=rows,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = P2bAslsPromotionGateOutputs(
        rows_tsv=output_dir / "p2b_asls_promotion_gate_rows.tsv",
        summary_tsv=output_dir / "p2b_asls_promotion_gate_summary.tsv",
        json_path=output_dir / "p2b_asls_promotion_gate.json",
        markdown_path=output_dir / "p2b_asls_promotion_gate.md",
    )
    _write_outputs(outputs, result)
    return outputs, result


def _build_row(
    row: Mapping[str, str],
    *,
    truth_by_family: Mapping[str, Mapping[str, str]],
) -> P2bAslsPromotionGateRow:
    family_id = row["selected_feature_id"].strip()
    old_reasons = _split_reasons(row.get("failure_reasons", ""))
    truth = truth_by_family.get(family_id)
    truth_status = "" if truth is None else truth.get("review_status", "").strip()
    truth_classification = (
        "" if truth is None else truth.get("dominant_classification", "").strip()
    )
    hard_blockers: list[str] = []
    accepted_reasons: list[str] = []
    asls_exceeds_raw_count = _parse_non_negative_int(
        row.get("asls_exceeds_raw_area_count", ""),
        "asls_exceeds_raw_area_count",
    )
    hard_blockers.extend(reason for reason in old_reasons if reason in _HARD_FAILURE_REASONS)
    if asls_exceeds_raw_count > 0 and "asls_area_exceeds_raw_area" not in hard_blockers:
        hard_blockers.append("asls_area_exceeds_raw_area")
    unknown_reasons = [
        reason
        for reason in old_reasons
        if reason not in _HARD_FAILURE_REASONS and reason != "area_rsd_regression"
    ]
    hard_blockers.extend(f"unsupported_old_failure_reason:{reason}" for reason in unknown_reasons)
    if "area_rsd_regression" in old_reasons:
        if truth is None:
            hard_blockers.append("baseline_truth_missing")
        elif truth_status == "linear_edge_over_subtraction_plausible":
            accepted_reasons.append("baseline_truth_supports_linear_edge_over_subtraction")
        else:
            hard_blockers.append("baseline_truth_not_supportive")
    if hard_blockers:
        revised_status = "FAIL"
    elif accepted_reasons:
        revised_status = "ACCEPTED_REVIEW"
    else:
        revised_status = "PASS"
    return P2bAslsPromotionGateRow(
        target_label=row["target_label"].strip(),
        selected_feature_id=family_id,
        old_status=row["status"].strip().upper(),
        old_failure_reasons=old_reasons,
        linear_area_rsd_pct=_optional_float(row.get("linear_area_rsd_pct")),
        asls_area_rsd_pct=_optional_float(row.get("asls_area_rsd_pct")),
        area_rsd_delta_pct=_optional_float(row.get("area_rsd_delta_pct")),
        asls_exceeds_raw_area_count=asls_exceeds_raw_count,
        baseline_truth_review_status=truth_status,
        baseline_truth_dominant_classification=truth_classification,
        revised_status=revised_status,
        hard_blockers=tuple(hard_blockers),
        accepted_reasons=tuple(accepted_reasons),
    )
```

- [x] **Step 3: Implement writers and CLI**

Add:

```python
def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the revised P2b AsLS promotion gate.")
    parser.add_argument("--p2-gate-rows-tsv", type=Path, required=True)
    parser.add_argument("--baseline-truth-summary-tsv", type=Path, required=True)
    parser.add_argument("--area-uncertainty-summary-tsv", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        outputs, result = run_p2b_asls_promotion_gate(
            p2_gate_rows_tsv=args.p2_gate_rows_tsv,
            baseline_truth_summary_tsv=args.baseline_truth_summary_tsv,
            area_uncertainty_summary_tsv=args.area_uncertainty_summary_tsv,
            output_dir=args.output_dir,
        )
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(f"Rows TSV: {outputs.rows_tsv}")
    print(f"Summary TSV: {outputs.summary_tsv}")
    print(f"Gate JSON: {outputs.json_path}")
    print(f"Gate report: {outputs.markdown_path}")
    return 0 if result.overall_status == "GO_FOR_PRODUCTION_CANDIDATE" else 1
```

Add the helper functions:

```python
def _write_outputs(
    outputs: P2bAslsPromotionGateOutputs,
    result: P2bAslsPromotionGateResult,
) -> None:
    _write_tsv(outputs.rows_tsv, ROW_FIELDS, (_row_dict(row) for row in result.rows))
    _write_tsv(outputs.summary_tsv, SUMMARY_FIELDS, (_summary_dict(result),))
    outputs.json_path.write_text(
        json.dumps(
            {
                **_summary_dict(result),
                "rows": [_row_dict(row) for row in result.rows],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    _write_markdown(outputs.markdown_path, result)


def _row_dict(row: P2bAslsPromotionGateRow) -> dict[str, object]:
    return {
        **asdict(row),
        "old_failure_reasons": ";".join(row.old_failure_reasons),
        "hard_blockers": ";".join(row.hard_blockers),
        "accepted_reasons": ";".join(row.accepted_reasons),
    }


def _summary_dict(result: P2bAslsPromotionGateResult) -> dict[str, object]:
    return {
        "overall_status": result.overall_status,
        "target_count": result.target_count,
        "hard_blocker_count": result.hard_blocker_count,
        "review_accepted_count": result.review_accepted_count,
        "global_blockers": ";".join(result.global_blockers),
        "area_uncertainty_unexplained_area_mismatch_count": (
            result.area_uncertainty_unexplained_area_mismatch_count
        ),
        "area_uncertainty_integration_context_incomplete_count": (
            result.area_uncertainty_integration_context_incomplete_count
        ),
    }


def _write_markdown(path: Path, result: P2bAslsPromotionGateResult) -> None:
    lines = [
        "# P2b Revised AsLS Promotion Gate",
        "",
        f"Overall status: {result.overall_status}",
        f"Hard blockers: {result.hard_blocker_count}",
        f"Accepted review rows: {result.review_accepted_count}",
        f"Global blockers: {';'.join(result.global_blockers)}",
        "",
        "| Target | Feature | Old status | Revised status | Hard blockers | Accepted reasons |",
        "|---|---|---|---|---|---|",
    ]
    for row in result.rows:
        lines.append(
            "| "
            f"{row.target_label} | "
            f"{row.selected_feature_id} | "
            f"{row.old_status} | "
            f"{row.revised_status} | "
            f"{';'.join(row.hard_blockers)} | "
            f"{';'.join(row.accepted_reasons)} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_tsv(
    path: Path,
    fieldnames: Sequence[str],
    rows: Iterable[Mapping[str, object]],
) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
            delimiter="\t",
            lineterminator="\n",
            extrasaction="ignore",
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({field: _format_value(row.get(field)) for field in fieldnames})


def _read_tsv(path: Path, required_columns: set[str]) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        columns = set(reader.fieldnames or ())
        missing = sorted(required_columns - columns)
        if missing:
            raise ValueError(f"{path}: missing required columns: {', '.join(missing)}")
        return [dict(row) for row in reader]


def _single_row(rows: Sequence[Mapping[str, str]], path: Path) -> Mapping[str, str]:
    if len(rows) != 1:
        raise ValueError(f"{path}: expected exactly one summary row, found {len(rows)}")
    return rows[0]


def _split_reasons(value: object) -> tuple[str, ...]:
    return tuple(
        part.strip()
        for part in str(value or "").split(";")
        if part.strip()
    )


def _optional_float(value: object) -> float | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = float(text)
    except ValueError as exc:
        raise ValueError(f"non-numeric numeric field value: {text}") from exc
    if not math.isfinite(parsed):
        raise ValueError(f"non-finite numeric field value: {text}")
    return parsed


def _parse_non_negative_int(value: object, field_name: str) -> int:
    text = str(value or "").strip()
    try:
        parsed = int(text)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be an integer: {text}") from exc
    if parsed < 0:
        raise ValueError(f"{field_name} must be >= 0")
    return parsed


def _format_value(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        if not math.isfinite(value):
            return ""
        return f"{value:.6g}"
    return str(value)


if __name__ == "__main__":
    raise SystemExit(main())
```

- [x] **Step 4: Run focused gate tests**

Run:

```powershell
$env:PYTHONPATH = (Get-Location).Path
C:\Users\user\Desktop\XIC_Extractor\.venv\Scripts\python.exe -m pytest tests\test_p2b_asls_promotion_gate.py -q
```

Expected: pass.

## Task 3: Spec And Decision Notes

**Files:**

- Modify: `docs/superpowers/specs/2026-05-24-peak-pipeline-area-baseline-asls-promotion-spec.md`
- Create: `docs/superpowers/notes/2026-05-25-p2b-revised-asls-promotion-gate-note.md`
- Modify: `docs/superpowers/specs/2026-05-24-peak-pipeline-modernization-overview-spec.md`
- Modify: `docs/superpowers/notes/2026-05-25-phase1-modernization-closeout-note.md`

- [x] **Step 1: Update P2b spec semantics**

Add a `2026-05-25 Revised Gate Semantics` section stating:

- the old strict linear-edge RSD comparator is superseded as a hard blocker
- `area_rsd_regression` is accepted when baseline truth says
  `linear_edge_over_subtraction_plausible`
- raw-area violations, coverage gaps, missing trace context, unsupported old
  failure reasons, and unclean P4 area uncertainty remain hard blockers
- the revised gate can only claim `GO_FOR_PRODUCTION_CANDIDATE` on 8RAW evidence
  until 85RAW is rerun or explicitly waived by the owner

- [x] **Step 2: Run the real revised gate**

Run:

```powershell
$env:PYTHONPATH = (Get-Location).Path
C:\Users\user\Desktop\XIC_Extractor\.venv\Scripts\python.exe -m tools.diagnostics.p2b_asls_promotion_gate --p2-gate-rows-tsv output\phase1_p2_asls_shadow_validation\diagnostics\p2_asls_shadow_gate\p2_asls_shadow_gate_rows.tsv --baseline-truth-summary-tsv output\phase1_p2_baseline_truth_audit\baseline_truth_audit_summary.tsv --area-uncertainty-summary-tsv output\phase1_p4_area_uncertainty_formula\diagnostics\area_integration_uncertainty\area_integration_uncertainty_summary.tsv --output-dir output\phase1_p2b_revised_asls_promotion_gate
```

Expected current 8RAW result: exit `0`, `overall_status=GO_FOR_PRODUCTION_CANDIDATE`, `hard_blocker_count=0`, `review_accepted_count=3`.

- [x] **Step 3: Create decision note**

Write `docs/superpowers/notes/2026-05-25-p2b-revised-asls-promotion-gate-note.md` with:

- revised gate verdict
- exact command and output path
- row counts and accepted-review count
- statement that production area was not switched in this task
- next step: separate production-switch plan if the owner accepts 8RAW `production_candidate`

- [x] **Step 4: Update overview and closeout**

Replace blanket `P2b NO-GO` wording with:

- old P2b strict RSD gate: `NO-GO`
- revised P2b 8RAW gate: `GO_FOR_PRODUCTION_CANDIDATE`
- production AsLS switch: not performed in this task
- 85RAW / `production_ready`: still pending

## Task 4: Verification And Review

**Files:** no new functional files beyond prior tasks.

- [x] **Step 1: Run focused and related tests**

Run:

```powershell
$env:PYTHONPATH = (Get-Location).Path
C:\Users\user\Desktop\XIC_Extractor\.venv\Scripts\python.exe -m pytest tests\test_p2b_asls_promotion_gate.py tests\test_p2_asls_shadow_gate.py tests\test_p2_baseline_truth_audit.py -q
```

Expected: pass.

- [x] **Step 2: Compile diagnostics**

Run:

```powershell
C:\Users\user\Desktop\XIC_Extractor\.venv\Scripts\python.exe -m py_compile tools\diagnostics\p2b_asls_promotion_gate.py tools\diagnostics\p2_asls_shadow_gate.py tools\diagnostics\p2_baseline_truth_audit.py
```

Expected: exit `0`.

- [x] **Step 3: Run diff hygiene**

Run:

```powershell
git -c safe.directory=C:/Users/user/Desktop/XIC_Extractor/.worktrees/peak-pipeline-modernization -C . diff --check
```

Expected: no whitespace errors; LF/CRLF warnings are acceptable on this Windows worktree.

- [x] **Step 4: Post-implementation review**

Check:

- revised gate does not read production modules or mutate production settings
- raw-area violation stays a hard blocker
- coverage failure stays a hard blocker
- RSD regression is accepted only with supportive baseline truth
- output note does not claim `production_ready`
- overview/closeout wording does not say P2b production switch already happened
