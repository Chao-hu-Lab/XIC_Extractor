from pathlib import Path

from scripts.compare_workbooks import WorkbookCompareResult
from scripts.validation_harness import (
    DEFAULT_FULL_TISSUE_DIR,
    DEFAULT_TISSUE_VALIDATION_DIR,
    ValidationRunSpec,
    build_validation_specs,
    command_to_powershell,
    main,
    run_validation_specs,
)


def test_build_validation_specs_freezes_tiers_commands_and_output_paths(
    tmp_path: Path,
) -> None:
    specs = build_validation_specs(
        suite_names=("manual-2raw", "tissue-8raw", "tissue-85raw"),
        base_dir=Path("C:/repo/XIC_Extractor"),
        output_root=tmp_path / "validation_harness",
        run_id="20260506_test",
        workers=4,
        resolver_mode="local_minimum",
        grid="quick",
    )

    assert [spec.name for spec in specs] == [
        "manual-2raw",
        "tissue-8raw",
        "tissue-85raw",
    ]
    assert specs[0].output_path == (
        tmp_path
        / "validation_harness"
        / "20260506_test"
        / "manual_2raw"
        / "local_minimum_param_sweep_summary.xlsx"
    )
    assert specs[1].output_path == (
        tmp_path
        / "validation_harness"
        / "20260506_test"
        / "tissue_8raw_local_minimum"
        / "xic_results_process_w4.xlsx"
    )
    assert specs[2].requires_confirmation is True

    manual_command = command_to_powershell(specs[0].command)
    assert "scripts\\local_minimum_param_sweep.py" in manual_command
    assert "--parallel-mode process" in manual_command
    assert "--parallel-workers 4" in manual_command

    tissue_command = command_to_powershell(specs[1].command)
    assert str(DEFAULT_TISSUE_VALIDATION_DIR) in tissue_command
    assert "--resolver-mode local_minimum" in tissue_command
    assert "--parallel-mode process" in tissue_command
    assert "--parallel-workers 4" in tissue_command

    full_command = command_to_powershell(specs[2].command)
    assert str(DEFAULT_FULL_TISSUE_DIR) in full_command
    assert "--confirm-full-run" in full_command


def test_run_validation_specs_compares_exact_baseline_workbook_paths(
    tmp_path: Path,
) -> None:
    data_dir = tmp_path / "validation"
    data_dir.mkdir()
    for index in range(8):
        (data_dir / f"Sample{index + 1}.raw").mkdir()

    output_root = tmp_path / "validation_harness"
    spec = ValidationRunSpec(
        name="tissue-8raw",
        kind="extraction",
        description="8 raw subset",
        output_dir=output_root / "run1" / "tissue_8raw_local_minimum",
        output_path=(
            output_root
            / "run1"
            / "tissue_8raw_local_minimum"
            / "xic_results_process_w4.xlsx"
        ),
        command=("uv", "run", "python", "scripts/validate.py"),
        data_dir=data_dir,
        expected_raw_count=8,
        resolver_mode="local_minimum",
        parallel_mode="process",
        workers=4,
    )
    baseline_root = tmp_path / "baseline"
    baseline_path = (
        baseline_root
        / "run1"
        / "tissue_8raw_local_minimum"
        / "xic_results_process_w4.xlsx"
    )
    runner_calls: list[dict[str, object]] = []
    compare_calls: list[tuple[Path, Path]] = []

    def fake_extraction_runner(**kwargs) -> Path:
        runner_calls.append(kwargs)
        return spec.output_path

    def fake_comparer(left: Path, right: Path) -> WorkbookCompareResult:
        compare_calls.append((left, right))
        return WorkbookCompareResult(matched=True, differences=[])

    results = run_validation_specs(
        [spec],
        base_dir=tmp_path,
        output_root=output_root,
        run_id="run1",
        baseline_root=baseline_root,
        extraction_runner=fake_extraction_runner,
        comparer=fake_comparer,
    )

    assert runner_calls == [
        {
            "base_dir": tmp_path,
            "data_dir": data_dir,
            "mode": "process",
            "workers": 4,
            "output_dir": spec.output_dir,
            "settings_overrides": {"resolver_mode": "local_minimum"},
        }
    ]
    assert compare_calls == [(baseline_path, spec.output_path)]
    assert results[0].compare_result == "pass"
    summary = (output_root / "run1" / "validation_summary.csv").read_text(
        encoding="utf-8-sig"
    )
    assert "suite,kind,raw_count,output_path,compare_result" in summary
    assert "tissue-8raw,extraction,8," in summary
    assert ",pass," in summary


