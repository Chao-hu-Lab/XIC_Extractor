from __future__ import annotations

import math
from dataclasses import replace
from typing import TYPE_CHECKING, Any

from xic_extractor.config import Target
from xic_extractor.evidence_semantics import EvidenceDecisionSemantics
from xic_extractor.neutral_loss import CandidateMS2Evidence, NLResult
from xic_extractor.peak_detection.hypotheses import PeakHypothesis
from xic_extractor.peak_detection.model_selection import PeakModelSelectionResult
from xic_extractor.peak_detection.selection_decision import (
    PeakHypothesisSelectionDecision,
    selection_decision_from_hypothesis,
)
from xic_extractor.peak_detection.targeted_product_projection import (
    TargetedPriorContext,
    TargetedProductProjection,
    build_targeted_product_projection,
)
from xic_extractor.peak_scoring import candidate_quality_penalty, hard_quality_flags
from xic_extractor.signal_processing import PeakCandidate, PeakDetectionResult

if TYPE_CHECKING:
    from xic_extractor.extractor import ExtractionResult


def build_extraction_result(
    *,
    peak_result: PeakDetectionResult,
    nl_result: NLResult | None,
    candidate_ms2_evidence: CandidateMS2Evidence | None,
    target: Target,
    candidate: PeakCandidate | None,
    scoring_context_builder: Any | None,
    selected_hypothesis: PeakHypothesis | None = None,
    selection_decision: PeakHypothesisSelectionDecision | None = None,
    model_selection_result: PeakModelSelectionResult | None = None,
) -> ExtractionResult:
    from xic_extractor import extractor

    resolved_selection_decision = _result_selection_decision(
        peak_result,
        selected_hypothesis,
        selection_decision,
    )
    quality_penalty = 0
    quality_flags: tuple[str, ...] = ()
    if candidate is not None:
        quality_penalty, _ = candidate_quality_penalty(candidate)
        quality_flags = tuple(
            str(flag) for flag in getattr(candidate, "quality_flags", ())
        )

    result = extractor.ExtractionResult(
        peak_result=peak_result,
        nl=nl_result,
        candidate_ms2_evidence=candidate_ms2_evidence,
        target_label=_result_target_label(target, selected_hypothesis),
        role=_result_role(target, selected_hypothesis),
        istd_pair=_result_istd_pair(target, selected_hypothesis),
        confidence=_result_confidence(peak_result, resolved_selection_decision),
        reason=_result_reason(peak_result, resolved_selection_decision),
        severities=peak_result.severities,
        prior_rt=getattr(scoring_context_builder, "rt_prior", None),
        prior_source=getattr(scoring_context_builder, "prior_source", ""),
        quality_penalty=quality_penalty,
        quality_flags=_result_quality_flags(quality_flags, selected_hypothesis),
        score_breakdown=peak_result.score_breakdown,
        selected_hypothesis=selected_hypothesis,
        selection_decision=resolved_selection_decision,
        model_selection_result=model_selection_result,
    )
    return replace(
        result,
        targeted_product_projection=_targeted_product_projection(
            result,
            target=target,
        ),
    )


def _result_target_label(
    target: Target,
    selected_hypothesis: PeakHypothesis | None,
) -> str:
    if selected_hypothesis is not None:
        return selected_hypothesis.target_label
    return target.label


def _result_role(
    target: Target,
    selected_hypothesis: PeakHypothesis | None,
) -> str:
    if selected_hypothesis is not None:
        return selected_hypothesis.role
    return "ISTD" if target.is_istd else "Analyte"


def _result_istd_pair(
    target: Target,
    selected_hypothesis: PeakHypothesis | None,
) -> str:
    if selected_hypothesis is not None:
        return selected_hypothesis.istd_pair
    return target.istd_pair


def _result_selection_decision(
    peak_result: PeakDetectionResult,
    selected_hypothesis: PeakHypothesis | None,
    selection_decision: PeakHypothesisSelectionDecision | None,
) -> PeakHypothesisSelectionDecision | None:
    if selection_decision is not None:
        return selection_decision
    if selected_hypothesis is None:
        return None
    return selection_decision_from_hypothesis(
        selected_hypothesis,
        peak_result=peak_result,
    )


def _result_confidence(
    peak_result: PeakDetectionResult,
    selection_decision: PeakHypothesisSelectionDecision | None,
) -> str:
    if selection_decision is not None:
        return selection_decision.projected_confidence
    if peak_result.peak is None:
        return ""
    return peak_result.confidence or "HIGH"


def _result_reason(
    peak_result: PeakDetectionResult,
    selection_decision: PeakHypothesisSelectionDecision | None,
) -> str:
    if selection_decision is not None:
        return selection_decision.projected_reason
    return peak_result.reason or ""


