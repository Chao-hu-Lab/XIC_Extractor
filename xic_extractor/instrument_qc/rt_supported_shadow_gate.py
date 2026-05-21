from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from math import isfinite
from typing import Mapping

SUPPORTED_TRANSFER_STATUSES = {
    "transfer_supported",
    "direction_supported_magnitude_shifted",
}

ROW_CLASSIFICATIONS = {
    "rt_supported_shadow_candidate",
    "clean_standard_only_review",
    "biological_context_missing",
    "biological_transfer_conflict",
    "rt_model_uncertain",
    "coverage_not_supported",
    "blocked_or_not_applicable",
}


@dataclass(frozen=True)
class RtSupportedShadowGateParameters:
    anchor_rt_window_min: float = 1.0
    anchor_injection_window: int = 20
    residual_max_min: float = 0.30
    uncertainty_max_min: float = 0.30


@dataclass(frozen=True)
class MatrixRtPreviewInputRow:
    source_row_id: str
    source_cell_key: str
    feature_id: str
    sample_name: str
    sample_stem: str
    feature_mz: float | None
    raw_feature_rt_min: float | None
    injection_order: int | None
    coverage_status: str
    rt_alignment_support_status: str
    local_residual_p95_min: float | None
    rt_uncertainty_min: float | None
    local_biological_istd_anchor_count: int | None
    correction_status: str
    correction_block_reason: str


@dataclass(frozen=True)
class BiologicalIstdAnchorInputRow:
    target_label: str
    sample_name: str
    injection_order: int | None
    observed_rt_min: float | None


@dataclass(frozen=True)
class RtSupportedShadowGateRow:
    source_row_id: str
    source_cell_key: str
    feature_id: str
    sample_name: str
    sample_stem: str
    feature_mz: float | None
    raw_feature_rt_min: float | None
    injection_order: int | None
    coverage_status: str
    correction_status: str
    rt_alignment_support_status: str
    local_residual_p95_min: float | None
    rt_uncertainty_min: float | None
    local_biological_istd_anchor_count: int | None
    nearby_biological_istd_anchor_count: int
    supported_biological_istd_anchor_count: int
    conflict_biological_istd_anchor_count: int
    nearest_biological_istd_label: str
    nearest_biological_istd_transfer_status: str
    nearest_biological_istd_rt_delta_min: float | None
    nearest_biological_istd_injection_order_delta: int | None
    supporting_biological_istd_label: str
    supporting_biological_istd_transfer_status: str
    supporting_biological_istd_rt_delta_min: float | None
    supporting_biological_istd_injection_order_delta: int | None
    row_classification: str
    review_reason: str


@dataclass(frozen=True)
class RtSupportedShadowGateResult:
    run_verdict: str
    rows: tuple[RtSupportedShadowGateRow, ...]
    counts_by_classification: dict[str, int]
    counts_by_coverage_status: dict[str, int]
    counts_by_correction_status: dict[str, int]
    counts_by_nearest_transfer_status: dict[str, int]
    istd_scope: str
    parameters: RtSupportedShadowGateParameters
    missing_artifacts: tuple[str, ...] = ()
    input_errors: tuple[str, ...] = ()


def build_required_artifact_missing_result(
    *,
    missing_artifacts: tuple[str, ...],
    parameters: RtSupportedShadowGateParameters,
) -> RtSupportedShadowGateResult:
    return RtSupportedShadowGateResult(
        run_verdict="required_artifact_missing",
        rows=(),
        counts_by_classification={},
        counts_by_coverage_status={},
        counts_by_correction_status={},
        counts_by_nearest_transfer_status={},
        istd_scope="",
        parameters=parameters,
        missing_artifacts=missing_artifacts,
    )


def build_input_invalid_result(
    *,
    input_errors: tuple[str, ...],
    parameters: RtSupportedShadowGateParameters,
) -> RtSupportedShadowGateResult:
    return RtSupportedShadowGateResult(
        run_verdict="input_invalid",
        rows=(),
        counts_by_classification={},
        counts_by_coverage_status={},
        counts_by_correction_status={},
        counts_by_nearest_transfer_status={},
        istd_scope="",
        parameters=parameters,
        input_errors=input_errors,
    )


