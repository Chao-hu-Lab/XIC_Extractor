from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from tools.diagnostics.instrument_qc_rt_supported_shadow_gate import main
from xic_extractor.instrument_qc.rt_supported_shadow_gate_io import (
    build_rt_supported_shadow_gate_from_files,
)

MATRIX_COLUMNS = [
    "source_row_id",
    "source_cell_key",
    "feature_id",
    "sample_name",
    "sample_stem",
    "feature_mz",
    "raw_feature_rt_min",
    "injection_order",
    "coverage_status",
    "rt_alignment_support_status",
    "local_residual_p95_min",
    "rt_uncertainty_min",
    "local_biological_istd_anchor_count",
    "correction_status",
    "correction_block_reason",
]

TRANSFER_COLUMNS = [
    "target_label",
    "transfer_status",
    "direction_status",
    "biological_qc_count",
    "clean_standard_count",
    "biological_rt_range_min",
    "clean_rt_delta_range_min",
    "biological_slope_min_per_injection",
    "clean_slope_min_per_injection",
    "slope_magnitude_ratio",
    "clean_warning_count",
    "review_reason",
]

ANCHOR_COLUMNS = ["target_label", "sample_name", "injection_order", "observed_rt_min"]


def test_candidate_requires_clean_and_biological_support(tmp_path: Path) -> None:
    paths = _fixture_paths(tmp_path)
    _write_default_inputs(paths)

    result = build_rt_supported_shadow_gate_from_files(
        matrix_rt_preview_tsv=paths["matrix_tsv"],
        matrix_rt_preview_summary_json=paths["matrix_json"],
        biological_istd_transfer_tsv=paths["transfer_tsv"],
        biological_istd_transfer_json=paths["transfer_json"],
        biological_istd_anchor_rows_tsv=paths["anchors_tsv"],
    )

    assert result.run_verdict == "shadow_gate_ready"
    assert result.rows[0].row_classification == "rt_supported_shadow_candidate"
    assert result.rows[0].nearest_biological_istd_label == "d3-5-medC"
    assert result.rows[0].supporting_biological_istd_label == "d3-5-medC"


def test_candidate_reports_supporting_anchor_when_nearest_conflicts(
    tmp_path: Path,
) -> None:
    paths = _fixture_paths(tmp_path)
    _write_default_inputs(paths)
    _write_tsv(
        paths["transfer_tsv"],
        TRANSFER_COLUMNS,
        [
            _transfer_row("nearest-conflict", "transfer_not_supported"),
            _transfer_row("supporting-anchor", "transfer_supported"),
        ],
    )
    _write_tsv(
        paths["anchors_tsv"],
        ANCHOR_COLUMNS,
        [
            {
                "target_label": "nearest-conflict",
                "sample_name": "QC1",
                "injection_order": "5",
                "observed_rt_min": "24.1",
            },
            {
                "target_label": "supporting-anchor",
                "sample_name": "QC1",
                "injection_order": "6",
                "observed_rt_min": "24.2",
            },
        ],
    )

    result = build_rt_supported_shadow_gate_from_files(
        matrix_rt_preview_tsv=paths["matrix_tsv"],
        matrix_rt_preview_summary_json=paths["matrix_json"],
        biological_istd_transfer_tsv=paths["transfer_tsv"],
        biological_istd_transfer_json=paths["transfer_json"],
        biological_istd_anchor_rows_tsv=paths["anchors_tsv"],
    )

    row = result.rows[0]
    assert row.row_classification == "rt_supported_shadow_candidate"
    assert row.nearest_biological_istd_label == "nearest-conflict"
    assert row.nearest_biological_istd_transfer_status == "transfer_not_supported"
    assert row.supporting_biological_istd_label == "supporting-anchor"
    assert row.supporting_biological_istd_transfer_status == "transfer_supported"


def test_biological_anchor_loader_accepts_existing_rt_min_column(
    tmp_path: Path,
) -> None:
    paths = _fixture_paths(tmp_path)
    _write_default_inputs(paths)
    _write_tsv(
        paths["anchors_tsv"],
        ["target_label", "sample_name", "injection_order", "rt_min"],
        [
            {
                "target_label": "d3-5-medC",
                "sample_name": "QC1",
                "injection_order": "6",
                "rt_min": "24.2",
            }
        ],
    )

    result = build_rt_supported_shadow_gate_from_files(
        matrix_rt_preview_tsv=paths["matrix_tsv"],
        matrix_rt_preview_summary_json=paths["matrix_json"],
        biological_istd_transfer_tsv=paths["transfer_tsv"],
        biological_istd_transfer_json=paths["transfer_json"],
        biological_istd_anchor_rows_tsv=paths["anchors_tsv"],
    )

    assert result.run_verdict == "shadow_gate_ready"


