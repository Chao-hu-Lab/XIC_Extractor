import csv
import math
from pathlib import Path
from types import SimpleNamespace

from xic_extractor.alignment.matrix import AlignedCell, AlignmentMatrix
from xic_extractor.alignment.models import AlignmentCluster

REVIEW_COLUMNS = [
    "feature_family_id",
    "neutral_loss_tag",
    "family_center_mz",
    "family_center_rt",
    "family_product_mz",
    "family_observed_neutral_loss_da",
    "has_anchor",
    "event_cluster_count",
    "event_cluster_ids",
    "event_member_count",
    "detected_count",
    "absent_count",
    "unchecked_count",
    "present_rate",
    "representative_samples",
    "family_evidence",
    "warning",
    "reason",
]


def test_write_alignment_review_tsv_columns_counts_rates_and_reason(tmp_path: Path):
    from xic_extractor.alignment.tsv_writer import write_alignment_review_tsv

    matrix = AlignmentMatrix(
        clusters=(_cluster(has_anchor=True, member_count=1),),
        cells=(
            _cell("sample-a", "detected", area=10.0, candidate_id="sample-a#1"),
            _cell("sample-b", "rescued", area=20.0),
            _cell("sample-c", "absent"),
            _cell("sample-d", "unchecked"),
        ),
        sample_order=("sample-a", "sample-b", "sample-c", "sample-d"),
    )

    path = write_alignment_review_tsv(tmp_path / "alignment_review.tsv", matrix)
    rows = _read_tsv(path)

    assert list(rows[0]) == REVIEW_COLUMNS
    assert rows[0] == {
        "feature_family_id": "ALN000001",
        "neutral_loss_tag": "DNA_dR",
        "family_center_mz": "500.123",
        "family_center_rt": "8.49",
        "family_product_mz": "384.076",
        "family_observed_neutral_loss_da": "116.047",
        "has_anchor": "TRUE",
        "event_cluster_count": "1",
        "event_cluster_ids": "ALN000001",
        "event_member_count": "1",
        "detected_count": "1",
        "absent_count": "1",
        "unchecked_count": "1",
        "present_rate": "0.5",
        "representative_samples": "sample-a;sample-b",
        "family_evidence": "",
        "warning": "",
        "reason": "anchor family; 2/4 present; 1 MS1 backfilled",
    }


def test_write_alignment_review_tsv_warning_precedence(tmp_path: Path):
    from xic_extractor.alignment.tsv_writer import write_alignment_review_tsv

    matrix = AlignmentMatrix(
        clusters=(
            _cluster(cluster_id="ALN000001", has_anchor=False),
            _cluster(cluster_id="ALN000002", has_anchor=True),
            _cluster(cluster_id="ALN000003", has_anchor=True),
            _cluster(cluster_id="ALN000004", has_anchor=True),
        ),
        cells=(
            _cell("sample-a", "detected", cluster_id="ALN000001", area=1.0),
            _cell("sample-b", "unchecked", cluster_id="ALN000001"),
            _cell("sample-a", "unchecked", cluster_id="ALN000002"),
            _cell("sample-b", "unchecked", cluster_id="ALN000002"),
            _cell("sample-a", "rescued", cluster_id="ALN000003", area=1.0),
            _cell("sample-b", "absent", cluster_id="ALN000003"),
            _cell("sample-a", "detected", cluster_id="ALN000004", area=1.0),
            _cell("sample-b", "absent", cluster_id="ALN000004"),
        ),
        sample_order=("sample-a", "sample-b"),
    )

    rows = _read_tsv(write_alignment_review_tsv(tmp_path / "review.tsv", matrix))

    assert [row["warning"] for row in rows] == [
        "no_anchor",
        "high_unchecked",
        "high_backfill_dependency",
        "",
    ]


