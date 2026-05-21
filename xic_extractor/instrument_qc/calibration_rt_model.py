from __future__ import annotations

import math
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from statistics import median

from xic_extractor.instrument_qc.calibration_product_models import (
    ARTIFACT_SCHEMA_VERSION,
    CalibrationEvidenceRow,
    CoverageStatus,
    RtDriftModelRow,
    RtLeaveOneAnchorOutRow,
)

LOCAL_RT_WINDOW_MIN = 4.0
LOCAL_INJECTION_WINDOW = 25
MIN_COVERED_ANCHORS = 3
MAX_LOCAL_ANCHORS = 8
LOAO_PASS_ERROR_MIN = 0.15
LOAO_WARN_ERROR_MIN = 0.30


@dataclass(frozen=True)
class RtAnchor:
    evidence_row_id: str
    source_type: str
    matrix_context: str
    compound: str
    compound_group: str
    injection_order: int
    reference_rt_min: float
    observed_rt_min: float
    rt_delta_min: float


@dataclass(frozen=True)
class RtPrediction:
    model_id: str
    predicted_rt_delta_min: float | None
    rt_uncertainty_min: float | None
    coverage_status: CoverageStatus
    rt_alignment_support_status: str
    local_anchor_count: int
    local_clean_anchor_count: int
    local_biological_istd_anchor_count: int
    local_residual_p95_min: float | None
    irt_anchor_scope: str
    irt_position: float | None
    review_reason: str
    local_anchor_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class RtModelBundle:
    anchors: tuple[RtAnchor, ...]
    model_rows: tuple[RtDriftModelRow, ...]
    leave_one_anchor_out_rows: tuple[RtLeaveOneAnchorOutRow, ...]
    summary: dict[str, object]

    def predict(
        self,
        *,
        feature_rt_min: float | None,
        injection_order: int | None,
        compound: str | None = None,
        exclude_evidence_row_id: str | None = None,
    ) -> RtPrediction:
        return predict_rt_delta(
            self.anchors,
            feature_rt_min=feature_rt_min,
            injection_order=injection_order,
            compound=compound,
            exclude_evidence_row_id=exclude_evidence_row_id,
        )


def build_rt_model_bundle(
    *,
    bundle_id: str,
    evidence_rows: tuple[CalibrationEvidenceRow, ...],
) -> RtModelBundle:
    anchors = calibration_rt_anchors(evidence_rows)
    loo_rows = _leave_one_anchor_out(bundle_id=bundle_id, anchors=anchors)
    model_rows = tuple(
        _model_row_for_anchor(bundle_id=bundle_id, anchor=anchor, anchors=anchors)
        for anchor in anchors
    )
    summary = _summary_payload(
        bundle_id=bundle_id,
        anchors=anchors,
        model_rows=model_rows,
        leave_one_rows=loo_rows,
    )
    return RtModelBundle(
        anchors=anchors,
        model_rows=model_rows,
        leave_one_anchor_out_rows=loo_rows,
        summary=summary,
    )


def calibration_rt_anchors(
    rows: tuple[CalibrationEvidenceRow, ...],
) -> tuple[RtAnchor, ...]:
    anchors: list[RtAnchor] = []
    for row in rows:
        if not row.calibration_eligible:
            continue
        if (
            row.injection_order is None
            or row.reference_rt_min is None
            or row.observed_rt_min is None
            or row.rt_delta_min is None
        ):
            continue
        anchors.append(
            RtAnchor(
                evidence_row_id=row.evidence_row_id,
                source_type=row.source_type,
                matrix_context=row.matrix_context,
                compound=row.compound,
                compound_group=row.compound_group,
                injection_order=row.injection_order,
                reference_rt_min=row.reference_rt_min,
                observed_rt_min=row.observed_rt_min,
                rt_delta_min=row.rt_delta_min,
            )
        )
    return tuple(
        sorted(
            anchors,
            key=lambda anchor: (
                anchor.injection_order,
                anchor.reference_rt_min,
                anchor.evidence_row_id,
            ),
        )
    )


