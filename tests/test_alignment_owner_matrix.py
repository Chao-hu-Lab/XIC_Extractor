from dataclasses import replace
from pathlib import Path

from tests.test_alignment_owner_backfill import _feature
from xic_extractor.alignment.matrix import AlignedCell
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
