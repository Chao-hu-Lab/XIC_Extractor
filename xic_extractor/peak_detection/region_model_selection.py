from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

ShadowStatus = Literal[
    "evaluated",
    "skipped_no_candidate",
    "skipped_no_boundary",
    "skipped_low_scan_support",
    "skipped_invalid_trace",
]
ShadowVerdict = Literal[
    "insufficient_evidence",
    "current_supported",
    "wider_boundary_preferred",
    "neighbor_apex_preferred",
    "merge_suggested",
    "split_supported",
]
MergeSuggestionSource = Literal[
    "",
    "adjacent_wis_local_minimum_merge",
    "same_apex_wider_boundary_merge",
]

MIN_SCAN_SUPPORT = 3
WIDER_AREA_RATIO_CUTOFF = 1.50
SCORE_DELTA_CUTOFF = 15
SPLIT_TOTAL_SCORE_DELTA_CUTOFF = 20
MERGE_SELECTED_INTERVAL_AREA_RATIO_MAX = 1.20
MERGE_SELECTED_INTERVAL_GAP_MAX_MIN = 0.08
_CWT_PROPOSAL_SOURCE = "centwave_cwt"


@dataclass(frozen=True)
class RegionBoundaryEvidence:
    boundary_id: str
    candidate_id: str
    proposal_sources: tuple[str, ...]
    boundary_sources: tuple[str, ...]
    selected_candidate: bool
    is_candidate_interval: bool
    nonoverlap_selected: bool
    rt_left_min: float
    rt_apex_min: float
    rt_right_min: float
    area_raw_counts_seconds: float
    boundary_score: int
    scan_count: int
    support_labels: tuple[str, ...] = ()
    concern_labels: tuple[str, ...] = ()


@dataclass(frozen=True)
class RegionSelectionDecision:
    shadow_status: ShadowStatus
    shadow_verdict: ShadowVerdict
    current_candidate_id: str = ""
    current_boundary_id: str = ""
    shadow_boundary_id: str = ""
    current_rt_left_min: float | None = None
    current_rt_apex_min: float | None = None
    current_rt_right_min: float | None = None
    current_area_raw_counts_seconds: float | None = None
    shadow_rt_left_min: float | None = None
    shadow_rt_apex_min: float | None = None
    shadow_rt_right_min: float | None = None
    shadow_area_raw_counts_seconds: float | None = None
    score_delta: int | None = None
    area_ratio: float | None = None
    current_scan_count: int | None = None
    shadow_scan_count: int | None = None
    selected_interval_count: int | None = None
    selected_interval_gap_max_min: float | None = None
    selected_interval_total_score: int | None = None
    best_single_boundary_score: int | None = None
    support_labels: tuple[str, ...] = ()
    concern_labels: tuple[str, ...] = ()
    review_reason: str = ""
    merge_suggestion_source: MergeSuggestionSource = ""


def decide_region_selection(
    boundaries: Sequence[RegionBoundaryEvidence],
) -> RegionSelectionDecision:
    if not boundaries:
        return _skipped("skipped_no_boundary", "no boundary hypotheses available")
    if any(not _valid_boundary(boundary) for boundary in boundaries):
        return _skipped("skipped_invalid_trace", "invalid boundary numeric fields")

    current = _selected_candidate_interval(boundaries)
    if current is None:
        return _skipped("skipped_no_candidate", "no selected candidate interval")
    if current.scan_count < MIN_SCAN_SUPPORT:
        return _decision(
            current,
            current,
            status="skipped_low_scan_support",
            verdict="insufficient_evidence",
            review_reason=(
                f"selected candidate has {current.scan_count} scans; "
                f"minimum is {MIN_SCAN_SUPPORT}"
            ),
        )

    comparable = [
        boundary
        for boundary in boundaries
        if boundary.boundary_id != current.boundary_id
    ]
    if not comparable:
        return _decision(
            current,
            current,
            verdict="insufficient_evidence",
            review_reason="no comparable boundary or candidate evidence",
        )

    merge = _merge_suggested(boundaries, current)
    if merge is not None:
        return merge

    selected_merge = _adjacent_selected_intervals_merge_suggested(
        boundaries,
        current,
    )
    if selected_merge is not None:
        return selected_merge

    split = _split_supported(boundaries, current)
    if split is not None:
        return split

    neighbor = _neighbor_apex_preferred(boundaries, current)
    if neighbor is not None:
        return neighbor

    wider = _wider_boundary_preferred(boundaries, current)
    if wider is not None:
        return wider

    return _decision(
        current,
        current,
        verdict="current_supported",
        review_reason=(
            "current selected interval is not contradicted by shadow evidence"
        ),
    )


