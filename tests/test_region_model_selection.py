from xic_extractor.peak_detection.region_model_selection import (
    RegionBoundaryEvidence,
    decide_region_selection,
)


def test_missing_boundaries_are_visible_insufficient_evidence() -> None:
    decision = decide_region_selection(())

    assert decision.shadow_status == "skipped_no_boundary"
    assert decision.shadow_verdict == "insufficient_evidence"
    assert "no boundary" in decision.review_reason


def test_missing_selected_candidate_is_visible() -> None:
    decision = decide_region_selection(
        (
            _boundary(
                "candidate-a|candidate",
                candidate_id="candidate-a",
                selected=False,
            ),
        )
    )

    assert decision.shadow_status == "skipped_no_candidate"
    assert decision.shadow_verdict == "insufficient_evidence"


def test_selected_candidate_with_low_scan_support_is_skipped() -> None:
    decision = decide_region_selection(
        (
            _boundary(
                "candidate-a|candidate",
                candidate_id="candidate-a",
                scan_count=2,
                selected=True,
            ),
        )
    )

    assert decision.shadow_status == "skipped_low_scan_support"
    assert decision.shadow_verdict == "insufficient_evidence"


def test_same_apex_wider_boundary_is_preferred_when_area_gain_is_large() -> None:
    decision = decide_region_selection(
        (
            _boundary(
                "candidate-a|candidate",
                candidate_id="candidate-a",
                selected=True,
                source="candidate_interval",
                area=100.0,
                score=55,
            ),
            _boundary(
                "candidate-a|baseline",
                candidate_id="candidate-a",
                selected=True,
                source="baseline_return",
                area=170.0,
                score=56,
                left=9.8,
                right=10.5,
            ),
        )
    )

    assert decision.shadow_status == "evaluated"
    assert decision.shadow_verdict == "wider_boundary_preferred"
    assert decision.area_ratio == 1.7
    assert decision.shadow_boundary_id == "candidate-a|baseline"


def test_neighbor_apex_requires_non_cwt_only_support() -> None:
    decision = decide_region_selection(
        (
            _boundary(
                "current|candidate",
                candidate_id="current",
                selected=True,
                score=60,
                area=100.0,
            ),
            _boundary(
                "cwt-neighbor|candidate",
                candidate_id="cwt-neighbor",
                selected=False,
                proposal_sources=("centwave_cwt",),
                score=95,
                area=180.0,
                apex=10.8,
                left=10.7,
                right=10.9,
            ),
        )
    )

    assert decision.shadow_status == "evaluated"
    assert decision.shadow_verdict == "current_supported"


def test_neighbor_apex_preferred_when_non_cwt_score_is_much_higher() -> None:
    decision = decide_region_selection(
        (
            _boundary(
                "current|candidate",
                candidate_id="current",
                selected=True,
                score=60,
                area=100.0,
            ),
            _boundary(
                "neighbor|candidate",
                candidate_id="neighbor",
                selected=False,
                proposal_sources=("local_minimum",),
                score=78,
                area=120.0,
                apex=10.5,
                left=10.4,
                right=10.7,
            ),
        )
    )

    assert decision.shadow_verdict == "neighbor_apex_preferred"
    assert decision.shadow_boundary_id == "neighbor|candidate"


def test_shallow_local_minimum_split_inside_wide_envelope_suggests_merge() -> None:
    decision = decide_region_selection(
        (
            _boundary(
                "left|candidate",
                candidate_id="left",
                selected=True,
                source="candidate_interval",
                proposal_sources=("local_minimum",),
                area=100.0,
                score=60,
                apex=10.0,
                left=9.95,
                right=10.15,
            ),
            _boundary(
                "left|wide",
                candidate_id="left",
                selected=True,
                source="baseline_return",
                proposal_sources=("local_minimum",),
                area=190.0,
                score=61,
                apex=10.0,
                left=9.9,
                right=10.6,
            ),
            _boundary(
                "right|candidate",
                candidate_id="right",
                selected=False,
                source="candidate_interval",
                proposal_sources=("local_minimum",),
                area=85.0,
                score=58,
                apex=10.35,
                left=10.25,
                right=10.5,
            ),
        )
    )

    assert decision.shadow_verdict == "merge_suggested"
    assert decision.shadow_boundary_id == "left|wide"


