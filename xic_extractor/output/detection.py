from __future__ import annotations

from typing import Any


def is_accepted_row_detection(
    row: dict[str, str],
    count_no_ms2_as_detected: bool,
) -> bool:
    if _safe_float(row.get("RT", "")) is None:
        return False
    area = _safe_float(row.get("Area", ""))
    if area is None or area <= 0:
        return False
    return _is_accepted_confidence_and_nl(
        confidence=row.get("Confidence", ""),
        nl=row.get("NL", ""),
        count_no_ms2_as_detected=count_no_ms2_as_detected,
    )


def is_accepted_result_detection(
    result: Any,
    count_no_ms2_as_detected: bool,
) -> bool:
    if result.reported_rt is None:
        return False
    peak = result.peak_result.peak
    if peak is None or peak.area <= 0:
        return False
    return _is_accepted_confidence_and_nl(
        confidence=result.confidence,
        nl=result.nl_token or "",
        count_no_ms2_as_detected=count_no_ms2_as_detected,
    )


def _is_accepted_confidence_and_nl(
    *,
    confidence: str,
    nl: str,
    count_no_ms2_as_detected: bool,
) -> bool:
    if confidence == "VERY_LOW":
        return False
    if nl == "NO_MS2":
        return count_no_ms2_as_detected
    if nl == "NL_FAIL":
        return False
    return nl == "" or nl == "OK" or nl.startswith("WARN_")


def _safe_float(value: str) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
