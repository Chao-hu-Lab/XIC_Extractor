from __future__ import annotations

from dataclasses import dataclass

from .schema import (
    EvidenceStage,
    FragmentObservationMode,
    FragmentTagMatchPolicy,
    RequestCandidateIdentityStatus,
    RequestIdentityCompletenessStatus,
    SeedGateClass,
    SeedRejectReason,
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


@dataclass(frozen=True)
class CandidateIdentityMatch:
    request_candidate_identity_status: RequestCandidateIdentityStatus
    precursor_error_ppm: float | None
    product_error_ppm: float | None
    cid_observed_loss_error_ppm: float | None
    cid_observed_loss_error_da: float | None
    missing_fields: tuple[str, ...] = ()
    mismatch_fields: tuple[str, ...] = ()
    fragment_tags_supported: tuple[str, ...] = ()


@dataclass(frozen=True)
class SeedCandidateEvidence:
    candidate_id: str
    precursor_mz: float | None
    product_mz: float | None
    cid_observed_loss_da: float | None
    fragment_tags: tuple[str, ...]
    best_seed_rt: float | None
    ms1_scan_support_score: float | None
    evidence_stage: EvidenceStage = EvidenceStage.PRE_BACKFILL


@dataclass(frozen=True)
class SeedGateConfig:
    min_ms1_scan_support_score: float = 0.50
    require_seed_rt_inside_owner_peak: bool = True


@dataclass(frozen=True)
class SeedGateResult:
    resolved_request: IdentityCoherenceRequest
    seed_gate_class: SeedGateClass
    seed_reject_reason: SeedRejectReason | None
    candidate_match: CandidateIdentityMatch
    review_flags: tuple[str, ...] = ()
