from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from statistics import median

from xic_extractor.alignment.config import AlignmentConfig
from xic_extractor.alignment.matrix import AlignedCell, AlignmentMatrix
from xic_extractor.alignment.models import AlignmentCluster

_PRESENT_STATUSES = {"detected", "rescued"}


@dataclass(frozen=True)
class MS1FeatureFamily:
    feature_family_id: str
    neutral_loss_tag: str
    family_center_mz: float
    family_center_rt: float
    family_product_mz: float
    family_observed_neutral_loss_da: float
    has_anchor: bool
    event_clusters: tuple[AlignmentCluster, ...]
    event_cluster_ids: tuple[str, ...]
    event_member_count: int
    evidence: str


def build_ms1_feature_family(
    *,
    family_id: str,
    event_clusters: tuple[AlignmentCluster, ...],
    evidence: str,
) -> MS1FeatureFamily:
    if not event_clusters:
        raise ValueError("MS1 feature family requires at least one event cluster")
    contributors = tuple(cluster for cluster in event_clusters if cluster.has_anchor)
    if not contributors:
        contributors = event_clusters
    neutral_loss_tags = {cluster.neutral_loss_tag for cluster in event_clusters}
    if len(neutral_loss_tags) != 1:
        raise ValueError("MS1 feature family requires one neutral_loss_tag")
    return MS1FeatureFamily(
        feature_family_id=family_id,
        neutral_loss_tag=event_clusters[0].neutral_loss_tag,
        family_center_mz=median(cluster.cluster_center_mz for cluster in contributors),
        family_center_rt=median(cluster.cluster_center_rt for cluster in contributors),
        family_product_mz=median(
            cluster.cluster_product_mz for cluster in contributors
        ),
        family_observed_neutral_loss_da=median(
            cluster.cluster_observed_neutral_loss_da for cluster in contributors
        ),
        has_anchor=any(cluster.has_anchor for cluster in event_clusters),
        event_clusters=event_clusters,
        event_cluster_ids=tuple(cluster.cluster_id for cluster in event_clusters),
        event_member_count=sum(len(cluster.members) for cluster in event_clusters),
        evidence=evidence,
    )


def build_ms1_feature_families(
    clusters: tuple[AlignmentCluster, ...],
    *,
    event_matrix: AlignmentMatrix,
    config: AlignmentConfig,
) -> tuple[MS1FeatureFamily, ...]:
    cells_by_cluster = _cells_by_cluster(event_matrix)
    consumed: set[str] = set()
    groups: list[list[AlignmentCluster]] = []
    for cluster in clusters:
        if cluster.cluster_id in consumed:
            continue
        group = [cluster]
        for candidate in clusters:
            if (
                candidate.cluster_id == cluster.cluster_id
                or candidate.cluster_id in consumed
            ):
                continue
            if all(
                _same_ms1_feature_family(
                    candidate,
                    existing,
                    cells_by_cluster=cells_by_cluster,
                    config=config,
                )
                for existing in group
            ):
                group.append(candidate)
                consumed.add(candidate.cluster_id)
        consumed.add(cluster.cluster_id)
        groups.append(group)

    return tuple(
        build_ms1_feature_family(
            family_id=f"FAM{index:06d}",
            event_clusters=tuple(_sort_family_group(group, cells_by_cluster)),
            evidence=_family_evidence(group, cells_by_cluster),
        )
        for index, group in enumerate(groups, start=1)
    )


