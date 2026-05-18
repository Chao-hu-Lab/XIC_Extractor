from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from xic_extractor.peak_detection.region_model_selection import (
    RegionSelectionDecision,
)

LocalMixtureDiagnosticLabel = Literal[
    "insufficient_evidence",
    "current_single_envelope",
    "one_envelope_supported",
    "ambiguous_adjacent_split",
    "two_peak_supported",
    "competing_boundary_model",
]

AMBIGUOUS_ADJACENT_SPLIT_GAP_MAX_MIN = 0.12
AMBIGUOUS_ADJACENT_SPLIT_AREA_RATIO_MAX = 1.20


@dataclass(frozen=True)
class LocalMixtureDiagnostic:
    label: LocalMixtureDiagnosticLabel
    reason: str


def classify_local_mixture(
    decision: RegionSelectionDecision,
) -> LocalMixtureDiagnostic:
    if (
        decision.shadow_status != "evaluated"
        or decision.shadow_verdict == "insufficient_evidence"
    ):
        return LocalMixtureDiagnostic(
            label="insufficient_evidence",
            reason="region model did not have enough comparable evidence",
        )

    if decision.shadow_verdict == "current_supported":
        return LocalMixtureDiagnostic(
            label="current_single_envelope",
            reason="current selected interval is not contradicted by alternatives",
        )

    if (
        decision.shadow_verdict == "merge_suggested"
        and decision.merge_suggestion_source
        == "adjacent_wis_local_minimum_merge"
    ):
        return LocalMixtureDiagnostic(
            label="one_envelope_supported",
            reason="adjacent WIS local-minimum intervals support one envelope",
        )

    if decision.shadow_verdict == "split_supported":
        gap = decision.selected_interval_gap_max_min
        area_ratio = decision.area_ratio
        if (
            gap is not None
            and gap <= AMBIGUOUS_ADJACENT_SPLIT_GAP_MAX_MIN
            and (
                area_ratio is None
                or area_ratio <= AMBIGUOUS_ADJACENT_SPLIT_AREA_RATIO_MAX
            )
        ):
            return LocalMixtureDiagnostic(
                label="ambiguous_adjacent_split",
                reason=(
                    "WIS supports multiple intervals, but they remain adjacent "
                    "with small area change"
                ),
            )
        return LocalMixtureDiagnostic(
            label="two_peak_supported",
            reason="WIS supports separated intervals over one envelope",
        )

    return LocalMixtureDiagnostic(
        label="competing_boundary_model",
        reason="shadow evidence prefers a non-merge boundary or apex model",
    )
