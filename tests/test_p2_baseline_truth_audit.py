from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
import pytest

from tools.diagnostics.p2_baseline_truth_audit import (
    BaselineTruthRow,
    _build_summary_rows,
    build_baseline_truth_row,
    classify_baseline_truth_row,
    compute_area_metrics,
    run_p2_baseline_truth_audit,
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
        outside_background_pct=2.0,
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
        outside_background_pct=15.0,
    )

    assert classification == "asls_under_subtraction_plausible"
    assert "asls_near_raw" in reason
    assert "outside_background_elevated" in reason


def test_classifies_flat_background_as_linear_edge_over_subtraction() -> None:
    metrics = compute_area_metrics(raw_area=100.0, linear_area=82.0, asls_area=99.5)

    classification, reason = classify_baseline_truth_row(
        metrics,
        trace_point_count=20,
        linear_edge_delta_pct=1.0,
        outside_background_pct=1.0,
    )

    assert classification == "linear_edge_over_subtraction_plausible"
    assert "outside_background_low" in reason


def test_classifies_methods_similar() -> None:
    metrics = compute_area_metrics(raw_area=100.0, linear_area=94.0, asls_area=96.0)

    classification, reason = classify_baseline_truth_row(
        metrics,
        trace_point_count=20,
        linear_edge_delta_pct=2.0,
        outside_background_pct=1.0,
    )

    assert classification == "methods_similar"
    assert "asls_vs_linear_within_5pct" in reason


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
    assert row.outside_background_pct == pytest.approx(5.0)
    assert row.plot_path == "plots/istd.png"