def test_missing_anchor_rows_keeps_rows_context_incomplete(tmp_path: Path) -> None:
    paths = _fixture_paths(tmp_path)
    _write_default_inputs(paths, write_anchors=False)

    result = build_rt_supported_shadow_gate_from_files(
        matrix_rt_preview_tsv=paths["matrix_tsv"],
        matrix_rt_preview_summary_json=paths["matrix_json"],
        biological_istd_transfer_tsv=paths["transfer_tsv"],
        biological_istd_transfer_json=paths["transfer_json"],
    )

    assert result.run_verdict == "context_incomplete"
    assert result.rows[0].row_classification == "biological_context_missing"


def test_nonlocal_biological_anchor_becomes_clean_standard_only_review(
    tmp_path: Path,
) -> None:
    paths = _fixture_paths(tmp_path)
    _write_default_inputs(paths)
    _write_tsv(
        paths["anchors_tsv"],
        ANCHOR_COLUMNS,
        [
            {
                "target_label": "d3-5-medC",
                "sample_name": "QC1",
                "injection_order": "99",
                "observed_rt_min": "44.2",
            }
        ],
    )

    result = build_rt_supported_shadow_gate_from_files(
        matrix_rt_preview_tsv=paths["matrix_tsv"],
        matrix_rt_preview_summary_json=paths["matrix_json"],
        biological_istd_transfer_tsv=paths["transfer_tsv"],
        biological_istd_transfer_json=paths["transfer_json"],
        biological_istd_anchor_rows_tsv=paths["anchors_tsv"],
    )

    assert result.run_verdict == "context_incomplete"
    assert result.rows[0].row_classification == "clean_standard_only_review"


def test_missing_istd_scope_blocks_candidate(tmp_path: Path) -> None:
    paths = _fixture_paths(tmp_path)
    _write_default_inputs(paths, istd_scope="")

    result = build_rt_supported_shadow_gate_from_files(
        matrix_rt_preview_tsv=paths["matrix_tsv"],
        matrix_rt_preview_summary_json=paths["matrix_json"],
        biological_istd_transfer_tsv=paths["transfer_tsv"],
        biological_istd_transfer_json=paths["transfer_json"],
        biological_istd_anchor_rows_tsv=paths["anchors_tsv"],
    )

    assert result.run_verdict == "context_incomplete"
    assert result.rows[0].row_classification == "biological_context_missing"


@pytest.mark.parametrize(
    ("updates", "expected"),
    [
        ({"coverage_status": "extrapolated"}, "coverage_not_supported"),
        ({"correction_status": "blocked_missing_value"}, "blocked_or_not_applicable"),
        ({"local_residual_p95_min": "0.31"}, "rt_model_uncertain"),
        ({"rt_uncertainty_min": "0.31"}, "rt_model_uncertain"),
    ],
)
def test_unsupported_rt_rows_never_become_candidates(
    tmp_path: Path,
    updates: dict[str, str],
    expected: str,
) -> None:
    paths = _fixture_paths(tmp_path)
    _write_default_inputs(paths, matrix_updates=updates)

    result = build_rt_supported_shadow_gate_from_files(
        matrix_rt_preview_tsv=paths["matrix_tsv"],
        matrix_rt_preview_summary_json=paths["matrix_json"],
        biological_istd_transfer_tsv=paths["transfer_tsv"],
        biological_istd_transfer_json=paths["transfer_json"],
        biological_istd_anchor_rows_tsv=paths["anchors_tsv"],
    )

    assert result.rows[0].row_classification == expected
    assert result.run_verdict != "shadow_gate_ready"


def test_transfer_conflict_is_explicit(tmp_path: Path) -> None:
    paths = _fixture_paths(tmp_path)
    _write_default_inputs(paths, transfer_status="transfer_not_supported")

    result = build_rt_supported_shadow_gate_from_files(
        matrix_rt_preview_tsv=paths["matrix_tsv"],
        matrix_rt_preview_summary_json=paths["matrix_json"],
        biological_istd_transfer_tsv=paths["transfer_tsv"],
        biological_istd_transfer_json=paths["transfer_json"],
        biological_istd_anchor_rows_tsv=paths["anchors_tsv"],
    )

    assert result.run_verdict == "no_supported_rows"
    assert result.rows[0].row_classification == "biological_transfer_conflict"


