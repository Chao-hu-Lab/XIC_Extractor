import csv
from pathlib import Path

from openpyxl import Workbook

from tools.diagnostics.build_istd_false_missing_fixture import (
    FIELDNAMES,
    _targeted_rows,
    build_istd_false_missing_fixture,
    main,
)


def test_build_istd_false_missing_fixture_maps_qc_names_and_targeted_evidence(
    tmp_path: Path,
):
    old_path = tmp_path / "old.xlsx"
    targeted_path = tmp_path / "targeted.xlsx"
    output_csv = tmp_path / "fixture.csv"
    _write_old_matrix(old_path)
    _write_targeted_workbook(targeted_path)

    rows = build_istd_false_missing_fixture(
        old_matrix_path=old_path,
        targeted_workbook_path=targeted_path,
        output_csv=output_csv,
    )

    assert len(rows) == 2
    assert rows[0]["old_sample_id"] == "Breast_Cancer_Tissue_pooled_QC_1"
    assert rows[0]["targeted_sample_id"] == "Breast_Cancer_Tissue_pooled_QC1"
    assert rows[0]["targeted_confidence"] == "HIGH"
    assert rows[0]["targeted_nl"] == "✓"
    assert rows[1]["old_sample_id"] == "TumorBC2257_DNA"
    assert rows[1]["targeted_area"] == "8959790.66"
    assert _read_csv(output_csv) == rows
    assert _read_csv_header(output_csv) == list(FIELDNAMES)


def test_fixture_builder_main_writes_csv(tmp_path: Path):
    old_path = tmp_path / "old.xlsx"
    targeted_path = tmp_path / "targeted.xlsx"
    output_csv = tmp_path / "fixture.csv"
    _write_old_matrix(old_path)
    _write_targeted_workbook(targeted_path)

    code = main(
        [
            "--old-matrix",
            str(old_path),
            "--targeted-workbook",
            str(targeted_path),
            "--output-csv",
            str(output_csv),
        ],
    )

    assert code == 0
    assert output_csv.exists()


def test_fixture_builder_main_reports_missing_targeted_sheet(
    tmp_path: Path,
    capsys,
):
    old_path = tmp_path / "old.xlsx"
    targeted_path = tmp_path / "targeted.xlsx"
    output_csv = tmp_path / "fixture.csv"
    _write_old_matrix(old_path)
    _write_targeted_workbook(targeted_path, sheet_name="Other Results")

    code = _run_main(old_path, targeted_path, output_csv)

    assert code == 2
    assert "XIC Results" in capsys.readouterr().err


def test_fixture_builder_main_reports_missing_targeted_columns(
    tmp_path: Path,
    capsys,
):
    old_path = tmp_path / "old.xlsx"
    targeted_path = tmp_path / "targeted.xlsx"
    output_csv = tmp_path / "fixture.csv"
    _write_old_matrix(old_path)
    _write_targeted_workbook(targeted_path, omit_columns={"Confidence"})

    code = _run_main(old_path, targeted_path, output_csv)

    assert code == 2
    stderr = capsys.readouterr().err
    assert "missing columns" in stderr
    assert "Confidence" in stderr


def test_fixture_builder_main_reports_missing_targeted_evidence(
    tmp_path: Path,
    capsys,
):
    old_path = tmp_path / "old.xlsx"
    targeted_path = tmp_path / "targeted.xlsx"
    output_csv = tmp_path / "fixture.csv"
    _write_old_matrix(old_path)
    _write_targeted_workbook(targeted_path, rows=[])

    code = _run_main(old_path, targeted_path, output_csv)

    assert code == 2
    assert "Missing targeted evidence" in capsys.readouterr().err


def test_targeted_rows_ignore_blank_sample_before_first_sample(tmp_path: Path):
    targeted_path = tmp_path / "targeted.xlsx"
    _write_targeted_workbook(
        targeted_path,
        rows=[
            [
                None,
                "QC",
                "d3-5-medC",
                "ISTD",
                None,
                11.3876,
                23305406.99,
                "✓",
                100,
                11.2,
                11.5,
                0.3,
                "HIGH",
                "blank-leading row",
            ],
            [
                "Breast_Cancer_Tissue_pooled_QC1",
                "QC",
                "d3-5-medC",
                "ISTD",
                None,
                11.3876,
                23305406.99,
                "✓",
                100,
                11.2,
                11.5,
                0.3,
                "HIGH",
                "sample row",
            ],
        ],
    )

    rows = _targeted_rows(targeted_path, "XIC Results")

    assert ("d3-5-medC", "") not in rows
    assert ("d3-5-medC", "Breast_Cancer_Tissue_pooled_QC1") in rows


def _run_main(old_path: Path, targeted_path: Path, output_csv: Path) -> int:
    return main(
        [
            "--old-matrix",
            str(old_path),
            "--targeted-workbook",
            str(targeted_path),
            "--output-csv",
            str(output_csv),
        ],
    )


def _write_old_matrix(path: Path) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "RawIntensity"
    sheet.append(
        [
            "Mz/RT",
            "Breast_Cancer_Tissue_pooled_QC_1",
            "TumorBC2257_DNA",
            "Imputation_Tag_Reasons",
        ],
    )
    sheet.append(["245.1332/12.28", None, 123.0, ""])
    sheet.append(["261.1283/8.97", 456.0, None, ""])
    workbook.save(path)


def _write_targeted_workbook(
    path: Path,
    *,
    sheet_name: str = "XIC Results",
    omit_columns: set[str] | None = None,
    rows: list[list[object]] | None = None,
) -> None:
    omit_columns = omit_columns or set()
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = sheet_name
    header = [
        "SampleName",
        "Group",
        "Target",
        "Role",
        "ISTD Pair",
        "RT",
        "Area",
        "NL",
        "Int",
        "PeakStart",
        "PeakEnd",
        "PeakWidth",
        "Confidence",
        "Reason",
    ]
    default_rows = [
        [
            "Breast_Cancer_Tissue_pooled_QC1",
            "QC",
            "d3-5-medC",
            "ISTD",
            None,
            11.3876,
            23305406.99,
            "✓",
            100,
            11.2,
            11.5,
            0.3,
            "HIGH",
            "decision: accepted; support: strict NL OK",
        ],
        [
            "TumorBC2257_DNA",
            "Tumor",
            "d3-5-hmdC",
            "ISTD",
            None,
            9.2009,
            8959790.66,
            "✓",
            100,
            9.0,
            9.3,
            0.3,
            "HIGH",
            "decision: accepted; support: strict NL OK",
        ],
    ]
    sheet.append([name for name in header if name not in omit_columns])
    for row in default_rows if rows is None else rows:
        sheet.append(
            [
                value
                for name, value in zip(header, row)
                if name not in omit_columns
            ],
        )
    workbook.save(path)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _read_csv_header(path: Path) -> list[str]:
    with path.open(newline="", encoding="utf-8") as handle:
        return next(csv.reader(handle))
