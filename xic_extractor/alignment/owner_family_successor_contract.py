from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal, TypeAlias

from xic_extractor.alignment.cross_sample_peak_groups import (
    CrossSamplePeakGroupEdgeFact,
    cross_sample_peak_group_edge_facts_from_owner_edges,
    cross_sample_peak_group_hypothesis_from_owner_feature,
)
from xic_extractor.alignment.edge_scoring import OwnerEdgeEvidence
from xic_extractor.alignment.owner_clustering import OwnerAlignedFeature

OwnerFamilyInvariant: TypeAlias = Literal[
    "stable_cross_sample_family_membership",
    "owner_edge_evidence_projection",
    "complete_link_edge_semantics",
    "hard_family_split_gates",
    "review_only_owner_records",
    "backfill_seed_and_matrix_delivery",
]
OwnerFamilyInvariantDisposition: TypeAlias = Literal[
    "successor_owned",
    "successor_gap",
    "active_policy",
    "internal_constructor_candidate",
    "compatibility_adapter_candidate",
    "retirement_candidate_after_parity",
]
OwnerClusteringDisposition: TypeAlias = Literal[
    "keep_as_stage",
    "internal_constructor_candidate",
    "compatibility_adapter_candidate",
    "retirement_candidate_after_parity",
]

OWNER_FAMILY_INVARIANTS: tuple[OwnerFamilyInvariant, ...] = (
    "stable_cross_sample_family_membership",
    "owner_edge_evidence_projection",
    "complete_link_edge_semantics",
    "hard_family_split_gates",
    "review_only_owner_records",
    "backfill_seed_and_matrix_delivery",
)


@dataclass(frozen=True)
class OwnerFamilyInvariantMapping:
    invariant: OwnerFamilyInvariant
    current_owner: str
    current_state: str
    successor_surface: str
    disposition: OwnerFamilyInvariantDisposition
    public_oracle: str
    exit_rule: str


@dataclass(frozen=True)
class OwnerClusteringDispositionDecision:
    disposition: OwnerClusteringDisposition
    reason: str
    blocking_invariants: tuple[OwnerFamilyInvariant, ...]
    exit_rule: str


