import csv
import math
from pathlib import Path
from types import SimpleNamespace

from xic_extractor.alignment.matrix import AlignedCell, AlignmentMatrix
from xic_extractor.alignment.models import AlignmentCluster

REVIEW_COLUMNS = [
    "cluster_id",
    "neutral_loss_tag",
    "cluster_center_mz",
    "cluster_center_rt",
    "cluster_product_mz",
    "cluster_observed_neutral_loss_da",
    "has_anchor",
    "member_count",
    "detected_count",
    "rescued_count",
    "absent_count",
    "unchecked_count",
    "present_rate",
    "rescued_rate",
    "representative_samples",
    "representative_candidate_ids",
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
        "cluster_id": "ALN000001",
        "neutral_loss_tag": "DNA_dR",
        "cluster_center_mz": "500.123",
        "cluster_center_rt": "8.49",
        "cluster_product_mz": "384.076",
        "cluster_observed_neutral_loss_da": "116.047",
        "has_anchor": "TRUE",
        "member_count": "1",
        "detected_count": "1",
        "rescued_count": "1",
        "absent_count": "1",
        "unchecked_count": "1",
        "present_rate": "0.5",
        "rescued_rate": "0.25",
        "representative_samples": "sample-a;sample-b",
        "representative_candidate_ids": "sample-a#1",
        "warning": "",
        "reason": "anchor cluster; 2/4 present; 1 rescued",
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
        "high_rescue_rate",
        "",
    ]


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
        "cluster_id",
        "neutral_loss_tag",
        "cluster_center_mz",
        "cluster_center_rt",
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
        "cluster_id",
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
        "cluster_center_mz",
        "cluster_center_rt",
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

    assert review[0]["cluster_id"] == "'=cluster"
    assert review[0]["neutral_loss_tag"] == "'+NL"
    assert review[0]["representative_samples"] == "'=sample"
    assert review[0]["representative_candidate_ids"] == "'@candidate"
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
    )


def _cell(
    sample_stem: str,
    status,
    *,
    cluster_id: str = "ALN000001",
    area: float | None = None,
    candidate_id: str | None = None,
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
        trace_quality="clean" if area is not None else "unchecked",
        scan_support_score=0.8 if area is not None else None,
        source_candidate_id=candidate_id,
        source_raw_file=Path(f"{sample_stem}.raw") if candidate_id else None,
        reason="cell reason",
    )
