from __future__ import annotations

import io
import pickle
from collections.abc import Callable, Iterable, Mapping, Sequence
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from dataclasses import dataclass, fields, is_dataclass
from multiprocessing import get_context
from pathlib import Path
from time import perf_counter
from types import ModuleType
from typing import Any

from xic_extractor.alignment.config import AlignmentConfig
from xic_extractor.alignment.identity_coherence.models import (
    CandidateTrace,
    IdentityCoherenceTraceRequest,
    IdentityCoherenceTraceResult,
)
from xic_extractor.alignment.matrix import AlignedCell
from xic_extractor.alignment.ms1_index_source import (
    OwnerBackfillXicBackend,
    source_for_owner_backfill_backend,
)
from xic_extractor.alignment.owner_backfill import build_owner_backfill_cells
from xic_extractor.alignment.owner_clustering import OwnerAlignedFeature
from xic_extractor.alignment.ownership import (
    OwnershipBuildResult,
    build_sample_local_owners,
)
from xic_extractor.alignment.ownership_models import (
    AmbiguousOwnerRecord,
    OwnerAssignment,
    SampleLocalMS1Owner,
)
from xic_extractor.config import ExtractionConfig
from xic_extractor.xic_models import XICRequest, XICTrace


@dataclass(frozen=True)
class OwnerBuildSampleJob:
    sample_index: int
    sample_stem: str
    raw_path: Path
    dll_dir: Path
    candidates: tuple[Any, ...]
    alignment_config: AlignmentConfig
    peak_config: ExtractionConfig
    raw_xic_batch_size: int = 1
    emit_region_audit: bool = False


@dataclass(frozen=True)
class OwnerBuildTimingStats:
    sample_stem: str
    elapsed_sec: float
    extract_xic_count: int
    point_count: int
    extract_xic_batch_count: int = 0
    raw_chromatogram_call_count: int = 0


@dataclass(frozen=True)
class OwnerBuildSampleResult:
    sample_index: int
    sample_stem: str
    owners: tuple[SampleLocalMS1Owner, ...]
    assignments: tuple[OwnerAssignment, ...]
    ambiguous_records: tuple[AmbiguousOwnerRecord, ...]
    timing_stats: tuple[OwnerBuildTimingStats, ...] = ()


@dataclass(frozen=True)
class OwnerBuildProcessOutput:
    ownership: OwnershipBuildResult
    timing_stats: tuple[OwnerBuildTimingStats, ...]


@dataclass(frozen=True)
class OwnerBuildWorkerError:
    sample_index: int
    sample_stem: str
    raw_name: str
    message: str


@dataclass(frozen=True)
class OwnerBackfillSampleJob:
    sample_index: int
    sample_stem: str
    raw_path: Path
    dll_dir: Path
    features: tuple[OwnerAlignedFeature, ...]
    alignment_config: AlignmentConfig
    peak_config: ExtractionConfig
    raw_xic_batch_size: int = 1
    owner_backfill_xic_backend: OwnerBackfillXicBackend = "raw"
    emit_region_audit: bool = False


@dataclass(frozen=True)
class OwnerBackfillTimingStats:
    sample_stem: str
    elapsed_sec: float
    extract_xic_count: int
    point_count: int
    extract_xic_batch_count: int = 0
    raw_chromatogram_call_count: int = 0


@dataclass(frozen=True)
class OwnerBackfillSampleResult:
    sample_index: int
    sample_stem: str
    cells: tuple[AlignedCell, ...]
    timing_stats: tuple[OwnerBackfillTimingStats, ...] = ()


@dataclass(frozen=True)
class OwnerBackfillProcessOutput:
    cells: tuple[AlignedCell, ...]
    timing_stats: tuple[OwnerBackfillTimingStats, ...]


@dataclass(frozen=True)
class OwnerBackfillWorkerError:
    sample_index: int
    sample_stem: str
    raw_name: str
    message: str


