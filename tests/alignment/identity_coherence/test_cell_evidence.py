from dataclasses import replace

from xic_extractor.alignment.identity_coherence.cell_evidence import (
    evaluate_cell_evidence,
    select_cell_evidence_for_sample,
)
from xic_extractor.alignment.identity_coherence.models import (
    CellCandidateEvidence,
    IdentityCoherenceConfig,
    RtCenterResult,
    SeedCandidateEvidence,
)
from xic_extractor.alignment.identity_coherence.request_builder import (
    build_identity_coherence_request,
)
from xic_extractor.alignment.identity_coherence.schema import (
    CellAssessmentStatus,
    CellBlockedReason,
    CellDataQualityReason,
    CellIdentityBasis,
    CellIdentityTier,
    EvidenceStage,
    FragmentMatchStatus,
    NonRtIdentityResult,
    RtCenterDecision,
    RtGateStatus,
    ShapeStatus,
)


class SeedLike:
    candidate_id = "SEED-1"
    sample_name = "RAW-1"
    precursor_mz = 500.0
    product_mz = 384.0
    observed_neutral_loss_da = 116.0
    matched_tag_names = ("MeR", "dR")
    neutral_loss_tag = "dR"


def _request():
    return build_identity_coherence_request(
        SeedLike(),
        request_id="REQ-1",
        decision_id="DEC-1",
        precursor_tolerance_ppm=10.0,
        product_tolerance_ppm=10.0,
        cid_observed_loss_tolerance_ppm=10.0,
        fragment_profile_id="profile-a",
    )


def _center(rt: float = 7.80) -> RtCenterResult:
    return RtCenterResult(
        center_rt_min=rt,
        center_rt_sec=rt * 60.0,
        center_decision=RtCenterDecision.SEED_ANCHORED,
        center_candidate_count=0,
        center_drift_sec=0.0,
    )


def _candidate(
    *,
    candidate_id: str = "CAND-2",
    sample_id: str = "RAW-2",
    apex_rt: float = 7.82,
    precursor_mz: float = 500.0,
    product_mz: float = 384.0,
    fragment_tags: tuple[str, ...] = ("MeR", "dR"),
    evidence_stage: EvidenceStage | str = EvidenceStage.PRE_BACKFILL,
    forbidden_evidence_seen: bool = False,
) -> CellCandidateEvidence:
    return CellCandidateEvidence(
        sample_id=sample_id,
        candidate_evidence=SeedCandidateEvidence(
            candidate_id=candidate_id,
            precursor_mz=precursor_mz,
            product_mz=product_mz,
            cid_observed_loss_da=116.0,
            fragment_tags=fragment_tags,
            best_seed_rt=apex_rt,
            ms1_scan_support_score=0.75,
            evidence_stage=evidence_stage,
        ),
        apex_rt=apex_rt,
        peak_start_rt=apex_rt - 0.05,
        peak_end_rt=apex_rt + 0.05,
        area=1000.0,
        height=200.0,
        point_count=9,
        forbidden_evidence_seen=forbidden_evidence_seen,
    )


def test_evaluate_cell_evidence_admits_tier1_fragment_support():
    cell = evaluate_cell_evidence(
        _request(),
        _candidate(),
        _center(),
        IdentityCoherenceConfig(),
        identity_family_id="IDF-1",
    )

    assert cell.cell_assessment_status is CellAssessmentStatus.ASSESSED
    assert cell.cell_identity_tier is CellIdentityTier.TIER1
    assert cell.cell_identity_basis is CellIdentityBasis.RT_FRAGMENT_SUPPORT
    assert cell.fragment_match_status is FragmentMatchStatus.PASS
    assert cell.rt_gate_status is RtGateStatus.PASS
    assert cell.shape_status is ShapeStatus.NOT_ASSESSED
    assert cell.non_rt_identity_result is NonRtIdentityResult.PASS
    assert cell.coherent_count_contribution is True
    assert cell.tier12_count_contribution is True


def test_select_cell_evidence_marks_unresolved_tie_as_ambiguous_no_count():
    first = _candidate(candidate_id="NON-SEED-A")
    second = _candidate(candidate_id="NON-SEED-B")

    cell = select_cell_evidence_for_sample(
        _request(),
        (first, second),
        _center(),
        IdentityCoherenceConfig(),
        identity_family_id="IDF-1",
    )

    assert cell.fragment_match_status is FragmentMatchStatus.AMBIGUOUS
    assert cell.cell_identity_tier is CellIdentityTier.RT_ONLY
    assert cell.non_rt_identity_result is NonRtIdentityResult.FAIL
    assert cell.coherent_count_contribution is False
    assert cell.tier12_count_contribution is False


