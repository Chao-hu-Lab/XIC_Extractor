from __future__ import annotations

import csv
from pathlib import Path

from tools.diagnostics import untargeted_alignment_guardrails as guardrails


def test_compute_guardrails_counts_families_cases_and_writes_case_summary(
    tmp_path: Path,
) -> None:
    alignment_dir = tmp_path / "alignment"
    _write_alignment_fixture(alignment_dir)

    metrics = guardrails.compute_guardrails(alignment_dir)

    assert metrics.zero_present_families == 3
    assert metrics.duplicate_only_families == 1
    assert metrics.high_backfill_dependency_families == 1
    assert metrics.negative_8oxodg_production_families == 1

    case1 = metrics.case_assertions["case1_mz242_5medC_like"]
    assert case1.production_family_count == 1
    assert case1.owner_count == 1
    assert case1.event_count == 3
    assert case1.supporting_event_count == 2

    case2 = metrics.case_assertions["case2_mz296_dense_duplicate"]
    assert case2.production_family_count == 2
    assert case2.preserved_split_or_ambiguous is True

    case3 = metrics.case_assertions["case3_mz322_dense_duplicate"]
    assert case3.strong_edge_count == 1

    summary_path = guardrails.write_case_assertion_summary_tsv(
        tmp_path / "case_assertion_summary.tsv",
        metrics.case_assertions,
    )
    rows = _read_tsv(summary_path)

    assert [row["case"] for row in rows] == [
        "case1_mz242_5medC_like",
        "case2_mz296_dense_duplicate",
        "case3_mz322_dense_duplicate",
        "case4_mz251_anchor_shadow_duplicates",
    ]
    assert rows[0]["supporting_event_count"] == "2"
    assert rows[1]["preserved_split_or_ambiguous"] == "true"
    assert rows[2]["strong_edge_count"] == "1"


def test_high_backfill_dependency_fallback_only_when_warning_column_absent(
    tmp_path: Path,
) -> None:
    alignment_dir = tmp_path / "alignment"
    alignment_dir.mkdir(parents=True)
    _write_tsv(
        alignment_dir / "alignment_review.tsv",
        [
            {
                "feature_family_id": "FAM001",
                "family_center_mz": 500.0,
                "family_center_rt": 5.0,
                "event_cluster_count": 1,
                "event_member_count": 1,
            },
        ],
    )
    _write_tsv(
        alignment_dir / "alignment_cells.tsv",
        [
            _cell_row("FAM001", "rescued"),
            _cell_row("FAM001", "rescued"),
        ],
    )

    metrics = guardrails.compute_guardrails(alignment_dir)

    assert metrics.high_backfill_dependency_families == 1


def test_case2_preserves_split_for_multiple_non_production_review_families(
    tmp_path: Path,
) -> None:
    alignment_dir = tmp_path / "alignment"
    alignment_dir.mkdir(parents=True)
    _write_tsv(
        alignment_dir / "alignment_review.tsv",
        [
            _review_row("FAM001", 296.074, 19.5, 1, 1),
            _review_row("FAM002", 296.075, 19.6, 1, 1),
        ],
    )
    _write_tsv(
        alignment_dir / "alignment_cells.tsv",
        [
            _cell_row("FAM001", "duplicate_assigned"),
            _cell_row("FAM002", "duplicate_assigned"),
        ],
    )

    metrics = guardrails.compute_guardrails(alignment_dir)
    case2 = metrics.case_assertions["case2_mz296_dense_duplicate"]

    assert case2.production_family_count == 0
    assert case2.preserved_split_or_ambiguous is True
    assert case2.status == "PASS"


def test_compare_guardrails_fails_when_candidate_metric_increases() -> None:
    rows = guardrails.compare_guardrails(
        {
            "duplicate_only_families": 1,
            "zero_present_families": 2,
            "high_backfill_dependency_families": 3,
            "negative_8oxodg_production_families": 4,
        },
        {
            "duplicate_only_families": 2,
            "zero_present_families": 2,
            "high_backfill_dependency_families": 1,
            "negative_8oxodg_production_families": 5,
        },
    )

    assert [row["metric"] for row in rows] == [
        "duplicate_only_families",
        "zero_present_families",
        "high_backfill_dependency_families",
        "negative_8oxodg_production_families",
    ]
    assert rows[0]["status"] == "FAIL"
    assert rows[1]["status"] == "PASS"
    assert rows[2]["status"] == "PASS"
    assert rows[3]["status"] == "FAIL"


