from __future__ import annotations

import csv
import math
from bisect import bisect_left, bisect_right
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ArtificialAdduct:
    adduct_id: str
    mz_delta: float
    adduct_name: str


@dataclass(frozen=True)
class ArtificialAdductPair:
    parent_family_id: str
    related_family_id: str
    adduct_name: str
    mz_delta_observed: float
    mz_delta_error_ppm: float
    rt_delta_min: float


@dataclass(frozen=True)
class _FamilySnapshot:
    index: int
    family_id: str
    mz: float
    rt: float


@dataclass(frozen=True)
class _IndexedAdduct:
    index: int
    adduct: ArtificialAdduct


def load_artificial_adducts(path: Path) -> list[ArtificialAdduct]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    adducts: list[ArtificialAdduct] = []
    for row_number, row in enumerate(rows, start=2):
        adducts.append(
            ArtificialAdduct(
                adduct_id=_required(row, "Artificial Adduct No.", row_number),
                mz_delta=_parse_float(row, "Artificial Adduct m/z", row_number),
                adduct_name=_required(row, "Artificial Adduct Name", row_number),
            )
        )
    return adducts


def match_artificial_adduct_pairs(
    families: Iterable[Any],
    adducts: Iterable[ArtificialAdduct],
    *,
    rt_window_min: float,
    mz_tolerance_ppm: float,
) -> tuple[ArtificialAdductPair, ...]:
    family_list = tuple(
        _snapshot_family(index, family) for index, family in enumerate(families)
    )
    indexed_adducts = tuple(
        _IndexedAdduct(index, adduct) for index, adduct in enumerate(adducts)
    )
    adducts_by_delta = tuple(
        sorted(
            indexed_adducts,
            key=lambda item: (item.adduct.mz_delta, item.index),
        )
    )
    adduct_deltas = tuple(item.adduct.mz_delta for item in adducts_by_delta)
    pairs: list[ArtificialAdductPair] = []
    for parent, related in _rt_candidate_pairs(
        family_list,
        rt_window_min=rt_window_min,
    ):
        rt_delta = abs(parent.rt - related.rt)
        mz_delta_observed = abs(parent.mz - related.mz)
        for indexed_adduct in _candidate_adducts(
            adducts_by_delta,
            adduct_deltas,
            observed_delta=mz_delta_observed,
            mz_tolerance_ppm=mz_tolerance_ppm,
        ):
            adduct = indexed_adduct.adduct
            error_ppm = _ppm_error(mz_delta_observed, adduct.mz_delta)
            pairs.append(
                ArtificialAdductPair(
                    parent_family_id=parent.family_id,
                    related_family_id=related.family_id,
                    adduct_name=adduct.adduct_name,
                    mz_delta_observed=mz_delta_observed,
                    mz_delta_error_ppm=error_ppm,
                    rt_delta_min=rt_delta,
                )
            )
    return tuple(pairs)


def _candidate_adducts(
    adducts_by_delta: Sequence[_IndexedAdduct],
    adduct_deltas: Sequence[float],
    *,
    observed_delta: float,
    mz_tolerance_ppm: float,
) -> tuple[_IndexedAdduct, ...]:
    tolerance_fraction = mz_tolerance_ppm * 1e-6
    if tolerance_fraction >= 1.0:
        candidates = adducts_by_delta
    else:
        lower = observed_delta / (1.0 + tolerance_fraction)
        upper = observed_delta / (1.0 - tolerance_fraction)
        start = bisect_left(adduct_deltas, lower)
        end = bisect_right(adduct_deltas, upper)
        candidates = adducts_by_delta[start:end]
    return tuple(
        sorted(
            (
                candidate
                for candidate in candidates
                if _ppm_error(observed_delta, candidate.adduct.mz_delta)
                <= mz_tolerance_ppm
            ),
            key=lambda candidate: candidate.index,
        )
    )


def _snapshot_family(index: int, family: Any) -> _FamilySnapshot:
    return _FamilySnapshot(
        index=index,
        family_id=_family_id(family),
        mz=_family_mz(family),
        rt=_family_rt(family),
    )


def _rt_candidate_pairs(
    families: Sequence[_FamilySnapshot],
    *,
    rt_window_min: float,
) -> Iterator[tuple[_FamilySnapshot, _FamilySnapshot]]:
    ordered = sorted(families, key=lambda family: family.rt)
    candidate_pairs: set[tuple[int, int]] = set()
    for left_index, left in enumerate(ordered):
        for right_index in range(left_index + 1, len(ordered)):
            right = ordered[right_index]
            if right.rt - left.rt > rt_window_min:
                break
            if left.index < right.index:
                candidate_pairs.add((left.index, right.index))
            else:
                candidate_pairs.add((right.index, left.index))
    for parent_index, related_index in sorted(candidate_pairs):
        yield families[parent_index], families[related_index]


def _required(row: dict[str, str], column: str, row_number: int) -> str:
    value = row.get(column, "").strip()
    if not value:
        raise ValueError(f"row {row_number}: {column} is required")
    return value


def _parse_float(row: dict[str, str], column: str, row_number: int) -> float:
    value = _required(row, column, row_number)
    try:
        parsed = float(value)
    except ValueError as exc:
        raise ValueError(
            f"row {row_number}: {column} must be a float: {value!r}"
        ) from exc
    if not math.isfinite(parsed) or parsed <= 0:
        raise ValueError(f"row {row_number}: {column} must be a positive finite value")
    return parsed


def _family_id(family: Any) -> str:
    if hasattr(family, "feature_family_id"):
        return str(family.feature_family_id)
    return str(family.cluster_id)


def _family_mz(family: Any) -> float:
    if hasattr(family, "family_center_mz"):
        return float(family.family_center_mz)
    return float(family.cluster_center_mz)


def _family_rt(family: Any) -> float:
    if hasattr(family, "family_center_rt"):
        return float(family.family_center_rt)
    return float(family.cluster_center_rt)


def _ppm_error(observed: float, expected: float) -> float:
    return abs(observed - expected) / expected * 1_000_000.0
