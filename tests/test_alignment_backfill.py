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


def _cluster(*members: Candidate, has_anchor: bool):
    return build_alignment_cluster(
        cluster_id="ALN000001",
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
