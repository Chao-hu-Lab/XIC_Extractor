from __future__ import annotations

import math
import re
from collections import defaultdict, deque
from dataclasses import dataclass, fields, is_dataclass, replace
from itertools import combinations
from statistics import mean, median
from types import SimpleNamespace
from typing import Any

from xic_extractor.alignment.config import AlignmentConfig
from xic_extractor.alignment.matrix import AlignedCell, AlignmentMatrix
from xic_extractor.alignment.output_rows import cells_by_cluster, row_id

_PRESENT_STATUSES = {"detected", "rescued"}
_DUPLICATE_WINNER_RE = re.compile(r"(?:^|;\s*)winner=([^;]+)")
_ORIGINAL_STATUS_RE = re.compile(r"(?:^|;\s*)original_status=([^;]+)")
_PRODUCT_PRECURSOR_SHIFT_TOLERANCE_DA = 0.02


@dataclass(frozen=True)
class _Observation:
    cell: AlignedCell
    source_cluster_id: str
    original_status: str


@dataclass(frozen=True)
class _FamilyStats:
    detected_count: int
    rescue_count: int
    duplicate_count: int
    ambiguous_count: int
    detected_samples: frozenset[str]
    total_area: float

    @property
    def rescue_heavy(self) -> bool:
        return self.rescue_count > self.detected_count and self.detected_count > 0


def consolidate_primary_family_rows(
    matrix: AlignmentMatrix,
    config: AlignmentConfig,
) -> AlignmentMatrix:
    clusters_by_id = {row_id(cluster): cluster for cluster in matrix.clusters}
    grouped_cells = cells_by_cluster(matrix)
    graph = _duplicate_claim_graph(matrix, clusters_by_id, config)
    components = _connected_components(graph)
    if not components:
        return _demote_near_duplicate_primary_competitors(matrix, config)

    cluster_replacements: dict[str, Any] = {}
    replacement_cells: dict[str, tuple[AlignedCell, ...]] = {}
    clustered_ids = {cluster_id for component in components for cluster_id in component}

    for component in components:
        winner_id = _winner_cluster_id(component, clusters_by_id, grouped_cells)
        selected_by_sample = _selected_observations_by_sample(
            component,
            grouped_cells,
        )
        center = _component_center(
            component,
            clusters_by_id=clusters_by_id,
            selected_by_sample=selected_by_sample,
        )
        cluster_replacements[winner_id] = _primary_cluster(
            clusters_by_id[winner_id],
            component=component,
            clusters_by_id=clusters_by_id,
            center=center,
        )
        for cluster_id in component:
            if cluster_id == winner_id:
                continue
            cluster_replacements[cluster_id] = _loser_cluster(
                clusters_by_id[cluster_id],
                winner_id=winner_id,
            )
        replacement_cells[winner_id] = _winner_cells(
            winner_id,
            grouped_cells=grouped_cells,
            selected_by_sample=selected_by_sample,
            sample_order=matrix.sample_order,
            center_rt=center["family_center_rt"],
        )

    clusters = tuple(
        cluster_replacements.get(row_id(cluster), cluster)
        for cluster in matrix.clusters
    )
    cells: list[AlignedCell] = []
    for cluster in matrix.clusters:
        cluster_id = row_id(cluster)
        if cluster_id in replacement_cells:
            cells.extend(replacement_cells[cluster_id])
        elif cluster_id in clustered_ids:
            cells.extend(grouped_cells.get(cluster_id, ()))
        else:
            cells.extend(grouped_cells.get(cluster_id, ()))
    consolidated = AlignmentMatrix(
        clusters=clusters,
        cells=tuple(cells),
        sample_order=matrix.sample_order,
    )
    return _demote_near_duplicate_primary_competitors(consolidated, config)


def _demote_near_duplicate_primary_competitors(
    matrix: AlignmentMatrix,
    config: AlignmentConfig,
) -> AlignmentMatrix:
    clusters_by_id = {row_id(cluster): cluster for cluster in matrix.clusters}
    grouped_cells = cells_by_cluster(matrix)
    graph = _near_duplicate_primary_graph(matrix, clusters_by_id, grouped_cells, config)
    components = _connected_components(graph)
    if not components:
        return matrix

    cluster_replacements: dict[str, Any] = {}
    for component in components:
        winner_id = _family_winner_cluster_id(component, clusters_by_id, grouped_cells)
        for cluster_id in component:
            if cluster_id == winner_id:
                continue
            cluster_replacements[cluster_id] = _loser_cluster(
                clusters_by_id[cluster_id],
                winner_id=winner_id,
            )
    return AlignmentMatrix(
        clusters=tuple(
            cluster_replacements.get(row_id(cluster), cluster)
            for cluster in matrix.clusters
        ),
        cells=matrix.cells,
        sample_order=matrix.sample_order,
    )


