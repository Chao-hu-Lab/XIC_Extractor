from dataclasses import dataclass, replace
from pathlib import Path

import pytest

from xic_extractor.alignment import AlignmentConfig
from xic_extractor.alignment.backfill import backfill_alignment_matrix
from xic_extractor.alignment.models import build_alignment_cluster
from xic_extractor.config import ExtractionConfig


@dataclass(frozen=True)
class Candidate:
    candidate_id: str
    sample_stem: str
    raw_file: Path = Path("sample.raw")
    neutral_loss_tag: str = "NL141"
    precursor_mz: float = 500.0
    product_mz: float = 359.0
    observed_neutral_loss_da: float = 141.0
    best_seed_rt: float | None = 5.0
    ms1_apex_rt: float | None = 5.0
    ms1_area: float | None = 100.0
    ms1_height: float | None = 50.0
    ms1_peak_rt_start: float | None = 4.9
    ms1_peak_rt_end: float | None = 5.1
    ms1_trace_quality: str = "clean"
    ms1_scan_support_score: float | None = 0.75


def test_backfill_rejects_duplicate_sample_order():
    with pytest.raises(ValueError, match="sample_order must be unique"):
        backfill_alignment_matrix(
            (),
            sample_order=("sample-a", "sample-a"),
            raw_sources={},
            alignment_config=AlignmentConfig(),
            peak_config=_peak_config(),
        )


def test_backfill_rejects_member_sample_missing_from_sample_order():
    cluster = _cluster(
        Candidate(candidate_id="sample-a#1", sample_stem="sample-a"),
        has_anchor=True,
    )

    with pytest.raises(ValueError, match="missing from sample_order"):
        backfill_alignment_matrix(
            (cluster,),
            sample_order=("sample-b",),
            raw_sources={},
            alignment_config=AlignmentConfig(),
            peak_config=_peak_config(),
        )


def test_backfill_rejects_duplicate_members_for_same_sample():
    first = Candidate(candidate_id="sample-a#1", sample_stem="sample-a")
    second = replace(first, candidate_id="sample-a#2")
    cluster = _cluster(first, second, has_anchor=False)

    with pytest.raises(ValueError, match="duplicate members for sample"):
        backfill_alignment_matrix(
            (cluster,),
            sample_order=("sample-a",),
            raw_sources={},
            alignment_config=AlignmentConfig(),
            peak_config=_peak_config(),
        )


def test_empty_clusters_returns_empty_matrix_with_sample_order():
    matrix = backfill_alignment_matrix(
        (),
        sample_order=("sample-b", "sample-a"),
        raw_sources={},
        alignment_config=AlignmentConfig(),
        peak_config=_peak_config(),
    )

    assert matrix.clusters == ()
    assert matrix.cells == ()
    assert matrix.sample_order == ("sample-b", "sample-a")


def test_detected_cell_uses_existing_candidate_without_raw_extraction():
    raw_source = FakeSource()
    candidate = Candidate(
        candidate_id="sample-a#1",
        sample_stem="sample-a",
        raw_file=Path("sample-a.raw"),
        ms1_area=123.4,
        ms1_apex_rt=5.2,
        ms1_height=50.0,
        ms1_peak_rt_start=5.0,
        ms1_peak_rt_end=5.4,
        ms1_trace_quality="clean",
        ms1_scan_support_score=0.8,
    )
    cluster = _cluster(candidate, has_anchor=True)

    matrix = backfill_alignment_matrix(
        (cluster,),
        sample_order=("sample-a",),
        raw_sources={"sample-a": raw_source},
        alignment_config=AlignmentConfig(),
        peak_config=_peak_config(),
    )

    assert raw_source.calls == []
    assert len(matrix.cells) == 1
    cell = matrix.cells[0]
    assert cell.sample_stem == "sample-a"
    assert cell.cluster_id == "ALN000001"
    assert cell.status == "detected"
    assert cell.area == 123.4
    assert cell.apex_rt == 5.2
    assert cell.height == 50.0
    assert cell.peak_start_rt == 5.0
    assert cell.peak_end_rt == 5.4
    assert cell.rt_delta_sec == pytest.approx(0.0)
    assert cell.trace_quality == "clean"
    assert cell.scan_support_score == 0.8
    assert cell.source_candidate_id == "sample-a#1"
    assert cell.source_raw_file == Path("sample-a.raw")
    assert cell.reason == "detected candidate"


