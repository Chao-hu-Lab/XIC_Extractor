from __future__ import annotations

from collections import defaultdict
from dataclasses import replace
from typing import Iterable

from xic_extractor.alignment.config import AlignmentConfig
from xic_extractor.alignment.matrix import AlignedCell, AlignmentMatrix
from xic_extractor.alignment.models import AlignmentCluster

_PRESENT_STATUSES = {"detected", "rescued"}
_DETECTED_STATUSES = {"detected"}


def fold_near_duplicate_clusters(
    matrix: AlignmentMatrix,
    *,
    config: AlignmentConfig,
) -> AlignmentMatrix:
    cells_by_cluster = _cells_by_cluster(matrix.cells)
    original_index = {
        cluster.cluster_id: index for index, cluster in enumerate(matrix.clusters)
    }
    groups: list[list[AlignmentCluster]] = []
    consumed: set[str] = set()

    for cluster in matrix.clusters:
        if cluster.cluster_id in consumed:
            continue
        group = [cluster]
        for candidate in matrix.clusters:
            if (
                candidate.cluster_id == cluster.cluster_id
                or candidate.cluster_id in consumed
            ):
                continue
            if _can_join_fold_group(
                candidate,
                group,
                cells_by_cluster=cells_by_cluster,
                config=config,
            ):
                group.append(candidate)
                consumed.add(candidate.cluster_id)
        consumed.add(cluster.cluster_id)
        groups.append(group)

    folded_clusters: list[AlignmentCluster] = []
    folded_cells: list[AlignedCell] = []
    for group in sorted(
        groups,
        key=lambda fold_group: original_index[
            min(
                fold_group,
                key=lambda cluster: _primary_sort_key(cluster, cells_by_cluster),
            ).cluster_id
        ],
    ):
        primary = min(
            group,
            key=lambda cluster: _primary_sort_key(cluster, cells_by_cluster),
        )
        secondaries = [
            cluster for cluster in group if cluster.cluster_id != primary.cluster_id
        ]
        merged_cells = _merged_cells_for_group(
            primary,
            secondaries,
            sample_order=matrix.sample_order,
            cells_by_cluster=cells_by_cluster,
        )
        folded_clusters.append(
            _with_fold_metadata(
                primary,
                secondaries,
                cells_by_cluster=cells_by_cluster,
                merged_cells=merged_cells,
            ),
        )
        folded_cells.extend(merged_cells)

    return AlignmentMatrix(
        clusters=tuple(folded_clusters),
        cells=tuple(folded_cells),
        sample_order=matrix.sample_order,
    )


def _can_join_fold_group(
    candidate: AlignmentCluster,
    group: list[AlignmentCluster],
    *,
    cells_by_cluster: dict[str, tuple[AlignedCell, ...]],
    config: AlignmentConfig,
) -> bool:
    return all(
        _clusters_are_fold_compatible(
            candidate,
            existing,
            cells_by_cluster=cells_by_cluster,
            config=config,
        )
        for existing in group
    )


def _clusters_are_fold_compatible(
    left: AlignmentCluster,
    right: AlignmentCluster,
    *,
    cells_by_cluster: dict[str, tuple[AlignedCell, ...]],
    config: AlignmentConfig,
) -> bool:
    if left.neutral_loss_tag != right.neutral_loss_tag:
        return False
    if _exceeds(
        _ppm(left.cluster_center_mz, right.cluster_center_mz),
        config.duplicate_fold_ppm,
    ):
        return False
    if (
        _exceeds(
            abs(left.cluster_center_rt - right.cluster_center_rt) * 60.0,
            config.duplicate_fold_rt_sec,
        )
    ):
        return False
    if _ms2_signature_conflicts(left, right):
        return False
    if (
        _exceeds(
            _ppm(left.cluster_product_mz, right.cluster_product_mz),
            config.duplicate_fold_product_ppm,
        )
    ):
        return False
    if (
        _exceeds(
            _ppm(
                left.cluster_observed_neutral_loss_da,
                right.cluster_observed_neutral_loss_da,
            ),
            config.duplicate_fold_observed_loss_ppm,
        )
    ):
        return False

    left_cells = cells_by_cluster.get(left.cluster_id, ())
    right_cells = cells_by_cluster.get(right.cluster_id, ())
    detected_overlap = _overlap_coefficient(
        left_cells,
        right_cells,
        statuses=_DETECTED_STATUSES,
    )
    present_overlap = _overlap_coefficient(
        left_cells,
        right_cells,
        statuses=_PRESENT_STATUSES,
    )
    detected_jaccard = _jaccard(
        left_cells,
        right_cells,
        statuses=_DETECTED_STATUSES,
    )
    shared_detected_count = _shared_count(
        left_cells,
        right_cells,
        statuses=_DETECTED_STATUSES,
    )
    return (
        detected_overlap >= config.duplicate_fold_min_detected_overlap
        and shared_detected_count >= config.duplicate_fold_min_shared_detected_count
        and detected_jaccard >= config.duplicate_fold_min_detected_jaccard
        and present_overlap >= config.duplicate_fold_min_present_overlap
    )


