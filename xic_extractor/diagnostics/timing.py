from __future__ import annotations

import json
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

JsonMetric = str | int | float | bool | None


@dataclass(frozen=True)
class TimingRecord:
    stage: str
    elapsed_sec: float
    sample_stem: str = ""
    metrics: dict[str, JsonMetric] = field(default_factory=dict)

    def to_json_dict(self) -> dict[str, object]:
        return {
            "sample_stem": self.sample_stem,
            "stage": self.stage,
            "elapsed_sec": self.elapsed_sec,
            "metrics": dict(self.metrics),
        }


@dataclass
class TimingStage:
    metrics: dict[str, JsonMetric] = field(default_factory=dict)


class TimingRecorder:
    def __init__(
        self,
        pipeline: str,
        *,
        run_id: str | None = None,
        enabled: bool = True,
        timer: Callable[[], float] = perf_counter,
    ) -> None:
        self.pipeline = pipeline
        self.run_id = run_id or _default_run_id()
        self.enabled = enabled
        self._timer = timer
        self._records: list[TimingRecord] = []

    @classmethod
    def disabled(
        cls,
        pipeline: str,
        *,
        timer: Callable[[], float] = perf_counter,
    ) -> TimingRecorder:
        return cls(pipeline, enabled=False, timer=timer)

    @property
    def records(self) -> tuple[TimingRecord, ...]:
        return tuple(self._records)

    def record(
        self,
        stage: str,
        *,
        elapsed_sec: float,
        sample_stem: str = "",
        metrics: Mapping[str, object] | None = None,
    ) -> None:
        if not self.enabled:
            return
        self._records.append(
            TimingRecord(
                stage=stage,
                elapsed_sec=max(0.0, elapsed_sec),
                sample_stem=sample_stem,
                metrics=_clean_metrics(metrics or {}),
            )
        )

    @contextmanager
    def stage(
        self,
        stage: str,
        *,
        sample_stem: str = "",
        metrics: Mapping[str, object] | None = None,
    ) -> Iterator[TimingStage]:
        scope = TimingStage(_clean_metrics(metrics or {}))
        if not self.enabled:
            yield scope
            return

        start = self._timer()
        try:
            yield scope
        finally:
            elapsed = self._timer() - start
            self._records.append(
                TimingRecord(
                    stage=stage,
                    elapsed_sec=max(0.0, elapsed),
                    sample_stem=sample_stem,
                    metrics=_clean_metrics(scope.metrics),
                )
            )

    def write_json(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "run_id": self.run_id,
            "pipeline": self.pipeline,
            "records": [record.to_json_dict() for record in self._records],
        }
        path.write_text(
            json.dumps(payload, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        return path


def _clean_metrics(metrics: Mapping[str, object]) -> dict[str, JsonMetric]:
    return {str(key): _clean_metric(value) for key, value in metrics.items()}


def _clean_metric(value: object) -> JsonMetric:
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    return str(value)


def _default_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
