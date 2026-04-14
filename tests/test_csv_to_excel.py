import csv
from pathlib import Path

from openpyxl import Workbook, load_workbook

from scripts.csv_to_excel import (
    _build_data_sheet,
    _build_summary_sheet,
    _is_detected,
    _load_column_meta,
    run,
)
from xic_extractor.config import ExtractionConfig, Target


def _write_targets(tmp_path: Path, rows: str) -> None:
    (tmp_path / "targets.csv").write_text(
        "label,mz,rt_min,rt_max,ppm_tol,neutral_loss_da,nl_ppm_warn,nl_ppm_max,"
        "is_istd,istd_pair\n" + rows,
        encoding="utf-8-sig",
    )


def _metric_values(ws) -> dict[str, list[object]]:
    return {
        ws.cell(row=row_idx, column=1).value: [
            ws.cell(row=row_idx, column=col_idx).value
            for col_idx in range(2, ws.max_column + 1)
        ]
        for row_idx in range(2, ws.max_row + 1)
    }


def test_load_column_meta_includes_area_peak_bounds_and_nl_only_when_configured(
    tmp_path: Path,
) -> None:
    _write_targets(
        tmp_path,
        "Analyte,258.1085,8,10,20,116.0474,20,50,false,ISTD\n"
        "NoNL,200.0,1,2,20,,,,false,\n"
        "ISTD,261.1273,8,10,20,116.0474,20,50,true,\n",
    )

    meta = _load_column_meta(tmp_path)

    assert meta["Analyte_RT"]["type"] == "ms1_rt"
    assert meta["Analyte_Int"]["type"] == "ms1_int"
    assert meta["Analyte_Area"]["type"] == "ms1_area"
    assert meta["Analyte_PeakStart"]["type"] == "ms1_peak_start"
    assert meta["Analyte_PeakEnd"]["type"] == "ms1_peak_end"
    assert meta["Analyte_NL"]["type"] == "ms2_nl"
    assert meta["Analyte_RT"]["istd_pair"] == "ISTD"
    assert meta["ISTD_RT"]["is_istd"] is True
    assert "NoNL_NL" not in meta


def test_build_data_sheet_formats_area_peak_bounds_and_four_state_nl(
    tmp_path: Path,
) -> None:
    _write_targets(
        tmp_path,
        "Analyte,258.1085,8,10,20,116.0474,20,50,false,\n",
    )
    col_meta = _load_column_meta(tmp_path)
    rows = [
        _result_row("Tumor_1", "9.1234", "1000", "12345.6", "8.9", "9.3", "OK"),
        _result_row(
            "Tumor_2", "9.2000", "1100", "22345.6", "8.8", "9.4", "WARN_12.3ppm"
        ),
        _result_row("Tumor_3", "9.3000", "1200", "32345.6", "8.7", "9.5", "NL_FAIL"),
        _result_row("Tumor_4", "9.4000", "1300", "42345.6", "8.6", "9.6", "NO_MS2"),
        _result_row("Tumor_5", "ND", "ND", "ND", "ND", "ND", "ND"),
        _result_row("Tumor_6", "ERROR", "ERROR", "ERROR", "ERROR", "ERROR", "ERROR"),
    ]
    wb = Workbook()
    ws = wb.active

    _build_data_sheet(ws, rows, col_meta, list(rows[0].keys()))

    assert ws["D2"].value == 12345.6
    assert ws["D2"].number_format == "#,##0.00"
    assert ws["E2"].value == 8.9
    assert ws["F2"].value == 9.3
    assert ws["G2"].value == "✓"
    assert ws["G3"].value == "⚠ 12.3ppm"
    assert ws["G4"].value == "✗ NL"
    assert ws["G5"].value == "— MS2"
    assert ws["G2"].fill.fgColor.rgb.endswith("C8E6C9")
    assert ws["G3"].fill.fgColor.rgb.endswith("FFF9C4")
    assert ws["G4"].fill.fgColor.rgb.endswith("FFCDD2")
    assert ws["G5"].fill.fgColor.rgb.endswith("E0E0E0")
    assert ws["D6"].value == "ND"
    assert ws["D7"].value == "ERROR"


def test_data_sheet_forces_sample_names_and_target_labels_to_literal_text(
    tmp_path: Path,
) -> None:
    _write_targets(
        tmp_path,
        "=Bad,258.1085,8,10,20,116.0474,20,50,false,\n",
    )
    col_meta = _load_column_meta(tmp_path)
    rows = [
        {
            "SampleName": "+Sample",
            "=Bad_RT": "9.1",
            "=Bad_Int": "1000",
            "=Bad_Area": "10000",
            "=Bad_PeakStart": "8.9",
            "=Bad_PeakEnd": "9.3",
            "=Bad_NL": "OK",
        }
    ]
    wb = Workbook()
    ws = wb.active

    _build_data_sheet(ws, rows, col_meta, list(rows[0].keys()))

    assert ws["A2"].value == "'+Sample"
    assert ws["A2"].data_type != "f"
    assert ws["B1"].value.startswith("'=Bad")
    assert ws["B1"].data_type != "f"


