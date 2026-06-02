from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from itertools import groupby
from typing import Literal, Protocol

import numpy as np
from numpy.typing import NDArray

from xic_extractor.alignment.backfill_scope import (
    any_detected_owner_can_be_superseded,
    backfill_request_sample_stems,
    backfill_seed_centers,
)
from xic_extractor.alignment.cell_region_audit import with_region_audit
from xic_extractor.alignment.config import AlignmentConfig
from xic_extractor.alignment.matrix import AlignedCell
from xic_extractor.alignment.matrix_handoff import integration_from_peak_trace
from xic_extractor.alignment.owner_area import median_owner_area, positive_finite
from xic_extractor.alignment.owner_group_delivery import (
    OwnerGroupDeliveryFeature,
    OwnerGroupDeliveryFeatures,
)
from xic_extractor.alignment.ownership_models import SampleLocalMS1Owner
from xic_extractor.alignment.trace_context import alignment_trace_group
from xic_extractor.config import ExtractionConfig
from xic_extractor.peak_detection.region_audit import build_peak_region_audit_summary
from xic_extractor.signal_processing import find_peak_and_area
from xic_extractor.xic_models import XICRequest, XICTrace

_RequestItem = tuple[OwnerGroupDeliveryFeature, str, XICRequest, float]
_RequestGroupKey = tuple[str, int | float, int | float]
_WindowedRequestItem = tuple[_RequestItem, tuple[int, int]]
OwnerBackfillWindowStrategy = Literal["exact", "super-window"]
OWNER_BACKFILL_WINDOW_STRATEGIES: tuple[OwnerBackfillWindowStrategy, ...] = (
    "exact",
    "super-window",
)


class OwnerBackfillSource(Protocol):
    def extract_xic(
        self,
        mz: float,
        rt_min: float,
        rt_max: float,
        ppm_tol: float,
    ) -> tuple[NDArray[np.float64], NDArray[np.float64]]: ...


def build_owner_backfill_cells(
    features: OwnerGroupDeliveryFeatures,
    *,
    sample_order: tuple[str, ...],
    raw_sources: Mapping[str, OwnerBackfillSource],
    validation_raw_sources: Mapping[str, OwnerBackfillSource] | None = None,
    alignment_config: AlignmentConfig,
    peak_config: ExtractionConfig,
    raw_xic_batch_size: int = 1,
    owner_backfill_window_strategy: OwnerBackfillWindowStrategy = "exact",
    owner_backfill_superwindow_span_factor: int = 2,
    emit_region_audit: bool = False,
    region_audit_family_ids: frozenset[str] | None = None,
    audit_evidence_mode: str = "full",
) -> tuple[AlignedCell, ...]:
    if raw_xic_batch_size < 1:
        raise ValueError("raw_xic_batch_size must be >= 1")
    if owner_backfill_superwindow_span_factor < 1:
        raise ValueError("owner_backfill_superwindow_span_factor must be >= 1")
    if owner_backfill_window_strategy not in OWNER_BACKFILL_WINDOW_STRATEGIES:
        raise ValueError(
            "owner_backfill_window_strategy must be exact or super-window",
        )
    effective_emit_region_audit = emit_region_audit and audit_evidence_mode != "none"
    cells: list[AlignedCell] = []
    pending: dict[str, list[_RequestItem]] = defaultdict(list)
    rt_window_min = alignment_config.max_rt_sec / 60.0
    raw_sample_stems = frozenset(raw_sources)
    for feature in features:
        for sample_stem in backfill_request_sample_stems(
            feature,
            sample_order=sample_order,
            raw_sample_stems=raw_sample_stems,
            alignment_config=alignment_config,
        ):
            for seed_mz, seed_rt in backfill_seed_centers(feature):
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
        for chunk, traces in _iter_extracted_request_traces(
            source,
            tuple(sample_requests),
            raw_xic_batch_size,
            window_strategy=owner_backfill_window_strategy,
            superwindow_span_factor=owner_backfill_superwindow_span_factor,
        ):
            for (feature, requested_sample, request, preferred_rt), trace in zip(
                chunk,
                traces,
                strict=True,
            ):
                cell = _backfill_feature_sample_trace(
                    feature,
                    requested_sample,
                    trace,
                    request=request,
                    preferred_rt=preferred_rt,
                    peak_config=peak_config,
                    emit_region_audit=_emit_region_audit_for_family(
                        effective_emit_region_audit,
                        feature.feature_family_id,
                        region_audit_family_ids,
                    ),
                )
                if cell is not None:
                    if validation_raw_sources is None:
                        _keep_best_rescued_cell(
                            rescued_by_feature_sample,
                            cell,
                        )
                    else:
                        validation_pending[requested_sample].append(
                            (feature, requested_sample, request, preferred_rt)
                        )
    if validation_raw_sources is not None:
        for sample_stem in sample_order:
            sample_requests = validation_pending.get(sample_stem, [])
            if not sample_requests or sample_stem not in validation_raw_sources:
                continue
            source = validation_raw_sources[sample_stem]
            for chunk, traces in _iter_extracted_request_traces(
                source,
                tuple(sample_requests),
                raw_xic_batch_size,
                window_strategy="exact",
                superwindow_span_factor=owner_backfill_superwindow_span_factor,
            ):
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
                        request=_request,
                        preferred_rt=preferred_rt,
                        peak_config=peak_config,
                        emit_region_audit=_emit_region_audit_for_family(
                            effective_emit_region_audit,
                            feature.feature_family_id,
                            region_audit_family_ids,
                        ),
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


