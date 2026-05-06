from pathlib import Path

from xic_extractor.output.review_report import write_review_report


def test_write_review_report_contains_batch_counts_target_health_and_legend(
    tmp_path: Path,
) -> None:
    rows = [
        {
            "SampleName": "S1",
            "Target": "A",
            "RT": "1.0",
            "Area": "100",
            "NL": "OK",
            "Confidence": "HIGH",
        },
        {
            "SampleName": "S2",
            "Target": "A",
            "RT": "ND",
            "Area": "ND",
            "NL": "NL_FAIL",
            "Confidence": "LOW",
        },
    ]
    review_rows = [
        {
            "Priority": "1",
            "Sample": "S2",
            "Target": "A",
            "Status": "Review",
            "Why": "NL support failed",
            "Action": "Check MS2 / NL evidence near selected RT",
            "Issue Count": "1",
            "Evidence": "strict observed neutral loss missing",
        }
    ]

    path = write_review_report(
        tmp_path / "review_report.html",
        rows,
        diagnostics=[],
        review_rows=review_rows,
        count_no_ms2_as_detected=False,
    )

    html = path.read_text(encoding="utf-8")
    assert "XIC Review Report" in html
    assert "Flagged Rows" in html
    assert "Detected %" in html
    assert "Flagged %" in html
    assert "clean-detected" in html
    assert "not-detected" in html
    assert "Review Queue" in html


def test_write_review_report_escapes_user_controlled_text(tmp_path: Path) -> None:
    rows = [
        {
            "SampleName": "<script>alert(1)</script>",
            "Target": "=A",
            "RT": "1",
            "Area": "1",
            "NL": "OK",
            "Confidence": "HIGH",
        }
    ]
    review_rows = [
        {
            "Priority": "1",
            "Sample": "<script>alert(1)</script>",
            "Target": "=A",
            "Status": "Review",
            "Why": "<b>bad</b>",
            "Action": "Check",
            "Issue Count": "1",
            "Evidence": "<img src=x>",
        }
    ]

    path = write_review_report(
        tmp_path / "review_report.html",
        rows,
        diagnostics=[],
        review_rows=review_rows,
        count_no_ms2_as_detected=False,
    )

    html = path.read_text(encoding="utf-8")
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "&lt;b&gt;bad&lt;/b&gt;" in html
    assert "&lt;img src=x&gt;" in html


def test_write_review_report_omits_clean_targets_from_flag_burden(
    tmp_path: Path,
) -> None:
    rows = [
        {
            "SampleName": "S1",
            "Target": "Clean",
            "RT": "1",
            "Area": "1",
            "NL": "OK",
            "Confidence": "HIGH",
        }
    ]

    path = write_review_report(
        tmp_path / "review_report.html",
        rows,
        diagnostics=[],
        review_rows=[],
        count_no_ms2_as_detected=False,
    )

    html = path.read_text(encoding="utf-8")
    assert "<section><h2>Flag Burden By Target</h2>" in html
    assert '<td colspan="4">None</td>' in html
    assert "<td>Clean</td><td>0</td>" not in html


def test_review_report_contains_visual_detection_and_flag_charts(
    tmp_path: Path,
) -> None:
    rows = [
        {
            "SampleName": "S1",
            "Target": "A",
            "RT": "1.0",
            "Area": "100",
            "NL": "OK",
            "Confidence": "HIGH",
        },
        {
            "SampleName": "S2",
            "Target": "A",
            "RT": "ND",
            "Area": "ND",
            "NL": "ND",
            "Confidence": "LOW",
        },
        {
            "SampleName": "S1",
            "Target": "B",
            "RT": "2.0",
            "Area": "200",
            "NL": "OK",
            "Confidence": "HIGH",
        },
        {
            "SampleName": "S2",
            "Target": "B",
            "RT": "2.1",
            "Area": "210",
            "NL": "NL_FAIL",
            "Confidence": "LOW",
        },
    ]
    review_rows = [
        {
            "Priority": "1",
            "Sample": "S2",
            "Target": "B",
            "Status": "Review",
            "Why": "NL support failed",
            "Action": "Check",
            "Issue Count": "1",
            "Evidence": "NL_FAIL",
        },
    ]

    path = write_review_report(
        tmp_path / "review_report.html",
        rows,
        diagnostics=[],
        review_rows=review_rows,
        count_no_ms2_as_detected=False,
    )

    html = path.read_text(encoding="utf-8")
    assert "<h2>Detection Rate By Target</h2>" in html
    assert "<h2>Flag Burden By Target</h2>" in html
    assert 'class="bar-fill detection"' in html
    assert 'class="bar-fill flagged"' in html
    assert "A</td><td>50%</td>" in html
    assert "B</td><td>50%</td>" not in html