def predict_rt_delta(
    anchors: tuple[RtAnchor, ...],
    *,
    feature_rt_min: float | None,
    injection_order: int | None,
    compound: str | None = None,
    exclude_evidence_row_id: str | None = None,
) -> RtPrediction:
    usable = tuple(
        anchor
        for anchor in anchors
        if anchor.evidence_row_id != exclude_evidence_row_id
    )
    if not usable:
        return _blocked_prediction(
            CoverageStatus.UNSUPPORTED,
            "unsupported_no_rt_anchors",
            "No eligible RT calibration anchors are available.",
        )
    if feature_rt_min is None:
        return _blocked_prediction(
            CoverageStatus.INCOMPLETE,
            "incomplete_missing_feature_rt",
            "Feature RT is missing, so local RT support cannot be evaluated.",
        )
    if injection_order is None:
        scope, position = _irt_scope(feature_rt_min, usable)
        return _blocked_prediction(
            CoverageStatus.INCOMPLETE,
            "incomplete_missing_injection_order",
            "Docs-derived injection order is missing for this matrix cell.",
            irt_anchor_scope=scope,
            irt_position=position,
        )

    local = _select_local_anchors(
        usable,
        feature_rt_min=feature_rt_min,
        injection_order=injection_order,
        compound=compound,
    )
    if not local:
        return _blocked_prediction(
            CoverageStatus.UNSUPPORTED,
            "unsupported_no_local_rt_anchors",
            "No local anchors are available for this RT/order position.",
        )
    predicted = _weighted_delta(
        local,
        feature_rt_min=feature_rt_min,
        injection_order=injection_order,
    )
    residuals = tuple(abs(anchor.rt_delta_min - predicted) for anchor in local)
    uncertainty = _median(residuals)
    residual_p95 = _percentile(residuals, 0.95)
    coverage = _coverage_status(
        usable,
        local,
        feature_rt_min=feature_rt_min,
        injection_order=injection_order,
    )
    status = _alignment_support_status(coverage)
    scope, position = _irt_scope(feature_rt_min, usable)
    local_clean = sum(1 for anchor in local if anchor.matrix_context == "clean")
    local_bio = sum(
        1
        for anchor in local
        if anchor.matrix_context == "biological_qc"
        or anchor.source_type == "biological_qc_istd"
    )
    return RtPrediction(
        model_id=f"local_rt_{coverage.value}_{len(local)}anchors",
        predicted_rt_delta_min=predicted,
        rt_uncertainty_min=uncertainty,
        coverage_status=coverage,
        rt_alignment_support_status=status,
        local_anchor_count=len(local),
        local_clean_anchor_count=local_clean,
        local_biological_istd_anchor_count=local_bio,
        local_residual_p95_min=residual_p95,
        irt_anchor_scope=scope,
        irt_position=position,
        review_reason=_prediction_reason(coverage, len(local), scope),
        local_anchor_ids=tuple(anchor.evidence_row_id for anchor in local),
    )


