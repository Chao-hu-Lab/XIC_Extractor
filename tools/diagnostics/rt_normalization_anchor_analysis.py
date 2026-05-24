"""Analysis helpers for the RT normalization anchor diagnostic."""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping, Sequence
from statistics import median

from tools.diagnostics.rt_normalization_anchor_models import (
    AlignmentCell,
    AlignmentFeature,
    FamilyRtSummary,
    LeaveOneAnchorOutSummary,
    RtNormalizationResult,
    SampleAnchorContext,
)
from xic_extractor.alignment.rt_normalization import (
    AnchorPoint,
    AnchorResidual,
    SampleRtModel,
    fit_sample_rt_models,
)


def _summarize_families(
    features: Mapping[str, AlignmentFeature],
    cells: Sequence[AlignmentCell],
    models: Mapping[str, SampleRtModel],
    residuals: Sequence[AnchorResidual],
    *,
    anchor_residual_max_min: float,
) -> tuple[FamilyRtSummary, ...]:
    cells_by_family: dict[str, list[AlignmentCell]] = {
        family_id: [] for family_id in features
    }
    for cell in cells:
        cells_by_family.setdefault(cell.feature_family_id, []).append(cell)

    anchor_context = _sample_anchor_context(residuals)
    rows: list[FamilyRtSummary] = []
    for family_id in sorted(cells_by_family):
        family_cells = cells_by_family[family_id]
        raw_rts = [cell.apex_rt for cell in family_cells]
        normalized_rts = [
            models[cell.sample_stem].normalize_rt(cell.apex_rt)
            for cell in family_cells
            if cell.sample_stem in models
        ]
        feature = features.get(
            family_id,
            AlignmentFeature(family_id, False, None, None),
        )
        raw_range = _range(raw_rts)
        normalized_range = _range(normalized_rts)
        improvement = (
            raw_range - normalized_range
            if raw_range is not None and normalized_range is not None
            else None
        )
        normalized_median = _median(normalized_rts)
        scopes = [
            _cell_anchor_scope(cell, anchor_context)
            for cell in family_cells
            if cell.sample_stem in models
        ]
        rows.append(
            FamilyRtSummary(
                feature_family_id=family_id,
                include_in_primary_matrix=feature.include_in_primary_matrix,
                family_center_mz=feature.family_center_mz,
                family_center_rt=feature.family_center_rt,
                raw_cell_count=len(raw_rts),
                modelled_cell_count=len(normalized_rts),
                unmodelled_cell_count=len(raw_rts) - len(normalized_rts),
                raw_rt_range_min=raw_range,
                normalized_rt_range_min=normalized_range,
                rt_range_improvement_min=improvement,
                raw_rt_median_min=_median(raw_rts),
                normalized_rt_median_min=normalized_median,
                rt_band=_rt_band(normalized_median or _median(raw_rts)),
                normalized_rt_support=_normalized_rt_support(improvement),
                anchor_scope=_combined_anchor_scope(scopes),
                anchor_support_level=_combined_anchor_scope(scopes),
                local_residual_window_min=_local_residual_window(
                    family_cells,
                    anchor_context,
                    fallback=anchor_residual_max_min,
                ),
            )
        )
    return tuple(rows)


def _leave_one_anchor_out(
    points: tuple[AnchorPoint, ...],
    *,
    model_type: str,
    anchor_residual_max_min: float,
    anchor_slope_min: float,
    anchor_slope_max: float,
) -> tuple[LeaveOneAnchorOutSummary, ...]:
    labels = sorted({point.target_label for point in points})
    rows: list[LeaveOneAnchorOutSummary] = []
    for label in labels:
        train_points = tuple(point for point in points if point.target_label != label)
        held_points = tuple(point for point in points if point.target_label == label)
        models, _residuals, _sample_count = fit_sample_rt_models(
            train_points,
            model_type=model_type,
            anchor_residual_max_min=anchor_residual_max_min,
            anchor_slope_min=anchor_slope_min,
            anchor_slope_max=anchor_slope_max,
        )
        errors = [
            models[point.sample_stem].normalize_rt(point.observed_rt_min)
            - point.reference_rt_min
            for point in held_points
            if point.sample_stem in models
        ]
        abs_errors = [abs(error) for error in errors]
        p95 = _percentile(abs_errors, 0.95)
        status = "FAIL"
        if p95 is not None:
            status = "PASS" if p95 <= anchor_residual_max_min else "WARN"
        rows.append(
            LeaveOneAnchorOutSummary(
                target_label=label,
                evaluated_count=len(abs_errors),
                median_abs_error_min=_median(abs_errors),
                p95_abs_error_min=p95,
                max_abs_error_min=_max_value(abs_errors),
                status=status,
            )
        )
    return tuple(rows)


