"""MS1 shape and coverage evidence for family overlay diagnostics."""

from __future__ import annotations

import math
from collections.abc import Iterable, Sequence

import numpy as np

from tools.diagnostics.family_ms1_overlay_models import (
    ABSOLUTE_TRACE_APEX_CLUSTER_FRACTION_MIN,
    APEX_ALIGN_GRID_SIZE,
    APEX_ALIGN_HALF_WINDOW_MIN,
    DDA_TRIGGER_HEIGHT_RATIO_MIN,
    DDA_TRIGGER_SHAPE_SUPPORT_FRACTION_MIN,
    FAMILY_SHAPE_SUPPORT_FRACTION_MIN,
    GLOBAL_APEX_CONFLICT_DELTA_MIN,
    GLOBAL_APEX_REVIEW_FRACTION_MIN,
    LOCAL_APEX_SUPPORT_DELTA_MIN,
    LOW_LOCAL_TO_GLOBAL_RATIO,
    MS1_ASSESSABLE_COVERAGE_MIN,
    SHAPE_SUPPORT_MIN,
    TraceOverlayRow,
)


def build_family_ms1_evidence_summary(
    rows: Sequence[TraceOverlayRow],
) -> dict[str, int | float | str | bool | None]:
    shape_similarity = _apex_aligned_shape_similarity(rows)
    absolute_shape_similarity = _absolute_own_max_shape_similarity(rows)
    detected = [row for row in rows if row.status == "detected"]
    rescued = [row for row in rows if row.status == "rescued"]
    status_rows = [row for row in rows if row.status in {"detected", "rescued"}]
    evaluable = [
        row
        for row in status_rows
        if shape_similarity.get(row.sample_stem) is not None
    ]
    shape_supported = [
        row
        for row in evaluable
        if (shape_similarity.get(row.sample_stem) or 0.0) >= SHAPE_SUPPORT_MIN
    ]
    absolute_shape_evaluable = [
        row
        for row in status_rows
        if absolute_shape_similarity.get(row.sample_stem) is not None
    ]
    absolute_shape_supported = [
        row
        for row in absolute_shape_evaluable
        if (absolute_shape_similarity.get(row.sample_stem) or 0.0) >= SHAPE_SUPPORT_MIN
    ]
    (
        absolute_trace_apex_assessable,
        absolute_trace_apex_clustered,
        absolute_trace_apex_median_rt,
        absolute_trace_apex_delta_abs_median,
    ) = _absolute_trace_apex_cluster(status_rows)
    global_apex_assessable = [
        row for row in status_rows if _global_trace_apex_delta(row) is not None
    ]
    selected_apex_in_trace_window = [
        row for row in status_rows if _selected_apex_in_trace_window(row)
    ]
    global_apex_interference = [
        row
        for row in global_apex_assessable
        if _abs_or_none(_global_trace_apex_delta(row)) is not None
        and (_abs_or_none(_global_trace_apex_delta(row)) or 0.0)
        > GLOBAL_APEX_CONFLICT_DELTA_MIN
    ]
    local_apex_assessable = [
        row for row in status_rows if _local_window_peak(row)[0] is not None
    ]
    local_apex_supported = [
        row
        for row in local_apex_assessable
        if _abs_or_none(_local_window_peak(row)[0]) is not None
        and (_abs_or_none(_local_window_peak(row)[0]) or 0.0)
        <= LOCAL_APEX_SUPPORT_DELTA_MIN
    ]
    low_local_to_global = [
        row
        for row in evaluable
        if _local_to_global_max_ratio(row) is not None
        and (_local_to_global_max_ratio(row) or 0.0) < LOW_LOCAL_TO_GLOBAL_RATIO
    ]
    shape_fraction = _safe_fraction(len(shape_supported), len(evaluable))
    global_apex_assessable_fraction = _safe_fraction(
        len(global_apex_assessable),
        len(status_rows),
    )
    selected_apex_in_trace_window_fraction = _safe_fraction(
        len(selected_apex_in_trace_window),
        len(status_rows),
    )
    global_interference_fraction = _safe_fraction(
        len(global_apex_interference),
        len(global_apex_assessable),
    )
    local_support_fraction = _safe_fraction(
        len(local_apex_supported),
        len(local_apex_assessable),
    )
    local_global_low_fraction = _safe_fraction(len(low_local_to_global), len(evaluable))
    absolute_shape_fraction = _safe_fraction(
        len(absolute_shape_supported),
        len(absolute_shape_evaluable),
    )
    absolute_trace_apex_cluster_fraction = _safe_fraction(
        len(absolute_trace_apex_clustered),
        len(absolute_trace_apex_assessable),
    )
    detected_height_median = _median_value(row.cell_height for row in detected)
    rescued_height_median = _median_value(row.cell_height for row in rescued)
    detected_local_max_median = _median_value(
        _local_window_peak(row)[1] for row in detected
    )
    rescued_local_max_median = _median_value(
        _local_window_peak(row)[1] for row in rescued
    )
    height_ratio = _positive_ratio(detected_height_median, rescued_height_median)
    local_max_ratio = _positive_ratio(
        detected_local_max_median,
        rescued_local_max_median,
    )
    dda_trigger_limited_ms2_support = (
        len(detected) >= 2
        and len(rescued) >= 2
        and shape_fraction is not None
        and shape_fraction >= DDA_TRIGGER_SHAPE_SUPPORT_FRACTION_MIN
        and (
            (height_ratio is not None and height_ratio >= DDA_TRIGGER_HEIGHT_RATIO_MIN)
            or (
                local_max_ratio is not None
                and local_max_ratio >= DDA_TRIGGER_HEIGHT_RATIO_MIN
            )
        )
    )

    enough_ms1_coverage = (
        global_apex_assessable_fraction is not None
        and global_apex_assessable_fraction >= MS1_ASSESSABLE_COVERAGE_MIN
        and selected_apex_in_trace_window_fraction is not None
        and selected_apex_in_trace_window_fraction >= MS1_ASSESSABLE_COVERAGE_MIN
    )
    has_low_selected_peak_dominance = (
        local_global_low_fraction is not None and local_global_low_fraction >= 0.50
    )
    apex_aligned_shape_support = (
        enough_ms1_coverage
        and shape_fraction is not None
        and shape_fraction >= FAMILY_SHAPE_SUPPORT_FRACTION_MIN
        and local_support_fraction is not None
        and local_support_fraction >= FAMILY_SHAPE_SUPPORT_FRACTION_MIN
        and not has_low_selected_peak_dominance
    )
    absolute_own_max_shape_support = (
        enough_ms1_coverage
        and absolute_shape_fraction is not None
        and absolute_shape_fraction >= FAMILY_SHAPE_SUPPORT_FRACTION_MIN
        and absolute_trace_apex_cluster_fraction is not None
        and absolute_trace_apex_cluster_fraction
        >= ABSOLUTE_TRACE_APEX_CLUSTER_FRACTION_MIN
        and not has_low_selected_peak_dominance
    )
    scaled_shape_support_overrides_global_interference = (
        apex_aligned_shape_support or absolute_own_max_shape_support
    )

    if len(detected) < 2:
        family_verdict = "insufficient_nl_seed_support"
    elif scaled_shape_support_overrides_global_interference:
        family_verdict = "ms1_shape_supports_family_backfill"
    elif (
        global_interference_fraction is not None
        and global_interference_fraction >= GLOBAL_APEX_REVIEW_FRACTION_MIN
    ):
        family_verdict = "review_required_neighboring_ms1_interference"
    elif not enough_ms1_coverage:
        family_verdict = "review_required_low_ms1_assessable_coverage"
    elif has_low_selected_peak_dominance:
        family_verdict = "review_required_low_selected_peak_dominance"
    else:
        family_verdict = "review_required_uncertain_ms1_shape"

    return {
        "family_verdict": family_verdict,
        "trace_count": len(rows),
        "detected_count": len(detected),
        "rescued_count": len(rescued),
        "detected_rescued_count": len(status_rows),
        "evaluable_trace_count": len(evaluable),
        "global_apex_assessable_trace_count": len(global_apex_assessable),
        "global_apex_assessable_fraction": global_apex_assessable_fraction,
        "selected_apex_in_trace_window_count": len(selected_apex_in_trace_window),
        "selected_apex_in_trace_window_fraction": (
            selected_apex_in_trace_window_fraction
        ),
        "local_apex_assessable_trace_count": len(local_apex_assessable),
        "shape_supported_count": len(shape_supported),
        "shape_supported_fraction": shape_fraction,
        "absolute_own_max_evaluable_trace_count": len(absolute_shape_evaluable),
        "absolute_own_max_shape_supported_count": len(absolute_shape_supported),
        "absolute_own_max_shape_supported_fraction": absolute_shape_fraction,
        "absolute_trace_apex_assessable_count": len(absolute_trace_apex_assessable),
        "absolute_trace_apex_cluster_count": len(absolute_trace_apex_clustered),
        "absolute_trace_apex_cluster_fraction": absolute_trace_apex_cluster_fraction,
        "absolute_trace_apex_median_rt": absolute_trace_apex_median_rt,
        "absolute_trace_apex_delta_abs_median_min": (
            absolute_trace_apex_delta_abs_median
        ),
        "global_apex_interference_count": len(global_apex_interference),
        "global_apex_interference_fraction": global_interference_fraction,
        "local_apex_supported_count": len(local_apex_supported),
        "local_apex_supported_fraction": local_support_fraction,
        "low_selected_peak_dominance_count": len(low_local_to_global),
        "low_selected_peak_dominance_fraction": local_global_low_fraction,
        "dda_trigger_limited_ms2_support": dda_trigger_limited_ms2_support,
        "detected_height_median": detected_height_median,
        "rescued_height_median": rescued_height_median,
        "detected_to_rescued_height_median_ratio": height_ratio,
        "detected_local_window_max_median": detected_local_max_median,
        "rescued_local_window_max_median": rescued_local_max_median,
        "detected_to_rescued_local_window_max_median_ratio": local_max_ratio,
        "detected_shape_similarity_median": _median_value(
            shape_similarity.get(row.sample_stem) for row in detected
        ),
        "rescued_shape_similarity_median": _median_value(
            shape_similarity.get(row.sample_stem) for row in rescued
        ),
        "global_trace_apex_delta_abs_median_min": _median_value(
            _abs_or_none(_global_trace_apex_delta(row)) for row in evaluable
        ),
        "local_window_apex_delta_abs_median_min": _median_value(
            _abs_or_none(_local_window_peak(row)[0]) for row in evaluable
        ),
        "local_window_to_global_max_ratio_median": _median_value(
            _local_to_global_max_ratio(row) for row in evaluable
        ),
    }


