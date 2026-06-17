from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
import pytest

from tools.diagnostics import standard_peak_heldout_trace_oracle as cli
from xic_extractor.alignment.matrix_handoff import integration_from_peak_trace
from xic_extractor.config import ExtractionConfig
from xic_extractor.diagnostics import standard_peak_heldout_trace_oracle as oracle
from xic_extractor.signal_processing import find_peak_and_area


def test_heldout_trace_oracle_cli_writes_low_scan_packet(
    tmp_path: Path,
) -> None:
    evidence_tsv, trace_root = _write_low_scan_fixture(tmp_path)
    output_dir = tmp_path / "oracle"

    assert (
        cli.main(
            [
                "--alignment-backfill-cell-evidence-tsv",
                str(evidence_tsv),
                "--trace-root",
                str(trace_root),
                "--output-dir",
                str(output_dir),
                "--source-run-id",
                "unit-low-scan-oracle",
                "--target-shape-class",
                "standard_low_scan_clean_trace",
            ],
        )
        == 0
    )

    summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary["status"] == "pass"
    assert summary["target_shape_class"] == "standard_low_scan_clean_trace"
    assert summary["available_candidate_rows"] == "1"
    assert summary["selected_case_count"] == "1"
    assert summary["oracle_case_status_pass_count"] == "1"
    assert summary["included_in_product_acceptance_count"] == "1"

    manifest = _read_tsv(output_dir / "heldout_oracle_manifest.tsv")[0]
    assert manifest["target_shape_class"] == "standard_low_scan_clean_trace"
    assert manifest["acceptable_boundary_delta_min"] == "0.1"
    assert manifest["acceptable_area_relative_error"] == "0.1"

    result = _read_tsv(output_dir / "heldout_oracle_results.tsv")[0]
    assert result["oracle_case_status"] == "pass"
    assert result["included_in_product_acceptance"] == "TRUE"
    assert result["observed_independence_basis"] == (
        "independent_boundary_reintegration_result"
    )

    pool = _read_tsv(output_dir / "heldout_trace_reintegration_full_eligible_pool.tsv")
    assert pool[0]["selected_for_oracle"] == "TRUE"
    assert pool[0]["oracle_scan_count"] == "7"


def test_heldout_trace_oracle_cli_writes_low_height_packet(
    tmp_path: Path,
) -> None:
    evidence_tsv, trace_root = _write_low_height_fixture(tmp_path)
    output_dir = tmp_path / "oracle"

    assert (
        cli.main(
            [
                "--alignment-backfill-cell-evidence-tsv",
                str(evidence_tsv),
                "--trace-root",
                str(trace_root),
                "--output-dir",
                str(output_dir),
                "--source-run-id",
                "unit-low-height-oracle",
                "--target-shape-class",
                "standard_low_height_clean_trace",
            ],
        )
        == 0
    )

    summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary["status"] == "pass"
    assert summary["target_shape_class"] == "standard_low_height_clean_trace"
    assert summary["available_candidate_rows"] == "1"
    assert summary["selected_case_count"] == "1"
    assert summary["oracle_case_status_pass_count"] == "1"
    assert summary["included_in_product_acceptance_count"] == "1"

    manifest = _read_tsv(output_dir / "heldout_oracle_manifest.tsv")[0]
    assert manifest["target_shape_class"] == "standard_low_height_clean_trace"

    pool = _read_tsv(output_dir / "heldout_trace_reintegration_full_eligible_pool.tsv")
    assert pool[0]["selected_for_oracle"] == "TRUE"
    assert float(pool[0]["cell_height"]) < 2_000_000.0
    assert int(pool[0]["oracle_scan_count"]) >= 10


def test_heldout_trace_oracle_expected_window_bounded_mode_closes_boundary_drift(
    tmp_path: Path,
) -> None:
    evidence_tsv, trace_root = _write_boundary_drift_fixture(tmp_path)
    full_output_dir = tmp_path / "full_oracle"
    bounded_output_dir = tmp_path / "bounded_oracle"

    assert (
        cli.main(
            [
                "--alignment-backfill-cell-evidence-tsv",
                str(evidence_tsv),
                "--trace-root",
                str(trace_root),
                "--output-dir",
                str(full_output_dir),
                "--source-run-id",
                "unit-boundary-drift-full-oracle",
                "--target-shape-class",
                "standard_low_height_clean_trace",
            ],
        )
        == 1
    )
    full_summary = json.loads(
        (full_output_dir / "summary.json").read_text(encoding="utf-8"),
    )
    assert full_summary["observed_reintegration_mode"] == "full_trace"
    assert full_summary["expected_window_padding_min"] == ""
    assert full_summary["status"] == "fail"
    assert full_summary["oracle_case_status_fail_count"] == "1"
    assert float(full_summary["max_observed_boundary_error_min"]) > 0.1

    assert (
        cli.main(
            [
                "--alignment-backfill-cell-evidence-tsv",
                str(evidence_tsv),
                "--trace-root",
                str(trace_root),
                "--output-dir",
                str(bounded_output_dir),
                "--source-run-id",
                "unit-boundary-drift-bounded-oracle",
                "--target-shape-class",
                "standard_low_height_clean_trace",
                "--observed-reintegration-mode",
                "expected_window_bounded",
                "--expected-window-padding-min",
                "0.1",
            ],
        )
        == 0
    )
    bounded_summary = json.loads(
        (bounded_output_dir / "summary.json").read_text(encoding="utf-8"),
    )
    assert bounded_summary["observed_reintegration_mode"] == "expected_window_bounded"
    assert bounded_summary["expected_window_padding_min"] == "0.1"
    assert bounded_summary["status"] == "pass"
    assert bounded_summary["oracle_case_status_pass_count"] == "1"

    observed = _read_tsv(bounded_output_dir / "heldout_observed_results.tsv")[0]
    assert observed["observed_result_source"] == (
        "heldout_trace_reintegration_expected_window_bounded_v1"
    )
    assert (
        "expected_window_padded_0.1min" in observed["observed_boundary_source"]
    )


