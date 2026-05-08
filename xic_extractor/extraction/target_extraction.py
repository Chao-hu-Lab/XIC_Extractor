from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

from xic_extractor.config import ExtractionConfig, Target
from xic_extractor.extraction.anchors import (
    apply_anchor_mismatch_penalty,
    paired_anchor_mismatch_diagnostic,
)
from xic_extractor.extraction.diagnostics import (
    anchor_rt_mismatch_diagnostic,
    candidate_ms2_evidence_builder,
    check_target_nl,
    nl_anchor_fallback_diagnostic,
)
from xic_extractor.extraction.drift import estimate_sample_drift
from xic_extractor.extraction.istd_recovery import recover_istd_anchor_peak_if_needed
from xic_extractor.extraction.rt_windows import get_rt_window
from xic_extractor.extraction.scoring_factory import (
    paired_istd_fwhm,
    selected_candidate,
    selected_shape_metrics,
)
from xic_extractor.neutral_loss import CandidateMS2Evidence
from xic_extractor.output.messages import (
    DiagnosticRecord,
    build_diagnostic_records,
    istd_confidence_note,
)
from xic_extractor.peak_scoring import candidate_quality_penalty
from xic_extractor.signal_processing import PeakCandidate

if TYPE_CHECKING:
    from xic_extractor.extractor import (
        ExtractionResult,
        FileResult,
        RawFileExtractionResult,
    )


def extract_raw_file_result(
    raw_index: int,
    config: ExtractionConfig,
    targets: list[Target],
    raw_path: Path,
    *,
    scoring_context_factory: Callable[..., Any] | None = None,
) -> RawFileExtractionResult:
    from xic_extractor import extractor

    file_result, diagnostics = process_file(
        config,
        targets,
        raw_path,
        scoring_context_factory=scoring_context_factory,
    )
    return extractor.RawFileExtractionResult(
        raw_index=raw_index,
        sample_name=file_result.sample_name,
        file_result=file_result,
        diagnostics=diagnostics,
    )


def process_file(
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
    from xic_extractor import extractor

    sample_name = raw_path.stem
    try:
        with extractor.open_raw(raw_path, config.dll_dir) as raw:
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
                    anchor_rt = extract_one_target(
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

            sample_drift = estimate_sample_drift(targets, istd_anchor_rts)

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
                extract_one_target(
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

            return extractor.FileResult(
                sample_name=sample_name,
                results=results,
            ), diagnostics
    except Exception as exc:
        reason = f"Failed to open .raw: {type(exc).__name__}: {exc}"
        return (
            extractor.FileResult(sample_name=sample_name, results={}, error=reason),
            [
                DiagnosticRecord(
                    sample_name=sample_name,
                    target_label="",
                    issue="FILE_ERROR",
                    reason=reason,
                )
            ],
        )


def extract_one_target(
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
    from xic_extractor import extractor

    rt_min, rt_max, anchor_used, anchor_rt = get_rt_window(
        raw, target, config, reference_rt=reference_rt, sample_drift=sample_drift
    )
    rt, intensity = raw.extract_xic(target.mz, rt_min, rt_max, target.ppm_tol)
    nl_result = check_target_nl(raw, target, config)
    scoring_context_builder = None
    candidate_ms2_builder = candidate_ms2_evidence_builder(raw, target, config)
    candidate_ms2_cache: dict[PeakCandidate, CandidateMS2Evidence] = {}

    def _cached_candidate_ms2_builder(
        candidate: PeakCandidate,
    ) -> CandidateMS2Evidence | None:
        if candidate_ms2_builder is None:
            return None
        evidence = candidate_ms2_cache.get(candidate)
        if evidence is None:
            evidence = candidate_ms2_builder(candidate)
            candidate_ms2_cache[candidate] = evidence
        return evidence

    if scoring_context_factory is not None:
        scoring_context_builder = scoring_context_factory(
            target=target,
            sample_name=sample_name,
            rt=rt,
            intensity=intensity,
            istd_rt_in_this_sample=istd_rt_in_this_sample,
            paired_istd_fwhm=paired_istd_fwhm,
            nl_result=nl_result,
            candidate_ms2_evidence_builder=_cached_candidate_ms2_builder,
        )
    if scoring_context_builder is not None:
        peak_result = extractor.find_peak_and_area(
            rt,
            intensity,
            config,
            preferred_rt=anchor_rt,
            strict_preferred_rt=strict_preferred_rt,
            scoring_context_builder=scoring_context_builder,
            istd_confidence_note=istd_confidence_note,
        )
    else:
        peak_result = extractor.find_peak_and_area(
            rt,
            intensity,
            config,
            preferred_rt=anchor_rt,
            strict_preferred_rt=strict_preferred_rt,
        )
    peak_result = recover_istd_anchor_peak_if_needed(
        peak_result,
        raw=raw,
        config=config,
        target=target,
        anchor_used=anchor_used,
        anchor_rt=anchor_rt,
        scoring_context_factory=scoring_context_factory,
        candidate_ms2_evidence_builder=_cached_candidate_ms2_builder,
        sample_name=sample_name,
        nl_result=nl_result,
        istd_confidence_note=istd_confidence_note,
        istd_rt_in_this_sample=istd_rt_in_this_sample,
        paired_istd_fwhm=paired_istd_fwhm,
        peak_finder=extractor.find_peak_and_area,
    )
    paired_rejection = paired_anchor_mismatch_diagnostic(
        sample_name,
        target,
        peak_result,
        reference_rt=reference_rt,
        anchor_rt=anchor_rt,
        strict_preferred_rt=strict_preferred_rt,
    )
    if paired_rejection is not None:
        peak_result = apply_anchor_mismatch_penalty(
            peak_result,
            paired_rejection.reason,
        )
    shape_metrics = selected_shape_metrics(intensity, peak_result)
    candidate = selected_candidate(peak_result)
    candidate_ms2_evidence = (
        candidate_ms2_cache.get(candidate) if candidate is not None else None
    )
    quality_penalty = 0
    quality_flags: tuple[str, ...] = ()
    if candidate is not None:
        quality_penalty, _ = candidate_quality_penalty(candidate)
        quality_flags = tuple(
            str(flag) for flag in getattr(candidate, "quality_flags", ())
        )
    if shape_metrics_by_label is not None and shape_metrics is not None:
        shape_metrics_by_label[target.label] = shape_metrics

    result = extractor.ExtractionResult(
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
    )
    results[target.label] = result
    diagnostics.extend(build_diagnostic_records(sample_name, target, result, config))
    if paired_rejection is not None:
        diagnostics.append(paired_rejection)

    anchor_diagnostic = anchor_rt_mismatch_diagnostic(
        sample_name,
        target,
        peak_result,
        anchor_rt=anchor_rt,
        paired_rejection=paired_rejection,
    )
    if anchor_diagnostic is not None:
        diagnostics.append(anchor_diagnostic)
    fallback_diagnostic = nl_anchor_fallback_diagnostic(
        sample_name,
        target,
        config,
        anchor_used=anchor_used,
        rt_min=rt_min,
        rt_max=rt_max,
        nl_result=result.nl,
    )
    if fallback_diagnostic is not None:
        diagnostics.append(fallback_diagnostic)
    return anchor_rt
