from __future__ import annotations

import csv
from pathlib import Path

from tools.diagnostics.p2b_asls_promotion_gate import (
    main as p2b_asls_promotion_gate_main,
)
from tools.diagnostics.p2b_asls_promotion_gate import run_p2b_asls_promotion_gate


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
                "classification_counts": (
                    "linear_edge_over_subtraction_plausible:6;methods_similar:2"
                ),
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
    assert (
        "baseline_truth_supports_linear_edge_over_subtraction"
        in result.rows[0].accepted_reasons
    )
    assert outputs.summary_tsv.exists()


def test_revised_gate_keeps_raw_area_violation_as_hard_blocker(
    tmp_path: Path,
) -> None:
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
                "failure_reasons": (
                    "area_rsd_regression;asls_area_exceeds_raw_area"
                ),
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


def test_revised_gate_blocks_rsd_regression_without_truth_support(
    tmp_path: Path,
) -> None:
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


def test_revised_gate_accepts_area_rsd_when_rt_boundary_evidence_supports_same_peak(
    tmp_path: Path,
) -> None:
    p2_rows = tmp_path / "p2_rows.tsv"
    truth = tmp_path / "truth.tsv"
    uncertainty = tmp_path / "uncertainty.tsv"
    evidence_spine = tmp_path / "evidence_spine.tsv"
    _write_area_rsd_row(p2_rows)
    _write_manual_review_truth(truth)
    _write_clean_area_uncertainty(uncertainty)
    _write_tsv(
        evidence_spine,
        [
            {
                "sample": "s1",
                "target_label": "ISTD-A",
                "untargeted_family_id": "FAM001",
                "rt_delta_min": "0.00001",
                "boundary_delta_start_min": "0.20",
                "boundary_delta_end_min": "0",
                "mismatch_reason": "boundary_start_delta_gt_0.10",
            },
            {
                "sample": "s2",
                "target_label": "ISTD-A",
                "untargeted_family_id": "FAM001",
                "rt_delta_min": "0",
                "boundary_delta_start_min": "0",
                "boundary_delta_end_min": "0",
                "mismatch_reason": "consistent",
            },
        ],
    )

    _outputs, result = run_p2b_asls_promotion_gate(
        p2_gate_rows_tsv=p2_rows,
        baseline_truth_summary_tsv=truth,
        area_uncertainty_summary_tsv=uncertainty,
        evidence_spine_rows_tsv=evidence_spine,
        output_dir=tmp_path / "gate",
    )

    row = result.rows[0]
    assert result.overall_status == "GO_FOR_PRODUCTION_CANDIDATE"
    assert row.revised_status == "ACCEPTED_REVIEW"
    assert row.evidence_spine_status == "rt_boundary_supported"
    assert row.evidence_spine_sample_count == 2
    assert row.evidence_spine_overwide_boundary_count == 0
    assert row.evidence_spine_narrower_boundary_count == 1
    assert (
        "rt_boundary_evidence_supports_area_variability" in row.accepted_reasons
    )


def test_revised_gate_blocks_area_rsd_when_rt_delta_is_large(
    tmp_path: Path,
) -> None:
    p2_rows = tmp_path / "p2_rows.tsv"
    truth = tmp_path / "truth.tsv"
    uncertainty = tmp_path / "uncertainty.tsv"
    evidence_spine = tmp_path / "evidence_spine.tsv"
    _write_area_rsd_row(p2_rows)
    _write_manual_review_truth(truth)
    _write_clean_area_uncertainty(uncertainty)
    _write_tsv(
        evidence_spine,
        [
            {
                "sample": "s1",
                "target_label": "ISTD-A",
                "untargeted_family_id": "FAM001",
                "rt_delta_min": "0.02",
                "boundary_delta_start_min": "0",
                "boundary_delta_end_min": "0",
                "mismatch_reason": "consistent",
            },
            {
                "sample": "s2",
                "target_label": "ISTD-A",
                "untargeted_family_id": "FAM001",
                "rt_delta_min": "0",
                "boundary_delta_start_min": "0",
                "boundary_delta_end_min": "0",
                "mismatch_reason": "consistent",
            }
        ],
    )

    _outputs, result = run_p2b_asls_promotion_gate(
        p2_gate_rows_tsv=p2_rows,
        baseline_truth_summary_tsv=truth,
        area_uncertainty_summary_tsv=uncertainty,
        evidence_spine_rows_tsv=evidence_spine,
        output_dir=tmp_path / "gate",
    )

    assert result.overall_status == "NO_GO"
    assert "rt_boundary_rt_delta_exceeds_0.5_sec" in result.rows[0].hard_blockers


