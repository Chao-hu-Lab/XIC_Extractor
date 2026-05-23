from __future__ import annotations

from pathlib import Path

from xic_extractor.alignment.config import AlignmentConfig
from xic_extractor.alignment.identity_coherence_adapter import (
    IdentityCoherenceSeedSource,
    build_identity_coherence_seed_sources,
    candidate_identity_family_id,
    candidate_is_non_seed_pool_member,
)
from xic_extractor.alignment.ownership import OwnershipBuildResult
from xic_extractor.alignment.ownership_models import (
    IdentityEvent,
    OwnerAssignment,
    SampleLocalMS1Owner,
)
from xic_extractor.discovery.models import DiscoveryCandidate


def _candidate(
    candidate_id: str,
    *,
    sample_stem: str = "Sample_A",
    precursor_mz: float = 500.0,
    product_mz: float = 384.0,
    observed_loss: float = 116.0,
    best_seed_rt: float = 5.0,
    apex_rt: float | None = 5.0,
    start_rt: float | None = 4.95,
    end_rt: float | None = 5.05,
    area: float | None = 1000.0,
    height: float | None = 100.0,
    matched_tags: tuple[str, ...] = ("MeR", "dR"),
) -> DiscoveryCandidate:
    return DiscoveryCandidate(
        review_priority="HIGH",
        evidence_score=80,
        evidence_tier="A",
        ms2_support="seed",
        ms1_support="owner",
        rt_alignment="local",
        family_context="single",
        candidate_id=candidate_id,
        precursor_mz=precursor_mz,
        product_mz=product_mz,
        observed_neutral_loss_da=observed_loss,
        best_seed_rt=best_seed_rt,
        seed_event_count=2,
        ms1_peak_found=apex_rt is not None,
        ms1_apex_rt=apex_rt,
        ms1_area=area,
        ms2_product_max_intensity=10000.0,
        reason="test candidate",
        raw_file=Path(f"{sample_stem}.raw"),
        sample_stem=sample_stem,
        best_ms2_scan_id=101,
        seed_scan_ids=(101,),
        neutral_loss_tag="dR",
        configured_neutral_loss_da=116.0,
        neutral_loss_mass_error_ppm=0.0,
        rt_seed_min=best_seed_rt,
        rt_seed_max=best_seed_rt,
        ms1_search_rt_min=best_seed_rt - 0.2,
        ms1_search_rt_max=best_seed_rt + 0.2,
        ms1_seed_delta_min=0.0,
        ms1_peak_rt_start=start_rt,
        ms1_peak_rt_end=end_rt,
        ms1_height=height,
        ms1_trace_quality="clean",
        ms1_scan_support_score=0.9,
        matched_tag_count=len(matched_tags),
        matched_tag_names=matched_tags,
        primary_tag_name="dR",
    )


def _event(candidate: DiscoveryCandidate) -> IdentityEvent:
    return IdentityEvent(
        candidate_id=candidate.candidate_id,
        sample_stem=candidate.sample_stem,
        raw_file=str(candidate.raw_file),
        neutral_loss_tag=candidate.neutral_loss_tag,
        precursor_mz=candidate.precursor_mz,
        product_mz=candidate.product_mz,
        observed_neutral_loss_da=candidate.observed_neutral_loss_da,
        seed_rt=candidate.best_seed_rt,
        evidence_score=candidate.evidence_score,
        seed_event_count=candidate.seed_event_count,
    )


def _owner(candidate: DiscoveryCandidate) -> SampleLocalMS1Owner:
    return SampleLocalMS1Owner(
        owner_id=f"OWN-{candidate.candidate_id}",
        sample_stem=candidate.sample_stem,
        raw_file=str(candidate.raw_file),
        precursor_mz=candidate.precursor_mz,
        owner_apex_rt=float(candidate.ms1_apex_rt),
        owner_peak_start_rt=float(candidate.ms1_peak_rt_start),
        owner_peak_end_rt=float(candidate.ms1_peak_rt_end),
        owner_area=float(candidate.ms1_area),
        owner_height=float(candidate.ms1_height),
        primary_identity_event=_event(candidate),
        supporting_events=(),
        identity_conflict=False,
        assignment_reason="primary_identity_event",
    )