def _split_supported(
    boundaries: Sequence[RegionBoundaryEvidence],
    current: RegionBoundaryEvidence,
) -> RegionSelectionDecision | None:
    selected = _supported_nonoverlap_intervals(boundaries)
    if len(selected) < 2:
        return None
    total_score = sum(boundary.boundary_score for boundary in selected)
    best_single_score = max(boundary.boundary_score for boundary in boundaries)
    if total_score < best_single_score + SPLIT_TOTAL_SCORE_DELTA_CUTOFF:
        return None
    shadow_area = sum(boundary.area_raw_counts_seconds for boundary in selected)
    dominant = _dominant_interval(selected)
    return RegionSelectionDecision(
        shadow_status="evaluated",
        shadow_verdict="split_supported",
        current_candidate_id=current.candidate_id,
        current_boundary_id=current.boundary_id,
        shadow_boundary_id=";".join(boundary.boundary_id for boundary in selected),
        current_rt_left_min=current.rt_left_min,
        current_rt_apex_min=current.rt_apex_min,
        current_rt_right_min=current.rt_right_min,
        current_area_raw_counts_seconds=current.area_raw_counts_seconds,
        shadow_rt_left_min=min(boundary.rt_left_min for boundary in selected),
        shadow_rt_apex_min=dominant.rt_apex_min,
        shadow_rt_right_min=max(boundary.rt_right_min for boundary in selected),
        shadow_area_raw_counts_seconds=shadow_area,
        score_delta=total_score - current.boundary_score,
        area_ratio=_safe_ratio(shadow_area, current.area_raw_counts_seconds),
        current_scan_count=current.scan_count,
        shadow_scan_count=sum(boundary.scan_count for boundary in selected),
        selected_interval_count=len(selected),
        selected_interval_gap_max_min=_max_interval_gap(selected),
        selected_interval_total_score=total_score,
        best_single_boundary_score=best_single_score,
        support_labels=_combine_labels(
            *(boundary.support_labels for boundary in selected)
        ),
        concern_labels=_combine_labels(
            *(boundary.concern_labels for boundary in selected)
        ),
        review_reason=(
            "weighted non-overlap selected multiple supported intervals over "
            "the current single interval"
        ),
    )


def _adjacent_selected_intervals_merge_suggested(
    boundaries: Sequence[RegionBoundaryEvidence],
    current: RegionBoundaryEvidence,
) -> RegionSelectionDecision | None:
    selected = _supported_nonoverlap_intervals(boundaries)
    if len(selected) < 2:
        return None
    if not all("local_minimum" in boundary.proposal_sources for boundary in selected):
        return None
    if _max_interval_gap(selected) > MERGE_SELECTED_INTERVAL_GAP_MAX_MIN:
        return None
    selected_area_sum = sum(boundary.area_raw_counts_seconds for boundary in selected)
    area_ratio_lower_bound = _safe_ratio(
        selected_area_sum,
        current.area_raw_counts_seconds,
    )
    if area_ratio_lower_bound > MERGE_SELECTED_INTERVAL_AREA_RATIO_MAX:
        return None
    total_score = sum(boundary.boundary_score for boundary in selected)
    dominant = _dominant_interval(selected)
    return RegionSelectionDecision(
        shadow_status="evaluated",
        shadow_verdict="merge_suggested",
        current_candidate_id=current.candidate_id,
        current_boundary_id=current.boundary_id,
        shadow_boundary_id=";".join(boundary.boundary_id for boundary in selected),
        current_rt_left_min=current.rt_left_min,
        current_rt_apex_min=current.rt_apex_min,
        current_rt_right_min=current.rt_right_min,
        current_area_raw_counts_seconds=current.area_raw_counts_seconds,
        shadow_rt_left_min=min(boundary.rt_left_min for boundary in selected),
        shadow_rt_apex_min=dominant.rt_apex_min,
        shadow_rt_right_min=max(boundary.rt_right_min for boundary in selected),
        shadow_area_raw_counts_seconds=None,
        score_delta=total_score - current.boundary_score,
        area_ratio=None,
        current_scan_count=current.scan_count,
        shadow_scan_count=sum(boundary.scan_count for boundary in selected),
        selected_interval_count=len(selected),
        selected_interval_gap_max_min=_max_interval_gap(selected),
        selected_interval_total_score=total_score,
        best_single_boundary_score=max(
            boundary.boundary_score for boundary in boundaries
        ),
        support_labels=_combine_labels(
            *(boundary.support_labels for boundary in selected)
        ),
        concern_labels=_combine_labels(
            *(boundary.concern_labels for boundary in selected)
        ),
        review_reason=(
            "adjacent WIS-selected local-minimum intervals have only small "
            "selected-interval area gain; production must validate the "
            "continuous envelope area"
        ),
        merge_suggestion_source="adjacent_wis_local_minimum_merge",
    )


