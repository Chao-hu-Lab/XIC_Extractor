import csv
from pathlib import Path

from tools.diagnostics import targeted_evidence_review_report as report


def test_targeted_evidence_review_report_renders_human_first_sections(
    tmp_path: Path,
) -> None:
    inputs = _targeted_inputs(tmp_path)
    output_html = tmp_path / "targeted_evidence_decision_report.html"

    assert report.main([*inputs, "--output-html", str(output_html)]) == 0

    html = output_html.read_text(encoding="utf-8")
    assert "Targeted Evidence Decision Report" in html
    assert "Run Verdict: WARN" in html
    assert "evidence chain is coherent, manual review recommended" in html
    assert "Action Summary" in html
    assert "Evidence Health" in html
    assert "Inspect now" in html
    assert "Check MS2 timing" in html
    assert "Systemic dropout context" in html
    assert "Target Burden Map" in html
    assert "Full Target Reliability Map" in html
    assert "NL Dropout Root Cause" in html
    assert "Evidence Consistency" in html
    assert "Review Queue" in html
    assert "42 / 42 consistent" in html
    assert "no_diagnostic_product 2" in html
    assert "off_apex_ms2 1" in html
    assert "ppm_gate_fail 1" in html
    assert "sample=S2,target=8-oxodG,mz=284.099" in html
    assert "targeted_nl_dropout_root_cause_rows.tsv" in html
    assert "Full row tables are intentionally kept in TSV artifacts." in html
    assert html.index("Priority Review Queue") < html.index("Target Burden Map")
    assert html.index("Target Burden Map") < html.index("Full Target Reliability Map")
    assert html.index("8-oxodG") < html.index("CleanTarget")
    assert html.index("ppm_gate_fail") < html.index("off_apex_ms2")
    assert "<table" not in html


def test_targeted_evidence_review_report_fails_on_cross_report_mismatch(
    tmp_path: Path,
) -> None:
    inputs = _targeted_inputs(
        tmp_path,
        cross_summary={
            "rows_checked": "42",
            "consistent_count": "40",
            "mismatch_count": "1",
            "missing_candidate_count": "1",
            "missing_reliability_count": "0",
            "issue_counts": "targeted_review_candidate_suggests_dropout:1",
        },
        include_cross_rows=True,
    )
    output_html = tmp_path / "report.html"

    assert report.main([*inputs, "--output-html", str(output_html)]) == 0

    html = output_html.read_text(encoding="utf-8")
    assert "Run Verdict: FAIL" in html
    assert "evidence chain is internally inconsistent" in html
    assert "targeted_review_candidate_suggests_dropout" in html
    assert "source_key=S9|ProblemTarget" in html


def test_targeted_evidence_review_report_orders_mismatch_before_missing_rows(
    tmp_path: Path,
) -> None:
    inputs = _targeted_inputs(
        tmp_path,
        cross_summary={
            "rows_checked": "42",
            "consistent_count": "40",
            "mismatch_count": "2",
            "missing_candidate_count": "1",
            "missing_reliability_count": "0",
            "issue_counts": (
                "missing_selected_candidate:1;"
                "targeted_review_candidate_suggests_dropout:1"
            ),
        },
        cross_rows=(
            _cross_row(
                sample="S1",
                target="MissingCandidate",
                issue="missing_selected_candidate",
            ),
            _cross_row(
                sample="S2",
                target="MismatchTarget",
                issue="targeted_review_candidate_suggests_dropout",
            ),
        ),
    )
    output_html = tmp_path / "report.html"

    assert report.main([*inputs, "--output-html", str(output_html)]) == 0

    html = output_html.read_text(encoding="utf-8")
    assert html.index("source_key=S2|MismatchTarget") < html.index(
        "source_key=S1|MissingCandidate"
    )


def test_targeted_evidence_review_report_passes_without_manual_review(
    tmp_path: Path,
) -> None:
    inputs = _targeted_inputs(
        tmp_path,
        reliability_summary=(
            {
                "target_label": "CleanTarget",
                "role": "Analyte",
                "benchmark_eligible_count": "2",
                "targeted_review_positive_count": "0",
                "targeted_review_count": "0",
                "targeted_negative_count": "0",
                "top_risk_reasons": "",
                "known_exception": "",
            },
        ),
        reliability_rows=(
            _reliability_row(
                sample="S1",
                target="CleanTarget",
                state="benchmark_eligible",
            ),
        ),
        root_summary={
            "rows_checked": "1",
            "review_positive_count": "0",
            "included_count": "0",
            "missing_candidate_count": "0",
            "bucket_counts": "",
            "target_counts": "",
            "product_absence_reason_counts": "",
        },
        root_rows=(),
    )
    output_html = tmp_path / "pass.html"

    assert report.main([*inputs, "--output-html", str(output_html)]) == 0

    html = output_html.read_text(encoding="utf-8")
    assert "Run Verdict: PASS" in html
    assert "no immediate manual review requested" in html


