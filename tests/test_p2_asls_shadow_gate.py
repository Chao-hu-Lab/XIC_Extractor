from __future__ import annotations

import csv
from pathlib import Path

from tools.diagnostics.p2_asls_shadow_gate import main as p2_asls_shadow_gate_main
from tools.diagnostics.p2_asls_shadow_gate import run_p2_asls_shadow_gate


def _write_tsv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def _read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def test_p2_asls_shadow_gate_passes_when_asls_rsd_is_close(tmp_path: Path) -> None:
    audit = tmp_path / "alignment_cell_integration_audit.tsv"
    summary = tmp_path / "targeted_istd_benchmark_summary.tsv"
    _write_tsv(
        audit,
        [
            {
                "feature_family_id": "FAM001",
                "sample_stem": "S1",
                "status": "detected",
                "area": "100",
                "area_baseline_corrected": "80",
                "area_baseline_corrected_asls": "78",
                "baseline_score_asls": "0.78",
            },
            {
                "feature_family_id": "FAM001",
                "sample_stem": "S2",
                "status": "detected",
                "area": "110",
                "area_baseline_corrected": "88",
                "area_baseline_corrected_asls": "86",
                "baseline_score_asls": "0.7818",
            },
        ],
    )
    _write_tsv(
        summary,
        [
            {
                "target_label": "ISTD-A",
                "role": "ISTD",
                "active_tag": "TRUE",
                "selected_feature_id": "FAM001",
                "coverage_denominator_count": "2",
            }
        ],
    )

    outputs, result = run_p2_asls_shadow_gate(
        alignment_integration_audit_tsv=audit,
        targeted_istd_benchmark_summary_tsv=summary,
        output_dir=tmp_path / "gate",
    )

    assert result.overall_status == "PASS"
    assert result.failed_count == 0
    assert outputs.summary_tsv.exists()
    assert outputs.rows_tsv.exists()
    assert b"\r\n" not in outputs.rows_tsv.read_bytes()
    assert b"\r\n" not in outputs.summary_tsv.read_bytes()
    assert outputs.rows_tsv.read_text(encoding="utf-8").splitlines()[0].split(
        "\t"
    ) == [
        "target_label",
        "selected_feature_id",
        "sample_count",
        "linear_area_rsd_pct",
        "asls_area_rsd_pct",
        "area_rsd_delta_pct",
        "median_abs_relative_diff_pct",
        "diff_gt_5pct_count",
        "asls_reduced_area_count",
        "asls_exceeds_raw_area_count",
        "status",
        "failure_reasons",
    ]
    assert _read_tsv(outputs.rows_tsv) == [
        {
            "target_label": "ISTD-A",
            "selected_feature_id": "FAM001",
            "sample_count": "2",
            "linear_area_rsd_pct": "6.73435",
            "asls_area_rsd_pct": "6.8986",
            "area_rsd_delta_pct": "0.164252",
            "median_abs_relative_diff_pct": "2.38636",
            "diff_gt_5pct_count": "0",
            "asls_reduced_area_count": "2",
            "asls_exceeds_raw_area_count": "0",
            "status": "PASS",
            "failure_reasons": "",
        },
    ]
    assert outputs.summary_tsv.read_text(encoding="utf-8").splitlines()[0].split(
        "\t"
    ) == [
        "overall_status",
        "failed_count",
        "target_count",
        "max_area_rsd_delta_pct",
        "max_median_abs_relative_diff_pct",
        "max_asls_exceeds_raw_area_count",
        "max_rsd_regression_pct",
    ]
    assert _read_tsv(outputs.summary_tsv) == [
        {
            "overall_status": "PASS",
            "failed_count": "0",
            "target_count": "1",
            "max_area_rsd_delta_pct": "0.164252",
            "max_median_abs_relative_diff_pct": "2.38636",
            "max_asls_exceeds_raw_area_count": "0",
            "max_rsd_regression_pct": "0.3",
        },
    ]


