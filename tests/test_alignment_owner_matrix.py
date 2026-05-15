from dataclasses import replace
from pathlib import Path

from tests.test_alignment_owner_backfill import _feature
from tests.test_alignment_owner_clustering import _owner
from xic_extractor.alignment.matrix import AlignedCell
from xic_extractor.alignment.owner_clustering import OwnerAlignedFeature
from xic_extractor.alignment.owner_matrix import (
    ambiguous_records_by_sample,
    build_owner_alignment_matrix,
)
from xic_extractor.alignment.ownership_models import AmbiguousOwnerRecord


def test_owner_matrix_writes_detected_rescued_ambiguous_and_absent_cells() -> None:
    feature = _feature()
    rescued = AlignedCell(
        sample_stem="sample-b",
        cluster_id=feature.feature_family_id,
        status="rescued",
        area=90.0,
        apex_rt=8.51,
        height=40.0,
        peak_start_rt=8.45,
        peak_end_rt=8.55,
        rt_delta_sec=0.6,
        trace_quality="owner_backfill",
        scan_support_score=None,
        source_candidate_id=None,
        source_raw_file=None,
        reason="owner-centered MS1 backfill",
    )
    ambiguous = AmbiguousOwnerRecord(
        ambiguity_id="AMB-sample-c-000001",
        sample_stem="sample-c",
        candidate_ids=("sample-c#1", "sample-c#2"),
        reason="owner_multiplet_ambiguity",
    )

    matrix = build_owner_alignment_matrix(
        (feature,),
        sample_order=("sample-a", "sample-b", "sample-c", "sample-d"),
        ambiguous_by_sample=ambiguous_records_by_sample((ambiguous,)),
        rescued_cells=(rescued,),
    )

    by_sample = {cell.sample_stem: cell for cell in matrix.cells}
    assert by_sample["sample-a"].status == "detected"
    assert by_sample["sample-a"].area == 1000.0
    assert by_sample["sample-a"].source_candidate_id == "sample-a#a"
    assert by_sample["sample-b"] is rescued
    assert by_sample["sample-c"].status == "ambiguous_ms1_owner"
    assert by_sample["sample-c"].area is None
    assert "sample-c#1;sample-c#2" in by_sample["sample-c"].reason
    assert by_sample["sample-d"].status == "absent"
    assert by_sample["sample-d"].source_raw_file is None
    assert matrix.clusters == (feature,)
    assert matrix.sample_order == ("sample-a", "sample-b", "sample-c", "sample-d")


def test_owner_matrix_detected_cell_does_not_invent_raw_path() -> None:
    matrix = build_owner_alignment_matrix(
        (_feature(),),
        sample_order=("sample-a",),
        ambiguous_by_sample={},
        rescued_cells=(),
    )

    assert matrix.cells[0].source_raw_file is None
    assert isinstance(Path("sample-a.raw"), Path)


def test_owner_matrix_uses_backfill_confirmation_for_severe_low_local_owner() -> None:
    low_owner = replace(_owner("sample-a", "low"), owner_area=10.0)
    feature = OwnerAlignedFeature(
        feature_family_id="FAM000001",
        neutral_loss_tag="NL116",
        family_center_mz=500.0,
        family_center_rt=8.5,
        family_product_mz=383.9526,
        family_observed_neutral_loss_da=116.0474,
        has_anchor=True,
        owners=(
            low_owner,
            _owner("sample-b", "normal"),
            _owner("sample-c", "normal"),
        ),
        evidence="owner_complete_link;owner_count=3",
        confirm_local_owners_with_backfill=True,
    )
    rescued = AlignedCell(
        sample_stem="sample-a",
        cluster_id=feature.feature_family_id,
        status="rescued",
        area=900.0,
        apex_rt=8.55,
        height=90.0,
        peak_start_rt=8.50,
        peak_end_rt=8.60,
        rt_delta_sec=3.0,
        trace_quality="owner_backfill",
        scan_support_score=None,
        source_candidate_id=None,
        source_raw_file=None,
        reason="owner-centered MS1 backfill",
    )

    matrix = build_owner_alignment_matrix(
        (feature,),
        sample_order=("sample-a",),
        ambiguous_by_sample={},
        rescued_cells=(rescued,),
    )

    assert matrix.cells[0].status == "rescued"
    assert matrix.cells[0].area == 900.0
    assert "superseded low local owner" in matrix.cells[0].reason


def test_owner_matrix_keeps_detected_cell_when_local_owner_is_not_low_outlier() -> None:
    feature = replace(_feature(), confirm_local_owners_with_backfill=True)
    rescued = AlignedCell(
        sample_stem="sample-a",
        cluster_id=feature.feature_family_id,
        status="rescued",
        area=4000.0,
        apex_rt=8.55,
        height=400.0,
        peak_start_rt=8.50,
        peak_end_rt=8.60,
        rt_delta_sec=3.0,
        trace_quality="owner_backfill",
        scan_support_score=None,
        source_candidate_id=None,
        source_raw_file=None,
        reason="owner-centered MS1 backfill",
    )

    matrix = build_owner_alignment_matrix(
        (feature,),
        sample_order=("sample-a",),
        ambiguous_by_sample={},
        rescued_cells=(rescued,),
    )

    assert matrix.cells[0].status == "detected"
    assert matrix.cells[0].area == 1000.0


def test_owner_matrix_ambiguous_review_feature_does_not_contaminate_other_features():
    detected_feature = _feature()
    ambiguous_feature = replace(
        _feature(review_only=True),
        feature_family_id="FAM000002",
        owners=(),
        ambiguous_sample_stem="sample-b",
        ambiguous_candidate_ids=("sample-b#1", "sample-b#2"),
    )

    matrix = build_owner_alignment_matrix(
        (detected_feature, ambiguous_feature),
        sample_order=("sample-a", "sample-b"),
        ambiguous_by_sample={},
        rescued_cells=(),
    )

    cells = {
        (cell.cluster_id, cell.sample_stem): cell
        for cell in matrix.cells
    }
    assert cells[("FAM000001", "sample-b")].status == "absent"
    assert cells[("FAM000002", "sample-b")].status == "ambiguous_ms1_owner"
