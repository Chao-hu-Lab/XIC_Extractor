from __future__ import annotations

from pathlib import Path

from xic_extractor.alignment.config import AlignmentConfig
from xic_extractor.alignment.folding import fold_near_duplicate_clusters
from xic_extractor.alignment.matrix import AlignedCell, AlignmentMatrix, CellStatus
from xic_extractor.alignment.models import AlignmentCluster


def test_folds_no_anchor_duplicate_into_anchor_primary():
    matrix = AlignmentMatrix(
        clusters=(
            _cluster("ALN000001", has_anchor=True, mz=242.114, rt=12.5927),
            _cluster("ALN000002", has_anchor=False, mz=242.115, rt=12.5916),
        ),
        cells=(
            _cell("s1", "ALN000001", "detected", area=100.0),
            _cell("s2", "ALN000001", "detected", area=120.0),
            _cell("s3", "ALN000001", "detected", area=130.0),
            _cell("s1", "ALN000002", "detected", area=90.0),
            _cell("s2", "ALN000002", "detected", area=110.0),
            _cell("s3", "ALN000002", "detected", area=115.0),
        ),
        sample_order=("s1", "s2", "s3"),
    )

    folded = fold_near_duplicate_clusters(matrix, config=AlignmentConfig())

    assert [cluster.cluster_id for cluster in folded.clusters] == ["ALN000001"]
    assert folded.clusters[0].folded_cluster_ids == ("ALN000002",)
    assert folded.clusters[0].folded_member_count == 1
    assert folded.clusters[0].folded_sample_fill_count == 0
    assert folded.clusters[0].fold_evidence.startswith("cid_nl_only;")
    observed_cells = {
        (cell.sample_stem, cell.cluster_id, cell.area) for cell in folded.cells
    }
    assert observed_cells == {
        ("s1", "ALN000001", 100.0),
        ("s2", "ALN000001", 120.0),
        ("s3", "ALN000001", 130.0),
    }


def test_secondary_present_sample_can_fill_missing_primary_cell_without_area_sum():
    matrix = AlignmentMatrix(
        clusters=(
            _cluster("ALN000001", has_anchor=True, mz=500.000, rt=8.500),
            _cluster("ALN000002", has_anchor=False, mz=500.001, rt=8.501),
        ),
        cells=(
            _cell("s1", "ALN000001", "detected", area=100.0),
            _cell("s2", "ALN000001", "absent", area=None),
            _cell("s1", "ALN000002", "detected", area=90.0),
            _cell("s2", "ALN000002", "detected", area=80.0),
        ),
        sample_order=("s1", "s2"),
    )

    folded = fold_near_duplicate_clusters(
        matrix,
        config=AlignmentConfig(
            duplicate_fold_min_detected_overlap=0.5,
            duplicate_fold_min_shared_detected_count=1,
            duplicate_fold_min_detected_jaccard=0.5,
            duplicate_fold_min_present_overlap=0.5,
        ),
    )

    assert [cluster.cluster_id for cluster in folded.clusters] == ["ALN000001"]
    assert folded.clusters[0].folded_sample_fill_count == 1
    cells = {
        (cell.sample_stem, cell.status, cell.area, cell.reason)
        for cell in folded.cells
    }
    assert ("s1", "detected", 100.0, "detected") in cells
    assert ("s2", "detected", 80.0, "detected; folded from ALN000002") in cells


def test_backfilled_present_overlap_without_shared_detected_does_not_fold():
    matrix = AlignmentMatrix(
        clusters=(
            _cluster("ALN000001", has_anchor=True),
            _cluster("ALN000002", has_anchor=False, mz=242.115, rt=12.5916),
        ),
        cells=(
            _cell("s1", "ALN000001", "detected", area=100.0),
            _cell("s2", "ALN000001", "rescued", area=120.0),
            _cell("s2", "ALN000002", "detected", area=90.0),
        ),
        sample_order=("s1", "s2"),
    )

    folded = fold_near_duplicate_clusters(
        matrix,
        config=AlignmentConfig(
            duplicate_fold_min_detected_overlap=0.8,
            duplicate_fold_min_shared_detected_count=2,
            duplicate_fold_min_detected_jaccard=0.6,
            duplicate_fold_min_present_overlap=0.8,
        ),
    )

    assert [cluster.cluster_id for cluster in folded.clusters] == [
        "ALN000001",
        "ALN000002",
    ]