def test_p2_asls_shadow_gate_reads_promoted_asls_schema(
    tmp_path: Path,
) -> None:
    audit = tmp_path / "alignment_cell_integration_audit.tsv"
    summary = tmp_path / "targeted_istd_benchmark_summary.tsv"
    _write_tsv(
        audit,
        [
            {
                "feature_family_id": "FAM001",
                "sample_stem": "S1",
                "status": "detected",
                "area": "100",
                "area_baseline_corrected": "78",
                "area_baseline_corrected_linear_edge": "80",
                "baseline_type": "asls",
                "baseline_score": "0.78",
                "baseline_score_linear_edge": "0.8",
            },
            {
                "feature_family_id": "FAM001",
                "sample_stem": "S2",
                "status": "detected",
                "area": "110",
                "area_baseline_corrected": "86",
                "area_baseline_corrected_linear_edge": "88",
                "baseline_type": "asls",
                "baseline_score": "0.7818",
                "baseline_score_linear_edge": "0.8",
            },
        ],
    )
    _write_tsv(
        summary,
        [
            {
                "target_label": "ISTD-A",
                "role": "ISTD",
                "active_tag": "TRUE",
                "selected_feature_id": "FAM001",
                "coverage_denominator_count": "2",
            }
        ],
    )

    _outputs, result = run_p2_asls_shadow_gate(
        alignment_integration_audit_tsv=audit,
        targeted_istd_benchmark_summary_tsv=summary,
        output_dir=tmp_path / "gate",
    )

    assert result.overall_status == "PASS"
    assert result.rows[0].linear_area_rsd_pct is not None
    assert result.rows[0].asls_area_rsd_pct is not None


def test_p2_asls_shadow_gate_reports_missing_post_rollback_comparator(
    tmp_path: Path,
) -> None:
    audit = tmp_path / "alignment_cell_integration_audit.tsv"
    summary = tmp_path / "targeted_istd_benchmark_summary.tsv"
    _write_tsv(
        audit,
        [
            {
                "feature_family_id": "FAM001",
                "sample_stem": "S1",
                "status": "detected",
                "area": "100",
                "area_baseline_corrected": "78",
                "baseline_type": "asls",
                "baseline_score": "0.78",
            },
            {
                "feature_family_id": "FAM001",
                "sample_stem": "S2",
                "status": "detected",
                "area": "110",
                "area_baseline_corrected": "86",
                "baseline_type": "asls",
                "baseline_score": "0.7818",
            },
        ],
    )
    _write_tsv(
        summary,
        [
            {
                "target_label": "ISTD-A",
                "role": "ISTD",
                "active_tag": "TRUE",
                "selected_feature_id": "FAM001",
                "coverage_denominator_count": "2",
            }
        ],
    )

    _outputs, result = run_p2_asls_shadow_gate(
        alignment_integration_audit_tsv=audit,
        targeted_istd_benchmark_summary_tsv=summary,
        output_dir=tmp_path / "gate",
    )

    assert result.overall_status == "FAIL"
    assert "baseline_comparison_columns_unavailable" in result.rows[0].failure_reasons


def test_p2_asls_shadow_gate_fails_when_asls_exceeds_raw_area(
    tmp_path: Path,
) -> None:
    audit = tmp_path / "alignment_cell_integration_audit.tsv"
    summary = tmp_path / "targeted_istd_benchmark_summary.tsv"
    _write_tsv(
        audit,
        [
            {
                "feature_family_id": "FAM001",
                "sample_stem": "S1",
                "status": "detected",
                "area": "100",
                "area_baseline_corrected": "80",
                "area_baseline_corrected_asls": "120",
                "baseline_score_asls": "1.2",
            },
            {
                "feature_family_id": "FAM001",
                "sample_stem": "S2",
                "status": "detected",
                "area": "100",
                "area_baseline_corrected": "80",
                "area_baseline_corrected_asls": "118",
                "baseline_score_asls": "1.18",
            },
        ],
    )
    _write_tsv(
        summary,
        [
            {
                "target_label": "ISTD-A",
                "role": "ISTD",
                "active_tag": "TRUE",
                "selected_feature_id": "FAM001",
                "coverage_denominator_count": "2",
            }
        ],
    )

    _outputs, result = run_p2_asls_shadow_gate(
        alignment_integration_audit_tsv=audit,
        targeted_istd_benchmark_summary_tsv=summary,
        output_dir=tmp_path / "gate",
    )

    assert result.overall_status == "FAIL"
    assert result.failed_count == 1
    assert "asls_area_exceeds_raw_area" in result.rows[0].failure_reasons


