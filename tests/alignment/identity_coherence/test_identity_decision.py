from dataclasses import replace

from xic_extractor.alignment.identity_coherence.decision import (
    summarize_identity_decision,
)
from xic_extractor.alignment.identity_coherence.models import (
    CellEvidenceResult,
    IdentityCoherenceConfig,
    RtCenterResult,
    SeedCandidateEvidence,
    SeedGateResult,
)
from xic_extractor.alignment.identity_coherence.request_builder import (
    build_identity_coherence_request,
)
from xic_extractor.alignment.identity_coherence.schema import (
    AreaHeightStatus,
    BaselineAuditStatus,
    CellAssessmentStatus,
    CellIdentityBasis,
    CellIdentityTier,
    DecisionReason,
    EvidenceStage,
    FragmentMatchStatus,
    FragmentObservationMode,
    IdentityDecision,
    NonRtIdentityResult,
    RequestCandidateIdentityStatus,
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
from xic_extractor.alignment.identity_coherence.seed_gate import evaluate_seed_gate


class SeedLike:
    candidate_id = "SEED-1"
    sample_name = "RAW-1"
    precursor_mz = 500.0
    product_mz = 384.0
    observed_neutral_loss_da = 116.0
    matched_tag_names = ("MeR", "dR")
    neutral_loss_tag = "dR"
    best_seed_rt = 7.80
    ms1_scan_support_score = 0.80


class OwnerLike:
    owner_apex_rt = 7.80
    owner_peak_start_rt = 7.70
    owner_peak_end_rt = 7.90
    owner_area = 1000.0
    owner_height = 200.0


def _seed_result() -> SeedGateResult:
    request = build_identity_coherence_request(
        SeedLike(),
        request_id="REQ-1",
        decision_id="DEC-1",
        precursor_tolerance_ppm=10.0,
        product_tolerance_ppm=10.0,
        cid_observed_loss_tolerance_ppm=10.0,
        fragment_profile_id="profile-a",
    )
    candidate = SeedLike()
    evidence = SeedCandidateEvidence(
        candidate_id=candidate.candidate_id,
        precursor_mz=candidate.precursor_mz,
        product_mz=candidate.product_mz,
        cid_observed_loss_da=candidate.observed_neutral_loss_da,
        fragment_tags=candidate.matched_tag_names,
        best_seed_rt=candidate.best_seed_rt,
        ms1_scan_support_score=candidate.ms1_scan_support_score,
        evidence_stage=EvidenceStage.PRE_BACKFILL,
    )
    return evaluate_seed_gate(request, evidence, OwnerLike())


def _center(decision=RtCenterDecision.SEED_ANCHORED) -> RtCenterResult:
    return RtCenterResult(
        center_rt_min=7.80,
        center_rt_sec=468.0,
        center_decision=decision,
        center_candidate_count=2,
        center_drift_sec=0.0,
    )


def _tier1_cell(sample_id: str) -> CellEvidenceResult:
    return CellEvidenceResult(
        decision_id="DEC-1",
        identity_family_id="IDF-1",
        sample_id=sample_id,
        candidate_id=f"CAND-{sample_id}",
        cell_assessment_status=CellAssessmentStatus.ASSESSED,
        cell_identity_tier=CellIdentityTier.TIER1,
        cell_identity_basis=CellIdentityBasis.RT_FRAGMENT_SUPPORT,
        fragment_observation_mode=FragmentObservationMode.CID_NEUTRAL_LOSS,
        fragment_match_status=FragmentMatchStatus.PASS,
        fragment_tags_supported=("MeR", "dR"),
        rt_delta_center_sec=2.0,
        rt_gate_status=RtGateStatus.PASS,
        shape_status=ShapeStatus.NOT_ASSESSED,
        shape_similarity_cosine=None,
        shape_reference_basis=ShapeReferenceBasis.NONE,
        shape_reference_candidate_id="",
        shape_fallback_used=False,
        shape_audit_status=ShapeAuditStatus.NOT_ASSESSED,
        width_status=WidthStatus.NOT_ASSESSED,
        width_ratio_to_prototype=None,
        baseline_audit_status=BaselineAuditStatus.NOT_ASSESSED,
        area_height_status=AreaHeightStatus.PASS,
        non_rt_identity_result=NonRtIdentityResult.PASS,
        coherent_count_contribution=True,
        tier12_count_contribution=True,
        blocked_reason="",
        data_quality_reason="",
        forbidden_evidence_seen=False,
    )


def test_summarize_identity_decision_promotes_seed_plus_two_tier1_cells():
    summary = summarize_identity_decision(
        _seed_result(),
        (_tier1_cell("RAW-2"), _tier1_cell("RAW-3")),
        _center(),
        IdentityCoherenceConfig(),
        identity_family_id="IDF-1",
        assessed_sample_count=8,
    )

    assert summary.decision is IdentityDecision.WOULD_PRIMARY
    assert summary.total_coherent_sample_count == 3
    assert summary.non_seed_coherent_sample_count == 2
    assert summary.tier12_non_seed_identity_sample_count == 2
    assert summary.tier1_fragment_confirmed_sample_count == 2
    assert summary.tier2_shape_supported_sample_count == 0
    assert summary.tier2_seed_shape_fallback_sample_count == 0
    assert summary.tier3_width_only_sample_count == 0
    assert (
        summary.tier12_non_seed_identity_sample_count
        == summary.tier1_fragment_confirmed_sample_count
    )
    assert summary.decision_reason == DecisionReason.TIER1_SUPPORT.value
    assert summary.request_candidate_identity_status is (
        RequestCandidateIdentityStatus.MATCH
    )
    assert summary.center_rt_source == RtCenterDecision.SEED_ANCHORED.value
    assert summary.forbidden_evidence_seen is False
    assert summary.weak_basis_reason is WeakBasisReason.NONE
    assert summary.coherent_fraction == 0.375


def test_summarize_identity_decision_keeps_failed_seed_review_only():
    failed_seed = replace(
        _seed_result(),
        seed_gate_class=SeedGateClass.REVIEW_ONLY_SEED_GATE_FAILED,
        seed_reject_reason=SeedRejectReason.LOW_MS1_SCAN_SUPPORT,
    )
    summary = summarize_identity_decision(
        failed_seed,
        (_tier1_cell("RAW-2"), _tier1_cell("RAW-3")),
        _center(),
        IdentityCoherenceConfig(),
        identity_family_id="IDF-1",
        assessed_sample_count=8,
    )

    assert summary.decision is IdentityDecision.REVIEW_ONLY_SEED_GATE_FAILED
    assert summary.total_coherent_sample_count == 0


def test_summarize_identity_decision_blocks_center_unstable_promotion():
    summary = summarize_identity_decision(
        _seed_result(),
        (_tier1_cell("RAW-2"), _tier1_cell("RAW-3")),
        _center(RtCenterDecision.CENTER_UNSTABLE_REVIEW_ONLY),
        IdentityCoherenceConfig(),
        identity_family_id="IDF-1",
        assessed_sample_count=8,
    )

    assert summary.decision is IdentityDecision.REVIEW_ONLY_CENTER_UNSTABLE
    assert summary.total_coherent_sample_count == 3


def test_summarize_identity_decision_rejects_seed_plus_one_tier1_cell():
    summary = summarize_identity_decision(
        _seed_result(),
        (_tier1_cell("RAW-2"),),
        _center(),
        IdentityCoherenceConfig(),
        identity_family_id="IDF-1",
        assessed_sample_count=8,
    )

    assert summary.decision is IdentityDecision.REVIEW_ONLY_INSUFFICIENT_SUPPORT
    assert summary.total_coherent_sample_count == 2
    assert summary.non_seed_coherent_sample_count == 1
    assert summary.tier12_non_seed_identity_sample_count == 1


def test_summarize_identity_decision_reports_rt_only_support_path():
    rt_only = replace(
        _tier1_cell("RAW-2"),
        cell_identity_tier=CellIdentityTier.RT_ONLY,
        cell_identity_basis=CellIdentityBasis.NONE,
        fragment_match_status=FragmentMatchStatus.FAIL,
        non_rt_identity_result=NonRtIdentityResult.FAIL,
        coherent_count_contribution=False,
        tier12_count_contribution=False,
    )
    summary = summarize_identity_decision(
        _seed_result(),
        (rt_only,),
        _center(),
        IdentityCoherenceConfig(),
        identity_family_id="IDF-1",
        assessed_sample_count=8,
    )

    assert summary.decision is IdentityDecision.REVIEW_ONLY_RT_ONLY_SUPPORT
    assert summary.weak_basis_reason is WeakBasisReason.RT_ONLY
    assert summary.total_coherent_sample_count == 1
    assert summary.tier12_non_seed_identity_sample_count == 0


def test_summarize_identity_decision_detects_forbidden_evidence_seen():
    forbidden = replace(_tier1_cell("RAW-2"), forbidden_evidence_seen=True)
    summary = summarize_identity_decision(
        _seed_result(),
        (forbidden, _tier1_cell("RAW-3")),
        _center(),
        IdentityCoherenceConfig(),
        identity_family_id="IDF-1",
        assessed_sample_count=8,
    )

    assert summary.decision is IdentityDecision.WOULD_PRIMARY
    assert summary.forbidden_evidence_seen is True
    assert summary.forbidden_evidence_used is False