def _model_row_for_anchor(
    *,
    bundle_id: str,
    anchor: RtAnchor,
    anchors: tuple[RtAnchor, ...],
) -> RtDriftModelRow:
    prediction = predict_rt_delta(
        anchors,
        feature_rt_min=anchor.reference_rt_min,
        injection_order=anchor.injection_order,
        compound=anchor.compound,
    )
    local = {
        local_anchor.evidence_row_id: local_anchor
        for local_anchor in anchors
        if local_anchor.evidence_row_id in prediction.local_anchor_ids
    }
    source_mix = ";".join(sorted({item.source_type for item in local.values()}))
    local_contexts = {item.matrix_context for item in local.values()}
    matrix_context = (
        next(iter(local_contexts)) if len(local_contexts) == 1 else "mixed"
    )
    model_status = _model_status(prediction.coverage_status)
    return RtDriftModelRow(
        schema_version=ARTIFACT_SCHEMA_VERSION,
        bundle_id=bundle_id,
        model_id=f"rt-local-{anchor.evidence_row_id}",
        model_scope="local_rt_order",
        compound=anchor.compound,
        compound_group=anchor.compound_group,
        source_type=source_mix or anchor.source_type,
        matrix_context=matrix_context,
        injection_order=anchor.injection_order,
        rt_region=_rt_region(anchor.reference_rt_min),
        source_mix=source_mix,
        anchor_ids=";".join(prediction.local_anchor_ids),
        anchor_count=prediction.local_anchor_count,
        clean_anchor_count=prediction.local_clean_anchor_count,
        biological_istd_anchor_count=prediction.local_biological_istd_anchor_count,
        predicted_rt_delta_min=prediction.predicted_rt_delta_min,
        rt_uncertainty_min=prediction.rt_uncertainty_min,
        coverage_status=prediction.coverage_status,
        conflict_status="insufficient_comparison",
        model_status=model_status,
        review_reason=prediction.review_reason,
    )


def _leave_one_anchor_out(
    *,
    bundle_id: str,
    anchors: tuple[RtAnchor, ...],
) -> tuple[RtLeaveOneAnchorOutRow, ...]:
    rows: list[RtLeaveOneAnchorOutRow] = []
    for anchor in anchors:
        prediction = predict_rt_delta(
            anchors,
            feature_rt_min=anchor.reference_rt_min,
            injection_order=anchor.injection_order,
            compound=anchor.compound,
            exclude_evidence_row_id=anchor.evidence_row_id,
        )
        error = (
            None
            if prediction.predicted_rt_delta_min is None
            else anchor.rt_delta_min - prediction.predicted_rt_delta_min
        )
        abs_error = None if error is None else abs(error)
        status = _loo_status(abs_error)
        rows.append(
            RtLeaveOneAnchorOutRow(
                schema_version=ARTIFACT_SCHEMA_VERSION,
                bundle_id=bundle_id,
                evidence_row_id=anchor.evidence_row_id,
                compound=anchor.compound,
                source_type=anchor.source_type,
                matrix_context=anchor.matrix_context,
                injection_order=anchor.injection_order,
                reference_rt_min=anchor.reference_rt_min,
                observed_rt_delta_min=anchor.rt_delta_min,
                predicted_rt_delta_min=prediction.predicted_rt_delta_min,
                prediction_error_min=error,
                abs_prediction_error_min=abs_error,
                local_anchor_count=prediction.local_anchor_count,
                coverage_status=prediction.coverage_status,
                status=status,
                review_reason=prediction.review_reason,
            )
        )
    return tuple(rows)


def _select_local_anchors(
    anchors: tuple[RtAnchor, ...],
    *,
    feature_rt_min: float,
    injection_order: int,
    compound: str | None,
) -> tuple[RtAnchor, ...]:
    if compound:
        same_compound = tuple(
            anchor for anchor in anchors if anchor.compound == compound
        )
        if len(same_compound) >= 2:
            return tuple(
                sorted(
                    same_compound,
                    key=lambda anchor: abs(anchor.injection_order - injection_order),
                )[:MAX_LOCAL_ANCHORS]
            )
    in_window = tuple(
        anchor
        for anchor in anchors
        if abs(anchor.reference_rt_min - feature_rt_min) <= LOCAL_RT_WINDOW_MIN
        and abs(anchor.injection_order - injection_order) <= LOCAL_INJECTION_WINDOW
    )
    if len(in_window) >= MIN_COVERED_ANCHORS:
        return tuple(
            sorted(
                in_window,
                key=lambda anchor: _distance(anchor, feature_rt_min, injection_order),
            )[:MAX_LOCAL_ANCHORS]
        )
    nearest = sorted(
        anchors,
        key=lambda anchor: _distance(anchor, feature_rt_min, injection_order),
    )
    return tuple(nearest[: min(max(MIN_COVERED_ANCHORS, len(in_window)), len(nearest))])