@dataclass(frozen=True)
class IdentityTraceSampleJob:
    sample_index: int
    sample_stem: str
    raw_path: Path
    dll_dir: Path
    requests: tuple[tuple[int, IdentityCoherenceTraceRequest], ...]
    raw_xic_batch_size: int = 1


@dataclass(frozen=True)
class IdentityTraceTimingStats:
    sample_stem: str
    elapsed_sec: float
    extract_xic_count: int
    point_count: int
    extract_xic_batch_count: int = 0
    raw_chromatogram_call_count: int = 0


@dataclass(frozen=True)
class IdentityTraceSampleResult:
    sample_index: int
    sample_stem: str
    indexed_results: tuple[tuple[int, IdentityCoherenceTraceResult], ...]
    timing_stats: tuple[IdentityTraceTimingStats, ...] = ()


@dataclass(frozen=True)
class IdentityTraceProcessOutput:
    results: tuple[IdentityCoherenceTraceResult, ...]
    timing_stats: tuple[IdentityTraceTimingStats, ...]


@dataclass(frozen=True)
class IdentityTraceWorkerError:
    sample_index: int
    sample_stem: str
    raw_name: str
    message: str


class AlignmentProcessExecutionError(RuntimeError):
    """Raised when an alignment process worker reports a failed sample job."""


OwnerBuildWorkerResult = OwnerBuildSampleResult | OwnerBuildWorkerError
OwnerBackfillWorkerResult = OwnerBackfillSampleResult | OwnerBackfillWorkerError
IdentityTraceWorkerResult = IdentityTraceSampleResult | IdentityTraceWorkerError


def run_owner_build_process(
    candidates: Sequence[Any],
    *,
    sample_order: tuple[str, ...],
    raw_paths: Mapping[str, Path],
    dll_dir: Path,
    alignment_config: AlignmentConfig,
    peak_config: ExtractionConfig,
    max_workers: int,
    raw_xic_batch_size: int = 1,
    emit_region_audit: bool = False,
    runner: Callable[..., list[OwnerBuildWorkerResult]] | None = None,
) -> OwnerBuildProcessOutput:
    if max_workers < 1:
        raise ValueError("max_workers must be >= 1")
    if raw_xic_batch_size < 1:
        raise ValueError("raw_xic_batch_size must be >= 1")
    candidates_by_sample: dict[str, list[Any]] = {}
    for candidate in candidates:
        candidates_by_sample.setdefault(
            str(candidate.sample_stem),
            [],
        ).append(candidate)

    jobs: list[OwnerBuildSampleJob] = []
    parent_results: list[OwnerBuildSampleResult] = []
    for index, sample_stem in enumerate(sample_order, start=1):
        sample_candidates = tuple(candidates_by_sample.get(sample_stem, ()))
        if not sample_candidates:
            continue
        raw_path = raw_paths.get(sample_stem)
        if raw_path is None:
            ownership = build_sample_local_owners(
                sample_candidates,
                raw_sources={},
                alignment_config=alignment_config,
                peak_config=peak_config,
                raw_xic_batch_size=raw_xic_batch_size,
                emit_region_audit=emit_region_audit,
            )
            parent_results.append(
                _owner_build_sample_result(
                    sample_index=index,
                    sample_stem=sample_stem,
                    ownership=ownership,
                    timing_stats=(),
                )
            )
            continue
        jobs.append(
            OwnerBuildSampleJob(
                sample_index=index,
                sample_stem=sample_stem,
                raw_path=raw_path,
                dll_dir=dll_dir,
                candidates=sample_candidates,
                alignment_config=alignment_config,
                peak_config=peak_config,
                raw_xic_batch_size=raw_xic_batch_size,
                emit_region_audit=emit_region_audit,
            )
        )
    active_runner = runner or run_owner_build_jobs
    worker_results = active_runner(jobs, max_workers=max_workers) if jobs else []
    return collect_owner_build_results((*parent_results, *worker_results))


