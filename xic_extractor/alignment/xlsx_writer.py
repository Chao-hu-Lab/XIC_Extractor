from __future__ import annotations

from pathlib import Path
from typing import Any

from openpyxl import Workbook

from xic_extractor.alignment.matrix import AlignedCell, AlignmentMatrix
from xic_extractor.alignment.output_rows import (
    cells_by_cluster,
    count_status,
    matrix_area,
    row_id,
)


def write_alignment_results_xlsx(
    path: Path,
    matrix: AlignmentMatrix,
    *,
    metadata: dict[str, str],
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    workbook = Workbook()
    matrix_sheet = workbook.active
    matrix_sheet.title = "Matrix"
    _write_matrix_sheet(matrix_sheet, matrix)
    _write_review_sheet(workbook.create_sheet("Review"), matrix)
    _write_metadata_sheet(workbook.create_sheet("Metadata"), metadata)
    workbook.save(path)
    return path


def _write_matrix_sheet(sheet: Any, matrix: AlignmentMatrix) -> None:
    headers = [
        "feature_family_id",
        "neutral_loss_tag",
        "family_center_mz",
        "family_center_rt",
        *matrix.sample_order,
    ]
    sheet.append(headers)
    grouped_cells = cells_by_cluster(matrix)
    for cluster in matrix.clusters:
        cluster_id = row_id(cluster)
        cells = {
            cell.sample_stem: cell for cell in grouped_cells.get(cluster_id, ())
        }
        sheet.append(
            [
                cluster_id,
                cluster.neutral_loss_tag,
                _family_center_mz(cluster),
                _family_center_rt(cluster),
                *[_xlsx_area(cells.get(sample)) for sample in matrix.sample_order],
            ],
        )


def _write_review_sheet(sheet: Any, matrix: AlignmentMatrix) -> None:
    sheet.append(
        [
            "feature_family_id",
            "neutral_loss_tag",
            "detected_count",
            "rescued_count",
            "absent_count",
            "unchecked_count",
            "duplicate_assigned_count",
            "ambiguous_ms1_owner_count",
        ],
    )
    grouped_cells = cells_by_cluster(matrix)
    for cluster in matrix.clusters:
        cluster_id = row_id(cluster)
        cells = grouped_cells.get(cluster_id, ())
        sheet.append(
            [
                cluster_id,
                cluster.neutral_loss_tag,
                count_status(cells, "detected"),
                count_status(cells, "rescued"),
                count_status(cells, "absent"),
                count_status(cells, "unchecked"),
                count_status(cells, "duplicate_assigned"),
                count_status(cells, "ambiguous_ms1_owner"),
            ],
        )


def _write_metadata_sheet(sheet: Any, metadata: dict[str, str]) -> None:
    sheet.append(["key", "value"])
    for key in sorted(metadata):
        sheet.append([key, metadata[key]])


def _xlsx_area(cell: AlignedCell | None) -> float | None:
    text = matrix_area(cell)
    return float(text) if text else None


def _family_center_mz(row: Any) -> float:
    if hasattr(row, "family_center_mz"):
        return row.family_center_mz
    return row.cluster_center_mz


def _family_center_rt(row: Any) -> float:
    if hasattr(row, "family_center_rt"):
        return row.family_center_rt
    return row.cluster_center_rt
