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
    assert "Review Focus" in html
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
    assert 'class="target-bar-chart detection-chart"' in html
    assert 'class="target-bar-chart flag-chart"' in html
    assert 'class="target-bar detection-bar"' in html
    assert 'class="target-bar flag-bar"' in html
    assert "width:720px;max-width:100%;height:auto" in html
    assert '<svg class="target-bar-chart detection-chart" width="720"' in html
    assert '<svg class="target-bar-chart flag-chart" width="720"' in html
    assert ".bar-table{table-layout:fixed}" in html
    assert '<details class="chart-details">' in html
    assert "<summary>Detection rate table</summary>" in html
    assert "<summary>Flag burden table</summary>" in html
    assert (
        '<colgroup><col class="target-col"><col class="percent-col">'
        '<col class="bar-col"></colgroup>'
    ) in html
    assert (
        '<colgroup><col class="target-col"><col class="count-col">'
        '<col class="percent-col"><col class="bar-col"></colgroup>'
    ) in html
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
    assert "Internal Standard (ISTD) Retention Time Trend" in html
    assert "Injection Order" in html
    assert "Retention Time (min)" in html
    assert 'class="trend-svg-legend"' in html
    assert 'class="trend-axis-label trend-x-label"' in html
    assert 'class="trend-axis-label trend-y-label"' in html
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