def collect_owner_build_results(
    results: Iterable[OwnerBuildWorkerResult],
) -> OwnerBuildProcessOutput:
    successes: list[OwnerBuildSampleResult] = []
    errors: list[OwnerBuildWorkerError] = []
    for result in results:
        if isinstance(result, OwnerBuildWorkerError):
            errors.append(result)
        else:
            successes.append(result)
    if errors:
        messages = "; ".join(
            f"{error.raw_name}: {error.message}"
            for error in sorted(errors, key=lambda item: item.sample_index)
        )
        raise AlignmentProcessExecutionError(messages)

    unresolved_assignments = tuple(
        assignment
        for result in sorted(successes, key=lambda item: item.sample_index)
        for assignment in result.assignments
        if assignment.assignment_status == "unresolved"
    )
    sample_sorted = sorted(successes, key=lambda item: item.sample_stem)
    resolved_assignments = tuple(
        assignment
        for result in sample_sorted
        for assignment in result.assignments
        if assignment.assignment_status != "unresolved"
    )
    ownership = OwnershipBuildResult(
        owners=tuple(owner for result in sample_sorted for owner in result.owners),
        assignments=(*unresolved_assignments, *resolved_assignments),
        ambiguous_records=tuple(
            record for result in sample_sorted for record in result.ambiguous_records
        ),
    )
    timing_stats = tuple(
        stat
        for result in sorted(successes, key=lambda item: item.sample_index)
        for stat in result.timing_stats
    )
    return OwnerBuildProcessOutput(ownership=ownership, timing_stats=timing_stats)


def _owner_build_sample_result(
    *,
    sample_index: int,
    sample_stem: str,
    ownership: OwnershipBuildResult,
    timing_stats: tuple[OwnerBuildTimingStats, ...],
) -> OwnerBuildSampleResult:
    return OwnerBuildSampleResult(
        sample_index=sample_index,
        sample_stem=sample_stem,
        owners=ownership.owners,
        assignments=ownership.assignments,
        ambiguous_records=ownership.ambiguous_records,
        timing_stats=timing_stats,
    )


def run_owner_build_jobs(
    jobs: Iterable[OwnerBuildSampleJob],
    *,
    max_workers: int,
    executor_factory: Callable[..., Any] | None = None,
) -> list[OwnerBuildWorkerResult]:
    return _run_process_jobs(
        jobs,
        worker=extract_owner_build_sample_job,
        error_factory=_owner_build_worker_error,
        max_workers=max_workers,
        executor_factory=executor_factory,
    )


def extract_owner_build_sample_job(
    job: OwnerBuildSampleJob,
) -> OwnerBuildWorkerResult:
    from xic_extractor.raw_reader import open_raw

    try:
        with open_raw(job.raw_path, job.dll_dir) as raw:
            stats = _TimedProcessStats(sample_stem=job.sample_stem)
            timed_raw = _TimedProcessRawSource(raw, stats=stats)
            ownership = build_sample_local_owners(
                job.candidates,
                raw_sources={job.sample_stem: timed_raw},
                alignment_config=job.alignment_config,
                peak_config=job.peak_config,
                raw_xic_batch_size=job.raw_xic_batch_size,
                emit_region_audit=job.emit_region_audit,
            )
        return _owner_build_sample_result(
            sample_index=job.sample_index,
            sample_stem=job.sample_stem,
            ownership=ownership,
            timing_stats=(
                OwnerBuildTimingStats(
                    sample_stem=job.sample_stem,
                    elapsed_sec=stats.elapsed_sec,
                    extract_xic_count=stats.extract_xic_count,
                    point_count=stats.point_count,
                    extract_xic_batch_count=stats.extract_xic_batch_count,
                    raw_chromatogram_call_count=(
                        stats.raw_chromatogram_call_count
                    ),
                ),
            ),
        )
    except Exception as exc:
        return OwnerBuildWorkerError(
            sample_index=job.sample_index,
            sample_stem=job.sample_stem,
            raw_name=job.raw_path.name,
            message=f"{type(exc).__name__}: {exc}",
        )