def _apex_aligned_shape_similarity(
    rows: Sequence[TraceOverlayRow],
) -> dict[str, float | None]:
    grid = np.linspace(
        -APEX_ALIGN_HALF_WINDOW_MIN,
        APEX_ALIGN_HALF_WINDOW_MIN,
        APEX_ALIGN_GRID_SIZE,
    )
    traces: dict[str, np.ndarray] = {}
    for row in rows:
        rt, normalized = _apex_aligned_normalized_trace(row)
        if rt.size < 2:
            continue
        traces[row.sample_stem] = np.interp(
            grid,
            rt,
            normalized,
            left=np.nan,
            right=np.nan,
        )
    if not traces:
        return {}
    stack = np.vstack(tuple(traces.values()))
    finite_columns = np.isfinite(stack).any(axis=0)
    if not np.any(finite_columns):
        return {sample: None for sample in traces}
    median_trace = np.nanmedian(stack[:, finite_columns], axis=0)
    return {
        sample: _pearson_similarity(values[finite_columns], median_trace)
        for sample, values in traces.items()
    }


def _absolute_own_max_shape_similarity(
    rows: Sequence[TraceOverlayRow],
) -> dict[str, float | None]:
    traces: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    for row in rows:
        rt, normalized = _absolute_own_max_normalized_trace(row)
        if rt.size < 2:
            continue
        traces[row.sample_stem] = (rt, normalized)
    if not traces:
        return {}
    rt_min = max(float(rt[0]) for rt, _normalized in traces.values())
    rt_max = min(float(rt[-1]) for rt, _normalized in traces.values())
    if not math.isfinite(rt_min) or not math.isfinite(rt_max) or rt_max <= rt_min:
        return {sample: None for sample in traces}
    grid = np.linspace(rt_min, rt_max, APEX_ALIGN_GRID_SIZE)
    interpolated = {
        sample: np.interp(grid, rt, normalized, left=np.nan, right=np.nan)
        for sample, (rt, normalized) in traces.items()
    }
    stack = np.vstack(tuple(interpolated.values()))
    finite_columns = np.isfinite(stack).all(axis=0)
    if not np.any(finite_columns):
        return {sample: None for sample in interpolated}
    median_trace = np.nanmedian(stack[:, finite_columns], axis=0)
    return {
        sample: _pearson_similarity(values[finite_columns], median_trace)
        for sample, values in interpolated.items()
    }


