from __future__ import annotations

import json
from pathlib import Path

from tools.diagnostics.cwt_peak_candidate_audit_models import (
    _CWT_ONLY_COLUMNS,
    _GROUP_COLUMNS,
    _SUMMARY_COLUMNS,
    CwtGroupAuditRow,
    CwtOnlyAuditRow,
)
from tools.diagnostics.diagnostic_io import write_tsv


def _write_outputs(
    output_dir: Path,
    payload: dict[str, object],
    groups: tuple[CwtGroupAuditRow, ...],
    cwt_only_rows: tuple[CwtOnlyAuditRow, ...],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_summary(output_dir / "cwt_peak_candidate_audit_summary.tsv", payload)
    _write_groups(output_dir / "cwt_peak_candidate_groups.tsv", groups)
    _write_groups(
        output_dir / "cwt_peak_candidate_far_alternatives.tsv",
        tuple(
            row
            for row in groups
            if row.cwt_agreement_class == "selected_cwt_far_alternative"
        ),
    )
    _write_cwt_only(output_dir / "cwt_peak_candidate_cwt_only.tsv", cwt_only_rows)
    (output_dir / "cwt_peak_candidate_audit.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_dir / "cwt_peak_candidate_audit.md").write_text(
        _markdown(payload),
        encoding="utf-8",
    )


def _write_summary(path: Path, payload: dict[str, object]) -> None:
    summary = payload["summary"]
    if not isinstance(summary, dict):
        raise TypeError("summary payload must be a dictionary")
    write_tsv(path, (summary,), _SUMMARY_COLUMNS, extrasaction="raise")


def _write_groups(path: Path, rows: tuple[CwtGroupAuditRow, ...]) -> None:
    write_tsv(
        path,
        tuple(_format_group_row(row) for row in rows),
        _GROUP_COLUMNS,
        extrasaction="raise",
    )


def _write_cwt_only(path: Path, rows: tuple[CwtOnlyAuditRow, ...]) -> None:
    write_tsv(
        path,
        tuple(_format_cwt_only_row(row) for row in rows),
        _CWT_ONLY_COLUMNS,
        extrasaction="raise",
    )


def _format_group_row(row: CwtGroupAuditRow) -> dict[str, str]:
    return {
        "group_id": row.group_id,
        "sample_name": row.sample_name,
        "target_label": row.target_label,
        "target_mz": _format_optional_float(row.target_mz),
        "resolver_mode": row.resolver_mode,
        "cwt_agreement_class": row.cwt_agreement_class,
        "cwt_conditioned_class": row.cwt_conditioned_class,
        "candidate_count": str(row.candidate_count),
        "cwt_row_count": str(row.cwt_row_count),
        "cwt_only_row_count": str(row.cwt_only_row_count),
        "selected_candidate_id": row.selected_candidate_id,
        "selected_rt_apex_min": _format_optional_float(row.selected_rt_apex_min),
        "selected_proposal_sources": row.selected_proposal_sources,
        "selected_ms2_present": row.selected_ms2_present,
        "selected_nl_match": row.selected_nl_match,
        "selected_ms2_trace_strength": row.selected_ms2_trace_strength,
        "nearest_cwt_candidate_id": row.nearest_cwt_candidate_id,
        "nearest_cwt_rt_apex_min": _format_optional_float(row.nearest_cwt_rt_apex_min),
        "nearest_cwt_delta_min": _format_optional_float(row.nearest_cwt_delta_min),
        "nearest_cwt_ms2_present": row.nearest_cwt_ms2_present,
        "nearest_cwt_nl_match": row.nearest_cwt_nl_match,
        "nearest_cwt_ms2_trace_strength": row.nearest_cwt_ms2_trace_strength,
        "selected_confidence": row.selected_confidence,
        "selected_raw_score": row.selected_raw_score,
        "selected_reason": row.selected_reason,
    }


def _format_cwt_only_row(row: CwtOnlyAuditRow) -> dict[str, str]:
    return {
        "group_id": row.group_id,
        "sample_name": row.sample_name,
        "target_label": row.target_label,
        "target_mz": _format_optional_float(row.target_mz),
        "resolver_mode": row.resolver_mode,
        "candidate_id": row.candidate_id,
        "rt_apex_min": _format_optional_float(row.rt_apex_min),
        "confidence": row.confidence,
        "raw_score": row.raw_score,
        "reason": row.reason,
    }


def _markdown(payload: dict[str, object]) -> str:
    summary = payload["summary"]
    if not isinstance(summary, dict):
        raise TypeError("summary payload must be a dictionary")
    return "\n".join(
        [
            "# CWT Peak Candidate Audit",
            "",
            f"- candidate_row_count: {summary['candidate_row_count']}",
            f"- candidate_group_count: {summary['candidate_group_count']}",
            f"- cwt_row_count: {summary['cwt_row_count']}",
            f"- cwt_only_row_count: {summary['cwt_only_row_count']}",
            "- selected_cwt_agreed_group_count: "
            f"{summary['selected_cwt_agreed_group_count']}",
            "- selected_cwt_nearby_group_count: "
            f"{summary['selected_cwt_nearby_group_count']}",
            "- selected_cwt_far_alternative_group_count: "
            f"{summary['selected_cwt_far_alternative_group_count']}",
            "- selected_without_cwt_group_count: "
            f"{summary['selected_without_cwt_group_count']}",
            "- cwt_selected_support_group_count: "
            f"{summary['cwt_selected_support_group_count']}",
            "- cwt_far_unconfirmed_group_count: "
            f"{summary['cwt_far_unconfirmed_group_count']}",
            "- cwt_far_chemically_plausible_group_count: "
            f"{summary['cwt_far_chemically_plausible_group_count']}",
            "",
        ]
    )


def _format_optional_float(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value:.5f}"
