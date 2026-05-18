from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass, replace

import numpy as np

from xic_extractor.peak_detection.baseline import integrate_linear_edge_baseline
from xic_extractor.peak_detection.boundaries import (
    BoundaryHypothesis,
    enumerate_boundary_hypotheses,
)
from xic_extractor.peak_detection.boundary_scoring import score_boundary_hypothesis
from xic_extractor.peak_detection.integration import integrate_area_counts_seconds
from xic_extractor.peak_detection.interval_selection import (
    WeightedInterval,
    select_weighted_nonoverlap_intervals,
)
from xic_extractor.peak_detection.models import (
    PeakCandidate,
    PeakCandidateScore,
    PeakCandidatesResult,
)
from xic_extractor.peak_detection.region_model_selection import (
    RegionBoundaryEvidence,
    RegionSelectionDecision,
    decide_region_selection,
)
from xic_extractor.peak_detection.trace_quality import trace_continuity_score

SAFE_MERGE_APEX_DELTA_MAX_MIN = 0.03
SAFE_MERGE_AREA_RATIO_MIN = 1.0
SAFE_MERGE_AREA_RATIO_MAX = 1.20
SAFE_MERGE_GAP_MAX_MIN = 0.08


@dataclass(frozen=True)
class RegionFirstSafeMergeOutcome:
    candidates_result: PeakCandidatesResult
    selected_candidate: PeakCandidate
    candidate_scores: tuple[PeakCandidateScore, ...]
    decision: RegionSelectionDecision
    promoted: bool = False


@dataclass(frozen=True)
class _ScoredBoundary:
    boundary: BoundaryHypothesis
    evidence: RegionBoundaryEvidence
    score: int


def apply_region_first_safe_merge(
    rt_values: np.ndarray,
    intensity_values: np.ndarray,
    candidates_result: PeakCandidatesResult,
    selected_candidate: PeakCandidate,
    *,
    candidate_scores: tuple[PeakCandidateScore, ...] = (),
) -> RegionFirstSafeMergeOutcome:
    scored_boundaries = scored_region_boundaries_for_candidates(
        rt_values,
        intensity_values,
        candidates_result.candidates,
        selected_candidate,
    )
    boundary_by_id = {
        scored.boundary.boundary_id: scored.boundary for scored in scored_boundaries
    }
    decision = decide_region_selection(
        tuple(scored.evidence for scored in scored_boundaries)
    )
    return apply_region_first_safe_merge_decision(
        rt_values,
        intensity_values,
        candidates_result,
        selected_candidate,
        decision,
        boundary_by_id,
        candidate_scores=candidate_scores,
    )


def apply_region_first_safe_merge_decision(
    rt_values: np.ndarray,
    intensity_values: np.ndarray,
    candidates_result: PeakCandidatesResult,
    selected_candidate: PeakCandidate,
    decision: RegionSelectionDecision,
    boundary_by_id: Mapping[str, BoundaryHypothesis],
    *,
    candidate_scores: tuple[PeakCandidateScore, ...] = (),
) -> RegionFirstSafeMergeOutcome:
    if not is_region_first_safe_merge_eligible(decision):
        return RegionFirstSafeMergeOutcome(
            candidates_result=candidates_result,
            selected_candidate=selected_candidate,
            candidate_scores=candidate_scores,
            decision=decision,
        )

    selected_boundaries = _selected_shadow_boundaries(decision, boundary_by_id)
    if not selected_boundaries:
        return RegionFirstSafeMergeOutcome(
            candidates_result=candidates_result,
            selected_candidate=selected_candidate,
            candidate_scores=candidate_scores,
            decision=decision,
        )

    rt = np.asarray(rt_values, dtype=float)
    intensity = np.asarray(intensity_values, dtype=float)
    left_index = min(boundary.left_index for boundary in selected_boundaries)
    right_index = max(boundary.right_index for boundary in selected_boundaries)
    promoted_area = integrate_area_counts_seconds(
        intensity,
        rt,
        left_index,
        right_index,
    )
    area_ratio = _safe_ratio(promoted_area, selected_candidate.peak.area)
    if not (SAFE_MERGE_AREA_RATIO_MIN <= area_ratio <= SAFE_MERGE_AREA_RATIO_MAX):
        return RegionFirstSafeMergeOutcome(
            candidates_result=candidates_result,
            selected_candidate=selected_candidate,
            candidate_scores=candidate_scores,
            decision=decision,
        )

    promoted_candidate = _promoted_candidate(
        selected_candidate,
        left_rt=float(rt[left_index]),
        right_rt=float(rt[right_index - 1]),
        area=promoted_area,
        scan_count=right_index - left_index,
    )
    promoted_result = replace(
        candidates_result,
        candidates=_replace_candidate(
            candidates_result.candidates,
            selected_candidate,
            promoted_candidate,
        ),
    )
    promoted_scores = _replace_candidate_scores(
        candidate_scores,
        selected_candidate,
        promoted_candidate,
    )
    return RegionFirstSafeMergeOutcome(
        candidates_result=promoted_result,
        selected_candidate=promoted_candidate,
        candidate_scores=promoted_scores,
        decision=decision,
        promoted=True,
    )


