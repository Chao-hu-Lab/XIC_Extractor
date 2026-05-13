from pathlib import Path
from types import SimpleNamespace

import pytest
from openpyxl import load_workbook

from xic_extractor.alignment.matrix import AlignedCell, AlignmentMatrix
from xic_extractor.alignment.xlsx_writer import write_alignment_results_xlsx


def test_alignment_results_xlsx_has_matrix_review_metadata_sheets(tmp_path: Path):
    matrix = sample_alignment_matrix()

    path = write_alignment_results_xlsx(
        tmp_path / "alignment_results.xlsx",
        matrix,
        metadata={
            "schema_version": "alignment-results-v1",
            "resolver_mode": "local_minimum",
        },
    )

    workbook = load_workbook(path, data_only=True)
    assert workbook.sheetnames == ["Matrix", "Review", "Audit", "Metadata"]
    assert workbook["Matrix"]["A1"].value == "feature_family_id"
    assert workbook["Matrix"]["E2"].value == 100.0
    assert workbook["Matrix"]["F2"].value is None
    assert [cell.value for cell in workbook["Review"][1]] == [
        "feature_family_id",
        "neutral_loss_tag",
        "detected_count",
        "rescued_count",
        "accepted_cell_count",
        "accepted_rescue_count",
        "review_rescue_count",
        "absent_count",
        "unchecked_count",
        "duplicate_assigned_count",
        "ambiguous_ms1_owner_count",
        "include_in_primary_matrix",
        "row_flags",
    ]
    assert workbook["Review"]["C2"].value == 1
    assert workbook["Review"]["K2"].value == 1
    assert [cell.value for cell in workbook["Audit"][1]] == [
        "feature_family_id",
        "sample_stem",
        "neutral_loss_tag",
        "family_center_mz",
        "family_center_rt",
        "raw_status",
        "production_status",
        "rescue_tier",
        "write_matrix_value",
        "blank_reason",
        "area",
        "apex_rt",
        "rt_delta_sec",
        "claim_state",
        "row_flags",
        "reason",
    ]
    assert workbook["Metadata"]["A1"].value == "key"


def test_alignment_results_xlsx_blanks_duplicate_assigned_matrix_area(
    tmp_path: Path,
):
    base = sample_alignment_matrix()
    matrix = AlignmentMatrix(
        clusters=base.clusters,
        sample_order=("s1", "s2"),
        cells=(
            sample_cell("s1", "FAM000001", "detected", 100.0),
            sample_cell("s2", "FAM000001", "duplicate_assigned", 200.0),
        ),
    )

    path = write_alignment_results_xlsx(
        tmp_path / "alignment_results.xlsx",
        matrix,
        metadata={"schema_version": "alignment-results-v1"},
    )

    workbook = load_workbook(path, data_only=True)
    assert workbook["Matrix"]["E2"].value == 100.0
    assert workbook["Matrix"]["F2"].value is None
    assert workbook["Review"]["J2"].value == 1


def test_alignment_results_xlsx_excludes_review_only_rows_from_matrix(
    tmp_path: Path,
):
    matrix = AlignmentMatrix(
        clusters=(
            sample_feature("FAM000001", evidence="owner_complete_link;owner_count=2"),
            sample_feature("FAM000002", evidence="", has_anchor=False),
        ),
        sample_order=("s1",),
        cells=(
            sample_cell("s1", "FAM000001", "detected", 100.0),
            sample_cell("s1", "FAM000002", "rescued", 200.0),
        ),
    )

    path = write_alignment_results_xlsx(
        tmp_path / "alignment_results.xlsx",
        matrix,
        metadata={"schema_version": "alignment-results-v1"},
    )

    workbook = load_workbook(path, data_only=True)
    assert workbook["Matrix"]["A2"].value == "FAM000001"
    assert workbook["Matrix"]["A3"].value is None
    assert workbook["Audit"]["A2"].value == "FAM000001"
    assert workbook["Audit"]["A3"].value == "FAM000002"
    assert workbook["Audit"]["H3"].value == "review_rescue"
    assert workbook["Audit"]["J3"].value == "missing_row_identity_support"


