from __future__ import annotations

from collections.abc import Callable, Mapping

from xic_extractor.config import ExtractionConfig, Target
from xic_extractor.neutral_loss import CandidateMS2Evidence
from xic_extractor.peak_detection.cwt import add_cwt_proposals_for_audit
from xic_extractor.peak_detection.hypotheses import (
    PeakHypothesis,
    build_peak_hypotheses,
    hypothesis_audit_id,
)
from xic_extractor.peak_detection.models import (
    PeakCandidate,
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

def candidate_audit_id(
    *,
    sample_name: str,
    target_label: str,
    resolver_mode: str,
    candidate: PeakCandidate,
) -> str:
    return hypothesis_audit_id(
        sample_name=sample_name,
        target_label=target_label,
        resolver_mode=resolver_mode,
        candidate=candidate,
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
    rt: object | None = None,
    intensity: object | None = None,
) -> list[PeakCandidateTableRow]:
    sample_group = group or classify_sample_group(sample_name)
    hypotheses = build_peak_hypotheses(
        sample_name=sample_name,
        target_label=target_label,
        role=role,
        istd_pair=istd_pair,
        resolver_mode=resolver_mode,
        peak_result=peak_result,
        candidate_ms2_evidence=candidate_ms2_evidence,
        rt=rt,
        intensity=intensity,
    )
    return [
        _row_from_hypothesis(
            sample_name=sample_name,
            group=sample_group,
            hypothesis=hypothesis,
        )
        for hypothesis in hypotheses
    ]


def _row_from_hypothesis(
    *,
    sample_name: str,
    group: str,
    hypothesis: PeakHypothesis,
) -> PeakCandidateTableRow:
    return {
        "sample_name": sample_name,
        "group": group,
        "target_label": hypothesis.target_label,
        "role": hypothesis.role,
        "istd_pair": hypothesis.istd_pair,
        "analysis_mode": hypothesis.analysis_mode,
        "resolver_mode": hypothesis.resolver_mode,
        "candidate_id": hypothesis.hypothesis_id,
        "proposal_sources": _join(hypothesis.audit.proposal_sources),
        "proposal_count": str(len(hypothesis.audit.proposal_sources)),
        "source_apex_rank": _format_optional_int(
            hypothesis.audit.source_apex_rank
        ),
        "merge_note": hypothesis.audit.merge_note,
        "rt_left_min": _format_float(hypothesis.integration.rt_left_min),
        "rt_apex_min": _format_float(hypothesis.integration.rt_apex_min),
        "rt_right_min": _format_float(hypothesis.integration.rt_right_min),
        "raw_apex_rt_min": _format_float(hypothesis.integration.raw_apex_rt_min),
        "rt_width_min": _format_float(hypothesis.integration.rt_width_min),
        "selection_apex_intensity": _format_float(
            hypothesis.integration.height_smoothed
        ),
        "raw_apex_intensity": _format_float(hypothesis.integration.height_raw),
        "prominence": _format_optional_float(hypothesis.evidence.prominence),
        "area_raw_counts_seconds": _format_float(
            hypothesis.integration.area_raw_counts_seconds,
            digits=2,
        ),
        "area_baseline_corrected": _format_optional_float(
            hypothesis.integration.area_baseline_corrected
        ),
        "area_uncertainty": _format_optional_float(
            hypothesis.integration.area_uncertainty
        ),
        "quality_flags": _join(hypothesis.evidence.quality_flags),
        "region_scan_count": _format_optional_int(
            hypothesis.evidence.region_scan_count
        ),
        "region_duration_min": _format_optional_float(
            hypothesis.evidence.region_duration_min
        ),
        "region_edge_ratio": _format_optional_float(
            hypothesis.evidence.region_edge_ratio
        ),
        "region_trace_continuity": _format_optional_float(
            hypothesis.evidence.region_trace_continuity
        ),
        "ms2_present": _format_optional_bool(hypothesis.evidence.ms2_present),
        "nl_match": _format_optional_bool(hypothesis.evidence.nl_match),
        "ms2_trace_strength": hypothesis.evidence.ms2_trace_strength,
        "rt_prior_min": _format_optional_float(hypothesis.evidence.rt_prior_min),
        "rt_prior_sigma": "",
        "confidence": hypothesis.evidence.confidence,
        "raw_score": _format_optional_int(hypothesis.evidence.raw_score),
        "support_labels": _join(hypothesis.evidence.support_labels),
        "concern_labels": _join(hypothesis.evidence.concern_labels),
        "cap_labels": _join(hypothesis.evidence.cap_labels),
        "reason": hypothesis.evidence.reason,
        "selected": "TRUE" if hypothesis.audit.selected else "FALSE",
        "selection_rank": _format_optional_int(hypothesis.audit.selection_rank),
        "selection_reference_rt_min": _format_optional_float(
            hypothesis.audit.selection_reference_rt_min
        ),
        "rejection_reason": hypothesis.audit.rejection_reason,
    }


def append_peak_candidate_rows(
    rows: list[PeakCandidateTableRow] | None,
    config: ExtractionConfig,
    sample_name: str,
    target: Target,
    peak_result: PeakDetectionResult,
    candidate_ms2_builder: Callable[[PeakCandidate], CandidateMS2Evidence | None],
    *,
    rt: object | None = None,
    intensity: object | None = None,
    audit_peak_result: PeakDetectionResult | None = None,
) -> None:
    if not config.emit_peak_candidates or rows is None:
        return
    audited = audit_peak_result
    if audited is None:
        audited = (
            add_cwt_proposals_for_audit(peak_result, rt, intensity, config)
            if rt is not None and intensity is not None
            else peak_result
        )
    rows.extend(
        build_peak_candidate_rows(
            sample_name=sample_name,
            target_label=target.label,
            role="ISTD" if target.is_istd else "Analyte",
            istd_pair=target.istd_pair,
            resolver_mode=config.resolver_mode,
            peak_result=audited,
            candidate_ms2_evidence=_candidate_table_ms2_evidence(
                audited,
                candidate_ms2_builder,
            ),
            rt=rt,
            intensity=intensity,
        )
    )


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
