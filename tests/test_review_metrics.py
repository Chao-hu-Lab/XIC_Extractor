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
    assert target.detected == 2
    assert target.total == 3
    assert target.detected_percent == "67%"
    assert target.flagged_rows == 2
    assert target.flagged_percent == "67%"
    assert target.ms2_nl_flags == 2
    assert target.low_confidence_rows == 1
    assert metrics.heatmap[("A", "S1")] == "clean-detected"
    assert metrics.heatmap[("A", "S2")] == "flagged-detected"
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
