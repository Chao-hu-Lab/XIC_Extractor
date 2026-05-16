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
    PeakCandidate,
    PeakCandidatesResult,
    PeakDetectionResult,
)
from xic_extractor.peak_detection.recovery import preferred_rt_recovery
from xic_extractor.peak_detection.selection import (
    select_candidate,
    selection_rt_for_scored_candidates,
)
from xic_extractor.peak_scoring import (
    ScoringContext,
    score_breakdown_fields,
    score_candidate,
    select_candidate_with_confidence,
)


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
    chosen_score_breakdown: tuple[tuple[str, str], ...] = ()
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
            chosen_score_breakdown = score_breakdown_fields(chosen.evidence_score)
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
            score_breakdown=chosen_score_breakdown,
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
                score_breakdown=score_breakdown_fields(scored_recovery.evidence_score),
            )
        return _detection_success(recovery_result, recovery_candidate)
    return _detection_failure(candidates_result)


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
    if resolver_mode == "arbitrated":
        return _find_peak_candidates_arbitrated(
            rt,
            intensity,
            config,
            peak_min_prominence_ratio=peak_min_prominence_ratio,
        )
    return find_peak_candidates_legacy_savgol(
        rt,
        intensity,
        config,
        peak_min_prominence_ratio=peak_min_prominence_ratio,
    )


def _find_peak_candidates_arbitrated(
    rt: np.ndarray,
    intensity: np.ndarray,
    config: ExtractionConfig,
    *,
    peak_min_prominence_ratio: float | None,
) -> PeakCandidatesResult:
    legacy_result = find_peak_candidates_legacy_savgol(
        rt,
        intensity,
        config,
        peak_min_prominence_ratio=peak_min_prominence_ratio,
    )
    local_result = find_peak_candidates_local_minimum(rt, intensity, config)
    candidates = _merge_resolver_candidates(
        legacy_result.candidates,
        local_result.candidates,
    )
    if candidates:
        return PeakCandidatesResult(
            status="OK",
            candidates=candidates,
            n_points=max(legacy_result.n_points, local_result.n_points),
            max_smoothed=_max_result_smoothed(legacy_result, local_result),
            n_prominent_peaks=len(candidates),
        )
    return _strongest_failure_result(legacy_result, local_result)


def _merge_resolver_candidates(
    legacy_candidates: tuple[PeakCandidate, ...],
    local_candidates: tuple[PeakCandidate, ...],
) -> tuple[PeakCandidate, ...]:
    merged = list(legacy_candidates)
    for local_candidate in local_candidates:
        match_index = _matching_apex_index(merged, local_candidate)
        if match_index is None:
            merged.append(local_candidate)
            continue
        if _candidate_detail_score(local_candidate) > _candidate_detail_score(
            merged[match_index]
        ):
            merged[match_index] = local_candidate
    return tuple(merged)


def _matching_apex_index(
    candidates: list[PeakCandidate],
    candidate: PeakCandidate,
) -> int | None:
    for index, existing in enumerate(candidates):
        if existing.selection_apex_index == candidate.selection_apex_index:
            return index
    return None


def _candidate_detail_score(candidate: PeakCandidate) -> int:
    return len(candidate.quality_flags) + sum(
        value is not None
        for value in (
            candidate.region_scan_count,
            candidate.region_duration_min,
            candidate.region_edge_ratio,
            candidate.region_trace_continuity,
        )
    )


def _max_result_smoothed(
    first: PeakCandidatesResult,
    second: PeakCandidatesResult,
) -> float | None:
    values = [
        value
        for value in (first.max_smoothed, second.max_smoothed)
        if value is not None
    ]
    if not values:
        return None
    return max(values)


def _strongest_failure_result(
    legacy_result: PeakCandidatesResult,
    local_result: PeakCandidatesResult,
) -> PeakCandidatesResult:
    status_rank = {
        "WINDOW_TOO_SHORT": 3,
        "NO_SIGNAL": 2,
        "PEAK_NOT_FOUND": 1,
        "OK": 0,
    }
    return max(
        (legacy_result, local_result),
        key=lambda result: (
            status_rank[result.status],
            result.n_points,
            result.max_smoothed if result.max_smoothed is not None else 0.0,
        ),
    )


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


def _detection_success(
    candidates_result: PeakCandidatesResult,
    candidate: PeakCandidate,
    *,
    confidence: str | None = None,
    reason: str | None = None,
    severities: tuple[tuple[int, str], ...] = (),
    score_breakdown: tuple[tuple[str, str], ...] = (),
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
        score_breakdown=score_breakdown,
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