def build_rt_supported_shadow_gate(
    *,
    matrix_rows: tuple[MatrixRtPreviewInputRow, ...],
    biological_istd_anchors: tuple[BiologicalIstdAnchorInputRow, ...],
    transfer_status_by_target: Mapping[str, str],
    istd_scope: str,
    parameters: RtSupportedShadowGateParameters | None = None,
) -> RtSupportedShadowGateResult:
    params = parameters or RtSupportedShadowGateParameters()
    rows = tuple(
        classify_rt_supported_shadow_row(
            row,
            biological_istd_anchors=biological_istd_anchors,
            transfer_status_by_target=transfer_status_by_target,
            istd_scope=istd_scope,
            parameters=params,
        )
        for row in matrix_rows
    )
    counts_by_classification = _counts(row.row_classification for row in rows)
    run_verdict = _run_verdict(
        counts_by_classification=counts_by_classification,
        istd_scope=istd_scope,
        anchors=biological_istd_anchors,
    )
    return RtSupportedShadowGateResult(
        run_verdict=run_verdict,
        rows=rows,
        counts_by_classification=counts_by_classification,
        counts_by_coverage_status=_counts(row.coverage_status for row in rows),
        counts_by_correction_status=_counts(row.correction_status for row in rows),
        counts_by_nearest_transfer_status=_counts(
            row.nearest_biological_istd_transfer_status or "missing"
            for row in rows
        ),
        istd_scope=istd_scope,
        parameters=params,
    )


def classify_rt_supported_shadow_row(
    row: MatrixRtPreviewInputRow,
    *,
    biological_istd_anchors: tuple[BiologicalIstdAnchorInputRow, ...],
    transfer_status_by_target: Mapping[str, str],
    istd_scope: str,
    parameters: RtSupportedShadowGateParameters,
) -> RtSupportedShadowGateRow:
    nearby = _nearby_anchors(row, biological_istd_anchors, parameters)
    nearest = nearby[0] if nearby else None
    supported_count = sum(
        1
        for anchor, _, _ in nearby
        if transfer_status_by_target.get(anchor.target_label)
        in SUPPORTED_TRANSFER_STATUSES
    )
    conflict_count = sum(
        1
        for anchor, _, _ in nearby
        if transfer_status_by_target.get(anchor.target_label)
        and transfer_status_by_target.get(anchor.target_label)
        not in SUPPORTED_TRANSFER_STATUSES
    )
    classification, reason = _classify(
        row,
        total_anchor_count=len(biological_istd_anchors),
        nearby_count=len(nearby),
        supported_count=supported_count,
        conflict_count=conflict_count,
        istd_scope=istd_scope,
        parameters=parameters,
    )
    nearest_label = ""
    nearest_status = ""
    nearest_rt_delta: float | None = None
    nearest_order_delta: int | None = None
    if nearest is not None:
        anchor, rt_delta, order_delta = nearest
        nearest_label = anchor.target_label
        nearest_status = transfer_status_by_target.get(anchor.target_label, "")
        nearest_rt_delta = rt_delta
        nearest_order_delta = order_delta
    supporting = _first_anchor_with_status(
        nearby,
        transfer_status_by_target=transfer_status_by_target,
        accepted_statuses=SUPPORTED_TRANSFER_STATUSES,
    )
    supporting_label = ""
    supporting_status = ""
    supporting_rt_delta: float | None = None
    supporting_order_delta: int | None = None
    if supporting is not None:
        anchor, rt_delta, order_delta = supporting
        supporting_label = anchor.target_label
        supporting_status = transfer_status_by_target.get(anchor.target_label, "")
        supporting_rt_delta = rt_delta
        supporting_order_delta = order_delta
    return RtSupportedShadowGateRow(
        source_row_id=row.source_row_id,
        source_cell_key=row.source_cell_key,
        feature_id=row.feature_id,
        sample_name=row.sample_name,
        sample_stem=row.sample_stem,
        feature_mz=row.feature_mz,
        raw_feature_rt_min=row.raw_feature_rt_min,
        injection_order=row.injection_order,
        coverage_status=row.coverage_status,
        correction_status=row.correction_status,
        rt_alignment_support_status=row.rt_alignment_support_status,
        local_residual_p95_min=row.local_residual_p95_min,
        rt_uncertainty_min=row.rt_uncertainty_min,
        local_biological_istd_anchor_count=row.local_biological_istd_anchor_count,
        nearby_biological_istd_anchor_count=len(nearby),
        supported_biological_istd_anchor_count=supported_count,
        conflict_biological_istd_anchor_count=conflict_count,
        nearest_biological_istd_label=nearest_label,
        nearest_biological_istd_transfer_status=nearest_status,
        nearest_biological_istd_rt_delta_min=nearest_rt_delta,
        nearest_biological_istd_injection_order_delta=nearest_order_delta,
        supporting_biological_istd_label=supporting_label,
        supporting_biological_istd_transfer_status=supporting_status,
        supporting_biological_istd_rt_delta_min=supporting_rt_delta,
        supporting_biological_istd_injection_order_delta=supporting_order_delta,
        row_classification=classification,
        review_reason=reason,
    )


