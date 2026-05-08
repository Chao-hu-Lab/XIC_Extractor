import math

import pytest

from xic_extractor.ms2_trace_evidence import MS2TracePoint, summarize_ms2_trace


def test_two_aligned_strict_product_points_yield_strong_trace() -> None:
    evidence = summarize_ms2_trace(
        (
            MS2TracePoint(
                rt=10.00,
                intensity=100.0,
                base_ratio=0.4,
                observed_loss_error_ppm=4.0,
            ),
            MS2TracePoint(
                rt=10.10,
                intensity=200.0,
                base_ratio=0.8,
                observed_loss_error_ppm=3.0,
            ),
        ),
        candidate_apex_rt=10.08,
        trigger_scan_count=2,
    )

    assert evidence.product_point_count == 2
    assert evidence.product_apex_rt == pytest.approx(10.10)
    assert evidence.product_apex_delta_min == pytest.approx(0.02)
    assert evidence.product_height == pytest.approx(200.0)
    assert evidence.product_area == pytest.approx(15.0)
    assert evidence.trace_continuity == pytest.approx(1.0)
    assert evidence.strength == "strong"


def test_one_aligned_strict_product_point_yields_moderate_trace() -> None:
    evidence = summarize_ms2_trace(
        (
            MS2TracePoint(
                rt=10.02,
                intensity=100.0,
                base_ratio=0.5,
                observed_loss_error_ppm=5.0,
            ),
        ),
        candidate_apex_rt=10.00,
        trigger_scan_count=1,
    )

    assert evidence.product_point_count == 1
    assert evidence.product_apex_rt == pytest.approx(10.02)
    assert evidence.product_apex_delta_min == pytest.approx(0.02)
    assert evidence.product_height == pytest.approx(100.0)
    assert evidence.product_area is None
    assert evidence.trace_continuity == pytest.approx(1.0)
    assert evidence.strength == "moderate"


def test_far_strict_product_point_yields_weak_trace() -> None:
    evidence = summarize_ms2_trace(
        (
            MS2TracePoint(
                rt=10.30,
                intensity=100.0,
                base_ratio=0.5,
                observed_loss_error_ppm=5.0,
            ),
        ),
        candidate_apex_rt=10.00,
        trigger_scan_count=1,
    )

    assert evidence.product_point_count == 1
    assert evidence.product_apex_delta_min == pytest.approx(0.30)
    assert evidence.trace_continuity == pytest.approx(1.0)
    assert evidence.strength == "weak"


def test_trigger_without_strict_product_points_yields_none_trace() -> None:
    evidence = summarize_ms2_trace(
        (),
        candidate_apex_rt=10.00,
        trigger_scan_count=2,
    )

    assert evidence.product_point_count == 0
    assert evidence.product_apex_rt is None
    assert evidence.product_apex_delta_min is None
    assert evidence.product_height is None
    assert evidence.product_area is None
    assert evidence.trace_continuity == pytest.approx(0.0)
    assert evidence.strength == "none"


def test_no_trigger_yields_unknown_continuity() -> None:
    evidence = summarize_ms2_trace(
        (),
        candidate_apex_rt=10.00,
        trigger_scan_count=0,
    )

    assert evidence.trace_continuity is None
    assert evidence.strength == "none"


def test_duplicate_or_unsorted_rt_points_do_not_break_summary() -> None:
    evidence = summarize_ms2_trace(
        (
            MS2TracePoint(
                rt=10.20,
                intensity=100.0,
                base_ratio=0.4,
                observed_loss_error_ppm=4.0,
            ),
            MS2TracePoint(
                rt=10.00,
                intensity=80.0,
                base_ratio=0.3,
                observed_loss_error_ppm=6.0,
            ),
            MS2TracePoint(
                rt=10.00,
                intensity=120.0,
                base_ratio=0.5,
                observed_loss_error_ppm=3.0,
            ),
        ),
        candidate_apex_rt=10.00,
        trigger_scan_count=3,
    )

    assert evidence.product_point_count == 3
    assert evidence.product_apex_rt == pytest.approx(10.00)
    assert evidence.product_height == pytest.approx(120.0)
    assert evidence.product_area is not None
    assert math.isfinite(evidence.product_area)
    assert evidence.product_area >= 0.0
    assert evidence.strength == "strong"
