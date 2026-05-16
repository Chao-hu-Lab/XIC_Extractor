from __future__ import annotations

from collections.abc import Callable, Mapping

from xic_extractor.config import ExtractionConfig, Target
from xic_extractor.neutral_loss import CandidateMS2Evidence
from xic_extractor.peak_detection.models import (
    PeakCandidate,
    PeakCandidateScore,
    PeakDetectionResult,
)
from xic_extractor.sample_groups import classify_sample_group

PeakCandidateTableRow = dict[str, str]

PEAK_CANDIDATE_HEADERS = (
    "sample_name",
    "group",
    "target_label",
    "role",
    "istd_pair",
    "analysis_mode",
    "resolver_mode",
    "candidate_id",
    "proposal_sources",
    "proposal_count",
    "source_apex_rank",
    "merge_note",
    "rt_left_min",
    "rt_apex_min",
    "rt_right_min",
    "raw_apex_rt_min",
    "rt_width_min",
    "selection_apex_intensity",
    "raw_apex_intensity",
    "prominence",
    "area_raw_counts_seconds",
    "area_baseline_corrected",
    "area_uncertainty",
    "quality_flags",
    "region_scan_count",
    "region_duration_min",
    "region_edge_ratio",
    "region_trace_continuity",
    "ms2_present",
    "nl_match",
    "ms2_trace_strength",
    "rt_prior_min",
    "rt_prior_sigma",
    "confidence",
    "raw_score",
    "support_labels",
    "concern_labels",
    "cap_labels",
    "reason",
    "selected",
    "selection_rank",
    "selection_reference_rt_min",
    "rejection_reason",
)

_CONFIDENCE_RANK = {
    "HIGH": 0,
    "MEDIUM": 1,
    "LOW": 2,
    "VERY_LOW": 3,
    "": 4,
}


