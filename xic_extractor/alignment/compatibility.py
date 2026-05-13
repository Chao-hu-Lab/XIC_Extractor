from __future__ import annotations

import math
from typing import Protocol

from xic_extractor.alignment.models import AlignmentCluster, CandidateLike


class CompatibilityConfig(Protocol):
    @property
    def max_ppm(self) -> float: ...

    @property
    def max_rt_sec(self) -> float: ...

    @property
    def product_mz_tolerance_ppm(self) -> float: ...

    @property
    def observed_loss_tolerance_ppm(self) -> float: ...

    @property
    def fragmentation_model(self) -> str: ...


class CompatibilityCandidate(CandidateLike, Protocol):
    neutral_loss_tag: str


def are_candidates_compatible(
    existing: CompatibilityCandidate,
    candidate: CompatibilityCandidate,
    config: CompatibilityConfig,
) -> bool:
    _require_cid_model(config)
    return (
        existing.neutral_loss_tag == candidate.neutral_loss_tag
        and _ppm_distance_for_field(existing, candidate, "precursor_mz")
        <= _positive_config_number(config, "max_ppm")
        and rt_seconds_difference(existing, candidate)
        <= _positive_config_number(config, "max_rt_sec")
        and product_mz_is_compatible(
            existing,
            candidate,
            max_ppm=_positive_config_number(config, "product_mz_tolerance_ppm"),
        )
        and observed_loss_is_compatible(
            existing,
            candidate,
            max_ppm=_positive_config_number(config, "observed_loss_tolerance_ppm"),
        )
    )


def can_attach_to_cluster(
    cluster: AlignmentCluster,
    candidate: CompatibilityCandidate,
    config: CompatibilityConfig,
) -> bool:
    _require_cid_model(config)
    compatibility_set = _cluster_compatibility_members(cluster)
    if candidate.neutral_loss_tag != cluster.neutral_loss_tag:
        return False
    return all(
        are_candidates_compatible(anchor_or_primary, candidate, config)
        for anchor_or_primary in compatibility_set
    )


def ppm_distance(reference: float, observed: float) -> float:
    _require_finite_positive_number(reference, "reference")
    _require_finite_positive_number(observed, "observed")
    return abs(observed - reference) / reference * 1_000_000


def rt_seconds_difference(left: CandidateLike, right: CandidateLike) -> float:
    return abs(_candidate_rt_min(left) - _candidate_rt_min(right)) * 60.0


def product_mz_is_compatible(
    existing: CandidateLike,
    candidate: CandidateLike,
    *,
    max_ppm: float,
) -> bool:
    return _ppm_distance_for_field(existing, candidate, "product_mz") <= max_ppm


def observed_loss_is_compatible(
    existing: CandidateLike,
    candidate: CandidateLike,
    *,
    max_ppm: float,
) -> bool:
    return (
        _ppm_distance_for_field(existing, candidate, "observed_neutral_loss_da")
        <= max_ppm
    )


def _candidate_rt_min(candidate: CandidateLike) -> float:
    rt = _optional_number(candidate, "ms1_apex_rt")
    if rt is None:
        rt = _optional_number(candidate, "best_seed_rt")
    if rt is None:
        raise ValueError(
            "compatibility candidate field 'ms1_apex_rt' or 'best_seed_rt' "
            "must provide finite retention time",
        )
    return rt


def _require_cid_model(config: CompatibilityConfig) -> None:
    if config.fragmentation_model != "cid_nl":
        raise ValueError('fragmentation_model must be "cid_nl" in v1')


def _cluster_compatibility_members(
    cluster: AlignmentCluster,
) -> tuple[CandidateLike, ...]:
    if not cluster.has_anchor:
        return cluster.members
    if not cluster.anchor_members:
        raise ValueError("compatibility anchored cluster requires anchor_members")
    return cluster.anchor_members


def _ppm_distance_for_field(
    existing: CandidateLike,
    candidate: CandidateLike,
    field: str,
) -> float:
    return ppm_distance(
        _positive_number(existing, field),
        _positive_number(candidate, field),
    )


def _positive_number(owner: object, field: str) -> float:
    try:
        value = getattr(owner, field)
    except AttributeError as exc:
        raise ValueError(
            f"compatibility candidate field '{field}' is required",
        ) from exc
    _require_finite_positive_number(value, field)
    return value


def _positive_config_number(owner: object, field: str) -> float:
    try:
        value = getattr(owner, field)
    except AttributeError as exc:
        raise ValueError(
            f"compatibility config field '{field}' is required",
        ) from exc
    _require_finite_positive_number(value, field, owner="config")
    return value


def _optional_number(owner: object, field: str) -> float | None:
    try:
        value = getattr(owner, field)
    except AttributeError as exc:
        raise ValueError(
            f"compatibility candidate field '{field}' is required",
        ) from exc
    if value is None:
        return None
    _require_finite_number(value, field)
    return value


def _require_finite_positive_number(
    value: object,
    field: str,
    *,
    owner: str = "candidate",
) -> None:
    number = _require_finite_number(value, field, owner=owner)
    if number <= 0:
        raise ValueError(
            f"compatibility {owner} field '{field}' must be positive",
        )


def _require_finite_number(
    value: object,
    field: str,
    *,
    owner: str = "candidate",
) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(
            f"compatibility {owner} field '{field}' must be numeric",
        )
    if not math.isfinite(value):
        raise ValueError(
            f"compatibility {owner} field '{field}' must be finite",
        )
    return float(value)
