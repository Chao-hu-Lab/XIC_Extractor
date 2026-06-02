from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal, TypeAlias

from xic_extractor.alignment.edge_scoring import (
    DriftPriorSource,
    EdgeDecision,
    HardGateFailureReason,
    OwnerEdgeEvidence,
)

if TYPE_CHECKING:
    from xic_extractor.alignment.owner_clustering import OwnerAlignedFeature

CrossSamplePeakGroupEdgeRole: TypeAlias = Literal[
    "membership_support",
    "membership_challenge",
]
CrossSamplePeakGroupConstructionPolicy: TypeAlias = Literal[
    "none",
    "construction_time_hard_gate_observed",
]


@dataclass(frozen=True)
class CrossSamplePeakGroupEdgeFact:
    left_owner_id: str
    right_owner_id: str
    owner_pair_ids: tuple[str, str]
    decision: EdgeDecision
    role: CrossSamplePeakGroupEdgeRole
    failure_reason: HardGateFailureReason | Literal[""]
    rt_raw_delta_sec: float
    rt_drift_corrected_delta_sec: float | None
    drift_prior_source: DriftPriorSource
    injection_order_gap: int | None
    score: int
    reason: str
    construction_policy: CrossSamplePeakGroupConstructionPolicy = "none"
    source: str = "owner_edge_evidence_shadow"


@dataclass(frozen=True)
class CrossSamplePeakGroupHypothesis:
    group_hypothesis_id: str
    public_family_id: str
    owner_ids: tuple[str, ...]
    event_ids: tuple[str, ...]
    event_member_count: int
    source: str = "owner_aligned_feature_shadow"
    edge_facts: tuple[CrossSamplePeakGroupEdgeFact, ...] = ()


def cross_sample_peak_group_hypothesis_from_owner_feature(
    feature: OwnerAlignedFeature,
    *,
    edge_evidence: Sequence[OwnerEdgeEvidence] = (),
) -> CrossSamplePeakGroupHypothesis:
    event_ids = tuple(
        event_id
        for owner in feature.owners
        for event_id in owner.event_candidate_ids
    )
    return CrossSamplePeakGroupHypothesis(
        group_hypothesis_id=feature.feature_family_id,
        public_family_id=feature.feature_family_id,
        owner_ids=feature.event_cluster_ids,
        event_ids=event_ids,
        event_member_count=feature.event_member_count,
        edge_facts=cross_sample_peak_group_edge_facts_from_owner_edges(
            edge_evidence,
            owner_ids=feature.event_cluster_ids,
        ),
    )


def cross_sample_peak_group_edge_fact_from_owner_edge(
    edge: OwnerEdgeEvidence,
) -> CrossSamplePeakGroupEdgeFact:
    owner_pair_ids = (
        min(edge.left_owner_id, edge.right_owner_id),
        max(edge.left_owner_id, edge.right_owner_id),
    )
    return CrossSamplePeakGroupEdgeFact(
        left_owner_id=edge.left_owner_id,
        right_owner_id=edge.right_owner_id,
        owner_pair_ids=owner_pair_ids,
        decision=edge.decision,
        role=(
            "membership_support"
            if edge.decision == "strong_edge"
            else "membership_challenge"
        ),
        failure_reason=edge.failure_reason,
        rt_raw_delta_sec=edge.rt_raw_delta_sec,
        rt_drift_corrected_delta_sec=edge.rt_drift_corrected_delta_sec,
        drift_prior_source=edge.drift_prior_source,
        injection_order_gap=edge.injection_order_gap,
        score=edge.score,
        reason=edge.reason,
        construction_policy=(
            "construction_time_hard_gate_observed"
            if edge.decision == "blocked_edge"
            else "none"
        ),
    )


def cross_sample_peak_group_edge_facts_from_owner_edges(
    edges: Sequence[OwnerEdgeEvidence],
    *,
    owner_ids: Iterable[str] | None = None,
) -> tuple[CrossSamplePeakGroupEdgeFact, ...]:
    owner_id_set = frozenset(owner_ids) if owner_ids is not None else None
    return tuple(
        cross_sample_peak_group_edge_fact_from_owner_edge(edge)
        for edge in edges
        if owner_id_set is None
        or (
            edge.left_owner_id in owner_id_set
            and edge.right_owner_id in owner_id_set
        )
    )