def owner_family_successor_mapping(
    feature: OwnerAlignedFeature,
    *,
    edge_evidence: Sequence[OwnerEdgeEvidence] | None = None,
) -> tuple[OwnerFamilyInvariantMapping, ...]:
    """Project current owner-family semantics onto the successor-spine contract.

    This is intentionally a read-only migration guard. It does not replace
    ``cluster_sample_local_owners`` or participate in matrix construction, and
    it should be updated once a successor cross-sample family spine owns these
    invariants.
    """

    review_state = (
        "review_only_present"
        if _feature_has_review_only_state(feature)
        else "review_only_supported_by_stage"
    )
    projected_edge_facts = cross_sample_peak_group_edge_facts_from_owner_edges(
        edge_evidence or (),
        owner_ids=feature.event_cluster_ids,
    )
    peak_group = cross_sample_peak_group_hypothesis_from_owner_feature(
        feature,
        edge_evidence=edge_evidence or (),
    )
    return (
        OwnerFamilyInvariantMapping(
            invariant="stable_cross_sample_family_membership",
            current_owner="OwnerAlignedFeature.feature_family_id / owners",
            current_state=(
                f"group_hypothesis_id={peak_group.group_hypothesis_id};"
                f"public_family_id={peak_group.public_family_id};"
                f"owner_count={len(peak_group.owner_ids)};"
                f"owner_ids={';'.join(peak_group.owner_ids)};"
                f"event_ids={';'.join(peak_group.event_ids)};"
                f"event_member_count={peak_group.event_member_count};"
                f"source={peak_group.source}"
            ),
            successor_surface="CrossSamplePeakGroupHypothesis shadow projection",
            disposition="successor_owned",
            public_oracle=(
                "tests/test_alignment_owner_family_successor_contract.py::"
                "test_cross_sample_peak_group_hypothesis_projects_owner_membership"
            ),
            exit_rule=(
                "C6-A1 owns only shadow identity and membership parity. Keep "
                "owner_clustering.py active until complete-link edge semantics, "
                "hard split gates, review-only records, and backfill/matrix "
                "delivery are successor-owned with alignment_matrix.tsv, "
                "alignment_cells.tsv, and alignment_review.tsv parity."
            ),
        ),
        OwnerFamilyInvariantMapping(
            invariant="owner_edge_evidence_projection",
            current_owner=(
                "owner_clustering.cluster_sample_local_owners / "
                "edge_scoring.evaluate_owner_edge / edge_evidence_sink"
            ),
            current_state=_edge_fact_state(feature, projected_edge_facts),
            successor_surface=(
                "CrossSamplePeakGroupEdgeFact shadow projection"
                if projected_edge_facts
                else "future_edge_evidence_projection"
            ),
            disposition=(
                "successor_owned" if projected_edge_facts else "active_policy"
            ),
            public_oracle=(
                "tests/test_alignment_owner_clustering.py::"
                "test_owner_clustering_does_not_bridge_three_owner_complete_link_group"
                if not projected_edge_facts
                else "tests/test_alignment_owner_family_successor_contract.py::"
                "test_strong_owner_edge_projects_support_fact_and_marks_successor_owned"
            ),
            exit_rule=(
                "Project owner edge evidence into successor-visible facts "
                "before using it as migration evidence."
                if not projected_edge_facts
                else "C6-A2 owns only shadow projection of current owner edge "
                "facts. Complete-link construction policy, hard gates, "
                "review-only owner records, and backfill/matrix delivery keep "
                "their existing live dispositions until later parity proves "
                "migration."
            ),
        ),
        OwnerFamilyInvariantMapping(
            invariant="complete_link_edge_semantics",
            current_owner=(
                "owner_clustering.cluster_sample_local_owners / "
                "all-pairs strong-edge complete-link rule"
            ),
            current_state=(
                f"family_evidence={feature.evidence};"
                f"shadow_edge_fact_count={len(projected_edge_facts)}"
            ),
            successor_surface="future_complete_link_membership_policy",
            disposition="active_policy",
            public_oracle=(
                "tests/test_alignment_owner_clustering.py::"
                "test_owner_clustering_does_not_bridge_three_owner_complete_link_group"
            ),
            exit_rule=(
                "A2 projects edge evidence facts only. Preserve the complete-link "
                "all-strong-pair grouping policy as active owner-clustering "
                "policy until successor tests can construct the same families "
                "and prove matrix/cells/review parity."
            ),
        ),
        OwnerFamilyInvariantMapping(
            invariant="hard_family_split_gates",
            current_owner="owner_clustering._group_can_pass_hard_gates",
            current_state=(
                f"neutral_loss_tag={feature.neutral_loss_tag};"
                f"product_mz={feature.family_product_mz};"
                f"observed_loss={feature.family_observed_neutral_loss_da}"
            ),
            successor_surface="future_family_split_policy",
            disposition="active_policy",
            public_oracle=(
                "tests/test_alignment_owner_clustering.py::"
                "test_owner_clustering_rejects_product_or_observed_loss_conflict"
            ),
            exit_rule=(
                "Preserve same-sample, neutral-loss, precursor, product, and "
                "observed-loss split gates in successor tests before migration."
            ),
        ),
        OwnerFamilyInvariantMapping(
            invariant="review_only_owner_records",
            current_owner=(
                "OwnerAlignedFeature.review_only / identity_conflict / "
                "ambiguous owner fields"
            ),
            current_state=review_state,
            successor_surface="future_review_only_family_projection",
            disposition="active_policy",
            public_oracle=(
                "tests/test_alignment_owner_clustering.py::"
                "test_ambiguous_records_become_review_only_features_without_owners"
            ),
            exit_rule=(
                "Successor projection must carry review-only families and "
                "ambiguous cells without contaminating production matrix rows."
            ),
        ),
        OwnerFamilyInvariantMapping(
            invariant="backfill_seed_and_matrix_delivery",
            current_owner=(
                "OwnerAlignedFeature.family_center_* / backfill_seed_centers / "
                "confirm_local_owners_with_backfill"
            ),
            current_state=(
                f"seed_center_count={len(feature.backfill_seed_centers)};"
                f"confirm_local_owners_with_backfill="
                f"{feature.confirm_local_owners_with_backfill}"
            ),
            successor_surface="future_matrix_delivery_adapter",
            disposition="successor_gap",
            public_oracle=(
                "tests/test_alignment_owner_matrix.py::"
                "test_owner_matrix_uses_backfill_confirmation_for_severe_low_local_owner"
            ),
            exit_rule=(
                "Successor migration must prove owner-backfill seed behavior, "
                "detected/rescued/ambiguous/absent cell delivery, and public "
                "writer parity before OwnerAlignedFeature becomes adapter-only."
            ),
        ),
    )


