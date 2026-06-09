"""PeakHypothesis normal-peak backfill decision surface.

This diagnostic turns reviewed PeakHypothesis promotion rows plus 85RAW
same-peak review evidence into an explicit normal-peak decision. It does not
write matrices or mutate alignment artifacts.
"""

from __future__ import annotations

import json
import math
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from xic_extractor.diagnostics.diagnostic_io import (
    format_diagnostic_value,
    text_value,
    write_tsv,
)

SCHEMA_VERSION = "backfill_peakhypothesis_normal_peak_decision_v1"
NORMAL_PEAK_SHAPE_DEFINITION = (
    "gaussian15_asls_residual_selected_segment_single_complete_unimodal_peak;"
    "raw_spikes_neighbor_contact_family_multiplet_not_blockers"
)

DECISION_COLUMNS = (
    "schema_version",
    "source_run_id",
    "peak_hypothesis_id",
    "activation_unit_scope",
    "feature_family_id",
    "seed_group_id",
    "sample_stem",
    "area_policy",
    "matrix_quantitative_use",
    "promotion_decision",
    "raw85_matched_peak_hypothesis_id",
    "raw85_cell_status",
    "raw85_primary_matrix_area",
    "raw85_primary_matrix_area_source",
    "raw85_include_in_primary_matrix",
    "raw85_consolidation_state",
    "manual_same_peak_verdict",
    "normal_peak_shape_definition",
    "normal_peak_decision",
    "normal_peak_backfill_required",
    "normal_peak_decision_reasons",
    "normal_peak_decision_blockers",
    "consolidation_policy_effect",
)

PROMOTION_REQUIRED_COLUMNS = (
    "peak_hypothesis_id",
    "activation_unit_scope",
    "feature_family_id",
    "seed_group_id",
    "sample_stem",
    "promotion_decision",
    "promotion_blockers",
    "area_policy",
    "matrix_quantitative_use",
    "projected_matrix_value",
)

RAW85_SLICE_REQUIRED_COLUMNS = (
    "peak_hypothesis_id",
    "feature_family_id",
    "seed_group_id",
    "sample_stem",
    "raw85_matched_peak_hypothesis_id",
    "raw85_cell_status",
    "raw85_primary_matrix_area",
    "raw85_primary_matrix_area_source",
    "raw85_include_in_primary_matrix",
    "raw85_consolidation_state",
    "raw85_slice_gate_status",
    "raw85_slice_blockers",
)

MANUAL_VERDICT_REQUIRED_COLUMNS = (
    "source_peak_hypothesis_id",
    "sample_stem",
    "raw85_matched_peak_hypothesis_id",
    "reviewer_verdict",
)

_ALLOWED_CONSOLIDATION_BLOCKERS = {
    "raw85_candidate_not_primary_matrix_row",
    "raw85_candidate_family_consolidation_review_required",
}
_GAUSSIAN15_AREA_SOURCE = "gaussian15_positive_asls_residual"


@dataclass(frozen=True)
class NormalPeakDecisionIndex:
    rows: tuple[dict[str, Any], ...]
    summary: dict[str, Any]


@dataclass(frozen=True)
class NormalPeakDecisionOutputs:
    decisions_tsv: Path
    summary_json: Path


def build_normal_peak_decision_index(
    *,
    promotion_rows: Sequence[Mapping[str, Any]],
    raw85_slice_gate_rows: Sequence[Mapping[str, Any]],
    manual_verdict_rows: Sequence[Mapping[str, Any]],
    source_run_id: str = "",
) -> NormalPeakDecisionIndex:
    raw85_by_key = {_promotion_key(row): row for row in raw85_slice_gate_rows}
    manual_by_key = {_manual_key(row): row for row in manual_verdict_rows}
    rows = tuple(
        _decision_row(
            promotion_row=promotion_row,
            raw85_row=raw85_by_key.get(_promotion_key(promotion_row), {}),
            manual_by_key=manual_by_key,
            source_run_id=source_run_id,
        )
        for promotion_row in promotion_rows
    )
    return NormalPeakDecisionIndex(
        rows=rows,
        summary=_summary(rows, source_run_id=source_run_id),
    )


