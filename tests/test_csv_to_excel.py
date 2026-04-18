import csv
from pathlib import Path

from openpyxl import Workbook, load_workbook

from scripts.csv_to_excel import (
    _build_data_sheet,
    _build_summary_sheet,
    _wide_to_long_rows,
    run,
)
from xic_extractor.config import ExtractionConfig, Target


def test_build_data_sheet_uses_row_based_compact_view_with_hidden_advanced_columns(
    tmp_path: Path,
) -> None:
    rows = [
        _long_row("Tumor_1", "Analyte", "9.1234", "12345.6", "OK"),
        _long_row("Tumor_2", "Analyte", "9.2000", "22345.6", "WARN_12.3ppm"),
        _long_row("Tumor_3", "Analyte", "9.3000", "32345.6", "NL_FAIL"),
        _long_row("Tumor_4", "Analyte", "9.4000", "42345.6", "NO_MS2"),
        _long_row("Tumor_5", "Analyte", "ND", "ND", "ND"),
    ]
    wb = Workbook()
    ws = wb.active

    _build_data_sheet(ws, rows)

    assert [ws.cell(row=1, column=i).value for i in range(1, 13)] == [
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
    ]
    assert ws["F2"].value == 9.1234
    assert ws["F2"].number_format == "0.0000"
    assert ws["G2"].value == 12345.6
    assert ws["G2"].number_format == "0.00E+00"
    assert ws["H2"].value == "✓"
    assert ws["H3"].value == "⚠ 12.3ppm"
    assert ws["H4"].value == "✗ NL"
    assert ws["H5"].value == "— MS2"
    assert ws["H2"].fill.fgColor.rgb.endswith("C8E6C9")
    assert ws["I2"].value == 1000.0
    assert ws["I2"].number_format == "0.00E+00"
    assert abs(ws["L2"].value - 0.4) < 1e-9
    assert ws["L2"].number_format == "0.0000"
    assert ws.column_dimensions["I"].hidden is True
    assert ws.column_dimensions["J"].hidden is True
    assert ws.column_dimensions["K"].hidden is True
    assert ws.column_dimensions["L"].hidden is True
    assert ws.auto_filter.ref == "A1:L6"


def test_data_sheet_merges_repeated_sample_and_group_cells() -> None:
    rows = [
        _long_row("Tumor_1", "Analyte", "9.1", "10000", "OK"),
        _long_row("Tumor_1", "ISTD", "9.2", "20000", "OK", role="ISTD"),
        _long_row("Normal_1", "Analyte", "9.3", "30000", "OK"),
    ]
    wb = Workbook()
    ws = wb.active

    _build_data_sheet(ws, rows)

    merged_ranges = {str(cell_range) for cell_range in ws.merged_cells.ranges}
    assert "A2:A3" in merged_ranges
    assert "B2:B3" in merged_ranges
    assert "A4:A4" not in merged_ranges
    assert ws["A2"].value == "Tumor_1"
    assert ws["A3"].value is None
    assert ws["B2"].value == "Tumor"
    assert ws["B3"].value is None


def test_data_sheet_forces_sample_names_and_target_labels_to_literal_text() -> None:
    rows = [_long_row("+Sample", "=Bad", "9.1", "10000", "OK")]
    wb = Workbook()
    ws = wb.active

    _build_data_sheet(ws, rows)

    assert ws["A2"].value == "'+Sample"
    assert ws["A2"].data_type != "f"
    assert ws["C2"].value == "'=Bad"
    assert ws["C2"].data_type != "f"


