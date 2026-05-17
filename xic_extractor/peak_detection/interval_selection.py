from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class WeightedInterval:
    item_id: str
    left: float
    right: float
    weight: int
    selected_priority: int = 0
    candidate_interval_priority: int = 0


def select_weighted_nonoverlap_intervals(
    intervals: Sequence[WeightedInterval],
) -> tuple[WeightedInterval, ...]:
    if not intervals:
        return ()
    ordered = sorted(intervals, key=_sort_key)
    previous = _previous_nonoverlap_indices(ordered)
    best: list[tuple[int, int, int, int, tuple[int, ...]]] = [
        (0, 0, 0, 0, ())
        for _ in range(len(ordered) + 1)
    ]

    for one_based_index, interval in enumerate(ordered, start=1):
        include_base = best[previous[one_based_index - 1] + 1]
        include = (
            include_base[0] + interval.weight,
            include_base[1] + interval.selected_priority,
            include_base[2] + interval.candidate_interval_priority,
            include_base[3] + 1,
            (*include_base[4], one_based_index - 1),
        )
        exclude = best[one_based_index - 1]
        best[one_based_index] = (
            include
            if _weighted_key(include) > _weighted_key(exclude)
            else exclude
        )

    return tuple(ordered[index] for index in best[-1][4])


def _previous_nonoverlap_indices(intervals: Sequence[WeightedInterval]) -> list[int]:
    previous: list[int] = []
    for index, interval in enumerate(intervals):
        compatible = -1
        for candidate_index in range(index - 1, -1, -1):
            candidate = intervals[candidate_index]
            if candidate.right <= interval.left:
                compatible = candidate_index
                break
        previous.append(compatible)
    return previous


def _weighted_key(
    value: tuple[int, int, int, int, tuple[int, ...]],
) -> tuple[int, int, int, int, tuple[int, ...]]:
    score, selected_priority, candidate_interval_priority, count, indices = value
    return (
        score,
        selected_priority,
        candidate_interval_priority,
        count,
        tuple(-index for index in indices),
    )


def _sort_key(interval: WeightedInterval) -> tuple[float, float, int, int, int]:
    return (
        interval.right,
        interval.left,
        -interval.weight,
        -interval.selected_priority,
        -interval.candidate_interval_priority,
    )
