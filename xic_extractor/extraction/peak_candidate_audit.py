from __future__ import annotations

from collections.abc import Callable
from typing import Any

from xic_extractor.config import ExtractionConfig, Target
from xic_extractor.extraction.peak_candidate_boundaries import (
    PeakCandidateBoundaryRow,
    append_peak_candidate_boundary_rows,
)
from xic_extractor.extraction.peak_candidate_table import (
    PeakCandidateTableRow,
    append_peak_candidate_rows,
)
from xic_extractor.neutral_loss import CandidateMS2Evidence
from xic_extractor.peak_detection.cwt import add_cwt_proposals_for_audit
from xic_extractor.peak_detection.models import PeakCandidate, PeakDetectionResult
from xic_extractor.peak_detection.traces import TraceGroup


def append_peak_audit_rows(
    *,
    peak_candidate_rows: list[PeakCandidateTableRow] | None,
    peak_candidate_boundary_rows: list[PeakCandidateBoundaryRow] | None,
    config: ExtractionConfig,
    sample_name: str,
    target: Target,
    peak_result: PeakDetectionResult,
    candidate_ms2_builder: Callable[[PeakCandidate], CandidateMS2Evidence | None],
    rt: Any,
    intensity: Any,
    trace_group: TraceGroup | None = None,
    scoring_context_builder: Callable[[PeakCandidate], Any] | None = None,
    istd_confidence_note: str | None = None,
) -> None:
    if not config.emit_peak_candidates:
        return
    audit_peak_result = add_cwt_proposals_for_audit(
        peak_result,
        rt,
        intensity,
        config,
    )
    append_peak_candidate_rows(
        peak_candidate_rows,
        config,
        sample_name,
        target,
        peak_result,
        candidate_ms2_builder,
        audit_peak_result=audit_peak_result,
        rt=rt,
        intensity=intensity,
        trace_group=trace_group,
        scoring_context_builder=scoring_context_builder,
        istd_confidence_note=istd_confidence_note,
    )
    append_peak_candidate_boundary_rows(
        peak_candidate_boundary_rows,
        config,
        sample_name,
        target,
        peak_result,
        rt=rt,
        intensity=intensity,
        trace_group=trace_group,
        audit_peak_result=audit_peak_result,
    )
