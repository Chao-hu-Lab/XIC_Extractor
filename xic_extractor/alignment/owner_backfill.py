from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol

import numpy as np
from numpy.typing import NDArray

from xic_extractor.alignment.config import AlignmentConfig
from xic_extractor.alignment.matrix import AlignedCell
from xic_extractor.alignment.owner_clustering import OwnerAlignedFeature
from xic_extractor.config import ExtractionConfig
from xic_extractor.signal_processing import find_peak_and_area


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
) -> tuple[AlignedCell, ...]:
    cells: list[AlignedCell] = []
    for feature in features:
        if feature.review_only:
            continue
        detected_samples = {owner.sample_stem for owner in feature.owners}
        for sample_stem in sample_order:
            if sample_stem in detected_samples:
                continue
            source = raw_sources.get(sample_stem)
            if source is None:
                continue
            cell = _backfill_feature_sample(
                feature,
                sample_stem,
                source,
                alignment_config=alignment_config,
                peak_config=peak_config,
            )
            if cell is not None:
                cells.append(cell)
    return tuple(cells)


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
