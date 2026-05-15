from __future__ import annotations

import csv
import math
from collections.abc import Iterable
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
    family_list = list(families)
    pairs: list[ArtificialAdductPair] = []
    for index, parent in enumerate(family_list):
        for related in family_list[index + 1 :]:
            rt_delta = abs(_family_rt(parent) - _family_rt(related))
            if rt_delta > rt_window_min:
                continue
            mz_delta_observed = abs(_family_mz(parent) - _family_mz(related))
            for adduct in adducts:
                error_ppm = _ppm_error(mz_delta_observed, adduct.mz_delta)
                if error_ppm <= mz_tolerance_ppm:
                    pairs.append(
                        ArtificialAdductPair(
                            parent_family_id=_family_id(parent),
                            related_family_id=_family_id(related),
                            adduct_name=adduct.adduct_name,
                            mz_delta_observed=mz_delta_observed,
                            mz_delta_error_ppm=error_ppm,
                            rt_delta_min=rt_delta,
                        )
                    )
    return tuple(pairs)


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