def _absolute_own_max_normalized_trace(
    row: TraceOverlayRow,
    *,
    smooth_points: int = 0,
) -> tuple[np.ndarray, np.ndarray]:
    rt = np.asarray(row.rt, dtype=float)
    intensity = np.asarray(row.intensity, dtype=float)
    mask = np.isfinite(rt) & np.isfinite(intensity)
    if not np.any(mask):
        return np.array([], dtype=float), np.array([], dtype=float)
    rt = rt[mask]
    intensity = _gaussian_smooth_values(intensity[mask], points=smooth_points)
    order = np.argsort(rt)
    rt = rt[order]
    intensity = intensity[order]
    max_intensity = float(np.max(intensity)) if intensity.size else 0.0
    if max_intensity <= 0:
        return np.array([], dtype=float), np.array([], dtype=float)
    return rt, intensity / max_intensity


def _apex_aligned_normalized_trace(
    row: TraceOverlayRow,
    *,
    smooth_points: int = 0,
) -> tuple[np.ndarray, np.ndarray]:
    apex_rt = row.cell_apex_rt if row.cell_apex_rt is not None else row.trace_apex_rt
    if apex_rt is None or not math.isfinite(apex_rt):
        return np.array([], dtype=float), np.array([], dtype=float)
    rt = np.asarray(row.rt, dtype=float) - apex_rt
    intensity = np.asarray(row.intensity, dtype=float)
    mask = (
        np.isfinite(rt)
        & np.isfinite(intensity)
        & (rt >= -APEX_ALIGN_HALF_WINDOW_MIN)
        & (rt <= APEX_ALIGN_HALF_WINDOW_MIN)
    )
    if not np.any(mask):
        return np.array([], dtype=float), np.array([], dtype=float)
    local_intensity = _gaussian_smooth_values(intensity[mask], points=smooth_points)
    local_max = float(np.max(local_intensity)) if local_intensity.size else 0.0
    if local_max <= 0:
        return np.array([], dtype=float), np.array([], dtype=float)
    return rt[mask], local_intensity / local_max