def test_compare_targeted_audit_counts_marks_split_and_miss_regressions(
    tmp_path: Path,
) -> None:
    baseline_csv = tmp_path / "baseline.csv"
    candidate_csv = tmp_path / "candidate.csv"
    _write_csv(
        baseline_csv,
        [
            {"sample_stem": "sample01", "failure_mode": "PASS"},
            {"sample_stem": "sample02", "failure_mode": "SPLIT"},
            {"sample_stem": "sample03", "failure_mode": "MISS"},
        ],
    )
    _write_csv(
        candidate_csv,
        [
            {"sample_stem": "sample01", "failure_mode": "SPLIT"},
            {"sample_stem": "sample02", "failure_mode": "SPLIT"},
            {"sample_stem": "sample03", "failure_mode": "MISS"},
            {"sample_stem": "sample04", "failure_mode": "MISS"},
        ],
    )

    rows = guardrails.compare_targeted_audit_counts(
        baseline_csv,
        candidate_csv,
        target_label="5-medC",
    )

    assert rows == [
        {
            "target_label": "5-medC",
            "failure_mode": "SPLIT",
            "baseline_count": "1",
            "candidate_count": "2",
            "delta": "1",
            "status": "FAIL",
        },
        {
            "target_label": "5-medC",
            "failure_mode": "MISS",
            "baseline_count": "1",
            "candidate_count": "2",
            "delta": "1",
            "status": "FAIL",
        },
    ]


def test_main_writes_requested_outputs(tmp_path: Path) -> None:
    baseline_dir = tmp_path / "baseline_alignment"
    candidate_dir = tmp_path / "candidate_alignment"
    _write_alignment_fixture(baseline_dir)
    _write_alignment_fixture(candidate_dir)
    baseline_csv = tmp_path / "baseline.csv"
    candidate_csv = tmp_path / "candidate.csv"
    _write_csv(
        baseline_csv,
        [{"sample_stem": "sample01", "failure_mode": "PASS"}],
    )
    _write_csv(
        candidate_csv,
        [{"sample_stem": "sample01", "failure_mode": "MISS"}],
    )

    code = guardrails.main(
        [
            "--alignment-dir",
            str(candidate_dir),
            "--baseline-dir",
            str(baseline_dir),
            "--candidate-dir",
            str(candidate_dir),
            "--output-json",
            str(tmp_path / "metrics.json"),
            "--case-summary-tsv",
            str(tmp_path / "case_assertion_summary.tsv"),
            "--comparison-csv",
            str(tmp_path / "comparison.csv"),
            "--baseline-targeted-comparison",
            str(baseline_csv),
            "--candidate-targeted-comparison",
            str(candidate_csv),
            "--target-label",
            "5-medC",
            "--targeted-comparison-csv",
            str(tmp_path / "targeted_comparison.csv"),
        ],
    )

    assert code == 0
    assert (tmp_path / "metrics.json").read_text(encoding="utf-8")
    assert _read_tsv(tmp_path / "case_assertion_summary.tsv")[0]["case"]
    assert _read_csv(tmp_path / "comparison.csv")[0]["metric"] == (
        "duplicate_only_families"
    )
    assert _read_csv(tmp_path / "targeted_comparison.csv")[1]["status"] == "FAIL"


def test_main_rejects_no_actionable_group(capsys) -> None:
    code = guardrails.main([])

    assert code == 2
    assert "Provide at least one actionable option group" in capsys.readouterr().err


def test_main_requires_complete_guardrail_comparison_group(
    tmp_path: Path,
    capsys,
) -> None:
    code = guardrails.main(["--baseline-dir", str(tmp_path / "baseline")])

    assert code == 2
    err = capsys.readouterr().err
    assert "--baseline-dir, --candidate-dir, and --comparison-csv" in err


def test_main_requires_complete_targeted_comparison_group(
    tmp_path: Path,
    capsys,
) -> None:
    code = guardrails.main(
        [
            "--baseline-targeted-comparison",
            str(tmp_path / "baseline.csv"),
            "--target-label",
            "5-medC",
        ],
    )

    assert code == 2
    err = capsys.readouterr().err
    assert "--baseline-targeted-comparison" in err
    assert "--targeted-comparison-csv" in err


