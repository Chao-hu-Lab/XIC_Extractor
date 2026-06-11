from __future__ import annotations

import math
from collections import Counter, defaultdict
from dataclasses import dataclass
from statistics import median
from typing import Mapping

MIN_STABLE_ISTD_POINTS = 5
MIN_STABLE_ELIGIBLE_FRACTION = 0.80
DEFAULT_NORMAL_RESIDUAL_FLOOR_MIN = 0.08
DEFAULT_WARNING_RESIDUAL_FLOOR_MIN = 0.15
HIGH_RAW_DRIFT_RANGE_MIN = 0.60

BIOLOGICAL_ISTD_RT_ROWS_REQUIRED_COLUMNS = {
    "sample_name",
    "injection_order",
    "target_label",
    "rt_min",
    "reliability_state",
}


@dataclass(frozen=True)
class BiologicalIstdRtInputRow:
    sample_name: str
    injection_order: float | None
    target_label: str
    rt_min: float | None
    area: float | None
    confidence: str
    reliability_state: str
    risk_reasons: str


@dataclass(frozen=True)
class BiologicalIstdRtEnvelopeRow:
    target_label: str
    sample_name: str
    injection_order: float | None
    observed_rt_min: float | None
    predicted_rt_min: float | None
    residual_min: float | None
    abs_residual_min: float | None
    normal_abs_residual_min: float | None
    warning_abs_residual_min: float | None
    envelope_status: str
    anchor_status: str
    reliability_state: str
    confidence: str
    review_reason: str


@dataclass(frozen=True)
class BiologicalIstdRtEnvelopeTarget:
    target_label: str
    anchor_status: str
    point_count: int
    eligible_count: int
    eligible_fraction: float | None
    rt_min: float | None
    rt_max: float | None
    rt_range_min: float | None
    slope_min_per_injection: float | None
    intercept_min: float | None
    median_abs_residual_min: float | None
    p90_abs_residual_min: float | None
    p95_abs_residual_min: float | None
    normal_abs_residual_min: float | None
    warning_abs_residual_min: float | None
    high_raw_drift: bool
    review_reason: str


@dataclass(frozen=True)
class BiologicalIstdRtEnvelopeResult:
    rows: tuple[BiologicalIstdRtEnvelopeRow, ...]
    targets: tuple[BiologicalIstdRtEnvelopeTarget, ...]
    run_verdict: str
    stable_target_count: int
    pooled_p95_abs_residual_min: float | None
    counts_by_envelope_status: dict[str, int]
    counts_by_anchor_status: dict[str, int]


