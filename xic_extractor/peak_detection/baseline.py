from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np

from xic_extractor.baseline import asls_baseline
from xic_extractor.peak_detection.integration import integrate_area_counts_seconds

BaselineMethod = Literal["linear_edge", "asls"]
AREA_UNCERTAINTY_FORMULA_VERSION = "baseline_residual_mad_v1"


@dataclass(frozen=True)
class BaselineIntegration:
    area_baseline_corrected: float
    area_uncertainty: float | None
    baseline_type: str
    baseline_score: float | None
    area_uncertainty_formula_version: str = ""
    baseline_residual_mad: float | None = None
    area_uncertainty_noise_source: str = ""


def integrate_linear_edge_baseline(
    intensity_values: np.ndarray,
    rt_values: np.ndarray,
    left: int,
    right: int,
    *,
    uncertainty_baseline_values: np.ndarray | None = None,
    baseline_residual_mad: float | None = None,
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
    residual_mad = baseline_residual_mad
    if residual_mad is None:
        _baseline_values, residual_mad = compute_asls_residual_mad(
            intensity,
            baseline_values=uncertainty_baseline_values,
        )
    noise_source = "asls_residual" if residual_mad is not None else ""
    if residual_mad is None:
        residual_mad = _pre_peak_mad(intensity, left_index)
        noise_source = "pre_peak_mad" if residual_mad is not None else ""
    uncertainty = _area_uncertainty_counts_seconds(
        rt,
        left_index,
        right_index,
        baseline_residual_mad=residual_mad,
    )
    if uncertainty is None:
        residual_mad = None
        noise_source = ""
    return BaselineIntegration(
        area_baseline_corrected=corrected_area,
        area_uncertainty=uncertainty,
        baseline_type="linear_edge",
        baseline_score=_safe_ratio(corrected_area, raw_area),
        area_uncertainty_formula_version=AREA_UNCERTAINTY_FORMULA_VERSION,
        baseline_residual_mad=residual_mad,
        area_uncertainty_noise_source=noise_source,
    )


def integrate_asls_baseline(
    intensity_values: np.ndarray,
    rt_values: np.ndarray,
    left: int,
    right: int,
    *,
    lam: float = 1e5,
    p: float = 0.01,
    n_iter: int = 10,
    baseline_values: np.ndarray | None = None,
) -> BaselineIntegration:
    rt = np.asarray(rt_values, dtype=float)
    intensity = np.asarray(intensity_values, dtype=float)
    _validate_trace_arrays(rt, intensity)
    left_index, right_index = bounded_trace_interval(left, right, len(rt))
    full_baseline = (
        np.asarray(baseline_values, dtype=float)
        if baseline_values is not None
        else asls_baseline(intensity, lam=lam, p=p, n_iter=n_iter)
    )
    if full_baseline.shape != intensity.shape:
        raise ValueError("baseline_values must match intensity_values shape")
    segment = intensity[left_index:right_index]
    segment_rt = rt[left_index:right_index]
    baseline_segment = full_baseline[left_index:right_index]
    corrected = np.maximum(segment - baseline_segment, 0.0)
    corrected_area = _area_counts_seconds(corrected, segment_rt)
    raw_area = integrate_area_counts_seconds(intensity, rt, left_index, right_index)
    return BaselineIntegration(
        area_baseline_corrected=corrected_area,
        area_uncertainty=None,
        baseline_type="asls",
        baseline_score=_safe_ratio(corrected_area, raw_area),
    )


def integrate_with_baseline(
    intensity_values: np.ndarray,
    rt_values: np.ndarray,
    left: int,
    right: int,
    *,
    baseline_method: BaselineMethod = "linear_edge",
) -> BaselineIntegration:
    if baseline_method == "linear_edge":
        return integrate_linear_edge_baseline(intensity_values, rt_values, left, right)
    if baseline_method == "asls":
        return integrate_asls_baseline(intensity_values, rt_values, left, right)
    raise ValueError("baseline_method must be 'linear_edge' or 'asls'")


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


def compute_asls_residual_mad(
    intensity_values: np.ndarray,
    *,
    baseline_values: np.ndarray | None = None,
) -> tuple[np.ndarray | None, float | None]:
    values = np.asarray(intensity_values, dtype=float)
    if len(values) < 5 or not np.all(np.isfinite(values)):
        return None, None
    try:
        baseline = (
            np.asarray(baseline_values, dtype=float)
            if baseline_values is not None
            else asls_baseline(values)
        )
    except (ValueError, FloatingPointError):
        return None, None
    if baseline.shape != values.shape:
        return None, None
    residual = values - baseline
    residual_mad = float(np.median(np.abs(residual - np.median(residual))))
    if not np.isfinite(residual_mad):
        return baseline, None
    return baseline, residual_mad


def _area_uncertainty_counts_seconds(
    rt_values: np.ndarray,
    left_index: int,
    right_index: int,
    *,
    baseline_residual_mad: float | None = None,
) -> float | None:
    noise = baseline_residual_mad
    if noise is None or not np.isfinite(noise):
        return None
    scan_period_s = _median_scan_period_seconds(rt_values)
    if scan_period_s is None:
        return None
    n_points = right_index - left_index
    if n_points < 2:
        return None
    return float(noise * scan_period_s * np.sqrt(n_points))


def _median_scan_period_seconds(rt_values: np.ndarray) -> float | None:
    if len(rt_values) < 2:
        return None
    diffs = np.diff(rt_values)
    if len(diffs) == 0 or not np.all(np.isfinite(diffs)):
        return None
    scan_period = float(np.median(diffs)) * 60.0
    if not np.isfinite(scan_period) or scan_period <= 0:
        return None
    return scan_period


def _pre_peak_mad(
    intensity_values: np.ndarray,
    left_index: int,
    *,
    window_size: int = 10,
) -> float | None:
    window_left = max(0, left_index - window_size)
    window = intensity_values[window_left:left_index]
    window = window[np.isfinite(window)]
    if len(window) < 3:
        return None
    median = float(np.median(window))
    mad = float(np.median(np.abs(window - median)))
    if not np.isfinite(mad):
        return None
    return mad


def _safe_ratio(value: float, reference: float) -> float | None:
    if reference <= 0:
        return None
    return max(0.0, min(1.0, value / reference))
