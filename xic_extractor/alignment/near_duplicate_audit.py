from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations


@dataclass(frozen=True)
class AlignmentNearDuplicateInput:
    row_id: str
    neutral_loss_tag: str
    mz: float
    rt: float
    product_mz: float
    observed_neutral_loss_da: float
    present_samples: frozenset[str]


@dataclass(frozen=True)
class NearDuplicatePair:
    left_id: str
    right_id: str
    shared_count: int
    overlap_coefficient: float
    jaccard: float
    mz_ppm: float
    rt_sec: float


@dataclass(frozen=True)
class NearDuplicateSummary:
    near_pair_count: int
    high_shared_pair_count: int
    top_pairs: tuple[NearDuplicatePair, ...]


def count_near_duplicate_pairs(
    rows: tuple[AlignmentNearDuplicateInput, ...],
    *,
    mz_ppm: float,
    rt_sec: float,
    product_ppm: float,
    observed_loss_ppm: float,
    min_shared_samples: int,
    min_overlap: float,
) -> NearDuplicateSummary:
    pairs: list[NearDuplicatePair] = []
    for left, right in combinations(rows, 2):
        if left.neutral_loss_tag != right.neutral_loss_tag:
            continue
        mz_distance = _ppm(left.mz, right.mz)
        rt_distance = abs(left.rt - right.rt) * 60.0
        if mz_distance > mz_ppm or rt_distance > rt_sec:
            continue
        if _ppm(left.product_mz, right.product_mz) > product_ppm:
            continue
        if (
            _ppm(left.observed_neutral_loss_da, right.observed_neutral_loss_da)
            > observed_loss_ppm
        ):
            continue
        shared = left.present_samples & right.present_samples
        union = left.present_samples | right.present_samples
        denominator = min(len(left.present_samples), len(right.present_samples))
        overlap = len(shared) / denominator if denominator else 0.0
        jaccard = len(shared) / len(union) if union else 0.0
        if len(shared) >= min_shared_samples and overlap >= min_overlap:
            pairs.append(
                NearDuplicatePair(
                    left_id=left.row_id,
                    right_id=right.row_id,
                    shared_count=len(shared),
                    overlap_coefficient=overlap,
                    jaccard=jaccard,
                    mz_ppm=mz_distance,
                    rt_sec=rt_distance,
                ),
            )

    sorted_pairs = tuple(
        sorted(
            pairs,
            key=lambda pair: (
                -pair.shared_count,
                -pair.overlap_coefficient,
                pair.mz_ppm,
                pair.rt_sec,
                pair.left_id,
                pair.right_id,
            ),
        ),
    )
    return NearDuplicateSummary(
        near_pair_count=len(pairs),
        high_shared_pair_count=sum(
            1 for pair in pairs if pair.shared_count >= min_shared_samples
        ),
        top_pairs=sorted_pairs[:20],
    )


def _ppm(left: float, right: float) -> float:
    return abs(left - right) / max(abs(left), 1e-12) * 1_000_000.0