def test_write_alignment_review_tsv_reports_duplicate_assigned_cells(tmp_path: Path):
    from xic_extractor.alignment.tsv_writer import write_alignment_review_tsv

    matrix = AlignmentMatrix(
        clusters=(_cluster(has_anchor=False),),
        cells=(
            _cell("sample-a", "duplicate_assigned"),
            _cell("sample-b", "duplicate_assigned"),
            _cell("sample-c", "unchecked"),
        ),
        sample_order=("sample-a", "sample-b", "sample-c"),
    )

    rows = _read_tsv(write_alignment_review_tsv(tmp_path / "review.tsv", matrix))

    assert rows[0]["reason"] == (
        "no anchor; 0/3 present; 0 MS1 backfilled; 2 duplicate-assigned"
    )


def test_write_alignment_review_tsv_counts_duplicate_assigned_separately(
    tmp_path: Path,
):
    from xic_extractor.alignment.tsv_writer import write_alignment_review_tsv

    matrix = AlignmentMatrix(
        clusters=(_cluster(has_anchor=True),),
        cells=(
            _cell("sample-a", "detected", area=100.0),
            _cell("sample-b", "rescued", area=90.0),
            _cell("sample-c", "duplicate_assigned"),
            _cell("sample-d", "absent"),
        ),
        sample_order=("sample-a", "sample-b", "sample-c", "sample-d"),
    )

    rows = _read_tsv(write_alignment_review_tsv(tmp_path / "review.tsv", matrix))

    assert rows[0]["detected_count"] == "1"
    assert rows[0]["absent_count"] == "1"
    assert rows[0]["unchecked_count"] == "0"
    assert rows[0]["present_rate"] == "0.5"
    assert "1 duplicate-assigned" in rows[0]["reason"]


def test_write_alignment_review_tsv_reports_ambiguous_ms1_owner_cells(
    tmp_path: Path,
):
    from xic_extractor.alignment.tsv_writer import write_alignment_review_tsv

    matrix = AlignmentMatrix(
        clusters=(_cluster(has_anchor=True),),
        cells=(
            _cell("sample-a", "detected", area=100.0),
            _cell("sample-b", "ambiguous_ms1_owner"),
            _cell("sample-c", "absent"),
        ),
        sample_order=("sample-a", "sample-b", "sample-c"),
    )

    rows = _read_tsv(write_alignment_review_tsv(tmp_path / "review.tsv", matrix))

    assert rows[0]["detected_count"] == "1"
    assert rows[0]["present_rate"] == "0.333333"
    assert "1 ambiguous MS1 owner" in rows[0]["reason"]


def test_write_alignment_review_tsv_reports_folded_clusters(tmp_path: Path):
    from xic_extractor.alignment.tsv_writer import write_alignment_review_tsv

    matrix = AlignmentMatrix(
        clusters=(
            _cluster(
                has_anchor=True,
                member_count=2,
                folded_cluster_ids=("ALN000002", "ALN000003"),
                folded_member_count=5,
                folded_sample_fill_count=1,
                fold_evidence=(
                    "cid_nl_only;max_mz_ppm=2;max_rt_sec=1;"
                    "min_shared_detected=4"
                ),
            ),
        ),
        cells=(
            _cell("sample-a", "detected", area=10.0, candidate_id="sample-a#1"),
            _cell("sample-b", "rescued", area=20.0),
        ),
        sample_order=("sample-a", "sample-b"),
    )

    rows = _read_tsv(write_alignment_review_tsv(tmp_path / "review.tsv", matrix))

    assert rows[0]["event_cluster_count"] == "3"
    assert rows[0]["event_cluster_ids"] == "ALN000001;ALN000002;ALN000003"
    assert rows[0]["event_member_count"] == "7"
    assert rows[0]["family_evidence"].startswith("cid_nl_only;")
    assert rows[0]["reason"] == (
        "anchor family; 2/2 present; 1 MS1 backfilled; "
        "merged 3 event clusters"
    )


