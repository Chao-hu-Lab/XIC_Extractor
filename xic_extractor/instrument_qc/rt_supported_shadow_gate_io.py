from __future__ import annotations

import csv
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Mapping

from xic_extractor.instrument_qc.calibration_product_loaders import (
    parse_optional_float,
    parse_optional_int,
    read_tsv_rows,
)
from xic_extractor.instrument_qc.rt_supported_shadow_gate import (
    BiologicalIstdAnchorInputRow,
    MatrixRtPreviewInputRow,
    RtSupportedShadowGateParameters,
    RtSupportedShadowGateResult,
    build_input_invalid_result,
    build_required_artifact_missing_result,
    build_rt_supported_shadow_gate,
)

MATRIX_RT_PREVIEW_REQUIRED_COLUMNS = {
    "source_row_id",
    "source_cell_key",
    "feature_id",
    "sample_name",
    "sample_stem",
    "feature_mz",
    "raw_feature_rt_min",
    "injection_order",
    "coverage_status",
    "rt_alignment_support_status",
    "local_residual_p95_min",
    "rt_uncertainty_min",
    "local_biological_istd_anchor_count",
    "correction_status",
    "correction_block_reason",
}

BIOLOGICAL_TRANSFER_REQUIRED_COLUMNS = {
    "target_label",
    "transfer_status",
}

BIOLOGICAL_ANCHOR_BASE_REQUIRED_COLUMNS = {
    "target_label",
    "injection_order",
}

ROWS_COLUMNS = [
    "source_row_id",
    "source_cell_key",
    "feature_id",
    "sample_name",
    "sample_stem",
    "feature_mz",
    "raw_feature_rt_min",
    "injection_order",
    "coverage_status",
    "correction_status",
    "rt_alignment_support_status",
    "local_residual_p95_min",
    "rt_uncertainty_min",
    "local_biological_istd_anchor_count",
    "nearby_biological_istd_anchor_count",
    "supported_biological_istd_anchor_count",
    "conflict_biological_istd_anchor_count",
    "nearest_biological_istd_label",
    "nearest_biological_istd_transfer_status",
    "nearest_biological_istd_rt_delta_min",
    "nearest_biological_istd_injection_order_delta",
    "supporting_biological_istd_label",
    "supporting_biological_istd_transfer_status",
    "supporting_biological_istd_rt_delta_min",
    "supporting_biological_istd_injection_order_delta",
    "row_classification",
    "review_reason",
]

SUMMARY_COLUMNS = [
    "category",
    "label",
    "count",
]


def build_rt_supported_shadow_gate_from_files(
    *,
    matrix_rt_preview_tsv: Path,
    matrix_rt_preview_summary_json: Path,
    biological_istd_transfer_tsv: Path,
    biological_istd_transfer_json: Path,
    biological_istd_anchor_rows_tsv: Path | None = None,
    parameters: RtSupportedShadowGateParameters | None = None,
) -> RtSupportedShadowGateResult:
    params = parameters or RtSupportedShadowGateParameters()
    required_paths = {
        "matrix_rt_calibration_preview.tsv": matrix_rt_preview_tsv,
        "matrix_rt_calibration_preview_summary.json": (
            matrix_rt_preview_summary_json
        ),
        "biological_istd_rt_transfer_audit.tsv": biological_istd_transfer_tsv,
        "biological_istd_rt_transfer_audit.json": biological_istd_transfer_json,
    }
    if biological_istd_anchor_rows_tsv is not None:
        required_paths["biological_istd_anchor_rows.tsv"] = (
            biological_istd_anchor_rows_tsv
        )
    missing = tuple(
        label for label, path in required_paths.items() if not path.exists()
    )
    if missing:
        return build_required_artifact_missing_result(
            missing_artifacts=missing,
            parameters=params,
        )

    _read_json_object(matrix_rt_preview_summary_json)
    transfer_summary = _read_json_object(biological_istd_transfer_json)
    istd_scope = str(transfer_summary.get("istd_scope") or "").strip()

    return build_rt_supported_shadow_gate(
        matrix_rows=_load_matrix_rt_preview_rows(matrix_rt_preview_tsv),
        biological_istd_anchors=_load_biological_istd_anchor_rows(
            biological_istd_anchor_rows_tsv
        ),
        transfer_status_by_target=_load_transfer_status_by_target(
            biological_istd_transfer_tsv
        ),
        istd_scope=istd_scope,
        parameters=params,
    )