def test_heldout_trace_oracle_rejects_negative_expected_window_padding(
    tmp_path: Path,
) -> None:
    evidence_tsv, trace_root = _write_low_height_fixture(tmp_path)

    assert (
        cli.main(
            [
                "--alignment-backfill-cell-evidence-tsv",
                str(evidence_tsv),
                "--trace-root",
                str(trace_root),
                "--output-dir",
                str(tmp_path / "cli_oracle"),
                "--source-run-id",
                "unit-negative-padding-cli",
                "--target-shape-class",
                "standard_low_height_clean_trace",
                "--observed-reintegration-mode",
                "expected_window_bounded",
                "--expected-window-padding-min",
                "-0.01",
            ],
        )
        == 2
    )
    with pytest.raises(ValueError, match="expected_window_padding_min"):
        oracle.run_heldout_trace_oracle(
            alignment_backfill_cell_evidence_tsv=evidence_tsv,
            trace_root=trace_root,
            output_dir=tmp_path / "oracle",
            source_run_id="unit-negative-padding",
            target_shape_class="standard_low_height_clean_trace",
            observed_reintegration_mode="expected_window_bounded",
            expected_window_padding_min=-0.01,
        )


def test_heldout_trace_oracle_bounded_mode_fails_closed_without_observed_peak(
    tmp_path: Path,
) -> None:
    evidence_tsv, trace_root = _write_flat_bounded_trace_fixture(tmp_path)
    output_dir = tmp_path / "oracle"

    assert (
        cli.main(
            [
                "--alignment-backfill-cell-evidence-tsv",
                str(evidence_tsv),
                "--trace-root",
                str(trace_root),
                "--output-dir",
                str(output_dir),
                "--source-run-id",
                "unit-flat-bounded-oracle",
                "--target-shape-class",
                "standard_low_height_clean_trace",
                "--observed-reintegration-mode",
                "expected_window_bounded",
            ],
        )
        == 1
    )

    summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary["status"] == "fail"
    assert summary["observed_reintegration_mode"] == "expected_window_bounded"
    assert summary["oracle_case_status_fail_count"] == "1"
    assert summary["included_in_product_acceptance_count"] == "0"

    observed_rows = _read_tsv(output_dir / "heldout_observed_results.tsv")
    assert observed_rows == []
    result = _read_tsv(output_dir / "heldout_oracle_results.tsv")[0]
    assert result["oracle_case_status"] == "inconclusive_review_only"
    assert result["inconclusive_reason"] == "missing_observed_result"
    assert result["included_in_product_acceptance"] == "FALSE"


def test_heldout_trace_oracle_cli_writes_apex_delta_packet(
    tmp_path: Path,
) -> None:
    evidence_tsv, trace_root = _write_apex_delta_fixture(tmp_path)
    output_dir = tmp_path / "oracle"

    assert (
        cli.main(
            [
                "--alignment-backfill-cell-evidence-tsv",
                str(evidence_tsv),
                "--trace-root",
                str(trace_root),
                "--output-dir",
                str(output_dir),
                "--source-run-id",
                "unit-apex-delta-oracle",
                "--target-shape-class",
                "standard_apex_delta_clean_trace",
            ],
        )
        == 0
    )

    summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary["status"] == "pass"
    assert summary["target_shape_class"] == "standard_apex_delta_clean_trace"
    assert summary["available_candidate_rows"] == "1"
    assert summary["selected_case_count"] == "1"
    assert summary["oracle_case_status_pass_count"] == "1"

    manifest = _read_tsv(output_dir / "heldout_oracle_manifest.tsv")[0]
    assert manifest["target_shape_class"] == "standard_apex_delta_clean_trace"

    pool = _read_tsv(output_dir / "heldout_trace_reintegration_full_eligible_pool.tsv")
    assert pool[0]["selected_for_oracle"] == "TRUE"
    assert float(pool[0]["apex_delta_from_family_center_min"]) > 0.15
    assert float(pool[0]["shape_similarity"]) >= 0.95
    assert int(pool[0]["oracle_scan_count"]) >= 10


def test_heldout_trace_oracle_cli_writes_width_packet(
    tmp_path: Path,
) -> None:
    evidence_tsv, trace_root = _write_width_fixture(tmp_path)
    output_dir = tmp_path / "oracle"

    assert (
        cli.main(
            [
                "--alignment-backfill-cell-evidence-tsv",
                str(evidence_tsv),
                "--trace-root",
                str(trace_root),
                "--output-dir",
                str(output_dir),
                "--source-run-id",
                "unit-width-oracle",
                "--target-shape-class",
                "standard_width_clean_trace",
            ],
        )
        == 0
    )

    summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary["status"] == "pass"
    assert summary["target_shape_class"] == "standard_width_clean_trace"
    assert summary["available_candidate_rows"] == "1"
    assert summary["selected_case_count"] == "1"
    assert summary["oracle_case_status_pass_count"] == "1"

    manifest = _read_tsv(output_dir / "heldout_oracle_manifest.tsv")[0]
    assert manifest["target_shape_class"] == "standard_width_clean_trace"

    pool = _read_tsv(output_dir / "heldout_trace_reintegration_full_eligible_pool.tsv")
    width = float(pool[0]["oracle_width_min"])
    assert pool[0]["selected_for_oracle"] == "TRUE"
    assert width < 0.30 or width > 0.65
    assert float(pool[0]["apex_delta_from_family_center_min"]) <= 0.15
    assert int(pool[0]["oracle_scan_count"]) >= 10


