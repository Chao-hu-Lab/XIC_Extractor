import typing

import pytest

from xic_extractor.config import Target
from xic_extractor.evidence_semantics import EvidenceDecisionSemantics
from xic_extractor.extraction.handoff_spine_runtime import (
    build_production_peak_hypotheses,
    selected_peak_hypothesis,
)
from xic_extractor.extraction.result_assembly import build_extraction_result
from xic_extractor.extractor import ExtractionResult
from xic_extractor.neutral_loss import CandidateMS2Evidence, NLResult
from xic_extractor.peak_detection.hypotheses import (
    AuditTrail,
    EvidenceVector,
    IntegrationResult,
    PeakHypothesis,
)
from xic_extractor.peak_detection.model_selection import PeakModelSelectionResult
from xic_extractor.peak_detection.models import (
    PeakCandidate,
    PeakCandidateScore,
    PeakDetectionResult,
    PeakResult,
)
from xic_extractor.peak_detection.selection_decision import (
    PeakHypothesisSelectionDecision,
)
from xic_extractor.peak_detection.targeted_product_projection import (
    TargetedProductProjection,
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
    assert with_hypothesis.selection_decision is not None
    assert (
        with_hypothesis.confidence
        == with_hypothesis.selection_decision.projected_confidence
    )
    assert with_hypothesis.reason == with_hypothesis.selection_decision.projected_reason


def test_build_extraction_result_keeps_high_fallback_without_scoring_confidence(
) -> None:
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
    assert result.selection_decision is not None
    assert result.selection_decision.projected_confidence == "HIGH"
    assert result.confidence == "HIGH"
    assert result.reason == ""


def test_build_extraction_result_preserves_final_confidence_when_score_is_stale(
) -> None:
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
    assert result.selection_decision is not None
    assert result.selection_decision.projected_confidence == "VERY_LOW"
    assert (
        result.selection_decision.projected_reason
        == "decision: review only, not counted; cap: VERY_LOW"
    )
    assert result.confidence == "VERY_LOW"
    assert result.reason == "decision: review only, not counted; cap: VERY_LOW"


def test_build_extraction_result_uses_selection_decision_projection() -> None:
    peak_result = _peak_result_with_candidate()
    selected = _selected_hypothesis_with_integration(
        IntegrationResult(
            rt_left_min=8.4,
            rt_apex_min=8.5,
            rt_right_min=8.6,
            raw_apex_rt_min=8.5,
            rt_width_min=0.2,
            height_raw=1200.0,
            height_smoothed=1100.0,
            area_raw_counts_seconds=1234.5,
        )
    )
    decision = PeakHypothesisSelectionDecision(
        selected_candidate_id=selected.hypothesis_id,
        trace_group_id=selected.trace_group_id,
        decision_class="review",
        projected_confidence="MEDIUM",
        projected_reason="decision projection",
        review_reasons=("explicit_decision_projection",),
        legacy_projection_status="active_policy_remaining",
    )

    result = build_extraction_result(
        peak_result=peak_result,
        nl_result=None,
        candidate_ms2_evidence=None,
        target=_target(),
        candidate=peak_result.candidates[0],
        scoring_context_builder=None,
        selected_hypothesis=selected,
        selection_decision=decision,
    )

    assert result.selection_decision is decision
    assert result.confidence == "MEDIUM"
    assert result.reason == "decision projection"


def test_extraction_result_reports_selected_integration_values() -> None:
    peak_result = _peak_result_with_candidate()
    selected = _selected_hypothesis_with_integration(
        IntegrationResult(
            rt_left_min=8.7,
            rt_apex_min=8.95,
            rt_right_min=9.3,
            raw_apex_rt_min=8.96,
            rt_width_min=-0.42,
            height_raw=765.0,
            height_smoothed=700.0,
            area_raw_counts_seconds=4567.89,
        )
    )

    result = build_extraction_result(
        peak_result=peak_result,
        nl_result=None,
        candidate_ms2_evidence=None,
        target=_target(),
        candidate=peak_result.candidates[0],
        scoring_context_builder=None,
        selected_hypothesis=selected,
    )

    assert result.reported_rt == 8.95
    assert result.reported_peak_area == 4567.89
    assert result.reported_peak_intensity == 765.0
    assert result.reported_peak_start == 8.7
    assert result.reported_peak_end == 9.3
    assert result.reported_peak_width == pytest.approx(0.42)


def test_extraction_result_runtime_type_hints_are_resolvable() -> None:
    hints = typing.get_type_hints(ExtractionResult)

    assert hints["selected_hypothesis"] == PeakHypothesis | None
    assert hints["selection_decision"] == PeakHypothesisSelectionDecision | None
    assert hints["model_selection_result"] == PeakModelSelectionResult | None
    assert hints["targeted_product_projection"] == TargetedProductProjection | None


def test_extraction_result_projection_accessors_fall_back_to_legacy_peak() -> None:
    peak_result = _peak_result_with_candidate()
    result = build_extraction_result(
        peak_result=peak_result,
        nl_result=None,
        candidate_ms2_evidence=None,
        target=_target(),
        candidate=peak_result.candidates[0],
        scoring_context_builder=None,
        selected_hypothesis=None,
    )

    peak = peak_result.peak
    assert peak is not None
    assert result.reported_rt == peak_result.candidates[0].selection_apex_rt
    assert result.reported_peak_area == peak.area
    assert result.reported_peak_intensity == peak.intensity
    assert result.reported_peak_start == peak.peak_start
    assert result.reported_peak_end == peak.peak_end
    assert result.reported_peak_width == abs(peak.peak_end - peak.peak_start)


def test_build_extraction_result_adds_targeted_product_projection() -> None:
    target = _target(is_istd=True)
    candidate = _candidate(quality_flags=())
    peak_result = PeakDetectionResult(
        status="OK",
        peak=candidate.peak,
        n_points=12,
        max_smoothed=1200.0,
        n_prominent_peaks=1,
        candidates=(candidate,),
        confidence="VERY_LOW",
        reason="decision: review only, not counted; cap: nl fail",
        severities=((3, "nl_support"),),
        candidate_scores=(
            PeakCandidateScore(
                candidate=candidate,
                confidence="VERY_LOW",
                reason="decision: review only, not counted; cap: nl fail",
                raw_score=10,
                support_labels=("local_sn_strong", "shape_clean"),
                concern_labels=("nl_fail",),
                cap_labels=("nl_fail_cap",),
            ),
        ),
    )
    selected = selected_peak_hypothesis(
        build_production_peak_hypotheses(
            config=_Config(),
            sample_name="SampleA",
            target=target,
            peak_result=peak_result,
            selected_candidate_ms2_evidence=_ms2_evidence(),
        )
    )

    result = build_extraction_result(
        peak_result=peak_result,
        nl_result=None,
        candidate_ms2_evidence=_ms2_evidence(),
        target=target,
        candidate=candidate,
        scoring_context_builder=None,
        selected_hypothesis=selected,
    )

    projection = result.targeted_product_projection
    assert projection is not None
    assert result.confidence == "VERY_LOW"
    assert result.nl_token == "NL_FAIL"
    assert projection.product_state == "detected_flagged"
    assert projection.counted_detection is True
    assert "plausible_dda_nl_dropout" in projection.review_reasons


def test_istd_rt_conflict_inside_target_window_stays_counted() -> None:
    target = _target(is_istd=True)
    candidate = _candidate(quality_flags=())
    peak_result = PeakDetectionResult(
        status="OK",
        peak=candidate.peak,
        n_points=12,
        max_smoothed=1200.0,
        n_prominent_peaks=1,
        candidates=(candidate,),
        confidence="HIGH",
        reason="decision: accepted",
        candidate_scores=(
            PeakCandidateScore(
                candidate=candidate,
                confidence="HIGH",
                reason="decision: accepted",
                raw_score=95,
                support_labels=("local_sn_strong", "shape_clean"),
            ),
        ),
    )
    selected = PeakHypothesis(
        hypothesis_id="SampleA|ISTD|selected",
        trace_group_id="SampleA|ISTD|targeted",
        target_label="ISTD",
        role="ISTD",
        istd_pair="ISTD",
        analysis_mode="targeted",
        resolver_mode="region_first_safe_merge",
        integration=IntegrationResult(
            rt_left_min=8.4,
            rt_apex_min=8.5,
            rt_right_min=8.6,
            raw_apex_rt_min=8.5,
            rt_width_min=0.2,
            height_raw=1200.0,
            height_smoothed=1100.0,
            area_raw_counts_seconds=1234.5,
        ),
        evidence=EvidenceVector(
            confidence="HIGH",
            reason="decision: accepted",
            decision_semantics=EvidenceDecisionSemantics(
                decision_class="ambiguous",
                support_reasons=("ms1_coherent", "candidate_aligned_ms2_nl"),
                conflict_reasons=("targeted_rt_conflict",),
                review_reasons=("targeted_rt_review",),
            ),
        ),
        audit=AuditTrail(selected=True, selection_rank=1),
    )
    ms2_evidence = CandidateMS2Evidence(
        ms2_present=True,
        nl_match=True,
        nl_status="OK",
        trigger_scan_count=1,
        strict_nl_scan_count=1,
        best_loss_ppm=2.5,
        best_scan_rt=8.5,
        best_product_base_ratio=0.8,
        alignment_source="region",
    )

    result = build_extraction_result(
        peak_result=peak_result,
        nl_result=NLResult("OK", 2.5, 8.5, 1, 0, 1),
        candidate_ms2_evidence=ms2_evidence,
        target=target,
        candidate=candidate,
        scoring_context_builder=None,
        selected_hypothesis=selected,
    )

    projection = result.targeted_product_projection
    assert projection is not None
    assert projection.product_state == "detected_flagged"
    assert projection.counted_detection is True
    assert "targeted_rt_conflict" not in projection.conflict_reasons
    assert "targeted_rt_review" in projection.review_reasons


@pytest.mark.parametrize(
    "conflict_reason",
    ("trace_morphology_conflict", "hard_local_quality_conflict"),
)
def test_istd_trace_conflict_with_product_support_stays_counted(
    conflict_reason: str,
) -> None:
    result = _result_with_targeted_projection_semantics(
        target=_target(is_istd=True),
        support_reasons=("ms1_coherent", "candidate_aligned_ms2_nl"),
        conflict_reasons=(conflict_reason,),
    )

    projection = result.targeted_product_projection
    assert projection is not None
    assert projection.product_state == "detected_flagged"
    assert projection.counted_detection is True
    assert conflict_reason not in projection.conflict_reasons
    assert "trace_morphology_review" in projection.review_reasons


def test_analyte_trace_conflict_does_not_use_istd_projection_escape() -> None:
    result = _result_with_targeted_projection_semantics(
        target=_target(is_istd=False),
        support_reasons=("ms1_coherent", "candidate_aligned_ms2_nl"),
        conflict_reasons=("trace_morphology_conflict",),
    )

    projection = result.targeted_product_projection
    assert projection is not None
    assert projection.product_state == "ambiguous"
    assert projection.counted_detection is False
    assert "trace_morphology_conflict" in projection.conflict_reasons


def test_paired_analyte_anchor_selected_trace_conflict_stays_counted() -> None:
    result = _result_with_targeted_projection_semantics(
        target=_target(is_istd=False),
        support_reasons=("candidate_aligned_ms2_nl",),
        conflict_reasons=("trace_morphology_conflict",),
        selection_reference_rt=8.5,
    )

    projection = result.targeted_product_projection
    assert projection is not None
    assert projection.product_state == "detected_flagged"
    assert projection.counted_detection is True
    assert "trace_morphology_conflict" not in projection.conflict_reasons
    assert "trace_morphology_review" in projection.review_reasons


def test_paired_analyte_anchor_conflict_blocks_trace_downgrade() -> None:
    result = _result_with_targeted_projection_semantics(
        target=_target(is_istd=False),
        support_reasons=("candidate_aligned_ms2_nl",),
        conflict_reasons=("anchor_conflict", "trace_morphology_conflict"),
        selection_reference_rt=8.9,
    )

    projection = result.targeted_product_projection
    assert projection is not None
    assert projection.product_state == "ambiguous"
    assert projection.counted_detection is False
    assert "anchor_conflict" in projection.conflict_reasons
    assert "trace_morphology_review" in projection.review_reasons


def test_paired_analyte_anchor_selected_nl_fail_still_requires_policy() -> None:
    result = _result_with_targeted_projection_semantics(
        target=_target(is_istd=False),
        support_reasons=(),
        conflict_reasons=("candidate_aligned_ms2_nl_conflict",),
        nl_status="NL_FAIL",
        selection_reference_rt=8.5,
    )

    projection = result.targeted_product_projection
    assert projection is not None
    assert projection.product_state == "ambiguous"
    assert projection.counted_detection is False
    assert "analyte_nl_fail_requires_policy" in projection.not_counted_reasons


def test_legacy_very_low_does_not_decide_product_not_counted() -> None:
    result = _result_with_targeted_projection_semantics(
        target=_target(is_istd=False),
        support_reasons=("ms1_coherent", "candidate_aligned_ms2_nl"),
        conflict_reasons=(),
        confidence="VERY_LOW",
        reason="decision: review only, not counted; cap: legacy score",
        not_counted_reasons=("legacy_review_only_projection",),
    )

    projection = result.targeted_product_projection
    assert projection is not None
    assert projection.counted_detection is True
    assert projection.product_state == "detected_flagged"
    assert "legacy_confidence_review" in projection.review_reasons
    assert projection.not_counted_reasons == ()


def test_analyte_no_ms2_still_requires_policy() -> None:
    result = _result_with_targeted_projection_semantics(
        target=_target(is_istd=False),
        support_reasons=("ms1_coherent",),
        conflict_reasons=(),
        nl_status="NO_MS2",
    )

    projection = result.targeted_product_projection
    assert projection is not None
    assert projection.product_state == "not_counted"
    assert projection.counted_detection is False
    assert "analyte_missing_ms2_requires_policy" in projection.not_counted_reasons


def test_istd_raw_hard_quality_flag_with_product_support_stays_counted() -> None:
    result = _result_with_targeted_projection_semantics(
        target=_target(is_istd=True),
        support_reasons=("candidate_aligned_ms2_nl", "role_aware_rt_support"),
        conflict_reasons=(),
        quality_flags=("shape_poor",),
    )

    projection = result.targeted_product_projection
    assert projection is not None
    assert projection.product_state == "detected_flagged"
    assert projection.counted_detection is True
    assert "hard_quality_flag:shape_poor" not in projection.conflict_reasons
    assert "trace_morphology_review" in projection.review_reasons


class _Config:
    resolver_mode = "region_first_safe_merge"


def _target(*, is_istd: bool = False) -> Target:
    return Target(
        label="ISTD" if is_istd else "Analyte",
        mz=258.1085,
        rt_min=8.0,
        rt_max=9.0,
        ppm_tol=20.0,
        neutral_loss_da=116.0474,
        nl_ppm_warn=20.0,
        nl_ppm_max=50.0,
        is_istd=is_istd,
        istd_pair="ISTD",
    )


def _candidate(quality_flags: tuple[str, ...] = ("too_broad",)) -> PeakCandidate:
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
        quality_flags=quality_flags,
    )


