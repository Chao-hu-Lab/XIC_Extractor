from collections.abc import Callable
from dataclasses import replace

import numpy as np

from xic_extractor.config import ExtractionConfig
from xic_extractor.peak_detection.legacy_savgol import (
    find_peak_candidates_legacy_savgol,
)
from xic_extractor.peak_detection.local_minimum import (
    find_peak_candidates_local_minimum,
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
        return find_peak_candidates_local_minimum(rt, intensity, config)
    return find_peak_candidates_legacy_savgol(
        rt,
        intensity,
        config,
        peak_min_prominence_ratio=peak_min_prominence_ratio,
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