def owner_clustering_disposition(
    mappings: tuple[OwnerFamilyInvariantMapping, ...],
) -> OwnerClusteringDispositionDecision:
    blocking = tuple(
        mapping.invariant
        for mapping in mappings
        if mapping.disposition in {"successor_gap", "active_policy"}
    )
    if blocking:
        return OwnerClusteringDispositionDecision(
            disposition="keep_as_stage",
            reason=(
                "The successor spine does not yet own every writer-visible "
                "owner-family invariant."
            ),
            blocking_invariants=blocking,
            exit_rule=(
                "Promote only after successor family tests own the blocking "
                "invariants and alignment_matrix.tsv, alignment_cells.tsv, and "
                "alignment_review.tsv parity is proven."
            ),
        )

    if all(mapping.disposition == "successor_owned" for mapping in mappings):
        return OwnerClusteringDispositionDecision(
            disposition="retirement_candidate_after_parity",
            reason="All owner-family invariants are successor-owned.",
            blocking_invariants=(),
            exit_rule=(
                "Delete or adapt the stage only in a later cleanup goal after "
                "public writer parity and compatibility migration are proven."
            ),
        )

    return OwnerClusteringDispositionDecision(
        disposition="compatibility_adapter_candidate",
        reason=(
            "Owner-family invariants have successor coverage but still need "
            "an old shape."
        ),
        blocking_invariants=(),
        exit_rule=(
            "Keep a thin adapter until public consumers no longer require "
            "OwnerAlignedFeature-compatible fields."
        ),
    )


def _feature_has_review_only_state(feature: OwnerAlignedFeature) -> bool:
    return (
        feature.review_only
        or feature.identity_conflict
        or feature.ambiguous_sample_stem is not None
        or bool(feature.ambiguous_candidate_ids)
    )


def _edge_fact_state(
    feature: OwnerAlignedFeature,
    edge_facts: tuple[CrossSamplePeakGroupEdgeFact, ...],
) -> str:
    if not edge_facts:
        return f"family_evidence={feature.evidence};edge_fact_count=0"

    support_count = sum(
        1 for fact in edge_facts if fact.role == "membership_support"
    )
    challenge_count = sum(
        1 for fact in edge_facts if fact.role == "membership_challenge"
    )
    blocked_count = sum(
        1 for fact in edge_facts if fact.decision == "blocked_edge"
    )
    edge_pairs = ";".join(
        (
            f"{fact.owner_pair_ids[0]}|{fact.owner_pair_ids[1]}:"
            f"{fact.role}:{fact.decision}:{fact.failure_reason or 'none'}"
        )
        for fact in edge_facts
    )
    return (
        f"family_evidence={feature.evidence};"
        f"edge_fact_count={len(edge_facts)};"
        f"support_count={support_count};"
        f"challenge_count={challenge_count};"
        f"blocked_count={blocked_count};"
        f"edge_pairs={edge_pairs}"
    )
