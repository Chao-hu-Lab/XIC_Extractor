from dataclasses import dataclass

from xic_extractor.alignment.identity_coherence.request_builder import (
    build_identity_coherence_request,
    build_seed_candidate_evidence,
)
from xic_extractor.alignment.identity_coherence.schema import (
    EvidenceStage,
    RequestCandidateIdentityStatus,
    SeedGateClass,
    SeedRejectReason,
)
from xic_extractor.alignment.identity_coherence.seed_gate import evaluate_seed_gate


@dataclass
class CandidateLike:
    candidate_id: str = "CAND-1"
    sample_name: str = "RAW-1"
    precursor_mz: float | None = 500.0
    product_mz: float | None = 384.0
    observed_neutral_loss_da: float | None = 116.0
    matched_tag_names: object = ("MeR", "dR")
    neutral_loss_tag: str | None = "dR"
    best_seed_rt: float = 7.83
    ms1_scan_support_score: float | None = 0.80


@dataclass
class OwnerLike:
    owner_apex_rt: float = 7.84
    owner_peak_start_rt: float = 7.70
    owner_peak_end_rt: float = 7.98
    owner_area: float = 1000.0
    owner_height: float = 200.0


def _request(candidate: CandidateLike):
    return build_identity_coherence_request(
        candidate,
        request_id="REQ-1",
        decision_id="DEC-1",
        precursor_tolerance_ppm=10.0,
        product_tolerance_ppm=10.0,
        cid_observed_loss_tolerance_ppm=10.0,
        fragment_profile_id="profile-a",
    )


def _evidence(candidate: CandidateLike, *, evidence_stage=EvidenceStage.PRE_BACKFILL):
    return build_seed_candidate_evidence(candidate, evidence_stage=evidence_stage)


def test_evaluate_seed_gate_accepts_matching_candidate_and_owner():
    candidate = CandidateLike()
    result = evaluate_seed_gate(_request(candidate), _evidence(candidate), OwnerLike())

    assert result.seed_gate_class is SeedGateClass.COHERENT_SEED
    assert result.seed_reject_reason is None
    assert result.resolved_request.request_candidate_identity_status is (
        RequestCandidateIdentityStatus.MATCH
    )


def test_evaluate_seed_gate_rejects_incomplete_request_before_candidate_match():
    candidate = CandidateLike(product_mz=None)
    result = evaluate_seed_gate(
        _request(candidate),
        _evidence(CandidateLike()),
        OwnerLike(),
    )

    assert result.seed_gate_class is SeedGateClass.REVIEW_ONLY_SEED_GATE_FAILED
    assert result.seed_reject_reason is (
        SeedRejectReason.MISSING_REQUEST_IDENTITY_CONSTRAINT
    )
    assert result.resolved_request.request_candidate_identity_status is (
        RequestCandidateIdentityStatus.NOT_ASSESSED
    )


def test_evaluate_seed_gate_rejects_candidate_identity_mismatch_before_owner_checks():
    request = _request(CandidateLike())
    candidate = CandidateLike(product_mz=390.0)
    result = evaluate_seed_gate(request, _evidence(candidate), None)

    assert result.seed_gate_class is SeedGateClass.REVIEW_ONLY_SEED_GATE_FAILED
    assert result.seed_reject_reason is (
        SeedRejectReason.REQUEST_CANDIDATE_IDENTITY_MISMATCH
    )


def test_evaluate_seed_gate_rejects_missing_owner():
    candidate = CandidateLike()
    result = evaluate_seed_gate(_request(candidate), _evidence(candidate), None)

    assert result.seed_gate_class is SeedGateClass.REVIEW_ONLY_SEED_GATE_FAILED
    assert result.seed_reject_reason is SeedRejectReason.NO_QUANTIFIABLE_OWNER


def test_evaluate_seed_gate_rejects_nonfinite_owner_geometry():
    candidate = CandidateLike()
    result = evaluate_seed_gate(
        _request(candidate),
        _evidence(candidate),
        OwnerLike(owner_area=float("nan")),
    )

    assert result.seed_gate_class is SeedGateClass.REVIEW_ONLY_SEED_GATE_FAILED
    assert result.seed_reject_reason is SeedRejectReason.NONFINITE_PEAK


