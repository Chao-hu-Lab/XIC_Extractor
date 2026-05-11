from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np
import pytest

import xic_extractor.alignment.backfill as backfill_module
from xic_extractor.alignment import AlignmentConfig
from xic_extractor.alignment.backfill import backfill_alignment_matrix
from xic_extractor.alignment.models import build_alignment_cluster
from xic_extractor.config import ExtractionConfig
from xic_extractor.peak_detection.models import PeakDetectionResult, PeakResult


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


def test_anchor_missing_sample_extracts_cluster_center_xic(monkeypatch):
    source = FakeSource()
    cluster = _cluster(
        Candidate(candidate_id="sample-a#1", sample_stem="sample-a"),
        has_anchor=True,
    )
    _patch_peak_result(monkeypatch, _no_peak_result())

    backfill_alignment_matrix(
        (cluster,),
        sample_order=("sample-a", "sample-b"),
        raw_sources={"sample-b": source},
        alignment_config=AlignmentConfig(preferred_ppm=20.0, max_rt_sec=180.0),
        peak_config=_peak_config(),
    )

    assert source.calls == [(500.0, 2.0, 8.0, 20.0)]


def test_anchor_missing_sample_rescues_peak(monkeypatch):
    source = FakeSource()
    cluster = _cluster(
        Candidate(candidate_id="sample-a#1", sample_stem="sample-a"),
        has_anchor=True,
    )
    _patch_peak_result(
        monkeypatch,
        _ok_peak_result(
            rt=5.1,
            area=456.7,
            height=88.0,
            peak_start=5.0,
            peak_end=5.2,
        ),
    )

    matrix = backfill_alignment_matrix(
        (cluster,),
        sample_order=("sample-a", "sample-b"),
        raw_sources={"sample-b": source},
        alignment_config=AlignmentConfig(max_rt_sec=180.0),
        peak_config=_peak_config(),
    )

    rescued = _cell(matrix, cluster_id="ALN000001", sample_stem="sample-b")
    assert rescued.status == "rescued"
    assert rescued.area == 456.7
    assert rescued.apex_rt == 5.1
    assert rescued.height == 88.0
    assert rescued.peak_start_rt == 5.0
    assert rescued.peak_end_rt == 5.2
    assert rescued.rt_delta_sec == pytest.approx(6.0)
    assert rescued.trace_quality == "rescued"
    assert rescued.scan_support_score == pytest.approx(0.6)
    assert rescued.source_candidate_id is None
    assert rescued.source_raw_file is None
    assert rescued.reason == "MS1 peak rescued at cluster center"


def test_anchor_missing_sample_no_peak_is_absent(monkeypatch):
    source = FakeSource()
    cluster = _cluster(
        Candidate(candidate_id="sample-a#1", sample_stem="sample-a"),
        has_anchor=True,
    )
    _patch_peak_result(monkeypatch, _no_peak_result())

    matrix = backfill_alignment_matrix(
        (cluster,),
        sample_order=("sample-a", "sample-b"),
        raw_sources={"sample-b": source},
        alignment_config=AlignmentConfig(),
        peak_config=_peak_config(),
    )

    absent = _cell(matrix, cluster_id="ALN000001", sample_stem="sample-b")
    assert absent.status == "absent"
    assert absent.area is None
    assert absent.apex_rt is None
    assert absent.reason == "MS1 backfill checked and no peak found"


def test_anchor_missing_sample_without_raw_source_is_unchecked(monkeypatch):
    cluster = _cluster(
        Candidate(candidate_id="sample-a#1", sample_stem="sample-a"),
        has_anchor=True,
    )
    _patch_peak_result(monkeypatch, _ok_peak_result())

    matrix = backfill_alignment_matrix(
        (cluster,),
        sample_order=("sample-a", "sample-b"),
        raw_sources={},
        alignment_config=AlignmentConfig(),
        peak_config=_peak_config(),
    )

    unchecked = _cell(matrix, cluster_id="ALN000001", sample_stem="sample-b")
    assert unchecked.status == "unchecked"
    assert unchecked.reason == "missing raw source for MS1 backfill"