def test_one_sample_subset_overlap_does_not_fold_rare_discovery_by_default():
    matrix = AlignmentMatrix(
        clusters=(
            _cluster("ALN000001", has_anchor=True, mz=242.114, rt=12.5927),
            _cluster("ALN000002", has_anchor=False, mz=242.115, rt=12.5916),
        ),
        cells=(
            _cell("s1", "ALN000001", "detected", area=100.0),
            _cell("s2", "ALN000001", "detected", area=120.0),
            _cell("s3", "ALN000001", "detected", area=130.0),
            _cell("s1", "ALN000002", "detected", area=90.0),
        ),
        sample_order=("s1", "s2", "s3"),
    )

    folded = fold_near_duplicate_clusters(matrix, config=AlignmentConfig())

    assert [cluster.cluster_id for cluster in folded.clusters] == [
        "ALN000001",
        "ALN000002",
    ]


def test_no_anchor_primary_prefers_higher_detected_count_over_lower_cluster_id():
    matrix = AlignmentMatrix(
        clusters=(
            _cluster("ALN000001", has_anchor=False, mz=500.000, rt=8.000),
            _cluster("ALN000002", has_anchor=False, mz=500.001, rt=8.001),
        ),
        cells=(
            _cell("s1", "ALN000001", "detected", area=100.0),
            _cell("s1", "ALN000002", "detected", area=90.0),
            _cell("s2", "ALN000002", "detected", area=95.0),
        ),
        sample_order=("s1", "s2"),
    )

    folded = fold_near_duplicate_clusters(
        matrix,
        config=AlignmentConfig(
            duplicate_fold_min_detected_overlap=0.5,
            duplicate_fold_min_shared_detected_count=1,
            duplicate_fold_min_detected_jaccard=0.5,
            duplicate_fold_min_present_overlap=0.5,
        ),
    )

    assert [cluster.cluster_id for cluster in folded.clusters] == ["ALN000002"]
    assert folded.clusters[0].folded_cluster_ids == ("ALN000001",)


def test_secondary_cell_fill_uses_deterministic_evidence_winner():
    matrix = AlignmentMatrix(
        clusters=(
            _cluster("ALN000001", has_anchor=True, mz=500.000, rt=8.000),
            _cluster("ALN000002", has_anchor=False, mz=500.001, rt=8.001),
            _cluster("ALN000003", has_anchor=False, mz=500.002, rt=8.002),
        ),
        cells=(
            _cell("shared", "ALN000001", "detected", area=100.0),
            _cell("fill", "ALN000001", "absent", area=None),
            _cell("shared", "ALN000002", "detected", area=90.0),
            _cell(
                "fill",
                "ALN000002",
                "detected",
                area=70.0,
                scan_support_score=0.5,
            ),
            _cell("shared", "ALN000003", "detected", area=80.0),
            _cell(
                "fill",
                "ALN000003",
                "detected",
                area=60.0,
                scan_support_score=0.9,
            ),
        ),
        sample_order=("shared", "fill"),
    )

    folded = fold_near_duplicate_clusters(
        matrix,
        config=AlignmentConfig(
            duplicate_fold_min_detected_overlap=0.5,
            duplicate_fold_min_shared_detected_count=1,
            duplicate_fold_min_detected_jaccard=0.5,
            duplicate_fold_min_present_overlap=0.5,
        ),
    )

    fill_cell = next(cell for cell in folded.cells if cell.sample_stem == "fill")
    assert fill_cell.area == 60.0
    assert fill_cell.reason == "detected; folded from ALN000003"


def test_folding_preserves_retained_primary_output_order():
    matrix = AlignmentMatrix(
        clusters=(
            _cluster("ALN000001", has_anchor=False, mz=100.000, rt=5.000),
            _cluster("ALN000002", has_anchor=False, mz=200.001, rt=8.001),
            _cluster("ALN000003", has_anchor=True, mz=200.000, rt=8.000),
        ),
        cells=(
            _cell("s1", "ALN000001", "detected", area=10.0),
            _cell("s1", "ALN000002", "detected", area=20.0),
            _cell("s1", "ALN000003", "detected", area=30.0),
        ),
        sample_order=("s1",),
    )

    folded = fold_near_duplicate_clusters(
        matrix,
        config=AlignmentConfig(
            duplicate_fold_min_detected_overlap=1.0,
            duplicate_fold_min_shared_detected_count=1,
            duplicate_fold_min_detected_jaccard=1.0,
            duplicate_fold_min_present_overlap=1.0,
        ),
    )

    assert [cluster.cluster_id for cluster in folded.clusters] == [
        "ALN000001",
        "ALN000003",
    ]