def _iter_extracted_request_traces(
    source: OwnerBackfillSource,
    items: tuple[_RequestItem, ...],
    chunk_size: int,
    *,
    window_strategy: OwnerBackfillWindowStrategy,
    superwindow_span_factor: int,
):
    if window_strategy == "super-window":
        groups = _superwindow_groups(
            source,
            items,
            superwindow_span_factor=superwindow_span_factor,
        )
        if groups is not None:
            for group in groups:
                group_items = tuple(item for item, _scan_window in group)
                try:
                    yield group_items, _extract_superwindow_group(source, group)
                except OSError:
                    yield from _iter_exact_request_traces(
                        source,
                        group_items,
                        chunk_size,
                    )
            return
    yield from _iter_exact_request_traces(source, items, chunk_size)


def _iter_exact_request_traces(
    source: OwnerBackfillSource,
    items: tuple[_RequestItem, ...],
    chunk_size: int,
):
    for chunk in _scan_window_aware_chunks(source, items, chunk_size):
        try:
            traces = _extract_many(source, tuple(item[2] for item in chunk))
        except OSError:
            continue
        yield chunk, traces


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


def _superwindow_groups(
    source: OwnerBackfillSource,
    items: tuple[_RequestItem, ...],
    *,
    superwindow_span_factor: int,
) -> tuple[tuple[_WindowedRequestItem, ...], ...] | None:
    windowed_items: list[_WindowedRequestItem] = []
    for item in items:
        scan_window = _source_scan_window_for_request(source, item[2])
        if scan_window is None:
            return None
        if _source_retention_time_for_scan(source, scan_window[0]) is None:
            return None
        if _source_retention_time_for_scan(source, scan_window[1]) is None:
            return None
        windowed_items.append((item, scan_window))
    if not windowed_items:
        return ()

    ordered = tuple(sorted(windowed_items, key=_windowed_request_sort_key))
    groups: list[tuple[_WindowedRequestItem, ...]] = []
    current: list[_WindowedRequestItem] = []
    current_start = 0
    current_end = 0
    current_max_span = 1
    for windowed_item in ordered:
        scan_start, scan_end = windowed_item[1]
        item_span = _scan_span(scan_start, scan_end)
        if not current:
            current = [windowed_item]
            current_start = scan_start
            current_end = scan_end
            current_max_span = item_span
            continue

        proposed_start = min(current_start, scan_start)
        proposed_end = max(current_end, scan_end)
        proposed_max_span = max(current_max_span, item_span)
        overlaps_current = scan_start <= current_end
        within_span_limit = (
            _scan_span(proposed_start, proposed_end)
            <= proposed_max_span * superwindow_span_factor
        )
        if overlaps_current and within_span_limit:
            current.append(windowed_item)
            current_start = proposed_start
            current_end = proposed_end
            current_max_span = proposed_max_span
            continue

        groups.append(tuple(current))
        current = [windowed_item]
        current_start = scan_start
        current_end = scan_end
        current_max_span = item_span
    if current:
        groups.append(tuple(current))
    return tuple(groups)


