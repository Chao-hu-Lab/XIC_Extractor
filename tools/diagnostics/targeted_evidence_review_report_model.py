"""Report model assembly for targeted evidence human review HTML."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from tools.diagnostics.alignment_decision_report_io import read_tsv

_RELIABILITY_SUMMARY_COLUMNS = (
    "target_label",
    "role",
    "benchmark_eligible_count",
    "targeted_review_positive_count",
    "targeted_review_count",
    "targeted_negative_count",
    "top_risk_reasons",
    "known_exception",
)
_RELIABILITY_ROWS_COLUMNS = (
    "sample_name",
    "target_label",
    "reliability_state",
    "risk_reasons",
    "area_to_target_median_ratio",
)
_ROOT_SUMMARY_COLUMNS = (
    "rows_checked",
    "review_positive_count",
    "included_count",
    "missing_candidate_count",
    "bucket_counts",
    "target_counts",
    "product_absence_reason_counts",
)
_ROOT_ROWS_COLUMNS = (
    "sample_name",
    "target_label",
    "target_mz",
    "reliability_state",
    "targeted_risk_reasons",
    "apex_ms2_delta_min",
    "best_loss_ppm",
    "nearest_product_loss_ppm",
    "root_cause_bucket",
    "root_cause_reason",
)
_CROSS_SUMMARY_COLUMNS = (
    "rows_checked",
    "consistent_count",
    "mismatch_count",
    "missing_candidate_count",
    "missing_reliability_count",
    "issue_counts",
)
_CROSS_ROWS_COLUMNS = (
    "sample_name",
    "target_label",
    "target_mz",
    "reliability_state",
    "targeted_risk_reasons",
    "targeted_area_to_median_ratio",
    "consistency_status",
    "issue_type",
    "reason",
)

_SOURCE_ROOT_ROWS = "targeted_nl_dropout_root_cause_rows.tsv"
_SOURCE_RELIABILITY_ROWS = "targeted_peak_reliability_rows.tsv"
_SOURCE_CROSS_ROWS = "cross_report_evidence_consistency_rows.tsv"


def build_report(
    *,
    targeted_reliability_summary_tsv: Path,
    targeted_reliability_rows_tsv: Path,
    root_cause_summary_tsv: Path,
    root_cause_rows_tsv: Path,
    cross_report_summary_tsv: Path,
    cross_report_rows_tsv: Path | None = None,
    run_label: str = "",
) -> dict[str, Any]:
    reliability_summary = read_tsv(
        targeted_reliability_summary_tsv,
        required_columns=_RELIABILITY_SUMMARY_COLUMNS,
    )
    reliability_rows = read_tsv(
        targeted_reliability_rows_tsv,
        required_columns=_RELIABILITY_ROWS_COLUMNS,
    )
    root_summary_table = read_tsv(
        root_cause_summary_tsv,
        required_columns=_ROOT_SUMMARY_COLUMNS,
    )
    root_rows = read_tsv(root_cause_rows_tsv, required_columns=_ROOT_ROWS_COLUMNS)
    cross_summary_table = read_tsv(
        cross_report_summary_tsv,
        required_columns=_CROSS_SUMMARY_COLUMNS,
    )
    cross_rows = (
        read_tsv(cross_report_rows_tsv, required_columns=_CROSS_ROWS_COLUMNS)
        if cross_report_rows_tsv is not None
        else None
    )

    root_summary = _first_row(root_summary_table.rows, root_cause_summary_tsv)
    cross_summary = _first_row(cross_summary_table.rows, cross_report_summary_tsv)
    reliability_targets = _target_reliability(reliability_summary.rows)
    root_cause = _root_cause_summary(root_summary, root_rows.rows)
    consistency = _consistency_summary(
        cross_summary,
        cross_rows.rows if cross_rows else (),
    )
    queue = _review_queue(
        reliability_rows=reliability_rows.rows,
        root_rows=root_rows.rows,
        cross_rows=cross_rows.rows if cross_rows else (),
    )
    verdict, verdict_message = _verdict(
        reliability_targets=reliability_targets,
        root_summary=root_summary,
        consistency=consistency,
    )
    return {
        "title": "Targeted Evidence Decision Report",
        "run_label": run_label,
        "verdict": verdict,
        "verdict_message": verdict_message,
        "sources": {
            "targeted_reliability_summary_tsv": str(targeted_reliability_summary_tsv),
            "targeted_reliability_rows_tsv": str(targeted_reliability_rows_tsv),
            "root_cause_summary_tsv": str(root_cause_summary_tsv),
            "root_cause_rows_tsv": str(root_cause_rows_tsv),
            "cross_report_summary_tsv": str(cross_report_summary_tsv),
            "cross_report_rows_tsv": str(cross_report_rows_tsv or ""),
        },
        "summary": _report_summary(reliability_targets, root_summary),
        "target_reliability": reliability_targets,
        "root_cause": root_cause,
        "consistency": consistency,
        "review_queue": queue[:30],
    }


def _target_reliability(rows: tuple[dict[str, str], ...]) -> list[dict[str, Any]]:
    targets: list[dict[str, Any]] = []
    for row in rows:
        eligible = _int_value(row["benchmark_eligible_count"])
        review_positive = _int_value(row["targeted_review_positive_count"])
        review = _int_value(row["targeted_review_count"])
        negative = _int_value(row["targeted_negative_count"])
        targets.append(
            {
                "target_label": row["target_label"],
                "role": row.get("role", ""),
                "benchmark_eligible_count": eligible,
                "targeted_review_positive_count": review_positive,
                "targeted_review_count": review,
                "targeted_negative_count": negative,
                "top_risk_reasons": row.get("top_risk_reasons", ""),
                "known_exception": row.get("known_exception", ""),
                "review_burden": review_positive + review,
            }
        )
    targets.sort(
        key=lambda item: (
            -int(item["review_burden"]),
            -int(item["targeted_review_positive_count"]),
            str(item["target_label"]),
        )
    )
    return targets


def _report_summary(
    reliability_targets: list[dict[str, Any]],
    root_summary: dict[str, str],
) -> dict[str, int]:
    eligible_count = 0
    review_positive_count = 0
    review_count = 0
    negative_count = 0
    for target in reliability_targets:
        eligible_count += int(target["benchmark_eligible_count"])
        review_positive_count += int(target["targeted_review_positive_count"])
        review_count += int(target["targeted_review_count"])
        negative_count += int(target["targeted_negative_count"])
    return {
        "eligible_count": eligible_count,
        "review_positive_count": review_positive_count,
        "review_count": review_count,
        "negative_count": negative_count,
        "root_cause_included_count": _int_value(root_summary.get("included_count", "")),
    }


def _root_cause_summary(
    summary: dict[str, str],
    rows: tuple[dict[str, str], ...],
) -> dict[str, Any]:
    bucket_counts = _parse_count_map(summary.get("bucket_counts", ""))
    target_counts = _parse_count_map(summary.get("target_counts", ""))
    top_targets = sorted(
        target_counts.items(),
        key=lambda item: (-item[1], item[0]),
    )[:10]
    return {
        "rows_checked": _int_value(summary.get("rows_checked", "")),
        "review_positive_count": _int_value(
            summary.get("review_positive_count", "")
        ),
        "included_count": _int_value(summary.get("included_count", "")),
        "missing_candidate_count": _int_value(
            summary.get("missing_candidate_count", "")
        ),
        "bucket_counts": dict(
            sorted(
                bucket_counts.items(),
                key=lambda item: (_root_priority(item[0]), item[0]),
            )
        ),
        "top_targets": top_targets,
        "row_count": len(rows),
    }


def _consistency_summary(
    summary: dict[str, str],
    rows: tuple[dict[str, str], ...],
) -> dict[str, Any]:
    issue_counts = _parse_count_map(summary.get("issue_counts", ""))
    mismatch_rows = [
        row
        for row in rows
        if row.get("consistency_status", "") != "consistent"
        or row.get("issue_type", "")
    ]
    return {
        "rows_checked": _int_value(summary.get("rows_checked", "")),
        "consistent_count": _int_value(summary.get("consistent_count", "")),
        "mismatch_count": _int_value(summary.get("mismatch_count", "")),
        "missing_candidate_count": _int_value(
            summary.get("missing_candidate_count", "")
        ),
        "missing_reliability_count": _int_value(
            summary.get("missing_reliability_count", "")
        ),
        "issue_counts": issue_counts,
        "mismatch_rows": mismatch_rows[:30],
    }


def _review_queue(
    *,
    reliability_rows: tuple[dict[str, str], ...],
    root_rows: tuple[dict[str, str], ...],
    cross_rows: tuple[dict[str, str], ...],
) -> list[dict[str, Any]]:
    reliability_by_key = {
        (row["sample_name"], row["target_label"]): row for row in reliability_rows
    }
    queue: list[dict[str, Any]] = []
    for row in cross_rows:
        if row.get("consistency_status", "") == "consistent" and not row.get(
            "issue_type",
            "",
        ):
            continue
        queue.append(_queue_from_cross_row(row))
    for row in root_rows:
        reliability = reliability_by_key.get((row["sample_name"], row["target_label"]))
        queue.append(_queue_from_root_row(row, reliability))
    root_keys = {
        (row["sample_name"], row["target_label"])
        for row in root_rows
    }
    for row in reliability_rows:
        reasons = _split_reasons(row.get("risk_reasons", ""))
        if "weak_area_rank" not in reasons:
            continue
        if (row["sample_name"], row["target_label"]) in root_keys:
            continue
        queue.append(_queue_from_weak_area_row(row))
    queue.sort(key=_queue_sort_key)
    return queue


def _queue_from_cross_row(row: dict[str, str]) -> dict[str, Any]:
    issue = row.get("issue_type", "") or row.get("consistency_status", "")
    return _queue_row(
        row=row,
        source_file=_SOURCE_CROSS_ROWS,
        root_cause=issue,
        priority=_cross_priority(issue),
        area_ratio=row.get("targeted_area_to_median_ratio", ""),
        loss_ppm="",
        apex_delta="",
    )


def _queue_from_root_row(
    row: dict[str, str],
    reliability: dict[str, str] | None,
) -> dict[str, Any]:
    bucket = row["root_cause_bucket"]
    return _queue_row(
        row=row,
        source_file=_SOURCE_ROOT_ROWS,
        root_cause=bucket,
        priority=_root_priority(bucket),
        area_ratio=(
            reliability.get("area_to_target_median_ratio", "")
            if reliability is not None
            else ""
        ),
        loss_ppm=row.get("best_loss_ppm") or row.get("nearest_product_loss_ppm", ""),
        apex_delta=row.get("apex_ms2_delta_min", ""),
    )


def _queue_from_weak_area_row(row: dict[str, str]) -> dict[str, Any]:
    return _queue_row(
        row=row,
        source_file=_SOURCE_RELIABILITY_ROWS,
        root_cause="weak_area_rank",
        priority=6,
        area_ratio=row.get("area_to_target_median_ratio", ""),
        loss_ppm="",
        apex_delta="",
    )


def _queue_row(
    *,
    row: dict[str, str],
    source_file: str,
    root_cause: str,
    priority: int,
    area_ratio: str,
    loss_ppm: str,
    apex_delta: str,
) -> dict[str, Any]:
    sample = row["sample_name"]
    target = row["target_label"]
    mz = row.get("target_mz", "")
    return {
        "sample": sample,
        "target": target,
        "mz": mz,
        "state": row.get("reliability_state", ""),
        "root_cause": root_cause,
        "area_ratio": area_ratio,
        "apex_delta_min": apex_delta,
        "best_or_nearest_loss_ppm": loss_ppm,
        "source_file": source_file,
        "source_key": f"{sample}|{target}",
        "row_locator": f"sample={sample},target={target},mz={mz}",
        "_priority": priority,
    }


def _queue_sort_key(row: dict[str, Any]) -> tuple[Any, ...]:
    priority = int(row["_priority"])
    if priority == 5:
        return (
            priority,
            _float_value(row["best_or_nearest_loss_ppm"], default=math.inf),
        )
    if priority == 6:
        return (priority, _float_value(row["area_ratio"], default=math.inf))
    return (priority, str(row["target"]), str(row["sample"]))


def _root_priority(bucket: str) -> int:
    if bucket == "ppm_gate_fail":
        return 3
    if bucket == "off_apex_ms2":
        return 4
    if bucket == "no_diagnostic_product":
        return 5
    return 7


def _cross_priority(issue: str) -> int:
    if issue in {"missing_selected_candidate", "missing_targeted_reliability"}:
        return 2
    return 1


def _verdict(
    *,
    reliability_targets: list[dict[str, Any]],
    root_summary: dict[str, str],
    consistency: dict[str, Any],
) -> tuple[str, str]:
    if (
        int(consistency["mismatch_count"]) > 0
        or int(consistency["missing_candidate_count"]) > 0
        or int(consistency["missing_reliability_count"]) > 0
        or _int_value(root_summary.get("missing_candidate_count", "")) > 0
    ):
        return "FAIL", "evidence chain is internally inconsistent"
    has_review = any(int(row["review_burden"]) > 0 for row in reliability_targets)
    has_root_cause = _int_value(root_summary.get("included_count", "")) > 0
    if has_review or has_root_cause:
        return "WARN", "evidence chain is coherent, manual review recommended"
    return "PASS", "no immediate manual review requested"


def _first_row(rows: tuple[dict[str, str], ...], path: Path) -> dict[str, str]:
    if not rows:
        raise ValueError(f"{path}: expected exactly one summary row")
    if len(rows) > 1:
        raise ValueError(f"{path}: expected exactly one summary row, got {len(rows)}")
    return rows[0]


def _parse_count_map(text: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in _split_reasons(text):
        if ":" not in item:
            continue
        key, value = item.rsplit(":", 1)
        counts[key] = _int_value(value)
    return counts


def _split_reasons(text: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in text.split(";") if part.strip())


def _int_value(value: str) -> int:
    try:
        return int(float(str(value)))
    except ValueError:
        return 0


def _float_value(value: Any, *, default: float) -> float:
    try:
        number = float(str(value))
    except ValueError:
        return default
    return number if math.isfinite(number) else default
