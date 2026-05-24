from __future__ import annotations

import math
from dataclasses import dataclass
from typing import cast

import numpy as np

from .models import (
    CellCandidateEvidence,
    IdentityCoherenceConfig,
    ShapeComparisonResult,
    ShapeReferenceResult,
)
from .schema import (
    CellIdentityTier,
    EvidenceStage,
    ShapeAuditStatus,
    ShapeReferenceBasis,
    ShapeStatus,
    WidthStatus,
)

_SHAPE_OWNER_ASSIGNMENT_STATUSES = {"primary", "supporting"}
_SHAPE_FAIL_AUDIT_STATUSES = {
    ShapeAuditStatus.FAIL.value,
    ShapeAuditStatus.SHOULDER.value,
    ShapeAuditStatus.BIMODAL.value,
    ShapeAuditStatus.COELUTION.value,
    ShapeAuditStatus.SATURATED.value,
    ShapeAuditStatus.CLIPPED.value,
}


@dataclass(frozen=True)
class NormalizedShapeTrace:
    shape_status: ShapeStatus
    normalized_intensity: tuple[float, ...]
    shape_audit_status: ShapeAuditStatus


def normalize_trace_for_shape(
    candidate: CellCandidateEvidence,
    config: IdentityCoherenceConfig,
) -> NormalizedShapeTrace:
    audit_status = _trace_audit_status(candidate)
    if _enum_value(audit_status) in _SHAPE_FAIL_AUDIT_STATUSES:
        return NormalizedShapeTrace(
            shape_status=ShapeStatus.FAIL,
            normalized_intensity=(),
            shape_audit_status=audit_status,
        )
    if candidate.trace is None:
        return NormalizedShapeTrace(
            shape_status=ShapeStatus.NOT_ASSESSED,
            normalized_intensity=(),
            shape_audit_status=ShapeAuditStatus.NOT_ASSESSED,
        )
    morphology = _morphology_values(candidate)
    if morphology is None:
        return NormalizedShapeTrace(
            shape_status=ShapeStatus.NOT_ASSESSED,
            normalized_intensity=(),
            shape_audit_status=audit_status,
        )
    if candidate.point_count is None or candidate.point_count < config.shape.min_points:
        return NormalizedShapeTrace(
            shape_status=ShapeStatus.LOW_POINTS,
            normalized_intensity=(),
            shape_audit_status=audit_status,
        )
    if len(candidate.trace.rt_min) != len(candidate.trace.intensity):
        return NormalizedShapeTrace(
            shape_status=ShapeStatus.NOT_ASSESSED,
            normalized_intensity=(),
            shape_audit_status=audit_status,
        )

    _apex_rt, peak_start_rt, peak_end_rt, _area, _height = morphology
    rt_values = np.asarray(candidate.trace.rt_min, dtype=float)
    intensity_values = np.asarray(candidate.trace.intensity, dtype=float)
    finite = np.isfinite(rt_values) & np.isfinite(intensity_values)
    inside = (
        (rt_values >= peak_start_rt)
        & (rt_values <= peak_end_rt)
        & finite
    )
    rt_inside = rt_values[inside]
    intensity_inside = intensity_values[inside]
    if rt_inside.size < config.shape.min_points:
        return NormalizedShapeTrace(
            shape_status=ShapeStatus.LOW_POINTS,
            normalized_intensity=(),
            shape_audit_status=audit_status,
        )

    order = np.argsort(rt_inside)
    rt_inside = rt_inside[order]
    intensity_inside = intensity_inside[order]
    shifted = np.clip(intensity_inside - np.min(intensity_inside), 0.0, None)

    normalized_positions = (
        (rt_inside - peak_start_rt)
        / (peak_end_rt - peak_start_rt)
    )
    target_positions = np.linspace(0.0, 1.0, config.shape.resample_points)
    resampled = np.interp(target_positions, normalized_positions, shifted)
    norm = float(np.linalg.norm(resampled))
    if not math.isfinite(norm) or norm <= 0.0:
        return NormalizedShapeTrace(
            shape_status=ShapeStatus.ZERO_SIGNAL,
            normalized_intensity=(),
            shape_audit_status=audit_status,
        )

    normalized = tuple(float(value) for value in resampled / norm)
    return NormalizedShapeTrace(
        shape_status=ShapeStatus.PASS,
        normalized_intensity=normalized,
        shape_audit_status=audit_status,
    )


