from dataclasses import dataclass
from typing import Literal

import numpy as np
from scipy.signal import find_peaks, peak_widths, savgol_filter

from xic_extractor.config import ExtractionConfig

PeakStatus = Literal["OK", "NO_SIGNAL", "WINDOW_TOO_SHORT", "PEAK_NOT_FOUND"]

# preferred_rt 選峰時，若最靠近 anchor 的峰強度 < 最高峰的這個比例，改選最高峰
_PREFERRED_RT_MIN_INTENSITY_RATIO: float = 0.2


@dataclass(frozen=True)
class PeakResult:
    rt: float
    intensity: float
    intensity_smoothed: float
    area: float
    peak_start: float
    peak_end: float


@dataclass(frozen=True)
class PeakCandidate:
    peak: PeakResult
    smoothed_apex_rt: float
    smoothed_apex_intensity: float
    smoothed_apex_index: int
    raw_apex_rt: float
    raw_apex_intensity: float
    raw_apex_index: int
    prominence: float


@dataclass(frozen=True)
class PeakCandidatesResult:
    status: PeakStatus
    candidates: tuple[PeakCandidate, ...]
    n_points: int
    max_smoothed: float | None
    n_prominent_peaks: int


@dataclass(frozen=True)
class PeakDetectionResult:
    status: PeakStatus
    peak: PeakResult | None
    n_points: int
    max_smoothed: float | None
    n_prominent_peaks: int
    candidates: tuple[PeakCandidate, ...] = ()


def find_peak_and_area(
    rt: np.ndarray,
    intensity: np.ndarray,
    config: ExtractionConfig,
    *,
    preferred_rt: float | None = None,
    strict_preferred_rt: bool = False,
) -> PeakDetectionResult:
    candidates_result = find_peak_candidates(rt, intensity, config)
    if candidates_result.status != "OK":
        return PeakDetectionResult(
            status=candidates_result.status,
            peak=None,
            n_points=candidates_result.n_points,
            max_smoothed=candidates_result.max_smoothed,
            n_prominent_peaks=candidates_result.n_prominent_peaks,
            candidates=candidates_result.candidates,
        )

    candidates = candidates_result.candidates
    best_candidate = _select_candidate(
        candidates,
        preferred_rt=preferred_rt,
        strict_preferred_rt=strict_preferred_rt,
    )
    return PeakDetectionResult(
        status="OK",
        peak=best_candidate.peak,
        n_points=candidates_result.n_points,
        max_smoothed=candidates_result.max_smoothed,
        n_prominent_peaks=candidates_result.n_prominent_peaks,
        candidates=candidates,
    )


