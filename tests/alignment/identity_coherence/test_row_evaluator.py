from __future__ import annotations

from dataclasses import replace

from xic_extractor.alignment.identity_coherence.models import (
    CandidateTrace,
    CellCandidateEvidence,
    IdentityCoherenceConfig,
    SeedCandidateEvidence,
    ShapeConfig,
)
from xic_extractor.alignment.identity_coherence.request_builder import (
    build_identity_coherence_request,
)
from xic_extractor.alignment.identity_coherence.row_evaluator import (
    evaluate_identity_coherence_row,
)
from xic_extractor.alignment.identity_coherence.schema import (
    CellIdentityTier,
    EvidenceStage,
    IdentityDecision,
    SeedGateClass,
    SeedRejectReason,
    ShapeReferenceBasis,
)
from xic_extractor.alignment.identity_coherence.seed_gate import evaluate_seed_gate


class SeedLike:
    candidate_id = "SEED"
    sample_name = "S1"
    precursor_mz = 500.0
    product_mz = 384.0
    observed_neutral_loss_da = 116.0
    matched_tag_names = ("MeR", "dR")
    neutral_loss_tag = "dR"
    best_seed_rt = 7.80
    ms1_scan_support_score = 0.80


class OwnerLike:
    owner_apex_rt = 7.80
    owner_peak_start_rt = 7.75
    owner_peak_end_rt = 7.85
    owner_area = 1000.0
    owner_height = 200.0


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


def _seed_evidence() -> SeedCandidateEvidence:
    return SeedCandidateEvidence(
        candidate_id="SEED",
        precursor_mz=500.0,
        product_mz=384.0,
        cid_observed_loss_da=116.0,
        fragment_tags=("MeR", "dR"),
        best_seed_rt=7.80,
        ms1_scan_support_score=0.80,
        evidence_stage=EvidenceStage.PRE_BACKFILL,
    )


def _trace() -> CandidateTrace:
    return CandidateTrace(
        rt_min=(7.75, 7.7625, 7.775, 7.7875, 7.80, 7.8125, 7.825, 7.8375, 7.85),
        intensity=(0.0, 1.0, 3.0, 7.0, 10.0, 7.0, 3.0, 1.0, 0.0),
    )


def _candidate(
    candidate_id: str,
    sample_id: str,
    *,
    fragment_tags: tuple[str, ...] = ("other",),
    precursor_mz: float = 500.5,
    product_mz: float = 384.5,
    loss_da: float = 116.5,
) -> CellCandidateEvidence:
    return CellCandidateEvidence(
        sample_id=sample_id,
        candidate_evidence=SeedCandidateEvidence(
            candidate_id=candidate_id,
            precursor_mz=precursor_mz,
            product_mz=product_mz,
            cid_observed_loss_da=loss_da,
            fragment_tags=fragment_tags,
            best_seed_rt=7.80,
            ms1_scan_support_score=0.70,
            evidence_stage=EvidenceStage.PRE_BACKFILL,
        ),
        apex_rt=7.80,
        peak_start_rt=7.75,
        peak_end_rt=7.85,
        area=100.0,
        height=20.0,
        point_count=9,
        trace=_trace(),
    )


def test_evaluate_identity_coherence_row_promotes_two_prototype_shape_cells():
    request = _request()
    seed_evidence = _seed_evidence()
    seed_gate = evaluate_seed_gate(request, seed_evidence, OwnerLike())
    seed_candidate = _candidate(
        "SEED",
        "S1",
        fragment_tags=("MeR", "dR"),
        precursor_mz=500.0,
        product_mz=384.0,
        loss_da=116.0,
    )

    result = evaluate_identity_coherence_row(
        seed_gate,
        seed_evidence,
        seed_candidate,
        (
            _candidate("A", "S2"),
            _candidate("B", "S3"),
            _candidate("C", "S4"),
        ),
        IdentityCoherenceConfig(shape=ShapeConfig(resample_points=9)),
        identity_family_id="IDF-1",
        assessed_sample_count=4,
    )

    assert result.decision.decision is IdentityDecision.WOULD_PRIMARY
    assert result.decision.tier2_shape_supported_sample_count >= 2
    assert result.decision.tier12_non_seed_identity_sample_count >= 2
    assert result.shape_reference.shape_reference_basis in {
        ShapeReferenceBasis.MORPHOLOGY_RT_MEDOID,
        ShapeReferenceBasis.TIER1_SUPPORTED_MEDOID,
    }
    assert result.shape_reference.shape_reference_candidate_id != "SEED"
    assert all(
        cell.cell_identity_tier in {CellIdentityTier.TIER2, CellIdentityTier.TIER3}
        for cell in result.cells
    )


def test_evaluate_identity_coherence_row_short_circuits_failed_seed_gate():
    request = _request()
    seed_evidence = _seed_evidence()
    failed_seed_gate = evaluate_seed_gate(request, seed_evidence, OwnerLike())
    failed_seed_gate = replace(
        failed_seed_gate,
        seed_gate_class=SeedGateClass.REVIEW_ONLY_SEED_GATE_FAILED,
        seed_reject_reason=SeedRejectReason.LOW_MS1_SCAN_SUPPORT,
    )
    result = evaluate_identity_coherence_row(
        failed_seed_gate,
        seed_evidence,
        _candidate(
            "SEED",
            "S1",
            fragment_tags=("MeR", "dR"),
            precursor_mz=500.0,
            product_mz=384.0,
            loss_da=116.0,
        ),
        (
            _candidate("A", "S2"),
            _candidate("B", "S3"),
            _candidate("C", "S4"),
        ),
        IdentityCoherenceConfig(shape=ShapeConfig(resample_points=9)),
        identity_family_id="IDF-1",
        assessed_sample_count=4,
    )

    assert result.cells == ()
    assert result.decision.decision is IdentityDecision.REVIEW_ONLY_SEED_GATE_FAILED
    assert result.decision.total_coherent_sample_count == 0
    assert result.decision.tier12_non_seed_identity_sample_count == 0
    assert result.shape_reference.shape_reference_basis is ShapeReferenceBasis.NONE
    assert result.prototype_width.prototype_width_sec is None
    assert result.center.center_candidate_count == 0


def test_evaluate_identity_coherence_row_never_counts_seed_in_width_pool():
    request = _request()
    request = replace(request, seed_sample=None)
    seed_evidence = _seed_evidence()
    seed_gate = evaluate_seed_gate(request, seed_evidence, OwnerLike())

    result = evaluate_identity_coherence_row(
        seed_gate,
        seed_evidence,
        _candidate(
            "SEED",
            "S1",
            fragment_tags=("MeR", "dR"),
            precursor_mz=500.0,
            product_mz=384.0,
            loss_da=116.0,
        ),
        (
            _candidate("A", "S2"),
            _candidate("B", "S3"),
        ),
        IdentityCoherenceConfig(shape=ShapeConfig(resample_points=9)),
        identity_family_id="IDF-1",
        assessed_sample_count=3,
    )

    assert result.prototype_width.prototype_width_sec is None
    assert result.prototype_width.non_seed_candidate_count == 2