def test_missing_required_columns_fail_clearly(tmp_path: Path) -> None:
    paths = _fixture_paths(tmp_path)
    _write_default_inputs(paths)
    _write_tsv(paths["matrix_tsv"], ["source_row_id"], [{"source_row_id": "1"}])

    with pytest.raises(ValueError, match="missing required columns"):
        build_rt_supported_shadow_gate_from_files(
            matrix_rt_preview_tsv=paths["matrix_tsv"],
            matrix_rt_preview_summary_json=paths["matrix_json"],
            biological_istd_transfer_tsv=paths["transfer_tsv"],
            biological_istd_transfer_json=paths["transfer_json"],
            biological_istd_anchor_rows_tsv=paths["anchors_tsv"],
        )


def test_cli_invalid_input_writes_input_invalid_artifact(tmp_path: Path) -> None:
    paths = _fixture_paths(tmp_path)
    _write_default_inputs(paths)
    _write_tsv(paths["matrix_tsv"], ["source_row_id"], [{"source_row_id": "1"}])
    output_dir = tmp_path / "out"

    exit_code = main(
        [
            "--matrix-rt-preview-tsv",
            str(paths["matrix_tsv"]),
            "--matrix-rt-preview-summary-json",
            str(paths["matrix_json"]),
            "--biological-istd-transfer-tsv",
            str(paths["transfer_tsv"]),
            "--biological-istd-transfer-json",
            str(paths["transfer_json"]),
            "--biological-istd-anchor-rows-tsv",
            str(paths["anchors_tsv"]),
            "--output-dir",
            str(output_dir),
        ]
    )

    assert exit_code == 2
    payload = json.loads(
        (output_dir / "instrument_qc_rt_supported_shadow_gate.json").read_text(
            encoding="utf-8"
        )
    )
    assert payload["run_verdict"] == "input_invalid"
    assert "missing required columns" in payload["input_errors"][0]


@pytest.mark.parametrize("column_source", ["matrix", "anchor"])
def test_cli_rejects_non_integral_injection_order(
    tmp_path: Path,
    column_source: str,
) -> None:
    paths = _fixture_paths(tmp_path)
    if column_source == "matrix":
        _write_default_inputs(paths, matrix_updates={"injection_order": "5.9"})
    else:
        _write_default_inputs(paths)
        _write_tsv(
            paths["anchors_tsv"],
            ANCHOR_COLUMNS,
            [
                {
                    "target_label": "d3-5-medC",
                    "sample_name": "QC1",
                    "injection_order": "5.9",
                    "observed_rt_min": "24.2",
                }
            ],
        )
    output_dir = tmp_path / "out"

    exit_code = main(
        [
            "--matrix-rt-preview-tsv",
            str(paths["matrix_tsv"]),
            "--matrix-rt-preview-summary-json",
            str(paths["matrix_json"]),
            "--biological-istd-transfer-tsv",
            str(paths["transfer_tsv"]),
            "--biological-istd-transfer-json",
            str(paths["transfer_json"]),
            "--biological-istd-anchor-rows-tsv",
            str(paths["anchors_tsv"]),
            "--output-dir",
            str(output_dir),
        ]
    )

    payload = json.loads(
        (output_dir / "instrument_qc_rt_supported_shadow_gate.json").read_text(
            encoding="utf-8"
        )
    )
    assert exit_code == 2
    assert payload["run_verdict"] == "input_invalid"
    assert "must be an integer" in payload["input_errors"][0]


def test_cli_writes_outputs_and_summary_counts(tmp_path: Path) -> None:
    paths = _fixture_paths(tmp_path)
    _write_default_inputs(paths)
    output_dir = tmp_path / "out"

    exit_code = main(
        [
            "--matrix-rt-preview-tsv",
            str(paths["matrix_tsv"]),
            "--matrix-rt-preview-summary-json",
            str(paths["matrix_json"]),
            "--biological-istd-transfer-tsv",
            str(paths["transfer_tsv"]),
            "--biological-istd-transfer-json",
            str(paths["transfer_json"]),
            "--biological-istd-anchor-rows-tsv",
            str(paths["anchors_tsv"]),
            "--output-dir",
            str(output_dir),
        ]
    )

    assert exit_code == 0
    payload = json.loads(
        (output_dir / "instrument_qc_rt_supported_shadow_gate.json").read_text(
            encoding="utf-8"
        )
    )
    assert payload["run_verdict"] == "shadow_gate_ready"
    assert payload["counts_by_classification"] == {
        "rt_supported_shadow_candidate": 1
    }
    assert (output_dir / "instrument_qc_rt_supported_shadow_gate_rows.tsv").exists()
    markdown = (
        output_dir / "instrument_qc_rt_supported_shadow_gate.md"
    ).read_text(encoding="utf-8")
    assert "instrument_qc_rt_supported_shadow_gate_rows.tsv" in markdown
    assert "## Top Review Rows" in markdown


