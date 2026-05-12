from __future__ import annotations

from types import SimpleNamespace

from xic_extractor.alignment.claim_registry import apply_ms1_peak_claim_registry
from xic_extractor.alignment.config import AlignmentConfig
from xic_extractor.alignment.matrix import AlignedCell, AlignmentMatrix


def test_claim_registry_marks_duplicate_same_sample_peak_loser() -> None:
    matrix = _matrix(
        clusters=(
            _feature("FAM000001", detected_count=10),
            _feature("FAM000002", detected_count=2),
        ),
        cells=(
            _cell("sample-a", "FAM000001", "detected"),
            _cell("sample-a", "FAM000002", "rescued"),
        ),
    )

    result = apply_ms1_peak_claim_registry(matrix, AlignmentConfig())
    cells = _cells_by_feature(result)

    assert cells["FAM000001"].status == "detected"
    assert cells["FAM000001"].area == 1000.0
    assert cells["FAM000002"].status == "duplicate_assigned"
    assert cells["FAM000002"].area == 1000.0
    assert cells["FAM000002"].apex_rt == 8.5
    assert cells["FAM000002"].peak_start_rt == 8.4
    assert cells["FAM000002"].peak_end_rt == 8.6
    assert cells["FAM000002"].reason == (
        "duplicate MS1 peak claim; winner=FAM000001; original_status=rescued"
    )


def test_claim_registry_conflicts_across_neutral_loss_tags() -> None:
    matrix = _matrix(
        clusters=(
            _feature("FAM000001", neutral_loss_tag="DNA_dR", detected_count=10),
            _feature("FAM000002", neutral_loss_tag="DNA_base", detected_count=2),
        ),
        cells=(
            _cell("sample-a", "FAM000001", "detected"),
            _cell("sample-a", "FAM000002", "detected"),
        ),
    )

    result = apply_ms1_peak_claim_registry(matrix, AlignmentConfig())

    assert _cells_by_feature(result)["FAM000002"].status == "duplicate_assigned"


def test_claim_registry_most_supported_family_can_win_with_rescued_cell() -> None:
    matrix = _matrix(
        clusters=(
            _feature("FAM000001", detected_count=40),
            _feature("FAM000002", detected_count=1),
        ),
        cells=(
            _cell("sample-a", "FAM000001", "rescued"),
            _cell("sample-a", "FAM000002", "detected"),
            _cell("sample-b", "FAM000001", "detected"),
            _cell("sample-c", "FAM000001", "detected"),
        ),
    )

    result = apply_ms1_peak_claim_registry(matrix, AlignmentConfig())
    cells = _cells_by_feature_sample(result)

    assert cells[("FAM000001", "sample-a")].status == "rescued"
    assert cells[("FAM000002", "sample-a")].status == "duplicate_assigned"
    assert "winner=FAM000001" in cells[("FAM000002", "sample-a")].reason


def test_claim_registry_equal_support_prefers_detected_over_rescued() -> None:
    matrix = _matrix(
        clusters=(
            _feature("FAM000001", detected_count=5),
            _feature("FAM000002", detected_count=5),
        ),
        cells=(
            _cell("sample-a", "FAM000001", "rescued"),
            _cell("sample-a", "FAM000002", "detected"),
        ),
    )

    result = apply_ms1_peak_claim_registry(matrix, AlignmentConfig())
    cells = _cells_by_feature(result)

    assert cells["FAM000001"].status == "duplicate_assigned"
    assert cells["FAM000002"].status == "detected"


def test_claim_registry_review_only_feature_cannot_win_claim() -> None:
    matrix = _matrix(
        clusters=(
            _feature("FAM000001", detected_count=1),
            _feature("FAM000002", detected_count=99, review_only=True),
        ),
        cells=(
            _cell("sample-a", "FAM000001", "rescued"),
            _cell("sample-a", "FAM000002", "detected"),
        ),
    )

    result = apply_ms1_peak_claim_registry(matrix, AlignmentConfig())
    cells = _cells_by_feature(result)

    assert cells["FAM000001"].status == "rescued"
    assert cells["FAM000002"].status == "duplicate_assigned"
    assert "winner=FAM000001" in cells["FAM000002"].reason