def build_biological_istd_rt_envelope(
    rows: tuple[BiologicalIstdRtInputRow, ...],
    *,
    min_stable_points: int = MIN_STABLE_ISTD_POINTS,
    min_eligible_fraction: float = MIN_STABLE_ELIGIBLE_FRACTION,
    normal_residual_floor_min: float = DEFAULT_NORMAL_RESIDUAL_FLOOR_MIN,
    warning_residual_floor_min: float = DEFAULT_WARNING_RESIDUAL_FLOOR_MIN,
) -> BiologicalIstdRtEnvelopeResult:
    targets: list[BiologicalIstdRtEnvelopeTarget] = []
    output_rows: list[BiologicalIstdRtEnvelopeRow] = []
    rows_by_target: dict[str, list[tuple[int, BiologicalIstdRtInputRow]]] = (
        defaultdict(list)
    )
    for row_index, row in enumerate(rows):
        rows_by_target[row.target_label].append((row_index, row))

    pooled_abs_residuals: list[float] = []
    target_context: dict[str, BiologicalIstdRtEnvelopeTarget] = {}
    predictions_by_index: dict[int, tuple[float | None, float | None]] = {}

    for target_label in sorted(rows_by_target):
        indexed_rows = tuple(rows_by_target[target_label])
        target_rows = tuple(row for _, row in indexed_rows)
        target = _summarize_target(
            target_label,
            target_rows,
            min_stable_points=min_stable_points,
            min_eligible_fraction=min_eligible_fraction,
            normal_residual_floor_min=normal_residual_floor_min,
            warning_residual_floor_min=warning_residual_floor_min,
        )
        targets.append(target)
        target_context[target_label] = target
        predictions = _predictions_for_target(target_rows, target)
        for (row_index, _), prediction in zip(indexed_rows, predictions, strict=True):
            predictions_by_index[row_index] = prediction
        if target.anchor_status == "stable_istd_anchor":
            pooled_abs_residuals.extend(
                abs_residual
                for _, abs_residual in predictions
                if abs_residual is not None
            )

    pooled_p95 = _percentile(pooled_abs_residuals, 0.95)
    for row_index, input_row in enumerate(rows):
        target = target_context[input_row.target_label]
        predicted, abs_residual = predictions_by_index.get(row_index, (None, None))
        residual = (
            None
            if predicted is None or input_row.rt_min is None
            else input_row.rt_min - predicted
        )
        status, reason = _classify_row(
            input_row,
            target,
            abs_residual=abs_residual,
        )
        output_rows.append(
            BiologicalIstdRtEnvelopeRow(
                target_label=input_row.target_label,
                sample_name=input_row.sample_name,
                injection_order=input_row.injection_order,
                observed_rt_min=input_row.rt_min,
                predicted_rt_min=predicted,
                residual_min=residual,
                abs_residual_min=abs_residual,
                normal_abs_residual_min=target.normal_abs_residual_min,
                warning_abs_residual_min=target.warning_abs_residual_min,
                envelope_status=status,
                anchor_status=target.anchor_status,
                reliability_state=input_row.reliability_state,
                confidence=input_row.confidence,
                review_reason=reason,
            )
        )

    envelope_counts = Counter(row.envelope_status for row in output_rows)
    anchor_counts = Counter(target.anchor_status for target in targets)
    stable_count = anchor_counts.get("stable_istd_anchor", 0)
    if not rows:
        verdict = "input_empty"
    elif stable_count == 0:
        verdict = "no_stable_istd_anchor"
    else:
        verdict = "rt_envelope_ready"
    return BiologicalIstdRtEnvelopeResult(
        rows=tuple(output_rows),
        targets=tuple(targets),
        run_verdict=verdict,
        stable_target_count=stable_count,
        pooled_p95_abs_residual_min=pooled_p95,
        counts_by_envelope_status=dict(sorted(envelope_counts.items())),
        counts_by_anchor_status=dict(sorted(anchor_counts.items())),
    )


def parse_biological_istd_rt_input_rows(
    rows: tuple[Mapping[str, str], ...],
) -> tuple[BiologicalIstdRtInputRow, ...]:
    parsed: list[BiologicalIstdRtInputRow] = []
    for row in rows:
        target = (row.get("target_label") or "").strip()
        sample = (row.get("sample_name") or "").strip()
        if not target or not sample:
            continue
        parsed.append(
            BiologicalIstdRtInputRow(
                sample_name=sample,
                injection_order=_to_optional_float(
                    row.get("injection_order"),
                    column="injection_order",
                ),
                target_label=target,
                rt_min=_to_optional_float(
                    row.get("rt_min") or row.get("observed_rt_min"),
                    column="rt_min",
                ),
                area=_to_optional_float(row.get("area"), column="area"),
                confidence=(row.get("confidence") or "").strip(),
                reliability_state=(row.get("reliability_state") or "").strip(),
                risk_reasons=(row.get("risk_reasons") or "").strip(),
            )
        )
    return tuple(parsed)