def test_cli_missing_artifact_writes_required_artifact_missing(
    tmp_path: Path,
) -> None:
    paths = _fixture_paths(tmp_path)
    _write_default_inputs(paths)
    paths["matrix_tsv"].unlink()
    output_dir = tmp_path / "out"

    exit_code = main(
        [
            "--matrix-rt-preview-tsv",
            str(paths["matrix_tsv"]),
            "--matrix-rt-preview-summary-json",
            str(paths["matrix_json"]),
            "--biological-istd-transfer-tsv",
            str(paths["transfer_tsv"]),
            "--biological-istd-transfer-json",
            str(paths["transfer_json"]),
            "--output-dir",
            str(output_dir),
        ]
    )

    assert exit_code == 0
    payload = json.loads(
        (output_dir / "instrument_qc_rt_supported_shadow_gate.json").read_text(
            encoding="utf-8"
        )
    )
    assert payload["run_verdict"] == "required_artifact_missing"
    assert payload["missing_artifacts"] == ["matrix_rt_calibration_preview.tsv"]


def _fixture_paths(tmp_path: Path) -> dict[str, Path]:
    return {
        "matrix_tsv": tmp_path / "matrix_rt_calibration_preview.tsv",
        "matrix_json": tmp_path / "matrix_rt_calibration_preview_summary.json",
        "transfer_tsv": tmp_path / "biological_istd_rt_transfer_audit.tsv",
        "transfer_json": tmp_path / "biological_istd_rt_transfer_audit.json",
        "anchors_tsv": tmp_path / "biological_istd_anchor_rows.tsv",
    }


def _write_default_inputs(
    paths: dict[str, Path],
    *,
    matrix_updates: dict[str, str] | None = None,
    transfer_status: str = "transfer_supported",
    istd_scope: str = "provided_biological_qc_istd_summary_rows_after_rt_gate_fix",
    write_anchors: bool = True,
) -> None:
    matrix_row = {
        "source_row_id": "2",
        "source_cell_key": "FAM001|QC1",
        "feature_id": "FAM001",
        "sample_name": "QC1",
        "sample_stem": "QC1",
        "feature_mz": "269.14",
        "raw_feature_rt_min": "24.1",
        "injection_order": "5",
        "coverage_status": "covered",
        "rt_alignment_support_status": "local_rt_supported",
        "local_residual_p95_min": "0.20",
        "rt_uncertainty_min": "0.20",
        "local_biological_istd_anchor_count": "0",
        "correction_status": "shadow_only",
        "correction_block_reason": "",
    }
    matrix_row.update(matrix_updates or {})
    _write_tsv(paths["matrix_tsv"], MATRIX_COLUMNS, [matrix_row])
    paths["matrix_json"].write_text(
        json.dumps(
            {
                "total_rows": 1,
                "counts_by_correction_status": {"shadow_only": 1},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    _write_tsv(
        paths["transfer_tsv"],
        TRANSFER_COLUMNS,
        [_transfer_row("d3-5-medC", transfer_status)],
    )
    paths["transfer_json"].write_text(
        json.dumps(
            {
                "istd_scope": istd_scope,
                "counts_by_transfer_status": {transfer_status: 1},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    if write_anchors:
        _write_tsv(
            paths["anchors_tsv"],
            ANCHOR_COLUMNS,
            [
                {
                    "target_label": "d3-5-medC",
                    "sample_name": "QC1",
                    "injection_order": "6",
                    "observed_rt_min": "24.2",
                }
            ],
        )


def _transfer_row(target_label: str, transfer_status: str) -> dict[str, str]:
    return {
        "target_label": target_label,
        "transfer_status": transfer_status,
        "direction_status": "same_direction",
        "biological_qc_count": "8",
        "clean_standard_count": "4",
        "biological_rt_range_min": "0.4",
        "clean_rt_delta_range_min": "0.3",
        "biological_slope_min_per_injection": "0.01",
        "clean_slope_min_per_injection": "0.01",
        "slope_magnitude_ratio": "1.0",
        "clean_warning_count": "0",
        "review_reason": "fixture",
    }


def _write_tsv(
    path: Path,
    fieldnames: list[str],
    rows: list[dict[str, str]],
) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)