def test_select_cell_evidence_tiebreaks_by_precursor_error():
    farther = _candidate(candidate_id="NON-SEED-FAR", precursor_mz=500.001)
    closer = _candidate(candidate_id="NON-SEED-CLOSE", precursor_mz=500.0001)

    cell = select_cell_evidence_for_sample(
        _request(),
        (farther, closer),
        _center(),
        IdentityCoherenceConfig(),
        identity_family_id="IDF-1",
    )

    assert cell.candidate_id == "NON-SEED-CLOSE"
    assert cell.fragment_match_status is FragmentMatchStatus.PASS
    assert cell.coherent_count_contribution is True


def test_evaluate_cell_evidence_keeps_rt_pass_fragment_mismatch_as_rt_only():
    cell = evaluate_cell_evidence(
        _request(),
        _candidate(product_mz=390.0),
        _center(),
        IdentityCoherenceConfig(),
        identity_family_id="IDF-1",
    )

    assert cell.cell_identity_tier is CellIdentityTier.RT_ONLY
    assert cell.cell_identity_basis is CellIdentityBasis.NONE
    assert cell.fragment_match_status is FragmentMatchStatus.FAIL
    assert cell.rt_gate_status is RtGateStatus.PASS
    assert cell.non_rt_identity_result is NonRtIdentityResult.FAIL
    assert cell.coherent_count_contribution is False
    assert cell.tier12_count_contribution is False


def test_evaluate_cell_evidence_does_not_count_rt_fail_even_if_fragment_matches():
    cell = evaluate_cell_evidence(
        _request(),
        _candidate(apex_rt=9.50),
        _center(7.80),
        IdentityCoherenceConfig(),
        identity_family_id="IDF-1",
    )

    assert cell.rt_gate_status is RtGateStatus.FAIL
    assert cell.fragment_match_status is FragmentMatchStatus.PASS
    assert cell.non_rt_identity_result is NonRtIdentityResult.PASS
    assert cell.coherent_count_contribution is False
    assert cell.tier12_count_contribution is False


def test_evaluate_cell_evidence_blocks_backfill_only_candidate_evidence():
    cell = evaluate_cell_evidence(
        _request(),
        _candidate(evidence_stage="backfill_only"),
        _center(),
        IdentityCoherenceConfig(),
        identity_family_id="IDF-1",
    )

    assert cell.cell_assessment_status is CellAssessmentStatus.BLOCKED
    assert cell.cell_identity_tier is CellIdentityTier.BLOCKED
    assert cell.non_rt_identity_result is NonRtIdentityResult.BLOCKED
    assert cell.blocked_reason == CellBlockedReason.BACKFILL_ONLY_EVIDENCE.value
    assert cell.coherent_count_contribution is False
    assert cell.forbidden_evidence_seen is True


def test_evaluate_cell_evidence_rejects_bad_morphology_as_data_quality():
    bad = replace(_candidate(), area=0.0)
    cell = evaluate_cell_evidence(
        _request(),
        bad,
        _center(),
        IdentityCoherenceConfig(),
        identity_family_id="IDF-1",
    )

    assert cell.cell_assessment_status is CellAssessmentStatus.DATA_QUALITY_REJECT
    assert cell.cell_identity_tier is CellIdentityTier.DATA_QUALITY
    assert cell.area_height_status.value == "fail"
    assert cell.data_quality_reason == (
        CellDataQualityReason.INVALID_PEAK_MORPHOLOGY.value
    )


def test_select_cell_evidence_without_tier1_uses_stable_fallback_order():
    farther = _candidate(
        candidate_id="NON-TIER1-FAR",
        apex_rt=7.92,
        product_mz=390.0,
    )
    closer = _candidate(
        candidate_id="NON-TIER1-CLOSE",
        apex_rt=7.81,
        product_mz=390.0,
    )

    first_order = select_cell_evidence_for_sample(
        _request(),
        (farther, closer),
        _center(),
        IdentityCoherenceConfig(),
        identity_family_id="IDF-1",
    )
    second_order = select_cell_evidence_for_sample(
        _request(),
        (closer, farther),
        _center(),
        IdentityCoherenceConfig(),
        identity_family_id="IDF-1",
    )

    assert first_order.candidate_id == "NON-TIER1-CLOSE"
    assert second_order.candidate_id == "NON-TIER1-CLOSE"
