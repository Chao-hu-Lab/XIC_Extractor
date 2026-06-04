import pytest

from xic_extractor.peak_detection.selected_envelope_oracle import BoundaryOracle
from xic_extractor.peak_detection.selected_envelope_oracle_artifacts import (
    SELECTED_ENVELOPE_BOUNDARY_ORACLE_HEADERS,
    SELECTED_ENVELOPE_ORACLE_REVIEW_QUEUE_HEADERS,
    boundary_oracle_artifact_row,
    build_selected_envelope_oracle_review_queue,
    parse_selected_envelope_boundary_oracle_rows,
)


def _diagnostic_row(
    *,
    sample_name: str = "sample-a",
    target_label: str = "5-medC",
    selected_candidate_id: str = "candidate-001",
    boundary_change_class: str = "flank_recovered",
    row_boundary_decision: str = "accept_candidate",
    boundary_stop_reason: str = "baseline_return_reached",
) -> dict[str, str]:
    return {
        "sample_name": sample_name,
        "target_label": target_label,
        "role": "Analyte",
        "selected_candidate_id": selected_candidate_id,
        "selected_boundary_mode": "selected_full_envelope",
        "row_boundary_decision": row_boundary_decision,
        "legacy_resolver_provenance": "local_minimum",
        "resolver_rt_start": "4.00000",
        "resolver_rt_end": "6.00000",
        "envelope_rt_start": "2.00000",
        "envelope_rt_end": "8.00000",
        "quantitation_context_rt_start": "0.00000",
        "quantitation_context_rt_end": "10.00000",
        "policy_snapshot": "baseline_return_min_residual=1",
        "resolved_baseline_return_threshold": "1.00000",
        "boundary_change_class": boundary_change_class,
        "boundary_evidence_sources": "asls_baseline;baseline_return",
        "boundary_stop_reason": boundary_stop_reason,
        "asls_area_old_interval": "100.00",
        "asls_area_selected_envelope": "160.00",
        "area_delta_ratio": "0.60000",
        "plot_path": "plots/sample-a.png",
    }


def test_review_queue_lists_changed_rows_requiring_boundary_oracle() -> None:
    queue = build_selected_envelope_oracle_review_queue(
        (
            _diagnostic_row(),
            _diagnostic_row(
                sample_name="sample-b",
                selected_candidate_id="candidate-002",
                boundary_change_class="no_change",
                row_boundary_decision="accept_candidate",
            ),
        )
    )

    assert len(queue) == 1
    row = queue[0]
    assert tuple(row) == SELECTED_ENVELOPE_ORACLE_REVIEW_QUEUE_HEADERS
    assert row["oracle_row_id"] == "sample-a|5-medC|candidate-001"
    assert row["review_priority"] == "changed_boundary_review"
    assert row["review_reason"] == (
        "flank_recovered;baseline_return_reached;accept_candidate"
    )
    assert row["allowed_oracle_sources"] == "manual_overlay;expert_overlay;manual_2raw"
    assert row["required_oracle_status"] == "expert_reviewed"
    assert row["candidate_envelope_rt_start"] == "2.00000"
    assert row["candidate_envelope_rt_end"] == "8.00000"
    assert row["reviewed_rt_start_min"] == ""
    assert row["reviewed_area_baseline_corrected"] == ""


def test_review_queue_prioritizes_externalized_high_risk_rows() -> None:
    queue = build_selected_envelope_oracle_review_queue(
        (
            _diagnostic_row(
                boundary_change_class="split_supported",
                row_boundary_decision="externalize",
                boundary_stop_reason="split_supported_review_required",
            ),
        )
    )

    assert queue[0]["review_priority"] == "high_risk_boundary_review"
    assert queue[0]["review_reason"] == (
        "split_supported;split_supported_review_required;externalize"
    )


def test_review_queue_requires_selected_candidate_identity() -> None:
    with pytest.raises(ValueError, match="selected_candidate_id"):
        build_selected_envelope_oracle_review_queue(
            (_diagnostic_row(selected_candidate_id=""),)
        )


def test_boundary_oracle_artifact_row_round_trips_to_boundary_oracle() -> None:
    oracle = BoundaryOracle(
        oracle_row_id="sample-a|5-medC|candidate-001",
        selected_candidate_id="candidate-001",
        oracle_status="expert_reviewed",
        oracle_source="manual_overlay",
        rt_start_min=2.0,
        rt_end_min=8.0,
        area_baseline_corrected=160.0,
        shape_class="clean_single_peak",
        acceptable_boundary_delta_min=0.05,
        acceptable_area_relative_error=0.08,
        required_plot_path="plots/sample-a.png",
    )

    row = boundary_oracle_artifact_row(oracle)
    parsed = parse_selected_envelope_boundary_oracle_rows((row,))

    assert tuple(row) == SELECTED_ENVELOPE_BOUNDARY_ORACLE_HEADERS
    assert parsed == (oracle,)


