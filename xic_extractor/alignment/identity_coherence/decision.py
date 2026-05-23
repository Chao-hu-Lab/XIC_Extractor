from __future__ import annotations

from .models import (
    CellEvidenceResult,
    IdentityCoherenceConfig,
    IdentityDecisionSummary,
    RtCenterResult,
    SeedGateResult,
)
from .schema import (
    CellIdentityTier,
    DecisionReason,
    IdentityDecision,
    RtCenterDecision,
    SeedGateClass,
    ShapeReferenceBasis,
    WeakBasisReason,
)


def summarize_identity_decision(
    seed_gate: SeedGateResult,
    cells: tuple[CellEvidenceResult, ...],
    center: RtCenterResult,
    config: IdentityCoherenceConfig,
    *,
    identity_family_id: str,
    assessed_sample_count: int,
) -> IdentityDecisionSummary:
    if seed_gate.seed_gate_class != SeedGateClass.COHERENT_SEED:
        return _summary(
            seed_gate,
            cells,
            center,
            config,
            identity_family_id=identity_family_id,
            assessed_sample_count=assessed_sample_count,
            decision=IdentityDecision.REVIEW_ONLY_SEED_GATE_FAILED,
            decision_reason=(
                seed_gate.seed_reject_reason.value
                if seed_gate.seed_reject_reason is not None
                else "seed_gate_failed"
            ),
            weak_basis_reason=WeakBasisReason.NONE,
            include_seed=False,
        )

    decision = _decision_for_coherent_seed(cells, center, config)
    return _summary(
        seed_gate,
        cells,
        center,
        config,
        identity_family_id=identity_family_id,
        assessed_sample_count=assessed_sample_count,
        decision=decision,
        decision_reason=_decision_reason(decision),
        weak_basis_reason=_weak_basis_reason(cells, decision),
        include_seed=True,
    )


def _decision_for_coherent_seed(
    cells: tuple[CellEvidenceResult, ...],
    center: RtCenterResult,
    config: IdentityCoherenceConfig,
) -> IdentityDecision:
    if center.center_decision == RtCenterDecision.CENTER_UNSTABLE_REVIEW_ONLY:
        return IdentityDecision.REVIEW_ONLY_CENTER_UNSTABLE

    non_seed_coherent = _non_seed_coherent_count(cells)
    tier12 = _tier12_count(cells)
    total = 1 + non_seed_coherent

    if (
        total >= config.promotion.min_total_coherent_samples
        and non_seed_coherent >= config.promotion.min_non_seed_coherent_samples
        and tier12 >= config.promotion.min_non_seed_tier12_identity_samples
    ):
        return IdentityDecision.WOULD_PRIMARY
    if _has_rt_only_support(cells):
        return IdentityDecision.REVIEW_ONLY_RT_ONLY_SUPPORT
    return IdentityDecision.REVIEW_ONLY_INSUFFICIENT_SUPPORT


def _summary(
    seed_gate: SeedGateResult,
    cells: tuple[CellEvidenceResult, ...],
    center: RtCenterResult,
    config: IdentityCoherenceConfig,
    *,
    identity_family_id: str,
    assessed_sample_count: int,
    decision: IdentityDecision,
    decision_reason: str,
    weak_basis_reason: WeakBasisReason,
    include_seed: bool,
) -> IdentityDecisionSummary:
    non_seed_coherent = (
        _non_seed_coherent_count(cells) if include_seed else 0
    )
    total = (1 if include_seed else 0) + non_seed_coherent
    coherent_fraction = (
        total / assessed_sample_count if assessed_sample_count > 0 else None
    )
    return IdentityDecisionSummary(
        decision_id=seed_gate.resolved_request.decision_id,
        identity_family_id=identity_family_id,
        seed_candidate_id=seed_gate.resolved_request.seed_candidate_id,
        seed_sample=seed_gate.resolved_request.seed_sample,
        seed_gate_class=seed_gate.seed_gate_class,
        request_identity_completeness_status=(
            seed_gate.resolved_request.request_identity_completeness_status
        ),
        request_candidate_identity_status=(
            seed_gate.resolved_request.request_candidate_identity_status
        ),
        decision=decision,
        decision_reason=decision_reason,
        total_coherent_sample_count=total,
        non_seed_coherent_sample_count=non_seed_coherent,
        tier12_non_seed_identity_sample_count=_tier12_count(cells),
        tier1_fragment_confirmed_sample_count=_tier1_count(cells),
        tier2_shape_supported_sample_count=_tier2_shape_count(cells),
        tier2_seed_shape_fallback_sample_count=_tier2_seed_fallback_count(cells),
        tier3_width_only_sample_count=_tier3_count(cells),
        min_total_coherent_samples=config.promotion.min_total_coherent_samples,
        min_non_seed_coherent_samples=(
            config.promotion.min_non_seed_coherent_samples
        ),
        min_non_seed_tier12_identity_samples=(
            config.promotion.min_non_seed_tier12_identity_samples
        ),
        weak_basis_reason=weak_basis_reason,
        shape_reference_basis=ShapeReferenceBasis.NONE,
        shape_reference_candidate_id="",
        prototype_width_sec=None,
        center_rt_source=center.center_decision.value,
        center=center,
        coherent_fraction=coherent_fraction,
        infrastructure_blocked_sample_count=sum(
            1 for cell in cells if cell.blocked_reason
        ),
        data_quality_reject_sample_count=sum(
            1 for cell in cells if cell.data_quality_reason
        ),
        forbidden_evidence_seen=any(
            cell.forbidden_evidence_seen for cell in cells
        ),
        forbidden_evidence_used=False,
    )


def _decision_reason(decision: IdentityDecision) -> str:
    if decision is IdentityDecision.WOULD_PRIMARY:
        return DecisionReason.TIER1_SUPPORT.value
    return decision.value


def _weak_basis_reason(
    cells: tuple[CellEvidenceResult, ...],
    decision: IdentityDecision,
) -> WeakBasisReason:
    if decision is IdentityDecision.REVIEW_ONLY_RT_ONLY_SUPPORT:
        return WeakBasisReason.RT_ONLY
    return WeakBasisReason.NONE


def _non_seed_coherent_count(cells: tuple[CellEvidenceResult, ...]) -> int:
    return sum(1 for cell in cells if cell.coherent_count_contribution)


def _tier12_count(non_seed_cells: tuple[CellEvidenceResult, ...]) -> int:
    return sum(1 for cell in non_seed_cells if cell.tier12_count_contribution)


def _tier1_count(cells: tuple[CellEvidenceResult, ...]) -> int:
    return sum(1 for cell in cells if cell.cell_identity_tier == CellIdentityTier.TIER1)


def _tier2_shape_count(cells: tuple[CellEvidenceResult, ...]) -> int:
    return sum(1 for cell in cells if cell.cell_identity_tier == CellIdentityTier.TIER2)


def _tier2_seed_fallback_count(cells: tuple[CellEvidenceResult, ...]) -> int:
    return sum(
        1
        for cell in cells
        if cell.cell_identity_tier == CellIdentityTier.TIER2
        and cell.shape_fallback_used
    )


def _tier3_count(cells: tuple[CellEvidenceResult, ...]) -> int:
    return sum(1 for cell in cells if cell.cell_identity_tier == CellIdentityTier.TIER3)


def _has_rt_only_support(cells: tuple[CellEvidenceResult, ...]) -> bool:
    return any(
        cell.cell_identity_tier == CellIdentityTier.RT_ONLY
        and cell.rt_gate_status.value == "pass"
        for cell in cells
    )
