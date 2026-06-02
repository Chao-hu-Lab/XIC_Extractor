from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import asdict
from pathlib import Path

from tools.diagnostics.cross_report_evidence_consistency_models import (
    _ROW_COLUMNS,
    _SUMMARY_COLUMNS,
    ConsistencyResult,
    ConsistencyRow,
    CrossReportConsistencyOutputs,
)
from tools.diagnostics.diagnostic_io import write_tsv as _write_diagnostic_tsv


def _write_outputs(
    outputs: CrossReportConsistencyOutputs,
    result: ConsistencyResult,
) -> None:
    _write_tsv(outputs.summary_tsv, _SUMMARY_COLUMNS, [asdict(result.summary)])
    _write_tsv(outputs.rows_tsv, _ROW_COLUMNS, _row_dicts(result.rows))
    outputs.json_path.write_text(
        json.dumps(
            {
                "summary": asdict(result.summary),
                "rows": _row_dicts(result.rows),
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    outputs.markdown_path.write_text(_markdown(result), encoding="utf-8")


def _row_dicts(rows: Sequence[ConsistencyRow]) -> list[dict[str, object]]:
    return [asdict(row) for row in rows]


def _write_tsv(
    path: Path,
    fieldnames: Sequence[str],
    rows: Sequence[Mapping[str, object]],
) -> None:
    _write_diagnostic_tsv(path, rows, fieldnames, formatter=_format_value)


def _markdown(result: ConsistencyResult) -> str:
    lines = [
        "# Cross-report Evidence Consistency",
        "",
        "This diagnostic compares targeted reliability rows with selected "
        "peak-candidate evidence. It does not change production selection.",
        "",
        "## Summary",
        "",
    ]
    summary = asdict(result.summary)
    lines.extend(f"- {key}: {summary[key]}" for key in _SUMMARY_COLUMNS)
    lines.extend(["", "## Top Issues", ""])
    for row in result.rows:
        if row.consistency_status != "mismatch":
            continue
        mz = "" if row.target_mz is None else f", m/z {row.target_mz:.6g}"
        lines.append(f"- {row.issue_type}: {row.sample_name} / {row.target_label}{mz}")
    lines.append("")
    return "\n".join(lines)


def _format_value(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)
