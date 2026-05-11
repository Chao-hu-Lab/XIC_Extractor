from types import SimpleNamespace

from xic_extractor.alignment.config import AlignmentConfig
from xic_extractor.alignment.feature_family import (
    build_ms1_feature_families,
    build_ms1_feature_family,
)
from xic_extractor.alignment.matrix import AlignedCell, AlignmentMatrix
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


def test_high_shared_subset_event_clusters_consolidate_into_one_family():
    primary = _cluster(
        "ALN000001",
        has_anchor=True,
        mz=242.114,
        rt=12.5927,
        members=("s1", "s2", "s3", "s4", "s5"),
    )
    secondary = _cluster(
        "ALN000002",
        has_anchor=False,
        mz=242.115,
        rt=12.5916,
        members=("s1", "s2", "s3", "s4"),
    )
    matrix = _event_matrix(
        (primary, secondary),
        sample_order=("s1", "s2", "s3", "s4", "s5"),
    )

    families = build_ms1_feature_families(
        (primary, secondary),
        event_matrix=matrix,
        config=AlignmentConfig(),
    )

    assert len(families) == 1
    assert families[0].event_cluster_ids == ("ALN000001", "ALN000002")
    assert "cid_nl_only" in families[0].evidence
    assert "shared_detected=4" in families[0].evidence


def test_low_shared_subset_event_cluster_stays_separate_for_rare_discovery():
    primary = _cluster(
        "ALN000001",
        has_anchor=True,
        members=("s1", "s2", "s3", "s4", "s5"),
    )
    rare = _cluster(
        "ALN000002",
        has_anchor=False,
        mz=242.115,
        rt=12.5916,
        members=("s1",),
    )
    matrix = _event_matrix(
        (primary, rare),
        sample_order=("s1", "s2", "s3", "s4", "s5"),
    )

    families = build_ms1_feature_families(
        (primary, rare),
        event_matrix=matrix,
        config=AlignmentConfig(),
    )

    assert [family.event_cluster_ids for family in families] == [
        ("ALN000001",),
        ("ALN000002",),
    ]


def test_full_ms2_signature_conflict_blocks_family_consolidation_when_available():
    left = _cluster("ALN000001", has_anchor=True, members=("s1", "s2", "s3"))
    right = _cluster(
        "ALN000002",
        has_anchor=False,
        mz=242.115,
        rt=12.5916,
        members=("s1", "s2", "s3"),
    )
    object.__setattr__(left, "cluster_ms2_signature", ("126.066", "98.060"))
    object.__setattr__(right, "cluster_ms2_signature", ("126.066", "97.010"))
    matrix = _event_matrix((left, right), sample_order=("s1", "s2", "s3"))

    families = build_ms1_feature_families(
        (left, right),
        event_matrix=matrix,
        config=AlignmentConfig(),
    )

    assert [family.event_cluster_ids for family in families] == [
        ("ALN000001",),
        ("ALN000002",),
    ]


def test_rescued_overlap_without_shared_detected_does_not_make_one_family():
    left = _cluster(
        "ALN000001",
        has_anchor=True,
        mz=242.114,
        rt=12.5927,
        members=("s1",),
    )
    right = _cluster(
        "ALN000002",
        has_anchor=False,
        mz=242.115,
        rt=12.5916,
        members=("s2",),
    )
    matrix = AlignmentMatrix(
        clusters=(left, right),
        sample_order=("s1", "s2"),
        cells=(
            _cell("s1", "ALN000001", "detected", area=100.0),
            _cell("s2", "ALN000001", "rescued", area=80.0),
            _cell("s1", "ALN000002", "rescued", area=90.0),
            _cell("s2", "ALN000002", "detected", area=95.0),
        ),
    )

    families = build_ms1_feature_families(
        (left, right),
        event_matrix=matrix,
        config=AlignmentConfig(
            duplicate_fold_min_shared_detected_count=1,
            duplicate_fold_min_detected_overlap=0.5,
            duplicate_fold_min_detected_jaccard=0.5,
        ),
    )

    assert [family.event_cluster_ids for family in families] == [
        ("ALN000001",),
        ("ALN000002",),
    ]


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


def _event_matrix(
    clusters: tuple[AlignmentCluster, ...],
    *,
    sample_order: tuple[str, ...],
) -> AlignmentMatrix:
    cells = []
    for cluster in clusters:
        member_samples = {member.sample_stem for member in cluster.members}
        for sample in sample_order:
            if sample in member_samples:
                cells.append(_cell(sample, cluster.cluster_id, "detected", area=100.0))
            else:
                cells.append(_cell(sample, cluster.cluster_id, "unchecked", area=None))
    return AlignmentMatrix(
        clusters=clusters,
        cells=tuple(cells),
        sample_order=sample_order,
    )


def _cell(
    sample_stem: str,
    cluster_id: str,
    status: str,
    *,
    area: float | None,
) -> AlignedCell:
    return AlignedCell(
        sample_stem=sample_stem,
        cluster_id=cluster_id,
        status=status,
        area=area,
        apex_rt=12.6 if area is not None else None,
        height=10.0 if area is not None else None,
        peak_start_rt=12.55 if area is not None else None,
        peak_end_rt=12.65 if area is not None else None,
        rt_delta_sec=0.0 if area is not None else None,
        trace_quality="clean" if area is not None else "unchecked",
        scan_support_score=1.0 if area is not None else None,
        source_candidate_id=f"{sample_stem}#{cluster_id}" if area is not None else None,
        source_raw_file=None,
        reason=status,
    )
