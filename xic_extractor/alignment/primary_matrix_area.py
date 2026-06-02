from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

MISSING_ASLS_PRIMARY_AREA = "missing_asls_primary_area"
ASLS_PRIMARY_MATRIX_AREA_SOURCE = "asls_baseline_corrected"


@dataclass(frozen=True)
class PrimaryMatrixAreaDecision:
    value: float | None
    source: str
    reason: str


def primary_matrix_area_from_integration(
    integration: Any | None,
) -> PrimaryMatrixAreaDecision:
    if integration is None:
        return PrimaryMatrixAreaDecision(
            value=None,
            source="",
            reason=MISSING_ASLS_PRIMARY_AREA,
        )
    if getattr(integration, "baseline_type", "") != "asls":
        return PrimaryMatrixAreaDecision(
            value=None,
            source="",
            reason=MISSING_ASLS_PRIMARY_AREA,
        )
    area = _valid_area(getattr(integration, "area_baseline_corrected", None))
    if area is None:
        return PrimaryMatrixAreaDecision(
            value=None,
            source="",
            reason=MISSING_ASLS_PRIMARY_AREA,
        )
    return PrimaryMatrixAreaDecision(
        value=area,
        source=ASLS_PRIMARY_MATRIX_AREA_SOURCE,
        reason="",
    )


def _valid_area(value: object) -> float | None:
    if (
        value is None
        or isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value <= 0
    ):
        return None
    return float(value)
