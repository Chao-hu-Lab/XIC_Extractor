from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from dataclasses import replace
from typing import Protocol

import numpy as np
from numpy.typing import NDArray

from xic_extractor.alignment.config import AlignmentConfig
from xic_extractor.alignment.feature_family import MS1FeatureFamily
from xic_extractor.alignment.matrix import AlignedCell, AlignmentMatrix
from xic_extractor.config import ExtractionConfig
from xic_extractor.signal_processing import find_peak_and_area


class FamilyIntegrationSource(Protocol):
    def extract_xic(
        self,
        mz: float,
        rt_min: float,
        rt_max: float,
        ppm_tol: float,
    ) -> tuple[NDArray[np.float64], NDArray[np.float64]]: ...


def integrate_feature_family_matrix(
    families: tuple[MS1FeatureFamily, ...],
    *,
    sample_order: tuple[str, ...],
    raw_sources: Mapping[str, FamilyIntegrationSource],
    alignment_config: AlignmentConfig,
    peak_config: ExtractionConfig,
) -> AlignmentMatrix:
    cells: list[AlignedCell] = []
    for family in families:
        for sample_stem in sample_order:
            cells.append(
                _integrate_family_cell(
                    family,
                    sample_stem,
                    raw_sources=raw_sources,
                    alignment_config=alignment_config,
                    peak_config=peak_config,
                ),
            )
    resolved_cells = _resolve_peak_ownership(tuple(cells), families, alignment_config)
    return AlignmentMatrix(
        clusters=families,
        cells=resolved_cells,
        sample_order=sample_order,
    )


def _integrate_family_cell(
    family: MS1FeatureFamily,
    sample_stem: str,
    *,
    raw_sources: Mapping[str, FamilyIntegrationSource],
    alignment_config: AlignmentConfig,
    peak_config: ExtractionConfig,
) -> AlignedCell:
    if not family.has_anchor and sample_stem not in _event_member_samples(family):
        return _unchecked_cell(
            family,
            sample_stem,
            reason="family integration skipped for non-anchor family",
        )
    source = raw_sources.get(sample_stem)
    if source is None:
        return _unchecked_cell(
            family,
            sample_stem,
            reason="missing raw source for family integration",
        )
    rt_min = family.family_center_rt - alignment_config.max_rt_sec / 60.0
    rt_max = family.family_center_rt + alignment_config.max_rt_sec / 60.0
    try:
        rt, intensity = source.extract_xic(
            family.family_center_mz,
            rt_min,
            rt_max,
            alignment_config.preferred_ppm,
        )
        rt_array, intensity_array = _validated_trace_arrays(rt, intensity)
        result = find_peak_and_area(
            rt_array,
            intensity_array,
            peak_config,
            preferred_rt=family.family_center_rt,
            strict_preferred_rt=False,
        )
    except Exception:
        return _unchecked_cell(
            family,
            sample_stem,
            reason="family integration could not be checked",
        )
    if result.status != "OK" or result.peak is None:
        return _absent_cell(family, sample_stem)
    peak = result.peak
    has_original_detection = _has_original_detection(family, sample_stem)
    status = "detected" if has_original_detection else "rescued"
    reason = (
        "family-centered MS1 integration from original detection"
        if has_original_detection
        else "family-centered MS1 backfill"
    )
    return AlignedCell(
        sample_stem=sample_stem,
        cluster_id=family.feature_family_id,
        status=status,
        area=peak.area,
        apex_rt=peak.rt,
        height=peak.intensity,
        peak_start_rt=peak.peak_start,
        peak_end_rt=peak.peak_end,
        rt_delta_sec=(peak.rt - family.family_center_rt) * 60.0,
        trace_quality="family_centered",
        scan_support_score=_scan_support_score(
            rt_array,
            peak_start=peak.peak_start,
            peak_end=peak.peak_end,
            scans_target=peak_config.resolver_min_scans,
        ),
        source_candidate_id=None,
        source_raw_file=None,
        reason=reason,
    )


