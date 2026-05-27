from xic_extractor.config import Target
from xic_extractor.extraction.handoff_spine_runtime import (
    build_production_peak_hypotheses,
    selected_peak_hypothesis,
)
from xic_extractor.extraction.result_assembly import build_extraction_result
from xic_extractor.neutral_loss import CandidateMS2Evidence, NLResult
from xic_extractor.peak_detection.models import (
    PeakCandidate,
    PeakCandidateScore,
    PeakDetectionResult,
    PeakResult,
)


def test_build_extraction_result_preserves_parity_with_selected_hypothesis() -> None:
    target = _target()
    candidate = _candidate()
    peak_result = PeakDetectionResult(
        status="OK",
        peak=candidate.peak,
        n_points=12,
        max_smoothed=1200.0,
        n_prominent_peaks=1,
        candidates=(candidate,),
        confidence="LOW",
        reason="concerns: local_sn",
        severities=((1, "local_sn"),),
        score_breakdown=(("Raw Score", "41"),),
        candidate_scores=(_score(candidate),),
    )
    evidence = _ms2_evidence()
    selected = selected_peak_hypothesis(
        build_production_peak_hypotheses(
            config=_Config(),
            sample_name="SampleA",
            target=target,
            peak_result=peak_result,
            selected_candidate_ms2_evidence=evidence,
        )
    )

    legacy = build_extraction_result(
        peak_result=peak_result,
        nl_result=NLResult("WARN", 12.0, 8.5, 1, 0, 1),
        candidate_ms2_evidence=evidence,
        target=target,
        candidate=candidate,
        scoring_context_builder=None,
    )
    with_hypothesis = build_extraction_result(
        peak_result=peak_result,
        nl_result=NLResult("WARN", 12.0, 8.5, 1, 0, 1),
        candidate_ms2_evidence=evidence,
        target=target,
        candidate=candidate,
        scoring_context_builder=None,
        selected_hypothesis=selected,
    )

    assert selected is not None
    assert with_hypothesis.peak_result is legacy.peak_result
    assert with_hypothesis.nl_token == legacy.nl_token
    assert with_hypothesis.target_label == legacy.target_label
    assert with_hypothesis.role == legacy.role
    assert with_hypothesis.istd_pair == legacy.istd_pair
    assert with_hypothesis.confidence == legacy.confidence
    assert with_hypothesis.reason == legacy.reason
    assert with_hypothesis.severities == legacy.severities
    assert with_hypothesis.quality_penalty == legacy.quality_penalty
    assert with_hypothesis.quality_flags == legacy.quality_flags
    assert with_hypothesis.score_breakdown == legacy.score_breakdown


def test_build_extraction_result_keeps_high_fallback_without_scoring_confidence() -> None:
    target = _target()
    candidate = _candidate()
    peak_result = PeakDetectionResult(
        status="OK",
        peak=candidate.peak,
        n_points=12,
        max_smoothed=1200.0,
        n_prominent_peaks=1,
        candidates=(candidate,),
    )
    selected = selected_peak_hypothesis(
        build_production_peak_hypotheses(
            config=_Config(),
            sample_name="SampleA",
            target=target,
            peak_result=peak_result,
        )
    )

    result = build_extraction_result(
        peak_result=peak_result,
        nl_result=None,
        candidate_ms2_evidence=None,
        target=target,
        candidate=candidate,
        scoring_context_builder=None,
        selected_hypothesis=selected,
    )

    assert selected is not None
    assert selected.evidence.confidence == ""
    assert result.confidence == "HIGH"
    assert result.reason == ""


def test_build_extraction_result_preserves_final_confidence_when_score_is_stale() -> None:
    target = _target()
    candidate = _candidate()
    peak_result = PeakDetectionResult(
        status="OK",
        peak=candidate.peak,
        n_points=12,
        max_smoothed=1200.0,
        n_prominent_peaks=1,
        candidates=(candidate,),
        confidence="VERY_LOW",
        reason="decision: review only, not counted; cap: VERY_LOW",
        candidate_scores=(
            PeakCandidateScore(
                candidate=candidate,
                confidence="HIGH",
                reason="decision: detected",
                raw_score=95,
            ),
        ),
    )
    selected = selected_peak_hypothesis(
        build_production_peak_hypotheses(
            config=_Config(),
            sample_name="SampleA",
            target=target,
            peak_result=peak_result,
        )
    )

    result = build_extraction_result(
        peak_result=peak_result,
        nl_result=None,
        candidate_ms2_evidence=None,
        target=target,
        candidate=candidate,
        scoring_context_builder=None,
        selected_hypothesis=selected,
    )

    assert selected is not None
    assert selected.evidence.confidence == "VERY_LOW"
    assert result.confidence == "VERY_LOW"
    assert result.reason == "decision: review only, not counted; cap: VERY_LOW"


class _Config:
    resolver_mode = "region_first_safe_merge"


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


def _candidate() -> PeakCandidate:
    peak = PeakResult(
        rt=8.5,
        intensity=1200.0,
        intensity_smoothed=1100.0,
        area=1234.5,
        peak_start=8.4,
        peak_end=8.6,
    )
    return PeakCandidate(
        peak=peak,
        selection_apex_rt=8.5,
        selection_apex_intensity=1100.0,
        selection_apex_index=1,
        raw_apex_rt=8.5,
        raw_apex_intensity=1200.0,
        raw_apex_index=1,
        prominence=700.0,
        quality_flags=("too_broad",),
    )


def _score(candidate: PeakCandidate) -> PeakCandidateScore:
    return PeakCandidateScore(
        candidate=candidate,
        confidence="LOW",
        reason="concerns: local_sn",
        raw_score=41,
        concern_labels=("local_sn",),
    )


def _ms2_evidence() -> CandidateMS2Evidence:
    return CandidateMS2Evidence(
        ms2_present=True,
        nl_match=False,
        nl_status="NL_FAIL",
        trigger_scan_count=1,
        strict_nl_scan_count=0,
        best_loss_ppm=125.0,
        best_scan_rt=8.5,
        best_product_base_ratio=0.4,
        alignment_source="region",
    )
