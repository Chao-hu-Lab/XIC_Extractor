from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Mapping
from itertools import groupby
from statistics import median
from typing import Protocol

import numpy as np
from numpy.typing import NDArray

from xic_extractor.alignment.config import AlignmentConfig
from xic_extractor.alignment.matrix import AlignedCell
from xic_extractor.alignment.owner_clustering import OwnerAlignedFeature
from xic_extractor.config import ExtractionConfig
from xic_extractor.signal_processing import find_peak_and_area
from xic_extractor.xic_models import XICRequest, XICTrace

_RequestItem = tuple[OwnerAlignedFeature, str, XICRequest, float]
_RequestGroupKey = tuple[str, int | float, int | float]


class OwnerBackfillSource(Protocol):
    def extract_xic(
        self,
        mz: float,
        rt_min: float,
        rt_max: float,
        ppm_tol: float,
    ) -> tuple[NDArray[np.float64], NDArray[np.float64]]: ...


def build_owner_backfill_cells(
    features: tuple[OwnerAlignedFeature, ...],
    *,
    sample_order: tuple[str, ...],
    raw_sources: Mapping[str, OwnerBackfillSource],
    validation_raw_sources: Mapping[str, OwnerBackfillSource] | None = None,
    alignment_config: AlignmentConfig,
    peak_config: ExtractionConfig,
    raw_xic_batch_size: int = 1,
) -> tuple[AlignedCell, ...]:
    if raw_xic_batch_size < 1:
        raise ValueError("raw_xic_batch_size must be >= 1")
    cells: list[AlignedCell] = []
    pending: dict[str, list[_RequestItem]] = defaultdict(list)
    rt_window_min = alignment_config.max_rt_sec / 60.0
    for feature in features:
        if feature.review_only:
            continue
        detected_samples = {owner.sample_stem for owner in feature.owners}
        owners_by_sample = {owner.sample_stem: owner for owner in feature.owners}
        if (
            len(detected_samples)
            < alignment_config.owner_backfill_min_detected_samples
        ):
            continue
        for sample_stem in sample_order:
            if sample_stem not in raw_sources:
                continue
            if (
                sample_stem in detected_samples
                and not feature.confirm_local_owners_with_backfill
            ):
                continue
            if (
                sample_stem in detected_samples
                and not _detected_owner_can_be_superseded(
                    feature,
                    owners_by_sample.get(sample_stem),
                )
            ):
                continue
            for seed_mz, seed_rt in _backfill_seed_centers(feature):
                pending[sample_stem].append(
                    (
                        feature,
                        sample_stem,
                        XICRequest(
                            mz=seed_mz,
                            rt_min=seed_rt - rt_window_min,
                            rt_max=seed_rt + rt_window_min,
                            ppm_tol=alignment_config.preferred_ppm,
                        ),
                        seed_rt,
                    )
                )
    rescued_by_feature_sample: dict[tuple[str, str], AlignedCell] = {}
    validation_pending: dict[str, list[_RequestItem]] = defaultdict(list)
    for sample_stem in sample_order:
        sample_requests = pending.get(sample_stem, [])
        if not sample_requests:
            continue
        source = raw_sources[sample_stem]
        for chunk in _scan_window_aware_chunks(
            source,
            tuple(sample_requests),
            raw_xic_batch_size,
        ):
            try:
                traces = _extract_many(source, tuple(item[2] for item in chunk))
            except OSError:
                continue
            for (feature, requested_sample, _request, preferred_rt), trace in zip(
                chunk,
                traces,
                strict=True,
            ):
                cell = _backfill_feature_sample_trace(
                    feature,
                    requested_sample,
                    trace,
                    preferred_rt=preferred_rt,
                    peak_config=peak_config,
                )
                if cell is not None:
                    if validation_raw_sources is None:
                        _keep_best_rescued_cell(
                            rescued_by_feature_sample,
                            cell,
                        )
                    else:
                        validation_pending[requested_sample].append(
                            (feature, requested_sample, _request, preferred_rt)
                        )
    if validation_raw_sources is not None:
        for sample_stem in sample_order:
            sample_requests = validation_pending.get(sample_stem, [])
            if not sample_requests or sample_stem not in validation_raw_sources:
                continue
            source = validation_raw_sources[sample_stem]
            for chunk in _scan_window_aware_chunks(
                source,
                tuple(sample_requests),
                raw_xic_batch_size,
            ):
                try:
                    traces = _extract_many(source, tuple(item[2] for item in chunk))
                except OSError:
                    continue
                for (
                    feature,
                    requested_sample,
                    _request,
                    preferred_rt,
                ), trace in zip(
                    chunk,
                    traces,
                    strict=True,
                ):
                    cell = _backfill_feature_sample_trace(
                        feature,
                        requested_sample,
                        trace,
                        preferred_rt=preferred_rt,
                        peak_config=peak_config,
                    )
                    if cell is not None:
                        _keep_best_rescued_cell(
                            rescued_by_feature_sample,
                            cell,
                        )
    for feature in features:
        if feature.review_only:
            continue
        for sample_stem in sample_order:
            cell = rescued_by_feature_sample.get(
                (feature.feature_family_id, sample_stem)
            )
            if cell is not None:
                cells.append(cell)
    return tuple(cells)