def _ownership(*owners: SampleLocalMS1Owner) -> OwnershipBuildResult:
    assignments = tuple(
        OwnerAssignment(
            candidate_id=owner.primary_identity_event.candidate_id,
            owner_id=owner.owner_id,
            assignment_status="primary",
            reason="primary_identity_event",
        )
        for owner in owners
    )
    return OwnershipBuildResult(
        owners=owners,
        assignments=assignments,
        ambiguous_records=(),
    )


def test_build_seed_sources_uses_primary_pre_backfill_owners() -> None:
    seed = _candidate("CAND-SEED")
    source = build_identity_coherence_seed_sources(
        candidates=(seed,),
        ownership=_ownership(_owner(seed)),
        alignment_config=AlignmentConfig(),
        fragment_profile_id="dna-cid-v1",
        fragment_profile_hash="hash1",
    )[0]

    assert isinstance(source, IdentityCoherenceSeedSource)
    assert source.request.request_id == "ICR000001"
    assert source.decision_id == "ICD000001"
    assert source.identity_family_id == "ICF000001"
    assert source.seed_candidate.candidate_id == "CAND-SEED"
    assert source.seed_evidence.candidate_id == "CAND-SEED"
    assert source.owner.owner_id == "OWN-CAND-SEED"
    assert source.owner_assignment_status == "primary"
    assert source.seed_gate.seed_gate_class.value == "coherent_seed"


def test_build_seed_sources_skips_owner_without_candidate_join() -> None:
    seed = _candidate("CAND-SEED")
    sources = build_identity_coherence_seed_sources(
        candidates=(),
        ownership=_ownership(_owner(seed)),
        alignment_config=AlignmentConfig(),
        fragment_profile_id="dna-cid-v1",
        fragment_profile_hash="hash1",
    )

    assert sources == ()


def test_build_seed_sources_skips_owner_without_assignment() -> None:
    seed = _candidate("CAND-SEED")
    sources = build_identity_coherence_seed_sources(
        candidates=(seed,),
        ownership=OwnershipBuildResult(
            owners=(_owner(seed),),
            assignments=(),
            ambiguous_records=(),
        ),
        alignment_config=AlignmentConfig(),
        fragment_profile_id="dna-cid-v1",
        fragment_profile_hash="hash1",
    )

    assert sources == ()


def test_candidate_pool_member_uses_metadata_before_trace_retrieval() -> None:
    seed = _candidate("CAND-SEED", sample_stem="Sample_A", best_seed_rt=5.0)
    request = build_identity_coherence_seed_sources(
        candidates=(seed,),
        ownership=_ownership(_owner(seed)),
        alignment_config=AlignmentConfig(),
        fragment_profile_id="dna-cid-v1",
        fragment_profile_hash="hash1",
    )[0].request
    nearby = _candidate("CAND-NEAR", sample_stem="Sample_B", best_seed_rt=5.5)
    far_rt = _candidate("CAND-FAR", sample_stem="Sample_B", best_seed_rt=9.0)
    same_sample = _candidate(
        "CAND-SAME",
        sample_stem="Sample_A",
        best_seed_rt=5.1,
    )
    bad_morphology = _candidate(
        "CAND-BAD",
        sample_stem="Sample_B",
        apex_rt=None,
        start_rt=None,
        end_rt=None,
        area=None,
        height=None,
    )

    assert candidate_is_non_seed_pool_member(
        request,
        nearby,
        seed_candidate=seed,
        config=AlignmentConfig(),
    )
    assert not candidate_is_non_seed_pool_member(
        request,
        far_rt,
        seed_candidate=seed,
        config=AlignmentConfig(),
    )
    assert not candidate_is_non_seed_pool_member(
        request,
        same_sample,
        seed_candidate=seed,
        config=AlignmentConfig(),
    )
    assert not candidate_is_non_seed_pool_member(
        request,
        bad_morphology,
        seed_candidate=seed,
        config=AlignmentConfig(),
    )


def test_candidate_identity_family_id_is_diagnostic_only() -> None:
    assert candidate_identity_family_id(3) == "ICF000003"
