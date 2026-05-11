from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol

import numpy as np
from numpy.typing import NDArray

from xic_extractor.alignment.config import AlignmentConfig
from xic_extractor.alignment.matrix import AlignmentMatrix
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
    return AlignmentMatrix(clusters=clusters, cells=(), sample_order=sample_order)


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