def test_heldout_trace_oracle_cli_writes_shape_margin_packet(
    tmp_path: Path,
) -> None:
    evidence_tsv, trace_root = _write_shape_margin_fixture(tmp_path)
    output_dir = tmp_path / "oracle"

    assert (
        cli.main(
            [
                "--alignment-backfill-cell-evidence-tsv",
                str(evidence_tsv),
                "--trace-root",
                str(trace_root),
                "--output-dir",
                str(output_dir),
                "--source-run-id",
                "unit-shape-margin-oracle",
                "--target-shape-class",
                "standard_shape_margin_clean_trace",
            ],
        )
        == 0
    )

    summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary["status"] == "pass"
    assert summary["target_shape_class"] == "standard_shape_margin_clean_trace"
    assert summary["available_candidate_rows"] == "1"
    assert summary["selected_case_count"] == "1"
    assert summary["oracle_case_status_pass_count"] == "1"

    manifest = _read_tsv(output_dir / "heldout_oracle_manifest.tsv")[0]
    assert manifest["target_shape_class"] == "standard_shape_margin_clean_trace"

    pool = _read_tsv(output_dir / "heldout_trace_reintegration_full_eligible_pool.tsv")
    shape = float(pool[0]["shape_similarity"])
    assert pool[0]["selected_for_oracle"] == "TRUE"
    assert oracle.MIN_SHAPE_MARGIN_SIMILARITY <= shape < oracle.MIN_SHAPE_SIMILARITY
    assert float(pool[0]["local_window_to_global_max_ratio"]) >= 0.95
    assert int(pool[0]["oracle_scan_count"]) >= 10


def test_width_target_shape_class_matches_only_outside_clean_width_band() -> None:
    clean = {
        "shape": oracle.MIN_SHAPE_SIMILARITY,
        "local_global": oracle.MIN_LOCAL_GLOBAL_RATIO,
        "height": oracle.MIN_CELL_HEIGHT,
        "apex_delta": oracle.MAX_APEX_DELTA_ABS_MIN,
        "scan_count": oracle.MIN_HIGH_SIGNAL_SCAN_COUNT,
    }

    assert oracle._target_shape_class_matches(
        oracle.WIDTH_CLEAN_SCOPE,
        width=oracle.MIN_BOUNDARY_WIDTH_MIN - 0.0001,
        **clean,
    )
    assert oracle._target_shape_class_matches(
        oracle.WIDTH_CLEAN_SCOPE,
        width=oracle.MAX_BOUNDARY_WIDTH_MIN + 0.0001,
        **clean,
    )

    for width in (
        oracle.MIN_BOUNDARY_WIDTH_MIN,
        0.475,
        oracle.MAX_BOUNDARY_WIDTH_MIN,
    ):
        assert not oracle._target_shape_class_matches(
            oracle.WIDTH_CLEAN_SCOPE,
            width=width,
            **clean,
        )

    dirty_cases = (
        {"shape": oracle.MIN_SHAPE_SIMILARITY - 0.0001},
        {"local_global": oracle.MIN_LOCAL_GLOBAL_RATIO - 0.0001},
        {"height": oracle.MIN_CELL_HEIGHT - 1.0},
        {"apex_delta": oracle.MAX_APEX_DELTA_ABS_MIN + 0.0001},
        {"scan_count": oracle.MIN_HIGH_SIGNAL_SCAN_COUNT - 1},
    )
    for dirty in dirty_cases:
        assert not oracle._target_shape_class_matches(
            oracle.WIDTH_CLEAN_SCOPE,
            width=oracle.MAX_BOUNDARY_WIDTH_MIN + 0.0001,
            **(clean | dirty),
        )


def test_shape_margin_target_shape_class_requires_near_threshold_shape() -> None:
    clean = {
        "local_global": oracle.MIN_LOCAL_GLOBAL_RATIO,
        "height": oracle.MIN_CELL_HEIGHT,
        "width": oracle.MIN_BOUNDARY_WIDTH_MIN,
        "apex_delta": oracle.MAX_APEX_DELTA_ABS_MIN,
        "scan_count": oracle.MIN_HIGH_SIGNAL_SCAN_COUNT,
    }

    assert oracle._target_shape_class_matches(
        oracle.SHAPE_MARGIN_CLEAN_SCOPE,
        shape=oracle.MIN_SHAPE_MARGIN_SIMILARITY,
        **clean,
    )
    assert oracle._target_shape_class_matches(
        oracle.SHAPE_MARGIN_CLEAN_SCOPE,
        shape=oracle.MIN_SHAPE_SIMILARITY - 0.0001,
        **clean,
    )
    assert oracle._target_shape_class_matches(
        oracle.SHAPE_MARGIN_CLEAN_SCOPE,
        shape=oracle.MIN_SHAPE_MARGIN_SIMILARITY,
        **(clean | {"width": oracle.MAX_BOUNDARY_WIDTH_MIN}),
    )

    for shape in (
        oracle.MIN_SHAPE_MARGIN_SIMILARITY - 0.0001,
        oracle.MIN_SHAPE_SIMILARITY,
    ):
        assert not oracle._target_shape_class_matches(
            oracle.SHAPE_MARGIN_CLEAN_SCOPE,
            shape=shape,
            **clean,
        )

    dirty_cases = (
        {"local_global": oracle.MIN_LOCAL_GLOBAL_RATIO - 0.0001},
        {"height": oracle.MIN_CELL_HEIGHT - 1.0},
        {"width": oracle.MIN_BOUNDARY_WIDTH_MIN - 0.0001},
        {"width": oracle.MAX_BOUNDARY_WIDTH_MIN + 0.0001},
        {"apex_delta": oracle.MAX_APEX_DELTA_ABS_MIN + 0.0001},
        {"scan_count": oracle.MIN_HIGH_SIGNAL_SCAN_COUNT - 1},
    )
    for dirty in dirty_cases:
        assert not oracle._target_shape_class_matches(
            oracle.SHAPE_MARGIN_CLEAN_SCOPE,
            shape=oracle.MIN_SHAPE_MARGIN_SIMILARITY,
            **(clean | dirty),
        )