def test_claim_registry_claims_exact_same_peak_even_outside_mz_gate() -> None:
    matrix = _matrix(
        clusters=(
            _feature("FAM000001", mz=500.0, detected_count=10),
            _feature("FAM000002", mz=500.01, detected_count=9),
        ),
        cells=(
            _cell("sample-a", "FAM000001", "detected"),
            _cell("sample-a", "FAM000002", "detected"),
        ),
    )

    result = apply_ms1_peak_claim_registry(
        matrix,
        AlignmentConfig(duplicate_fold_ppm=5.0),
    )

    assert _cells_by_feature(result)["FAM000002"].status == "duplicate_assigned"


def test_claim_registry_keeps_distinct_peak_window_claims() -> None:
    matrix = _matrix(
        clusters=(
            _feature("FAM000001", mz=500.0, detected_count=10),
            _feature("FAM000002", mz=500.01, detected_count=9),
            _feature("FAM000003", mz=500.0, detected_count=8),
        ),
        cells=(
            _cell("sample-a", "FAM000001", "detected", start=8.4, end=8.6),
            _cell(
                "sample-a",
                "FAM000002",
                "detected",
                apex=8.7,
                start=8.6,
                end=8.8,
            ),
            _cell("sample-a", "FAM000003", "detected", start=8.58, end=8.78),
        ),
    )

    result = apply_ms1_peak_claim_registry(
        matrix,
        AlignmentConfig(
            duplicate_fold_ppm=5.0,
            owner_window_overlap_fraction=0.5,
        ),
    )

    assert {cell.status for cell in result.cells} == {"detected"}


def test_claim_registry_complete_link_prevents_chain_claiming() -> None:
    matrix = _matrix(
        clusters=(
            _feature("FAM000001", mz=500.000, detected_count=30),
            _feature("FAM000002", mz=500.001, detected_count=20),
            _feature("FAM000003", mz=500.002, detected_count=10),
        ),
        cells=(
            _cell("sample-a", "FAM000001", "detected", apex=8.500),
            _cell("sample-a", "FAM000002", "detected", apex=8.525),
            _cell("sample-a", "FAM000003", "detected", apex=8.550),
        ),
    )

    result = apply_ms1_peak_claim_registry(
        matrix,
        AlignmentConfig(owner_apex_close_sec=2.0),
    )
    cells = _cells_by_feature(result)

    assert cells["FAM000001"].status == "detected"
    assert cells["FAM000002"].status == "duplicate_assigned"
    assert cells["FAM000003"].status == "detected"


def _matrix(*, clusters, cells) -> AlignmentMatrix:
    return AlignmentMatrix(
        clusters=clusters,
        cells=cells,
        sample_order=tuple(dict.fromkeys(cell.sample_stem for cell in cells)),
    )


def _feature(
    feature_id: str,
    *,
    mz: float = 500.0,
    neutral_loss_tag: str = "DNA_dR",
    detected_count: int,
    event_member_count: int | None = None,
    event_cluster_count: int | None = None,
    review_only: bool = False,
):
    event_cluster_count = (
        detected_count if event_cluster_count is None else event_cluster_count
    )
    return SimpleNamespace(
        feature_family_id=feature_id,
        neutral_loss_tag=neutral_loss_tag,
        family_center_mz=mz,
        family_center_rt=8.5,
        family_product_mz=384.0,
        family_observed_neutral_loss_da=116.0,
        has_anchor=not review_only,
        event_cluster_ids=tuple(
            f"OWN-{feature_id}-{index}" for index in range(event_cluster_count)
        ),
        event_member_count=(
            detected_count if event_member_count is None else event_member_count
        ),
        evidence="owner_complete_link",
        review_only=review_only,
    )


def _cell(
    sample: str,
    feature_id: str,
    status: str,
    *,
    apex: float = 8.5,
    start: float = 8.4,
    end: float = 8.6,
) -> AlignedCell:
    return AlignedCell(
        sample_stem=sample,
        cluster_id=feature_id,
        status=status,  # type: ignore[arg-type]
        area=1000.0,
        apex_rt=apex,
        height=100.0,
        peak_start_rt=start,
        peak_end_rt=end,
        rt_delta_sec=0.0,
        trace_quality=status,
        scan_support_score=None,
        source_candidate_id=f"{sample}#{feature_id}",
        source_raw_file=None,
        reason=f"{status} reason",
    )


def _cells_by_feature(matrix: AlignmentMatrix) -> dict[str, AlignedCell]:
    return {cell.cluster_id: cell for cell in matrix.cells}


def _cells_by_feature_sample(
    matrix: AlignmentMatrix,
) -> dict[tuple[str, str], AlignedCell]:
    return {(cell.cluster_id, cell.sample_stem): cell for cell in matrix.cells}
