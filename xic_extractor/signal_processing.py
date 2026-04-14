from dataclasses import dataclass
from typing import Literal

import numpy as np
from scipy.signal import find_peaks, peak_widths, savgol_filter

from xic_extractor.config import ExtractionConfig

PeakStatus = Literal["OK", "NO_SIGNAL", "WINDOW_TOO_SHORT", "PEAK_NOT_FOUND"]


@dataclass(frozen=True)
class PeakResult:
    rt: float
    intensity: float
    intensity_smoothed: float
    area: float
    peak_start: float
    peak_end: float


@dataclass(frozen=True)
class PeakDetectionResult:
    status: PeakStatus
    peak: PeakResult | None
    n_points: int
    max_smoothed: float | None
    n_prominent_peaks: int


def find_peak_and_area(
    rt: np.ndarray, intensity: np.ndarray, config: ExtractionConfig
) -> PeakDetectionResult:
    rt_values, intensity_values = _as_matching_arrays(rt, intensity)
    n_points = len(intensity_values)
    if n_points == 0:
        return _failure("NO_SIGNAL", n_points, None)
    if n_points < config.smooth_window:
        return _failure("WINDOW_TOO_SHORT", n_points, None)

    smoothed = savgol_filter(
        intensity_values, config.smooth_window, config.smooth_polyorder
    )
    max_smoothed = float(np.max(smoothed))
    if max_smoothed <= 0:
        return _failure("NO_SIGNAL", n_points, max_smoothed)

    prominence = _prominence_threshold(
        intensity_values, smoothed, max_smoothed, config.peak_min_prominence_ratio
    )
    peaks, _ = find_peaks(smoothed, prominence=prominence)
    if len(peaks) == 0:
        return _failure("PEAK_NOT_FOUND", n_points, max_smoothed)

    best_idx = int(peaks[np.argmax(smoothed[peaks])])
    left, right = _peak_bounds(smoothed, best_idx, config.peak_rel_height, n_points)
    area = float(np.trapezoid(intensity_values[left:right], rt_values[left:right]))

    return PeakDetectionResult(
        status="OK",
        peak=PeakResult(
            rt=float(rt_values[best_idx]),
            intensity=float(intensity_values[best_idx]),
            intensity_smoothed=float(smoothed[best_idx]),
            area=area,
            peak_start=float(rt_values[left]),
            peak_end=float(rt_values[right - 1]),
        ),
        n_points=n_points,
        max_smoothed=max_smoothed,
        n_prominent_peaks=len(peaks),
    )


def _as_matching_arrays(
    rt: np.ndarray, intensity: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    rt_values = np.asarray(rt, dtype=float)
    intensity_values = np.asarray(intensity, dtype=float)
    if len(rt_values) != len(intensity_values):
        raise ValueError("rt and intensity must have the same length")
    return rt_values, intensity_values


def _failure(
    status: Literal["NO_SIGNAL", "WINDOW_TOO_SHORT", "PEAK_NOT_FOUND"],
    n_points: int,
    max_smoothed: float | None,
) -> PeakDetectionResult:
    return PeakDetectionResult(
        status=status,
        peak=None,
        n_points=n_points,
        max_smoothed=max_smoothed,
        n_prominent_peaks=0,
    )


def _prominence_threshold(
    intensity: np.ndarray,
    smoothed: np.ndarray,
    max_smoothed: float,
    peak_min_prominence_ratio: float,
) -> float:
    residual = intensity - smoothed
    median = float(np.median(residual))
    mad = float(np.median(np.abs(residual - median)))
    noise_floor = 6.0 * 1.4826 * mad
    return max(max_smoothed * peak_min_prominence_ratio, noise_floor)


def _peak_bounds(
    smoothed: np.ndarray, best_idx: int, peak_rel_height: float, n_points: int
) -> tuple[int, int]:
    widths = peak_widths(smoothed, [best_idx], rel_height=peak_rel_height)
    left = max(0, int(np.floor(widths[2][0])))
    right = min(n_points, int(np.ceil(widths[3][0])) + 1)
    return left, right
