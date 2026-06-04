from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from xic_extractor.alignment.config import AlignmentConfig
from xic_extractor.alignment.matrix import AlignedCell, AlignmentMatrix
from xic_extractor.alignment.output_rows import (
    cells_by_cluster,
    format_value,
    production_matrix_area,
    row_id,
)
from xic_extractor.alignment.production_decisions import (
    ProductionCellDecision,
    ProductionDecisionSet,
    build_production_decisions,
)

MATRIX_IDENTITY_SCHEMA_VERSION = "untargeted_peak_hypothesis_matrix_identity_v1"

ALIGNMENT_MATRIX_IDENTITY_COLUMNS = (
    "identity_schema_version",
    "matrix_row_index",
    "Mz",
    "RT",
    "peak_hypothesis_id",
    "row_identity_basis",
    "split_evaluation_status",
    "projection_status",
    "source_feature_family_ids",
    "source_feature_family_count",
    "center_mz_basis",
    "center_rt_basis",
    "center_weight_basis",
    "accepted_cell_count",
    "accepted_sample_count",
    "evidence_status",
    "parent_peak_hypothesis_id",
    "child_peak_hypothesis_ids",
)

_ALLOWED_ROW_IDENTITY_BASIS = {
    "no_split_peak_hypothesis",
    "split_peak_hypothesis",
}
_FORBIDDEN_ROW_IDENTITY_BASIS = {
    "family_projection",
    "family_projection_no_split_evidence",
}
_ALLOWED_SPLIT_EVALUATION_STATUS = {
    "complete_no_product_ready_split",
    "complete_product_ready_split",
}


@dataclass(frozen=True)
class ProductMatrixRow:
    matrix_row_index: int
    peak_hypothesis_id: str
    mz: float
    rt: float
    sample_values: dict[str, str]
    identity: dict[str, object]


def build_product_matrix_rows(
    matrix: AlignmentMatrix,
    *,
    alignment_config: AlignmentConfig | None = None,
) -> tuple[ProductMatrixRow, ...]:
    config = alignment_config or AlignmentConfig()
    decisions = build_production_decisions(matrix, config)
    grouped_cells = cells_by_cluster(matrix)
    rows: list[ProductMatrixRow] = []
    seen_source_candidates: dict[str, str] = {}

    for cluster in matrix.clusters:
        cluster_id = row_id(cluster)
        row_decision = decisions.row(cluster_id)
        if not row_decision.include_in_primary_matrix:
            continue
        cluster_cells = grouped_cells.get(cluster_id, ())
        product_cells = _product_cells(cluster_id, cluster_cells, decisions)
        for cell, _decision in product_cells:
            if cell.source_candidate_id is None:
                continue
            previous = seen_source_candidates.setdefault(
                cell.source_candidate_id,
                cluster_id,
            )
            if previous != cluster_id:
                raise ValueError(
                    "source peak cannot contribute to multiple product "
                    f"hypothesis rows: {cell.source_candidate_id}"
                )
        identity = _identity_row(
            cluster,
            matrix_row_index=len(rows) + 1,
            product_cells=product_cells,
        )
        sample_values = {}
        for sample_stem in matrix.sample_order:
            decision = (
                decisions.cell(cluster_id, sample_stem)
                if any(cell.sample_stem == sample_stem for cell in cluster_cells)
                else None
            )
            sample_values[sample_stem] = production_matrix_area(decision)
        rows.append(
            ProductMatrixRow(
                matrix_row_index=len(rows) + 1,
                peak_hypothesis_id=str(identity["peak_hypothesis_id"]),
                mz=_float_identity_value(identity["Mz"], name="Mz"),
                rt=_float_identity_value(identity["RT"], name="RT"),
                sample_values=sample_values,
                identity=identity,
            )
        )
    return tuple(rows)


def product_matrix_tsv_rows(
    matrix: AlignmentMatrix,
    *,
    alignment_config: AlignmentConfig | None = None,
) -> list[dict[str, object]]:
    return [
        {"Mz": row.mz, "RT": row.rt, **row.sample_values}
        for row in build_product_matrix_rows(
            matrix,
            alignment_config=alignment_config,
        )
    ]


def product_matrix_identity_rows(
    matrix: AlignmentMatrix,
    *,
    alignment_config: AlignmentConfig | None = None,
) -> list[dict[str, object]]:
    return [
        row.identity
        for row in build_product_matrix_rows(
            matrix,
            alignment_config=alignment_config,
        )
    ]


