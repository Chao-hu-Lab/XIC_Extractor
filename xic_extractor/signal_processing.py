from collections.abc import Callable
from dataclasses import replace
from typing import Literal

import numpy as np
from scipy.signal import find_peaks, savgol_filter

from xic_extractor.config import ExtractionConfig
from xic_extractor.peak_detection.integration import (
    integrate_area_counts_seconds,
    peak_bounds,
    raw_apex_index,
)
from xic_extractor.peak_detection.models import (
    LocalMinimumQualityFlag,
    LocalMinimumRegionQuality,
    PeakCandidate,
    PeakCandidatesResult,
    PeakDetectionResult,
    PeakResult,
    PeakStatus,
)
from xic_extractor.peak_detection.selection import (
    select_candidate,
    selection_rt_for_scored_candidates,
)
from xic_extractor.peak_detection.trace_quality import (
    local_minimum_region_quality,
    passes_local_peak_height_filters,
)
from xic_extractor.peak_scoring import (
    ScoringContext,
    score_candidate,
    select_candidate_with_confidence,
)

__all__ = [
    "LocalMinimumQualityFlag",
    "LocalMinimumRegionQuality",
    "PeakCandidate",
    "PeakCandidatesResult",
    "PeakDetectionResult",
    "PeakResult",
    "PeakStatus",
    "find_peak_and_area",
    "find_peak_candidates",
]

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
        preliminary_candidate = select_candidate(
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
            selection_rt = selection_rt_for_scored_candidates(
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
            best_candidate = select_candidate(
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
        if passes_local_peak_height_filters(
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
        quality = local_minimum_region_quality(
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
    left, right = peak_bounds(smoothed, selection_apex_idx, peak_rel_height, n_points)
    raw_apex_idx = raw_apex_index(intensity_values, left, right)
    area = integrate_area_counts_seconds(intensity_values, rt_values, left, right)

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
    raw_apex_idx = raw_apex_index(intensity_values, left, right)
    apex_intensity = float(intensity_values[raw_apex_idx])
    edge_height = max(float(intensity_values[left]), float(intensity_values[right - 1]))
    area = integrate_area_counts_seconds(intensity_values, rt_values, left, right)

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




