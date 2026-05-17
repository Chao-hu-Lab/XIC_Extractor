from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

import numpy as np

from xic_extractor.evidence_semantics import (
    CommonEvidence,
    common_evidence_from_targeted_candidate,
)
from xic_extractor.neutral_loss import CandidateMS2Evidence
from xic_extractor.peak_detection.baseline import (
    bounded_trace_interval,
    integrate_linear_edge_baseline,
)
from xic_extractor.peak_detection.models import (
    PeakCandidate,
    PeakCandidateScore,
    PeakDetectionResult,
)

_CONFIDENCE_RANK = {
    "HIGH": 0,
    "MEDIUM": 1,
    "LOW": 2,
    "VERY_LOW": 3,
    "": 4,
}


@dataclass(frozen=True)
class IntegrationResult:
    rt_left_min: float
    rt_apex_min: float
    rt_right_min: float
    raw_apex_rt_min: float
    rt_width_min: float
    height_raw: float
    height_smoothed: float
    area_raw_counts_seconds: float
    integration_method: str = "raw_trapezoid"
    boundary_sources: tuple[str, ...] = ("candidate_interval",)
    area_baseline_corrected: float | None = None
    area_uncertainty: float | None = None
    baseline_type: str = ""
    baseline_score: float | None = None
    raw_scan_indices: tuple[int, ...] = ()


@dataclass(frozen=True)
class EvidenceVector:
    confidence: str = ""
    raw_score: int | None = None
    support_labels: tuple[str, ...] = ()
    concern_labels: tuple[str, ...] = ()
    cap_labels: tuple[str, ...] = ()
    reason: str = ""
    quality_flags: tuple[str, ...] = ()
    prominence: float | None = None
    region_scan_count: int | None = None
    region_duration_min: float | None = None
    region_edge_ratio: float | None = None
    region_trace_continuity: float | None = None
    ms2_present: bool | None = None
    nl_match: bool | None = None
    ms2_trace_strength: str = ""
    rt_prior_min: float | None = None
    cwt_best_scale: float | None = None
    cwt_ridge_persistence: float | None = None
    boundary_score: float | None = None
    baseline_score: float | None = None
    common: CommonEvidence | None = None


@dataclass(frozen=True)
class AuditTrail:
    proposal_sources: tuple[str, ...] = ()
    source_apex_rank: int | None = None
    merge_note: str = ""
    selected: bool = False
    selection_rank: int | None = None
    selection_reference_rt_min: float | None = None
    rejection_reason: str = ""


@dataclass(frozen=True)
class PeakHypothesis:
    hypothesis_id: str
    trace_group_id: str
    target_label: str
    role: str
    istd_pair: str
    analysis_mode: str
    resolver_mode: str
    integration: IntegrationResult
    evidence: EvidenceVector
    audit: AuditTrail


def hypothesis_audit_id(
    *,
    sample_name: str,
    target_label: str,
    resolver_mode: str,
    candidate: PeakCandidate,
) -> str:
    return "|".join(
        (
            sample_name,
            target_label,
            resolver_mode,
            _join(candidate.proposal_sources),
            _format_float(candidate.selection_apex_rt, digits=5),
            _format_float(candidate.peak.peak_start, digits=5),
            _format_float(candidate.peak.peak_end, digits=5),
        )
    )


def build_peak_hypotheses(
    *,
    sample_name: str,
    target_label: str,
    role: str,
    istd_pair: str,
    resolver_mode: str,
    peak_result: PeakDetectionResult,
    candidate_ms2_evidence: Mapping[PeakCandidate, CandidateMS2Evidence] | None = None,
    rt: object | None = None,
    intensity: object | None = None,
) -> tuple[PeakHypothesis, ...]:
    selected = _selected_candidate(peak_result)
    score_by_candidate = {
        score.candidate: score for score in peak_result.candidate_scores
    }
    rank_by_candidate = _rank_candidates(peak_result.candidate_scores)
    selected_score = score_by_candidate.get(selected) if selected is not None else None
    evidence_by_candidate = candidate_ms2_evidence or {}

    hypotheses: list[PeakHypothesis] = []
    for candidate in peak_result.candidates:
        score = score_by_candidate.get(candidate)
        evidence = evidence_by_candidate.get(candidate)
        is_selected = selected is not None and candidate == selected
        hypotheses.append(
            PeakHypothesis(
                hypothesis_id=hypothesis_audit_id(
                    sample_name=sample_name,
                    target_label=target_label,
                    resolver_mode=resolver_mode,
                    candidate=candidate,
                ),
                trace_group_id=_trace_group_id(
                    sample_name=sample_name,
                    target_label=target_label,
                    resolver_mode=resolver_mode,
                ),
                target_label=target_label,
                role=role,
                istd_pair=istd_pair,
                analysis_mode="targeted",
                resolver_mode=resolver_mode,
                integration=_integration_from_candidate(
                    candidate,
                    rt=rt,
                    intensity=intensity,
                ),
                evidence=_evidence_from_candidate(
                    candidate,
                    score,
                    evidence,
                    target_label=target_label,
                ),
                audit=AuditTrail(
                    proposal_sources=candidate.proposal_sources,
                    source_apex_rank=candidate.source_apex_rank,
                    merge_note=candidate.merge_note,
                    selected=is_selected,
                    selection_rank=1
                    if is_selected
                    else rank_by_candidate.get(candidate),
                    selection_reference_rt_min=peak_result.selection_reference_rt,
                    rejection_reason=""
                    if is_selected
                    else _rejection_reason(
                        candidate,
                        score,
                        selected,
                        selected_score,
                        selection_reference_rt=peak_result.selection_reference_rt,
                    ),
                ),
            )
        )
    return tuple(hypotheses)