def write_rt_supported_shadow_gate_outputs(
    *,
    output_dir: Path,
    result: RtSupportedShadowGateResult,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    rows_tsv = output_dir / "instrument_qc_rt_supported_shadow_gate_rows.tsv"
    summary_tsv = output_dir / "instrument_qc_rt_supported_shadow_gate_summary.tsv"
    summary_json = output_dir / "instrument_qc_rt_supported_shadow_gate.json"
    review_md = output_dir / "instrument_qc_rt_supported_shadow_gate.md"
    _write_rows_tsv(rows_tsv, result)
    _write_summary_tsv(summary_tsv, result)
    summary_json.write_text(
        json.dumps(
            _summary_payload(result, rows_tsv=rows_tsv, summary_tsv=summary_tsv),
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    review_md.write_text(
        _render_markdown(result, rows_tsv=rows_tsv, summary_tsv=summary_tsv),
        encoding="utf-8",
    )
    return {
        "rows_tsv": rows_tsv,
        "summary_tsv": summary_tsv,
        "summary_json": summary_json,
        "review_md": review_md,
    }


def _load_matrix_rt_preview_rows(path: Path) -> tuple[MatrixRtPreviewInputRow, ...]:
    raw_rows = read_tsv_rows(path, required_columns=MATRIX_RT_PREVIEW_REQUIRED_COLUMNS)
    output: list[MatrixRtPreviewInputRow] = []
    for index, row in enumerate(raw_rows, start=2):
        output.append(
            MatrixRtPreviewInputRow(
                source_row_id=(row.get("source_row_id") or "").strip(),
                source_cell_key=(row.get("source_cell_key") or "").strip(),
                feature_id=(row.get("feature_id") or "").strip(),
                sample_name=(row.get("sample_name") or "").strip(),
                sample_stem=(row.get("sample_stem") or "").strip(),
                feature_mz=parse_optional_float(
                    row,
                    "feature_mz",
                    path=path,
                    row_number=index,
                ),
                raw_feature_rt_min=parse_optional_float(
                    row,
                    "raw_feature_rt_min",
                    path=path,
                    row_number=index,
                ),
                injection_order=_parse_optional_integral(
                    row,
                    "injection_order",
                    path=path,
                    row_number=index,
                ),
                coverage_status=(row.get("coverage_status") or "").strip(),
                rt_alignment_support_status=(
                    row.get("rt_alignment_support_status") or ""
                ).strip(),
                local_residual_p95_min=parse_optional_float(
                    row,
                    "local_residual_p95_min",
                    path=path,
                    row_number=index,
                ),
                rt_uncertainty_min=parse_optional_float(
                    row,
                    "rt_uncertainty_min",
                    path=path,
                    row_number=index,
                ),
                local_biological_istd_anchor_count=parse_optional_int(
                    row,
                    "local_biological_istd_anchor_count",
                    path=path,
                    row_number=index,
                ),
                correction_status=(row.get("correction_status") or "").strip(),
                correction_block_reason=(
                    row.get("correction_block_reason") or ""
                ).strip(),
            )
        )
    return tuple(output)


def _load_transfer_status_by_target(path: Path) -> dict[str, str]:
    rows = read_tsv_rows(path, required_columns=BIOLOGICAL_TRANSFER_REQUIRED_COLUMNS)
    output: dict[str, str] = {}
    for row in rows:
        target = (row.get("target_label") or "").strip()
        status = (row.get("transfer_status") or "").strip()
        if target:
            output[target] = status
    return output


def _load_biological_istd_anchor_rows(
    path: Path | None,
) -> tuple[BiologicalIstdAnchorInputRow, ...]:
    if path is None:
        return ()
    rows = read_tsv_rows(
        path,
        required_columns=BIOLOGICAL_ANCHOR_BASE_REQUIRED_COLUMNS,
    )
    if rows and "observed_rt_min" not in rows[0] and "rt_min" not in rows[0]:
        raise ValueError(
            f"{path.name} missing required columns: observed_rt_min or rt_min"
        )
    output: list[BiologicalIstdAnchorInputRow] = []
    for index, row in enumerate(rows, start=2):
        rt_column = "observed_rt_min" if "observed_rt_min" in row else "rt_min"
        output.append(
            BiologicalIstdAnchorInputRow(
                target_label=(row.get("target_label") or "").strip(),
                sample_name=(row.get("sample_name") or "").strip(),
                injection_order=_parse_optional_integral(
                    row,
                    "injection_order",
                    path=path,
                    row_number=index,
                ),
                observed_rt_min=parse_optional_float(
                    row,
                    rt_column,
                    path=path,
                    row_number=index,
                ),
            )
        )
    return tuple(output)


def _write_rows_tsv(path: Path, result: RtSupportedShadowGateResult) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=ROWS_COLUMNS, delimiter="\t")
        writer.writeheader()
        for row in result.rows:
            raw = asdict(row)
            writer.writerow(
                {column: _format_value(raw.get(column)) for column in ROWS_COLUMNS}
            )


def _write_summary_tsv(path: Path, result: RtSupportedShadowGateResult) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=SUMMARY_COLUMNS, delimiter="\t")
        writer.writeheader()
        for row in _summary_rows(result):
            writer.writerow(row)


def _summary_rows(
    result: RtSupportedShadowGateResult,
) -> tuple[dict[str, str], ...]:
    rows: list[dict[str, str]] = [
        {"category": "run_verdict", "label": result.run_verdict, "count": "1"},
    ]
    for category, counts in (
        ("row_classification", result.counts_by_classification),
        ("coverage_status", result.counts_by_coverage_status),
        ("correction_status", result.counts_by_correction_status),
        ("nearest_transfer_status", result.counts_by_nearest_transfer_status),
    ):
        for label, count in sorted(counts.items()):
            rows.append(
                {"category": category, "label": str(label), "count": str(count)}
            )
    for artifact in result.missing_artifacts:
        rows.append({"category": "missing_artifact", "label": artifact, "count": "1"})
    for error in result.input_errors:
        rows.append({"category": "input_error", "label": error, "count": "1"})
    return tuple(rows)


def _summary_payload(
    result: RtSupportedShadowGateResult,
    *,
    rows_tsv: Path,
    summary_tsv: Path,
) -> dict[str, Any]:
    return {
        "run_verdict": result.run_verdict,
        "total_rows": len(result.rows),
        "counts_by_classification": result.counts_by_classification,
        "counts_by_coverage_status": result.counts_by_coverage_status,
        "counts_by_correction_status": result.counts_by_correction_status,
        "counts_by_nearest_transfer_status": (
            result.counts_by_nearest_transfer_status
        ),
        "istd_scope": result.istd_scope,
        "parameters": asdict(result.parameters),
        "missing_artifacts": list(result.missing_artifacts),
        "input_errors": list(result.input_errors),
        "rows_tsv": rows_tsv.name,
        "summary_tsv": summary_tsv.name,
    }


def _render_markdown(
    result: RtSupportedShadowGateResult,
    *,
    rows_tsv: Path,
    summary_tsv: Path,
) -> str:
    lines = [
        "# Instrument QC RT-Supported Shadow Gate",
        "",
        f"Run verdict: `{result.run_verdict}`",
        "",
        "This diagnostic is audit-only. It does not mutate matrix values,",
        "targeted reliability, scoring, resolver behavior, or downstream",
        "normalization.",
        "",
        f"ISTD scope: `{result.istd_scope or 'missing'}`",
        "",
        "Review files:",
        "",
        f"- rows: `{rows_tsv.name}`",
        f"- summary: `{summary_tsv.name}`",
        "",
        "## Row Classifications",
        "",
    ]
    if result.counts_by_classification:
        for label, count in sorted(result.counts_by_classification.items()):
            lines.append(f"- `{label}`: {count}")
    else:
        lines.append("- no rows evaluated")
    if result.missing_artifacts:
        lines.extend(["", "## Missing Artifacts", ""])
        for artifact in result.missing_artifacts:
            lines.append(f"- `{artifact}`")
    if result.input_errors:
        lines.extend(["", "## Input Errors", ""])
        for error in result.input_errors:
            lines.append(f"- {error}")
    top_rows = _top_review_rows(result)
    if top_rows:
        lines.extend(
            [
                "",
                "## Top Review Rows",
                "",
                "| classification | feature | sample | m/z | RT | "
                "supporting ISTD | reason |",
                "| --- | --- | --- | ---: | ---: | --- | --- |",
            ]
        )
        for row in top_rows:
            lines.append(
                "| "
                + " | ".join(
                    [
                        f"`{row.row_classification}`",
                        row.feature_id or row.source_row_id,
                        row.sample_stem or row.sample_name,
                        _format_value(row.feature_mz),
                        _format_value(row.raw_feature_rt_min),
                        row.supporting_biological_istd_label
                        or row.nearest_biological_istd_label
                        or "missing",
                        row.review_reason,
                    ]
                )
                + " |"
            )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- `rt_supported_shadow_candidate` means clean RT evidence and local",
            "  biological ISTD transfer context both support review.",
            "- `biological_context_missing` means the row cannot be promoted by this",
            "  shadow gate because local biological ISTD evidence is absent or",
            "  unscoped.",
            "- This report is not a Level 3 production correction approval.",
            "",
        ]
    )
    return "\n".join(lines)


