from collections.abc import Callable

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
from xic_extractor.peak_detection.recovery import preferred_rt_recovery
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
        recovery_candidate, recovery_result = preferred_rt_recovery(
            rt,
            intensity,
            config,
            preferred_rt=preferred_rt,
            strict_preferred_rt=strict_preferred_rt,
            current_candidate=preliminary_candidate,
            candidate_finder=find_peak_candidates,
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

    recovery_candidate, recovery_result = preferred_rt_recovery(
        rt,
        intensity,
        config,
        preferred_rt=preferred_rt,
        strict_preferred_rt=strict_preferred_rt,
        current_candidate=None,
        candidate_finder=find_peak_candidates,
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