def _scan_window_aware_chunks(
    source: OwnerBackfillSource,
    items: tuple[_RequestItem, ...],
    chunk_size: int,
) -> tuple[tuple[_RequestItem, ...], ...]:
    if chunk_size < 1:
        raise ValueError("raw_xic_batch_size must be >= 1")
    keyed_items = tuple((_request_group_key(source, item), item) for item in items)
    ordered_items = tuple(sorted(keyed_items, key=_grouped_request_sort_key))
    chunks: list[tuple[_RequestItem, ...]] = []
    current: list[_RequestItem] = []
    for _group_key, group_iter in groupby(ordered_items, key=lambda pair: pair[0]):
        group = [item for _key, item in group_iter]
        if current and len(current) + len(group) > chunk_size:
            chunks.append(tuple(current))
            current = []
        current.extend(group)
        if len(current) >= chunk_size:
            chunks.append(tuple(current))
            current = []
    if current:
        chunks.append(tuple(current))
    return tuple(chunks)


def _grouped_request_sort_key(
    keyed_item: tuple[_RequestGroupKey, _RequestItem],
) -> tuple[str, int | float, int | float, float, str, str]:
    group_key, item = keyed_item
    feature, sample_stem, request, _preferred_rt = item
    return (
        *group_key,
        request.mz,
        feature.feature_family_id,
        sample_stem,
    )


def _request_group_key(
    source: OwnerBackfillSource,
    item: _RequestItem,
) -> _RequestGroupKey:
    request = item[2]
    scan_window = _source_scan_window_for_request(source, request)
    if scan_window is not None:
        return ("scan", scan_window[0], scan_window[1])
    return ("rt", request.rt_min, request.rt_max)


def _source_scan_window_for_request(
    source: OwnerBackfillSource,
    request: XICRequest,
) -> tuple[int, int] | None:
    resolver = getattr(source, "scan_window_for_request", None)
    if not callable(resolver):
        return None
    try:
        start_scan, end_scan = resolver(request)
    except (AttributeError, NotImplementedError):
        return None
    return int(start_scan), int(end_scan)


def _backfill_feature_sample(
    feature: OwnerAlignedFeature,
    sample_stem: str,
    source: OwnerBackfillSource,
    *,
    alignment_config: AlignmentConfig,
    peak_config: ExtractionConfig,
) -> AlignedCell | None:
    rt_window_min = alignment_config.max_rt_sec / 60.0
    rt_min = feature.family_center_rt - rt_window_min
    rt_max = feature.family_center_rt + rt_window_min
    try:
        rt, intensity = source.extract_xic(
            feature.family_center_mz,
            rt_min,
            rt_max,
            alignment_config.preferred_ppm,
        )
        rt_array, intensity_array = _validated_trace_arrays(rt, intensity)
    except (OSError, ValueError):
        return None
    result = find_peak_and_area(
        rt_array,
        intensity_array,
        peak_config,
        preferred_rt=feature.family_center_rt,
        strict_preferred_rt=False,
    )
    if result.status != "OK" or result.peak is None:
        return None
    peak = result.peak
    return AlignedCell(
        sample_stem=sample_stem,
        cluster_id=feature.feature_family_id,
        status="rescued",
        area=peak.area,
        apex_rt=peak.rt,
        height=peak.intensity,
        peak_start_rt=peak.peak_start,
        peak_end_rt=peak.peak_end,
        rt_delta_sec=(peak.rt - feature.family_center_rt) * 60.0,
        trace_quality="owner_backfill",
        scan_support_score=None,
        source_candidate_id=None,
        source_raw_file=None,
        reason="owner-centered MS1 backfill",
    )