def estimate_shape_reference(
    candidates: tuple[CellCandidateEvidence, ...],
    config: IdentityCoherenceConfig,
    *,
    seed_sample_id: str | None,
    tier_by_candidate_id: dict[str, CellIdentityTier],
    center_rt_min: float,
) -> ShapeReferenceResult:
    usable = tuple(
        (candidate, normalized)
        for candidate in candidates
        if _is_shape_candidate(
            candidate,
            config,
            seed_sample_id=seed_sample_id,
            center_rt_min=center_rt_min,
        )
        for normalized in (normalize_trace_for_shape(candidate, config),)
        if normalized.shape_status is ShapeStatus.PASS
    )
    non_seed_count = len(usable)
    if len(usable) < config.shape.prototype_min_candidates:
        return _empty_shape_reference(non_seed_count)
    if non_seed_count < config.shape.prototype_min_non_seed_candidates:
        return _empty_shape_reference(non_seed_count)

    medoid_candidate, medoid_trace = _select_medoid(
        usable,
        tier_by_candidate_id,
        center_rt_min=center_rt_min,
    )
    medoid_tier = tier_by_candidate_id.get(
        medoid_candidate.candidate_evidence.candidate_id
    )
    basis = (
        ShapeReferenceBasis.TIER1_SUPPORTED_MEDOID
        if _enum_value(medoid_tier) == CellIdentityTier.TIER1.value
        else ShapeReferenceBasis.MORPHOLOGY_RT_MEDOID
    )
    if (
        _enum_value(basis) == ShapeReferenceBasis.MORPHOLOGY_RT_MEDOID.value
        and not config.shape.allow_morphology_rt_medoid
    ):
        return _empty_shape_reference(non_seed_count)
    return ShapeReferenceResult(
        shape_reference_basis=basis,
        shape_reference_candidate_id=medoid_candidate.candidate_evidence.candidate_id,
        normalized_intensity=medoid_trace.normalized_intensity,
        candidate_count=len(usable),
        non_seed_candidate_count=non_seed_count,
        seed_fallback_used=False,
    )


def create_seed_shape_reference(
    seed_candidate: CellCandidateEvidence,
    config: IdentityCoherenceConfig,
) -> ShapeReferenceResult:
    if not config.shape.allow_seed_shape_fallback:
        return _empty_shape_reference(0)
    normalized = normalize_trace_for_shape(seed_candidate, config)
    if normalized.shape_status is not ShapeStatus.PASS:
        return _empty_shape_reference(0)
    return ShapeReferenceResult(
        shape_reference_basis=ShapeReferenceBasis.SEED_FALLBACK,
        shape_reference_candidate_id=seed_candidate.candidate_evidence.candidate_id,
        normalized_intensity=normalized.normalized_intensity,
        candidate_count=1,
        non_seed_candidate_count=0,
        seed_fallback_used=True,
    )


def compare_shape_to_reference(
    candidate: CellCandidateEvidence,
    reference: ShapeReferenceResult | None,
    config: IdentityCoherenceConfig,
    *,
    width_sanity_status: WidthStatus,
) -> ShapeComparisonResult:
    if _enum_value(width_sanity_status) != WidthStatus.PASS.value:
        return _shape_comparison(
            ShapeStatus.NOT_ASSESSED,
            reference,
            shape_similarity_cosine=None,
            shape_audit_status=ShapeAuditStatus.NOT_ASSESSED,
        )
    if reference is None or not reference.normalized_intensity:
        return _shape_comparison(
            ShapeStatus.NOT_ASSESSED,
            reference,
            shape_similarity_cosine=None,
            shape_audit_status=ShapeAuditStatus.NOT_ASSESSED,
        )

    normalized = normalize_trace_for_shape(candidate, config)
    if normalized.shape_status is not ShapeStatus.PASS:
        return _shape_comparison(
            normalized.shape_status,
            reference,
            shape_similarity_cosine=None,
            shape_audit_status=normalized.shape_audit_status,
        )

    similarity = _cosine(
        normalized.normalized_intensity,
        reference.normalized_intensity,
    )
    status = (
        ShapeStatus.PASS
        if similarity >= config.shape.min_cosine
        else ShapeStatus.FAIL
    )
    return _shape_comparison(
        status,
        reference,
        shape_similarity_cosine=similarity,
        shape_audit_status=normalized.shape_audit_status,
    )


