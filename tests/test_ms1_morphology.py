import numpy as np
import pytest

from xic_extractor.peak_detection.ms1_morphology import (
    DEFAULT_GAUSSIAN15_WINDOW_POINTS,
    MS1_MORPHOLOGY_AREA_SOURCE,
    MS1_MORPHOLOGY_TRACE_METHOD,
    gaussian15_morphology_trace,
    gaussian15_positive_asls_residual_metrics,
    positive_residual_area,
)


def test_gaussian15_morphology_trace_preserves_centered_spike_area() -> None:
    residual = np.zeros(31)
    residual[15] = 100.0

    smoothed = gaussian15_morphology_trace(residual)

    assert smoothed[15] < 100.0
    assert smoothed.sum() == pytest.approx(100.0)
    assert np.all(smoothed >= 0.0)


def test_positive_residual_area_integrates_only_positive_signal_seconds() -> None:
    rt = np.array([0.0, 1.0, 2.0])
    residual = np.array([-5.0, 10.0, -5.0])

    area = positive_residual_area(rt, residual, 0, 3)

    assert area == pytest.approx(600.0)


def test_gaussian15_positive_asls_residual_metrics_carry_provenance() -> None:
    rt = np.linspace(0.0, 2.0, 31)
    intensity = np.zeros(31)
    intensity[15] = 100.0
    baseline = np.zeros(31)

    metrics = gaussian15_positive_asls_residual_metrics(
        rt,
        intensity,
        baseline,
        10,
        21,
    )

    assert metrics.area_positive_asls_residual > 0.0
    assert metrics.area_source == MS1_MORPHOLOGY_AREA_SOURCE
    assert metrics.trace_method == MS1_MORPHOLOGY_TRACE_METHOD
    assert metrics.trace_window_points == DEFAULT_GAUSSIAN15_WINDOW_POINTS
    assert metrics.trace_effective_points == DEFAULT_GAUSSIAN15_WINDOW_POINTS