def _classify(
    row: MatrixRtPreviewInputRow,
    *,
    total_anchor_count: int,
    nearby_count: int,
    supported_count: int,
    conflict_count: int,
    istd_scope: str,
    parameters: RtSupportedShadowGateParameters,
) -> tuple[str, str]:
    if row.correction_status != "shadow_only":
        return (
            "blocked_or_not_applicable",
            "Row is not an eligible shadow-only RT preview row.",
        )
    if row.coverage_status != "covered":
        return (
            "coverage_not_supported",
            f"RT model coverage is {row.coverage_status or 'missing'}.",
        )
    if row.rt_alignment_support_status != "local_rt_supported":
        return (
            "coverage_not_supported",
            "RT alignment support is not local_rt_supported.",
        )
    if not _within_limit(row.local_residual_p95_min, parameters.residual_max_min):
        return (
            "rt_model_uncertain",
            "Local residual p95 is missing or above the shadow gate limit.",
        )
    if not _within_limit(row.rt_uncertainty_min, parameters.uncertainty_max_min):
        return (
            "rt_model_uncertain",
            "RT uncertainty is missing or above the shadow gate limit.",
        )
    if not istd_scope:
        return (
            "biological_context_missing",
            "Biological ISTD transfer scope is missing.",
        )
    if total_anchor_count == 0:
        return (
            "biological_context_missing",
            "No biological ISTD anchor rows were provided.",
        )
    if nearby_count == 0:
        return (
            "clean_standard_only_review",
            "Clean RT model supports review, but no nearby biological ISTD "
            "anchor was available for this row.",
        )
    if supported_count > 0:
        return (
            "rt_supported_shadow_candidate",
            "Clean RT model and nearby biological ISTD transfer evidence agree.",
        )
    if conflict_count > 0:
        return (
            "biological_transfer_conflict",
            "Nearby biological ISTD anchors do not support clean-standard transfer.",
        )
    return (
        "biological_context_missing",
        "Nearby biological ISTD anchors have no transfer status.",
    )


def _nearby_anchors(
    row: MatrixRtPreviewInputRow,
    anchors: tuple[BiologicalIstdAnchorInputRow, ...],
    parameters: RtSupportedShadowGateParameters,
) -> tuple[tuple[BiologicalIstdAnchorInputRow, float, int], ...]:
    if row.raw_feature_rt_min is None or row.injection_order is None:
        return ()
    nearby: list[tuple[BiologicalIstdAnchorInputRow, float, int]] = []
    for anchor in anchors:
        if anchor.observed_rt_min is None or anchor.injection_order is None:
            continue
        rt_delta = abs(row.raw_feature_rt_min - anchor.observed_rt_min)
        order_delta = abs(row.injection_order - anchor.injection_order)
        if (
            rt_delta <= parameters.anchor_rt_window_min
            and order_delta <= parameters.anchor_injection_window
        ):
            nearby.append((anchor, rt_delta, order_delta))
    nearby.sort(key=lambda item: (item[1], item[2], item[0].target_label))
    return tuple(nearby)


def _first_anchor_with_status(
    anchors: tuple[tuple[BiologicalIstdAnchorInputRow, float, int], ...],
    *,
    transfer_status_by_target: Mapping[str, str],
    accepted_statuses: set[str],
) -> tuple[BiologicalIstdAnchorInputRow, float, int] | None:
    for anchor, rt_delta, order_delta in anchors:
        if transfer_status_by_target.get(anchor.target_label) in accepted_statuses:
            return anchor, rt_delta, order_delta
    return None


def _within_limit(value: float | None, limit: float) -> bool:
    return value is not None and isfinite(value) and value <= limit


def _run_verdict(
    *,
    counts_by_classification: Mapping[str, int],
    istd_scope: str,
    anchors: tuple[BiologicalIstdAnchorInputRow, ...],
) -> str:
    if counts_by_classification.get("rt_supported_shadow_candidate", 0) > 0:
        return "shadow_gate_ready"
    if not istd_scope or not anchors:
        return "context_incomplete"
    if (
        counts_by_classification.get("biological_context_missing", 0) > 0
        or counts_by_classification.get("clean_standard_only_review", 0) > 0
    ):
        return "context_incomplete"
    return "no_supported_rows"


def _counts(values: Iterable[str]) -> dict[str, int]:
    return dict(sorted(Counter(str(value) for value in values).items()))
