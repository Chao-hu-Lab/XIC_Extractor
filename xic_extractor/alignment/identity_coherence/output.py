from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from .models import (
    CellEvidenceResult,
    IdentityDecisionSummary,
    SeedGateResult,
)
from .row_evaluator import IdentityCoherenceRowResult
from .schema import (
    IDENTITY_COHERENCE_CELL_EVIDENCE_COLUMNS,
    IDENTITY_COHERENCE_CONTROL_COLUMNS,
    IDENTITY_COHERENCE_DECISION_COLUMNS,
    IDENTITY_COHERENCE_REQUEST_COLUMNS,
    RequestCandidateIdentityStatus,
    RequestIdentityCompletenessStatus,
)
from .tags import format_fragment_tags


@dataclass(frozen=True)
class IdentityCoherenceOutputRecord:
    seed_gate: SeedGateResult
    row_result: IdentityCoherenceRowResult


@dataclass(frozen=True)
class IdentityCoherenceOutputContext:
    command: str
    mode: str
    input_source: str
    input_hashes: tuple[tuple[str, str], ...] = ()
    control_manifest_path: str = "not_provided"
    raw_xic_request_count: int | None = None
    xic_point_count: int | None = None
    projected_85raw_identity_request_count: int | None = None


@dataclass(frozen=True)
class IdentityCoherenceOutputPaths:
    requests_tsv: Path
    decisions_tsv: Path
    cell_evidence_tsv: Path
    controls_tsv: Path
    summary_md: Path


def project_request_row(seed_gate: SeedGateResult) -> dict[str, str]:
    request = seed_gate.resolved_request
    _validate_frozen_request_status(request)
    identity = request.identity
    match = seed_gate.candidate_match
    values = {
        "request_id": request.request_id,
        "decision_id": request.decision_id,
        "seed_candidate_id": request.seed_candidate_id,
        "seed_sample": request.seed_sample,
        "fragment_observation_mode": identity.fragment_observation_mode,
        "precursor_mz": identity.precursor_mz,
        "product_mz": identity.product_mz,
        "fragment_tags": format_fragment_tags(identity.fragment_tags),
        "fragment_tag_match_policy": identity.fragment_tag_match_policy,
        "fragment_profile_id": identity.fragment_profile_id,
        "fragment_profile_hash": identity.fragment_profile_hash,
        "precursor_tolerance_ppm": identity.precursor_tolerance_ppm,
        "product_tolerance_ppm": identity.product_tolerance_ppm,
        "cid_observed_loss_da": identity.mode_constraint.cid_observed_loss_da,
        "cid_observed_loss_tolerance_ppm": (
            identity.mode_constraint.cid_observed_loss_tolerance_ppm
        ),
        "request_identity_completeness_status": (
            request.request_identity_completeness_status
        ),
        "request_candidate_identity_status": (
            request.request_candidate_identity_status
        ),
        "precursor_error_ppm": match.precursor_error_ppm,
        "product_error_ppm": match.product_error_ppm,
        "cid_observed_loss_error_ppm": match.cid_observed_loss_error_ppm,
        "cid_observed_loss_error_da": match.cid_observed_loss_error_da,
        "request_builder_flags": request.request_builder_flags,
    }
    return _project_columns(IDENTITY_COHERENCE_REQUEST_COLUMNS, values)


def project_decision_row(summary: IdentityDecisionSummary) -> dict[str, str]:
    _validate_decision_summary(summary)
    values = {
        "decision_id": summary.decision_id,
        "identity_family_id": summary.identity_family_id,
        "seed_candidate_id": summary.seed_candidate_id,
        "seed_sample": summary.seed_sample,
        "seed_gate_class": summary.seed_gate_class,
        "decision": summary.decision,
        "decision_reason": summary.decision_reason,
        "request_identity_completeness_status": (
            summary.request_identity_completeness_status
        ),
        "request_candidate_identity_status": (
            summary.request_candidate_identity_status
        ),
        "total_coherent_sample_count": summary.total_coherent_sample_count,
        "non_seed_coherent_sample_count": summary.non_seed_coherent_sample_count,
        "tier12_non_seed_identity_sample_count": (
            summary.tier12_non_seed_identity_sample_count
        ),
        "tier1_fragment_confirmed_sample_count": (
            summary.tier1_fragment_confirmed_sample_count
        ),
        "tier2_shape_supported_sample_count": (
            summary.tier2_shape_supported_sample_count
        ),
        "tier2_seed_shape_fallback_sample_count": (
            summary.tier2_seed_shape_fallback_sample_count
        ),
        "tier3_width_only_sample_count": summary.tier3_width_only_sample_count,
        "min_total_coherent_samples": summary.min_total_coherent_samples,
        "min_non_seed_coherent_samples": summary.min_non_seed_coherent_samples,
        "min_non_seed_tier12_identity_samples": (
            summary.min_non_seed_tier12_identity_samples
        ),
        "weak_basis_reason": summary.weak_basis_reason,
        "shape_reference_basis": summary.shape_reference_basis,
        "shape_reference_candidate_id": summary.shape_reference_candidate_id,
        "prototype_width_sec": summary.prototype_width_sec,
        "center_rt_sec": summary.center.center_rt_sec,
        "center_rt_source": summary.center_rt_source,
        "coherent_fraction": summary.coherent_fraction,
        "infrastructure_blocked_sample_count": (
            summary.infrastructure_blocked_sample_count
        ),
        "data_quality_reject_sample_count": (
            summary.data_quality_reject_sample_count
        ),
        "forbidden_evidence_used": summary.forbidden_evidence_used,
    }
    return _project_columns(IDENTITY_COHERENCE_DECISION_COLUMNS, values)


