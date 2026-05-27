from __future__ import annotations

from dataclasses import dataclass, replace

import numpy as np

from xic_extractor.peak_detection.baseline import (
    bounded_trace_interval,
    compute_asls_residual_mad,
    integrate_asls_baseline,
    integrate_linear_edge_baseline,
)


@dataclass(frozen=True)
class CellIntegrationAuditSummary:
    raw_area: float | None = None
    area_baseline_corrected: float | None = None
    area_uncertainty: float | None = None
    area_uncertainty_formula_version: str = ""
    baseline_residual_mad: float | None = None
    area_uncertainty_noise_source: str = ""
    baseline_type: str = ""
    baseline_score: float | None = None
    uncertainty_fraction: float | None = None
    baseline_fraction: float | None = None
    integration_scan_count: int | None = None
    area_baseline_corrected_asls: float | None = None
    baseline_score_asls: float | None = None
    area_baseline_corrected_linear_edge: float | None = None
    baseline_score_linear_edge: float | None = None

    @property
    def is_empty(self) -> bool:
        return self.integration_scan_count is None


EMPTY_INTEGRATION_AUDIT = CellIntegrationAuditSummary()


def build_cell_integration_audit_summary(
    rt_values: np.ndarray,
    intensity_values: np.ndarray,
    *,
    peak_start_rt: float | None,
    peak_end_rt: float | None,
    raw_area: float | None,
    baseline_integration_method: str = "asls",
    baseline_audit_method: str = "",
) -> CellIntegrationAuditSummary:
    if baseline_integration_method not in {"asls", "linear_edge"}:
        raise ValueError("baseline_integration_method must be 'asls' or 'linear_edge'")
    if baseline_audit_method not in {"", "asls"}:
        raise ValueError("baseline_audit_method must be empty or 'asls'")
    if peak_start_rt is None or peak_end_rt is None or raw_area is None:
        return EMPTY_INTEGRATION_AUDIT
    if not _is_finite_positive(raw_area):
        return EMPTY_INTEGRATION_AUDIT
    rt = np.asarray(rt_values, dtype=float)
    intensity = np.asarray(intensity_values, dtype=float)
    if not _valid_trace(rt, intensity):
        return EMPTY_INTEGRATION_AUDIT

    try:
        left_index, right_index = _bounded_indices_for_rt_window(
            rt,
            peak_start_rt,
            peak_end_rt,
        )
        asls_baseline_values, residual_mad = compute_asls_residual_mad(intensity)
        linear_edge = integrate_linear_edge_baseline(
            intensity,
            rt,
            left_index,
            right_index,
            uncertainty_baseline_values=asls_baseline_values,
            baseline_residual_mad=residual_mad,
            baseline_residual_mad_source="asls_residual",
        )
        asls = (
            integrate_asls_baseline(
                intensity,
                rt,
                left_index,
                right_index,
                baseline_values=asls_baseline_values,
            )
            if baseline_audit_method == "asls" and asls_baseline_values is not None
            else None
        )
        if baseline_integration_method == "asls" and asls_baseline_values is not None:
            asls = integrate_asls_baseline(
                intensity,
                rt,
                left_index,
                right_index,
                baseline_values=asls_baseline_values,
            )
            baseline = asls
            linear_edge_rollback = linear_edge
        elif baseline_integration_method == "asls":
            baseline = replace(linear_edge, baseline_type="linear_edge_fallback")
            linear_edge_rollback = None
        else:
            baseline = linear_edge
            linear_edge_rollback = None
    except (IndexError, TypeError, ValueError, FloatingPointError):
        return EMPTY_INTEGRATION_AUDIT

    uncertainty_fraction = (
        baseline.area_uncertainty / raw_area
        if baseline.area_uncertainty is not None
        else None
    )
    baseline_fraction = baseline.area_baseline_corrected / raw_area
    return CellIntegrationAuditSummary(
        raw_area=float(raw_area),
        area_baseline_corrected=baseline.area_baseline_corrected,
        area_uncertainty=baseline.area_uncertainty,
        area_uncertainty_formula_version=baseline.area_uncertainty_formula_version,
        baseline_residual_mad=baseline.baseline_residual_mad,
        area_uncertainty_noise_source=baseline.area_uncertainty_noise_source,
        baseline_type=baseline.baseline_type,
        baseline_score=baseline.baseline_score,
        uncertainty_fraction=uncertainty_fraction,
        baseline_fraction=baseline_fraction,
        integration_scan_count=right_index - left_index,
        area_baseline_corrected_asls=(
            None if asls is None else asls.area_baseline_corrected
        ),
        baseline_score_asls=(None if asls is None else asls.baseline_score),
        area_baseline_corrected_linear_edge=(
            None
            if linear_edge_rollback is None
            else linear_edge_rollback.area_baseline_corrected
        ),
        baseline_score_linear_edge=(
            None if linear_edge_rollback is None else linear_edge_rollback.baseline_score
        ),
    )


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


def _valid_trace(rt_values: np.ndarray, intensity_values: np.ndarray) -> bool:
    if rt_values.ndim != 1 or intensity_values.ndim != 1:
        return False
    if len(rt_values) != len(intensity_values) or len(rt_values) < 2:
        return False
    return bool(
        np.all(np.isfinite(rt_values)) and np.all(np.isfinite(intensity_values))
    )


def _is_finite_positive(value: float | None) -> bool:
    return value is not None and bool(np.isfinite(value)) and value > 0
