from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from typing import Protocol

import numpy as np
from numpy.typing import NDArray

from xic_extractor.alignment.config import AlignmentConfig
from xic_extractor.alignment.matrix import AlignedCell
from xic_extractor.alignment.owner_clustering import OwnerAlignedFeature
from xic_extractor.config import ExtractionConfig
from xic_extractor.signal_processing import find_peak_and_area
from xic_extractor.xic_models import XICRequest, XICTrace


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
    alignment_config: AlignmentConfig,
    peak_config: ExtractionConfig,
    raw_xic_batch_size: int = 1,
) -> tuple[AlignedCell, ...]:
    if raw_xic_batch_size < 1:
        raise ValueError("raw_xic_batch_size must be >= 1")
    cells: list[AlignedCell] = []
    pending: dict[str, list[tuple[OwnerAlignedFeature, str, XICRequest]]] = (
        defaultdict(list)
    )
    rt_window_min = alignment_config.max_rt_sec / 60.0
    for feature in features:
        if feature.review_only:
            continue
        detected_samples = {owner.sample_stem for owner in feature.owners}
        if (
            len(detected_samples)
            < alignment_config.owner_backfill_min_detected_samples
        ):
            continue
        for sample_stem in sample_order:
            if sample_stem in detected_samples or sample_stem not in raw_sources:
                continue
            pending[sample_stem].append(
                (
                    feature,
                    sample_stem,
                    XICRequest(
                        mz=feature.family_center_mz,
                        rt_min=feature.family_center_rt - rt_window_min,
                        rt_max=feature.family_center_rt + rt_window_min,
                        ppm_tol=alignment_config.preferred_ppm,
                    ),
                )
            )
    rescued_by_feature_sample: dict[tuple[str, str], AlignedCell] = {}
    for sample_stem in sample_order:
        sample_requests = pending.get(sample_stem, [])
        if not sample_requests:
            continue
        source = raw_sources[sample_stem]
        ordered_requests = tuple(sorted(sample_requests, key=_request_locality_key))
        for chunk in _chunked(ordered_requests, raw_xic_batch_size):
            try:
                traces = _extract_many(source, tuple(item[2] for item in chunk))
            except OSError:
                continue
            for (feature, requested_sample, _request), trace in zip(
                chunk,
                traces,
                strict=True,
            ):
                cell = _backfill_feature_sample_trace(
                    feature,
                    requested_sample,
                    trace,
                    peak_config=peak_config,
                )
                if cell is not None:
                    rescued_by_feature_sample[
                        (feature.feature_family_id, requested_sample)
                    ] = cell
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


def _request_locality_key(
    item: tuple[OwnerAlignedFeature, str, XICRequest],
) -> tuple[float, float, float, str, str]:
    feature, sample_stem, request = item
    return (
        request.rt_min,
        request.rt_max,
        request.mz,
        feature.feature_family_id,
        sample_stem,
    )


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


def _chunked(
    items: tuple[object, ...],
    chunk_size: int,
) -> tuple[tuple[object, ...], ...]:
    if chunk_size < 1:
        raise ValueError("raw_xic_batch_size must be >= 1")
    return tuple(
        items[index : index + chunk_size]
        for index in range(0, len(items), chunk_size)
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
        raise ValueError("owner backfill trace arrays must be finite 1D pairs")
    return rt_array, intensity_array