def project_cell_evidence_row(cell: CellEvidenceResult) -> dict[str, str]:
    values = {
        "decision_id": cell.decision_id,
        "identity_family_id": cell.identity_family_id,
        "sample_id": cell.sample_id,
        "candidate_id": cell.candidate_id,
        "cell_assessment_status": cell.cell_assessment_status,
        "cell_identity_tier": cell.cell_identity_tier,
        "cell_identity_basis": cell.cell_identity_basis,
        "fragment_observation_mode": cell.fragment_observation_mode,
        "fragment_match_status": cell.fragment_match_status,
        "fragment_tags_supported": format_fragment_tags(
            cell.fragment_tags_supported,
        ),
        "rt_delta_center_sec": cell.rt_delta_center_sec,
        "rt_gate_status": cell.rt_gate_status,
        "shape_status": cell.shape_status,
        "shape_similarity_cosine": cell.shape_similarity_cosine,
        "shape_reference_basis": cell.shape_reference_basis,
        "shape_reference_candidate_id": cell.shape_reference_candidate_id,
        "shape_fallback_used": cell.shape_fallback_used,
        "shape_audit_status": cell.shape_audit_status,
        "width_status": cell.width_status,
        "width_ratio_to_prototype": cell.width_ratio_to_prototype,
        "baseline_audit_status": cell.baseline_audit_status,
        "area_height_status": cell.area_height_status,
        "non_rt_identity_result": cell.non_rt_identity_result,
        "coherent_count_contribution": cell.coherent_count_contribution,
        "tier12_count_contribution": cell.tier12_count_contribution,
        "blocked_reason": cell.blocked_reason,
        "data_quality_reason": cell.data_quality_reason,
        "forbidden_evidence_seen": cell.forbidden_evidence_seen,
    }
    return _project_columns(IDENTITY_COHERENCE_CELL_EVIDENCE_COLUMNS, values)


def project_control_row(row: Mapping[str, object]) -> dict[str, str]:
    return _project_columns(IDENTITY_COHERENCE_CONTROL_COLUMNS, row)


def _validate_frozen_request_status(request: object) -> None:
    completeness = _enum_value(request.request_identity_completeness_status)
    candidate_status = _enum_value(request.request_candidate_identity_status)
    if (
        completeness == RequestIdentityCompletenessStatus.COMPLETE.value
        and candidate_status == RequestCandidateIdentityStatus.NOT_ASSESSED.value
    ):
        raise ValueError("complete request cannot be emitted as not_assessed")


def _validate_decision_summary(summary: IdentityDecisionSummary) -> None:
    if summary.forbidden_evidence_used:
        raise ValueError("forbidden_evidence_used cannot be emitted")


def _project_columns(
    columns: tuple[str, ...],
    values: Mapping[str, object],
) -> dict[str, str]:
    return {column: _format_tsv_value(values.get(column)) for column in columns}


def _format_tsv_value(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            return ""
        return f"{value:.12g}"
    if isinstance(value, tuple):
        return ";".join(_format_tsv_value(item) for item in value)
    if isinstance(value, list):
        return ";".join(_format_tsv_value(item) for item in value)
    if isinstance(value, set):
        return ";".join(_format_tsv_value(item) for item in sorted(value))
    text = str(value)
    if text.startswith(("=", "+", "-", "@")):
        return f"'{text}"
    return text


def _enum_value(value: object) -> object:
    if isinstance(value, Enum):
        return value.value
    return value