def test_p2_asls_shadow_gate_fails_when_asls_rsd_regresses(
    tmp_path: Path,
) -> None:
    audit = tmp_path / "alignment_cell_integration_audit.tsv"
    summary = tmp_path / "targeted_istd_benchmark_summary.tsv"
    _write_tsv(
        audit,
        [
            {
                "feature_family_id": "FAM001",
                "sample_stem": "S1",
                "status": "detected",
                "area": "200",
                "area_baseline_corrected": "100",
                "area_baseline_corrected_asls": "100",
                "baseline_score_asls": "0.5",
            },
            {
                "feature_family_id": "FAM001",
                "sample_stem": "S2",
                "status": "detected",
                "area": "200",
                "area_baseline_corrected": "100",
                "area_baseline_corrected_asls": "120",
                "baseline_score_asls": "0.6",
            },
        ],
    )
    _write_tsv(
        summary,
        [
            {
                "target_label": "ISTD-A",
                "role": "ISTD",
                "active_tag": "TRUE",
                "selected_feature_id": "FAM001",
                "coverage_denominator_count": "2",
            }
        ],
    )

    _outputs, result = run_p2_asls_shadow_gate(
        alignment_integration_audit_tsv=audit,
        targeted_istd_benchmark_summary_tsv=summary,
        output_dir=tmp_path / "gate",
    )

    assert result.overall_status == "FAIL"
    assert result.failed_count == 1
    assert "area_rsd_regression" in result.rows[0].failure_reasons


def test_p2_asls_shadow_gate_fails_when_shadow_coverage_is_incomplete(
    tmp_path: Path,
) -> None:
    audit = tmp_path / "alignment_cell_integration_audit.tsv"
    summary = tmp_path / "targeted_istd_benchmark_summary.tsv"
    _write_tsv(
        audit,
        [
            {
                "feature_family_id": "FAM001",
                "sample_stem": "S1",
                "status": "detected",
                "area": "100",
                "area_baseline_corrected": "80",
                "area_baseline_corrected_asls": "80",
                "baseline_score_asls": "0.8",
            },
            {
                "feature_family_id": "FAM001",
                "sample_stem": "S2",
                "status": "detected",
                "area": "110",
                "area_baseline_corrected": "88",
                "area_baseline_corrected_asls": "88",
                "baseline_score_asls": "0.8",
            },
        ],
    )
    _write_tsv(
        summary,
        [
            {
                "target_label": "ISTD-A",
                "role": "ISTD",
                "active_tag": "TRUE",
                "selected_feature_id": "FAM001",
                "coverage_denominator_count": "8",
            }
        ],
    )

    _outputs, result = run_p2_asls_shadow_gate(
        alignment_integration_audit_tsv=audit,
        targeted_istd_benchmark_summary_tsv=summary,
        output_dir=tmp_path / "gate",
    )

    assert result.overall_status == "FAIL"
    assert result.failed_count == 1
    assert "shadow_coverage_incomplete" in result.rows[0].failure_reasons


def test_p2_asls_shadow_gate_cli_exit_codes(tmp_path: Path) -> None:
    audit = tmp_path / "alignment_cell_integration_audit.tsv"
    summary = tmp_path / "targeted_istd_benchmark_summary.tsv"
    _write_tsv(
        audit,
        [
            {
                "feature_family_id": "FAM001",
                "sample_stem": "S1",
                "status": "detected",
                "area": "100",
                "area_baseline_corrected": "80",
                "area_baseline_corrected_asls": "78",
                "baseline_score_asls": "0.78",
            },
            {
                "feature_family_id": "FAM001",
                "sample_stem": "S2",
                "status": "detected",
                "area": "110",
                "area_baseline_corrected": "88",
                "area_baseline_corrected_asls": "86",
                "baseline_score_asls": "0.7818",
            },
        ],
    )
    _write_tsv(
        summary,
        [
            {
                "target_label": "ISTD-A",
                "role": "ISTD",
                "active_tag": "TRUE",
                "selected_feature_id": "FAM001",
                "coverage_denominator_count": "2",
            }
        ],
    )

    pass_code = p2_asls_shadow_gate_main(
        [
            "--alignment-integration-audit-tsv",
            str(audit),
            "--targeted-istd-benchmark-summary-tsv",
            str(summary),
            "--output-dir",
            str(tmp_path / "pass_gate"),
        ]
    )
    fail_code = p2_asls_shadow_gate_main(
        [
            "--alignment-integration-audit-tsv",
            str(audit),
            "--targeted-istd-benchmark-summary-tsv",
            str(summary),
            "--output-dir",
            str(tmp_path / "fail_gate"),
            "--max-rsd-regression-pct",
            "-1",
        ]
    )
    invalid_code = p2_asls_shadow_gate_main(
        [
            "--alignment-integration-audit-tsv",
            str(tmp_path / "missing.tsv"),
            "--targeted-istd-benchmark-summary-tsv",
            str(summary),
            "--output-dir",
            str(tmp_path / "invalid_gate"),
        ]
    )

    assert pass_code == 0
    assert fail_code == 1
    assert invalid_code == 2
