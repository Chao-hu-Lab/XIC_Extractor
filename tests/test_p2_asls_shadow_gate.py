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
