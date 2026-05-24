from dataclasses import replace

from xic_extractor.alignment.identity_coherence.cell_evidence import (
    evaluate_cell_evidence,
    select_cell_evidence_for_sample,
)
from xic_extractor.alignment.identity_coherence.models import (
    CandidateTrace,
    CellCandidateEvidence,
    IdentityCoherenceConfig,
    PrototypeWidthResult,
    RtCenterResult,
    SeedCandidateEvidence,
    ShapeConfig,
    ShapeReferenceResult,
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
    ShapeAuditStatus,
    ShapeReferenceBasis,
    ShapeStatus,
    WidthStatus,
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
    peak_start_rt: float | None = None,
    peak_end_rt: float | None = None,
    precursor_mz: float = 500.0,
    product_mz: float = 384.0,
    loss_da: float = 116.0,
    fragment_tags: tuple[str, ...] = ("MeR", "dR"),
    trace: CandidateTrace | None = None,
    point_count: int | None = 9,
    evidence_stage: EvidenceStage | str = EvidenceStage.PRE_BACKFILL,
    forbidden_evidence_seen: bool = False,
) -> CellCandidateEvidence:
    return CellCandidateEvidence(
        sample_id=sample_id,
        candidate_evidence=SeedCandidateEvidence(
            candidate_id=candidate_id,
            precursor_mz=precursor_mz,
            product_mz=product_mz,
            cid_observed_loss_da=loss_da,
            fragment_tags=fragment_tags,
            best_seed_rt=apex_rt,
            ms1_scan_support_score=0.75,
            evidence_stage=evidence_stage,
        ),
        apex_rt=apex_rt,
        peak_start_rt=apex_rt - 0.05 if peak_start_rt is None else peak_start_rt,
        peak_end_rt=apex_rt + 0.05 if peak_end_rt is None else peak_end_rt,
        area=1000.0,
        height=200.0,
        point_count=point_count,
        forbidden_evidence_seen=forbidden_evidence_seen,
        trace=trace,
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


def _trace(
    intensities: tuple[float, ...] = (0, 1, 3, 7, 10, 7, 3, 1, 0),
    *,
    start: float = 7.75,
    end: float = 7.85,
) -> CandidateTrace:
    step = (end - start) / (len(intensities) - 1)
    return CandidateTrace(
        rt_min=tuple(start + step * i for i in range(len(intensities))),
        intensity=intensities,
        shape_audit_status=ShapeAuditStatus.PASS,
    )


def _shape_reference() -> ShapeReferenceResult:
    return ShapeReferenceResult(
        shape_reference_basis=ShapeReferenceBasis.MORPHOLOGY_RT_MEDOID,
        shape_reference_candidate_id="REF",
        normalized_intensity=(
            0.0,
            0.060522753266880246,
            0.18156825980064073,
            0.4236592728681617,
            0.6052275326688024,
            0.4236592728681617,
            0.18156825980064073,
            0.060522753266880246,
            0.0,
        ),
        candidate_count=3,
        non_seed_candidate_count=3,
    )


def test_evaluate_cell_evidence_promotes_tier2_shape_after_rt_and_width_pass():
    request = _request()
    center = _center()
    candidate = _candidate(
        candidate_id="SHAPE",
        apex_rt=7.80,
        peak_start_rt=7.75,
        peak_end_rt=7.85,
        precursor_mz=500.5,
        product_mz=384.5,
        loss_da=116.5,
        fragment_tags=("other",),
        trace=_trace(),
        point_count=9,
    )
    width_result = PrototypeWidthResult(
        width_status=WidthStatus.PASS,
        prototype_width_sec=6.0,
        candidate_count=3,
        non_seed_candidate_count=3,
        width_candidate_ids=("REF", "A", "B"),
    )

    cell = evaluate_cell_evidence(
        request,
        candidate,
        center,
        IdentityCoherenceConfig(shape=ShapeConfig(resample_points=9)),
        identity_family_id="IDF-1",
        shape_reference=_shape_reference(),
        prototype_width=width_result,
    )

    assert cell.cell_identity_tier is CellIdentityTier.TIER2
    assert cell.cell_identity_basis is CellIdentityBasis.RT_SHAPE_SIMILARITY
    assert cell.fragment_match_status is FragmentMatchStatus.FAIL
    assert cell.non_rt_identity_result is NonRtIdentityResult.FAIL
    assert cell.shape_status is ShapeStatus.PASS
    assert cell.width_status is WidthStatus.PASS
    assert cell.coherent_count_contribution is True
    assert cell.tier12_count_contribution is True


def test_evaluate_cell_evidence_promotes_tier3_width_when_shape_unavailable():
    request = _request()
    center = _center()
    candidate = _candidate(
        candidate_id="WIDTH",
        apex_rt=7.80,
        peak_start_rt=7.75,
        peak_end_rt=7.85,
        precursor_mz=500.5,
        product_mz=384.5,
        loss_da=116.5,
        fragment_tags=("other",),
        trace=None,
    )
    width_result = PrototypeWidthResult(
        width_status=WidthStatus.PASS,
        prototype_width_sec=6.0,
        candidate_count=3,
        non_seed_candidate_count=3,
        width_candidate_ids=("REF", "A", "B"),
    )

    cell = evaluate_cell_evidence(
        request,
        candidate,
        center,
        IdentityCoherenceConfig(),
        identity_family_id="IDF-1",
        shape_reference=None,
        prototype_width=width_result,
    )

    assert cell.cell_identity_tier is CellIdentityTier.TIER3
    assert cell.cell_identity_basis is CellIdentityBasis.RT_PROTOTYPE_WIDTH
    assert cell.non_rt_identity_result is NonRtIdentityResult.FAIL
    assert cell.width_status is WidthStatus.PASS
    assert cell.coherent_count_contribution is True
    assert cell.tier12_count_contribution is False


def test_evaluate_cell_evidence_keeps_tier1_even_when_width_sanity_fails():
    request = _request()
    center = _center()
    candidate = _candidate(
        candidate_id="TIER1",
        apex_rt=7.80,
        peak_start_rt=7.70,
        peak_end_rt=7.90,
        trace=_trace(start=7.70, end=7.90),
        point_count=9,
    )
    width_result = PrototypeWidthResult(
        width_status=WidthStatus.PASS,
        prototype_width_sec=6.0,
        candidate_count=3,
        non_seed_candidate_count=3,
        width_candidate_ids=("REF", "A", "B"),
    )

    cell = evaluate_cell_evidence(
        request,
        candidate,
        center,
        IdentityCoherenceConfig(shape=ShapeConfig(resample_points=9)),
        identity_family_id="IDF-1",
        shape_reference=_shape_reference(),
        prototype_width=width_result,
    )

    assert cell.cell_identity_tier is CellIdentityTier.TIER1
    assert cell.cell_identity_basis is CellIdentityBasis.RT_FRAGMENT_SUPPORT
    assert cell.width_status is WidthStatus.FAIL
    assert cell.tier12_count_contribution is True


def test_evaluate_cell_evidence_does_not_use_shape_without_width_sanity():
    request = _request()
    center = _center()
    candidate = _candidate(
        candidate_id="NO_WIDTH",
        apex_rt=7.80,
        peak_start_rt=7.75,
        peak_end_rt=7.85,
        precursor_mz=500.5,
        product_mz=384.5,
        loss_da=116.5,
        fragment_tags=("other",),
        trace=_trace(),
        point_count=9,
    )

    cell = evaluate_cell_evidence(
        request,
        candidate,
        center,
        IdentityCoherenceConfig(shape=ShapeConfig(resample_points=9)),
        identity_family_id="IDF-1",
        shape_reference=_shape_reference(),
        prototype_width=None,
    )

    assert cell.cell_identity_tier is CellIdentityTier.RT_ONLY
    assert cell.shape_status is ShapeStatus.NOT_ASSESSED
    assert cell.width_status is WidthStatus.NOT_ASSESSED
    assert cell.coherent_count_contribution is False


def test_select_cell_evidence_prefers_tier2_over_closer_rt_only_candidate():
    request = _request()
    center = _center()
    shape_candidate = _candidate(
        candidate_id="SHAPE",
        sample_id="S2",
        apex_rt=7.875,
        peak_start_rt=7.825,
        peak_end_rt=7.925,
        precursor_mz=500.5,
        product_mz=384.5,
        loss_da=116.5,
        fragment_tags=("other",),
        trace=_trace(start=7.825, end=7.925),
        point_count=9,
    )
    rt_only_candidate = _candidate(
        candidate_id="RT_ONLY",
        sample_id="S2",
        apex_rt=7.820,
        peak_start_rt=7.700,
        peak_end_rt=7.940,
        precursor_mz=500.5,
        product_mz=384.5,
        loss_da=116.5,
        fragment_tags=("other",),
        trace=None,
    )
    width_result = PrototypeWidthResult(
        width_status=WidthStatus.PASS,
        prototype_width_sec=6.0,
        candidate_count=3,
        non_seed_candidate_count=3,
        width_candidate_ids=("REF", "A", "B"),
    )

    selected = select_cell_evidence_for_sample(
        request,
        (rt_only_candidate, shape_candidate),
        center,
        IdentityCoherenceConfig(shape=ShapeConfig(resample_points=9)),
        identity_family_id="IDF-1",
        shape_reference=_shape_reference(),
        prototype_width=width_result,
    )

    assert selected.candidate_id == "SHAPE"
    assert selected.cell_identity_tier is CellIdentityTier.TIER2