def test_main_requires_output_json_with_alignment_dir(
    tmp_path: Path,
    capsys,
) -> None:
    code = guardrails.main(["--alignment-dir", str(tmp_path / "alignment")])

    assert code == 2
    err = capsys.readouterr().err
    assert "--alignment-dir" in err
    assert "--output-json" in err


def test_main_rejects_output_json_without_alignment_dir(
    tmp_path: Path,
    capsys,
) -> None:
    baseline_dir = tmp_path / "baseline_alignment"
    candidate_dir = tmp_path / "candidate_alignment"
    _write_alignment_fixture(baseline_dir)
    _write_alignment_fixture(candidate_dir)

    code = guardrails.main(
        [
            "--baseline-dir",
            str(baseline_dir),
            "--candidate-dir",
            str(candidate_dir),
            "--comparison-csv",
            str(tmp_path / "comparison.csv"),
            "--output-json",
            str(tmp_path / "metrics.json"),
        ],
    )

    assert code == 2
    err = capsys.readouterr().err
    assert "--alignment-dir" in err
    assert "--output-json" in err


def test_main_rejects_stray_case_summary_tsv_with_valid_baseline_group(
    tmp_path: Path,
    capsys,
) -> None:
    baseline_dir = tmp_path / "baseline_alignment"
    candidate_dir = tmp_path / "candidate_alignment"
    _write_alignment_fixture(baseline_dir)
    _write_alignment_fixture(candidate_dir)

    code = guardrails.main(
        [
            "--baseline-dir",
            str(baseline_dir),
            "--candidate-dir",
            str(candidate_dir),
            "--comparison-csv",
            str(tmp_path / "comparison.csv"),
            "--case-summary-tsv",
            str(tmp_path / "case_assertion_summary.tsv"),
        ],
    )

    assert code == 2
    err = capsys.readouterr().err
    assert "--alignment-dir" in err
    assert "alignment" in err


def test_main_reports_missing_alignment_review_tsv(
    tmp_path: Path,
    capsys,
) -> None:
    alignment_dir = tmp_path / "alignment"
    alignment_dir.mkdir()

    code = guardrails.main(
        [
            "--alignment-dir",
            str(alignment_dir),
            "--output-json",
            str(tmp_path / "metrics.json"),
        ],
    )

    assert code == 2
    assert str(alignment_dir / "alignment_review.tsv") in capsys.readouterr().err


def test_main_reports_missing_targeted_comparison_csv(
    tmp_path: Path,
    capsys,
) -> None:
    baseline_csv = tmp_path / "baseline.csv"
    missing_candidate_csv = tmp_path / "missing_candidate.csv"
    _write_csv(
        baseline_csv,
        [{"sample_stem": "sample01", "failure_mode": "PASS"}],
    )

    code = guardrails.main(
        [
            "--baseline-targeted-comparison",
            str(baseline_csv),
            "--candidate-targeted-comparison",
            str(missing_candidate_csv),
            "--target-label",
            "5-medC",
            "--targeted-comparison-csv",
            str(tmp_path / "targeted_comparison.csv"),
        ],
    )

    assert code == 2
    assert str(missing_candidate_csv) in capsys.readouterr().err


def test_main_rejects_targeted_comparison_without_failure_mode_column(
    tmp_path: Path,
    capsys,
) -> None:
    baseline_csv = tmp_path / "baseline.csv"
    candidate_csv = tmp_path / "candidate.csv"
    _write_csv(baseline_csv, [{"sample_stem": "sample01"}])
    _write_csv(candidate_csv, [{"sample_stem": "sample01", "failure_mode": "MISS"}])

    code = guardrails.main(
        [
            "--baseline-targeted-comparison",
            str(baseline_csv),
            "--candidate-targeted-comparison",
            str(candidate_csv),
            "--target-label",
            "5-medC",
            "--targeted-comparison-csv",
            str(tmp_path / "targeted_comparison.csv"),
        ],
    )

    assert code == 2
    assert "failure_mode" in capsys.readouterr().err


ALIGNMENT_REVIEW_COLUMNS = (
    "feature_family_id",
    "neutral_loss_tag",
    "family_center_mz",
    "family_center_rt",
    "family_product_mz",
    "family_observed_neutral_loss_da",
    "has_anchor",
    "event_cluster_count",
    "event_cluster_ids",
    "event_member_count",
    "detected_count",
    "absent_count",
    "unchecked_count",
    "duplicate_assigned_count",
    "ambiguous_ms1_owner_count",
    "present_rate",
    "representative_samples",
    "family_evidence",
    "warning",
    "reason",
)

