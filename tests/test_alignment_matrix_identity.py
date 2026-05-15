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


def test_extreme_dr_backfill_dependency_is_provisional_discovery() -> None:
    matrix = _matrix(
        _feature("FAM001", evidence="owner_complete_link;owner_count=2"),
        (
            _cell("seed1", "FAM001", "detected", 100.0),
            _cell("seed2", "FAM001", "detected", 95.0),
            *tuple(
                _cell(f"rescue{i:02d}", "FAM001", "rescued", 80.0 + i)
                for i in range(1, 84)
            ),
        ),
    )

    decision = build_matrix_identity_decisions(matrix, AlignmentConfig()).row("FAM001")

    assert decision.include_in_primary_matrix is False
    assert decision.identity_decision == "provisional_discovery"
    assert decision.identity_reason == "extreme_backfill_dependency"
    assert decision.quantifiable_detected_count == 2
    assert decision.quantifiable_rescue_count == 83
    assert "high_backfill_dependency" in decision.row_flags


def test_high_detected_dr_family_can_still_use_backfill() -> None:
    matrix = _matrix(
        _feature("FAM001", evidence="owner_complete_link;owner_count=20"),
        (
            *tuple(
                _cell(f"seed{i:02d}", "FAM001", "detected", 100.0 + i)
                for i in range(1, 21)
            ),
            *tuple(
                _cell(f"rescue{i:02d}", "FAM001", "rescued", 80.0 + i)
                for i in range(1, 66)
            ),
        ),
    )

    decision = build_matrix_identity_decisions(matrix, AlignmentConfig()).row("FAM001")

    assert decision.include_in_primary_matrix is True
    assert decision.identity_decision == "production_family"
    assert decision.identity_reason == "owner_complete_link"
    assert "high_backfill_dependency" not in decision.row_flags
    assert "rescue_heavy" in decision.row_flags


def test_weak_seed_dr_backfill_dependency_is_provisional_discovery() -> None:
    matrix = _matrix(
        _feature(
            "FAM001",
            evidence="owner_complete_link;owner_count=3",
            members=(
                _candidate("seed1#candidate", evidence_score=55),
                _candidate("seed2#candidate", seed_event_count=1),
                _candidate("seed3#candidate", nl_ppm=12.0),
            ),
        ),
        (
            _cell(
                "seed1",
                "FAM001",
                "detected",
                100.0,
                source_candidate_id="seed1#candidate",
            ),
            _cell(
                "seed2",
                "FAM001",
                "detected",
                95.0,
                source_candidate_id="seed2#candidate",
            ),
            _cell(
                "seed3",
                "FAM001",
                "detected",
                90.0,
                source_candidate_id="seed3#candidate",
            ),
            *tuple(
                _cell(f"rescue{i}", "FAM001", "rescued", 70.0 + i)
                for i in range(1, 7)
            ),
            _cell("absent", "FAM001", "absent", None),
        ),
    )

    decision = build_matrix_identity_decisions(matrix, AlignmentConfig()).row("FAM001")

    assert decision.include_in_primary_matrix is False
    assert decision.identity_decision == "provisional_discovery"
    assert decision.identity_reason == "weak_seed_backfill_dependency"
    assert decision.quantifiable_detected_count == 3
    assert decision.quantifiable_rescue_count == 6
    assert "weak_seed_backfill_dependency" in decision.row_flags
    assert "rescue_heavy" in decision.row_flags


def test_adequate_seed_dr_backfill_dependency_remains_production() -> None:
    matrix = _matrix(
        _feature(
            "FAM001",
            evidence="owner_complete_link;owner_count=3",
            members=(
                _candidate("seed1#candidate"),
                _candidate("seed2#candidate"),
                _candidate("seed3#candidate"),
            ),
        ),
        (
            _cell(
                "seed1",
                "FAM001",
                "detected",
                100.0,
                source_candidate_id="seed1#candidate",
            ),
            _cell(
                "seed2",
                "FAM001",
                "detected",
                95.0,
                source_candidate_id="seed2#candidate",
            ),
            _cell(
                "seed3",
                "FAM001",
                "detected",
                90.0,
                source_candidate_id="seed3#candidate",
            ),
            *tuple(
                _cell(f"rescue{i}", "FAM001", "rescued", 70.0 + i)
                for i in range(1, 7)
            ),
            _cell("absent", "FAM001", "absent", None),
        ),
    )

    decision = build_matrix_identity_decisions(matrix, AlignmentConfig()).row("FAM001")

    assert decision.include_in_primary_matrix is True
    assert decision.identity_decision == "production_family"
    assert decision.identity_reason == "owner_complete_link"
    assert "weak_seed_backfill_dependency" not in decision.row_flags
    assert "rescue_heavy" in decision.row_flags