def test_heldout_trace_oracle_cli_writes_low_height_low_scan_packet(
    tmp_path: Path,
) -> None:
    evidence_tsv, trace_root = _write_low_height_low_scan_fixture(tmp_path)
    output_dir = tmp_path / "oracle"

    assert (
        cli.main(
            [
                "--alignment-backfill-cell-evidence-tsv",
                str(evidence_tsv),
                "--trace-root",
                str(trace_root),
                "--output-dir",
                str(output_dir),
                "--source-run-id",
                "unit-low-height-low-scan-oracle",
                "--target-shape-class",
                "standard_low_height_low_scan_clean_trace",
                "--observed-reintegration-mode",
                "expected_window_bounded",
                "--expected-window-padding-min",
                "0.5",
            ],
        )
        == 0
    )

    summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary["status"] == "pass"
    assert summary["target_shape_class"] == (
        "standard_low_height_low_scan_clean_trace"
    )
    assert summary["observed_reintegration_mode"] == "expected_window_bounded"
    assert summary["available_candidate_rows"] == "1"
    assert summary["selected_case_count"] == "1"
    assert summary["oracle_case_status_pass_count"] == "1"

    pool = _read_tsv(output_dir / "heldout_trace_reintegration_full_eligible_pool.tsv")
    assert pool[0]["selected_for_oracle"] == "TRUE"
    assert float(pool[0]["cell_height"]) < oracle.MIN_CELL_HEIGHT
    assert oracle.MIN_LOW_SCAN_COUNT <= int(pool[0]["oracle_scan_count"]) <= (
        oracle.MAX_LOW_SCAN_COUNT
    )


def test_heldout_trace_oracle_cli_writes_low_height_stability_family_packet(
    tmp_path: Path,
) -> None:
    evidence_tsv, trace_root = _write_low_height_fixture(tmp_path)
    stability_tsv = tmp_path / "reintegration_stability_audit.tsv"
    activation_scope_tsv = tmp_path / "activation_high_signal_clean_scope_audit.tsv"
    _write_tsv(
        stability_tsv,
        [
            {
                "schema_version": "standard_peak_reintegration_stability_audit_v1",
                "source_run_id": "unit-stability",
                "feature_family_id": "FAM_LOW_HEIGHT",
                "sample_id": "BackfilledSample",
                "matrix_value_effect": "written",
                "matrix_value_source_row_sha256": "stable-low-height-sha",
                "stability_status": "eligible",
            },
        ],
    )
    _write_tsv(
        activation_scope_tsv,
        [
            {
                "schema_version": "standard_peak_activation_scope_audit_v1",
                "source_run_id": "unit-activation",
                "feature_family_id": "FAM_LOW_HEIGHT",
                "sample_id": "BackfilledSample",
                "matrix_value_effect": "written",
                "matrix_value_source_row_sha256": "stable-low-height-sha",
                "cell_height": "500000",
            },
        ],
    )
    output_dir = tmp_path / "oracle"

    assert (
        cli.main(
            [
                "--alignment-backfill-cell-evidence-tsv",
                str(evidence_tsv),
                "--trace-root",
                str(trace_root),
                "--output-dir",
                str(output_dir),
                "--source-run-id",
                "unit-low-height-stability-family-oracle",
                "--target-shape-class",
                "standard_low_height_reintegration_stable_candidate_family_trace",
                "--observed-reintegration-mode",
                "expected_window_bounded",
                "--expected-window-padding-min",
                "0.5",
                "--reintegration-stability-audit-tsv",
                str(stability_tsv),
                "--activation-scope-audit-tsv",
                str(activation_scope_tsv),
            ],
        )
        == 0
    )

    summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary["status"] == "pass"
    assert summary["target_shape_class"] == (
        "standard_low_height_reintegration_stable_candidate_family_trace"
    )
    assert summary["candidate_family_scope_status"] == "applied"
    assert summary["candidate_family_scope_row_count"] == "1"
    assert summary["candidate_family_scope_family_count"] == "1"
    assert summary["candidate_family_scope_match_level"] == "family_id"
    assert summary["candidate_family_scope_oracle_basis"] == (
        "detected_trace_rows_from_candidate_families"
    )
    assert summary["available_candidate_rows"] == "1"
    assert summary["selected_case_count"] == "1"
    assert summary["oracle_case_status_pass_count"] == "1"

    pool = _read_tsv(output_dir / "heldout_trace_reintegration_full_eligible_pool.tsv")
    assert pool[0]["feature_family_id"] == "FAM_LOW_HEIGHT"
    assert pool[0]["selected_for_oracle"] == "TRUE"