def run_owner_backfill_process(
    features: tuple[OwnerAlignedFeature, ...],
    *,
    sample_order: tuple[str, ...],
    raw_paths: Mapping[str, Path],
    dll_dir: Path,
    alignment_config: AlignmentConfig,
    peak_config: ExtractionConfig,
    max_workers: int,
    raw_xic_batch_size: int = 1,
    owner_backfill_xic_backend: OwnerBackfillXicBackend = "raw",
    emit_region_audit: bool = False,
    runner: Callable[..., list[OwnerBackfillWorkerResult]] | None = None,
) -> OwnerBackfillProcessOutput:
    if max_workers < 1:
        raise ValueError("max_workers must be >= 1")
    if raw_xic_batch_size < 1:
        raise ValueError("raw_xic_batch_size must be >= 1")
    jobs = [
        OwnerBackfillSampleJob(
            sample_index=index,
            sample_stem=sample_stem,
            raw_path=raw_paths[sample_stem],
            dll_dir=dll_dir,
            features=features,
            alignment_config=alignment_config,
            peak_config=peak_config,
            raw_xic_batch_size=raw_xic_batch_size,
            owner_backfill_xic_backend=owner_backfill_xic_backend,
            emit_region_audit=emit_region_audit,
        )
        for index, sample_stem in enumerate(sample_order, start=1)
        if sample_stem in raw_paths
    ]
    if not jobs:
        return OwnerBackfillProcessOutput(cells=(), timing_stats=())
    active_runner = runner or run_owner_backfill_jobs
    results = active_runner(jobs, max_workers=max_workers)
    return collect_owner_backfill_results(
        results,
        feature_order=tuple(feature.feature_family_id for feature in features),
        sample_order=sample_order,
    )


def collect_owner_backfill_results(
    results: Iterable[OwnerBackfillWorkerResult],
    *,
    feature_order: tuple[str, ...],
    sample_order: tuple[str, ...],
) -> OwnerBackfillProcessOutput:
    successes: list[OwnerBackfillSampleResult] = []
    errors: list[OwnerBackfillWorkerError] = []
    for result in results:
        if isinstance(result, OwnerBackfillWorkerError):
            errors.append(result)
        else:
            successes.append(result)
    if errors:
        messages = "; ".join(
            f"{error.raw_name}: {error.message}"
            for error in sorted(errors, key=lambda item: item.sample_index)
        )
        raise AlignmentProcessExecutionError(messages)

    feature_rank = {feature_id: index for index, feature_id in enumerate(feature_order)}
    sample_rank = {sample_stem: index for index, sample_stem in enumerate(sample_order)}
    cells = tuple(
        sorted(
            (cell for result in successes for cell in result.cells),
            key=lambda cell: (
                feature_rank.get(cell.cluster_id, len(feature_rank)),
                sample_rank.get(cell.sample_stem, len(sample_rank)),
            ),
        )
    )
    timing_stats = tuple(
        stat
        for result in sorted(successes, key=lambda item: item.sample_index)
        for stat in result.timing_stats
    )
    return OwnerBackfillProcessOutput(cells=cells, timing_stats=timing_stats)


def run_owner_backfill_jobs(
    jobs: Iterable[OwnerBackfillSampleJob],
    *,
    max_workers: int,
    executor_factory: Callable[..., Any] | None = None,
) -> list[OwnerBackfillWorkerResult]:
    return _run_process_jobs(
        jobs,
        worker=extract_owner_backfill_sample_job,
        error_factory=_owner_backfill_worker_error,
        max_workers=max_workers,
        executor_factory=executor_factory,
    )


