import csv
from pathlib import Path

from tools.diagnostics import instrument_qc_matrix_calibration_preview


TREND_COLUMNS = [
    "sample_name",
    "raw_path",
    "injection_order",
    "compound",
    "precursor_mz",
    "identity_evidence",
    "reference_rt_min",
    "rt_delta_to_reference_min",
    "apex_rt_min",
    "area",
    "base_width_min",
    "reference_base_width_min",
    "base_width_ratio_to_reference",
    "peak_start_rt_min",
    "peak_end_rt_min",
    "trend_confidence",
    "trend_flags",
    "status",
    "reason",
]


def _write_tsv(path: Path, columns: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def _write_trend(path: Path) -> None:
    _write_tsv(
        path,
        TREND_COLUMNS,
        [
            {
                "sample_name": "SDOLEK_1",
                "raw_path": "SDOLEK_1.raw",
                "injection_order": "4",
                "compound": "SDO",
                "precursor_mz": "311.0814",
                "identity_evidence": "MS1_ONLY",
                "reference_rt_min": "6.26",
                "rt_delta_to_reference_min": "0.05",
                "apex_rt_min": "6.31",
                "area": "1000",
                "base_width_min": "0.83",
                "reference_base_width_min": "0.83",
                "base_width_ratio_to_reference": "1",
                "peak_start_rt_min": "5.9",
                "peak_end_rt_min": "6.73",
                "trend_confidence": "clean",
                "trend_flags": "",
                "status": "detected",
                "reason": "OK",
            }
        ],
    )


def _write_alignment_cells(path: Path) -> None:
    path.write_text(
        "\t".join(
            [
                "feature_family_id",
                "sample_stem",
                "status",
                "area",
                "apex_rt",
                "source_raw_file",
                "family_center_mz",
                "family_center_rt",
            ]
        )
        + "\n"
        + "\t".join(
            [
                "FAM001",
                "SampleA",
                "detected",
                "1000",
                "12.05",
                "SampleA.raw",
                "300.0",
                "12.0",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def test_cli_writes_level0_bundle_without_matrix_input(tmp_path: Path) -> None:
    instrument_qc_dir = tmp_path / "instrument_qc"
    _write_trend(instrument_qc_dir / "instrument_qc_sdolek_trend.tsv")
    output_dir = tmp_path / "bundle"

    rc = instrument_qc_matrix_calibration_preview.main(
        [
            "--instrument-qc-dir",
            str(instrument_qc_dir),
            "--output-dir",
            str(output_dir),
        ]
    )

    assert rc == 0
    assert (output_dir / "instrument_qc_calibration_manifest.json").exists()
    assert (output_dir / "instrument_qc_calibration_evidence.tsv").exists()
    assert not (output_dir / "matrix_rt_calibration_preview.tsv").exists()


def test_cli_writes_level1_rt_preview_with_matrix_input(tmp_path: Path) -> None:
    instrument_qc_dir = tmp_path / "instrument_qc"
    _write_trend(instrument_qc_dir / "instrument_qc_sdolek_trend.tsv")
    matrix_input = tmp_path / "alignment_cells.tsv"
    _write_alignment_cells(matrix_input)
    output_dir = tmp_path / "bundle"

    rc = instrument_qc_matrix_calibration_preview.main(
        [
            "--instrument-qc-dir",
            str(instrument_qc_dir),
            "--matrix-input",
            str(matrix_input),
            "--matrix-input-role",
            "untargeted_cell_table",
            "--preview-kind",
            "rt",
            "--output-dir",
            str(output_dir),
        ]
    )

    assert rc == 0
    assert (output_dir / "matrix_rt_calibration_preview.tsv").exists()
    assert (output_dir / "matrix_rt_calibration_preview_summary.json").exists()


def test_cli_rejects_preview_without_matrix_input(tmp_path: Path, capsys) -> None:
    instrument_qc_dir = tmp_path / "instrument_qc"
    _write_trend(instrument_qc_dir / "instrument_qc_sdolek_trend.tsv")

    rc = instrument_qc_matrix_calibration_preview.main(
        [
            "--instrument-qc-dir",
            str(instrument_qc_dir),
            "--preview-kind",
            "rt",
            "--output-dir",
            str(tmp_path / "bundle"),
        ]
    )

    assert rc == 2
    assert "--matrix-input is required" in capsys.readouterr().err


def test_cli_rejects_missing_instrument_qc_dir(tmp_path: Path, capsys) -> None:
    rc = instrument_qc_matrix_calibration_preview.main(
        [
            "--instrument-qc-dir",
            str(tmp_path / "missing"),
            "--output-dir",
            str(tmp_path / "out"),
        ]
    )

    assert rc == 2
    assert "instrument QC dir not found" in capsys.readouterr().err
