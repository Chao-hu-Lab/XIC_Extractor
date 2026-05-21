from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Mapping

MIN_BIOLOGICAL_QC_POINTS = 6
MIN_CLEAN_STANDARD_POINTS = 3
SLOPE_EPSILON = 0.001
SUPPORTED_RATIO_MIN = 0.67
SUPPORTED_RATIO_MAX = 1.50

BIOLOGICAL_ISTD_SUMMARY_REQUIRED_COLUMNS = {
    "target_label",
    "benchmark_eligible_count",
    "rt_range_min",
    "rt_slope_min_per_injection",
}

CLEAN_STANDARD_SUMMARY_REQUIRED_COLUMNS = {
    "compound",
    "point_count",
    "rt_delta_range_min",
    "rt_slope_min_per_injection",
    "warning_count",
}


@dataclass(frozen=True)
class BiologicalIstdTransferAuditRow:
    target_label: str
    transfer_status: str
    direction_status: str
    biological_qc_count: int | None
    clean_standard_count: int | None
    biological_rt_range_min: float | None
    clean_rt_delta_range_min: float | None
    biological_slope_min_per_injection: float | None
    clean_slope_min_per_injection: float | None
    slope_magnitude_ratio: float | None
    clean_warning_count: int | None
    review_reason: str


def build_biological_istd_transfer_audit_rows(
    *,
    biological_qc_rows: tuple[Mapping[str, str], ...],
    clean_standard_rows: tuple[Mapping[str, str], ...],
) -> tuple[BiologicalIstdTransferAuditRow, ...]:
    clean_by_compound = {
        (row.get("compound") or "").strip(): row
        for row in clean_standard_rows
        if (row.get("compound") or "").strip()
    }
    output: list[BiologicalIstdTransferAuditRow] = []
    for bio in biological_qc_rows:
        target = (bio.get("target_label") or "").strip()
        if not target:
            continue
        output.append(
            classify_biological_istd_transfer(
                target_label=target,
                biological_qc_row=bio,
                clean_standard_row=clean_by_compound.get(target),
            )
        )
    return tuple(output)


def classify_biological_istd_transfer(
    *,
    target_label: str,
    biological_qc_row: Mapping[str, str],
    clean_standard_row: Mapping[str, str] | None,
) -> BiologicalIstdTransferAuditRow:
    bio_count = _to_int(biological_qc_row.get("benchmark_eligible_count"))
    bio_range = _to_float(biological_qc_row.get("rt_range_min"))
    bio_slope = _to_float(biological_qc_row.get("rt_slope_min_per_injection"))
    clean_count = _to_int(
        clean_standard_row.get("point_count") if clean_standard_row else None
    )
    clean_range = _to_float(
        clean_standard_row.get("rt_delta_range_min") if clean_standard_row else None
    )
    clean_slope = _to_float(
        clean_standard_row.get("rt_slope_min_per_injection")
        if clean_standard_row
        else None
    )
    clean_warning_count = _to_int(
        clean_standard_row.get("warning_count") if clean_standard_row else None
    )
    direction = direction_status(bio_slope, clean_slope)
    ratio = slope_magnitude_ratio(bio_slope, clean_slope)
    status, reason = transfer_status(
        biological_qc_count=bio_count,
        clean_standard_count=clean_count,
        direction=direction,
        slope_ratio=ratio,
        biological_slope=bio_slope,
        clean_slope=clean_slope,
    )
    return BiologicalIstdTransferAuditRow(
        target_label=target_label,
        transfer_status=status,
        direction_status=direction,
        biological_qc_count=bio_count,
        clean_standard_count=clean_count,
        biological_rt_range_min=bio_range,
        clean_rt_delta_range_min=clean_range,
        biological_slope_min_per_injection=bio_slope,
        clean_slope_min_per_injection=clean_slope,
        slope_magnitude_ratio=ratio,
        clean_warning_count=clean_warning_count,
        review_reason=reason,
    )


def transfer_status(
    *,
    biological_qc_count: int | None,
    clean_standard_count: int | None,
    direction: str,
    slope_ratio: float | None,
    biological_slope: float | None,
    clean_slope: float | None,
) -> tuple[str, str]:
    if (
        biological_qc_count is None
        or biological_qc_count < MIN_BIOLOGICAL_QC_POINTS
    ):
        return (
            "insufficient_biological_istd",
            "Biological QC ISTD evidence is too sparse for transfer assessment.",
        )
    if clean_standard_count is None or clean_standard_count < MIN_CLEAN_STANDARD_POINTS:
        return (
            "insufficient_clean_standard",
            "Clean-standard evidence is missing or too sparse.",
        )
    if direction == "opposite_direction":
        return (
            "transfer_not_supported",
            "Clean-standard and biological QC ISTD slopes point in opposite "
            "directions.",
        )
    if direction in {"bio_drift_clean_flat", "bio_flat_clean_drift"}:
        return (
            "transfer_not_supported",
            "One side shows meaningful RT drift while the other is effectively flat.",
        )
    if direction == "both_flat":
        return (
            "transfer_supported",
            "Both clean-standard and biological QC ISTD slopes are effectively flat.",
        )
    if (
        slope_ratio is not None
        and SUPPORTED_RATIO_MIN <= slope_ratio <= SUPPORTED_RATIO_MAX
    ):
        return (
            "transfer_supported",
            "Clean-standard and biological QC ISTD slopes agree in direction "
            "and magnitude.",
        )
    if _has_meaningful_slope(biological_slope) and _has_meaningful_slope(clean_slope):
        return (
            "direction_supported_magnitude_shifted",
            "Slope direction agrees, but biological matrix changes the apparent "
            "drift magnitude.",
        )
    return (
        "transfer_not_supported",
        "Clean-standard evidence does not explain biological QC ISTD drift.",
    )


def direction_status(
    biological_slope: float | None,
    clean_slope: float | None,
) -> str:
    if biological_slope is None or clean_slope is None:
        return "incomplete"
    bio_meaningful = _has_meaningful_slope(biological_slope)
    clean_meaningful = _has_meaningful_slope(clean_slope)
    if not bio_meaningful and not clean_meaningful:
        return "both_flat"
    if bio_meaningful and not clean_meaningful:
        return "bio_drift_clean_flat"
    if clean_meaningful and not bio_meaningful:
        return "bio_flat_clean_drift"
    if math.copysign(1.0, biological_slope) == math.copysign(1.0, clean_slope):
        return "same_direction"
    return "opposite_direction"


def slope_magnitude_ratio(
    biological_slope: float | None,
    clean_slope: float | None,
) -> float | None:
    if not _has_meaningful_slope(biological_slope):
        return None
    if not _has_meaningful_slope(clean_slope):
        return None
    assert biological_slope is not None
    assert clean_slope is not None
    return abs(biological_slope) / abs(clean_slope)


def _has_meaningful_slope(value: float | None) -> bool:
    return value is not None and abs(value) >= SLOPE_EPSILON


def _to_float(value: str | None) -> float | None:
    if value is None or value == "":
        return None
    try:
        number = float(value)
    except ValueError:
        return None
    if not math.isfinite(number):
        return None
    return number


def _to_int(value: str | None) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(float(value))
    except ValueError:
        return None
