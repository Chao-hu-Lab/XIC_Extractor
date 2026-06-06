import numpy as np
import pytest

from xic_extractor.peak_detection.selected_envelope import (
    SelectedEnvelopePolicy,
    _morphology_trace,
    evaluate_selected_envelope_boundary,
)


def _trace(residual: list[float]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    rt = np.arange(float(len(residual)), dtype=float)
    baseline = np.full(len(residual), 10.0)
    intensity = baseline + np.asarray(residual, dtype=float)
    return rt, intensity, baseline


def _evaluate(
    residual: list[float],
    *,
    apex_rt: float,
    resolver_start: float,
    resolver_end: float,
    context_start: float = 0.0,
    context_end: float | None = None,
    policy: SelectedEnvelopePolicy | None = None,
    blank_like_context: bool = False,
):
    rt, intensity, baseline = _trace(residual)
    return evaluate_selected_envelope_boundary(
        rt,
        intensity,
        baseline,
        selected_apex_rt=apex_rt,
        resolver_rt_start=resolver_start,
        resolver_rt_end=resolver_end,
        quantitation_context_rt_start=context_start,
        quantitation_context_rt_end=(
            float(len(residual) - 1) if context_end is None else context_end
        ),
        selected_candidate_id="candidate-001",
        policy=policy,
        legacy_resolver_provenance="local_minimum",
        blank_like_context=blank_like_context,
    )


def test_clean_clipped_single_peak_recovers_full_baseline_envelope() -> None:
    result = _evaluate(
        [0, 0, 2, 10, 30, 50, 30, 10, 2, 0, 0],
        apex_rt=5.0,
        resolver_start=4.0,
        resolver_end=6.0,
    )

    assert result.selected_boundary_mode == "selected_full_envelope"
    assert result.boundary_change_class == "flank_recovered"
    assert result.row_boundary_decision == "accept_candidate"
    assert result.selected_candidate_id == "candidate-001"
    assert result.policy_snapshot == SelectedEnvelopePolicy()
    assert result.resolved_baseline_return_threshold == pytest.approx(1.0)
    assert result.resolver_interval.rt_start_min == pytest.approx(4.0)
    assert result.resolver_interval.rt_end_min == pytest.approx(6.0)
    assert result.selected_envelope_interval.rt_start_min == pytest.approx(2.0)
    assert result.selected_envelope_interval.rt_end_min == pytest.approx(8.0)
    assert result.asls_area_selected_envelope > result.asls_area_old_interval
    assert result.area_delta_ratio is not None
    assert result.area_delta_ratio > 0.0
    assert result.legacy_resolver_provenance == "local_minimum"
    assert "baseline_return" in result.boundary_evidence_sources


def test_clean_full_single_peak_keeps_resolver_interval() -> None:
    result = _evaluate(
        [0, 0, 2, 10, 30, 50, 30, 10, 2, 0, 0],
        apex_rt=5.0,
        resolver_start=2.0,
        resolver_end=8.0,
    )

    assert result.selected_boundary_mode == "resolver_interval"
    assert result.boundary_change_class == "no_change"
    assert result.row_boundary_decision == "accept_candidate"
    assert result.selected_envelope_interval == result.resolver_interval
    assert result.area_delta_ratio == pytest.approx(0.0)


def test_short_internal_dip_is_bridged_within_same_peak_envelope() -> None:
    result = _evaluate(
        [0, 0, 2, 12, 30, 50, 18, 0, 16, 24, 14, 2, 0, 0],
        apex_rt=5.0,
        resolver_start=4.0,
        resolver_end=6.0,
    )

    assert result.selected_boundary_mode == "selected_full_envelope"
    assert result.boundary_change_class == "internal_dip_bridged"
    assert result.row_boundary_decision == "accept_candidate"
    assert result.selected_envelope_interval.rt_start_min == pytest.approx(2.0)
    assert result.selected_envelope_interval.rt_end_min == pytest.approx(11.0)
    assert "internal_dip_bridge" in result.boundary_evidence_sources
    assert result.asls_area_selected_envelope > result.asls_area_old_interval


def test_gaussian_15_morphology_trace_spans_raw_one_scan_dip() -> None:
    core = [1, 3, 8, 16, 28, 40, 52, 40, 22, 0, 20, 30, 18, 8, 3, 1]
    residual = ([0] * 12) + core + ([0] * 12)
    raw_dip_index = 12 + core.index(0)

    result = _evaluate(
        residual,
        apex_rt=18.0,
        resolver_start=17.0,
        resolver_end=19.0,
        policy=SelectedEnvelopePolicy(max_envelope_width_min=40.0),
    )

    assert result.selected_boundary_mode == "selected_full_envelope"
    assert result.boundary_change_class == "flank_recovered"
    assert result.row_boundary_decision == "accept_candidate"
    assert result.policy_snapshot.morphology_trace_method == "gaussian_15"
    assert result.policy_snapshot.morphology_trace_window_points == 15
    assert result.selected_envelope_interval.start_index < raw_dip_index
    assert result.selected_envelope_interval.end_index > raw_dip_index + 1
    assert "morphology_trace" in result.boundary_evidence_sources
    assert result.asls_area_selected_envelope > result.asls_area_old_interval


def test_gaussian_15_morphology_trace_is_not_boxcar_average() -> None:
    residual = np.zeros(31, dtype=float)
    residual[15] = 100.0

    gaussian_trace = _morphology_trace(
        residual,
        SelectedEnvelopePolicy(morphology_trace_method="gaussian_15"),
    )
    boxcar_trace = _morphology_trace(
        residual,
        SelectedEnvelopePolicy(morphology_trace_method="smooth_15"),
    )

    assert gaussian_trace[15] > gaussian_trace[14] > gaussian_trace[10] > 0.0
    assert gaussian_trace[15] > boxcar_trace[15]
    assert gaussian_trace[14] > boxcar_trace[14]
    assert float(np.sum(gaussian_trace)) == pytest.approx(float(np.sum(residual)))


def test_deep_valley_with_independent_apex_is_externalized_not_bridged() -> None:
    result = _evaluate(
        [0, 0, 2, 12, 30, 50, 0, 44, 18, 2, 0, 0],
        apex_rt=5.0,
        resolver_start=4.0,
        resolver_end=6.0,
    )

    assert result.selected_boundary_mode == "review_only"
    assert result.boundary_change_class == "split_supported"
    assert result.row_boundary_decision == "externalize"
    assert result.boundary_stop_reason == "split_supported_review_required"
    assert "split_supported" in result.boundary_evidence_sources


def test_resolved_neighboring_peak_is_not_swallowed() -> None:
    result = _evaluate(
        [0, 0, 10, 50, 10, 0, 0, 40, 0, 0, 0],
        apex_rt=3.0,
        resolver_start=2.0,
        resolver_end=4.0,
    )

    assert result.row_boundary_decision == "accept_candidate"
    assert result.boundary_change_class == "no_change"
    assert result.selected_envelope_interval.rt_end_min == pytest.approx(4.0)
    assert result.selected_envelope_interval.rt_end_min < 7.0


def test_neighboring_shoulder_peak_is_externalized_for_review() -> None:
    result = _evaluate(
        [0, 0, 10, 50, 40, 45, 30, 0, 0],
        apex_rt=3.0,
        resolver_start=2.0,
        resolver_end=4.0,
    )

    assert result.selected_boundary_mode == "review_only"
    assert result.boundary_change_class == "split_supported"
    assert result.row_boundary_decision == "externalize"
    assert result.boundary_stop_reason == "split_supported_review_required"
    assert "split_supported" in result.boundary_evidence_sources


def test_separate_neighbor_apex_conflict_is_externalized_for_review() -> None:
    result = _evaluate(
        [0, 0, 10, 50, 10, 2, 20, 42, 18, 0, 0],
        apex_rt=3.0,
        resolver_start=2.0,
        resolver_end=4.0,
    )

    assert result.selected_boundary_mode == "review_only"
    assert result.boundary_change_class == "neighbor_apex"
    assert result.row_boundary_decision == "externalize"
    assert result.boundary_stop_reason == "neighbor_apex_conflict"
    assert "neighbor_apex" in result.boundary_evidence_sources


def test_baseline_separated_apex_inside_smoothed_envelope_externalizes() -> None:
    residual = [0] * 8 + [0, 8, 12, 10, 0, 0, 28, 55, 50, 8, 0, 0] + [0] * 8
    result = _evaluate(
        residual,
        apex_rt=11.0,
        resolver_start=10.0,
        resolver_end=12.0,
        policy=SelectedEnvelopePolicy(
            max_envelope_width_min=40.0,
            neighbor_apex_min_delta_min=10.0,
            split_apex_max_delta_min=10.0,
        ),
    )

    assert result.selected_boundary_mode == "review_only"
    assert result.boundary_change_class == "split_supported"
    assert result.row_boundary_decision == "externalize"
    assert result.boundary_stop_reason == "split_supported_review_required"
    assert "split_supported" in result.boundary_evidence_sources


def test_small_baseline_separated_neighbor_peak_is_externalized() -> None:
    core = [0, 25, 80, 120, 78, 24, 0, 0, 22, 32, 24, 6, 0]
    residual = [0] * 8 + core + [0] * 8
    result = _evaluate(
        residual,
        apex_rt=11.0,
        resolver_start=10.0,
        resolver_end=13.0,
        policy=SelectedEnvelopePolicy(
            max_envelope_width_min=40.0,
            split_apex_max_delta_min=10.0,
        ),
    )

    assert result.selected_boundary_mode == "review_only"
    assert result.boundary_change_class == "split_supported"
    assert result.row_boundary_decision == "externalize"
    assert result.boundary_stop_reason == "split_supported_review_required"
    assert "split_supported" in result.boundary_evidence_sources


def test_split_evidence_takes_precedence_over_narrower_resolver_gate() -> None:
    core = [0, 25, 80, 120, 78, 24, 0, 0, 22, 32, 24, 6, 0]
    residual = [0] * 8 + core + [0] * 8
    result = _evaluate(
        residual,
        apex_rt=11.0,
        resolver_start=1.0,
        resolver_end=13.0,
        policy=SelectedEnvelopePolicy(
            max_envelope_width_min=40.0,
            split_apex_max_delta_min=10.0,
        ),
    )

    assert result.selected_boundary_mode == "review_only"
    assert result.boundary_change_class == "split_supported"
    assert result.row_boundary_decision == "externalize"
    assert result.boundary_stop_reason == "split_supported_review_required"
    assert "split_supported" in result.boundary_evidence_sources


def test_tailing_peak_at_context_edge_is_deferred() -> None:
    result = _evaluate(
        [0, 0, 10, 50, 30, 20, 15, 12, 10, 8, 6],
        apex_rt=3.0,
        resolver_start=2.0,
        resolver_end=5.0,
    )

    assert result.selected_boundary_mode == "review_only"
    assert result.boundary_change_class == "tail_uncertain"
    assert result.row_boundary_decision == "defer"
    assert result.boundary_stop_reason == "context_edge_above_baseline_return"


def test_low_signal_trace_is_not_promoted() -> None:
    result = _evaluate(
        [0, 0, 1, 4, 1, 0, 0],
        apex_rt=3.0,
        resolver_start=2.0,
        resolver_end=4.0,
    )

    assert result.selected_boundary_mode == "review_only"
    assert result.boundary_change_class == "low_sn"
    assert result.row_boundary_decision == "externalize"
    assert result.boundary_stop_reason == "apex_below_min_residual"


def test_blank_like_context_is_not_promoted() -> None:
    result = _evaluate(
        [0, 0, 2, 10, 30, 50, 30, 10, 2, 0, 0],
        apex_rt=5.0,
        resolver_start=4.0,
        resolver_end=6.0,
        blank_like_context=True,
    )

    assert result.selected_boundary_mode == "review_only"
    assert result.boundary_change_class == "carryover_blank_like"
    assert result.row_boundary_decision == "externalize"
    assert result.boundary_stop_reason == "blank_like_context"


def test_low_scan_support_is_not_promoted() -> None:
    result = _evaluate(
        [0, 8],
        apex_rt=1.0,
        resolver_start=0.0,
        resolver_end=1.0,
        policy=SelectedEnvelopePolicy(min_scan_count=3),
    )

    assert result.selected_boundary_mode == "invalid_trace"
    assert result.boundary_change_class == "low_scan"
    assert result.row_boundary_decision == "externalize"
    assert result.boundary_stop_reason == "too_few_scans"


def test_selected_envelope_below_min_scan_count_is_not_promoted() -> None:
    result = _evaluate(
        [0, 0, 0, 50, 0, 0],
        apex_rt=3.0,
        resolver_start=2.0,
        resolver_end=4.0,
        policy=SelectedEnvelopePolicy(min_scan_count=3),
    )

    assert result.selected_boundary_mode == "review_only"
    assert result.boundary_change_class == "low_scan"
    assert result.row_boundary_decision == "externalize"
    assert result.boundary_stop_reason == "selected_envelope_too_few_scans"
    assert result.selected_envelope_interval.scan_count == 1


def test_selected_envelope_narrower_than_resolver_is_active_boundary() -> None:
    result = _evaluate(
        [0, 0, 2, 10, 50, 10, 2, 0, 0],
        apex_rt=4.0,
        resolver_start=1.0,
        resolver_end=7.0,
    )

    assert result.selected_boundary_mode == "selected_full_envelope"
    assert result.boundary_change_class == "resolver_overwide_narrowed"
    assert result.row_boundary_decision == "accept_candidate"
    assert result.boundary_stop_reason == "baseline_return_reached"
    assert "resolver_interval_narrowing" in result.boundary_evidence_sources


def test_stronger_context_apex_outside_envelope_is_not_promoted() -> None:
    result = _evaluate(
        [0, 0, 2, 10, 50, 10, 2, 0, 0, 45, 80, 45, 0],
        apex_rt=4.0,
        resolver_start=3.0,
        resolver_end=5.0,
    )

    assert result.selected_boundary_mode == "review_only"
    assert result.boundary_change_class == "context_apex_conflict"
    assert result.row_boundary_decision == "externalize"
    assert result.boundary_stop_reason == "stronger_context_apex_outside_envelope"
    assert "context_apex_conflict" in result.boundary_evidence_sources


def test_envelope_wider_than_policy_is_rejected() -> None:
    result = _evaluate(
        [0, 2, 5, 10, 20, 30, 20, 10, 5, 2, 0],
        apex_rt=5.0,
        resolver_start=4.0,
        resolver_end=6.0,
        policy=SelectedEnvelopePolicy(max_envelope_width_min=4.0),
    )

    assert result.selected_boundary_mode == "review_only"
    assert result.boundary_change_class == "overmerge_rejected"
    assert result.row_boundary_decision == "reject"
    assert result.boundary_stop_reason == "max_envelope_width_exceeded"