def is_region_first_safe_merge_eligible(
    decision: RegionSelectionDecision,
) -> bool:
    if decision.shadow_status != "evaluated":
        return False
    if decision.shadow_verdict != "merge_suggested":
        return False
    if decision.merge_suggestion_source != "adjacent_wis_local_minimum_merge":
        return False
    if (decision.selected_interval_count or 0) < 2:
        return False
    gap_max = decision.selected_interval_gap_max_min
    if gap_max is None or gap_max > SAFE_MERGE_GAP_MAX_MIN:
        return False
    if (
        decision.area_ratio is not None
        and decision.area_ratio > SAFE_MERGE_AREA_RATIO_MAX
    ):
        return False
    if decision.current_rt_apex_min is None or decision.shadow_rt_apex_min is None:
        return False
    return (
        abs(decision.current_rt_apex_min - decision.shadow_rt_apex_min)
        <= SAFE_MERGE_APEX_DELTA_MAX_MIN
    )


def scored_region_boundaries_for_candidates(
    rt_values: np.ndarray,
    intensity_values: np.ndarray,
    candidates: tuple[PeakCandidate, ...],
    selected_candidate: PeakCandidate,
) -> tuple[_ScoredBoundary, ...]:
    scored: list[_ScoredBoundary] = []
    for index, candidate in enumerate(candidates):
        candidate_id = _candidate_id(index, candidate)
        boundaries = enumerate_boundary_hypotheses(
            rt_values,
            intensity_values,
            candidate,
            candidate_id=candidate_id,
        )
        reference = _candidate_interval_reference(boundaries)
        candidate_scored = tuple(
            _score_boundary(
                boundary,
                reference,
                rt_values,
                intensity_values,
                candidate,
                candidate_id,
                selected_candidate=candidate == selected_candidate,
            )
            for boundary in boundaries
        )
        scored.extend(candidate_scored)
    selected_ids = _selected_top_boundary_ids(tuple(scored))
    return tuple(
        replace(
            boundary,
            evidence=replace(
                boundary.evidence,
                nonoverlap_selected=boundary.evidence.boundary_id in selected_ids,
            ),
        )
        for boundary in scored
    )


def _selected_top_boundary_ids(
    scored_boundaries: tuple[_ScoredBoundary, ...],
) -> set[str]:
    top_by_candidate: dict[str, _ScoredBoundary] = {}
    for boundary in scored_boundaries:
        current = top_by_candidate.get(boundary.evidence.candidate_id)
        if current is None or _top_boundary_rank(boundary) > _top_boundary_rank(
            current
        ):
            top_by_candidate[boundary.evidence.candidate_id] = boundary
    by_id = {
        boundary.evidence.boundary_id: boundary
        for boundary in top_by_candidate.values()
    }
    intervals = tuple(
        WeightedInterval(
            item_id=boundary.evidence.boundary_id,
            left=boundary.evidence.rt_left_min,
            right=boundary.evidence.rt_right_min,
            weight=boundary.score,
            selected_priority=1 if boundary.evidence.selected_candidate else 0,
            candidate_interval_priority=(
                1 if boundary.evidence.is_candidate_interval else 0
            ),
        )
        for boundary in top_by_candidate.values()
    )
    return {
        interval.item_id
        for interval in select_weighted_nonoverlap_intervals(intervals)
        if interval.item_id in by_id
    }