def _peak_result_with_candidate() -> PeakDetectionResult:
    candidate = _candidate()
    return PeakDetectionResult(
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


def _result_with_targeted_projection_semantics(
    *,
    target: Target,
    support_reasons: tuple[str, ...],
    conflict_reasons: tuple[str, ...],
    confidence: str = "HIGH",
    reason: str = "decision: accepted",
    not_counted_reasons: tuple[str, ...] = (),
    quality_flags: tuple[str, ...] = (),
    nl_status: str = "OK",
    selection_reference_rt: float | None = None,
) -> ExtractionResult:
    candidate = _candidate(quality_flags=())
    peak_result = PeakDetectionResult(
        status="OK",
        peak=candidate.peak,
        n_points=12,
        max_smoothed=1200.0,
        n_prominent_peaks=1,
        candidates=(candidate,),
        confidence=confidence,
        reason=reason,
        candidate_scores=(
            PeakCandidateScore(
                candidate=candidate,
                confidence=confidence,
                reason=reason,
                raw_score=95,
                support_labels=("local_sn_strong", "shape_clean"),
            ),
        ),
        selection_reference_rt=selection_reference_rt,
    )
    selected = PeakHypothesis(
        hypothesis_id=f"SampleA|{target.label}|selected",
        trace_group_id=f"SampleA|{target.label}|targeted",
        target_label=target.label,
        role="ISTD" if target.is_istd else "Analyte",
        istd_pair=target.istd_pair,
        analysis_mode="targeted",
        resolver_mode="region_first_safe_merge",
        integration=IntegrationResult(
            rt_left_min=8.4,
            rt_apex_min=8.5,
            rt_right_min=8.6,
            raw_apex_rt_min=8.5,
            rt_width_min=0.2,
            height_raw=1200.0,
            height_smoothed=1100.0,
            area_raw_counts_seconds=1234.5,
        ),
        evidence=EvidenceVector(
            confidence=confidence,
            reason=reason,
            quality_flags=quality_flags,
            decision_semantics=EvidenceDecisionSemantics(
                decision_class="ambiguous",
                support_reasons=support_reasons,
                conflict_reasons=conflict_reasons,
                not_counted_reasons=not_counted_reasons,
            ),
        ),
        audit=AuditTrail(selected=True, selection_rank=1),
    )
    return build_extraction_result(
        peak_result=peak_result,
        nl_result=NLResult(nl_status, 2.5 if nl_status == "OK" else None, 8.5, 1, 0, 1),
        candidate_ms2_evidence=(
            CandidateMS2Evidence(
                ms2_present=nl_status != "NO_MS2",
                nl_match=nl_status == "OK",
                nl_status=nl_status,
                trigger_scan_count=0 if nl_status == "NO_MS2" else 1,
                strict_nl_scan_count=1 if nl_status == "OK" else 0,
                best_loss_ppm=2.5 if nl_status == "OK" else None,
                best_scan_rt=8.5,
                best_product_base_ratio=0.8 if nl_status == "OK" else None,
                alignment_source="region",
            )
        ),
        target=target,
        candidate=candidate,
        scoring_context_builder=None,
        selected_hypothesis=selected,
    )


def _selected_hypothesis_with_integration(
    integration: IntegrationResult,
) -> PeakHypothesis:
    return PeakHypothesis(
        hypothesis_id="SampleA|Analyte|selected",
        trace_group_id="SampleA|Analyte|targeted",
        target_label="Analyte",
        role="Analyte",
        istd_pair="ISTD",
        analysis_mode="targeted",
        resolver_mode="local_minimum",
        integration=integration,
        evidence=EvidenceVector(
            confidence="LOW",
            reason="selected spine",
            decision_semantics=EvidenceDecisionSemantics(
                decision_class="review",
                review_reasons=("trace_morphology_review",),
                compatibility_labels=("trace_quality_cap",),
            ),
        ),
        audit=AuditTrail(selected=True, selection_rank=1),
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