def run_identity_trace_process(
    requests: Sequence[IdentityCoherenceTraceRequest],
    *,
    raw_paths: Mapping[str, Path],
    dll_dir: Path,
    max_workers: int,
    raw_xic_batch_size: int = 1,
    runner: Callable[..., list[IdentityTraceWorkerResult]] | None = None,
) -> IdentityTraceProcessOutput:
    if max_workers < 1:
        raise ValueError("max_workers must be >= 1")
    if raw_xic_batch_size < 1:
        raise ValueError("raw_xic_batch_size must be >= 1")

    indexed_requests = tuple(enumerate(requests))
    grouped: dict[str, list[tuple[int, IdentityCoherenceTraceRequest]]] = {}
    for index, request in indexed_requests:
        grouped.setdefault(request.sample_id, []).append((index, request))

    jobs: list[IdentityTraceSampleJob] = []
    parent_results: list[IdentityTraceSampleResult] = []
    for sample_index, sample_stem in enumerate(sorted(grouped), start=1):
        sample_requests = tuple(grouped[sample_stem])
        raw_path = raw_paths.get(sample_stem)
        if raw_path is None:
            parent_results.append(
                IdentityTraceSampleResult(
                    sample_index=sample_index,
                    sample_stem=sample_stem,
                    indexed_results=tuple(
                        (
                            index,
                            _identity_trace_blocked_result(
                                request,
                                "missing_raw_source",
                            ),
                        )
                        for index, request in sample_requests
                    ),
                )
            )
            continue
        jobs.append(
            IdentityTraceSampleJob(
                sample_index=sample_index,
                sample_stem=sample_stem,
                raw_path=raw_path,
                dll_dir=dll_dir,
                requests=sample_requests,
                raw_xic_batch_size=raw_xic_batch_size,
            )
        )

    active_runner = runner or run_identity_trace_jobs
    worker_results = active_runner(jobs, max_workers=max_workers) if jobs else []
    return collect_identity_trace_results(
        (*parent_results, *worker_results),
        request_count=len(indexed_requests),
    )


def run_identity_trace_jobs(
    jobs: Iterable[IdentityTraceSampleJob],
    *,
    max_workers: int,
    executor_factory: Callable[..., Any] | None = None,
) -> list[IdentityTraceWorkerResult]:
    return _run_process_jobs(
        jobs,
        worker=extract_identity_trace_sample_job,
        error_factory=_identity_trace_worker_error,
        max_workers=max_workers,
        executor_factory=executor_factory,
    )


def collect_identity_trace_results(
    results: Iterable[IdentityTraceWorkerResult],
    *,
    request_count: int,
) -> IdentityTraceProcessOutput:
    successes: list[IdentityTraceSampleResult] = []
    errors: list[IdentityTraceWorkerError] = []
    for result in results:
        if isinstance(result, IdentityTraceWorkerError):
            errors.append(result)
        else:
            successes.append(result)
    if errors:
        messages = "; ".join(
            f"{error.raw_name}: {error.message}"
            for error in sorted(errors, key=lambda item: item.sample_index)
        )
        raise AlignmentProcessExecutionError(messages)

    indexed: list[tuple[int, IdentityCoherenceTraceResult]] = [
        item for result in successes for item in result.indexed_results
    ]
    indexed.sort(key=lambda item: item[0])
    if [index for index, _result in indexed] != list(range(request_count)):
        raise AlignmentProcessExecutionError("identity trace results are incomplete")
    timing_stats = tuple(
        stat
        for result in sorted(successes, key=lambda item: item.sample_index)
        for stat in result.timing_stats
    )
    return IdentityTraceProcessOutput(
        results=tuple(result for _index, result in indexed),
        timing_stats=timing_stats,
    )


