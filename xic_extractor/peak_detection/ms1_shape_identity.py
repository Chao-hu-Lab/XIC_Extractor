from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

DEFAULT_OWN_MAX_SMOOTH_POINTS = 15
DEFAULT_LOCAL_HALF_WINDOW_MIN = 0.35
DEFAULT_LOCAL_GRID_SIZE = 175
DEFAULT_COMPETING_EXCLUSION_WINDOW_MIN = 0.20
DEFAULT_COMPETING_MIN_RATIO = 0.05


@dataclass(frozen=True)
class OwnMaxTrace:
    status: str
    reason: str
    rt: tuple[float, ...] = ()
    intensity: tuple[float, ...] = ()
    max_intensity: float | None = None

    @property
    def is_usable(self) -> bool:
        return self.status == "ok"


@dataclass(frozen=True)
class ShapeSimilarityResult:
    status: str
    reason: str
    similarity: float | None = None
    compared_point_count: int = 0

    @property
    def is_usable(self) -> bool:
        return self.status == "ok" and self.similarity is not None


@dataclass(frozen=True)
class CompetingPeakSummary:
    status: str
    reason: str
    strongest_peak_rt_min: float | None = None
    strongest_peak_own_max_ratio: float | None = None
    strongest_competing_peak_rt_min: float | None = None
    strongest_competing_peak_own_max_ratio: float | None = None

    @property
    def has_competing_peak(self) -> bool:
        return self.strongest_competing_peak_own_max_ratio is not None


def gaussian_smooth_values(
    values: Sequence[float | int | None],
    *,
    points: int = DEFAULT_OWN_MAX_SMOOTH_POINTS,
) -> tuple[float, ...]:
    array = _float_array(values)
    if points < 3 or array.size < 3:
        return tuple(float(value) for value in array)
    window = min(points, array.size)
    if window % 2 == 0:
        window -= 1
    if window < 3:
        return tuple(float(value) for value in array)
    sigma = window / 6.0
    offsets = np.arange(window, dtype=float) - (window - 1) / 2.0
    kernel = np.exp(-0.5 * (offsets / sigma) ** 2)
    kernel = kernel / float(np.sum(kernel))
    pad = window // 2
    padded = np.pad(array, pad_width=pad, mode="edge")
    smoothed = np.convolve(padded, kernel, mode="valid")
    return tuple(float(value) for value in smoothed)


def own_max_normalized_trace(
    rt: Sequence[float | int | None],
    intensity: Sequence[float | int | None],
    *,
    smooth_points: int = DEFAULT_OWN_MAX_SMOOTH_POINTS,
) -> OwnMaxTrace:
    rt_array = _float_array(rt)
    intensity_array = _float_array(intensity)
    if rt_array.size != intensity_array.size:
        return OwnMaxTrace("inconclusive", "length_mismatch")
    mask = np.isfinite(rt_array) & np.isfinite(intensity_array)
    if int(np.sum(mask)) == 0:
        return OwnMaxTrace("inconclusive", "no_finite_points")
    rt_array = rt_array[mask]
    intensity_array = intensity_array[mask]
    if rt_array.size < 3:
        return OwnMaxTrace("inconclusive", "too_few_points")
    order = np.argsort(rt_array)
    rt_array = rt_array[order]
    smoothed = np.asarray(
        gaussian_smooth_values(intensity_array[order], points=smooth_points),
        dtype=float,
    )
    max_intensity = float(np.max(smoothed)) if smoothed.size else 0.0
    if max_intensity <= 0:
        return OwnMaxTrace("inconclusive", "non_positive_signal")
    normalized = smoothed / max_intensity
    return OwnMaxTrace(
        "ok",
        "own_max_normalized",
        tuple(float(value) for value in rt_array),
        tuple(float(value) for value in normalized),
        max_intensity,
    )


def local_own_max_shape_similarity(
    *,
    candidate_rt_min: float,
    candidate_rt: Sequence[float | int | None],
    candidate_intensity: Sequence[float | int | None],
    reference_rt_min: float,
    reference_rt: Sequence[float | int | None],
    reference_intensity: Sequence[float | int | None],
    half_window_min: float = DEFAULT_LOCAL_HALF_WINDOW_MIN,
    grid_size: int = DEFAULT_LOCAL_GRID_SIZE,
    smooth_points: int = DEFAULT_OWN_MAX_SMOOTH_POINTS,
) -> ShapeSimilarityResult:
    if grid_size < 5:
        return ShapeSimilarityResult("inconclusive", "grid_too_small")
    grid = np.linspace(-half_window_min, half_window_min, grid_size)
    candidate = _local_own_max_curve(
        candidate_rt,
        candidate_intensity,
        apex_rt_min=candidate_rt_min,
        grid=grid,
        smooth_points=smooth_points,
    )
    reference = _local_own_max_curve(
        reference_rt,
        reference_intensity,
        apex_rt_min=reference_rt_min,
        grid=grid,
        smooth_points=smooth_points,
    )
    similarity, count = _pearson_similarity(candidate, reference)
    if similarity is None:
        return ShapeSimilarityResult(
            "inconclusive",
            "similarity_unavailable",
            None,
            count,
        )
    return ShapeSimilarityResult(
        "ok",
        "local_own_max_shape_similarity",
        similarity,
        count,
    )


