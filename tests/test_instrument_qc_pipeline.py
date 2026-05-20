from pathlib import Path

import numpy as np

from xic_extractor.instrument_qc.pipeline import run_sdolek_pipeline


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
