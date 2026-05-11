from __future__ import annotations

import math
from dataclasses import dataclass
from statistics import median
from typing import Protocol

ClusterCenter = tuple[float, float, float, float, bool]


class CandidateLike(Protocol):
    precursor_mz: float
    product_mz: float
    observed_neutral_loss_da: float
    ms1_apex_rt: float | None
    best_seed_rt: float | None


@dataclass(frozen=True)
class AlignmentCluster:
    cluster_id: str
    neutral_loss_tag: str
    cluster_center_mz: float
    cluster_center_rt: float
    cluster_product_mz: float
    cluster_observed_neutral_loss_da: float
    has_anchor: bool
    members: tuple[CandidateLike, ...]
    anchor_members: tuple[CandidateLike, ...] = ()


def build_alignment_cluster(
    *,
    cluster_id: str,
    neutral_loss_tag: str,
    members: tuple[CandidateLike, ...],
    anchor_members: tuple[CandidateLike, ...] = (),
) -> AlignmentCluster:
    center_mz, center_rt, product_mz, observed_loss, has_anchor = (
        calculate_alignment_cluster_center(members, anchor_members=anchor_members)
    )
    return AlignmentCluster(
        cluster_id=cluster_id,
        neutral_loss_tag=neutral_loss_tag,
        cluster_center_mz=center_mz,
        cluster_center_rt=center_rt,
        cluster_product_mz=product_mz,
        cluster_observed_neutral_loss_da=observed_loss,
        has_anchor=has_anchor,
        members=tuple(members),
        anchor_members=tuple(anchor_members),
    )


def calculate_alignment_cluster_center(
    members: tuple[CandidateLike, ...],
    *,
    anchor_members: tuple[CandidateLike, ...] = (),
) -> ClusterCenter:
    contributors = _center_contributors(members, anchor_members)
    return (
        median(candidate.precursor_mz for candidate in contributors),
        median(_candidate_rt(candidate) for candidate in contributors),
        median(candidate.product_mz for candidate in contributors),
        median(candidate.observed_neutral_loss_da for candidate in contributors),
        bool(anchor_members),
    )


def _center_contributors(
    members: tuple[CandidateLike, ...],
    anchor_members: tuple[CandidateLike, ...],
) -> tuple[CandidateLike, ...]:
    if not members:
        raise ValueError("Alignment cluster center requires at least one member")
    if anchor_members:
        member_ids = {id(member) for member in members}
        if any(id(anchor) not in member_ids for anchor in anchor_members):
            raise ValueError("Alignment cluster anchor_members must be members")
        return tuple(anchor_members)
    return tuple(members)


def _candidate_rt(candidate: CandidateLike) -> float:
    if candidate.ms1_apex_rt is not None:
        rt = candidate.ms1_apex_rt
    else:
        rt = candidate.best_seed_rt
    if rt is None or not math.isfinite(rt):
        raise ValueError("Alignment cluster center requires finite retention time")
    return rt
