from __future__ import annotations

import math
from dataclasses import replace

from .candidate_matcher import match_identity_constraints_to_candidate
from .models import (
    CandidateIdentityMatch,
    CellCandidateEvidence,
    CellEvidenceResult,
    IdentityCoherenceConfig,
    IdentityCoherenceRequest,
    PrototypeWidthResult,
    RtCenterResult,
    ShapeReferenceResult,
)
from .schema import (
    AreaHeightStatus,
    BaselineAuditStatus,
    CellAssessmentStatus,
    CellBlockedReason,
    CellDataQualityReason,
    CellIdentityBasis,
    CellIdentityTier,
    EvidenceStage,
    FragmentMatchStatus,
    NonRtIdentityResult,
    RequestCandidateIdentityStatus,
    RtGateStatus,
    ShapeAuditStatus,
    ShapeReferenceBasis,
    ShapeStatus,
    WidthStatus,
)
from .shape import compare_shape_to_reference
from .width import assess_width_against_prototype


def select_cell_evidence_for_sample(
    request: IdentityCoherenceRequest,
    candidates: tuple[CellCandidateEvidence, ...],
    center: RtCenterResult,
    config: IdentityCoherenceConfig,
    *,
    identity_family_id: str,
    shape_reference: ShapeReferenceResult | None = None,
    prototype_width: PrototypeWidthResult | None = None,
) -> CellEvidenceResult:
    if not candidates:
        raise ValueError("at least one candidate is required for cell selection")

    assessed = tuple(
        evaluate_cell_evidence(
            request,
            candidate,
            center,
            config,
            identity_family_id=identity_family_id,
            shape_reference=shape_reference,
            prototype_width=prototype_width,
        )
        for candidate in candidates
    )
    tier1 = tuple(
        (
            candidate,
            cell,
            match_identity_constraints_to_candidate(
                request,
                candidate.candidate_evidence,
            ),
        )
        for candidate, cell in zip(candidates, assessed, strict=True)
        if cell.cell_identity_tier == CellIdentityTier.TIER1
    )
    if not tier1:
        return min(assessed, key=_non_tier1_fallback_key)
    if len(tier1) == 1:
        return tier1[0][1]

    ranked = sorted(
        tier1,
        key=lambda item: _tier1_tie_break_key(request, item[0], center, item[2]),
    )
    first_key = _tier1_tie_break_key(
        request, ranked[0][0], center, ranked[0][2]
    )
    second_key = _tier1_tie_break_key(
        request, ranked[1][0], center, ranked[1][2]
    )
    if first_key == second_key:
        return _ambiguous_cell(ranked[0][1])
    return ranked[0][1]


