import inspect

import numpy as np

from xic_extractor.config import ExtractionConfig, Target
from xic_extractor.extraction import handoff_spine_runtime
from xic_extractor.neutral_loss import CandidateMS2Evidence
from xic_extractor.peak_detection.models import (
    PeakCandidate,
    PeakCandidateScore,
    PeakDetectionResult,
    PeakResult,
)
from xic_extractor.peak_detection.traces import Trace, targeted_trace_group


def test_build_production_peak_hypotheses_maps_selected_ms2_only(tmp_path) -> None:
    target = _target()
    rt = np.asarray([8.3, 8.5, 8.7, 8.9, 9.1])
    intensity = np.asarray([10.0, 100.0, 20.0, 80.0, 10.0])
    trace_group = targeted_trace_group(
        Trace.from_arrays(
            sample_name="SampleA",
            mz=target.mz,
            rt=rt,
            intensity=intensity,
            rt_min=8.0,
            rt_max=9.2,
            ppm_tol=target.ppm_tol,
            source="unit_test",
        ),
        target_label=target.label,
        resolver_mode="region_first_safe_merge",
        role="Analyte",
        istd_pair=target.istd_pair,
    )
    selected = _candidate(8.50)
    rejected = _candidate(8.90)
    peak_result = PeakDetectionResult(
        status="OK",
        peak=selected.peak,
        n_points=11,
        max_smoothed=1200.0,
        n_prominent_peaks=2,
        candidates=(selected, rejected),
        candidate_scores=(
            _score(selected, confidence="HIGH"),
            _score(rejected, confidence="LOW"),
        ),
    )
    hypotheses = handoff_spine_runtime.build_production_peak_hypotheses(
        config=_config(tmp_path),
        sample_name="SampleA",
        target=target,
        peak_result=peak_result,
        selected_candidate_ms2_evidence=_ms2_evidence(),
        rt=rt,
        intensity=intensity,
        trace_group=trace_group,
    )

    selected_hypothesis = handoff_spine_runtime.selected_peak_hypothesis(hypotheses)
    rejected_hypothesis = next(
        hypothesis for hypothesis in hypotheses if not hypothesis.audit.selected
    )

    assert selected_hypothesis is not None
    assert selected_hypothesis.trace_group_id == trace_group.trace_group_id
    assert selected_hypothesis.integration.raw_scan_indices != ()
    assert selected_hypothesis.evidence.nl_status == "OK"
    assert rejected_hypothesis.evidence.nl_status == ""


def test_selected_peak_hypothesis_returns_none_without_selected_candidate(
    tmp_path,
) -> None:
    hypotheses = handoff_spine_runtime.build_production_peak_hypotheses(
        config=_config(tmp_path),
        sample_name="SampleA",
        target=_target(),
        peak_result=PeakDetectionResult(
            status="PEAK_NOT_FOUND",
            peak=None,
            n_points=5,
            max_smoothed=10.0,
            n_prominent_peaks=0,
            candidates=(),
        ),
    )

    assert hypotheses == ()
    assert handoff_spine_runtime.selected_peak_hypothesis(hypotheses) is None


def test_selected_hypothesis_uses_final_peak_result_confidence_when_score_is_stale(
    tmp_path,
) -> None:
    candidate = _candidate(8.50)
    peak_result = PeakDetectionResult(
        status="OK",
        peak=candidate.peak,
        n_points=11,
        max_smoothed=1200.0,
        n_prominent_peaks=1,
        candidates=(candidate,),
        confidence="VERY_LOW",
        reason="decision: review only, not counted; cap: VERY_LOW",
        candidate_scores=(_score(candidate, confidence="HIGH"),),
    )

    selected = handoff_spine_runtime.selected_peak_hypothesis(
        handoff_spine_runtime.build_production_peak_hypotheses(
            config=_config(tmp_path),
            sample_name="SampleA",
            target=_target(),
            peak_result=peak_result,
        )
    )

    assert selected is not None
    assert selected.evidence.confidence == "VERY_LOW"
    assert selected.evidence.reason == (
        "decision: review only, not counted; cap: VERY_LOW"
    )


def test_production_handoff_runtime_has_no_cwt_audit_dependency() -> None:
    source = inspect.getsource(handoff_spine_runtime)

    assert "add_cwt_proposals_for_audit" not in source
    assert "peak_candidate_table" not in source
    assert "peak_candidate_boundaries" not in source
    assert "peak_candidate_audit" not in source


def _config(tmp_path) -> ExtractionConfig:
    return ExtractionConfig(
        data_dir=tmp_path,
        dll_dir=tmp_path,
        output_csv=tmp_path / "xic_results.csv",
        diagnostics_csv=tmp_path / "diagnostics.csv",
        smooth_window=15,
        smooth_polyorder=3,
        peak_rel_height=0.95,
        peak_min_prominence_ratio=0.1,
        ms2_precursor_tol_da=0.5,
        nl_min_intensity_ratio=0.01,
        resolver_mode="region_first_safe_merge",
    )


def _target() -> Target:
    return Target(
        label="Analyte",
        mz=258.1085,
        rt_min=8.0,
        rt_max=9.0,
        ppm_tol=20.0,
        neutral_loss_da=116.0474,
        nl_ppm_warn=20.0,
        nl_ppm_max=50.0,
        is_istd=False,
        istd_pair="ISTD",
    )


def _candidate(rt: float) -> PeakCandidate:
    peak = PeakResult(
        rt=rt,
        intensity=1200.0,
        intensity_smoothed=1100.0,
        area=1234.5,
        peak_start=rt - 0.1,
        peak_end=rt + 0.1,
    )
    return PeakCandidate(
        peak=peak,
        selection_apex_rt=rt,
        selection_apex_intensity=1100.0,
        selection_apex_index=1,
        raw_apex_rt=rt,
        raw_apex_intensity=1200.0,
        raw_apex_index=1,
        prominence=700.0,
        quality_flags=("trace_continuity_ok",),
    )


def _score(candidate: PeakCandidate, *, confidence: str) -> PeakCandidateScore:
    return PeakCandidateScore(
        candidate=candidate,
        confidence=confidence,
        reason=f"decision: {confidence.lower()}",
        raw_score=90 if confidence == "HIGH" else 40,
        support_labels=("strict_nl_ok",) if confidence == "HIGH" else (),
        concern_labels=() if confidence == "HIGH" else ("low_score",),
    )


def _ms2_evidence() -> CandidateMS2Evidence:
    return CandidateMS2Evidence(
        ms2_present=True,
        nl_match=True,
        nl_status="OK",
        trigger_scan_count=1,
        strict_nl_scan_count=1,
        best_loss_ppm=1.2,
        best_scan_rt=8.5,
        best_product_base_ratio=0.4,
        alignment_source="region",
    )
