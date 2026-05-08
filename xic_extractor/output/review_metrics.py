from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class TargetReviewMetrics:
    target: str
    total: int
    detected: int
    detected_percent: str
    flagged_rows: int
    flagged_percent: str
    ms2_nl_flags: int
    low_confidence_rows: int
    priority_counts: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class ReviewMetrics:
    sample_count: int
    target_count: int
    flagged_rows: int
    diagnostics_count: int
    detected_rows: int
    targets: dict[str, TargetReviewMetrics]
    heatmap: dict[tuple[str, str], str]


def build_review_metrics(
    rows: list[dict[str, str]],
    *,
    diagnostics: list[dict[str, str]],
    review_rows: list[dict[str, str]],
    count_no_ms2_as_detected: bool,
) -> ReviewMetrics:
    samples = _ordered_distinct(row.get("SampleName", "") for row in rows)
    targets = _ordered_distinct(row.get("Target", "") for row in rows)
    flagged_keys = {
        (row.get("Target", ""), row.get("Sample", "")) for row in review_rows
    }
    review_rows_by_target = _review_rows_by_target(review_rows)
    target_metrics: dict[str, TargetReviewMetrics] = {}
    heatmap: dict[tuple[str, str], str] = {}
    detected_rows = 0

    for target in targets:
        target_rows = [row for row in rows if row.get("Target", "") == target]
        detected = sum(
            1
            for row in target_rows
            if _is_detected(row, count_no_ms2_as_detected)
        )
        detected_rows += detected
        flagged_rows = len(review_rows_by_target.get(target, []))
        total = len(target_rows)
        target_metrics[target] = TargetReviewMetrics(
            target=target,
            total=total,
            detected=detected,
            detected_percent=_percent(detected, total),
            flagged_rows=flagged_rows,
            flagged_percent=_percent(flagged_rows, total),
            ms2_nl_flags=sum(1 for row in target_rows if _has_ms2_nl_flag(row)),
            low_confidence_rows=sum(
                1
                for row in target_rows
                if row.get("Confidence", "") in {"LOW", "VERY_LOW"}
            ),
            priority_counts=_priority_counts(review_rows_by_target.get(target, [])),
        )
        for sample in samples:
            row = next(
                (
                    item
                    for item in target_rows
                    if item.get("SampleName", "") == sample
                ),
                None,
            )
            if row is None:
                continue
            heatmap[(target, sample)] = _heatmap_state(
                row,
                is_flagged=(target, sample) in flagged_keys,
                count_no_ms2_as_detected=count_no_ms2_as_detected,
            )

    return ReviewMetrics(
        sample_count=len(samples),
        target_count=len(targets),
        flagged_rows=len(review_rows),
        diagnostics_count=len(diagnostics),
        detected_rows=detected_rows,
        targets=target_metrics,
        heatmap=heatmap,
    )


def _ordered_distinct(values) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


def _review_rows_by_target(
    review_rows: list[dict[str, str]],
) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in review_rows:
        grouped.setdefault(row.get("Target", ""), []).append(row)
    return grouped


def _priority_counts(review_rows: list[dict[str, str]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in review_rows:
        priority = row.get("Priority", "")
        if not priority:
            continue
        counts[priority] = counts.get(priority, 0) + 1
    return counts


def _heatmap_state(
    row: dict[str, str],
    *,
    is_flagged: bool,
    count_no_ms2_as_detected: bool,
) -> str:
    if _is_error(row):
        return "error"
    if not _is_detected(row, count_no_ms2_as_detected):
        return "not-detected"
    return "flagged-detected" if is_flagged else "clean-detected"


def _is_error(row: dict[str, str]) -> bool:
    return any(row.get(key, "") == "ERROR" for key in ("RT", "Area", "NL"))


def _is_detected(
    row: dict[str, str],
    count_no_ms2_as_detected: bool,
) -> bool:
    if _safe_float(row.get("RT", "")) is None:
        return False
    area = _safe_float(row.get("Area", ""))
    if area is None or area <= 0:
        return False
    if row.get("Confidence", "") == "VERY_LOW":
        return False
    nl = row.get("NL", "")
    if nl == "NO_MS2":
        return count_no_ms2_as_detected
    if nl == "NL_FAIL":
        return False
    return nl == "" or nl == "OK" or nl.startswith("WARN_")


def _has_ms2_nl_flag(row: dict[str, str]) -> bool:
    nl = row.get("NL", "")
    return nl in {"NL_FAIL", "NO_MS2"} or nl.startswith("WARN_")


def _percent(numerator: int, denominator: int) -> str:
    return f"{numerator / denominator * 100:.0f}%" if denominator else "0%"


def _safe_float(value: str) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
