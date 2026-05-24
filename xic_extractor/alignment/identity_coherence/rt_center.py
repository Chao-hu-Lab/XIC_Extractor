from __future__ import annotations

import math
from statistics import median
from typing import cast

from .models import (
    CellCandidateEvidence,
    IdentityCoherenceConfig,
    RtCenterResult,
    SeedCandidateEvidence,
)
from .schema import EvidenceStage, RtCenterDecision

_CENTER_OWNER_ASSIGNMENT_STATUSES = {"primary", "supporting"}


def estimate_rt_center(
    seed_evidence: SeedCandidateEvidence,
    candidates: tuple[CellCandidateEvidence, ...],
    config: IdentityCoherenceConfig,
) -> RtCenterResult:
    seed_rt_min = seed_evidence.best_seed_rt
    if not _finite_number(seed_rt_min):
        raise ValueError("seed best_seed_rt must be finite")
    seed_rt = float(cast(float, seed_rt_min))

    center_candidates = tuple(
        candidate
        for candidate in candidates
        if _is_center_candidate(candidate, seed_rt, config)
    )
    if not center_candidates:
        return RtCenterResult(
            center_rt_min=seed_rt,
            center_rt_sec=seed_rt * 60.0,
            center_decision=RtCenterDecision.SEED_ANCHORED,
            center_candidate_count=0,
            center_drift_sec=0.0,
        )

    proposed_center_rt_min = median(
        _candidate_apex_rt(candidate) for candidate in center_candidates
    )
    center_drift_sec = abs(proposed_center_rt_min - seed_rt) * 60.0
    if center_drift_sec > config.rt.max_center_drift_sec:
        return RtCenterResult(
            center_rt_min=seed_rt,
            center_rt_sec=seed_rt * 60.0,
            center_decision=RtCenterDecision.CENTER_UNSTABLE_REVIEW_ONLY,
            center_candidate_count=len(center_candidates),
            center_drift_sec=center_drift_sec,
        )

    return RtCenterResult(
        center_rt_min=proposed_center_rt_min,
        center_rt_sec=proposed_center_rt_min * 60.0,
        center_decision=RtCenterDecision.RECENTERED_STABLE,
        center_candidate_count=len(center_candidates),
        center_drift_sec=center_drift_sec,
    )


def _is_center_candidate(
    candidate: CellCandidateEvidence,
    seed_rt_min: float,
    config: IdentityCoherenceConfig,
) -> bool:
    if candidate.candidate_evidence.evidence_stage != EvidenceStage.PRE_BACKFILL:
        return False
    if candidate.blocked_reason or candidate.data_quality_reason:
        return False
    if candidate.duplicate_loser:
        return False
    if candidate.owner_assignment_status not in _CENTER_OWNER_ASSIGNMENT_STATUSES:
        return False
    if not _has_complete_morphology(candidate):
        return False
    return abs(_candidate_apex_rt(candidate) - seed_rt_min) * 60.0 <= (
        config.rt.seed_center_candidate_sec
    )


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


def _finite_number(value: object) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(value)
    )
