from collections.abc import Callable
from dataclasses import dataclass, replace
from typing import Literal

import numpy as np
from scipy.signal import find_peaks, peak_widths, savgol_filter

from xic_extractor.config import ExtractionConfig
from xic_extractor.peak_scoring import (
    ScoringContext,
    score_candidate,
    select_candidate_with_confidence,
)

PeakStatus = Literal["OK", "NO_SIGNAL", "WINDOW_TOO_SHORT", "PEAK_NOT_FOUND"]
LocalMinimumQualityFlag = Literal[
    "edge_clipped",
    "too_broad",
    "too_short",
    "low_scan_count",
    "low_top_edge_ratio",
    "low_scan_support",
    "low_trace_continuity",
    "poor_edge_recovery",
]

# preferred_rt 選峰時，若最靠近 anchor 的峰強度 < 最高峰的這個比例，改選最高峰
_ANCHOR_SELECTION_MIN_INTENSITY_RATIO: float = 0.2
_PREFERRED_RT_RECOVERY_PROMINENCE_FRACTION: float = 0.2
_PREFERRED_RT_RECOVERY_MIN_PROMINENCE_RATIO: float = 0.01
_PREFERRED_RT_RECOVERY_MAX_DELTA_MIN: float = 0.35
_RECOVERY_CANDIDATE_MIN_INTENSITY_RATIO: float = 0.03
_LOCAL_RECOVERY_RELATIVE_HEIGHT_FRACTION: float = 0.25
_LOCAL_RECOVERY_MIN_RELATIVE_HEIGHT: float = 0.01
_LOCAL_RECOVERY_ABSOLUTE_HEIGHT_FRACTION: float = 0.5
_LOCAL_RECOVERY_MIN_ABSOLUTE_HEIGHT: float = 5.0
_LOCAL_RECOVERY_TOP_EDGE_RATIO: float = 1.05
_LOCAL_RECOVERY_DURATION_MAX_MULTIPLIER: float = 1.5
_TRACE_CONTINUITY_MIN_SCORE: float = 0.70
_TRACE_CONTINUITY_SIGNIFICANT_STEP_FRACTION: float = 0.05


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
    selection_apex_rt: float
    selection_apex_intensity: float
    selection_apex_index: int
    raw_apex_rt: float
    raw_apex_intensity: float
    raw_apex_index: int
    prominence: float
    quality_flags: tuple[LocalMinimumQualityFlag, ...] = ()
    region_scan_count: int | None = None
    region_duration_min: float | None = None
    region_edge_ratio: float | None = None
    region_trace_continuity: float | None = None


@dataclass(frozen=True)
class LocalMinimumRegionQuality:
    flags: tuple[LocalMinimumQualityFlag, ...]
    scan_count: int
    duration_min: float
    edge_ratio: float | None
    trace_continuity: float | None


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
    confidence: str | None = None
    reason: str | None = None
    severities: tuple[tuple[int, str], ...] = ()


