import math
from pathlib import Path
from types import SimpleNamespace

from xic_extractor.alignment.config import AlignmentConfig
from xic_extractor.alignment.matrix import AlignedCell, AlignmentMatrix
from xic_extractor.alignment.production_decisions import build_production_decisions


def test_detected_and_supported_rescue_write_numeric_values():
    matrix = _matrix(
        clusters=(_feature("FAM001", evidence="owner_complete_link;owner_count=2"),),
        cells=(
            _cell("s1", "FAM001", "detected", 100.0),
            _cell("s4", "FAM001", "detected", 95.0),
            _cell("s2", "FAM001", "rescued", 90.0),
            _cell("s3", "FAM001", "rescued", 80.0),
        ),
        sample_order=("s1", "s4", "s2", "s3"),
    )

    decisions = build_production_decisions(matrix, AlignmentConfig())

    assert decisions.cell("FAM001", "s1").write_matrix_value is True
    assert decisions.cell("FAM001", "s1").production_status == "detected"
    assert decisions.cell("FAM001", "s1").matrix_value == 100.0
    assert decisions.cell("FAM001", "s4").write_matrix_value is True
    assert decisions.cell("FAM001", "s4").production_status == "detected"
    assert decisions.cell("FAM001", "s2").write_matrix_value is True
    assert decisions.cell("FAM001", "s2").production_status == "accepted_rescue"
    assert decisions.cell("FAM001", "s2").rescue_tier == "accepted_rescue"
    assert decisions.cell("FAM001", "s3").write_matrix_value is True
    assert decisions.cell("FAM001", "s3").production_status == "accepted_rescue"
    assert decisions.row("FAM001").include_in_primary_matrix is True
    assert decisions.row("FAM001").identity_decision == "production_family"
    assert decisions.row("FAM001").primary_evidence == "owner_complete_link"
    assert decisions.row("FAM001").quantifiable_detected_count == 2
    assert decisions.row("FAM001").row_flags == ()


def test_single_sample_local_owner_does_not_create_primary_identity():
    matrix = _matrix(
        clusters=(_feature("FAM001", evidence="single_sample_local_owner"),),
        cells=(
            _cell("s1", "FAM001", "detected", 100.0),
            _cell("s2", "FAM001", "rescued", 90.0),
        ),
        sample_order=("s1", "s2"),
    )

    decisions = build_production_decisions(matrix, AlignmentConfig())

    assert decisions.cell("FAM001", "s1").write_matrix_value is False
    assert decisions.cell("FAM001", "s1").blank_reason == "missing_row_identity_support"
    assert decisions.cell("FAM001", "s2").write_matrix_value is False
    assert decisions.cell("FAM001", "s2").production_status == "review_rescue"
    assert decisions.row("FAM001").include_in_primary_matrix is False
    assert decisions.row("FAM001").identity_decision == "provisional_discovery"
    assert decisions.row("FAM001").identity_reason == "single_sample_local_owner"
    assert "single_sample_local_owner" in decisions.row("FAM001").row_flags


def test_rescue_heavy_row_needs_multiple_detected_owners_for_primary_promotion():
    matrix = _matrix(
        clusters=(_feature("FAM001", evidence="owner_complete_link;owner_count=2"),),
        cells=(
            _cell("s1", "FAM001", "detected", 100.0),
            _cell("s2", "FAM001", "rescued", 90.0),
            _cell("s3", "FAM001", "rescued", 80.0),
        ),
        sample_order=("s1", "s2", "s3"),
    )

    decisions = build_production_decisions(matrix, AlignmentConfig())

    assert set(decisions.row("FAM001").row_flags) == {
        "rescue_heavy",
        "rescue_only_review",
    }
    assert decisions.row("FAM001").accepted_cell_count == 0
    assert decisions.row("FAM001").quantifiable_detected_count == 1
    assert decisions.row("FAM001").quantifiable_rescue_count == 2
    assert decisions.row("FAM001").include_in_primary_matrix is False


def test_extreme_backfill_dependency_row_is_excluded_from_primary_matrix():
    matrix = _matrix(
        clusters=(_feature("FAM001", evidence="owner_complete_link;owner_count=2"),),
        cells=(
            _cell("seed1", "FAM001", "detected", 100.0),
            _cell("seed2", "FAM001", "detected", 95.0),
            *tuple(
                _cell(f"rescue{i:02d}", "FAM001", "rescued", 80.0 + i)
                for i in range(1, 84)
            ),
        ),
        sample_order=(
            "seed1",
            "seed2",
            *(f"rescue{i:02d}" for i in range(1, 84)),
        ),
    )

    decisions = build_production_decisions(matrix, AlignmentConfig())

    assert decisions.row("FAM001").include_in_primary_matrix is False
    assert decisions.row("FAM001").identity_decision == "provisional_discovery"
    assert decisions.row("FAM001").identity_reason == "extreme_backfill_dependency"
    assert "high_backfill_dependency" in decisions.row("FAM001").row_flags
    assert decisions.cell("FAM001", "seed1").write_matrix_value is False
    assert (
        decisions.cell("FAM001", "seed1").blank_reason
        == "missing_row_identity_support"
    )
    assert decisions.cell("FAM001", "rescue01").production_status == "review_rescue"
    assert decisions.cell("FAM001", "rescue01").write_matrix_value is False