def test_build_summary_sheet_uses_row_based_target_metrics() -> None:
    rows = [
        _long_row("Tumor_1", "Analyte", "9.0", "10000", "OK", istd_pair="ISTD"),
        _long_row("Tumor_1", "ISTD", "9.1", "20000", "OK", role="ISTD"),
        _long_row("Tumor_2", "Analyte", "9.2", "30000", "WARN_5ppm", istd_pair="ISTD"),
        _long_row("Tumor_2", "ISTD", "9.1", "60000", "OK", role="ISTD"),
        _long_row("Tumor_3", "Analyte", "9.3", "50000", "NO_MS2", istd_pair="ISTD"),
        _long_row("Tumor_3", "ISTD", "9.1", "100000", "NO_MS2", role="ISTD"),
        _long_row("Tumor_4", "Analyte", "9.4", "70000", "OK", istd_pair="ISTD"),
        _long_row("Tumor_4", "ISTD", "ND", "ND", "ND", role="ISTD"),
    ]
    wb = Workbook()
    ws = wb.active

    _build_summary_sheet(ws, rows, count_no_ms2_as_detected=True)
    data = _summary_rows(ws)

    assert "Mean Int" not in data["headers"]
    assert data["Analyte"]["Role"] == "Analyte"
    assert data["Analyte"]["Detected"] == 4
    assert data["Analyte"]["Total"] == 4
    assert data["Analyte"]["Detection %"] == "100%"
    assert "Median Area (detected)" in data["headers"]
    assert "Area / ISTD ratio (paired detected)" in data["headers"]
    assert data["Analyte"]["Median Area (detected)"] == 40000.0
    assert ws["H2"].number_format == "0.00E+00"
    assert data["Analyte"]["Area / ISTD ratio (paired detected)"] == "—"
    assert data["Analyte"]["NL OK"] == 2
    assert data["Analyte"]["NL WARN"] == 1
    assert data["Analyte"]["NL FAIL"] == 0
    assert data["Analyte"]["NO MS2"] == 1
    assert data["Analyte"]["RT Delta vs ISTD"] == "0.1333±0.0577 min (n=3)"
    assert data["ISTD"]["Area / ISTD ratio (paired detected)"] == "—"


def test_summary_area_ratio_uses_only_explicit_qc_samples() -> None:
    rows = [
        _long_row("Tumor_1", "Analyte", "9.0", "10000", "OK", istd_pair="ISTD"),
        _long_row("Tumor_1", "ISTD", "9.0", "10000", "OK", role="ISTD"),
        _long_row("Tumor_2", "Analyte", "9.0", "90000", "OK", istd_pair="ISTD"),
        _long_row("Tumor_2", "ISTD", "9.0", "10000", "OK", role="ISTD"),
        _long_row(
            "Breast Cancer Tissue_pooled_QC1",
            "Analyte",
            "9.0",
            "20000",
            "OK",
            istd_pair="ISTD",
        ),
        _long_row(
            "Breast Cancer Tissue_pooled_QC1",
            "ISTD",
            "9.0",
            "10000",
            "OK",
            role="ISTD",
        ),
        _long_row(
            "Breast Cancer Tissue_pooled_QC_2",
            "Analyte",
            "9.0",
            "40000",
            "OK",
            istd_pair="ISTD",
        ),
        _long_row(
            "Breast Cancer Tissue_pooled_QC_2",
            "ISTD",
            "9.0",
            "10000",
            "OK",
            role="ISTD",
        ),
    ]
    wb = Workbook()
    ws = wb.active

    _build_summary_sheet(ws, rows)
    data = _summary_rows(ws)

    assert data["Analyte"]["Detected"] == 4
    assert data["Analyte"]["Area / ISTD ratio (paired detected)"] == (
        "3.0000±1.4142, CV=47.1% (n=2)"
    )


def test_wide_to_long_rows_classifies_qc_from_sample_name_token() -> None:
    rows = [
        {
            "SampleName": "Breast Cancer Tissue_pooled_QC_1",
            "Analyte_RT": "9.0",
            "Analyte_Area": "10000",
            "Analyte_NL": "OK",
        },
        {
            "SampleName": "SampleA",
            "Analyte_RT": "9.0",
            "Analyte_Area": "10000",
            "Analyte_NL": "OK",
        },
        {
            "SampleName": "Breast_Cancer_Tissue_pooled_QC1",
            "Analyte_RT": "9.0",
            "Analyte_Area": "10000",
            "Analyte_NL": "OK",
        },
    ]

    long_rows = _wide_to_long_rows(rows, [_target("Analyte")])

    assert long_rows[0]["Group"] == "QC"
    assert long_rows[1]["Group"] == "Other"
    assert long_rows[2]["Group"] == "QC"


