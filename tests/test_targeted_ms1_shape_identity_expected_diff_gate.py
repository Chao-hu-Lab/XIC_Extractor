from __future__ import annotations

import csv
from pathlib import Path

import pytest

from tools.diagnostics import targeted_ms1_shape_identity_expected_diff_gate as tool
from xic_extractor.diagnostics.targeted_ms1_shape_identity_expected_diff import (
    evaluate_limited_targeted_ms1_shape_identity_expected_diff,
)


def test_limited_expected_diff_gate_accepts_hmdc_medc_flagged_rows() -> None:
    summary = evaluate_limited_targeted_ms1_shape_identity_expected_diff(
        [
            _expected_diff_row("S1", "5-hmdC"),
            _expected_diff_row("S2", "5-medC"),
        ],
        [
            _matrix_diff_row("S1", "5-hmdC_RT"),
            _matrix_diff_row("S1", "5-hmdC_Area"),
            _matrix_diff_row("S2", "5-medC_RT"),
            _matrix_diff_row("S2", "5-medC_Area"),
        ],
        expected_long_row_count=2,
        expected_matrix_cell_count=4,
    )

    assert summary.gate_status == "pass"
    assert summary.long_changed_rows == 2
    assert summary.matrix_changed_cells == 4
    assert summary.target_counts == {"5-hmdC": 1, "5-medC": 1}


def test_limited_expected_diff_gate_rejects_rows_outside_scope() -> None:
    with pytest.raises(ValueError, match="outside limited_5hmdc_5medc_v1 scope"):
        evaluate_limited_targeted_ms1_shape_identity_expected_diff(
            [_expected_diff_row("S1", "5-fC")],
            [_matrix_diff_row("S1", "5-hmdC_RT")],
        )


def test_limited_expected_diff_gate_rejects_clean_detected_output() -> None:
    row = _expected_diff_row("S1", "5-hmdC")
    row["optin_product_state"] = "detected_clean"

    with pytest.raises(ValueError, match="optin_product_state"):
        evaluate_limited_targeted_ms1_shape_identity_expected_diff(
            [row],
            [_matrix_diff_row("S1", "5-hmdC_RT")],
        )


def test_limited_expected_diff_gate_rejects_unexpected_matrix_column() -> None:
    with pytest.raises(ValueError, match="unexpected matrix measurement"):
        evaluate_limited_targeted_ms1_shape_identity_expected_diff(
            [_expected_diff_row("S1", "5-hmdC")],
            [_matrix_diff_row("S1", "5-hmdC_ReviewState")],
        )


def test_limited_expected_diff_gate_requires_matching_matrix_keys() -> None:
    with pytest.raises(ValueError, match="missing sample/target keys"):
        evaluate_limited_targeted_ms1_shape_identity_expected_diff(
            [
                _expected_diff_row("S1", "5-hmdC"),
                _expected_diff_row("S2", "5-medC"),
            ],
            [_matrix_diff_row("S1", "5-hmdC_RT")],
        )

    with pytest.raises(ValueError, match="keys outside expected diff"):
        evaluate_limited_targeted_ms1_shape_identity_expected_diff(
            [_expected_diff_row("S1", "5-hmdC")],
            [
                _matrix_diff_row("S1", "5-hmdC_RT"),
                _matrix_diff_row("S2", "5-medC_RT"),
            ],
        )


def test_limited_expected_diff_gate_cli_writes_summary(tmp_path: Path) -> None:
    expected_diff = tmp_path / "expected_diff_summary.tsv"
    matrix_diff = tmp_path / "matrix_diff_summary.tsv"
    summary_tsv = tmp_path / "gate_summary.tsv"
    _write_tsv(expected_diff, [_expected_diff_row("S1", "5-hmdC")])
    _write_tsv(matrix_diff, [_matrix_diff_row("S1", "5-hmdC_RT")])

    assert (
        tool.main(
            [
                "--expected-diff-summary-tsv",
                str(expected_diff),
                "--matrix-diff-summary-tsv",
                str(matrix_diff),
                "--summary-tsv",
                str(summary_tsv),
                "--expected-long-row-count",
                "1",
                "--expected-matrix-cell-count",
                "1",
            ]
        )
        == 0
    )

    rows = _read_tsv(summary_tsv)
    assert rows[0] == {"metric": "gate_status", "value": "pass"}
    assert {"metric": "long_changed_rows", "value": "1"} in rows


def _expected_diff_row(sample_name: str, target_name: str) -> dict[str, str]:
    return {
        "sample_name": sample_name,
        "target_name": target_name,
        "role": "Analyte",
        "changed_fields": (
            "Product State;Counted Detection;RT;Area;Int;PeakStart;PeakEnd;"
            "PeakWidth;Confidence;Reason;Projection Support Reasons;"
            "Projection Not Counted Reasons"
        ),
        "baseline_product_state": "not_counted",
        "optin_product_state": "detected_flagged",
        "baseline_counted_detection": "FALSE",
        "optin_counted_detection": "TRUE",
        "baseline_rt": "ND",
        "optin_rt": "9.10",
        "baseline_area": "ND",
        "optin_area": "12345.67",
        "baseline_nl": "NL_FAIL",
        "optin_nl": "NL_FAIL",
        "baseline_reason": (
            "decision: not_counted; "
            "not_counted: analyte_nl_fail_requires_policy"
        ),
        "optin_reason": (
            "decision: detected_flagged; support: own_max_same_peak_support"
        ),
    }


def _matrix_diff_row(
    row_key: str,
    column: str,
    *,
    optin_value: str = "9.10",
) -> dict[str, str]:
    return {
        "row_key": row_key,
        "column": column,
        "baseline_value": "ND",
        "optin_value": optin_value,
    }


def _write_tsv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=tuple(rows[0]), delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def _read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))