def find_peak_candidates(
    rt: np.ndarray,
    intensity: np.ndarray,
    config: ExtractionConfig,
) -> PeakCandidatesResult:
    rt_values, intensity_values = _as_matching_arrays(rt, intensity)
    n_points = len(intensity_values)
    if n_points == 0:
        return _candidate_failure("NO_SIGNAL", n_points, None)
    if n_points < config.smooth_window:
        return _candidate_failure("WINDOW_TOO_SHORT", n_points, None)

    smoothed = savgol_filter(
        intensity_values, config.smooth_window, config.smooth_polyorder
    )
    max_smoothed = float(np.max(smoothed))
    if max_smoothed <= 0:
        return _candidate_failure("NO_SIGNAL", n_points, max_smoothed)

    prominence = _prominence_threshold(
        intensity_values, smoothed, max_smoothed, config.peak_min_prominence_ratio
    )
    peaks, properties = find_peaks(smoothed, prominence=prominence)
    if len(peaks) == 0:
        return _candidate_failure("PEAK_NOT_FOUND", n_points, max_smoothed)

    prominences = properties.get("prominences", np.zeros(len(peaks), dtype=float))
    candidates = tuple(
        _build_candidate(
            rt_values,
            intensity_values,
            smoothed,
            smoothed_apex_idx=int(peak_idx),
            prominence=float(prominences[index]),
            peak_rel_height=config.peak_rel_height,
        )
        for index, peak_idx in enumerate(peaks)
    )

    return PeakCandidatesResult(
        status="OK",
        candidates=candidates,
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


def _candidate_failure(
    status: Literal["NO_SIGNAL", "WINDOW_TOO_SHORT", "PEAK_NOT_FOUND"],
    n_points: int,
    max_smoothed: float | None,
) -> PeakCandidatesResult:
    return PeakCandidatesResult(
        status=status,
        candidates=(),
        n_points=n_points,
        max_smoothed=max_smoothed,
        n_prominent_peaks=0,
    )


def _select_candidate(
    candidates: tuple[PeakCandidate, ...],
    *,
    preferred_rt: float | None,
    strict_preferred_rt: bool,
) -> PeakCandidate:
    strongest_candidate = max(
        candidates, key=lambda candidate: candidate.smoothed_apex_intensity
    )
    if preferred_rt is None or len(candidates) == 1:
        return strongest_candidate

    # NL anchor 指向化合物實際 RT；多峰時優先選距 anchor 最近的峰。
    # paired analyte 已由 ISTD anchor 約束時強制尊重最近峰；其他路徑若最近峰
    # 強度 < 最高峰的 20%，anchor 可能是雜訊，回到選最高峰。
    nearest_candidate = min(
        candidates, key=lambda candidate: abs(candidate.smoothed_apex_rt - preferred_rt)
    )
    if strict_preferred_rt:
        return nearest_candidate
    if (
        nearest_candidate.smoothed_apex_intensity
        >= strongest_candidate.smoothed_apex_intensity
        * _PREFERRED_RT_MIN_INTENSITY_RATIO
    ):
        return nearest_candidate
    return strongest_candidate


def _build_candidate(
    rt_values: np.ndarray,
    intensity_values: np.ndarray,
    smoothed: np.ndarray,
    *,
    smoothed_apex_idx: int,
    prominence: float,
    peak_rel_height: float,
) -> PeakCandidate:
    n_points = len(intensity_values)
    left, right = _peak_bounds(smoothed, smoothed_apex_idx, peak_rel_height, n_points)
    raw_apex_idx = _raw_apex_index(intensity_values, left, right)
    area = _integrate_area_counts_seconds(intensity_values, rt_values, left, right)

    peak = PeakResult(
        rt=float(rt_values[raw_apex_idx]),
        intensity=float(intensity_values[raw_apex_idx]),
        intensity_smoothed=float(smoothed[raw_apex_idx]),
        area=area,
        peak_start=float(rt_values[left]),
        peak_end=float(rt_values[right - 1]),
    )
    return PeakCandidate(
        peak=peak,
        smoothed_apex_rt=float(rt_values[smoothed_apex_idx]),
        smoothed_apex_intensity=float(smoothed[smoothed_apex_idx]),
        smoothed_apex_index=smoothed_apex_idx,
        raw_apex_rt=peak.rt,
        raw_apex_intensity=peak.intensity,
        raw_apex_index=raw_apex_idx,
        prominence=prominence,
    )


def _raw_apex_index(intensity_values: np.ndarray, left: int, right: int) -> int:
    if right <= left:
        return left
    local_offset = int(np.argmax(intensity_values[left:right]))
    return left + local_offset


def _integrate_area_counts_seconds(
    intensity_values: np.ndarray,
    rt_values: np.ndarray,
    left: int,
    right: int,
) -> float:
    # Thermo returns rt in minutes, but LC-MS convention (Xcalibur, MassHunter,
    # manual integration) reports area in counts·seconds — convert so downstream
    # numbers match what chemists see in Xcalibur.
    area_counts_minutes = float(
        np.trapezoid(intensity_values[left:right], rt_values[left:right])
    )
    return area_counts_minutes * 60.0


def _prominence_threshold(
    intensity: np.ndarray,
    smoothed: np.ndarray,
    max_smoothed: float,
    peak_min_prominence_ratio: float,
) -> float:
    residual = intensity - smoothed
    median = float(np.median(residual))
    mad = float(np.median(np.abs(residual - median)))
    noise_floor = 3.0 * 1.4826 * mad
    return max(max_smoothed * peak_min_prominence_ratio, noise_floor)


def _peak_bounds(
    smoothed: np.ndarray, best_idx: int, peak_rel_height: float, n_points: int
) -> tuple[int, int]:
    widths = peak_widths(smoothed, [best_idx], rel_height=peak_rel_height)
    left = max(0, int(np.floor(widths[2][0])))
    right = min(n_points, int(np.ceil(widths[3][0])) + 1)
    return left, right