def test_low_height_stability_family_scope_requires_scope_inputs(
    tmp_path: Path,
) -> None:
    evidence_tsv, trace_root = _write_low_height_fixture(tmp_path)

    assert (
        cli.main(
            [
                "--alignment-backfill-cell-evidence-tsv",
                str(evidence_tsv),
                "--trace-root",
                str(trace_root),
                "--output-dir",
                str(tmp_path / "oracle"),
                "--source-run-id",
                "unit-missing-family-scope",
                "--target-shape-class",
                "standard_low_height_reintegration_stable_candidate_family_trace",
            ],
        )
        == 2
    )


def test_low_height_low_scan_target_shape_class_requires_both_edges() -> None:
    clean = {
        "shape": oracle.MIN_SHAPE_SIMILARITY,
        "local_global": oracle.MIN_LOCAL_GLOBAL_RATIO,
        "width": oracle.MIN_BOUNDARY_WIDTH_MIN,
        "apex_delta": oracle.MAX_APEX_DELTA_ABS_MIN,
    }

    assert oracle._target_shape_class_matches(
        oracle.LOW_HEIGHT_LOW_SCAN_CLEAN_SCOPE,
        height=oracle.MIN_CELL_HEIGHT - 1.0,
        scan_count=oracle.MIN_LOW_SCAN_COUNT,
        **clean,
    )
    assert oracle._target_shape_class_matches(
        oracle.LOW_HEIGHT_LOW_SCAN_CLEAN_SCOPE,
        height=oracle.MIN_CELL_HEIGHT - 1.0,
        scan_count=oracle.MAX_LOW_SCAN_COUNT,
        **(clean | {"width": oracle.MAX_BOUNDARY_WIDTH_MIN}),
    )

    dirty_cases = (
        {"shape": oracle.MIN_SHAPE_SIMILARITY - 0.0001},
        {"local_global": oracle.MIN_LOCAL_GLOBAL_RATIO - 0.0001},
        {"width": oracle.MIN_BOUNDARY_WIDTH_MIN - 0.0001},
        {"width": oracle.MAX_BOUNDARY_WIDTH_MIN + 0.0001},
        {"apex_delta": oracle.MAX_APEX_DELTA_ABS_MIN + 0.0001},
        {"height": oracle.MIN_CELL_HEIGHT},
        {"scan_count": oracle.MIN_LOW_SCAN_COUNT - 1},
        {"scan_count": oracle.MAX_LOW_SCAN_COUNT + 1},
    )
    for dirty in dirty_cases:
        candidate = {
            **clean,
            "height": oracle.MIN_CELL_HEIGHT - 1.0,
            "scan_count": oracle.MIN_LOW_SCAN_COUNT,
            **dirty,
        }
        assert not oracle._target_shape_class_matches(
            oracle.LOW_HEIGHT_LOW_SCAN_CLEAN_SCOPE,
            **candidate,
        )


def _write_low_scan_fixture(tmp_path: Path) -> tuple[Path, Path]:
    trace_root = tmp_path / "traces"
    trace_root.mkdir()
    rt = np.round(np.arange(0.0, 2.01, 0.05), 4)
    intensity = 1_000.0 + 5_000_000.0 * np.exp(-((rt - 1.0) ** 2) / (2 * 0.08**2))
    result = find_peak_and_area(rt, intensity, _config())
    assert result.peak is not None
    integration = integration_from_peak_trace(
        result.peak,
        rt,
        intensity,
        boundary_sources=("local_minimum",),
        integration_method="raw_trapezoid",
        baseline_integration_method="asls",
    )
    assert integration is not None
    assert integration.area_ms1_morphology is not None
    trace_json = trace_root / "FAM_LOW_SCAN_trace_data.json"
    trace_json.write_text(
        json.dumps(
            {
                "family_id": "FAM_LOW_SCAN",
                "family_center_rt": 1.0,
                "traces": [
                    {
                        "sample_stem": "SampleA",
                        "status": "detected",
                        "cell_area": float(result.peak.area),
                        "cell_height": float(result.peak.intensity),
                        "cell_apex_rt": float(result.peak.rt),
                        "cell_start_rt": 0.84995,
                        "cell_end_rt": 1.15005,
                        "local_window_to_global_max_ratio": 1.0,
                        "apex_aligned_shape_similarity": 0.99,
                        "rt": [float(value) for value in rt],
                        "intensity": [float(value) for value in intensity],
                    },
                ],
            },
        ),
        encoding="utf-8",
    )
    evidence_tsv = tmp_path / "alignment_backfill_cell_evidence.tsv"
    _write_tsv(
        evidence_tsv,
        [
            {
                "feature_family_id": "FAM_LOW_SCAN",
                "sample_stem": "SampleA",
                "status": "detected",
                "production_cell_status": "detected",
                "write_matrix_value": "TRUE",
                "include_in_primary_matrix": "TRUE",
                "primary_matrix_area": f"{integration.area_ms1_morphology:.8f}",
                "primary_matrix_area_source": (
                    "gaussian15_positive_asls_residual"
                ),
                "peak_start_rt": f"{result.peak.peak_start:.5f}",
                "peak_end_rt": f"{result.peak.peak_end:.5f}",
                "reason": (
                    "source_reason=sample-local MS1 owner with original MS2 "
                    "evidence"
                ),
            },
        ],
    )
    return evidence_tsv, trace_root


