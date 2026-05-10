from dataclasses import replace
from itertools import permutations
from pathlib import Path

from xic_extractor.discovery.evidence_config import (
    DEFAULT_EVIDENCE_PROFILE,
    DiscoveryEvidenceProfile,
)
from xic_extractor.discovery.feature_family import assign_feature_families
from xic_extractor.discovery.models import (
    DiscoveryCandidate,
    DiscoverySettings,
    NeutralLossProfile,
)


def test_assign_feature_families_groups_candidates_sharing_ms1_peak() -> None:
    first = _candidate(
        candidate_id="Sample#10",
        precursor_mz=244.130,
        product_mz=128.082,
        apex_rt=12.228,
        peak_start=12.104,
        peak_end=12.306,
    )
    second = _candidate(
        candidate_id="Sample#20",
        precursor_mz=483.221,
        product_mz=367.174,
        apex_rt=12.228,
        peak_start=12.104,
        peak_end=12.306,
    )

    assigned = assign_feature_families((second, first))

    assert {candidate.feature_family_id for candidate in assigned} == {"Sample@F0001"}
    assert [candidate.feature_family_size for candidate in assigned] == [2, 2]
    assert [candidate.candidate_id for candidate in assigned] == [
        "Sample#20",
        "Sample#10",
    ]


def test_assign_feature_families_keeps_distinct_ms1_peaks_separate() -> None:
    assigned = assign_feature_families(
        (
            _candidate(
                candidate_id="Sample#10",
                apex_rt=7.80,
                peak_start=7.70,
                peak_end=7.88,
            ),
            _candidate(
                candidate_id="Sample#20",
                apex_rt=8.04,
                peak_start=7.96,
                peak_end=8.14,
            ),
        )
    )

    assert [candidate.feature_family_id for candidate in assigned] == [
        "Sample@F0001",
        "Sample@F0002",
    ]
    assert [candidate.feature_family_size for candidate in assigned] == [1, 1]


def test_assign_feature_families_does_not_group_missing_ms1_peaks() -> None:
    assigned = assign_feature_families(
        (
            _candidate(candidate_id="Sample#10", ms1_peak_found=False),
            _candidate(candidate_id="Sample#20", ms1_peak_found=False),
        )
    )

    assert [candidate.feature_family_id for candidate in assigned] == [
        "Sample@F0001",
        "Sample@F0002",
    ]
    assert [candidate.feature_family_size for candidate in assigned] == [1, 1]


def test_assign_feature_superfamilies_groups_close_overlapping_ms1_peaks() -> None:
    assigned = assign_feature_families(
        (
            _candidate(
                candidate_id="Sample#10",
                apex_rt=13.100,
                peak_start=12.90,
                peak_end=13.30,
            ),
            _candidate(
                candidate_id="Sample#20",
                apex_rt=13.180,
                peak_start=13.00,
                peak_end=13.36,
            ),
        )
    )

    assert {candidate.feature_superfamily_id for candidate in assigned} == {
        "Sample@SF0001"
    }
    assert [candidate.feature_superfamily_size for candidate in assigned] == [2, 2]
    assert {candidate.feature_superfamily_confidence for candidate in assigned} == {
        "MEDIUM"
    }
    assert {candidate.feature_superfamily_evidence for candidate in assigned} == {
        "peak_boundary_overlap;apex_close"
    }


def test_assign_feature_superfamilies_selects_one_representative() -> None:
    assigned = assign_feature_families(
        (
            _candidate(
                candidate_id="Sample#10",
                review_priority="MEDIUM",
                seed_event_count=1,
                ms2_product_max_intensity=9000.0,
                apex_rt=13.100,
                peak_start=12.90,
                peak_end=13.30,
            ),
            _candidate(
                candidate_id="Sample#20",
                review_priority="HIGH",
                seed_event_count=2,
                ms2_product_max_intensity=1000.0,
                apex_rt=13.180,
                peak_start=13.00,
                peak_end=13.36,
            ),
        )
    )

    roles = {
        candidate.candidate_id: candidate.feature_superfamily_role
        for candidate in assigned
    }
    assert roles == {
        "Sample#10": "member",
        "Sample#20": "representative",
    }


