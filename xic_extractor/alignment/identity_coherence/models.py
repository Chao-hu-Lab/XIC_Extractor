from __future__ import annotations

from dataclasses import dataclass, field

from .schema import (
    AreaHeightStatus,
    BaselineAuditStatus,
    CellAssessmentStatus,
    CellIdentityBasis,
    CellIdentityTier,
    EvidenceStage,
    FragmentMatchStatus,
    FragmentObservationMode,
    FragmentTagMatchPolicy,
    IdentityDecision,
    NonRtIdentityResult,
    RequestCandidateIdentityStatus,
    RequestIdentityCompletenessStatus,
    RtCenterDecision,
    RtGateStatus,
    SeedGateClass,
    SeedRejectReason,
    ShapeAuditStatus,
    ShapeReferenceBasis,
    ShapeStatus,
    WeakBasisReason,
    WidthStatus,
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


@dataclass(frozen=True)
class PromotionConfig:
    min_total_coherent_samples: int = 3
    min_non_seed_coherent_samples: int = 2
    min_non_seed_tier12_identity_samples: int = 2


@dataclass(frozen=True)
class RtConfig:
    max_rt_sec: float = 180.0
    preferred_rt_sec: float = 60.0
    seed_center_candidate_sec: float = 30.0
    max_center_drift_sec: float = 30.0


@dataclass(frozen=True)
class IdentityCoherenceConfig:
    seed_gate: SeedGateConfig = field(default_factory=SeedGateConfig)
    promotion: PromotionConfig = field(default_factory=PromotionConfig)
    rt: RtConfig = field(default_factory=RtConfig)


@dataclass(frozen=True)
class CellCandidateEvidence:
    sample_id: str
    candidate_evidence: SeedCandidateEvidence
    apex_rt: float | None
    peak_start_rt: float | None
    peak_end_rt: float | None
    area: float | None
    height: float | None
    point_count: int | None = None
    owner_assignment_status: str = "primary"
    duplicate_loser: bool = False
    forbidden_evidence_seen: bool = False
    blocked_reason: str = ""
    data_quality_reason: str = ""


@dataclass(frozen=True)
class RtCenterResult:
    center_rt_min: float
    center_rt_sec: float
    center_decision: RtCenterDecision
    center_candidate_count: int
    center_drift_sec: float


@dataclass(frozen=True)
class CellEvidenceResult:
    decision_id: str
    identity_family_id: str
    sample_id: str
    candidate_id: str
    cell_assessment_status: CellAssessmentStatus
    cell_identity_tier: CellIdentityTier
    cell_identity_basis: CellIdentityBasis
    fragment_observation_mode: FragmentObservationMode
    fragment_match_status: FragmentMatchStatus
    fragment_tags_supported: tuple[str, ...]
    rt_delta_center_sec: float | None
    rt_gate_status: RtGateStatus
    shape_status: ShapeStatus
    shape_similarity_cosine: float | None
    shape_reference_basis: ShapeReferenceBasis
    shape_reference_candidate_id: str
    shape_fallback_used: bool
    shape_audit_status: ShapeAuditStatus
    width_status: WidthStatus
    width_ratio_to_prototype: float | None
    baseline_audit_status: BaselineAuditStatus
    area_height_status: AreaHeightStatus
    non_rt_identity_result: NonRtIdentityResult
    coherent_count_contribution: bool
    tier12_count_contribution: bool
    blocked_reason: str
    data_quality_reason: str
    forbidden_evidence_seen: bool


@dataclass(frozen=True)
class IdentityDecisionSummary:
    decision_id: str
    identity_family_id: str
    seed_candidate_id: str
    seed_sample: str | None
    seed_gate_class: SeedGateClass
    request_identity_completeness_status: RequestIdentityCompletenessStatus
    request_candidate_identity_status: RequestCandidateIdentityStatus
    decision: IdentityDecision
    decision_reason: str
    total_coherent_sample_count: int
    non_seed_coherent_sample_count: int
    tier12_non_seed_identity_sample_count: int
    tier1_fragment_confirmed_sample_count: int
    tier2_shape_supported_sample_count: int
    tier2_seed_shape_fallback_sample_count: int
    tier3_width_only_sample_count: int
    min_total_coherent_samples: int
    min_non_seed_coherent_samples: int
    min_non_seed_tier12_identity_samples: int
    weak_basis_reason: WeakBasisReason
    shape_reference_basis: ShapeReferenceBasis
    shape_reference_candidate_id: str
    prototype_width_sec: float | None
    center_rt_source: str
    center: RtCenterResult
    coherent_fraction: float | None
    infrastructure_blocked_sample_count: int
    data_quality_reject_sample_count: int
    forbidden_evidence_seen: bool
    forbidden_evidence_used: bool