def _write_low_height_low_scan_fixture(tmp_path: Path) -> tuple[Path, Path]:
    trace_root = tmp_path / "traces"
    trace_root.mkdir()
    rt = np.round(np.arange(0.0, 2.01, 0.05), 4)
    intensity = 100.0 + 500_000.0 * np.exp(-((rt - 1.0) ** 2) / (2 * 0.08**2))
    result = find_peak_and_area(rt, intensity, _config())
    assert result.peak is not None
    integration = integration_from_peak_trace(
        result.peak,
        rt,
        intensity,
        boundary_sources=("local_minimum",),
        integration_method="raw_trapezoid",
        baseline_integration_method="asls",
    )
    assert integration is not None
    assert integration.area_ms1_morphology is not None
    trace_json = trace_root / "FAM_LOW_HEIGHT_LOW_SCAN_trace_data.json"
    trace_json.write_text(
        json.dumps(
            {
                "family_id": "FAM_LOW_HEIGHT_LOW_SCAN",
                "family_center_rt": 1.0,
                "traces": [
                    {
                        "sample_stem": "SampleA",
                        "status": "detected",
                        "cell_area": float(result.peak.area),
                        "cell_height": float(result.peak.intensity),
                        "cell_apex_rt": float(result.peak.rt),
                        "cell_start_rt": 0.84995,
                        "cell_end_rt": 1.15005,
                        "local_window_to_global_max_ratio": 1.0,
                        "apex_aligned_shape_similarity": 0.99,
                        "rt": [float(value) for value in rt],
                        "intensity": [float(value) for value in intensity],
                    },
                ],
            },
        ),
        encoding="utf-8",
    )
    evidence_tsv = tmp_path / "alignment_backfill_cell_evidence.tsv"
    _write_tsv(
        evidence_tsv,
        [
            {
                "feature_family_id": "FAM_LOW_HEIGHT_LOW_SCAN",
                "sample_stem": "SampleA",
                "status": "detected",
                "production_cell_status": "detected",
                "write_matrix_value": "TRUE",
                "include_in_primary_matrix": "TRUE",
                "primary_matrix_area": f"{integration.area_ms1_morphology:.8f}",
                "primary_matrix_area_source": (
                    "gaussian15_positive_asls_residual"
                ),
                "peak_start_rt": f"{result.peak.peak_start:.5f}",
                "peak_end_rt": f"{result.peak.peak_end:.5f}",
                "reason": (
                    "source_reason=sample-local MS1 owner with original MS2 "
                    "evidence"
                ),
            },
        ],
    )
    return evidence_tsv, trace_root


def _write_shape_margin_fixture(tmp_path: Path) -> tuple[Path, Path]:
    trace_root = tmp_path / "traces"
    trace_root.mkdir()
    rt = np.round(np.arange(0.0, 2.01, 0.05), 4)
    intensity = 1_000.0 + 5_000_000.0 * np.exp(-((rt - 1.0) ** 2) / (2 * 0.12**2))
    result = find_peak_and_area(rt, intensity, _config())
    assert result.peak is not None
    integration = integration_from_peak_trace(
        result.peak,
        rt,
        intensity,
        boundary_sources=("local_minimum",),
        integration_method="raw_trapezoid",
        baseline_integration_method="asls",
    )
    assert integration is not None
    assert integration.area_ms1_morphology is not None
    trace_json = trace_root / "FAM_SHAPE_MARGIN_trace_data.json"
    trace_json.write_text(
        json.dumps(
            {
                "family_id": "FAM_SHAPE_MARGIN",
                "family_center_rt": 1.0,
                "traces": [
                    {
                        "sample_stem": "SampleA",
                        "status": "detected",
                        "cell_area": float(result.peak.area),
                        "cell_height": float(result.peak.intensity),
                        "cell_apex_rt": float(result.peak.rt),
                        "cell_start_rt": float(result.peak.peak_start),
                        "cell_end_rt": float(result.peak.peak_end),
                        "local_window_to_global_max_ratio": 1.0,
                        "apex_aligned_shape_similarity": 0.94,
                        "rt": [float(value) for value in rt],
                        "intensity": [float(value) for value in intensity],
                    },
                ],
            },
        ),
        encoding="utf-8",
    )
    evidence_tsv = tmp_path / "alignment_backfill_cell_evidence.tsv"
    _write_tsv(
        evidence_tsv,
        [
            {
                "feature_family_id": "FAM_SHAPE_MARGIN",
                "sample_stem": "SampleA",
                "status": "detected",
                "production_cell_status": "detected",
                "write_matrix_value": "TRUE",
                "include_in_primary_matrix": "TRUE",
                "primary_matrix_area": f"{integration.area_ms1_morphology:.8f}",
                "primary_matrix_area_source": (
                    "gaussian15_positive_asls_residual"
                ),
                "peak_start_rt": f"{result.peak.peak_start:.5f}",
                "peak_end_rt": f"{result.peak.peak_end:.5f}",
                "reason": (
                    "source_reason=sample-local MS1 owner with original MS2 "
                    "evidence"
                ),
            },
        ],
    )
    return evidence_tsv, trace_root


