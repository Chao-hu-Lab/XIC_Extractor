from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import asdict
from typing import Literal

from xic_extractor.peak_detection.selected_envelope import (
    SelectedEnvelopeBoundaryEvaluation,
    SelectedEnvelopePolicy,
    TraceInterval,
)

SelectedEnvelopeDiagnosticRow = dict[str, str]
SelectedEnvelopeGateManifest = dict[str, str]
SelectedEnvelopeGateDecision = Literal["promote", "no_go", "externalize", "defer"]

SELECTED_ENVELOPE_DIAGNOSTIC_HEADERS = (
    "sample_name",
    "target_label",
    "role",
    "selected_candidate_id",
    "selected_boundary_mode",
    "row_boundary_decision",
    "legacy_resolver_provenance",
    "resolver_rt_start",
    "resolver_rt_end",
    "envelope_rt_start",
    "envelope_rt_end",
    "quantitation_context_rt_start",
    "quantitation_context_rt_end",
    "morphology_trace_method",
    "morphology_trace_window_points",
    "morphology_trace_effective_points",
    "policy_snapshot",
    "resolved_baseline_return_threshold",
    "boundary_change_class",
    "boundary_evidence_sources",
    "boundary_stop_reason",
    "asls_area_old_interval",
    "asls_area_selected_envelope",
    "area_delta_ratio",
    "gaussian15_area_old_interval_shadow",
    "gaussian15_area_selected_envelope_shadow",
    "gaussian15_area_delta_ratio_shadow",
    "plot_path",
)

SELECTED_ENVELOPE_GATE_MANIFEST_FIELDS = (
    "gate_decision",
    "changed_row_count",
    "changed_row_denominator",
    "high_risk_strata",
    "unresolved_blocker_count",
    "blocked_reasons",
    "next_gate",
)

_HIGH_RISK_CHANGE_CLASSES = {
    "neighbor_apex",
    "split_supported",
    "tail_uncertain",
    "overmerge_rejected",
    "carryover_blank_like",
    "low_sn",
    "low_scan",
    "malformed",
    "context_apex_conflict",
}


def selected_envelope_diagnostic_row(
    *,
    sample_name: str,
    target_label: str,
    role: str,
    evaluation: SelectedEnvelopeBoundaryEvaluation,
    plot_path: str = "",
) -> SelectedEnvelopeDiagnosticRow:
    if not evaluation.selected_candidate_id:
        raise ValueError("selected_candidate_id is required for diagnostics")

    row = {
        "sample_name": sample_name,
        "target_label": target_label,
        "role": role,
        "selected_candidate_id": evaluation.selected_candidate_id,
        "selected_boundary_mode": evaluation.selected_boundary_mode,
        "row_boundary_decision": evaluation.row_boundary_decision,
        "legacy_resolver_provenance": evaluation.legacy_resolver_provenance,
        "resolver_rt_start": _format_interval_start(evaluation.resolver_interval),
        "resolver_rt_end": _format_interval_end(evaluation.resolver_interval),
        "envelope_rt_start": _format_interval_start(
            evaluation.selected_envelope_interval
        ),
        "envelope_rt_end": _format_interval_end(
            evaluation.selected_envelope_interval
        ),
        "quantitation_context_rt_start": _format_interval_start(
            evaluation.quantitation_context_interval
        ),
        "quantitation_context_rt_end": _format_interval_end(
            evaluation.quantitation_context_interval
        ),
        "morphology_trace_method": evaluation.morphology_trace_method,
        "morphology_trace_window_points": str(
            evaluation.morphology_trace_window_points
        ),
        "morphology_trace_effective_points": str(
            evaluation.morphology_trace_effective_points
        ),
        "policy_snapshot": _policy_snapshot(evaluation.policy_snapshot),
        "resolved_baseline_return_threshold": _format_optional_float(
            evaluation.resolved_baseline_return_threshold
        ),
        "boundary_change_class": evaluation.boundary_change_class,
        "boundary_evidence_sources": _join(evaluation.boundary_evidence_sources),
        "boundary_stop_reason": evaluation.boundary_stop_reason,
        "asls_area_old_interval": _format_optional_float(
            evaluation.asls_area_old_interval,
            digits=2,
        ),
        "asls_area_selected_envelope": _format_optional_float(
            evaluation.asls_area_selected_envelope,
            digits=2,
        ),
        "area_delta_ratio": _format_optional_float(evaluation.area_delta_ratio),
        "gaussian15_area_old_interval_shadow": _format_optional_float(
            evaluation.gaussian15_area_old_interval_shadow,
            digits=2,
        ),
        "gaussian15_area_selected_envelope_shadow": _format_optional_float(
            evaluation.gaussian15_area_selected_envelope_shadow,
            digits=2,
        ),
        "gaussian15_area_delta_ratio_shadow": _format_optional_float(
            evaluation.gaussian15_area_delta_ratio_shadow,
        ),
        "plot_path": plot_path,
    }
    return {header: row[header] for header in SELECTED_ENVELOPE_DIAGNOSTIC_HEADERS}


