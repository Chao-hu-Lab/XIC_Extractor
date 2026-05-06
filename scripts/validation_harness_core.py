from __future__ import annotations

import csv
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from scripts.benchmark_parallel import _run_extraction_once
from scripts.compare_workbooks import WorkbookCompareResult, compare_workbooks

DEFAULT_MANUAL_DIR = Path(r"C:\Xcalibur\data\20251219_need process data\XIC test")
DEFAULT_MANUAL_WORKBOOK = DEFAULT_MANUAL_DIR / "20260112 UPLC splitting_forXIC.xlsx"
DEFAULT_NOSPLIT_RAW = (
    DEFAULT_MANUAL_DIR / "20251219_HESI_NoSplit_25ppb_ISTDs-1_60min_1_02.raw"
)
DEFAULT_SPLIT_RAW = (
    DEFAULT_MANUAL_DIR / "20260104_Split_NSI_w-75um-50cm_25ppb_ISTDs-1_60min_1_02.raw"
)
DEFAULT_NOSPLIT_TARGETS = DEFAULT_MANUAL_DIR / "combined_targets_file1.csv"
DEFAULT_SPLIT_TARGETS = DEFAULT_MANUAL_DIR / "combined_targets_file2.csv"
DEFAULT_TISSUE_VALIDATION_DIR = Path(
    r"C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation"
)
DEFAULT_FULL_TISSUE_DIR = Path(r"C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R")

SUITE_CHOICES = ("manual-2raw", "tissue-8raw", "tissue-85raw")


@dataclass(frozen=True)
class ValidationRunSpec:
    name: str
    kind: str
    description: str
    output_dir: Path
    output_path: Path
    command: tuple[str, ...]
    data_dir: Path | None = None
    expected_raw_count: int | None = None
    resolver_mode: str = "local_minimum"
    parallel_mode: str = "process"
    workers: int = 4
    requires_confirmation: bool = False


@dataclass(frozen=True)
class ValidationRunResult:
    suite: str
    kind: str
    raw_count: int | None
    output_path: Path
    compare_result: str
    status: str
    message: str = ""
    compare_differences: tuple[str, ...] = ()


ExtractionRunner = Callable[..., Path]
SweepRunner = Callable[[Sequence[str]], int]
Comparer = Callable[[Path, Path], WorkbookCompareResult]


def build_validation_specs(
    *,
    suite_names: Sequence[str],
    base_dir: Path,
    output_root: Path,
    run_id: str,
    workers: int,
    resolver_mode: str,
    grid: str,
    parallel_mode: str = "process",
    data_dir_override: Path | None = None,
) -> list[ValidationRunSpec]:
    run_root = output_root / run_id
    specs: list[ValidationRunSpec] = []
    for suite_name in _expand_suite_names(suite_names):
        if suite_name == "manual-2raw":
            output_dir = run_root / "manual_2raw"
            specs.append(
                ValidationRunSpec(
                    name=suite_name,
                    kind="manual_truth_sweep",
                    description="Two standard RAW files scored against manual truth.",
                    output_dir=output_dir,
                    output_path=output_dir / "local_minimum_param_sweep_summary.xlsx",
                    command=_manual_2raw_command(
                        output_dir=output_dir,
                        grid=grid,
                        parallel_mode=parallel_mode,
                        workers=workers,
                    ),
                    expected_raw_count=2,
                    parallel_mode=parallel_mode,
                    workers=workers,
                )
            )
        elif suite_name == "tissue-8raw":
            data_dir = data_dir_override or DEFAULT_TISSUE_VALIDATION_DIR
            output_dir = run_root / f"tissue_8raw_{resolver_mode}"
            specs.append(
                ValidationRunSpec(
                    name=suite_name,
                    kind="extraction",
                    description="Daily tissue validation subset.",
                    output_dir=output_dir,
                    output_path=(
                        output_dir / f"xic_results_{parallel_mode}_w{workers}.xlsx"
                    ),
                    command=_harness_command(
                        suite_name=suite_name,
                        base_dir=base_dir,
                        output_root=output_root,
                        run_id=run_id,
                        resolver_mode=resolver_mode,
                        parallel_mode=parallel_mode,
                        workers=workers,
                        data_dir=data_dir,
                    ),
                    data_dir=data_dir,
                    expected_raw_count=8,
                    resolver_mode=resolver_mode,
                    parallel_mode=parallel_mode,
                    workers=workers,
                )
            )
        elif suite_name == "tissue-85raw":
            data_dir = data_dir_override or DEFAULT_FULL_TISSUE_DIR
            output_dir = run_root / f"tissue_85raw_{resolver_mode}"
            specs.append(
                ValidationRunSpec(
                    name=suite_name,
                    kind="extraction",
                    description="Full tissue release gate.",
                    output_dir=output_dir,
                    output_path=(
                        output_dir / f"xic_results_{parallel_mode}_w{workers}.xlsx"
                    ),
                    command=(
                        *_harness_command(
                            suite_name=suite_name,
                            base_dir=base_dir,
                            output_root=output_root,
                            run_id=run_id,
                            resolver_mode=resolver_mode,
                            parallel_mode=parallel_mode,
                            workers=workers,
                            data_dir=data_dir,
                        ),
                        "--confirm-full-run",
                    ),
                    data_dir=data_dir,
                    expected_raw_count=85,
                    resolver_mode=resolver_mode,
                    parallel_mode=parallel_mode,
                    workers=workers,
                    requires_confirmation=True,
                )
            )
    return specs


