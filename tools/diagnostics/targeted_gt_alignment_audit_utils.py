from __future__ import annotations

import math
from collections.abc import Iterable
from typing import Any

from tools.diagnostics.targeted_gt_alignment_audit_models import TargetGroundTruth


def _is_trueish(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "t", "yes", "y"}


def _to_int(value: object) -> int:
    parsed = _to_float(value)
    if parsed is None:
        return 0
    return int(parsed)


def _cell_rt(cell: dict[str, str] | None) -> float | None:
    if cell is None:
        return None
    return _to_float(cell.get("apex_rt")) or _to_float(cell.get("family_center_rt"))


def _rt_delta_sec(
    target: TargetGroundTruth,
    cell: dict[str, str] | None,
) -> float | None:
    if target.target_rt_min is None:
        return None
    rt = _cell_rt(cell)
    if rt is None:
        return None
    return (rt - target.target_rt_min) * 60.0


def _join_ids(values: Iterable[object]) -> str:
    return ";".join(sorted({str(value) for value in values if value}))


def _to_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def _format_float(value: float | None, places: int) -> str:
    if value is None:
        return ""
    return f"{value:.{places}f}"


def _is_numeric_text(value: str) -> bool:
    try:
        parsed = float(value)
    except ValueError:
        return False
    return math.isfinite(parsed)


def _unescape_excel_formula(value: object) -> str:
    if value is None:
        return ""
    text = str(value)
    if len(text) > 1 and text[0] == "'" and text[1] in "=+-@":
        return text[1:]
    return text