def _is_shape_candidate(
    candidate: CellCandidateEvidence,
    config: IdentityCoherenceConfig,
    *,
    seed_sample_id: str | None,
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
    if candidate.owner_assignment_status not in _SHAPE_OWNER_ASSIGNMENT_STATUSES:
        return False
    if not _has_complete_morphology(candidate):
        return False
    apex_rt = _candidate_apex_rt(candidate)
    center_delta_sec = abs(apex_rt - center_rt_min) * 60.0
    return center_delta_sec <= config.rt.preferred_rt_sec


def _select_medoid(
    usable: tuple[tuple[CellCandidateEvidence, NormalizedShapeTrace], ...],
    tier_by_candidate_id: dict[str, CellIdentityTier],
    *,
    center_rt_min: float,
) -> tuple[CellCandidateEvidence, NormalizedShapeTrace]:
    scored: list[
        tuple[
            float,
            int,
            float,
            float,
            str,
            CellCandidateEvidence,
            NormalizedShapeTrace,
        ]
    ] = []
    for candidate, normalized in usable:
        similarities = tuple(
            _cosine(normalized.normalized_intensity, other.normalized_intensity)
            for _, other in usable
            if other is not normalized
        )
        mean_similarity = (
            sum(similarities) / len(similarities) if similarities else 1.0
        )
        tier_rank = (
            0
            if _enum_value(
                tier_by_candidate_id.get(candidate.candidate_evidence.candidate_id)
            )
            == CellIdentityTier.TIER1.value
            else 1
        )
        scan_support = candidate.candidate_evidence.ms1_scan_support_score
        scored.append(
            (
                -mean_similarity,
                tier_rank,
                -float(cast(float, scan_support))
                if _finite_number(scan_support)
                else 0.0,
                abs(_candidate_apex_rt(candidate) - center_rt_min),
                candidate.candidate_evidence.candidate_id,
                candidate,
                normalized,
            )
        )
    scored.sort()
    return scored[0][5], scored[0][6]


def _trace_audit_status(candidate: CellCandidateEvidence) -> ShapeAuditStatus:
    if candidate.trace is None:
        return ShapeAuditStatus.NOT_ASSESSED
    value = _enum_value(candidate.trace.shape_audit_status)
    try:
        return ShapeAuditStatus(value)
    except ValueError:
        return ShapeAuditStatus.UNAVAILABLE


def _shape_comparison(
    status: ShapeStatus,
    reference: ShapeReferenceResult | None,
    *,
    shape_similarity_cosine: float | None,
    shape_audit_status: ShapeAuditStatus,
) -> ShapeComparisonResult:
    return ShapeComparisonResult(
        shape_status=status,
        shape_similarity_cosine=shape_similarity_cosine,
        shape_reference_basis=(
            reference.shape_reference_basis
            if reference is not None
            else ShapeReferenceBasis.NONE
        ),
        shape_reference_candidate_id=(
            reference.shape_reference_candidate_id if reference is not None else ""
        ),
        shape_fallback_used=(
            reference.seed_fallback_used if reference is not None else False
        ),
        shape_audit_status=shape_audit_status,
    )


def _empty_shape_reference(non_seed_candidate_count: int) -> ShapeReferenceResult:
    return ShapeReferenceResult(
        shape_reference_basis=ShapeReferenceBasis.NONE,
        shape_reference_candidate_id="",
        normalized_intensity=(),
        candidate_count=non_seed_candidate_count,
        non_seed_candidate_count=non_seed_candidate_count,
        seed_fallback_used=False,
    )


def _cosine(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    left_values = np.asarray(left, dtype=float)
    right_values = np.asarray(right, dtype=float)
    if left_values.size != right_values.size:
        return 0.0
    return float(np.dot(left_values, right_values))


def _candidate_apex_rt(candidate: CellCandidateEvidence) -> float:
    return float(cast(float, candidate.apex_rt))


def _morphology_values(
    candidate: CellCandidateEvidence,
) -> tuple[float, float, float, float, float] | None:
    values = (
        candidate.apex_rt,
        candidate.peak_start_rt,
        candidate.peak_end_rt,
        candidate.area,
        candidate.height,
    )
    if any(not _finite_number(value) for value in values):
        return None
    apex_rt = float(cast(float, candidate.apex_rt))
    peak_start_rt = float(cast(float, candidate.peak_start_rt))
    peak_end_rt = float(cast(float, candidate.peak_end_rt))
    area = float(cast(float, candidate.area))
    height = float(cast(float, candidate.height))
    if not (peak_start_rt < apex_rt < peak_end_rt and area > 0.0 and height > 0.0):
        return None
    return apex_rt, peak_start_rt, peak_end_rt, area, height


def _has_complete_morphology(candidate: CellCandidateEvidence) -> bool:
    return _morphology_values(candidate) is not None


def _finite_number(value: object) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(value)
    )


def _enum_value(value: object) -> str:
    return str(getattr(value, "value", value))