def _result_quality_flags(
    quality_flags: tuple[str, ...],
    selected_hypothesis: PeakHypothesis | None,
) -> tuple[str, ...]:
    if selected_hypothesis is not None:
        return selected_hypothesis.evidence.quality_flags
    return quality_flags


def _targeted_product_projection(
    result: ExtractionResult,
    *,
    target: Target,
) -> TargetedProductProjection:
    semantics = (
        result.selected_hypothesis.evidence.decision_semantics
        if result.selected_hypothesis is not None
        else None
    )
    support = _projection_support_reasons(result, semantics)
    conflicts = _projection_conflict_reasons(result, semantics, target=target)
    review = _projection_review_reasons(
        result,
        semantics,
        conflicts,
        target=target,
    )
    not_counted = _projection_not_counted_reasons(
        result,
        semantics,
        review,
        conflicts,
    )
    nl_status = result.nl_token or ""
    return build_targeted_product_projection(
        TargetedPriorContext(
            role=result.role or ("ISTD" if target.is_istd else "Analyte"),
            expected_present=target.is_istd,
            target_label=result.target_label or target.label,
            istd_pair=result.istd_pair or target.istd_pair,
        ),
        rt=result.reported_rt,
        area=result.reported_peak_area,
        confidence=result.confidence,
        nl_status=nl_status,
        support_reasons=support,
        review_reasons=review,
        conflict_reasons=conflicts,
        not_counted_reasons=not_counted,
        legacy_evidence={
            "confidence": result.confidence,
            "nl_status": nl_status,
            "reason": result.reason,
        },
    )


def _projection_support_reasons(
    result: ExtractionResult,
    semantics: EvidenceDecisionSemantics | None,
) -> tuple[str, ...]:
    reasons: list[str] = []
    if _positive(result.reported_rt) and _positive(result.reported_peak_area):
        reasons.append("ms1_peak_present")
    if semantics is not None:
        reasons.extend(semantics.support_reasons)
    if not hard_quality_flags(result.quality_flags):
        reasons.append("trace_coherent")
    return _unique(reasons)


def _projection_conflict_reasons(
    result: ExtractionResult,
    semantics: EvidenceDecisionSemantics | None,
    *,
    target: Target,
) -> tuple[str, ...]:
    reasons: list[str] = []
    support_reasons = semantics.support_reasons if semantics is not None else ()
    if semantics is not None:
        reasons.extend(
            reason
            for reason in semantics.conflict_reasons
            if not _downgrade_nl_conflict_to_istd_review(result, reason)
            and not _downgrade_rt_conflict_to_istd_review(
                result,
                target,
                reason,
                support_reasons,
            )
            and not _downgrade_trace_conflict_to_istd_review(
                result,
                target,
                reason,
                support_reasons,
            )
            and not _downgrade_trace_conflict_to_paired_analyte_review(
                result,
                target,
                reason,
                support_reasons,
            )
        )
        reasons.extend(semantics.ambiguity_reasons)
    for flag in hard_quality_flags(result.quality_flags):
        if not _downgrade_quality_flag_to_review(
            result,
            target,
            support_reasons,
        ):
            reasons.append(f"hard_quality_flag:{flag}")
    return _unique(reasons)


def _downgrade_nl_conflict_to_istd_review(
    result: ExtractionResult,
    reason: str,
) -> bool:
    return (
        reason == "candidate_aligned_ms2_nl_conflict"
        and result.role.upper() == "ISTD"
        and result.nl_token == "NL_FAIL"
        and result.candidate_ms2_evidence is not None
        and result.candidate_ms2_evidence.strict_nl_scan_count == 0
        and _positive(result.reported_rt)
        and _positive(result.reported_peak_area)
    )


def _downgrade_rt_conflict_to_istd_review(
    result: ExtractionResult,
    target: Target,
    reason: str,
    support_reasons: tuple[str, ...],
) -> bool:
    return (
        reason == "targeted_rt_conflict"
        and result.role.upper() == "ISTD"
        and _positive(result.reported_rt)
        and _positive(result.reported_peak_area)
        and _rt_inside_target_window(result.reported_rt, target)
        and "candidate_aligned_ms2_nl" in support_reasons
    )


def _downgrade_trace_conflict_to_istd_review(
    result: ExtractionResult,
    target: Target,
    reason: str,
    support_reasons: tuple[str, ...],
) -> bool:
    return (
        reason in {"trace_morphology_conflict", "hard_local_quality_conflict"}
        and result.role.upper() == "ISTD"
        and _positive(result.reported_rt)
        and _positive(result.reported_peak_area)
        and "candidate_aligned_ms2_nl" in support_reasons
        and (
            "role_aware_rt_support" in support_reasons
            or _rt_inside_target_window(result.reported_rt, target)
        )
    )


