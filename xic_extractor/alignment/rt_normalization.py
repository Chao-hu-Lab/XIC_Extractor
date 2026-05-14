from __future__ import annotations

import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from statistics import median


@dataclass(frozen=True)
class AnchorPoint:
    sample_stem: str
    target_label: str
    observed_rt_min: float
    reference_rt_min: float


@dataclass(frozen=True)
class RtKnot:
    observed_rt_min: float
    reference_rt_min: float


@dataclass(frozen=True)
class SampleRtModel:
    sample_stem: str
    model_type: str
    anchor_count: int
    excluded_anchor_count: int
    slope: float
    intercept: float
    anchor_median_abs_residual_min: float | None
    anchor_max_abs_residual_min: float | None
    knots: tuple[RtKnot, ...] = ()

    def normalize_rt(self, raw_rt_min: float) -> float:
        if self.model_type == "piecewise" and self.knots:
            return _piecewise_normalize(raw_rt_min, self.knots)
        return (raw_rt_min - self.intercept) / self.slope


@dataclass(frozen=True)
class AnchorResidual:
    sample_stem: str
    target_label: str
    reference_rt_min: float
    observed_rt_min: float
    normalized_rt_min: float
    normalized_residual_min: float
    used_in_model: bool
    anchor_status: str


def apply_anchor_reference_source(
    points: tuple[AnchorPoint, ...],
    reference_source: str,
) -> tuple[AnchorPoint, ...]:
    if reference_source == "target-window":
        return points
    if reference_source != "observed-median":
        raise ValueError(f"unsupported reference source: {reference_source}")
    by_label: dict[str, list[float]] = {}
    for point in points:
        by_label.setdefault(point.target_label, []).append(point.observed_rt_min)
    references = {
        label: float(median(values)) for label, values in by_label.items() if values
    }
    return tuple(
        AnchorPoint(
            sample_stem=point.sample_stem,
            target_label=point.target_label,
            observed_rt_min=point.observed_rt_min,
            reference_rt_min=references[point.target_label],
        )
        for point in points
        if point.target_label in references
    )


def fit_sample_rt_models(
    points: Sequence[AnchorPoint],
    *,
    model_type: str,
    anchor_residual_max_min: float,
    anchor_slope_min: float,
    anchor_slope_max: float,
) -> tuple[dict[str, SampleRtModel], tuple[AnchorResidual, ...], int]:
    points_by_sample: dict[str, list[AnchorPoint]] = {}
    for point in points:
        points_by_sample.setdefault(point.sample_stem, []).append(point)

    models: dict[str, SampleRtModel] = {}
    residuals: list[AnchorResidual] = []
    for sample, sample_points in sorted(points_by_sample.items()):
        deduped = _dedupe_anchor_points(sample_points)
        used_points, excluded_points = _select_anchor_points(
            deduped,
            residual_max_min=anchor_residual_max_min,
            slope_min=anchor_slope_min,
            slope_max=anchor_slope_max,
        )
        model = _fit_sample_model(
            sample,
            used_points,
            requested_model_type=model_type,
            excluded_anchor_count=len(excluded_points),
        )
        if model is None:
            continue
        sample_residuals: list[float] = []
        used_labels = {point.target_label for point in used_points}
        for point in deduped:
            normalized_rt = model.normalize_rt(point.observed_rt_min)
            residual = normalized_rt - point.reference_rt_min
            used_in_model = point.target_label in used_labels
            if used_in_model:
                sample_residuals.append(residual)
            residuals.append(
                AnchorResidual(
                    sample_stem=sample,
                    target_label=point.target_label,
                    reference_rt_min=point.reference_rt_min,
                    observed_rt_min=point.observed_rt_min,
                    normalized_rt_min=normalized_rt,
                    normalized_residual_min=residual,
                    used_in_model=used_in_model,
                    anchor_status="used" if used_in_model else "excluded",
                )
            )
        models[sample] = SampleRtModel(
            sample_stem=model.sample_stem,
            model_type=model.model_type,
            anchor_count=model.anchor_count,
            excluded_anchor_count=model.excluded_anchor_count,
            slope=model.slope,
            intercept=model.intercept,
            anchor_median_abs_residual_min=_median_abs(sample_residuals),
            anchor_max_abs_residual_min=_max_abs(sample_residuals),
            knots=model.knots,
        )
    return models, tuple(residuals), len(points_by_sample)


def _dedupe_anchor_points(points: Sequence[AnchorPoint]) -> tuple[AnchorPoint, ...]:
    latest: dict[str, AnchorPoint] = {}
    for point in points:
        latest[point.target_label] = point
    return tuple(latest[label] for label in sorted(latest))


def _select_anchor_points(
    points: Sequence[AnchorPoint],
    *,
    residual_max_min: float,
    slope_min: float,
    slope_max: float,
) -> tuple[tuple[AnchorPoint, ...], tuple[AnchorPoint, ...]]:
    ordered = tuple(sorted(points, key=lambda point: point.reference_rt_min))
    if len(ordered) <= 3:
        return ordered, ()

    candidates: list[tuple[float, float, float, tuple[AnchorPoint, ...]]] = []
    subsets = [ordered]
    subsets.extend(
        tuple(point for point in ordered if point is not excluded)
        for excluded in ordered
    )
    for subset in subsets:
        if len(subset) < 2:
            continue
        model = _fit_affine_model("_candidate", subset, excluded_anchor_count=0)
        if model is None:
            continue
        if not (slope_min <= model.slope <= slope_max):
            continue
        residuals = [
            model.normalize_rt(point.observed_rt_min) - point.reference_rt_min
            for point in subset
        ]
        max_abs = _max_abs(residuals)
        median_abs = _median_abs(residuals)
        if max_abs is None or median_abs is None or max_abs > residual_max_min:
            continue
        candidates.append(
            (
                -float(len(subset)),
                median_abs,
                abs(model.slope - 1.0),
                subset,
            )
        )
    if not candidates:
        return ordered, ()

    chosen = min(candidates, key=lambda item: item[:3])[3]
    chosen_labels = {point.target_label for point in chosen}
    excluded = tuple(
        point for point in ordered if point.target_label not in chosen_labels
    )
    return chosen, excluded


