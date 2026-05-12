from pathlib import Path
from types import SimpleNamespace

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
    assert workbook.sheetnames == ["Matrix", "Review", "Metadata"]
    assert workbook["Matrix"]["A1"].value == "feature_family_id"
    assert workbook["Matrix"]["E2"].value == 100.0
    assert workbook["Matrix"]["F2"].value is None
    assert workbook["Review"]["A1"].value == "feature_family_id"
    assert workbook["Review"]["H2"].value == 1
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
    assert workbook["Review"]["G2"].value == 1


def sample_alignment_matrix() -> AlignmentMatrix:
    cluster = SimpleNamespace(
        feature_family_id="FAM000001",
        neutral_loss_tag="DNA_dR",
        family_center_mz=242.114,
        family_center_rt=12.593,
        family_product_mz=126.066,
        family_observed_neutral_loss_da=116.048,
        has_anchor=True,
        event_cluster_ids=("OWN-s1-000001",),
        event_member_count=1,
        evidence="owner_identity",
    )
    return AlignmentMatrix(
        clusters=(cluster,),
        sample_order=("s1", "s2"),
        cells=(
            sample_cell("s1", "FAM000001", "detected", 100.0),
            sample_cell("s2", "FAM000001", "ambiguous_ms1_owner", None),
        ),
    )


def sample_cell(
    sample: str,
    cluster_id: str,
    status: str,
    area: float | None,
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
        reason=status,
    )