def _run_process_jobs(
    jobs: Iterable[Any],
    *,
    worker: Callable[[Any], Any],
    error_factory: Callable[[Any, Exception], Any],
    max_workers: int,
    executor_factory: Callable[..., Any] | None = None,
) -> list[Any]:
    pending_jobs = list(jobs)
    for job in pending_jobs:
        validate_process_job_payload(job)
    if not pending_jobs:
        return []
    context = get_context("spawn")
    factory = executor_factory or ProcessPoolExecutor
    results: list[Any] = []
    next_job_index = 0
    worker_count = min(max_workers, len(pending_jobs))

    with factory(max_workers=worker_count, mp_context=context) as executor:
        future_to_job: dict[Any, Any] = {}

        def _submit_until_capacity() -> None:
            nonlocal next_job_index
            while (
                len(future_to_job) < worker_count
                and next_job_index < len(pending_jobs)
            ):
                job = pending_jobs[next_job_index]
                next_job_index += 1
                try:
                    future = executor.submit(worker, job)
                except Exception as exc:
                    results.append(error_factory(job, exc))
                    continue
                future_to_job[future] = job

        _submit_until_capacity()
        while future_to_job:
            done, _not_done = wait(
                future_to_job,
                timeout=0.1,
                return_when=FIRST_COMPLETED,
            )
            if not done:
                continue
            for future in done:
                job = future_to_job.pop(future)
                _submit_until_capacity()
                try:
                    results.append(future.result())
                except Exception as exc:
                    results.append(error_factory(job, exc))
    return results


def _owner_build_worker_error(
    job: OwnerBuildSampleJob,
    exc: Exception,
) -> OwnerBuildWorkerError:
    return OwnerBuildWorkerError(
        sample_index=job.sample_index,
        sample_stem=job.sample_stem,
        raw_name=job.raw_path.name,
        message=f"{type(exc).__name__}: {exc}",
    )


def _owner_backfill_worker_error(
    job: OwnerBackfillSampleJob,
    exc: Exception,
) -> OwnerBackfillWorkerError:
    return OwnerBackfillWorkerError(
        sample_index=job.sample_index,
        sample_stem=job.sample_stem,
        raw_name=job.raw_path.name,
        message=f"{type(exc).__name__}: {exc}",
    )


def extract_owner_backfill_sample_job(
    job: OwnerBackfillSampleJob,
) -> OwnerBackfillWorkerResult:
    from xic_extractor.raw_reader import open_raw

    try:
        with open_raw(job.raw_path, job.dll_dir) as raw:
            stats = _TimedProcessStats(sample_stem=job.sample_stem)
            source = source_for_owner_backfill_backend(
                raw,
                job.owner_backfill_xic_backend,
            )
            timed_raw = _TimedProcessRawSource(source, stats=stats)
            validation_raw_sources = (
                {job.sample_stem: _TimedProcessRawSource(raw, stats=stats)}
                if job.owner_backfill_xic_backend == "ms1_index_hybrid"
                else None
            )
            validation_kwargs = (
                {"validation_raw_sources": validation_raw_sources}
                if validation_raw_sources is not None
                else {}
            )
            cells = build_owner_backfill_cells(
                job.features,
                sample_order=(job.sample_stem,),
                raw_sources={job.sample_stem: timed_raw},
                **validation_kwargs,
                alignment_config=job.alignment_config,
                peak_config=job.peak_config,
                raw_xic_batch_size=job.raw_xic_batch_size,
                emit_region_audit=job.emit_region_audit,
            )
        return OwnerBackfillSampleResult(
            sample_index=job.sample_index,
            sample_stem=job.sample_stem,
            cells=cells,
            timing_stats=(
                OwnerBackfillTimingStats(
                    sample_stem=job.sample_stem,
                    elapsed_sec=stats.elapsed_sec,
                    extract_xic_count=stats.extract_xic_count,
                    point_count=stats.point_count,
                    extract_xic_batch_count=stats.extract_xic_batch_count,
                    raw_chromatogram_call_count=(
                        stats.raw_chromatogram_call_count
                    ),
                ),
            ),
        )
    except Exception as exc:
        return OwnerBackfillWorkerError(
            sample_index=job.sample_index,
            sample_stem=job.sample_stem,
            raw_name=job.raw_path.name,
            message=f"{type(exc).__name__}: {exc}",
        )