def evaluate_cell_evidence(
    request: IdentityCoherenceRequest,
    candidate: CellCandidateEvidence,
    center: RtCenterResult,
    config: IdentityCoherenceConfig,
    *,
    identity_family_id: str,
    shape_reference: ShapeReferenceResult | None = None,
    prototype_width: PrototypeWidthResult | None = None,
) -> CellEvidenceResult:
    if (
        _enum_value(candidate.candidate_evidence.evidence_stage)
        != EvidenceStage.PRE_BACKFILL.value
    ):
        return _blocked_cell(
            request,
            candidate,
            identity_family_id,
            CellBlockedReason.BACKFILL_ONLY_EVIDENCE.value,
        )
    if candidate.blocked_reason:
        return _blocked_cell(
            request,
            candidate,
            identity_family_id,
            candidate.blocked_reason,
        )
    if candidate.data_quality_reason:
        return _data_quality_cell(
            request,
            candidate,
            identity_family_id,
            candidate.data_quality_reason,
        )
    if not _has_valid_morphology(candidate):
        return _data_quality_cell(
            request,
            candidate,
            identity_family_id,
            CellDataQualityReason.INVALID_PEAK_MORPHOLOGY.value,
        )

    rt_delta_center_sec = (float(candidate.apex_rt) - center.center_rt_min) * 60.0
    rt_gate_status = (
        RtGateStatus.PASS
        if abs(rt_delta_center_sec) <= config.rt.preferred_rt_sec
        else RtGateStatus.FAIL
    )
    candidate_match = match_identity_constraints_to_candidate(
        request,
        candidate.candidate_evidence,
    )
    fragment_match_status = _fragment_match_status(candidate_match)
    non_rt_identity_result = (
        NonRtIdentityResult.PASS
        if _enum_value(candidate_match.request_candidate_identity_status)
        == RequestCandidateIdentityStatus.MATCH.value
        else NonRtIdentityResult.FAIL
    )
    prototype_width_sec = (
        prototype_width.prototype_width_sec if prototype_width is not None else None
    )
    width_assessment = assess_width_against_prototype(
        candidate,
        prototype_width_sec=prototype_width_sec,
        config=config,
    )
    shape_comparison = compare_shape_to_reference(
        candidate,
        shape_reference,
        config,
        width_sanity_status=width_assessment.width_status,
    )

    rt_gate_pass = _enum_value(rt_gate_status) == RtGateStatus.PASS.value
    non_rt_pass = (
        _enum_value(non_rt_identity_result) == NonRtIdentityResult.PASS.value
    )
    shape_pass = (
        _enum_value(shape_comparison.shape_status) == ShapeStatus.PASS.value
    )
    width_pass = (
        _enum_value(width_assessment.width_status) == WidthStatus.PASS.value
    )

    if rt_gate_pass and non_rt_pass:
        tier = CellIdentityTier.TIER1
        basis = CellIdentityBasis.RT_FRAGMENT_SUPPORT
        coherent = True
        tier12 = True
    elif rt_gate_pass and shape_pass:
        tier = CellIdentityTier.TIER2
        basis = CellIdentityBasis.RT_SHAPE_SIMILARITY
        coherent = True
        tier12 = True
    elif rt_gate_pass and width_pass:
        tier = CellIdentityTier.TIER3
        basis = CellIdentityBasis.RT_PROTOTYPE_WIDTH
        coherent = True
        tier12 = False
    else:
        tier = CellIdentityTier.RT_ONLY
        basis = CellIdentityBasis.NONE
        coherent = False
        tier12 = False

    return _cell(
        request,
        candidate,
        identity_family_id,
        cell_assessment_status=CellAssessmentStatus.ASSESSED,
        cell_identity_tier=tier,
        cell_identity_basis=basis,
        fragment_match_status=fragment_match_status,
        rt_delta_center_sec=rt_delta_center_sec,
        rt_gate_status=rt_gate_status,
        area_height_status=AreaHeightStatus.PASS,
        non_rt_identity_result=non_rt_identity_result,
        coherent_count_contribution=coherent,
        tier12_count_contribution=tier12,
        blocked_reason="",
        data_quality_reason="",
        shape_status=shape_comparison.shape_status,
        shape_similarity_cosine=shape_comparison.shape_similarity_cosine,
        shape_reference_basis=shape_comparison.shape_reference_basis,
        shape_reference_candidate_id=shape_comparison.shape_reference_candidate_id,
        shape_fallback_used=shape_comparison.shape_fallback_used,
        shape_audit_status=shape_comparison.shape_audit_status,
        width_status=width_assessment.width_status,
        width_ratio_to_prototype=width_assessment.width_ratio_to_prototype,
    )


def _blocked_cell(
    request: IdentityCoherenceRequest,
    candidate: CellCandidateEvidence,
    identity_family_id: str,
    reason: str,
) -> CellEvidenceResult:
    return _cell(
        request,
        candidate,
        identity_family_id,
        cell_assessment_status=CellAssessmentStatus.BLOCKED,
        cell_identity_tier=CellIdentityTier.BLOCKED,
        cell_identity_basis=CellIdentityBasis.NONE,
        fragment_match_status=FragmentMatchStatus.NOT_ASSESSED,
        rt_delta_center_sec=None,
        rt_gate_status=RtGateStatus.NOT_ASSESSED,
        area_height_status=AreaHeightStatus.NOT_ASSESSED,
        non_rt_identity_result=NonRtIdentityResult.BLOCKED,
        coherent_count_contribution=False,
        tier12_count_contribution=False,
        blocked_reason=reason,
        data_quality_reason="",
    )


def _data_quality_cell(
    request: IdentityCoherenceRequest,
    candidate: CellCandidateEvidence,
    identity_family_id: str,
    reason: str,
) -> CellEvidenceResult:
    return _cell(
        request,
        candidate,
        identity_family_id,
        cell_assessment_status=CellAssessmentStatus.DATA_QUALITY_REJECT,
        cell_identity_tier=CellIdentityTier.DATA_QUALITY,
        cell_identity_basis=CellIdentityBasis.NONE,
        fragment_match_status=FragmentMatchStatus.NOT_ASSESSED,
        rt_delta_center_sec=None,
        rt_gate_status=RtGateStatus.NOT_ASSESSED,
        area_height_status=AreaHeightStatus.FAIL,
        non_rt_identity_result=NonRtIdentityResult.NOT_ASSESSED,
        coherent_count_contribution=False,
        tier12_count_contribution=False,
        blocked_reason="",
        data_quality_reason=reason,
    )


