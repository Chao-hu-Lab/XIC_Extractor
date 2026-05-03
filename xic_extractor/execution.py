from __future__ import annotations

import io
import pickle
from collections.abc import Iterable
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass, fields, is_dataclass
from multiprocessing import get_context
from pathlib import Path
from types import ModuleType
from typing import Any

from xic_extractor.config import ExtractionConfig, Target
from xic_extractor.extraction.scoring_factory import build_scoring_context_factory
from xic_extractor.extractor import RawFileExtractionResult
from xic_extractor.rt_prior_library import LibraryEntry


@dataclass(frozen=True)
class ScoringInputs:
    injection_order: dict[str, int]
    istd_rts_by_sample: dict[str, dict[str, float]]
    rt_prior_library: dict[tuple[str, str], LibraryEntry]


@dataclass(frozen=True)
class RawFileJob:
    raw_index: int
    raw_path: Path
    config: ExtractionConfig
    targets: tuple[Target, ...]
    scoring_inputs: ScoringInputs | Any | None = None


@dataclass(frozen=True)
class IstdPrepassResult:
    raw_index: int
    raw_name: str
    sample_name: str
    anchors: dict[str, float]
    results: dict[str, Any]
    diagnostics: list[Any]
    shape_metrics: dict[str, tuple[float, float | None]]


@dataclass(frozen=True)
class WorkerError:
    raw_index: int
    raw_name: str
    message: str


@dataclass(frozen=True)
class SpawnSmokeJob:
    raw_index: int
    raw_name: str


class ParallelExecutionError(RuntimeError):
    """Raised when a process worker reports a failed RAW job."""


WorkerResult = RawFileExtractionResult | WorkerError
IstdPrepassWorkerResult = IstdPrepassResult | WorkerError


def validate_job_payload(job: RawFileJob) -> None:
    _validate_payload_value(job, path="job")
    try:
        pickle.dumps(job)
    except Exception as exc:
        raise TypeError(f"job payload is not pickleable: {exc}") from exc


def collect_ordered_results(
    results: Iterable[WorkerResult],
) -> list[RawFileExtractionResult]:
    successes: list[RawFileExtractionResult] = []
    errors: list[WorkerError] = []
    for result in results:
        if isinstance(result, WorkerError):
            errors.append(result)
        else:
            successes.append(result)

    if errors:
        messages = "; ".join(
            f"{error.raw_name}: {error.message}" for error in sorted(
                errors,
                key=lambda item: item.raw_index,
            )
        )
        raise ParallelExecutionError(messages)
    return sorted(successes, key=lambda item: item.raw_index)


def run_istd_prepass_jobs(
    jobs: Iterable[RawFileJob],
    *,
    max_workers: int,
) -> list[IstdPrepassWorkerResult]:
    pending_jobs = list(jobs)
    for job in pending_jobs:
        validate_job_payload(job)
    context = get_context("spawn")
    results: list[IstdPrepassWorkerResult] = []
    with ProcessPoolExecutor(max_workers=max_workers, mp_context=context) as executor:
        future_to_job = {
            executor.submit(extract_istd_prepass_job, job): job
            for job in pending_jobs
        }
        for future in as_completed(future_to_job):
            job = future_to_job[future]
            try:
                results.append(future.result())
            except Exception as exc:
                results.append(
                    WorkerError(
                        raw_index=job.raw_index,
                        raw_name=job.raw_path.name,
                        message=f"{type(exc).__name__}: {exc}",
                    )
                )
    return results


def run_raw_file_jobs(
    jobs: Iterable[RawFileJob],
    *,
    max_workers: int,
) -> list[WorkerResult]:
    pending_jobs = list(jobs)
    for job in pending_jobs:
        validate_job_payload(job)
    context = get_context("spawn")
    results: list[WorkerResult] = []
    with ProcessPoolExecutor(max_workers=max_workers, mp_context=context) as executor:
        future_to_job = {
            executor.submit(extract_raw_file_job, job): job for job in pending_jobs
        }
        for future in as_completed(future_to_job):
            job = future_to_job[future]
            try:
                results.append(future.result())
            except Exception as exc:
                results.append(
                    WorkerError(
                        raw_index=job.raw_index,
                        raw_name=job.raw_path.name,
                        message=f"{type(exc).__name__}: {exc}",
                    )
                )
    return results


def extract_raw_file_job(job: RawFileJob) -> WorkerResult:
    from xic_extractor.extractor import _extract_raw_file_result

    try:
        scoring_context_factory = None
        if job.scoring_inputs is not None:
            scoring_context_factory = build_scoring_context_factory(
                config=job.config,
                injection_order=job.scoring_inputs.injection_order,
                istd_rts_by_sample=job.scoring_inputs.istd_rts_by_sample,
                rt_prior_library=job.scoring_inputs.rt_prior_library,
            )
        return _extract_raw_file_result(
            job.raw_index,
            job.config,
            list(job.targets),
            job.raw_path,
            scoring_context_factory=scoring_context_factory,
        )
    except Exception as exc:
        return WorkerError(
            raw_index=job.raw_index,
            raw_name=job.raw_path.name,
            message=f"{type(exc).__name__}: {exc}",
        )


def extract_istd_prepass_job(job: RawFileJob) -> IstdPrepassWorkerResult:
    from xic_extractor.extractor import _extract_istd_anchors_only

    try:
        prepass = _extract_istd_anchors_only(
            job.config,
            list(job.targets),
            job.raw_path,
        )
        if prepass is None:
            return IstdPrepassResult(
                raw_index=job.raw_index,
                raw_name=job.raw_path.name,
                sample_name=job.raw_path.stem,
                anchors={},
                results={},
                diagnostics=[],
                shape_metrics={},
            )
        anchors, results, diagnostics, shape_metrics = prepass
        return IstdPrepassResult(
            raw_index=job.raw_index,
            raw_name=job.raw_path.name,
            sample_name=job.raw_path.stem,
            anchors=anchors,
            results=results,
            diagnostics=diagnostics,
            shape_metrics=shape_metrics,
        )
    except Exception as exc:
        return WorkerError(
            raw_index=job.raw_index,
            raw_name=job.raw_path.name,
            message=f"{type(exc).__name__}: {exc}",
        )


def spawn_smoke_worker(job: SpawnSmokeJob) -> str:
    return f"{job.raw_index}:{job.raw_name}"


def _validate_payload_value(value: Any, *, path: str) -> None:
    if callable(value):
        raise TypeError(f"{path} contains callable value")
    if isinstance(value, io.IOBase):
        raise TypeError(f"{path} contains file handle")
    if isinstance(value, ModuleType):
        raise TypeError(f"{path} contains module object")
    if is_dataclass(value) and not isinstance(value, type):
        for field in fields(value):
            _validate_payload_value(
                getattr(value, field.name),
                path=f"{path}.{field.name}",
            )
        return
    if isinstance(value, dict):
        for key, item in value.items():
            _validate_payload_value(key, path=f"{path}.<key>")
            _validate_payload_value(item, path=f"{path}[{key!r}]")
        return
    if isinstance(value, (list, tuple, set, frozenset)):
        for index, item in enumerate(value):
            _validate_payload_value(item, path=f"{path}[{index}]")
