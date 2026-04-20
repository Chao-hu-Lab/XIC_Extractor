import tomllib
from pathlib import Path
from types import SimpleNamespace

from xic_extractor.config import ConfigError, ExtractionConfig, Target
from xic_extractor.extractor import DiagnosticRecord, RunOutput
from xic_extractor.raw_reader import RawReaderError


def test_cli_runs_extraction_with_base_dir_and_skips_excel(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    module = _module()
    config = _config(tmp_path)
    targets = [_target("Analyte")]
    calls: dict[str, object] = {}

    def _load_config(config_dir: Path) -> tuple[ExtractionConfig, list[Target]]:
        calls["config_dir"] = config_dir
        return config, targets

    monkeypatch.setattr(module, "load_config", _load_config)
    monkeypatch.setattr(module.extractor, "run", _fake_run(calls))
    monkeypatch.setattr(
        module.csv_to_excel,
        "run",
        lambda *_args: calls.setdefault("excel", True),
    )

    exit_code = module.main(["--base-dir", str(tmp_path), "--skip-excel"])

    assert exit_code == 0
    assert calls["config_dir"] == tmp_path / "config"
    assert calls["run_config"] is config
    assert calls["run_targets"] == targets
    assert "excel" not in calls
    stdout = capsys.readouterr().out
    assert "Processed files: 2" in stdout
    assert "Diagnostics: 1" in stdout
    assert "1/2 SampleA.raw" in stdout


def test_cli_runs_excel_conversion_by_default(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    module = _module()
    config = _config(tmp_path)
    targets = [_target("Analyte")]
    calls: dict[str, object] = {}

    monkeypatch.setattr(module, "load_config", lambda _config_dir: (config, targets))
    monkeypatch.setattr(module.extractor, "run", _fake_run(calls))
    monkeypatch.setattr(
        module.csv_to_excel,
        "run",
        lambda excel_config, excel_targets: calls.update(
            {"excel_config": excel_config, "excel_targets": excel_targets}
        ),
    )

    exit_code = module.main(["--base-dir", str(tmp_path)])

    assert exit_code == 0
    assert calls["excel_config"] is config
    assert calls["excel_targets"] == targets
    assert "Excel skipped" not in capsys.readouterr().out


def test_cli_accepts_excel_flag_for_compatibility(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    module = _module()
    config = _config(tmp_path)
    targets = [_target("Analyte")]
    calls: dict[str, object] = {}

    monkeypatch.setattr(module, "load_config", lambda _config_dir: (config, targets))
    monkeypatch.setattr(module.extractor, "run", _fake_run(calls))
    monkeypatch.setattr(
        module.csv_to_excel,
        "run",
        lambda excel_config, excel_targets: calls.update(
            {"excel_config": excel_config, "excel_targets": excel_targets}
        ),
    )

    exit_code = module.main(["--base-dir", str(tmp_path), "--excel"])

    assert exit_code == 0
    assert calls["excel_config"] is config
    assert calls["excel_targets"] == targets
    assert "Excel skipped" not in capsys.readouterr().out


def test_cli_reports_config_errors_without_traceback(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    module = _module()
    monkeypatch.setattr(
        module,
        "load_config",
        lambda _config_dir: (_ for _ in ()).throw(ConfigError("settings.csv missing")),
    )

    exit_code = module.main(["--base-dir", str(tmp_path)])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "settings.csv missing" in captured.err
    assert "Traceback" not in captured.err


def test_cli_reports_reader_setup_errors_without_traceback(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    module = _module()
    config = _config(tmp_path)
    targets = [_target("Analyte")]
    monkeypatch.setattr(module, "load_config", lambda _config_dir: (config, targets))
    monkeypatch.setattr(
        module.extractor,
        "run",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            RawReaderError("pythonnet is not installed")
        ),
    )

    exit_code = module.main(["--base-dir", str(tmp_path)])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "pythonnet is not installed" in captured.err
    assert "Traceback" not in captured.err


def test_pyproject_exposes_cli_entry_point() -> None:
    pyproject = Path("pyproject.toml").read_text(encoding="utf-8")

    assert 'xic-extractor-cli = "scripts.run_extraction:main"' in pyproject


def test_pyproject_excludes_python_314_for_pythonnet() -> None:
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    assert pyproject["project"]["requires-python"] == ">=3.10,<3.14"


def _module():
    import scripts.run_extraction as module

    return module


def _fake_run(calls: dict[str, object]):
    def _run(config, targets, progress_callback=None):
        calls["run_config"] = config
        calls["run_targets"] = targets
        if progress_callback is not None:
            progress_callback(1, 2, "SampleA.raw")
        return RunOutput(
            file_results=[
                SimpleNamespace(sample_name="SampleA"),
                SimpleNamespace(sample_name="SampleB"),
            ],
            diagnostics=[
                DiagnosticRecord(
                    sample_name="SampleB",
                    target_label="Analyte",
                    issue="PEAK_NOT_FOUND",
                    reason="No peak",
                )
            ],
        )

    return _run


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