def command_to_powershell(command: Sequence[str]) -> str:
    return " ".join(_quote_powershell_arg(part) for part in command)


def run_validation_specs(
    specs: Sequence[ValidationRunSpec],
    *,
    base_dir: Path,
    output_root: Path,
    run_id: str,
    baseline_root: Path | None = None,
    extraction_runner: ExtractionRunner = _run_extraction_once,
    sweep_runner: SweepRunner | None = None,
    comparer: Comparer = compare_workbooks,
) -> list[ValidationRunResult]:
    if sweep_runner is None:
        sweep_runner = _run_command
    results: list[ValidationRunResult] = []
    for spec in specs:
        result = _run_one_spec(
            spec,
            base_dir=base_dir,
            output_root=output_root,
            baseline_root=baseline_root,
            extraction_runner=extraction_runner,
            sweep_runner=sweep_runner,
            comparer=comparer,
        )
        results.append(result)

    _write_validation_summary(
        output_root / run_id / "validation_summary.csv",
        specs,
        results,
    )
    return results


def _run_one_spec(
    spec: ValidationRunSpec,
    *,
    base_dir: Path,
    output_root: Path,
    baseline_root: Path | None,
    extraction_runner: ExtractionRunner,
    sweep_runner: SweepRunner,
    comparer: Comparer,
) -> ValidationRunResult:
    raw_count = _raw_count(spec)
    if (
        spec.expected_raw_count is not None
        and raw_count is not None
        and raw_count != spec.expected_raw_count
    ):
        return ValidationRunResult(
            suite=spec.name,
            kind=spec.kind,
            raw_count=raw_count,
            output_path=spec.output_path,
            compare_result="not_run",
            status="failed",
            message=f"expected {spec.expected_raw_count} raw files, found {raw_count}",
        )

    try:
        if spec.kind == "manual_truth_sweep":
            exit_code = sweep_runner(spec.command[4:])
            if exit_code != 0:
                return ValidationRunResult(
                    suite=spec.name,
                    kind=spec.kind,
                    raw_count=raw_count,
                    output_path=spec.output_path,
                    compare_result="manual_truth",
                    status="failed",
                    message=f"manual truth sweep exited with {exit_code}",
                )
        elif spec.kind == "extraction":
            if spec.data_dir is None:
                raise ValueError(f"{spec.name}: extraction suite requires data_dir")
            workbook_path = extraction_runner(
                base_dir=base_dir,
                data_dir=spec.data_dir,
                mode=spec.parallel_mode,
                workers=spec.workers,
                output_dir=spec.output_dir,
                settings_overrides={"resolver_mode": spec.resolver_mode},
            )
            if workbook_path != spec.output_path:
                raise ValueError(
                    f"{spec.name}: expected output {spec.output_path}, "
                    f"got {workbook_path}"
                )
        else:
            raise ValueError(f"Unknown validation kind: {spec.kind}")
    except (OSError, ValueError) as exc:
        return ValidationRunResult(
            suite=spec.name,
            kind=spec.kind,
            raw_count=raw_count,
            output_path=spec.output_path,
            compare_result="not_run",
            status="failed",
            message=str(exc),
        )

    try:
        compare_result, differences = _compare_if_requested(
            spec,
            output_root=output_root,
            baseline_root=baseline_root,
            comparer=comparer,
        )
    except OSError as exc:
        return ValidationRunResult(
            suite=spec.name,
            kind=spec.kind,
            raw_count=raw_count,
            output_path=spec.output_path,
            compare_result="fail",
            status="failed",
            message=str(exc),
        )
    return ValidationRunResult(
        suite=spec.name,
        kind=spec.kind,
        raw_count=raw_count,
        output_path=spec.output_path,
        compare_result=compare_result,
        status="passed" if compare_result != "fail" else "failed",
        compare_differences=differences,
    )


