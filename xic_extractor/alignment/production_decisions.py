from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Literal

from xic_extractor.alignment.config import AlignmentConfig
from xic_extractor.alignment.matrix import AlignedCell, AlignmentMatrix
from xic_extractor.alignment.output_rows import cells_by_cluster, row_id

ProductionStatus = Literal[
    "detected",
    "accepted_rescue",
    "review_rescue",
    "rejected_rescue",
    "blank",
]
RescueTier = Literal["", "accepted_rescue", "review_rescue", "rejected_rescue"]


@dataclass(frozen=True)
class ProductionCellDecision:
    feature_family_id: str
    sample_stem: str
    raw_status: str
    production_status: ProductionStatus
    rescue_tier: RescueTier
    write_matrix_value: bool
    matrix_value: float | None
    blank_reason: str


@dataclass(frozen=True)
class ProductionRowDecision:
    feature_family_id: str
    include_in_primary_matrix: bool
    accepted_cell_count: int
    detected_count: int
    accepted_rescue_count: int
    review_rescue_count: int
    duplicate_assigned_count: int
    row_flags: tuple[str, ...]


@dataclass(frozen=True)
class ProductionDecisionSet:
    cells: dict[tuple[str, str], ProductionCellDecision]
    rows: dict[str, ProductionRowDecision]

    def cell(self, feature_family_id: str, sample_stem: str) -> ProductionCellDecision:
        return self.cells[(feature_family_id, sample_stem)]

    def row(self, feature_family_id: str) -> ProductionRowDecision:
        return self.rows[feature_family_id]


def build_production_decisions(
    matrix: AlignmentMatrix,
    config: AlignmentConfig,
) -> ProductionDecisionSet:
    grouped_cells = cells_by_cluster(matrix)
    cell_decisions: dict[tuple[str, str], ProductionCellDecision] = {}
    row_decisions: dict[str, ProductionRowDecision] = {}

    for cluster in matrix.clusters:
        cluster_id = row_id(cluster)
        cluster_cells = grouped_cells.get(cluster_id, ())
        row_anchor_lost = _identity_anchor_lost(cluster_cells)
        row_has_identity = _has_row_identity_support(cluster) and not row_anchor_lost

        for cell in cluster_cells:
            decision = _cell_decision(
                cell,
                config=config,
                row_has_identity=row_has_identity,
            )
            cell_decisions[(cell.cluster_id, cell.sample_stem)] = decision

        decisions = tuple(
            cell_decisions[(cell.cluster_id, cell.sample_stem)]
            for cell in cluster_cells
        )
        row_decisions[cluster_id] = _row_decision(
            cluster_id,
            cluster_cells,
            decisions,
            row_anchor_lost=row_anchor_lost,
        )

    return ProductionDecisionSet(cells=cell_decisions, rows=row_decisions)


def _cell_decision(
    cell: AlignedCell,
    *,
    config: AlignmentConfig,
    row_has_identity: bool,
) -> ProductionCellDecision:
    if cell.status == "detected":
        area = _valid_area(cell.area)
        if area is None:
            return _blank(cell, "blank", "", "invalid_area")
        if not row_has_identity:
            return _blank(cell, "blank", "", "missing_row_identity_support")
        return ProductionCellDecision(
            feature_family_id=cell.cluster_id,
            sample_stem=cell.sample_stem,
            raw_status=cell.status,
            production_status="detected",
            rescue_tier="",
            write_matrix_value=True,
            matrix_value=area,
            blank_reason="",
        )
    if cell.status == "rescued":
        return _rescue_decision(
            cell,
            config=config,
            row_has_identity=row_has_identity,
        )
    if cell.status == "duplicate_assigned":
        return _blank(cell, "blank", "", "duplicate_loser")
    if cell.status == "ambiguous_ms1_owner":
        return _blank(cell, "blank", "", "ambiguous_ms1_owner")
    if cell.status == "absent":
        return _blank(cell, "blank", "", "absent")
    if cell.status == "unchecked":
        return _blank(cell, "blank", "", "unchecked")
    return _blank(cell, "blank", "", f"unsupported_status:{cell.status}")