def _build_result(
    *,
    reference_source: str,
    model_type: str,
    anchor_residual_max_min: float,
    anchor_label_count: int,
    sample_count: int,
    models: Mapping[str, SampleRtModel],
    residuals: tuple[AnchorResidual, ...],
    families: tuple[FamilyRtSummary, ...],
    leave_one_out: tuple[LeaveOneAnchorOutSummary, ...],
) -> RtNormalizationResult:
    improvements = [
        family.rt_range_improvement_min
        for family in families
        if family.rt_range_improvement_min is not None
    ]
    raw_ranges = [
        family.raw_rt_range_min
        for family in families
        if family.raw_rt_range_min is not None
    ]
    normalized_ranges = [
        family.normalized_rt_range_min
        for family in families
        if family.normalized_rt_range_min is not None
    ]
    overall_status = _overall_status(
        anchor_label_count=anchor_label_count,
        has_models=bool(models),
        median_rt_range_improvement_min=_median(improvements),
    )
    return RtNormalizationResult(
        overall_status=overall_status,
        reference_source=reference_source,
        model_type=model_type,
        anchor_residual_max_min=anchor_residual_max_min,
        anchor_label_count=anchor_label_count,
        sample_count=sample_count,
        modelled_sample_count=len(models),
        unmodelled_sample_count=max(sample_count - len(models), 0),
        excluded_anchor_count=sum(
            model.excluded_anchor_count for model in models.values()
        ),
        family_count=len(families),
        families_improved_count=sum(
            1 for value in improvements if value is not None and value > 0
        ),
        families_worsened_count=sum(
            1 for value in improvements if value is not None and value < 0
        ),
        median_raw_rt_range_min=_median(raw_ranges),
        median_normalized_rt_range_min=_median(normalized_ranges),
        median_rt_range_improvement_min=_median(improvements),
        rt_band_summary=_rt_band_summary(families),
        leave_one_anchor_out=leave_one_out,
        samples=tuple(models[sample] for sample in sorted(models)),
        anchors=residuals,
        families=families,
    )


def _overall_status(
    *,
    anchor_label_count: int,
    has_models: bool,
    median_rt_range_improvement_min: float | None,
) -> str:
    if anchor_label_count < 2 or not has_models:
        return "FAIL"
    if (
        median_rt_range_improvement_min is not None
        and median_rt_range_improvement_min < 0
    ):
        return "WARN"
    return "PASS"


def _sample_anchor_context(
    residuals: Sequence[AnchorResidual],
) -> dict[str, SampleAnchorContext]:
    grouped: dict[str, list[AnchorResidual]] = {}
    for residual in residuals:
        if residual.used_in_model:
            grouped.setdefault(residual.sample_stem, []).append(residual)
    contexts: dict[str, SampleAnchorContext] = {}
    for sample, sample_residuals in grouped.items():
        observed = [row.observed_rt_min for row in sample_residuals]
        abs_residuals = tuple(
            abs(row.normalized_residual_min)
            for row in sample_residuals
            if math.isfinite(row.normalized_residual_min)
        )
        if observed:
            contexts[sample] = SampleAnchorContext(
                observed_min_rt=min(observed),
                observed_max_rt=max(observed),
                abs_residuals=abs_residuals,
            )
    return contexts


def _cell_anchor_scope(
    cell: AlignmentCell,
    anchor_context: Mapping[str, SampleAnchorContext],
) -> str:
    context = anchor_context.get(cell.sample_stem)
    if context is None:
        return "no_model"
    if cell.apex_rt < context.observed_min_rt:
        return "before_anchor_range"
    if cell.apex_rt > context.observed_max_rt:
        return "after_anchor_range"
    return "inside_anchor_range"


def _combined_anchor_scope(scopes: Sequence[str]) -> str:
    if not scopes:
        return "unmodelled"
    unique = set(scopes)
    if len(unique) == 1:
        return next(iter(unique))
    if unique <= {"before_anchor_range", "after_anchor_range"}:
        return "outside_anchor_range"
    return "mixed_anchor_range"


def _rt_band(rt_min: float | None) -> str:
    if rt_min is None:
        return "unmodelled"
    if rt_min < 10.0:
        return "<10"
    if rt_min < 20.0:
        return "10-20"
    if rt_min < 30.0:
        return "20-30"
    return ">=30"


def _normalized_rt_support(improvement: float | None) -> str:
    if improvement is None:
        return "unmodelled"
    if improvement > 0.01:
        return "improved"
    if improvement < -0.01:
        return "worsened"
    return "stable"


def _local_residual_window(
    family_cells: Sequence[AlignmentCell],
    anchor_context: Mapping[str, SampleAnchorContext],
    *,
    fallback: float,
) -> float | None:
    residuals: list[float] = []
    for cell in family_cells:
        context = anchor_context.get(cell.sample_stem)
        if context is not None:
            residuals.extend(context.abs_residuals)
    if not family_cells:
        return None
    p95 = _percentile(residuals, 0.95)
    if p95 is None:
        p95 = fallback
    return max(0.05, p95)


def _rt_band_summary(
    families: Sequence[FamilyRtSummary],
) -> dict[str, dict[str, int]]:
    summary: dict[str, dict[str, int]] = {}
    for family in families:
        bucket = summary.setdefault(
            family.rt_band,
            {"improved": 0, "worsened": 0, "stable": 0, "unmodelled": 0},
        )
        bucket[family.normalized_rt_support] = (
            bucket.get(family.normalized_rt_support, 0) + 1
        )
    return summary


def _percentile(values: Sequence[float], quantile: float) -> float | None:
    finite = sorted(value for value in values if math.isfinite(value))
    if not finite:
        return None
    if len(finite) == 1:
        return finite[0]
    index = (len(finite) - 1) * quantile
    lower = math.floor(index)
    upper = math.ceil(index)
    if lower == upper:
        return finite[int(index)]
    fraction = index - lower
    return finite[lower] + (finite[upper] - finite[lower]) * fraction


def _max_value(values: Sequence[float]) -> float | None:
    finite = [value for value in values if math.isfinite(value)]
    if not finite:
        return None
    return max(finite)


def _median(values: Iterable[float | None]) -> float | None:
    finite = [
        float(value)
        for value in values
        if isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    ]
    if not finite:
        return None
    return float(median(finite))


def _range(values: Sequence[float]) -> float | None:
    finite = [value for value in values if math.isfinite(value)]
    if len(finite) < 2:
        return None
    return max(finite) - min(finite)