def test_run_validation_specs_records_compare_errors_without_traceback(
    tmp_path: Path,
) -> None:
    data_dir = tmp_path / "validation"
    data_dir.mkdir()
    for index in range(8):
        (data_dir / f"Sample{index + 1}.raw").mkdir()

    output_root = tmp_path / "validation_harness"
    spec = ValidationRunSpec(
        name="tissue-8raw",
        kind="extraction",
        description="8 raw subset",
        output_dir=output_root / "run1" / "tissue_8raw_local_minimum",
        output_path=(
            output_root
            / "run1"
            / "tissue_8raw_local_minimum"
            / "xic_results_process_w4.xlsx"
        ),
        command=("uv", "run", "python", "scripts/validate.py"),
        data_dir=data_dir,
        expected_raw_count=8,
        resolver_mode="local_minimum",
        parallel_mode="process",
        workers=4,
    )

    def fake_extraction_runner(**_kwargs) -> Path:
        return spec.output_path

    def failing_comparer(_left: Path, _right: Path) -> WorkbookCompareResult:
        raise FileNotFoundError("baseline workbook is missing")

    results = run_validation_specs(
        [spec],
        base_dir=tmp_path,
        output_root=output_root,
        run_id="run1",
        baseline_root=tmp_path / "baseline",
        extraction_runner=fake_extraction_runner,
        comparer=failing_comparer,
    )

    assert results[0].status == "failed"
    assert results[0].compare_result == "fail"
    assert "baseline workbook is missing" in results[0].message


def test_run_validation_specs_records_baseline_path_errors_without_traceback(
    tmp_path: Path,
) -> None:
    data_dir = tmp_path / "validation"
    data_dir.mkdir()
    for index in range(8):
        (data_dir / f"Sample{index + 1}.raw").mkdir()

    spec = ValidationRunSpec(
        name="tissue-8raw",
        kind="extraction",
        description="8 raw subset",
        output_dir=tmp_path / "outside",
        output_path=tmp_path / "outside" / "xic_results_process_w4.xlsx",
        command=("uv", "run", "python", "scripts/validate.py"),
        data_dir=data_dir,
        expected_raw_count=8,
        resolver_mode="local_minimum",
        parallel_mode="process",
        workers=4,
    )

    results = run_validation_specs(
        [spec],
        base_dir=tmp_path,
        output_root=tmp_path / "validation_harness",
        run_id="run1",
        baseline_root=tmp_path / "baseline",
        extraction_runner=lambda **_kwargs: spec.output_path,
    )

    assert results[0].status == "failed"
    assert results[0].compare_result == "fail"
    assert "outside" in results[0].message


def test_run_validation_specs_runs_manual_sweep_with_script_arguments(
    tmp_path: Path,
) -> None:
    spec = build_validation_specs(
        suite_names=("manual-2raw",),
        base_dir=tmp_path,
        output_root=tmp_path / "validation_harness",
        run_id="run1",
        workers=4,
        resolver_mode="local_minimum",
        grid="quick",
    )[0]
    sweep_args: list[str] = []

    def fake_sweep_runner(argv) -> int:
        sweep_args.extend(argv)
        return 0

    results = run_validation_specs(
        [spec],
        base_dir=tmp_path,
        output_root=tmp_path / "validation_harness",
        run_id="run1",
        sweep_runner=fake_sweep_runner,
    )

    assert results[0].status == "passed"
    assert sweep_args[0] == "--manual-workbook"
    assert "scripts\\local_minimum_param_sweep.py" not in sweep_args
    assert "--parallel-workers" in sweep_args


def test_run_validation_specs_rejects_wrong_raw_count(tmp_path: Path) -> None:
    data_dir = tmp_path / "validation"
    data_dir.mkdir()
    (data_dir / "OnlyOne.raw").mkdir()
    spec = ValidationRunSpec(
        name="tissue-8raw",
        kind="extraction",
        description="8 raw subset",
        output_dir=tmp_path / "out",
        output_path=tmp_path / "out" / "xic_results_process_w4.xlsx",
        command=("uv", "run", "python", "scripts/validate.py"),
        data_dir=data_dir,
        expected_raw_count=8,
        resolver_mode="local_minimum",
        parallel_mode="process",
        workers=4,
    )

    results = run_validation_specs(
        [spec],
        base_dir=tmp_path,
        output_root=tmp_path / "validation_harness",
        run_id="run1",
        extraction_runner=lambda **_kwargs: spec.output_path,
    )

    assert results[0].status == "failed"
    assert "expected 8 raw files, found 1" in results[0].message


def test_cli_refuses_full85_without_confirmation(tmp_path: Path, capsys) -> None:
    exit_code = main(
        [
            "--suite",
            "tissue-85raw",
            "--output-root",
            str(tmp_path / "validation_harness"),
            "--run-id",
            "run1",
            "--dry-run",
        ]
    )

    assert exit_code == 2
    assert "requires --confirm-full-run" in capsys.readouterr().err