def _score_boundary(
    boundary: BoundaryHypothesis,
    reference: BoundaryHypothesis,
    rt_values: np.ndarray,
    intensity_values: np.ndarray,
    candidate: PeakCandidate,
    candidate_id: str,
    *,
    selected_candidate: bool,
) -> _ScoredBoundary:
    baseline = integrate_linear_edge_baseline(
        intensity_values,
        rt_values,
        boundary.left_index,
        boundary.right_index,
    )
    score = score_boundary_hypothesis(
        boundary,
        reference,
        baseline_score=baseline.baseline_score,
        trace_continuity=trace_continuity_score(
            intensity_values,
            left=boundary.left_index,
            right=boundary.right_index,
        ),
    )
    evidence = RegionBoundaryEvidence(
        boundary_id=boundary.boundary_id,
        candidate_id=candidate_id,
        proposal_sources=candidate.proposal_sources,
        boundary_sources=boundary.sources,
        selected_candidate=selected_candidate,
        is_candidate_interval="candidate_interval" in boundary.sources,
        nonoverlap_selected=False,
        rt_left_min=boundary.rt_left_min,
        rt_apex_min=boundary.rt_apex_min,
        rt_right_min=boundary.rt_right_min,
        area_raw_counts_seconds=boundary.area_raw_counts_seconds,
        boundary_score=score.score,
        scan_count=boundary.scan_count,
        support_labels=score.support_labels,
        concern_labels=score.concern_labels,
    )
    return _ScoredBoundary(boundary=boundary, evidence=evidence, score=score.score)


def _promoted_candidate(
    candidate: PeakCandidate,
    *,
    left_rt: float,
    right_rt: float,
    area: float,
    scan_count: int,
) -> PeakCandidate:
    peak = replace(
        candidate.peak,
        area=area,
        peak_start=left_rt,
        peak_end=right_rt,
    )
    return replace(
        candidate,
        peak=peak,
        region_scan_count=scan_count,
        region_duration_min=right_rt - left_rt,
        merge_note=_combine_merge_note(candidate.merge_note, "region_first_safe_merge"),
        ms2_evidence_peak_start=(
            candidate.ms2_evidence_peak_start
            if candidate.ms2_evidence_peak_start is not None
            else candidate.peak.peak_start
        ),
        ms2_evidence_peak_end=(
            candidate.ms2_evidence_peak_end
            if candidate.ms2_evidence_peak_end is not None
            else candidate.peak.peak_end
        ),
    )


def _selected_shadow_boundaries(
    decision: RegionSelectionDecision,
    boundary_by_id: Mapping[str, BoundaryHypothesis],
) -> tuple[BoundaryHypothesis, ...]:
    boundaries: list[BoundaryHypothesis] = []
    for boundary_id in decision.shadow_boundary_id.split(";"):
        boundary = boundary_by_id.get(boundary_id)
        if boundary is None:
            return ()
        boundaries.append(boundary)
    return tuple(boundaries)


def _replace_candidate(
    candidates: tuple[PeakCandidate, ...],
    old: PeakCandidate,
    new: PeakCandidate,
) -> tuple[PeakCandidate, ...]:
    return tuple(new if candidate == old else candidate for candidate in candidates)


def _replace_candidate_scores(
    scores: tuple[PeakCandidateScore, ...],
    old: PeakCandidate,
    new: PeakCandidate,
) -> tuple[PeakCandidateScore, ...]:
    return tuple(
        replace(score, candidate=new) if score.candidate == old else score
        for score in scores
    )


def _candidate_id(index: int, candidate: PeakCandidate) -> str:
    return "|".join(
        (
            f"candidate-{index}",
            ";".join(candidate.proposal_sources),
            f"{candidate.selection_apex_rt:.5f}",
        )
    )


def _candidate_interval_reference(
    boundaries: tuple[BoundaryHypothesis, ...],
) -> BoundaryHypothesis:
    for boundary in boundaries:
        if "candidate_interval" in boundary.sources:
            return boundary
    if not boundaries:
        raise ValueError("safe merge requires at least one boundary hypothesis")
    return boundaries[0]


def _top_boundary_rank(boundary: _ScoredBoundary) -> tuple[int, int, float]:
    return (
        boundary.score,
        1 if boundary.evidence.is_candidate_interval else 0,
        boundary.evidence.area_raw_counts_seconds,
    )


def _safe_ratio(value: float, reference: float) -> float:
    if reference <= 0:
        return math.inf
    return value / reference


def _combine_merge_note(current: str, note: str) -> str:
    values = [value for value in current.split(";") if value]
    if note not in values:
        values.append(note)
    return ";".join(values)
