from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Literal, Sequence

import numpy as np

from xic_extractor.peak_detection.baseline import (
    asls_baseline,
    bounded_trace_interval,
    integrate_with_baseline,
)
from xic_extractor.peak_detection.chrom_peak_segments import (
    ChromPeakSegment,
    ChromPeakSegmentPolicy,
    enumerate_chrom_peak_segments,
)
from xic_extractor.peak_detection.hypotheses import (
    AuditTrail,
    EvidenceVector,
    IntegrationResult,
    PeakHypothesis,
)
from xic_extractor.peak_detection.integration import integrate_area_counts_seconds
from xic_extractor.peak_detection.ms1_morphology import (
    MS1_MORPHOLOGY_AREA_SOURCE,
    gaussian15_positive_asls_residual_metrics,
)
from xic_extractor.peak_detection.selected_envelope import (
    SelectedEnvelopeBoundaryEvaluation,
    TraceInterval,
)

ChromPeakSegmentBoundaryDecision = Literal[
    "accept_candidate",
    "externalize",
    "defer",
]

_RIGHT_TAIL_MAX_INTERNAL_GAP_MIN = 0.25


@dataclass(frozen=True)
class ChromPeakSegmentBoundaryProjection:
    selected_candidate_id: str
    row_boundary_decision: ChromPeakSegmentBoundaryDecision
    boundary_change_class: str
    boundary_stop_reason: str
    selected_segment_id: str = ""
    selected_segment_class: str = ""
    selected_segment_rt_start: float | None = None
    selected_segment_rt_end: float | None = None
    selected_segment_projection: str = ""
    evidence_sources: tuple[str, ...] = ()

    @property
    def accepted(self) -> bool:
        return self.row_boundary_decision == "accept_candidate"


def chrom_peak_segment_promoted_hypothesis_from_hypothesis(
    hypothesis: PeakHypothesis,
    *,
    rt_values: Any,
    intensity_values: Any,
    quantitation_context_rt_start: float,
    quantitation_context_rt_end: float,
    selected_envelope_evaluation: SelectedEnvelopeBoundaryEvaluation | None = None,
    policy: ChromPeakSegmentPolicy | None = None,
) -> tuple[PeakHypothesis, ChromPeakSegmentBoundaryProjection]:
    if not hypothesis.audit.selected:
        raise ValueError("chrom-peak-segment projection requires selected hypothesis")
    rt, intensity = _context_trace(
        rt_values,
        intensity_values,
        quantitation_context_rt_start=quantitation_context_rt_start,
        quantitation_context_rt_end=quantitation_context_rt_end,
    )
    baseline = asls_baseline(intensity)
    enumeration = enumerate_chrom_peak_segments(
        rt,
        intensity,
        baseline,
        quantitation_context_rt_start=float(rt[0]),
        quantitation_context_rt_end=float(rt[-1]),
        policy=policy,
    )
    if enumeration.status != "OK":
        return hypothesis, ChromPeakSegmentBoundaryProjection(
            selected_candidate_id=hypothesis.hypothesis_id,
            row_boundary_decision="defer",
            boundary_change_class="chrom_peak_segment_unavailable",
            boundary_stop_reason=enumeration.status.lower(),
            evidence_sources=("chrom_peak_segment", "morphology_trace"),
        )
    segment = _segment_containing_apex(
        enumeration.segments,
        hypothesis.integration.rt_apex_min,
    )
    if segment is None:
        return hypothesis, ChromPeakSegmentBoundaryProjection(
            selected_candidate_id=hypothesis.hypothesis_id,
            row_boundary_decision="externalize",
            boundary_change_class="chrom_peak_segment_apex_mismatch",
            boundary_stop_reason="selected_apex_not_inside_segment",
            evidence_sources=("chrom_peak_segment", "morphology_trace"),
        )
    morphology_projection = _context_conflict_morphology_segment(
        enumeration.segments,
        selected_segment=segment,
        selected_envelope_evaluation=selected_envelope_evaluation,
        rt=rt,
        intensity=intensity,
        baseline=baseline,
        morphology_window_points=enumeration.morphology_trace_window_points,
    )
    if morphology_projection is not None:
        promoted = _promoted_hypothesis(
            hypothesis,
            segment=morphology_projection,
            rt=rt,
            intensity=intensity,
            baseline=baseline,
            morphology_window_points=enumeration.morphology_trace_window_points,
        )
        return promoted, _projection_from_segment(
            hypothesis,
            morphology_projection,
            decision="accept_candidate",
            change_class="chrom_peak_segment_gaussian15_peak_group",
        )
    extension = _right_tail_extended_segment(
        segment,
        selected_envelope_evaluation,
        rt=rt,
        intensity=intensity,
        baseline=baseline,
        morphology_window_points=enumeration.morphology_trace_window_points,
    )
    if extension is not None:
        promoted = _promoted_hypothesis(
            hypothesis,
            segment=extension,
            rt=rt,
            intensity=intensity,
            baseline=baseline,
            morphology_window_points=enumeration.morphology_trace_window_points,
        )
        return promoted, _projection_from_segment(
            hypothesis,
            extension,
            decision="accept_candidate",
            change_class="chrom_peak_segment_right_tail_extended",
        )
    if segment.segment_class == "low_scan_segment":
        return hypothesis, _projection_from_segment(
            hypothesis,
            segment,
            decision="externalize",
            change_class="chrom_peak_segment_low_scan",
        )
    if segment.segment_class == "shoulder_candidate":
        promoted = _promoted_hypothesis(
            hypothesis,
            segment=segment,
            rt=rt,
            intensity=intensity,
            baseline=baseline,
            morphology_window_points=enumeration.morphology_trace_window_points,
        )
        return promoted, _projection_from_segment(
            hypothesis,
            segment,
            decision="defer",
            change_class="chrom_peak_segment_shoulder_review",
        )
    promoted = _promoted_hypothesis(
        hypothesis,
        segment=segment,
        rt=rt,
        intensity=intensity,
        baseline=baseline,
        morphology_window_points=enumeration.morphology_trace_window_points,
    )
    return promoted, _projection_from_segment(
        hypothesis,
        segment,
        decision="accept_candidate",
        change_class=_boundary_change_class(hypothesis.integration, segment),
    )


def _segment_containing_apex(
    segments: tuple[ChromPeakSegment, ...],
    apex_rt_min: float,
) -> ChromPeakSegment | None:
    containing = [
        segment
        for segment in segments
        if segment.interval.rt_start_min <= apex_rt_min <= segment.interval.rt_end_min
    ]
    if not containing:
        return None
    return min(containing, key=lambda segment: abs(segment.apex_rt_min - apex_rt_min))


def _context_conflict_morphology_segment(
    segments: Sequence[ChromPeakSegment],
    *,
    selected_segment: ChromPeakSegment,
    selected_envelope_evaluation: SelectedEnvelopeBoundaryEvaluation | None,
    rt: np.ndarray,
    intensity: np.ndarray,
    baseline: np.ndarray,
    morphology_window_points: int,
) -> ChromPeakSegment | None:
    if not _right_tail_extension_supported(
        selected_segment,
        selected_envelope_evaluation,
    ):
        return None
    assert selected_envelope_evaluation is not None
    dominant = _dominant_segment_in_envelope(
        segments,
        selected_envelope_evaluation.selected_envelope_interval,
    )
    if dominant is None:
        return None
    group = _connected_shoulder_group(segments, dominant)
    interval = _morphology_group_interval(
        group,
        selected_envelope_evaluation,
        segments=segments,
        rt=rt,
    )
    if (
        interval.start_index == selected_segment.interval.start_index
        and interval.end_index == selected_segment.interval.end_index
    ):
        return None
    return _segment_with_interval(
        group,
        interval=interval,
        rt=rt,
        intensity=intensity,
        baseline=baseline,
        morphology_window_points=morphology_window_points,
    )


def _dominant_segment_in_envelope(
    segments: Sequence[ChromPeakSegment],
    envelope: TraceInterval,
) -> ChromPeakSegment | None:
    overlapping = [
        segment
        for segment in segments
        if _scan_overlap(segment.interval, envelope) > 0
    ]
    if not overlapping:
        return None
    return max(
        overlapping,
        key=lambda segment: (
            segment.morphology_area_shadow,
            segment.morphology_apex_residual,
            segment.interval.scan_count,
        ),
    )


def _connected_shoulder_group(
    segments: Sequence[ChromPeakSegment],
    dominant: ChromPeakSegment,
) -> tuple[ChromPeakSegment, ...]:
    ordered = tuple(sorted(segments, key=lambda item: item.interval.start_index))
    try:
        index = next(
            idx for idx, segment in enumerate(ordered) if segment is dominant
        )
    except StopIteration:
        return (dominant,)
    left = index
    while left > 0 and _should_merge_shoulder_pair(ordered[left - 1], ordered[left]):
        left -= 1
    right = index
    while (
        right + 1 < len(ordered)
        and _should_merge_shoulder_pair(ordered[right], ordered[right + 1])
    ):
        right += 1
    return ordered[left : right + 1]


def _should_merge_shoulder_pair(
    left: ChromPeakSegment,
    right: ChromPeakSegment,
) -> bool:
    if left.segment_class != "shoulder_candidate":
        return False
    if right.segment_class != "shoulder_candidate":
        return False
    return right.interval.start_index <= left.interval.end_index + 1


def _morphology_group_interval(
    group: Sequence[ChromPeakSegment],
    evaluation: SelectedEnvelopeBoundaryEvaluation,
    *,
    segments: Sequence[ChromPeakSegment],
    rt: np.ndarray,
) -> TraceInterval:
    left = min(segment.interval.start_index for segment in group)
    right = max(segment.interval.end_index for segment in group)
    envelope = evaluation.selected_envelope_interval
    if envelope.end_index > right and not _independent_segment_before_index(
        segments,
        group=group,
        stop_index=envelope.end_index,
    ):
        right = envelope.end_index
    right = max(left + 1, min(right, len(rt)))
    return TraceInterval(
        start_index=left,
        end_index=right,
        rt_start_min=float(rt[left]),
        rt_end_min=float(rt[right - 1]),
        scan_count=right - left,
    )


def _independent_segment_before_index(
    segments: Sequence[ChromPeakSegment],
    *,
    group: Sequence[ChromPeakSegment],
    stop_index: int,
) -> bool:
    group_ids = {id(segment) for segment in group}
    group_right = max(segment.interval.end_index for segment in group)
    for segment in segments:
        if id(segment) in group_ids:
            continue
        if group_right <= segment.interval.start_index < stop_index:
            return True
    return False


def _segment_with_interval(
    group: Sequence[ChromPeakSegment],
    *,
    interval: TraceInterval,
    rt: np.ndarray,
    intensity: np.ndarray,
    baseline: np.ndarray,
    morphology_window_points: int,
) -> ChromPeakSegment:
    dominant = max(
        group,
        key=lambda segment: (
            segment.morphology_area_shadow,
            segment.morphology_apex_residual,
        ),
    )
    baseline_integration = integrate_with_baseline(
        intensity,
        rt,
        interval.start_index,
        interval.end_index,
        baseline_values=baseline,
    )
    morphology = gaussian15_positive_asls_residual_metrics(
        rt,
        intensity,
        baseline,
        interval.start_index,
        interval.end_index,
        window_points=morphology_window_points,
    )
    segment_ids = "+".join(segment.segment_id for segment in group)
    return ChromPeakSegment(
        segment_id=f"gaussian15_peak_group:{segment_ids}",
        interval=interval,
        apex_index=dominant.apex_index,
        apex_rt_min=dominant.apex_rt_min,
        raw_apex_residual=dominant.raw_apex_residual,
        morphology_apex_residual=dominant.morphology_apex_residual,
        area_baseline_corrected=baseline_integration.area_baseline_corrected,
        morphology_area_shadow=(
            morphology.area_positive_asls_residual
            if morphology.area_positive_asls_residual is not None
            else sum(segment.morphology_area_shadow for segment in group)
        ),
        segment_class=dominant.segment_class,
        boundary_stop_reason="gaussian15_morphology_peak_group",
        evidence_sources=tuple(
            dict.fromkeys(
                (
                    "morphology_trace",
                    "morphology_local_maximum",
                    "gaussian15_morphology_peak_group",
                    "selected_envelope_context_conflict",
                    *(
                        source
                        for segment in group
                        for source in segment.evidence_sources
                    ),
                )
            )
        ),
    )


def _scan_overlap(left: TraceInterval, right: TraceInterval) -> int:
    return max(
        0,
        min(left.end_index, right.end_index)
        - max(left.start_index, right.start_index),
    )


def _right_tail_extended_segment(
    segment: ChromPeakSegment,
    evaluation: SelectedEnvelopeBoundaryEvaluation | None,
    *,
    rt: np.ndarray,
    intensity: np.ndarray,
    baseline: np.ndarray,
    morphology_window_points: int,
) -> ChromPeakSegment | None:
    if not _right_tail_extension_supported(segment, evaluation):
        return None
    assert evaluation is not None
    envelope = evaluation.selected_envelope_interval
    if envelope.end_index <= segment.interval.end_index:
        return None
    if envelope.start_index > segment.interval.start_index:
        return None
    threshold = evaluation.resolved_baseline_return_threshold
    if threshold is None or threshold <= 0.0:
        return None
    residual = np.maximum(intensity - baseline, 0.0)
    right = _right_tail_boundary_index(
        rt,
        residual,
        search_start=segment.interval.end_index,
        envelope_end=envelope.end_index,
        threshold=float(threshold),
        material_signal_threshold=max(
            float(threshold),
            segment.morphology_apex_residual * 0.05,
        ),
        max_bridge_gap_min=_RIGHT_TAIL_MAX_INTERNAL_GAP_MIN,
    )
    if right <= segment.interval.end_index:
        return None
    interval = TraceInterval(
        start_index=segment.interval.start_index,
        end_index=right,
        rt_start_min=segment.interval.rt_start_min,
        rt_end_min=float(rt[right - 1]),
        scan_count=right - segment.interval.start_index,
    )
    baseline_integration = integrate_with_baseline(
        intensity,
        rt,
        interval.start_index,
        interval.end_index,
        baseline_values=baseline,
    )
    morphology = gaussian15_positive_asls_residual_metrics(
        rt,
        intensity,
        baseline,
        interval.start_index,
        interval.end_index,
        window_points=morphology_window_points,
    )
    morphology_area = (
        morphology.area_positive_asls_residual
        if morphology.area_positive_asls_residual is not None
        else segment.morphology_area_shadow
    )
    return replace(
        segment,
        interval=interval,
        area_baseline_corrected=baseline_integration.area_baseline_corrected,
        morphology_area_shadow=morphology_area,
        boundary_stop_reason="raw_baseline_return_after_right_tail",
        evidence_sources=tuple(
            dict.fromkeys(
                (
                    *segment.evidence_sources,
                    "selected_envelope_right_tail",
                    "raw_baseline_return",
                )
            )
        ),
    )


def _right_tail_extension_supported(
    segment: ChromPeakSegment,
    evaluation: SelectedEnvelopeBoundaryEvaluation | None,
) -> bool:
    if evaluation is None:
        return False
    if evaluation.selected_candidate_id == "":
        return False
    if evaluation.boundary_change_class != "context_apex_conflict":
        return False
    if evaluation.row_boundary_decision not in {"externalize", "defer"}:
        return False
    if segment.segment_class == "low_scan_segment":
        return False
    return True


def _right_tail_boundary_index(
    rt: np.ndarray,
    residual: np.ndarray,
    *,
    search_start: int,
    envelope_end: int,
    threshold: float,
    material_signal_threshold: float,
    max_bridge_gap_min: float,
) -> int:
    index = max(0, min(search_start, len(residual)))
    stop = max(index, min(envelope_end, len(residual)))
    while index < stop:
        if residual[index] > threshold:
            index += 1
            continue

        run_start = index
        while index + 1 < stop and residual[index + 1] <= threshold:
            index += 1
        run_end = index
        next_material_index = _next_material_signal_index(
            residual,
            run_end + 1,
            stop,
            material_signal_threshold=material_signal_threshold,
        )
        if next_material_index is not None and (
            float(rt[next_material_index] - rt[run_start]) <= max_bridge_gap_min
        ):
            index = run_end + 1
            continue
        return run_start
    return stop


def _next_material_signal_index(
    residual: np.ndarray,
    start: int,
    stop: int,
    *,
    material_signal_threshold: float,
) -> int | None:
    if start >= stop:
        return None
    for index in range(start, stop):
        if residual[index] > material_signal_threshold:
            return index
    return None


def _promoted_hypothesis(
    hypothesis: PeakHypothesis,
    *,
    segment: ChromPeakSegment,
    rt: np.ndarray,
    intensity: np.ndarray,
    baseline: np.ndarray,
    morphology_window_points: int,
) -> PeakHypothesis:
    integration = _promoted_integration(
        hypothesis.integration,
        segment=segment,
        rt=rt,
        intensity=intensity,
        baseline=baseline,
        morphology_window_points=morphology_window_points,
    )
    return replace(
        hypothesis,
        integration=integration,
        audit=_audit_with_chrom_peak_segment(hypothesis.audit, segment),
        evidence=_evidence_with_chrom_peak_segment(hypothesis.evidence, segment),
    )


def _promoted_integration(
    integration: IntegrationResult,
    *,
    segment: ChromPeakSegment,
    rt: np.ndarray,
    intensity: np.ndarray,
    baseline: np.ndarray,
    morphology_window_points: int,
) -> IntegrationResult:
    left, right = bounded_trace_interval(
        segment.interval.start_index,
        segment.interval.end_index,
        len(rt),
    )
    baseline_integration = integrate_with_baseline(
        intensity,
        rt,
        left,
        right,
        baseline_values=baseline,
    )
    morphology = gaussian15_positive_asls_residual_metrics(
        rt,
        intensity,
        baseline,
        left,
        right,
        window_points=morphology_window_points,
    )
    return IntegrationResult(
        rt_left_min=float(rt[left]),
        rt_apex_min=segment.apex_rt_min,
        rt_right_min=float(rt[right - 1]),
        raw_apex_rt_min=segment.apex_rt_min,
        rt_width_min=float(rt[right - 1] - rt[left]),
        height_raw=integration.height_raw,
        height_smoothed=integration.height_smoothed,
        area_raw_counts_seconds=integrate_area_counts_seconds(
            intensity,
            rt,
            left,
            right,
        ),
        integration_method="chrom_peak_segment_gaussian15",
        boundary_sources=_boundary_sources(integration, segment),
        area_baseline_corrected=baseline_integration.area_baseline_corrected,
        area_uncertainty=baseline_integration.area_uncertainty,
        area_uncertainty_formula_version=(
            baseline_integration.area_uncertainty_formula_version
        ),
        baseline_residual_mad=baseline_integration.baseline_residual_mad,
        area_uncertainty_noise_source=(
            baseline_integration.area_uncertainty_noise_source
        ),
        baseline_type=baseline_integration.baseline_type,
        baseline_score=baseline_integration.baseline_score,
        raw_scan_indices=tuple(range(left, right)),
        area_ms1_morphology=morphology.area_positive_asls_residual,
        ms1_morphology_area_source=MS1_MORPHOLOGY_AREA_SOURCE,
        ms1_morphology_trace_method=morphology.trace_method,
        ms1_morphology_trace_window_points=morphology.trace_window_points,
        ms1_morphology_trace_effective_points=morphology.trace_effective_points,
    )


def _audit_with_chrom_peak_segment(
    audit: AuditTrail,
    segment: ChromPeakSegment,
) -> AuditTrail:
    return replace(
        audit,
        proposal_sources=tuple(
            dict.fromkeys((*audit.proposal_sources, "chrom_peak_segment"))
        ),
        merge_note="; ".join(
            item
            for item in (
                audit.merge_note,
                f"{segment.segment_class}:{segment.boundary_stop_reason}",
            )
            if item
        ),
    )


def _evidence_with_chrom_peak_segment(
    evidence: EvidenceVector,
    segment: ChromPeakSegment,
) -> EvidenceVector:
    semantics = evidence.decision_semantics
    if semantics is None:
        return evidence
    support = tuple(
        dict.fromkeys(
            (
                *semantics.support_reasons,
                "chrom_peak_segment_context",
            )
        )
    )
    review = semantics.review_reasons
    if segment.segment_class == "shoulder_candidate":
        review = tuple(
            dict.fromkeys((*review, "chrom_peak_segment_shoulder_review"))
        )
    return replace(
        evidence,
        decision_semantics=replace(
            semantics,
            support_reasons=support,
            review_reasons=review,
        ),
    )


def _projection_from_segment(
    hypothesis: PeakHypothesis,
    segment: ChromPeakSegment,
    *,
    decision: ChromPeakSegmentBoundaryDecision,
    change_class: str,
) -> ChromPeakSegmentBoundaryProjection:
    return ChromPeakSegmentBoundaryProjection(
        selected_candidate_id=hypothesis.hypothesis_id,
        row_boundary_decision=decision,
        boundary_change_class=change_class,
        boundary_stop_reason=segment.boundary_stop_reason,
        selected_segment_id=segment.segment_id,
        selected_segment_class=segment.segment_class,
        selected_segment_rt_start=segment.interval.rt_start_min,
        selected_segment_rt_end=segment.interval.rt_end_min,
        selected_segment_projection="selected_apex_contains",
        evidence_sources=("chrom_peak_segment", *segment.evidence_sources),
    )


def _boundary_change_class(
    integration: IntegrationResult,
    segment: ChromPeakSegment,
) -> str:
    if (
        abs(integration.rt_left_min - segment.interval.rt_start_min) <= 1e-9
        and abs(integration.rt_right_min - segment.interval.rt_end_min) <= 1e-9
    ):
        return "chrom_peak_segment_no_change"
    if (
        segment.interval.rt_start_min > integration.rt_left_min
        or segment.interval.rt_end_min < integration.rt_right_min
    ):
        return "chrom_peak_segment_narrowed"
    return "chrom_peak_segment_rebounded"


def _boundary_sources(
    integration: IntegrationResult,
    segment: ChromPeakSegment,
) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(
            (
                *integration.boundary_sources,
                "chrom_peak_segment",
                "gaussian15_morphology",
                segment.segment_class,
                segment.boundary_stop_reason,
                *segment.evidence_sources,
            )
        )
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
