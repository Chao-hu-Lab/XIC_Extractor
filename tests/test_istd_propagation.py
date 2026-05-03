from xic_extractor.output.messages import istd_confidence_note


def test_note_none_when_high() -> None:
    assert istd_confidence_note("HIGH") is None


def test_note_present_when_low() -> None:
    note = istd_confidence_note("LOW")
    assert note is not None
    assert "LOW" in note


def test_note_present_when_very_low() -> None:
    note = istd_confidence_note("VERY_LOW")
    assert note is not None
    assert "VERY_LOW" in note
