from __future__ import annotations

from typing import TYPE_CHECKING, Any

from xic_extractor.config import Target
from xic_extractor.neutral_loss import CandidateMS2Evidence, NLResult
from xic_extractor.peak_detection.hypotheses import PeakHypothesis
from xic_extractor.peak_scoring import candidate_quality_penalty
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
) -> ExtractionResult:
    from xic_extractor import extractor

    quality_penalty = 0
    quality_flags: tuple[str, ...] = ()
    if candidate is not None:
        quality_penalty, _ = candidate_quality_penalty(candidate)
        quality_flags = tuple(
            str(flag) for flag in getattr(candidate, "quality_flags", ())
        )

    return extractor.ExtractionResult(
        peak_result=peak_result,
        nl=nl_result,
        candidate_ms2_evidence=candidate_ms2_evidence,
        target_label=_result_target_label(target, selected_hypothesis),
        role=_result_role(target, selected_hypothesis),
        istd_pair=_result_istd_pair(target, selected_hypothesis),
        confidence=_result_confidence(peak_result, selected_hypothesis),
        reason=_result_reason(peak_result, selected_hypothesis),
        severities=peak_result.severities,
        prior_rt=getattr(scoring_context_builder, "rt_prior", None),
        prior_source=getattr(scoring_context_builder, "prior_source", ""),
        quality_penalty=quality_penalty,
        quality_flags=_result_quality_flags(quality_flags, selected_hypothesis),
        score_breakdown=peak_result.score_breakdown,
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


def _result_confidence(
    peak_result: PeakDetectionResult,
    selected_hypothesis: PeakHypothesis | None,
) -> str:
    if selected_hypothesis is not None and selected_hypothesis.evidence.confidence:
        return selected_hypothesis.evidence.confidence
    if peak_result.peak is None:
        return ""
    return peak_result.confidence or "HIGH"


def _result_reason(
    peak_result: PeakDetectionResult,
    selected_hypothesis: PeakHypothesis | None,
) -> str:
    if selected_hypothesis is not None and selected_hypothesis.evidence.reason:
        return selected_hypothesis.evidence.reason
    return peak_result.reason or ""


def _result_quality_flags(
    quality_flags: tuple[str, ...],
    selected_hypothesis: PeakHypothesis | None,
) -> tuple[str, ...]:
    if selected_hypothesis is not None:
        return selected_hypothesis.evidence.quality_flags
    return quality_flags
