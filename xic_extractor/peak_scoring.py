"""Tier-based peak scoring. Each signal returns (severity, label)."""

from __future__ import annotations

_LABEL_SYMMETRY = "symmetry"

_SYMMETRY_SOFT_LOW, _SYMMETRY_SOFT_HIGH = 0.5, 2.0
_SYMMETRY_HARD_LOW, _SYMMETRY_HARD_HIGH = 0.3, 3.0


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