def test_adjacent_wis_intervals_with_small_area_gain_suggest_merge() -> None:
    decision = decide_region_selection(
        (
            _boundary(
                "left|candidate",
                candidate_id="left",
                selected=True,
                source="candidate_interval",
                proposal_sources=("local_minimum",),
                area=100.0,
                score=70,
                apex=10.0,
                left=9.9,
                right=10.2,
                nonoverlap_selected=True,
            ),
            _boundary(
                "right|candidate",
                candidate_id="right",
                selected=False,
                source="candidate_interval",
                proposal_sources=("local_minimum",),
                area=10.0,
                score=55,
                apex=10.25,
                left=10.22,
                right=10.35,
                nonoverlap_selected=True,
            ),
        )
    )

    assert decision.shadow_verdict == "merge_suggested"
    assert decision.area_ratio == 1.1
    assert decision.selected_interval_count == 2
    assert decision.selected_interval_gap_max_min == 0.02
    assert decision.selected_interval_total_score == 125
    assert decision.best_single_boundary_score == 70
    assert decision.current_scan_count == 5
    assert decision.shadow_scan_count == 10


def test_multi_interval_merge_uses_dominant_area_apex_as_shadow_rt() -> None:
    decision = decide_region_selection(
        (
            _boundary(
                "left|candidate",
                candidate_id="left",
                selected=False,
                source="candidate_interval",
                proposal_sources=("local_minimum",),
                area=10.0,
                score=80,
                apex=25.9,
                left=25.84,
                right=25.91,
                nonoverlap_selected=True,
            ),
            _boundary(
                "right|candidate",
                candidate_id="right",
                selected=True,
                source="candidate_interval",
                proposal_sources=("local_minimum",),
                area=100.0,
                score=70,
                apex=26.15,
                left=25.94,
                right=26.32,
                nonoverlap_selected=True,
            ),
        )
    )

    assert decision.shadow_verdict == "merge_suggested"
    assert decision.shadow_rt_apex_min == 26.15
    assert decision.selected_interval_gap_max_min == 0.03


def test_supported_nonoverlap_intervals_can_support_split() -> None:
    decision = decide_region_selection(
        (
            _boundary(
                "wide|candidate",
                candidate_id="wide",
                selected=True,
                source="candidate_interval",
                area=220.0,
                score=70,
                left=9.8,
                right=10.8,
            ),
            _boundary(
                "left|candidate",
                candidate_id="left",
                selected=False,
                nonoverlap_selected=True,
                source="candidate_interval",
                area=110.0,
                score=55,
                apex=10.0,
                left=9.85,
                right=10.2,
            ),
            _boundary(
                "right|candidate",
                candidate_id="right",
                selected=False,
                nonoverlap_selected=True,
                source="candidate_interval",
                area=120.0,
                score=55,
                apex=10.55,
                left=10.35,
                right=10.75,
            ),
        )
    )

    assert decision.shadow_verdict == "split_supported"
    assert decision.shadow_boundary_id == "left|candidate;right|candidate"
    assert decision.selected_interval_count == 2
    assert decision.best_single_boundary_score == 70


def _boundary(
    boundary_id: str,
    *,
    candidate_id: str,
    selected: bool,
    source: str = "candidate_interval",
    proposal_sources: tuple[str, ...] = ("local_minimum",),
    area: float = 100.0,
    score: int = 60,
    scan_count: int = 5,
    apex: float = 10.0,
    left: float = 9.9,
    right: float = 10.2,
    nonoverlap_selected: bool = False,
) -> RegionBoundaryEvidence:
    return RegionBoundaryEvidence(
        boundary_id=boundary_id,
        candidate_id=candidate_id,
        proposal_sources=proposal_sources,
        boundary_sources=(source,),
        selected_candidate=selected,
        is_candidate_interval=source == "candidate_interval",
        nonoverlap_selected=nonoverlap_selected,
        rt_left_min=left,
        rt_apex_min=apex,
        rt_right_min=right,
        area_raw_counts_seconds=area,
        boundary_score=score,
        scan_count=scan_count,
        support_labels=("scan_support_ok",),
        concern_labels=(),
    )