def _coverage_status(
    anchors: tuple[RtAnchor, ...],
    local: tuple[RtAnchor, ...],
    *,
    feature_rt_min: float,
    injection_order: int,
) -> CoverageStatus:
    rt_values = [anchor.reference_rt_min for anchor in anchors]
    orders = [anchor.injection_order for anchor in anchors]
    if not rt_values or not orders:
        return CoverageStatus.UNSUPPORTED
    if (
        feature_rt_min < min(rt_values)
        or feature_rt_min > max(rt_values)
        or injection_order < min(orders)
        or injection_order > max(orders)
    ):
        return CoverageStatus.EXTRAPOLATED
    in_window_count = sum(
        1
        for anchor in local
        if abs(anchor.reference_rt_min - feature_rt_min) <= LOCAL_RT_WINDOW_MIN
        and abs(anchor.injection_order - injection_order) <= LOCAL_INJECTION_WINDOW
    )
    if in_window_count >= MIN_COVERED_ANCHORS:
        return CoverageStatus.COVERED
    return CoverageStatus.SPARSE


def _weighted_delta(
    anchors: tuple[RtAnchor, ...],
    *,
    feature_rt_min: float,
    injection_order: int,
) -> float:
    weighted_sum = 0.0
    weight_total = 0.0
    for anchor in anchors:
        rt_distance = abs(anchor.reference_rt_min - feature_rt_min)
        order_distance = abs(anchor.injection_order - injection_order)
        weight = 1.0 / (0.25 + rt_distance) * 1.0 / (1.0 + order_distance / 10.0)
        weighted_sum += anchor.rt_delta_min * weight
        weight_total += weight
    if weight_total <= 0:
        return float(median(anchor.rt_delta_min for anchor in anchors))
    return weighted_sum / weight_total


def _blocked_prediction(
    coverage: CoverageStatus,
    support_status: str,
    reason: str,
    *,
    irt_anchor_scope: str = "not_assessable",
    irt_position: float | None = None,
) -> RtPrediction:
    return RtPrediction(
        model_id=support_status,
        predicted_rt_delta_min=None,
        rt_uncertainty_min=None,
        coverage_status=coverage,
        rt_alignment_support_status=support_status,
        local_anchor_count=0,
        local_clean_anchor_count=0,
        local_biological_istd_anchor_count=0,
        local_residual_p95_min=None,
        irt_anchor_scope=irt_anchor_scope,
        irt_position=irt_position,
        review_reason=reason,
    )


def _distance(anchor: RtAnchor, feature_rt_min: float, injection_order: int) -> float:
    rt_component = abs(anchor.reference_rt_min - feature_rt_min) / LOCAL_RT_WINDOW_MIN
    order_component = (
        abs(anchor.injection_order - injection_order) / LOCAL_INJECTION_WINDOW
    )
    return rt_component + order_component


def _irt_scope(
    feature_rt_min: float,
    anchors: tuple[RtAnchor, ...],
) -> tuple[str, float | None]:
    rt_values = [anchor.reference_rt_min for anchor in anchors]
    if not rt_values:
        return "no_rt_anchors", None
    lo = min(rt_values)
    hi = max(rt_values)
    if math.isclose(lo, hi):
        return "single_anchor_rt", None
    position = 100.0 * (feature_rt_min - lo) / (hi - lo)
    if feature_rt_min < lo:
        return "before_anchor_range", position
    if feature_rt_min > hi:
        return "after_anchor_range", position
    return "inside_anchor_range", position


def _alignment_support_status(coverage: CoverageStatus) -> str:
    if coverage == CoverageStatus.COVERED:
        return "local_rt_supported"
    if coverage == CoverageStatus.SPARSE:
        return "local_rt_sparse_review"
    if coverage == CoverageStatus.EXTRAPOLATED:
        return "local_rt_extrapolated_review"
    if coverage == CoverageStatus.INCOMPLETE:
        return "local_rt_context_incomplete"
    return "local_rt_unsupported"


