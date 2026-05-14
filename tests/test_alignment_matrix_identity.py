from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from xic_extractor.alignment.config import AlignmentConfig
from xic_extractor.alignment.matrix import AlignedCell, AlignmentMatrix
from xic_extractor.alignment.matrix_identity import build_matrix_identity_decisions


def test_owner_complete_link_requires_two_detected_identity_cells() -> None:
    matrix = _matrix(
        _feature("FAM001", evidence="owner_complete_link;owner_count=2"),
        (
            _cell("s1", "FAM001", "detected", 100.0),
            _cell("s2", "FAM001", "rescued", 90.0),
            _cell("s3", "FAM001", "rescued", 80.0),
        ),
    )

    decision = build_matrix_identity_decisions(matrix, AlignmentConfig()).row("FAM001")

    assert decision.include_in_primary_matrix is False
    assert decision.identity_decision == "provisional_discovery"
    assert decision.identity_reason == "insufficient_detected_identity_support"
    assert decision.quantifiable_detected_count == 1
    assert decision.quantifiable_rescue_count == 2
    assert "rescue_heavy" in decision.row_flags


def test_owner_complete_link_with_two_detected_cells_is_production_family() -> None:
    matrix = _matrix(
        _feature("FAM001", evidence="owner_complete_link;owner_count=2"),
        (
            _cell("s1", "FAM001", "detected", 100.0),
            _cell("s2", "FAM001", "detected", 90.0),
            _cell("s3", "FAM001", "rescued", 80.0),
        ),
    )

    decision = build_matrix_identity_decisions(matrix, AlignmentConfig()).row("FAM001")

    assert decision.include_in_primary_matrix is True
    assert decision.identity_decision == "production_family"
    assert decision.identity_confidence == "high"
    assert decision.primary_evidence == "owner_complete_link"
    assert decision.quantifiable_detected_count == 2


def test_single_sample_local_owner_is_audit_even_with_rescue() -> None:
    matrix = _matrix(
        _feature("FAM001", evidence="single_sample_local_owner"),
        (
            _cell("s1", "FAM001", "detected", 100.0),
            _cell("s2", "FAM001", "rescued", 90.0),
        ),
    )

    decision = build_matrix_identity_decisions(matrix, AlignmentConfig()).row("FAM001")

    assert decision.include_in_primary_matrix is False
    assert decision.identity_decision == "provisional_discovery"
    assert decision.identity_reason == "single_sample_local_owner"
    assert "single_sample_local_owner" in decision.row_flags


def test_anchored_single_detected_family_is_provisional_discovery() -> None:
    matrix = _matrix(
        _feature("FAM001", evidence="", has_anchor=True),
        (_cell("s1", "FAM001", "detected", 100.0),),
    )

    decision = build_matrix_identity_decisions(matrix, AlignmentConfig()).row("FAM001")

    assert decision.include_in_primary_matrix is False
    assert decision.identity_decision == "provisional_discovery"
    assert decision.identity_reason == "anchored_single_detected_phase_a"
    assert "anchored_single_detected" in decision.row_flags


def test_weak_nonzero_detected_support_is_provisional_discovery() -> None:
    matrix = _matrix(
        _feature("FAM001", evidence="", has_anchor=False),
        (_cell("s1", "FAM001", "detected", 100.0),),
    )

    decision = build_matrix_identity_decisions(matrix, AlignmentConfig()).row("FAM001")

    assert decision.include_in_primary_matrix is False
    assert decision.identity_decision == "provisional_discovery"
    assert decision.identity_reason == "insufficient_detected_identity_support"


def test_rescue_only_backfill_only_family_is_audit() -> None:
    matrix = _matrix(
        _feature("FAM001", evidence="owner_complete_link;owner_count=2"),
        (
            _cell("s1", "FAM001", "rescued", 100.0),
            _cell("s2", "FAM001", "rescued", 90.0),
        ),
    )

    decision = build_matrix_identity_decisions(matrix, AlignmentConfig()).row("FAM001")

    assert decision.include_in_primary_matrix is False
    assert decision.identity_decision == "audit_family"
    assert decision.identity_reason == "rescue_only"
    assert "rescue_only" in decision.row_flags


def test_duplicate_pressure_above_detected_support_is_audit() -> None:
    matrix = _matrix(
        _feature("FAM001", evidence="owner_complete_link;owner_count=2"),
        (
            _cell("s1", "FAM001", "detected", 100.0),
            _cell("s2", "FAM001", "duplicate_assigned", 90.0),
            _cell("s3", "FAM001", "duplicate_assigned", 80.0),
        ),
    )

    decision = build_matrix_identity_decisions(matrix, AlignmentConfig()).row("FAM001")

    assert decision.include_in_primary_matrix is False
    assert decision.identity_decision == "audit_family"
    assert decision.identity_reason == "duplicate_claim_pressure"
    assert "duplicate_claim_pressure" in decision.row_flags


def test_family_consolidation_loser_is_audit_only() -> None:
    matrix = _matrix(
        _feature(
            "FAM001",
            evidence=(
                "owner_complete_link;owner_count=2;"
                "primary_family_consolidation_loser;winner=FAM999"
            ),
            review_only=True,
        ),
        (
            _cell("s1", "FAM001", "detected", 100.0),
            _cell("s2", "FAM001", "detected", 90.0),
        ),
    )

    decision = build_matrix_identity_decisions(matrix, AlignmentConfig()).row("FAM001")

    assert decision.include_in_primary_matrix is False
    assert decision.identity_reason == "review_only"
    assert "family_consolidation_loser" in decision.row_flags


def _matrix(feature: object, cells: tuple[AlignedCell, ...]) -> AlignmentMatrix:
    return AlignmentMatrix(
        clusters=(feature,),
        cells=cells,
        sample_order=tuple(cell.sample_stem for cell in cells),
    )


def _feature(
    feature_family_id: str,
    *,
    evidence: str,
    review_only: bool = False,
    has_anchor: bool = True,
) -> SimpleNamespace:
    return SimpleNamespace(
        feature_family_id=feature_family_id,
        neutral_loss_tag="DNA_dR",
        family_center_mz=500.123,
        family_center_rt=8.49,
        family_product_mz=384.076,
        family_observed_neutral_loss_da=116.047,
        has_anchor=has_anchor,
        event_cluster_ids=("OWN-s1-000001",),
        event_member_count=1,
        evidence=evidence,
        review_only=review_only,
    )


def _cell(
    sample_stem: str,
    cluster_id: str,
    status: str,
    area: float,
) -> AlignedCell:
    return AlignedCell(
        sample_stem=sample_stem,
        cluster_id=cluster_id,
        status=status,  # type: ignore[arg-type]
        area=area,
        apex_rt=8.49,
        height=100.0,
        peak_start_rt=8.4,
        peak_end_rt=8.6,
        rt_delta_sec=0.0,
        trace_quality="clean",
        scan_support_score=0.8,
        source_candidate_id=f"{sample_stem}#{cluster_id}",
        source_raw_file=Path(f"{sample_stem}.raw"),
        reason=status,
    )