def _duplicate_claim_graph(
    matrix: AlignmentMatrix,
    clusters_by_id: dict[str, Any],
    config: AlignmentConfig,
) -> dict[str, set[str]]:
    graph: dict[str, set[str]] = defaultdict(set)
    for cell in matrix.cells:
        if cell.status != "duplicate_assigned":
            continue
        winner_id = _duplicate_winner(cell.reason)
        if (
            winner_id is None
            or winner_id == "none"
            or winner_id == cell.cluster_id
            or winner_id not in clusters_by_id
            or cell.cluster_id not in clusters_by_id
        ):
            continue
        if not _compatible_primary_family(
            clusters_by_id[cell.cluster_id],
            clusters_by_id[winner_id],
            config,
        ):
            continue
        graph[cell.cluster_id].add(winner_id)
        graph[winner_id].add(cell.cluster_id)
    return graph


def _near_duplicate_primary_graph(
    matrix: AlignmentMatrix,
    clusters_by_id: dict[str, Any],
    grouped_cells: dict[str, tuple[AlignedCell, ...]],
    config: AlignmentConfig,
) -> dict[str, set[str]]:
    graph: dict[str, set[str]] = defaultdict(set)
    stats_by_id = {
        cluster_id: _family_stats(grouped_cells.get(cluster_id, ()))
        for cluster_id in clusters_by_id
    }
    family_ids = tuple(row_id(cluster) for cluster in matrix.clusters)
    for left_id, right_id in combinations(family_ids, 2):
        left = clusters_by_id[left_id]
        right = clusters_by_id[right_id]
        left_stats = stats_by_id[left_id]
        right_stats = stats_by_id[right_id]
        if not _near_duplicate_primary_competition(
            left,
            right,
            left_stats=left_stats,
            right_stats=right_stats,
            config=config,
        ):
            continue
        graph[left_id].add(right_id)
        graph[right_id].add(left_id)
    return graph


def _near_duplicate_primary_competition(
    left: Any,
    right: Any,
    *,
    left_stats: _FamilyStats,
    right_stats: _FamilyStats,
    config: AlignmentConfig,
) -> bool:
    if _review_only_or_loser(left) or _review_only_or_loser(right):
        return False
    if not _loose_compatible_primary_family(left, right, config):
        return False
    if not (left_stats.detected_samples & right_stats.detected_samples):
        return False
    return (
        (left_stats.rescue_heavy and right_stats.detected_count >= 2)
        or (right_stats.rescue_heavy and left_stats.detected_count >= 2)
    )


def _connected_components(graph: dict[str, set[str]]) -> tuple[tuple[str, ...], ...]:
    visited: set[str] = set()
    components: list[tuple[str, ...]] = []
    for start in sorted(graph):
        if start in visited:
            continue
        queue: deque[str] = deque((start,))
        visited.add(start)
        component: list[str] = []
        while queue:
            current = queue.popleft()
            component.append(current)
            for neighbor in sorted(graph[current]):
                if neighbor in visited:
                    continue
                visited.add(neighbor)
                queue.append(neighbor)
        if len(component) > 1:
            components.append(tuple(component))
    return tuple(components)


def _winner_cluster_id(
    component: tuple[str, ...],
    clusters_by_id: dict[str, Any],
    grouped_cells: dict[str, tuple[AlignedCell, ...]],
) -> str:
    center_rt = _component_seed_rt(component, grouped_cells, clusters_by_id)
    return min(
        component,
        key=lambda cluster_id: (
            -_current_present_count(grouped_cells.get(cluster_id, ())),
            -_current_detected_count(grouped_cells.get(cluster_id, ())),
            abs(_family_center_rt(clusters_by_id[cluster_id]) - center_rt),
            cluster_id,
        ),
    )


