from __future__ import annotations

import statistics
from collections.abc import Mapping, Sequence

from xic_extractor.peak_detection.region_mixture_diagnostic import (
    classify_local_mixture,
)
from xic_extractor.peak_detection.region_model_selection import (
    RegionBoundaryEvidence,
    RegionSelectionDecision,
    decide_region_selection,
)

PeakRegionSelectionShadowRow = dict[str, str]

PEAK_REGION_SELECTION_SHADOW_HEADERS = (
    "sample_name",
    "group",
    "target_label",
    "target_mz",
    "role",
    "istd_pair",
    "analysis_mode",
    "resolver_mode",
    "current_candidate_id",
    "current_boundary_id",
    "shadow_boundary_id",
    "current_rt_left_min",
    "current_rt_apex_min",
    "current_rt_right_min",
    "current_area_raw_counts_seconds",
    "shadow_rt_left_min",
    "shadow_rt_apex_min",
    "shadow_rt_right_min",
    "shadow_area_raw_counts_seconds",
    "shadow_status",
    "shadow_verdict",
    "merge_suggestion_source",
    "score_delta",
    "area_ratio",
    "current_scan_count",
    "shadow_scan_count",
    "selected_interval_count",
    "selected_interval_gap_max_min",
    "selected_interval_total_score",
    "best_single_boundary_score",
    "support_labels",
    "concern_labels",
    "local_mixture_diagnostic",
    "local_mixture_reason",
    "review_reason",
)

PEAK_REGION_SELECTION_SHADOW_SUMMARY_HEADERS = (
    "sample_name",
    "target_label",
    "target_mz",
    "role",
    "resolver_mode",
    "current_rt_apex_min",
    "shadow_rt_apex_min",
    "current_area_raw_counts_seconds",
    "shadow_area_raw_counts_seconds",
    "shadow_status",
    "shadow_verdict",
    "merge_suggestion_source",
    "score_delta",
    "area_ratio",
    "current_scan_count",
    "shadow_scan_count",
    "selected_interval_count",
    "selected_interval_gap_max_min",
    "selected_interval_total_score",
    "best_single_boundary_score",
    "local_mixture_diagnostic",
    "local_mixture_reason",
    "review_reason",
)

PEAK_REGION_SELECTION_BLAST_RADIUS_HEADERS = (
    "total_rows",
    "rows_that_would_change",
    "istd_rows_that_would_change",
    "affected_target_labels",
    "area_ratio_min",
    "area_ratio_median",
    "area_ratio_max",
)

_PROMOTING_VERDICTS = {
    "wider_boundary_preferred",
    "neighbor_apex_preferred",
    "merge_suggested",
    "split_supported",
}


def build_peak_region_selection_shadow_rows(
    boundary_rows: Sequence[Mapping[str, str]],
) -> list[PeakRegionSelectionShadowRow]:
    grouped: dict[tuple[str, str, str, str], list[Mapping[str, str]]] = {}
    for row in boundary_rows:
        grouped.setdefault(_group_key(row), []).append(row)

    output_rows: list[PeakRegionSelectionShadowRow] = []
    for rows in grouped.values():
        context = rows[0]
        try:
            evidence = tuple(_evidence_from_boundary_row(row) for row in rows)
            decision = decide_region_selection(evidence)
        except (TypeError, ValueError) as exc:
            decision = RegionSelectionDecision(
                shadow_status="skipped_invalid_trace",
                shadow_verdict="insufficient_evidence",
                review_reason=str(exc),
            )
        output_rows.append(_row_from_decision(context, decision))
    return output_rows


def build_peak_region_selection_shadow_summary_rows(
    rows: Sequence[Mapping[str, str]],
) -> list[PeakRegionSelectionShadowRow]:
    return [
        {
            header: str(row.get(header, ""))
            for header in PEAK_REGION_SELECTION_SHADOW_SUMMARY_HEADERS
        }
        for row in rows
    ]


def build_peak_region_selection_blast_radius_rows(
    rows: Sequence[Mapping[str, str]],
) -> list[PeakRegionSelectionShadowRow]:
    affected = [
        row
        for row in rows
        if row.get("shadow_status", "evaluated") == "evaluated"
        and row.get("shadow_verdict") in _PROMOTING_VERDICTS
    ]
    ratios = sorted(
        ratio
        for row in affected
        if (ratio := _parse_optional_float(row.get("area_ratio", ""))) is not None
    )
    labels = sorted(
        {
            row.get("target_label", "")
            for row in affected
            if row.get("target_label")
        }
    )
    istd_count = sum(1 for row in affected if row.get("role") == "ISTD")
    return [
        {
            "total_rows": str(len(rows)),
            "rows_that_would_change": str(len(affected)),
            "istd_rows_that_would_change": str(istd_count),
            "affected_target_labels": ";".join(labels),
            "area_ratio_min": _format_optional_float(ratios[0] if ratios else None),
            "area_ratio_median": _format_optional_float(
                statistics.median(ratios) if ratios else None
            ),
            "area_ratio_max": _format_optional_float(ratios[-1] if ratios else None),
        }
    ]


