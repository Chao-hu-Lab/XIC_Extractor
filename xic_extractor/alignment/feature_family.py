from __future__ import annotations

from dataclasses import dataclass
from statistics import median

from xic_extractor.alignment.models import AlignmentCluster


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
