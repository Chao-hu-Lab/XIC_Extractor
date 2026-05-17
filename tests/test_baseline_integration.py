import numpy as np
import pytest

from xic_extractor.peak_detection.baseline import (
    bounded_trace_interval,
    integrate_linear_edge_baseline,
)


def test_linear_edge_baseline_subtracts_sloped_local_baseline() -> None:
    rt = np.asarray([0.0, 0.1, 0.2, 0.3, 0.4])
    intensity = np.asarray([10.0, 25.0, 50.0, 35.0, 20.0])

    result = integrate_linear_edge_baseline(intensity, rt, 0, 5)

    assert result.baseline_type == "linear_edge"
    assert result.area_baseline_corrected == pytest.approx(390.0)
    assert result.area_uncertainty is not None
    assert result.baseline_score is not None
    assert 0.0 <= result.baseline_score <= 1.0


def test_linear_edge_baseline_rejects_mismatched_arrays() -> None:
    with pytest.raises(ValueError, match="same length"):
        integrate_linear_edge_baseline(
            np.asarray([1.0, 2.0]),
            np.asarray([0.0]),
            0,
            2,
        )


def test_bounded_trace_interval_matches_integration_interval_contract() -> None:
    assert bounded_trace_interval(2, 3, 3) == (1, 3)
    assert bounded_trace_interval(-5, 1, 4) == (0, 2)

    with pytest.raises(ValueError, match="at least 2"):
        bounded_trace_interval(0, 1, 1)
