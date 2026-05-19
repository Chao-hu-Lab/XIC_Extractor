from __future__ import annotations

from typing import TYPE_CHECKING, Any

from xic_extractor.config import Target
from xic_extractor.neutral_loss import CandidateMS2Evidence, NLResult
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
        target_label=target.label,
        role="ISTD" if target.is_istd else "Analyte",
        istd_pair=target.istd_pair,
        confidence=(
            peak_result.confidence or "HIGH"
            if peak_result.peak is not None
            else ""
        ),
        reason=peak_result.reason or "",
        severities=peak_result.severities,
        prior_rt=getattr(scoring_context_builder, "rt_prior", None),
        prior_source=getattr(scoring_context_builder, "prior_source", ""),
        quality_penalty=quality_penalty,
        quality_flags=quality_flags,
        score_breakdown=peak_result.score_breakdown,
    )