def find_peak_and_area(
    rt: np.ndarray,
    intensity: np.ndarray,
    config: ExtractionConfig,
    *,
    preferred_rt: float | None = None,
    strict_preferred_rt: bool = False,
    scoring_context_builder: Callable[[PeakCandidate], ScoringContext] | None = None,
    istd_confidence_note: str | None = None,
) -> PeakDetectionResult:
    candidates_result = find_peak_candidates(rt, intensity, config)
    chosen_confidence: str | None = None
    chosen_reason: str | None = None
    chosen_severities: tuple[tuple[int, str], ...] = ()
    if candidates_result.status == "OK":
        preliminary_candidate = _select_candidate(
            candidates_result.candidates,
            preferred_rt=preferred_rt,
            strict_preferred_rt=strict_preferred_rt,
        )
        recovery_candidate, recovery_result = _preferred_rt_recovery(
            rt,
            intensity,
            config,
            preferred_rt=preferred_rt,
            strict_preferred_rt=strict_preferred_rt,
            current_candidate=preliminary_candidate,
        )
        all_candidates = candidates_result.candidates
        result_for_output = candidates_result
        if recovery_candidate is not None and recovery_result is not None:
            all_candidates = _append_candidate_once(all_candidates, recovery_candidate)
            result_for_output = _with_candidates(candidates_result, all_candidates)

        if scoring_context_builder is not None:
            scored_candidates = [
                _score_with_context(
                    candidate,
                    scoring_context_builder(candidate),
                    istd_confidence_note=istd_confidence_note,
                )
                for candidate in all_candidates
            ]
            selection_rt = _selection_rt_for_scored_candidates(
                candidates_result.candidates,
                preferred_rt=preferred_rt,
                strict_preferred_rt=strict_preferred_rt,
            )
            if recovery_candidate is not None and recovery_result is not None:
                selection_rt = preferred_rt
            chosen = select_candidate_with_confidence(
                scored_candidates,
                selection_rt=selection_rt,
                strict_selection_rt=strict_preferred_rt,
            )
            best_candidate = chosen.candidate
            chosen_confidence = chosen.confidence.value
            chosen_reason = chosen.reason
            chosen_severities = chosen.severities
        else:
            if recovery_candidate is not None and recovery_result is not None:
                return _detection_success(
                    result_for_output,
                    recovery_candidate,
                )
            best_candidate = _select_candidate(
                all_candidates,
                preferred_rt=preferred_rt,
                strict_preferred_rt=strict_preferred_rt,
            )
        return _detection_success(
            result_for_output,
            best_candidate,
            confidence=chosen_confidence,
            reason=chosen_reason,
            severities=chosen_severities,
        )

    recovery_candidate, recovery_result = _preferred_rt_recovery(
        rt,
        intensity,
        config,
        preferred_rt=preferred_rt,
        strict_preferred_rt=strict_preferred_rt,
        current_candidate=None,
    )
    if recovery_candidate is not None and recovery_result is not None:
        if scoring_context_builder is not None:
            scored_recovery = _score_with_context(
                recovery_candidate,
                scoring_context_builder(recovery_candidate),
                istd_confidence_note=istd_confidence_note,
            )
            return _detection_success(
                recovery_result,
                recovery_candidate,
                confidence=scored_recovery.confidence.value,
                reason=scored_recovery.reason,
                severities=scored_recovery.severities,
            )
        return _detection_success(recovery_result, recovery_candidate)
    return _detection_failure(candidates_result)


def _score_with_context(
    candidate: PeakCandidate,
    context: ScoringContext,
    *,
    istd_confidence_note: str | None,
):
    return score_candidate(
        candidate,
        context,
        prior_rt=context.rt_prior,
        istd_confidence_note=istd_confidence_note,
    )


def find_peak_candidates(
    rt: np.ndarray,
    intensity: np.ndarray,
    config: ExtractionConfig,
    *,
    peak_min_prominence_ratio: float | None = None,
) -> PeakCandidatesResult:
    resolver_mode = getattr(config, "resolver_mode", "legacy_savgol")
    if resolver_mode == "local_minimum":
        return _find_peak_candidates_local_minimum(rt, intensity, config)
    return _find_peak_candidates_legacy_savgol(
        rt,
        intensity,
        config,
        peak_min_prominence_ratio=peak_min_prominence_ratio,
    )


