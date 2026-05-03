import gc
from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path
from statistics import median
from typing import Any

from xic_extractor.config import ExtractionConfig, Target
from xic_extractor.extraction.scoring_factory import (
    allow_prepass_anchor,
    build_scoring_context_factory,
    paired_istd_fwhm,
    selected_candidate,
    selected_shape_metrics,
)
from xic_extractor.injection_rolling import read_injection_order
from xic_extractor.neutral_loss import NLResult, check_nl, find_nl_anchor_rt
from xic_extractor.output import csv_writers
from xic_extractor.output.messages import (
    DiagnosticIssue,
    DiagnosticRecord,
    build_diagnostic_records,
    istd_confidence_note,
)
from xic_extractor.peak_scoring import candidate_quality_penalty
from xic_extractor.raw_reader import RawReaderError, open_raw, preflight_raw_reader
from xic_extractor.rt_prior_library import LibraryEntry, load_library
from xic_extractor.signal_processing import (
    PeakDetectionResult,
    PeakResult,
    find_peak_and_area,
)

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
    def total_severity(self) -> int:
        return sum(severity for severity, _ in self.severities) + self.quality_penalty

    @property
    def reported_rt(self) -> float | None:
        """User-facing RT uses the selected candidate's smoothed apex when available."""
        candidate = selected_candidate(self.peak_result)
        if candidate is not None:
            return candidate.smoothed_apex_rt
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
    wide_rows: list[dict[str, str]]
    long_rows: list[dict[str, str]]
    score_breakdown_rows: list[dict[str, str]]
    error: str | None = None


def run(
    config: ExtractionConfig,
    targets: list[Target],
    progress_callback: Callable[[int, int, str], None] | None = None,
    should_stop: Callable[[], bool] | None = None,
    injection_order: dict[str, int] | None = None,
    rt_prior_library: dict[tuple[str, str], LibraryEntry] | None = None,
) -> RunOutput:
    reader_errors = preflight_raw_reader(config.dll_dir)
    if reader_errors:
        raise RawReaderError(" ".join(reader_errors))

    return _run_serial(
        config,
        targets,
        progress_callback=progress_callback,
        should_stop=should_stop,
        injection_order=injection_order,
        rt_prior_library=rt_prior_library,
    )


def _run_serial(
    config: ExtractionConfig,
    targets: list[Target],
    *,
    progress_callback: Callable[[int, int, str], None] | None = None,
    should_stop: Callable[[], bool] | None = None,
    injection_order: dict[str, int] | None = None,
    rt_prior_library: dict[tuple[str, str], LibraryEntry] | None = None,
) -> RunOutput:
    raw_paths = sorted(config.data_dir.glob("*.raw"))
    resolved_injection_order = _resolve_injection_order(
        config, raw_paths, injection_order
    )
    resolved_rt_prior_library = _resolve_rt_prior_library(config, rt_prior_library)
    istd_targets = [target for target in targets if target.is_istd]
    istd_rts_by_sample: dict[str, dict[str, float]] = {}
    for raw_path in raw_paths:
        if should_stop is not None and should_stop():
            break
        prepass = _extract_istd_anchors_only(config, istd_targets, raw_path)
        if prepass is None:
            continue
        anchors, _, _, _ = prepass
        for istd_label, anchor_rt in anchors.items():
            istd_rts_by_sample.setdefault(istd_label, {})[raw_path.stem] = anchor_rt

    scoring_context_factory = build_scoring_context_factory(
        config=config,
        injection_order=(
            resolved_injection_order
            if resolved_injection_order is not None
            else _fallback_injection_order_from_mtime(raw_paths)
        ),
        istd_rts_by_sample=istd_rts_by_sample,
        rt_prior_library=resolved_rt_prior_library or {},
    )

    file_results: list[FileResult] = []
    diagnostics: list[DiagnosticRecord] = []
    total = len(raw_paths)

    for index, raw_path in enumerate(raw_paths, start=1):
        if should_stop is not None and should_stop():
            break

        raw_result = _extract_raw_file_result(
            index,
            config,
            targets,
            raw_path,
            scoring_context_factory=scoring_context_factory,
        )
        file_results.append(raw_result.file_result)
        diagnostics.extend(raw_result.diagnostics)

        if progress_callback is not None:
            progress_callback(index, total, raw_path.name)
        if index % 50 == 0:
            gc.collect()

    output = RunOutput(file_results=file_results, diagnostics=diagnostics)
    if config.keep_intermediate_csv:
        csv_writers.write_all(
            config,
            targets,
            file_results,
            diagnostics,
            emit_score_breakdown=config.emit_score_breakdown,
        )
    return output