def test_assign_feature_superfamilies_keeps_distant_or_weak_overlap_separate() -> None:
    assigned = assign_feature_families(
        (
            _candidate(
                candidate_id="Sample#10",
                apex_rt=13.100,
                peak_start=12.90,
                peak_end=13.00,
            ),
            _candidate(
                candidate_id="Sample#20",
                apex_rt=13.300,
                peak_start=13.20,
                peak_end=13.36,
            ),
        )
    )

    assert [candidate.feature_superfamily_id for candidate in assigned] == [
        "Sample@SF0001",
        "Sample@SF0002",
    ]
    assert [candidate.feature_superfamily_size for candidate in assigned] == [1, 1]
    assert [candidate.feature_superfamily_role for candidate in assigned] == [
        "representative",
        "representative",
    ]


def test_assign_feature_superfamilies_does_not_chain_across_broad_rt_region() -> None:
    assigned = assign_feature_families(
        (
            _candidate(
                candidate_id="Sample#10",
                apex_rt=13.00,
                peak_start=12.90,
                peak_end=13.20,
            ),
            _candidate(
                candidate_id="Sample#20",
                apex_rt=13.10,
                peak_start=12.98,
                peak_end=13.30,
            ),
            _candidate(
                candidate_id="Sample#30",
                apex_rt=13.20,
                peak_start=13.08,
                peak_end=13.40,
            ),
        )
    )

    assert assigned[0].feature_superfamily_id == assigned[1].feature_superfamily_id
    assert assigned[2].feature_superfamily_id != assigned[0].feature_superfamily_id
    assert [candidate.feature_superfamily_size for candidate in assigned] == [2, 2, 1]


def test_assign_feature_superfamilies_is_stable_across_input_order() -> None:
    candidates = (
        _candidate(
            candidate_id="Sample#10",
            apex_rt=13.00,
            peak_start=12.90,
            peak_end=13.20,
        ),
        _candidate(
            candidate_id="Sample#20",
            apex_rt=13.10,
            peak_start=12.98,
            peak_end=13.30,
        ),
        _candidate(
            candidate_id="Sample#30",
            apex_rt=13.20,
            peak_start=13.08,
            peak_end=13.40,
        ),
    )

    observed = {
        tuple(
            sorted(
                (
                    candidate.candidate_id,
                    candidate.feature_superfamily_id,
                    candidate.feature_superfamily_size,
                    candidate.feature_superfamily_role,
                )
                for candidate in assign_feature_families(order)
            )
        )
        for order in permutations(candidates)
    }

    assert len(observed) == 1


def test_assign_feature_families_assigns_evidence_score_and_tier() -> None:
    assigned = assign_feature_families(
        (
            _candidate(
                candidate_id="Sample#10",
                review_priority="HIGH",
                seed_event_count=3,
                ms2_product_max_intensity=150000.0,
                apex_rt=13.100,
                peak_start=12.90,
                peak_end=13.30,
                ms1_area=20_000_000.0,
            ),
            _candidate(
                candidate_id="Sample#20",
                review_priority="MEDIUM",
                seed_event_count=1,
                ms2_product_max_intensity=5000.0,
                apex_rt=13.500,
                peak_start=13.40,
                peak_end=13.60,
                ms1_area=50_000.0,
            ),
            _candidate(
                candidate_id="Sample#30",
                review_priority="LOW",
                ms1_peak_found=False,
                seed_event_count=1,
                ms2_product_max_intensity=500.0,
                ms1_area=None,
            ),
        )
    )

    by_id = {candidate.candidate_id: candidate for candidate in assigned}
    assert by_id["Sample#10"].evidence_tier == "A"
    assert by_id["Sample#10"].evidence_score >= 80
    assert by_id["Sample#10"].ms2_support == "strong"
    assert by_id["Sample#10"].ms1_support == "strong"
    assert by_id["Sample#10"].rt_alignment == "aligned"
    assert by_id["Sample#10"].family_context == "singleton"
    assert by_id["Sample#20"].evidence_tier in {"B", "C"}
    assert by_id["Sample#20"].ms2_support == "weak"
    assert by_id["Sample#20"].ms1_support == "moderate"
    assert by_id["Sample#30"].evidence_tier == "E"
    assert by_id["Sample#30"].ms1_support == "missing"
    assert by_id["Sample#30"].rt_alignment == "missing"