def test_build_summary_rows_accumulates_family_metrics_once() -> None:
    rows = [
        _baseline_truth_row(
            sample="S1",
            classification="methods_similar",
            linear_subtracted=10.0,
            asls_subtracted=2.0,
            asls_vs_linear=8.0,
            linear_edge_delta=1.0,
            outside_background=2.0,
            plot_path="plots/first.png",
        ),
        _baseline_truth_row(
            sample="S2",
            classification="asls_under_subtraction_plausible",
            linear_subtracted=30.0,
            asls_subtracted=4.0,
            asls_vs_linear=18.0,
            linear_edge_delta=3.0,
            outside_background=16.0,
            plot_path="plots/second.png",
        ),
        _baseline_truth_row(
            sample="S3",
            classification="methods_similar",
            linear_subtracted=None,
            asls_subtracted=None,
            asls_vs_linear=12.0,
            linear_edge_delta=2.0,
            outside_background=None,
            plot_path="plots/third.png",
        ),
    ]

    summary = _build_summary_rows(rows)

    assert summary == [
        {
            "target_label": "ISTD-A",
            "feature_family_id": "FAM001",
            "row_count": 3,
            "dominant_classification": "methods_similar",
            "classification_counts": (
                "asls_under_subtraction_plausible:1;methods_similar:2"
            ),
            "median_linear_baseline_subtracted_pct": 20.0,
            "median_asls_baseline_subtracted_pct": 3.0,
            "median_asls_vs_linear_pct": 12.0,
            "max_asls_vs_linear_pct": 18.0,
            "median_linear_edge_delta_pct": 2.0,
            "median_outside_background_pct": 9.0,
            "review_status": "manual_review_required",
            "plot_path": "plots/first.png",
        }
    ]


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

    def fake_trace_loader(
        sample_stem: str,
        mz: float,
        rt_min: float,
        rt_max: float,
        ppm: float,
    ) -> tuple[np.ndarray, np.ndarray]:
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
    assert b"\r\n" not in outputs.rows_tsv.read_bytes()
    assert b"\r\n" not in outputs.summary_tsv.read_bytes()
    assert outputs.rows_tsv.read_text(encoding="utf-8").splitlines()[0].split(
        "\t"
    ) == [
        "target_label",
        "feature_family_id",
        "sample_stem",
        "status",
        "raw_area",
        "linear_area",
        "asls_area",
        "linear_raw_pct",
        "asls_raw_pct",
        "asls_vs_linear_pct",
        "linear_baseline_subtracted_pct",
        "asls_baseline_subtracted_pct",
        "linear_edge_delta_pct",
        "outside_background_pct",
        "peak_start_rt",
        "apex_rt",
        "peak_end_rt",
        "trace_point_count",
        "classification",
        "review_reason",
        "plot_path",
    ]
    assert _read_tsv(outputs.rows_tsv) == [
        {
            "target_label": "ISTD-A",
            "feature_family_id": "FAM001",
            "sample_stem": "S1",
            "status": "detected",
            "raw_area": "1000",
            "linear_area": "800",
            "asls_area": "980",
            "linear_raw_pct": "80",
            "asls_raw_pct": "98",
            "asls_vs_linear_pct": "22.5",
            "linear_baseline_subtracted_pct": "20",
            "asls_baseline_subtracted_pct": "2",
            "linear_edge_delta_pct": "36.25",
            "outside_background_pct": "5",
            "peak_start_rt": "10",
            "apex_rt": "10.1",
            "peak_end_rt": "10.3",
            "trace_point_count": "4",
            "classification": "linear_edge_over_subtraction_plausible",
            "review_reason": (
                "asls_near_raw;linear_subtracts_gt_5pct;"
                "linear_subtracts_gt_10pct;linear_edge_elevated;"
                "outside_background_low"
            ),
            "plot_path": "plots/ISTD-A__FAM001.png",
        },
    ]
    assert outputs.summary_tsv.read_text(encoding="utf-8").splitlines()[0].split(
        "\t"
    ) == [
        "target_label",
        "feature_family_id",
        "row_count",
        "dominant_classification",
        "classification_counts",
        "median_linear_baseline_subtracted_pct",
        "median_asls_baseline_subtracted_pct",
        "median_asls_vs_linear_pct",
        "max_asls_vs_linear_pct",
        "median_linear_edge_delta_pct",
        "median_outside_background_pct",
        "review_status",
        "plot_path",
    ]
    assert _read_tsv(outputs.summary_tsv) == [
        {
            "target_label": "ISTD-A",
            "feature_family_id": "FAM001",
            "row_count": "1",
            "dominant_classification": "linear_edge_over_subtraction_plausible",
            "classification_counts": "linear_edge_over_subtraction_plausible:1",
            "median_linear_baseline_subtracted_pct": "20",
            "median_asls_baseline_subtracted_pct": "2",
            "median_asls_vs_linear_pct": "22.5",
            "max_asls_vs_linear_pct": "22.5",
            "median_linear_edge_delta_pct": "36.25",
            "median_outside_background_pct": "5",
            "review_status": "linear_edge_over_subtraction_plausible",
            "plot_path": "plots/ISTD-A__FAM001.png",
        },
    ]
    payload = json.loads(outputs.json_path.read_text(encoding="utf-8"))
    assert payload["families"] == payload["summary_rows"]
    assert payload["families"][0]["target_label"] == "ISTD-A"


def test_run_p2_baseline_truth_audit_reads_promoted_asls_schema(
    tmp_path: Path,
) -> None:
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
                "area_baseline_corrected": "980",
                "area_baseline_corrected_linear_edge": "800",
                "baseline_type": "asls",
                "family_center_mz": "245",
                "peak_start_rt": "10.0",
                "apex_rt": "10.1",
                "peak_end_rt": "10.3",
            }
        ],
    )

    def fake_trace_loader(
        sample_stem: str,
        mz: float,
        rt_min: float,
        rt_max: float,
        ppm: float,
    ) -> tuple[np.ndarray, np.ndarray]:
        return (
            np.asarray([9.8, 9.9, 10.0, 10.1, 10.2, 10.3, 10.4]),
            np.asarray([10.0, 20.0, 120.0, 200.0, 130.0, 25.0, 10.0]),
        )

    _outputs, result = run_p2_baseline_truth_audit(
        p2_gate_rows_tsv=gate_rows,
        alignment_integration_audit_tsv=audit,
        output_dir=tmp_path / "truth",
        trace_loader=fake_trace_loader,
    )

    assert result.rows[0].linear_area == pytest.approx(800.0)
    assert result.rows[0].asls_area == pytest.approx(980.0)


