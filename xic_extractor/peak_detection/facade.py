from collections.abc import Callable
from dataclasses import replace

import numpy as np

from xic_extractor.config import ExtractionConfig
from xic_extractor.peak_detection.chrom_peak_candidate_adapter import (
    chrom_peak_segment_candidates,
)
from xic_extractor.peak_detection.legacy_savgol import (
    find_peak_candidates_legacy_savgol,
)
from xic_extractor.peak_detection.local_minimum import (
    find_peak_candidates_local_minimum,
)
from xic_extractor.peak_detection.models import (
    PeakCandidate,
    PeakCandidateScore,
    PeakCandidatesResult,
    PeakDetectionResult,
)
from xic_extractor.peak_detection.recovery import preferred_rt_recovery
from xic_extractor.peak_detection.region_safe_merge import (
    apply_region_first_safe_merge,
)
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
from xic_extractor.settings_schema import (
    ARBITRATED_RESOLVER_RETIRED_MESSAGE,
    RESOLVER_MODES,
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
    if scoring_context_builder is not None:
        candidates_result = _augment_with_chrom_peak_segment_candidates(
            rt,
            intensity,
            config,
            candidates_result,
        )
    chosen_confidence: str | None = None
    chosen_reason: str | None = None
    chosen_severities: tuple[tuple[int, str], ...] = ()
    chosen_score_breakdown: tuple[tuple[str, str], ...] = ()
    candidate_scores: tuple[PeakCandidateScore, ...] = ()
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
            recovery_candidate, recovery_result = _mark_recovery_candidate(
                recovery_candidate,
                recovery_result,
            )
            all_candidates, recovery_candidate = _append_or_merge_recovery_candidate(
                all_candidates,
                recovery_candidate,
            )
            result_for_output = _with_candidates(candidates_result, all_candidates)

        selection_rt = selection_rt_for_scored_candidates(
            candidates_result.candidates,
            preferred_rt=preferred_rt,
            strict_preferred_rt=strict_preferred_rt,
        )
        if recovery_candidate is not None and recovery_result is not None:
            selection_rt = preferred_rt

        if scoring_context_builder is not None:
            scored_candidates = [
                _score_with_context(
                    candidate,
                    scoring_context_builder(candidate),
                    istd_confidence_note=istd_confidence_note,
                )
                for candidate in all_candidates
            ]
            candidate_scores = tuple(
                _candidate_score_summary(scored_candidate)
                for scored_candidate in scored_candidates
            )
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
                best_candidate = recovery_candidate
            else:
                best_candidate = select_candidate(
                    all_candidates,
                    preferred_rt=preferred_rt,
                    strict_preferred_rt=strict_preferred_rt,
                )
        result_for_output, best_candidate, candidate_scores = (
            _apply_region_first_safe_merge_if_enabled(
                rt,
                intensity,
                config,
                result_for_output,
                best_candidate,
                candidate_scores,
            )
        )
        return _detection_success(
            result_for_output,
            best_candidate,
            confidence=chosen_confidence,
            reason=chosen_reason,
            severities=chosen_severities,
            score_breakdown=chosen_score_breakdown,
            candidate_scores=candidate_scores,
            selection_reference_rt=selection_rt,
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
        recovery_candidate, recovery_result = _mark_recovery_candidate(
            recovery_candidate,
            recovery_result,
        )
        if scoring_context_builder is not None:
            scored_recovery = _score_with_context(
                recovery_candidate,
                scoring_context_builder(recovery_candidate),
                istd_confidence_note=istd_confidence_note,
            )
            candidate_scores = (_candidate_score_summary(scored_recovery),)
            recovery_result, recovery_candidate, candidate_scores = (
                _apply_region_first_safe_merge_if_enabled(
                    rt,
                    intensity,
                    config,
                    recovery_result,
                    recovery_candidate,
                    candidate_scores,
                )
            )
            return _detection_success(
                recovery_result,
                recovery_candidate,
                confidence=scored_recovery.confidence.value,
                reason=scored_recovery.reason,
                severities=scored_recovery.severities,
                score_breakdown=score_breakdown_fields(scored_recovery.evidence_score),
                candidate_scores=candidate_scores,
                selection_reference_rt=preferred_rt,
            )
        recovery_result, recovery_candidate, candidate_scores = (
            _apply_region_first_safe_merge_if_enabled(
                rt,
                intensity,
                config,
                recovery_result,
                recovery_candidate,
                candidate_scores,
            )
        )
        return _detection_success(
            recovery_result,
            recovery_candidate,
            selection_reference_rt=preferred_rt,
        )
    return _detection_failure(candidates_result)


def find_peak_candidates(
    rt: np.ndarray,
    intensity: np.ndarray,
    config: ExtractionConfig,
    *,
    peak_min_prominence_ratio: float | None = None,
) -> PeakCandidatesResult:
    resolver_mode = getattr(config, "resolver_mode", "legacy_savgol")
    if resolver_mode in {"local_minimum", "region_first_safe_merge"}:
        return find_peak_candidates_local_minimum(rt, intensity, config)
    if resolver_mode == "arbitrated":
        raise ValueError(ARBITRATED_RESOLVER_RETIRED_MESSAGE)
    if resolver_mode == "legacy_savgol":
        return find_peak_candidates_legacy_savgol(
            rt,
            intensity,
            config,
            peak_min_prominence_ratio=peak_min_prominence_ratio,
        )
    allowed = ", ".join(RESOLVER_MODES[:-1]) + f", or {RESOLVER_MODES[-1]}"
    raise ValueError(f"unsupported resolver mode {resolver_mode!r}; must be {allowed}")


def _augment_with_chrom_peak_segment_candidates(
    rt: np.ndarray,
    intensity: np.ndarray,
    config: ExtractionConfig,
    candidates_result: PeakCandidatesResult,
) -> PeakCandidatesResult:
    if getattr(config, "resolver_mode", "legacy_savgol") != "region_first_safe_merge":
        return candidates_result
    chrom_candidates = chrom_peak_segment_candidates(rt, intensity, config)
    if not chrom_candidates:
        return candidates_result
    candidates = candidates_result.candidates
    for candidate in chrom_candidates:
        candidates = _append_or_merge_chrom_peak_segment_candidate(
            candidates,
            candidate,
        )
    status = "OK" if candidates else candidates_result.status
    return replace(
        candidates_result,
        status=status,
        candidates=candidates,
        n_prominent_peaks=len(candidates),
    )


def _append_or_merge_chrom_peak_segment_candidate(
    candidates: tuple[PeakCandidate, ...],
    chrom_candidate: PeakCandidate,
) -> tuple[PeakCandidate, ...]:
    merged: list[PeakCandidate] = []
    replaced = False
    for candidate in candidates:
        if _same_chrom_peak_segment_identity(candidate, chrom_candidate):
            merged.append(_chrom_boundary_upgrade_candidate(candidate, chrom_candidate))
            replaced = True
        else:
            merged.append(candidate)
    if not replaced:
        merged.append(chrom_candidate)
    return tuple(merged)


def _same_chrom_peak_segment_identity(
    candidate: PeakCandidate,
    chrom_candidate: PeakCandidate,
) -> bool:
    if _same_peak_candidate_identity(candidate, chrom_candidate):
        return True
    if candidate.selection_apex_index == chrom_candidate.selection_apex_index:
        return True
    return abs(candidate.selection_apex_rt - chrom_candidate.selection_apex_rt) <= 1e-9


def _chrom_boundary_upgrade_candidate(
    candidate: PeakCandidate,
    chrom_candidate: PeakCandidate,
) -> PeakCandidate:
    return replace(
        chrom_candidate,
        proposal_sources=_combine_proposal_sources(candidate, chrom_candidate),
        source_apex_rank=(
            candidate.source_apex_rank
            if candidate.source_apex_rank is not None
            else chrom_candidate.source_apex_rank
        ),
        cwt_best_scale=(
            chrom_candidate.cwt_best_scale
            if chrom_candidate.cwt_best_scale is not None
            else candidate.cwt_best_scale
        ),
        cwt_ridge_persistence=(
            chrom_candidate.cwt_ridge_persistence
            if chrom_candidate.cwt_ridge_persistence is not None
            else candidate.cwt_ridge_persistence
        ),
        ms2_evidence_peak_start=(
            chrom_candidate.ms2_evidence_peak_start
            if chrom_candidate.ms2_evidence_peak_start is not None
            else candidate.ms2_evidence_peak_start
        ),
        ms2_evidence_peak_end=(
            chrom_candidate.ms2_evidence_peak_end
            if chrom_candidate.ms2_evidence_peak_end is not None
            else candidate.ms2_evidence_peak_end
        ),
        merge_note=_combine_merge_note(
            candidate.merge_note,
            chrom_candidate.merge_note,
        ),
    )


def _apply_region_first_safe_merge_if_enabled(
    rt: np.ndarray,
    intensity: np.ndarray,
    config: ExtractionConfig,
    candidates_result: PeakCandidatesResult,
    selected_candidate: PeakCandidate,
    candidate_scores: tuple[PeakCandidateScore, ...],
) -> tuple[PeakCandidatesResult, PeakCandidate, tuple[PeakCandidateScore, ...]]:
    if getattr(config, "resolver_mode", "legacy_savgol") != "region_first_safe_merge":
        return candidates_result, selected_candidate, candidate_scores
    outcome = apply_region_first_safe_merge(
        rt,
        intensity,
        candidates_result,
        selected_candidate,
        candidate_scores=candidate_scores,
        baseline_integration_method=getattr(
            config,
            "baseline_integration_method",
            "asls",
        ),
    )
    return (
        outcome.candidates_result,
        outcome.selected_candidate,
        outcome.candidate_scores,
    )


def _combine_proposal_sources(
    first: PeakCandidate,
    second: PeakCandidate,
) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(
            source
            for source in (*first.proposal_sources, *second.proposal_sources)
            if source
        )
    )


def _combine_merge_note(current: str, note: str) -> str:
    if not current:
        return note
    if not note or note in current.split("; "):
        return current
    return f"{current}; {note}"


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


def _candidate_score_summary(scored_candidate) -> PeakCandidateScore:
    evidence_score = scored_candidate.evidence_score
    return PeakCandidateScore(
        candidate=scored_candidate.candidate,
        confidence=scored_candidate.confidence.value,
        reason=scored_candidate.reason,
        raw_score=evidence_score.raw_score if evidence_score is not None else None,
        support_labels=(
            evidence_score.support_labels if evidence_score is not None else ()
        ),
        concern_labels=(
            evidence_score.concern_labels if evidence_score is not None else ()
        ),
        cap_labels=evidence_score.cap_labels if evidence_score is not None else (),
        prior_rt=scored_candidate.prior_rt,
        quality_penalty=scored_candidate.quality_penalty,
        selection_quality_penalty=scored_candidate.selection_quality_penalty,
        severities=scored_candidate.severities,
    )


def _detection_success(
    candidates_result: PeakCandidatesResult,
    candidate: PeakCandidate,
    *,
    confidence: str | None = None,
    reason: str | None = None,
    severities: tuple[tuple[int, str], ...] = (),
    score_breakdown: tuple[tuple[str, str], ...] = (),
    candidate_scores: tuple[PeakCandidateScore, ...] = (),
    selection_reference_rt: float | None = None,
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
        candidate_scores=candidate_scores,
        selection_reference_rt=selection_reference_rt,
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


def _append_or_merge_recovery_candidate(
    candidates: tuple[PeakCandidate, ...],
    candidate: PeakCandidate,
) -> tuple[tuple[PeakCandidate, ...], PeakCandidate]:
    merged_candidates = list(candidates)
    for index, existing in enumerate(merged_candidates):
        if not _same_peak_candidate_identity(existing, candidate):
            continue
        merged_candidate = replace(
            existing,
            proposal_sources=_combine_proposal_sources(existing, candidate),
        )
        merged_candidates[index] = merged_candidate
        return tuple(merged_candidates), merged_candidate
    return (*candidates, candidate), candidate


def _same_peak_candidate_identity(
    first: PeakCandidate,
    second: PeakCandidate,
) -> bool:
    return (
        first.selection_apex_rt == second.selection_apex_rt
        and first.peak == second.peak
    )


def _mark_recovery_candidate(
    recovery_candidate: PeakCandidate,
    recovery_result: PeakCandidatesResult,
) -> tuple[PeakCandidate, PeakCandidatesResult]:
    marked_candidate = _with_added_proposal_source(
        recovery_candidate,
        "preferred_rt_recovery",
    )
    marked_candidates = tuple(
        marked_candidate
        if candidate is recovery_candidate or candidate == recovery_candidate
        else candidate
        for candidate in recovery_result.candidates
    )
    return marked_candidate, _with_candidates(recovery_result, marked_candidates)


def _with_added_proposal_source(
    candidate: PeakCandidate,
    source: str,
) -> PeakCandidate:
    return replace(
        candidate,
        proposal_sources=tuple(
            dict.fromkeys((*candidate.proposal_sources, source))
        ),
    )


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
