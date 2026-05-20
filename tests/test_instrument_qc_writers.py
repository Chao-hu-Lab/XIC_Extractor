import csv
import json
from pathlib import Path

from xic_extractor.instrument_qc.models import (
    InstrumentQCDiagnostic,
    SDOLEKTrendRow,
)
from xic_extractor.instrument_qc.writers import (
    TREND_TSV_COLUMNS,
    write_diagnostics_tsv,
    write_sdolek_json,
    write_trend_tsv,
)


def _row(raw_path: Path) -> SDOLEKTrendRow:
    return SDOLEKTrendRow(
        sample_name="SDOLEK-pretest",
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


def test_write_trend_tsv_uses_contract_columns(tmp_path: Path) -> None:
    path = tmp_path / "trend.tsv"
    write_trend_tsv(path, [_row(tmp_path / "a.raw")])

    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        rows = list(reader)

    assert reader.fieldnames == TREND_TSV_COLUMNS
    assert rows[0]["compound"] == "SDO"
    assert rows[0]["identity_evidence"] == "MS1_ONLY"


def test_write_diagnostics_tsv_uses_contract_columns(tmp_path: Path) -> None:
    path = tmp_path / "diagnostics.tsv"
    write_diagnostics_tsv(
        path,
        [
            InstrumentQCDiagnostic(
                sample_name="S1",
                raw_path=tmp_path / "S1.raw",
                issue="INJECTION_ORDER_MISSING",
                detail="No injection-order file supplied.",
            )
        ],
    )

    text = path.read_text(encoding="utf-8")
    assert text.splitlines()[0] == "sample_name\traw_path\tissue\tdetail"


def test_write_sdolek_json_contains_summary_and_rows(tmp_path: Path) -> None:
    path = tmp_path / "trend.json"
    write_sdolek_json(
        path,
        [_row(tmp_path / "a.raw")],
        [
            InstrumentQCDiagnostic(
                sample_name="S1",
                raw_path=tmp_path / "S1.raw",
                issue="INJECTION_ORDER_MISSING",
                detail="No injection-order file supplied.",
            )
        ],
    )

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["summary"]["total_rows"] == 1
    assert payload["summary"]["status_counts"] == {"detected": 1}
    assert payload["rows"][0]["compound"] == "SDO"
