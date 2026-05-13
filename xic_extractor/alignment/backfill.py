from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol

import numpy as np
from numpy.typing import NDArray

from xic_extractor.alignment.config import AlignmentConfig
from xic_extractor.alignment.matrix import AlignedCell, AlignmentMatrix
from xic_extractor.alignment.models import AlignmentCluster
from xic_extractor.config import ExtractionConfig
from xic_extractor.signal_processing import find_peak_and_area


class MS1BackfillSource(Protocol):
    def extract_xic(
        self,
        mz: float,
        rt_min: float,
        rt_max: float,
        ppm_tol: float,
    ) -> tuple[NDArray[np.float64], NDArray[np.float64]]: ...


def backfill_alignment_matrix(
    clusters: tuple[AlignmentCluster, ...],
    *,
    sample_order: tuple[str, ...],
    raw_sources: Mapping[str, MS1BackfillSource],
    alignment_config: AlignmentConfig,
    peak_config: ExtractionConfig,
) -> AlignmentMatrix:
    _validate_sample_order(sample_order)
    _validate_cluster_members(clusters, sample_order)
    cells: list[AlignedCell] = []
    for cluster in clusters:
        members_by_sample = {
            member.sample_stem: member
            for member in cluster.members
        }
        for sample_stem in sample_order:
            member = members_by_sample.get(sample_stem)
            if member is not None:
                cells.append(_detected_cell(cluster, member))
            elif cluster.has_anchor:
                cells.append(
                    _backfill_anchor_cell(
                        cluster,
                        sample_stem,
                        raw_sources=raw_sources,
                        alignment_config=alignment_config,
                        peak_config=peak_config,
                    ),
                )
            else:
                cells.append(_unchecked_cell(cluster, sample_stem))
    return AlignmentMatrix(
        clusters=clusters,
        cells=tuple(cells),
        sample_order=sample_order,
    )


def _validate_sample_order(sample_order: tuple[str, ...]) -> None:
    if len(set(sample_order)) != len(sample_order):
        raise ValueError("sample_order must be unique")


def _validate_cluster_members(
    clusters: tuple[AlignmentCluster, ...],
    sample_order: tuple[str, ...],
) -> None:
    allowed_samples = set(sample_order)
    for cluster in clusters:
        seen_samples: set[str] = set()
        for member in cluster.members:
            sample_stem = member.sample_stem
            if sample_stem not in allowed_samples:
                raise ValueError(
                    f"cluster {cluster.cluster_id} member sample "
                    f"'{sample_stem}' is missing from sample_order",
                )
            if sample_stem in seen_samples:
                raise ValueError(
                    f"cluster {cluster.cluster_id} has duplicate members "
                    f"for sample '{sample_stem}'",
                )
            seen_samples.add(sample_stem)


def _detected_cell(cluster: AlignmentCluster, member: Any) -> AlignedCell:
    apex_rt = member.ms1_apex_rt
    return AlignedCell(
        sample_stem=member.sample_stem,
        cluster_id=cluster.cluster_id,
        status="detected",
        area=member.ms1_area,
        apex_rt=apex_rt,
        height=member.ms1_height,
        peak_start_rt=member.ms1_peak_rt_start,
        peak_end_rt=member.ms1_peak_rt_end,
        rt_delta_sec=_rt_delta_sec(apex_rt, cluster.cluster_center_rt),
        trace_quality=member.ms1_trace_quality,
        scan_support_score=member.ms1_scan_support_score,
        source_candidate_id=member.candidate_id,
        source_raw_file=member.raw_file,
        reason="detected candidate",
    )


def _backfill_anchor_cell(
    cluster: AlignmentCluster,
    sample_stem: str,
    *,
    raw_sources: Mapping[str, MS1BackfillSource],
    alignment_config: AlignmentConfig,
    peak_config: ExtractionConfig,
) -> AlignedCell:
    source = raw_sources.get(sample_stem)
    if source is None:
        return _unchecked_cell(
            cluster,
            sample_stem,
            reason="missing raw source for MS1 backfill",
        )

    rt_min = cluster.cluster_center_rt - alignment_config.max_rt_sec / 60.0
    rt_max = cluster.cluster_center_rt + alignment_config.max_rt_sec / 60.0
    try:
        rt, intensity = source.extract_xic(
            cluster.cluster_center_mz,
            rt_min,
            rt_max,
            alignment_config.preferred_ppm,
        )
        rt_array, intensity_array = _validated_trace_arrays(rt, intensity)
        result = find_peak_and_area(
            rt_array,
            intensity_array,
            peak_config,
            preferred_rt=cluster.cluster_center_rt,
            strict_preferred_rt=False,
        )
    except Exception:
        return _unchecked_cell(
            cluster,
            sample_stem,
            reason="MS1 backfill could not be checked",
        )

    if result.status != "OK" or result.peak is None:
        return _absent_cell(
            cluster,
            sample_stem,
            reason="MS1 backfill checked and no peak found",
        )

    peak = result.peak
    rt_delta_sec = _rt_delta_sec(peak.rt, cluster.cluster_center_rt)
    if rt_delta_sec is None or abs(rt_delta_sec) > alignment_config.max_rt_sec:
        return _absent_cell(
            cluster,
            sample_stem,
            apex_rt=peak.rt,
            reason="MS1 peak outside cluster RT guard",
        )

    return AlignedCell(
        sample_stem=sample_stem,
        cluster_id=cluster.cluster_id,
        status="rescued",
        area=peak.area,
        apex_rt=peak.rt,
        height=peak.intensity,
        peak_start_rt=peak.peak_start,
        peak_end_rt=peak.peak_end,
        rt_delta_sec=rt_delta_sec,
        trace_quality="rescued",
        scan_support_score=_scan_support_score(
            rt_array,
            peak_start=peak.peak_start,
            peak_end=peak.peak_end,
            scans_target=peak_config.resolver_min_scans,
        ),
        source_candidate_id=None,
        source_raw_file=None,
        reason="MS1 peak rescued at cluster center",
    )


def _absent_cell(
    cluster: AlignmentCluster,
    sample_stem: str,
    *,
    apex_rt: float | None = None,
    reason: str,
) -> AlignedCell:
    return AlignedCell(
        sample_stem=sample_stem,
        cluster_id=cluster.cluster_id,
        status="absent",
        area=None,
        apex_rt=apex_rt,
        height=None,
        peak_start_rt=None,
        peak_end_rt=None,
        rt_delta_sec=_rt_delta_sec(apex_rt, cluster.cluster_center_rt),
        trace_quality="missing",
        scan_support_score=None,
        source_candidate_id=None,
        source_raw_file=None,
        reason=reason,
    )


def _unchecked_cell(
    cluster: AlignmentCluster,
    sample_stem: str,
    *,
    reason: str = "backfill skipped for non-anchor cluster",
) -> AlignedCell:
    return AlignedCell(
        sample_stem=sample_stem,
        cluster_id=cluster.cluster_id,
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


def _rt_delta_sec(apex_rt: float | None, center_rt: float) -> float | None:
    if apex_rt is None:
        return None
    return (apex_rt - center_rt) * 60.0


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
            "MS1 backfill trace arrays must be finite one-dimensional pairs",
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
