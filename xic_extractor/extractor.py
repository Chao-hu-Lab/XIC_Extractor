from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path
from statistics import median
from typing import Any

from xic_extractor import raw_reader
from xic_extractor.config import ExtractionConfig, Target
from xic_extractor.extraction.scoring_factory import selected_candidate
from xic_extractor.injection_rolling import read_injection_order
from xic_extractor.neutral_loss import (
    CandidateMS2Evidence,
    NLResult,
    check_nl,
    collect_candidate_ms2_evidence,
    find_nl_anchor_rt,
)
from xic_extractor.output.messages import (
    DiagnosticIssue,
    DiagnosticRecord,
)
from xic_extractor.rt_prior_library import LibraryEntry, load_library
from xic_extractor.signal_processing import (
    PeakCandidate,
    PeakDetectionResult,
    PeakResult,
    find_peak_and_area,
)

open_raw = raw_reader.open_raw

__all__ = [
    "DiagnosticIssue",
    "DiagnosticRecord",
    "ExtractionResult",
    "FileResult",
    "RunOutput",
    "run",
]

# paired analyte 有自己的 NL anchor 時，以 target anchor 作為最直接的證據。
_PAIRED_TARGET_ANCHOR_PEAK_DELTA_MAX_MIN: float = 0.25
# target anchor 缺失時才退回 ISTD anchor，門檻較寬但仍擋掉明顯旁峰。
_PAIRED_FALLBACK_ISTD_PEAK_DELTA_MAX_MIN: float = 0.5
# 非 paired/非拒絕情境下，選出的峰 RT 距 NL anchor 超過此距離時發出警告。
_ANCHOR_PEAK_DELTA_WARN_MIN: float = 0.5


@dataclass(frozen=True)
class ExtractionResult:
    peak_result: PeakDetectionResult
    nl: NLResult | None
    candidate_ms2_evidence: CandidateMS2Evidence | None = None
    target_label: str = ""
    role: str = ""
    istd_pair: str = ""
    confidence: str = ""
    reason: str = ""
    severities: tuple[tuple[int, str], ...] = ()
    prior_rt: float | None = None
    prior_source: str = ""
    quality_penalty: int = 0
    quality_flags: tuple[str, ...] = ()

    @property
    def peak(self) -> PeakResult | None:
        return self.peak_result.peak

    @property
    def nl_result(self) -> NLResult | None:
        return self.nl

    @property
    def nl_token(self) -> str | None:
        if self.candidate_ms2_evidence is not None:
            return self.candidate_ms2_evidence.to_token()
        if self.nl is not None:
            return self.nl.to_token()
        return None

    @property
    def total_severity(self) -> int:
        return sum(severity for severity, _ in self.severities) + self.quality_penalty

    @property
    def reported_rt(self) -> float | None:
        """User-facing RT uses the selected candidate apex when available."""
        candidate = selected_candidate(self.peak_result)
        if candidate is not None:
            return candidate.selection_apex_rt
        peak = self.peak
        if peak is None:
            return None
        return peak.rt


@dataclass
class FileResult:
    sample_name: str
    results: dict[str, ExtractionResult]
    group: str | None = None
    error: str | None = None

    @property
    def extraction_results(self) -> list[ExtractionResult]:
        return list(self.results.values())


@dataclass
class RunOutput:
    file_results: list[FileResult]
    diagnostics: list[DiagnosticRecord]


@dataclass
class RawFileExtractionResult:
    raw_index: int
    sample_name: str
    file_result: FileResult
    diagnostics: list[DiagnosticRecord]


def run(
    config: ExtractionConfig,
    targets: list[Target],
    progress_callback: Callable[[int, int, str], None] | None = None,
    should_stop: Callable[[], bool] | None = None,
    injection_order: dict[str, int] | None = None,
    rt_prior_library: dict[tuple[str, str], LibraryEntry] | None = None,
) -> RunOutput:
    from xic_extractor.extraction.pipeline import run_pipeline

    return run_pipeline(
        config,
        targets,
        progress_callback=progress_callback,
        should_stop=should_stop,
        injection_order=injection_order,
        rt_prior_library=rt_prior_library,
    )