def _manual_2raw_command(
    *,
    output_dir: Path,
    grid: str,
    parallel_mode: str,
    workers: int,
) -> tuple[str, ...]:
    return (
        "uv",
        "run",
        "python",
        r"scripts\local_minimum_param_sweep.py",
        "--manual-workbook",
        str(DEFAULT_MANUAL_WORKBOOK),
        "--nosplit-raw",
        str(DEFAULT_NOSPLIT_RAW),
        "--split-raw",
        str(DEFAULT_SPLIT_RAW),
        "--nosplit-targets",
        str(DEFAULT_NOSPLIT_TARGETS),
        "--split-targets",
        str(DEFAULT_SPLIT_TARGETS),
        "--output-dir",
        str(output_dir),
        "--grid",
        grid,
        "--parallel-mode",
        parallel_mode,
        "--parallel-workers",
        str(workers),
    )


def _harness_command(
    *,
    suite_name: str,
    base_dir: Path,
    output_root: Path,
    run_id: str,
    resolver_mode: str,
    parallel_mode: str,
    workers: int,
    data_dir: Path,
) -> tuple[str, ...]:
    return (
        "uv",
        "run",
        "python",
        r"scripts\validation_harness.py",
        "--suite",
        suite_name,
        "--base-dir",
        str(base_dir),
        "--output-root",
        str(output_root),
        "--run-id",
        run_id,
        "--resolver-mode",
        resolver_mode,
        "--parallel-mode",
        parallel_mode,
        "--parallel-workers",
        str(workers),
        "--data-dir",
        str(data_dir),
    )


def _expand_suite_names(suite_names: Sequence[str]) -> tuple[str, ...]:
    expanded: list[str] = []
    for suite_name in suite_names:
        if suite_name == "all":
            expanded.extend(SUITE_CHOICES)
        else:
            expanded.append(suite_name)
    for suite_name in expanded:
        if suite_name not in SUITE_CHOICES:
            raise ValueError(f"Unknown validation suite: {suite_name}")
    return tuple(dict.fromkeys(expanded))


def _raw_count(spec: ValidationRunSpec) -> int | None:
    if spec.kind == "manual_truth_sweep":
        return spec.expected_raw_count
    if spec.data_dir is None:
        return None
    return len(sorted(spec.data_dir.glob("*.raw")))


def _compare_if_requested(
    spec: ValidationRunSpec,
    *,
    output_root: Path,
    baseline_root: Path | None,
    comparer: Comparer,
) -> tuple[str, tuple[str, ...]]:
    if spec.kind == "manual_truth_sweep":
        return "manual_truth", ()
    if baseline_root is None:
        return "not_requested", ()
    baseline_path = baseline_root / spec.output_path.relative_to(output_root)
    comparison = comparer(baseline_path, spec.output_path)
    return ("pass" if comparison.matched else "fail"), tuple(comparison.differences)


def _write_validation_summary(
    path: Path,
    specs: Sequence[ValidationRunSpec],
    results: Sequence[ValidationRunResult],
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    specs_by_name = {spec.name: spec for spec in specs}
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "suite",
                "kind",
                "raw_count",
                "output_path",
                "compare_result",
                "status",
                "message",
                "compare_differences",
                "command",
            ],
        )
        writer.writeheader()
        for result in results:
            spec = specs_by_name[result.suite]
            writer.writerow(
                {
                    "suite": result.suite,
                    "kind": result.kind,
                    "raw_count": "" if result.raw_count is None else result.raw_count,
                    "output_path": str(result.output_path),
                    "compare_result": result.compare_result,
                    "status": result.status,
                    "message": result.message,
                    "compare_differences": " | ".join(result.compare_differences),
                    "command": command_to_powershell(spec.command),
                }
            )
    return path


def _run_command(argv: Sequence[str]) -> int:
    from scripts import local_minimum_param_sweep

    return local_minimum_param_sweep.main(argv)


def _quote_powershell_arg(value: str) -> str:
    if not value:
        return '""'
    if any(char.isspace() for char in value):
        return f'"{value}"'
    return value
