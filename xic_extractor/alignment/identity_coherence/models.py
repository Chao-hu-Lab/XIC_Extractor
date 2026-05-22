from __future__ import annotations

from dataclasses import dataclass

from .schema import (
    FragmentObservationMode,
    FragmentTagMatchPolicy,
    RequestCandidateIdentityStatus,
    RequestIdentityCompletenessStatus,
)


@dataclass(frozen=True)
class CidNeutralLossConstraint:
    cid_observed_loss_da: float | None
    cid_observed_loss_tolerance_ppm: float | None


@dataclass(frozen=True)
class FragmentIdentity:
    fragment_observation_mode: FragmentObservationMode | None
    precursor_mz: float | None
    product_mz: float | None
    fragment_tags: tuple[str, ...]
    fragment_tag_match_policy: FragmentTagMatchPolicy
    precursor_tolerance_ppm: float | None
    product_tolerance_ppm: float | None
    fragment_profile_id: str
    fragment_profile_hash: str
    mode_constraint: CidNeutralLossConstraint


@dataclass(frozen=True)
class IdentityCoherenceRequest:
    request_id: str
    decision_id: str
    seed_candidate_id: str
    seed_sample: str | None
    identity: FragmentIdentity
    request_identity_completeness_status: RequestIdentityCompletenessStatus
    request_candidate_identity_status: RequestCandidateIdentityStatus
    request_builder_flags: tuple[str, ...] = ()