def _family_winner_cluster_id(
    component: tuple[str, ...],
    clusters_by_id: dict[str, Any],
    grouped_cells: dict[str, tuple[AlignedCell, ...]],
) -> str:
    center_rt = _component_seed_rt(component, grouped_cells, clusters_by_id)
    stats_by_id = {
        cluster_id: _family_stats(grouped_cells.get(cluster_id, ()))
        for cluster_id in component
    }
    return min(
        component,
        key=lambda cluster_id: (
            -int(stats_by_id[cluster_id].detected_count >= 2),
            -stats_by_id[cluster_id].detected_count,
            stats_by_id[cluster_id].duplicate_count
            + stats_by_id[cluster_id].ambiguous_count,
            -stats_by_id[cluster_id].rescue_count,
            -stats_by_id[cluster_id].total_area,
            abs(_family_center_rt(clusters_by_id[cluster_id]) - center_rt),
            cluster_id,
        ),
    )


def _selected_observations_by_sample(
    component: tuple[str, ...],
    grouped_cells: dict[str, tuple[AlignedCell, ...]],
) -> dict[str, _Observation]:
    observations = [
        observation
        for cluster_id in component
        for cell in grouped_cells.get(cluster_id, ())
        for observation in (_observation(cell),)
        if observation is not None
    ]
    if not observations:
        return {}
    center_rt = _observation_seed_rt(observations)
    by_sample: dict[str, list[_Observation]] = defaultdict(list)
    for observation in observations:
        by_sample[observation.cell.sample_stem].append(observation)
    return {
        sample_stem: min(items, key=lambda item: _observation_sort_key(item, center_rt))
        for sample_stem, items in by_sample.items()
    }


def _component_center(
    component: tuple[str, ...],
    *,
    clusters_by_id: dict[str, Any],
    selected_by_sample: dict[str, _Observation],
) -> dict[str, float]:
    selected_cells = [observation.cell for observation in selected_by_sample.values()]
    selected_rts = [
        cell.apex_rt
        for cell in selected_cells
        if cell.apex_rt is not None and _finite(cell.apex_rt)
    ]
    return {
        "family_center_mz": median(
            _family_center_mz(clusters_by_id[cluster_id])
            for cluster_id in component
        ),
        "family_center_rt": (
            mean(selected_rts)
            if selected_rts
            else median(
                _family_center_rt(clusters_by_id[cluster_id])
                for cluster_id in component
            )
        ),
        "family_product_mz": median(
            _family_product_mz(clusters_by_id[cluster_id])
            for cluster_id in component
        ),
        "family_observed_neutral_loss_da": median(
            _family_observed_loss(clusters_by_id[cluster_id])
            for cluster_id in component
        ),
    }


def _winner_cells(
    winner_id: str,
    *,
    grouped_cells: dict[str, tuple[AlignedCell, ...]],
    selected_by_sample: dict[str, _Observation],
    sample_order: tuple[str, ...],
    center_rt: float,
) -> tuple[AlignedCell, ...]:
    current_by_sample = {
        cell.sample_stem: cell for cell in grouped_cells.get(winner_id, ())
    }
    cells: list[AlignedCell] = []
    for sample_stem in sample_order:
        observation = selected_by_sample.get(sample_stem)
        if observation is not None:
            cells.append(_merged_observation_cell(observation, winner_id, center_rt))
            continue
        current = current_by_sample.get(sample_stem)
        if current is not None:
            cells.append(_with_cluster_and_rt_delta(current, winner_id, center_rt))
    return tuple(cells)


def _primary_cluster(
    cluster: Any,
    *,
    component: tuple[str, ...],
    clusters_by_id: dict[str, Any],
    center: dict[str, float],
) -> Any:
    event_cluster_ids = tuple(
        event_id
        for cluster_id in component
        for event_id in _event_cluster_ids(clusters_by_id[cluster_id])
    )
    evidence = (
        f"owner_complete_link;owner_count={max(2, len(event_cluster_ids))};"
        f"primary_family_consolidated;family_count={len(component)}"
    )
    return _clone_cluster(
        cluster,
        {
            **center,
            "has_anchor": any(
                bool(getattr(clusters_by_id[cluster_id], "has_anchor", False))
                for cluster_id in component
            ),
            "event_cluster_ids": event_cluster_ids,
            "event_member_count": sum(
                _event_member_count(clusters_by_id[cluster_id])
                for cluster_id in component
            ),
            "evidence": evidence,
            "review_only": False,
        },
    )


def _loser_cluster(cluster: Any, *, winner_id: str) -> Any:
    evidence = _family_evidence(cluster)
    suffix = f"primary_family_consolidation_loser;winner={winner_id}"
    return _clone_cluster(
        cluster,
        {
            "evidence": f"{evidence};{suffix}" if evidence else suffix,
            "review_only": True,
        },
    )


