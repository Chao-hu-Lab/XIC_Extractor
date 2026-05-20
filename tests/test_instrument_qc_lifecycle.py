import csv
from pathlib import Path

import pytest

from xic_extractor.instrument_qc.lifecycle import (
    DuplicateLifecycleRunError,
    append_lifecycle_dataset,
)
from xic_extractor.instrument_qc.models import InstrumentQCRunOutput, SDOLEKTrendRow


def _write_artifacts(output_dir: Path) -> InstrumentQCRunOutput:
    output_dir.mkdir(parents=True, exist_ok=True)
    trend_tsv = output_dir / "instrument_qc_sdolek_trend.tsv"
    trend_json = output_dir / "instrument_qc_sdolek_trend.json"
    diagnostics_tsv = output_dir / "instrument_qc_sdolek_diagnostics.tsv"
    workbook = output_dir / "instrument_qc_trend_sdolek.xlsx"
    for path in (trend_tsv, trend_json, diagnostics_tsv, workbook):
        path.write_text(path.name, encoding="utf-8")
    return InstrumentQCRunOutput(
        trend_rows=(_row(output_dir / "SDOLEK.raw", sample_name="SDOLEK"),),
        diagnostics=(),
        trend_tsv=trend_tsv,
        trend_json=trend_json,
        diagnostics_tsv=diagnostics_tsv,
        workbook=workbook,
        mixstds_rows=(_row(output_dir / "Mix_STDs.raw", sample_name="Mix_STDs"),),
    )


def test_append_lifecycle_dataset_writes_run_and_row_files(tmp_path: Path) -> None:
    output = _write_artifacts(tmp_path / "out")

    result = append_lifecycle_dataset(
        output=output,
        raw_dir=tmp_path / "raw",
        output_dir=tmp_path / "out",
        lifecycle_root=tmp_path / "life",
        instrument_id="Orbitrap-1",
        method_doc=tmp_path / "method.docx",
        code_version="abc123",
        timestamp_utc="2026-05-20T00:00:00Z",
    )

    assert result.runs_tsv.exists()
    assert result.sdolek_tsv.exists()
    assert result.mixstds_tsv.exists()
    assert result.blank_tsv.exists()
    with result.runs_tsv.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    assert rows[0]["instrument_id"] == "Orbitrap-1"
    assert rows[0]["code_version"] == "abc123"
    assert rows[0]["run_fingerprint"] == result.run_fingerprint


def test_append_lifecycle_dataset_blocks_duplicate_by_default(
    tmp_path: Path,
) -> None:
    output = _write_artifacts(tmp_path / "out")
    kwargs = {
        "output": output,
        "raw_dir": tmp_path / "raw",
        "output_dir": tmp_path / "out",
        "lifecycle_root": tmp_path / "life",
        "instrument_id": "Orbitrap-1",
        "method_doc": tmp_path / "method.docx",
        "code_version": "abc123",
        "timestamp_utc": "2026-05-20T00:00:00Z",
    }
    append_lifecycle_dataset(**kwargs)

    with pytest.raises(DuplicateLifecycleRunError):
        append_lifecycle_dataset(**kwargs)


def test_append_lifecycle_dataset_can_explicitly_allow_duplicate(
    tmp_path: Path,
) -> None:
    output = _write_artifacts(tmp_path / "out")
    kwargs = {
        "output": output,
        "raw_dir": tmp_path / "raw",
        "output_dir": tmp_path / "out",
        "lifecycle_root": tmp_path / "life",
        "instrument_id": "Orbitrap-1",
        "method_doc": tmp_path / "method.docx",
        "code_version": "abc123",
        "timestamp_utc": "2026-05-20T00:00:00Z",
    }
    append_lifecycle_dataset(**kwargs)
    append_lifecycle_dataset(**kwargs, allow_duplicate=True)

    with (tmp_path / "life" / "instrument_qc_lifecycle_runs.tsv").open(
        encoding="utf-8",
        newline="",
    ) as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    assert len(rows) == 2


def _row(raw_path: Path, *, sample_name: str) -> SDOLEKTrendRow:
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