def test_boundary_oracle_loader_rejects_targeted_workbook_boundary_truth() -> None:
    row = _oracle_row(
        oracle_status="expert_reviewed",
        oracle_source="targeted_workbook_control",
    )

    with pytest.raises(ValueError, match="targeted workbook"):
        parse_selected_envelope_boundary_oracle_rows((row,))


def test_boundary_oracle_loader_rejects_invalid_status_or_source() -> None:
    with pytest.raises(ValueError, match="invalid oracle_status"):
        parse_selected_envelope_boundary_oracle_rows(
            (_oracle_row(oracle_status="reviewed"),)
        )

    with pytest.raises(ValueError, match="invalid oracle_source"):
        parse_selected_envelope_boundary_oracle_rows(
            (_oracle_row(oracle_source="target_label"),)
        )


def test_boundary_oracle_loader_allows_targeted_workbook_as_benchmark_only() -> None:
    row = _oracle_row(
        oracle_status="benchmark_control_only",
        oracle_source="targeted_workbook_control",
        area_baseline_corrected="",
    )

    parsed = parse_selected_envelope_boundary_oracle_rows((row,))

    assert parsed[0].oracle_status == "benchmark_control_only"
    assert parsed[0].oracle_source == "targeted_workbook_control"
    assert parsed[0].area_baseline_corrected is None


def test_boundary_oracle_loader_rejects_manual_sources_as_benchmark_only() -> None:
    row = _oracle_row(
        oracle_status="benchmark_control_only",
        oracle_source="manual_overlay",
        area_baseline_corrected="",
    )

    with pytest.raises(ValueError, match="benchmark_control_only"):
        parse_selected_envelope_boundary_oracle_rows((row,))


def test_boundary_oracle_loader_requires_area_for_expert_reviewed_rows() -> None:
    row = _oracle_row(area_baseline_corrected="")

    with pytest.raises(ValueError, match="area_baseline_corrected"):
        parse_selected_envelope_boundary_oracle_rows((row,))


def test_boundary_oracle_loader_rejects_zero_area_or_tolerance() -> None:
    with pytest.raises(ValueError, match="area_baseline_corrected"):
        parse_selected_envelope_boundary_oracle_rows(
            (_oracle_row(area_baseline_corrected="0"),)
        )

    row = _oracle_row()
    row["acceptable_boundary_delta_min"] = "0"
    with pytest.raises(ValueError, match="acceptable_boundary_delta_min"):
        parse_selected_envelope_boundary_oracle_rows((row,))

    row = _oracle_row()
    row["acceptable_area_relative_error"] = "-0.1"
    with pytest.raises(ValueError, match="acceptable_area_relative_error"):
        parse_selected_envelope_boundary_oracle_rows((row,))


def test_boundary_oracle_loader_rejects_invalid_reviewed_bounds() -> None:
    row = _oracle_row(rt_start_min="8.0", rt_end_min="2.0")

    with pytest.raises(ValueError, match="rt_start_min"):
        parse_selected_envelope_boundary_oracle_rows((row,))


def test_boundary_oracle_writer_rejects_invalid_dataclass_values() -> None:
    oracle = BoundaryOracle(
        oracle_row_id="sample-a|5-medC|candidate-001",
        selected_candidate_id="candidate-001",
        oracle_status="expert_reviewed",
        oracle_source="targeted_workbook_control",
        rt_start_min=2.0,
        rt_end_min=8.0,
        area_baseline_corrected=160.0,
        shape_class="clean_single_peak",
    )

    with pytest.raises(ValueError, match="targeted workbook"):
        boundary_oracle_artifact_row(oracle)


def test_boundary_oracle_writer_rejects_manual_sources_as_benchmark_only() -> None:
    oracle = BoundaryOracle(
        oracle_row_id="sample-a|5-medC|candidate-001",
        selected_candidate_id="candidate-001",
        oracle_status="benchmark_control_only",
        oracle_source="manual_overlay",
        rt_start_min=2.0,
        rt_end_min=8.0,
        area_baseline_corrected=None,
        shape_class="clean_single_peak",
    )

    with pytest.raises(ValueError, match="benchmark_control_only"):
        boundary_oracle_artifact_row(oracle)


def _oracle_row(
    *,
    oracle_status: str = "expert_reviewed",
    oracle_source: str = "manual_overlay",
    rt_start_min: str = "2.0",
    rt_end_min: str = "8.0",
    area_baseline_corrected: str = "160.0",
) -> dict[str, str]:
    return {
        "oracle_row_id": "sample-a|5-medC|candidate-001",
        "selected_candidate_id": "candidate-001",
        "oracle_status": oracle_status,
        "oracle_source": oracle_source,
        "rt_start_min": rt_start_min,
        "rt_end_min": rt_end_min,
        "area_baseline_corrected": area_baseline_corrected,
        "shape_class": "clean_single_peak",
        "acceptable_boundary_delta_min": "0.05",
        "acceptable_area_relative_error": "0.08",
        "required_plot_path": "plots/sample-a.png",
    }