def candidate_audit_id(
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


def build_peak_candidate_rows(
    *,
    sample_name: str,
    target_label: str,
    role: str,
    istd_pair: str,
    resolver_mode: str,
    peak_result: PeakDetectionResult,
    group: str | None = None,
    candidate_ms2_evidence: Mapping[PeakCandidate, CandidateMS2Evidence] | None = None,
    selection_reference_rt: float | None = None,
) -> list[PeakCandidateTableRow]:
    selected = _selected_candidate(peak_result)
    score_by_candidate = {
        score.candidate: score for score in peak_result.candidate_scores
    }
    rank_by_candidate = _rank_candidates(peak_result.candidate_scores)
    selected_score = score_by_candidate.get(selected) if selected is not None else None
    evidence_by_candidate = candidate_ms2_evidence or {}
    sample_group = group or classify_sample_group(sample_name)

    rows: list[PeakCandidateTableRow] = []
    for candidate in peak_result.candidates:
        score = score_by_candidate.get(candidate)
        evidence = evidence_by_candidate.get(candidate)
        is_selected = selected is not None and candidate == selected
        row = {
            "sample_name": sample_name,
            "group": sample_group,
            "target_label": target_label,
            "role": role,
            "istd_pair": istd_pair,
            "analysis_mode": "targeted",
            "resolver_mode": resolver_mode,
            "candidate_id": candidate_audit_id(
                sample_name=sample_name,
                target_label=target_label,
                resolver_mode=resolver_mode,
                candidate=candidate,
            ),
            "proposal_sources": _join(candidate.proposal_sources),
            "proposal_count": str(len(candidate.proposal_sources)),
            "source_apex_rank": _format_optional_int(candidate.source_apex_rank),
            "merge_note": candidate.merge_note,
            "rt_left_min": _format_float(candidate.peak.peak_start),
            "rt_apex_min": _format_float(candidate.selection_apex_rt),
            "rt_right_min": _format_float(candidate.peak.peak_end),
            "raw_apex_rt_min": _format_float(candidate.raw_apex_rt),
            "rt_width_min": _format_float(
                candidate.peak.peak_end - candidate.peak.peak_start
            ),
            "selection_apex_intensity": _format_float(
                candidate.selection_apex_intensity
            ),
            "raw_apex_intensity": _format_float(candidate.raw_apex_intensity),
            "prominence": _format_float(candidate.prominence),
            "area_raw_counts_seconds": _format_float(candidate.peak.area, digits=2),
            "area_baseline_corrected": "",
            "area_uncertainty": "",
            "quality_flags": _join(
                tuple(str(flag) for flag in candidate.quality_flags)
            ),
            "region_scan_count": _format_optional_int(candidate.region_scan_count),
            "region_duration_min": _format_optional_float(
                candidate.region_duration_min
            ),
            "region_edge_ratio": _format_optional_float(candidate.region_edge_ratio),
            "region_trace_continuity": _format_optional_float(
                candidate.region_trace_continuity
            ),
            "ms2_present": _format_optional_bool(
                evidence.ms2_present if evidence is not None else None
            ),
            "nl_match": _format_optional_bool(
                evidence.nl_match if evidence is not None else None
            ),
            "ms2_trace_strength": (
                evidence.trace.strength if evidence is not None else ""
            ),
            "rt_prior_min": _format_optional_float(
                score.prior_rt if score is not None else None
            ),
            "rt_prior_sigma": "",
            "confidence": score.confidence if score is not None else "",
            "raw_score": (
                str(score.raw_score)
                if score is not None and score.raw_score is not None
                else ""
            ),
            "support_labels": _join(score.support_labels if score is not None else ()),
            "concern_labels": _join(score.concern_labels if score is not None else ()),
            "cap_labels": _join(score.cap_labels if score is not None else ()),
            "reason": score.reason if score is not None else "",
            "selected": "TRUE" if is_selected else "FALSE",
            "selection_rank": (
                "1"
                if is_selected
                else _format_optional_int(rank_by_candidate.get(candidate))
            ),
            "selection_reference_rt_min": _format_optional_float(
                selection_reference_rt
            ),
            "rejection_reason": (
                ""
                if is_selected
                else _rejection_reason(
                    candidate,
                    score,
                    selected,
                    selected_score,
                    selection_reference_rt=selection_reference_rt,
                )
            ),
        }
        rows.append(row)
    return rows


def append_peak_candidate_rows(
    rows: list[PeakCandidateTableRow] | None,
    config: ExtractionConfig,
    sample_name: str,
    target: Target,
    peak_result: PeakDetectionResult,
    candidate_ms2_builder: Callable[[PeakCandidate], CandidateMS2Evidence | None],
) -> None:
    if not config.emit_peak_candidates or rows is None:
        return
    rows.extend(
        build_peak_candidate_rows(
            sample_name=sample_name,
            target_label=target.label,
            role="ISTD" if target.is_istd else "Analyte",
            istd_pair=target.istd_pair,
            resolver_mode=config.resolver_mode,
            peak_result=peak_result,
            candidate_ms2_evidence=_candidate_table_ms2_evidence(
                peak_result,
                candidate_ms2_builder,
            ),
            selection_reference_rt=peak_result.selection_reference_rt,
        )
    )


def _selected_candidate(peak_result: PeakDetectionResult) -> PeakCandidate | None:
    if peak_result.peak is None:
        return None
    for candidate in peak_result.candidates:
        if candidate.peak == peak_result.peak:
            return candidate
    return None


def _candidate_table_ms2_evidence(
    peak_result: PeakDetectionResult,
    candidate_ms2_builder: Callable[[PeakCandidate], CandidateMS2Evidence | None],
) -> dict[PeakCandidate, CandidateMS2Evidence]:
    evidence_by_candidate: dict[PeakCandidate, CandidateMS2Evidence] = {}
    for candidate in peak_result.candidates:
        evidence = candidate_ms2_builder(candidate)
        if evidence is not None:
            evidence_by_candidate[candidate] = evidence
    return evidence_by_candidate


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


def _format_optional_float(value: float | None) -> str:
    if value is None:
        return ""
    return _format_float(value)


def _format_optional_int(value: int | None) -> str:
    if value is None:
        return ""
    return str(value)


def _format_optional_bool(value: bool | None) -> str:
    if value is None:
        return ""
    return "TRUE" if value else "FALSE"


def _join(values: tuple[str, ...]) -> str:
    return ";".join(values)