def _merge_suggested(
    boundaries: Sequence[RegionBoundaryEvidence],
    current: RegionBoundaryEvidence,
) -> RegionSelectionDecision | None:
    wider = _best_same_candidate_wider_boundary(boundaries, current)
    if wider is None:
        return None
    overlapping_local_candidates = {
        boundary.candidate_id
        for boundary in boundaries
        if boundary.candidate_id != current.candidate_id
        and "local_minimum" in boundary.proposal_sources
        and wider.rt_left_min <= boundary.rt_apex_min <= wider.rt_right_min
    }
    if not overlapping_local_candidates:
        return None
    return _decision(
        current,
        wider,
        verdict="merge_suggested",
        review_reason=(
            "wider same-apex boundary covers neighboring local-minimum candidates"
        ),
        merge_suggestion_source="same_apex_wider_boundary_merge",
    )


def _supported_nonoverlap_intervals(
    boundaries: Sequence[RegionBoundaryEvidence],
) -> list[RegionBoundaryEvidence]:
    selected = [
        boundary
        for boundary in boundaries
        if boundary.nonoverlap_selected and boundary.scan_count >= MIN_SCAN_SUPPORT
    ]
    return sorted(
        selected,
        key=lambda boundary: (boundary.rt_left_min, boundary.boundary_id),
    )


def _dominant_interval(
    boundaries: Sequence[RegionBoundaryEvidence],
) -> RegionBoundaryEvidence:
    return max(boundaries, key=lambda boundary: boundary.area_raw_counts_seconds)


def _max_interval_gap(boundaries: Sequence[RegionBoundaryEvidence]) -> float:
    ordered = sorted(boundaries, key=lambda boundary: boundary.rt_left_min)
    gaps = [
        next_boundary.rt_left_min - boundary.rt_right_min
        for boundary, next_boundary in zip(ordered, ordered[1:], strict=False)
    ]
    return round(max(max(gaps, default=0.0), 0.0), 5)


def _neighbor_apex_preferred(
    boundaries: Sequence[RegionBoundaryEvidence],
    current: RegionBoundaryEvidence,
) -> RegionSelectionDecision | None:
    neighbors = [
        boundary
        for boundary in boundaries
        if boundary.candidate_id != current.candidate_id
        and not _is_cwt_only(boundary)
        and boundary.scan_count >= MIN_SCAN_SUPPORT
    ]
    if not neighbors:
        return None
    best = max(neighbors, key=_boundary_rank_key)
    if best.boundary_score < current.boundary_score + SCORE_DELTA_CUTOFF:
        return None
    return _decision(
        current,
        best,
        verdict="neighbor_apex_preferred",
        review_reason="neighbor apex has materially higher non-CWT-only support",
    )


def _wider_boundary_preferred(
    boundaries: Sequence[RegionBoundaryEvidence],
    current: RegionBoundaryEvidence,
) -> RegionSelectionDecision | None:
    wider = _best_same_candidate_wider_boundary(boundaries, current)
    if wider is None:
        return None
    return _decision(
        current,
        wider,
        verdict="wider_boundary_preferred",
        review_reason="same-apex wider boundary has materially higher area",
    )


