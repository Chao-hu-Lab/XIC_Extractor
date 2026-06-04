from xic_extractor.output.schema import (
    DIAGNOSTIC_HEADERS,
    LONG_ADVANCED_HEADERS,
    LONG_HEADERS,
    SCORE_BREAKDOWN_HEADERS,
    TARGETED_PRODUCT_PROJECTION_HEADERS,
)


def test_long_schema_has_projection_columns() -> None:
    assert len(LONG_HEADERS) == 25
    assert LONG_HEADERS[0] == "SampleName"
    assert LONG_HEADERS[13] == "Reason"
    assert LONG_HEADERS[-11:] == TARGETED_PRODUCT_PROJECTION_HEADERS
    assert set(TARGETED_PRODUCT_PROJECTION_HEADERS) <= LONG_ADVANCED_HEADERS


def test_diagnostic_schema_has_4_columns() -> None:
    assert DIAGNOSTIC_HEADERS == ("SampleName", "Target", "Issue", "Reason")


def test_score_breakdown_schema_has_projection_columns() -> None:
    assert len(SCORE_BREAKDOWN_HEADERS) == 28
    assert SCORE_BREAKDOWN_HEADERS[:8] == (
        "SampleName",
        "Target",
        "Final Confidence",
        "Detection Counted",
        "Product State",
        "Review State",
        "Projection Reason",
        "Legacy Authority Status",
    )
