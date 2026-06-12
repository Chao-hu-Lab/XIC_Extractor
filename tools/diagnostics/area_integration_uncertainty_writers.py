from __future__ import annotations

import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import asdict
from pathlib import Path

from tools.diagnostics.area_integration_uncertainty_models import (
    ROW_FIELDS,
    SUMMARY_FIELDS,
    AreaIntegrationUncertaintyOutputs,
    AreaIntegrationUncertaintyResult,
)
from tools.diagnostics.diagnostic_io import write_tsv


def _write_outputs(
    outputs: AreaIntegrationUncertaintyOutputs,
    result: AreaIntegrationUncertaintyResult,
) -> None:
    _write_tsv(outputs.summary_tsv, SUMMARY_FIELDS, (asdict(result.summary),))
    _write_tsv(outputs.rows_tsv, ROW_FIELDS, tuple(asdict(row) for row in result.rows))
    with outputs.json_path.open("w", encoding="utf-8") as handle:
        json.dump(asdict(result), handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    _write_markdown(outputs.markdown_path, result)


def _write_markdown(
    path: Path,
    result: AreaIntegrationUncertaintyResult,
) -> None:
    lines = [
        "# Area Integration Uncertainty Audit",
        "",
        f"- Rows checked: {result.summary.rows_checked}",
        f"- Bucket counts: {result.summary.bucket_counts}",
        "",
        "## Review Rows",
        "",
    ]
    for row in result.rows[:25]:
        lines.append(
            "- "
            f"{row.sample} / {row.target_label}: {row.integration_bucket} "
            f"(family={row.untargeted_family_id or 'NA'}, "
            f"raw_ratio={_fmt(row.raw_area_ratio)}, "
            f"baseline_ratio={_fmt(row.baseline_area_ratio)})"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_tsv(
    path: Path,
    fields: Sequence[str],
    rows: Sequence[Mapping[str, object]],
) -> None:
    write_tsv(path, rows, fields, formatter=_format_value, lineterminator="\n")


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
