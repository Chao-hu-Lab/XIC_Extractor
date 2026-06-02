from __future__ import annotations

import math

import numpy as np

from xic_extractor.peak_detection.baseline import (
    bounded_trace_interval,
    integrate_with_baseline,
)
from xic_extractor.peak_detection.hypotheses import IntegrationResult
from xic_extractor.peak_detection.models import PeakResult


def integration_from_peak(
    peak: PeakResult,
    *,
    boundary_sources: tuple[str, ...],
    integration_method: str = "raw_trapezoid",
) -> IntegrationResult | None:
    return integration_from_values(
        area_raw_counts_seconds=peak.area,
        rt_apex_min=peak.rt,
        raw_apex_rt_min=peak.rt,
        height_raw=peak.intensity,
        height_smoothed=getattr(peak, "intensity_smoothed", peak.intensity),
        rt_left_min=peak.peak_start,
        rt_right_min=peak.peak_end,
        boundary_sources=boundary_sources,
        integration_method=integration_method,
    )


def integration_from_peak_trace(
    peak: PeakResult,
    rt_values: object,
    intensity_values: object,
    *,
    boundary_sources: tuple[str, ...],
    integration_method: str = "raw_trapezoid",
    baseline_integration_method: str = "asls",
) -> IntegrationResult | None:
    integration = integration_from_peak(
        peak,
        boundary_sources=boundary_sources,
        integration_method=integration_method,
    )
    if integration is None:
        return None
    try:
        rt = np.asarray(rt_values, dtype=float)
        intensity = np.asarray(intensity_values, dtype=float)
        _validate_trace(rt, intensity)
        left_index, right_index = _bounded_indices_for_rt_window(
            rt,
            peak.peak_start,
            peak.peak_end,
        )
        baseline = integrate_with_baseline(
            intensity,
            rt,
            left_index,
            right_index,
            baseline_method=baseline_integration_method,
        )
    except (IndexError, TypeError, ValueError, FloatingPointError):
        return integration
    return integration_from_values(
        area_raw_counts_seconds=peak.area,
        rt_apex_min=peak.rt,
        raw_apex_rt_min=peak.rt,
        height_raw=peak.intensity,
        height_smoothed=getattr(peak, "intensity_smoothed", peak.intensity),
        rt_left_min=peak.peak_start,
        rt_right_min=peak.peak_end,
        boundary_sources=boundary_sources,
        integration_method=integration_method,
        area_baseline_corrected=baseline.area_baseline_corrected,
        area_uncertainty=baseline.area_uncertainty,
        area_uncertainty_formula_version=baseline.area_uncertainty_formula_version,
        baseline_residual_mad=baseline.baseline_residual_mad,
        area_uncertainty_noise_source=baseline.area_uncertainty_noise_source,
        baseline_type=baseline.baseline_type,
        baseline_score=baseline.baseline_score,
    )


def integration_from_values(
    *,
    area_raw_counts_seconds: object,
    rt_apex_min: object,
    raw_apex_rt_min: object | None = None,
    height_raw: object,
    height_smoothed: object | None = None,
    rt_left_min: object,
    rt_right_min: object,
    boundary_sources: tuple[str, ...],
    integration_method: str = "raw_trapezoid",
    area_baseline_corrected: object | None = None,
    area_uncertainty: object | None = None,
    area_uncertainty_formula_version: str = "",
    baseline_residual_mad: object | None = None,
    area_uncertainty_noise_source: str = "",
    baseline_type: str = "",
    baseline_score: object | None = None,
) -> IntegrationResult | None:
    values = (
        area_raw_counts_seconds,
        rt_apex_min,
        height_raw,
        rt_left_min,
        rt_right_min,
    )
    if any(_finite(value) is None for value in values):
        return None
    apex = _finite(rt_apex_min)
    left = _finite(rt_left_min)
    right = _finite(rt_right_min)
    area = _finite(area_raw_counts_seconds)
    height = _finite(height_raw)
    raw_apex = _finite(raw_apex_rt_min)
    smoothed_height = _finite(height_smoothed)
    if apex is None or left is None or right is None or area is None or height is None:
        return None
    return IntegrationResult(
        rt_left_min=left,
        rt_apex_min=apex,
        rt_right_min=right,
        raw_apex_rt_min=apex if raw_apex is None else raw_apex,
        rt_width_min=right - left,
        height_raw=height,
        height_smoothed=height if smoothed_height is None else smoothed_height,
        area_raw_counts_seconds=area,
        integration_method=integration_method,
        boundary_sources=boundary_sources,
        area_baseline_corrected=_finite(area_baseline_corrected),
        area_uncertainty=_finite(area_uncertainty),
        area_uncertainty_formula_version=area_uncertainty_formula_version,
        baseline_residual_mad=_finite(baseline_residual_mad),
        area_uncertainty_noise_source=area_uncertainty_noise_source,
        baseline_type=baseline_type,
        baseline_score=_finite(baseline_score),
    )


def _finite(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if not math.isfinite(value):
        return None
    return float(value)


def _bounded_indices_for_rt_window(
    rt_values: np.ndarray,
    peak_start_rt: float,
    peak_end_rt: float,
) -> tuple[int, int]:
    if not np.isfinite(peak_start_rt) or not np.isfinite(peak_end_rt):
        raise ValueError("peak RT bounds must be finite")
    left_rt = min(float(peak_start_rt), float(peak_end_rt))
    right_rt = max(float(peak_start_rt), float(peak_end_rt))
    if right_rt <= left_rt:
        raise ValueError("peak RT window must have positive width")
    left_index = int(np.searchsorted(rt_values, left_rt, side="left"))
    right_index = int(np.searchsorted(rt_values, right_rt, side="right"))
    if right_index - left_index < 2:
        left_index = int(np.argmin(np.abs(rt_values - left_rt)))
        right_index = int(np.argmin(np.abs(rt_values - right_rt))) + 1
    return bounded_trace_interval(left_index, right_index, len(rt_values))


def _validate_trace(rt_values: np.ndarray, intensity_values: np.ndarray) -> None:
    if rt_values.ndim != 1 or intensity_values.ndim != 1:
        raise ValueError("trace arrays must be 1-D")
    if len(rt_values) != len(intensity_values) or len(rt_values) < 2:
        raise ValueError("trace arrays must have matching length >= 2")
    if not (
        np.all(np.isfinite(rt_values)) and np.all(np.isfinite(intensity_values))
    ):
        raise ValueError("trace arrays must contain finite values")
