from __future__ import annotations

import math
from typing import Any, cast

CWT_PROPOSAL_SOURCE = "centwave_cwt"
CWT_SAME_APEX_SUPPORT_POINTS = 5


def has_same_apex_cwt_support(candidate: Any) -> bool:
    sources = {str(source) for source in getattr(candidate, "proposal_sources", ())}
    if CWT_PROPOSAL_SOURCE not in sources:
        return False
    if not sources.difference({CWT_PROPOSAL_SOURCE}):
        return False
    return positive_finite_legacy_cwt_presence_metric(
        getattr(candidate, "cwt_best_scale", None)
    ) or positive_finite_legacy_cwt_presence_metric(
        getattr(candidate, "cwt_ridge_persistence", None)
    )


def positive_finite_legacy_cwt_presence_metric(value: object) -> bool:
    try:
        metric = float(cast(Any, value))
    except (TypeError, ValueError):
        return False
    return math.isfinite(metric) and metric > 0
