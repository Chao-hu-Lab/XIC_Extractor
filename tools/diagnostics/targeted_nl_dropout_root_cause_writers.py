"""Output writers for targeted NL dropout root-cause audit."""

from __future__ import annotations

import csv
import json
from collections.abc import Mapping, Sequence
from dataclasses import asdict
from pathlib import Path

from tools.diagnostics.targeted_nl_dropout_root_cause_models import (
    _ROW_COLUMNS,
    _SUMMARY_COLUMNS,
    RootCauseRow,
    TargetedNLDropoutRootCauseOutputs,
    TargetedNLDropoutRootCauseResult,
)


def _write_outputs(
    outputs: TargetedNLDropoutRootCauseOutputs,
    result: TargetedNLDropoutRootCauseResult,
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


def _row_dicts(rows: Sequence[RootCauseRow]) -> list[dict[str, object]]:
    return [asdict(row) for row in rows]


def _write_tsv(
    path: Path,
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


def _markdown(result: TargetedNLDropoutRootCauseResult) -> str:
    lines = [
        "# Targeted NL Dropout Root-cause Audit",
        "",
        "This diagnostic classifies targeted_review_positive rows only. It does "
        "not rescan RAW files, change selected peaks, or alter XIC Results.",
        "",
        "## Summary",
        "",
    ]
    summary = asdict(result.summary)
    lines.extend(f"- {key}: {summary[key]}" for key in _SUMMARY_COLUMNS)
    lines.extend(["", "## Rows", ""])
    for row in result.rows:
        mz = "" if row.target_mz is None else f", m/z {row.target_mz:.6g}"
        lines.append(
            f"- {row.root_cause_bucket}: {row.sample_name} / "
            f"{row.target_label}{mz} - {row.root_cause_reason}"
        )
    lines.append("")
    return "\n".join(lines)


def _format_value(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)