def test_evaluate_seed_gate_rejects_seed_rt_outside_owner_peak():
    candidate = CandidateLike(best_seed_rt=8.10)
    result = evaluate_seed_gate(_request(candidate), _evidence(candidate), OwnerLike())

    assert result.seed_gate_class is SeedGateClass.REVIEW_ONLY_SEED_GATE_FAILED
    assert result.seed_reject_reason is SeedRejectReason.SEED_RT_OUTSIDE_OWNER_PEAK


def test_evaluate_seed_gate_rejects_ambiguous_owner_assignment():
    candidate = CandidateLike()
    result = evaluate_seed_gate(
        _request(candidate),
        _evidence(candidate),
        OwnerLike(),
        owner_assignment_status="ambiguous",
    )

    assert result.seed_reject_reason is SeedRejectReason.AMBIGUOUS_OWNER


def test_evaluate_seed_gate_rejects_unresolved_owner_assignment():
    candidate = CandidateLike()
    result = evaluate_seed_gate(
        _request(candidate),
        _evidence(candidate),
        OwnerLike(),
        owner_assignment_status="unresolved",
    )

    assert result.seed_reject_reason is SeedRejectReason.NO_QUANTIFIABLE_OWNER


def test_evaluate_seed_gate_allows_supporting_owner_assignment():
    candidate = CandidateLike()
    result = evaluate_seed_gate(
        _request(candidate),
        _evidence(candidate),
        OwnerLike(),
        owner_assignment_status="supporting",
    )

    assert result.seed_gate_class is SeedGateClass.COHERENT_SEED


def test_evaluate_seed_gate_rejects_unknown_owner_assignment_status():
    candidate = CandidateLike()
    result = evaluate_seed_gate(
        _request(candidate),
        _evidence(candidate),
        OwnerLike(),
        owner_assignment_status="ambigous",
    )

    assert result.seed_reject_reason is SeedRejectReason.AMBIGUOUS_OWNER


def test_evaluate_seed_gate_rejects_duplicate_loser():
    candidate = CandidateLike()
    result = evaluate_seed_gate(
        _request(candidate),
        _evidence(candidate),
        OwnerLike(),
        duplicate_loser=True,
    )

    assert result.seed_reject_reason is SeedRejectReason.DUPLICATE_LOSER


def test_evaluate_seed_gate_rejects_low_scan_support_when_available():
    candidate = CandidateLike(ms1_scan_support_score=0.25)
    result = evaluate_seed_gate(_request(candidate), _evidence(candidate), OwnerLike())

    assert result.seed_reject_reason is SeedRejectReason.LOW_MS1_SCAN_SUPPORT


def test_evaluate_seed_gate_rejects_nonfinite_scan_support_when_available():
    candidate = CandidateLike(ms1_scan_support_score=float("nan"))
    result = evaluate_seed_gate(_request(candidate), _evidence(candidate), OwnerLike())

    assert result.seed_reject_reason is SeedRejectReason.LOW_MS1_SCAN_SUPPORT


def test_evaluate_seed_gate_allows_missing_scan_support_as_unassessed():
    candidate = CandidateLike(ms1_scan_support_score=None)
    result = evaluate_seed_gate(_request(candidate), _evidence(candidate), OwnerLike())

    assert result.seed_gate_class is SeedGateClass.COHERENT_SEED
    assert "ms1_scan_support_unavailable" in result.review_flags


def test_evaluate_seed_gate_rejects_backfill_only_candidate_evidence():
    candidate = CandidateLike()
    result = evaluate_seed_gate(
        _request(candidate),
        _evidence(candidate, evidence_stage=EvidenceStage.BACKFILL_ONLY),
        OwnerLike(),
    )

    assert result.seed_reject_reason is SeedRejectReason.BACKFILL_ONLY_EVIDENCE


def test_evaluate_seed_gate_rejects_post_backfill_owner_evidence():
    candidate = CandidateLike()
    result = evaluate_seed_gate(
        _request(candidate),
        _evidence(candidate),
        OwnerLike(),
        owner_evidence_stage=EvidenceStage.POST_BACKFILL,
    )

    assert result.seed_reject_reason is SeedRejectReason.BACKFILL_ONLY_EVIDENCE
