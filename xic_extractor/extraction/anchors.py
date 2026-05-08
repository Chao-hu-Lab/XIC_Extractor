from __future__ import annotations

from dataclasses import replace

from xic_extractor.config import Target
from xic_extractor.output.messages import DiagnosticRecord
from xic_extractor.signal_processing import PeakDetectionResult

PAIRED_TARGET_ANCHOR_PEAK_DELTA_MAX_MIN: float = 0.25
PAIRED_FALLBACK_ISTD_PEAK_DELTA_MAX_MIN: float = 0.5
ANCHOR_PEAK_DELTA_WARN_MIN: float = 0.5


def paired_anchor_mismatch_diagnostic(
    sample_name: str,
    target: Target,
    peak_result: PeakDetectionResult,
    *,
    reference_rt: float | None,
    anchor_rt: float | None,
    strict_preferred_rt: bool,
) -> DiagnosticRecord | None:
    if (
        not strict_preferred_rt
        or reference_rt is None
        or peak_result.peak is None
    ):
        return None

    peak = peak_result.peak
    if anchor_rt is not None:
        expected_rt = anchor_rt
        anchor_label = "target NL anchor"
        allowed_delta = PAIRED_TARGET_ANCHOR_PEAK_DELTA_MAX_MIN
        secondary_note = f"; ISTD anchor at {reference_rt:.3f} min"
    else:
        expected_rt = reference_rt
        anchor_label = "ISTD anchor"
        allowed_delta = PAIRED_FALLBACK_ISTD_PEAK_DELTA_MAX_MIN
        secondary_note = "; no target NL anchor"

    delta = abs(peak.rt - expected_rt)
    if delta <= allowed_delta:
        return None

    return DiagnosticRecord(
        sample_name=sample_name,
        target_label=target.label,
        issue="ANCHOR_RT_MISMATCH",
        reason=(
            f"Paired analyte peak RT {peak.rt:.3f} min deviates "
            f"{delta:.2f} min from {anchor_label} at "
            f"{expected_rt:.3f} min (allowed ±{allowed_delta:.2f} min)"
            f"{secondary_note}; retained with downgraded confidence for manual review"
        ),
    )


def apply_anchor_mismatch_penalty(
    peak_result: PeakDetectionResult,
    mismatch_reason: str,
) -> PeakDetectionResult:
    reason = (
        "decision: review only, not counted; "
        "cap: VERY_LOW due to anchor mismatch; "
        f"concerns: anchor mismatch; {mismatch_reason}"
    )
    if peak_result.reason:
        reason = f"{reason}; {peak_result.reason}"
    confidence = anchor_mismatch_confidence(peak_result.confidence)
    return replace(peak_result, confidence=confidence, reason=reason)


def anchor_mismatch_confidence(_confidence: str | None) -> str:
    return "VERY_LOW"