def _absolute_trace_apex_cluster(
    rows: Sequence[TraceOverlayRow],
) -> tuple[list[TraceOverlayRow], list[TraceOverlayRow], float | None, float | None]:
    assessable = [
        row
        for row in rows
        if row.trace_apex_rt is not None and math.isfinite(row.trace_apex_rt)
    ]
    median_rt = _median_value(row.trace_apex_rt for row in assessable)
    if median_rt is None:
        return assessable, [], None, None
    clustered = [
        row
        for row in assessable
        if row.trace_apex_rt is not None
        and abs(row.trace_apex_rt - median_rt) <= GLOBAL_APEX_CONFLICT_DELTA_MIN
    ]
    delta_median = _median_value(
        abs(row.trace_apex_rt - median_rt)
        for row in assessable
        if row.trace_apex_rt is not None
    )
    return assessable, clustered, median_rt, delta_median


def _gaussian_smooth_values(values: np.ndarray, *, points: int) -> np.ndarray:
    if points < 3 or values.size < 3:
        return values.copy()
    window = min(points, values.size)
    if window % 2 == 0:
        window -= 1
    if window < 3:
        return values.copy()
    sigma = window / 6.0
    offsets = np.arange(window, dtype=float) - (window - 1) / 2.0
    kernel = np.exp(-0.5 * (offsets / sigma) ** 2)
    kernel = kernel / float(np.sum(kernel))
    pad = window // 2
    padded = np.pad(values, pad_width=pad, mode="edge")
    return np.convolve(padded, kernel, mode="valid")


