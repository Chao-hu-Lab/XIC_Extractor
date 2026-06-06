"""Synthetic benchmark generation for the P2c AsLS truth-validation gate."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from statistics import median
from typing import Mapping, Sequence, TypeAlias

import numpy as np
from numpy.typing import NDArray

from tools.diagnostics.asls_truth_validation_manifests import (
    FixtureLock,
    FixtureLockRecord,
    FixtureManifest,
)
from tools.diagnostics.asls_truth_validation_models import (
    BENCHMARK_STATUS_PASS,
    BLOCKER_SCOPE_B1_C1B,
    BLOCKER_SCOPE_B2_RETIREMENT,
    BLOCKER_SCOPE_CAUTION,
    INCONCLUSIVE_FIXTURE_LOCK_CHANGED,
    PRODUCTION_LIKE_IN_SCOPE,
    ROW_STATUS_HARD_BLOCKER,
    ROW_STATUS_PASS,
    TIER_B1_ACCURACY_FAIL,
    TIER_B1_ACCURACY_PLANNING_ONLY,
    TIER_B1_ACCURACY_RETIREMENT_ELIGIBLE,
    TIER_B1_RELEVANCE,
    TIER_B2_STATUS_STRESS_REQUIRES_TIER_C,
)
from xic_extractor.peak_detection.baseline import (
    BaselineIntegration,
    bounded_trace_interval,
    integrate_asls_baseline,
)
from xic_extractor.peak_detection.integration import integrate_area_counts_seconds

SYNTHETIC_FIXTURE_LOCK_VALID = BENCHMARK_STATUS_PASS
FloatArray: TypeAlias = NDArray[np.float64]


@dataclass(frozen=True)
class SyntheticTrace:
    fixture_id: str
    fixture_class: str
    split: str
    replicate_id: int
    sn_stratum: str
    peak_width_stratum: str
    hard_case_stratum: str
    tier_b_layer: str
    stress_role: str
    production_like_bounds_status: str
    scan_density_stratum: str
    integration_point_count: int
    integration_width_min: float
    rt_values: FloatArray
    intensity_values: FloatArray
    true_baseline_values: FloatArray
    true_peak_values: FloatArray
    nuisance_values: FloatArray
    true_area: float
    left_index: int
    right_index: int
    source_record: FixtureLockRecord


@dataclass(frozen=True)
class SyntheticComparisonRow:
    tier_b_layer: str
    fixture_id: str
    fixture_class: str
    split: str
    replicate_id: int
    stress_role: str
    production_like_bounds_status: str
    scan_density_stratum: str
    integration_point_count: int
    integration_width_min: float
    raw_area: float
    true_area: float
    linear_edge_area: float
    asls_area: float
    linear_edge_abs_error: float
    asls_abs_error: float
    linear_edge_relative_error_pct: float | None
    asls_relative_error_pct: float | None
    asls_error_over_linear_error: float | None
    asls_exceeds_raw_area: bool
    asls_negative_nonblank_area: bool
    blank_false_positive: bool
    blank_not_quantifiable: bool
    asls_area_uncertainty: float | None
    asls_baseline_residual_mad: float | None
    asls_area_uncertainty_noise_source: str
    blocker_scope: str
    row_status: str
    failure_reasons: tuple[str, ...]


@dataclass(frozen=True)
class TierBBlockerSummary:
    tier_b1_status: str
    tier_b1_accuracy_scope: str
    tier_b2_status: str
    b1_hard_blockers: tuple[str, ...]
    b1_cautions: tuple[str, ...]
    b2_retirement_blockers: tuple[str, ...]


def validate_synthetic_fixture_lock(
    manifest: FixtureManifest,
    lock: FixtureLock,
) -> str:
    if manifest.fixture_lock_hash != lock.whole_lock_hash:
        return INCONCLUSIVE_FIXTURE_LOCK_CHANGED
    return SYNTHETIC_FIXTURE_LOCK_VALID


def generate_synthetic_traces(
    manifest: FixtureManifest,
    lock: FixtureLock,
) -> tuple[SyntheticTrace, ...]:
    status = validate_synthetic_fixture_lock(manifest, lock)
    if status != SYNTHETIC_FIXTURE_LOCK_VALID:
        raise ValueError(status)
    return tuple(_trace_from_record(record) for record in lock.records)


def compare_synthetic_trace(
    trace: SyntheticTrace,
    *,
    asls_params: Mapping[str, float | int],
    reference_nonblank_median_true_area: float,
) -> SyntheticComparisonRow:
    raw_area = integrate_area_counts_seconds(
        trace.intensity_values,
        trace.rt_values,
        trace.left_index,
        trace.right_index,
    )
    linear_edge = _integrate_historical_linear_edge_baseline(
        trace.intensity_values,
        trace.rt_values,
        trace.left_index,
        trace.right_index,
    )
    asls = integrate_asls_baseline(
        trace.intensity_values,
        trace.rt_values,
        trace.left_index,
        trace.right_index,
        lam=float(asls_params["lam"]),
        p=float(asls_params["p"]),
        n_iter=int(asls_params["n_iter"]),
    )
    return _comparison_row(
        trace,
        raw_area=raw_area,
        linear_edge=linear_edge,
        asls=asls,
        reference_nonblank_median_true_area=reference_nonblank_median_true_area,
    )


def _integrate_historical_linear_edge_baseline(
    intensity_values: np.ndarray,
    rt_values: np.ndarray,
    left: int,
    right: int,
) -> BaselineIntegration:
    """Historical comparator retained only for locked retirement evidence."""
    rt = np.asarray(rt_values, dtype=float)
    intensity = np.asarray(intensity_values, dtype=float)
    left_index, right_index = bounded_trace_interval(left, right, len(rt))
    segment = intensity[left_index:right_index]
    segment_rt = rt[left_index:right_index]
    baseline = np.linspace(float(segment[0]), float(segment[-1]), len(segment))
    corrected = np.maximum(segment - baseline, 0.0)
    corrected_area = integrate_area_counts_seconds(
        corrected,
        segment_rt,
        0,
        len(segment),
    )
    raw_area = integrate_area_counts_seconds(intensity, rt, left_index, right_index)
    baseline_score = corrected_area / raw_area if raw_area else None
    return BaselineIntegration(
        area_baseline_corrected=corrected_area,
        area_uncertainty=None,
        baseline_type="historical_linear_edge",
        baseline_score=baseline_score,
    )


def tier_b_hard_blockers(
    rows: Sequence[SyntheticComparisonRow],
) -> tuple[str, ...]:
    """Compatibility helper returning all B1/B2 hard blockers."""

    summary = classify_tier_b_blockers(rows)
    return tuple(
        sorted(
            {
                *summary.b1_hard_blockers,
                *summary.b2_retirement_blockers,
            }
        )
    )


def classify_tier_b_blockers(
    rows: Sequence[SyntheticComparisonRow],
) -> TierBBlockerSummary:
    """Return decision-scoped Tier B blocker groups."""

    b1_blockers = {
        reason
        for row in rows
        if row.blocker_scope == BLOCKER_SCOPE_B1_C1B
        for reason in row.failure_reasons
    }
    b1_cautions = {
        reason
        for row in rows
        if row.blocker_scope == BLOCKER_SCOPE_CAUTION
        for reason in row.failure_reasons
    }
    b2_blockers = {
        reason
        for row in rows
        if row.blocker_scope == BLOCKER_SCOPE_B2_RETIREMENT
        for reason in row.failure_reasons
    }
    heldout_by_class: dict[str, list[SyntheticComparisonRow]] = defaultdict(list)
    for row in rows:
        if row.split == "heldout_gate" and _is_b1_decision_row(row):
            heldout_by_class[row.fixture_class].append(row)
    for fixture_class, class_rows in heldout_by_class.items():
        asls_abs = [row.asls_abs_error for row in class_rows]
        linear_abs = [row.linear_edge_abs_error for row in class_rows]
        linear_expected_to_fail = fixture_class != "flat_peak_control"
        if (
            linear_expected_to_fail
            and asls_abs
            and linear_abs
            and median(asls_abs) > median(linear_abs)
        ):
            b1_blockers.add(f"{fixture_class}:asls_median_abs_error_exceeds_linear_edge")
        if fixture_class == "blank_noise_control":
            continue
        rel_errors = [
            row.asls_relative_error_pct
            for row in class_rows
            if row.asls_relative_error_pct is not None
        ]
        if not rel_errors:
            continue
        median_rel = median(rel_errors)
        p95_rel = _p95(rel_errors)
        if fixture_class == "flat_peak_control":
            if median_rel > 5.0:
                b1_blockers.add("flat_peak_control:median_asls_relative_error_gt_5pct")
            if p95_rel > 8.0:
                b1_cautions.add("flat_peak_control:p95_asls_relative_error_gt_8pct")
        if median_rel > 25.0:
            b1_blockers.add(f"{fixture_class}:median_asls_relative_error_gt_25pct")
        elif median_rel > 10.0:
            if median(asls_abs) <= median(linear_abs):
                b1_cautions.add(
                    f"{fixture_class}:median_asls_relative_error_gt_10pct_planning_only"
                )
            else:
                b1_blockers.add(f"{fixture_class}:median_asls_relative_error_gt_10pct")
        if p95_rel > 20.0:
            b1_cautions.add(f"{fixture_class}:p95_asls_relative_error_gt_20pct")
        if fixture_class in {
            "sloped_baseline_peak",
            "tailing_peak",
            "adjacent_shoulder",
        }:
            asls_median_abs = median(asls_abs)
            linear_median_abs = median(linear_abs)
            true_median = median(
                row.true_area for row in class_rows if row.true_area > 0
            )
            asls_abs_pct = asls_median_abs / true_median * 100.0
            improves_by_20pct = asls_median_abs <= 0.8 * linear_median_abs
            abs_error_below_3pct = asls_abs_pct < 3.0
            if median_rel > 10.0 and not (improves_by_20pct or abs_error_below_3pct):
                b1_blockers.add(
                    f"{fixture_class}:asls_lacks_20pct_improvement_or_3pct_abs_error"
                )
    tier_b1_status = "FAIL" if b1_blockers else BENCHMARK_STATUS_PASS
    tier_b2_status = (
        TIER_B2_STATUS_STRESS_REQUIRES_TIER_C if b2_blockers else BENCHMARK_STATUS_PASS
    )
    accuracy_scope = (
        TIER_B1_ACCURACY_FAIL
        if b1_blockers
        else TIER_B1_ACCURACY_PLANNING_ONLY
        if b1_cautions
        else TIER_B1_ACCURACY_RETIREMENT_ELIGIBLE
    )
    return TierBBlockerSummary(
        tier_b1_status=tier_b1_status,
        tier_b1_accuracy_scope=accuracy_scope,
        tier_b2_status=tier_b2_status,
        b1_hard_blockers=tuple(sorted(b1_blockers)),
        b1_cautions=tuple(sorted(b1_cautions)),
        b2_retirement_blockers=tuple(sorted(b2_blockers)),
    )


def _is_b1_decision_row(row: SyntheticComparisonRow) -> bool:
    return (
        row.tier_b_layer == TIER_B1_RELEVANCE
        and row.production_like_bounds_status == PRODUCTION_LIKE_IN_SCOPE
    )


def blank_false_positive(
    *,
    asls_area: float,
    area_uncertainty: float | None,
    reference_nonblank_median_true_area: float,
) -> bool:
    threshold = 0.005 * max(reference_nonblank_median_true_area, 0.0)
    if area_uncertainty is not None and np.isfinite(area_uncertainty):
        threshold = max(threshold, 3.0 * float(area_uncertainty))
    return bool(asls_area > threshold)


def _trace_from_record(record: FixtureLockRecord) -> SyntheticTrace:
    params = record.parameters
    n_points = _param_int(params, "trace_length_points")
    scan_spacing = _param_float(params, "scan_spacing_min")
    apex_rt = _param_float(params, "apex_rt_min")
    center_index = n_points // 2
    start_rt = apex_rt - center_index * scan_spacing
    rt = start_rt + np.arange(n_points, dtype=np.float64) * scan_spacing
    baseline = _baseline_values(rt, params, apex_rt)
    target_peak, nuisance = _peak_and_nuisance_values(record, rt, apex_rt)
    noise = _deterministic_noise(record, baseline + target_peak + nuisance)
    intensity = np.maximum(baseline + target_peak + nuisance + noise, 0.0)
    left, right = record.expected_bound_indices
    true_area = integrate_area_counts_seconds(target_peak, rt, left, right)
    return SyntheticTrace(
        fixture_id=record.fixture_id,
        fixture_class=record.fixture_class,
        split=record.split,
        replicate_id=record.replicate_id,
        sn_stratum=record.sn_stratum,
        peak_width_stratum=record.peak_width_stratum,
        hard_case_stratum=record.hard_case_stratum,
        tier_b_layer=record.gate_layer,
        stress_role=record.stress_role,
        production_like_bounds_status=record.production_like_bounds_status,
        scan_density_stratum=record.scan_density_stratum,
        integration_point_count=record.integration_point_count,
        integration_width_min=record.integration_width_min,
        rt_values=rt,
        intensity_values=intensity,
        true_baseline_values=baseline,
        true_peak_values=target_peak,
        nuisance_values=nuisance,
        true_area=float(max(true_area, 0.0)),
        left_index=left,
        right_index=right,
        source_record=record,
    )


def _baseline_values(
    rt: FloatArray,
    params: Mapping[str, object],
    apex_rt: float,
) -> FloatArray:
    centered_rt = rt - apex_rt
    baseline = np.full(rt.shape, _param_float(params, "baseline_intercept"))
    baseline += _param_float(params, "baseline_slope_per_min") * centered_rt
    hump_amplitude = _param_float(params, "hump_amplitude")
    if hump_amplitude:
        sigma = _param_float(params, "peak_sigma_min")
        hump_width = max(_param_float(params, "hump_width_sigma") * sigma, sigma)
        baseline += hump_amplitude * np.exp(-0.5 * (centered_rt / hump_width) ** 2)
    dip_fraction = _param_float(params, "local_dip_depth_fraction")
    if dip_fraction:
        sigma = _param_float(params, "peak_sigma_min")
        dip_center = apex_rt - 1.8 * sigma
        dip_width = max(1.5 * sigma, 1e-9)
        depth = dip_fraction * max(_param_float(params, "peak_height"), 1.0)
        baseline -= depth * np.exp(-0.5 * ((rt - dip_center) / dip_width) ** 2)
    return baseline


def _peak_and_nuisance_values(
    record: FixtureLockRecord,
    rt: FloatArray,
    apex_rt: float,
) -> tuple[FloatArray, FloatArray]:
    params = record.parameters
    formula = record.true_area_formula_version
    if formula == "no_peak_v1":
        target = np.zeros_like(rt, dtype=np.float64)
        return target, _blank_nuisance_values(rt, params, apex_rt)
    gaussian = _gaussian_peak(rt, params, apex_rt)
    nuisance = np.zeros_like(rt, dtype=np.float64)
    if formula == "symmetric_gaussian_v1":
        target = gaussian
    elif formula == "exponential_tail_gaussian_v1":
        target = _tailing_peak(rt, params, apex_rt)
    elif formula == "gaussian_with_shoulder_v1":
        shoulder = _offset_gaussian(
            rt,
            params,
            apex_rt
            + _param_float(params, "shoulder_offset_sigma")
            * _param_float(params, "peak_sigma_min"),
            _param_float(params, "shoulder_height_fraction"),
        )
        target = gaussian + shoulder
    elif formula == "gaussian_with_interference_v1":
        target = gaussian
        nuisance = _offset_gaussian(
            rt,
            params,
            apex_rt
            + _param_float(params, "shoulder_offset_sigma")
            * _param_float(params, "peak_sigma_min"),
            _param_float(params, "interference_height_fraction"),
        )
    elif formula == "clipped_gaussian_v1":
        clip_at = _param_float(params, "clip_fraction") * _param_float(
            params,
            "peak_height",
        )
        target = np.minimum(gaussian, clip_at)
    else:
        raise ValueError(f"unsupported true_area_formula_version: {formula}")
    return target, nuisance


def _gaussian_peak(
    rt: FloatArray,
    params: Mapping[str, object],
    apex_rt: float,
) -> FloatArray:
    sigma = max(_param_float(params, "peak_sigma_min"), 1e-9)
    height = _param_float(params, "peak_height")
    return height * np.exp(-0.5 * ((rt - apex_rt) / sigma) ** 2)


def _offset_gaussian(
    rt: FloatArray,
    params: Mapping[str, object],
    apex_rt: float,
    height_fraction: float,
) -> FloatArray:
    sigma = max(_param_float(params, "peak_sigma_min"), 1e-9)
    height = _param_float(params, "peak_height") * height_fraction
    return height * np.exp(-0.5 * ((rt - apex_rt) / sigma) ** 2)


def _tailing_peak(
    rt: FloatArray,
    params: Mapping[str, object],
    apex_rt: float,
) -> FloatArray:
    sigma = max(_param_float(params, "peak_sigma_min"), 1e-9)
    height = _param_float(params, "peak_height")
    tail_sigma = max(_param_float(params, "tail_factor_sigma") * sigma, sigma * 0.2)
    left = height * np.exp(-0.5 * ((rt - apex_rt) / sigma) ** 2)
    right = height * np.exp(-(rt - apex_rt) / tail_sigma)
    return np.where(rt <= apex_rt, left, right)


def _blank_nuisance_values(
    rt: FloatArray,
    params: Mapping[str, object],
    apex_rt: float,
) -> FloatArray:
    height = _param_float(params, "blank_transient_height", default=0.0)
    if not height:
        return np.zeros_like(rt, dtype=np.float64)
    sigma = max(_param_float(params, "blank_transient_sigma_min", default=0.02), 1e-9)
    offset = _param_float(params, "blank_transient_rt_offset_min", default=0.0)
    center = apex_rt + offset
    return height * np.exp(-0.5 * ((rt - center) / sigma) ** 2)


def _deterministic_noise(
    record: FixtureLockRecord,
    signal: FloatArray,
) -> FloatArray:
    params = record.parameters
    x = np.arange(len(signal), dtype=np.float64)
    phase = record.replicate_id * 0.61803398875
    base_noise = _param_float(params, "noise_sigma") * (
        0.55 * np.sin(1.73 * x + phase) + 0.25 * np.cos(0.47 * x + phase * 0.5)
    )
    intensity_noise = (
        _param_float(params, "noise_intensity_fraction")
        * np.sqrt(np.maximum(signal, 0.0))
        * np.sin(0.91 * x + phase * 1.7)
    )
    return base_noise + intensity_noise


def _param_float(
    params: Mapping[str, object],
    key: str,
    *,
    default: float | None = None,
) -> float:
    value = params.get(key, default)
    if value is None or isinstance(value, bool):
        raise ValueError(f"{key} must be numeric")
    if isinstance(value, int | float | str):
        return float(value)
    raise ValueError(f"{key} must be numeric")


def _param_int(params: Mapping[str, object], key: str) -> int:
    value = params.get(key)
    if value is None or isinstance(value, bool):
        raise ValueError(f"{key} must be an integer")
    if isinstance(value, int | str):
        return int(value)
    if isinstance(value, float) and value.is_integer():
        return int(value)
    raise ValueError(f"{key} must be an integer")


def _comparison_row(
    trace: SyntheticTrace,
    *,
    raw_area: float,
    linear_edge: BaselineIntegration,
    asls: BaselineIntegration,
    reference_nonblank_median_true_area: float,
) -> SyntheticComparisonRow:
    linear_area = float(linear_edge.area_baseline_corrected)
    asls_area = float(asls.area_baseline_corrected)
    linear_error = abs(linear_area - trace.true_area)
    asls_error = abs(asls_area - trace.true_area)
    asls_exceeds_raw = bool(asls_area > raw_area)
    asls_negative_nonblank = bool(trace.true_area > 0 and asls_area < 0)
    blank_fp = False
    blank_not_quantifiable = False
    if trace.true_area == 0:
        blank_not_quantifiable = asls.area_uncertainty is None
        blank_fp = blank_false_positive(
            asls_area=asls_area,
            area_uncertainty=asls.area_uncertainty,
            reference_nonblank_median_true_area=reference_nonblank_median_true_area,
        )
    reasons: list[str] = []
    blocker_scope = ""
    if asls_exceeds_raw:
        reasons.append("asls_exceeds_raw_area")
    if asls_negative_nonblank:
        reasons.append("asls_negative_nonblank_area")
    if blank_fp:
        reasons.append("blank_false_positive")
    if blank_not_quantifiable:
        reasons.append("blank_not_quantifiable")
    if reasons:
        blocker_scope = (
            BLOCKER_SCOPE_B1_C1B
            if _trace_is_b1_decision(trace)
            else BLOCKER_SCOPE_B2_RETIREMENT
        )
    return SyntheticComparisonRow(
        tier_b_layer=trace.tier_b_layer,
        fixture_id=trace.fixture_id,
        fixture_class=trace.fixture_class,
        split=trace.split,
        replicate_id=trace.replicate_id,
        stress_role=trace.stress_role,
        production_like_bounds_status=trace.production_like_bounds_status,
        scan_density_stratum=trace.scan_density_stratum,
        integration_point_count=trace.integration_point_count,
        integration_width_min=trace.integration_width_min,
        raw_area=float(raw_area),
        true_area=trace.true_area,
        linear_edge_area=linear_area,
        asls_area=asls_area,
        linear_edge_abs_error=float(linear_error),
        asls_abs_error=float(asls_error),
        linear_edge_relative_error_pct=_relative_error_pct(
            linear_error,
            trace.true_area,
        ),
        asls_relative_error_pct=_relative_error_pct(asls_error, trace.true_area),
        asls_error_over_linear_error=(
            float(asls_error / linear_error) if linear_error > 0 else None
        ),
        asls_exceeds_raw_area=asls_exceeds_raw,
        asls_negative_nonblank_area=asls_negative_nonblank,
        blank_false_positive=blank_fp,
        blank_not_quantifiable=blank_not_quantifiable,
        asls_area_uncertainty=asls.area_uncertainty,
        asls_baseline_residual_mad=asls.baseline_residual_mad,
        asls_area_uncertainty_noise_source=asls.area_uncertainty_noise_source,
        blocker_scope=blocker_scope,
        row_status=ROW_STATUS_HARD_BLOCKER if reasons else ROW_STATUS_PASS,
        failure_reasons=tuple(reasons),
    )


def _trace_is_b1_decision(trace: SyntheticTrace) -> bool:
    return (
        trace.tier_b_layer == TIER_B1_RELEVANCE
        and trace.production_like_bounds_status == PRODUCTION_LIKE_IN_SCOPE
    )


def _relative_error_pct(error: float, true_area: float) -> float | None:
    if true_area <= 0:
        return None
    return float(error / true_area * 100.0)


def _p95(values: Sequence[float]) -> float:
    sorted_values = sorted(float(value) for value in values)
    index = min(len(sorted_values) - 1, int(round(0.95 * (len(sorted_values) - 1))))
    return sorted_values[index]