def _get_rt_window(
    raw: Any,
    target: Target,
    config: ExtractionConfig,
    *,
    reference_rt: float | None,
    sample_drift: float = 0.0,
) -> tuple[float, float, bool, float | None]:
    """回傳 (rt_min, rt_max, anchor_used, anchor_rt)。

    reference_rt 控制 anchor 選擇邏輯（見 find_nl_anchor_rt）：
    - None → 選最高 base_peak（ISTD 及無 ISTD pair 的 analyte）
    - float → 選最靠近 reference_rt 的 scan
      （有 ISTD pair 的 analyte，傳 ISTD anchor_rt）

    sample_drift 是從本樣本所有成功 ISTD 估計的整體 RT 偏移量，用於校正 anchor
    搜尋中心與 fallback 窗口中心，讓兩者跟著樣本實際 RT 移動。
    """
    if target.neutral_loss_da is None or target.nl_ppm_max is None:
        return target.rt_min, target.rt_max, False, None

    rt_center = (target.rt_min + target.rt_max) / 2.0 + sample_drift
    anchor_rt = find_nl_anchor_rt(
        raw,
        precursor_mz=target.mz,
        rt_center=rt_center,
        search_margin_min=config.nl_rt_anchor_search_margin_min,
        neutral_loss_da=target.neutral_loss_da,
        nl_ppm_max=target.nl_ppm_max,
        ms2_precursor_tol_da=config.ms2_precursor_tol_da,
        nl_min_intensity_ratio=config.nl_min_intensity_ratio,
        reference_rt=reference_rt,
    )
    if (
        target.is_istd
        and reference_rt is None
        and anchor_rt is not None
        and abs(anchor_rt - rt_center) > config.nl_rt_anchor_half_window_min
    ):
        centered_anchor_rt = find_nl_anchor_rt(
            raw,
            precursor_mz=target.mz,
            rt_center=rt_center,
            search_margin_min=config.nl_rt_anchor_search_margin_min,
            neutral_loss_da=target.neutral_loss_da,
            nl_ppm_max=target.nl_ppm_max,
            ms2_precursor_tol_da=config.ms2_precursor_tol_da,
            nl_min_intensity_ratio=config.nl_min_intensity_ratio,
            reference_rt=rt_center,
        )
        if (
            centered_anchor_rt is not None
            and abs(centered_anchor_rt - rt_center) < abs(anchor_rt - rt_center)
        ):
            anchor_rt = centered_anchor_rt

    if anchor_rt is not None:
        half = config.nl_rt_anchor_half_window_min
        return max(0.0, anchor_rt - half), anchor_rt + half, True, anchor_rt

    half = config.nl_fallback_half_window_min
    return max(0.0, rt_center - half), rt_center + half, False, None


def _recover_istd_peak_with_wider_anchor_window(
    raw: Any,
    config: ExtractionConfig,
    target: Target,
    *,
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
) -> PeakDetectionResult | None:
    wider_half_window = max(
        config.nl_fallback_half_window_min,
        config.nl_rt_anchor_half_window_min,
    )
    if wider_half_window <= config.nl_rt_anchor_half_window_min:
        return None

    rt_min = max(0.0, anchor_rt - wider_half_window)
    rt_max = anchor_rt + wider_half_window
    rt, intensity = raw.extract_xic(target.mz, rt_min, rt_max, target.ppm_tol)
    scoring_context_builder = None
    if scoring_context_factory is not None:
        scoring_context_builder = scoring_context_factory(
            target=target,
            sample_name=sample_name,
            rt=rt,
            intensity=intensity,
            istd_rt_in_this_sample=istd_rt_in_this_sample,
            paired_istd_fwhm=paired_istd_fwhm,
            nl_result=nl_result,
            candidate_ms2_evidence_builder=candidate_ms2_evidence_builder,
        )
    if scoring_context_builder is not None:
        peak_result = find_peak_and_area(
            rt,
            intensity,
            config,
            preferred_rt=anchor_rt,
            strict_preferred_rt=False,
            scoring_context_builder=scoring_context_builder,
            istd_confidence_note=istd_confidence_note,
        )
    else:
        peak_result = find_peak_and_area(
            rt,
            intensity,
            config,
            preferred_rt=anchor_rt,
            strict_preferred_rt=False,
        )
    if peak_result.peak is None:
        return None
    return peak_result