def _find_peak_candidates_legacy_savgol(
    rt: np.ndarray,
    intensity: np.ndarray,
    config: ExtractionConfig,
    *,
    peak_min_prominence_ratio: float | None = None,
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
        intensity_values,
        smoothed,
        max_smoothed,
        (
            config.peak_min_prominence_ratio
            if peak_min_prominence_ratio is None
            else peak_min_prominence_ratio
        ),
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
            selection_apex_idx=int(peak_idx),
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


def _find_peak_candidates_local_minimum(
    rt: np.ndarray,
    intensity: np.ndarray,
    config: ExtractionConfig,
) -> PeakCandidatesResult:
    rt_values, intensity_values = _as_matching_arrays(rt, intensity)
    n_points = len(intensity_values)
    if n_points == 0:
        return _candidate_failure("NO_SIGNAL", n_points, None)
    if n_points < max(config.resolver_min_scans, 3):
        return _candidate_failure("WINDOW_TOO_SHORT", n_points, None)

    max_intensity = float(np.max(intensity_values))
    if max_intensity <= 0:
        return _candidate_failure("NO_SIGNAL", n_points, max_intensity)

    threshold = _local_minimum_threshold(
        intensity_values,
        config.resolver_chrom_threshold,
    )
    peak_indices = _local_peak_indices(intensity_values)
    accepted_peaks = [
        peak_idx
        for peak_idx in peak_indices
        if _passes_local_peak_height_filters(
            intensity_values[peak_idx],
            max_intensity,
            config,
        )
    ]
    if not accepted_peaks:
        return _candidate_failure("PEAK_NOT_FOUND", n_points, max_intensity)

    regions = _local_minimum_regions(
        rt_values,
        intensity_values,
        accepted_peaks,
        threshold,
        config,
    )
    candidates: list[PeakCandidate] = []
    for left, right in regions:
        quality = _local_minimum_region_quality(
            rt_values,
            intensity_values,
            left=left,
            right=right,
            max_intensity=max_intensity,
            config=config,
        )
        if quality is None:
            continue
        candidates.append(
            _build_local_minimum_candidate(
                rt_values,
                intensity_values,
                left=left,
                right=right,
                quality=quality,
            )
        )
    candidates_result = tuple(candidates)
    if not candidates_result:
        return _candidate_failure("PEAK_NOT_FOUND", n_points, max_intensity)

    return PeakCandidatesResult(
        status="OK",
        candidates=candidates_result,
        n_points=n_points,
        max_smoothed=max_intensity,
        n_prominent_peaks=len(candidates_result),
    )


def _detection_success(
    candidates_result: PeakCandidatesResult,
    candidate: PeakCandidate,
    *,
    confidence: str | None = None,
    reason: str | None = None,
    severities: tuple[tuple[int, str], ...] = (),
) -> PeakDetectionResult:
    return PeakDetectionResult(
        status="OK",
        peak=candidate.peak,
        n_points=candidates_result.n_points,
        max_smoothed=candidates_result.max_smoothed,
        n_prominent_peaks=candidates_result.n_prominent_peaks,
        candidates=candidates_result.candidates,
        confidence=confidence,
        reason=reason,
        severities=severities,
    )


def _detection_failure(candidates_result: PeakCandidatesResult) -> PeakDetectionResult:
    return PeakDetectionResult(
        status=candidates_result.status,
        peak=None,
        n_points=candidates_result.n_points,
        max_smoothed=candidates_result.max_smoothed,
        n_prominent_peaks=candidates_result.n_prominent_peaks,
        candidates=candidates_result.candidates,
    )


def _append_candidate_once(
    candidates: tuple[PeakCandidate, ...],
    candidate: PeakCandidate,
) -> tuple[PeakCandidate, ...]:
    if any(existing is candidate for existing in candidates):
        return candidates
    return (*candidates, candidate)


def _with_candidates(
    candidates_result: PeakCandidatesResult,
    candidates: tuple[PeakCandidate, ...],
) -> PeakCandidatesResult:
    return PeakCandidatesResult(
        status=candidates_result.status,
        candidates=candidates,
        n_points=candidates_result.n_points,
        max_smoothed=candidates_result.max_smoothed,
        n_prominent_peaks=candidates_result.n_prominent_peaks,
    )


def _preferred_rt_recovery(
    rt: np.ndarray,
    intensity: np.ndarray,
    config: ExtractionConfig,
    *,
    preferred_rt: float | None,
    strict_preferred_rt: bool,
    current_candidate: PeakCandidate | None,
) -> tuple[PeakCandidate | None, PeakCandidatesResult | None]:
    if preferred_rt is None or strict_preferred_rt:
        return None, None
    if (
        current_candidate is not None
        and abs(current_candidate.selection_apex_rt - preferred_rt)
        <= _PREFERRED_RT_RECOVERY_MAX_DELTA_MIN
    ):
        return None, None

    resolver_mode = getattr(config, "resolver_mode", "legacy_savgol")
    if resolver_mode == "local_minimum":
        relaxed_config = _relaxed_local_minimum_recovery_config(config)
        if relaxed_config == config:
            return None, None
        relaxed_result = find_peak_candidates(
            rt,
            intensity,
            relaxed_config,
        )
    else:
        relaxed_ratio = max(
            _PREFERRED_RT_RECOVERY_MIN_PROMINENCE_RATIO,
            config.peak_min_prominence_ratio
            * _PREFERRED_RT_RECOVERY_PROMINENCE_FRACTION,
        )
        if relaxed_ratio >= config.peak_min_prominence_ratio:
            return None, None
        relaxed_result = find_peak_candidates(
            rt,
            intensity,
            config,
            peak_min_prominence_ratio=relaxed_ratio,
        )
    if relaxed_result.status != "OK":
        return None, None

    candidate = _select_preferred_recovery_candidate(
        relaxed_result.candidates,
        preferred_rt=preferred_rt,
    )
    if candidate is None:
        return None, None
    return candidate, relaxed_result


def _selection_rt_for_scored_candidates(
    candidates: tuple[PeakCandidate, ...],
    *,
    preferred_rt: float | None,
    strict_preferred_rt: bool,
) -> float | None:
    if preferred_rt is None or not candidates:
        return None
    if strict_preferred_rt:
        return preferred_rt

    nearest_candidate = min(
        candidates,
        key=lambda candidate: abs(candidate.selection_apex_rt - preferred_rt),
    )
    strongest_candidate = max(
        candidates, key=lambda candidate: candidate.selection_apex_intensity
    )
    if (
        nearest_candidate.selection_apex_intensity
        >= strongest_candidate.selection_apex_intensity
        * _ANCHOR_SELECTION_MIN_INTENSITY_RATIO
    ):
        return preferred_rt
    return None


def _relaxed_local_minimum_recovery_config(
    config: ExtractionConfig,
) -> ExtractionConfig:
    return replace(
        config,
        resolver_min_relative_height=max(
            _LOCAL_RECOVERY_MIN_RELATIVE_HEIGHT,
            config.resolver_min_relative_height
            * _LOCAL_RECOVERY_RELATIVE_HEIGHT_FRACTION,
        ),
        resolver_min_absolute_height=max(
            _LOCAL_RECOVERY_MIN_ABSOLUTE_HEIGHT,
            config.resolver_min_absolute_height
            * _LOCAL_RECOVERY_ABSOLUTE_HEIGHT_FRACTION,
        ),
        resolver_min_ratio_top_edge=min(
            config.resolver_min_ratio_top_edge,
            _LOCAL_RECOVERY_TOP_EDGE_RATIO,
        ),
        resolver_peak_duration_max=max(
            config.resolver_peak_duration_max,
            config.resolver_peak_duration_max
            * _LOCAL_RECOVERY_DURATION_MAX_MULTIPLIER,
        ),
    )


def _select_preferred_recovery_candidate(
    candidates: tuple[PeakCandidate, ...],
    *,
    preferred_rt: float,
) -> PeakCandidate | None:
    nearest_candidate = min(
        candidates,
        key=lambda candidate: abs(candidate.selection_apex_rt - preferred_rt),
    )
    delta = abs(nearest_candidate.selection_apex_rt - preferred_rt)
    if delta > _PREFERRED_RT_RECOVERY_MAX_DELTA_MIN:
        return None

    strongest_candidate = max(
        candidates, key=lambda candidate: candidate.selection_apex_intensity
    )
    if (
        nearest_candidate.selection_apex_intensity
        < strongest_candidate.selection_apex_intensity
        * _RECOVERY_CANDIDATE_MIN_INTENSITY_RATIO
    ):
        return None
    return nearest_candidate


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
        candidates, key=lambda candidate: candidate.selection_apex_intensity
    )
    if preferred_rt is None or len(candidates) == 1:
        return strongest_candidate

    # NL anchor 指向化合物實際 RT；多峰時優先選距 anchor 最近的峰。
    # paired analyte 已由 ISTD anchor 約束時強制尊重最近峰；其他路徑若最近峰
    # 強度 < 最高峰的 20%，anchor 可能是雜訊，回到選最高峰。
    nearest_candidate = min(
        candidates,
        key=lambda candidate: abs(candidate.selection_apex_rt - preferred_rt),
    )
    if strict_preferred_rt:
        return nearest_candidate
    if (
        nearest_candidate.selection_apex_intensity
        >= strongest_candidate.selection_apex_intensity
        * _ANCHOR_SELECTION_MIN_INTENSITY_RATIO
    ):
        return nearest_candidate
    return strongest_candidate