def _top_review_rows(
    result: RtSupportedShadowGateResult,
    *,
    limit: int = 12,
) -> tuple[Any, ...]:
    priority = {
        "rt_supported_shadow_candidate": 0,
        "biological_transfer_conflict": 1,
        "clean_standard_only_review": 2,
        "biological_context_missing": 3,
    }
    rows = [row for row in result.rows if row.row_classification in priority]
    rows.sort(
        key=lambda row: (
            priority[row.row_classification],
            row.feature_id,
            row.sample_stem,
        )
    )
    return tuple(rows[:limit])


def build_input_invalid_shadow_gate_result(
    *,
    error: ValueError,
    parameters: RtSupportedShadowGateParameters,
) -> RtSupportedShadowGateResult:
    return build_input_invalid_result(
        input_errors=(str(error),),
        parameters=parameters,
    )


def _read_json_object(path: Path) -> Mapping[str, Any]:
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, Mapping):
        raise ValueError(f"JSON root must be an object: {path}")
    return payload


def _parse_optional_integral(
    row: Mapping[str, str],
    column: str,
    *,
    path: Path,
    row_number: int,
) -> int | None:
    value = (row.get(column) or "").strip()
    if not value:
        return None
    try:
        parsed = float(value)
    except ValueError as exc:
        raise ValueError(
            f"{path.name} column {column} row {row_number} has invalid integer "
            f"value: {value!r}"
        ) from exc
    if not parsed.is_integer():
        raise ValueError(
            f"{path.name} column {column} row {row_number} must be an integer "
            f"or integer-like decimal value: {value!r}"
        )
    return int(parsed)


def _format_value(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)