def competing_peak_summary(
    rt: Sequence[float | int | None],
    intensity: Sequence[float | int | None],
    *,
    candidate_rt_min: float,
    exclusion_window_min: float = DEFAULT_COMPETING_EXCLUSION_WINDOW_MIN,
    min_peak_ratio: float = DEFAULT_COMPETING_MIN_RATIO,
    smooth_points: int = DEFAULT_OWN_MAX_SMOOTH_POINTS,
) -> CompetingPeakSummary:
    normalized = own_max_normalized_trace(
        rt,
        intensity,
        smooth_points=smooth_points,
    )
    if not normalized.is_usable:
        return CompetingPeakSummary(normalized.status, normalized.reason)
    rt_array = np.asarray(normalized.rt, dtype=float)
    intensity_array = np.asarray(normalized.intensity, dtype=float)
    peaks = _local_maxima(rt_array, intensity_array, min_height=min_peak_ratio)
    if not peaks:
        return CompetingPeakSummary("inconclusive", "no_local_maxima")
    strongest = peaks[0]
    competing = next(
        (
            peak
            for peak in peaks
            if abs(peak[0] - candidate_rt_min) > exclusion_window_min
        ),
        None,
    )
    return CompetingPeakSummary(
        "ok",
        "competing_peak_summary",
        strongest_peak_rt_min=strongest[0],
        strongest_peak_own_max_ratio=strongest[1],
        strongest_competing_peak_rt_min=None if competing is None else competing[0],
        strongest_competing_peak_own_max_ratio=(
            None if competing is None else competing[1]
        ),
    )


def _local_own_max_curve(
    rt: Sequence[float | int | None],
    intensity: Sequence[float | int | None],
    *,
    apex_rt_min: float,
    grid: np.ndarray,
    smooth_points: int,
) -> np.ndarray:
    rt_array = _float_array(rt)
    intensity_array = _float_array(intensity)
    if rt_array.size != intensity_array.size or rt_array.size < 3:
        return np.full_like(grid, np.nan, dtype=float)
    relative_rt = rt_array - apex_rt_min
    mask = (
        np.isfinite(relative_rt)
        & np.isfinite(intensity_array)
        & (relative_rt >= float(grid[0]))
        & (relative_rt <= float(grid[-1]))
    )
    if int(np.sum(mask)) < 3:
        return np.full_like(grid, np.nan, dtype=float)
    relative_rt = relative_rt[mask]
    intensity_array = intensity_array[mask]
    order = np.argsort(relative_rt)
    relative_rt = relative_rt[order]
    smoothed = np.asarray(
        gaussian_smooth_values(intensity_array[order], points=smooth_points),
        dtype=float,
    )
    max_intensity = float(np.max(smoothed)) if smoothed.size else 0.0
    if max_intensity <= 0:
        return np.full_like(grid, np.nan, dtype=float)
    return np.interp(
        grid,
        relative_rt,
        smoothed / max_intensity,
        left=np.nan,
        right=np.nan,
    )


def _local_maxima(
    rt: np.ndarray,
    intensity: np.ndarray,
    *,
    min_height: float,
) -> tuple[tuple[float, float], ...]:
    peaks: list[tuple[float, float]] = []
    for index in range(1, len(intensity) - 1):
        value = float(intensity[index])
        if not math.isfinite(value) or value < min_height:
            continue
        left = float(intensity[index - 1])
        right = float(intensity[index + 1])
        if value >= left and value >= right and (value > left or value > right):
            peaks.append((float(rt[index]), value))
    peaks.sort(key=lambda peak: peak[1], reverse=True)
    deduplicated: list[tuple[float, float]] = []
    for peak_rt, peak_height in peaks:
        if all(abs(peak_rt - existing_rt) > 0.08 for existing_rt, _ in deduplicated):
            deduplicated.append((peak_rt, peak_height))
    return tuple(deduplicated)


def _pearson_similarity(
    values: np.ndarray,
    reference: np.ndarray,
) -> tuple[float | None, int]:
    mask = np.isfinite(values) & np.isfinite(reference)
    count = int(np.sum(mask))
    if count < 5:
        return None, count
    x = values[mask]
    y = reference[mask]
    if float(np.std(x)) <= 1e-12 or float(np.std(y)) <= 1e-12:
        return None, count
    return float(np.corrcoef(x, y)[0, 1]), count


def _float_array(values: Sequence[float | int | None]) -> np.ndarray:
    try:
        return np.asarray(tuple(values), dtype=float)
    except (TypeError, ValueError):
        return np.array([], dtype=float)
