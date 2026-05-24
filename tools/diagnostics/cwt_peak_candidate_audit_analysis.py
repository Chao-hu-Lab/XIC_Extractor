from __future__ import annotations

from tools.diagnostics.cwt_peak_candidate_audit_models import (
    CwtCandidateRow,
    CwtGroupAuditRow,
    CwtOnlyAuditRow,
)


def _audit_groups(
    rows: tuple[CwtCandidateRow, ...],
    *,
    target_mz_by_label: dict[str, float],
    near_rt_window_min: float,
) -> tuple[CwtGroupAuditRow, ...]:
    grouped: dict[str, list[CwtCandidateRow]] = {}
    for row in rows:
        grouped.setdefault(row.group_id, []).append(row)
    return tuple(
        _audit_group(
            group_rows,
            target_mz_by_label=target_mz_by_label,
            near_rt_window_min=near_rt_window_min,
        )
        for _, group_rows in sorted(grouped.items(), key=lambda item: item[0])
    )


def _audit_group(
    rows: list[CwtCandidateRow],
    *,
    target_mz_by_label: dict[str, float],
    near_rt_window_min: float,
) -> CwtGroupAuditRow:
    first = rows[0]
    selected = next((row for row in rows if row.selected), None)
    cwt_rows = [row for row in rows if row.has_cwt]
    cwt_only_count = sum(row.cwt_only for row in rows)
    nearest = _nearest_cwt(selected, cwt_rows)
    nearest_delta = (
        abs(selected.rt_apex_min - nearest.rt_apex_min)
        if selected is not None and nearest is not None
        else None
    )
    agreement_class = _agreement_class(
        selected,
        cwt_rows,
        nearest_delta_min=nearest_delta,
        near_rt_window_min=near_rt_window_min,
    )
    return CwtGroupAuditRow(
        group_id=first.group_id,
        sample_name=first.sample_name,
        target_label=first.target_label,
        target_mz=target_mz_by_label.get(first.target_label),
        resolver_mode=first.resolver_mode,
        cwt_agreement_class=agreement_class,
        cwt_conditioned_class=_conditioned_class(agreement_class, nearest),
        candidate_count=len(rows),
        cwt_row_count=len(cwt_rows),
        cwt_only_row_count=cwt_only_count,
        selected_candidate_id=selected.candidate_id if selected else "",
        selected_rt_apex_min=selected.rt_apex_min if selected else None,
        selected_proposal_sources=selected.proposal_sources if selected else "",
        selected_ms2_present=selected.ms2_present if selected else "",
        selected_nl_match=selected.nl_match if selected else "",
        selected_ms2_trace_strength=selected.ms2_trace_strength if selected else "",
        nearest_cwt_candidate_id=nearest.candidate_id if nearest else "",
        nearest_cwt_rt_apex_min=nearest.rt_apex_min if nearest else None,
        nearest_cwt_delta_min=nearest_delta,
        nearest_cwt_ms2_present=nearest.ms2_present if nearest else "",
        nearest_cwt_nl_match=nearest.nl_match if nearest else "",
        nearest_cwt_ms2_trace_strength=nearest.ms2_trace_strength if nearest else "",
        selected_confidence=selected.confidence if selected else "",
        selected_raw_score=selected.raw_score if selected else "",
        selected_reason=selected.reason if selected else "",
    )


def _agreement_class(
    selected: CwtCandidateRow | None,
    cwt_rows: list[CwtCandidateRow],
    *,
    nearest_delta_min: float | None,
    near_rt_window_min: float,
) -> str:
    if selected is None:
        return "no_selected_candidate"
    if selected.has_cwt:
        return "selected_cwt_agreed"
    if cwt_rows:
        if nearest_delta_min is not None and nearest_delta_min <= near_rt_window_min:
            return "selected_cwt_nearby"
        return "selected_cwt_far_alternative"
    return "selected_without_cwt"


def _conditioned_class(
    agreement_class: str,
    nearest_cwt: CwtCandidateRow | None,
) -> str:
    if agreement_class in {"selected_cwt_agreed", "selected_cwt_nearby"}:
        return "cwt_selected_support"
    if agreement_class == "selected_cwt_far_alternative":
        if nearest_cwt is not None and _chemically_plausible(nearest_cwt):
            return "cwt_far_chemically_plausible"
        return "cwt_far_unconfirmed"
    if agreement_class == "selected_without_cwt":
        return "no_cwt_proposal"
    return agreement_class


def _chemically_plausible(row: CwtCandidateRow) -> bool:
    return (
        row.nl_match.strip().upper() == "TRUE"
        and row.ms2_trace_strength.strip().lower() in {"moderate", "strong"}
    )


def _nearest_cwt(
    selected: CwtCandidateRow | None,
    cwt_rows: list[CwtCandidateRow],
) -> CwtCandidateRow | None:
    if selected is None or not cwt_rows:
        return None
    return min(cwt_rows, key=lambda row: abs(selected.rt_apex_min - row.rt_apex_min))


def _cwt_only_rows(
    rows: tuple[CwtCandidateRow, ...],
    *,
    target_mz_by_label: dict[str, float],
) -> tuple[CwtOnlyAuditRow, ...]:
    return tuple(
        CwtOnlyAuditRow(
            group_id=row.group_id,
            sample_name=row.sample_name,
            target_label=row.target_label,
            target_mz=target_mz_by_label.get(row.target_label),
            resolver_mode=row.resolver_mode,
            candidate_id=row.candidate_id,
            rt_apex_min=row.rt_apex_min,
            confidence=row.confidence,
            raw_score=row.raw_score,
            reason=row.reason,
        )
        for row in rows
        if row.cwt_only
    )


def _summary(
    rows: tuple[CwtCandidateRow, ...],
    groups: tuple[CwtGroupAuditRow, ...],
    cwt_only_rows: tuple[CwtOnlyAuditRow, ...],
) -> dict[str, int]:
    return {
        "candidate_row_count": len(rows),
        "candidate_group_count": len(groups),
        "cwt_row_count": sum(row.has_cwt for row in rows),
        "cwt_only_row_count": len(cwt_only_rows),
        "selected_cwt_agreed_group_count": _group_class_count(
            groups, "selected_cwt_agreed"
        ),
        "selected_cwt_nearby_group_count": _group_class_count(
            groups, "selected_cwt_nearby"
        ),
        "selected_cwt_far_alternative_group_count": _group_class_count(
            groups, "selected_cwt_far_alternative"
        ),
        "selected_without_cwt_group_count": _group_class_count(
            groups, "selected_without_cwt"
        ),
        "cwt_selected_support_group_count": _conditioned_class_count(
            groups, "cwt_selected_support"
        ),
        "cwt_far_unconfirmed_group_count": _conditioned_class_count(
            groups, "cwt_far_unconfirmed"
        ),
        "cwt_far_chemically_plausible_group_count": _conditioned_class_count(
            groups, "cwt_far_chemically_plausible"
        ),
    }


def _group_class_count(
    groups: tuple[CwtGroupAuditRow, ...],
    cwt_agreement_class: str,
) -> int:
    return sum(row.cwt_agreement_class == cwt_agreement_class for row in groups)


def _conditioned_class_count(
    groups: tuple[CwtGroupAuditRow, ...],
    cwt_conditioned_class: str,
) -> int:
    return sum(row.cwt_conditioned_class == cwt_conditioned_class for row in groups)