def _trace_group_id(
    *,
    sample_name: str,
    target_label: str,
    resolver_mode: str,
) -> str:
    return "|".join((sample_name, target_label, resolver_mode))


def _integration_from_candidate(
    candidate: PeakCandidate,
    *,
    rt: object | None = None,
    intensity: object | None = None,
) -> IntegrationResult:
    baseline = None
    raw_scan_indices: tuple[int, ...] = ()
    if rt is not None and intensity is not None:
        rt_values = np.asarray(rt, dtype=float)
        intensity_values = np.asarray(intensity, dtype=float)
        left_index = _nearest_index(rt_values, candidate.peak.peak_start)
        right_index = _nearest_index(rt_values, candidate.peak.peak_end) + 1
        bounded_left, bounded_right = bounded_trace_interval(
            left_index,
            right_index,
            len(rt_values),
        )
        raw_scan_indices = tuple(range(bounded_left, bounded_right))
        baseline = integrate_linear_edge_baseline(
            intensity_values,
            rt_values,
            left_index,
            right_index,
        )
    return IntegrationResult(
        rt_left_min=candidate.peak.peak_start,
        rt_apex_min=candidate.selection_apex_rt,
        rt_right_min=candidate.peak.peak_end,
        raw_apex_rt_min=candidate.raw_apex_rt,
        rt_width_min=candidate.peak.peak_end - candidate.peak.peak_start,
        height_raw=candidate.raw_apex_intensity,
        height_smoothed=candidate.selection_apex_intensity,
        area_raw_counts_seconds=candidate.peak.area,
        area_baseline_corrected=(
            baseline.area_baseline_corrected if baseline is not None else None
        ),
        area_uncertainty=baseline.area_uncertainty if baseline is not None else None,
        baseline_type=baseline.baseline_type if baseline is not None else "",
        baseline_score=baseline.baseline_score if baseline is not None else None,
        raw_scan_indices=raw_scan_indices,
    )


def _evidence_from_candidate(
    candidate: PeakCandidate,
    score: PeakCandidateScore | None,
    evidence: CandidateMS2Evidence | None,
    *,
    target_label: str,
) -> EvidenceVector:
    common = common_evidence_from_targeted_candidate(
        candidate,
        score=score,
        candidate_ms2_evidence=evidence,
        target_label=target_label,
    )
    return EvidenceVector(
        confidence=score.confidence if score is not None else "",
        raw_score=score.raw_score if score is not None else None,
        support_labels=score.support_labels if score is not None else (),
        concern_labels=score.concern_labels if score is not None else (),
        cap_labels=score.cap_labels if score is not None else (),
        reason=score.reason if score is not None else "",
        quality_flags=tuple(str(flag) for flag in candidate.quality_flags),
        prominence=candidate.prominence,
        region_scan_count=candidate.region_scan_count,
        region_duration_min=candidate.region_duration_min,
        region_edge_ratio=candidate.region_edge_ratio,
        region_trace_continuity=candidate.region_trace_continuity,
        ms2_present=common.ms2_present,
        nl_match=common.nl_match,
        ms2_trace_strength=common.ms2_trace_strength,
        rt_prior_min=score.prior_rt if score is not None else None,
        cwt_best_scale=candidate.cwt_best_scale,
        cwt_ridge_persistence=candidate.cwt_ridge_persistence,
        common=common,
    )


def _selected_candidate(peak_result: PeakDetectionResult) -> PeakCandidate | None:
    if peak_result.peak is None:
        return None
    for candidate in peak_result.candidates:
        if candidate.peak == peak_result.peak:
            return candidate
    return None


def _rank_candidates(
    scores: tuple[PeakCandidateScore, ...],
) -> dict[PeakCandidate, int]:
    ranked = sorted(
        scores,
        key=lambda score: (
            _CONFIDENCE_RANK.get(score.confidence, 4),
            -(score.raw_score if score.raw_score is not None else -10_000),
        ),
    )
    return {score.candidate: index + 1 for index, score in enumerate(ranked)}


def _rejection_reason(
    candidate: PeakCandidate,
    score: PeakCandidateScore | None,
    selected: PeakCandidate | None,
    selected_score: PeakCandidateScore | None,
    *,
    selection_reference_rt: float | None,
) -> str:
    if score is not None and selected_score is not None:
        if _confidence_rank(score) > _confidence_rank(selected_score):
            return "lower_confidence"
        if _raw_score(score) < _raw_score(selected_score):
            return "lower_score"
        if (
            selection_reference_rt is not None
            and selected is not None
            and abs(candidate.selection_apex_rt - selection_reference_rt)
            > abs(selected.selection_apex_rt - selection_reference_rt)
        ):
            return "farther_from_preferred_rt"
        if score.quality_penalty > selected_score.quality_penalty:
            return "quality_penalty"
    return "non_selected_candidate"


def _confidence_rank(score: PeakCandidateScore) -> int:
    return _CONFIDENCE_RANK.get(score.confidence, 4)


def _raw_score(score: PeakCandidateScore) -> int:
    if score.raw_score is None:
        return -10_000
    return score.raw_score


def _format_float(value: float, *, digits: int = 5) -> str:
    return f"{value:.{digits}f}"


def _join(values: tuple[str, ...]) -> str:
    return ";".join(values)


def _nearest_index(rt: np.ndarray, value: float) -> int:
    return int(np.argmin(np.abs(rt - value)))
