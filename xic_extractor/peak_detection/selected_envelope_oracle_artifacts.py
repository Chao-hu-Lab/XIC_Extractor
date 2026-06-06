from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import cast

from xic_extractor.peak_detection.selected_envelope_oracle import (
    BoundaryOracle,
    OracleSource,
    OracleStatus,
)

SelectedEnvelopeOracleReviewQueueRow = dict[str, str]
SelectedEnvelopeBoundaryOracleRow = dict[str, str]

SELECTED_ENVELOPE_ORACLE_REVIEW_QUEUE_HEADERS = (
    "oracle_row_id",
    "sample_name",
    "target_label",
    "role",
    "selected_candidate_id",
    "review_priority",
    "review_reason",
    "boundary_change_class",
    "row_boundary_decision",
    "resolver_rt_start",
    "resolver_rt_end",
    "candidate_envelope_rt_start",
    "candidate_envelope_rt_end",
    "asls_area_old_interval",
    "asls_area_selected_envelope",
    "area_delta_ratio",
    "diagnostic_plot_path",
    "allowed_oracle_sources",
    "required_oracle_status",
    "reviewed_rt_start_min",
    "reviewed_rt_end_min",
    "reviewed_area_baseline_corrected",
    "shape_class",
    "acceptable_boundary_delta_min",
    "acceptable_area_relative_error",
    "review_note",
)

SELECTED_ENVELOPE_BOUNDARY_ORACLE_HEADERS = (
    "oracle_row_id",
    "selected_candidate_id",
    "oracle_status",
    "oracle_source",
    "rt_start_min",
    "rt_end_min",
    "area_baseline_corrected",
    "shape_class",
    "acceptable_boundary_delta_min",
    "acceptable_area_relative_error",
    "required_plot_path",
)

_ALLOWED_EXPERT_ORACLE_SOURCES = ("manual_overlay", "expert_overlay", "manual_2raw")
_HIGH_RISK_CHANGE_CLASSES = {
    "neighbor_apex",
    "split_supported",
    "tail_uncertain",
    "overmerge_rejected",
    "carryover_blank_like",
    "low_sn",
    "low_scan",
    "malformed",
}


def build_selected_envelope_oracle_review_queue(
    diagnostic_rows: Iterable[Mapping[str, str]],
) -> tuple[SelectedEnvelopeOracleReviewQueueRow, ...]:
    queue: list[SelectedEnvelopeOracleReviewQueueRow] = []
    for diagnostic_row in diagnostic_rows:
        selected_candidate_id = _required_text(
            diagnostic_row,
            "selected_candidate_id",
        )
        boundary_change_class = diagnostic_row.get("boundary_change_class", "")
        row_boundary_decision = diagnostic_row.get("row_boundary_decision", "")
        if (
            boundary_change_class == "no_change"
            and row_boundary_decision == "accept_candidate"
        ):
            continue

        row = {
            "oracle_row_id": _oracle_row_id(diagnostic_row, selected_candidate_id),
            "sample_name": diagnostic_row.get("sample_name", ""),
            "target_label": diagnostic_row.get("target_label", ""),
            "role": diagnostic_row.get("role", ""),
            "selected_candidate_id": selected_candidate_id,
            "review_priority": _review_priority(
                boundary_change_class,
                row_boundary_decision,
            ),
            "review_reason": _review_reason(diagnostic_row),
            "boundary_change_class": boundary_change_class,
            "row_boundary_decision": row_boundary_decision,
            "resolver_rt_start": diagnostic_row.get("resolver_rt_start", ""),
            "resolver_rt_end": diagnostic_row.get("resolver_rt_end", ""),
            "candidate_envelope_rt_start": diagnostic_row.get(
                "envelope_rt_start",
                "",
            ),
            "candidate_envelope_rt_end": diagnostic_row.get("envelope_rt_end", ""),
            "asls_area_old_interval": diagnostic_row.get("asls_area_old_interval", ""),
            "asls_area_selected_envelope": diagnostic_row.get(
                "asls_area_selected_envelope",
                "",
            ),
            "area_delta_ratio": diagnostic_row.get("area_delta_ratio", ""),
            "diagnostic_plot_path": diagnostic_row.get("plot_path", ""),
            "allowed_oracle_sources": ";".join(_ALLOWED_EXPERT_ORACLE_SOURCES),
            "required_oracle_status": "expert_reviewed",
            "reviewed_rt_start_min": "",
            "reviewed_rt_end_min": "",
            "reviewed_area_baseline_corrected": "",
            "shape_class": "",
            "acceptable_boundary_delta_min": "0.1",
            "acceptable_area_relative_error": "0.1",
            "review_note": "",
        }
        queue.append(
            {
                header: row[header]
                for header in SELECTED_ENVELOPE_ORACLE_REVIEW_QUEUE_HEADERS
            }
        )
    return tuple(queue)


