from types import SimpleNamespace

from xic_extractor.alignment.feature_family import build_ms1_feature_family
from xic_extractor.alignment.models import AlignmentCluster


def test_build_ms1_feature_family_tracks_event_clusters_and_cid_only_evidence():
    anchor = _cluster(
        "ALN000001",
        has_anchor=True,
        mz=242.114,
        rt=12.5927,
        members=("s1", "s2"),
    )
    secondary = _cluster(
        "ALN000002",
        has_anchor=False,
        mz=242.115,
        rt=12.5916,
        members=("s1",),
    )

    family = build_ms1_feature_family(
        family_id="FAM000001",
        event_clusters=(anchor, secondary),
        evidence="cid_nl_only;shared_detected=1;overlap=1",
    )

    assert family.feature_family_id == "FAM000001"
    assert family.neutral_loss_tag == "DNA_dR"
    assert family.family_center_mz == 242.114
    assert family.family_center_rt == 12.5927
    assert family.family_product_mz == 126.066
    assert family.family_observed_neutral_loss_da == 116.048
    assert family.has_anchor is True
    assert family.event_cluster_ids == ("ALN000001", "ALN000002")
    assert family.event_member_count == 3
    assert family.evidence == "cid_nl_only;shared_detected=1;overlap=1"


def test_build_ms1_feature_family_uses_non_anchor_median_when_no_anchor_exists():
    left = _cluster("ALN000001", has_anchor=False, mz=100.0, rt=1.0)
    right = _cluster("ALN000002", has_anchor=False, mz=102.0, rt=1.2)

    family = build_ms1_feature_family(
        family_id="FAM000001",
        event_clusters=(left, right),
        evidence="cid_nl_only",
    )

    assert family.family_center_mz == 101.0
    assert family.family_center_rt == 1.1
    assert family.has_anchor is False


def _cluster(
    cluster_id: str,
    *,
    has_anchor: bool,
    mz: float = 242.114,
    rt: float = 12.5927,
    product: float = 126.066,
    observed_loss: float = 116.048,
    members: tuple[str, ...] = ("s1",),
) -> AlignmentCluster:
    member_objects = tuple(
        SimpleNamespace(sample_stem=sample, candidate_id=f"{cluster_id}#{sample}")
        for sample in members
    )
    return AlignmentCluster(
        cluster_id=cluster_id,
        neutral_loss_tag="DNA_dR",
        cluster_center_mz=mz,
        cluster_center_rt=rt,
        cluster_product_mz=product,
        cluster_observed_neutral_loss_da=observed_loss,
        has_anchor=has_anchor,
        members=member_objects,
        anchor_members=member_objects if has_anchor else (),
    )