def _with_fold_metadata(
    primary: AlignmentCluster,
    secondaries: list[AlignmentCluster],
    *,
    cells_by_cluster: dict[str, tuple[AlignedCell, ...]],
    merged_cells: list[AlignedCell],
) -> AlignmentCluster:
    return replace(
        primary,
        folded_cluster_ids=tuple(cluster.cluster_id for cluster in secondaries),
        folded_member_count=sum(len(cluster.members) for cluster in secondaries),
        folded_sample_fill_count=sum(
            1 for cell in merged_cells if "folded from" in cell.reason
        ),
        fold_evidence=_fold_evidence_summary(
            primary,
            secondaries,
            cells_by_cluster=cells_by_cluster,
        ),
    )


def _merged_cells_for_group(
    primary: AlignmentCluster,
    secondaries: list[AlignmentCluster],
    *,
    sample_order: tuple[str, ...],
    cells_by_cluster: dict[str, tuple[AlignedCell, ...]],
) -> list[AlignedCell]:
    primary_by_sample = _cells_by_sample(cells_by_cluster.get(primary.cluster_id, ()))
    secondary_by_sample = {
        cluster.cluster_id: _cells_by_sample(
            cells_by_cluster.get(cluster.cluster_id, ()),
        )
        for cluster in secondaries
    }
    merged: list[AlignedCell] = []
    for sample in sample_order:
        primary_cell = primary_by_sample.get(sample)
        if primary_cell is not None and primary_cell.status in _PRESENT_STATUSES:
            merged.append(primary_cell)
            continue
        replacement = _best_present_secondary_cell(sample, secondary_by_sample)
        if replacement is not None:
            merged.append(
                replace(
                    replacement,
                    cluster_id=primary.cluster_id,
                    reason=(
                        f"{replacement.reason}; "
                        f"folded from {replacement.cluster_id}"
                    ),
                ),
            )
        elif primary_cell is not None:
            merged.append(primary_cell)
    return merged


def _best_present_secondary_cell(
    sample: str,
    secondary_by_sample: dict[str, dict[str, AlignedCell]],
) -> AlignedCell | None:
    candidates = [
        cell
        for cells in secondary_by_sample.values()
        for cell in (cells.get(sample),)
        if cell is not None and cell.status in _PRESENT_STATUSES
    ]
    if not candidates:
        return None
    return min(candidates, key=_secondary_cell_sort_key)


def _secondary_cell_sort_key(cell: AlignedCell) -> tuple[object, ...]:
    scan_support = (
        cell.scan_support_score if cell.scan_support_score is not None else -1.0
    )
    rt_delta = abs(cell.rt_delta_sec) if cell.rt_delta_sec is not None else float("inf")
    area = cell.area if cell.area is not None and cell.area > 0 else 0.0
    return (
        0 if cell.status == "detected" else 1,
        -scan_support,
        _trace_quality_rank(cell.trace_quality),
        rt_delta,
        -area,
        cell.cluster_id,
    )


def _trace_quality_rank(value: str) -> int:
    return {"clean": 0, "weak": 1, "poor": 2}.get(value, 3)