def test_weak_seed_backfill_dependency_row_is_excluded_from_primary_matrix():
    matrix = _matrix(
        clusters=(
            _feature(
                "FAM001",
                evidence="owner_complete_link;owner_count=3",
                members=(
                    _candidate("seed1#candidate", evidence_score=55),
                    _candidate("seed2#candidate", seed_event_count=1),
                    _candidate("seed3#candidate", nl_ppm=12.0),
                ),
            ),
        ),
        cells=(
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
        sample_order=(
            "seed1",
            "seed2",
            "seed3",
            *(f"rescue{i}" for i in range(1, 7)),
            "absent",
        ),
    )

    decisions = build_production_decisions(matrix, AlignmentConfig())

    assert decisions.row("FAM001").include_in_primary_matrix is False
    assert decisions.row("FAM001").identity_decision == "provisional_discovery"
    assert decisions.row("FAM001").identity_reason == "weak_seed_backfill_dependency"
    assert "weak_seed_backfill_dependency" in decisions.row("FAM001").row_flags
    assert decisions.cell("FAM001", "seed1").write_matrix_value is False
    assert (
        decisions.cell("FAM001", "seed1").blank_reason
        == "missing_row_identity_support"
    )
    assert decisions.cell("FAM001", "rescue1").production_status == "review_rescue"
    assert decisions.cell("FAM001", "rescue1").write_matrix_value is False


def test_duplicate_claim_pressure_blocks_unconsolidated_primary_promotion():
    matrix = _matrix(
        clusters=(_feature("FAM001", evidence="owner_complete_link;owner_count=2"),),
        cells=(
            _cell("s1", "FAM001", "detected", 100.0),
            _cell("s2", "FAM001", "duplicate_assigned", 95.0),
            _cell("s3", "FAM001", "duplicate_assigned", 90.0),
        ),
        sample_order=("s1", "s2", "s3"),
    )

    decisions = build_production_decisions(matrix, AlignmentConfig())

    assert decisions.row("FAM001").row_flags == ("duplicate_claim_pressure",)
    assert decisions.row("FAM001").include_in_primary_matrix is False


def test_rescue_without_identity_support_is_review_only_and_row_is_excluded():
    matrix = _matrix(
        clusters=(_feature("FAM001", evidence="", has_anchor=False),),
        cells=(
            _cell("s1", "FAM001", "rescued", 90.0),
            _cell("s2", "FAM001", "absent", None),
        ),
        sample_order=("s1", "s2"),
    )

    decisions = build_production_decisions(matrix, AlignmentConfig())

    assert decisions.cell("FAM001", "s1").write_matrix_value is False
    assert decisions.cell("FAM001", "s1").production_status == "review_rescue"
    assert decisions.cell("FAM001", "s1").blank_reason == "missing_row_identity_support"
    assert decisions.row("FAM001").include_in_primary_matrix is False
    assert set(decisions.row("FAM001").row_flags) == {
        "rescue_only",
        "rescue_only_review",
    }


def test_duplicate_ambiguous_absent_unchecked_and_invalid_areas_are_blank():
    matrix = _matrix(
        clusters=(_feature("FAM001", evidence="single_sample_local_owner"),),
        cells=(
            _cell("duplicate", "FAM001", "duplicate_assigned", 10.0),
            _cell("ambiguous", "FAM001", "ambiguous_ms1_owner", 20.0),
            _cell("absent", "FAM001", "absent", None),
            _cell("unchecked", "FAM001", "unchecked", None),
            _cell("zero", "FAM001", "detected", 0.0),
            _cell("nan", "FAM001", "detected", math.nan),
        ),
        sample_order=("duplicate", "ambiguous", "absent", "unchecked", "zero", "nan"),
    )

    decisions = build_production_decisions(matrix, AlignmentConfig())

    assert decisions.cell("FAM001", "duplicate").blank_reason == "duplicate_loser"
    assert decisions.cell("FAM001", "ambiguous").blank_reason == "ambiguous_ms1_owner"
    assert decisions.cell("FAM001", "absent").blank_reason == "absent"
    assert decisions.cell("FAM001", "unchecked").blank_reason == "unchecked"
    assert decisions.cell("FAM001", "zero").blank_reason == "invalid_area"
    assert decisions.cell("FAM001", "nan").blank_reason == "invalid_area"
    assert decisions.row("FAM001").include_in_primary_matrix is False


def test_identity_anchor_lost_row_is_excluded_until_review_passes():
    matrix = _matrix(
        clusters=(_feature("FAM001", evidence="single_sample_local_owner"),),
        cells=(
            _cell("s1", "FAM001", "duplicate_assigned", 100.0),
            _cell("s2", "FAM001", "rescued", 90.0),
        ),
        sample_order=("s1", "s2"),
    )

    decisions = build_production_decisions(matrix, AlignmentConfig())

    assert decisions.cell("FAM001", "s2").production_status == "review_rescue"
    assert decisions.row("FAM001").include_in_primary_matrix is False
    assert set(decisions.row("FAM001").row_flags) == {
        "single_sample_local_owner",
        "rescue_only",
        "duplicate_claim_pressure",
        "rescue_only_review",
    }


def test_rescued_with_incomplete_peak_fields_is_review_only():
    matrix = _matrix(
        clusters=(_feature("FAM001", evidence="owner_complete_link;owner_count=2"),),
        cells=(
            _cell(
                "s1",
                "FAM001",
                "rescued",
                90.0,
                apex_rt=None,
            ),
        ),
        sample_order=("s1",),
    )

    decision = build_production_decisions(
        matrix,
        AlignmentConfig(),
    ).cell("FAM001", "s1")

    assert decision.write_matrix_value is False
    assert decision.production_status == "review_rescue"
    assert decision.rescue_tier == "review_rescue"
    assert decision.blank_reason == "incomplete_peak"


def test_rescued_outside_max_rt_is_review_only():
    config = AlignmentConfig()
    matrix = _matrix(
        clusters=(_feature("FAM001", evidence="owner_complete_link;owner_count=2"),),
        cells=(
            _cell(
                "s1",
                "FAM001",
                "rescued",
                90.0,
                rt_delta_sec=config.max_rt_sec + 0.1,
            ),
        ),
        sample_order=("s1",),
    )

    decision = build_production_decisions(matrix, config).cell("FAM001", "s1")

    assert decision.write_matrix_value is False
    assert decision.production_status == "review_rescue"
    assert decision.rescue_tier == "review_rescue"
    assert decision.blank_reason == "rt_outside_max"


def test_bool_area_is_not_a_valid_production_matrix_area():
    matrix = _matrix(
        clusters=(_feature("FAM001", evidence="single_sample_local_owner"),),
        cells=(
            _cell("detected_bool", "FAM001", "detected", True),
            _cell("rescued_bool", "FAM001", "rescued", True),
        ),
        sample_order=("detected_bool", "rescued_bool"),
    )

    decisions = build_production_decisions(matrix, AlignmentConfig())

    detected = decisions.cell("FAM001", "detected_bool")
    rescued = decisions.cell("FAM001", "rescued_bool")
    assert detected.write_matrix_value is False
    assert detected.production_status == "blank"
    assert detected.blank_reason == "invalid_area"
    assert rescued.write_matrix_value is False
    assert rescued.production_status == "rejected_rescue"
    assert rescued.rescue_tier == "rejected_rescue"
    assert rescued.blank_reason == "invalid_area"


def _matrix(
    *,
    clusters: tuple[object, ...],
    cells: tuple[AlignedCell, ...],
    sample_order: tuple[str, ...],
) -> AlignmentMatrix:
    return AlignmentMatrix(clusters=clusters, cells=cells, sample_order=sample_order)


def _feature(
    feature_family_id: str,
    *,
    evidence: str,
    has_anchor: bool = True,
    **extra: object,
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
        review_only=False,
        **extra,
    )


def _cell(
    sample_stem: str,
    cluster_id: str,
    status: str,
    area: float | bool | None,
    *,
    apex_rt: float | None = 8.49,
    height: float | None = 100.0,
    peak_start_rt: float | None = 8.4,
    peak_end_rt: float | None = 8.6,
    rt_delta_sec: float | None = 0.0,
    source_candidate_id: str | None = None,
) -> AlignedCell:
    has_area = area is not None
    return AlignedCell(
        sample_stem=sample_stem,
        cluster_id=cluster_id,
        status=status,  # type: ignore[arg-type]
        area=area,  # type: ignore[arg-type]
        apex_rt=apex_rt if has_area else None,
        height=height if has_area else None,
        peak_start_rt=peak_start_rt if has_area else None,
        peak_end_rt=peak_end_rt if has_area else None,
        rt_delta_sec=rt_delta_sec if has_area else None,
        trace_quality="clean" if has_area else status,
        scan_support_score=0.8 if has_area else None,
        source_candidate_id=(
            source_candidate_id
            if source_candidate_id is not None
            else f"{sample_stem}#1" if status == "detected" else None
        ),
        source_raw_file=Path(f"{sample_stem}.raw") if status == "detected" else None,
        reason=(
            "duplicate MS1 peak claim; winner=FAM000000; original_status=detected"
            if status == "duplicate_assigned"
            else status
        ),
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
