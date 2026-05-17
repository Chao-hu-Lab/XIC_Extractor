from __future__ import annotations

import math
from dataclasses import dataclass

from xic_extractor.peak_detection.boundaries import BoundaryHypothesis


@dataclass(frozen=True)
class BoundaryAuditScore:
    score: int
    support_labels: tuple[str, ...]
    concern_labels: tuple[str, ...]


def score_boundary_hypothesis(
    boundary: BoundaryHypothesis,
    reference: BoundaryHypothesis,
    *,
    baseline_score: float | None,
    trace_continuity: float | None,
) -> BoundaryAuditScore:
    score = 50
    support: list[str] = []
    concerns: list[str] = []

    if "candidate_interval" in boundary.sources:
        support.append("candidate_interval")

    baseline_delta, baseline_label = _baseline_signal_score(baseline_score)
    score += baseline_delta
    _append_label(baseline_label, support, concerns, baseline_delta)

    continuity_delta, continuity_label = _trace_continuity_score(trace_continuity)
    score += continuity_delta
    _append_label(continuity_label, support, concerns, continuity_delta)

    scan_delta, scan_label = _scan_support_score(boundary.scan_count)
    score += scan_delta
    _append_label(scan_label, support, concerns, scan_delta)

    width_delta, width_label = _width_stability_score(boundary, reference)
    score += width_delta
    _append_label(width_label, support, concerns, width_delta)

    return BoundaryAuditScore(
        score=max(0, min(100, int(round(score)))),
        support_labels=tuple(support),
        concern_labels=tuple(concerns),
    )


def _baseline_signal_score(value: float | None) -> tuple[int, str]:
    if value is None or not math.isfinite(value):
        return 0, "baseline_unavailable"
    if value >= 0.50:
        return 20, "baseline_supported"
    if value >= 0.20:
        return 5, "baseline_partial"
    return -20, "low_baseline_signal"


def _trace_continuity_score(value: float | None) -> tuple[int, str]:
    if value is None or not math.isfinite(value):
        return 0, "trace_continuity_unavailable"
    if value >= 0.75:
        return 15, "trace_continuity_ok"
    return -15, "low_trace_continuity"


def _scan_support_score(scan_count: int) -> tuple[int, str]:
    if scan_count >= 5:
        return 10, "scan_support_ok"
    if scan_count >= 3:
        return 5, "scan_support_minimal"
    return -15, "low_scan_support"


def _width_stability_score(
    boundary: BoundaryHypothesis,
    reference: BoundaryHypothesis,
) -> tuple[int, str]:
    if reference.width_min <= 0:
        return 0, "width_reference_unavailable"
    ratio = boundary.width_min / reference.width_min
    if 0.5 <= ratio <= 1.5:
        return 5, "width_near_candidate"
    if ratio < 0.25 or ratio > 2.0:
        return -10, "width_extreme"
    return 0, "width_shifted"


def _append_label(
    label: str,
    support: list[str],
    concerns: list[str],
    delta: int,
) -> None:
    if delta > 0:
        support.append(label)
    else:
        concerns.append(label)
