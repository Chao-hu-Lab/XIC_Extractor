from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from xic_extractor.alignment.config import AlignmentConfig
from xic_extractor.alignment.matrix import AlignedCell, AlignmentMatrix
from xic_extractor.alignment.primary_consolidation import (
    consolidate_primary_family_rows,
)
from xic_extractor.alignment.production_decisions import build_production_decisions


def test_consolidation_promotes_one_primary_row_from_duplicate_claim_family():
    matrix = AlignmentMatrix(
        clusters=(
            _feature("FAM001", rt=8.40),
            _feature("FAM002", rt=8.55),
            _feature("FAM003", rt=8.70),
        ),
        sample_order=("s1", "s2", "s3"),
        cells=(
            _cell("s1", "FAM001", "detected", 100.0, apex=8.40),
            _duplicate_cell(
                "s2", "FAM001", winner="FAM002", original="rescued", apex=8.55
            ),
            _duplicate_cell(
                "s3", "FAM001", winner="FAM003", original="rescued", apex=8.70
            ),
            _duplicate_cell(
                "s1", "FAM002", winner="FAM001", original="rescued", apex=8.40
            ),
            _cell("s2", "FAM002", "detected", 200.0, apex=8.55),
            _duplicate_cell(
                "s3", "FAM002", winner="FAM003", original="rescued", apex=8.70
            ),
            _duplicate_cell(
                "s1", "FAM003", winner="FAM001", original="rescued", apex=8.40
            ),
            _duplicate_cell(
                "s2", "FAM003", winner="FAM002", original="rescued", apex=8.55
            ),
            _cell("s3", "FAM003", "detected", 300.0, apex=8.70),
        ),
    )

    consolidated = consolidate_primary_family_rows(matrix, AlignmentConfig())
    decisions = build_production_decisions(consolidated, AlignmentConfig())
    primary_rows = [
        row.feature_family_id
        for row in decisions.rows.values()
        if row.include_in_primary_matrix
    ]

    assert primary_rows == ["FAM002"]
    assert decisions.row("FAM002").accepted_cell_count == 3
    assert decisions.row("FAM001").include_in_primary_matrix is False
    assert decisions.row("FAM003").include_in_primary_matrix is False
    winner_cells = {
        cell.sample_stem: cell
        for cell in consolidated.cells
        if cell.cluster_id == "FAM002"
    }
    assert [
        (sample, cell.status, cell.area) for sample, cell in winner_cells.items()
    ] == [
        ("s1", "detected", 100.0),
        ("s2", "detected", 200.0),
        ("s3", "detected", 300.0),
    ]
    assert _feature_by_id(consolidated, "FAM002").family_center_rt == 8.55


def test_consolidation_keeps_different_product_identity_separate():
    matrix = AlignmentMatrix(
        clusters=(
            _feature("FAM001", product_mz=384.0),
            _feature("FAM002", product_mz=390.0),
        ),
        sample_order=("s1", "s2"),
        cells=(
            _cell("s1", "FAM001", "detected", 100.0, apex=8.50),
            _duplicate_cell(
                "s2", "FAM001", winner="FAM002", original="rescued", apex=8.50
            ),
            _duplicate_cell(
                "s1", "FAM002", winner="FAM001", original="rescued", apex=8.50
            ),
            _cell("s2", "FAM002", "detected", 200.0, apex=8.50),
        ),
    )

    consolidated = consolidate_primary_family_rows(matrix, AlignmentConfig())

    assert [cluster.feature_family_id for cluster in consolidated.clusters] == [
        "FAM001",
        "FAM002",
    ]
    assert all(
        not getattr(cluster, "review_only", False)
        for cluster in consolidated.clusters
    )


