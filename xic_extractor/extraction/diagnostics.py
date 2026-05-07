from __future__ import annotations

from collections.abc import Callable
from typing import Any

from xic_extractor.config import ExtractionConfig, Target
from xic_extractor.extraction.anchors import ANCHOR_PEAK_DELTA_WARN_MIN
from xic_extractor.neutral_loss import NLResult
from xic_extractor.output.messages import DiagnosticRecord
from xic_extractor.signal_processing import PeakCandidate, PeakDetectionResult


def check_target_nl(
    raw: Any,
    target: Target,
    config: ExtractionConfig,
) -> NLResult | None:
    """NL quality uses the original target window for full matched scan counts."""
    from xic_extractor import extractor

    if target.neutral_loss_da is None:
        return None
    if target.nl_ppm_warn is None or target.nl_ppm_max is None:
        return None
    return extractor.check_nl(
        raw,
        precursor_mz=target.mz,
        rt_min=target.rt_min,
        rt_max=target.rt_max,
        neutral_loss_da=target.neutral_loss_da,
        nl_ppm_warn=target.nl_ppm_warn,
        nl_ppm_max=target.nl_ppm_max,
        ms2_precursor_tol_da=config.ms2_precursor_tol_da,
        nl_min_intensity_ratio=config.nl_min_intensity_ratio,
    )


def candidate_ms2_evidence_builder(
    raw: Any,
    target: Target,
    config: ExtractionConfig,
) -> Callable[[PeakCandidate], Any] | None:
    from xic_extractor import extractor

    if target.neutral_loss_da is None:
        return None
    if target.nl_ppm_warn is None or target.nl_ppm_max is None:
        return None
    neutral_loss_da = target.neutral_loss_da
    nl_ppm_warn = target.nl_ppm_warn
    nl_ppm_max = target.nl_ppm_max

    def _builder(candidate: PeakCandidate) -> Any:
        return extractor.collect_candidate_ms2_evidence(
            raw,
            candidate=candidate,
            precursor_mz=target.mz,
            neutral_loss_da=neutral_loss_da,
            nl_ppm_warn=nl_ppm_warn,
            nl_ppm_max=nl_ppm_max,
            ms2_precursor_tol_da=config.ms2_precursor_tol_da,
            nl_min_intensity_ratio=config.nl_min_intensity_ratio,
        )

    return _builder


def anchor_rt_mismatch_diagnostic(
    sample_name: str,
    target: Target,
    peak_result: PeakDetectionResult,
    *,
    anchor_rt: float | None,
    paired_rejection: DiagnosticRecord | None,
) -> DiagnosticRecord | None:
    if (
        paired_rejection is not None
        or anchor_rt is None
        or peak_result.peak is None
    ):
        return None
    delta = abs(peak_result.peak.rt - anchor_rt)
    if delta <= ANCHOR_PEAK_DELTA_WARN_MIN:
        return None
    return DiagnosticRecord(
        sample_name=sample_name,
        target_label=target.label,
        issue="ANCHOR_RT_MISMATCH",
        reason=(
            f"Peak RT {peak_result.peak.rt:.3f} min deviates "
            f"{delta:.2f} min "
            f"from NL anchor at {anchor_rt:.3f} min "
            f"(threshold {ANCHOR_PEAK_DELTA_WARN_MIN} min); "
            f"anchor scan may be noise — verify manually"
        ),
    )


def nl_anchor_fallback_diagnostic(
    sample_name: str,
    target: Target,
    config: ExtractionConfig,
    *,
    anchor_used: bool,
    rt_min: float,
    rt_max: float,
    nl_result: NLResult | None,
) -> DiagnosticRecord | None:
    if anchor_used or target.neutral_loss_da is None:
        return None
    rt_center = (target.rt_min + target.rt_max) / 2.0
    nl_note = ""
    if nl_result is not None and nl_result.status in {"NL_FAIL", "NO_MS2"}:
        nl_note = f"; NL check also {nl_result.status} within fallback window"
    return DiagnosticRecord(
        sample_name=sample_name,
        target_label=target.label,
        issue="NL_ANCHOR_FALLBACK",
        reason=(
            f"No NL-confirmed MS2 within RT center "
            f"{rt_center:.2f} ± {config.nl_rt_anchor_search_margin_min} min; "
            f"fallback window [{rt_min:.2f}, {rt_max:.2f}]{nl_note}"
        ),
    )