def _downgrade_trace_conflict_to_paired_analyte_review(
    result: ExtractionResult,
    target: Target,
    reason: str,
    support_reasons: tuple[str, ...],
) -> bool:
    return (
        reason
        in {
            "trace_morphology_conflict",
            "hard_local_quality_conflict",
            "hard_quality_flag_conflict",
        }
        and _paired_analyte_has_product_supported_peak(
            result,
            target,
            support_reasons,
        )
    )


def _downgrade_quality_flag_to_review(
    result: ExtractionResult,
    target: Target,
    support_reasons: tuple[str, ...],
) -> bool:
    return _istd_has_product_supported_peak(
        result,
        target,
        support_reasons,
    ) or _paired_analyte_has_product_supported_peak(
        result,
        target,
        support_reasons,
    )


def _istd_has_product_supported_peak(
    result: ExtractionResult,
    target: Target,
    support_reasons: tuple[str, ...],
) -> bool:
    return (
        result.role.upper() == "ISTD"
        and _positive(result.reported_rt)
        and _positive(result.reported_peak_area)
        and "candidate_aligned_ms2_nl" in support_reasons
        and (
            "role_aware_rt_support" in support_reasons
            or _rt_inside_target_window(result.reported_rt, target)
        )
    )


def _paired_analyte_has_product_supported_peak(
    result: ExtractionResult,
    target: Target,
    support_reasons: tuple[str, ...],
) -> bool:
    return (
        result.role.upper() == "ANALYTE"
        and bool(target.istd_pair)
        and result.confidence.upper() != "VERY_LOW"
        and _positive(result.reported_rt)
        and _positive(result.reported_peak_area)
        and _rt_inside_target_window(result.reported_rt, target)
        and result.peak_result.selection_reference_rt is not None
        and "candidate_aligned_ms2_nl" in support_reasons
    )


def _projection_review_reasons(
    result: ExtractionResult,
    semantics: EvidenceDecisionSemantics | None,
    conflict_reasons: tuple[str, ...],
    *,
    target: Target,
) -> tuple[str, ...]:
    reasons: list[str] = []
    if semantics is not None:
        reasons.extend(semantics.review_reasons)
        if "plausible_nl_dropout_review" in semantics.review_reasons:
            reasons.append("plausible_dda_nl_dropout")
        if any(
            _downgrade_trace_conflict_to_istd_review(
                result,
                target,
                reason,
                semantics.support_reasons,
            )
            or _downgrade_trace_conflict_to_paired_analyte_review(
                result,
                target,
                reason,
                semantics.support_reasons,
            )
            for reason in semantics.conflict_reasons
        ):
            reasons.append("trace_morphology_review")
        has_raw_hard_flags = hard_quality_flags(result.quality_flags)
        if has_raw_hard_flags and _downgrade_quality_flag_to_review(
            result, target, semantics.support_reasons
        ):
            reasons.append("trace_morphology_review")
    if (
        result.role.upper() == "ISTD"
        and result.nl_token == "NL_FAIL"
        and not conflict_reasons
        and result.candidate_ms2_evidence is not None
        and result.candidate_ms2_evidence.strict_nl_scan_count == 0
    ):
        reasons.append("plausible_dda_nl_dropout")
    if result.confidence.upper() == "VERY_LOW" and not conflict_reasons:
        reasons.append("legacy_confidence_review")
    return _unique(reasons)


def _projection_not_counted_reasons(
    result: ExtractionResult,
    semantics: EvidenceDecisionSemantics | None,
    review_reasons: tuple[str, ...],
    conflict_reasons: tuple[str, ...],
) -> tuple[str, ...]:
    reasons: list[str] = []
    if semantics is not None:
        reasons.extend(_typed_not_counted_reasons(semantics.not_counted_reasons))
    nl_failed = result.nl_token == "NL_FAIL"
    no_ms2 = result.nl_token == "NO_MS2"
    if nl_failed and result.role.upper() != "ISTD":
        reasons.append("analyte_nl_fail_requires_policy")
    if no_ms2 and result.role.upper() != "ISTD":
        reasons.append("analyte_missing_ms2_requires_policy")
    if nl_failed and result.role.upper() == "ISTD" and not (
        "plausible_dda_nl_dropout" in review_reasons
        and not conflict_reasons
    ):
        reasons.append("istd_nl_fail_without_dropout_support")
    return _unique(reasons)


def _typed_not_counted_reasons(reasons: tuple[str, ...]) -> tuple[str, ...]:
    legacy_compatibility_reasons = {
        "legacy_review_only_projection",
        "missing_ms2_compatibility_cap",
        "zero_area_compatibility_cap",
        "hard_quality_flag_compatibility_cap",
    }
    return tuple(
        reason for reason in reasons if reason not in legacy_compatibility_reasons
    )


def _positive(value: float | None) -> bool:
    return value is not None and math.isfinite(value) and value > 0


def _rt_inside_target_window(rt: float | None, target: Target) -> bool:
    return rt is not None and target.rt_min <= rt <= target.rt_max


def _unique(reasons: list[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(reason for reason in reasons if reason))