def build_selected_envelope_gate_manifest(
    evaluations: tuple[SelectedEnvelopeBoundaryEvaluation, ...],
) -> SelectedEnvelopeGateManifest:
    if not evaluations:
        return {
            "gate_decision": "defer",
            "changed_row_count": "0",
            "changed_row_denominator": "0",
            "high_risk_strata": "",
            "unresolved_blocker_count": "1",
            "blocked_reasons": "no_evaluated_rows",
            "next_gate": "bounded_follow_up_required",
        }

    gate_decision = _gate_decision(evaluations)
    blocked_reasons = _blocked_reasons(evaluations)
    manifest = {
        "gate_decision": gate_decision,
        "changed_row_count": str(
            sum(1 for evaluation in evaluations if _is_changed(evaluation))
        ),
        "changed_row_denominator": str(len(evaluations)),
        "high_risk_strata": _join(
            tuple(
                sorted(
                    {
                        evaluation.boundary_change_class
                        for evaluation in evaluations
                        if evaluation.boundary_change_class
                        in _HIGH_RISK_CHANGE_CLASSES
                    }
                )
            )
        ),
        "unresolved_blocker_count": str(
            sum(
                1
                for evaluation in evaluations
                if evaluation.row_boundary_decision != "accept_candidate"
            )
        ),
        "blocked_reasons": _join(blocked_reasons),
        "next_gate": _next_gate(gate_decision),
    }
    return {field: manifest[field] for field in SELECTED_ENVELOPE_GATE_MANIFEST_FIELDS}


def build_selected_envelope_gate_manifest_from_rows(
    diagnostic_rows: Iterable[Mapping[str, str]],
) -> SelectedEnvelopeGateManifest:
    rows = tuple(diagnostic_rows)
    if not rows:
        return {
            "gate_decision": "defer",
            "changed_row_count": "0",
            "changed_row_denominator": "0",
            "high_risk_strata": "",
            "unresolved_blocker_count": "1",
            "blocked_reasons": "no_evaluated_rows",
            "next_gate": "bounded_follow_up_required",
        }

    gate_decision = _gate_decision_from_row_decisions(
        tuple(row.get("row_boundary_decision", "") for row in rows)
    )
    blocked_reasons = _blocked_reasons_from_rows(rows)
    manifest = {
        "gate_decision": gate_decision,
        "changed_row_count": str(sum(1 for row in rows if _is_changed_row(row))),
        "changed_row_denominator": str(len(rows)),
        "high_risk_strata": _join(
            tuple(
                sorted(
                    {
                        row.get("boundary_change_class", "")
                        for row in rows
                        if row.get("boundary_change_class", "")
                        in _HIGH_RISK_CHANGE_CLASSES
                    }
                )
            )
        ),
        "unresolved_blocker_count": str(
            sum(
                1
                for row in rows
                if row.get("row_boundary_decision", "") != "accept_candidate"
            )
        ),
        "blocked_reasons": _join(blocked_reasons),
        "next_gate": _next_gate(gate_decision),
    }
    return {field: manifest[field] for field in SELECTED_ENVELOPE_GATE_MANIFEST_FIELDS}


def _gate_decision(
    evaluations: tuple[SelectedEnvelopeBoundaryEvaluation, ...],
) -> SelectedEnvelopeGateDecision:
    row_decisions = {evaluation.row_boundary_decision for evaluation in evaluations}
    if "reject" in row_decisions:
        return "no_go"
    if "defer" in row_decisions:
        return "defer"
    if "externalize" in row_decisions:
        return "externalize"
    return "promote"


def _gate_decision_from_row_decisions(
    row_decisions: tuple[str, ...],
) -> SelectedEnvelopeGateDecision:
    decisions = set(row_decisions)
    if "reject" in decisions:
        return "no_go"
    if decisions - {"accept_candidate", "defer", "externalize", "reject"}:
        return "defer"
    if "defer" in decisions:
        return "defer"
    if "externalize" in decisions:
        return "externalize"
    return "promote"


def _next_gate(gate_decision: SelectedEnvelopeGateDecision) -> str:
    if gate_decision == "promote":
        return "manual_overlay_oracle"
    if gate_decision == "no_go":
        return "stop_selected_envelope_product_path"
    if gate_decision == "externalize":
        return "diagnostic_review_only"
    return "bounded_follow_up_required"


def _blocked_reasons(
    evaluations: tuple[SelectedEnvelopeBoundaryEvaluation, ...],
) -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                evaluation.boundary_stop_reason
                for evaluation in evaluations
                if evaluation.row_boundary_decision != "accept_candidate"
                and evaluation.boundary_stop_reason
            }
        )
    )


def _blocked_reasons_from_rows(rows: tuple[Mapping[str, str], ...]) -> tuple[str, ...]:
    reasons = {
        row.get("boundary_stop_reason", "")
        for row in rows
        if row.get("row_boundary_decision", "") != "accept_candidate"
        and row.get("boundary_stop_reason", "")
    }
    if any(
        row.get("row_boundary_decision", "")
        not in {"accept_candidate", "defer", "externalize", "reject"}
        for row in rows
    ):
        reasons.add("unknown_row_boundary_decision")
    return tuple(sorted(reasons))


def _is_changed(evaluation: SelectedEnvelopeBoundaryEvaluation) -> bool:
    return evaluation.boundary_change_class != "no_change"


def _is_changed_row(row: Mapping[str, str]) -> bool:
    return row.get("boundary_change_class", "") != "no_change"


def _policy_snapshot(policy: SelectedEnvelopePolicy) -> str:
    return ";".join(
        f"{name}={_format_compact_float(value)}"
        for name, value in sorted(asdict(policy).items())
    )


def _format_interval_start(interval: TraceInterval) -> str:
    return _format_float(interval.rt_start_min)


def _format_interval_end(interval: TraceInterval) -> str:
    return _format_float(interval.rt_end_min)


def _format_optional_float(value: float | None, *, digits: int = 5) -> str:
    if value is None:
        return ""
    return _format_float(value, digits=digits)


def _format_float(value: float, *, digits: int = 5) -> str:
    return f"{value:.{digits}f}"


def _format_compact_float(value: object) -> str:
    if isinstance(value, float):
        return f"{value:g}"
    return str(value)


def _join(values: tuple[str, ...]) -> str:
    return ";".join(values)