def _group_key(row: Mapping[str, str]) -> tuple[str, str, str, str]:
    return (
        str(row.get("sample_name", "")),
        str(row.get("target_label", "")),
        str(row.get("target_mz", "")),
        str(row.get("resolver_mode", "")),
    )


def _evidence_from_boundary_row(row: Mapping[str, str]) -> RegionBoundaryEvidence:
    return RegionBoundaryEvidence(
        boundary_id=_required(row, "boundary_id"),
        candidate_id=_required(row, "candidate_id"),
        proposal_sources=_split_labels(row.get("proposal_sources", "")),
        boundary_sources=_split_labels(row.get("boundary_sources", "")),
        selected_candidate=_parse_bool(row.get("selected_candidate", "")),
        is_candidate_interval=_parse_bool(row.get("is_candidate_interval", "")),
        nonoverlap_selected=_parse_bool(
            row.get("boundary_nonoverlap_selected", "")
        ),
        rt_left_min=_parse_float(row.get("rt_left_min", "")),
        rt_apex_min=_parse_float(row.get("rt_apex_min", "")),
        rt_right_min=_parse_float(row.get("rt_right_min", "")),
        area_raw_counts_seconds=_parse_float(
            row.get("area_raw_counts_seconds", "")
        ),
        boundary_score=_parse_int(row.get("boundary_audit_score", "")),
        scan_count=_parse_int(row.get("scan_count", "")),
        support_labels=_split_labels(row.get("boundary_support_labels", "")),
        concern_labels=_split_labels(row.get("boundary_concern_labels", "")),
    )


def _row_from_decision(
    context: Mapping[str, str],
    decision: RegionSelectionDecision,
) -> PeakRegionSelectionShadowRow:
    local_mixture = classify_local_mixture(decision)
    return {
        "sample_name": str(context.get("sample_name", "")),
        "group": str(context.get("group", "")),
        "target_label": str(context.get("target_label", "")),
        "target_mz": str(context.get("target_mz", "")),
        "role": str(context.get("role", "")),
        "istd_pair": str(context.get("istd_pair", "")),
        "analysis_mode": str(context.get("analysis_mode", "")),
        "resolver_mode": str(context.get("resolver_mode", "")),
        "current_candidate_id": decision.current_candidate_id,
        "current_boundary_id": decision.current_boundary_id,
        "shadow_boundary_id": decision.shadow_boundary_id,
        "current_rt_left_min": _format_optional_float(decision.current_rt_left_min),
        "current_rt_apex_min": _format_optional_float(decision.current_rt_apex_min),
        "current_rt_right_min": _format_optional_float(decision.current_rt_right_min),
        "current_area_raw_counts_seconds": _format_optional_float(
            decision.current_area_raw_counts_seconds,
            digits=2,
        ),
        "shadow_rt_left_min": _format_optional_float(decision.shadow_rt_left_min),
        "shadow_rt_apex_min": _format_optional_float(decision.shadow_rt_apex_min),
        "shadow_rt_right_min": _format_optional_float(decision.shadow_rt_right_min),
        "shadow_area_raw_counts_seconds": _format_optional_float(
            decision.shadow_area_raw_counts_seconds,
            digits=2,
        ),
        "shadow_status": decision.shadow_status,
        "shadow_verdict": decision.shadow_verdict,
        "merge_suggestion_source": decision.merge_suggestion_source,
        "score_delta": (
            ""
            if decision.score_delta is None
            else str(decision.score_delta)
        ),
        "area_ratio": _format_optional_float(decision.area_ratio),
        "current_scan_count": _format_optional_int(decision.current_scan_count),
        "shadow_scan_count": _format_optional_int(decision.shadow_scan_count),
        "selected_interval_count": _format_optional_int(
            decision.selected_interval_count
        ),
        "selected_interval_gap_max_min": _format_optional_float(
            decision.selected_interval_gap_max_min
        ),
        "selected_interval_total_score": _format_optional_int(
            decision.selected_interval_total_score
        ),
        "best_single_boundary_score": _format_optional_int(
            decision.best_single_boundary_score
        ),
        "support_labels": _join(decision.support_labels),
        "concern_labels": _join(decision.concern_labels),
        "local_mixture_diagnostic": local_mixture.label,
        "local_mixture_reason": local_mixture.reason,
        "review_reason": decision.review_reason,
    }


def _required(row: Mapping[str, str], header: str) -> str:
    value = str(row.get(header, ""))
    if value == "":
        raise ValueError(f"missing required boundary row field: {header}")
    return value


def _parse_bool(value: str) -> bool:
    return str(value).upper() == "TRUE"


def _parse_float(value: object) -> float:
    return float(str(value))


def _parse_optional_float(value: object) -> float | None:
    text = str(value).strip()
    if text == "":
        return None
    return float(text)


def _parse_int(value: object) -> int:
    return int(str(value))


def _split_labels(value: object) -> tuple[str, ...]:
    return tuple(label for label in str(value).split(";") if label)


def _join(values: tuple[str, ...]) -> str:
    return ";".join(values)


def _format_optional_float(value: float | None, *, digits: int = 5) -> str:
    if value is None:
        return ""
    return f"{value:.{digits}f}"


def _format_optional_int(value: int | None) -> str:
    if value is None:
        return ""
    return str(value)