def _windowed_request_sort_key(
    windowed_item: _WindowedRequestItem,
) -> tuple[int, int, float, str, str]:
    item, scan_window = windowed_item
    feature, sample_stem, request, _preferred_rt = item
    return (
        scan_window[0],
        scan_window[1],
        request.mz,
        feature.feature_family_id,
        sample_stem,
    )


def _extract_superwindow_group(
    source: OwnerBackfillSource,
    group: tuple[_WindowedRequestItem, ...],
) -> tuple[XICTrace, ...]:
    union_start = min(scan_window[0] for _item, scan_window in group)
    union_end = max(scan_window[1] for _item, scan_window in group)
    union_rt_min = _source_retention_time_for_scan(source, union_start)
    union_rt_max = _source_retention_time_for_scan(source, union_end)
    if union_rt_min is None or union_rt_max is None:
        raise AttributeError("scan RT lookup is unavailable")
    if union_rt_min > union_rt_max:
        union_rt_min, union_rt_max = union_rt_max, union_rt_min
    union_requests = tuple(
        XICRequest(
            mz=item[2].mz,
            rt_min=union_rt_min,
            rt_max=union_rt_max,
            ppm_tol=item[2].ppm_tol,
        )
        for item, _scan_window in group
    )
    union_traces = _extract_many(source, union_requests)
    return tuple(
        _crop_trace_to_scan_window(source, trace, scan_window)
        for trace, (_item, scan_window) in zip(union_traces, group, strict=True)
    )


def _crop_trace_to_scan_window(
    source: OwnerBackfillSource,
    trace: XICTrace,
    scan_window: tuple[int, int],
) -> XICTrace:
    rt_min = _source_retention_time_for_scan(source, scan_window[0])
    rt_max = _source_retention_time_for_scan(source, scan_window[1])
    if rt_min is None or rt_max is None:
        return trace
    if rt_min > rt_max:
        rt_min, rt_max = rt_max, rt_min
    mask = (trace.rt >= rt_min) & (trace.rt <= rt_max)
    return XICTrace.from_arrays(trace.rt[mask], trace.intensity[mask])


def _scan_span(start_scan: int, end_scan: int) -> int:
    return max(1, abs(end_scan - start_scan) + 1)


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


def _source_retention_time_for_scan(
    source: OwnerBackfillSource,
    scan_number: int,
) -> float | None:
    resolver = getattr(source, "retention_time_for_scan", None)
    if not callable(resolver):
        return None
    try:
        return float(resolver(scan_number))
    except (AttributeError, NotImplementedError):
        return None