def test_targeted_evidence_review_report_missing_required_columns_fails(
    tmp_path: Path,
) -> None:
    inputs_dir = tmp_path / "diagnostics"
    _write_tsv(
        inputs_dir / "targeted_peak_reliability_summary.tsv",
        (
            {
                "target_label": "T1",
                "benchmark_eligible_count": "1",
            },
        ),
    )
    _write_tsv(
        inputs_dir / "targeted_peak_reliability_rows.tsv",
        (_reliability_row(sample="S1", target="T1", state="benchmark_eligible"),),
    )
    _write_tsv(inputs_dir / "targeted_nl_dropout_root_cause_summary.tsv", ())
    _write_tsv(inputs_dir / "targeted_nl_dropout_root_cause_rows.tsv", ())
    _write_tsv(inputs_dir / "cross_report_evidence_consistency_summary.tsv", ())

    code = report.main(
        [
            "--targeted-reliability-summary-tsv",
            str(inputs_dir / "targeted_peak_reliability_summary.tsv"),
            "--targeted-reliability-rows-tsv",
            str(inputs_dir / "targeted_peak_reliability_rows.tsv"),
            "--root-cause-summary-tsv",
            str(inputs_dir / "targeted_nl_dropout_root_cause_summary.tsv"),
            "--root-cause-rows-tsv",
            str(inputs_dir / "targeted_nl_dropout_root_cause_rows.tsv"),
            "--cross-report-summary-tsv",
            str(inputs_dir / "cross_report_evidence_consistency_summary.tsv"),
            "--output-html",
            str(tmp_path / "report.html"),
        ]
    )

    assert code == 2


