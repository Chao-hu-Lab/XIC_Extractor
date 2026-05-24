from __future__ import annotations

import math
from statistics import median
from typing import cast

from .models import (
    CellCandidateEvidence,
    IdentityCoherenceConfig,
    PrototypeWidthResult,
    WidthAssessmentResult,
)
from .schema import EvidenceStage, WidthStatus

_WIDTH_OWNER_ASSIGNMENT_STATUSES = {"primary", "supporting"}


def estimate_prototype_width(
    candidates: tuple[CellCandidateEvidence, ...],
    config: IdentityCoherenceConfig,
    *,
    seed_sample_id: str | None,
    seed_rt_min: float,
    center_rt_min: float,
) -> PrototypeWidthResult:
    width_candidates = tuple(
        candidate
        for candidate in candidates
        if _is_width_candidate(
            candidate,
            config,
            seed_sample_id=seed_sample_id,
            seed_rt_min=seed_rt_min,
            center_rt_min=center_rt_min,
        )
    )
    non_seed_count = len(width_candidates)
    if len(width_candidates) < config.width.prototype_min_candidates:
        return PrototypeWidthResult(
            width_status=WidthStatus.NOT_ASSESSED,
            prototype_width_sec=None,
            candidate_count=len(width_candidates),
            non_seed_candidate_count=non_seed_count,
            width_candidate_ids=tuple(
                candidate.candidate_evidence.candidate_id
                for candidate in width_candidates
            ),
        )

    prototype_width_sec = median(
        _candidate_width_sec(candidate) for candidate in width_candidates
    )
    return PrototypeWidthResult(
        width_status=WidthStatus.PASS,
        prototype_width_sec=prototype_width_sec,
        candidate_count=len(width_candidates),
        non_seed_candidate_count=non_seed_count,
        width_candidate_ids=tuple(
            candidate.candidate_evidence.candidate_id for candidate in width_candidates
        ),
    )


def assess_width_against_prototype(
    candidate: CellCandidateEvidence,
    *,
    prototype_width_sec: float | None,
    config: IdentityCoherenceConfig,
) -> WidthAssessmentResult:
    if not _finite_positive(prototype_width_sec):
        return WidthAssessmentResult(
            width_status=WidthStatus.NOT_ASSESSED,
            width_ratio_to_prototype=None,
        )
    if not _has_complete_morphology(candidate):
        return WidthAssessmentResult(
            width_status=WidthStatus.NOT_ASSESSED,
            width_ratio_to_prototype=None,
        )

    ratio = _candidate_width_sec(candidate) / float(cast(float, prototype_width_sec))
    status = (
        WidthStatus.PASS
        if config.width.min_ratio <= ratio <= config.width.max_ratio
        else WidthStatus.FAIL
    )
    return WidthAssessmentResult(
        width_status=status,
        width_ratio_to_prototype=ratio,
    )


def _is_width_candidate(
    candidate: CellCandidateEvidence,
    config: IdentityCoherenceConfig,
    *,
    seed_sample_id: str | None,
    seed_rt_min: float,
    center_rt_min: float,
) -> bool:
    if seed_sample_id is not None and candidate.sample_id == seed_sample_id:
        return False
    if (
        _enum_value(candidate.candidate_evidence.evidence_stage)
        != EvidenceStage.PRE_BACKFILL.value
    ):
        return False
    if candidate.blocked_reason or candidate.data_quality_reason:
        return False
    if candidate.duplicate_loser:
        return False
    if candidate.owner_assignment_status not in _WIDTH_OWNER_ASSIGNMENT_STATUSES:
        return False
    if not _has_complete_morphology(candidate):
        return False
    apex_rt = _candidate_apex_rt(candidate)
    center_delta_sec = abs(apex_rt - center_rt_min) * 60.0
    if center_delta_sec > config.rt.preferred_rt_sec:
        return False
    seed_delta_sec = abs(apex_rt - seed_rt_min) * 60.0
    return seed_delta_sec <= config.rt.seed_center_candidate_sec


def _candidate_width_sec(candidate: CellCandidateEvidence) -> float:
    return (
        float(cast(float, candidate.peak_end_rt))
        - float(cast(float, candidate.peak_start_rt))
    ) * 60.0


def _candidate_apex_rt(candidate: CellCandidateEvidence) -> float:
    return float(cast(float, candidate.apex_rt))


def _has_complete_morphology(candidate: CellCandidateEvidence) -> bool:
    values = (
        candidate.apex_rt,
        candidate.peak_start_rt,
        candidate.peak_end_rt,
        candidate.area,
        candidate.height,
    )
    if any(not _finite_number(value) for value in values):
        return False
    peak_start_rt = float(cast(float, candidate.peak_start_rt))
    apex_rt = float(cast(float, candidate.apex_rt))
    peak_end_rt = float(cast(float, candidate.peak_end_rt))
    area = float(cast(float, candidate.area))
    height = float(cast(float, candidate.height))
    return peak_start_rt < apex_rt < peak_end_rt and area > 0.0 and height > 0.0


def _finite_positive(value: object) -> bool:
    return _finite_number(value) and float(cast(float, value)) > 0.0


def _finite_number(value: object) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(value)
    )


def _enum_value(value: object) -> str:
    return str(getattr(value, "value", value))