def _fit_sample_model(
    sample_stem: str,
    points: Sequence[AnchorPoint],
    *,
    requested_model_type: str,
    excluded_anchor_count: int,
) -> SampleRtModel | None:
    if not points:
        return None
    if len(points) == 1:
        point = points[0]
        return SampleRtModel(
            sample_stem=sample_stem,
            model_type="shift",
            anchor_count=1,
            excluded_anchor_count=excluded_anchor_count,
            slope=1.0,
            intercept=point.observed_rt_min - point.reference_rt_min,
            anchor_median_abs_residual_min=None,
            anchor_max_abs_residual_min=None,
        )
    if requested_model_type in {"auto", "piecewise"} and len(points) >= 3:
        piecewise = _fit_piecewise_model(
            sample_stem,
            points,
            excluded_anchor_count=excluded_anchor_count,
        )
        if piecewise is not None:
            return piecewise
        if requested_model_type == "piecewise":
            return None
    return _fit_affine_model(
        sample_stem,
        points,
        excluded_anchor_count=excluded_anchor_count,
    )


def _fit_affine_model(
    sample_stem: str,
    points: Sequence[AnchorPoint],
    *,
    excluded_anchor_count: int,
) -> SampleRtModel | None:
    references = [point.reference_rt_min for point in points]
    observed = [point.observed_rt_min for point in points]
    ref_mean = sum(references) / len(references)
    obs_mean = sum(observed) / len(observed)
    denominator = sum((value - ref_mean) ** 2 for value in references)
    if denominator <= 0:
        return None
    slope = sum(
        (reference - ref_mean) * (rt - obs_mean)
        for reference, rt in zip(references, observed, strict=True)
    ) / denominator
    if not math.isfinite(slope) or abs(slope) < 1e-9:
        return None
    intercept = obs_mean - slope * ref_mean
    return SampleRtModel(
        sample_stem=sample_stem,
        model_type="affine",
        anchor_count=len(points),
        excluded_anchor_count=excluded_anchor_count,
        slope=slope,
        intercept=intercept,
        anchor_median_abs_residual_min=None,
        anchor_max_abs_residual_min=None,
    )


def _fit_piecewise_model(
    sample_stem: str,
    points: Sequence[AnchorPoint],
    *,
    excluded_anchor_count: int,
) -> SampleRtModel | None:
    ordered = tuple(sorted(points, key=lambda point: point.reference_rt_min))
    knots = tuple(
        RtKnot(
            observed_rt_min=point.observed_rt_min,
            reference_rt_min=point.reference_rt_min,
        )
        for point in ordered
    )
    if any(
        right.observed_rt_min <= left.observed_rt_min
        for left, right in zip(knots, knots[1:])
    ):
        return None
    affine = _fit_affine_model(
        sample_stem,
        ordered,
        excluded_anchor_count=excluded_anchor_count,
    )
    if affine is None:
        return None
    return SampleRtModel(
        sample_stem=sample_stem,
        model_type="piecewise",
        anchor_count=len(ordered),
        excluded_anchor_count=excluded_anchor_count,
        slope=affine.slope,
        intercept=affine.intercept,
        anchor_median_abs_residual_min=None,
        anchor_max_abs_residual_min=None,
        knots=knots,
    )


def _piecewise_normalize(raw_rt_min: float, knots: tuple[RtKnot, ...]) -> float:
    if len(knots) == 1:
        return raw_rt_min - (
            knots[0].observed_rt_min - knots[0].reference_rt_min
        )
    if raw_rt_min <= knots[0].observed_rt_min:
        return _interpolate_rt(raw_rt_min, knots[0], knots[1])
    for left, right in zip(knots, knots[1:]):
        if left.observed_rt_min <= raw_rt_min <= right.observed_rt_min:
            return _interpolate_rt(raw_rt_min, left, right)
    return _interpolate_rt(raw_rt_min, knots[-2], knots[-1])


def _interpolate_rt(raw_rt_min: float, left: RtKnot, right: RtKnot) -> float:
    observed_delta = right.observed_rt_min - left.observed_rt_min
    if abs(observed_delta) < 1e-12:
        return left.reference_rt_min
    fraction = (raw_rt_min - left.observed_rt_min) / observed_delta
    return left.reference_rt_min + fraction * (
        right.reference_rt_min - left.reference_rt_min
    )


def _median_abs(values: Iterable[float]) -> float | None:
    finite = [abs(value) for value in values if math.isfinite(value)]
    if not finite:
        return None
    return float(median(finite))


def _max_abs(values: Iterable[float]) -> float | None:
    finite = [abs(value) for value in values if math.isfinite(value)]
    if not finite:
        return None
    return max(finite)
