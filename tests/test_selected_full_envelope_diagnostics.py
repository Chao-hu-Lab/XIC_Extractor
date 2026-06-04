import numpy as np
import pytest

from xic_extractor.peak_detection.selected_envelope import (
    SelectedEnvelopeBoundaryEvaluation,
    SelectedEnvelopePolicy,
    evaluate_selected_envelope_boundary,
)
from xic_extractor.peak_detection.selected_envelope_diagnostics import (
    SELECTED_ENVELOPE_DIAGNOSTIC_HEADERS,
    build_selected_envelope_gate_manifest,
    build_selected_envelope_gate_manifest_from_rows,
    selected_envelope_diagnostic_row,
)


def _trace(residual: list[float]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    rt = np.arange(float(len(residual)), dtype=float)
    baseline = np.full(len(residual), 10.0)
    intensity = baseline + np.asarray(residual, dtype=float)
    return rt, intensity, baseline


def _evaluation(
    residual: list[float],
    *,
    selected_candidate_id: str = "candidate-001",
    apex_rt: float = 5.0,
    resolver_start: float = 4.0,
    resolver_end: float = 6.0,
    context_end: float | None = None,
    policy: SelectedEnvelopePolicy | None = None,
    blank_like_context: bool = False,
) -> SelectedEnvelopeBoundaryEvaluation:
    rt, intensity, baseline = _trace(residual)
    return evaluate_selected_envelope_boundary(
        rt,
        intensity,
        baseline,
        selected_apex_rt=apex_rt,
        resolver_rt_start=resolver_start,
        resolver_rt_end=resolver_end,
        quantitation_context_rt_start=0.0,
        quantitation_context_rt_end=(
            float(len(residual) - 1) if context_end is None else context_end
        ),
        selected_candidate_id=selected_candidate_id,
        policy=policy,
        legacy_resolver_provenance="local_minimum",
        blank_like_context=blank_like_context,
    )


def test_diagnostic_row_renders_domain_evaluation_without_gate_decision() -> None:
    evaluation = _evaluation([0, 0, 2, 10, 30, 50, 30, 10, 2, 0, 0])

    row = selected_envelope_diagnostic_row(
        sample_name="sample-a",
        target_label="5-medC",
        role="Analyte",
        evaluation=evaluation,
        plot_path="plots/sample-a.png",
    )

    assert set(row) == set(SELECTED_ENVELOPE_DIAGNOSTIC_HEADERS)
    assert "gate_decision" not in row
    assert row["sample_name"] == "sample-a"
    assert row["target_label"] == "5-medC"
    assert row["selected_candidate_id"] == "candidate-001"
    assert row["selected_boundary_mode"] == "selected_full_envelope"
    assert row["row_boundary_decision"] == "accept_candidate"
    assert row["legacy_resolver_provenance"] == "local_minimum"
    assert row["resolver_rt_start"] == "4.00000"
    assert row["resolver_rt_end"] == "6.00000"
    assert row["envelope_rt_start"] == "2.00000"
    assert row["envelope_rt_end"] == "8.00000"
    assert row["quantitation_context_rt_start"] == "0.00000"
    assert row["quantitation_context_rt_end"] == "10.00000"
    assert row["morphology_trace_method"] == "gaussian_15"
    assert row["morphology_trace_window_points"] == "15"
    assert row["morphology_trace_effective_points"] == "1"
    assert "baseline_return_min_residual=1" in row["policy_snapshot"]
    assert row["resolved_baseline_return_threshold"] == "1.00000"
    assert float(row["asls_area_selected_envelope"]) > float(
        row["asls_area_old_interval"]
    )
    assert float(row["gaussian15_area_selected_envelope_shadow"]) > float(
        row["gaussian15_area_old_interval_shadow"]
    )
    assert row["gaussian15_area_delta_ratio_shadow"] != ""
    assert row["plot_path"] == "plots/sample-a.png"


def test_diagnostic_row_reports_effective_gaussian_15_window() -> None:
    core = [1, 3, 8, 16, 28, 40, 52, 40, 22, 0, 20, 30, 18, 8, 3, 1]
    evaluation = _evaluation(
        ([0] * 12) + core + ([0] * 12),
        apex_rt=18.0,
        resolver_start=17.0,
        resolver_end=19.0,
        policy=SelectedEnvelopePolicy(max_envelope_width_min=40.0),
    )

    row = selected_envelope_diagnostic_row(
        sample_name="sample-a",
        target_label="5-medC",
        role="Analyte",
        evaluation=evaluation,
    )

    assert row["morphology_trace_method"] == "gaussian_15"
    assert row["morphology_trace_window_points"] == "15"
    assert row["morphology_trace_effective_points"] == "15"


def test_diagnostic_row_reports_raw_effective_window_when_smoothing_disabled() -> None:
    evaluation = _evaluation(
        [0, 0, 2, 10, 30, 50, 30, 10, 2, 0, 0],
        policy=SelectedEnvelopePolicy(morphology_trace_method="raw_residual"),
    )

    row = selected_envelope_diagnostic_row(
        sample_name="sample-a",
        target_label="5-medC",
        role="Analyte",
        evaluation=evaluation,
    )

    assert row["morphology_trace_method"] == "raw_residual"
    assert row["morphology_trace_window_points"] == "15"
    assert row["morphology_trace_effective_points"] == "1"


def test_diagnostic_row_reports_zero_effective_window_when_blocked() -> None:
    evaluation = _evaluation(
        [0, 8],
        apex_rt=1.0,
        resolver_start=0.0,
        resolver_end=1.0,
        policy=SelectedEnvelopePolicy(min_scan_count=3),
    )

    row = selected_envelope_diagnostic_row(
        sample_name="sample-a",
        target_label="5-medC",
        role="Analyte",
        evaluation=evaluation,
    )

    assert row["selected_boundary_mode"] == "invalid_trace"
    assert row["morphology_trace_method"] == "gaussian_15"
    assert row["morphology_trace_window_points"] == "15"
    assert row["morphology_trace_effective_points"] == "0"


def test_diagnostic_row_rejects_missing_selected_candidate_identity() -> None:
    evaluation = _evaluation(
        [0, 0, 2, 10, 30, 50, 30, 10, 2, 0, 0],
        selected_candidate_id="",
    )

    with pytest.raises(ValueError, match="selected_candidate_id"):
        selected_envelope_diagnostic_row(
            sample_name="sample-a",
            target_label="5-medC",
            role="Analyte",
            evaluation=evaluation,
        )


def test_manifest_promotes_only_when_every_row_accepts_candidate() -> None:
    accepted = _evaluation([0, 0, 2, 10, 30, 50, 30, 10, 2, 0, 0])
    no_change = _evaluation(
        [0, 0, 2, 10, 30, 50, 30, 10, 2, 0, 0],
        resolver_start=2.0,
        resolver_end=8.0,
    )

    manifest = build_selected_envelope_gate_manifest((accepted, no_change))

    assert manifest["gate_decision"] == "promote"
    assert manifest["changed_row_count"] == "1"
    assert manifest["changed_row_denominator"] == "2"
    assert manifest["unresolved_blocker_count"] == "0"
    assert manifest["blocked_reasons"] == ""
    assert manifest["next_gate"] == "manual_overlay_oracle"


def test_manifest_defers_when_no_rows_were_evaluated() -> None:
    manifest = build_selected_envelope_gate_manifest(())

    assert manifest["gate_decision"] == "defer"
    assert manifest["changed_row_count"] == "0"
    assert manifest["changed_row_denominator"] == "0"
    assert manifest["unresolved_blocker_count"] == "1"
    assert manifest["blocked_reasons"] == "no_evaluated_rows"
    assert manifest["next_gate"] == "bounded_follow_up_required"


def test_manifest_no_go_on_rejected_width_case_before_scaleup() -> None:
    rejected = _evaluation(
        [0, 2, 5, 10, 20, 30, 20, 10, 5, 2, 0],
        policy=SelectedEnvelopePolicy(max_envelope_width_min=4.0),
    )

    manifest = build_selected_envelope_gate_manifest((rejected,))

    assert manifest["gate_decision"] == "no_go"
    assert manifest["unresolved_blocker_count"] == "1"
    assert manifest["blocked_reasons"] == "max_envelope_width_exceeded"
    assert manifest["next_gate"] == "stop_selected_envelope_product_path"


def test_manifest_defers_before_externalizing_or_promoting() -> None:
    deferred = _evaluation(
        [0, 0, 10, 50, 30, 20, 15, 12, 10, 8, 6],
        apex_rt=3.0,
        resolver_start=2.0,
        resolver_end=5.0,
    )
    externalized = _evaluation(
        [0, 0, 10, 50, 40, 45, 30, 0, 0],
        apex_rt=3.0,
        resolver_start=2.0,
        resolver_end=4.0,
    )

    manifest = build_selected_envelope_gate_manifest((deferred, externalized))

    assert manifest["gate_decision"] == "defer"
    assert manifest["unresolved_blocker_count"] == "2"
    assert manifest["blocked_reasons"] == (
        "context_edge_above_baseline_return;split_supported_review_required"
    )
    assert manifest["high_risk_strata"] == "split_supported;tail_uncertain"
    assert manifest["next_gate"] == "bounded_follow_up_required"


def test_manifest_reports_split_supported_as_high_risk_review_stratum() -> None:
    split_supported = _evaluation(
        [0, 0, 10, 50, 40, 45, 30, 0, 0],
        apex_rt=3.0,
        resolver_start=2.0,
        resolver_end=4.0,
    )

    row = selected_envelope_diagnostic_row(
        sample_name="sample-a",
        target_label="5-medC",
        role="Analyte",
        evaluation=split_supported,
    )
    manifest = build_selected_envelope_gate_manifest((split_supported,))

    assert row["boundary_change_class"] == "split_supported"
    assert row["boundary_stop_reason"] == "split_supported_review_required"
    assert manifest["gate_decision"] == "externalize"
    assert manifest["high_risk_strata"] == "split_supported"
    assert manifest["blocked_reasons"] == "split_supported_review_required"


def test_manifest_externalizes_review_only_rows_without_reject_or_defer() -> None:
    externalized = _evaluation(
        [0, 0, 10, 50, 40, 45, 30, 0, 0],
        apex_rt=3.0,
        resolver_start=2.0,
        resolver_end=4.0,
    )

    manifest = build_selected_envelope_gate_manifest((externalized,))

    assert manifest["gate_decision"] == "externalize"
    assert manifest["next_gate"] == "diagnostic_review_only"


def test_manifest_from_diagnostic_rows_matches_evaluation_manifest() -> None:
    accepted = _evaluation([0, 0, 2, 10, 30, 50, 30, 10, 2, 0, 0])
    externalized = _evaluation(
        [0, 0, 10, 50, 40, 45, 30, 0, 0],
        apex_rt=3.0,
        resolver_start=2.0,
        resolver_end=4.0,
    )
    rows = tuple(
        selected_envelope_diagnostic_row(
            sample_name="sample-a",
            target_label="5-medC",
            role="Analyte",
            evaluation=evaluation,
        )
        for evaluation in (accepted, externalized)
    )

    manifest = build_selected_envelope_gate_manifest_from_rows(rows)

    assert manifest == build_selected_envelope_gate_manifest((accepted, externalized))


def test_manifest_from_empty_diagnostic_rows_defers() -> None:
    manifest = build_selected_envelope_gate_manifest_from_rows(())

    assert manifest["gate_decision"] == "defer"
    assert manifest["blocked_reasons"] == "no_evaluated_rows"


def test_manifest_from_unknown_row_decision_defers() -> None:
    accepted = selected_envelope_diagnostic_row(
        sample_name="sample-a",
        target_label="5-medC",
        role="Analyte",
        evaluation=_evaluation([0, 0, 2, 10, 30, 50, 30, 10, 2, 0, 0]),
    )
    malformed = dict(accepted)
    malformed["sample_name"] = "sample-b"
    malformed["row_boundary_decision"] = ""
    malformed["boundary_stop_reason"] = ""

    manifest = build_selected_envelope_gate_manifest_from_rows((accepted, malformed))

    assert manifest["gate_decision"] == "defer"
    assert manifest["unresolved_blocker_count"] == "1"
    assert manifest["blocked_reasons"] == "unknown_row_boundary_decision"