def test_consolidation_prefers_stronger_sample_peak_over_weak_detected_peak():
    matrix = AlignmentMatrix(
        clusters=(
            _feature("FAM001", rt=8.50),
            _feature("FAM002", rt=8.90),
        ),
        sample_order=("s1", "s2"),
        cells=(
            _cell("s1", "FAM001", "detected", 100.0, apex=8.50),
            _duplicate_cell(
                "s1", "FAM002", winner="FAM001", original="rescued", apex=8.90
            ),
            _cell("s2", "FAM002", "detected", 500.0, apex=8.90),
            _duplicate_cell(
                "s2", "FAM001", winner="FAM002", original="rescued", apex=8.90
            ),
        ),
    )
    strong = next(
        cell
        for cell in matrix.cells
        if cell.sample_stem == "s1" and cell.cluster_id == "FAM002"
    )
    strong = AlignedCell(
        sample_stem=strong.sample_stem,
        cluster_id=strong.cluster_id,
        status=strong.status,
        area=1000.0,
        apex_rt=strong.apex_rt,
        height=strong.height,
        peak_start_rt=strong.peak_start_rt,
        peak_end_rt=strong.peak_end_rt,
        rt_delta_sec=strong.rt_delta_sec,
        trace_quality=strong.trace_quality,
        scan_support_score=strong.scan_support_score,
        source_candidate_id=strong.source_candidate_id,
        source_raw_file=strong.source_raw_file,
        reason=strong.reason,
    )
    matrix = AlignmentMatrix(
        clusters=matrix.clusters,
        sample_order=matrix.sample_order,
        cells=(
            matrix.cells[0],
            strong,
            matrix.cells[2],
            matrix.cells[3],
        ),
    )

    consolidated = consolidate_primary_family_rows(matrix, AlignmentConfig())
    winner_id = next(
        row.feature_family_id
        for row in build_production_decisions(
            consolidated,
            AlignmentConfig(),
        ).rows.values()
        if row.include_in_primary_matrix
    )
    winner_cells = {
        cell.sample_stem: cell
        for cell in consolidated.cells
        if cell.cluster_id == winner_id
    }

    assert winner_cells["s1"].area == 1000.0
    assert winner_cells["s1"].status == "rescued"


def _feature(
    feature_family_id: str,
    *,
    mz: float = 500.0,
    rt: float = 8.5,
    product_mz: float = 384.0,
    observed_loss: float = 116.0,
) -> SimpleNamespace:
    return SimpleNamespace(
        feature_family_id=feature_family_id,
        neutral_loss_tag="DNA_dR",
        family_center_mz=mz,
        family_center_rt=rt,
        family_product_mz=product_mz,
        family_observed_neutral_loss_da=observed_loss,
        has_anchor=True,
        event_cluster_ids=(f"OWN-{feature_family_id}",),
        event_member_count=1,
        evidence="single_sample_local_owner",
        review_only=False,
    )


def _cell(
    sample_stem: str,
    cluster_id: str,
    status: str,
    area: float,
    *,
    apex: float,
) -> AlignedCell:
    return AlignedCell(
        sample_stem=sample_stem,
        cluster_id=cluster_id,
        status=status,  # type: ignore[arg-type]
        area=area,
        apex_rt=apex,
        height=100.0,
        peak_start_rt=apex - 0.05,
        peak_end_rt=apex + 0.05,
        rt_delta_sec=0.0,
        trace_quality="clean",
        scan_support_score=0.9,
        source_candidate_id=f"{sample_stem}#{cluster_id}",
        source_raw_file=Path(f"{sample_stem}.raw"),
        reason=status,
    )


def _duplicate_cell(
    sample_stem: str,
    cluster_id: str,
    *,
    winner: str,
    original: str,
    apex: float,
) -> AlignedCell:
    source = _cell(sample_stem, cluster_id, original, 100.0, apex=apex)
    return AlignedCell(
        sample_stem=source.sample_stem,
        cluster_id=source.cluster_id,
        status="duplicate_assigned",
        area=source.area,
        apex_rt=source.apex_rt,
        height=source.height,
        peak_start_rt=source.peak_start_rt,
        peak_end_rt=source.peak_end_rt,
        rt_delta_sec=source.rt_delta_sec,
        trace_quality=source.trace_quality,
        scan_support_score=source.scan_support_score,
        source_candidate_id=source.source_candidate_id,
        source_raw_file=source.source_raw_file,
        reason=(
            "duplicate MS1 peak claim; "
            f"winner={winner}; original_status={original}"
        ),
    )


def _feature_by_id(matrix: AlignmentMatrix, feature_id: str):
    return next(
        cluster
        for cluster in matrix.clusters
        if cluster.feature_family_id == feature_id
    )