def _extract_raw_file_result(
    raw_index: int,
    config: ExtractionConfig,
    targets: list[Target],
    raw_path: Path,
    *,
    scoring_context_factory: Callable[..., Any] | None = None,
) -> RawFileExtractionResult:
    """Extract one RAW file and return a pickleable result object.

    Process backends may pass a scoring context factory only after rebuilding it
    inside the worker process; nested factories must not be sent in job payloads.
    """
    file_result, diagnostics = _process_file(
        config,
        targets,
        raw_path,
        scoring_context_factory=scoring_context_factory,
    )
    return RawFileExtractionResult(
        raw_index=raw_index,
        sample_name=file_result.sample_name,
        file_result=file_result,
        diagnostics=diagnostics,
        wide_rows=[csv_writers._output_row(file_result, targets)],
        long_rows=csv_writers._long_output_rows(file_result, targets),
        score_breakdown_rows=csv_writers._score_breakdown_rows(file_result),
        error=file_result.error,
    )


def _process_file(
    config: ExtractionConfig,
    targets: list[Target],
    raw_path: Path,
    *,
    scoring_context_factory: Callable[..., Any] | None = None,
    precomputed_istd_results: dict[str, ExtractionResult] | None = None,
    precomputed_istd_diagnostics: list[DiagnosticRecord] | None = None,
    precomputed_istd_anchor_rts: dict[str, float] | None = None,
    precomputed_istd_shape_metrics: dict[str, tuple[float, float | None]] | None = None,
) -> tuple[FileResult, list[DiagnosticRecord]]:
    sample_name = raw_path.stem
    try:
        with open_raw(raw_path, config.dll_dir) as raw:
            results: dict[str, ExtractionResult] = dict(precomputed_istd_results or {})
            diagnostics: list[DiagnosticRecord] = list(
                precomputed_istd_diagnostics or []
            )
            istd_shape_metrics_by_label: dict[str, tuple[float, float | None]] = dict(
                precomputed_istd_shape_metrics or {}
            )
            istd_confidence_by_label = {
                label: result.peak_result.confidence
                for label, result in results.items()
                if result.peak_result.confidence is not None
            }

            if precomputed_istd_anchor_rts is None:
                istd_anchor_rts: dict[str, float] = {}
                for target in targets:
                    if not target.is_istd:
                        continue
                    anchor_rt = _extract_one_target(
                        raw,
                        config,
                        sample_name,
                        target,
                        reference_rt=None,
                        strict_preferred_rt=False,
                        results=results,
                        diagnostics=diagnostics,
                        scoring_context_factory=scoring_context_factory,
                        shape_metrics_by_label=istd_shape_metrics_by_label,
                    )
                    confidence = results[target.label].peak_result.confidence
                    if confidence is not None:
                        istd_confidence_by_label[target.label] = confidence
                    if anchor_rt is not None:
                        istd_anchor_rts[target.label] = anchor_rt
            else:
                istd_anchor_rts = dict(precomputed_istd_anchor_rts)

            sample_drift = _estimate_sample_drift(targets, istd_anchor_rts)

            # Pass 2: analytes — reference_rt 依 ISTD pair 決定
            # 有 ISTD pair 且 anchor 成功 → 選最靠近 ISTD anchor_rt 的 scan
            # 有 ISTD pair 但 anchor 失敗 → 發 ISTD_ANCHOR_MISSING
            # 無 ISTD pair → reference_rt=None，選 base_peak 最高的 scan
            for target in targets:
                if target.is_istd:
                    continue
                if target.istd_pair and target.istd_pair in istd_anchor_rts:
                    reference_rt: float | None = istd_anchor_rts[target.istd_pair]
                else:
                    if target.istd_pair:
                        diagnostics.append(
                            DiagnosticRecord(
                                sample_name=sample_name,
                                target_label=target.label,
                                issue="ISTD_ANCHOR_MISSING",
                                reason=(
                                    f"ISTD '{target.istd_pair}' yielded no "
                                    f"NL-confirmed anchor in this sample; "
                                    f"falling back to highest base_peak — isobar "
                                    f"discrimination disabled"
                                ),
                            )
                        )
                    reference_rt = None
                _extract_one_target(
                    raw,
                    config,
                    sample_name,
                    target,
                    reference_rt=reference_rt,
                    sample_drift=sample_drift,
                    strict_preferred_rt=reference_rt is not None,
                    results=results,
                    diagnostics=diagnostics,
                    scoring_context_factory=scoring_context_factory,
                    istd_confidence_note=istd_confidence_note(
                        istd_confidence_by_label.get(target.istd_pair)
                    ),
                    istd_rt_in_this_sample=istd_anchor_rts.get(target.istd_pair),
                    paired_istd_fwhm=paired_istd_fwhm(
                        target,
                        istd_shape_metrics_by_label,
                    ),
                )

            return FileResult(sample_name=sample_name, results=results), diagnostics
    except Exception as exc:
        reason = f"Failed to open .raw: {type(exc).__name__}: {exc}"
        return (
            FileResult(sample_name=sample_name, results={}, error=reason),
            [
                DiagnosticRecord(
                    sample_name=sample_name,
                    target_label="",
                    issue="FILE_ERROR",
                    reason=reason,
                )
            ],
        )


