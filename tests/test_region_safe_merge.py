from pathlib import Path

import numpy as np
import pytest

from xic_extractor.config import ExtractionConfig
from xic_extractor.peak_detection import facade
from xic_extractor.peak_detection.boundaries import BoundaryHypothesis
from xic_extractor.peak_detection.models import (
    PeakCandidate,
    PeakCandidateScore,
    PeakCandidatesResult,
    PeakResult,
)
from xic_extractor.peak_detection.region_model_selection import (
    RegionSelectionDecision,
)
from xic_extractor.peak_detection.region_safe_merge import (
    RegionFirstSafeMergeOutcome,
    apply_region_first_safe_merge_decision,
)


def test_adjacent_wis_safe_merge_updates_selected_boundary_and_area() -> None:
    rt = np.asarray([10.0, 10.1, 10.2, 10.3], dtype=float)
    intensity = np.asarray([100.0, 100.0, 100.0, 100.0], dtype=float)
    selected = _candidate(area=1700.0)
    result = _result(selected)
    score = PeakCandidateScore(candidate=selected, confidence="high", reason="ok")
    decision = _decision(
        shadow_boundary_id="left;right",
        source="adjacent_wis_local_minimum_merge",
    )

    outcome = apply_region_first_safe_merge_decision(
        rt,
        intensity,
        result,
        selected,
        decision,
        {
            "left": _boundary("left", 0, 2),
            "right": _boundary("right", 2, 4),
        },
        candidate_scores=(score,),
    )

    assert outcome.promoted is True
    assert outcome.selected_candidate.peak.peak_start == pytest.approx(10.0)
    assert outcome.selected_candidate.peak.peak_end == pytest.approx(10.3)
    assert outcome.selected_candidate.peak.area == pytest.approx(1800.0)
    assert outcome.selected_candidate.selection_apex_rt == pytest.approx(
        selected.selection_apex_rt
    )
    assert outcome.selected_candidate.ms2_evidence_peak_start == pytest.approx(
        selected.peak.peak_start
    )
    assert outcome.selected_candidate.ms2_evidence_peak_end == pytest.approx(
        selected.peak.peak_end
    )
    assert outcome.selected_candidate.merge_note == "region_first_safe_merge"
    assert outcome.candidates_result.candidates[0] == outcome.selected_candidate
    assert outcome.candidate_scores[0].candidate == outcome.selected_candidate


def test_adjacent_wis_safe_merge_accepts_touching_intervals() -> None:
    rt = np.asarray([10.0, 10.1, 10.2, 10.3], dtype=float)
    intensity = np.asarray([100.0, 100.0, 100.0, 100.0], dtype=float)
    selected = _candidate(area=1700.0)
    result = _result(selected)
    decision = _decision(
        shadow_boundary_id="left;right",
        source="adjacent_wis_local_minimum_merge",
        area_ratio=None,
        selected_interval_gap_max_min=0.0,
    )

    outcome = apply_region_first_safe_merge_decision(
        rt,
        intensity,
        result,
        selected,
        decision,
        {
            "left": _boundary("left", 0, 2),
            "right": _boundary("right", 2, 4),
        },
    )

    assert outcome.promoted is True
    assert outcome.selected_candidate.peak.area == pytest.approx(1800.0)


@pytest.mark.parametrize(
    ("verdict", "source"),
    [
        ("merge_suggested", "same_apex_wider_boundary_merge"),
        ("split_supported", ""),
        ("neighbor_apex_preferred", ""),
        ("wider_boundary_preferred", ""),
        ("current_supported", ""),
    ],
)
def test_safe_merge_refuses_non_adjacent_wis_decisions(
    verdict: str,
    source: str,
) -> None:
    rt = np.asarray([10.0, 10.1, 10.2, 10.3], dtype=float)
    intensity = np.asarray([100.0, 100.0, 100.0, 100.0], dtype=float)
    selected = _candidate(area=1700.0)
    result = _result(selected)

    outcome = apply_region_first_safe_merge_decision(
        rt,
        intensity,
        result,
        selected,
        _decision(
            shadow_boundary_id="left;right",
            verdict=verdict,
            source=source,
        ),
        {
            "left": _boundary("left", 0, 2),
            "right": _boundary("right", 2, 4),
        },
    )

    assert outcome.promoted is False
    assert outcome.selected_candidate == selected
    assert outcome.candidates_result == result


def test_safe_merge_refuses_large_continuous_area_gain() -> None:
    rt = np.asarray([10.0, 10.1, 10.2, 10.3], dtype=float)
    intensity = np.asarray([500.0, 500.0, 500.0, 500.0], dtype=float)
    selected = _candidate(area=1700.0)
    result = _result(selected)
    decision = _decision(
        shadow_boundary_id="left;right",
        source="adjacent_wis_local_minimum_merge",
    )

    outcome = apply_region_first_safe_merge_decision(
        rt,
        intensity,
        result,
        selected,
        decision,
        {
            "left": _boundary("left", 0, 2),
            "right": _boundary("right", 2, 4),
        },
    )

    assert outcome.promoted is False
    assert outcome.selected_candidate == selected


def test_safe_merge_refuses_continuous_area_loss() -> None:
    rt = np.asarray([10.0, 10.1, 10.2, 10.3], dtype=float)
    intensity = np.asarray([50.0, 50.0, 50.0, 50.0], dtype=float)
    selected = _candidate(area=1700.0)
    result = _result(selected)
    decision = _decision(
        shadow_boundary_id="left;right",
        source="adjacent_wis_local_minimum_merge",
    )

    outcome = apply_region_first_safe_merge_decision(
        rt,
        intensity,
        result,
        selected,
        decision,
        {
            "left": _boundary("left", 0, 2),
            "right": _boundary("right", 2, 4),
        },
    )

    assert outcome.promoted is False
    assert outcome.selected_candidate == selected