def _identity_row(
    cluster: Any,
    *,
    matrix_row_index: int,
    product_cells: tuple[tuple[AlignedCell, ProductionCellDecision], ...],
) -> dict[str, object]:
    cluster_id = row_id(cluster)
    row_identity_basis = str(
        getattr(cluster, "row_identity_basis", "no_split_peak_hypothesis")
    )
    split_evaluation_status = str(
        getattr(
            cluster,
            "split_evaluation_status",
            (
                "complete_product_ready_split"
                if row_identity_basis == "split_peak_hypothesis"
                else "complete_no_product_ready_split"
            ),
        )
    )
    projection_status = str(getattr(cluster, "projection_status", "not_projection"))
    _validate_identity_tokens(
        cluster_id,
        row_identity_basis=row_identity_basis,
        split_evaluation_status=split_evaluation_status,
        projection_status=projection_status,
    )
    source_ids = _source_feature_family_ids(cluster, fallback=cluster_id)
    mz = _family_center_mz(cluster)
    rt, rt_basis = _center_rt(cluster, product_cells)
    child_peak_hypothesis_ids = _child_peak_hypothesis_ids(cluster)
    if child_peak_hypothesis_ids:
        raise ValueError(
            f"{cluster_id}: parent aggregate product row cannot write beside "
            f"child hypotheses {child_peak_hypothesis_ids}"
        )
    accepted_samples = {
        cell.sample_stem
        for cell, decision in product_cells
        if decision.write_matrix_value
    }
    return {
        "identity_schema_version": MATRIX_IDENTITY_SCHEMA_VERSION,
        "matrix_row_index": matrix_row_index,
        "Mz": mz,
        "RT": rt,
        "peak_hypothesis_id": str(
            getattr(cluster, "peak_hypothesis_id", cluster_id)
        ),
        "row_identity_basis": row_identity_basis,
        "split_evaluation_status": split_evaluation_status,
        "projection_status": projection_status,
        "source_feature_family_ids": ";".join(source_ids),
        "source_feature_family_count": len(source_ids),
        "center_mz_basis": str(
            getattr(cluster, "center_mz_basis", "source_family_center_mz")
        ),
        "center_rt_basis": str(getattr(cluster, "center_rt_basis", rt_basis)),
        "center_weight_basis": str(
            getattr(cluster, "center_weight_basis", "primary_matrix_area")
        ),
        "accepted_cell_count": len(product_cells),
        "accepted_sample_count": len(accepted_samples),
        "evidence_status": str(
            getattr(cluster, "evidence_status", "product_matrix_identity_complete")
        ),
        "parent_peak_hypothesis_id": str(
            getattr(cluster, "parent_peak_hypothesis_id", "")
        ),
        "child_peak_hypothesis_ids": child_peak_hypothesis_ids,
    }


def _validate_identity_tokens(
    cluster_id: str,
    *,
    row_identity_basis: str,
    split_evaluation_status: str,
    projection_status: str,
) -> None:
    if row_identity_basis in _FORBIDDEN_ROW_IDENTITY_BASIS:
        raise ValueError(
            f"{cluster_id}: product matrix row cannot use {row_identity_basis}"
        )
    if row_identity_basis not in _ALLOWED_ROW_IDENTITY_BASIS:
        raise ValueError(
            f"{cluster_id}: unsupported product row_identity_basis "
            f"{row_identity_basis}"
        )
    if split_evaluation_status not in _ALLOWED_SPLIT_EVALUATION_STATUS:
        raise ValueError(
            f"{cluster_id}: unsupported product split_evaluation_status "
            f"{split_evaluation_status}"
        )
    if projection_status != "not_projection":
        raise ValueError(
            f"{cluster_id}: product projection_status must be not_projection, "
            f"got {projection_status}"
        )
    if (
        row_identity_basis == "no_split_peak_hypothesis"
        and split_evaluation_status != "complete_no_product_ready_split"
    ):
        raise ValueError(
            f"{cluster_id}: no-split product row requires "
            "complete_no_product_ready_split"
        )
    if (
        row_identity_basis == "split_peak_hypothesis"
        and split_evaluation_status != "complete_product_ready_split"
    ):
        raise ValueError(
            f"{cluster_id}: split product row requires complete_product_ready_split"
        )


def _product_cells(
    cluster_id: str,
    cells: tuple[AlignedCell, ...],
    decisions: ProductionDecisionSet,
) -> tuple[tuple[AlignedCell, ProductionCellDecision], ...]:
    product_cells = []
    for cell in cells:
        decision = decisions.cell(cluster_id, cell.sample_stem)
        if decision.write_matrix_value:
            product_cells.append((cell, decision))
    return tuple(product_cells)


def _source_feature_family_ids(cluster: Any, *, fallback: str) -> tuple[str, ...]:
    raw_value = getattr(cluster, "source_feature_family_ids", None)
    if raw_value is None:
        return (fallback,)
    if isinstance(raw_value, str):
        values = tuple(part for part in raw_value.split(";") if part)
    else:
        values = tuple(str(part) for part in raw_value if str(part))
    return tuple(dict.fromkeys(values)) or (fallback,)


def _float_identity_value(value: object, *, name: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be numeric")
    if isinstance(value, (int, float)):
        return float(value)
    raise ValueError(f"{name} must be numeric")


def _child_peak_hypothesis_ids(cluster: Any) -> str:
    raw_value = getattr(cluster, "child_peak_hypothesis_ids", "")
    if isinstance(raw_value, str):
        return raw_value
    return ";".join(str(part) for part in raw_value)


def _family_center_mz(row: Any) -> float:
    if hasattr(row, "family_center_mz"):
        return float(row.family_center_mz)
    return float(row.cluster_center_mz)


def _family_center_rt(row: Any) -> float:
    if hasattr(row, "family_center_rt"):
        return float(row.family_center_rt)
    return float(row.cluster_center_rt)


def _center_rt(
    cluster: Any,
    product_cells: tuple[tuple[AlignedCell, ProductionCellDecision], ...],
) -> tuple[float, str]:
    weighted_sum = 0.0
    weight_sum = 0.0
    for cell, decision in product_cells:
        if cell.apex_rt is None or decision.matrix_value is None:
            continue
        if not math.isfinite(cell.apex_rt):
            continue
        weight = decision.matrix_value
        if not math.isfinite(weight) or weight <= 0:
            continue
        weighted_sum += cell.apex_rt * weight
        weight_sum += weight
    if weight_sum > 0:
        return weighted_sum / weight_sum, "accepted_cell_area_weighted_apex_rt"
    return _family_center_rt(cluster), "source_family_center_rt"


def formatted_identity_rows(
    matrix: AlignmentMatrix,
    *,
    alignment_config: AlignmentConfig | None = None,
) -> list[dict[str, object]]:
    rows = product_matrix_identity_rows(matrix, alignment_config=alignment_config)
    return [
        {
            column: format_value(row.get(column, ""))
            for column in ALIGNMENT_MATRIX_IDENTITY_COLUMNS
        }
        for row in rows
    ]