def test_is_detected_uses_area_and_optionally_counts_no_ms2() -> None:
    row = {
        "Analyte_RT": "9.1",
        "Analyte_Area": "10000",
        "Analyte_NL": "NO_MS2",
        "Legacy_Int": "ND",
    }

    assert not _is_detected(row, "Analyte_RT", "Analyte_Area", "Analyte_NL", False)
    assert _is_detected(row, "Analyte_RT", "Analyte_Area", "Analyte_NL", True)
    assert not _is_detected(row, "Analyte_RT", "Missing_Area", None, True)
    assert _is_detected(row, "Analyte_RT", "Analyte_Area", None, False)


def test_build_summary_sheet_uses_area_metrics_and_independent_istd_eligibility(
    tmp_path: Path,
) -> None:
    _write_targets(
        tmp_path,
        "Analyte,258.1085,8,10,20,116.0474,20,50,false,ISTD\n"
        "ISTD,261.1273,8,10,20,116.0474,20,50,true,\n",
    )
    col_meta = _load_column_meta(tmp_path)
    rows = [
        _paired_row("Tumor_1", "9.0", "10000", "OK", "9.1", "20000", "OK"),
        _paired_row("Tumor_2", "9.2", "30000", "WARN_5ppm", "9.1", "60000", "OK"),
        _paired_row("Tumor_3", "9.3", "50000", "NO_MS2", "9.1", "100000", "NO_MS2"),
        _paired_row("Tumor_4", "9.4", "70000", "OK", "ND", "ND", "ND"),
    ]
    wb = Workbook()
    ws = wb.active

    _build_summary_sheet(
        ws,
        rows,
        col_meta,
        list(rows[0].keys()),
        count_no_ms2_as_detected=True,
    )
    metrics = _metric_values(ws)

    assert "Mean Int" not in metrics
    assert metrics["Median Area"][0] == "40,000.00"
    assert metrics["Area / ISTD ratio"][0] == "0.5000±0.0000 (n=3)"
    assert metrics["Area / ISTD ratio"][1] == "—"
    assert metrics["NL ✓/⚠/✗/—"][0] == "✓2 ⚠1 ✗0 —1"
    assert metrics["RT Δ vs ISTD (%)"][0] == "1.47±0.63% (n=3)"
    assert metrics["Total Detection"][0] == "4/4 (100%)"


def test_run_writes_diagnostics_sheet_and_makes_it_active(tmp_path: Path) -> None:
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
                "Analyte_NL": "NL_FAIL",
            }
        ],
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
    assert wb.sheetnames == ["XIC Results", "Summary", "Diagnostics"]
    assert wb.active.title == "Diagnostics"
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


def test_run_includes_diagnostics_sheet_when_file_has_only_headers(
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
                "Analyte_NL": "OK",
            }
        ],
    )
    _write_empty_diagnostics_csv(config.diagnostics_csv)

    excel_path = run(config, targets)

    wb = load_workbook(excel_path)
    assert wb.sheetnames == ["XIC Results", "Summary", "Diagnostics"]
    assert wb.active.title == "XIC Results"
    ws = wb["Diagnostics"]
    assert ws.auto_filter.ref == "A1:D1"


def _result_row(
    sample_name: str,
    rt: str,
    intensity: str,
    area: str,
    peak_start: str,
    peak_end: str,
    nl: str,
) -> dict[str, str]:
    return {
        "SampleName": sample_name,
        "Analyte_RT": rt,
        "Analyte_Int": intensity,
        "Analyte_Area": area,
        "Analyte_PeakStart": peak_start,
        "Analyte_PeakEnd": peak_end,
        "Analyte_NL": nl,
    }


def _paired_row(
    sample_name: str,
    analyte_rt: str,
    analyte_area: str,
    analyte_nl: str,
    istd_rt: str,
    istd_area: str,
    istd_nl: str,
) -> dict[str, str]:
    return {
        "SampleName": sample_name,
        "Analyte_RT": analyte_rt,
        "Analyte_Int": "1000",
        "Analyte_Area": analyte_area,
        "Analyte_PeakStart": "8.8",
        "Analyte_PeakEnd": "9.5",
        "Analyte_NL": analyte_nl,
        "ISTD_RT": istd_rt,
        "ISTD_Int": "2000",
        "ISTD_Area": istd_area,
        "ISTD_PeakStart": "8.8" if istd_rt != "ND" else "ND",
        "ISTD_PeakEnd": "9.5" if istd_rt != "ND" else "ND",
        "ISTD_NL": istd_nl,
    }


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