def test_review_report_rt_trend_includes_qc_markers_bands_and_legend(
    tmp_path: Path,
) -> None:
    rows = [
        {
            "SampleName": "QC1",
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
            "SampleName": "QC1",
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
        injection_order={"QC1": 1, "S2": 2},
    )

    html = path.read_text(encoding="utf-8")
    assert html.count('class="trend-band"') == 2
    assert html.count('class="trend-qc"') == 1
    assert "QC Injection" in html
    assert "Acceptable Range (Median +/- 0.5 min)" in html
    assert 'data-target="d3-A"' in html
    assert 'data-target="d3-B"' in html


def test_review_report_draws_istd_area_cv_table_and_normalized_chart(
    tmp_path: Path,
) -> None:
    rows = [
        {
            "SampleName": "QC1",
            "Target": "d3-A",
            "Role": "ISTD",
            "RT": "8.90",
            "Area": "90",
            "NL": "OK",
            "Confidence": "HIGH",
        },
        {
            "SampleName": "S2",
            "Target": "d3-A",
            "Role": "ISTD",
            "RT": "9.00",
            "Area": "100",
            "NL": "OK",
            "Confidence": "HIGH",
        },
        {
            "SampleName": "S3",
            "Target": "d3-A",
            "Role": "ISTD",
            "RT": "9.10",
            "Area": "110",
            "NL": "OK",
            "Confidence": "HIGH",
        },
        {
            "SampleName": "QC1",
            "Target": "d3-B",
            "Role": "ISTD",
            "RT": "12.00",
            "Area": "1000",
            "NL": "OK",
            "Confidence": "HIGH",
        },
        {
            "SampleName": "S2",
            "Target": "d3-B",
            "Role": "ISTD",
            "RT": "12.10",
            "Area": "1100",
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
        injection_order={"QC1": 1, "S2": 2, "S3": 3},
    )

    html = path.read_text(encoding="utf-8")
    assert "<h2>ISTD Area Injection Stability</h2>" in html
    assert (
        "Detected counts positive numeric ISTD area rows; total counts ISTD rows "
        "with injection order."
    ) in html
    assert "<th>Mean Area</th><th>SD</th><th>CV%</th>" in html
    assert (
        "<td>d3-A</td><td>3/3</td><td>1.00e+02</td><td>1.00e+01</td>"
        "<td>10.0%</td>"
    ) in html
    assert (
        "<td>d3-B</td><td>2/2</td><td>1.05e+03</td><td>7.07e+01</td>"
        "<td>6.7%</td>"
    ) in html
    assert '<svg class="area-stability-svg"' in html
    assert '<div class="area-stability-layout">' in html
    assert '<div class="area-stability-chart">' in html
    assert '<div class="area-stability-table-wrap">' in html
    assert ".area-stability-table-wrap{max-width:940px}" in html
    assert ".area-stability-table{width:100%;min-width:900px;" in html
    assert html.index('<div class="area-stability-chart">') < html.index(
        '<table class="area-stability-table">'
    )
    assert "Normalized Area (%)" in html
    assert "Injection Order" in html
    assert "d3-A: Injection 1, area 90.0, normalized 90.0%" in html
    assert html.count('class="area-point"') == 5
    assert html.count('class="area-qc"') == 1
    area_section = html.split("<h2>ISTD Area Injection Stability</h2>", 1)[1].split(
        "</section>",
        1,
    )[0]
    assert "QC Injection" in area_section
    assert "Acceptable Range" not in area_section


def test_review_report_area_cv_excludes_invalid_area_values(
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
            "RT": "8.95",
            "Area": "ND",
            "NL": "ND",
            "Confidence": "LOW",
        },
        {
            "SampleName": "S3",
            "Target": "d3-A",
            "Role": "ISTD",
            "RT": "9.00",
            "Area": "",
            "NL": "ND",
            "Confidence": "LOW",
        },
        {
            "SampleName": "S4",
            "Target": "d3-A",
            "Role": "ISTD",
            "RT": "9.05",
            "Area": "not-a-number",
            "NL": "ND",
            "Confidence": "LOW",
        },
        {
            "SampleName": "S5",
            "Target": "d3-A",
            "Role": "ISTD",
            "RT": "9.10",
            "Area": "0",
            "NL": "ND",
            "Confidence": "LOW",
        },
        {
            "SampleName": "S6",
            "Target": "d3-A",
            "Role": "ISTD",
            "RT": "9.15",
            "Area": "120",
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
        injection_order={f"S{i}": i for i in range(1, 7)},
    )

    html = path.read_text(encoding="utf-8")
    assert (
        "<td>d3-A</td><td>2/6</td><td>1.10e+02</td><td>1.41e+01</td>"
        "<td>12.9%</td>"
    ) in html
    assert html.count('class="area-point"') == 2


def test_review_report_area_cv_uses_na_with_less_than_two_valid_points(
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
            "RT": "8.95",
            "Area": "ND",
            "NL": "ND",
            "Confidence": "LOW",
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
    assert "<td>d3-A</td><td>1/2</td><td>1.00e+02</td><td>NA</td><td>NA</td>" in html
    assert '<svg class="area-stability-svg"' not in html


def test_review_report_omits_istd_area_cv_without_injection_order(
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
            "RT": "9.00",
            "Area": "110",
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
    assert "ISTD Area Injection Stability" not in html


def test_review_report_area_stability_escapes_user_controlled_text(
    tmp_path: Path,
) -> None:
    rows = [
        {
            "SampleName": "S<1>",
            "Target": "<d3-A>",
            "Role": "ISTD",
            "RT": "8.90",
            "Area": "90",
            "NL": "OK",
            "Confidence": "HIGH",
        },
        {
            "SampleName": "S<2>",
            "Target": "<d3-A>",
            "Role": "ISTD",
            "RT": "9.00",
            "Area": "110",
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
        injection_order={"S<1>": 1, "S<2>": 2},
    )

    html = path.read_text(encoding="utf-8")
    assert "<td><d3-A></td>" not in html
    assert "&lt;d3-A&gt;" in html
    assert "S&lt;1&gt;" in html


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
    assert html.index('class="heatmap-target">Low</span>') < html.index(
        'class="heatmap-target">High</span>'
    )


def test_review_report_uses_at_a_glance_focus_and_compact_heatmap(
    tmp_path: Path,
) -> None:
    rows = [
        {
            "SampleName": "S1",
            "Target": "A",
            "RT": "1",
            "Area": "1",
            "NL": "OK",
            "Confidence": "HIGH",
            "Role": "Analyte",
        },
        {
            "SampleName": "S2",
            "Target": "A",
            "RT": "ND",
            "Area": "ND",
            "NL": "ND",
            "Confidence": "LOW",
            "Role": "Analyte",
        },
        {
            "SampleName": "S1",
            "Target": "B",
            "RT": "2",
            "Area": "1",
            "NL": "NL_FAIL",
            "Confidence": "LOW",
            "Role": "Analyte",
        },
        {
            "SampleName": "S1",
            "Target": "d3-A",
            "RT": "1.1",
            "Area": "10",
            "NL": "OK",
            "Confidence": "HIGH",
            "Role": "ISTD",
        },
        {
            "SampleName": "S2",
            "Target": "d3-A",
            "RT": "1.2",
            "Area": "11",
            "NL": "OK",
            "Confidence": "HIGH",
            "Role": "ISTD",
        },
    ]
    review_rows = [
        {
            "Priority": "1",
            "Sample": "S2",
            "Target": "A",
            "Status": "Review",
            "Why": "ND",
            "Action": "Open workbook",
            "Issue Count": "1",
            "Evidence": "missing peak",
        },
        {
            "Priority": "2",
            "Sample": "S1",
            "Target": "B",
            "Status": "Review",
            "Why": "NL",
            "Action": "Open workbook",
            "Issue Count": "1",
            "Evidence": "NL fail",
        },
    ]

    path = write_review_report(
        tmp_path / "review_report.html",
        rows,
        diagnostics=[],
        review_rows=review_rows,
        count_no_ms2_as_detected=False,
        injection_order={"S1": 1, "S2": 2},
    )

    html = path.read_text(encoding="utf-8")
    assert "<h2>Review Focus</h2>" in html
    assert "Top Targets" in html
    assert "Top Samples" in html
    assert 'class="focus-grid"' in html
    assert 'class="compact-heatmap"' in html
    assert "display:inline-block" in html
    assert 'class="heat-cell flagged-detected"' in html
    assert 'class="heat-cell not-detected"' in html
    assert "#1f9d55" in html
    assert "#f59e0b" in html
    assert "#cbd5e1" in html
    assert "#d1242f" in html
    assert "#fff8c5" not in html
    assert "#ffebe9" not in html
    assert "<details class=\"review-details\">" in html
    assert "<summary>Review Queue details" in html
    assert "Excel workbook remains the row-level source" in html
    assert html.index("<h2>Review Focus</h2>") < html.index(
        "<h2>Detection / Flag Map</h2>"
    )
    assert html.index("<h2>Detection / Flag Map</h2>") < html.index(
        "<h2>Detection Rate By Target</h2>"
    )
    assert html.index("<h2>Detection Rate By Target</h2>") < html.index(
        "<h2>ISTD RT Injection Trend</h2>"
    )


def test_review_report_keeps_full_batch_heatmap_on_one_row_per_target(
    tmp_path: Path,
) -> None:
    samples = [f"S{i:02d}" for i in range(1, 86)]
    rows = [
        {
            "SampleName": sample,
            "Target": "A",
            "RT": "1",
            "Area": "1",
            "NL": "OK",
            "Confidence": "HIGH",
        }
        for sample in samples
    ]

    path = write_review_report(
        tmp_path / "review_report.html",
        rows,
        diagnostics=[],
        review_rows=[],
        count_no_ms2_as_detected=False,
    )

    html = path.read_text(encoding="utf-8")
    assert "flex-wrap:nowrap" in html
    assert "box-sizing:border-box" in html
    assert "--sample-count:85" in html
    assert "--heat-cell-size:8px" in html
    assert "--heat-cell-gap:2px" in html
    assert html.count('class="heat-cell clean-detected"') == 85
    assert html.count('class="heatmap-target">A</span>') == 1
