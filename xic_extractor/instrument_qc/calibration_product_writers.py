from __future__ import annotations

import csv
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
)

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
    "correction_status",
    "correction_block_reason",
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
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=CALIBRATION_EVIDENCE_COLUMNS,
            delimiter="\t",
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(_row_to_dict(row, CALIBRATION_EVIDENCE_COLUMNS))


def write_matrix_rt_preview_tsv(
    path: Path,
    rows: Iterable[MatrixRTPreviewRow],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=MATRIX_RT_PREVIEW_COLUMNS,
            delimiter="\t",
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(_row_to_dict(row, MATRIX_RT_PREVIEW_COLUMNS))


def write_matrix_response_preview_tsv(
    path: Path,
    rows: Iterable[MatrixResponsePreviewRow],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=MATRIX_RESPONSE_PREVIEW_COLUMNS,
            delimiter="\t",
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(_row_to_dict(row, MATRIX_RESPONSE_PREVIEW_COLUMNS))


def write_preview_summary_json(path: Path, payload: dict[str, Any]) -> None:
    _write_json(path, payload)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


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
