from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Literal

ReviewPriority = Literal["HIGH", "MEDIUM", "LOW"]


@dataclass(frozen=True)
class AlignmentConfig:
    preferred_ppm: float = 20.0
    max_ppm: float = 50.0
    preferred_rt_sec: float = 60.0
    max_rt_sec: float = 180.0
    product_mz_tolerance_ppm: float = 20.0
    observed_loss_tolerance_ppm: float = 20.0
    mz_bucket_neighbor_radius: int = 2
    anchor_priorities: tuple[ReviewPriority, ...] = ("HIGH",)
    anchor_min_evidence_score: int = 60
    anchor_min_seed_events: int = 2
    anchor_min_scan_support_score: float = 0.5
    rt_unit: Literal["min"] = "min"
    fragmentation_model: Literal["cid_nl"] = "cid_nl"

    def __post_init__(self) -> None:
        _require_positive("preferred_ppm", self.preferred_ppm)
        _require_positive("max_ppm", self.max_ppm)
        _require_at_most("preferred_ppm", self.preferred_ppm, "max_ppm", self.max_ppm)
        _require_positive("preferred_rt_sec", self.preferred_rt_sec)
        _require_positive("max_rt_sec", self.max_rt_sec)
        _require_at_most(
            "preferred_rt_sec",
            self.preferred_rt_sec,
            "max_rt_sec",
            self.max_rt_sec,
        )
        _require_positive("product_mz_tolerance_ppm", self.product_mz_tolerance_ppm)
        _require_positive(
            "observed_loss_tolerance_ppm",
            self.observed_loss_tolerance_ppm,
        )
        _require_positive_int(
            "mz_bucket_neighbor_radius",
            self.mz_bucket_neighbor_radius,
        )

        _require_anchor_priorities(self.anchor_priorities)
        _require_int_range(
            "anchor_min_evidence_score",
            self.anchor_min_evidence_score,
            0,
            100,
        )
        _require_positive_int("anchor_min_seed_events", self.anchor_min_seed_events)
        _require_numeric_range(
            "anchor_min_scan_support_score",
            self.anchor_min_scan_support_score,
            0,
            1,
        )
        if self.rt_unit != "min":
            raise ValueError('rt_unit must be "min" in v1')
        if self.fragmentation_model != "cid_nl":
            raise ValueError('fragmentation_model must be "cid_nl" in v1')


def _require_positive(name: str, value: float) -> None:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value <= 0
    ):
        raise ValueError(f"{name} must be finite and positive")


def _require_positive_int(name: str, value: int) -> None:
    if type(value) is not int or value < 1:
        raise ValueError(f"{name} must be an integer >= 1")


def _require_anchor_priorities(value: tuple[ReviewPriority, ...]) -> None:
    valid_priorities = {"HIGH", "MEDIUM", "LOW"}
    if (
        type(value) is not tuple
        or not value
        or any(priority not in valid_priorities for priority in value)
    ):
        raise ValueError("anchor_priorities must be a non-empty tuple of valid values")


def _require_int_range(name: str, value: int, minimum: int, maximum: int) -> None:
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError(f"{name} must be an integer between {minimum} and {maximum}")


def _require_numeric_range(
    name: str,
    value: float,
    minimum: float,
    maximum: float,
) -> None:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or not minimum <= value <= maximum
    ):
        raise ValueError(f"{name} must be finite numeric between {minimum} and {maximum}")


def _require_at_most(
    preferred_name: str,
    preferred_value: float,
    max_name: str,
    max_value: float,
) -> None:
    if preferred_value > max_value:
        raise ValueError(f"{preferred_name} must be <= {max_name}")
