import pickle
from pathlib import Path

import numpy as np
import pytest

from xic_extractor.config import ExtractionConfig, Target
from xic_extractor.extractor import RunOutput
from xic_extractor.rt_prior_library import LibraryEntry
from xic_extractor.signal_processing import (
    PeakCandidate,
    PeakDetectionResult,
    PeakResult,
)


@pytest.fixture(autouse=True)
def _disable_reader_preflight(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "xic_extractor.extraction.pipeline.preflight_raw_reader",
        lambda _dll_dir: [],
        raising=False,
    )


def test_run_uses_serial_backend_by_default(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from xic_extractor import extractor
    from xic_extractor.extraction import serial_backend

    config = _config(tmp_path, keep_intermediate_csv=False)
    (config.data_dir / "B.raw").write_text("", encoding="utf-8")
    (config.data_dir / "A.raw").write_text("", encoding="utf-8")
    targets = [_target("Analyte")]
    returned = RunOutput(file_results=[], diagnostics=[])
    calls: list[tuple[ExtractionConfig, list[Target], list[str]]] = []

    def _fake_run_serial(
        config_arg: ExtractionConfig,
        targets_arg: list[Target],
        *,
        raw_paths: list[Path],
        progress_callback=None,
        should_stop=None,
        injection_order=None,
        rt_prior_library=None,
    ) -> RunOutput:
        calls.append((config_arg, targets_arg, [path.name for path in raw_paths]))
        assert progress_callback is _progress
        assert should_stop is _should_stop
        assert injection_order == {"SampleA": 1}
        assert rt_prior_library == {}
        return returned

    def _progress(_current: int, _total: int, _filename: str) -> None:
        raise AssertionError("fake serial backend should receive but not call callback")

    def _should_stop() -> bool:
        return False

    monkeypatch.setattr(serial_backend, "run_serial", _fake_run_serial)

    output = extractor.run(
        config,
        targets,
        progress_callback=_progress,
        should_stop=_should_stop,
        injection_order={"SampleA": 1},
        rt_prior_library={},
    )

    assert output is returned
    assert calls == [(config, targets, ["A.raw", "B.raw"])]


def test_run_resolves_scoring_inputs_before_backend(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from xic_extractor import extractor
    from xic_extractor.extraction import serial_backend

    config = _config(tmp_path, keep_intermediate_csv=False)
    config = ExtractionConfig(
        **{
            **config.__dict__,
            "injection_order_source": tmp_path / "sample_info.csv",
            "rt_prior_library_path": tmp_path / "rt_prior_library.csv",
            "config_hash": "abcd1234",
        }
    )
    (config.data_dir / "SampleA.raw").write_text("", encoding="utf-8")
    targets = [_target("Analyte")]
    library = {
        ("Analyte", "Analyte"): LibraryEntry(
            config_hash="abcd1234",
            target_label="Analyte",
            role="Analyte",
            istd_pair="",
            median_delta_rt=None,
            sigma_delta_rt=None,
            median_abs_rt=8.5,
            sigma_abs_rt=0.1,
            n_samples=3,
            updated_at="2026-05-07",
        )
    }

    monkeypatch.setattr(
        "xic_extractor.extraction.pipeline.read_injection_order",
        lambda path: {"SampleA": 1},
    )
    monkeypatch.setattr(
        "xic_extractor.extraction.pipeline.load_library",
        lambda path, config_hash: library,
    )

    def _fake_run_serial(
        config_arg: ExtractionConfig,
        targets_arg: list[Target],
        *,
        raw_paths: list[Path],
        progress_callback=None,
        should_stop=None,
        injection_order=None,
        rt_prior_library=None,
    ) -> RunOutput:
        assert config_arg is config
        assert targets_arg is targets
        assert [path.name for path in raw_paths] == ["SampleA.raw"]
        assert injection_order == {"SampleA": 1}
        assert rt_prior_library == library
        return RunOutput(file_results=[], diagnostics=[])

    monkeypatch.setattr(serial_backend, "run_serial", _fake_run_serial)

    output = extractor.run(config, targets)

    assert output.file_results == []


def test_resolve_injection_order_returns_empty_dict_without_raw_files(
    tmp_path: Path,
) -> None:
    from xic_extractor.extraction.pipeline import resolve_injection_order

    config = _config(tmp_path, keep_intermediate_csv=False)

    assert resolve_injection_order(config, [], None) == {}


def test_serial_backend_keeps_sorted_raw_output_order(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from xic_extractor.extractor import run

    config = _config(tmp_path, keep_intermediate_csv=False)
    (config.data_dir / "B.raw").write_text("", encoding="utf-8")
    (config.data_dir / "A.raw").write_text("", encoding="utf-8")
    targets = [_target("Analyte")]
    monkeypatch.setattr("xic_extractor.extractor.open_raw", _open_raw_factory())
    monkeypatch.setattr(
        "xic_extractor.extractor.find_peak_and_area",
        _peak_sequence([_ok_peak(8.5, 1000.0, 2000.0), _ok_peak(8.6, 1100.0, 2100.0)]),
    )

    output = run(config, targets)

    assert [file_result.sample_name for file_result in output.file_results] == [
        "A",
        "B",
    ]


def test_per_file_result_primitive_returns_worker_payload_and_is_pickleable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from xic_extractor.extraction.target_extraction import extract_raw_file_result

    config = _config(tmp_path, keep_intermediate_csv=False)
    raw_path = config.data_dir / "SampleA.raw"
    raw_path.write_text("", encoding="utf-8")
    targets = [_target("Analyte")]
    monkeypatch.setattr("xic_extractor.extractor.open_raw", _open_raw_factory())
    monkeypatch.setattr(
        "xic_extractor.extractor.find_peak_and_area",
        _peak_sequence([_ok_peak(8.5, 1000.0, 2000.0)]),
    )

    result = extract_raw_file_result(
        7,
        config,
        targets,
        raw_path,
        scoring_context_factory=None,
    )

    restored = pickle.loads(pickle.dumps(result))
    assert restored.raw_index == 7
    assert restored.sample_name == "SampleA"
    assert restored.file_result.sample_name == "SampleA"
    assert restored.diagnostics == []
    assert not hasattr(restored, "wide_rows")
    assert not hasattr(restored, "long_rows")
    assert not hasattr(restored, "score_breakdown_rows")
    assert not hasattr(restored, "error")


def test_per_file_result_primitive_captures_file_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from xic_extractor.extraction.target_extraction import extract_raw_file_result

    config = _config(tmp_path, keep_intermediate_csv=False)
    raw_path = config.data_dir / "Bad.raw"
    raw_path.write_text("", encoding="utf-8")
    targets = [_target("Analyte")]
    monkeypatch.setattr(
        "xic_extractor.extractor.open_raw",
        _open_raw_factory(errors={"Bad.raw": RuntimeError("file locked")}),
    )

    result = extract_raw_file_result(
        2,
        config,
        targets,
        raw_path,
        scoring_context_factory=None,
    )

    assert result.raw_index == 2
    assert result.sample_name == "Bad"
    assert result.file_result.error is not None
    assert "file locked" in result.file_result.error
    assert not hasattr(result, "error")
    assert not hasattr(result, "wide_rows")
    assert not hasattr(result, "long_rows")
    assert not hasattr(result, "score_breakdown_rows")
    assert result.diagnostics[0].issue == "FILE_ERROR"


def test_raw_file_extraction_result_remains_internal() -> None:
    from xic_extractor import extractor

    assert hasattr(extractor, "RawFileExtractionResult")
    assert "RawFileExtractionResult" not in extractor.__all__


def _config(tmp_path: Path, *, keep_intermediate_csv: bool) -> ExtractionConfig:
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
        keep_intermediate_csv=keep_intermediate_csv,
    )


def _target(label: str) -> Target:
    return Target(
        label=label,
        mz=258.1085,
        rt_min=8.0,
        rt_max=10.0,
        ppm_tol=20.0,
        neutral_loss_da=None,
        nl_ppm_warn=None,
        nl_ppm_max=None,
        is_istd=False,
        istd_pair="",
    )


def _ok_peak(rt: float, intensity: float, area: float) -> PeakDetectionResult:
    peak = PeakResult(
        rt=rt,
        intensity=intensity,
        intensity_smoothed=intensity,
        area=area,
        peak_start=rt - 0.5,
        peak_end=rt + 0.5,
    )
    candidate = PeakCandidate(
        peak=peak,
        selection_apex_rt=rt,
        selection_apex_intensity=intensity,
        selection_apex_index=7,
        raw_apex_rt=rt,
        raw_apex_intensity=intensity,
        raw_apex_index=7,
        prominence=intensity * 0.5,
        quality_flags=(),
        region_scan_count=15,
        region_duration_min=1.0,
        region_edge_ratio=1.5,
    )
    return PeakDetectionResult(
        status="OK",
        peak=peak,
        n_points=15,
        max_smoothed=intensity,
        n_prominent_peaks=1,
        candidates=(candidate,),
    )


def _peak_sequence(results: list[PeakDetectionResult]):
    pending = list(results)

    def _fake_find_peak_and_area(
        rt: np.ndarray,
        intensity: np.ndarray,
        config: ExtractionConfig,
        *,
        preferred_rt: float | None = None,
        strict_preferred_rt: bool = False,
        scoring_context_builder: object | None = None,
        istd_confidence_note: str | None = None,
    ) -> PeakDetectionResult:
        return pending.pop(0)

    return _fake_find_peak_and_area


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

    def iter_ms2_scans(self, rt_min: float, rt_max: float):
        return iter([])