def _build_candidate(
    rt_values: np.ndarray,
    intensity_values: np.ndarray,
    smoothed: np.ndarray,
    *,
    selection_apex_idx: int,
    prominence: float,
    peak_rel_height: float,
) -> PeakCandidate:
    n_points = len(intensity_values)
    left, right = _peak_bounds(smoothed, selection_apex_idx, peak_rel_height, n_points)
    raw_apex_idx = _raw_apex_index(intensity_values, left, right)
    area = _integrate_area_counts_seconds(intensity_values, rt_values, left, right)

    peak = PeakResult(
        rt=float(rt_values[selection_apex_idx]),
        intensity=float(intensity_values[raw_apex_idx]),
        intensity_smoothed=float(smoothed[selection_apex_idx]),
        area=area,
        peak_start=float(rt_values[left]),
        peak_end=float(rt_values[right - 1]),
    )
    return PeakCandidate(
        peak=peak,
        selection_apex_rt=float(rt_values[selection_apex_idx]),
        selection_apex_intensity=float(smoothed[selection_apex_idx]),
        selection_apex_index=selection_apex_idx,
        raw_apex_rt=float(rt_values[raw_apex_idx]),
        raw_apex_intensity=peak.intensity,
        raw_apex_index=raw_apex_idx,
        prominence=prominence,
    )


