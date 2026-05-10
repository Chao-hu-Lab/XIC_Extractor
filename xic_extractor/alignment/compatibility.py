from __future__ import annotations

import math
from typing import Protocol

from xic_extractor.alignment.models import AlignmentCluster, CandidateLike


class CompatibilityConfig(Protocol):
    max_ppm: float
    max_rt_sec: float
    product_mz_tolerance_ppm: float
    observed_loss_tolerance_ppm: float
    fragmentation_model: str


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
        and ppm_distance(existing.precursor_mz, candidate.precursor_mz) <= config.max_ppm
        and rt_seconds_difference(existing, candidate) <= config.max_rt_sec
        and product_mz_is_compatible(
            existing,
            candidate,
            max_ppm=config.product_mz_tolerance_ppm,
        )
        and observed_loss_is_compatible(
            existing,
            candidate,
            max_ppm=config.observed_loss_tolerance_ppm,
        )
    )


def can_attach_to_cluster(
    cluster: AlignmentCluster,
    candidate: CompatibilityCandidate,
    config: CompatibilityConfig,
    *,
    anchor_members: tuple[CompatibilityCandidate, ...] = (),
) -> bool:
    _require_cid_model(config)
    compatibility_set = anchor_members or cluster.members
    if candidate.neutral_loss_tag != cluster.neutral_loss_tag:
        return False
    return all(
        are_candidates_compatible(anchor_or_primary, candidate, config)
        for anchor_or_primary in compatibility_set
    )


def ppm_distance(reference: float, observed: float) -> float:
    if not _is_finite_positive(reference) or not math.isfinite(observed):
        raise ValueError("ppm distance requires finite values and positive reference")
    return abs(observed - reference) / reference * 1_000_000


def rt_seconds_difference(left: CandidateLike, right: CandidateLike) -> float:
    return abs(_candidate_rt_min(left) - _candidate_rt_min(right)) * 60.0


def product_mz_is_compatible(
    existing: CandidateLike,
    candidate: CandidateLike,
    *,
    max_ppm: float,
) -> bool:
    return ppm_distance(existing.product_mz, candidate.product_mz) <= max_ppm


def observed_loss_is_compatible(
    existing: CandidateLike,
    candidate: CandidateLike,
    *,
    max_ppm: float,
) -> bool:
    return (
        ppm_distance(
            existing.observed_neutral_loss_da,
            candidate.observed_neutral_loss_da,
        )
        <= max_ppm
    )


def _candidate_rt_min(candidate: CandidateLike) -> float:
    rt = candidate.ms1_apex_rt
    if rt is None:
        rt = candidate.best_seed_rt
    if rt is None or not math.isfinite(rt):
        raise ValueError("Compatibility requires finite retention time")
    return rt


def _is_finite_positive(value: float) -> bool:
    return not isinstance(value, bool) and math.isfinite(value) and value > 0


def _require_cid_model(config: CompatibilityConfig) -> None:
    if config.fragmentation_model != "cid_nl":
        raise ValueError('fragmentation_model must be "cid_nl" in v1')
