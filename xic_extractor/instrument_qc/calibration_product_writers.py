from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Iterable

from xic_extractor.instrument_qc.calibration_product_models import (
    CalibrationBundleManifest,
    CalibrationEvidenceRow,
    CalibrationEvidenceSummary,
    MatrixResponsePreviewRow,
    MatrixRTPreviewRow,
    RtDriftModelRow,
    RtLeaveOneAnchorOutRow,
)
from xic_extractor.tabular_io import write_tsv

CALIBRATION_EVIDENCE_COLUMNS = [
    "schema_version",
    "bundle_id",
    "evidence_row_id",
    "source_artifact_id",
    "source_artifact_hash",
    "source_type",
    "matrix_context",
    "sample_name",
    "raw_stem",
    "source_raw_file",
    "raw_path_kind",
    "injection_order",
    "compound",
    "compound_group",
    "precursor_mz",
    "observed_mz",
    "mz_ppm_error",
    "reference_rt_min",
    "observed_rt_min",
    "rt_delta_min",
    "rt_region",
    "area",
    "height",
    "log2_area_delta",
    "log2_height_delta",
    "peak_width_min",
    "activation_method",
    "product_support_status",
    "neutral_loss_support_status",
    "evidence_confidence",
    "calibration_eligible",
    "coverage_status",
    "exclusion_reason",
]

MATRIX_RT_PREVIEW_COLUMNS = [
    "schema_version",
    "bundle_id",
    "matrix_source",
    "matrix_source_hash",
    "matrix_schema_version",
    "source_row_id",
    "source_cell_key",
    "feature_id",
    "matrix_column_name",
    "sample_name",
    "sample_stem",
    "raw_file_stem",
    "feature_mz",
    "raw_feature_rt_min",
    "injection_order",
    "model_id",
    "predicted_rt_delta_min",
    "rt_uncertainty_min",
    "rt_if_standard_corrected_min",
    "coverage_status",
    "rt_alignment_support_status",
    "local_anchor_count",
    "local_clean_anchor_count",
    "local_biological_istd_anchor_count",
    "local_residual_p95_min",
    "irt_anchor_scope",
    "irt_position",
    "correction_status",
    "correction_block_reason",
    "review_reason",
]

RT_DRIFT_MODEL_COLUMNS = [
    "schema_version",
    "bundle_id",
    "model_id",
    "model_scope",
    "compound",
    "compound_group",
    "source_type",
    "matrix_context",
    "injection_order",
    "rt_region",
    "source_mix",
    "anchor_ids",
    "anchor_count",
    "clean_anchor_count",
    "biological_istd_anchor_count",
    "predicted_rt_delta_min",
    "rt_uncertainty_min",
    "coverage_status",
    "conflict_status",
    "model_status",
    "review_reason",
]

RT_LEAVE_ONE_ANCHOR_OUT_COLUMNS = [
    "schema_version",
    "bundle_id",
    "evidence_row_id",
    "compound",
    "source_type",
    "matrix_context",
    "injection_order",
    "reference_rt_min",
    "observed_rt_delta_min",
    "predicted_rt_delta_min",
    "prediction_error_min",
    "abs_prediction_error_min",
    "local_anchor_count",
    "coverage_status",
    "status",
    "review_reason",
]

MATRIX_RESPONSE_PREVIEW_COLUMNS = [
    "schema_version",
    "bundle_id",
    "matrix_source",
    "matrix_source_hash",
    "matrix_schema_version",
    "source_row_id",
    "source_cell_key",
    "feature_id",
    "matrix_column_name",
    "sample_name",
    "sample_stem",
    "raw_file_stem",
    "feature_mz",
    "raw_feature_rt_min",
    "injection_order",
    "raw_area",
    "raw_area_status",
    "raw_height",
    "raw_height_status",
    "model_id",
    "predicted_log2_response_delta",
    "area_if_response_corrected",
    "height_if_response_corrected",
    "preview_area_status",
    "preview_height_status",
    "response_uncertainty_log2",
    "transfer_status",
    "correction_status",
    "correction_block_reason",
    "review_reason",
]


def write_calibration_manifest_json(
    path: Path,
    manifest: CalibrationBundleManifest,
) -> None:
    _write_json(path, _to_jsonable(manifest))


def write_calibration_evidence_summary_json(
    path: Path,
    summary: CalibrationEvidenceSummary,
) -> None:
    _write_json(path, _to_jsonable(summary))


def write_calibration_evidence_tsv(
    path: Path,
    rows: Iterable[CalibrationEvidenceRow],
) -> None:
    _write_tsv_rows(path, rows, CALIBRATION_EVIDENCE_COLUMNS)


def write_matrix_rt_preview_tsv(
    path: Path,
    rows: Iterable[MatrixRTPreviewRow],
) -> None:
    _write_tsv_rows(path, rows, MATRIX_RT_PREVIEW_COLUMNS)


def write_rt_drift_model_tsv(
    path: Path,
    rows: Iterable[RtDriftModelRow],
) -> None:
    _write_tsv_rows(path, rows, RT_DRIFT_MODEL_COLUMNS)


def write_rt_leave_one_anchor_out_tsv(
    path: Path,
    rows: Iterable[RtLeaveOneAnchorOutRow],
) -> None:
    _write_tsv_rows(path, rows, RT_LEAVE_ONE_ANCHOR_OUT_COLUMNS)


def write_matrix_response_preview_tsv(
    path: Path,
    rows: Iterable[MatrixResponsePreviewRow],
) -> None:
    _write_tsv_rows(path, rows, MATRIX_RESPONSE_PREVIEW_COLUMNS)


def write_preview_summary_json(path: Path, payload: dict[str, Any]) -> None:
    _write_json(path, payload)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _write_tsv_rows(path: Path, rows: Iterable[Any], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    write_tsv(
        path,
        tuple(_row_to_dict(row, columns) for row in rows),
        columns,
    )


def _row_to_dict(row: Any, columns: list[str]) -> dict[str, str]:
    values = _to_jsonable(row)
    return {column: _format_tsv_value(values.get(column)) for column in columns}


def _to_jsonable(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value) and not isinstance(value, type):
        return {key: _to_jsonable(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {str(key): _to_jsonable(item) for key, item in value.items()}
    if isinstance(value, tuple | list):
        return [_to_jsonable(item) for item in value]
    return value


def _format_tsv_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, list):
        return ";".join(_format_tsv_value(item) for item in value)
    return str(value)
