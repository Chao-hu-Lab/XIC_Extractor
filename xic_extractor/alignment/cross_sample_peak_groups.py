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
CrossSamplePeakGroupReviewReason: TypeAlias = Literal[
    "identity_conflict",
    "ambiguous_owner",
    "review_only",
]
CrossSamplePeakGroupReviewRole: TypeAlias = Literal["review_only_challenge"]
CrossSamplePeakGroupHardGateRole: TypeAlias = Literal["split_gate_challenge"]


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
class CrossSamplePeakGroupReviewFact:
    feature_family_id: str
    public_family_id: str
    review_only: bool
    identity_conflict: bool
    ambiguous_sample_stem: str | None
    ambiguous_candidate_ids: tuple[str, ...]
    evidence: str
    reason: CrossSamplePeakGroupReviewReason
    role: CrossSamplePeakGroupReviewRole = "review_only_challenge"
    source: str = "owner_aligned_feature_review_shadow"


@dataclass(frozen=True)
class CrossSamplePeakGroupHardGateChallengeFact:
    left_owner_id: str
    right_owner_id: str
    owner_pair_ids: tuple[str, str]
    decision: EdgeDecision
    role: CrossSamplePeakGroupHardGateRole
    failure_reason: HardGateFailureReason | Literal[""]
    reason: str
    construction_policy: CrossSamplePeakGroupConstructionPolicy = (
        "construction_time_hard_gate_observed"
    )
    source: str = "owner_edge_hard_gate_shadow"


@dataclass(frozen=True)
class CrossSamplePeakGroupHypothesis:
    group_hypothesis_id: str
    public_family_id: str
    owner_ids: tuple[str, ...]
    event_ids: tuple[str, ...]
    event_member_count: int
    source: str = "owner_aligned_feature_shadow"
    edge_facts: tuple[CrossSamplePeakGroupEdgeFact, ...] = ()
    review_facts: tuple[CrossSamplePeakGroupReviewFact, ...] = ()
    hard_gate_challenge_facts: tuple[
        CrossSamplePeakGroupHardGateChallengeFact,
        ...
    ] = ()


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
    edge_facts = cross_sample_peak_group_edge_facts_from_owner_edges(
        edge_evidence,
        owner_ids=feature.event_cluster_ids,
    )
    review_fact = cross_sample_peak_group_review_fact_from_owner_feature(feature)
    review_facts = () if review_fact is None else (review_fact,)
    hard_gate_challenge_facts = (
        cross_sample_peak_group_hard_gate_challenge_facts_from_owner_edges(
            edge_evidence,
            owner_ids=feature.event_cluster_ids,
        )
    )
    return CrossSamplePeakGroupHypothesis(
        group_hypothesis_id=feature.feature_family_id,
        public_family_id=feature.feature_family_id,
        owner_ids=feature.event_cluster_ids,
        event_ids=event_ids,
        event_member_count=feature.event_member_count,
        edge_facts=edge_facts,
        review_facts=review_facts,
        hard_gate_challenge_facts=hard_gate_challenge_facts,
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


def cross_sample_peak_group_review_fact_from_owner_feature(
    feature: OwnerAlignedFeature,
) -> CrossSamplePeakGroupReviewFact | None:
    if not feature.review_only:
        return None

    reason: CrossSamplePeakGroupReviewReason
    if feature.identity_conflict:
        reason = "identity_conflict"
    elif feature.ambiguous_sample_stem is not None or feature.ambiguous_candidate_ids:
        reason = "ambiguous_owner"
    else:
        reason = "review_only"

    return CrossSamplePeakGroupReviewFact(
        feature_family_id=feature.feature_family_id,
        public_family_id=feature.feature_family_id,
        review_only=feature.review_only,
        identity_conflict=feature.identity_conflict,
        ambiguous_sample_stem=feature.ambiguous_sample_stem,
        ambiguous_candidate_ids=feature.ambiguous_candidate_ids,
        evidence=feature.evidence,
        reason=reason,
    )


def cross_sample_peak_group_hard_gate_challenge_fact_from_owner_edge(
    edge: OwnerEdgeEvidence,
) -> CrossSamplePeakGroupHardGateChallengeFact | None:
    if edge.decision != "blocked_edge":
        return None

    owner_pair_ids = (
        min(edge.left_owner_id, edge.right_owner_id),
        max(edge.left_owner_id, edge.right_owner_id),
    )
    return CrossSamplePeakGroupHardGateChallengeFact(
        left_owner_id=edge.left_owner_id,
        right_owner_id=edge.right_owner_id,
        owner_pair_ids=owner_pair_ids,
        decision=edge.decision,
        role="split_gate_challenge",
        failure_reason=edge.failure_reason,
        reason=edge.reason,
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
        if _edge_matches_owner_ids(edge, owner_id_set)
    )


def cross_sample_peak_group_hard_gate_challenge_facts_from_owner_edges(
    edges: Sequence[OwnerEdgeEvidence],
    *,
    owner_ids: Iterable[str] | None = None,
) -> tuple[CrossSamplePeakGroupHardGateChallengeFact, ...]:
    owner_id_set = frozenset(owner_ids) if owner_ids is not None else None
    facts: list[CrossSamplePeakGroupHardGateChallengeFact] = []
    for edge in edges:
        if not _edge_matches_owner_ids(edge, owner_id_set):
            continue
        fact = cross_sample_peak_group_hard_gate_challenge_fact_from_owner_edge(
            edge,
        )
        if fact is not None:
            facts.append(fact)
    return tuple(facts)


def _edge_matches_owner_ids(
    edge: OwnerEdgeEvidence,
    owner_id_set: frozenset[str] | None,
) -> bool:
    return owner_id_set is None or (
        edge.left_owner_id in owner_id_set
        and edge.right_owner_id in owner_id_set
    )