def _unchecked_cell(
    family: MS1FeatureFamily,
    sample_stem: str,
    *,
    reason: str,
) -> AlignedCell:
    return AlignedCell(
        sample_stem=sample_stem,
        cluster_id=family.feature_family_id,
        status="unchecked",
        area=None,
        apex_rt=None,
        height=None,
        peak_start_rt=None,
        peak_end_rt=None,
        rt_delta_sec=None,
        trace_quality="unchecked",
        scan_support_score=None,
        source_candidate_id=None,
        source_raw_file=None,
        reason=reason,
    )


def _absent_cell(family: MS1FeatureFamily, sample_stem: str) -> AlignedCell:
    return AlignedCell(
        sample_stem=sample_stem,
        cluster_id=family.feature_family_id,
        status="absent",
        area=None,
        apex_rt=None,
        height=None,
        peak_start_rt=None,
        peak_end_rt=None,
        rt_delta_sec=None,
        trace_quality="missing",
        scan_support_score=None,
        source_candidate_id=None,
        source_raw_file=None,
        reason="family-centered MS1 integration found no peak",
    )


def _event_member_samples(family: MS1FeatureFamily) -> frozenset[str]:
    return frozenset(
        member.sample_stem
        for cluster in family.event_clusters
        for member in cluster.members
    )


def _has_original_detection(family: MS1FeatureFamily, sample_stem: str) -> bool:
    return sample_stem in _event_member_samples(family)


def _resolve_peak_ownership(
    cells: tuple[AlignedCell, ...],
    families: tuple[MS1FeatureFamily, ...],
    config: AlignmentConfig,
) -> tuple[AlignedCell, ...]:
    family_by_id = {family.feature_family_id: family for family in families}
    cells_by_sample: dict[str, list[tuple[int, AlignedCell]]] = defaultdict(list)
    for index, cell in enumerate(cells):
        if cell.status == "detected":
            cells_by_sample[cell.sample_stem].append((index, cell))

    losers: dict[int, str] = {}
    for sample_cells in cells_by_sample.values():
        for component in _peak_conflict_components(
            sample_cells,
            family_by_id=family_by_id,
            config=config,
        ):
            if len(component) < 2:
                continue
            winner_index, winner_cell = max(
                component,
                key=lambda item: _ownership_key(
                    item[0],
                    item[1],
                    family_by_id[item[1].cluster_id],
                ),
            )
            for loser_index, _loser_cell in component:
                if loser_index != winner_index:
                    losers[loser_index] = winner_cell.cluster_id

    if not losers:
        return cells

    return tuple(
        _assigned_to_selected_family(cell, winners_family_id=losers[index])
        if index in losers
        else cell
        for index, cell in enumerate(cells)
    )


def _peak_conflict_components(
    sample_cells: list[tuple[int, AlignedCell]],
    *,
    family_by_id: dict[str, MS1FeatureFamily],
    config: AlignmentConfig,
) -> tuple[tuple[tuple[int, AlignedCell], ...], ...]:
    remaining = set(range(len(sample_cells)))
    components: list[tuple[tuple[int, AlignedCell], ...]] = []
    while remaining:
        seed = remaining.pop()
        stack = [seed]
        component_indexes = {seed}
        while stack:
            current_index = stack.pop()
            _current_global_index, current_cell = sample_cells[current_index]
            current_family = family_by_id[current_cell.cluster_id]
            for candidate_index in tuple(remaining):
                _candidate_global_index, candidate_cell = sample_cells[candidate_index]
                if _same_sample_peak(
                    current_cell,
                    candidate_cell,
                    current_family,
                    family_by_id[candidate_cell.cluster_id],
                    config=config,
                ):
                    remaining.remove(candidate_index)
                    stack.append(candidate_index)
                    component_indexes.add(candidate_index)
        components.append(tuple(sample_cells[index] for index in component_indexes))
    return tuple(components)


