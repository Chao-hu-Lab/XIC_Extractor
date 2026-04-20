import pytest

from xic_extractor.peak_scoring import symmetry_severity


@pytest.mark.parametrize(
    ("ratio", "expected"),
    [
        (1.0, 0),
        (0.6, 0),
        (1.8, 0),
        (0.4, 1),
        (2.5, 1),
        (0.2, 2),
        (4.0, 2),
    ],
)
def test_symmetry_severity(ratio: float, expected: int) -> None:
    severity, label = symmetry_severity(ratio)
    assert severity == expected
    assert label == "symmetry"
