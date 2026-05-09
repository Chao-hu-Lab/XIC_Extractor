from pathlib import Path

from xic_extractor.discovery.feature_family import assign_feature_families
from xic_extractor.discovery.models import DiscoveryCandidate


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


def _candidate(
    *,
    candidate_id: str,
    sample_stem: str = "Sample",
    precursor_mz: float = 258.1085,
    product_mz: float = 142.0611,
    apex_rt: float | None = 7.84,
    peak_start: float | None = 7.70,
    peak_end: float | None = 7.98,
    ms1_peak_found: bool = True,
) -> DiscoveryCandidate:
    return DiscoveryCandidate(
        review_priority="MEDIUM",
        candidate_id=candidate_id,
        precursor_mz=precursor_mz,
        product_mz=product_mz,
        observed_neutral_loss_da=116.0474,
        best_seed_rt=apex_rt or 7.84,
        seed_event_count=1,
        ms1_peak_found=ms1_peak_found,
        ms1_apex_rt=apex_rt,
        ms1_area=1000.0 if ms1_peak_found else None,
        ms2_product_max_intensity=5000.0,
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