def _pearson_similarity(
    values: np.ndarray,
    reference: np.ndarray,
) -> float | None:
    mask = np.isfinite(values) & np.isfinite(reference)
    if int(np.sum(mask)) < 5:
        return None
    x = values[mask]
    y = reference[mask]
    x_std = float(np.std(x))
    y_std = float(np.std(y))
    if x_std <= 1e-12 or y_std <= 1e-12:
        return None
    return float(np.corrcoef(x, y)[0, 1])


def _global_trace_apex_delta(row: TraceOverlayRow) -> float | None:
    if row.cell_apex_rt is None or row.trace_apex_rt is None:
        return None
    if not math.isfinite(row.cell_apex_rt) or not math.isfinite(row.trace_apex_rt):
        return None
    return row.trace_apex_rt - row.cell_apex_rt


def _local_window_peak(row: TraceOverlayRow) -> tuple[float | None, float | None]:
    apex_rt = row.cell_apex_rt if row.cell_apex_rt is not None else row.trace_apex_rt
    if apex_rt is None or not math.isfinite(apex_rt):
        return None, None
    rt = np.asarray(row.rt, dtype=float) - apex_rt
    intensity = np.asarray(row.intensity, dtype=float)
    mask = (
        np.isfinite(rt)
        & np.isfinite(intensity)
        & (rt >= -APEX_ALIGN_HALF_WINDOW_MIN)
        & (rt <= APEX_ALIGN_HALF_WINDOW_MIN)
    )
    if not np.any(mask):
        return None, None
    local_rt = rt[mask]
    local_intensity = intensity[mask]
    if local_intensity.size == 0:
        return None, None
    local_max = float(np.max(local_intensity))
    if local_max <= 0:
        return None, None
    index = int(np.argmax(local_intensity))
    return float(local_rt[index]), local_max


def _local_to_global_max_ratio(row: TraceOverlayRow) -> float | None:
    if row.trace_max_intensity <= 0:
        return None
    _delta, local_max = _local_window_peak(row)
    if local_max is None or local_max <= 0:
        return None
    return local_max / row.trace_max_intensity


def _selected_apex_in_trace_window(row: TraceOverlayRow) -> bool:
    if row.cell_apex_rt is None or not math.isfinite(row.cell_apex_rt):
        return False
    rt = _finite_values(row.rt)
    if not rt:
        return False
    tolerance = 1e-9
    return min(rt) - tolerance <= row.cell_apex_rt <= max(rt) + tolerance


def _abs_or_none(value: float | None) -> float | None:
    if value is None or not math.isfinite(value):
        return None
    return abs(value)


def _safe_fraction(numerator: int, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return numerator / denominator


def _positive_ratio(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator is None:
        return None
    if not math.isfinite(numerator) or not math.isfinite(denominator):
        return None
    if denominator <= 0:
        return None
    return numerator / denominator


def _finite_values(values: Iterable[float | None]) -> list[float]:
    return [value for value in values if value is not None and math.isfinite(value)]


def _median_value(values: Iterable[float | None]) -> float | None:
    finite = _finite_values(values)
    if not finite:
        return None
    return float(np.median(np.asarray(finite, dtype=float)))