def test_write_alignment_matrix_tsv_blanks_missing_and_invalid_areas(tmp_path: Path):
    from xic_extractor.alignment.tsv_writer import write_alignment_matrix_tsv

    matrix = AlignmentMatrix(
        clusters=(_cluster(),),
        cells=(
            _cell("detected-positive", "detected", area=1234.567),
            _cell("rescued-positive", "rescued", area=25.0),
            _cell("absent-positive", "absent", area=30.0),
            _cell("unchecked-positive", "unchecked", area=40.0),
            _cell("none", "detected", area=None),
            _cell("zero", "detected", area=0.0),
            _cell("negative", "detected", area=-1.0),
            _cell("nan", "detected", area=math.nan),
        ),
        sample_order=(
            "detected-positive",
            "rescued-positive",
            "absent-positive",
            "unchecked-positive",
            "none",
            "zero",
            "negative",
            "nan",
        ),
    )

    rows = _read_tsv(write_alignment_matrix_tsv(tmp_path / "matrix.tsv", matrix))

    assert list(rows[0]) == [
        "feature_family_id",
        "neutral_loss_tag",
        "family_center_mz",
        "family_center_rt",
        "detected-positive",
        "rescued-positive",
        "absent-positive",
        "unchecked-positive",
        "none",
        "zero",
        "negative",
        "nan",
    ]
    assert rows[0]["detected-positive"] == "1234.57"
    assert rows[0]["rescued-positive"] == "25"
    assert rows[0]["absent-positive"] == ""
    assert rows[0]["unchecked-positive"] == ""
    assert rows[0]["none"] == ""
    assert rows[0]["zero"] == ""
    assert rows[0]["negative"] == ""
    assert rows[0]["nan"] == ""


def test_write_alignment_matrix_tsv_blanks_duplicate_assigned_cells(tmp_path: Path):
    from xic_extractor.alignment.tsv_writer import write_alignment_matrix_tsv

    matrix = AlignmentMatrix(
        clusters=(_cluster(),),
        cells=(
            _cell(
                "sample-a",
                "duplicate_assigned",
                area=100.0,
                trace_quality="assigned_duplicate",
            ),
        ),
        sample_order=("sample-a",),
    )

    rows = _read_tsv(write_alignment_matrix_tsv(tmp_path / "matrix.tsv", matrix))

    assert rows[0]["sample-a"] == ""


def test_write_alignment_matrix_tsv_blanks_ambiguous_ms1_owner_cells(
    tmp_path: Path,
):
    from xic_extractor.alignment.tsv_writer import write_alignment_matrix_tsv

    matrix = AlignmentMatrix(
        clusters=(_cluster(),),
        cells=(
            _cell(
                "sample-a",
                "ambiguous_ms1_owner",
                area=100.0,
                trace_quality="ambiguous_ms1_owner",
            ),
        ),
        sample_order=("sample-a",),
    )

    rows = _read_tsv(write_alignment_matrix_tsv(tmp_path / "matrix.tsv", matrix))

    assert rows[0]["sample-a"] == ""


def test_write_alignment_status_matrix_tsv_preserves_duplicate_assigned(
    tmp_path: Path,
):
    from xic_extractor.alignment.tsv_writer import write_alignment_status_matrix_tsv

    matrix = AlignmentMatrix(
        clusters=(_cluster(),),
        cells=(
            _cell(
                "sample-a",
                "duplicate_assigned",
                area=None,
                trace_quality="assigned_duplicate",
            ),
        ),
        sample_order=("sample-a",),
    )

    rows = _read_tsv(
        write_alignment_status_matrix_tsv(tmp_path / "status.tsv", matrix)
    )

    assert rows[0]["sample-a"] == "duplicate_assigned"


