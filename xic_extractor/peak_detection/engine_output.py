from __future__ import annotations

from collections.abc import Callable

import numpy as np

from xic_extractor.config import ExtractionConfig
from xic_extractor.peak_detection.models import (
    PeakCandidate,
    PeakCandidateScore,
    PeakCandidatesResult,
    PeakDetectionResult,
)
from xic_extractor.peak_detection.region_safe_merge import (
    RegionFirstSafeMergeOutcome,
    apply_region_first_safe_merge,
)
from xic_extractor.settings_schema import CANONICAL_RESOLVER_MODE

SafeMergeFunc = Callable[..., RegionFirstSafeMergeOutcome]


def apply_region_first_safe_merge_if_enabled(
    rt: np.ndarray,
    intensity: np.ndarray,
    config: ExtractionConfig,
    candidates_result: PeakCandidatesResult,
    selected_candidate: PeakCandidate,
    candidate_scores: tuple[PeakCandidateScore, ...],
    *,
    safe_merge_func: SafeMergeFunc = apply_region_first_safe_merge,
) -> tuple[PeakCandidatesResult, PeakCandidate, tuple[PeakCandidateScore, ...]]:
    resolver_mode = getattr(config, "resolver_mode", CANONICAL_RESOLVER_MODE)
    if resolver_mode != CANONICAL_RESOLVER_MODE:
        return candidates_result, selected_candidate, candidate_scores
    outcome = safe_merge_func(
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


def detection_success(
    candidates_result: PeakCandidatesResult,
    candidate: PeakCandidate,
    *,
    confidence: str | None = None,
    reason: str | None = None,
    severities: tuple[tuple[int, str], ...] = (),
    score_breakdown: tuple[tuple[str, str], ...] = (),
    candidate_scores: tuple[PeakCandidateScore, ...] = (),
    selection_reference_rt: float | None = None,
    paired_istd_anchor_rt: float | None = None,
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
        paired_istd_anchor_rt=paired_istd_anchor_rt,
    )


def detection_failure(candidates_result: PeakCandidatesResult) -> PeakDetectionResult:
    return PeakDetectionResult(
        status=candidates_result.status,
        peak=None,
        n_points=candidates_result.n_points,
        max_smoothed=candidates_result.max_smoothed,
        n_prominent_peaks=candidates_result.n_prominent_peaks,
        candidates=candidates_result.candidates,
    )