def test_non_anchor_missing_sample_is_unchecked_without_raw_extraction():
    raw_source = FakeSource()
    cluster = _cluster(
        Candidate(candidate_id="sample-a#1", sample_stem="sample-a"),
        has_anchor=False,
    )

    matrix = backfill_alignment_matrix(
        (cluster,),
        sample_order=("sample-a", "sample-b"),
        raw_sources={"sample-b": raw_source},
        alignment_config=AlignmentConfig(),
        peak_config=_peak_config(),
    )

    assert raw_source.calls == []
    missing_cell = _cell(matrix, cluster_id="ALN000001", sample_stem="sample-b")
    assert missing_cell.status == "unchecked"
    assert missing_cell.area is None
    assert missing_cell.apex_rt is None
    assert missing_cell.reason == "backfill skipped for non-anchor cluster"


def test_matrix_emits_one_cell_per_cluster_sample_pair():
    first = _cluster_with_id(
        Candidate(candidate_id="sample-a#1", sample_stem="sample-a"),
        has_anchor=False,
        cluster_id="ALN000001",
    )
    second = _cluster_with_id(
        Candidate(candidate_id="sample-b#1", sample_stem="sample-b"),
        has_anchor=False,
        cluster_id="ALN000002",
    )

    matrix = backfill_alignment_matrix(
        (first, second),
        sample_order=("sample-a", "sample-b"),
        raw_sources={},
        alignment_config=AlignmentConfig(),
        peak_config=_peak_config(),
    )

    assert [
        (cell.cluster_id, cell.sample_stem, cell.status)
        for cell in matrix.cells
    ] == [
        ("ALN000001", "sample-a", "detected"),
        ("ALN000001", "sample-b", "unchecked"),
        ("ALN000002", "sample-a", "unchecked"),
        ("ALN000002", "sample-b", "detected"),
    ]


class FakeSource:
    def __init__(self) -> None:
        self.calls: list[tuple[float, float, float, float]] = []

    def extract_xic(
        self,
        mz: float,
        rt_min: float,
        rt_max: float,
        ppm_tol: float,
    ):
        self.calls.append((mz, rt_min, rt_max, ppm_tol))
        return (), ()


def _cell(matrix, *, cluster_id: str, sample_stem: str):
    for cell in matrix.cells:
        if cell.cluster_id == cluster_id and cell.sample_stem == sample_stem:
            return cell
    raise AssertionError(f"missing cell {cluster_id}/{sample_stem}")


def _cluster(*members: Candidate, has_anchor: bool):
    return build_alignment_cluster(
        cluster_id="ALN000001",
        neutral_loss_tag="NL141",
        members=members,
        anchor_members=members if has_anchor else (),
    )


def _cluster_with_id(*members: Candidate, has_anchor: bool, cluster_id: str):
    return build_alignment_cluster(
        cluster_id=cluster_id,
        neutral_loss_tag="NL141",
        members=members,
        anchor_members=members if has_anchor else (),
    )


def _peak_config() -> ExtractionConfig:
    return ExtractionConfig(
        data_dir=Path("."),
        dll_dir=Path("."),
        output_csv=Path("output.csv"),
        diagnostics_csv=Path("diagnostics.csv"),
        smooth_window=15,
        smooth_polyorder=3,
        peak_rel_height=0.95,
        peak_min_prominence_ratio=0.1,
        ms2_precursor_tol_da=1.6,
        nl_min_intensity_ratio=0.01,
    )
