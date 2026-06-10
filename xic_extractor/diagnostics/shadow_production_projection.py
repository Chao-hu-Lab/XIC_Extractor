"""Cell-level shadow production projection for backfill review.

This module is deliberately a projection layer: it consumes the production
decision snapshot and existing diagnostic evidence, then writes a review TSV.
It does not mutate the alignment matrix or workbook outputs.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from xic_extractor.alignment.production_decisions import (
    ProductionCellDecision,
    ProductionDecisionSet,
)
from xic_extractor.alignment.promotion_policy import (
    ANCHOR_OWN_MAX_MS1_SUPPORT_REASON,
    BACKFILL_HYPOTHESIS_BLOCKED_REASON,
    STANDARD_PEAK_GATE_MS1_SUPPORT_REASON,
)
from xic_extractor.diagnostics.diagnostic_io import (
    format_diagnostic_value,
    optional_float,
    split_semicolon_labels,
    text_value,
    write_tsv,
)

SCHEMA_VERSION = "shadow_production_projection_v1"

ShadowDecision = Literal["accept", "block", "context"]

SHADOW_PRODUCTION_PROJECTION_COLUMNS = (
    "schema_version",
    "peak_hypothesis_id",
    "activation_unit_scope",
    "feature_family_id",
    "seed_group_id",
    "sample_stem",
    "current_raw_status",
    "current_production_status",
    "current_rescue_tier",
    "current_matrix_written",
    "current_matrix_value",
    "current_blank_reason",
    "current_matrix_source",
    "review_rescued_cell",
    "shadow_decision",
    "shadow_reasons",
    "shadow_warnings",
    "projected_matrix_written",
    "projected_matrix_value",
    "projection_authority",
    "product_authority_chain",
    "seed_mz",
    "seed_rt",
    "seed_rt_window",
    "detected_anchor_count",
    "rescued_cell_count",
    "request_window_overlap",
    "local_global_ratio",
    "cell_status",
    "gap_fill_state",
    "gap_fill_reason",
    "evidence_gate_status",
    "support_components",
    "hard_blockers",
    "missing_evidence",
    "shadow_projection_row_sha256",
    "overlay_verdict",
    "overlay_png_path",
)

RETAINED_GATE_REQUIRED_COLUMNS = (
    "feature_family_id",
    "seed_group_id",
    "seed_group_basis",
    "seed_mz",
    "seed_rt",
    "suggested_rt_min",
    "suggested_rt_max",
    "detected_cell_count",
    "rescued_cell_count",
    "seed_source_samples",
    "evidence_gate_status",
    "support_components",
    "challenge_blockers",
    "missing_evidence",
)

HARD_BLOCKER_TOKENS = {
    "not_same_gaussian15_peak_segment",
    "outside_selected_segment",
    "neighboring_interference_hard_block",
    "missing_ms1_peak_segment",
}
CURRENT_PRODUCTION_HARD_BLOCKERS = {BACKFILL_HYPOTHESIS_BLOCKED_REASON}

PROJECTION_ACCEPT_GATE_STATUSES = {
    "visual_support",
    "product_grade_support",
}
_PRODUCT_AUTHORIZED_STATUS = "product_authorized"
_PRODUCT_AUTHORIZED_SCOPE = "feature_family_sample"
_SUPPORT_STATUSES = {"supportive", "partial_support"}
_MS1_SAME_PEAK_LEVEL = "trace_constellation"
_MS1_SAME_PEAK_SUPPORT_REASONS = frozenset(
    {
        ANCHOR_OWN_MAX_MS1_SUPPORT_REASON,
        STANDARD_PEAK_GATE_MS1_SUPPORT_REASON,
    }
)
_IDENTITY_SUPPORTED_REVIEW_REASON = "identity_supported_review"
_SEED_REQUEST_COMPONENT = "seed_request_provenance"
_MS1_SHAPE_SUPPORT_COMPONENT = "ms1_shape_supports_family_backfill"


@dataclass(frozen=True)
class ShadowProductionProjectionIndex:
    rows: tuple[dict[str, str], ...]
    summary: dict[str, object]


@dataclass(frozen=True)
class ShadowProductionProjectionOutputs:
    tsv: Path
    json: Path


def build_shadow_production_projection_index(
    *,
    production_decisions: ProductionDecisionSet,
    cell_rows: Iterable[Mapping[str, str]],
    retained_gate_rows: Iterable[Mapping[str, str]],
    overlay_rows: Iterable[Mapping[str, str]] = (),
    source_run_id: str = "",
    source_review_sha256: str = "",
    source_cell_sha256: str = "",
    source_gate_sha256: str = "",
    source_matrix_sha256: str = "",
    source_overlay_artifacts: Sequence[str] = (),
    source_overlay_sha256s: Sequence[str] = (),
    source_ms1_pattern_coherence_artifacts: Sequence[str] = (),
    source_ms1_pattern_coherence_sha256s: Sequence[str] = (),
) -> ShadowProductionProjectionIndex:
    gate_rows = tuple(dict(row) for row in retained_gate_rows)
    _validate_gate_rows(gate_rows)
    gate_projection_summary = _gate_projection_summary(gate_rows)
    cells_by_key = {
        (
            text_value(row.get("feature_family_id")),
            text_value(row.get("sample_stem")),
        ): dict(row)
        for row in cell_rows
        if text_value(row.get("feature_family_id"))
        and text_value(row.get("sample_stem"))
    }
    overlays_by_family = _group_by_family(overlay_rows)
    rows: list[dict[str, str]] = []
    for gate_row in gate_rows:
        family_id = text_value(gate_row.get("feature_family_id"))
        seed_group_id = text_value(gate_row.get("seed_group_id"))
        if not family_id or not seed_group_id:
            continue
        overlay_row = _selected_overlay_row(
            overlays_by_family.get(family_id, ()),
            seed_group_id=seed_group_id,
        )
        for sample in split_semicolon_labels(gate_row.get("seed_source_samples")):
            decision = production_decisions.cells.get((family_id, sample))
            cell = cells_by_key.get((family_id, sample), {})
            rows.append(
                _projection_row(
                    gate_row=gate_row,
                    overlay_row=overlay_row,
                    cell=cell,
                    sample_stem=sample,
                    decision=decision,
                ),
            )

    sorted_rows = tuple(sorted(rows, key=_row_sort_key))
    return ShadowProductionProjectionIndex(
        rows=sorted_rows,
        summary=_summary(
            sorted_rows,
            gate_projection_summary=gate_projection_summary,
            source_run_id=source_run_id,
            source_review_sha256=source_review_sha256,
            source_cell_sha256=source_cell_sha256,
            source_gate_sha256=source_gate_sha256,
            source_matrix_sha256=source_matrix_sha256,
            source_overlay_artifacts=source_overlay_artifacts,
            source_overlay_sha256s=source_overlay_sha256s,
            source_ms1_pattern_coherence_artifacts=(
                source_ms1_pattern_coherence_artifacts
            ),
            source_ms1_pattern_coherence_sha256s=(
                source_ms1_pattern_coherence_sha256s
            ),
        ),
    )


def write_shadow_production_projection_outputs(
    output_dir: Path,
    index: ShadowProductionProjectionIndex,
) -> ShadowProductionProjectionOutputs:
    output_dir.mkdir(parents=True, exist_ok=True)
    tsv_path = output_dir / "shadow_production_projection_cells.tsv"
    json_path = output_dir / "shadow_production_projection_summary.json"
    write_tsv(
        tsv_path,
        index.rows,
        SHADOW_PRODUCTION_PROJECTION_COLUMNS,
        formatter=format_diagnostic_value,
        lineterminator="\n",
    )
    json_path.write_text(
        json.dumps(index.summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return ShadowProductionProjectionOutputs(tsv=tsv_path, json=json_path)


def _projection_row(
    *,
    gate_row: Mapping[str, str],
    overlay_row: Mapping[str, str],
    cell: Mapping[str, str],
    sample_stem: str,
    decision: ProductionCellDecision | None,
) -> dict[str, str]:
    current_written = bool(decision and decision.write_matrix_value)
    current_status = decision.production_status if decision else "blank"
    current_value = decision.matrix_value if decision else None
    current_blank = decision.blank_reason if decision else "missing_production_decision"
    current_raw_status = (
        decision.raw_status if decision else text_value(cell.get("status"))
    )
    review_rescued = (
        decision is not None
        and decision.production_status == "review_rescue"
        and current_raw_status == "rescued"
    )
    shadow_decision, reasons, warnings = _shadow_projection_decision(
        gate_row=gate_row,
        cell=cell,
        decision=decision,
        review_rescued=review_rescued,
        current_written=current_written,
    )
    projected_value = current_value if current_written else None
    if shadow_decision == "accept":
        projected_value = _projected_cell_value(cell)
        if projected_value is None:
            shadow_decision = "context"
            reasons = (*reasons, "missing_projected_matrix_value")
            warnings = (*warnings, "projection_accept_without_positive_area")
    elif _IDENTITY_SUPPORTED_REVIEW_REASON in reasons:
        projected_value = _projected_cell_value(cell)
    projected_written = current_written or (
        shadow_decision == "accept" and projected_value is not None
    )
    rt_start = text_value(gate_row.get("suggested_rt_min"))
    rt_end = text_value(gate_row.get("suggested_rt_max"))
    peak_hypothesis_id = text_value(cell.get("peak_hypothesis_id")) or text_value(
        cell.get("group_hypothesis_id"),
    )
    hard_blockers = tuple(
        token
        for token in _hard_blocker_tokens(gate_row)
        if token in HARD_BLOCKER_TOKENS
    )
    row = {
        "schema_version": SCHEMA_VERSION,
        "peak_hypothesis_id": peak_hypothesis_id,
        "activation_unit_scope": (
            "peak_hypothesis" if peak_hypothesis_id else ""
        ),
        "feature_family_id": text_value(gate_row.get("feature_family_id")),
        "seed_group_id": text_value(gate_row.get("seed_group_id")),
        "sample_stem": sample_stem,
        "current_raw_status": current_raw_status,
        "current_production_status": current_status,
        "current_rescue_tier": decision.rescue_tier if decision else "",
        "current_matrix_written": _bool_text(current_written),
        "current_matrix_value": _number_text(current_value),
        "current_blank_reason": current_blank,
        "current_matrix_source": "production_decision_snapshot",
        "review_rescued_cell": _bool_text(review_rescued),
        "shadow_decision": shadow_decision,
        "shadow_reasons": ";".join(reasons),
        "shadow_warnings": ";".join(warnings),
        "projected_matrix_written": _bool_text(projected_written),
        "projected_matrix_value": _number_text(projected_value),
        "projection_authority": "shadow_projection_only",
        "product_authority_chain": _product_authority_chain_text(cell),
        "seed_mz": text_value(gate_row.get("seed_mz")),
        "seed_rt": text_value(gate_row.get("seed_rt")),
        "seed_rt_window": f"{rt_start}-{rt_end}" if rt_start or rt_end else "",
        "detected_anchor_count": text_value(gate_row.get("detected_cell_count")),
        "rescued_cell_count": text_value(gate_row.get("rescued_cell_count")),
        "request_window_overlap": _bool_text(_request_window_overlap(cell, gate_row)),
        "local_global_ratio": _local_global_ratio_text(cell, overlay_row),
        "cell_status": text_value(cell.get("status")),
        "gap_fill_state": text_value(cell.get("gap_fill_state")),
        "gap_fill_reason": text_value(cell.get("gap_fill_reason")),
        "evidence_gate_status": text_value(gate_row.get("evidence_gate_status")),
        "support_components": text_value(gate_row.get("support_components")),
        "hard_blockers": ";".join(hard_blockers),
        "missing_evidence": text_value(gate_row.get("missing_evidence")),
        "shadow_projection_row_sha256": "",
        "overlay_verdict": text_value(gate_row.get("overlay_family_verdict")),
        "overlay_png_path": (
            text_value(overlay_row.get("png_path"))
            or text_value(gate_row.get("overlay_png_path"))
        ),
    }
    row["shadow_projection_row_sha256"] = _shadow_projection_row_sha256(row)
    return row


def _shadow_projection_row_sha256(row: Mapping[str, str]) -> str:
    payload = {
        column: text_value(row.get(column))
        for column in SHADOW_PRODUCTION_PROJECTION_COLUMNS
        if column != "shadow_projection_row_sha256"
    }
    serialized = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


def _shadow_projection_decision(
    *,
    gate_row: Mapping[str, str],
    cell: Mapping[str, str],
    decision: ProductionCellDecision | None,
    review_rescued: bool,
    current_written: bool,
) -> tuple[ShadowDecision, tuple[str, ...], tuple[str, ...]]:
    if current_written:
        return "context", ("already_written_current_matrix",), ()
    if not review_rescued:
        reason = (
            "missing_production_decision"
            if decision is None
            else "not_review_rescued_cell"
        )
        return "context", (reason,), _warnings(cell, gate_row)

    if _int_text(gate_row.get("detected_cell_count")) <= 0:
        return "block", ("no_detected_anchor",), _warnings(cell, gate_row)
    if not _has_ms1_peak_segment(cell):
        return "block", ("missing_ms1_peak_segment",), _warnings(cell, gate_row)
    if not _request_window_overlap(cell, gate_row):
        return "block", ("outside_request_window",), _warnings(cell, gate_row)

    current_blocker = _current_production_hard_blocker(decision)
    if current_blocker:
        return "block", (current_blocker,), _warnings(cell, gate_row)
    cell_blocker = _cell_hypothesis_blocker(cell)
    if cell_blocker:
        return "block", (cell_blocker,), _warnings(cell, gate_row)

    blockers = _hard_blocker_tokens(gate_row)
    if blockers:
        return "block", blockers, _warnings(cell, gate_row)
    product_authorized = _product_authorized_same_peak_backfill(cell)
    gate_status = text_value(gate_row.get("evidence_gate_status"))
    if (
        not product_authorized
        and gate_status
        and gate_status not in PROJECTION_ACCEPT_GATE_STATUSES
    ):
        return "context", ("evidence_gate_requires_review",), _warnings(
            cell,
            gate_row,
        )
    soft_blockers = _soft_blocker_tokens(gate_row)
    if soft_blockers:
        return "context", ("challenge_blockers_require_review",), _warnings(
            cell,
            gate_row,
        )
    if not product_authorized:
        if _identity_supported_by_review(gate_row):
            return "context", (_IDENTITY_SUPPORTED_REVIEW_REASON,), _warnings(
                cell,
                gate_row,
            )
        return "context", ("missing_product_authorized_evidence_chain",), _warnings(
            cell,
            gate_row,
        )
    if _same_peak_multi_claim(cell):
        return "accept", ("product_authorized_same_peak_backfill",), _warnings(
            cell,
            gate_row,
        )
    return "accept", ("product_authorized_same_peak_backfill",), _warnings(
        cell,
        gate_row,
    )


def _product_authorized_same_peak_backfill(cell: Mapping[str, str]) -> bool:
    if not _product_authority_present(
        status=cell.get("backfill_ms1_product_authority_status"),
        scope=cell.get("backfill_ms1_product_authority_scope"),
        source=cell.get("backfill_ms1_product_authority_source"),
    ):
        return False
    if _normalize(cell.get("backfill_ms1_pattern_status")) not in _SUPPORT_STATUSES:
        return False
    if (
        _normalize(cell.get("backfill_ms1_pattern_evidence_level"))
        != _MS1_SAME_PEAK_LEVEL
    ):
        return False
    if not (
        _MS1_SAME_PEAK_SUPPORT_REASONS
        & set(split_semicolon_labels(cell.get("backfill_evidence_reason")))
    ):
        return False
    return True


def _identity_supported_by_review(gate_row: Mapping[str, str]) -> bool:
    gate_status = text_value(gate_row.get("evidence_gate_status"))
    components = set(split_semicolon_labels(gate_row.get("support_components")))
    return (
        gate_status in PROJECTION_ACCEPT_GATE_STATUSES
        and _SEED_REQUEST_COMPONENT in components
        and _MS1_SHAPE_SUPPORT_COMPONENT in components
    )


def _product_authority_chain_text(cell: Mapping[str, str]) -> str:
    return " | ".join(
        part
        for part in (
            _authority_component_text(
                cell,
                label="MS1",
                prefix="backfill_ms1",
                status_key="backfill_ms1_pattern_status",
                level_key="backfill_ms1_pattern_evidence_level",
            ),
            _authority_component_text(
                cell,
                label="candidateMS2(optional)",
                prefix="backfill_candidate_ms2",
                status_key="backfill_candidate_ms2_pattern_status",
                level_key="backfill_candidate_ms2_evidence_level",
            ),
            _same_peak_reason_text(cell),
        )
        if part
    )


def _authority_component_text(
    cell: Mapping[str, str],
    *,
    label: str,
    prefix: str,
    status_key: str,
    level_key: str,
) -> str:
    authority_status = text_value(cell.get(f"{prefix}_product_authority_status"))
    if not authority_status:
        return ""
    pattern_status = text_value(cell.get(status_key)) or "no_pattern_status"
    evidence_level = text_value(cell.get(level_key)) or "no_evidence_level"
    scope = text_value(cell.get(f"{prefix}_product_authority_scope"))
    source = text_value(cell.get(f"{prefix}_product_authority_source"))
    reason = text_value(cell.get(f"{prefix}_product_authority_reason"))
    parts = [
        label,
        authority_status,
        pattern_status,
        evidence_level,
    ]
    if scope:
        parts.append(scope)
    if reason:
        parts.append(reason)
    elif source:
        parts.append(source)
    return ":".join(parts)


def _same_peak_reason_text(cell: Mapping[str, str]) -> str:
    reasons = set(split_semicolon_labels(cell.get("backfill_evidence_reason")))
    matched = tuple(sorted(_MS1_SAME_PEAK_SUPPORT_REASONS & reasons))
    if not matched:
        return ""
    return "same_peak_reason:" + ";".join(matched)


def _product_authority_present(
    *,
    status: object,
    scope: object,
    source: object,
) -> bool:
    return (
        _normalize(status) == _PRODUCT_AUTHORIZED_STATUS
        and _normalize(scope) == _PRODUCT_AUTHORIZED_SCOPE
        and bool(_normalize(source))
    )


def _normalize(value: object) -> str:
    return text_value(value).strip().lower().replace(" ", "_")


def _warnings(
    cell: Mapping[str, str],
    gate_row: Mapping[str, str],
) -> tuple[str, ...]:
    warnings: list[str] = []
    if _same_peak_multi_claim(cell):
        warnings.append("same_peak_multi_claim")
    ratio = optional_float(cell.get("local_window_to_global_max_ratio"))
    if ratio is not None and ratio <= 0.5:
        warnings.append("low_dominance")
    for token in split_semicolon_labels(gate_row.get("challenge_blockers")):
        if token and token not in HARD_BLOCKER_TOKENS:
            warnings.append(token)
    return tuple(dict.fromkeys(warnings))


def _current_production_hard_blocker(
    decision: ProductionCellDecision | None,
) -> str:
    if decision is None:
        return ""
    return (
        decision.blank_reason
        if decision.blank_reason in CURRENT_PRODUCTION_HARD_BLOCKERS
        else ""
    )


def _cell_hypothesis_blocker(cell: Mapping[str, str]) -> str:
    tokens = " ".join(
        text_value(cell.get(key)).lower().replace(" ", "_")
        for key in (
            "group_claim_state",
            "consolidation_state",
            "peak_hypothesis_status",
            "product_selection_blocker",
            "rt_mode_status",
            "activation_product_effect",
            "activation_contract_rule_id",
            "activation_reason",
            "reason",
            "backfill_evidence_reason",
        )
    )
    hard_markers = (
        "duplicate_loser",
        "primary_loser",
        "wrong_peak",
        "cross_mode_rescue_blocked",
        "mode_split_required",
        "consolidation_no_go",
    )
    if any(marker in tokens for marker in hard_markers):
        return BACKFILL_HYPOTHESIS_BLOCKED_REASON
    return ""


def _hard_blocker_tokens(gate_row: Mapping[str, str]) -> tuple[str, ...]:
    tokens = split_semicolon_labels(gate_row.get("challenge_blockers"))
    return tuple(token for token in tokens if token in HARD_BLOCKER_TOKENS)


def _soft_blocker_tokens(gate_row: Mapping[str, str]) -> tuple[str, ...]:
    tokens = split_semicolon_labels(gate_row.get("challenge_blockers"))
    return tuple(token for token in tokens if token not in HARD_BLOCKER_TOKENS)


def _same_peak_multi_claim(cell: Mapping[str, str]) -> bool:
    text = " ".join(
        text_value(cell.get(key)).lower()
        for key in (
            "gap_fill_state",
            "gap_fill_reason",
            "reason",
            "group_claim_state",
            "consolidation_state",
        )
    )
    return "duplicate" in text or "same_peak_multi_claim" in text


def _request_window_overlap(
    cell: Mapping[str, str],
    gate_row: Mapping[str, str],
) -> bool:
    if not _has_ms1_peak_segment(cell):
        return False
    start = optional_float(cell.get("peak_start_rt"))
    end = optional_float(cell.get("peak_end_rt"))
    apex = optional_float(cell.get("apex_rt"))
    gate_start = optional_float(gate_row.get("suggested_rt_min"))
    gate_end = optional_float(gate_row.get("suggested_rt_max"))
    if None in (start, end, gate_start, gate_end):
        return False
    assert start is not None
    assert end is not None
    assert gate_start is not None
    assert gate_end is not None
    overlaps = end >= gate_start and start <= gate_end
    if apex is None:
        return overlaps
    return overlaps and gate_start <= apex <= gate_end


def _validate_gate_rows(rows: Sequence[Mapping[str, str]]) -> None:
    for index, row in enumerate(rows, start=1):
        missing = [
            column
            for column in RETAINED_GATE_REQUIRED_COLUMNS
            if column not in row
        ]
        if missing:
            raise ValueError(
                "retained gate row "
                f"{index} missing required shadow projection columns: "
                + ", ".join(missing),
            )


def _has_ms1_peak_segment(cell: Mapping[str, str]) -> bool:
    return (
        optional_float(cell.get("peak_start_rt")) is not None
        and optional_float(cell.get("peak_end_rt")) is not None
    )


def _projected_cell_value(cell: Mapping[str, str]) -> float | None:
    for key in ("primary_matrix_area", "area"):
        value = optional_float(cell.get(key))
        if value is not None and value > 0:
            return value
    return None


def _local_global_ratio_text(
    cell: Mapping[str, str],
    overlay_row: Mapping[str, str],
) -> str:
    for key in (
        "local_window_to_global_max_ratio",
        "absolute_own_max_shape_supported_fraction",
    ):
        value = optional_float(cell.get(key))
        if value is None:
            value = optional_float(overlay_row.get(key))
        if value is not None:
            return _number_text(value)
    return ""


def _selected_overlay_row(
    rows: Sequence[Mapping[str, str]],
    *,
    seed_group_id: str,
) -> Mapping[str, str]:
    for row in rows:
        if text_value(row.get("seed_group_id")) == seed_group_id:
            return row
    return {}


def _group_by_family(
    rows: Iterable[Mapping[str, str]],
) -> dict[str, tuple[Mapping[str, str], ...]]:
    grouped: dict[str, list[Mapping[str, str]]] = {}
    for row in rows:
        family = text_value(row.get("feature_family_id"))
        if family:
            grouped.setdefault(family, []).append(row)
    return {family: tuple(items) for family, items in grouped.items()}


def _summary(
    rows: Sequence[Mapping[str, str]],
    *,
    gate_projection_summary: Mapping[str, object],
    source_run_id: str,
    source_review_sha256: str,
    source_cell_sha256: str,
    source_gate_sha256: str,
    source_matrix_sha256: str,
    source_overlay_artifacts: Sequence[str],
    source_overlay_sha256s: Sequence[str],
    source_ms1_pattern_coherence_artifacts: Sequence[str],
    source_ms1_pattern_coherence_sha256s: Sequence[str],
) -> dict[str, object]:
    decisions = Counter(row["shadow_decision"] for row in rows)
    current_written = sum(row["current_matrix_written"] == "TRUE" for row in rows)
    projected_written = sum(row["projected_matrix_written"] == "TRUE" for row in rows)
    projected_new = sum(
        row["current_matrix_written"] == "FALSE"
        and row["projected_matrix_written"] == "TRUE"
        for row in rows
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "validation_label": "shadow_projection_only",
        "source_run_id": source_run_id,
        **gate_projection_summary,
        "row_count": len(rows),
        "decision_counts": dict(sorted(decisions.items())),
        "current_matrix_written_count": current_written,
        "projected_matrix_written_count": projected_written,
        "projected_new_write_count": projected_new,
        "review_rescued_target_count": sum(
            row["review_rescued_cell"] == "TRUE" for row in rows
        ),
        "source_review_sha256": source_review_sha256,
        "source_cell_sha256": source_cell_sha256,
        "source_gate_sha256": source_gate_sha256,
        "source_matrix_sha256": source_matrix_sha256,
        "source_overlay_artifacts": tuple(source_overlay_artifacts),
        "source_overlay_sha256s": tuple(source_overlay_sha256s),
        "source_ms1_pattern_coherence_artifacts": tuple(
            source_ms1_pattern_coherence_artifacts
        ),
        "source_ms1_pattern_coherence_sha256s": tuple(
            source_ms1_pattern_coherence_sha256s
        ),
        "current_matrix_source": "production_decision_snapshot",
        "alignment_matrix_cross_checked": False,
        "matrix_contract_changed": False,
        "product_behavior_changed": False,
    }


def _gate_projection_summary(
    gate_rows: Sequence[Mapping[str, str]],
) -> dict[str, object]:
    reasons = Counter(
        reason
        for row in gate_rows
        if (reason := _unprojectable_gate_reason(row))
    )
    unprojectable = sum(reasons.values())
    return {
        "gate_row_count": len(gate_rows),
        "projectable_gate_row_count": len(gate_rows) - unprojectable,
        "unprojectable_gate_row_count": unprojectable,
        "unprojectable_gate_reasons": dict(sorted(reasons.items())),
    }


def _unprojectable_gate_reason(row: Mapping[str, str]) -> str:
    if not text_value(row.get("feature_family_id")):
        return "missing_feature_family_id"
    if not text_value(row.get("seed_group_id")):
        return "missing_seed_group_id"
    if not split_semicolon_labels(row.get("seed_source_samples")):
        seed_basis = text_value(row.get("seed_group_basis"))
        if seed_basis == "missing_seed_audit":
            return "missing_seed_audit"
        return "missing_seed_source_samples"
    return ""


def _int_text(value: object) -> int:
    parsed = optional_float(value)
    if parsed is None:
        return 0
    return int(parsed)


def _number_text(value: object) -> str:
    parsed = optional_float(value)
    if parsed is None:
        return ""
    return f"{parsed:.6g}"


def _bool_text(value: bool) -> str:
    return "TRUE" if value else "FALSE"


def _row_sort_key(row: Mapping[str, str]) -> tuple[str, str, str]:
    return (
        text_value(row.get("feature_family_id")),
        text_value(row.get("seed_group_id")),
        text_value(row.get("sample_stem")),
    )