def _merged_observation_cell(
    observation: _Observation,
    winner_id: str,
    center_rt: float,
) -> AlignedCell:
    cell = _with_cluster_and_rt_delta(observation.cell, winner_id, center_rt)
    reason = (
        "primary family consolidation; "
        f"source_family={observation.source_cluster_id}; "
        f"original_status={observation.original_status}; "
        f"source_reason={observation.cell.reason}"
    )
    return replace(
        cell,
        status=observation.original_status,  # type: ignore[arg-type]
        reason=reason,
    )


def _with_cluster_and_rt_delta(
    cell: AlignedCell,
    cluster_id: str,
    center_rt: float,
) -> AlignedCell:
    rt_delta_sec = (
        (cell.apex_rt - center_rt) * 60.0
        if cell.apex_rt is not None and _finite(cell.apex_rt)
        else None
    )
    return replace(cell, cluster_id=cluster_id, rt_delta_sec=rt_delta_sec)


def _observation(cell: AlignedCell) -> _Observation | None:
    original_status = _original_status(cell)
    if original_status not in _PRESENT_STATUSES:
        return None
    if not _valid_present_cell(cell):
        return None
    return _Observation(
        cell=cell,
        source_cluster_id=cell.cluster_id,
        original_status=original_status,
    )


def _observation_seed_rt(observations: list[_Observation]) -> float:
    detected = [
        observation.cell.apex_rt
        for observation in observations
        if observation.original_status == "detected"
        and observation.cell.apex_rt is not None
    ]
    if detected:
        return median(detected)
    return median(
        observation.cell.apex_rt
        for observation in observations
        if observation.cell.apex_rt is not None
    )


def _component_seed_rt(
    component: tuple[str, ...],
    grouped_cells: dict[str, tuple[AlignedCell, ...]],
    clusters_by_id: dict[str, Any],
) -> float:
    observations = [
        observation
        for cluster_id in component
        for cell in grouped_cells.get(cluster_id, ())
        for observation in (_observation(cell),)
        if observation is not None
    ]
    if observations:
        return _observation_seed_rt(observations)
    return median(
        _family_center_rt(clusters_by_id[cluster_id])
        for cluster_id in component
    )


def _observation_sort_key(
    observation: _Observation,
    center_rt: float,
) -> tuple[object, ...]:
    cell = observation.cell
    area = float(cell.area or 0.0)
    return (
        -area,
        0 if observation.original_status == "detected" else 1,
        abs((cell.apex_rt or center_rt) - center_rt),
        _trace_quality_rank(cell.trace_quality),
        observation.source_cluster_id,
    )


def _current_present_count(cells: tuple[AlignedCell, ...]) -> int:
    return sum(1 for cell in cells if cell.status in _PRESENT_STATUSES)


def _current_detected_count(cells: tuple[AlignedCell, ...]) -> int:
    return sum(1 for cell in cells if cell.status == "detected")


def _family_stats(cells: tuple[AlignedCell, ...]) -> _FamilyStats:
    detected = tuple(cell for cell in cells if cell.status == "detected")
    rescued = tuple(cell for cell in cells if cell.status == "rescued")
    return _FamilyStats(
        detected_count=sum(1 for cell in detected if _valid_present_cell(cell)),
        rescue_count=sum(1 for cell in rescued if _valid_present_cell(cell)),
        duplicate_count=sum(1 for cell in cells if cell.status == "duplicate_assigned"),
        ambiguous_count=sum(
            1 for cell in cells if cell.status == "ambiguous_ms1_owner"
        ),
        detected_samples=frozenset(
            cell.sample_stem for cell in detected if _valid_present_cell(cell)
        ),
        total_area=sum(
            float(cell.area or 0.0) for cell in cells if _valid_present_cell(cell)
        ),
    )


def _valid_present_cell(cell: AlignedCell) -> bool:
    return (
        cell.area is not None
        and _finite(cell.area)
        and cell.area > 0
        and cell.apex_rt is not None
        and _finite(cell.apex_rt)
        and cell.peak_start_rt is not None
        and _finite(cell.peak_start_rt)
        and cell.peak_end_rt is not None
        and _finite(cell.peak_end_rt)
    )


def _compatible_primary_family(
    left: Any,
    right: Any,
    config: AlignmentConfig,
) -> bool:
    if bool(getattr(left, "review_only", False)) or bool(
        getattr(right, "review_only", False),
    ):
        return False
    if str(left.neutral_loss_tag) != str(right.neutral_loss_tag):
        return False
    if _ppm(_family_center_mz(left), _family_center_mz(right)) > config.max_ppm:
        return False
    if (
        abs(_family_center_rt(left) - _family_center_rt(right)) * 60.0
        > config.identity_rt_candidate_window_sec
    ):
        return False
    if (
        _ppm(_family_product_mz(left), _family_product_mz(right))
        > config.product_mz_tolerance_ppm
    ):
        return False
    return (
        _ppm(_family_observed_loss(left), _family_observed_loss(right))
        <= config.observed_loss_tolerance_ppm
    )


