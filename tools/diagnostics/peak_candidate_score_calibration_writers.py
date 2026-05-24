from __future__ import annotations

import csv
import json
from pathlib import Path

from tools.diagnostics.peak_candidate_score_calibration_models import (
    _LABEL_COLUMNS,
    _RISK_COLUMNS,
    _SUMMARY_COLUMNS,
    ScoreLabelImpactRow,
    ScoreRiskRow,
)


def _write_outputs(
    output_dir: Path,
    payload: dict[str, object],
    risk_rows: tuple[ScoreRiskRow, ...],
    label_impact: tuple[ScoreLabelImpactRow, ...],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_summary(output_dir / "peak_candidate_score_calibration_summary.tsv", payload)
    _write_risk_rows(output_dir / "peak_candidate_score_risk_rows.tsv", risk_rows)
    _write_label_impact(
        output_dir / "peak_candidate_score_label_impact.tsv",
        label_impact,
    )
    (output_dir / "peak_candidate_score_calibration.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_dir / "peak_candidate_score_calibration.md").write_text(
        _markdown(payload),
        encoding="utf-8",
    )


def _write_summary(path: Path, payload: dict[str, object]) -> None:
    summary = payload["summary"]
    if not isinstance(summary, dict):
        raise TypeError("summary payload must be a dictionary")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=_SUMMARY_COLUMNS, delimiter="\t")
        writer.writeheader()
        writer.writerow(summary)


def _write_risk_rows(path: Path, rows: tuple[ScoreRiskRow, ...]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=_RISK_COLUMNS, delimiter="\t")
        writer.writeheader()
        writer.writerows(_format_risk_row(row) for row in rows)


def _write_label_impact(path: Path, rows: tuple[ScoreLabelImpactRow, ...]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=_LABEL_COLUMNS, delimiter="\t")
        writer.writeheader()
        writer.writerows(_format_label_impact_row(row) for row in rows)


def _format_risk_row(row: ScoreRiskRow) -> dict[str, str]:
    return {
        "group_id": row.group_id,
        "sample_name": row.sample_name,
        "target_label": row.target_label,
        "resolver_mode": row.resolver_mode,
        "risk_type": row.risk_type,
        "selected_candidate_id": row.selected_candidate_id,
        "selected_rt_apex_min": _format_optional_float(row.selected_rt_apex_min),
        "selected_raw_score": _format_optional_float(row.selected_raw_score),
        "selected_confidence": row.selected_confidence,
        "selected_support_labels": row.selected_support_labels,
        "selected_concern_labels": row.selected_concern_labels,
        "challenger_candidate_id": row.challenger_candidate_id,
        "challenger_rt_apex_min": _format_optional_float(row.challenger_rt_apex_min),
        "challenger_raw_score": _format_optional_float(row.challenger_raw_score),
        "challenger_confidence": row.challenger_confidence,
        "challenger_support_labels": row.challenger_support_labels,
        "challenger_concern_labels": row.challenger_concern_labels,
        "reason": row.reason,
    }


def _format_label_impact_row(row: ScoreLabelImpactRow) -> dict[str, str]:
    return {
        "label_kind": row.label_kind,
        "label": row.label,
        "selected_count": str(row.selected_count),
        "rejected_count": str(row.rejected_count),
        "selected_rate": _format_optional_float(row.selected_rate),
        "selected_median_raw_score": _format_optional_float(
            row.selected_median_raw_score
        ),
        "rejected_median_raw_score": _format_optional_float(
            row.rejected_median_raw_score
        ),
    }


def _markdown(payload: dict[str, object]) -> str:
    summary = payload["summary"]
    recommendations = payload["recommendations"]
    if not isinstance(summary, dict):
        raise TypeError("summary payload must be a dictionary")
    if not isinstance(recommendations, list | tuple):
        raise TypeError("recommendations payload must be a sequence")
    lines = [
        "# Peak Candidate Score Calibration",
        "",
        "This diagnostic does not change production selection.",
        "",
        "## Summary",
        "",
    ]
    lines.extend(f"- {column}: {summary[column]}" for column in _SUMMARY_COLUMNS)
    lines.extend(["", "## Recommendations", ""])
    lines.extend(f"- {recommendation}" for recommendation in recommendations)
    lines.append("")
    return "\n".join(lines)


def _format_optional_float(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value:.5f}"