def test_region_first_safe_merge_candidate_finder_preserves_local_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    legacy = _candidate(
        area=1000.0,
        proposal_sources=("legacy_savgol",),
        left=9.8,
        right=10.2,
    )
    local = _candidate(
        area=900.0,
        proposal_sources=("local_minimum",),
        left=9.81,
        right=10.19,
    )
    monkeypatch.setattr(
        facade,
        "find_peak_candidates_legacy_savgol",
        lambda *_args, **_kwargs: _result(legacy),
    )
    monkeypatch.setattr(
        facade,
        "find_peak_candidates_local_minimum",
        lambda *_args, **_kwargs: _result(local),
    )

    result = facade.find_peak_candidates(
        np.asarray([9.8, 10.0, 10.2], dtype=float),
        np.asarray([1.0, 10.0, 1.0], dtype=float),
        _config(resolver_mode="region_first_safe_merge"),
    )

    assert result.candidates == (local,)


def test_find_peak_and_area_calls_safe_merge_only_for_explicit_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    selected = _candidate(area=1700.0)
    candidate_result = _result(selected)
    calls: list[str] = []

    monkeypatch.setattr(
        facade,
        "find_peak_candidates",
        lambda *_args, **_kwargs: candidate_result,
    )

    def _fake_safe_merge(*args, **kwargs) -> RegionFirstSafeMergeOutcome:
        calls.append("called")
        return RegionFirstSafeMergeOutcome(
            candidates_result=args[2],
            selected_candidate=args[3],
            candidate_scores=kwargs.get("candidate_scores", ()),
            decision=_decision(
                shadow_boundary_id="left;right",
                source="adjacent_wis_local_minimum_merge",
            ),
        )

    monkeypatch.setattr(facade, "apply_region_first_safe_merge", _fake_safe_merge)

    facade.find_peak_and_area(
        np.asarray([9.8, 10.0, 10.2], dtype=float),
        np.asarray([1.0, 10.0, 1.0], dtype=float),
        _config(resolver_mode="legacy_savgol"),
    )
    assert calls == []

    facade.find_peak_and_area(
        np.asarray([9.8, 10.0, 10.2], dtype=float),
        np.asarray([1.0, 10.0, 1.0], dtype=float),
        _config(resolver_mode="region_first_safe_merge"),
    )
    assert calls == ["called"]


def _decision(
    *,
    shadow_boundary_id: str,
    verdict: str = "merge_suggested",
    source: str,
    area_ratio: float | None = 1.1,
    selected_interval_gap_max_min: float | None = 0.02,
) -> RegionSelectionDecision:
    return RegionSelectionDecision(
        shadow_status="evaluated",
        shadow_verdict=verdict,
        current_candidate_id="current",
        current_boundary_id="current",
        shadow_boundary_id=shadow_boundary_id,
        current_rt_left_min=10.0,
        current_rt_apex_min=10.2,
        current_rt_right_min=10.2,
        current_area_raw_counts_seconds=1700.0,
        shadow_rt_left_min=10.0,
        shadow_rt_apex_min=10.2,
        shadow_rt_right_min=10.3,
        shadow_area_raw_counts_seconds=1800.0,
        score_delta=20,
        area_ratio=area_ratio,
        current_scan_count=3,
        shadow_scan_count=4,
        selected_interval_count=2,
        selected_interval_gap_max_min=selected_interval_gap_max_min,
        selected_interval_total_score=120,
        best_single_boundary_score=70,
        review_reason="test",
        merge_suggestion_source=source,
    )


def _candidate(
    *,
    area: float,
    proposal_sources: tuple[str, ...] = ("local_minimum",),
    left: float = 10.0,
    right: float = 10.2,
) -> PeakCandidate:
    peak = PeakResult(
        rt=10.2,
        intensity=100.0,
        intensity_smoothed=100.0,
        area=area,
        peak_start=left,
        peak_end=right,
    )
    return PeakCandidate(
        peak=peak,
        selection_apex_rt=10.2,
        selection_apex_intensity=100.0,
        selection_apex_index=2,
        raw_apex_rt=10.2,
        raw_apex_intensity=100.0,
        raw_apex_index=2,
        prominence=90.0,
        proposal_sources=proposal_sources,
    )


def _boundary(
    boundary_id: str,
    left_index: int,
    right_index: int,
) -> BoundaryHypothesis:
    rt_values = [10.0, 10.1, 10.2, 10.3]
    return BoundaryHypothesis(
        boundary_id=boundary_id,
        sources=("candidate_interval",),
        left_index=left_index,
        right_index=right_index,
        rt_left_min=rt_values[left_index],
        rt_apex_min=10.2,
        rt_right_min=rt_values[right_index - 1],
        width_min=rt_values[right_index - 1] - rt_values[left_index],
        area_raw_counts_seconds=900.0,
        scan_count=right_index - left_index,
    )


def _result(candidate: PeakCandidate) -> PeakCandidatesResult:
    return PeakCandidatesResult(
        status="OK",
        candidates=(candidate,),
        n_points=4,
        max_smoothed=100.0,
        n_prominent_peaks=1,
    )


def _config(*, resolver_mode: str) -> ExtractionConfig:
    return ExtractionConfig(
        data_dir=Path("."),
        dll_dir=Path("."),
        output_csv=Path("xic_results.csv"),
        diagnostics_csv=Path("xic_diagnostics.csv"),
        smooth_window=3,
        smooth_polyorder=1,
        peak_rel_height=0.95,
        peak_min_prominence_ratio=0.1,
        ms2_precursor_tol_da=1.6,
        nl_min_intensity_ratio=0.01,
        resolver_mode=resolver_mode,
    )
