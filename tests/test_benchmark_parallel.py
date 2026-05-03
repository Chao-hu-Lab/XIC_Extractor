from pathlib import Path

from scripts.benchmark_parallel import build_run_specs, run_benchmark
from scripts.compare_workbooks import WorkbookCompareResult


def test_build_run_specs_uses_expected_mode_worker_matrix_and_output_dirs(
    tmp_path: Path,
) -> None:
    specs = build_run_specs(tmp_path / "parallel_benchmark", workers=(2, 4))

    assert [(spec.mode, spec.workers) for spec in specs] == [
        ("serial", 1),
        ("process", 2),
        ("process", 4),
    ]
    assert [spec.output_dir.name for spec in specs] == [
        "serial_w1",
        "process_w2",
        "process_w4",
    ]


def test_run_benchmark_compares_exact_returned_workbook_paths(tmp_path: Path) -> None:
    data_dir = tmp_path / "validation"
    data_dir.mkdir()
    for name in ("A.raw", "B.raw", "C.raw"):
        (data_dir / name).mkdir()
    returned_paths: dict[tuple[str, int], Path] = {}
    runner_calls: list[tuple[str, int, Path]] = []
    compare_calls: list[tuple[Path, Path]] = []

    def fake_runner(
        *,
        base_dir: Path,
        data_dir: Path,
        mode: str,
        workers: int,
        output_dir: Path,
    ) -> Path:
        runner_calls.append((mode, workers, output_dir))
        workbook_path = output_dir / f"actual_{mode}_w{workers}.xlsx"
        returned_paths[(mode, workers)] = workbook_path
        return workbook_path

    def fake_compare(left: Path, right: Path) -> WorkbookCompareResult:
        compare_calls.append((left, right))
        return WorkbookCompareResult(matched=True, differences=[])

    results = run_benchmark(
        base_dir=tmp_path,
        data_dir=data_dir,
        workers=(2, 4),
        output_dir=tmp_path / "parallel_benchmark",
        runner=fake_runner,
        comparer=fake_compare,
        timer=_fake_timer(),
    )

    assert runner_calls == [
        ("serial", 1, tmp_path / "parallel_benchmark" / "serial_w1"),
        ("process", 2, tmp_path / "parallel_benchmark" / "process_w2"),
        ("process", 4, tmp_path / "parallel_benchmark" / "process_w4"),
    ]
    assert compare_calls == [
        (returned_paths[("serial", 1)], returned_paths[("process", 2)]),
        (returned_paths[("serial", 1)], returned_paths[("process", 4)]),
    ]
    assert [(result.mode, result.workers, result.raw_count) for result in results] == [
        ("serial", 1, 3),
        ("process", 2, 3),
        ("process", 4, 3),
    ]
    assert [result.compare_result for result in results] == [
        "baseline",
        "pass",
        "pass",
    ]


def test_run_benchmark_writes_summary_csv(tmp_path: Path) -> None:
    data_dir = tmp_path / "validation"
    data_dir.mkdir()
    (data_dir / "A.raw").mkdir()

    def fake_runner(
        *,
        base_dir: Path,
        data_dir: Path,
        mode: str,
        workers: int,
        output_dir: Path,
    ) -> Path:
        return output_dir / f"{mode}_w{workers}.xlsx"

    run_benchmark(
        base_dir=tmp_path,
        data_dir=data_dir,
        workers=(2,),
        output_dir=tmp_path / "parallel_benchmark",
        runner=fake_runner,
        comparer=lambda _left, _right: WorkbookCompareResult(
            matched=False,
            differences=["XIC Results!R2C3: 1 != 2"],
        ),
        timer=_fake_timer(),
    )

    summary = (tmp_path / "parallel_benchmark" / "benchmark_summary.csv").read_text(
        encoding="utf-8-sig"
    )

    assert (
        "mode,workers,raw_count,elapsed_seconds,workbook_path,compare_result"
        in summary
    )
    assert "serial,1,1," in summary
    assert "baseline" in summary
    assert "process,2,1," in summary
    assert "fail" in summary
    assert "XIC Results!R2C3: 1 != 2" in summary


def _fake_timer():
    values = iter([0.0, 1.0, 1.0, 3.0, 3.0, 6.0])
    return lambda: next(values)
