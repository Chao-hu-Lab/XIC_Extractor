from __future__ import annotations

from collections.abc import Mapping
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
    return AlignmentMatrix(
        clusters=families,
        cells=tuple(cells),
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
    return AlignedCell(
        sample_stem=sample_stem,
        cluster_id=family.feature_family_id,
        status="detected",
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
        reason="family-centered MS1 integration",
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
