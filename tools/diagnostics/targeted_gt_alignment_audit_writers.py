from __future__ import annotations

import csv
import html
from collections import Counter
from pathlib import Path

from tools.diagnostics.targeted_gt_alignment_audit_models import (
    DRIFT_MODE,
    DUPLICATE_MODE,
    MISS_MODE,
    PASS_MODE,
    SPLIT_MODE,
    AuditConfig,
    TargetGroundTruth,
)
from tools.diagnostics.targeted_gt_alignment_audit_utils import (
    _format_float,
    _is_numeric_text,
)


def _write_report(
    path: Path,
    comparison: list[dict[str, object]],
    review_rows: list[dict[str, str]],
    config: AuditConfig,
) -> None:
    counts = Counter(str(row["failure_mode"]) for row in comparison)
    total = len(comparison)
    lines = [
        f"# Targeted GT Alignment Audit: {config.target_label}",
        "",
        f"Target m/z: {config.target_mz:.6g}",
        f"Alignment run: `{config.alignment_run}`",
        "",
        "## Summary",
        "",
        "| Mode | Count | Percent |",
        "|---|---:|---:|",
    ]
    for mode in (PASS_MODE, SPLIT_MODE, DRIFT_MODE, DUPLICATE_MODE, MISS_MODE):
        count = counts.get(mode, 0)
        percent = count / total * 100.0 if total else 0.0
        lines.append(f"| {mode} | {count} | {percent:.1f}% |")
    lines.extend(
        [
            "",
            "## Families In Target m/z Range",
            "",
            "| Family | m/z | RT | Anchor | Warning |",
            "|---|---:|---:|---|---|",
        ],
    )
    for row in review_rows:
        lines.append(
            "| "
            f"{row.get('feature_family_id', '')} | "
            f"{row.get('family_center_mz', '')} | "
            f"{row.get('family_center_rt', '')} | "
            f"{row.get('has_anchor', '')} | "
            f"{row.get('warning', '')} |"
        )
    lines.extend(["", "## Per-Sample Detail", ""])
    for row in comparison:
        lines.extend(
            [
                f"### {row['sample_stem']} - `{row['failure_mode']}`",
                "",
                f"- GT RT: {row['gt_target_rt_min']} min",
                f"- Production families: {row['production_family_ids'] or '(none)'}",
                f"- Duplicate families: {row['duplicate_family_ids'] or '(none)'}",
                (
                    "- Closest: "
                    f"{row['closest_family_id'] or '(none)'} "
                    f"{row['closest_status']} "
                    f"delta={row['closest_rt_delta_sec']} sec"
                ),
                "",
            ],
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_svg(
    path: Path,
    comparison: list[dict[str, object]],
    config: AuditConfig,
) -> None:
    row_height = 34
    width = 900
    height = max(160, 80 + len(comparison) * row_height)
    colors = {
        PASS_MODE: "#2ca02c",
        SPLIT_MODE: "#ff7f0e",
        DRIFT_MODE: "#1f77b4",
        DUPLICATE_MODE: "#9467bd",
        MISS_MODE: "#d62728",
    }
    items = [
        _svg_text(20, 30, f"Targeted GT Audit: {config.target_label}", 18),
        _svg_text(20, 55, f"Alignment run: {config.alignment_run}", 11),
    ]
    for index, row in enumerate(comparison):
        y = 90 + index * row_height
        mode = str(row["failure_mode"])
        color = colors.get(mode, "#777777")
        items.append(
            f'<rect x="20" y="{y - 18}" width="18" height="18" fill="{color}" />',
        )
        label = (
            f"{row['sample_stem']}  {mode}  "
            f"closest={row['closest_family_id'] or 'NA'} "
            f"delta={row['closest_rt_delta_sec'] or 'NA'} sec"
        )
        items.append(_svg_text(50, y - 4, label, 12))
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
        f'height="{height}" viewBox="0 0 {width} {height}">\n'
        '<rect width="100%" height="100%" fill="white" />\n'
        + "\n".join(items)
        + "\n</svg>\n"
    )
    path.write_text(svg, encoding="utf-8")


def _write_dict_csv(path: Path, rows: list[object]) -> None:
    serialized = [_as_output_dict(row) for row in rows]
    if not serialized:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(serialized[0].keys()))
        writer.writeheader()
        for row in serialized:
            writer.writerow(
                {key: _escape_excel_formula(value) for key, value in row.items()},
            )


def _as_output_dict(row: object) -> dict[str, object]:
    if isinstance(row, TargetGroundTruth):
        return {
            "sample_stem": row.sample_stem,
            "group": row.group,
            "target_mz": _format_float(row.target_mz, 6),
            "target_rt_min": _format_float(row.target_rt_min, 4),
            "target_peak_start_min": _format_float(row.target_peak_start_min, 4),
            "target_peak_end_min": _format_float(row.target_peak_end_min, 4),
            "target_peak_width_min": _format_float(row.target_peak_width_min, 4),
            "target_area": _format_float(row.target_area, 2),
            "target_confidence": row.target_confidence,
            "target_nl_ok": row.target_nl_ok,
            "target_reason": row.target_reason,
            "istd_rt_min": _format_float(row.istd_rt_min, 4),
            "istd_rt_delta_sec": _format_float(row.istd_rt_delta_sec, 2),
        }
    return dict(row)  # type: ignore[arg-type]


def _escape_excel_formula(value: object) -> object:
    if (
        isinstance(value, str)
        and value.startswith(("=", "+", "-", "@"))
        and not _is_numeric_text(value)
    ):
        return f"'{value}"
    return value


def _svg_text(x: int, y: int, text: str, size: int) -> str:
    return (
        f'<text x="{x}" y="{y}" font-family="Arial, sans-serif" '
        f'font-size="{size}">{html.escape(text)}</text>'
    )
