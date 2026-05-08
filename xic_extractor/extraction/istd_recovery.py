from __future__ import annotations

from collections.abc import Callable
from typing import Any

from xic_extractor.config import ExtractionConfig, Target
from xic_extractor.extraction.rt_windows import (
    recover_istd_peak_with_wider_anchor_window,
)
from xic_extractor.extraction.scoring_factory import selected_candidate
from xic_extractor.neutral_loss import CandidateMS2Evidence, NLResult
from xic_extractor.peak_scoring import (
    candidate_quality_penalty,
    candidate_selection_quality_penalty,
)
from xic_extractor.signal_processing import PeakCandidate, PeakDetectionResult

_ISTD_WIDER_RECOVERY_MIN_INTENSITY_RATIO = 2.0


def recover_istd_anchor_peak_if_needed(
    peak_result: PeakDetectionResult,
    *,
    raw: Any,
    config: ExtractionConfig,
    target: Target,
    anchor_used: bool,
    anchor_rt: float | None,
    scoring_context_factory: Callable[..., Any] | None,
    candidate_ms2_evidence_builder: Callable[
        [PeakCandidate], CandidateMS2Evidence | None
    ],
    sample_name: str,
    nl_result: NLResult | None,
    istd_confidence_note: str | None,
    istd_rt_in_this_sample: float | None,
    paired_istd_fwhm: float | None,
    peak_finder: Callable[..., PeakDetectionResult],
) -> PeakDetectionResult:
    if not target.is_istd or not anchor_used or anchor_rt is None:
        return peak_result

    if peak_result.status == "PEAK_NOT_FOUND" and peak_result.peak is None:
        recovered = _recover(
            raw=raw,
            config=config,
            target=target,
            anchor_rt=anchor_rt,
            scoring_context_factory=scoring_context_factory,
            candidate_ms2_evidence_builder=candidate_ms2_evidence_builder,
            sample_name=sample_name,
            nl_result=nl_result,
            istd_confidence_note=istd_confidence_note,
            istd_rt_in_this_sample=istd_rt_in_this_sample,
            paired_istd_fwhm=paired_istd_fwhm,
            peak_finder=peak_finder,
        )
        return recovered or peak_result

    if not _should_try_wider_istd_anchor_recovery(peak_result):
        return peak_result
    recovered = _recover(
        raw=raw,
        config=config,
        target=target,
        anchor_rt=anchor_rt,
        scoring_context_factory=scoring_context_factory,
        candidate_ms2_evidence_builder=candidate_ms2_evidence_builder,
        sample_name=sample_name,
        nl_result=nl_result,
        istd_confidence_note=istd_confidence_note,
        istd_rt_in_this_sample=istd_rt_in_this_sample,
        paired_istd_fwhm=paired_istd_fwhm,
        peak_finder=peak_finder,
    )
    if recovered is not None and _should_use_wider_istd_recovery(
        peak_result, recovered
    ):
        return recovered
    return peak_result


def _recover(
    *,
    raw: Any,
    config: ExtractionConfig,
    target: Target,
    anchor_rt: float,
    scoring_context_factory: Callable[..., Any] | None,
    candidate_ms2_evidence_builder: Callable[
        [PeakCandidate], CandidateMS2Evidence | None
    ],
    sample_name: str,
    nl_result: NLResult | None,
    istd_confidence_note: str | None,
    istd_rt_in_this_sample: float | None,
    paired_istd_fwhm: float | None,
    peak_finder: Callable[..., PeakDetectionResult],
) -> PeakDetectionResult | None:
    return recover_istd_peak_with_wider_anchor_window(
        raw,
        config,
        target,
        anchor_rt=anchor_rt,
        scoring_context_factory=scoring_context_factory,
        candidate_ms2_evidence_builder=candidate_ms2_evidence_builder,
        sample_name=sample_name,
        nl_result=nl_result,
        istd_confidence_note=istd_confidence_note,
        istd_rt_in_this_sample=istd_rt_in_this_sample,
        paired_istd_fwhm=paired_istd_fwhm,
        peak_finder=peak_finder,
    )


def _should_try_wider_istd_anchor_recovery(
    peak_result: PeakDetectionResult,
) -> bool:
    if peak_result.peak is None:
        return False
    candidate = selected_candidate(peak_result)
    if candidate is None:
        return False
    return bool(getattr(candidate, "quality_flags", ()))


def _should_use_wider_istd_recovery(
    current: PeakDetectionResult,
    recovered: PeakDetectionResult,
) -> bool:
    if recovered.peak is None:
        return False
    if current.peak is None:
        return True

    current_candidate = selected_candidate(current)
    recovered_candidate = selected_candidate(recovered)
    if current_candidate is None or recovered_candidate is None:
        return False

    current_penalty = _selection_penalty(current_candidate)
    recovered_penalty = _selection_penalty(recovered_candidate)
    if recovered_penalty >= current_penalty:
        return False

    return recovered_candidate.selection_apex_intensity >= (
        current_candidate.selection_apex_intensity
        * _ISTD_WIDER_RECOVERY_MIN_INTENSITY_RATIO
    )


def _selection_penalty(candidate: PeakCandidate) -> float:
    quality_penalty, _ = candidate_quality_penalty(candidate)
    return quality_penalty + candidate_selection_quality_penalty(candidate)