def extract_identity_trace_sample_job(
    job: IdentityTraceSampleJob,
) -> IdentityTraceWorkerResult:
    from xic_extractor.raw_reader import open_raw

    stats = _TimedProcessStats(sample_stem=job.sample_stem)
    try:
        raw_context = open_raw(job.raw_path, job.dll_dir)
        raw = raw_context.__enter__()
    except Exception:
        indexed_results = tuple(
            (
                index,
                _identity_trace_blocked_result(
                    request,
                    "raw_xic_extraction_error",
                    raw_xic_request_count=1,
                ),
            )
            for index, request in job.requests
        )
    else:
        exc_info = (None, None, None)
        try:
            timed_raw = _TimedProcessRawSource(raw, stats=stats)
            indexed_results = _extract_identity_trace_results_for_sample(
                job.requests,
                timed_raw,
                raw_xic_batch_size=job.raw_xic_batch_size,
            )
        except BaseException as error:
            exc_info = (type(error), error, error.__traceback__)
            raise
        finally:
            raw_context.__exit__(*exc_info)

    return IdentityTraceSampleResult(
        sample_index=job.sample_index,
        sample_stem=job.sample_stem,
        indexed_results=indexed_results,
        timing_stats=(
            IdentityTraceTimingStats(
                sample_stem=job.sample_stem,
                elapsed_sec=stats.elapsed_sec,
                extract_xic_count=stats.extract_xic_count,
                point_count=stats.point_count,
                extract_xic_batch_count=stats.extract_xic_batch_count,
                raw_chromatogram_call_count=stats.raw_chromatogram_call_count,
            ),
        ),
    )


def _extract_identity_trace_results_for_sample(
    indexed_requests: tuple[tuple[int, IdentityCoherenceTraceRequest], ...],
    timed_raw: _TimedProcessRawSource,
    *,
    raw_xic_batch_size: int,
) -> tuple[tuple[int, IdentityCoherenceTraceResult], ...]:
    indexed_results: list[tuple[int, IdentityCoherenceTraceResult]] = []
    for chunk in _chunked(indexed_requests, raw_xic_batch_size):
        xic_requests = tuple(
            _identity_trace_to_xic_request(request) for _, request in chunk
        )
        try:
            traces = tuple(timed_raw.extract_xic_many(xic_requests))
        except Exception:
            indexed_results.extend(
                (
                    index,
                    _identity_trace_blocked_result(
                        request,
                        "raw_xic_extraction_error",
                        raw_xic_request_count=1,
                    ),
                )
                for index, request in chunk
            )
            continue
        for (index, request), xic_trace in zip(chunk, traces, strict=True):
            try:
                trace = CandidateTrace(
                    rt_min=tuple(float(value) for value in xic_trace.rt),
                    intensity=tuple(float(value) for value in xic_trace.intensity),
                )
            except (TypeError, ValueError):
                result = _identity_trace_data_quality_result(
                    request,
                    "invalid_trace_payload",
                )
            else:
                result = IdentityCoherenceTraceResult(
                    request=request,
                    trace=trace,
                    status="pass",
                    raw_xic_request_count=1,
                    xic_point_count=len(trace.rt_min),
                )
            indexed_results.append((index, result))
    return tuple(indexed_results)


def _identity_trace_to_xic_request(
    request: IdentityCoherenceTraceRequest,
) -> XICRequest:
    return XICRequest(
        mz=request.precursor_mz,
        rt_min=request.rt_min,
        rt_max=request.rt_max,
        ppm_tol=request.ppm_tolerance,
    )


def _identity_trace_blocked_result(
    request: IdentityCoherenceTraceRequest,
    blocked_reason: str,
    *,
    raw_xic_request_count: int = 0,
) -> IdentityCoherenceTraceResult:
    return IdentityCoherenceTraceResult(
        request=request,
        trace=None,
        status="blocked_infrastructure",
        blocked_reason=blocked_reason,
        raw_xic_request_count=raw_xic_request_count,
    )


