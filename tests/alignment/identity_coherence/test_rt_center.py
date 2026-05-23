import pytest

from xic_extractor.alignment.identity_coherence.models import (
    CellCandidateEvidence,
    IdentityCoherenceConfig,
    RtConfig,
    SeedCandidateEvidence,
)
from xic_extractor.alignment.identity_coherence.rt_center import estimate_rt_center
from xic_extractor.alignment.identity_coherence.schema import (
    EvidenceStage,
    RtCenterDecision,
)


def _seed(rt: float = 7.80) -> SeedCandidateEvidence:
    return SeedCandidateEvidence(
        candidate_id="SEED-1",
        precursor_mz=500.0,
        product_mz=384.0,
        cid_observed_loss_da=116.0,
        fragment_tags=("MeR", "dR"),
        best_seed_rt=rt,
        ms1_scan_support_score=0.80,
    )


def _cell(
    candidate_id: str,
    apex_rt: float,
    *,
    start_rt: float | None = None,
    end_rt: float | None = None,
    area: float | None = 1000.0,
    height: float | None = 200.0,
    evidence_stage: EvidenceStage = EvidenceStage.PRE_BACKFILL,
    owner_assignment_status: str = "primary",
    duplicate_loser: bool = False,
    blocked_reason: str = "",
    data_quality_reason: str = "",
) -> CellCandidateEvidence:
    return CellCandidateEvidence(
        sample_id=f"RAW-{candidate_id}",
        candidate_evidence=SeedCandidateEvidence(
            candidate_id=candidate_id,
            precursor_mz=500.0,
            product_mz=384.0,
            cid_observed_loss_da=116.0,
            fragment_tags=("MeR", "dR"),
            best_seed_rt=apex_rt,
            ms1_scan_support_score=0.75,
            evidence_stage=evidence_stage,
        ),
        apex_rt=apex_rt,
        peak_start_rt=apex_rt - 0.05 if start_rt is None else start_rt,
        peak_end_rt=apex_rt + 0.05 if end_rt is None else end_rt,
        area=area,
        height=height,
        point_count=9,
        owner_assignment_status=owner_assignment_status,
        duplicate_loser=duplicate_loser,
        blocked_reason=blocked_reason,
        data_quality_reason=data_quality_reason,
    )


def test_estimate_rt_center_seed_anchored_without_center_candidates():
    center = estimate_rt_center(_seed(7.80), (), IdentityCoherenceConfig())

    assert center.center_rt_min == 7.80
    assert center.center_rt_sec == 468.0
    assert center.center_candidate_count == 0
    assert center.center_drift_sec == 0.0
    assert center.center_decision is RtCenterDecision.SEED_ANCHORED


def test_estimate_rt_center_recenters_to_median_complete_candidate_apex():
    center = estimate_rt_center(
        _seed(7.80),
        (_cell("A", 7.81), _cell("B", 7.82), _cell("C", 7.83)),
        IdentityCoherenceConfig(),
    )

    assert center.center_rt_min == 7.82
    assert center.center_rt_sec == pytest.approx(469.2)
    assert center.center_candidate_count == 3
    assert center.center_drift_sec == pytest.approx(1.2)
    assert center.center_decision is RtCenterDecision.RECENTERED_STABLE


def test_estimate_rt_center_excludes_far_or_incomplete_candidates():
    center = estimate_rt_center(
        _seed(7.80),
        (
            _cell("A", 7.81),
            _cell("FAR", 8.80),
            _cell("BAD", 7.82, area=0.0),
        ),
        IdentityCoherenceConfig(),
    )

    assert center.center_rt_min == 7.81
    assert center.center_candidate_count == 1
    assert center.center_decision is RtCenterDecision.RECENTERED_STABLE


def test_estimate_rt_center_excludes_forbidden_or_invalid_candidates():
    center = estimate_rt_center(
        _seed(7.80),
        (
            _cell("A", 7.81),
            _cell(
                "BACKFILL",
                7.82,
                evidence_stage=EvidenceStage.BACKFILL_ONLY,
            ),
            _cell("DUP", 7.83, duplicate_loser=True),
            _cell("BLOCKED", 7.84, blocked_reason="blocked_input"),
            _cell("BADOWNER", 7.85, owner_assignment_status="ambiguous"),
        ),
        IdentityCoherenceConfig(),
    )

    assert center.center_rt_min == 7.81
    assert center.center_candidate_count == 1
    assert center.center_decision is RtCenterDecision.RECENTERED_STABLE


def test_estimate_rt_center_marks_unstable_when_median_drift_exceeds_guard():
    config = IdentityCoherenceConfig(
        rt=RtConfig(
            seed_center_candidate_sec=60.0,
            max_center_drift_sec=10.0,
        ),
    )
    center = estimate_rt_center(
        _seed(7.80),
        (_cell("A", 8.00), _cell("B", 8.01), _cell("C", 8.02)),
        config,
    )

    assert center.center_rt_min == 7.80
    assert center.center_candidate_count == 3
    assert center.center_drift_sec > config.rt.max_center_drift_sec
    assert center.center_decision is RtCenterDecision.CENTER_UNSTABLE_REVIEW_ONLY