def test_revised_gate_accepts_large_rt_delta_when_target_trend_is_locally_coherent(
    tmp_path: Path,
) -> None:
    p2_rows = tmp_path / "p2_rows.tsv"
    truth = tmp_path / "truth.tsv"
    uncertainty = tmp_path / "uncertainty.tsv"
    evidence_spine = tmp_path / "evidence_spine.tsv"
    target_rt_trend = tmp_path / "target_rt_trend.tsv"
    _write_area_rsd_row(p2_rows)
    _write_manual_review_truth(truth)
    _write_clean_area_uncertainty(uncertainty)
    _write_tsv(
        evidence_spine,
        [
            {
                "sample": "s1",
                "target_label": "ISTD-A",
                "untargeted_family_id": "FAM001",
                "rt_delta_min": "0.02",
                "boundary_delta_start_min": "0",
                "boundary_delta_end_min": "0",
                "mismatch_reason": "consistent",
            },
            {
                "sample": "s2",
                "target_label": "ISTD-A",
                "untargeted_family_id": "FAM001",
                "rt_delta_min": "0",
                "boundary_delta_start_min": "0",
                "boundary_delta_end_min": "0",
                "mismatch_reason": "consistent",
            },
        ],
    )
    _write_tsv(
        target_rt_trend,
        [
            {
                "target_label": "ISTD-A",
                "sample_count": "85",
                "range_rt_min": "2.15",
                "global_abs_delta_p95_min": "1.45",
                "local_abs_delta_p95_min": "0.048",
                "local_moderate_or_severe_count": "0",
                "local_severe_count": "0",
            }
        ],
    )

    _outputs, result = run_p2b_asls_promotion_gate(
        p2_gate_rows_tsv=p2_rows,
        baseline_truth_summary_tsv=truth,
        area_uncertainty_summary_tsv=uncertainty,
        evidence_spine_rows_tsv=evidence_spine,
        target_rt_trend_summary_tsv=target_rt_trend,
        output_dir=tmp_path / "gate",
    )

    row = result.rows[0]
    assert result.overall_status == "GO_FOR_PRODUCTION_CANDIDATE"
    assert row.revised_status == "ACCEPTED_REVIEW"
    assert row.evidence_spine_status == "rt_boundary_rt_delta_explained_by_target_trend"
    assert "target_rt_trend_supports_large_rt_delta" in row.accepted_reasons


def test_revised_gate_blocks_area_rsd_when_alignment_boundary_is_overwide(
    tmp_path: Path,
) -> None:
    p2_rows = tmp_path / "p2_rows.tsv"
    truth = tmp_path / "truth.tsv"
    uncertainty = tmp_path / "uncertainty.tsv"
    evidence_spine = tmp_path / "evidence_spine.tsv"
    _write_area_rsd_row(p2_rows)
    _write_manual_review_truth(truth)
    _write_clean_area_uncertainty(uncertainty)
    _write_tsv(
        evidence_spine,
        [
            {
                "sample": "s1",
                "target_label": "ISTD-A",
                "untargeted_family_id": "FAM001",
                "rt_delta_min": "0",
                "boundary_delta_start_min": "-0.20",
                "boundary_delta_end_min": "0",
                "mismatch_reason": "boundary_start_delta_gt_0.10",
            },
            {
                "sample": "s2",
                "target_label": "ISTD-A",
                "untargeted_family_id": "FAM001",
                "rt_delta_min": "0",
                "boundary_delta_start_min": "0",
                "boundary_delta_end_min": "0",
                "mismatch_reason": "consistent",
            }
        ],
    )

    _outputs, result = run_p2b_asls_promotion_gate(
        p2_gate_rows_tsv=p2_rows,
        baseline_truth_summary_tsv=truth,
        area_uncertainty_summary_tsv=uncertainty,
        evidence_spine_rows_tsv=evidence_spine,
        output_dir=tmp_path / "gate",
    )

    assert result.overall_status == "NO_GO"
    assert "rt_boundary_alignment_overwide" in result.rows[0].hard_blockers


def test_revised_gate_blocks_unclean_area_uncertainty_summary(
    tmp_path: Path,
) -> None:
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
    target_rt_trend = tmp_path / "target_rt_trend.tsv"
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
    _write_tsv(
        target_rt_trend,
        [
            {
                "target_label": "ISTD-A",
                "local_abs_delta_p95_min": "0.05",
                "local_moderate_or_severe_count": "0",
                "local_severe_count": "0",
            }
        ],
    )

    pass_code = p2b_asls_promotion_gate_main(
        [
            "--p2-gate-rows-tsv",
            str(p2_rows),
            "--baseline-truth-summary-tsv",
            str(truth),
            "--area-uncertainty-summary-tsv",
            str(uncertainty),
            "--target-rt-trend-summary-tsv",
            str(target_rt_trend),
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


def _write_area_rsd_row(path: Path) -> None:
    _write_tsv(
        path,
        [
            {
                "target_label": "ISTD-A",
                "selected_feature_id": "FAM001",
                "sample_count": "2",
                "linear_area_rsd_pct": "10",
                "asls_area_rsd_pct": "11",
                "area_rsd_delta_pct": "1",
                "median_abs_relative_diff_pct": "10",
                "diff_gt_5pct_count": "2",
                "asls_reduced_area_count": "0",
                "asls_exceeds_raw_area_count": "0",
                "status": "FAIL",
                "failure_reasons": "area_rsd_regression",
            }
        ],
    )


def _write_manual_review_truth(path: Path) -> None:
    _write_tsv(
        path,
        [
            {
                "target_label": "ISTD-A",
                "feature_family_id": "FAM001",
                "row_count": "2",
                "dominant_classification": "methods_similar",
                "classification_counts": "methods_similar:2",
                "median_linear_baseline_subtracted_pct": "5",
                "median_asls_baseline_subtracted_pct": "4",
                "median_asls_vs_linear_pct": "1",
                "max_asls_vs_linear_pct": "2",
                "median_linear_edge_delta_pct": "1",
                "median_outside_background_pct": "0",
                "review_status": "manual_review_required",
                "plot_path": "plots/ISTD-A__FAM001.png",
            }
        ],
    )
