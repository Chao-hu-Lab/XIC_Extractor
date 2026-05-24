"""Targeted audit and ISTD benchmark guardrails."""

from __future__ import annotations

import csv
import json
from collections import Counter
from collections.abc import Mapping
from pathlib import Path

from tools.diagnostics.untargeted_alignment_guardrail_metrics import _is_trueish


def compare_targeted_audit_counts(
    baseline_csv: Path,
    candidate_csv: Path,
    *,
    target_label: str,
) -> list[dict[str, str]]:
    baseline_counts = _targeted_failure_counts(baseline_csv, target_label)
    candidate_counts = _targeted_failure_counts(candidate_csv, target_label)
    rows = []
    for failure_mode in ("SPLIT", "MISS"):
        baseline_count = baseline_counts[failure_mode]
        candidate_count = candidate_counts[failure_mode]
        delta = candidate_count - baseline_count
        rows.append(
            {
                "target_label": target_label,
                "failure_mode": failure_mode,
                "baseline_count": str(baseline_count),
                "candidate_count": str(candidate_count),
                "delta": str(delta),
                "status": "FAIL" if delta > 0 else "PASS",
            },
        )
    return rows


def targeted_istd_benchmark_guardrail_rows(
    benchmark_json: Path,
) -> list[dict[str, str]]:
    if not benchmark_json.exists():
        raise FileNotFoundError(str(benchmark_json))
    payload = json.loads(benchmark_json.read_text(encoding="utf-8"))
    summaries = _benchmark_summaries(payload, benchmark_json)
    rows = [
        _targeted_istd_metric_row(
            "overall_status",
            str(payload.get("overall_status", "")),
            "PASS",
            "FAIL" if payload.get("overall_status") != "PASS" else "PASS",
            "strict targeted ISTD benchmark status",
        ),
        _targeted_istd_metric_row(
            "active_fail_count",
            _count_summaries(summaries, active_only=True, status="FAIL"),
            "0",
            "FAIL"
            if _count_summaries(summaries, active_only=True, status="FAIL") > 0
            else "PASS",
            "active DNA ISTD failures",
        ),
        _targeted_istd_metric_row(
            "miss_count",
            _count_failure_mode(summaries, "MISS"),
            "0",
            "FAIL" if _count_failure_mode(summaries, "MISS") > 0 else "PASS",
            "active DNA ISTDs without primary hit",
        ),
        _targeted_istd_metric_row(
            "split_count",
            _count_failure_mode(summaries, "SPLIT"),
            "0",
            "FAIL" if _count_failure_mode(summaries, "SPLIT") > 0 else "PASS",
            "active DNA ISTDs with multiple primary hits",
        ),
        _targeted_istd_metric_row(
            "false_positive_tag_count",
            _count_failure_mode(summaries, "FALSE_POSITIVE_TAG"),
            "0",
            "FAIL"
            if _count_failure_mode(summaries, "FALSE_POSITIVE_TAG") > 0
            else "PASS",
            "inactive tag primary hits",
        ),
    ]
    return rows


def _targeted_failure_counts(path: Path, target_label: str) -> Counter[str]:
    if not path.exists():
        raise FileNotFoundError(str(path))
    counts: Counter[str] = Counter()
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []
        if "failure_mode" not in fieldnames:
            raise ValueError(f"{path} is missing required column: failure_mode")
        has_target_label = "target_label" in fieldnames
        for row in reader:
            if not has_target_label or row.get("target_label") == target_label:
                counts[row.get("failure_mode", "")] += 1
    return counts


def _targeted_istd_metric_row(
    metric: str,
    value: object,
    threshold: str,
    status: str,
    note: str,
) -> dict[str, str]:
    return {
        "metric": metric,
        "value": str(value),
        "threshold": threshold,
        "status": status,
        "note": note,
    }


def _count_summaries(
    summaries: list[object],
    *,
    active_only: bool,
    status: str,
) -> int:
    return sum(
        1
        for summary in summaries
        if isinstance(summary, dict)
        and summary.get("status") == status
        and (not active_only or _is_json_trueish(summary.get("active_tag")))
    )


def _benchmark_summaries(
    payload: Mapping[str, object],
    benchmark_json: Path,
) -> list[object]:
    raw_summaries = payload.get("summaries")
    if raw_summaries is None:
        raw_summaries = payload.get("targets")
    if not isinstance(raw_summaries, list):
        raise ValueError(f"{benchmark_json} is missing summaries or targets list")
    return [_normalize_benchmark_summary(summary) for summary in raw_summaries]


def _normalize_benchmark_summary(summary: object) -> object:
    if not isinstance(summary, dict):
        return summary
    normalized = dict(summary)
    if "status" not in normalized and "benchmark_class" in normalized:
        normalized["status"] = normalized.get("benchmark_class")
    if "active_tag" not in normalized and "active_dna_istd_candidate" in normalized:
        normalized["active_tag"] = normalized.get("active_dna_istd_candidate")
    return normalized


def _count_failure_mode(summaries: list[object], failure_mode: str) -> int:
    count = 0
    for summary in summaries:
        if not isinstance(summary, dict):
            continue
        modes = summary.get("failure_modes", "")
        if isinstance(modes, list):
            has_mode = failure_mode in modes
        else:
            has_mode = failure_mode in str(modes).split(";")
        if has_mode:
            count += 1
    return count


def _is_json_trueish(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return _is_trueish(value)
    return False
