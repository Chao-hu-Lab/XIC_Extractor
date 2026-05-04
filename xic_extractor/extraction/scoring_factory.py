from collections.abc import Callable
from typing import Any

import numpy as np
from scipy.signal import peak_widths

from xic_extractor.config import ExtractionConfig, Target
from xic_extractor.injection_rolling import rolling_median_rt
from xic_extractor.neutral_loss import NLResult
from xic_extractor.peak_scoring import (
    ScoringContext,
    compute_local_sn_cache,
    is_adap_like_quality_flag,
)
from xic_extractor.rt_prior_library import LibraryEntry
from xic_extractor.signal_processing import (
    PeakCandidate,
    PeakDetectionResult,
)


def build_scoring_context_factory(
    *,
    config: ExtractionConfig,
    injection_order: dict[str, int],
    istd_rts_by_sample: dict[str, dict[str, float]],
    rt_prior_library: dict[tuple[str, str], LibraryEntry],
) -> Callable[..., Callable[[PeakCandidate], ScoringContext]]:
    def _factory(
        *,
        target: Target,
        sample_name: str,
        rt: np.ndarray,
        intensity: np.ndarray,
        istd_rt_in_this_sample: float | None,
        paired_istd_fwhm: float | None,
        nl_result: NLResult | None,
    ) -> Callable[[PeakCandidate], ScoringContext]:
        rt_prior: float | None = None
        rt_prior_sigma: float | None = None
        prior_source = ""

        if target.is_istd:
            rt_map = istd_rts_by_sample.get(target.label, {})
            rt_prior = rolling_median_rt(
                target.label,
                sample_name,
                rt_map,
                injection_order,
                window=config.rolling_window_size,
            )
            if rt_prior is not None:
                prior_source = "rolling_median"
            else:
                library_entry = rt_prior_library.get((target.label, "ISTD"))
                if (
                    library_entry is not None
                    and library_entry.median_abs_rt is not None
                ):
                    rt_prior = library_entry.median_abs_rt
                    rt_prior_sigma = library_entry.sigma_abs_rt
                    prior_source = "library_abs"
        else:
            library_entry = rt_prior_library.get((target.label, "analyte"))
            if (
                library_entry is not None
                and istd_rt_in_this_sample is not None
                and library_entry.median_delta_rt is not None
            ):
                rt_prior = istd_rt_in_this_sample + library_entry.median_delta_rt
                rt_prior_sigma = library_entry.sigma_delta_rt
                prior_source = "delta_rt_library"

        rt_values = np.asarray(rt, dtype=float)
        intensity_values = np.asarray(intensity, dtype=float)
        baseline_array, residual_mad = compute_local_sn_cache(intensity_values)
        ms2_present = nl_result is not None and nl_result.matched_scan_count > 0
        nl_match = nl_result is not None and nl_result.status in {"OK", "WARN"}
        prefer_rt_prior_tiebreak = (
            not target.is_istd
            and bool(target.istd_pair)
            and istd_rt_in_this_sample is not None
            and rt_prior is not None
            and prior_source == "delta_rt_library"
        )

        def builder(candidate: PeakCandidate) -> ScoringContext:
            half_width_ratio, fwhm = compute_shape_metrics(
                intensity_values,
                candidate.smoothed_apex_index,
            )
            fwhm_ratio: float | None = None
            if (
                not target.is_istd
                and fwhm is not None
                and paired_istd_fwhm is not None
                and paired_istd_fwhm > 0
            ):
                fwhm_ratio = fwhm / paired_istd_fwhm
            return ScoringContext(
                rt_array=rt_values,
                intensity_array=intensity_values,
                apex_index=candidate.smoothed_apex_index,
                half_width_ratio=half_width_ratio,
                fwhm_ratio=fwhm_ratio,
                ms2_present=ms2_present,
                nl_match=nl_match,
                rt_prior=rt_prior,
                rt_prior_sigma=rt_prior_sigma,
                rt_min=target.rt_min,
                rt_max=target.rt_max,
                dirty_matrix=config.dirty_matrix_mode,
                baseline_array=baseline_array,
                residual_mad=residual_mad,
                prefer_rt_prior_tiebreak=prefer_rt_prior_tiebreak,
            )

        setattr(builder, "rt_prior", rt_prior)
        setattr(builder, "prior_source", prior_source)
        return builder

    return _factory


def make_scoring_context_factory(
    *,
    config: ExtractionConfig,
    injection_order: dict[str, int],
    istd_rts_by_sample: dict[str, dict[str, float]],
    rt_prior_library: dict[tuple[str, str], Any],
) -> Callable[..., Any]:
    return build_scoring_context_factory(
        config=config,
        injection_order=injection_order,
        istd_rts_by_sample=istd_rts_by_sample,
        rt_prior_library=rt_prior_library,
    )


def compute_shape_metrics(
    intensity: np.ndarray,
    apex_index: int,
) -> tuple[float, float | None]:
    values = np.asarray(intensity, dtype=float)
    if len(values) == 0 or apex_index < 0 or apex_index >= len(values):
        return 1.0, None
    widths, _, left_ips, right_ips = peak_widths(values, [apex_index], rel_height=0.5)
    if len(widths) == 0:
        return 1.0, None
    fwhm = float(widths[0])
    left = apex_index - float(left_ips[0])
    right = float(right_ips[0]) - apex_index
    if left <= 0 or right <= 0:
        return 1.0, fwhm
    return float(left / right), fwhm


def selected_shape_metrics(
    intensity: np.ndarray,
    peak_result: PeakDetectionResult,
) -> tuple[float, float | None] | None:
    candidate = selected_candidate(peak_result)
    if candidate is None:
        return None
    return compute_shape_metrics(intensity, candidate.smoothed_apex_index)


def selected_candidate(peak_result: PeakDetectionResult) -> PeakCandidate | None:
    if peak_result.peak is None:
        return None
    for candidate in peak_result.candidates:
        if candidate.peak == peak_result.peak:
            return candidate
    return None


def allow_prepass_anchor(peak_result: PeakDetectionResult) -> bool:
    candidate = selected_candidate(peak_result)
    if candidate is None:
        return False
    flags = tuple(str(flag) for flag in getattr(candidate, "quality_flags", ()))
    return not any(not is_adap_like_quality_flag(flag) for flag in flags)


def paired_istd_fwhm(
    target: Target,
    istd_shape_metrics_by_label: dict[str, tuple[float, float | None]],
) -> float | None:
    if not target.istd_pair:
        return None
    metrics = istd_shape_metrics_by_label.get(target.istd_pair)
    if metrics is None:
        return None
    return metrics[1]