def test_review_report_draws_istd_rt_injection_trend(tmp_path: Path) -> None:
    rows = [
        {
            "SampleName": "S1",
            "Target": "d3-A",
            "Role": "ISTD",
            "RT": "8.90",
            "Area": "100",
            "NL": "OK",
            "Confidence": "HIGH",
        },
        {
            "SampleName": "S2",
            "Target": "d3-A",
            "Role": "ISTD",
            "RT": "9.10",
            "Area": "100",
            "NL": "OK",
            "Confidence": "HIGH",
        },
        {
            "SampleName": "S1",
            "Target": "A",
            "Role": "Analyte",
            "RT": "9.00",
            "Area": "50",
            "NL": "OK",
            "Confidence": "HIGH",
        },
    ]

    path = write_review_report(
        tmp_path / "review_report.html",
        rows,
        diagnostics=[],
        review_rows=[],
        count_no_ms2_as_detected=False,
        injection_order={"S1": 1, "S2": 2},
    )

    html = path.read_text(encoding="utf-8")
    assert "<h2>ISTD RT Injection Trend</h2>" in html
    assert "<svg" in html
    assert "d3-A" in html
    assert "RT 8.9000 min" in html
    assert "Injection 1" in html


def test_review_report_omits_istd_trend_without_injection_order(
    tmp_path: Path,
) -> None:
    rows = [
        {
            "SampleName": "S1",
            "Target": "d3-A",
            "Role": "ISTD",
            "RT": "8.90",
            "Area": "100",
            "NL": "OK",
            "Confidence": "HIGH",
        },
    ]

    path = write_review_report(
        tmp_path / "review_report.html",
        rows,
        diagnostics=[],
        review_rows=[],
        count_no_ms2_as_detected=False,
    )

    html = path.read_text(encoding="utf-8")
    assert "ISTD RT Injection Trend" not in html


def test_review_report_draws_istd_rt_injection_trend_for_flat_rt(
    tmp_path: Path,
) -> None:
    rows = [
        {
            "SampleName": "S1",
            "Target": "d3-A",
            "Role": "ISTD",
            "RT": "8.90",
            "Area": "100",
            "NL": "OK",
            "Confidence": "HIGH",
        },
        {
            "SampleName": "S2",
            "Target": "d3-A",
            "Role": "ISTD",
            "RT": "8.90",
            "Area": "100",
            "NL": "OK",
            "Confidence": "HIGH",
        },
    ]

    path = write_review_report(
        tmp_path / "review_report.html",
        rows,
        diagnostics=[],
        review_rows=[],
        count_no_ms2_as_detected=False,
        injection_order={"S1": 1, "S2": 2},
    )

    html = path.read_text(encoding="utf-8")
    assert "<h2>ISTD RT Injection Trend</h2>" in html
    assert "<svg" in html
    assert "RT 8.9000 min" in html


def test_review_report_draws_separate_rt_trend_line_per_istd(
    tmp_path: Path,
) -> None:
    rows = [
        {
            "SampleName": "S1",
            "Target": "d3-A",
            "Role": "ISTD",
            "RT": "8.90",
            "Area": "100",
            "NL": "OK",
            "Confidence": "HIGH",
        },
        {
            "SampleName": "S2",
            "Target": "d3-A",
            "Role": "ISTD",
            "RT": "9.10",
            "Area": "100",
            "NL": "OK",
            "Confidence": "HIGH",
        },
        {
            "SampleName": "S1",
            "Target": "d3-B",
            "Role": "ISTD",
            "RT": "12.20",
            "Area": "100",
            "NL": "OK",
            "Confidence": "HIGH",
        },
        {
            "SampleName": "S2",
            "Target": "d3-B",
            "Role": "ISTD",
            "RT": "12.40",
            "Area": "100",
            "NL": "OK",
            "Confidence": "HIGH",
        },
    ]

    path = write_review_report(
        tmp_path / "review_report.html",
        rows,
        diagnostics=[],
        review_rows=[],
        count_no_ms2_as_detected=False,
        injection_order={"S1": 1, "S2": 2},
    )

    html = path.read_text(encoding="utf-8")
    assert html.count('class="trend-line"') == 2


def test_review_report_heatmap_sorts_low_detection_targets_first(
    tmp_path: Path,
) -> None:
    rows = [
        {
            "SampleName": "S1",
            "Target": "High",
            "RT": "1",
            "Area": "1",
            "NL": "OK",
            "Confidence": "HIGH",
        },
        {
            "SampleName": "S2",
            "Target": "High",
            "RT": "2",
            "Area": "1",
            "NL": "OK",
            "Confidence": "HIGH",
        },
        {
            "SampleName": "S1",
            "Target": "Low",
            "RT": "ND",
            "Area": "ND",
            "NL": "ND",
            "Confidence": "LOW",
        },
        {
            "SampleName": "S2",
            "Target": "Low",
            "RT": "2",
            "Area": "1",
            "NL": "OK",
            "Confidence": "HIGH",
        },
    ]

    path = write_review_report(
        tmp_path / "review_report.html",
        rows,
        diagnostics=[],
        review_rows=[],
        count_no_ms2_as_detected=False,
    )

    html = path.read_text(encoding="utf-8")
    assert html.index("<th>Low</th>") < html.index("<th>High</th>")
