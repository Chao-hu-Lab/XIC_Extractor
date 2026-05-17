from xic_extractor.peak_detection.interval_selection import (
    WeightedInterval,
    select_weighted_nonoverlap_intervals,
)


def test_weighted_interval_selection_prefers_best_total_score() -> None:
    selected = select_weighted_nonoverlap_intervals(
        (
            WeightedInterval("wide", left=8.0, right=8.4, weight=60),
            WeightedInterval("left", left=8.0, right=8.2, weight=40),
            WeightedInterval("right", left=8.2, right=8.4, weight=40),
        )
    )

    assert tuple(interval.item_id for interval in selected) == ("left", "right")


def test_weighted_interval_selection_allows_touching_intervals() -> None:
    selected = select_weighted_nonoverlap_intervals(
        (
            WeightedInterval("left", left=8.0, right=8.2, weight=40),
            WeightedInterval("right", left=8.2, right=8.4, weight=40),
        )
    )

    assert tuple(interval.item_id for interval in selected) == ("left", "right")


def test_weighted_interval_selection_tie_prefers_priority() -> None:
    selected = select_weighted_nonoverlap_intervals(
        (
            WeightedInterval("plain", left=8.0, right=8.4, weight=80),
            WeightedInterval(
                "selected",
                left=8.0,
                right=8.4,
                weight=80,
                selected_priority=1,
            ),
        )
    )

    assert tuple(interval.item_id for interval in selected) == ("selected",)