def _rescue_decision(
    cell: AlignedCell,
    *,
    config: AlignmentConfig,
    row_has_identity: bool,
) -> ProductionCellDecision:
    area = _valid_area(cell.area)
    if area is None:
        return _blank(cell, "rejected_rescue", "rejected_rescue", "invalid_area")
    if not row_has_identity:
        return _blank(
            cell,
            "review_rescue",
            "review_rescue",
            "missing_row_identity_support",
        )
    if not _has_complete_peak(cell):
        return _blank(cell, "review_rescue", "review_rescue", "incomplete_peak")
    if cell.rt_delta_sec is None or abs(cell.rt_delta_sec) > config.max_rt_sec:
        return _blank(cell, "review_rescue", "review_rescue", "rt_outside_max")
    return ProductionCellDecision(
        feature_family_id=cell.cluster_id,
        sample_stem=cell.sample_stem,
        raw_status=cell.status,
        production_status="accepted_rescue",
        rescue_tier="accepted_rescue",
        write_matrix_value=True,
        matrix_value=area,
        blank_reason="",
    )


def _row_decision(
    cluster_id: str,
    cells: tuple[AlignedCell, ...],
    decisions: tuple[ProductionCellDecision, ...],
    *,
    row_anchor_lost: bool,
) -> ProductionRowDecision:
    detected_count = sum(1 for cell in cells if cell.status == "detected")
    accepted_rescue_count = sum(
        1 for decision in decisions if decision.production_status == "accepted_rescue"
    )
    review_rescue_count = sum(
        1 for decision in decisions if decision.production_status == "review_rescue"
    )
    duplicate_count = sum(1 for cell in cells if cell.status == "duplicate_assigned")
    accepted_cell_count = sum(
        1 for decision in decisions if decision.write_matrix_value
    )

    flags: list[str] = []
    if accepted_rescue_count > detected_count and detected_count > 0:
        flags.append("rescue_heavy")
    if accepted_cell_count == 0 and review_rescue_count > 0:
        flags.append("rescue_only_review")
    if duplicate_count > 0:
        flags.append("duplicate_claim_pressure")
    if row_anchor_lost:
        flags.append("identity_anchor_lost")

    return ProductionRowDecision(
        feature_family_id=cluster_id,
        include_in_primary_matrix=accepted_cell_count > 0 and not row_anchor_lost,
        accepted_cell_count=accepted_cell_count,
        detected_count=detected_count,
        accepted_rescue_count=accepted_rescue_count,
        review_rescue_count=review_rescue_count,
        duplicate_assigned_count=duplicate_count,
        row_flags=tuple(flags),
    )


def _blank(
    cell: AlignedCell,
    production_status: ProductionStatus,
    rescue_tier: RescueTier,
    blank_reason: str,
) -> ProductionCellDecision:
    return ProductionCellDecision(
        feature_family_id=cell.cluster_id,
        sample_stem=cell.sample_stem,
        raw_status=cell.status,
        production_status=production_status,
        rescue_tier=rescue_tier,
        write_matrix_value=False,
        matrix_value=None,
        blank_reason=blank_reason,
    )


def _valid_area(value: float | None) -> float | None:
    if (
        value is None
        or isinstance(value, bool)
        or not math.isfinite(value)
        or value <= 0
    ):
        return None
    return float(value)


def _has_complete_peak(cell: AlignedCell) -> bool:
    return all(
        _finite(value)
        for value in (
            cell.apex_rt,
            cell.height,
            cell.peak_start_rt,
            cell.peak_end_rt,
        )
    )


def _finite(value: object) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _has_row_identity_support(cluster: Any) -> bool:
    if bool(getattr(cluster, "review_only", False)):
        return False
    evidence = _family_evidence(cluster)
    if evidence in {"single_sample_local_owner", "owner_identity"}:
        return True
    if evidence.startswith("owner_complete_link;"):
        return True
    if evidence.startswith("cid_nl_only;"):
        return True
    if bool(getattr(cluster, "has_anchor", False)):
        return True
    return False


def _identity_anchor_lost(cells: tuple[AlignedCell, ...]) -> bool:
    if any(cell.status == "detected" for cell in cells):
        return False
    has_duplicate_detected = any(
        cell.status == "duplicate_assigned"
        and "original_status=detected" in cell.reason
        for cell in cells
    )
    has_rescue = any(cell.status == "rescued" for cell in cells)
    return has_duplicate_detected and has_rescue


def _family_evidence(cluster: Any) -> str:
    if hasattr(cluster, "evidence"):
        return str(cluster.evidence)
    if hasattr(cluster, "fold_evidence"):
        return str(cluster.fold_evidence)
    return ""