def _write_width_fixture(tmp_path: Path) -> tuple[Path, Path]:
    trace_root = tmp_path / "traces"
    trace_root.mkdir()
    rt = np.round(np.arange(0.0, 3.01, 0.05), 4)
    intensity = 1_000.0 + 5_000_000.0 * np.exp(-((rt - 1.5) ** 2) / (2 * 0.28**2))
    result = find_peak_and_area(rt, intensity, _config())
    assert result.peak is not None
    integration = integration_from_peak_trace(
        result.peak,
        rt,
        intensity,
        boundary_sources=("local_minimum",),
        integration_method="raw_trapezoid",
        baseline_integration_method="asls",
    )
    assert integration is not None
    assert integration.area_ms1_morphology is not None
    assert result.peak.peak_end - result.peak.peak_start > 0.65
    trace_json = trace_root / "FAM_WIDTH_trace_data.json"
    trace_json.write_text(
        json.dumps(
            {
                "family_id": "FAM_WIDTH",
                "family_center_rt": float(result.peak.rt),
                "traces": [
                    {
                        "sample_stem": "SampleA",
                        "status": "detected",
                        "cell_area": float(result.peak.area),
                        "cell_height": float(result.peak.intensity),
                        "cell_apex_rt": float(result.peak.rt),
                        "cell_start_rt": float(result.peak.peak_start),
                        "cell_end_rt": float(result.peak.peak_end),
                        "local_window_to_global_max_ratio": 1.0,
                        "apex_aligned_shape_similarity": 0.99,
                        "rt": [float(value) for value in rt],
                        "intensity": [float(value) for value in intensity],
                    },
                ],
            },
        ),
        encoding="utf-8",
    )
    evidence_tsv = tmp_path / "alignment_backfill_cell_evidence.tsv"
    _write_tsv(
        evidence_tsv,
        [
            {
                "feature_family_id": "FAM_WIDTH",
                "sample_stem": "SampleA",
                "status": "detected",
                "production_cell_status": "detected",
                "write_matrix_value": "TRUE",
                "include_in_primary_matrix": "TRUE",
                "primary_matrix_area": f"{integration.area_ms1_morphology:.8f}",
                "primary_matrix_area_source": (
                    "gaussian15_positive_asls_residual"
                ),
                "peak_start_rt": f"{result.peak.peak_start:.5f}",
                "peak_end_rt": f"{result.peak.peak_end:.5f}",
                "reason": (
                    "source_reason=sample-local MS1 owner with original MS2 "
                    "evidence"
                ),
            },
        ],
    )
    return evidence_tsv, trace_root


def _write_apex_delta_fixture(tmp_path: Path) -> tuple[Path, Path]:
    trace_root = tmp_path / "traces"
    trace_root.mkdir()
    rt = np.round(np.arange(0.0, 2.01, 0.05), 4)
    intensity = 1_000.0 + 5_000_000.0 * np.exp(-((rt - 1.0) ** 2) / (2 * 0.12**2))
    result = find_peak_and_area(rt, intensity, _config())
    assert result.peak is not None
    integration = integration_from_peak_trace(
        result.peak,
        rt,
        intensity,
        boundary_sources=("local_minimum",),
        integration_method="raw_trapezoid",
        baseline_integration_method="asls",
    )
    assert integration is not None
    assert integration.area_ms1_morphology is not None
    trace_json = trace_root / "FAM_APEX_DELTA_trace_data.json"
    trace_json.write_text(
        json.dumps(
            {
                "family_id": "FAM_APEX_DELTA",
                "family_center_rt": 1.35,
                "traces": [
                    {
                        "sample_stem": "SampleA",
                        "status": "detected",
                        "cell_area": float(result.peak.area),
                        "cell_height": float(result.peak.intensity),
                        "cell_apex_rt": float(result.peak.rt),
                        "cell_start_rt": float(result.peak.peak_start),
                        "cell_end_rt": float(result.peak.peak_end),
                        "local_window_to_global_max_ratio": 1.0,
                        "apex_aligned_shape_similarity": 0.99,
                        "rt": [float(value) for value in rt],
                        "intensity": [float(value) for value in intensity],
                    },
                ],
            },
        ),
        encoding="utf-8",
    )
    evidence_tsv = tmp_path / "alignment_backfill_cell_evidence.tsv"
    _write_tsv(
        evidence_tsv,
        [
            {
                "feature_family_id": "FAM_APEX_DELTA",
                "sample_stem": "SampleA",
                "status": "detected",
                "production_cell_status": "detected",
                "write_matrix_value": "TRUE",
                "include_in_primary_matrix": "TRUE",
                "primary_matrix_area": f"{integration.area_ms1_morphology:.8f}",
                "primary_matrix_area_source": (
                    "gaussian15_positive_asls_residual"
                ),
                "peak_start_rt": f"{result.peak.peak_start:.5f}",
                "peak_end_rt": f"{result.peak.peak_end:.5f}",
                "reason": (
                    "source_reason=sample-local MS1 owner with original MS2 "
                    "evidence"
                ),
            },
        ],
    )
    return evidence_tsv, trace_root


def _write_low_height_fixture(tmp_path: Path) -> tuple[Path, Path]:
    trace_root = tmp_path / "traces"
    trace_root.mkdir()
    rt = np.round(np.arange(0.0, 2.01, 0.05), 4)
    intensity = 100.0 + 500_000.0 * np.exp(-((rt - 1.0) ** 2) / (2 * 0.12**2))
    result = find_peak_and_area(rt, intensity, _config())
    assert result.peak is not None
    integration = integration_from_peak_trace(
        result.peak,
        rt,
        intensity,
        boundary_sources=("local_minimum",),
        integration_method="raw_trapezoid",
        baseline_integration_method="asls",
    )
    assert integration is not None
    assert integration.area_ms1_morphology is not None
    trace_json = trace_root / "FAM_LOW_HEIGHT_trace_data.json"
    trace_json.write_text(
        json.dumps(
            {
                "family_id": "FAM_LOW_HEIGHT",
                "family_center_rt": 1.0,
                "traces": [
                    {
                        "sample_stem": "SampleA",
                        "status": "detected",
                        "cell_area": float(result.peak.area),
                        "cell_height": float(result.peak.intensity),
                        "cell_apex_rt": float(result.peak.rt),
                        "cell_start_rt": float(result.peak.peak_start),
                        "cell_end_rt": float(result.peak.peak_end),
                        "local_window_to_global_max_ratio": 1.0,
                        "apex_aligned_shape_similarity": 0.99,
                        "rt": [float(value) for value in rt],
                        "intensity": [float(value) for value in intensity],
                    },
                ],
            },
        ),
        encoding="utf-8",
    )
    evidence_tsv = tmp_path / "alignment_backfill_cell_evidence.tsv"
    _write_tsv(
        evidence_tsv,
        [
            {
                "feature_family_id": "FAM_LOW_HEIGHT",
                "sample_stem": "SampleA",
                "status": "detected",
                "production_cell_status": "detected",
                "write_matrix_value": "TRUE",
                "include_in_primary_matrix": "TRUE",
                "primary_matrix_area": f"{integration.area_ms1_morphology:.8f}",
                "primary_matrix_area_source": (
                    "gaussian15_positive_asls_residual"
                ),
                "peak_start_rt": f"{result.peak.peak_start:.5f}",
                "peak_end_rt": f"{result.peak.peak_end:.5f}",
                "reason": (
                    "source_reason=sample-local MS1 owner with original MS2 "
                    "evidence"
                ),
            },
        ],
    )
    return evidence_tsv, trace_root