def _identity_trace_data_quality_result(
    request: IdentityCoherenceTraceRequest,
    reason: str,
) -> IdentityCoherenceTraceResult:
    return IdentityCoherenceTraceResult(
        request=request,
        trace=None,
        status="data_quality_reject",
        blocked_reason=reason,
        raw_xic_request_count=1,
    )


def _identity_trace_worker_error(
    job: IdentityTraceSampleJob,
    exc: Exception,
) -> IdentityTraceWorkerError:
    return IdentityTraceWorkerError(
        sample_index=job.sample_index,
        sample_stem=job.sample_stem,
        raw_name=job.raw_path.name,
        message=f"{type(exc).__name__}: {exc}",
    )


def _chunked(
    values: Sequence[Any],
    size: int,
) -> Iterable[tuple[Any, ...]]:
    if size < 1:
        raise ValueError("size must be >= 1")
    for index in range(0, len(values), size):
        yield tuple(values[index : index + size])


def validate_owner_backfill_job_payload(job: OwnerBackfillSampleJob) -> None:
    validate_process_job_payload(job)


def validate_process_job_payload(job: Any) -> None:
    _validate_payload_value(job, path="job")
    try:
        pickle.dumps(job)
    except Exception as exc:
        raise TypeError(f"job payload is not pickleable: {exc}") from exc


@dataclass
class _TimedProcessStats:
    sample_stem: str
    elapsed_sec: float = 0.0
    extract_xic_count: int = 0
    extract_xic_batch_count: int = 0
    raw_chromatogram_call_count: int = 0
    point_count: int = 0


class _TimedProcessRawSource:
    def __init__(
        self,
        source: Any,
        *,
        stats: _TimedProcessStats,
        timer: Callable[[], float] = perf_counter,
    ) -> None:
        self._source = source
        self._stats = stats
        self._timer = timer

    def extract_xic(self, mz: float, rt_min: float, rt_max: float, ppm_tol: float):
        raw_call_count_before = _raw_chromatogram_call_count(self._source)
        start = self._timer()
        try:
            rt, intensity = self._source.extract_xic(mz, rt_min, rt_max, ppm_tol)
        finally:
            self._stats.extract_xic_count += 1
            self._stats.extract_xic_batch_count += 1
            self._stats.elapsed_sec += self._timer() - start
            self._stats.raw_chromatogram_call_count += _raw_call_delta(
                raw_call_count_before,
                _raw_chromatogram_call_count(self._source),
            )
        self._stats.point_count += _trace_point_count(rt)
        return rt, intensity

    def extract_xic_many(self, requests):
        requests = tuple(requests)
        if hasattr(self._source, "extract_xic_many"):
            raw_call_count_before = _raw_chromatogram_call_count(self._source)
            start = self._timer()
            try:
                traces = tuple(self._source.extract_xic_many(requests))
            finally:
                self._stats.elapsed_sec += self._timer() - start
            self._stats.extract_xic_count += len(requests)
            self._stats.extract_xic_batch_count += 1 if requests else 0
            self._stats.raw_chromatogram_call_count += _raw_call_delta(
                raw_call_count_before,
                _raw_chromatogram_call_count(self._source),
            )
            self._stats.point_count += sum(len(trace.intensity) for trace in traces)
            return traces

        traces: list[XICTrace] = []
        for request in requests:
            rt, intensity = self.extract_xic(
                request.mz,
                request.rt_min,
                request.rt_max,
                request.ppm_tol,
            )
            traces.append(XICTrace.from_arrays(rt, intensity))
        return tuple(traces)

    def scan_window_for_request(self, request):
        return self._source.scan_window_for_request(request)


def _trace_point_count(trace: object) -> int:
    try:
        return len(trace)  # type: ignore[arg-type]
    except TypeError:
        return 0


def _raw_chromatogram_call_count(source: object) -> int | None:
    value = getattr(source, "raw_chromatogram_call_count", None)
    if isinstance(value, int):
        return value
    return None


def _raw_call_delta(before: int | None, after: int | None) -> int:
    if before is None or after is None:
        return 0
    return max(0, after - before)


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
