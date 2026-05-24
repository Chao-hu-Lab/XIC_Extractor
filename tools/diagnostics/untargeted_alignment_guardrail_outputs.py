"""Report row and comparison writers for untargeted alignment guardrails."""

from __future__ import annotations

import csv
from collections.abc import Mapping
from pathlib import Path

from tools.diagnostics.untargeted_alignment_guardrail_models import (
    CASE_SUMMARY_COLUMNS,
    COMPARISON_METRICS,
    CaseAssertion,
)


def compare_guardrails(
    baseline: Mapping[str, int],
    candidate: Mapping[str, int],
) -> list[dict[str, str]]:
    rows = []
    for metric in COMPARISON_METRICS:
        baseline_count = int(baseline.get(metric, 0))
        candidate_count = int(candidate.get(metric, 0))
        delta = candidate_count - baseline_count
        rows.append(
            {
                "metric": metric,
                "baseline_count": str(baseline_count),
                "candidate_count": str(candidate_count),
                "delta": str(delta),
                "status": "FAIL" if delta > 0 else "PASS",
            },
        )
    return rows


def write_case_assertion_summary_tsv(
    path: Path,
    cases: Mapping[str, CaseAssertion],
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=CASE_SUMMARY_COLUMNS,
            delimiter="\t",
        )
        writer.writeheader()
        for case_name, assertion in cases.items():
            writer.writerow(_case_summary_row(case_name, assertion))
    return path


def _case_summary_row(case_name: str, assertion: CaseAssertion) -> dict[str, str]:
    return {
        "case": case_name,
        "production_family_count": str(assertion.production_family_count),
        "owner_count": str(assertion.owner_count),
        "event_count": str(assertion.event_count),
        "supporting_event_count": str(assertion.supporting_event_count),
        "strong_edge_count": str(assertion.strong_edge_count),
        "preserved_split_or_ambiguous": _bool_text(
            assertion.preserved_split_or_ambiguous,
        ),
        "status": assertion.status,
        "reason": assertion.reason,
    }


def _bool_text(value: bool) -> str:
    return "true" if value else "false"