def boundary_oracle_artifact_row(
    oracle: BoundaryOracle,
) -> SelectedEnvelopeBoundaryOracleRow:
    _validate_boundary_oracle(oracle)
    row = {
        "oracle_row_id": oracle.oracle_row_id,
        "selected_candidate_id": oracle.selected_candidate_id,
        "oracle_status": oracle.oracle_status,
        "oracle_source": oracle.oracle_source,
        "rt_start_min": _format_float(oracle.rt_start_min),
        "rt_end_min": _format_float(oracle.rt_end_min),
        "area_baseline_corrected": _format_optional_float(
            oracle.area_baseline_corrected
        ),
        "shape_class": oracle.shape_class,
        "acceptable_boundary_delta_min": _format_float(
            oracle.acceptable_boundary_delta_min
        ),
        "acceptable_area_relative_error": _format_float(
            oracle.acceptable_area_relative_error
        ),
        "required_plot_path": oracle.required_plot_path,
    }
    return {header: row[header] for header in SELECTED_ENVELOPE_BOUNDARY_ORACLE_HEADERS}


def parse_selected_envelope_boundary_oracle_rows(
    rows: Iterable[Mapping[str, str]],
) -> tuple[BoundaryOracle, ...]:
    return tuple(_parse_boundary_oracle_row(row) for row in rows)


def _parse_boundary_oracle_row(row: Mapping[str, str]) -> BoundaryOracle:
    oracle_row_id = _required_text(row, "oracle_row_id")
    selected_candidate_id = _required_text(row, "selected_candidate_id")
    oracle_status = _oracle_status(_required_text(row, "oracle_status"))
    oracle_source = _oracle_source(_required_text(row, "oracle_source"))
    _validate_oracle_status_source(oracle_status, oracle_source)

    rt_start_min = _required_float(row, "rt_start_min")
    rt_end_min = _required_float(row, "rt_end_min")
    if rt_end_min <= rt_start_min:
        raise ValueError("rt_start_min must be lower than rt_end_min")

    area = _optional_positive_float(row, "area_baseline_corrected")
    if oracle_status == "expert_reviewed" and area is None:
        raise ValueError("area_baseline_corrected is required for expert oracle rows")

    oracle = BoundaryOracle(
        oracle_row_id=oracle_row_id,
        selected_candidate_id=selected_candidate_id,
        oracle_status=oracle_status,
        oracle_source=oracle_source,
        rt_start_min=rt_start_min,
        rt_end_min=rt_end_min,
        area_baseline_corrected=area,
        shape_class=_required_text(row, "shape_class"),
        acceptable_boundary_delta_min=_required_positive_float(
            row,
            "acceptable_boundary_delta_min",
        ),
        acceptable_area_relative_error=_required_positive_float(
            row,
            "acceptable_area_relative_error",
        ),
        required_plot_path=row.get("required_plot_path", ""),
    )
    _validate_boundary_oracle(oracle)
    return oracle