def _build_local_minimum_candidate(
    rt_values: np.ndarray,
    intensity_values: np.ndarray,
    *,
    left: int,
    right: int,
    quality: LocalMinimumRegionQuality,
) -> PeakCandidate:
    raw_apex_idx = _raw_apex_index(intensity_values, left, right)
    apex_intensity = float(intensity_values[raw_apex_idx])
    edge_height = max(float(intensity_values[left]), float(intensity_values[right - 1]))
    area = _integrate_area_counts_seconds(intensity_values, rt_values, left, right)

    peak = PeakResult(
        rt=float(rt_values[raw_apex_idx]),
        intensity=apex_intensity,
        intensity_smoothed=apex_intensity,
        area=area,
        peak_start=float(rt_values[left]),
        peak_end=float(rt_values[right - 1]),
    )
    return PeakCandidate(
        peak=peak,
        selection_apex_rt=peak.rt,
        selection_apex_intensity=apex_intensity,
        selection_apex_index=raw_apex_idx,
        raw_apex_rt=peak.rt,
        raw_apex_intensity=apex_intensity,
        raw_apex_index=raw_apex_idx,
        prominence=max(0.0, apex_intensity - edge_height),
        quality_flags=quality.flags,
        region_scan_count=quality.scan_count,
        region_duration_min=quality.duration_min,
        region_edge_ratio=quality.edge_ratio,
        region_trace_continuity=quality.trace_continuity,
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


def _local_minimum_threshold(
    intensity_values: np.ndarray, chrom_threshold: float
) -> float:
    baseline = float(np.min(intensity_values))
    apex = float(np.max(intensity_values))
    return baseline + (apex - baseline) * chrom_threshold


def _local_peak_indices(intensity_values: np.ndarray) -> list[int]:
    peak_indices = [int(index) for index in find_peaks(intensity_values)[0]]
    if len(intensity_values) == 1:
        return [0]
    if intensity_values[0] > intensity_values[1]:
        peak_indices.insert(0, 0)
    if intensity_values[-1] > intensity_values[-2]:
        peak_indices.append(len(intensity_values) - 1)
    if not peak_indices:
        peak_indices.append(int(np.argmax(intensity_values)))
    return sorted(set(peak_indices))


def _passes_local_peak_height_filters(
    apex_intensity: float,
    max_intensity: float,
    config: ExtractionConfig,
) -> bool:
    return (
        apex_intensity >= config.resolver_min_absolute_height
        and apex_intensity >= max_intensity * config.resolver_min_relative_height
    )


def _local_minimum_regions(
    rt_values: np.ndarray,
    intensity_values: np.ndarray,
    peak_indices: list[int],
    threshold: float,
    config: ExtractionConfig,
) -> list[tuple[int, int]]:
    if len(peak_indices) == 1:
        peak_idx = peak_indices[0]
        return [
            (
                _left_threshold_boundary(intensity_values, peak_idx, threshold),
                _right_threshold_boundary(intensity_values, peak_idx, threshold),
            )
        ]

    regions: list[tuple[int, int]] = []
    region_left = _left_threshold_boundary(intensity_values, peak_indices[0], threshold)
    last_peak = peak_indices[0]
    for peak_idx in peak_indices[1:]:
        valley_idx = _valley_index(intensity_values, last_peak, peak_idx)
        if _should_split_local_region(
            rt_values,
            intensity_values,
            left_peak=last_peak,
            right_peak=peak_idx,
            valley_idx=valley_idx,
            config=config,
        ):
            regions.append((region_left, valley_idx + 1))
            region_left = min(valley_idx + 1, peak_idx)
        last_peak = peak_idx
    region_right = _right_threshold_boundary(
        intensity_values,
        peak_indices[-1],
        threshold,
    )
    regions.append((region_left, region_right))
    return regions


def _left_threshold_boundary(
    intensity_values: np.ndarray, peak_idx: int, threshold: float
) -> int:
    left = peak_idx
    while left > 0 and intensity_values[left - 1] > threshold:
        left -= 1
    return left


def _right_threshold_boundary(
    intensity_values: np.ndarray, peak_idx: int, threshold: float
) -> int:
    right = peak_idx + 1
    while right < len(intensity_values) and intensity_values[right] > threshold:
        right += 1
    return right


def _valley_index(intensity_values: np.ndarray, left_peak: int, right_peak: int) -> int:
    valley_slice = intensity_values[left_peak : right_peak + 1]
    return left_peak + int(np.argmin(valley_slice))


def _should_split_local_region(
    rt_values: np.ndarray,
    intensity_values: np.ndarray,
    *,
    left_peak: int,
    right_peak: int,
    valley_idx: int,
    config: ExtractionConfig,
) -> bool:
    if (
        rt_values[right_peak] - rt_values[left_peak]
        < config.resolver_min_search_range_min
    ):
        return False
    valley_height = float(intensity_values[valley_idx])
    if valley_height <= 0:
        return True
    left_ratio = float(intensity_values[left_peak]) / valley_height
    right_ratio = float(intensity_values[right_peak]) / valley_height
    return (
        left_ratio >= config.resolver_min_ratio_top_edge
        and right_ratio >= config.resolver_min_ratio_top_edge
    )


def _local_minimum_region_quality(
    rt_values: np.ndarray,
    intensity_values: np.ndarray,
    *,
    left: int,
    right: int,
    max_intensity: float,
    config: ExtractionConfig,
) -> LocalMinimumRegionQuality | None:
    scan_count = right - left
    duration = float(rt_values[right - 1] - rt_values[left])

    apex_idx = _raw_apex_index(intensity_values, left, right)
    apex_intensity = float(intensity_values[apex_idx])
    if not _passes_local_peak_height_filters(apex_intensity, max_intensity, config):
        return None

    edge_height = max(float(intensity_values[left]), float(intensity_values[right - 1]))
    edge_ratio = (
        None if edge_height <= 0 else float(apex_intensity / edge_height)
    )
    trace_continuity = _trace_continuity_score(
        intensity_values,
        left=left,
        right=right,
    )
    flags: list[LocalMinimumQualityFlag] = []
    if left == 0 or right == len(intensity_values):
        flags.append("edge_clipped")
    if scan_count < config.resolver_min_scans:
        flags.append("low_scan_support")
    if duration < config.resolver_peak_duration_min:
        flags.append("too_short")
    if duration > config.resolver_peak_duration_max:
        flags.append("too_broad")
    if (
        edge_ratio is not None
        and edge_ratio < config.resolver_min_ratio_top_edge
    ):
        flags.append("poor_edge_recovery")
    if (
        trace_continuity is not None
        and trace_continuity < _TRACE_CONTINUITY_MIN_SCORE
    ):
        flags.append("low_trace_continuity")
    return LocalMinimumRegionQuality(
        flags=tuple(flags),
        scan_count=scan_count,
        duration_min=duration,
        edge_ratio=edge_ratio,
        trace_continuity=trace_continuity,
    )


def _trace_continuity_score(
    intensity_values: np.ndarray,
    *,
    left: int,
    right: int,
) -> float | None:
    region = np.asarray(intensity_values[left:right], dtype=float)
    if len(region) < 5:
        return None
    apex = float(np.max(region))
    edge = max(float(region[0]), float(region[-1]))
    dynamic_range = apex - edge
    if dynamic_range <= 0:
        return 0.0

    diffs = np.diff(region)
    significant = np.abs(diffs) >= (
        dynamic_range * _TRACE_CONTINUITY_SIGNIFICANT_STEP_FRACTION
    )
    signs = np.sign(diffs[significant])
    if len(signs) <= 2:
        return 1.0
    sign_changes = int(np.count_nonzero(signs[1:] != signs[:-1]))
    return max(0.0, 1.0 - sign_changes / max(1, len(signs) - 1))


def _peak_bounds(
    smoothed: np.ndarray, best_idx: int, peak_rel_height: float, n_points: int
) -> tuple[int, int]:
    widths = peak_widths(smoothed, [best_idx], rel_height=peak_rel_height)
    left = max(0, int(np.floor(widths[2][0])))
    right = min(n_points, int(np.ceil(widths[3][0])) + 1)
    return left, right