def _extract_one_target(
    raw: Any,
    config: ExtractionConfig,
    sample_name: str,
    target: Target,
    *,
    reference_rt: float | None,
    sample_drift: float = 0.0,
    strict_preferred_rt: bool = False,
    results: dict[str, ExtractionResult],
    diagnostics: list[DiagnosticRecord],
    scoring_context_factory: Callable[..., Any] | None = None,
    istd_confidence_note: str | None = None,
    istd_rt_in_this_sample: float | None = None,
    paired_istd_fwhm: float | None = None,
    shape_metrics_by_label: dict[str, tuple[float, float | None]] | None = None,
) -> float | None:
    """處理單一 target 並將結果寫入 results/diagnostics。

    回傳 anchor_rt（若無則 None）。
    """
    rt_min, rt_max, anchor_used, anchor_rt = _get_rt_window(
        raw, target, config, reference_rt=reference_rt, sample_drift=sample_drift
    )
    rt, intensity = raw.extract_xic(target.mz, rt_min, rt_max, target.ppm_tol)
    nl_result = _check_target_nl(raw, target, config)
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
        )
    if scoring_context_builder is not None:
        peak_result = find_peak_and_area(
            rt,
            intensity,
            config,
            preferred_rt=anchor_rt,
            strict_preferred_rt=strict_preferred_rt,
            scoring_context_builder=scoring_context_builder,
            istd_confidence_note=istd_confidence_note,
        )
    else:
        peak_result = find_peak_and_area(
            rt,
            intensity,
            config,
            preferred_rt=anchor_rt,
            strict_preferred_rt=strict_preferred_rt,
        )
    if (
        peak_result.status == "PEAK_NOT_FOUND"
        and peak_result.peak is None
        and target.is_istd
        and anchor_used
        and anchor_rt is not None
    ):
        recovered_peak_result = _recover_istd_peak_with_wider_anchor_window(
            raw,
            config,
            target,
            anchor_rt=anchor_rt,
            scoring_context_factory=scoring_context_factory,
            sample_name=sample_name,
            nl_result=nl_result,
            istd_confidence_note=istd_confidence_note,
            istd_rt_in_this_sample=istd_rt_in_this_sample,
            paired_istd_fwhm=paired_istd_fwhm,
        )
        if recovered_peak_result is not None:
            peak_result = recovered_peak_result
    paired_rejection = _paired_anchor_mismatch_diagnostic(
        sample_name,
        target,
        peak_result,
        reference_rt=reference_rt,
        anchor_rt=anchor_rt,
        strict_preferred_rt=strict_preferred_rt,
    )
    if paired_rejection is not None:
        peak_result = _apply_anchor_mismatch_penalty(
            peak_result,
            paired_rejection.reason,
        )
    shape_metrics = selected_shape_metrics(intensity, peak_result)
    candidate = selected_candidate(peak_result)
    quality_penalty = 0
    quality_flags: tuple[str, ...] = ()
    if candidate is not None:
        quality_penalty, _ = candidate_quality_penalty(candidate)
        quality_flags = tuple(
            str(flag) for flag in getattr(candidate, "quality_flags", ())
        )
    if shape_metrics_by_label is not None and shape_metrics is not None:
        shape_metrics_by_label[target.label] = shape_metrics

    result = ExtractionResult(
        peak_result=peak_result,
        nl=nl_result,
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
    )
    results[target.label] = result
    diagnostics.extend(build_diagnostic_records(sample_name, target, result, config))
    if paired_rejection is not None:
        diagnostics.append(paired_rejection)

    # 問題 7：anchor 找到，但選出的峰 RT 與 anchor 相差過大（可能 anchor 是雜訊）
    if (
        paired_rejection is None
        and anchor_rt is not None
        and peak_result.peak is not None
    ):
        delta = abs(peak_result.peak.rt - anchor_rt)
        if delta > _ANCHOR_PEAK_DELTA_WARN_MIN:
            diagnostics.append(
                DiagnosticRecord(
                    sample_name=sample_name,
                    target_label=target.label,
                    issue="ANCHOR_RT_MISMATCH",
                    reason=(
                        f"Peak RT {peak_result.peak.rt:.3f} min deviates "
                        f"{delta:.2f} min "
                        f"from NL anchor at {anchor_rt:.3f} min "
                        f"(threshold {_ANCHOR_PEAK_DELTA_WARN_MIN} min); "
                        f"anchor scan may be noise — verify manually"
                    ),
                )
            )

    # 問題 8：anchor 找不到時的 fallback；若 NL check 也失敗，一併提示
    if not anchor_used and target.neutral_loss_da is not None:
        rt_center = (target.rt_min + target.rt_max) / 2.0
        nl_note = ""
        if result.nl is not None and result.nl.status in {"NL_FAIL", "NO_MS2"}:
            nl_note = f"; NL check also {result.nl.status} within fallback window"
        diagnostics.append(
            DiagnosticRecord(
                sample_name=sample_name,
                target_label=target.label,
                issue="NL_ANCHOR_FALLBACK",
                reason=(
                    f"No NL-confirmed MS2 within RT center "
                    f"{rt_center:.2f} ± {config.nl_rt_anchor_search_margin_min} min; "
                    f"fallback window [{rt_min:.2f}, {rt_max:.2f}]{nl_note}"
                ),
            )
        )
    return anchor_rt


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


