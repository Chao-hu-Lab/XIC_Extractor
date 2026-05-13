from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass, replace
from typing import Any

from xic_extractor.alignment.config import AlignmentConfig
from xic_extractor.alignment.matrix import AlignedCell, AlignmentMatrix
from xic_extractor.alignment.output_rows import cells_by_cluster, count_status, row_id


@dataclass(frozen=True)
class _ClaimCandidate:
    index: int
    cell: AlignedCell
    cluster: Any
    cluster_id: str
    family_mz: float
    detected_count: int
    event_member_count: int
    event_cluster_count: int
    review_only: bool


@dataclass
class _ClaimGroup:
    candidates: list[_ClaimCandidate]
    min_mz: float
    max_mz: float


def apply_ms1_peak_claim_registry(
    matrix: AlignmentMatrix,
    config: AlignmentConfig,
) -> AlignmentMatrix:
    cluster_by_id = {row_id(cluster): cluster for cluster in matrix.clusters}
    grouped_cells = cells_by_cluster(matrix)
    candidates_by_sample: dict[str, list[_ClaimCandidate]] = {}
    for index, cell in enumerate(matrix.cells):
        if cell.status not in {"detected", "rescued"}:
            continue
        cluster = cluster_by_id.get(cell.cluster_id)
        if cluster is None or not _cell_has_finite_peak_claim(cell):
            continue
        family_mz = _family_center_mz(cluster)
        if not _finite(family_mz):
            continue
        cluster_cells = grouped_cells.get(cell.cluster_id, ())
        candidates_by_sample.setdefault(cell.sample_stem, []).append(
            _ClaimCandidate(
                index=index,
                cell=cell,
                cluster=cluster,
                cluster_id=cell.cluster_id,
                family_mz=family_mz,
                detected_count=count_status(cluster_cells, "detected"),
                event_member_count=_event_member_count(cluster),
                event_cluster_count=len(_event_cluster_ids(cluster)),
                review_only=bool(getattr(cluster, "review_only", False)),
            ),
        )

    replacements: dict[int, AlignedCell] = {}
    for candidates in candidates_by_sample.values():
        exact_replacements = _exact_peak_replacements(candidates)
        replacements.update(exact_replacements)
        fuzzy_candidates = [
            candidate
            for candidate in candidates
            if candidate.index not in exact_replacements
        ]
        for group in _claim_groups(fuzzy_candidates, config):
            if len(group.candidates) < 2:
                continue
            replacements.update(_duplicate_replacements(group.candidates))

    if not replacements:
        return matrix
    return AlignmentMatrix(
        clusters=matrix.clusters,
        cells=tuple(
            replacements.get(index, cell)
            for index, cell in enumerate(matrix.cells)
        ),
        sample_order=matrix.sample_order,
    )


def _exact_peak_replacements(
    candidates: list[_ClaimCandidate],
) -> dict[int, AlignedCell]:
    keyed: dict[tuple[float, float, float, float], list[_ClaimCandidate]] = (
        defaultdict(list)
    )
    for candidate in candidates:
        keyed[_exact_peak_key(candidate.cell)].append(candidate)
    replacements: dict[int, AlignedCell] = {}
    for group in keyed.values():
        if len(group) < 2:
            continue
        replacements.update(_duplicate_replacements(group))
    return replacements


def _exact_peak_key(cell: AlignedCell) -> tuple[float, float, float, float]:
    assert cell.apex_rt is not None
    assert cell.peak_start_rt is not None
    assert cell.peak_end_rt is not None
    assert cell.area is not None
    return (
        round(cell.apex_rt, 8),
        round(cell.peak_start_rt, 8),
        round(cell.peak_end_rt, 8),
        round(cell.area, 6),
    )


def _claim_groups(
    candidates: list[_ClaimCandidate],
    config: AlignmentConfig,
) -> tuple[_ClaimGroup, ...]:
    groups: list[_ClaimGroup] = []
    active: list[_ClaimGroup] = []
    for candidate in sorted(
        candidates,
        key=lambda item: (item.family_mz, item.cell.apex_rt, item.cluster_id),
    ):
        active = [
            group
            for group in active
            if not _mz_window_is_past(candidate.family_mz, group.max_mz, config)
        ]
        compatible_groups = [
            group
            for group in active
            if all(
                _compatible_claim(candidate, existing, config)
                for existing in group.candidates
            )
        ]
        if compatible_groups:
            group = min(compatible_groups, key=_group_sort_key)
            group.candidates.append(candidate)
            group.min_mz = min(group.min_mz, candidate.family_mz)
            group.max_mz = max(group.max_mz, candidate.family_mz)
            continue
        group = _ClaimGroup(
            candidates=[candidate],
            min_mz=candidate.family_mz,
            max_mz=candidate.family_mz,
        )
        groups.append(group)
        active.append(group)
    return tuple(groups)