def _best_same_candidate_wider_boundary(
    boundaries: Sequence[RegionBoundaryEvidence],
    current: RegionBoundaryEvidence,
) -> RegionBoundaryEvidence | None:
    same_candidate = [
        boundary
        for boundary in boundaries
        if boundary.candidate_id == current.candidate_id
        and boundary.boundary_id != current.boundary_id
        and boundary.scan_count >= MIN_SCAN_SUPPORT
        and boundary.boundary_score >= current.boundary_score
        and _safe_ratio(
            boundary.area_raw_counts_seconds,
            current.area_raw_counts_seconds,
        )
        >= WIDER_AREA_RATIO_CUTOFF
    ]
    if not same_candidate:
        return None
    return max(same_candidate, key=_boundary_rank_key)


def _selected_candidate_interval(
    boundaries: Sequence[RegionBoundaryEvidence],
) -> RegionBoundaryEvidence | None:
    selected_intervals = [
        boundary
        for boundary in boundaries
        if boundary.selected_candidate and boundary.is_candidate_interval
    ]
    if selected_intervals:
        return max(selected_intervals, key=_boundary_rank_key)
    selected = [boundary for boundary in boundaries if boundary.selected_candidate]
    if selected:
        return max(selected, key=_boundary_rank_key)
    return None


def _decision(
    current: RegionBoundaryEvidence,
    shadow: RegionBoundaryEvidence,
    *,
    status: ShadowStatus = "evaluated",
    verdict: ShadowVerdict,
    review_reason: str,
    merge_suggestion_source: MergeSuggestionSource = "",
) -> RegionSelectionDecision:
    score_delta = shadow.boundary_score - current.boundary_score
    return RegionSelectionDecision(
        shadow_status=status,
        shadow_verdict=verdict,
        current_candidate_id=current.candidate_id,
        current_boundary_id=current.boundary_id,
        shadow_boundary_id=shadow.boundary_id,
        current_rt_left_min=current.rt_left_min,
        current_rt_apex_min=current.rt_apex_min,
        current_rt_right_min=current.rt_right_min,
        current_area_raw_counts_seconds=current.area_raw_counts_seconds,
        shadow_rt_left_min=shadow.rt_left_min,
        shadow_rt_apex_min=shadow.rt_apex_min,
        shadow_rt_right_min=shadow.rt_right_min,
        shadow_area_raw_counts_seconds=shadow.area_raw_counts_seconds,
        score_delta=score_delta,
        area_ratio=_safe_ratio(
            shadow.area_raw_counts_seconds,
            current.area_raw_counts_seconds,
        ),
        current_scan_count=current.scan_count,
        shadow_scan_count=shadow.scan_count,
        support_labels=shadow.support_labels,
        concern_labels=shadow.concern_labels,
        review_reason=review_reason,
        merge_suggestion_source=merge_suggestion_source,
    )


def _skipped(status: ShadowStatus, reason: str) -> RegionSelectionDecision:
    return RegionSelectionDecision(
        shadow_status=status,
        shadow_verdict="insufficient_evidence",
        review_reason=reason,
    )


def _valid_boundary(boundary: RegionBoundaryEvidence) -> bool:
    numeric_values = (
        boundary.rt_left_min,
        boundary.rt_apex_min,
        boundary.rt_right_min,
        boundary.area_raw_counts_seconds,
        float(boundary.boundary_score),
        float(boundary.scan_count),
    )
    return (
        all(math.isfinite(value) for value in numeric_values)
        and boundary.rt_left_min < boundary.rt_right_min
        and boundary.rt_left_min <= boundary.rt_apex_min <= boundary.rt_right_min
        and boundary.area_raw_counts_seconds >= 0
        and boundary.scan_count >= 0
    )


def _boundary_rank_key(boundary: RegionBoundaryEvidence) -> tuple[int, float, int]:
    return (
        boundary.boundary_score,
        boundary.area_raw_counts_seconds,
        1 if boundary.is_candidate_interval else 0,
    )


def _safe_ratio(value: float, reference: float) -> float:
    if reference <= 0:
        return math.inf
    return round(value / reference, 5)


def _is_cwt_only(boundary: RegionBoundaryEvidence) -> bool:
    sources = {source for source in boundary.proposal_sources if source}
    return sources == {_CWT_PROPOSAL_SOURCE}


def _combine_labels(*label_groups: tuple[str, ...]) -> tuple[str, ...]:
    labels: list[str] = []
    for group in label_groups:
        for label in group:
            if label and label not in labels:
                labels.append(label)
    return tuple(labels)