def test_anchor_backfill_peak_outside_max_rt_is_absent(monkeypatch):
    source = FakeSource()
    cluster = _cluster(
        Candidate(candidate_id="sample-a#1", sample_stem="sample-a"),
        has_anchor=True,
    )
    _patch_peak_result(monkeypatch, _ok_peak_result(rt=8.1))

    matrix = backfill_alignment_matrix(
        (cluster,),
        sample_order=("sample-a", "sample-b"),
        raw_sources={"sample-b": source},
        alignment_config=AlignmentConfig(max_rt_sec=180.0),
        peak_config=_peak_config(),
    )

    absent = _cell(matrix, cluster_id="ALN000001", sample_stem="sample-b")
    assert absent.status == "absent"
    assert absent.area is None
    assert absent.apex_rt == 8.1
    assert absent.reason == "MS1 peak outside cluster RT guard"


@pytest.mark.parametrize(
    ("rt", "intensity"),
    [
        (np.array([4.9, np.nan, 5.1]), np.array([1.0, 4.0, 10.0])),
        (np.array([4.9, 5.0, 5.1]), np.array([1.0, np.inf, 10.0])),
    ],
)
def test_anchor_backfill_nonfinite_trace_is_unchecked_without_peak_picker(
    monkeypatch,
    rt,
    intensity,
):
    source = FakeSource(rt=rt, intensity=intensity)
    cluster = _cluster(
        Candidate(candidate_id="sample-a#1", sample_stem="sample-a"),
        has_anchor=True,
    )
    peak_picker_called = False

    def fail_if_called(*args, **kwargs):
        nonlocal peak_picker_called
        peak_picker_called = True
        return _no_peak_result()

    monkeypatch.setattr(backfill_module, "find_peak_and_area", fail_if_called)

    matrix = backfill_alignment_matrix(
        (cluster,),
        sample_order=("sample-a", "sample-b"),
        raw_sources={"sample-b": source},
        alignment_config=AlignmentConfig(),
        peak_config=_peak_config(),
    )

    unchecked = _cell(matrix, cluster_id="ALN000001", sample_stem="sample-b")
    assert unchecked.status == "unchecked"
    assert unchecked.reason == "MS1 backfill could not be checked"
    assert peak_picker_called is False


class FakeSource:
    def __init__(
        self,
        rt: np.ndarray | None = None,
        intensity: np.ndarray | None = None,
    ) -> None:
        self.rt = rt if rt is not None else np.array([4.9, 5.0, 5.1, 5.2])
        self.intensity = (
            intensity if intensity is not None else np.array([1.0, 4.0, 10.0, 3.0])
        )
        self.calls: list[tuple[float, float, float, float]] = []

    def extract_xic(
        self,
        mz: float,
        rt_min: float,
        rt_max: float,
        ppm_tol: float,
    ):
        self.calls.append((mz, rt_min, rt_max, ppm_tol))
        return self.rt, self.intensity


def _cell(matrix, *, cluster_id: str, sample_stem: str):
    for cell in matrix.cells:
        if cell.cluster_id == cluster_id and cell.sample_stem == sample_stem:
            return cell
    raise AssertionError(f"missing cell {cluster_id}/{sample_stem}")


def _patch_peak_result(monkeypatch, result: PeakDetectionResult) -> None:
    def fake_find_peak_and_area(rt, intensity, config, **kwargs):
        assert kwargs["preferred_rt"] == 5.0
        assert kwargs["strict_preferred_rt"] is False
        return result

    monkeypatch.setattr(backfill_module, "find_peak_and_area", fake_find_peak_and_area)


def _ok_peak_result(
    *,
    rt: float = 5.1,
    area: float = 456.7,
    height: float = 88.0,
    peak_start: float = 5.0,
    peak_end: float = 5.2,
) -> PeakDetectionResult:
    return PeakDetectionResult(
        status="OK",
        peak=PeakResult(
            rt=rt,
            intensity=height,
            intensity_smoothed=height,
            area=area,
            peak_start=peak_start,
            peak_end=peak_end,
        ),
        n_points=4,
        max_smoothed=height,
        n_prominent_peaks=1,
    )


def _no_peak_result() -> PeakDetectionResult:
    return PeakDetectionResult(
        status="PEAK_NOT_FOUND",
        peak=None,
        n_points=4,
        max_smoothed=10.0,
        n_prominent_peaks=0,
    )


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
