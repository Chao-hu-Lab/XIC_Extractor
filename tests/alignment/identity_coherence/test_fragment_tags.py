import pytest

from xic_extractor.alignment.identity_coherence.tags import (
    format_fragment_tags,
    has_fragment_tags,
    normalize_fragment_tags,
)


@pytest.mark.parametrize(
    ("raw_tags", "expected"),
    [
        ("dR;MeR", ("MeR", "dR")),
        ("dR|MeR", ("MeR", "dR")),
        ("dR,MeR", ("MeR", "dR")),
        (["dR", "MeR"], ("MeR", "dR")),
        (("dR", "MeR"), ("MeR", "dR")),
        ({"dR", "MeR"}, ("MeR", "dR")),
    ],
)
def test_normalize_fragment_tags_accepts_supported_shapes(raw_tags, expected):
    tags, flags = normalize_fragment_tags(raw_tags)

    assert tags == expected
    assert flags == ()


def test_normalize_fragment_tags_preserves_case_variants():
    tags, flags = normalize_fragment_tags("base;BASE")

    assert tags == ("BASE", "base")
    assert flags == ("fragment_tag_case_variant_seen",)


def test_format_fragment_tags_uses_semicolon():
    assert format_fragment_tags(("MeR", "dR")) == "MeR;dR"


def test_has_fragment_tags_treats_empty_values_as_absent():
    assert has_fragment_tags(None) is False
    assert has_fragment_tags("") is False
    assert has_fragment_tags(["", "  "]) is False
    assert has_fragment_tags("dR") is True


def test_normalize_fragment_tags_ignores_empty_separator_slots():
    tags, flags = normalize_fragment_tags("dR;;MeR")

    assert tags == ("MeR", "dR")
    assert flags == ()