def _same_sample_peak(
    left_cell: AlignedCell,
    right_cell: AlignedCell,
    left_family: MS1FeatureFamily,
    right_family: MS1FeatureFamily,
    *,
    config: AlignmentConfig,
) -> bool:
    if left_family.neutral_loss_tag != right_family.neutral_loss_tag:
        return False
    if _ppm(left_family.family_center_mz, right_family.family_center_mz) > (
        config.duplicate_fold_ppm
    ):
        return False
    if _ppm(left_family.family_product_mz, right_family.family_product_mz) > (
        config.duplicate_fold_product_ppm
    ):
        return False
    if _ppm(
        left_family.family_observed_neutral_loss_da,
        right_family.family_observed_neutral_loss_da,
    ) > config.duplicate_fold_observed_loss_ppm:
        return False
    return _peak_windows_overlap(left_cell, right_cell) or _apexes_are_close(
        left_cell,
        right_cell,
        config=config,
    )


def _peak_windows_overlap(left: AlignedCell, right: AlignedCell) -> bool:
    if (
        left.peak_start_rt is None
        or left.peak_end_rt is None
        or right.peak_start_rt is None
        or right.peak_end_rt is None
    ):
        return False
    return max(left.peak_start_rt, right.peak_start_rt) <= min(
        left.peak_end_rt,
        right.peak_end_rt,
    )


def _apexes_are_close(
    left: AlignedCell,
    right: AlignedCell,
    *,
    config: AlignmentConfig,
) -> bool:
    if left.apex_rt is None or right.apex_rt is None:
        return False
    return abs(left.apex_rt - right.apex_rt) * 60.0 <= config.duplicate_fold_rt_sec


def _ownership_key(
    index: int,
    cell: AlignedCell,
    family: MS1FeatureFamily,
) -> tuple[int, float, int, float, int]:
    rt_delta_sec = (
        abs(cell.apex_rt - family.family_center_rt) * 60.0
        if cell.apex_rt is not None
        else float("inf")
    )
    return (
        1 if family.has_anchor else 0,
        -rt_delta_sec,
        family.event_member_count,
        cell.area or 0.0,
        -index,
    )


def _assigned_to_selected_family(
    cell: AlignedCell,
    *,
    winners_family_id: str,
) -> AlignedCell:
    return replace(
        cell,
        status="duplicate_assigned",
        area=None,
        apex_rt=None,
        height=None,
        peak_start_rt=None,
        peak_end_rt=None,
        rt_delta_sec=None,
        trace_quality="assigned_duplicate",
        scan_support_score=None,
        reason=f"MS1 peak assigned to selected feature family {winners_family_id}",
    )


def _validated_trace_arrays(
    rt: object,
    intensity: object,
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    rt_array = np.asarray(rt, dtype=float)
    intensity_array = np.asarray(intensity, dtype=float)
    if (
        rt_array.ndim != 1
        or intensity_array.ndim != 1
        or rt_array.shape != intensity_array.shape
        or not np.all(np.isfinite(rt_array))
        or not np.all(np.isfinite(intensity_array))
    ):
        raise ValueError(
            "family integration trace arrays must be finite one-dimensional pairs",
        )
    return rt_array, intensity_array


def _ppm(left: float, right: float) -> float:
    denominator = left if left else right
    if denominator == 0:
        return float("inf")
    return abs(left - right) / abs(denominator) * 1_000_000


def _scan_support_score(
    rt: NDArray[np.float64],
    *,
    peak_start: float,
    peak_end: float,
    scans_target: int,
) -> float:
    if scans_target <= 0:
        return 0.0
    scan_count = int(np.count_nonzero((rt >= peak_start) & (rt <= peak_end)))
    return min(1.0, scan_count / scans_target)