def test_run_p2_baseline_truth_audit_reads_post_rollback_asls_schema(
    tmp_path: Path,
) -> None:
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
                "area_baseline_corrected": "980",
                "baseline_type": "asls",
                "family_center_mz": "245",
                "peak_start_rt": "10.0",
                "apex_rt": "10.1",
                "peak_end_rt": "10.3",
            }
        ],
    )

    def fake_trace_loader(
        sample_stem: str,
        mz: float,
        rt_min: float,
        rt_max: float,
        ppm: float,
    ) -> tuple[np.ndarray, np.ndarray]:
        return (
            np.asarray([9.8, 9.9, 10.0, 10.1, 10.2, 10.3, 10.4]),
            np.asarray([10.0, 20.0, 120.0, 200.0, 130.0, 25.0, 10.0]),
        )

    _outputs, result = run_p2_baseline_truth_audit(
        p2_gate_rows_tsv=gate_rows,
        alignment_integration_audit_tsv=audit,
        output_dir=tmp_path / "truth",
        trace_loader=fake_trace_loader,
    )

    assert result.rows[0].linear_area is None
    assert result.rows[0].asls_area == pytest.approx(980.0)


def test_run_p2_baseline_truth_audit_can_include_pass_gate_rows(tmp_path: Path) -> None:
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
            },
            {
                "target_label": "ISTD-B",
                "selected_feature_id": "FAM002",
                "status": "PASS",
                "failure_reasons": "",
            },
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
            },
            {
                "feature_family_id": "FAM002",
                "sample_stem": "S1",
                "status": "detected",
                "area": "1000",
                "area_baseline_corrected": "960",
                "area_baseline_corrected_asls": "980",
                "family_center_mz": "246",
                "peak_start_rt": "11.0",
                "apex_rt": "11.1",
                "peak_end_rt": "11.3",
            },
        ],
    )

    def fake_trace_loader(
        sample_stem: str,
        mz: float,
        rt_min: float,
        rt_max: float,
        ppm: float,
    ) -> tuple[np.ndarray, np.ndarray]:
        return (
            np.asarray(
                [9.8, 9.9, 10.0, 10.1, 10.2, 10.3, 10.4, 11.0, 11.2, 11.4]
            ),
            np.asarray(
                [10.0, 20.0, 120.0, 200.0, 130.0, 25.0, 10.0, 60.0, 160.0, 50.0]
            ),
        )

    _, default_result = run_p2_baseline_truth_audit(
        p2_gate_rows_tsv=gate_rows,
        alignment_integration_audit_tsv=audit,
        output_dir=tmp_path / "truth_default",
        trace_loader=fake_trace_loader,
    )
    _, all_status_result = run_p2_baseline_truth_audit(
        p2_gate_rows_tsv=gate_rows,
        alignment_integration_audit_tsv=audit,
        output_dir=tmp_path / "truth_all_status",
        trace_loader=fake_trace_loader,
        include_gate_statuses=("FAIL", "PASS"),
    )

    assert [row.feature_family_id for row in default_result.rows] == ["FAM001"]
    assert [row.feature_family_id for row in all_status_result.rows] == [
        "FAM001",
        "FAM002",
    ]


def _write_tsv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def _read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def _baseline_truth_row(
    *,
    sample: str,
    classification: str,
    linear_subtracted: float | None,
    asls_subtracted: float | None,
    asls_vs_linear: float | None,
    linear_edge_delta: float | None,
    outside_background: float | None,
    plot_path: str,
) -> BaselineTruthRow:
    return BaselineTruthRow(
        target_label="ISTD-A",
        feature_family_id="FAM001",
        sample_stem=sample,
        status="detected",
        raw_area=1000.0,
        linear_area=800.0,
        asls_area=980.0,
        linear_raw_pct=80.0,
        asls_raw_pct=98.0,
        asls_vs_linear_pct=asls_vs_linear,
        linear_baseline_subtracted_pct=linear_subtracted,
        asls_baseline_subtracted_pct=asls_subtracted,
        linear_edge_delta_pct=linear_edge_delta,
        outside_background_pct=outside_background,
        peak_start_rt=10.0,
        apex_rt=10.1,
        peak_end_rt=10.3,
        trace_point_count=4,
        classification=classification,
        review_reason="reason",
        plot_path=plot_path,
    )