def _fold_evidence_summary(
    primary: AlignmentCluster,
    secondaries: list[AlignmentCluster],
    *,
    cells_by_cluster: dict[str, tuple[AlignedCell, ...]],
) -> str:
    if not secondaries:
        return ""
    mz_ppms = [
        _ppm(primary.cluster_center_mz, secondary.cluster_center_mz)
        for secondary in secondaries
    ]
    rt_secs = [
        abs(primary.cluster_center_rt - secondary.cluster_center_rt) * 60.0
        for secondary in secondaries
    ]
    shared_detected = [
        _shared_count(
            cells_by_cluster.get(primary.cluster_id, ()),
            cells_by_cluster.get(secondary.cluster_id, ()),
            statuses=_DETECTED_STATUSES,
        )
        for secondary in secondaries
    ]
    detected_jaccards = [
        _jaccard(
            cells_by_cluster.get(primary.cluster_id, ()),
            cells_by_cluster.get(secondary.cluster_id, ()),
            statuses=_DETECTED_STATUSES,
        )
        for secondary in secondaries
    ]
    return (
        "cid_nl_only;"
        f"max_mz_ppm={max(mz_ppms):.3g};"
        f"max_rt_sec={max(rt_secs):.3g};"
        f"min_shared_detected={min(shared_detected)};"
        f"min_detected_jaccard={min(detected_jaccards):.3g}"
    )


def _cells_by_cluster(
    cells: Iterable[AlignedCell],
) -> dict[str, tuple[AlignedCell, ...]]:
    grouped: dict[str, list[AlignedCell]] = defaultdict(list)
    for cell in cells:
        grouped[cell.cluster_id].append(cell)
    return {cluster_id: tuple(values) for cluster_id, values in grouped.items()}


def _cells_by_sample(cells: tuple[AlignedCell, ...]) -> dict[str, AlignedCell]:
    return {cell.sample_stem: cell for cell in cells}


def _overlap_coefficient(
    left_cells: tuple[AlignedCell, ...],
    right_cells: tuple[AlignedCell, ...],
    *,
    statuses: set[str],
) -> float:
    left = _sample_set(left_cells, statuses=statuses)
    right = _sample_set(right_cells, statuses=statuses)
    denominator = min(len(left), len(right))
    if denominator == 0:
        return 0.0
    return len(left & right) / denominator


def _jaccard(
    left_cells: tuple[AlignedCell, ...],
    right_cells: tuple[AlignedCell, ...],
    *,
    statuses: set[str],
) -> float:
    left = _sample_set(left_cells, statuses=statuses)
    right = _sample_set(right_cells, statuses=statuses)
    union = left | right
    if not union:
        return 0.0
    return len(left & right) / len(union)


def _shared_count(
    left_cells: tuple[AlignedCell, ...],
    right_cells: tuple[AlignedCell, ...],
    *,
    statuses: set[str],
) -> int:
    return len(
        _sample_set(left_cells, statuses=statuses)
        & _sample_set(right_cells, statuses=statuses),
    )


def _sample_set(
    cells: tuple[AlignedCell, ...],
    *,
    statuses: set[str],
) -> set[str]:
    return {cell.sample_stem for cell in cells if cell.status in statuses}


def _ms2_signature_conflicts(left: AlignmentCluster, right: AlignmentCluster) -> bool:
    left_signature = getattr(left, "cluster_ms2_signature", None)
    right_signature = getattr(right, "cluster_ms2_signature", None)
    if left_signature is None or right_signature is None:
        return False
    return left_signature != right_signature


def _primary_sort_key(
    cluster: AlignmentCluster,
    cells_by_cluster: dict[str, tuple[AlignedCell, ...]],
) -> tuple[object, ...]:
    cells = cells_by_cluster.get(cluster.cluster_id, ())
    detected_count = _count(cells, "detected")
    present_count = detected_count + _count(cells, "rescued")
    unchecked_count = _count(cells, "unchecked")
    absent_count = _count(cells, "absent")
    return (
        0 if cluster.has_anchor else 1,
        -detected_count,
        -present_count,
        unchecked_count,
        absent_count,
        cluster.cluster_center_mz,
        cluster.cluster_center_rt,
        cluster.cluster_id,
    )


def _count(cells: tuple[AlignedCell, ...], status: str) -> int:
    return sum(1 for cell in cells if cell.status == status)


def _ppm(left: float, right: float) -> float:
    denominator = max(abs(left), 1e-12)
    return abs(left - right) / denominator * 1_000_000.0


def _exceeds(value: float, threshold: float) -> bool:
    return value > threshold + 1e-9