def _extract_istd_anchors_only(
    config: ExtractionConfig, istd_targets: list[Target], raw_path: Path
) -> tuple[
    dict[str, float],
    dict[str, ExtractionResult],
    list[DiagnosticRecord],
    dict[str, tuple[float, float | None]],
] | None:
    if not istd_targets:
        return {}, {}, [], {}
    try:
        with open_raw(raw_path, config.dll_dir) as raw:
            results: dict[str, ExtractionResult] = {}
            diagnostics: list[DiagnosticRecord] = []
            anchors: dict[str, float] = {}
            shape_metrics_by_label: dict[str, tuple[float, float | None]] = {}
            for target in istd_targets:
                anchor_rt = _extract_one_target(
                    raw,
                    config,
                    raw_path.stem,
                    target,
                    reference_rt=None,
                    strict_preferred_rt=False,
                    results=results,
                    diagnostics=diagnostics,
                    shape_metrics_by_label=shape_metrics_by_label,
                )
                result = results.get(target.label)
                if (
                    anchor_rt is not None
                    and result is not None
                    and allow_prepass_anchor(result.peak_result)
                ):
                    anchors[target.label] = anchor_rt
            return anchors, results, diagnostics, shape_metrics_by_label
    except Exception:
        return None


def _fallback_injection_order_from_mtime(raw_paths: list[Path]) -> dict[str, int]:
    ordered_paths = sorted(
        raw_paths,
        key=lambda path: (path.stat().st_mtime, path.name),
    )
    return {path.stem: index for index, path in enumerate(ordered_paths, start=1)}