def _same_ms1_feature_family(
    left: AlignmentCluster,
    right: AlignmentCluster,
    *,
    cells_by_cluster: dict[str, tuple[AlignedCell, ...]],
    config: AlignmentConfig,
) -> bool:
    if left.neutral_loss_tag != right.neutral_loss_tag:
        return False
    if (
        _ppm(left.cluster_center_mz, right.cluster_center_mz)
        > config.duplicate_fold_ppm
    ):
        return False
    if (
        abs(left.cluster_center_rt - right.cluster_center_rt) * 60.0
        > config.duplicate_fold_rt_sec
    ):
        return False
    if (
        _ppm(left.cluster_product_mz, right.cluster_product_mz)
        > config.duplicate_fold_product_ppm
    ):
        return False
    if (
        _ppm(
            left.cluster_observed_neutral_loss_da,
            right.cluster_observed_neutral_loss_da,
        )
        > config.duplicate_fold_observed_loss_ppm
    ):
        return False
    if _ms2_signature_conflicts(left, right):
        return False

    left_present = _present_samples(cells_by_cluster.get(left.cluster_id, ()))
    right_present = _present_samples(cells_by_cluster.get(right.cluster_id, ()))
    shared = left_present & right_present
    union = left_present | right_present
    denominator = min(len(left_present), len(right_present))
    overlap = len(shared) / denominator if denominator else 0.0
    jaccard = len(shared) / len(union) if union else 0.0
    if len(shared) < config.duplicate_fold_min_shared_detected_count:
        return False
    if overlap < config.duplicate_fold_min_detected_overlap:
        return False

    high_shared_support = len(shared) >= 30 and overlap >= 0.8
    return high_shared_support or jaccard >= config.duplicate_fold_min_detected_jaccard


def _cells_by_cluster(matrix: AlignmentMatrix) -> dict[str, tuple[AlignedCell, ...]]:
    grouped: dict[str, list[AlignedCell]] = defaultdict(list)
    for cell in matrix.cells:
        grouped[cell.cluster_id].append(cell)
    return {cluster_id: tuple(cells) for cluster_id, cells in grouped.items()}


def _present_samples(cells: tuple[AlignedCell, ...]) -> frozenset[str]:
    return frozenset(
        cell.sample_stem for cell in cells if cell.status in _PRESENT_STATUSES
    )


def _sort_family_group(
    group: list[AlignmentCluster],
    cells_by_cluster: dict[str, tuple[AlignedCell, ...]],
) -> tuple[AlignmentCluster, ...]:
    return tuple(
        sorted(
            group,
            key=lambda cluster: (
                0 if cluster.has_anchor else 1,
                -len(_present_samples(cells_by_cluster.get(cluster.cluster_id, ()))),
                cluster.cluster_center_mz,
                cluster.cluster_center_rt,
                cluster.cluster_id,
            ),
        ),
    )


def _family_evidence(
    group: list[AlignmentCluster],
    cells_by_cluster: dict[str, tuple[AlignedCell, ...]],
) -> str:
    if len(group) == 1:
        return "single_event_cluster"
    shared_counts: list[int] = []
    overlaps: list[float] = []
    primary = _sort_family_group(group, cells_by_cluster)[0]
    primary_samples = _present_samples(cells_by_cluster.get(primary.cluster_id, ()))
    for secondary in group:
        if secondary.cluster_id == primary.cluster_id:
            continue
        secondary_samples = _present_samples(
            cells_by_cluster.get(secondary.cluster_id, ())
        )
        shared = primary_samples & secondary_samples
        denominator = min(len(primary_samples), len(secondary_samples))
        shared_counts.append(len(shared))
        overlaps.append(len(shared) / denominator if denominator else 0.0)
    return (
        "cid_nl_only;"
        f"event_clusters={len(group)};"
        f"shared_detected={min(shared_counts)};"
        f"overlap={min(overlaps):.3f}"
    )


def _ms2_signature_conflicts(
    left: AlignmentCluster,
    right: AlignmentCluster,
) -> bool:
    left_signature = getattr(left, "cluster_ms2_signature", None)
    right_signature = getattr(right, "cluster_ms2_signature", None)
    if left_signature is None or right_signature is None:
        return False
    return left_signature != right_signature


def _ppm(left: float, right: float) -> float:
    return abs(left - right) / max(abs(left), 1e-12) * 1_000_000.0
