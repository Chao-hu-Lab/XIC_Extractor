"""Tier-based peak scoring. Each signal returns (severity, label)."""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Any

import numpy as np

from xic_extractor.baseline import asls_baseline

_LABEL_SYMMETRY = "symmetry"
_LABEL_LOCAL_SN = "local_sn"
_LABEL_NL = "nl_support"
_LABEL_RT_PRIOR = "rt_prior"
_LABEL_RT_CENTRALITY = "rt_centrality"
_LABEL_NOISE_SHAPE = "noise_shape"
_LABEL_PEAK_WIDTH = "peak_width"

_SYMMETRY_SOFT_LOW, _SYMMETRY_SOFT_HIGH = 0.5, 2.0
_SYMMETRY_HARD_LOW, _SYMMETRY_HARD_HIGH = 0.3, 3.0
_SN_SOFT_THRESHOLD = 3.0
_SN_HARD_THRESHOLD = 2.0
_SN_DIRTY_SOFT_THRESHOLD = 2.0
_SN_DIRTY_HARD_THRESHOLD = 1.3
_RT_PRIOR_SIGMA_SOFT = 2.0
_RT_PRIOR_SIGMA_HARD = 5.0
_RT_PRIOR_NO_SIGMA_SOFT_MIN = 0.2
_RT_PRIOR_NO_SIGMA_HARD_MIN = 1.0