def test_weak_seed_gate_reads_owner_member_events() -> None:
    matrix = _matrix(
        _feature(
            "FAM001",
            evidence="owner_complete_link;owner_count=3",
            members=(
                _owner("seed1#candidate", evidence_score=55),
                _owner("seed2#candidate"),
                _owner("seed3#candidate"),
            ),
        ),
        (
            _cell(
                "seed1",
                "FAM001",
                "detected",
                100.0,
                source_candidate_id="seed1#candidate",
            ),
            _cell(
                "seed2",
                "FAM001",
                "detected",
                95.0,
                source_candidate_id="seed2#candidate",
            ),
            _cell(
                "seed3",
                "FAM001",
                "detected",
                90.0,
                source_candidate_id="seed3#candidate",
            ),
            *tuple(
                _cell(f"rescue{i}", "FAM001", "rescued", 70.0 + i)
                for i in range(1, 7)
            ),
            _cell("absent", "FAM001", "absent", None),
        ),
    )

    decision = build_matrix_identity_decisions(matrix, AlignmentConfig()).row("FAM001")

    assert decision.include_in_primary_matrix is False
    assert decision.identity_reason == "weak_seed_backfill_dependency"


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


def test_multi_tag_support_does_not_promote_single_sample_family() -> None:
    matrix = _matrix(
        _feature(
            "FAM001",
            evidence="single_sample_local_owner",
            matched_tag_count=3,
        ),
        (_cell("s1", "FAM001", "detected", 100.0),),
    )

    decision = build_matrix_identity_decisions(matrix, AlignmentConfig()).row("FAM001")

    assert decision.identity_decision == "provisional_discovery"
    assert decision.include_in_primary_matrix is False


def test_artificial_adduct_annotation_does_not_demote_supported_family() -> None:
    matrix = _matrix(
        _feature(
            "FAM001",
            evidence="owner_complete_link;owner_count=5",
            artificial_adduct_role="related_annotation",
        ),
        (
            _cell("s1", "FAM001", "detected", 100.0),
            _cell("s2", "FAM001", "detected", 90.0),
        ),
    )

    decision = build_matrix_identity_decisions(matrix, AlignmentConfig()).row("FAM001")

    assert decision.identity_decision == "production_family"
    assert decision.include_in_primary_matrix is True


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
    neutral_loss_tag: str = "DNA_dR",
    **extra: object,
) -> SimpleNamespace:
    return SimpleNamespace(
        feature_family_id=feature_family_id,
        neutral_loss_tag=neutral_loss_tag,
        family_center_mz=500.123,
        family_center_rt=8.49,
        family_product_mz=384.076,
        family_observed_neutral_loss_da=116.047,
        has_anchor=has_anchor,
        event_cluster_ids=("OWN-s1-000001",),
        event_member_count=1,
        evidence=evidence,
        review_only=review_only,
        **extra,
    )


def _cell(
    sample_stem: str,
    cluster_id: str,
    status: str,
    area: float | None,
    *,
    source_candidate_id: str | None = None,
) -> AlignedCell:
    has_area = area is not None
    return AlignedCell(
        sample_stem=sample_stem,
        cluster_id=cluster_id,
        status=status,  # type: ignore[arg-type]
        area=area,
        apex_rt=8.49 if has_area else None,
        height=100.0 if has_area else None,
        peak_start_rt=8.4 if has_area else None,
        peak_end_rt=8.6 if has_area else None,
        rt_delta_sec=0.0 if has_area else None,
        trace_quality="clean" if has_area else status,
        scan_support_score=0.8 if has_area else None,
        source_candidate_id=(
            source_candidate_id
            if source_candidate_id is not None
            else f"{sample_stem}#{cluster_id}"
        ),
        source_raw_file=Path(f"{sample_stem}.raw") if status == "detected" else None,
        reason=status,
    )


def _candidate(
    candidate_id: str,
    *,
    evidence_score: int = 80,
    seed_event_count: int = 3,
    nl_ppm: float = 3.0,
    scan_support: float = 0.8,
) -> SimpleNamespace:
    return SimpleNamespace(
        candidate_id=candidate_id,
        evidence_score=evidence_score,
        seed_event_count=seed_event_count,
        neutral_loss_mass_error_ppm=nl_ppm,
        ms1_scan_support_score=scan_support,
    )


def _owner(
    candidate_id: str,
    *,
    evidence_score: int = 80,
    seed_event_count: int = 3,
    nl_ppm: float = 3.0,
) -> SimpleNamespace:
    return SimpleNamespace(
        all_events=(
            _candidate(
                candidate_id,
                evidence_score=evidence_score,
                seed_event_count=seed_event_count,
                nl_ppm=nl_ppm,
            ),
        ),
    )