def test_run_writes_row_based_results_sheet_and_makes_diagnostics_active(
    tmp_path: Path,
) -> None:
    config = _config(tmp_path)
    targets = [_target("Analyte")]
    config.output_csv.parent.mkdir(parents=True)
    _write_csv(
        config.output_csv,
        [
            {
                "SampleName": "Tumor_1",
                "Analyte_RT": "ND",
                "Analyte_Int": "ND",
                "Analyte_Area": "ND",
                "Analyte_PeakStart": "ND",
                "Analyte_PeakEnd": "ND",
                "Analyte_PeakWidth": "ND",
                "Analyte_NL": "NL_FAIL",
            }
        ],
    )
    _write_csv(
        config.output_csv.with_name("xic_results_long.csv"),
        [_long_row("Tumor_1", "Analyte", "ND", "ND", "NL_FAIL")],
    )
    _write_csv(
        config.diagnostics_csv,
        [
            {
                "SampleName": "Tumor_1",
                "Target": "Analyte",
                "Issue": "NL_FAIL",
                "Reason": "=unsafe reason",
            }
        ],
    )

    excel_path = run(config, targets)

    wb = load_workbook(excel_path)
    assert wb.sheetnames == ["XIC Results", "Summary", "Targets", "Diagnostics"]
    assert wb.active.title == "Diagnostics"
    ws_results = wb["XIC Results"]
    assert ws_results["A1"].value == "SampleName"
    assert ws_results["C1"].value == "Target"
    assert ws_results["G1"].value == "Area"
    assert ws_results["I1"].value == "Int"
    assert ws_results.column_dimensions["I"].hidden is True
    ws = wb["Diagnostics"]
    assert [ws.cell(row=1, column=i).value for i in range(1, 5)] == [
        "SampleName",
        "Target",
        "Issue",
        "Reason",
    ]
    assert ws.auto_filter.ref == "A1:D2"
    assert ws["C2"].value == "NL_FAIL"
    assert ws["D2"].value == "'=unsafe reason"
    assert ws["C2"].fill.fgColor.rgb.endswith("FFCDD2")


def test_run_can_build_long_results_from_legacy_wide_csv_when_needed(
    tmp_path: Path,
) -> None:
    config = _config(tmp_path)
    targets = [_target("Analyte")]
    config.output_csv.parent.mkdir(parents=True)
    _write_csv(
        config.output_csv,
        [
            {
                "SampleName": "Tumor_1",
                "Analyte_RT": "9.1",
                "Analyte_Int": "1000",
                "Analyte_Area": "10000",
                "Analyte_PeakStart": "8.9",
                "Analyte_PeakEnd": "9.3",
                "Analyte_PeakWidth": "0.4000",
                "Analyte_NL": "OK",
            }
        ],
    )
    _write_empty_diagnostics_csv(config.diagnostics_csv)

    excel_path = run(config, targets)

    wb = load_workbook(excel_path)
    assert wb.sheetnames == ["XIC Results", "Summary", "Targets", "Diagnostics"]
    assert wb.active.title == "XIC Results"
    assert wb["XIC Results"]["C2"].value == "Analyte"
    assert wb["Diagnostics"].auto_filter.ref == "A1:D1"


def _long_row(
    sample_name: str,
    target: str,
    rt: str,
    area: str,
    nl: str,
    *,
    role: str = "Analyte",
    istd_pair: str = "",
) -> dict[str, str]:
    return {
        "SampleName": sample_name,
        "Group": "Tumor" if sample_name.startswith("Tumor") else "QC",
        "Target": target,
        "Role": role,
        "ISTD Pair": istd_pair,
        "RT": rt,
        "Area": area,
        "NL": nl,
        "Int": "1000",
        "PeakStart": "8.9",
        "PeakEnd": "9.3",
        "PeakWidth": "0.4000",
    }


def _summary_rows(ws) -> dict[str, object]:
    headers = [ws.cell(row=1, column=i).value for i in range(1, ws.max_column + 1)]
    data: dict[str, object] = {"headers": headers}
    for row_idx in range(2, ws.max_row + 1):
        target = ws.cell(row=row_idx, column=1).value
        data[target] = {
            headers[col_idx - 1]: ws.cell(row=row_idx, column=col_idx).value
            for col_idx in range(1, ws.max_column + 1)
        }
    return data


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _write_empty_diagnostics_csv(path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=["SampleName", "Target", "Issue", "Reason"]
        )
        writer.writeheader()


def _config(tmp_path: Path) -> ExtractionConfig:
    return ExtractionConfig(
        data_dir=tmp_path / "raw",
        dll_dir=tmp_path / "dll",
        output_csv=tmp_path / "output" / "xic_results.csv",
        diagnostics_csv=tmp_path / "output" / "xic_diagnostics.csv",
        smooth_window=15,
        smooth_polyorder=3,
        peak_rel_height=0.95,
        peak_min_prominence_ratio=0.10,
        ms2_precursor_tol_da=0.5,
        nl_min_intensity_ratio=0.01,
        count_no_ms2_as_detected=True,
    )


def _target(label: str) -> Target:
    return Target(
        label=label,
        mz=258.1085,
        rt_min=8.0,
        rt_max=10.0,
        ppm_tol=20.0,
        neutral_loss_da=116.0474,
        nl_ppm_warn=20.0,
        nl_ppm_max=50.0,
        is_istd=False,
        istd_pair="",
    )