def _summarize_target(
    target_label: str,
    rows: tuple[BiologicalIstdRtInputRow, ...],
    *,
    min_stable_points: int,
    min_eligible_fraction: float,
    normal_residual_floor_min: float,
    warning_residual_floor_min: float,
) -> BiologicalIstdRtEnvelopeTarget:
    usable = tuple(
        row
        for row in rows
        if row.rt_min is not None and row.injection_order is not None
    )
    eligible = tuple(
        row
        for row in usable
        if row.reliability_state == "benchmark_eligible"
        and not _has_hard_risk_reason(row.risk_reasons)
    )
    has_hard_risk = any(_has_hard_risk_reason(row.risk_reasons) for row in usable)
    eligible_fraction = len(eligible) / len(usable) if usable else None
    slope, intercept = _linear_fit(eligible)
    abs_residuals = _abs_residuals(eligible, slope=slope, intercept=intercept)
    p95 = _percentile(abs_residuals, 0.95)
    robust_limit = _robust_residual_limit(abs_residuals)
    normal_base = robust_limit if robust_limit is not None else p95
    normal = (
        None
        if normal_base is None
        else max(normal_base, normal_residual_floor_min)
    )
    warning_base = None if normal is None else normal * 1.5
    warning = (
        None
        if warning_base is None
        else max(warning_base, warning_residual_floor_min, normal or 0.0)
    )
    rt_values = [row.rt_min for row in usable if row.rt_min is not None]
    rt_min = min(rt_values) if rt_values else None
    rt_max = max(rt_values) if rt_values else None
    rt_range = None if rt_min is None or rt_max is None else rt_max - rt_min
    if has_hard_risk:
        status = "hard_risk_excluded"
        reason = (
            "At least one biological ISTD row has a hard manual risk marker, "
            "so this target is not used as a stable RT anchor."
        )
    elif len(eligible) < min_stable_points:
        status = "insufficient_points"
        reason = "Too few benchmark-eligible biological ISTD RT points."
    elif eligible_fraction is None or eligible_fraction < min_eligible_fraction:
        status = "unstable_or_incomplete"
        reason = "Benchmark-eligible fraction is below the stable-anchor threshold."
    elif slope is None or intercept is None:
        status = "model_unavailable"
        reason = "RT drift model cannot be fit for this ISTD."
    else:
        status = "stable_istd_anchor"
        reason = (
            "Enough benchmark-eligible biological ISTD points define an "
            "empirical RT envelope."
        )
    return BiologicalIstdRtEnvelopeTarget(
        target_label=target_label,
        anchor_status=status,
        point_count=len(usable),
        eligible_count=len(eligible),
        eligible_fraction=eligible_fraction,
        rt_min=rt_min,
        rt_max=rt_max,
        rt_range_min=rt_range,
        slope_min_per_injection=slope,
        intercept_min=intercept,
        median_abs_residual_min=median(abs_residuals) if abs_residuals else None,
        p90_abs_residual_min=_percentile(abs_residuals, 0.90),
        p95_abs_residual_min=p95,
        normal_abs_residual_min=normal,
        warning_abs_residual_min=warning,
        high_raw_drift=rt_range is not None and rt_range >= HIGH_RAW_DRIFT_RANGE_MIN,
        review_reason=reason,
    )


def _predictions_for_target(
    rows: tuple[BiologicalIstdRtInputRow, ...],
    target: BiologicalIstdRtEnvelopeTarget,
) -> tuple[tuple[float | None, float | None], ...]:
    if target.anchor_status != "stable_istd_anchor":
        return tuple((None, None) for _ in rows)
    predictions: list[tuple[float | None, float | None]] = []
    for row in rows:
        if (
            row.injection_order is None
            or row.rt_min is None
            or target.slope_min_per_injection is None
            or target.intercept_min is None
        ):
            predictions.append((None, None))
            continue
        predicted = (
            target.slope_min_per_injection * row.injection_order
            + target.intercept_min
        )
        predictions.append((predicted, abs(row.rt_min - predicted)))
    return tuple(predictions)


