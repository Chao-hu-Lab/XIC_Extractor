import csv
from pathlib import Path

import numpy as np

from xic_extractor.extraction.peak_candidate_boundaries import (
    build_peak_candidate_boundary_rows,
)
from xic_extractor.output.peak_candidate_boundaries import (
    write_peak_candidate_boundaries_tsv,
)
from xic_extractor.signal_processing import (
    PeakCandidate,
    PeakDetectionResult,
    PeakResult,
)


def test_build_boundary_rows_emits_alternatives_for_each_candidate() -> None:
    selected = _candidate(8.30, left=8.00, right=8.60)
    rejected = _candidate(8.80, left=8.50, right=9.00, sources=("local_minimum",))
    peak_result = PeakDetectionResult(
        status="OK",
        peak=selected.peak,
        n_points=11,
        max_smoothed=100.0,
        n_prominent_peaks=2,
        candidates=(selected, rejected),
    )
    rt = np.asarray([8.0, 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 8.8, 8.9, 9.0])
    intensity = np.asarray(
        [10.0, 18.0, 70.0, 100.0, 70.0, 18.0, 10.0, 20.0, 80.0, 20.0, 10.0]
    )

    rows = build_peak_candidate_boundary_rows(
        sample_name="SampleA",
        target_label="Analyte",
        role="Analyte",
        istd_pair="ISTD",
        resolver_mode="arbitrated",
        peak_result=peak_result,
        rt=rt,
        intensity=intensity,
        group="Tumor",
    )

    assert {row["target_label"] for row in rows} == {"Analyte"}
    assert {row["resolver_mode"] for row in rows} == {"arbitrated"}
    assert {row["analysis_mode"] for row in rows} == {"targeted"}
    assert {row["selected_candidate"] for row in rows} == {"TRUE", "FALSE"}
    assert {row["candidate_id"] for row in rows} == {
        "SampleA|Analyte|arbitrated|legacy_savgol|8.30000|8.00000|8.60000",
        "SampleA|Analyte|arbitrated|local_minimum|8.80000|8.50000|9.00000",
    }
    selected_rows = [row for row in rows if row["selected_candidate"] == "TRUE"]
    assert any("candidate_interval" in row["boundary_sources"] for row in selected_rows)
    assert "half_height" in {row["boundary_sources"] for row in selected_rows}
    assert all(row["boundary_id"].startswith(row["candidate_id"]) for row in rows)
    assert all(row["area_delta_vs_candidate_interval"] != "" for row in rows)
    assert all(row["area_baseline_corrected"] != "" for row in rows)
    assert all(row["area_uncertainty"] != "" for row in rows)
    assert {row["baseline_type"] for row in rows} == {"linear_edge"}
    assert all(row["baseline_score"] != "" for row in rows)


def test_write_peak_candidate_boundaries_tsv_serializes_rows_safely(
    tmp_path: Path,
) -> None:
    path = tmp_path / "peak_candidate_boundaries.tsv"
    row = build_peak_candidate_boundary_rows(
        sample_name="SampleA",
        target_label="Analyte",
        role="Analyte",
        istd_pair="",
        resolver_mode="legacy_savgol",
        peak_result=PeakDetectionResult(
            status="OK",
            peak=_candidate(8.30, left=8.00, right=8.60).peak,
            n_points=11,
            max_smoothed=100.0,
            n_prominent_peaks=1,
            candidates=(_candidate(8.30, left=8.00, right=8.60),),
        ),
        rt=np.asarray([8.0, 8.1, 8.2, 8.3, 8.4, 8.5, 8.6]),
        intensity=np.asarray([10.0, 18.0, 70.0, 100.0, 70.0, 18.0, 10.0]),
    )[0]
    row["boundary_sources"] = "line1\nline2\twith tab"

    write_peak_candidate_boundaries_tsv(path, [row])

    text = path.read_text(encoding="utf-8-sig")
    assert "line1 line2 with tab" in text
    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    assert rows[0]["sample_name"] == "SampleA"
    assert rows[0]["boundary_sources"] == "line1 line2 with tab"


def test_disabled_boundary_writer_is_noop(tmp_path: Path) -> None:
    path = tmp_path / "peak_candidate_boundaries.tsv"

    write_peak_candidate_boundaries_tsv(
        path,
        [{"sample_name": "SampleA"}],
        enabled=False,
    )

    assert not path.exists()


def _candidate(
    rt: float,
    *,
    left: float,
    right: float,
    sources: tuple[str, ...] = ("legacy_savgol",),
) -> PeakCandidate:
    peak = PeakResult(
        rt=rt,
        intensity=100.0,
        intensity_smoothed=95.0,
        area=1200.0,
        peak_start=left,
        peak_end=right,
    )
    return PeakCandidate(
        peak=peak,
        selection_apex_rt=rt,
        selection_apex_intensity=95.0,
        selection_apex_index=3,
        raw_apex_rt=rt,
        raw_apex_intensity=100.0,
        raw_apex_index=3,
        prominence=90.0,
        proposal_sources=sources,
        source_apex_rank=1,
    )
