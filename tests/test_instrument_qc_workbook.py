from pathlib import Path

from openpyxl import load_workbook

from xic_extractor.instrument_qc.models import (
    InstrumentQCDiagnostic,
    SDOLEKTrendRow,
)
from xic_extractor.instrument_qc.workbook import write_sdolek_workbook


def test_write_sdolek_workbook_has_overview_trend_and_diagnostics(
    tmp_path: Path,
) -> None:
    path = write_sdolek_workbook(
        tmp_path / "instrument_qc_trend_sdolek.xlsx",
        [_row(tmp_path / "SDOLEK-pretest.raw")],
        [
            InstrumentQCDiagnostic(
                sample_name="SDOLEK-pretest",
                raw_path=tmp_path / "SDOLEK-pretest.raw",
                issue="INJECTION_ORDER_MISSING",
                detail="No injection-order file supplied.",
            )
        ],
        metadata_source_status={
            "injection_order_source": "",
            "injection_order_status": "missing",
        },
    )

    workbook = load_workbook(path, data_only=False)

    assert workbook.sheetnames == ["Overview", "SDOLEK Trend", "Diagnostics"]
    assert workbook["Overview"]["A1"].value == "metric"
    assert workbook["Overview"]["A2"].value == "report_type"
    assert workbook["Overview"]["B4"].value == 1
    assert workbook["SDOLEK Trend"]["A1"].value == "sample_name"
    assert workbook["SDOLEK Trend"]["D2"].value == "SDO"
    assert workbook["Diagnostics"]["C2"].value == "INJECTION_ORDER_MISSING"


def test_write_sdolek_workbook_escapes_formula_like_values(tmp_path: Path) -> None:
    path = write_sdolek_workbook(
        tmp_path / "instrument_qc_trend_sdolek.xlsx",
        [_row(Path("=raw.raw"), sample_name="=SDOLEK")],
        [],
    )

    workbook = load_workbook(path, data_only=False)

    assert workbook["SDOLEK Trend"]["A2"].value == "'=SDOLEK"
    assert workbook["SDOLEK Trend"]["B2"].value.endswith("'=raw.raw")


def _row(raw_path: Path, *, sample_name: str = "SDOLEK-pretest") -> SDOLEKTrendRow:
    return SDOLEKTrendRow(
        sample_name=sample_name,
        raw_path=raw_path,
        injection_order=4,
        compound="SDO",
        precursor_mz=311.0814,
        identity_evidence="MS1_ONLY",
        reference_rt_min=6.26,
        rt_delta_to_reference_min=0.01,
        apex_rt_min=6.27,
        area=123.4,
        base_width_min=0.83,
        reference_base_width_min=0.83,
        base_width_ratio_to_reference=1.0,
        peak_start_rt_min=5.90,
        peak_end_rt_min=6.73,
        trend_confidence="clean",
        trend_flags=(),
        status="detected",
        reason="OK",
    )
