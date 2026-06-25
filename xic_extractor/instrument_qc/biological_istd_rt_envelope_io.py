from __future__ import annotations

import csv
import json
from collections import Counter
from dataclasses import asdict
from pathlib import Path
from typing import Any

from xic_extractor.instrument_qc.biological_istd_rt_envelope import (
    BIOLOGICAL_ISTD_RT_ROWS_REQUIRED_COLUMNS,
    BiologicalIstdRtEnvelopeResult,
    BiologicalIstdRtEnvelopeRow,
    BiologicalIstdRtEnvelopeTarget,
    build_biological_istd_rt_envelope,
    parse_biological_istd_rt_input_rows,
)
from xic_extractor.instrument_qc.calibration_product_loaders import read_tsv_rows

ENVELOPE_ROW_COLUMNS = [
    "target_label",
    "sample_name",
    "injection_order",
    "observed_rt_min",
    "predicted_rt_min",
    "residual_min",
    "abs_residual_min",
    "normal_abs_residual_min",
    "warning_abs_residual_min",
    "envelope_status",
    "anchor_status",
    "reliability_state",
    "confidence",
    "review_reason",
]

ENVELOPE_TARGET_COLUMNS = [
    "target_label",
    "anchor_status",
    "point_count",
    "eligible_count",
    "eligible_fraction",
    "rt_min",
    "rt_max",
    "rt_range_min",
    "slope_min_per_injection",
    "intercept_min",
    "median_abs_residual_min",
    "p90_abs_residual_min",
    "p95_abs_residual_min",
    "normal_abs_residual_min",
    "warning_abs_residual_min",
    "high_raw_drift",
    "review_reason",
]


def build_biological_istd_rt_envelope_from_files(
    *,
    biological_istd_rows_tsv: Path,
) -> BiologicalIstdRtEnvelopeResult:
    raw_rows = read_tsv_rows(
        biological_istd_rows_tsv,
        required_columns=BIOLOGICAL_ISTD_RT_ROWS_REQUIRED_COLUMNS,
    )
    input_rows = parse_biological_istd_rt_input_rows(raw_rows)
    return build_biological_istd_rt_envelope(input_rows)


def write_biological_istd_rt_envelope_outputs(
    *,
    output_dir: Path,
    result: BiologicalIstdRtEnvelopeResult,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    rows_tsv = output_dir / "biological_istd_rt_envelope_rows.tsv"
    targets_tsv = output_dir / "biological_istd_rt_envelope_targets.tsv"
    summary_tsv = output_dir / "biological_istd_rt_envelope_summary.tsv"
    summary_json = output_dir / "biological_istd_rt_envelope.json"
    review_md = output_dir / "biological_istd_rt_envelope.md"
    _write_rows_tsv(rows_tsv, result.rows)
    _write_targets_tsv(targets_tsv, result.targets)
    _write_summary_tsv(summary_tsv, result)
    summary_json.write_text(
        json.dumps(_summary_payload(result), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    review_md.write_text(_render_markdown(result), encoding="utf-8")
    return {
        "rows_tsv": rows_tsv,
        "targets_tsv": targets_tsv,
        "summary_tsv": summary_tsv,
        "summary_json": summary_json,
        "review_md": review_md,
    }


def _write_rows_tsv(
    path: Path,
    rows: tuple[BiologicalIstdRtEnvelopeRow, ...],
) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=ENVELOPE_ROW_COLUMNS, delimiter="\t")
        writer.writeheader()
        for row in rows:
            writer.writerow(_dataclass_row(row, ENVELOPE_ROW_COLUMNS))


def _write_targets_tsv(
    path: Path,
    targets: tuple[BiologicalIstdRtEnvelopeTarget, ...],
) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=ENVELOPE_TARGET_COLUMNS,
            delimiter="\t",
        )
        writer.writeheader()
        for target in targets:
            writer.writerow(_dataclass_row(target, ENVELOPE_TARGET_COLUMNS))


def _write_summary_tsv(path: Path, result: BiologicalIstdRtEnvelopeResult) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["category", "label", "count"],
            delimiter="\t",
        )
        writer.writeheader()
        writer.writerow(
            {"category": "run_verdict", "label": result.run_verdict, "count": 1}
        )
        writer.writerow(
            {
                "category": "stable_target_count",
                "label": "stable_istd_anchor",
                "count": result.stable_target_count,
            }
        )
        for label, count in result.counts_by_anchor_status.items():
            writer.writerow(
                {"category": "anchor_status", "label": label, "count": count}
            )
        for label, count in result.counts_by_envelope_status.items():
            writer.writerow(
                {"category": "envelope_status", "label": label, "count": count}
            )


def _summary_payload(result: BiologicalIstdRtEnvelopeResult) -> dict[str, Any]:
    return {
        "run_verdict": result.run_verdict,
        "stable_target_count": result.stable_target_count,
        "pooled_p95_abs_residual_min": result.pooled_p95_abs_residual_min,
        "counts_by_anchor_status": result.counts_by_anchor_status,
        "counts_by_envelope_status": result.counts_by_envelope_status,
        "target_count": len(result.targets),
        "row_count": len(result.rows),
    }


def _render_markdown(result: BiologicalIstdRtEnvelopeResult) -> str:
    target_counts = Counter(target.anchor_status for target in result.targets)
    lines = [
        "# Biological ISTD RT Envelope",
        "",
        "This report is audit-only. It defines the observed RT drift envelope from",
        "biological-sample ISTDs, then reports residuals after a target-specific",
        "injection-order drift model. It does not mutate matrix values.",
        "",
        "## Verdict",
        "",
        f"- run verdict: `{result.run_verdict}`",
        f"- stable ISTD anchors: `{result.stable_target_count}`",
        (
            "- pooled p95 abs residual min: "
            f"`{_format_float(result.pooled_p95_abs_residual_min)}`"
        ),
        "",
        "## Anchor Status Counts",
        "",
    ]
    for status, count in sorted(target_counts.items()):
        lines.append(f"- `{status}`: {count}")
    lines.extend(
        [
            "",
            "## Stable ISTD Anchors",
            "",
            "| Target | Points | RT range | Slope | p95 residual | "
            "Normal envelope | Raw drift warning |",
            "| --- | ---: | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    for target in result.targets:
        if target.anchor_status != "stable_istd_anchor":
            continue
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{target.target_label}`",
                    str(target.point_count),
                    _format_float(target.rt_range_min),
                    _format_float(target.slope_min_per_injection),
                    _format_float(target.p95_abs_residual_min),
                    _format_float(target.normal_abs_residual_min),
                    "`yes`" if target.high_raw_drift else "`no`",
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "Interpretation: large raw RT range is not automatically a failure when",
            "the injection-order model leaves small residuals. This output should be",
            "used to prioritize review of apparent neighboring-interference",
            "patterns. It does not prove whether a case is true interference or",
            "normal biological-matrix RT drift without overlay context.",
            "",
        ]
    )
    return "\n".join(lines)


def _dataclass_row(
    item: BiologicalIstdRtEnvelopeRow | BiologicalIstdRtEnvelopeTarget,
    columns: list[str],
) -> dict[str, str]:
    raw = asdict(item)
    return {column: _format_value(raw.get(column)) for column in columns}


def _format_value(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, float):
        return _format_float(value)
    return str(value)


def _format_float(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value:.6g}"
