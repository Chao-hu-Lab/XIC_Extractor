"""Bridge PeakHypothesis backfill promotions into activation sidecars.

This module does not apply activation or write matrices. It converts reviewed
backfill PeakHypothesis promotion rows into the existing shared-peak activation
decision/acceptance TSV contract so the established activation owner remains
the only matrix writer.
"""

from __future__ import annotations

import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from xic_extractor.alignment.shared_peak_identity_explanation.schema import (
    ACTIVATION_ACCEPTANCE_COLUMNS,
    ACTIVATION_ACCEPTANCE_SCHEMA_VERSION,
    ACTIVATION_DECISION_COLUMNS,
    ACTIVATION_DECISION_SCHEMA_VERSION,
)
from xic_extractor.diagnostics import (
    backfill_peakhypothesis_normal_peak_decision,
    backfill_peakhypothesis_promotion,
)
from xic_extractor.diagnostics.diagnostic_io import (
    format_diagnostic_value,
    numeric_equal,
    text_value,
    write_tsv,
)
from xic_extractor.diagnostics.matrix_identity_projection import (
    matrix_values_by_identity,
)

SCHEMA_VERSION = "backfill_peakhypothesis_activation_bridge_v1"
PROMOTION_INPUT_REQUIRED_COLUMNS = backfill_peakhypothesis_promotion.PROMOTION_COLUMNS
NORMAL_PEAK_DECISION_INPUT_REQUIRED_COLUMNS = (
    backfill_peakhypothesis_normal_peak_decision.DECISION_COLUMNS
)

_PROMOTE_DECISION = "promote_matrix_write"
_ACTIVATION_RULE_ID = "machine_observed_sufficient_positive_identity"
_ACTIVATION_REASON = "allowlisted_peakhypothesis_same_peak_backfill"
_ACCEPTANCE_FAIL_REASON = "activation_acceptance_requires_matrix_diff_validation"
_NEXT_ACTION = "run_activation_matrix_diff_smoke"
_MATRIX_CONFLICT_REASON = "public_matrix_conflicts_with_projection_current_snapshot"
_NORMAL_PEAK_DECISION_FAIL_REASON = (
    "normal_peak_decision_missing_or_not_required"
)
_NORMAL_PEAK_DECISION_NEXT_ACTION = "review_normal_peak_decision_before_activation"
_MATRIX_CONFLICT_NEXT_ACTION = (
    "rebuild_alignment_matrix_with_current_writer_before_activation"
)

MATRIX_PREFLIGHT_COLUMNS = (
    "schema_version",
    "peak_hypothesis_id",
    "feature_family_id",
    "sample_stem",
    "promotion_decision",
    "projection_current_matrix_written",
    "public_matrix_written",
    "public_matrix_value",
    "preflight_status",
    "bridge_action",
    "preflight_reason",
)


@dataclass(frozen=True)
class ActivationBridgeIndex:
    activation_decision_rows: tuple[dict[str, str], ...]
    activation_matrix_preflight_rows: tuple[dict[str, str], ...]
    activation_acceptance_row: dict[str, str]
    summary: dict[str, Any]


@dataclass(frozen=True)
class ActivationBridgeOutputs:
    activation_decisions_tsv: Path
    activation_acceptance_tsv: Path
    activation_matrix_preflight_tsv: Path
    summary_json: Path


def build_activation_bridge(
    promotion_rows: Sequence[Mapping[str, Any]],
    *,
    public_matrix_rows: Sequence[Mapping[str, Any]] = (),
    matrix_identity_rows: Sequence[Mapping[str, Any]] = (),
    normal_peak_decision_rows: Sequence[Mapping[str, Any]] = (),
    source_run_id: str = "",
) -> ActivationBridgeIndex:
    public_matrix_values = _public_matrix_written_values(
        public_matrix_rows,
        matrix_identity_rows,
    )
    normal_decision_by_key = _normal_decision_by_key(normal_peak_decision_rows)
    promoted_rows = tuple(
        row
        for row in promotion_rows
        if _value(row, "promotion_decision") == _PROMOTE_DECISION
    )
    eligible_rows = tuple(
        row
        for row in promoted_rows
        if _normal_peak_required(row, normal_decision_by_key)
    )
    normal_peak_decision_blocked_count = (
        0 if not normal_peak_decision_rows else len(promoted_rows) - len(eligible_rows)
    )
    public_matrix_written_count = sum(
        1 for row in eligible_rows if _promotion_key(row) in public_matrix_values
    )
    conflict_count = sum(
        1
        for row in eligible_rows
        if _has_public_matrix_projection_conflict(row, public_matrix_values)
    )
    preflight_rows = tuple(
        _matrix_preflight_row(row, public_matrix_values) for row in eligible_rows
    )
    decision_rows = tuple(
        _activation_decision_row(row)
        for row in eligible_rows
        if _promotion_key(row) not in public_matrix_values
    )
    acceptance_row = _activation_acceptance_row(
        promotion_rows=promotion_rows,
        decision_rows=decision_rows,
        public_matrix_already_written_count=public_matrix_written_count,
        public_matrix_projection_conflict_count=conflict_count,
        normal_peak_decision_blocked_count=normal_peak_decision_blocked_count,
    )
    return ActivationBridgeIndex(
        activation_decision_rows=decision_rows,
        activation_matrix_preflight_rows=preflight_rows,
        activation_acceptance_row=acceptance_row,
        summary=_summary(
            promotion_rows=promotion_rows,
            decision_rows=decision_rows,
            public_matrix_already_written_count=public_matrix_written_count,
            public_matrix_projection_conflict_count=conflict_count,
            normal_peak_decision_input_count=len(normal_peak_decision_rows),
            normal_peak_required_backfill_count=len(eligible_rows),
            normal_peak_decision_blocked_count=normal_peak_decision_blocked_count,
            matrix_preflight_row_count=len(preflight_rows),
            source_run_id=source_run_id,
        ),
    )


