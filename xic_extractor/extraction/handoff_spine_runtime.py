from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from typing import cast

from xic_extractor.config import ExtractionConfig, Target
from xic_extractor.extraction.ms2_selection import selected_candidate_ms2_evidence
from xic_extractor.extraction.scoring_factory import selected_candidate
from xic_extractor.extraction.trace_context import targeted_extraction_trace_group
from xic_extractor.neutral_loss import CandidateMS2Evidence
from xic_extractor.peak_detection.baseline import BaselineMethod
from xic_extractor.peak_detection.hypotheses import (
    PeakHypothesis,
    build_peak_hypotheses,
)
from xic_extractor.peak_detection.models import PeakDetectionResult
from xic_extractor.peak_detection.selection_decision import (
    PeakHypothesisSelectionDecision,
    selection_decision_from_hypothesis,
)
from xic_extractor.peak_detection.traces import TraceGroup
from xic_extractor.signal_processing import PeakCandidate


@dataclass(frozen=True)
class HandoffPeakSelection:
    candidate_ms2_evidence: CandidateMS2Evidence | None
    selected_hypothesis: PeakHypothesis | None
    selection_decision: PeakHypothesisSelectionDecision | None
    trace_group: TraceGroup | None


def build_production_peak_hypotheses(
    *,
    config: ExtractionConfig,
    sample_name: str,
    target: Target,
    peak_result: PeakDetectionResult,
    selected_candidate_ms2_evidence: CandidateMS2Evidence | None = None,
    rt: object | None = None,
    intensity: object | None = None,
    trace_group: TraceGroup | None = None,
) -> tuple[PeakHypothesis, ...]:
    candidate = selected_candidate(peak_result)
    evidence_by_candidate = (
        {candidate: selected_candidate_ms2_evidence}
        if candidate is not None and selected_candidate_ms2_evidence is not None
        else None
    )
    hypotheses = build_peak_hypotheses(
        sample_name=sample_name,
        target_label=target.label,
        role="ISTD" if target.is_istd else "Analyte",
        istd_pair=target.istd_pair,
        resolver_mode=config.resolver_mode,
        peak_result=peak_result,
        candidate_ms2_evidence=evidence_by_candidate,
        rt=rt,
        intensity=intensity,
        trace_group=trace_group,
        baseline_integration_method=cast(
            BaselineMethod,
            getattr(config, "baseline_integration_method", "asls"),
        ),
    )
    return _with_final_selected_result_evidence(hypotheses, peak_result)


def selected_peak_hypothesis(
    hypotheses: tuple[PeakHypothesis, ...],
) -> PeakHypothesis | None:
    for hypothesis in hypotheses:
        if hypothesis.audit.selected:
            return hypothesis
    return None


def selected_handoff_peak(
    *,
    config: ExtractionConfig,
    sample_name: str,
    target: Target,
    peak_result: PeakDetectionResult,
    candidate: PeakCandidate | None,
    candidate_ms2_cache: dict[PeakCandidate, CandidateMS2Evidence],
    candidate_ms2_builder: Callable[[PeakCandidate], CandidateMS2Evidence | None],
    rt: object,
    intensity: object,
    rt_min: float,
    rt_max: float,
    expected_rt_min: float | None,
) -> HandoffPeakSelection:
    trace_group = (
        targeted_extraction_trace_group(
            sample_name=sample_name,
            target=target,
            config=config,
            rt=rt,
            intensity=intensity,
            rt_min=rt_min,
            rt_max=rt_max,
            expected_rt_min=expected_rt_min,
        )
        if config.emit_peak_candidates
        else None
    )
    candidate_ms2_evidence = selected_candidate_ms2_evidence(
        candidate,
        candidate_ms2_cache,
        candidate_ms2_builder,
    )
    hypotheses = build_production_peak_hypotheses(
        config=config,
        sample_name=sample_name,
        target=target,
        peak_result=peak_result,
        selected_candidate_ms2_evidence=candidate_ms2_evidence,
        rt=rt,
        intensity=intensity,
        trace_group=trace_group,
    )
    selected_hypothesis = selected_peak_hypothesis(hypotheses)
    return HandoffPeakSelection(
        candidate_ms2_evidence=candidate_ms2_evidence,
        selected_hypothesis=selected_hypothesis,
        selection_decision=(
            selection_decision_from_hypothesis(
                selected_hypothesis,
                peak_result=peak_result,
            )
            if selected_hypothesis is not None
            else None
        ),
        trace_group=trace_group,
    )


def _with_final_selected_result_evidence(
    hypotheses: tuple[PeakHypothesis, ...],
    peak_result: PeakDetectionResult,
) -> tuple[PeakHypothesis, ...]:
    if peak_result.confidence is None and not peak_result.reason:
        return hypotheses
    updated: list[PeakHypothesis] = []
    for hypothesis in hypotheses:
        if not hypothesis.audit.selected:
            updated.append(hypothesis)
            continue
        updated.append(
            replace(
                hypothesis,
                evidence=replace(
                    hypothesis.evidence,
                    confidence=peak_result.confidence
                    or hypothesis.evidence.confidence,
                    reason=peak_result.reason or hypothesis.evidence.reason,
                ),
            )
        )
    return tuple(updated)
