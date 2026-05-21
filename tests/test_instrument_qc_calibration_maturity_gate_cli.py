import csv
import json
from pathlib import Path

from tools.diagnostics import instrument_qc_calibration_maturity_gate


def test_cli_writes_maturity_gate_outputs(tmp_path: Path) -> None:
    rt_json = tmp_path / "rt_model.json"
    matrix_json = tmp_path / "matrix_preview.json"
    matrix_tsv = tmp_path / "matrix_preview.tsv"
    transfer_json = tmp_path / "transfer.json"
    output_dir = tmp_path / "out"
    _write_json(
        rt_json,
        {
            "leave_one_anchor_out_status_counts": {
                "PASS": 107,
                "WARN": 41,
                "FAIL": 60,
            },
            "leave_one_anchor_out_p95_abs_error_min": 0.633,
        },
    )
    _write_json(
        matrix_json,
        {"counts_by_correction_status": {"shadow_only": 6279}},
    )
    _write_tsv(
        matrix_tsv,
        ["coverage_status", "correction_status", "correction_block_reason"],
        [
            {
                "coverage_status": "covered",
                "correction_status": "shadow_only",
                "correction_block_reason": "",
            },
            {
                "coverage_status": "extrapolated",
                "correction_status": "blocked_missing_value",
                "correction_block_reason": "raw feature RT is missing",
            },
        ],
    )
    _write_json(
        transfer_json,
        {
            "counts_by_transfer_status": {
                "transfer_supported": 3,
                "direction_supported_magnitude_shifted": 2,
                "transfer_not_supported": 1,
                "insufficient_biological_istd": 1,
            },
            "istd_scope": "provided_biological_qc_istd_summary_rows",
        },
    )

    rc = instrument_qc_calibration_maturity_gate.main(
        [
            "--rt-model-summary-json",
            str(rt_json),
            "--matrix-rt-preview-summary-json",
            str(matrix_json),
            "--matrix-rt-preview-tsv",
            str(matrix_tsv),
            "--biological-istd-transfer-json",
            str(transfer_json),
            "--output-dir",
            str(output_dir),
        ]
    )

    assert rc == 0
    rows_tsv = output_dir / "instrument_qc_calibration_maturity_gate.tsv"
    summary_json = output_dir / "instrument_qc_calibration_maturity_gate.json"
    review_md = output_dir / "instrument_qc_calibration_maturity_gate.md"
    assert rows_tsv.exists()
    assert summary_json.exists()
    assert review_md.exists()
    rows = list(csv.DictReader(rows_tsv.open(encoding="utf-8"), delimiter="\t"))
    assert rows[0]["maturity_level"] == "level_2"
    assert rows[0]["go_no_go"] == "go"
    assert rows[1]["maturity_level"] == "level_3"
    assert rows[1]["go_no_go"] == "no_go"


def test_cli_reports_missing_required_json(tmp_path: Path, capsys) -> None:
    rc = instrument_qc_calibration_maturity_gate.main(
        [
            "--rt-model-summary-json",
            str(tmp_path / "missing-rt.json"),
            "--matrix-rt-preview-summary-json",
            str(tmp_path / "missing-matrix.json"),
            "--matrix-rt-preview-tsv",
            str(tmp_path / "missing-matrix.tsv"),
            "--biological-istd-transfer-json",
            str(tmp_path / "missing-transfer.json"),
            "--output-dir",
            str(tmp_path / "out"),
        ]
    )

    assert rc == 2
    assert "required JSON not found" in capsys.readouterr().err


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_tsv(
    path: Path,
    columns: list[str],
    rows: list[dict[str, str]],
) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)