def write_activation_bridge_outputs(
    output_dir: Path,
    index: ActivationBridgeIndex,
) -> ActivationBridgeOutputs:
    output_dir.mkdir(parents=True, exist_ok=True)
    decisions_tsv = output_dir / "activation_decisions.tsv"
    acceptance_tsv = output_dir / "activation_acceptance.tsv"
    preflight_tsv = output_dir / "activation_matrix_preflight.tsv"
    summary_json = output_dir / "backfill_peakhypothesis_activation_bridge_summary.json"
    write_tsv(
        decisions_tsv,
        index.activation_decision_rows,
        ACTIVATION_DECISION_COLUMNS,
        formatter=format_diagnostic_value,
        lineterminator="\n",
    )
    write_tsv(
        acceptance_tsv,
        [index.activation_acceptance_row],
        ACTIVATION_ACCEPTANCE_COLUMNS,
        formatter=format_diagnostic_value,
        lineterminator="\n",
    )
    write_tsv(
        preflight_tsv,
        index.activation_matrix_preflight_rows,
        MATRIX_PREFLIGHT_COLUMNS,
        formatter=format_diagnostic_value,
        lineterminator="\n",
    )
    summary_json.write_text(
        json.dumps(index.summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return ActivationBridgeOutputs(
        activation_decisions_tsv=decisions_tsv,
        activation_acceptance_tsv=acceptance_tsv,
        activation_matrix_preflight_tsv=preflight_tsv,
        summary_json=summary_json,
    )


def _activation_decision_row(row: Mapping[str, Any]) -> dict[str, str]:
    _validate_promoted_row(row)
    family_id = _value(row, "feature_family_id")
    sample = _value(row, "sample_stem")
    peak_hypothesis_id = _value(row, "peak_hypothesis_id")
    return {
        "activation_schema_version": ACTIVATION_DECISION_SCHEMA_VERSION,
        "feature_family_id": family_id,
        "candidate_container_id": family_id,
        "sample_id": sample,
        "peak_hypothesis_id": peak_hypothesis_id,
        "activation_unit_scope": "peak_hypothesis",
        "machine_current_label": _value(row, "current_production_status"),
        "evidence_support_status": _value(row, "promotion_decision"),
        "activation_status": "auto_activate",
        "activation_action": "activate_pass",
        "product_label_candidate": "pass",
        "product_effect": "accept_label_or_rescue",
        "activation_confidence": "review",
        "hard_product_block": "FALSE",
        "contract_rule_id": _ACTIVATION_RULE_ID,
        "activation_reason": _ACTIVATION_REASON,
        "required_review_reason": "",
        "source_evidence_tokens": _source_evidence_tokens(row),
        "diagnostic_only": "FALSE",
    }


def _activation_acceptance_row(
    *,
    promotion_rows: Sequence[Mapping[str, Any]],
    decision_rows: Sequence[Mapping[str, str]],
    public_matrix_already_written_count: int,
    public_matrix_projection_conflict_count: int,
    normal_peak_decision_blocked_count: int = 0,
) -> dict[str, str]:
    assessed_count = len(promotion_rows)
    activated_count = len(decision_rows)
    fail_reasons = _acceptance_fail_reasons(
        public_matrix_already_written_count,
        public_matrix_projection_conflict_count,
        normal_peak_decision_blocked_count,
    )
    next_action = _acceptance_next_action(
        activated_count,
        public_matrix_already_written_count,
        public_matrix_projection_conflict_count,
        normal_peak_decision_blocked_count,
    )
    return {
        "activation_acceptance_schema_version": ACTIVATION_ACCEPTANCE_SCHEMA_VERSION,
        "activation_mode": "sidecar_to_product_label_contract",
        "activation_decision_scope": "backfill_peakhypothesis_promotion_rows",
        "blast_radius_current": "FALSE",
        "decision_rows_total": str(activated_count),
        "assessed_rows": str(assessed_count),
        "assessed_rows_basis": "backfill_peakhypothesis_promotion_cells",
        "product_affecting_rows": str(activated_count),
        "product_affecting_rows_basis": "activation_decision_rows",
        "auto_activate_count": str(activated_count),
        "auto_block_count": "0",
        "confidence_only_count": "0",
        "review_required_count": "0",
        "not_applicable_count": str(max(0, assessed_count - activated_count)),
        "product_affecting_fraction": _fraction_text(activated_count, assessed_count),
        "max_allowed_product_affecting_rows": str(activated_count),
        "must_not_regress_status": "not_assessed",
        "must_not_regress_basis": "manual_status_flag",
        "must_not_regress_failure_reasons": "",
        "hard_fail_count": str(len(fail_reasons)),
        "acceptance_status": "fail",
        "hard_fail_reasons": ";".join(fail_reasons),
        "next_action": next_action,
    }


def _validate_promoted_row(row: Mapping[str, Any]) -> None:
    if (
        _value(row, "schema_version")
        != backfill_peakhypothesis_promotion.SCHEMA_VERSION
    ):
        raise ValueError("promotion row schema_version mismatch")
    missing = [
        column
        for column in (
            "peak_hypothesis_id",
            "feature_family_id",
            "sample_stem",
            "projected_matrix_value",
        )
        if not _value(row, column)
    ]
    if missing:
        raise ValueError(
            "promoted backfill activation row missing required fields: "
            + ", ".join(missing),
        )
    if _value(row, "activation_unit_scope") != "peak_hypothesis":
        raise ValueError("promoted backfill activation requires PeakHypothesis scope")
    if _value(row, "promotion_blockers"):
        raise ValueError("promoted backfill activation row has promotion blockers")
    if not _positive_number(_value(row, "projected_matrix_value")):
        raise ValueError("promoted backfill activation requires positive area")


def _source_evidence_tokens(row: Mapping[str, Any]) -> str:
    tokens = (
        f"promotion_reason:{_value(row, 'promotion_reasons')}",
        f"area_policy:{_value(row, 'area_policy')}",
        f"shadow_sha:{_value(row, 'shadow_projection_sha256')}",
        f"shadow_row_sha:{_value(row, 'shadow_projection_row_sha256')}",
    )
    return ";".join(token for token in tokens if not token.endswith(":"))


def _summary(
    *,
    promotion_rows: Sequence[Mapping[str, Any]],
    decision_rows: Sequence[Mapping[str, str]],
    public_matrix_already_written_count: int,
    public_matrix_projection_conflict_count: int,
    normal_peak_decision_input_count: int,
    normal_peak_required_backfill_count: int,
    normal_peak_decision_blocked_count: int,
    matrix_preflight_row_count: int,
    source_run_id: str,
) -> dict[str, Any]:
    fail_reasons = _acceptance_fail_reasons(
        public_matrix_already_written_count,
        public_matrix_projection_conflict_count,
        normal_peak_decision_blocked_count,
    )
    next_action = _acceptance_next_action(
        len(decision_rows),
        public_matrix_already_written_count,
        public_matrix_projection_conflict_count,
        normal_peak_decision_blocked_count,
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "source_run_id": source_run_id,
        "promotion_row_count": len(promotion_rows),
        "activation_decision_row_count": len(decision_rows),
        "matrix_preflight_row_count": matrix_preflight_row_count,
        "public_matrix_already_written_count": public_matrix_already_written_count,
        "public_matrix_projection_conflict_count": (
            public_matrix_projection_conflict_count
        ),
        "normal_peak_decision_input_count": normal_peak_decision_input_count,
        "normal_peak_required_backfill_count": normal_peak_required_backfill_count,
        "normal_peak_decision_blocked_count": normal_peak_decision_blocked_count,
        "acceptance_status": "fail",
        "hard_fail_reasons": ";".join(fail_reasons),
        "matrix_contract_changed": False,
        "product_behavior_changed": False,
        "next_action": next_action,
    }


def _matrix_preflight_row(
    row: Mapping[str, Any],
    public_matrix_values: Mapping[tuple[str, str], str],
) -> dict[str, str]:
    key = _promotion_key(row)
    public_value = public_matrix_values.get(key, "")
    public_written = bool(public_value)
    projection_written = _is_true(_value(row, "current_matrix_written"))
    projected_value = _value(row, "projected_matrix_value")
    if public_written and not projection_written:
        status = "projection_public_matrix_conflict"
        action = "suppress_activation"
        reason = (
            "public_matrix_value_conflicts_with_"
            "projection_current_matrix_written_FALSE"
        )
    elif public_written and not numeric_equal(public_value, projected_value):
        status = "projection_public_matrix_conflict"
        action = "suppress_activation"
        reason = "public_matrix_value_conflicts_with_projected_matrix_value"
    elif public_written:
        status = "public_matrix_already_written"
        action = "suppress_activation"
        reason = "public_matrix_already_contains_promoted_cell"
    else:
        status = "needs_activation"
        action = "emit_activation_decision"
        reason = "public_matrix_has_no_value_for_promoted_cell"
    return {
        "schema_version": SCHEMA_VERSION,
        "peak_hypothesis_id": _value(row, "peak_hypothesis_id"),
        "feature_family_id": _value(row, "feature_family_id"),
        "sample_stem": _value(row, "sample_stem"),
        "promotion_decision": _value(row, "promotion_decision"),
        "projection_current_matrix_written": _value(row, "current_matrix_written"),
        "public_matrix_written": str(public_written).upper(),
        "public_matrix_value": public_value,
        "preflight_status": status,
        "bridge_action": action,
        "preflight_reason": reason,
    }


def _has_public_matrix_projection_conflict(
    row: Mapping[str, Any],
    public_matrix_values: Mapping[tuple[str, str], str],
) -> bool:
    public_value = public_matrix_values.get(_promotion_key(row), "")
    projected_value = _value(row, "projected_matrix_value")
    return (
        _promotion_key(row) in public_matrix_values
        and (
            not _is_true(_value(row, "current_matrix_written"))
            or not numeric_equal(public_value, projected_value)
        )
    )


def _public_matrix_written_values(
    public_matrix_rows: Sequence[Mapping[str, Any]],
    matrix_identity_rows: Sequence[Mapping[str, Any]],
) -> dict[tuple[str, str], str]:
    if not public_matrix_rows:
        return {}
    return matrix_values_by_identity(
        matrix_rows=public_matrix_rows,
        matrix_identity_rows=matrix_identity_rows,
        key_mode="peak_hypothesis",
        include_blank=False,
        duplicate_policy="last",
    )


def _promotion_key(row: Mapping[str, Any]) -> tuple[str, str]:
    return (_value(row, "peak_hypothesis_id"), _value(row, "sample_stem"))


def _normal_decision_by_key(
    rows: Sequence[Mapping[str, Any]],
) -> dict[tuple[str, str], Mapping[str, Any]]:
    return {
        (_value(row, "peak_hypothesis_id"), _value(row, "sample_stem")): row
        for row in rows
    }


def _normal_peak_required(
    promotion_row: Mapping[str, Any],
    normal_decision_by_key: Mapping[tuple[str, str], Mapping[str, Any]],
) -> bool:
    if not normal_decision_by_key:
        return True
    decision_row = normal_decision_by_key.get(_promotion_key(promotion_row), {})
    return (
        _value(decision_row, "normal_peak_decision") == "require_backfill"
        and _value(decision_row, "normal_peak_backfill_required") == "TRUE"
        and not _value(decision_row, "normal_peak_decision_blockers")
    )


def _acceptance_fail_reasons(
    public_matrix_already_written_count: int,
    public_matrix_projection_conflict_count: int,
    normal_peak_decision_blocked_count: int = 0,
) -> tuple[str, ...]:
    if normal_peak_decision_blocked_count:
        return (_NORMAL_PEAK_DECISION_FAIL_REASON,)
    if public_matrix_projection_conflict_count:
        return (_MATRIX_CONFLICT_REASON,)
    if public_matrix_already_written_count:
        return ("public_matrix_already_contains_promoted_cells",)
    return (_ACCEPTANCE_FAIL_REASON,)


def _acceptance_next_action(
    activation_decision_count: int,
    public_matrix_already_written_count: int,
    public_matrix_projection_conflict_count: int,
    normal_peak_decision_blocked_count: int = 0,
) -> str:
    if normal_peak_decision_blocked_count:
        return _NORMAL_PEAK_DECISION_NEXT_ACTION
    if public_matrix_projection_conflict_count:
        return _MATRIX_CONFLICT_NEXT_ACTION
    if public_matrix_already_written_count and activation_decision_count == 0:
        return "investigate_projection_matrix_contract_drift"
    return _NEXT_ACTION


def _fraction_text(numerator: int, denominator: int) -> str:
    if denominator <= 0:
        return "0"
    return f"{numerator / denominator:.6f}".rstrip("0").rstrip(".")


def _positive_number(value: str) -> bool:
    try:
        parsed = float(value)
    except ValueError:
        return False
    return math.isfinite(parsed) and parsed > 0


def _is_true(value: str) -> bool:
    return value.strip().upper() == "TRUE"


def _value(row: Mapping[str, Any], column: str) -> str:
    return text_value(row.get(column, ""))
