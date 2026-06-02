import numpy as np

from xic_extractor.alignment.matrix_handoff import integration_from_peak_trace
from xic_extractor.peak_detection.models import PeakResult


def test_integration_from_peak_trace_populates_asls_primary_fields() -> None:
    peak = PeakResult(
        rt=2.0,
        intensity=50.0,
        intensity_smoothed=50.0,
        area=4000.0,
        peak_start=1.0,
        peak_end=3.0,
    )

    integration = integration_from_peak_trace(
        peak,
        np.array([0.0, 1.0, 2.0, 3.0, 4.0]),
        np.array([10.0, 12.0, 50.0, 12.0, 10.0]),
        boundary_sources=("test_trace",),
    )

    assert integration is not None
    assert integration.area_raw_counts_seconds == 4000.0
    assert integration.baseline_type == "asls"
    assert integration.area_baseline_corrected is not None
    assert 0.0 < integration.area_baseline_corrected < 4000.0
    assert integration.area_uncertainty is not None
    assert integration.baseline_residual_mad is not None


def test_integration_from_peak_trace_keeps_raw_audit_when_asls_unavailable() -> None:
    peak = PeakResult(
        rt=2.0,
        intensity=50.0,
        intensity_smoothed=50.0,
        area=80.0,
        peak_start=1.0,
        peak_end=3.0,
    )

    integration = integration_from_peak_trace(
        peak,
        np.array([0.0]),
        np.array([50.0]),
        boundary_sources=("test_trace",),
    )

    assert integration is not None
    assert integration.area_raw_counts_seconds == 80.0
    assert integration.baseline_type == ""
    assert integration.area_baseline_corrected is None
