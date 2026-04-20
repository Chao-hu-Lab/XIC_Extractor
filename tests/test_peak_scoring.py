import numpy as np
import pytest

from xic_extractor.peak_scoring import local_sn_severity, symmetry_severity


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


def _make_trace(
    peak_height: float, noise_std: float = 0.05, n: int = 400, seed: int = 0
) -> np.ndarray:
    rng = np.random.default_rng(seed)
    x = np.arange(n)
    peak = peak_height * np.exp(-((x - n / 2) ** 2) / (2 * 5**2))
    noise = rng.normal(0.0, noise_std, n)
    return peak + noise + 1.0


def test_local_sn_pass_high_peak() -> None:
    y = _make_trace(peak_height=10.0, noise_std=0.05)
    sev, label = local_sn_severity(y, apex_index=200, dirty_matrix=False)
    assert sev == 0
    assert label == "local_sn"


def test_local_sn_minor_low_peak() -> None:
    y = _make_trace(peak_height=0.03, noise_std=0.05)
    sev, _ = local_sn_severity(y, apex_index=200, dirty_matrix=False)
    assert sev == 1


def test_local_sn_major_no_peak() -> None:
    y = _make_trace(peak_height=0.0, noise_std=0.05)
    sev, _ = local_sn_severity(y, apex_index=200, dirty_matrix=False)
    assert sev == 2


def test_dirty_matrix_relaxes_threshold() -> None:
    y = _make_trace(peak_height=0.3, noise_std=0.05)
    sev_default, _ = local_sn_severity(y, apex_index=200, dirty_matrix=False)
    sev_dirty, _ = local_sn_severity(y, apex_index=200, dirty_matrix=True)
    assert sev_dirty <= sev_default


def test_local_sn_invalid_trace_is_major() -> None:
    y = _make_trace(peak_height=10.0)
    y[200] = np.nan
    sev, label = local_sn_severity(y, apex_index=200, dirty_matrix=False)
    assert sev == 2
    assert label == "local_sn"
