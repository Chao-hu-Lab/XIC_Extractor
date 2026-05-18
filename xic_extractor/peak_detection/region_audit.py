from __future__ import annotations

import warnings
from dataclasses import dataclass

import numpy as np

from xic_extractor.config import ExtractionConfig
from xic_extractor.peak_detection.cwt import add_cwt_proposals_for_audit
from xic_extractor.peak_detection.models import (
    PeakCandidate,
    PeakCandidatesResult,
    PeakDetectionResult,
    PeakResult,
)
from xic_extractor.peak_detection.region_mixture_diagnostic import (
    classify_local_mixture,
)
from xic_extractor.peak_detection.region_model_selection import (
    RegionSelectionDecision,
    decide_region_selection,
)
from xic_extractor.peak_detection.region_safe_merge import (
    scored_region_boundaries_for_candidates,
)
from xic_extractor.peak_detection.traces import TraceGroup


@dataclass(frozen=True)
class PeakRegionAuditSummary:
    candidate_count: int | None = None
    selected_proposal_sources: tuple[str, ...] = ()
    selected_merge_note: str = ""
    shadow_status: str = ""
    shadow_verdict: str = ""
    merge_suggestion_source: str = ""
    area_ratio: float | None = None
    selected_interval_count: int | None = None
    selected_interval_gap_max_min: float | None = None
    local_mixture_diagnostic: str = ""
    local_mixture_reason: str = ""
    review_reason: str = ""


EMPTY_REGION_AUDIT = PeakRegionAuditSummary()


def build_peak_region_audit_summary(
    rt_values: np.ndarray,
    intensity_values: np.ndarray,
    result: PeakDetectionResult,
    config: ExtractionConfig,
    *,
    include_cwt: bool = True,
    trace_group: TraceGroup | None = None,
) -> PeakRegionAuditSummary:
    if result.status != "OK" or result.peak is None:
        return EMPTY_REGION_AUDIT
    if trace_group is not None:
        trace = trace_group.primary_trace
        rt_values = trace.rt
        intensity_values = trace.intensity

    if include_cwt:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            audited_result = add_cwt_proposals_for_audit(
                result,
                rt_values,
                intensity_values,
                config,
            )
    else:
        audited_result = result
    selected = _selected_candidate(audited_result)
    if selected is None:
        return PeakRegionAuditSummary(candidate_count=len(audited_result.candidates))

    candidates_result = PeakCandidatesResult(
        status="OK",
        candidates=audited_result.candidates,
        n_points=audited_result.n_points,
        max_smoothed=audited_result.max_smoothed,
        n_prominent_peaks=audited_result.n_prominent_peaks,
    )
    try:
        decision = decide_region_selection(
            tuple(
                scored.evidence
                for scored in scored_region_boundaries_for_candidates(
                    rt_values,
                    intensity_values,
                    candidates_result.candidates,
                    selected,
                )
            )
        )
    except (TypeError, ValueError) as exc:
        decision = RegionSelectionDecision(
            shadow_status="skipped_invalid_trace",
            shadow_verdict="insufficient_evidence",
            review_reason=str(exc),
        )
    return _summary_from_decision(
        decision,
        selected=selected,
        candidate_count=len(candidates_result.candidates),
    )


def _summary_from_decision(
    decision: RegionSelectionDecision,
    *,
    selected: PeakCandidate,
    candidate_count: int,
) -> PeakRegionAuditSummary:
    local_mixture = classify_local_mixture(decision)
    return PeakRegionAuditSummary(
        candidate_count=candidate_count,
        selected_proposal_sources=selected.proposal_sources,
        selected_merge_note=selected.merge_note,
        shadow_status=decision.shadow_status,
        shadow_verdict=decision.shadow_verdict,
        merge_suggestion_source=decision.merge_suggestion_source,
        area_ratio=decision.area_ratio,
        selected_interval_count=decision.selected_interval_count,
        selected_interval_gap_max_min=decision.selected_interval_gap_max_min,
        local_mixture_diagnostic=local_mixture.label,
        local_mixture_reason=local_mixture.reason,
        review_reason=decision.review_reason,
    )


def _selected_candidate(result: PeakDetectionResult) -> PeakCandidate | None:
    peak = result.peak
    if peak is None or not result.candidates:
        return None
    for candidate in result.candidates:
        if _same_peak(candidate.peak, peak):
            return candidate
    return min(
        result.candidates,
        key=lambda candidate: abs(candidate.selection_apex_rt - peak.rt),
    )


def _same_peak(candidate_peak: PeakResult, selected_peak: PeakResult) -> bool:
    return (
        candidate_peak == selected_peak
        or (
            abs(candidate_peak.rt - selected_peak.rt) <= 1e-9
            and abs(candidate_peak.peak_start - selected_peak.peak_start) <= 1e-9
            and abs(candidate_peak.peak_end - selected_peak.peak_end) <= 1e-9
        )
    )
