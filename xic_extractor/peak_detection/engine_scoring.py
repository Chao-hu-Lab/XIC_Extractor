from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace

from xic_extractor.peak_detection.candidate_scoring import score_candidate
from xic_extractor.peak_detection.evidence_facts import (
    build_candidate_evidence_facts,
    decision_semantics_from_candidate_facts,
    projected_confidence_from_candidate_facts,
    projected_reason_from_candidate_facts,
)
from xic_extractor.peak_detection.models import PeakCandidate, PeakCandidateScore
from xic_extractor.peak_detection.scoring_models import (
    ScoredCandidate,
    ScoringContext,
    confidence_from_value,
)


def score_with_context(
    candidate: PeakCandidate,
    context: ScoringContext,
    *,
    istd_confidence_note: str | None,
    evidence_role: str = "",
    istd_pair: str = "",
    paired_istd_anchor_rt: float | None = None,
    score_candidate_func: Callable[..., ScoredCandidate] = score_candidate,
) -> ScoredCandidate:
    scored = score_candidate_func(
        candidate,
        context,
        prior_rt=context.rt_prior,
        istd_confidence_note=istd_confidence_note,
    )
    if (
        scored.evidence_facts is not None
        and not evidence_role
        and not istd_pair
        and paired_istd_anchor_rt is None
    ):
        return scored
    evidence_facts = build_candidate_evidence_facts(
        candidate,
        context,
        role=evidence_role,
        istd_pair=istd_pair,
        paired_istd_anchor_rt_min=paired_istd_anchor_rt,
    )
    semantics = decision_semantics_from_candidate_facts(
        evidence_facts,
        count_no_ms2_as_detected=context.count_no_ms2_as_detected,
    )
    reason = projected_reason_from_candidate_facts(evidence_facts, semantics)
    if istd_confidence_note:
        reason = f"{reason}; {istd_confidence_note}"
    return replace(
        scored,
        confidence=confidence_from_value(
            projected_confidence_from_candidate_facts(evidence_facts, semantics)
        ),
        reason=reason,
        evidence_facts=evidence_facts,
    )


def candidate_score_summary(scored_candidate: ScoredCandidate) -> PeakCandidateScore:
    evidence_score = scored_candidate.evidence_score
    return PeakCandidateScore(
        candidate=scored_candidate.candidate,
        confidence=scored_candidate.confidence.value,
        reason=scored_candidate.reason,
        raw_score=evidence_score.raw_score if evidence_score is not None else None,
        support_labels=(
            evidence_score.support_labels if evidence_score is not None else ()
        ),
        concern_labels=(
            evidence_score.concern_labels if evidence_score is not None else ()
        ),
        cap_labels=evidence_score.cap_labels if evidence_score is not None else (),
        prior_rt=scored_candidate.prior_rt,
        quality_penalty=scored_candidate.quality_penalty,
        selection_quality_penalty=scored_candidate.selection_quality_penalty,
        severities=scored_candidate.severities,
        evidence_facts=scored_candidate.evidence_facts,
    )
