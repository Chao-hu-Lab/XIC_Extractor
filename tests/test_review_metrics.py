import pytest

from xic_extractor.output.detection import is_accepted_row_detection
from xic_extractor.output.review_metrics import build_review_metrics


def test_review_metrics_separates_detection_from_flagged_workload() -> None:
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
            "RT": "1.1",
            "Area": "110",
            "NL": "NL_FAIL",
            "Confidence": "LOW",
        },
        {
            "SampleName": "S3",
            "Target": "A",
            "RT": "1.2",
            "Area": "120",
            "NL": "NO_MS2",
            "Confidence": "MEDIUM",
        },
    ]
    review_rows = [
        {"Priority": "1", "Sample": "S2", "Target": "A", "Status": "Review"},
        {"Priority": "2", "Sample": "S3", "Target": "A", "Status": "Check"},
    ]

    metrics = build_review_metrics(
        rows,
        diagnostics=[],
        review_rows=review_rows,
        count_no_ms2_as_detected=False,
    )

    target = metrics.targets["A"]
    assert target.detected == 1
    assert target.total == 3
    assert target.detected_percent == "33%"
    assert target.flagged_rows == 2
    assert target.flagged_percent == "67%"
    assert target.ms2_nl_flags == 2
    assert target.low_confidence_rows == 1
    assert metrics.heatmap[("A", "S1")] == "clean-detected"
    assert metrics.heatmap[("A", "S2")] == "not-detected"
    assert metrics.heatmap[("A", "S3")] == "not-detected"


def test_review_metrics_honors_count_no_ms2_as_detected() -> None:
    rows = [
        {
            "SampleName": "S1",
            "Target": "A",
            "RT": "1.0",
            "Area": "100",
            "NL": "NO_MS2",
            "Confidence": "HIGH",
        },
    ]

    strict = build_review_metrics(
        rows,
        diagnostics=[],
        review_rows=[],
        count_no_ms2_as_detected=False,
    )
    permissive = build_review_metrics(
        rows,
        diagnostics=[],
        review_rows=[],
        count_no_ms2_as_detected=True,
    )

    assert strict.targets["A"].detected == 0
    assert permissive.targets["A"].detected == 1


def test_review_metrics_do_not_count_very_low_rows_as_detected() -> None:
    rows = [
        {
            "SampleName": "S1",
            "Target": "A",
            "RT": "1.0",
            "Area": "100",
            "NL": "OK",
            "Confidence": "VERY_LOW",
        },
    ]

    metrics = build_review_metrics(
        rows,
        diagnostics=[],
        review_rows=[{"Priority": "1", "Sample": "S1", "Target": "A"}],
        count_no_ms2_as_detected=False,
    )

    assert metrics.targets["A"].detected == 0
    assert metrics.targets["A"].detected_percent == "0%"
    assert metrics.heatmap[("A", "S1")] == "not-detected"


def test_review_metrics_do_not_count_non_positive_area_as_detected() -> None:
    rows = [
        {
            "SampleName": "S1",
            "Target": "A",
            "RT": "1.0",
            "Area": "100",
            "NL": "OK",
            "Confidence": "LOW",
        },
        {
            "SampleName": "S2",
            "Target": "A",
            "RT": "1.1",
            "Area": "0",
            "NL": "OK",
            "Confidence": "LOW",
        },
        {
            "SampleName": "S3",
            "Target": "A",
            "RT": "1.2",
            "Area": "-5",
            "NL": "OK",
            "Confidence": "LOW",
        },
    ]

    metrics = build_review_metrics(
        rows,
        diagnostics=[],
        review_rows=[],
        count_no_ms2_as_detected=False,
    )

    assert metrics.targets["A"].detected == 1
    assert metrics.targets["A"].detected_percent == "33%"
    assert metrics.heatmap[("A", "S1")] == "clean-detected"
    assert metrics.heatmap[("A", "S2")] == "not-detected"
    assert metrics.heatmap[("A", "S3")] == "not-detected"


def test_review_metrics_do_not_count_nl_fail_or_very_low_as_detected() -> None:
    rows = [
        {
            "SampleName": "S1",
            "Target": "A",
            "RT": "1.0",
            "Area": "100",
            "NL": "NL_FAIL",
            "Confidence": "LOW",
        },
        {
            "SampleName": "S2",
            "Target": "A",
            "RT": "1.1",
            "Area": "110",
            "NL": "OK",
            "Confidence": "VERY_LOW",
        },
        {
            "SampleName": "S3",
            "Target": "A",
            "RT": "1.2",
            "Area": "120",
            "NL": "OK",
            "Confidence": "LOW",
        },
        {
            "SampleName": "S4",
            "Target": "A",
            "RT": "1.3",
            "Area": "0",
            "NL": "OK",
            "Confidence": "LOW",
        },
    ]

    metrics = build_review_metrics(
        rows,
        diagnostics=[],
        review_rows=[],
        count_no_ms2_as_detected=False,
    )

    assert metrics.targets["A"].detected == 1
    assert metrics.targets["A"].detected_percent == "25%"
    assert metrics.heatmap[("A", "S1")] == "not-detected"
    assert metrics.heatmap[("A", "S2")] == "not-detected"
    assert metrics.heatmap[("A", "S3")] == "clean-detected"
    assert metrics.heatmap[("A", "S4")] == "not-detected"


@pytest.mark.parametrize(
    ("row", "count_no_ms2_as_detected", "expected"),
    [
        (
            {"RT": "1.0", "Area": "100", "NL": "OK", "Confidence": "HIGH"},
            False,
            True,
        ),
        (
            {
                "RT": "1.0",
                "Area": "100",
                "NL": "WARN_LOW_PRODUCT",
                "Confidence": "LOW",
            },
            False,
            True,
        ),
        (
            {"RT": "1.0", "Area": "100", "NL": "OK", "Confidence": "VERY_LOW"},
            False,
            False,
        ),
        (
            {"RT": "1.0", "Area": "100", "NL": "NL_FAIL", "Confidence": "LOW"},
            False,
            False,
        ),
        (
            {"RT": "1.0", "Area": "100", "NL": "NO_MS2", "Confidence": "LOW"},
            False,
            False,
        ),
        (
            {"RT": "1.0", "Area": "100", "NL": "NO_MS2", "Confidence": "LOW"},
            True,
            True,
        ),
        (
            {"RT": "1.0", "Area": "0", "NL": "OK", "Confidence": "LOW"},
            False,
            False,
        ),
        (
            {"RT": "ND", "Area": "100", "NL": "OK", "Confidence": "HIGH"},
            False,
            False,
        ),
    ],
)
def test_accepted_detection_decision_table(
    row: dict[str, str],
    count_no_ms2_as_detected: bool,
    expected: bool,
) -> None:
    assert is_accepted_row_detection(row, count_no_ms2_as_detected) is expected