def _write_flat_bounded_trace_fixture(tmp_path: Path) -> tuple[Path, Path]:
    evidence_tsv, trace_root = _write_low_height_fixture(tmp_path)
    trace_json = trace_root / "FAM_LOW_HEIGHT_trace_data.json"
    data = json.loads(trace_json.read_text(encoding="utf-8"))
    trace = data["traces"][0]
    trace["intensity"] = [100.0 for _ in trace["rt"]]
    trace_json.write_text(json.dumps(data), encoding="utf-8")
    return evidence_tsv, trace_root


def _write_boundary_drift_fixture(tmp_path: Path) -> tuple[Path, Path]:
    trace_root = tmp_path / "traces"
    trace_root.mkdir()
    rt = np.round(np.arange(0.0, 2.01, 0.05), 4)
    intensity = (
        100.0
        + 500_000.0 * np.exp(-((rt - 1.0) ** 2) / (2 * 0.10**2))
        + 50_000.0 * np.exp(-((rt - 0.65) ** 2) / (2 * 0.22**2))
    )
    oracle_start = 0.70
    oracle_end = 1.20
    oracle_apex = 1.0
    bounded_mask = (rt >= oracle_start - 0.1) & (rt <= oracle_end + 0.1)
    bounded_rt = rt[bounded_mask]
    bounded_intensity = intensity[bounded_mask]
    bounded_result = find_peak_and_area(
        bounded_rt,
        bounded_intensity,
        _config(),
        preferred_rt=oracle_apex,
        strict_preferred_rt=True,
    )
    assert bounded_result.peak is not None
    bounded_integration = integration_from_peak_trace(
        bounded_result.peak,
        bounded_rt,
        bounded_intensity,
        boundary_sources=("local_minimum",),
        integration_method="raw_trapezoid",
        baseline_integration_method="asls",
    )
    assert bounded_integration is not None
    assert bounded_integration.area_ms1_morphology is not None

    full_result = find_peak_and_area(rt, intensity, _config())
    assert full_result.peak is not None
    assert (
        max(
            abs(full_result.peak.peak_start - oracle_start),
            abs(full_result.peak.peak_end - oracle_end),
        )
        > 0.1
    )

    trace_json = trace_root / "FAM_BOUNDARY_DRIFT_trace_data.json"
    trace_json.write_text(
        json.dumps(
            {
                "family_id": "FAM_BOUNDARY_DRIFT",
                "family_center_rt": oracle_apex,
                "traces": [
                    {
                        "sample_stem": "SampleA",
                        "status": "detected",
                        "cell_area": float(
                            bounded_integration.area_ms1_morphology,
                        ),
                        "cell_height": 500_000.0,
                        "cell_apex_rt": oracle_apex,
                        "cell_start_rt": oracle_start,
                        "cell_end_rt": oracle_end,
                        "local_window_to_global_max_ratio": 1.0,
                        "apex_aligned_shape_similarity": 0.99,
                        "rt": [float(value) for value in rt],
                        "intensity": [float(value) for value in intensity],
                    },
                ],
            },
        ),
        encoding="utf-8",
    )
    evidence_tsv = tmp_path / "alignment_backfill_cell_evidence.tsv"
    _write_tsv(
        evidence_tsv,
        [
            {
                "feature_family_id": "FAM_BOUNDARY_DRIFT",
                "sample_stem": "SampleA",
                "status": "detected",
                "production_cell_status": "detected",
                "write_matrix_value": "TRUE",
                "include_in_primary_matrix": "TRUE",
                "primary_matrix_area": (
                    f"{bounded_integration.area_ms1_morphology:.8f}"
                ),
                "primary_matrix_area_source": (
                    "gaussian15_positive_asls_residual"
                ),
                "peak_start_rt": f"{oracle_start:.5f}",
                "peak_end_rt": f"{oracle_end:.5f}",
                "reason": (
                    "source_reason=sample-local MS1 owner with original MS2 "
                    "evidence"
                ),
            },
        ],
    )
    return evidence_tsv, trace_root


def _config() -> ExtractionConfig:
    return ExtractionConfig(
        data_dir=Path("."),
        dll_dir=Path("."),
        output_csv=Path("unused.csv"),
        diagnostics_csv=Path("unused_diagnostics.csv"),
        smooth_window=15,
        smooth_polyorder=3,
        peak_rel_height=0.05,
        peak_min_prominence_ratio=0.0,
        ms2_precursor_tol_da=0.5,
        nl_min_intensity_ratio=0.0,
        resolver_mode="local_minimum",
        resolver_min_search_range_min=0.08,
        resolver_min_relative_height=0.02,
        resolver_min_ratio_top_edge=1.7,
        resolver_peak_duration_max=2.0,
        baseline_integration_method="asls",
    )


def _write_tsv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def _read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))
