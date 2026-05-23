from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass

from .candidate_matcher import match_identity_constraints_to_candidate
from .cell_evidence import select_cell_evidence_for_sample
from .decision import summarize_identity_decision
from .models import (
    CellCandidateEvidence,
    CellEvidenceResult,
    IdentityCoherenceConfig,
    IdentityDecisionSummary,
    PrototypeWidthResult,
    RtCenterResult,
    SeedCandidateEvidence,
    SeedGateResult,
    ShapeReferenceResult,
)
from .rt_center import estimate_rt_center
from .schema import CellIdentityTier, EvidenceStage, RequestCandidateIdentityStatus
from .shape import create_seed_shape_reference, estimate_shape_reference
from .width import estimate_prototype_width

_TIER1_OWNER_ASSIGNMENT_STATUSES = {"primary", "supporting"}


@dataclass(frozen=True)
class IdentityCoherenceRowResult:
    center: RtCenterResult
    prototype_width: PrototypeWidthResult
    shape_reference: ShapeReferenceResult
    cells: tuple[CellEvidenceResult, ...]
    decision: IdentityDecisionSummary


def evaluate_identity_coherence_row(
    seed_gate: SeedGateResult,
    seed_evidence: SeedCandidateEvidence,
    seed_candidate: CellCandidateEvidence | None,
    non_seed_candidates: tuple[CellCandidateEvidence, ...],
    config: IdentityCoherenceConfig,
    *,
    identity_family_id: str,
    assessed_sample_count: int,
) -> IdentityCoherenceRowResult:
    center = estimate_rt_center(seed_evidence, non_seed_candidates, config)
    all_width_candidates = (
        (seed_candidate,) + non_seed_candidates
        if seed_candidate is not None
        else non_seed_candidates
    )
    prototype_width = estimate_prototype_width(
        all_width_candidates,
        config,
        seed_sample_id=seed_gate.resolved_request.seed_sample,
        seed_rt_min=float(seed_evidence.best_seed_rt),
        center_rt_min=center.center_rt_min,
    )

    tier_by_candidate_id = _candidate_tier1_support_map(
        seed_gate,
        non_seed_candidates,
        center,
        config,
    )
    shape_reference = estimate_shape_reference(
        non_seed_candidates,
        config,
        seed_sample_id=seed_gate.resolved_request.seed_sample,
        tier_by_candidate_id=tier_by_candidate_id,
        center_rt_min=center.center_rt_min,
    )
    if not shape_reference.normalized_intensity and seed_candidate is not None:
        shape_reference = create_seed_shape_reference(seed_candidate, config)

    cells = _evaluate_cells(
        seed_gate,
        non_seed_candidates,
        center,
        config,
        identity_family_id=identity_family_id,
        shape_reference=shape_reference,
        prototype_width=prototype_width,
    )
    decision = summarize_identity_decision(
        seed_gate,
        cells,
        center,
        config,
        identity_family_id=identity_family_id,
        assessed_sample_count=assessed_sample_count,
        prototype_width=prototype_width,
    )
    return IdentityCoherenceRowResult(
        center=center,
        prototype_width=prototype_width,
        shape_reference=shape_reference,
        cells=cells,
        decision=decision,
    )


def _evaluate_cells(
    seed_gate: SeedGateResult,
    candidates: tuple[CellCandidateEvidence, ...],
    center: RtCenterResult,
    config: IdentityCoherenceConfig,
    *,
    identity_family_id: str,
    shape_reference: ShapeReferenceResult | None,
    prototype_width: PrototypeWidthResult | None,
) -> tuple[CellEvidenceResult, ...]:
    grouped = _group_by_sample(candidates)
    return tuple(
        select_cell_evidence_for_sample(
            seed_gate.resolved_request,
            tuple(sample_candidates),
            center,
            config,
            identity_family_id=identity_family_id,
            shape_reference=shape_reference,
            prototype_width=prototype_width,
        )
        for _, sample_candidates in sorted(grouped.items())
    )


def _group_by_sample(
    candidates: tuple[CellCandidateEvidence, ...],
) -> dict[str, list[CellCandidateEvidence]]:
    grouped: dict[str, list[CellCandidateEvidence]] = defaultdict(list)
    for candidate in candidates:
        grouped[candidate.sample_id].append(candidate)
    return dict(grouped)


def _candidate_tier1_support_map(
    seed_gate: SeedGateResult,
    candidates: tuple[CellCandidateEvidence, ...],
    center: RtCenterResult,
    config: IdentityCoherenceConfig,
) -> dict[str, CellIdentityTier]:
    return {
        candidate.candidate_evidence.candidate_id: CellIdentityTier.TIER1
        for candidate in candidates
        if _candidate_has_tier1_support(
            seed_gate,
            candidate,
            center,
            config,
        )
    }


def _candidate_has_tier1_support(
    seed_gate: SeedGateResult,
    candidate: CellCandidateEvidence,
    center: RtCenterResult,
    config: IdentityCoherenceConfig,
) -> bool:
    if (
        _enum_value(candidate.candidate_evidence.evidence_stage)
        != EvidenceStage.PRE_BACKFILL.value
    ):
        return False
    if candidate.blocked_reason or candidate.data_quality_reason:
        return False
    if candidate.duplicate_loser:
        return False
    if candidate.owner_assignment_status not in _TIER1_OWNER_ASSIGNMENT_STATUSES:
        return False
    if not _has_complete_morphology(candidate):
        return False
    rt_delta_sec = (float(candidate.apex_rt) - center.center_rt_min) * 60.0
    if abs(rt_delta_sec) > config.rt.preferred_rt_sec:
        return False
    match = match_identity_constraints_to_candidate(
        seed_gate.resolved_request,
        candidate.candidate_evidence,
    )
    return (
        _enum_value(match.request_candidate_identity_status)
        == RequestCandidateIdentityStatus.MATCH.value
    )


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
    return (
        float(candidate.peak_start_rt)
        < float(candidate.apex_rt)
        < float(candidate.peak_end_rt)
        and float(candidate.area) > 0.0
        and float(candidate.height) > 0.0
    )


def _finite_number(value: object) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(value)
    )


def _enum_value(value: object) -> object:
    return getattr(value, "value", value)
