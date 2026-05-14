from __future__ import annotations

import math
from pathlib import Path

from xic_extractor.alignment.cell_quality import (
    build_cell_quality_decisions,
    decide_cell_quality,
)
from xic_extractor.alignment.config import AlignmentConfig
from xic_extractor.alignment.matrix import AlignedCell


def test_detected_cell_requires_positive_finite_area() -> None:
    config = AlignmentConfig()

    assert (
        decide_cell_quality(_cell("s1", "FAM001", "detected", 100.0), config)
        .quality_status
        == "detected_quantifiable"
    )
    assert (
        decide_cell_quality(_cell("s1", "FAM001", "detected", 0.0), config)
        .quality_status
        == "invalid"
    )
    assert (
        decide_cell_quality(_cell("s1", "FAM001", "detected", math.nan), config)
        .quality_status
        == "invalid"
    )


def test_rescue_requires_complete_peak_and_rt_inside_alignment_window() -> None:
    config = AlignmentConfig(preferred_rt_sec=10.0, max_rt_sec=30.0)

    assert (
        decide_cell_quality(_cell("s1", "FAM001", "rescued", 100.0), config)
        .quality_status
        == "rescue_quantifiable"
    )
    assert (
        decide_cell_quality(
            _cell("s1", "FAM001", "rescued", 100.0, apex_rt=None),
            config,
        ).quality_status
        == "review_rescue"
    )
    outside = decide_cell_quality(
        _cell("s1", "FAM001", "rescued", 100.0, rt_delta_sec=31.0),
        config,
    )
    assert outside.quality_status == "review_rescue"
    assert outside.quality_reason == "rt_outside_max"


def test_duplicate_and_ambiguous_cells_do_not_support_identity() -> None:
    config = AlignmentConfig()
    decisions = build_cell_quality_decisions(
        (
            _cell("s1", "FAM001", "duplicate_assigned", 100.0),
            _cell("s2", "FAM001", "ambiguous_ms1_owner", None),
        ),
        config,
    )

    assert decisions[("FAM001", "s1")].quality_status == "duplicate_loser"
    assert decisions[("FAM001", "s2")].quality_status == "ambiguous_owner"
    assert not decisions[("FAM001", "s1")].is_quantifiable_cell
    assert not decisions[("FAM001", "s2")].is_detected_identity_support


def _cell(
    sample_stem: str,
    cluster_id: str,
    status: str,
    area: float | None,
    *,
    apex_rt: float | None = 8.5,
    height: float | None = 100.0,
    peak_start_rt: float | None = 8.45,
    peak_end_rt: float | None = 8.55,
    rt_delta_sec: float | None = 0.0,
) -> AlignedCell:
    return AlignedCell(
        sample_stem=sample_stem,
        cluster_id=cluster_id,
        status=status,  # type: ignore[arg-type]
        area=area,
        apex_rt=apex_rt,
        height=height,
        peak_start_rt=peak_start_rt,
        peak_end_rt=peak_end_rt,
        rt_delta_sec=rt_delta_sec,
        trace_quality="clean",
        scan_support_score=0.8,
        source_candidate_id=f"{sample_stem}#{cluster_id}",
        source_raw_file=Path(f"{sample_stem}.raw"),
        reason=status,
    )
