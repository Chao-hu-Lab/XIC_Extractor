import pytest

from xic_extractor.alignment.identity_coherence.models import (
    CellCandidateEvidence,
    IdentityCoherenceConfig,
    SeedCandidateEvidence,
)
from xic_extractor.alignment.identity_coherence.schema import (
    EvidenceStage,
    WidthStatus,
)
from xic_extractor.alignment.identity_coherence.width import (
    assess_width_against_prototype,
    estimate_prototype_width,
)


def _seed_candidate(
    candidate_id: str,
    *,
    evidence_stage: EvidenceStage | str = EvidenceStage.PRE_BACKFILL,
) -> SeedCandidateEvidence:
    return SeedCandidateEvidence(
        candidate_id=candidate_id,
        precursor_mz=500.0,
        product_mz=384.0,
        cid_observed_loss_da=116.0,
        fragment_tags=("dR", "MeR"),
        best_seed_rt=7.80,
        ms1_scan_support_score=0.75,
        evidence_stage=evidence_stage,
    )


def _candidate(
    candidate_id: str,
    *,
    sample_id: str = "S2",
    start: float = 7.75,
    apex: float = 7.80,
    end: float = 7.85,
    duplicate_loser: bool = False,
    owner_assignment_status: str = "primary",
    blocked_reason: str = "",
    data_quality_reason: str = "",
    evidence_stage: EvidenceStage | str = EvidenceStage.PRE_BACKFILL,
) -> CellCandidateEvidence:
    return CellCandidateEvidence(
        sample_id=sample_id,
        candidate_evidence=_seed_candidate(candidate_id, evidence_stage=evidence_stage),
        apex_rt=apex,
        peak_start_rt=start,
        peak_end_rt=end,
        area=100.0,
        height=20.0,
        point_count=9,
        owner_assignment_status=owner_assignment_status,
        duplicate_loser=duplicate_loser,
        blocked_reason=blocked_reason,
        data_quality_reason=data_quality_reason,
    )


def test_estimate_prototype_width_uses_median_width_seconds():
    config = IdentityCoherenceConfig()
    result = estimate_prototype_width(
        (
            _candidate("C1", start=7.75, end=7.85),
            _candidate("C2", start=7.74, end=7.86),
            _candidate("C3", start=7.76, end=7.84),
        ),
        config,
        seed_sample_id="S1",
        seed_rt_min=7.80,
        center_rt_min=7.80,
    )

    assert result.width_status is WidthStatus.PASS
    assert result.prototype_width_sec == pytest.approx(6.0)
    assert result.candidate_count == 3
    assert result.non_seed_candidate_count == 3
    assert result.width_candidate_ids == ("C1", "C2", "C3")


def test_estimate_prototype_width_requires_minimum_candidates():
    config = IdentityCoherenceConfig()
    result = estimate_prototype_width(
        (
            _candidate("C1", start=7.75, end=7.85),
            _candidate("C2", start=7.76, end=7.84),
        ),
        config,
        seed_sample_id="S1",
        seed_rt_min=7.80,
        center_rt_min=7.80,
    )

    assert result.width_status is WidthStatus.NOT_ASSESSED
    assert result.prototype_width_sec is None
    assert result.candidate_count == 2


def test_estimate_prototype_width_excludes_seed_from_reference_and_minimum():
    config = IdentityCoherenceConfig()
    result = estimate_prototype_width(
        (
            _candidate("SEED", sample_id="S1", start=7.75, end=7.85),
            _candidate("C1", sample_id="S2", start=7.75, end=7.85),
            _candidate("C2", sample_id="S3", start=7.76, end=7.84),
        ),
        config,
        seed_sample_id="S1",
        seed_rt_min=7.80,
        center_rt_min=7.80,
    )

    assert result.width_status is WidthStatus.NOT_ASSESSED
    assert result.prototype_width_sec is None
    assert result.candidate_count == 2
    assert result.non_seed_candidate_count == 2
    assert result.width_candidate_ids == ("C1", "C2")


def test_estimate_prototype_width_excludes_forbidden_and_bad_candidates():
    config = IdentityCoherenceConfig()
    result = estimate_prototype_width(
        (
            _candidate("GOOD1", start=7.75, end=7.85),
            _candidate("GOOD2", start=7.76, end=7.84),
            _candidate("GOOD3", start=7.74, end=7.86),
            _candidate("BACKFILL", evidence_stage=EvidenceStage.BACKFILL_ONLY),
            _candidate("DUP", duplicate_loser=True),
            _candidate("AMB", owner_assignment_status="ambiguous"),
            _candidate("BLOCK", blocked_reason="raw_open_failed"),
            _candidate("DQ", data_quality_reason="invalid_peak_morphology"),
            _candidate("FAR_CENTER", apex=9.80, start=9.75, end=9.85),
            _candidate("FAR_SEED", apex=8.60, start=8.55, end=8.65),
        ),
        config,
        seed_sample_id="S1",
        seed_rt_min=7.80,
        center_rt_min=7.80,
    )

    assert result.width_status is WidthStatus.PASS
    assert result.width_candidate_ids == ("GOOD1", "GOOD2", "GOOD3")


def test_estimate_prototype_width_accepts_public_string_stage_values():
    config = IdentityCoherenceConfig()
    result = estimate_prototype_width(
        (
            _candidate("GOOD1", start=7.75, end=7.85),
            _candidate("GOOD2", start=7.76, end=7.84),
            _candidate("GOOD3", start=7.74, end=7.86),
            _candidate("BACKFILL", evidence_stage="backfill_only"),
        ),
        config,
        seed_sample_id="S1",
        seed_rt_min=7.80,
        center_rt_min=7.80,
    )

    assert result.width_status is WidthStatus.PASS
    assert result.width_candidate_ids == ("GOOD1", "GOOD2", "GOOD3")


def test_assess_width_passes_inside_ratio_range():
    result = assess_width_against_prototype(
        _candidate("C1", start=7.75, end=7.85),
        prototype_width_sec=6.0,
        config=IdentityCoherenceConfig(),
    )

    assert result.width_status is WidthStatus.PASS
    assert result.width_ratio_to_prototype == pytest.approx(1.0)


def test_assess_width_fails_outside_ratio_range():
    result = assess_width_against_prototype(
        _candidate("WIDE", start=7.675, end=7.925),
        prototype_width_sec=6.0,
        config=IdentityCoherenceConfig(),
    )

    assert result.width_status is WidthStatus.FAIL
    assert result.width_ratio_to_prototype == pytest.approx(2.5)


def test_assess_width_not_assessed_without_prototype_width():
    result = assess_width_against_prototype(
        _candidate("C1"),
        prototype_width_sec=None,
        config=IdentityCoherenceConfig(),
    )

    assert result.width_status is WidthStatus.NOT_ASSESSED
    assert result.width_ratio_to_prototype is None
