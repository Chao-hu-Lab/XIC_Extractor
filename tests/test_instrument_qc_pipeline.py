import csv
import json
from pathlib import Path

import numpy as np

from xic_extractor.instrument_qc.pipeline import DEFAULT_DLL_DIR, run_sdolek_pipeline


class FakeRaw:
    def __init__(self, traces: dict[float, tuple[np.ndarray, np.ndarray]]) -> None:
        self.traces = traces
        self.requests: list[tuple[float, float, float, float]] = []

    def __enter__(self) -> "FakeRaw":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def extract_xic(
        self,
        mz: float,
        rt_min: float,
        rt_max: float,
        ppm_tol: float,
    ) -> tuple[np.ndarray, np.ndarray]:
        self.requests.append((mz, rt_min, rt_max, ppm_tol))
        return self.traces[mz]


def _write_raw(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("", encoding="utf-8")


def _trace(apex_rt: float) -> tuple[np.ndarray, np.ndarray]:
    rt = np.array([apex_rt - 0.2, apex_rt, apex_rt + 0.2])
    intensity = np.array([0.0, 1000.0, 0.0])
    return rt, intensity


def test_sdolek_pipeline_extracts_two_compounds_and_writes_outputs(
    tmp_path: Path,
) -> None:
    raw_root = tmp_path / "raw"
    raw_path = raw_root / "SDOLEK" / "SDO LEK - 1.raw"
    _write_raw(raw_path)
    output_dir = tmp_path / "out"
    injection_order = tmp_path / "order.csv"
    injection_order.write_text(
        "Sample_Name,Injection_Order\nSDO LEK - 1,4\n",
        encoding="utf-8",
    )

    fake_raw = FakeRaw(
        {
            311.0814: _trace(6.26),
            556.2771: _trace(6.40),
        }
    )

    output = run_sdolek_pipeline(
        raw_dir=raw_root,
        output_dir=output_dir,
        injection_order_source=injection_order,
        raw_opener=lambda _path: fake_raw,
    )

    assert len(output.trend_rows) == 2
    assert {row.compound for row in output.trend_rows} == {"SDO", "LEK"}
    assert {row.injection_order for row in output.trend_rows} == {4}
    assert all(row.identity_evidence == "MS1_ONLY" for row in output.trend_rows)
    assert output.trend_tsv.exists()
    assert output.trend_json.exists()
    assert output.diagnostics_tsv.exists()
    assert output.workbook.exists()
    payload = json.loads(output.trend_json.read_text(encoding="utf-8"))
    assert payload["metadata_source_status"]["injection_order_status"] == "provided"


def test_sdolek_pipeline_reports_missing_injection_order_without_failing(
    tmp_path: Path,
) -> None:
    raw_root = tmp_path / "raw"
    raw_path = raw_root / "SDOLEK" / "SDOLEK-pretest.raw"
    _write_raw(raw_path)

    output = run_sdolek_pipeline(
        raw_dir=raw_root,
        output_dir=tmp_path / "out",
        raw_opener=lambda _path: FakeRaw(
            {
                311.0814: _trace(6.26),
                556.2771: _trace(6.40),
            }
        ),
    )

    assert all(row.injection_order is None for row in output.trend_rows)
    assert any(diag.issue == "INJECTION_ORDER_MISSING" for diag in output.diagnostics)
    payload = json.loads(output.trend_json.read_text(encoding="utf-8"))
    assert payload["metadata_source_status"] == {
        "injection_order_source": "",
        "injection_order_status": "missing",
    }


def test_sdolek_pipeline_ignores_biological_root_raws(tmp_path: Path) -> None:
    raw_root = tmp_path / "raw"
    _write_raw(raw_root / "TumorBC2257_DNA.raw")
    _write_raw(raw_root / "SDOLEK" / "SDO-posttest.raw")

    output = run_sdolek_pipeline(
        raw_dir=raw_root,
        output_dir=tmp_path / "out",
        raw_opener=lambda _path: FakeRaw(
            {
                311.0814: _trace(6.26),
                556.2771: _trace(6.40),
            }
        ),
    )

    assert {row.sample_name for row in output.trend_rows} == {"SDO-posttest"}


def test_sdolek_pipeline_uses_xcalibur_default_dll_dir(
    tmp_path: Path,
    monkeypatch,
) -> None:
    raw_root = tmp_path / "raw"
    _write_raw(raw_root / "SDOLEK" / "SDO-posttest.raw")
    calls: dict[str, Path] = {}

    def fake_open_raw(raw_path: Path, dll_dir: Path) -> FakeRaw:
        calls["raw_path"] = raw_path
        calls["dll_dir"] = dll_dir
        return FakeRaw(
            {
                311.0814: _trace(6.26),
                556.2771: _trace(6.40),
            }
        )

    monkeypatch.setattr("xic_extractor.instrument_qc.pipeline.open_raw", fake_open_raw)

    output = run_sdolek_pipeline(
        raw_dir=raw_root,
        output_dir=tmp_path / "out",
    )

    assert len(output.trend_rows) == 2
    assert calls["dll_dir"] == DEFAULT_DLL_DIR


def test_sdolek_pipeline_fails_clearly_when_sdolek_folder_missing(
    tmp_path: Path,
) -> None:
    raw_root = tmp_path / "raw"
    raw_root.mkdir()

    try:
        run_sdolek_pipeline(
            raw_dir=raw_root,
            output_dir=tmp_path / "out",
            raw_opener=lambda _path: FakeRaw({}),
        )
    except FileNotFoundError as exc:
        assert "SDOLEK" in str(exc)
    else:
        raise AssertionError("Expected missing SDOLEK folder to fail clearly")


def test_pipeline_can_emit_mixstds_outputs_from_explicit_registry(
    tmp_path: Path,
) -> None:
    raw_root = tmp_path / "raw"
    _write_raw(raw_root / "SDOLEK" / "SDOLEK-pretest.raw")
    _write_raw(raw_root / "STDs" / "Mix_STDs_01.raw")
    registry = tmp_path / "mixstds.csv"
    registry.write_text(
        "compound,precursor_mz,rt_min,rt_max,ppm_tol\n"
        "STD-A,123.4567,1.0,2.0,10\n",
        encoding="utf-8",
    )

    output = run_sdolek_pipeline(
        raw_dir=raw_root,
        output_dir=tmp_path / "out",
        raw_opener=lambda _path: FakeRaw(
            {
                311.0814: _trace(6.26),
                556.2771: _trace(6.40),
                123.4567: _trace(1.50),
            }
        ),
        emit_mixstds=True,
        mixstds_target_registry=registry,
    )

    assert output.mixstds_trend_tsv is not None
    assert output.mixstds_trend_json is not None
    assert output.mixstds_diagnostics_tsv is not None
    with output.mixstds_trend_tsv.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    assert rows[0]["sample_name"] == "Mix_STDs_01"
    assert rows[0]["compound"] == "STD-A"
    assert rows[0]["identity_evidence"] == "MS1_ONLY"


def test_pipeline_reports_mixstds_missing_registry_without_extraction(
    tmp_path: Path,
) -> None:
    raw_root = tmp_path / "raw"
    _write_raw(raw_root / "SDOLEK" / "SDOLEK-pretest.raw")
    _write_raw(raw_root / "STDs" / "Mix_STDs_01.raw")

    output = run_sdolek_pipeline(
        raw_dir=raw_root,
        output_dir=tmp_path / "out",
        raw_opener=lambda _path: FakeRaw(
            {
                311.0814: _trace(6.26),
                556.2771: _trace(6.40),
            }
        ),
        emit_mixstds=True,
    )

    assert output.mixstds_trend_tsv is not None
    assert output.mixstds_trend_tsv.exists()
    assert any(
        diag.issue == "MIXSTDS_TARGET_REGISTRY_MISSING"
        for diag in output.diagnostics
    )
