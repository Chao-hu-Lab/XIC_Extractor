"""Tier-based peak scoring. Each signal returns (severity, label)."""

from __future__ import annotations

import numpy as np

from xic_extractor.baseline import asls_baseline

_LABEL_SYMMETRY = "symmetry"
_LABEL_LOCAL_SN = "local_sn"
_LABEL_NL = "nl_support"
_LABEL_RT_PRIOR = "rt_prior"
_LABEL_RT_CENTRALITY = "rt_centrality"

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


def symmetry_severity(half_width_ratio: float) -> tuple[int, str]:
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
    deviation = abs(observed - prior)
    if sigma is not None and sigma > 0:
        n_sigma = deviation / sigma
        if n_sigma >= _RT_PRIOR_SIGMA_HARD:
            return 2, _LABEL_RT_PRIOR
        if n_sigma >= _RT_PRIOR_SIGMA_SOFT:
            return 1, _LABEL_RT_PRIOR
        return 0, _LABEL_RT_PRIOR
    if deviation >= _RT_PRIOR_NO_SIGMA_HARD_MIN:
        return 2, _LABEL_RT_PRIOR
    if deviation >= _RT_PRIOR_NO_SIGMA_SOFT_MIN:
        return 1, _LABEL_RT_PRIOR
    return 0, _LABEL_RT_PRIOR


def rt_centrality_severity(
    observed: float, rt_min: float, rt_max: float
) -> tuple[int, str]:
    span = rt_max - rt_min
    if span <= 0:
        return 0, _LABEL_RT_CENTRALITY
    distance_low = observed - rt_min
    distance_high = rt_max - observed
    min_edge = min(distance_low, distance_high) / span
    if min_edge < 0.01:
        return 2, _LABEL_RT_CENTRALITY
    if min_edge < 0.10:
        return 1, _LABEL_RT_CENTRALITY
    return 0, _LABEL_RT_CENTRALITY
