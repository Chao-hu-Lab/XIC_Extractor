import numpy as np
import pytest

from xic_extractor.peak_detection.baseline import (
    bounded_trace_interval,
    integrate_linear_edge_baseline,
)
from xic_extractor.peak_detection.integration_audit import (
    build_cell_integration_audit_summary,
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


def test_cell_integration_audit_reports_baseline_corrected_area() -> None:
    rt = np.asarray([0.0, 0.1, 0.2, 0.3, 0.4])
    intensity = np.asarray([10.0, 25.0, 50.0, 35.0, 20.0])

    summary = build_cell_integration_audit_summary(
        rt,
        intensity,
        peak_start_rt=0.0,
        peak_end_rt=0.4,
        raw_area=1200.0,
    )

    assert summary.raw_area == pytest.approx(1200.0)
    assert summary.area_baseline_corrected == pytest.approx(390.0)
    assert summary.baseline_type == "linear_edge"
    assert summary.baseline_fraction == pytest.approx(390.0 / 1200.0)
    assert summary.integration_scan_count == 5


def test_cell_integration_audit_flags_high_local_noise_uncertainty() -> None:
    rt = np.asarray([0.0, 0.1, 0.2, 0.3, 0.4])
    intensity = np.asarray([10.0, 80.0, 20.0, 95.0, 25.0])

    summary = build_cell_integration_audit_summary(
        rt,
        intensity,
        peak_start_rt=0.0,
        peak_end_rt=0.4,
        raw_area=300.0,
    )

    assert summary.area_uncertainty is not None
    assert summary.uncertainty_fraction is not None
    assert summary.uncertainty_fraction > 0.20


def test_cell_integration_audit_returns_empty_for_invalid_trace() -> None:
    summary = build_cell_integration_audit_summary(
        np.asarray([0.0, 0.1]),
        np.asarray([10.0]),
        peak_start_rt=0.0,
        peak_end_rt=0.1,
        raw_area=100.0,
    )

    assert summary.is_empty