def test_assign_feature_families_labels_superfamily_context() -> None:
    assigned = assign_feature_families(
        (
            _candidate(
                candidate_id="Sample#10",
                review_priority="MEDIUM",
                apex_rt=13.100,
                peak_start=12.90,
                peak_end=13.30,
            ),
            _candidate(
                candidate_id="Sample#20",
                review_priority="HIGH",
                seed_event_count=2,
                apex_rt=13.180,
                peak_start=13.00,
                peak_end=13.36,
            ),
        )
    )

    contexts = {
        candidate.candidate_id: candidate.family_context
        for candidate in assigned
    }
    assert contexts == {
        "Sample#10": "member",
        "Sample#20": "representative",
    }


def test_assign_feature_families_threads_custom_evidence_settings() -> None:
    default_assigned = assign_feature_families((_candidate(candidate_id="Sample#10"),))
    custom_settings = DiscoverySettings(
        neutral_loss_profile=NeutralLossProfile("DNA_dR", 116.0474),
        evidence_profile=DiscoveryEvidenceProfile(
            name="default",
            weights=replace(
                DEFAULT_EVIDENCE_PROFILE.weights,
                ms1_peak_present=30,
            ),
            thresholds=DEFAULT_EVIDENCE_PROFILE.thresholds,
        ),
    )

    custom_assigned = assign_feature_families(
        (_candidate(candidate_id="Sample#10"),),
        settings=custom_settings,
    )

    assert custom_assigned[0].evidence_score == default_assigned[0].evidence_score + 5


def _candidate(
    *,
    candidate_id: str,
    review_priority: str = "MEDIUM",
    sample_stem: str = "Sample",
    precursor_mz: float = 258.1085,
    product_mz: float = 142.0611,
    apex_rt: float | None = 7.84,
    peak_start: float | None = 7.70,
    peak_end: float | None = 7.98,
    ms1_peak_found: bool = True,
    seed_event_count: int = 1,
    ms2_product_max_intensity: float = 5000.0,
    ms1_area: float | None = None,
) -> DiscoveryCandidate:
    return DiscoveryCandidate(
        review_priority=review_priority,  # type: ignore[arg-type]
        evidence_score=0,
        evidence_tier="E",
        ms2_support="weak",
        ms1_support="missing",
        rt_alignment="missing",
        family_context="singleton",
        candidate_id=candidate_id,
        precursor_mz=precursor_mz,
        product_mz=product_mz,
        observed_neutral_loss_da=116.0474,
        best_seed_rt=apex_rt or 7.84,
        seed_event_count=seed_event_count,
        ms1_peak_found=ms1_peak_found,
        ms1_apex_rt=apex_rt,
        ms1_area=(
            (1000.0 if ms1_peak_found else None)
            if ms1_area is None
            else ms1_area
        ),
        ms2_product_max_intensity=ms2_product_max_intensity,
        reason="single MS2 NL seed; MS1 peak found",
        raw_file=Path("C:/data/Sample.raw"),
        sample_stem=sample_stem,
        best_ms2_scan_id=10,
        seed_scan_ids=(10,),
        neutral_loss_tag="DNA_dR",
        configured_neutral_loss_da=116.0474,
        neutral_loss_mass_error_ppm=0.0,
        rt_seed_min=apex_rt or 7.84,
        rt_seed_max=apex_rt or 7.84,
        ms1_search_rt_min=7.60,
        ms1_search_rt_max=8.10,
        ms1_seed_delta_min=0.0 if ms1_peak_found else None,
        ms1_peak_rt_start=peak_start if ms1_peak_found else None,
        ms1_peak_rt_end=peak_end if ms1_peak_found else None,
        ms1_height=100.0 if ms1_peak_found else None,
        ms1_trace_quality="clean" if ms1_peak_found else "missing",
    )