def test_targeted_evidence_review_report_script_entrypoint_works(
    tmp_path: Path,
) -> None:
    inputs = _targeted_inputs(tmp_path)
    output_html = tmp_path / "script.html"
    script = Path("tools/diagnostics/targeted_evidence_review_report.py")

    import subprocess

    completed = subprocess.run(
        [
            "python",
            str(script),
            *inputs,
            "--output-html",
            str(output_html),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert "Verdict: WARN" in completed.stdout
    assert output_html.is_file()


def test_targeted_evidence_review_report_escapes_user_derived_text(
    tmp_path: Path,
) -> None:
    inputs = _targeted_inputs(
        tmp_path,
        reliability_summary=(
            {
                "target_label": "<script>x</script>",
                "role": "Analyte",
                "benchmark_eligible_count": "0",
                "targeted_review_positive_count": "1",
                "targeted_review_count": "0",
                "targeted_negative_count": "0",
                "top_risk_reasons": "plausible_nl_dropout",
                "known_exception": "",
            },
        ),
        reliability_rows=(
            _reliability_row(
                sample="<b>S1</b>",
                target="<script>x</script>",
                state="targeted_review_positive",
            ),
        ),
        root_rows=(
            _root_row(
                sample="<b>S1</b>",
                target="<script>x</script>",
                mz="284.099",
                bucket="ppm_gate_fail",
                best_loss_ppm="88.2",
            ),
        ),
        root_summary={
            "rows_checked": "1",
            "review_positive_count": "1",
            "included_count": "1",
            "missing_candidate_count": "0",
            "bucket_counts": "ppm_gate_fail:1",
            "target_counts": "<script>x</script>:1",
            "product_absence_reason_counts": "",
        },
    )
    output_html = tmp_path / "escaped.html"

    assert report.main([*inputs, "--output-html", str(output_html)]) == 0

    html = output_html.read_text(encoding="utf-8")
    assert "<script>x</script>" not in html
    assert "<b>S1</b>" not in html
    assert "&lt;script&gt;x&lt;/script&gt;" in html
    assert "&lt;b&gt;S1&lt;/b&gt;" in html


def _targeted_inputs(
    tmp_path: Path,
    *,
    reliability_summary: tuple[dict[str, str], ...] | None = None,
    reliability_rows: tuple[dict[str, str], ...] | None = None,
    root_summary: dict[str, str] | None = None,
    root_rows: tuple[dict[str, str], ...] | None = None,
    cross_summary: dict[str, str] | None = None,
    cross_rows: tuple[dict[str, str], ...] | None = None,
    include_cross_rows: bool = False,
) -> list[str]:
    inputs_dir = tmp_path / "diagnostics"
    reliability_summary_path = inputs_dir / "targeted_peak_reliability_summary.tsv"
    reliability_rows_path = inputs_dir / "targeted_peak_reliability_rows.tsv"
    root_summary_path = inputs_dir / "targeted_nl_dropout_root_cause_summary.tsv"
    root_rows_path = inputs_dir / "targeted_nl_dropout_root_cause_rows.tsv"
    cross_summary_path = inputs_dir / "cross_report_evidence_consistency_summary.tsv"
    cross_rows_path = inputs_dir / "cross_report_evidence_consistency_rows.tsv"

    _write_tsv(
        reliability_summary_path,
        reliability_summary
        if reliability_summary is not None
        else (
            _reliability_summary("8-oxodG", eligible=3, review_positive=3, review=2),
            _reliability_summary("CleanTarget", eligible=5, review_positive=0),
        ),
    )
    _write_tsv(
        reliability_rows_path,
        reliability_rows
        if reliability_rows is not None
        else (
            _reliability_row(
                sample="S1",
                target="8-oxodG",
                state="targeted_review_positive",
                area_ratio="0.02",
                risk="plausible_nl_dropout;weak_area_rank",
            ),
            _reliability_row(
                sample="S2",
                target="8-oxodG",
                state="targeted_review_positive",
                area_ratio="0.40",
                risk="plausible_nl_dropout",
            ),
            _reliability_row(
                sample="S3",
                target="CleanTarget",
                state="benchmark_eligible",
                area_ratio="1.0",
            ),
        ),
    )
    _write_tsv(
        root_summary_path,
        (
            root_summary
            if root_summary is not None
            else {
                "rows_checked": "42",
                "review_positive_count": "4",
                "included_count": "4",
                "missing_candidate_count": "0",
                "bucket_counts": (
                    "no_diagnostic_product:2;off_apex_ms2:1;ppm_gate_fail:1"
                ),
                "target_counts": "8-oxodG:3;G:1",
                "product_absence_reason_counts": "product_outside_diagnostic_window:2",
            }
        ),
    )
    _write_tsv(
        root_rows_path,
        root_rows
        if root_rows is not None
        else (
            _root_row(
                sample="S1",
                target="8-oxodG",
                mz="284.099",
                bucket="no_diagnostic_product",
                nearest_loss_ppm="120.2",
            ),
            _root_row(
                sample="S2",
                target="8-oxodG",
                mz="284.099",
                bucket="ppm_gate_fail",
                best_loss_ppm="88.0",
            ),
            _root_row(
                sample="S3",
                target="G",
                mz="284.099",
                bucket="off_apex_ms2",
                apex_delta="0.31",
            ),
        ),
        fieldnames=_ROOT_ROW_COLUMNS,
    )
    _write_tsv(
        cross_summary_path,
        (
            cross_summary
            if cross_summary is not None
            else {
                "rows_checked": "42",
                "consistent_count": "42",
                "mismatch_count": "0",
                "missing_candidate_count": "0",
                "missing_reliability_count": "0",
                "issue_counts": "",
            }
        ),
    )
    args = [
        "--targeted-reliability-summary-tsv",
        str(reliability_summary_path),
        "--targeted-reliability-rows-tsv",
        str(reliability_rows_path),
        "--root-cause-summary-tsv",
        str(root_summary_path),
        "--root-cause-rows-tsv",
        str(root_rows_path),
        "--cross-report-summary-tsv",
        str(cross_summary_path),
        "--run-label",
        "unit test run",
    ]
    if include_cross_rows or cross_rows is not None:
        _write_tsv(
            cross_rows_path,
            cross_rows
            if cross_rows is not None
            else (
                _cross_row(
                    sample="S9",
                    target="ProblemTarget",
                    issue="targeted_review_candidate_suggests_dropout",
                ),
            ),
        )
        args.extend(["--cross-report-rows-tsv", str(cross_rows_path)])
    return args


def _reliability_summary(
    target: str,
    *,
    eligible: int,
    review_positive: int,
    review: int = 0,
) -> dict[str, str]:
    return {
        "target_label": target,
        "role": "Analyte",
        "benchmark_eligible_count": str(eligible),
        "targeted_review_positive_count": str(review_positive),
        "targeted_review_count": str(review),
        "targeted_negative_count": "0",
        "top_risk_reasons": "plausible_nl_dropout;weak_area_rank",
        "known_exception": "",
    }


def _reliability_row(
    *,
    sample: str,
    target: str,
    state: str,
    area_ratio: str = "",
    risk: str = "",
) -> dict[str, str]:
    return {
        "sample_name": sample,
        "target_label": target,
        "role": "Analyte",
        "rt": "12.3",
        "area": "1000",
        "confidence": "LOW",
        "nl": "NL_FAIL",
        "prior_rt": "",
        "prior_source": "",
        "total_severity": "20",
        "quality_flags": "",
        "reliability_state": state,
        "risk_reasons": risk,
        "known_exception": "",
        "target_area_median": "1000",
        "area_to_target_median_ratio": area_ratio,
        "weak_area_threshold_ratio": "0.05",
    }


def _root_row(
    *,
    sample: str,
    target: str,
    mz: str,
    bucket: str,
    best_loss_ppm: str = "",
    nearest_loss_ppm: str = "",
    apex_delta: str = "",
) -> dict[str, str]:
    return {
        "sample_name": sample,
        "target_label": target,
        "target_mz": mz,
        "role": "Analyte",
        "reliability_state": "targeted_review_positive",
        "targeted_risk_reasons": "plausible_nl_dropout",
        "resolver_mode": "local_minimum",
        "selected_candidate_id": f"{sample}|{target}",
        "selected_rt_apex_min": "12.3",
        "selected_raw_score": "25",
        "selected_confidence": "VERY_LOW",
        "proposal_sources": "local_minimum",
        "support_labels": "shape_clean",
        "concern_labels": "nl_fail",
        "quality_flags": "",
        "ms2_present": "TRUE",
        "nl_match": "FALSE",
        "nl_status": "NL_FAIL",
        "best_loss_ppm": best_loss_ppm,
        "best_ms2_scan_rt_min": "12.4",
        "apex_ms2_delta_min": apex_delta,
        "best_product_base_ratio": "",
        "trigger_scan_count": "1",
        "strict_nl_scan_count": "0",
        "ms2_alignment_source": "region",
        "diagnostic_product_absence_reason": "product_outside_diagnostic_window",
        "nearest_product_loss_ppm": nearest_loss_ppm,
        "nearest_product_base_ratio": "0.2",
        "nearest_product_mz": "168.051",
        "root_cause_bucket": bucket,
        "root_cause_reason": f"Reason for {bucket}",
    }


def _cross_row(*, sample: str, target: str, issue: str) -> dict[str, str]:
    return {
        "sample_name": sample,
        "target_label": target,
        "target_mz": "300.123",
        "reliability_state": "targeted_review",
        "targeted_risk_reasons": "plausible_nl_dropout",
        "resolver_mode": "local_minimum",
        "selected_candidate_id": f"{sample}|{target}",
        "selected_rt_apex_min": "12.3",
        "selected_raw_score": "50",
        "selected_confidence": "MEDIUM",
        "targeted_area_to_median_ratio": "0.2",
        "candidate_support_labels": "shape_clean",
        "candidate_concern_labels": "nl_fail",
        "candidate_consistency_labels": "ms1_coherent",
        "consistency_status": "mismatch",
        "issue_type": issue,
        "reason": "Candidate suggests review.",
    }


def _write_tsv(
    path: Path,
    rows: tuple[dict[str, str], ...] | tuple[()] | dict[str, str],
    *,
    fieldnames: tuple[str, ...] = (),
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized = (rows,) if isinstance(rows, dict) else rows
    names: list[str] = list(fieldnames)
    for row in normalized:
        for key in row:
            if key not in names:
                names.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=names, delimiter="\t")
        writer.writeheader()
        writer.writerows(normalized)


_ROOT_ROW_COLUMNS = (
    "sample_name",
    "target_label",
    "target_mz",
    "role",
    "reliability_state",
    "targeted_risk_reasons",
    "resolver_mode",
    "selected_candidate_id",
    "selected_rt_apex_min",
    "selected_raw_score",
    "selected_confidence",
    "proposal_sources",
    "support_labels",
    "concern_labels",
    "quality_flags",
    "ms2_present",
    "nl_match",
    "nl_status",
    "best_loss_ppm",
    "best_ms2_scan_rt_min",
    "apex_ms2_delta_min",
    "best_product_base_ratio",
    "trigger_scan_count",
    "strict_nl_scan_count",
    "ms2_alignment_source",
    "diagnostic_product_absence_reason",
    "nearest_product_loss_ppm",
    "nearest_product_base_ratio",
    "nearest_product_mz",
    "root_cause_bucket",
    "root_cause_reason",
)