def write_normal_peak_decision_outputs(
    output_dir: Path,
    index: NormalPeakDecisionIndex,
) -> NormalPeakDecisionOutputs:
    output_dir.mkdir(parents=True, exist_ok=True)
    decisions_tsv = output_dir / "backfill_peakhypothesis_normal_peak_decisions.tsv"
    summary_json = (
        output_dir / "backfill_peakhypothesis_normal_peak_decision_summary.json"
    )
    write_tsv(
        decisions_tsv,
        index.rows,
        DECISION_COLUMNS,
        formatter=format_diagnostic_value,
        lineterminator="\n",
    )
    summary_json.write_text(
        json.dumps(index.summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return NormalPeakDecisionOutputs(
        decisions_tsv=decisions_tsv,
        summary_json=summary_json,
    )


def _decision_row(
    *,
    promotion_row: Mapping[str, Any],
    raw85_row: Mapping[str, Any],
    manual_by_key: Mapping[tuple[str, str, str], Mapping[str, Any]],
    source_run_id: str,
) -> dict[str, Any]:
    raw85_id = _value(raw85_row, "raw85_matched_peak_hypothesis_id")
    manual = manual_by_key.get(
        (
            _value(promotion_row, "peak_hypothesis_id"),
            _value(promotion_row, "sample_stem"),
            raw85_id,
        ),
        {},
    )
    decision, required, reasons, blockers, consolidation_effect = _classify(
        promotion_row=promotion_row,
        raw85_row=raw85_row,
        manual_row=manual,
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "source_run_id": source_run_id,
        "peak_hypothesis_id": _value(promotion_row, "peak_hypothesis_id"),
        "activation_unit_scope": _value(promotion_row, "activation_unit_scope"),
        "feature_family_id": _value(promotion_row, "feature_family_id"),
        "seed_group_id": _value(promotion_row, "seed_group_id"),
        "sample_stem": _value(promotion_row, "sample_stem"),
        "area_policy": _value(promotion_row, "area_policy"),
        "matrix_quantitative_use": _value(
            promotion_row,
            "matrix_quantitative_use",
        ),
        "promotion_decision": _value(promotion_row, "promotion_decision"),
        "raw85_matched_peak_hypothesis_id": raw85_id,
        "raw85_cell_status": _value(raw85_row, "raw85_cell_status"),
        "raw85_primary_matrix_area": _value(
            raw85_row,
            "raw85_primary_matrix_area",
        ),
        "raw85_primary_matrix_area_source": _value(
            raw85_row,
            "raw85_primary_matrix_area_source",
        ),
        "raw85_include_in_primary_matrix": _value(
            raw85_row,
            "raw85_include_in_primary_matrix",
        ),
        "raw85_consolidation_state": _value(
            raw85_row,
            "raw85_consolidation_state",
        ),
        "manual_same_peak_verdict": _value(manual, "reviewer_verdict"),
        "normal_peak_shape_definition": NORMAL_PEAK_SHAPE_DEFINITION,
        "normal_peak_decision": decision,
        "normal_peak_backfill_required": required,
        "normal_peak_decision_reasons": ";".join(reasons),
        "normal_peak_decision_blockers": ";".join(blockers),
        "consolidation_policy_effect": consolidation_effect,
    }


def _classify(
    *,
    promotion_row: Mapping[str, Any],
    raw85_row: Mapping[str, Any],
    manual_row: Mapping[str, Any],
) -> tuple[str, bool, tuple[str, ...], tuple[str, ...], str]:
    area_policy = _value(promotion_row, "area_policy")
    if area_policy == "nonstandard_assessable_area":
        return (
            "review_only_nonstandard_peak",
            False,
            (),
            ("nonstandard_peak_out_of_goal_scope",),
            "not_applicable_nonstandard_peak",
        )
    blockers = _normal_peak_blockers(promotion_row, raw85_row, manual_row)
    if blockers:
        return ("blocked", False, (), tuple(blockers), "")
    consolidation_override = _has_only_allowed_consolidation_blockers(raw85_row)
    reasons = [
        "standard_peak_same_peak_supported",
        "positive_gaussian15_area",
    ]
    effect = "not_needed_primary_candidate"
    if consolidation_override:
        reasons.append("consolidation_not_blocking_normal_peak")
        effect = "allow_same_peak_peakhypothesis_candidate_despite_non_primary"
    return ("require_backfill", True, tuple(reasons), (), effect)


def _normal_peak_blockers(
    promotion_row: Mapping[str, Any],
    raw85_row: Mapping[str, Any],
    manual_row: Mapping[str, Any],
) -> list[str]:
    blockers: list[str] = []
    if _value(promotion_row, "area_policy") != "standard_assessable_area":
        blockers.append("normal_peak_area_policy_not_standard")
    if _value(promotion_row, "matrix_quantitative_use") != "standard_quantitative_use":
        blockers.append("normal_peak_quantitative_use_not_standard")
    if _value(promotion_row, "promotion_decision") != "promote_matrix_write":
        blockers.append("promotion_not_marked_for_matrix_write")
    if _value(promotion_row, "promotion_blockers"):
        blockers.append("promotion_blockers_present")
    if not raw85_row:
        blockers.append("missing_raw85_slice_gate_row")
    if _value(raw85_row, "raw85_cell_status") not in {"detected", "rescued"}:
        blockers.append("raw85_cell_not_detected_or_rescued")
    if _value(raw85_row, "raw85_primary_matrix_area_source") != (
        _GAUSSIAN15_AREA_SOURCE
    ):
        blockers.append("raw85_area_source_not_gaussian15")
    if not _positive_number(_value(raw85_row, "raw85_primary_matrix_area")):
        blockers.append("raw85_area_not_positive")
    if _value(manual_row, "reviewer_verdict") != "same_peak_supported":
        blockers.append("manual_same_peak_not_supported")
    disallowed = set(_semicolon_values(_value(raw85_row, "raw85_slice_blockers")))
    disallowed -= _ALLOWED_CONSOLIDATION_BLOCKERS
    if disallowed:
        blockers.append("raw85_disallowed_slice_blockers_present")
    return blockers


def _summary(
    rows: Sequence[Mapping[str, Any]],
    *,
    source_run_id: str,
) -> dict[str, Any]:
    decisions = Counter(_value(row, "normal_peak_decision") for row in rows)
    normal_count = sum(
        1 for row in rows if _value(row, "area_policy") == "standard_assessable_area"
    )
    required_count = decisions.get("require_backfill", 0)
    blocked_count = decisions.get("blocked", 0)
    review_only_count = decisions.get("review_only_nonstandard_peak", 0)
    consolidation_override_count = sum(
        1
        for row in rows
        if _value(row, "consolidation_policy_effect")
        == "allow_same_peak_peakhypothesis_candidate_despite_non_primary"
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "source_run_id": source_run_id,
        "row_count": len(rows),
        "normal_peak_candidate_count": normal_count,
        "required_backfill_count": required_count,
        "review_only_nonstandard_count": review_only_count,
        "blocked_count": blocked_count,
        "consolidation_override_count": consolidation_override_count,
        "decision_counts": dict(sorted(decisions.items())),
        "normal_peak_policy_status": _policy_status(
            normal_count=normal_count,
            required_count=required_count,
            blocked_count=blocked_count,
        ),
        "normal_peak_shape_definition": NORMAL_PEAK_SHAPE_DEFINITION,
        "matrix_contract_changed": False,
        "product_behavior_changed": False,
        "next_action": (
            "wire_normal_peak_decisions_into_activation_or_matrix_writer"
            if required_count
            else "review_normal_peak_decision_blockers"
        ),
    }


def _policy_status(
    *,
    normal_count: int,
    required_count: int,
    blocked_count: int,
) -> str:
    if normal_count and required_count == normal_count and blocked_count == 0:
        return "normal_peak_backfill_required_all_reviewed_candidates"
    if blocked_count:
        return "normal_peak_backfill_blocked_or_incomplete"
    return "no_normal_peak_candidates"


def _promotion_key(row: Mapping[str, Any]) -> tuple[str, str, str, str]:
    return (
        _value(row, "peak_hypothesis_id"),
        _value(row, "feature_family_id"),
        _value(row, "seed_group_id"),
        _value(row, "sample_stem"),
    )


def _manual_key(row: Mapping[str, Any]) -> tuple[str, str, str]:
    return (
        _value(row, "source_peak_hypothesis_id"),
        _value(row, "sample_stem"),
        _value(row, "raw85_matched_peak_hypothesis_id"),
    )


def _has_only_allowed_consolidation_blockers(row: Mapping[str, Any]) -> bool:
    blockers = set(_semicolon_values(_value(row, "raw85_slice_blockers")))
    return bool(blockers) and blockers <= _ALLOWED_CONSOLIDATION_BLOCKERS


def _positive_number(value: str) -> bool:
    try:
        parsed = float(value)
    except ValueError:
        return False
    return math.isfinite(parsed) and parsed > 0


def _semicolon_values(value: str) -> tuple[str, ...]:
    return tuple(part for part in text_value(value).split(";") if part)


def _value(row: Mapping[str, Any], column: str) -> str:
    return text_value(row.get(column, ""))