class Confidence(Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    VERY_LOW = "VERY_LOW"


@dataclass(frozen=True)
class ScoredCandidate:
    candidate: Any
    severities: tuple[tuple[int, str], ...]
    confidence: Confidence
    reason: str
    prior_rt: float | None


@dataclass(frozen=True)
class ScoringContext:
    rt_array: np.ndarray
    intensity_array: np.ndarray
    apex_index: int
    half_width_ratio: float
    fwhm_ratio: float | None
    ms2_present: bool
    nl_match: bool
    rt_prior: float | None
    rt_prior_sigma: float | None
    rt_min: float
    rt_max: float
    dirty_matrix: bool


_CONFIDENCE_RANK = {
    Confidence.HIGH: 0,
    Confidence.MEDIUM: 1,
    Confidence.LOW: 2,
    Confidence.VERY_LOW: 3,
}


def confidence_from_total(total_severity: int) -> Confidence:
    if total_severity == 0:
        return Confidence.HIGH
    if total_severity <= 2:
        return Confidence.MEDIUM
    if total_severity <= 4:
        return Confidence.LOW
    return Confidence.VERY_LOW


def build_reason(
    signals: list[tuple[int, str]],
    istd_confidence_note: str | None,
) -> str:
    concerns = [(severity, label) for severity, label in signals if severity >= 1]
    if not concerns and istd_confidence_note is None:
        return "all checks passed"

    parts: list[str] = []
    if concerns:
        concerns.sort(key=lambda pair: -pair[0])
        phrase = "; ".join(
            f"{label} ({'major' if severity == 2 else 'minor'})"
            for severity, label in concerns
        )
        parts.append(f"concerns: {phrase}")
    if istd_confidence_note is not None:
        parts.append(istd_confidence_note)
    return "; ".join(parts)


def select_candidate_with_confidence(scored: list[ScoredCandidate]) -> ScoredCandidate:
    if not scored:
        raise ValueError("select_candidate_with_confidence requires at least one candidate")

    def key(scored_candidate: ScoredCandidate) -> tuple[int, float, float]:
        candidate = scored_candidate.candidate
        distance = (
            abs(candidate.smoothed_apex_rt - scored_candidate.prior_rt)
            if scored_candidate.prior_rt is not None
            else 0.0
        )
        return (
            _CONFIDENCE_RANK[scored_candidate.confidence],
            distance,
            -candidate.smoothed_apex_intensity,
        )

    return min(scored, key=key)


def score_candidate(
    candidate: Any,
    ctx: ScoringContext,
    prior_rt: float | None,
    istd_confidence_note: str | None = None,
) -> ScoredCandidate:
    severities: list[tuple[int, str]] = [
        symmetry_severity(ctx.half_width_ratio),
        local_sn_severity(ctx.intensity_array, ctx.apex_index, ctx.dirty_matrix),
        nl_support_severity(ctx.ms2_present, ctx.nl_match),
        rt_prior_severity(candidate.smoothed_apex_rt, ctx.rt_prior, ctx.rt_prior_sigma),
        rt_centrality_severity(candidate.smoothed_apex_rt, ctx.rt_min, ctx.rt_max),
        noise_shape_severity(ctx.intensity_array),
        peak_width_severity(ctx.fwhm_ratio),
    ]
    total = sum(severity for severity, _ in severities)
    confidence = confidence_from_total(total)
    reason = build_reason(severities, istd_confidence_note)
    return ScoredCandidate(
        candidate=candidate,
        severities=tuple(severities),
        confidence=confidence,
        reason=reason,
        prior_rt=prior_rt,
    )


def _is_finite(value: float) -> bool:
    return math.isfinite(float(value))


def _at_least(value: float, threshold: float) -> bool:
    return value >= threshold or math.isclose(
        value,
        threshold,
        rel_tol=1e-12,
        abs_tol=1e-12,
    )


def symmetry_severity(half_width_ratio: float) -> tuple[int, str]:
    if not _is_finite(half_width_ratio):
        return 2, _LABEL_SYMMETRY
    if (
        half_width_ratio < _SYMMETRY_HARD_LOW
        or half_width_ratio > _SYMMETRY_HARD_HIGH
    ):
        return 2, _LABEL_SYMMETRY
    if (
        half_width_ratio < _SYMMETRY_SOFT_LOW
        or half_width_ratio > _SYMMETRY_SOFT_HIGH
    ):
        return 1, _LABEL_SYMMETRY
    return 0, _LABEL_SYMMETRY


def local_sn_severity(
    intensity: np.ndarray,
    apex_index: int,
    dirty_matrix: bool,
) -> tuple[int, str]:
    """S/N ratio of peak apex vs. MAD of trace residual after AsLS baseline."""
    values = np.asarray(intensity, dtype=float)
    if len(values) < 5 or apex_index < 0 or apex_index >= len(values):
        return 2, _LABEL_LOCAL_SN
    try:
        baseline = asls_baseline(values)
    except ValueError:
        return 2, _LABEL_LOCAL_SN
    residual = values - baseline
    mad = float(np.median(np.abs(residual - np.median(residual))))
    if mad <= 0:
        return 0, _LABEL_LOCAL_SN
    peak_above_baseline = float(values[apex_index] - baseline[apex_index])
    ratio = peak_above_baseline / mad
    hard = _SN_DIRTY_HARD_THRESHOLD if dirty_matrix else _SN_HARD_THRESHOLD
    soft = _SN_DIRTY_SOFT_THRESHOLD if dirty_matrix else _SN_SOFT_THRESHOLD
    if ratio < hard:
        return 2, _LABEL_LOCAL_SN
    if ratio < soft:
        return 1, _LABEL_LOCAL_SN
    return 0, _LABEL_LOCAL_SN


def nl_support_severity(ms2_present: bool, nl_match: bool) -> tuple[int, str]:
    if ms2_present and nl_match:
        return 0, _LABEL_NL
    if ms2_present and not nl_match:
        return 2, _LABEL_NL
    return 1, _LABEL_NL


def rt_prior_severity(
    observed: float,
    prior: float | None,
    sigma: float | None,
) -> tuple[int, str]:
    if prior is None:
        return 0, _LABEL_RT_PRIOR
    if not _is_finite(observed) or not _is_finite(prior):
        return 2, _LABEL_RT_PRIOR
    deviation = abs(observed - prior)
    if sigma is not None and _is_finite(sigma) and sigma > 0:
        n_sigma = deviation / sigma
        if _at_least(n_sigma, _RT_PRIOR_SIGMA_HARD):
            return 2, _LABEL_RT_PRIOR
        if _at_least(n_sigma, _RT_PRIOR_SIGMA_SOFT):
            return 1, _LABEL_RT_PRIOR
        return 0, _LABEL_RT_PRIOR
    if _at_least(deviation, _RT_PRIOR_NO_SIGMA_HARD_MIN):
        return 2, _LABEL_RT_PRIOR
    if _at_least(deviation, _RT_PRIOR_NO_SIGMA_SOFT_MIN):
        return 1, _LABEL_RT_PRIOR
    return 0, _LABEL_RT_PRIOR


def rt_centrality_severity(
    observed: float, rt_min: float, rt_max: float
) -> tuple[int, str]:
    if not (_is_finite(observed) and _is_finite(rt_min) and _is_finite(rt_max)):
        return 2, _LABEL_RT_CENTRALITY
    span = rt_max - rt_min
    if span <= 0:
        return 2, _LABEL_RT_CENTRALITY
    distance_low = observed - rt_min
    distance_high = rt_max - observed
    min_edge = min(distance_low, distance_high) / span
    if min_edge < 0.01:
        return 2, _LABEL_RT_CENTRALITY
    if min_edge < 0.10:
        return 1, _LABEL_RT_CENTRALITY
    return 0, _LABEL_RT_CENTRALITY


def noise_shape_severity(intensity: np.ndarray) -> tuple[int, str]:
    """Jaggedness: sum of abs second differences normalised by peak span."""
    values = np.asarray(intensity, dtype=float)
    if values.ndim != 1 or not np.all(np.isfinite(values)):
        return 2, _LABEL_NOISE_SHAPE
    if len(values) < 3:
        return 0, _LABEL_NOISE_SHAPE
    span = float(values.max() - values.min())
    if span <= 0:
        return 0, _LABEL_NOISE_SHAPE
    second_diff = np.abs(np.diff(values, n=2))
    jagged = float(second_diff.sum() / (span * len(values)))
    if jagged > 0.5:
        return 2, _LABEL_NOISE_SHAPE
    if jagged > 0.3:
        return 1, _LABEL_NOISE_SHAPE
    return 0, _LABEL_NOISE_SHAPE


def peak_width_severity(fwhm_ratio: float | None) -> tuple[int, str]:
    if fwhm_ratio is None:
        return 0, _LABEL_PEAK_WIDTH
    if not _is_finite(fwhm_ratio):
        return 2, _LABEL_PEAK_WIDTH
    if fwhm_ratio < 0.3 or fwhm_ratio > 3.0:
        return 2, _LABEL_PEAK_WIDTH
    if fwhm_ratio < 0.5 or fwhm_ratio > 2.0:
        return 1, _LABEL_PEAK_WIDTH
    return 0, _LABEL_PEAK_WIDTH
