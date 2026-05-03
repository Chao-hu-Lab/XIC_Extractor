from xic_extractor.output.schema import (
    DIAGNOSTIC_HEADERS,
    LONG_HEADERS,
    SCORE_BREAKDOWN_HEADERS,
)


def test_long_schema_has_14_columns() -> None:
    assert len(LONG_HEADERS) == 14
    assert LONG_HEADERS[0] == "SampleName"
    assert LONG_HEADERS[-1] == "Reason"


def test_diagnostic_schema_has_4_columns() -> None:
    assert DIAGNOSTIC_HEADERS == ("SampleName", "Target", "Issue", "Reason")


def test_score_breakdown_schema_has_15_columns() -> None:
    assert len(SCORE_BREAKDOWN_HEADERS) == 15
