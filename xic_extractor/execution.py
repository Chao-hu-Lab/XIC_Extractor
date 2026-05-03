from __future__ import annotations

import io
import pickle
from collections.abc import Iterable
from dataclasses import dataclass, fields, is_dataclass
from pathlib import Path
from types import ModuleType
from typing import Any

from xic_extractor.config import ExtractionConfig, Target
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
