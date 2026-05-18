from xic_extractor.peak_detection.region_mixture_diagnostic import (
    classify_local_mixture,
)
from xic_extractor.peak_detection.region_model_selection import (
    RegionSelectionDecision,
)


def test_adjacent_safe_merge_is_one_envelope_supported() -> None:
    diagnostic = classify_local_mixture(
        _decision(
            verdict="merge_suggested",
            source="adjacent_wis_local_minimum_merge",
            gap=0.04,
            area_ratio=1.08,
        )
    )

    assert diagnostic.label == "one_envelope_supported"
    assert "adjacent" in diagnostic.reason


def test_close_split_with_small_area_change_is_ambiguous_adjacent_split() -> None:
    diagnostic = classify_local_mixture(
        _decision(verdict="split_supported", gap=0.09, area_ratio=1.05)
    )

    assert diagnostic.label == "ambiguous_adjacent_split"


def test_wide_gap_split_is_two_peak_supported() -> None:
    diagnostic = classify_local_mixture(
        _decision(verdict="split_supported", gap=0.18, area_ratio=1.04)
    )

    assert diagnostic.label == "two_peak_supported"


def test_current_supported_maps_to_current_single_envelope() -> None:
    diagnostic = classify_local_mixture(_decision(verdict="current_supported"))

    assert diagnostic.label == "current_single_envelope"


def test_insufficient_evidence_stays_visible() -> None:
    diagnostic = classify_local_mixture(
        _decision(status="skipped_invalid_trace", verdict="insufficient_evidence")
    )

    assert diagnostic.label == "insufficient_evidence"


def _decision(
    *,
    status: str = "evaluated",
    verdict: str,
    source: str = "",
    gap: float | None = None,
    area_ratio: float | None = None,
) -> RegionSelectionDecision:
    return RegionSelectionDecision(
        shadow_status=status,
        shadow_verdict=verdict,
        merge_suggestion_source=source,
        selected_interval_count=2 if gap is not None else None,
        selected_interval_gap_max_min=gap,
        area_ratio=area_ratio,
    )