def test_alignment_results_xlsx_audit_explains_duplicate_blank(
    tmp_path: Path,
):
    matrix = AlignmentMatrix(
        clusters=(
            sample_feature(
                "FAM000001",
                evidence="owner_complete_link;owner_count=2",
            ),
        ),
        sample_order=("s1",),
        cells=(sample_cell("s1", "FAM000001", "duplicate_assigned", 200.0),),
    )

    path = write_alignment_results_xlsx(
        tmp_path / "alignment_results.xlsx",
        matrix,
        metadata={"schema_version": "alignment-results-v1"},
    )

    workbook = load_workbook(path, data_only=True)
    assert workbook["Matrix"]["A2"].value is None
    assert workbook["Audit"]["A2"].value == "FAM000001"
    assert workbook["Audit"]["F2"].value == "duplicate_assigned"
    assert workbook["Audit"]["I2"].value is False
    assert workbook["Audit"]["J2"].value == "duplicate_loser"


def test_alignment_results_xlsx_escapes_formula_like_external_strings(
    tmp_path: Path,
):
    matrix = AlignmentMatrix(
        clusters=(
            sample_feature(
                "=FAM000001",
                evidence="owner_identity",
                neutral_loss_tag="-DNA_dR",
            ),
        ),
        sample_order=("+Sample_A",),
        cells=(
            sample_cell(
                "+Sample_A",
                "=FAM000001",
                "detected",
                100.0,
                reason="@audit reason",
            ),
        ),
    )

    path = write_alignment_results_xlsx(
        tmp_path / "alignment_results.xlsx",
        matrix,
        metadata={"schema_version": "@metadata value"},
    )

    workbook = load_workbook(path, data_only=False)
    assert workbook["Matrix"]["A2"].value == "'=FAM000001"
    assert workbook["Matrix"]["A2"].data_type != "f"
    assert workbook["Matrix"]["E1"].value == "'+Sample_A"
    assert workbook["Matrix"]["E1"].data_type != "f"
    assert workbook["Review"]["B2"].value == "'-DNA_dR"
    assert workbook["Review"]["B2"].data_type != "f"
    assert workbook["Audit"]["B2"].value == "'+Sample_A"
    assert workbook["Audit"]["P2"].value == "'@audit reason"
    assert workbook["Audit"]["I2"].value is True
    assert workbook["Metadata"]["B2"].value == "'@metadata value"
    assert workbook["Metadata"]["B2"].data_type != "f"


def test_alignment_results_xlsx_rejects_orphan_audit_cell(tmp_path: Path):
    matrix = AlignmentMatrix(
        clusters=(sample_feature("FAM000001", evidence="owner_identity"),),
        sample_order=("s1",),
        cells=(sample_cell("s1", "FAM999999", "detected", 100.0),),
    )

    with pytest.raises(ValueError, match="unknown cluster: FAM999999"):
        write_alignment_results_xlsx(
            tmp_path / "alignment_results.xlsx",
            matrix,
            metadata={"schema_version": "alignment-results-v1"},
        )


def sample_alignment_matrix() -> AlignmentMatrix:
    cluster = sample_feature("FAM000001", evidence="owner_identity")
    return AlignmentMatrix(
        clusters=(cluster,),
        sample_order=("s1", "s2"),
        cells=(
            sample_cell("s1", "FAM000001", "detected", 100.0),
            sample_cell("s2", "FAM000001", "ambiguous_ms1_owner", None),
        ),
    )


def sample_feature(
    feature_family_id: str,
    *,
    evidence: str,
    has_anchor: bool = True,
    neutral_loss_tag: str = "DNA_dR",
):
    return SimpleNamespace(
        feature_family_id=feature_family_id,
        neutral_loss_tag=neutral_loss_tag,
        family_center_mz=242.114,
        family_center_rt=12.593,
        family_product_mz=126.066,
        family_observed_neutral_loss_da=116.048,
        has_anchor=has_anchor,
        event_cluster_ids=("OWN-s1-000001",),
        event_member_count=1,
        evidence=evidence,
        review_only=False,
    )


def sample_cell(
    sample: str,
    cluster_id: str,
    status: str,
    area: float | None,
    *,
    reason: str | None = None,
) -> AlignedCell:
    return AlignedCell(
        sample_stem=sample,
        cluster_id=cluster_id,
        status=status,  # type: ignore[arg-type]
        area=area,
        apex_rt=12.593 if area else None,
        height=1000.0 if area else None,
        peak_start_rt=12.55 if area else None,
        peak_end_rt=12.64 if area else None,
        rt_delta_sec=0.0 if area else None,
        trace_quality=status,
        scan_support_score=None,
        source_candidate_id="s1#6095" if area else None,
        source_raw_file=None,
        reason=reason or status,
    )