ALIGNMENT_CELLS_COLUMNS = (
    "feature_family_id",
    "sample_stem",
    "status",
    "area",
    "apex_rt",
    "height",
    "peak_start_rt",
    "peak_end_rt",
    "rt_delta_sec",
    "trace_quality",
    "scan_support_score",
    "source_candidate_id",
    "source_raw_file",
    "neutral_loss_tag",
    "family_center_mz",
    "family_center_rt",
    "reason",
)

OWNER_EDGE_EVIDENCE_COLUMNS = (
    "left_owner_id",
    "right_owner_id",
    "left_sample_stem",
    "right_sample_stem",
    "neutral_loss_tag",
    "left_precursor_mz",
    "right_precursor_mz",
    "left_rt_min",
    "right_rt_min",
    "decision",
    "failure_reason",
    "rt_raw_delta_sec",
    "rt_drift_corrected_delta_sec",
    "drift_prior_source",
    "injection_order_gap",
    "owner_quality",
    "seed_support_level",
    "duplicate_context",
    "score",
    "reason",
)


def _write_alignment_fixture(path: Path) -> None:
    path.mkdir(parents=True)
    _write_tsv(
        path / "alignment_review.tsv",
        [
            _review_row("FAM001", 242.114, 12.0, 1, 3),
            _review_row("FAM002", 296.074, 19.5, 1, 1),
            _review_row("FAM003", 296.075, 19.6, 1, 1),
            _review_row("FAM004", 322.143, 23.0, 1, 4),
            _review_row("FAM005", 284.0989, 10.0, 1, 1),
            _review_row("FAM006", 400.0, 15.0, 1, 3, "high_backfill_dependency"),
            _review_row("FAM007", 251.084, 8.5, 1, 1),
            _review_row("FAM008", 500.0, 5.0, 1, 1),
            _review_row("FAM009", 501.0, 5.1, 1, 1),
        ],
        fieldnames=ALIGNMENT_REVIEW_COLUMNS,
    )
    _write_tsv(
        path / "alignment_cells.tsv",
        [
            _cell_row("FAM001", "detected"),
            _cell_row("FAM002", "detected"),
            _cell_row("FAM003", "rescued"),
            _cell_row("FAM003", "ambiguous_ms1_owner"),
            _cell_row("FAM004", "duplicate_assigned"),
            _cell_row("FAM005", "detected"),
            _cell_row("FAM006", "rescued"),
            _cell_row("FAM006", "rescued"),
            _cell_row("FAM007", "ambiguous_ms1_owner"),
            _cell_row("FAM008", "rescued"),
            _cell_row("FAM008", "rescued"),
        ],
        fieldnames=ALIGNMENT_CELLS_COLUMNS,
    )
    _write_tsv(
        path / "owner_edge_evidence.tsv",
        [
            {
                "decision": "strong_edge",
                "left_precursor_mz": "322.143",
                "left_rt_min": "22.8",
                "right_precursor_mz": "322.1435",
                "right_rt_min": "23.5",
            },
            {
                "decision": "weak_edge",
                "left_precursor_mz": "322.143",
                "left_rt_min": "22.8",
                "right_precursor_mz": "322.143",
                "right_rt_min": "23.5",
            },
        ],
        fieldnames=OWNER_EDGE_EVIDENCE_COLUMNS,
    )


def _review_row(
    family_id: str,
    mz: float,
    rt: float,
    event_cluster_count: int,
    event_member_count: int,
    warning: str = "",
) -> dict[str, object]:
    return {
        "feature_family_id": family_id,
        "family_center_mz": mz,
        "family_center_rt": rt,
        "event_cluster_count": event_cluster_count,
        "event_member_count": event_member_count,
        "warning": warning,
    }


def _cell_row(family_id: str, status: str) -> dict[str, object]:
    return {
        "feature_family_id": family_id,
        "status": status,
    }


def _write_tsv(
    path: Path,
    rows: list[dict[str, object]],
    *,
    fieldnames: tuple[str, ...] | None = None,
) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=list(fieldnames or rows[0]),
            delimiter="\t",
        )
        writer.writeheader()
        writer.writerows(rows)


def _read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
