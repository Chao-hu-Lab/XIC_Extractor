from xic_extractor.peak_detection.boundaries import BoundaryHypothesis
from xic_extractor.peak_detection.boundary_scoring import score_boundary_hypothesis


def test_boundary_score_rewards_supported_clean_boundary() -> None:
    reference = _boundary(width=0.4, scan_count=6)
    boundary = _boundary(
        sources=("candidate_interval", "derivative_zero_crossing"),
        width=0.4,
        scan_count=6,
    )

    score = score_boundary_hypothesis(
        boundary,
        reference,
        baseline_score=0.75,
        trace_continuity=0.90,
    )

    assert score.score == 100
    assert score.support_labels == (
        "candidate_interval",
        "baseline_supported",
        "trace_continuity_ok",
        "scan_support_ok",
        "width_near_candidate",
    )
    assert score.concern_labels == ()


def test_boundary_score_flags_weak_boundary_evidence() -> None:
    reference = _boundary(width=0.4, scan_count=6)
    boundary = _boundary(width=1.0, scan_count=2)

    score = score_boundary_hypothesis(
        boundary,
        reference,
        baseline_score=0.05,
        trace_continuity=0.20,
    )

    assert score.score == 0
    assert score.support_labels == ()
    assert score.concern_labels == (
        "low_baseline_signal",
        "low_trace_continuity",
        "low_scan_support",
        "width_extreme",
    )


def test_boundary_score_treats_non_finite_metrics_as_unavailable() -> None:
    boundary = _boundary(width=0.4, scan_count=6)

    score = score_boundary_hypothesis(
        boundary,
        boundary,
        baseline_score=float("nan"),
        trace_continuity=float("inf"),
    )

    assert score.score == 65
    assert score.support_labels == (
        "scan_support_ok",
        "width_near_candidate",
    )
    assert score.concern_labels == (
        "baseline_unavailable",
        "trace_continuity_unavailable",
    )


def _boundary(
    *,
    sources: tuple[str, ...] = ("half_height",),
    width: float,
    scan_count: int,
) -> BoundaryHypothesis:
    return BoundaryHypothesis(
        boundary_id="",
        sources=sources,
        left_index=0,
        right_index=scan_count,
        rt_left_min=8.0,
        rt_apex_min=8.2,
        rt_right_min=8.0 + width,
        width_min=width,
        area_raw_counts_seconds=100.0,
        scan_count=scan_count,
    )