def _validate_boundary_oracle(oracle: BoundaryOracle) -> None:
    if not oracle.oracle_row_id.strip():
        raise ValueError("oracle_row_id is required")
    if not oracle.selected_candidate_id.strip():
        raise ValueError("selected_candidate_id is required")
    oracle_status = _oracle_status(oracle.oracle_status)
    oracle_source = _oracle_source(oracle.oracle_source)
    _validate_oracle_status_source(oracle_status, oracle_source)
    if oracle.rt_end_min <= oracle.rt_start_min:
        raise ValueError("rt_start_min must be lower than rt_end_min")
    if oracle_status == "expert_reviewed" and oracle.area_baseline_corrected is None:
        raise ValueError("area_baseline_corrected is required for expert oracle rows")
    if (
        oracle.area_baseline_corrected is not None
        and oracle.area_baseline_corrected <= 0.0
    ):
        raise ValueError("area_baseline_corrected must be positive")
    if not oracle.shape_class.strip():
        raise ValueError("shape_class is required")
    if oracle.acceptable_boundary_delta_min <= 0.0:
        raise ValueError("acceptable_boundary_delta_min must be positive")
    if oracle.acceptable_area_relative_error <= 0.0:
        raise ValueError("acceptable_area_relative_error must be positive")


def _oracle_row_id(
    row: Mapping[str, str],
    selected_candidate_id: str,
) -> str:
    return "|".join(
        (
            row.get("sample_name", ""),
            row.get("target_label", ""),
            selected_candidate_id,
        )
    )


def _review_priority(
    boundary_change_class: str,
    row_boundary_decision: str,
) -> str:
    if (
        boundary_change_class in _HIGH_RISK_CHANGE_CLASSES
        or row_boundary_decision != "accept_candidate"
    ):
        return "high_risk_boundary_review"
    return "changed_boundary_review"


def _review_reason(row: Mapping[str, str]) -> str:
    return ";".join(
        value
        for value in (
            row.get("boundary_change_class", ""),
            row.get("boundary_stop_reason", ""),
            row.get("row_boundary_decision", ""),
        )
        if value
    )


def _oracle_status(value: str) -> OracleStatus:
    if value in {"expert_reviewed", "benchmark_control_only"}:
        return cast(OracleStatus, value)
    raise ValueError(f"invalid oracle_status: {value}")


def _oracle_source(value: str) -> OracleSource:
    if value in {
        "manual_overlay",
        "expert_overlay",
        "manual_2raw",
        "targeted_workbook_control",
    }:
        return cast(OracleSource, value)
    raise ValueError(f"invalid oracle_source: {value}")


def _validate_oracle_status_source(
    oracle_status: OracleStatus,
    oracle_source: OracleSource,
) -> None:
    if oracle_status == "benchmark_control_only":
        if oracle_source != "targeted_workbook_control":
            raise ValueError(
                "benchmark_control_only rows must use targeted_workbook_control"
            )
        return
    if oracle_source == "targeted_workbook_control":
        raise ValueError("targeted workbook area cannot be a boundary oracle")


def _required_text(row: Mapping[str, str], field: str) -> str:
    value = row.get(field, "").strip()
    if not value:
        raise ValueError(f"{field} is required")
    return value


def _required_float(row: Mapping[str, str], field: str) -> float:
    value = _required_text(row, field)
    try:
        return float(value)
    except ValueError as exc:
        raise ValueError(f"{field} must be numeric") from exc


def _required_positive_float(row: Mapping[str, str], field: str) -> float:
    value = _required_float(row, field)
    if value <= 0.0:
        raise ValueError(f"{field} must be positive")
    return value


def _optional_positive_float(row: Mapping[str, str], field: str) -> float | None:
    raw = row.get(field, "").strip()
    if not raw:
        return None
    try:
        value = float(raw)
    except ValueError as exc:
        raise ValueError(f"{field} must be numeric") from exc
    if value <= 0.0:
        raise ValueError(f"{field} must be positive")
    return value


def _format_float(value: float) -> str:
    return f"{value:.6g}"


def _format_optional_float(value: float | None) -> str:
    if value is None:
        return ""
    return _format_float(value)