def test_debug_tsvs_write_cells_and_status_matrix(tmp_path: Path):
    from xic_extractor.alignment.tsv_writer import (
        write_alignment_cells_tsv,
        write_alignment_status_matrix_tsv,
    )

    matrix = AlignmentMatrix(
        clusters=(_cluster(),),
        cells=(
            _cell("sample-a", "detected", area=10.0, candidate_id="sample-a#1"),
            _cell("sample-b", "unchecked"),
        ),
        sample_order=("sample-a", "sample-b"),
    )

    cells = _read_tsv(write_alignment_cells_tsv(tmp_path / "cells.tsv", matrix))
    status = _read_tsv(
        write_alignment_status_matrix_tsv(tmp_path / "status.tsv", matrix)
    )

    assert list(cells[0]) == [
        "feature_family_id",
        "sample_stem",
        "status",
        "area",
        "apex_rt",
        "height",
        "peak_start_rt",
        "peak_end_rt",
        "rt_delta_sec",
        "trace_quality",
        "scan_support_score",
        "source_candidate_id",
        "source_raw_file",
        "neutral_loss_tag",
        "family_center_mz",
        "family_center_rt",
        "reason",
    ]
    assert cells[0]["status"] == "detected"
    assert cells[0]["source_candidate_id"] == "sample-a#1"
    assert status[0]["sample-a"] == "detected"
    assert status[0]["sample-b"] == "unchecked"


def test_tsv_writers_escape_formula_like_text(tmp_path: Path):
    from xic_extractor.alignment.tsv_writer import (
        write_alignment_matrix_tsv,
        write_alignment_review_tsv,
    )

    matrix = AlignmentMatrix(
        clusters=(
            _cluster(
                cluster_id="=cluster",
                neutral_loss_tag="+NL",
            ),
        ),
        cells=(
            _cell(
                "=sample",
                "detected",
                cluster_id="=cluster",
                area=10.0,
                candidate_id="@candidate",
            ),
        ),
        sample_order=("=sample",),
    )

    review = _read_tsv(write_alignment_review_tsv(tmp_path / "review.tsv", matrix))
    matrix_rows = _read_tsv(write_alignment_matrix_tsv(tmp_path / "matrix.tsv", matrix))

    assert review[0]["feature_family_id"] == "'=cluster"
    assert review[0]["neutral_loss_tag"] == "'+NL"
    assert review[0]["representative_samples"] == "'=sample"
    assert "'=sample" in matrix_rows[0]


def _read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def _cluster(
    *,
    cluster_id: str = "ALN000001",
    neutral_loss_tag: str = "DNA_dR",
    has_anchor: bool = True,
    member_count: int = 0,
    folded_cluster_ids: tuple[str, ...] = (),
    folded_member_count: int = 0,
    folded_sample_fill_count: int = 0,
    fold_evidence: str = "",
) -> AlignmentCluster:
    return AlignmentCluster(
        cluster_id=cluster_id,
        neutral_loss_tag=neutral_loss_tag,
        cluster_center_mz=500.123,
        cluster_center_rt=8.49,
        cluster_product_mz=384.076,
        cluster_observed_neutral_loss_da=116.047,
        has_anchor=has_anchor,
        members=tuple(
            SimpleNamespace(candidate_id=f"{cluster_id}#member-{index}")
            for index in range(member_count)
        ),
        anchor_members=(),
        folded_cluster_ids=folded_cluster_ids,
        folded_member_count=folded_member_count,
        folded_sample_fill_count=folded_sample_fill_count,
        fold_evidence=fold_evidence,
    )


def _cell(
    sample_stem: str,
    status,
    *,
    cluster_id: str = "ALN000001",
    area: float | None = None,
    candidate_id: str | None = None,
    trace_quality: str | None = None,
) -> AlignedCell:
    return AlignedCell(
        sample_stem=sample_stem,
        cluster_id=cluster_id,
        status=status,
        area=area,
        apex_rt=8.49 if area is not None else None,
        height=100.0 if area is not None else None,
        peak_start_rt=8.4 if area is not None else None,
        peak_end_rt=8.6 if area is not None else None,
        rt_delta_sec=0.0 if area is not None else None,
        trace_quality=(
            trace_quality
            if trace_quality is not None
            else ("clean" if area is not None else "unchecked")
        ),
        scan_support_score=0.8 if area is not None else None,
        source_candidate_id=candidate_id,
        source_raw_file=Path(f"{sample_stem}.raw") if candidate_id else None,
        reason="cell reason",
    )
