from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from xic_extractor.tabular_io import text_value


@dataclass(frozen=True)
class TimingRecordView:
    stage: str
    elapsed_sec: float
    sample_stem: str = ""
    metrics: Mapping[str, object] | None = None


def summarize_timing_records(
    records: Iterable[object],
) -> dict[str, object]:
    """Build no-RAW timing and XIC locality summaries from recorded spans."""

    views = tuple(_record_view(record) for record in records)
    return {
        "stage_summary": _stage_summary(views),
        "raw_xic_locality_summary": _raw_xic_locality_summary(views),
    }


def _stage_summary(
    records: tuple[TimingRecordView, ...],
) -> list[dict[str, object]]:
    by_stage: dict[str, list[TimingRecordView]] = defaultdict(list)
    for record in records:
        by_stage[record.stage].append(record)
    rows: list[dict[str, object]] = []
    for stage, stage_records in by_stage.items():
        elapsed_values = [record.elapsed_sec for record in stage_records]
        sample_stems = {
            record.sample_stem for record in stage_records if record.sample_stem
        }
        rows.append(
            {
                "stage": stage,
                "record_count": len(stage_records),
                "sample_count": len(sample_stems),
                "total_elapsed_sec": sum(elapsed_values),
                "max_elapsed_sec": max(elapsed_values, default=0.0),
            }
        )
    return sorted(
        rows,
        key=_summary_sort_key,
    )


def _raw_xic_locality_summary(
    records: tuple[TimingRecordView, ...],
) -> list[dict[str, object]]:
    by_stage: dict[str, list[TimingRecordView]] = defaultdict(list)
    for record in records:
        metrics = record.metrics or {}
        if any(
            _int_metric(metrics, field)
            for field in (
                "extract_xic_count",
                "extract_xic_batch_count",
                "raw_chromatogram_call_count",
                "point_count",
            )
        ):
            by_stage[record.stage].append(record)

    rows: list[dict[str, object]] = []
    for stage, stage_records in by_stage.items():
        extract_xic_count = _sum_metric(stage_records, "extract_xic_count")
        extract_xic_batch_count = _sum_metric(
            stage_records,
            "extract_xic_batch_count",
        )
        raw_call_count = _sum_metric(stage_records, "raw_chromatogram_call_count")
        point_count = _sum_metric(stage_records, "point_count")
        elapsed_sec = sum(record.elapsed_sec for record in stage_records)
        rows.append(
            {
                "stage": stage,
                "record_count": len(stage_records),
                "total_elapsed_sec": elapsed_sec,
                "extract_xic_count": extract_xic_count,
                "extract_xic_batch_count": extract_xic_batch_count,
                "raw_chromatogram_call_count": raw_call_count,
                "point_count": point_count,
                "raw_calls_per_xic": _ratio_or_none(
                    raw_call_count,
                    extract_xic_count,
                ),
                "mean_xic_per_raw_chromatogram_call": (
                    None if raw_call_count == 0 else extract_xic_count / raw_call_count
                ),
                "mean_xic_per_extract_batch": (
                    None
                    if extract_xic_batch_count == 0
                    else extract_xic_count / extract_xic_batch_count
                ),
            }
        )
    return sorted(
        rows,
        key=_summary_sort_key,
    )


def _summary_sort_key(row: Mapping[str, object]) -> tuple[float, str]:
    return (-_float_value(row.get("total_elapsed_sec")), text_value(row.get("stage")))


def _ratio_or_none(numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return numerator / denominator


def _sum_metric(records: Iterable[TimingRecordView], field: str) -> int:
    return sum(_int_metric(record.metrics or {}, field) for record in records)


def _int_metric(metrics: Mapping[str, object], field: str) -> int:
    value = metrics.get(field)
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    text = text_value(value)
    if not text:
        return 0
    try:
        return int(float(text))
    except ValueError:
        return 0


def _record_view(record: object) -> TimingRecordView:
    if isinstance(record, Mapping):
        return TimingRecordView(
            stage=text_value(record.get("stage")),
            elapsed_sec=_float_value(record.get("elapsed_sec")),
            sample_stem=text_value(record.get("sample_stem")),
            metrics=_mapping_or_empty(record.get("metrics")),
        )
    return TimingRecordView(
        stage=text_value(getattr(record, "stage", "")),
        elapsed_sec=_float_value(getattr(record, "elapsed_sec", 0.0)),
        sample_stem=text_value(getattr(record, "sample_stem", "")),
        metrics=_mapping_or_empty(getattr(record, "metrics", {})),
    )


def _mapping_or_empty(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


def _float_value(value: object) -> float:
    if isinstance(value, bool):
        return 0.0
    if isinstance(value, int | float):
        return float(value)
    try:
        return float(text_value(value))
    except ValueError:
        return 0.0
