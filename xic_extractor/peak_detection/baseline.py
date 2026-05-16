from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from xic_extractor.peak_detection.integration import integrate_area_counts_seconds


@dataclass(frozen=True)
class BaselineIntegration:
    area_baseline_corrected: float
    area_uncertainty: float | None
    baseline_type: str
    baseline_score: float | None


def integrate_linear_edge_baseline(
    intensity_values: np.ndarray,
    rt_values: np.ndarray,
    left: int,
    right: int,
) -> BaselineIntegration:
    rt = np.asarray(rt_values, dtype=float)
    intensity = np.asarray(intensity_values, dtype=float)
    _validate_trace_arrays(rt, intensity)
    left_index, right_index = bounded_trace_interval(left, right, len(rt))
    segment = intensity[left_index:right_index]
    segment_rt = rt[left_index:right_index]
    baseline = np.linspace(float(segment[0]), float(segment[-1]), len(segment))
    corrected = np.maximum(segment - baseline, 0.0)
    corrected_area = _area_counts_seconds(corrected, segment_rt)
    raw_area = integrate_area_counts_seconds(intensity, rt, left_index, right_index)
    return BaselineIntegration(
        area_baseline_corrected=corrected_area,
        area_uncertainty=_area_uncertainty_counts_seconds(segment, segment_rt),
        baseline_type="linear_edge",
        baseline_score=_safe_ratio(corrected_area, raw_area),
    )


def _validate_trace_arrays(rt: np.ndarray, intensity: np.ndarray) -> None:
    if rt.ndim != 1 or intensity.ndim != 1:
        raise ValueError("rt_values and intensity_values must be one-dimensional")
    if len(rt) != len(intensity):
        raise ValueError("rt_values and intensity_values must have the same length")
    if len(rt) < 2:
        raise ValueError("rt_values and intensity_values must contain at least 2 scans")


def bounded_trace_interval(
    left_index: int,
    right_index: int,
    n_points: int,
) -> tuple[int, int]:
    if n_points < 2:
        raise ValueError("n_points must be at least 2")
    bounded_left = max(0, min(left_index, n_points - 2))
    bounded_right = max(bounded_left + 2, min(right_index, n_points))
    return bounded_left, bounded_right


def _area_counts_seconds(values: np.ndarray, rt_values: np.ndarray) -> float:
    return float(np.trapezoid(values, rt_values)) * 60.0


def _area_uncertainty_counts_seconds(
    segment: np.ndarray,
    rt_values: np.ndarray,
) -> float | None:
    if len(segment) < 3:
        return None
    diffs = np.diff(segment)
    if len(diffs) == 0:
        return None
    median = float(np.median(diffs))
    mad = float(np.median(np.abs(diffs - median)))
    duration_seconds = float(rt_values[-1] - rt_values[0]) * 60.0
    return mad * duration_seconds


def _safe_ratio(value: float, reference: float) -> float | None:
    if reference <= 0:
        return None
    return max(0.0, min(1.0, value / reference))
