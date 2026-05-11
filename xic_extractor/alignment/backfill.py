from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol

import numpy as np
from numpy.typing import NDArray

from xic_extractor.alignment.config import AlignmentConfig
from xic_extractor.alignment.matrix import AlignedCell, AlignmentMatrix
from xic_extractor.alignment.models import AlignmentCluster
from xic_extractor.config import ExtractionConfig


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


def _detected_cell(cluster: AlignmentCluster, member: object) -> AlignedCell:
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


def _unchecked_cell(cluster: AlignmentCluster, sample_stem: str) -> AlignedCell:
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
        reason="backfill skipped for non-anchor cluster",
    )


def _rt_delta_sec(apex_rt: float | None, center_rt: float) -> float | None:
    if apex_rt is None:
        return None
    return (apex_rt - center_rt) * 60.0
