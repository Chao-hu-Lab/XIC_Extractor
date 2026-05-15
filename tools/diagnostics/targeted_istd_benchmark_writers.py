"""Output writers for the targeted ISTD benchmark diagnostic."""

from __future__ import annotations

import csv
import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import asdict
from typing import Any

SUMMARY_COLUMNS = (
    "target_label",
    "role",
    "active_tag",
    "neutral_loss_da",
    "target_mz",
    "target_rt_min",
    "target_rt_max",
    "targeted_positive_count",
    "targeted_total_count",
    "targeted_mean_rt",
    "candidate_match_count",
    "primary_match_count",
    "primary_feature_ids",
    "selected_feature_id",
    "untargeted_positive_count",
    "coverage_minimum",
    "paired_area_n",
    "log_area_pearson",
    "log_area_spearman",
    "family_mean_rt_delta_min",
    "sample_rt_pair_n",
    "sample_rt_median_abs_delta_min",
    "sample_rt_p95_abs_delta_min",
    "status",
    "failure_modes",
    "note",
)

MATCH_COLUMNS = (
    "target_label",
    "feature_family_id",
    "include_in_primary_matrix",
    "family_center_mz",
    "family_center_rt",
    "family_product_mz",
    "family_observed_neutral_loss_da",
    "mz_delta_ppm",
    "rt_delta_sec",
    "product_delta_ppm",
    "loss_delta_da",
    "mass_shift_da",
    "match_type",
    "distance_score",
)


def write_benchmark_outputs(
    outputs: Any,
    *,
    summaries: Sequence[Any],
    matches: Sequence[Any],
    thresholds: Any,
) -> None:
    _write_tsv(outputs.summary_tsv, SUMMARY_COLUMNS, _summary_rows(summaries))
    _write_tsv(outputs.matches_tsv, MATCH_COLUMNS, _match_rows(matches))
    _write_json(outputs.json_path, _json_payload(summaries, thresholds))
    _write_markdown(outputs.markdown_path, summaries)


def _summary_rows(summaries: Sequence[Any]) -> list[dict[str, object]]:
    return [
        {
            **asdict(summary),
            "active_tag": _bool_text(summary.active_tag),
            "primary_feature_ids": ";".join(summary.primary_feature_ids),
            "failure_modes": ";".join(summary.failure_modes),
        }
        for summary in summaries
    ]


def _match_rows(matches: Sequence[Any]) -> list[dict[str, object]]:
    return [asdict(match) for match in matches]


def _json_payload(
    summaries: Sequence[Any],
    thresholds: Any,
) -> dict[str, object]:
    fail_count = sum(summary.status == "FAIL" for summary in summaries)
    active_fail_count = sum(
        summary.status == "FAIL" and summary.active_tag
        for summary in summaries
    )
    false_positive_tag_count = sum(
        "FALSE_POSITIVE_TAG" in summary.failure_modes
        for summary in summaries
    )
    return {
        "overall_status": "FAIL" if fail_count else "PASS",
        "fail_count": fail_count,
        "active_fail_count": active_fail_count,
        "false_positive_tag_count": false_positive_tag_count,
        "thresholds": asdict(thresholds),
        "summaries": _summary_rows(summaries),
    }


def _write_markdown(path: Any, summaries: Sequence[Any]) -> None:
    fail_count = sum(summary.status == "FAIL" for summary in summaries)
    lines = [
        "# Targeted ISTD Benchmark",
        "",
        f"Overall status: {'FAIL' if fail_count else 'PASS'}",
        "",
        "| Target | Active | Primary hits | Selected | Status | Failure modes |",
        "|---|---:|---:|---|---|---|",
    ]
    for summary in summaries:
        lines.append(
            "| "
            f"{summary.target_label} | "
            f"{_bool_text(summary.active_tag)} | "
            f"{summary.primary_match_count} | "
            f"{summary.selected_feature_id} | "
            f"{summary.status} | "
            f"{';'.join(summary.failure_modes)} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_json(path: Any, payload: Mapping[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _write_tsv(
    path: Any,
    fieldnames: Sequence[str],
    rows: Sequence[Mapping[str, object]],
) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {key: _format_value(row.get(key, "")) for key in fieldnames}
            )


def _format_value(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return _bool_text(value)
    if isinstance(value, float):
        if math.isnan(value):
            return ""
        return f"{value:.6g}"
    return str(value)


def _bool_text(value: bool) -> str:
    return "TRUE" if value else "FALSE"