def _estimate_sample_drift(
    targets: list[Target], istd_anchor_rts: dict[str, float]
) -> float:
    """從本樣本成功定位的 ISTD anchor RT 估計整體 RT 偏移量。

    每個 ISTD 的偏移 = anchor_rt − configured_rt_center。
    取中位數作為 sample-level 估計，用於校正無 ISTD pair analyte 的搜尋中心。
    若無任何 ISTD anchor 可用，回傳 0.0（不校正）。
    """
    deltas: list[float] = []
    for target in targets:
        if not target.is_istd:
            continue
        anchor_rt = istd_anchor_rts.get(target.label)
        if anchor_rt is None:
            continue
        rt_center = (target.rt_min + target.rt_max) / 2.0
        deltas.append(anchor_rt - rt_center)
    return median(deltas) if deltas else 0.0


def _check_target_nl(
    raw: Any,
    target: Target,
    config: ExtractionConfig,
) -> NLResult | None:
    """NL 品質評估用 target 原始窗口，確保 matched_scan_count 完整。"""
    if target.neutral_loss_da is None:
        return None
    if target.nl_ppm_warn is None or target.nl_ppm_max is None:
        return None
    return check_nl(
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


def _candidate_ms2_evidence_builder(
    raw: Any,
    target: Target,
    config: ExtractionConfig,
) -> Callable[[PeakCandidate], Any] | None:
    if target.neutral_loss_da is None:
        return None
    if target.nl_ppm_warn is None or target.nl_ppm_max is None:
        return None
    neutral_loss_da = target.neutral_loss_da
    nl_ppm_warn = target.nl_ppm_warn
    nl_ppm_max = target.nl_ppm_max

    def _builder(candidate: PeakCandidate) -> Any:
        return collect_candidate_ms2_evidence(
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


def _paired_anchor_mismatch_diagnostic(
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
        allowed_delta = _PAIRED_TARGET_ANCHOR_PEAK_DELTA_MAX_MIN
        secondary_note = f"; ISTD anchor at {reference_rt:.3f} min"
    else:
        expected_rt = reference_rt
        anchor_label = "ISTD anchor"
        allowed_delta = _PAIRED_FALLBACK_ISTD_PEAK_DELTA_MAX_MIN
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


def _apply_anchor_mismatch_penalty(
    peak_result: PeakDetectionResult,
    mismatch_reason: str,
) -> PeakDetectionResult:
    reason = f"anchor mismatch; {mismatch_reason}"
    if peak_result.reason:
        reason = f"{peak_result.reason}; {reason}"
    confidence = _anchor_mismatch_confidence(peak_result.confidence)
    return replace(peak_result, confidence=confidence, reason=reason)


def _anchor_mismatch_confidence(confidence: str | None) -> str:
    if confidence == "VERY_LOW":
        return "VERY_LOW"
    return "LOW"


def _resolve_injection_order(
    config: ExtractionConfig,
    raw_paths: list[Path],
    injection_order: dict[str, int] | None,
) -> dict[str, int] | None:
    if injection_order is not None:
        return injection_order
    if config.injection_order_source is not None:
        return read_injection_order(config.injection_order_source)
    if not raw_paths:
        return None
    return _fallback_injection_order_from_mtime(raw_paths)


def _resolve_rt_prior_library(
    config: ExtractionConfig,
    rt_prior_library: dict[tuple[str, str], LibraryEntry] | None,
) -> dict[tuple[str, str], LibraryEntry]:
    if rt_prior_library is not None:
        return rt_prior_library
    if config.rt_prior_library_path is None:
        return {}
    return load_library(config.rt_prior_library_path, config.config_hash)


def _fallback_injection_order_from_mtime(raw_paths: list[Path]) -> dict[str, int]:
    ordered_paths = sorted(
        raw_paths,
        key=lambda path: (path.stat().st_mtime, path.name),
    )
    return {path.stem: index for index, path in enumerate(ordered_paths, start=1)}
