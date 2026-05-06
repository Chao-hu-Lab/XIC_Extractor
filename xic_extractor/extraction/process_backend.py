from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

from xic_extractor.config import ExtractionConfig, Target
from xic_extractor.extraction.pipeline import (
    fallback_injection_order_from_mtime,
    resolve_injection_order,
    resolve_rt_prior_library,
)
from xic_extractor.output.messages import DiagnosticRecord
from xic_extractor.rt_prior_library import LibraryEntry

if TYPE_CHECKING:
    from xic_extractor.extraction.jobs import ScoringInputs
    from xic_extractor.extractor import RawFileExtractionResult, RunOutput


def run_process(
    config: ExtractionConfig,
    targets: list[Target],
    *,
    progress_callback: Callable[[int, int, str], None] | None = None,
    should_stop: Callable[[], bool] | None = None,
    injection_order: dict[str, int] | None = None,
    rt_prior_library: dict[tuple[str, str], LibraryEntry] | None = None,
) -> RunOutput:
    from xic_extractor import extractor
    from xic_extractor.extraction.jobs import ScoringInputs

    raw_paths = sorted(config.data_dir.glob("*.raw"))
    resolved_injection_order = resolve_injection_order(
        config, raw_paths, injection_order
    )
    resolved_rt_prior_library = resolve_rt_prior_library(config, rt_prior_library)
    istd_targets = tuple(target for target in targets if target.is_istd)
    istd_rts_by_sample = collect_istd_prepass_process(
        config,
        istd_targets,
        raw_paths,
        should_stop=should_stop,
    )
    process_injection_order = (
        resolved_injection_order
        if resolved_injection_order is not None
        else fallback_injection_order_from_mtime(raw_paths)
    )

    scoring_inputs = ScoringInputs(
        injection_order=process_injection_order,
        istd_rts_by_sample=istd_rts_by_sample,
        rt_prior_library=resolved_rt_prior_library or {},
    )
    raw_results = collect_raw_file_results_process(
        config,
        tuple(targets),
        raw_paths,
        scoring_inputs,
        progress_callback=progress_callback,
        should_stop=should_stop,
    )

    file_results = [result.file_result for result in raw_results]
    diagnostics: list[DiagnosticRecord] = []
    for result in raw_results:
        diagnostics.extend(result.diagnostics)

    return extractor.RunOutput(file_results=file_results, diagnostics=diagnostics)


def collect_raw_file_results_process(
    config: ExtractionConfig,
    targets: tuple[Target, ...],
    raw_paths: list[Path],
    scoring_inputs: ScoringInputs,
    *,
    progress_callback: Callable[[int, int, str], None] | None = None,
    should_stop: Callable[[], bool] | None = None,
    runner: Callable[..., list[Any]] | None = None,
) -> list[RawFileExtractionResult]:
    from xic_extractor.extraction.jobs import (
        RawFileJob,
        collect_ordered_results,
        run_raw_file_jobs,
    )

    if should_stop is not None and should_stop():
        return []
    jobs = [
        RawFileJob(
            raw_index=index,
            raw_path=raw_path,
            config=config,
            targets=targets,
            scoring_inputs=scoring_inputs,
        )
        for index, raw_path in enumerate(raw_paths, start=1)
    ]
    raw_runner = runner if runner is not None else run_raw_file_jobs
    results = raw_runner(
        jobs,
        max_workers=config.parallel_workers,
        should_stop=should_stop,
        progress_callback=progress_callback,
        total=len(raw_paths),
    )
    return collect_ordered_results(results)


def collect_istd_prepass_process(
    config: ExtractionConfig,
    istd_targets: tuple[Target, ...],
    raw_paths: list[Path],
    *,
    should_stop: Callable[[], bool] | None = None,
    runner: Callable[..., list[Any]] | None = None,
) -> dict[str, dict[str, float]]:
    from xic_extractor.extraction.jobs import (
        IstdPrepassResult,
        ParallelExecutionError,
        RawFileJob,
        WorkerError,
        run_istd_prepass_jobs,
    )

    if not istd_targets:
        return {}
    if should_stop is not None and should_stop():
        return {}
    jobs = [
        RawFileJob(
            raw_index=index,
            raw_path=raw_path,
            config=config,
            targets=istd_targets,
        )
        for index, raw_path in enumerate(raw_paths, start=1)
    ]
    prepass_runner = runner if runner is not None else run_istd_prepass_jobs
    results = prepass_runner(
        jobs,
        max_workers=config.parallel_workers,
        should_stop=should_stop,
    )

    errors = [result for result in results if isinstance(result, WorkerError)]
    if errors:
        messages = "; ".join(
            f"{error.raw_name}: {error.message}"
            for error in sorted(errors, key=lambda item: item.raw_index)
        )
        raise ParallelExecutionError(messages)

    istd_rts_by_sample: dict[str, dict[str, float]] = {}
    ordered_results = sorted(
        (result for result in results if isinstance(result, IstdPrepassResult)),
        key=lambda item: item.raw_index,
    )
    for result in ordered_results:
        for istd_label, anchor_rt in result.anchors.items():
            istd_rts_by_sample.setdefault(istd_label, {})[
                result.sample_name
            ] = anchor_rt
    return istd_rts_by_sample