def _backfill_feature_sample_trace(
    feature: OwnerAlignedFeature,
    sample_stem: str,
    trace: XICTrace,
    *,
    preferred_rt: float | None = None,
    peak_config: ExtractionConfig,
) -> AlignedCell | None:
    try:
        rt_array, intensity_array = _validated_trace_arrays(trace.rt, trace.intensity)
    except ValueError:
        return None
    result = find_peak_and_area(
        rt_array,
        intensity_array,
        peak_config,
        preferred_rt=(
            feature.family_center_rt if preferred_rt is None else preferred_rt
        ),
        strict_preferred_rt=False,
    )
    if result.status != "OK" or result.peak is None:
        return None
    peak = result.peak
    return AlignedCell(
        sample_stem=sample_stem,
        cluster_id=feature.feature_family_id,
        status="rescued",
        area=peak.area,
        apex_rt=peak.rt,
        height=peak.intensity,
        peak_start_rt=peak.peak_start,
        peak_end_rt=peak.peak_end,
        rt_delta_sec=(peak.rt - feature.family_center_rt) * 60.0,
        trace_quality="owner_backfill",
        scan_support_score=None,
        source_candidate_id=None,
        source_raw_file=None,
        reason="owner-centered MS1 backfill",
    )


def _backfill_seed_centers(
    feature: OwnerAlignedFeature,
) -> tuple[tuple[float, float], ...]:
    return feature.backfill_seed_centers or (
        (feature.family_center_mz, feature.family_center_rt),
    )


def _detected_owner_can_be_superseded(
    feature: OwnerAlignedFeature,
    owner: object | None,
) -> bool:
    detected_area = _positive_finite(getattr(owner, "owner_area", None))
    if detected_area is None:
        return False
    family_area = _median_owner_area(feature)
    if family_area is None:
        return False
    return detected_area <= family_area * 0.25


def _median_owner_area(feature: OwnerAlignedFeature) -> float | None:
    areas = [
        area
        for owner in feature.owners
        for area in (_positive_finite(getattr(owner, "owner_area", None)),)
        if area is not None
    ]
    return float(median(areas)) if areas else None


def _positive_finite(value: object) -> float | None:
    if (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
        and value > 0
    ):
        return float(value)
    return None


def _keep_best_rescued_cell(
    cells: dict[tuple[str, str], AlignedCell],
    candidate: AlignedCell,
) -> None:
    key = (candidate.cluster_id, candidate.sample_stem)
    current = cells.get(key)
    if current is None or _rescued_cell_sort_key(candidate) < _rescued_cell_sort_key(
        current,
    ):
        cells[key] = candidate


def _rescued_cell_sort_key(cell: AlignedCell) -> tuple[float, float, float]:
    area = float(cell.area or 0.0)
    rt_delta = abs(cell.rt_delta_sec) if cell.rt_delta_sec is not None else np.inf
    apex_rt = float(cell.apex_rt or 0.0)
    return (-area, rt_delta, apex_rt)


def _extract_many(
    source: OwnerBackfillSource,
    requests: tuple[XICRequest, ...],
) -> tuple[XICTrace, ...]:
    if hasattr(source, "extract_xic_many"):
        return tuple(source.extract_xic_many(requests))  # type: ignore[attr-defined]
    traces: list[XICTrace] = []
    for request in requests:
        rt, intensity = source.extract_xic(
            request.mz,
            request.rt_min,
            request.rt_max,
            request.ppm_tol,
        )
        traces.append(XICTrace.from_arrays(rt, intensity))
    return tuple(traces)


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
        raise ValueError("owner backfill trace arrays must be finite 1D pairs")
    return rt_array, intensity_array