def _loose_compatible_primary_family(
    left: Any,
    right: Any,
    config: AlignmentConfig,
) -> bool:
    if str(left.neutral_loss_tag) != str(right.neutral_loss_tag):
        return False
    if _ppm(_family_center_mz(left), _family_center_mz(right)) > config.max_ppm:
        return False
    if (
        abs(_family_center_rt(left) - _family_center_rt(right)) * 60.0
        > config.identity_rt_candidate_window_sec
    ):
        return False
    if (
        _ppm(_family_observed_loss(left), _family_observed_loss(right))
        > config.observed_loss_tolerance_ppm
    ):
        return False
    if (
        _ppm(_family_product_mz(left), _family_product_mz(right))
        <= config.product_mz_tolerance_ppm
    ):
        return True
    precursor_delta = _family_center_mz(right) - _family_center_mz(left)
    product_delta = _family_product_mz(right) - _family_product_mz(left)
    return (
        abs(product_delta - precursor_delta)
        <= _PRODUCT_PRECURSOR_SHIFT_TOLERANCE_DA
    )


def _review_only_or_loser(row: Any) -> bool:
    if bool(getattr(row, "review_only", False)):
        return True
    evidence = _family_evidence(row)
    return (
        "primary_family_consolidation_loser" in evidence
        or "pre_backfill_identity_consolidation_loser" in evidence
    )


def _clone_cluster(cluster: Any, updates: dict[str, Any]) -> Any:
    if is_dataclass(cluster) and not isinstance(cluster, type):
        allowed = {field.name for field in fields(cluster)}
        return replace(
            cluster,
            **{key: value for key, value in updates.items() if key in allowed},
        )
    if isinstance(cluster, SimpleNamespace):
        values = vars(cluster).copy()
        values.update(updates)
        return SimpleNamespace(**values)
    values = {
        key: getattr(cluster, key)
        for key in dir(cluster)
        if not key.startswith("_") and not callable(getattr(cluster, key))
    }
    values.update(updates)
    return SimpleNamespace(**values)


def _duplicate_winner(reason: str) -> str | None:
    match = _DUPLICATE_WINNER_RE.search(reason)
    return None if match is None else match.group(1)


def _original_status(cell: AlignedCell) -> str:
    if cell.status != "duplicate_assigned":
        return cell.status
    match = _ORIGINAL_STATUS_RE.search(cell.reason)
    return "" if match is None else match.group(1)


def _trace_quality_rank(value: str) -> int:
    return {"clean": 0, "owner_exact_apex_match": 1, "weak": 2, "poor": 3}.get(
        value,
        4,
    )


def _family_center_mz(row: Any) -> float:
    if hasattr(row, "family_center_mz"):
        return float(row.family_center_mz)
    return float(row.cluster_center_mz)


def _family_center_rt(row: Any) -> float:
    if hasattr(row, "family_center_rt"):
        return float(row.family_center_rt)
    return float(row.cluster_center_rt)


def _family_product_mz(row: Any) -> float:
    if hasattr(row, "family_product_mz"):
        return float(row.family_product_mz)
    return float(row.cluster_product_mz)


def _family_observed_loss(row: Any) -> float:
    if hasattr(row, "family_observed_neutral_loss_da"):
        return float(row.family_observed_neutral_loss_da)
    return float(row.cluster_observed_neutral_loss_da)


def _event_cluster_ids(row: Any) -> tuple[str, ...]:
    if hasattr(row, "event_cluster_ids"):
        return tuple(row.event_cluster_ids)
    return (str(row.cluster_id), *tuple(row.folded_cluster_ids))


def _event_member_count(row: Any) -> int:
    if hasattr(row, "event_member_count"):
        return int(row.event_member_count)
    return len(row.members) + int(row.folded_member_count)


def _family_evidence(row: Any) -> str:
    if hasattr(row, "evidence"):
        return str(row.evidence)
    if hasattr(row, "fold_evidence"):
        return str(row.fold_evidence)
    return ""


def _ppm(left: float, right: float) -> float:
    return abs(left - right) / max(abs(left), 1e-12) * 1_000_000.0


def _finite(value: object) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )
