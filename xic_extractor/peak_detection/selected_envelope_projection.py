from __future__ import annotations

from typing import Any

import numpy as np

from xic_extractor.peak_detection.baseline import asls_baseline
from xic_extractor.peak_detection.hypotheses import PeakHypothesis
from xic_extractor.peak_detection.selected_envelope import (
    SelectedEnvelopeBoundaryEvaluation,
    SelectedEnvelopePolicy,
    evaluate_selected_envelope_boundary,
)
from xic_extractor.peak_detection.selected_envelope_diagnostics import (
    SelectedEnvelopeDiagnosticRow,
    selected_envelope_diagnostic_row,
)


def selected_envelope_evaluation_from_hypothesis(
    hypothesis: PeakHypothesis,
    *,
    rt_values: Any,
    intensity_values: Any,
    quantitation_context_rt_start: float,
    quantitation_context_rt_end: float,
    policy: SelectedEnvelopePolicy | None = None,
    blank_like_context: bool = False,
) -> SelectedEnvelopeBoundaryEvaluation:
    if not hypothesis.audit.selected:
        raise ValueError("selected-envelope diagnostics require a selected hypothesis")
    _validate_context_contains_resolver(
        hypothesis,
        quantitation_context_rt_start=quantitation_context_rt_start,
        quantitation_context_rt_end=quantitation_context_rt_end,
    )
    rt, intensity = _context_trace(
        rt_values,
        intensity_values,
        quantitation_context_rt_start=quantitation_context_rt_start,
        quantitation_context_rt_end=quantitation_context_rt_end,
    )
    baseline = asls_baseline(intensity)
    return evaluate_selected_envelope_boundary(
        rt,
        intensity,
        baseline,
        selected_apex_rt=hypothesis.integration.rt_apex_min,
        resolver_rt_start=hypothesis.integration.rt_left_min,
        resolver_rt_end=hypothesis.integration.rt_right_min,
        quantitation_context_rt_start=float(rt[0]),
        quantitation_context_rt_end=float(rt[-1]),
        selected_candidate_id=hypothesis.hypothesis_id,
        policy=policy,
        legacy_resolver_provenance=hypothesis.resolver_mode,
        blank_like_context=blank_like_context,
    )


def selected_envelope_diagnostic_row_from_hypothesis(
    *,
    sample_name: str,
    hypothesis: PeakHypothesis,
    rt_values: Any,
    intensity_values: Any,
    quantitation_context_rt_start: float,
    quantitation_context_rt_end: float,
    policy: SelectedEnvelopePolicy | None = None,
    blank_like_context: bool = False,
    plot_path: str = "",
) -> SelectedEnvelopeDiagnosticRow:
    evaluation = selected_envelope_evaluation_from_hypothesis(
        hypothesis,
        rt_values=rt_values,
        intensity_values=intensity_values,
        quantitation_context_rt_start=quantitation_context_rt_start,
        quantitation_context_rt_end=quantitation_context_rt_end,
        policy=policy,
        blank_like_context=blank_like_context,
    )
    return selected_envelope_diagnostic_row(
        sample_name=sample_name,
        target_label=hypothesis.target_label,
        role=hypothesis.role,
        evaluation=evaluation,
        plot_path=plot_path,
    )


def _context_trace(
    rt_values: Any,
    intensity_values: Any,
    *,
    quantitation_context_rt_start: float,
    quantitation_context_rt_end: float,
) -> tuple[np.ndarray, np.ndarray]:
    rt = np.asarray(rt_values, dtype=float)
    intensity = np.asarray(intensity_values, dtype=float)
    if rt.ndim != 1 or intensity.ndim != 1:
        raise ValueError("rt_values and intensity_values must be one-dimensional")
    if len(rt) != len(intensity):
        raise ValueError("rt_values and intensity_values must have the same length")
    if not np.all(np.isfinite(rt)):
        raise ValueError("rt_values must contain finite values")
    if len(rt) >= 2 and not np.all(np.diff(rt) > 0.0):
        raise ValueError("rt_values must be strictly increasing")
    start = min(
        float(quantitation_context_rt_start),
        float(quantitation_context_rt_end),
    )
    end = max(
        float(quantitation_context_rt_start),
        float(quantitation_context_rt_end),
    )
    left = int(np.searchsorted(rt, start, side="left"))
    right = int(np.searchsorted(rt, end, side="right"))
    if right - left < 2:
        raise ValueError("quantitation context must contain at least 2 scans")
    context_rt = rt[left:right]
    context_intensity = intensity[left:right]
    if not (np.all(np.isfinite(context_rt)) and np.all(np.isfinite(context_intensity))):
        raise ValueError("quantitation context trace must contain finite values")
    return context_rt, context_intensity


def _validate_context_contains_resolver(
    hypothesis: PeakHypothesis,
    *,
    quantitation_context_rt_start: float,
    quantitation_context_rt_end: float,
) -> None:
    start = min(
        float(quantitation_context_rt_start),
        float(quantitation_context_rt_end),
    )
    end = max(
        float(quantitation_context_rt_start),
        float(quantitation_context_rt_end),
    )
    if (
        start > hypothesis.integration.rt_left_min
        or end < hypothesis.integration.rt_right_min
    ):
        raise ValueError("quantitation context must contain the resolver interval")
