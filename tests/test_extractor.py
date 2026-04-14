import csv
from pathlib import Path

import numpy as np
import pytest

from xic_extractor.config import ExtractionConfig, Target
from xic_extractor.neutral_loss import NLResult
from xic_extractor.raw_reader import RawReaderError
from xic_extractor.signal_processing import PeakDetectionResult, PeakResult


@pytest.fixture(autouse=True)
def _disable_reader_preflight(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "xic_extractor.extractor.preflight_raw_reader",
        lambda _dll_dir: [],
        raising=False,
    )


def test_run_raises_before_processing_when_reader_preflight_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = _config(tmp_path)
    (config.data_dir / "SampleA.raw").write_text("", encoding="utf-8")
    monkeypatch.setattr(
        "xic_extractor.extractor.preflight_raw_reader",
        lambda _dll_dir: ["pythonnet is not installed"],
        raising=False,
    )
    monkeypatch.setattr(
        "xic_extractor.extractor.open_raw",
        lambda *_args: pytest.fail(
            "open_raw should not be called after preflight failure"
        ),
    )

    with pytest.raises(RawReaderError, match="pythonnet is not installed"):
        _run(config, [_target("Analyte")])

    assert not config.output_csv.exists()
    assert not config.diagnostics_csv.exists()


def test_run_writes_success_rows_with_area_columns_and_optional_nl(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = _config(tmp_path)
    (config.data_dir / "SampleA.raw").write_text("", encoding="utf-8")
    targets = [_target("NoNL", neutral_loss_da=None), _target("WithNL")]
    monkeypatch.setattr("xic_extractor.extractor.open_raw", _open_raw_factory())
    monkeypatch.setattr(
        "xic_extractor.extractor.find_peak_and_area",
        _peak_sequence(
            [_ok_peak(8.5, 1200.0, 3400.25), _ok_peak(9.5, 2200.0, 4400.75)]
        ),
    )
    monkeypatch.setattr(
        "xic_extractor.extractor.check_nl",
        _nl_sequence([NLResult("WARN", 12.34, 3, 0, 2)]),
    )

    output = _run(config, targets, progress_callback=lambda *_args: None)

    rows = _read_csv(config.output_csv)
    assert list(rows[0].keys()) == [
        "SampleName",
        "NoNL_RT",
        "NoNL_Int",
        "NoNL_Area",
        "NoNL_PeakStart",
        "NoNL_PeakEnd",
        "NoNL_PeakWidthSec",
        "WithNL_RT",
        "WithNL_Int",
        "WithNL_Area",
        "WithNL_PeakStart",
        "WithNL_PeakEnd",
        "WithNL_PeakWidthSec",
        "WithNL_NL",
    ]
    assert rows == [
        {
            "SampleName": "SampleA",
            "NoNL_RT": "8.5000",
            "NoNL_Int": "1200",
            "NoNL_Area": "3400.25",
            "NoNL_PeakStart": "8.0000",
            "NoNL_PeakEnd": "9.0000",
            "NoNL_PeakWidthSec": "60.00",
            "WithNL_RT": "9.5000",
            "WithNL_Int": "2200",
            "WithNL_Area": "4400.75",
            "WithNL_PeakStart": "9.0000",
            "WithNL_PeakEnd": "10.0000",
            "WithNL_PeakWidthSec": "60.00",
            "WithNL_NL": "WARN_12.3ppm",
        }
    ]
    assert _read_csv(config.diagnostics_csv) == []
    assert len(output.file_results) == 1
    assert output.diagnostics == []
    assert _read_csv(config.output_csv.with_name("xic_results_long.csv")) == [
        {
            "SampleName": "SampleA",
            "Group": "QC",
            "Target": "NoNL",
            "Role": "Analyte",
            "ISTD Pair": "",
            "RT": "8.5000",
            "Area": "3400.25",
            "NL": "",
            "Int": "1200",
            "PeakStart": "8.0000",
            "PeakEnd": "9.0000",
            "PeakWidthSec": "60.00",
        },
        {
            "SampleName": "SampleA",
            "Group": "QC",
            "Target": "WithNL",
            "Role": "Analyte",
            "ISTD Pair": "",
            "RT": "9.5000",
            "Area": "4400.75",
            "NL": "WARN_12.3ppm",
            "Int": "2200",
            "PeakStart": "9.0000",
            "PeakEnd": "10.0000",
            "PeakWidthSec": "60.00",
        },
    ]


def test_run_writes_nd_for_peak_failure_but_keeps_nl_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = _config(tmp_path)
    (config.data_dir / "SampleA.raw").write_text("", encoding="utf-8")
    targets = [_target("WithNL")]
    monkeypatch.setattr("xic_extractor.extractor.open_raw", _open_raw_factory())
    monkeypatch.setattr(
        "xic_extractor.extractor.find_peak_and_area",
        _peak_sequence(
            [_failed_peak("PEAK_NOT_FOUND", n_points=15, max_smoothed=1234.0)]
        ),
    )
    monkeypatch.setattr(
        "xic_extractor.extractor.check_nl",
        _nl_sequence([NLResult("OK", 1.2, 3, 0, 2)]),
    )

    _run(config, targets)

    rows = _read_csv(config.output_csv)
    assert rows[0]["WithNL_RT"] == "ND"
    assert rows[0]["WithNL_Int"] == "ND"
    assert rows[0]["WithNL_Area"] == "ND"
    assert rows[0]["WithNL_PeakStart"] == "ND"
    assert rows[0]["WithNL_PeakEnd"] == "ND"
    assert rows[0]["WithNL_PeakWidthSec"] == "ND"
    assert rows[0]["WithNL_NL"] == "OK"
    diagnostics = _read_csv(config.diagnostics_csv)
    assert diagnostics[0]["Issue"] == "PEAK_NOT_FOUND"
    assert diagnostics[0]["Target"] == "WithNL"
    assert "prominence" in diagnostics[0]["Reason"]
    assert "max=1234" in diagnostics[0]["Reason"]


def test_run_writes_file_error_row_and_continues(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = _config(tmp_path)
    (config.data_dir / "Bad.raw").write_text("", encoding="utf-8")
    (config.data_dir / "Good.raw").write_text("", encoding="utf-8")
    targets = [_target("NoNL", neutral_loss_da=None), _target("WithNL")]
    monkeypatch.setattr(
        "xic_extractor.extractor.open_raw",
        _open_raw_factory(errors={"Bad.raw": RuntimeError("file locked")}),
    )
    monkeypatch.setattr(
        "xic_extractor.extractor.find_peak_and_area",
        _peak_sequence([_ok_peak(8.5, 1000.0, 2000.0), _ok_peak(9.5, 1100.0, 2100.0)]),
    )
    monkeypatch.setattr(
        "xic_extractor.extractor.check_nl",
        _nl_sequence([NLResult("OK", 1.0, 2, 0, 1)]),
    )

    output = _run(config, targets)

    rows = _read_csv(config.output_csv)
    assert rows[0] == {
        "SampleName": "Bad",
        "NoNL_RT": "ERROR",
        "NoNL_Int": "ERROR",
        "NoNL_Area": "ERROR",
        "NoNL_PeakStart": "ERROR",
        "NoNL_PeakEnd": "ERROR",
        "NoNL_PeakWidthSec": "ERROR",
        "WithNL_RT": "ERROR",
        "WithNL_Int": "ERROR",
        "WithNL_Area": "ERROR",
        "WithNL_PeakStart": "ERROR",
        "WithNL_PeakEnd": "ERROR",
        "WithNL_PeakWidthSec": "ERROR",
        "WithNL_NL": "ERROR",
    }
    assert rows[1]["SampleName"] == "Good"
    diagnostics = _read_csv(config.diagnostics_csv)
    assert diagnostics[0]["SampleName"] == "Bad"
    assert diagnostics[0]["Target"] == ""
    assert diagnostics[0]["Issue"] == "FILE_ERROR"
    assert "file locked" in diagnostics[0]["Reason"]
    assert output.file_results[0].error is not None


@pytest.mark.parametrize(
    ("peak_status", "n_points", "max_smoothed", "issue", "reason_part"),
    [
        ("NO_SIGNAL", 0, None, "NO_SIGNAL", "XIC empty"),
        ("WINDOW_TOO_SHORT", 7, None, "WINDOW_TOO_SHORT", "Only 7 scans"),
        ("PEAK_NOT_FOUND", 15, 25.0, "PEAK_NOT_FOUND", "prominence"),
    ],
)
def test_run_writes_peak_diagnostics(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    peak_status: str,
    n_points: int,
    max_smoothed: float | None,
    issue: str,
    reason_part: str,
) -> None:
    config = _config(tmp_path)
    (config.data_dir / "SampleA.raw").write_text("", encoding="utf-8")
    targets = [_target("NoNL", neutral_loss_da=None)]
    monkeypatch.setattr("xic_extractor.extractor.open_raw", _open_raw_factory())
    monkeypatch.setattr(
        "xic_extractor.extractor.find_peak_and_area",
        _peak_sequence(
            [
                _failed_peak(
                    peak_status,
                    n_points=n_points,
                    max_smoothed=max_smoothed,
                )
            ]
        ),
    )

    _run(config, targets)

    diagnostics = _read_csv(config.diagnostics_csv)
    assert diagnostics[0]["Issue"] == issue
    assert diagnostics[0]["Target"] == "NoNL"
    assert reason_part in diagnostics[0]["Reason"]


@pytest.mark.parametrize(
    ("nl_result", "issue", "reason_part"),
    [
        (NLResult("NL_FAIL", 78.4, 10, 1, 3), "NL_FAIL", "best NL product 78.4 ppm"),
        (NLResult("NL_FAIL", None, 10, 1, 3), "NL_FAIL", "no product within"),
        (NLResult("NO_MS2", None, 42, 2, 0), "NO_MS2", "42 valid MS2 scans"),
    ],
)
def test_run_writes_neutral_loss_diagnostics(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    nl_result: NLResult,
    issue: str,
    reason_part: str,
) -> None:
    config = _config(tmp_path)
    (config.data_dir / "SampleA.raw").write_text("", encoding="utf-8")
    targets = [_target("WithNL")]
    monkeypatch.setattr("xic_extractor.extractor.open_raw", _open_raw_factory())
    monkeypatch.setattr(
        "xic_extractor.extractor.find_peak_and_area",
        _peak_sequence([_ok_peak(8.5, 1000.0, 2000.0)]),
    )
    monkeypatch.setattr("xic_extractor.extractor.check_nl", _nl_sequence([nl_result]))

    _run(config, targets)

    rows = _read_csv(config.output_csv)
    assert rows[0]["WithNL_NL"] == nl_result.to_token()
    diagnostics = _read_csv(config.diagnostics_csv)
    assert diagnostics[0]["Issue"] == issue
    assert diagnostics[0]["Target"] == "WithNL"
    assert reason_part in diagnostics[0]["Reason"]


def test_run_reports_progress_and_stops_between_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = _config(tmp_path)
    (config.data_dir / "A.raw").write_text("", encoding="utf-8")
    (config.data_dir / "B.raw").write_text("", encoding="utf-8")
    targets = [_target("NoNL", neutral_loss_da=None)]
    progress_calls: list[tuple[int, int, str]] = []
    monkeypatch.setattr("xic_extractor.extractor.open_raw", _open_raw_factory())
    monkeypatch.setattr(
        "xic_extractor.extractor.find_peak_and_area",
        _peak_sequence([_ok_peak(8.5, 1000.0, 2000.0)]),
    )

    output = _run(
        config,
        targets,
        progress_callback=lambda current, total, filename: progress_calls.append(
            (current, total, filename)
        ),
        should_stop=lambda: bool(progress_calls),
    )

    assert progress_calls == [(1, 2, "A.raw")]
    assert [file_result.sample_name for file_result in output.file_results] == ["A"]
    assert [row["SampleName"] for row in _read_csv(config.output_csv)] == ["A"]


def _run(config: ExtractionConfig, targets: list[Target], **kwargs):
    from xic_extractor.extractor import run

    return run(config, targets, **kwargs)


def _config(tmp_path: Path) -> ExtractionConfig:
    data_dir = tmp_path / "raw"
    output_dir = tmp_path / "output"
    dll_dir = tmp_path / "dll"
    data_dir.mkdir()
    output_dir.mkdir()
    dll_dir.mkdir()
    return ExtractionConfig(
        data_dir=data_dir,
        dll_dir=dll_dir,
        output_csv=output_dir / "xic_results.csv",
        diagnostics_csv=output_dir / "xic_diagnostics.csv",
        smooth_window=15,
        smooth_polyorder=3,
        peak_rel_height=0.95,
        peak_min_prominence_ratio=0.10,
        ms2_precursor_tol_da=0.5,
        nl_min_intensity_ratio=0.01,
    )


def _target(label: str, *, neutral_loss_da: float | None = 116.0474) -> Target:
    return Target(
        label=label,
        mz=258.1085,
        rt_min=8.0,
        rt_max=10.0,
        ppm_tol=20.0,
        neutral_loss_da=neutral_loss_da,
        nl_ppm_warn=20.0 if neutral_loss_da is not None else None,
        nl_ppm_max=50.0 if neutral_loss_da is not None else None,
        is_istd=False,
        istd_pair="",
    )


def _ok_peak(rt: float, intensity: float, area: float) -> PeakDetectionResult:
    return PeakDetectionResult(
        status="OK",
        peak=PeakResult(
            rt=rt,
            intensity=intensity,
            intensity_smoothed=intensity,
            area=area,
            peak_start=rt - 0.5,
            peak_end=rt + 0.5,
        ),
        n_points=15,
        max_smoothed=intensity,
        n_prominent_peaks=1,
    )


def _failed_peak(
    status: str, *, n_points: int, max_smoothed: float | None
) -> PeakDetectionResult:
    return PeakDetectionResult(
        status=status,
        peak=None,
        n_points=n_points,
        max_smoothed=max_smoothed,
        n_prominent_peaks=0,
    )


def _peak_sequence(results: list[PeakDetectionResult]):
    pending = list(results)

    def _fake_find_peak_and_area(
        rt: np.ndarray, intensity: np.ndarray, config: ExtractionConfig
    ) -> PeakDetectionResult:
        return pending.pop(0)

    return _fake_find_peak_and_area


def _nl_sequence(results: list[NLResult]):
    pending = list(results)

    def _fake_check_nl(*_args, **_kwargs) -> NLResult:
        return pending.pop(0)

    return _fake_check_nl


def _open_raw_factory(*, errors: dict[str, Exception] | None = None):
    error_by_name = errors or {}

    def _fake_open_raw(path: Path, dll_dir: Path):
        if path.name in error_by_name:
            raise error_by_name[path.name]
        return _FakeRaw()

    return _fake_open_raw


class _FakeRaw:
    def __enter__(self):
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def extract_xic(
        self, mz: float, rt_min: float, rt_max: float, ppm_tol: float
    ) -> tuple[np.ndarray, np.ndarray]:
        return np.asarray([rt_min, rt_max], dtype=float), np.asarray(
            [1.0, 2.0], dtype=float
        )


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))
