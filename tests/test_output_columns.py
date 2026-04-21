from pathlib import Path

from openpyxl import load_workbook

from xic_extractor.extractor import ExtractionResult, FileResult, RunOutput, _write_xlsx
from xic_extractor.signal_processing import PeakDetectionResult, PeakResult


def _fabricate_run_output() -> RunOutput:
    peak = PeakResult(
        rt=9.03,
        intensity=500,
        intensity_smoothed=500,
        area=123.0,
        peak_start=8.9,
        peak_end=9.2,
    )
    peak_result = PeakDetectionResult(
        status="OK",
        peak=peak,
        n_points=10,
        max_smoothed=500.0,
        n_prominent_peaks=1,
        confidence="HIGH",
        reason="all checks passed",
    )
    extraction_result = ExtractionResult(
        peak_result=peak_result,
        nl=None,
        target_label="d3-5-hmdC",
        role="ISTD",
        istd_pair="",
        confidence="HIGH",
        reason="all checks passed",
        severities=(
            (0, "symmetry"),
            (1, "local_sn"),
            (0, "nl_support"),
            (2, "rt_prior"),
            (0, "rt_centrality"),
            (1, "noise_shape"),
            (0, "peak_width"),
        ),
        prior_rt=9.01,
        prior_source="rolling_median",
    )
    file_result = FileResult(
        sample_name="S1",
        results={"d3-5-hmdC": extraction_result},
        group=None,
    )
    return RunOutput(file_results=[file_result], diagnostics=[])


def test_main_sheet_has_confidence_and_reason(tmp_path: Path) -> None:
    out = tmp_path / "r.xlsx"
    _write_xlsx(out, _fabricate_run_output(), targets=[], emit_score_breakdown=False)
    wb = load_workbook(out, read_only=True)
    ws = wb["XIC Results"]
    headers = [cell.value for cell in next(ws.iter_rows(max_row=1))]
    assert "Confidence" in headers
    assert "Reason" in headers


def test_summary_sheet_has_confidence_counts(tmp_path: Path) -> None:
    out = tmp_path / "r.xlsx"
    _write_xlsx(out, _fabricate_run_output(), targets=[], emit_score_breakdown=False)
    wb = load_workbook(out, read_only=True)
    ws = wb["Summary"]
    headers = [cell.value for cell in next(ws.iter_rows(max_row=1))]
    for label in (
        "Confidence HIGH",
        "Confidence MEDIUM",
        "Confidence LOW",
        "Confidence VERY_LOW",
    ):
        assert label in headers


def test_score_breakdown_sheet_absent_by_default(tmp_path: Path) -> None:
    out = tmp_path / "r.xlsx"
    _write_xlsx(out, _fabricate_run_output(), targets=[], emit_score_breakdown=False)
    wb = load_workbook(out, read_only=True)
    assert "Score Breakdown" not in wb.sheetnames


def test_score_breakdown_sheet_emitted_when_flag_on(tmp_path: Path) -> None:
    out = tmp_path / "r.xlsx"
    _write_xlsx(out, _fabricate_run_output(), targets=[], emit_score_breakdown=True)
    wb = load_workbook(out, read_only=True)
    assert "Score Breakdown" in wb.sheetnames
    ws = wb["Score Breakdown"]
    rows = list(ws.iter_rows(values_only=True))
    headers = list(rows[0])
    for col in (
        "SampleName",
        "Target",
        "symmetry",
        "local_sn",
        "nl_support",
        "rt_prior",
        "rt_centrality",
        "noise_shape",
        "peak_width",
        "Total Severity",
        "Confidence",
        "Prior RT",
        "Prior Source",
    ):
        assert col in headers
    assert len(rows) == 2
    row = dict(zip(headers, rows[1], strict=False))
    assert row["SampleName"] == "S1"
    assert row["Target"] == "d3-5-hmdC"
    assert row["local_sn"] == 1
    assert row["rt_prior"] == 2
    assert row["noise_shape"] == 1
    assert row["Total Severity"] == 4
    assert row["Confidence"] == "HIGH"
    assert row["Prior RT"] == 9.01
    assert row["Prior Source"] == "rolling_median"
