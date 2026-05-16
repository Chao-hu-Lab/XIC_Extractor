from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from xic_extractor.config import ExtractionConfig, Target
from xic_extractor.extraction.peak_candidate_table import candidate_audit_id
from xic_extractor.peak_detection.baseline import integrate_linear_edge_baseline
from xic_extractor.peak_detection.boundaries import (
    BoundaryHypothesis,
    enumerate_boundary_hypotheses,
)
from xic_extractor.peak_detection.cwt import add_cwt_proposals_for_audit
from xic_extractor.peak_detection.models import PeakCandidate, PeakDetectionResult
from xic_extractor.sample_groups import classify_sample_group

PeakCandidateBoundaryRow = dict[str, str]

PEAK_CANDIDATE_BOUNDARY_HEADERS = (
    "sample_name",
    "group",
    "target_label",
    "role",
    "istd_pair",
    "analysis_mode",
    "resolver_mode",
    "candidate_id",
    "proposal_sources",
    "selected_candidate",
    "boundary_id",
    "boundary_sources",
    "rt_left_min",
    "rt_apex_min",
    "rt_right_min",
    "rt_width_min",
    "area_raw_counts_seconds",
    "area_baseline_corrected",
    "area_uncertainty",
    "baseline_type",
    "baseline_score",
    "scan_count",
    "area_delta_vs_candidate_interval",
    "area_ratio_vs_candidate_interval",
    "width_delta_vs_candidate_interval",
    "is_candidate_interval",
)


def build_peak_candidate_boundary_rows(
    *,
    sample_name: str,
    target_label: str,
    role: str,
    istd_pair: str,
    resolver_mode: str,
    peak_result: PeakDetectionResult,
    rt: Any,
    intensity: Any,
    group: str | None = None,
) -> list[PeakCandidateBoundaryRow]:
    sample_group = group or classify_sample_group(sample_name)
    selected = _selected_candidate(peak_result)
    rows: list[PeakCandidateBoundaryRow] = []
    for candidate in peak_result.candidates:
        candidate_id = candidate_audit_id(
            sample_name=sample_name,
            target_label=target_label,
            resolver_mode=resolver_mode,
            candidate=candidate,
        )
        boundaries = enumerate_boundary_hypotheses(
            rt,
            intensity,
            candidate,
            candidate_id=candidate_id,
        )
        reference = _candidate_interval_reference(boundaries)
        rows.extend(
            _row_from_boundary(
                sample_name=sample_name,
                group=sample_group,
                target_label=target_label,
                role=role,
                istd_pair=istd_pair,
                resolver_mode=resolver_mode,
                candidate=candidate,
                candidate_id=candidate_id,
                selected_candidate=selected is not None and candidate == selected,
                boundary=boundary,
                reference=reference,
                rt=rt,
                intensity=intensity,
            )
            for boundary in boundaries
        )
    return rows


def append_peak_candidate_boundary_rows(
    rows: list[PeakCandidateBoundaryRow] | None,
    config: ExtractionConfig,
    sample_name: str,
    target: Target,
    peak_result: PeakDetectionResult,
    *,
    rt: Any,
    intensity: Any,
    audit_peak_result: PeakDetectionResult | None = None,
) -> None:
    if not config.emit_peak_candidates or rows is None:
        return
    audited = audit_peak_result
    if audited is None:
        audited = add_cwt_proposals_for_audit(
            peak_result,
            rt,
            intensity,
            config,
        )
    rows.extend(
        build_peak_candidate_boundary_rows(
            sample_name=sample_name,
            target_label=target.label,
            role="ISTD" if target.is_istd else "Analyte",
            istd_pair=target.istd_pair,
            resolver_mode=config.resolver_mode,
            peak_result=audited,
            rt=rt,
            intensity=intensity,
        )
    )


def _row_from_boundary(
    *,
    sample_name: str,
    group: str,
    target_label: str,
    role: str,
    istd_pair: str,
    resolver_mode: str,
    candidate: PeakCandidate,
    candidate_id: str,
    selected_candidate: bool,
    boundary: BoundaryHypothesis,
    reference: BoundaryHypothesis,
    rt: Any,
    intensity: Any,
) -> PeakCandidateBoundaryRow:
    area_delta = boundary.area_raw_counts_seconds - reference.area_raw_counts_seconds
    width_delta = boundary.width_min - reference.width_min
    baseline = integrate_linear_edge_baseline(
        intensity,
        rt,
        boundary.left_index,
        boundary.right_index,
    )
    return {
        "sample_name": sample_name,
        "group": group,
        "target_label": target_label,
        "role": role,
        "istd_pair": istd_pair,
        "analysis_mode": "targeted",
        "resolver_mode": resolver_mode,
        "candidate_id": candidate_id,
        "proposal_sources": _join(candidate.proposal_sources),
        "selected_candidate": "TRUE" if selected_candidate else "FALSE",
        "boundary_id": boundary.boundary_id,
        "boundary_sources": _join(boundary.sources),
        "rt_left_min": _format_float(boundary.rt_left_min),
        "rt_apex_min": _format_float(boundary.rt_apex_min),
        "rt_right_min": _format_float(boundary.rt_right_min),
        "rt_width_min": _format_float(boundary.width_min),
        "area_raw_counts_seconds": _format_float(
            boundary.area_raw_counts_seconds,
            digits=2,
        ),
        "area_baseline_corrected": _format_float(
            baseline.area_baseline_corrected,
            digits=2,
        ),
        "area_uncertainty": _format_optional_float(baseline.area_uncertainty),
        "baseline_type": baseline.baseline_type,
        "baseline_score": _format_optional_float(baseline.baseline_score),
        "scan_count": str(boundary.scan_count),
        "area_delta_vs_candidate_interval": _format_float(area_delta, digits=2),
        "area_ratio_vs_candidate_interval": _format_optional_float(
            _safe_ratio(
                boundary.area_raw_counts_seconds,
                reference.area_raw_counts_seconds,
            )
        ),
        "width_delta_vs_candidate_interval": _format_float(width_delta),
        "is_candidate_interval": "TRUE"
        if "candidate_interval" in boundary.sources
        else "FALSE",
    }


def _selected_candidate(peak_result: PeakDetectionResult) -> PeakCandidate | None:
    if peak_result.peak is None:
        return None
    for candidate in peak_result.candidates:
        if candidate.peak == peak_result.peak:
            return candidate
    return None


def _candidate_interval_reference(
    boundaries: Sequence[BoundaryHypothesis],
) -> BoundaryHypothesis:
    for boundary in boundaries:
        if "candidate_interval" in boundary.sources:
            return boundary
    if not boundaries:
        raise ValueError("boundary rows require at least one boundary hypothesis")
    return boundaries[0]


def _safe_ratio(value: float, reference: float) -> float | None:
    if reference == 0:
        return None
    return value / reference


def _format_float(value: float, *, digits: int = 5) -> str:
    return f"{value:.{digits}f}"


def _format_optional_float(value: float | None) -> str:
    if value is None:
        return ""
    return _format_float(value)


def _join(values: tuple[str, ...]) -> str:
    return ";".join(values)