def _backfill_feature_sample(
    feature: OwnerGroupDeliveryFeature,
    sample_stem: str,
    source: OwnerBackfillSource,
    *,
    alignment_config: AlignmentConfig,
    peak_config: ExtractionConfig,
    emit_region_audit: bool = False,
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
    trace_group = (
        alignment_trace_group(
            sample_stem=sample_stem,
            family_id=feature.feature_family_id,
            mz=feature.family_center_mz,
            rt_values=rt_array,
            intensity_values=intensity_array,
            rt_min=rt_min,
            rt_max=rt_max,
            ppm_tol=alignment_config.preferred_ppm,
            expected_rt_min=feature.family_center_rt,
            neutral_loss_tag=feature.neutral_loss_tag,
            product_mz=feature.family_product_mz,
            observed_neutral_loss_da=feature.family_observed_neutral_loss_da,
            source="owner_backfill",
        )
        if emit_region_audit
        else None
    )
    region_audit = (
        build_peak_region_audit_summary(
            rt_array,
            intensity_array,
            result,
            peak_config,
            trace_group=trace_group,
        )
        if emit_region_audit
        else None
    )
    peak = result.peak
    cell = AlignedCell(
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
        scan_support_score=_scan_support_score(
            rt_array,
            peak_start=peak.peak_start,
            peak_end=peak.peak_end,
            scans_target=peak_config.resolver_min_scans,
        ),
        source_candidate_id=None,
        source_raw_file=None,
        reason="owner-centered MS1 backfill",
        selected_integration=integration_from_peak_trace(
            peak,
            rt_array,
            intensity_array,
            boundary_sources=("owner_backfill",),
            baseline_integration_method=getattr(
                peak_config,
                "baseline_integration_method",
                "asls",
            ),
        ),
        backfill_seed_mz=feature.family_center_mz,
        backfill_seed_rt=feature.family_center_rt,
        backfill_request_rt_min=rt_min,
        backfill_request_rt_max=rt_max,
        backfill_request_ppm=alignment_config.preferred_ppm,
    )
    return with_region_audit(cell, region_audit)


def _backfill_feature_sample_trace(
    feature: OwnerGroupDeliveryFeature,
    sample_stem: str,
    trace: XICTrace,
    *,
    request: XICRequest,
    preferred_rt: float | None = None,
    peak_config: ExtractionConfig,
    emit_region_audit: bool = False,
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
    trace_group = (
        alignment_trace_group(
            sample_stem=sample_stem,
            family_id=feature.feature_family_id,
            mz=request.mz,
            rt_values=rt_array,
            intensity_values=intensity_array,
            rt_min=request.rt_min,
            rt_max=request.rt_max,
            ppm_tol=request.ppm_tol,
            expected_rt_min=feature.family_center_rt,
            neutral_loss_tag=feature.neutral_loss_tag,
            product_mz=feature.family_product_mz,
            observed_neutral_loss_da=feature.family_observed_neutral_loss_da,
            source="owner_backfill_batch",
        )
        if emit_region_audit
        else None
    )
    region_audit = (
        build_peak_region_audit_summary(
            rt_array,
            intensity_array,
            result,
            peak_config,
            trace_group=trace_group,
        )
        if emit_region_audit
        else None
    )
    peak = result.peak
    cell = AlignedCell(
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
        scan_support_score=_scan_support_score(
            rt_array,
            peak_start=peak.peak_start,
            peak_end=peak.peak_end,
            scans_target=peak_config.resolver_min_scans,
        ),
        source_candidate_id=None,
        source_raw_file=None,
        reason="owner-centered MS1 backfill",
        selected_integration=integration_from_peak_trace(
            peak,
            rt_array,
            intensity_array,
            boundary_sources=("owner_backfill_batch",),
            baseline_integration_method=getattr(
                peak_config,
                "baseline_integration_method",
                "asls",
            ),
        ),
        backfill_seed_mz=request.mz,
        backfill_seed_rt=preferred_rt,
        backfill_request_rt_min=request.rt_min,
        backfill_request_rt_max=request.rt_max,
        backfill_request_ppm=request.ppm_tol,
    )
    return with_region_audit(cell, region_audit)


def _backfill_seed_centers(
    feature: OwnerGroupDeliveryFeature,
) -> tuple[tuple[float, float], ...]:
    return backfill_seed_centers(feature)


def _any_detected_owner_can_be_superseded(
    feature: OwnerGroupDeliveryFeature,
    owners: Sequence[SampleLocalMS1Owner] | None,
) -> bool:
    return any_detected_owner_can_be_superseded(feature, owners)


def _detected_owner_can_be_superseded(
    feature: OwnerGroupDeliveryFeature,
    owner: SampleLocalMS1Owner,
) -> bool:
    detected_area = positive_finite(owner.owner_area)
    if detected_area is None:
        return False
    family_area = median_owner_area(feature)
    if family_area is None:
        return False
    return detected_area <= family_area * 0.25


def _emit_region_audit_for_family(
    emit_region_audit: bool,
    family_id: str,
    region_audit_family_ids: frozenset[str] | None,
) -> bool:
    if not emit_region_audit:
        return False
    if region_audit_family_ids is None:
        return True
    return family_id in region_audit_family_ids


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
    unique_requests = tuple(dict.fromkeys(requests))
    if len(unique_requests) != len(requests):
        unique_traces = _extract_unique_many(source, unique_requests)
        traces_by_request = dict(zip(unique_requests, unique_traces, strict=True))
        return tuple(traces_by_request[request] for request in requests)
    return _extract_unique_many(source, requests)


def _extract_unique_many(
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