def _cell(
    request: IdentityCoherenceRequest,
    candidate: CellCandidateEvidence,
    identity_family_id: str,
    *,
    cell_assessment_status: CellAssessmentStatus,
    cell_identity_tier: CellIdentityTier,
    cell_identity_basis: CellIdentityBasis,
    fragment_match_status: FragmentMatchStatus,
    rt_delta_center_sec: float | None,
    rt_gate_status: RtGateStatus,
    area_height_status: AreaHeightStatus,
    non_rt_identity_result: NonRtIdentityResult,
    coherent_count_contribution: bool,
    tier12_count_contribution: bool,
    blocked_reason: str,
    data_quality_reason: str,
    shape_status: ShapeStatus = ShapeStatus.NOT_ASSESSED,
    shape_similarity_cosine: float | None = None,
    shape_reference_basis: ShapeReferenceBasis = ShapeReferenceBasis.NONE,
    shape_reference_candidate_id: str = "",
    shape_fallback_used: bool = False,
    shape_audit_status: ShapeAuditStatus = ShapeAuditStatus.NOT_ASSESSED,
    width_status: WidthStatus = WidthStatus.NOT_ASSESSED,
    width_ratio_to_prototype: float | None = None,
) -> CellEvidenceResult:
    return CellEvidenceResult(
        decision_id=request.decision_id,
        identity_family_id=identity_family_id,
        sample_id=candidate.sample_id,
        candidate_id=candidate.candidate_evidence.candidate_id,
        cell_assessment_status=cell_assessment_status,
        cell_identity_tier=cell_identity_tier,
        cell_identity_basis=cell_identity_basis,
        fragment_observation_mode=request.identity.fragment_observation_mode,
        fragment_match_status=fragment_match_status,
        fragment_tags_supported=candidate.candidate_evidence.fragment_tags,
        rt_delta_center_sec=rt_delta_center_sec,
        rt_gate_status=rt_gate_status,
        shape_status=shape_status,
        shape_similarity_cosine=shape_similarity_cosine,
        shape_reference_basis=shape_reference_basis,
        shape_reference_candidate_id=shape_reference_candidate_id,
        shape_fallback_used=shape_fallback_used,
        shape_audit_status=shape_audit_status,
        width_status=width_status,
        width_ratio_to_prototype=width_ratio_to_prototype,
        baseline_audit_status=BaselineAuditStatus.NOT_ASSESSED,
        area_height_status=area_height_status,
        non_rt_identity_result=non_rt_identity_result,
        coherent_count_contribution=coherent_count_contribution,
        tier12_count_contribution=tier12_count_contribution,
        blocked_reason=blocked_reason,
        data_quality_reason=data_quality_reason,
        forbidden_evidence_seen=(
            candidate.forbidden_evidence_seen
            or _enum_value(candidate.candidate_evidence.evidence_stage)
            != EvidenceStage.PRE_BACKFILL.value
        ),
    )


def _tier1_tie_break_key(
    request: IdentityCoherenceRequest,
    candidate: CellCandidateEvidence,
    center: RtCenterResult,
    candidate_match: CandidateIdentityMatch,
) -> tuple[float, float, float, float]:
    requested_tags = set(request.identity.fragment_tags)
    supported_tags = set(candidate_match.fragment_tags_supported)
    tag_set_penalty = 0.0 if supported_tags == requested_tags else 1.0
    rt_delta_sec = (float(candidate.apex_rt) - center.center_rt_min) * 60.0
    return (
        tag_set_penalty,
        _abs_or_inf(candidate_match.precursor_error_ppm),
        _abs_or_inf(candidate_match.cid_observed_loss_error_ppm),
        abs(rt_delta_sec),
    )


def _non_tier1_fallback_key(
    cell: CellEvidenceResult,
) -> tuple[int, int, float, str]:
    tier_rank = {
        CellIdentityTier.TIER2.value: 0,
        CellIdentityTier.TIER3.value: 1,
    }.get(_enum_value(cell.cell_identity_tier), 2)
    rt_pass_penalty = (
        0
        if _enum_value(cell.rt_gate_status) == RtGateStatus.PASS.value
        else 1
    )
    rt_delta = _abs_or_inf(cell.rt_delta_center_sec)
    return (tier_rank, rt_pass_penalty, rt_delta, cell.candidate_id)


def _ambiguous_cell(cell: CellEvidenceResult) -> CellEvidenceResult:
    return replace(
        cell,
        cell_identity_tier=CellIdentityTier.RT_ONLY,
        cell_identity_basis=CellIdentityBasis.NONE,
        fragment_match_status=FragmentMatchStatus.AMBIGUOUS,
        non_rt_identity_result=NonRtIdentityResult.FAIL,
        coherent_count_contribution=False,
        tier12_count_contribution=False,
    )


def _abs_or_inf(value: float | None) -> float:
    return abs(value) if value is not None else math.inf


def _fragment_match_status(
    candidate_match: CandidateIdentityMatch,
) -> FragmentMatchStatus:
    if (
        _enum_value(candidate_match.request_candidate_identity_status)
        == RequestCandidateIdentityStatus.MATCH.value
    ):
        return FragmentMatchStatus.PASS
    return FragmentMatchStatus.FAIL


def _has_valid_morphology(candidate: CellCandidateEvidence) -> bool:
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