def _prediction_reason(
    coverage: CoverageStatus,
    anchor_count: int,
    irt_scope: str,
) -> str:
    if coverage == CoverageStatus.COVERED:
        return (
            f"Local RT prediction uses {anchor_count} anchors; feature is "
            f"{irt_scope}."
        )
    if coverage == CoverageStatus.SPARSE:
        return (
            f"Local RT prediction is sparse with {anchor_count} anchors; feature "
            f"is {irt_scope}."
        )
    if coverage == CoverageStatus.EXTRAPOLATED:
        return (
            f"RT/order position is outside anchor coverage; prediction is "
            f"review-only with {anchor_count} nearest anchors."
        )
    return "Local RT prediction is not supported."


def _model_status(coverage: CoverageStatus) -> str:
    if coverage == CoverageStatus.COVERED:
        return "usable"
    if coverage in {CoverageStatus.SPARSE, CoverageStatus.EXTRAPOLATED}:
        return "review"
    return "not_usable"


def _loo_status(abs_error: float | None) -> str:
    if abs_error is None:
        return "FAIL"
    if abs_error <= LOAO_PASS_ERROR_MIN:
        return "PASS"
    if abs_error <= LOAO_WARN_ERROR_MIN:
        return "WARN"
    return "FAIL"


def _summary_payload(
    *,
    bundle_id: str,
    anchors: tuple[RtAnchor, ...],
    model_rows: tuple[RtDriftModelRow, ...],
    leave_one_rows: tuple[RtLeaveOneAnchorOutRow, ...],
) -> dict[str, object]:
    abs_errors = [
        row.abs_prediction_error_min
        for row in leave_one_rows
        if row.abs_prediction_error_min is not None
    ]
    return {
        "schema_version": ARTIFACT_SCHEMA_VERSION,
        "bundle_id": bundle_id,
        "model_kind": "local_rt_alignment_support",
        "anchor_count": len(anchors),
        "counts_by_source_type": _counts(anchor.source_type for anchor in anchors),
        "counts_by_matrix_context": _counts(
            anchor.matrix_context for anchor in anchors
        ),
        "counts_by_coverage_status": _counts(
            row.coverage_status.value for row in model_rows
        ),
        "leave_one_anchor_out_count": len(leave_one_rows),
        "leave_one_anchor_out_status_counts": _counts(
            row.status for row in leave_one_rows
        ),
        "leave_one_anchor_out_median_abs_error_min": _median(abs_errors),
        "leave_one_anchor_out_p95_abs_error_min": _percentile(abs_errors, 0.95),
        "rt_anchor_min_min": min(
            (anchor.reference_rt_min for anchor in anchors),
            default=None,
        ),
        "rt_anchor_max_min": max(
            (anchor.reference_rt_min for anchor in anchors),
            default=None,
        ),
        "injection_order_min": min(
            (anchor.injection_order for anchor in anchors),
            default=None,
        ),
        "injection_order_max": max(
            (anchor.injection_order for anchor in anchors),
            default=None,
        ),
        "review_reason": (
            "Audit-only local RT model. Predictions support alignment review and "
            "do not alter matrix RT, area, scoring, reliability, or identity."
        ),
    }


def _counts(values: Iterable[object]) -> dict[str, int]:
    return dict(sorted(Counter(str(value) for value in values).items()))


def _median(values: list[float] | tuple[float, ...]) -> float | None:
    return float(median(values)) if values else None


def _percentile(values: list[float] | tuple[float, ...], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = q * (len(ordered) - 1)
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction


def _rt_region(rt: float | None) -> str:
    if rt is None:
        return "rt_unknown"
    start = int(rt)
    return f"rt_{start:02d}_{start + 1:02d}"
