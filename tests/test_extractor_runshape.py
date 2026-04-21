from xic_extractor.extractor import RunOutput


def test_run_output_has_expected_fields() -> None:
    assert {"file_results", "diagnostics"}.issubset(
        RunOutput.__dataclass_fields__.keys()
    )