def _duplicate_replacements(
    candidates: list[_ClaimCandidate],
) -> dict[int, AlignedCell]:
    production_candidates = [
        candidate for candidate in candidates if not candidate.review_only
    ]
    if production_candidates:
        winner = min(production_candidates, key=_winner_sort_key)
        return {
            candidate.index: _duplicate_cell(candidate.cell, winner.cluster_id)
            for candidate in candidates
            if candidate.index != winner.index
        }
    return {
        candidate.index: _review_only_duplicate_cell(candidate.cell)
        for candidate in candidates
    }


def _compatible_claim(
    left: _ClaimCandidate,
    right: _ClaimCandidate,
    config: AlignmentConfig,
) -> bool:
    return (
        _ppm(left.family_mz, right.family_mz) <= config.duplicate_fold_ppm
        and _apex_delta_sec(left.cell, right.cell) <= config.owner_apex_close_sec
        and _window_overlap_fraction(left.cell, right.cell)
        >= config.owner_window_overlap_fraction
    )


def _winner_sort_key(candidate: _ClaimCandidate) -> tuple[object, ...]:
    return (
        1 if candidate.review_only else 0,
        -candidate.detected_count,
        -candidate.event_member_count,
        -candidate.event_cluster_count,
        0 if candidate.cell.status == "detected" else 1,
        abs(candidate.cell.rt_delta_sec)
        if candidate.cell.rt_delta_sec is not None
        else math.inf,
        candidate.cluster_id,
        candidate.cell.sample_stem,
    )


def _group_sort_key(group: _ClaimGroup) -> tuple[object, ...]:
    winner = min(group.candidates, key=_winner_sort_key)
    return (*_winner_sort_key(winner), group.min_mz, group.max_mz)


def _duplicate_cell(cell: AlignedCell, winner_id: str) -> AlignedCell:
    return replace(
        cell,
        status="duplicate_assigned",
        reason=(
            "duplicate MS1 peak claim; "
            f"winner={winner_id}; original_status={cell.status}"
        ),
    )


def _review_only_duplicate_cell(cell: AlignedCell) -> AlignedCell:
    return replace(
        cell,
        status="duplicate_assigned",
        reason=(
            "review-only MS1 peak claim; "
            f"winner=none; original_status={cell.status}"
        ),
    )


def _cell_has_finite_peak_claim(cell: AlignedCell) -> bool:
    return all(
        _finite(value)
        for value in (
            cell.area,
            cell.apex_rt,
            cell.peak_start_rt,
            cell.peak_end_rt,
        )
    )


def _apex_delta_sec(left: AlignedCell, right: AlignedCell) -> float:
    assert left.apex_rt is not None
    assert right.apex_rt is not None
    return abs(left.apex_rt - right.apex_rt) * 60.0


def _window_overlap_fraction(left: AlignedCell, right: AlignedCell) -> float:
    assert left.peak_start_rt is not None
    assert left.peak_end_rt is not None
    assert right.peak_start_rt is not None
    assert right.peak_end_rt is not None
    left_width = left.peak_end_rt - left.peak_start_rt
    right_width = right.peak_end_rt - right.peak_start_rt
    if left_width <= 0 or right_width <= 0:
        return 0.0
    overlap = min(left.peak_end_rt, right.peak_end_rt) - max(
        left.peak_start_rt,
        right.peak_start_rt,
    )
    if overlap <= 0:
        return 0.0
    return overlap / min(left_width, right_width)


def _mz_window_is_past(
    candidate_mz: float,
    group_max_mz: float,
    config: AlignmentConfig,
) -> bool:
    return candidate_mz > group_max_mz and _ppm(group_max_mz, candidate_mz) > (
        config.duplicate_fold_ppm
    )


def _family_center_mz(row: Any) -> float:
    if hasattr(row, "family_center_mz"):
        return float(row.family_center_mz)
    return float(row.cluster_center_mz)


def _event_cluster_ids(row: Any) -> tuple[str, ...]:
    if hasattr(row, "event_cluster_ids"):
        return tuple(row.event_cluster_ids)
    return (str(row.cluster_id), *tuple(row.folded_cluster_ids))


def _event_member_count(row: Any) -> int:
    if hasattr(row, "event_member_count"):
        return int(row.event_member_count)
    return len(row.members) + int(row.folded_member_count)


def _ppm(left: float, right: float) -> float:
    denominator = max(abs(left), 1e-12)
    return abs(left - right) / denominator * 1_000_000.0


def _finite(value: object) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )
