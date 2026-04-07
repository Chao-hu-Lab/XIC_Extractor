import statistics
from pathlib import Path

from openpyxl import Workbook

from scripts.csv_to_excel import (
    _build_data_sheet,
    _build_summary_sheet,
    _load_column_meta,
    run,
)


def _write_targets(tmp_path: Path, rows: str) -> None:
    (tmp_path / "targets.csv").write_text(
        "label,mz,rt_min,rt_max,ppm_tol,neutral_loss_da,nl_ppm_warn,nl_ppm_max,is_istd,istd_pair\n"
        + rows,
        encoding="utf-8-sig",
    )


def test_load_column_meta_is_istd(tmp_path):
    _write_targets(
        tmp_path,
        "5-hmdC,258.1085,8,10,20,116.0474,20,50,false,d3-5-hmdC\n"
        "d3-5-hmdC,261.1273,8,10,20,116.0474,20,50,true,\n",
    )
    meta = _load_column_meta(tmp_path)
    assert meta["5-hmdC_RT"]["is_istd"] is False
    assert meta["d3-5-hmdC_RT"]["is_istd"] is True


def test_load_column_meta_istd_pair(tmp_path):
    _write_targets(
        tmp_path,
        "5-hmdC,258.1085,8,10,20,116.0474,20,50,false,d3-5-hmdC\n"
        "d3-5-hmdC,261.1273,8,10,20,116.0474,20,50,true,\n",
    )
    meta = _load_column_meta(tmp_path)
    assert meta["5-hmdC_RT"]["istd_pair"] == "d3-5-hmdC"
    assert meta["d3-5-hmdC_RT"]["istd_pair"] == ""


def test_load_column_meta_backward_compat(tmp_path):
    """targets.csv without is_istd/istd_pair columns reads without error."""
    (tmp_path / "targets.csv").write_text(
        "label,mz,rt_min,rt_max,ppm_tol,neutral_loss_da,nl_ppm_warn,nl_ppm_max\n"
        "5-hmdC,258.1085,8,10,20,116.0474,20,50\n",
        encoding="utf-8-sig",
    )
    meta = _load_column_meta(tmp_path)
    assert meta["5-hmdC_RT"]["is_istd"] is False
    assert meta["5-hmdC_RT"]["istd_pair"] == ""


def _rt_delta_pct(rt_analyte: float, rt_istd: float) -> float:
    return abs(rt_analyte - rt_istd) / rt_istd * 100


def test_rt_delta_pct_exact():
    assert abs(_rt_delta_pct(9.0, 9.1) - (0.1 / 9.1 * 100)) < 1e-9


def test_rt_delta_mean_sd():
    deltas = [_rt_delta_pct(9.0, 9.1), _rt_delta_pct(9.2, 9.1)]
    mean = sum(deltas) / len(deltas)
    sd = statistics.stdev(deltas)
    assert abs(mean - (0.1 / 9.1 * 100)) < 0.01
    assert sd >= 0


def test_build_data_sheet_uses_deep_orange_for_istd_nd(tmp_path):
    _write_targets(
        tmp_path,
        "5-hmdC,258.1085,8,10,20,116.0474,20,50,false,d3-5-hmdC\n"
        "d3-5-hmdC,261.1273,8,10,20,116.0474,20,50,true,\n",
    )
    col_meta = _load_column_meta(tmp_path)
    wb = Workbook()
    ws = wb.active
    rows = [
        {
            "SampleName": "Tumor_1",
            "5-hmdC_RT": "ND",
            "5-hmdC_Int": "ND",
            "5-hmdC_NL": "ND",
            "d3-5-hmdC_RT": "ND",
            "d3-5-hmdC_Int": "ND",
            "d3-5-hmdC_NL": "ND",
        }
    ]
    csv_keys = list(rows[0].keys())

    _build_data_sheet(ws, rows, col_meta, csv_keys)

    assert ws["B2"].fill.fgColor.rgb.endswith("FFE0B2")
    assert ws["E2"].fill.fgColor.rgb.endswith("FF7043")


def test_build_summary_sheet_adds_rt_delta_metric(tmp_path):
    _write_targets(
        tmp_path,
        "5-hmdC,258.1085,8,10,20,116.0474,20,50,false,d3-5-hmdC\n"
        "d3-5-hmdC,261.1273,8,10,20,116.0474,20,50,true,\n",
    )
    col_meta = _load_column_meta(tmp_path)
    wb = Workbook()
    ws = wb.active
    rows = [
        {
            "SampleName": "Tumor_1",
            "5-hmdC_RT": "9.0",
            "5-hmdC_Int": "1000",
            "5-hmdC_NL": "OK",
            "d3-5-hmdC_RT": "9.1",
            "d3-5-hmdC_Int": "2000",
            "d3-5-hmdC_NL": "OK",
        },
        {
            "SampleName": "Normal_1",
            "5-hmdC_RT": "9.2",
            "5-hmdC_Int": "1100",
            "5-hmdC_NL": "WARN_5ppm",
            "d3-5-hmdC_RT": "9.1",
            "d3-5-hmdC_Int": "2100",
            "d3-5-hmdC_NL": "WARN_3ppm",
        },
    ]
    csv_keys = list(rows[0].keys())

    _build_summary_sheet(ws, rows, col_meta, csv_keys)

    metric_row = next(
        row_idx
        for row_idx in range(2, ws.max_row + 1)
        if ws.cell(row=row_idx, column=1).value == "RT Δ vs ISTD (%)"
    )
    assert ws.cell(row=metric_row, column=2).value == "1.10±0.00% (n=2)"
    assert ws.cell(row=metric_row, column=3).value == "—"


def test_run_prints_istd_nd_warning(tmp_path, capsys):
    config_dir = tmp_path / "config"
    output_dir = tmp_path / "output"
    config_dir.mkdir()
    output_dir.mkdir()
    _write_targets(
        config_dir,
        "5-hmdC,258.1085,8,10,20,116.0474,20,50,false,d3-5-hmdC\n"
        "d3-5-hmdC,261.1273,8,10,20,116.0474,20,50,true,\n",
    )
    (output_dir / "xic_results.csv").write_text(
        "SampleName,5-hmdC_RT,5-hmdC_Int,5-hmdC_NL,d3-5-hmdC_RT,d3-5-hmdC_Int,d3-5-hmdC_NL\n"
        "Tumor_1,9.0,1000,OK,9.1,2000,OK\n"
        "Tumor_2,9.2,1100,OK,ND,ND,ND\n",
        encoding="utf-8-sig",
    )

    run(tmp_path)

    stdout = capsys.readouterr().out
    assert "ISTD_ND: d3-5-hmdC 1/2" in stdout
