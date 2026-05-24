from __future__ import annotations

import csv
import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import asdict
from pathlib import Path

from tools.diagnostics.evidence_spine_consistency_models import (
    ROW_FIELDS,
    SUMMARY_FIELDS,
    EvidenceSpineConsistencyOutputs,
    EvidenceSpineConsistencyResult,
)


def _write_outputs(
    outputs: EvidenceSpineConsistencyOutputs,
    result: EvidenceSpineConsistencyResult,
) -> None:
    _write_tsv(outputs.summary_tsv, SUMMARY_FIELDS, (asdict(result.summary),))
    _write_tsv(outputs.rows_tsv, ROW_FIELDS, tuple(asdict(row) for row in result.rows))
    with outputs.json_path.open("w", encoding="utf-8") as handle:
        json.dump(asdict(result), handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    _write_markdown(outputs.markdown_path, result)


def _write_markdown(
    path: Path,
    result: EvidenceSpineConsistencyResult,
) -> None:
    lines = [
        "# Evidence Spine Consistency",
        "",
        f"- Rows checked: {result.summary.rows_checked}",
        f"- Matched rows: {result.summary.matched_rows}",
        f"- Consistent rows: {result.summary.consistent_rows}",
        f"- Missing alignment rows: {result.summary.missing_alignment_rows}",
        f"- Mismatch reasons: {result.summary.mismatch_reason_counts}",
        "",
        "## Review Rows",
        "",
    ]
    for row in result.rows[:20]:
        lines.append(
            "- "
            f"{row.sample} / {row.target_label}: {row.mismatch_reason} "
            f"(family={row.untargeted_family_id or 'NA'}, "
            f"target_rt={_fmt(row.targeted_selected_rt)}, "
            f"align_rt={_fmt(row.untargeted_selected_rt)})"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_tsv(
    path: Path,
    fields: Sequence[str],
    rows: Sequence[Mapping[str, object]],
) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=tuple(fields),
            delimiter="\t",
            lineterminator="\n",
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({field: _format_value(row.get(field)) for field in fields})


def _format_value(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, float):
        if not math.isfinite(value):
            return ""
        return f"{value:.10g}"
    return str(value)


def _fmt(value: float | None) -> str:
    return "NA" if value is None else f"{value:.4g}"
