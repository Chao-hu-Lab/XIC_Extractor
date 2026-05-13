from __future__ import annotations

import csv
import math
from dataclasses import asdict
from pathlib import Path
from typing import Any, Sequence

from xic_extractor.alignment.validation_compare import FeatureMatch, SummaryMetric

SUMMARY_COLUMNS = ("source", "metric", "value", "threshold", "status", "note")

MATCH_COLUMNS = (
    "source",
    "xic_cluster_id",
    "legacy_feature_id",
    "xic_mz",
    "legacy_mz",
    "mz_delta_ppm",
    "xic_rt",
    "legacy_rt",
    "rt_delta_sec",
    "distance_score",
    "shared_sample_count",
    "xic_present_count",
    "legacy_present_count",
    "both_present_count",
    "xic_only_count",
    "legacy_only_count",
    "both_missing_count",
    "present_jaccard",
    "log_area_pearson",
    "status",
    "note",
)


def write_validation_summary_tsv(
    path: Path,
    metrics: Sequence[SummaryMetric],
) -> Path:
    return _write_tsv(path, SUMMARY_COLUMNS, [asdict(metric) for metric in metrics])


def write_legacy_matches_tsv(
    path: Path,
    matches: Sequence[FeatureMatch],
) -> Path:
    return _write_tsv(path, MATCH_COLUMNS, [asdict(match) for match in matches])


def _write_tsv(
    path: Path,
    columns: tuple[str, ...],
    rows: list[dict[str, Any]],
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, delimiter="\t")
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {column: _format_value(row.get(column)) for column in columns}
            )
    return path


def _format_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            return ""
        return f"{value:.6g}"
    return _escape_tsv_text(str(value))


def _escape_tsv_text(value: str) -> str:
    if value.startswith(("=", "+", "-", "@")):
        return f"'{value}"
    return value