def test_does_not_fold_when_product_or_observed_loss_conflicts():
    matrix = AlignmentMatrix(
        clusters=(
            _cluster("ALN000001", product=126.066, observed_loss=116.048),
            _cluster(
                "ALN000002",
                mz=242.115,
                rt=12.5916,
                product=130.0,
                observed_loss=112.0,
            ),
        ),
        cells=(
            _cell("s1", "ALN000001", "detected", area=100.0),
            _cell("s1", "ALN000002", "detected", area=90.0),
        ),
        sample_order=("s1",),
    )

    folded = fold_near_duplicate_clusters(matrix, config=AlignmentConfig())

    assert [cluster.cluster_id for cluster in folded.clusters] == [
        "ALN000001",
        "ALN000002",
    ]


def test_full_ms2_signature_conflict_blocks_hard_fold_when_available():
    left = _cluster("ALN000001")
    right = _cluster("ALN000002", mz=242.115, rt=12.5916)
    object.__setattr__(left, "cluster_ms2_signature", ("126.066", "98.060"))
    object.__setattr__(right, "cluster_ms2_signature", ("126.066", "97.010"))
    matrix = AlignmentMatrix(
        clusters=(left, right),
        cells=(
            _cell("s1", "ALN000001", "detected", area=100.0),
            _cell("s1", "ALN000002", "detected", area=90.0),
        ),
        sample_order=("s1",),
    )

    folded = fold_near_duplicate_clusters(
        matrix,
        config=AlignmentConfig(
            duplicate_fold_min_shared_detected_count=1,
            duplicate_fold_min_detected_jaccard=1.0,
        ),
    )

    assert [cluster.cluster_id for cluster in folded.clusters] == [
        "ALN000001",
        "ALN000002",
    ]


def test_no_chain_folding_requires_secondary_to_match_existing_folded_members():
    primary = _cluster("ALN000001", mz=500.000, rt=8.000)
    bridge = _cluster("ALN000002", mz=500.002, rt=8.010)
    endpoint = _cluster("ALN000003", mz=500.004, rt=8.020)
    matrix = AlignmentMatrix(
        clusters=(primary, bridge, endpoint),
        cells=(
            _cell("s1", "ALN000001", "detected", area=100.0),
            _cell("s1", "ALN000002", "detected", area=90.0),
            _cell("s1", "ALN000003", "detected", area=80.0),
        ),
        sample_order=("s1",),
    )

    folded = fold_near_duplicate_clusters(
        matrix,
        config=AlignmentConfig(
            duplicate_fold_ppm=5.0,
            duplicate_fold_rt_sec=0.75,
            duplicate_fold_min_detected_overlap=1.0,
            duplicate_fold_min_shared_detected_count=1,
            duplicate_fold_min_detected_jaccard=1.0,
            duplicate_fold_min_present_overlap=1.0,
        ),
    )

    assert [cluster.cluster_id for cluster in folded.clusters] == [
        "ALN000001",
        "ALN000003",
    ]
    assert folded.clusters[0].folded_cluster_ids == ("ALN000002",)


def _cluster(
    cluster_id: str,
    *,
    has_anchor: bool = True,
    mz: float = 242.114,
    rt: float = 12.5927,
    product: float = 126.066,
    observed_loss: float = 116.048,
) -> AlignmentCluster:
    members = (object(),)
    return AlignmentCluster(
        cluster_id=cluster_id,
        neutral_loss_tag="DNA_dR",
        cluster_center_mz=mz,
        cluster_center_rt=rt,
        cluster_product_mz=product,
        cluster_observed_neutral_loss_da=observed_loss,
        has_anchor=has_anchor,
        members=members,
        anchor_members=members if has_anchor else (),
    )


def _cell(
    sample_stem: str,
    cluster_id: str,
    status: CellStatus,
    *,
    area: float | None,
    scan_support_score: float | None = None,
    trace_quality: str | None = None,
    rt_delta_sec: float | None = None,
) -> AlignedCell:
    resolved_scan_support = (
        scan_support_score
        if scan_support_score is not None
        else (0.9 if area else None)
    )
    return AlignedCell(
        sample_stem=sample_stem,
        cluster_id=cluster_id,
        status=status,
        area=area,
        apex_rt=12.5927,
        height=100.0 if area else None,
        peak_start_rt=12.55 if area else None,
        peak_end_rt=12.65 if area else None,
        rt_delta_sec=(
            rt_delta_sec if rt_delta_sec is not None else (0.0 if area else None)
        ),
        trace_quality=trace_quality or ("clean" if area else "absent"),
        scan_support_score=resolved_scan_support,
        source_candidate_id=f"{sample_stem}#{cluster_id}",
        source_raw_file=Path(f"{sample_stem}.raw"),
        reason=status,
    )
