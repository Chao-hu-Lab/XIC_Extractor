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


def test_write_review_report_omits_clean_targets_from_top_flagged(
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
    assert '<section><h2>Top Flagged Targets</h2>' in html
    assert '<td colspan="4">None</td>' in html
    assert "<td>Clean</td><td>0</td>" not in html