def _classify_row(
    row: BiologicalIstdRtInputRow,
    target: BiologicalIstdRtEnvelopeTarget,
    *,
    abs_residual: float | None,
) -> tuple[str, str]:
    if target.anchor_status != "stable_istd_anchor":
        if _has_hard_risk_reason(row.risk_reasons):
            return (
                "hard_risk_excluded",
                "Row has a hard manual risk marker and cannot define normal RT drift.",
            )
        return (
            "anchor_not_stable",
            f"Target anchor status is {target.anchor_status}.",
        )
    if row.reliability_state != "benchmark_eligible":
        return (
            "row_not_benchmark_eligible",
            "Row is not benchmark eligible and should not define normal RT drift.",
        )
    if abs_residual is None:
        return "rt_context_missing", "Observed RT or injection order is missing."
    normal = target.normal_abs_residual_min
    warning = target.warning_abs_residual_min
    if normal is not None and abs_residual <= normal:
        return (
            "inside_normal_envelope",
            "RT residual is inside this ISTD's empirical normal envelope.",
        )
    if warning is not None and abs_residual <= warning:
        return (
            "inside_warning_envelope",
            "RT residual is outside normal but still inside the warning envelope.",
        )
    return (
        "outside_envelope",
        "RT residual exceeds this ISTD's empirical warning envelope.",
    )


def _linear_fit(
    rows: tuple[BiologicalIstdRtInputRow, ...],
) -> tuple[float | None, float | None]:
    pairs = tuple(
        (row.injection_order, row.rt_min)
        for row in rows
        if row.injection_order is not None and row.rt_min is not None
    )
    if len(pairs) < 2:
        return None, None
    slopes: list[float] = []
    for index, (x1, y1) in enumerate(pairs):
        for x2, y2 in pairs[index + 1 :]:
            if x1 == x2:
                continue
            slopes.append((y2 - y1) / (x2 - x1))
    if not slopes:
        return None, None
    slope = median(slopes)
    intercept = median([y - slope * x for x, y in pairs])
    return slope, intercept


def _robust_residual_limit(values: list[float]) -> float | None:
    if not values:
        return None
    center = median(values)
    deviations = [abs(value - center) for value in values]
    mad = median(deviations)
    return center + 3.0 * mad


def _abs_residuals(
    rows: tuple[BiologicalIstdRtInputRow, ...],
    *,
    slope: float | None,
    intercept: float | None,
) -> list[float]:
    if slope is None or intercept is None:
        return []
    residuals: list[float] = []
    for row in rows:
        if row.injection_order is None or row.rt_min is None:
            continue
        residuals.append(abs(row.rt_min - (slope * row.injection_order + intercept)))
    return residuals


def _percentile(values: list[float], quantile: float) -> float | None:
    if not values:
        return None
    sorted_values = sorted(values)
    if len(sorted_values) == 1:
        return sorted_values[0]
    position = (len(sorted_values) - 1) * quantile
    lower_index = math.floor(position)
    upper_index = math.ceil(position)
    if lower_index == upper_index:
        return sorted_values[lower_index]
    lower_value = sorted_values[lower_index]
    upper_value = sorted_values[upper_index]
    fraction = position - lower_index
    return lower_value + (upper_value - lower_value) * fraction


def _has_hard_risk_reason(risk_reasons: str) -> bool:
    tokens = {token.strip() for token in risk_reasons.split(";") if token.strip()}
    return bool(tokens & {"manual_false_positive", "wrong_peak", "targeted_negative"})


def _to_optional_float(value: str | None, *, column: str) -> float | None:
    if value is None:
        return None
    text = value.strip()
    if not text:
        return None
    try:
        number = float(text)
    except ValueError:
        raise ValueError(f"column {column} has invalid numeric value: {text!r}")
    if not math.isfinite(number):
        raise ValueError(f"column {column} has non-finite numeric value: {text!r}")
    return number
