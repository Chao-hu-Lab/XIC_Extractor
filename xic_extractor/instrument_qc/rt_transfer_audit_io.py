from __future__ import annotations

import csv
import json
from collections import Counter
from dataclasses import asdict
from pathlib import Path
from typing import Any

from xic_extractor.instrument_qc.calibration_product_loaders import read_tsv_rows
from xic_extractor.instrument_qc.rt_transfer_audit import (
    BIOLOGICAL_ISTD_SUMMARY_REQUIRED_COLUMNS,
    CLEAN_STANDARD_SUMMARY_REQUIRED_COLUMNS,
    BiologicalIstdTransferAuditRow,
    build_biological_istd_transfer_audit_rows,
)

BIOLOGICAL_ISTD_TRANSFER_COLUMNS = [
    "target_label",
    "transfer_status",
    "direction_status",
    "biological_qc_count",
    "clean_standard_count",
    "biological_rt_range_min",
    "clean_rt_delta_range_min",
    "biological_slope_min_per_injection",
    "clean_slope_min_per_injection",
    "slope_magnitude_ratio",
    "clean_warning_count",
    "review_reason",
]


def build_biological_istd_transfer_audit_from_files(
    *,
    clean_standard_summary_tsv: Path,
    biological_qc_istd_summary_tsv: Path,
) -> tuple[BiologicalIstdTransferAuditRow, ...]:
    clean_rows = read_tsv_rows(
        clean_standard_summary_tsv,
        required_columns=CLEAN_STANDARD_SUMMARY_REQUIRED_COLUMNS,
    )
    biological_rows = read_tsv_rows(
        biological_qc_istd_summary_tsv,
        required_columns=BIOLOGICAL_ISTD_SUMMARY_REQUIRED_COLUMNS,
    )
    return build_biological_istd_transfer_audit_rows(
        biological_qc_rows=biological_rows,
        clean_standard_rows=clean_rows,
    )


def write_biological_istd_transfer_audit_outputs(
    *,
    output_dir: Path,
    rows: tuple[BiologicalIstdTransferAuditRow, ...],
    istd_scope: str,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    rows_tsv = output_dir / "biological_istd_rt_transfer_audit.tsv"
    summary_json = output_dir / "biological_istd_rt_transfer_audit.json"
    review_md = output_dir / "biological_istd_rt_transfer_audit.md"
    write_biological_istd_transfer_audit_tsv(rows_tsv, rows)
    summary = _summary_payload(
        rows,
        rows_tsv=rows_tsv,
        review_md=review_md,
        istd_scope=istd_scope,
    )
    summary_json.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    review_md.write_text(
        _render_markdown(rows, istd_scope=istd_scope),
        encoding="utf-8",
    )
    return {
        "rows_tsv": rows_tsv,
        "summary_json": summary_json,
        "review_md": review_md,
    }


def write_biological_istd_transfer_audit_tsv(
    path: Path,
    rows: tuple[BiologicalIstdTransferAuditRow, ...],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=BIOLOGICAL_ISTD_TRANSFER_COLUMNS,
            delimiter="\t",
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(_row_to_dict(row))


def _summary_payload(
    rows: tuple[BiologicalIstdTransferAuditRow, ...],
    *,
    rows_tsv: Path,
    review_md: Path,
    istd_scope: str,
) -> dict[str, Any]:
    counts = Counter(row.transfer_status for row in rows)
    return {
        "total_rows": len(rows),
        "counts_by_transfer_status": dict(sorted(counts.items())),
        "istd_scope": istd_scope,
        "rows_tsv": rows_tsv.name,
        "review_md": review_md.name,
    }


def _render_markdown(
    rows: tuple[BiologicalIstdTransferAuditRow, ...],
    *,
    istd_scope: str,
) -> str:
    counts = Counter(row.transfer_status for row in rows)
    lines = [
        "# Biological ISTD RT Transfer Audit",
        "",
        "This report is audit-only. It checks whether clean-standard RT trends are",
        "directionally transferable to biological QC ISTDs. It does not approve",
        "production RT correction or matrix mutation.",
        "",
        f"ISTD scope: `{istd_scope}`.",
        "",
        "## Summary",
        "",
    ]
    for status, count in sorted(counts.items()):
        lines.append(f"- `{status}`: {count}")
    lines.extend(
        [
            "",
            "## Rows",
            "",
            "| Target | Status | Direction | Bio count | Clean count | Bio slope | "
            "Clean slope | Ratio | Reason |",
            "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{row.target_label}`",
                    f"`{row.transfer_status}`",
                    f"`{row.direction_status}`",
                    _format_int(row.biological_qc_count),
                    _format_int(row.clean_standard_count),
                    _format_float(row.biological_slope_min_per_injection),
                    _format_float(row.clean_slope_min_per_injection),
                    _format_float(row.slope_magnitude_ratio),
                    row.review_reason,
                ]
            )
            + " |"
        )
    lines.append("")
    return "\n".join(lines)


def _row_to_dict(row: BiologicalIstdTransferAuditRow) -> dict[str, str]:
    raw = asdict(row)
    return {
        column: _format_value(raw.get(column))
        for column in BIOLOGICAL_ISTD_TRANSFER_COLUMNS
    }


def _format_value(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return _format_float(value)
    return str(value)


def _format_float(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value:.6g}"


def _format_int(value: int | None) -> str:
    if value is None:
        return ""
    return str(value)
