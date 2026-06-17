from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np

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
