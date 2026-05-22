from __future__ import annotations

import math
from dataclasses import replace
from typing import Any

from .candidate_matcher import match_request_to_candidate
from .models import (
    CandidateIdentityMatch,
    IdentityCoherenceRequest,
    SeedCandidateEvidence,
    SeedGateConfig,
    SeedGateResult,
)
from .schema import (
    EvidenceStage,
    RequestCandidateIdentityStatus,
    RequestIdentityCompletenessStatus,
    SeedGateClass,
    SeedRejectReason,
)

_ALLOWED_OWNER_ASSIGNMENT_STATUSES = {
    "primary",
    "supporting",
    "ambiguous",
    "unresolved",
}


def evaluate_seed_gate(
    request: IdentityCoherenceRequest,
    candidate_evidence: SeedCandidateEvidence | None,
    owner_like: object | None,
    *,
    owner_assignment_status: str = "primary",
    duplicate_loser: bool = False,
    owner_evidence_stage: EvidenceStage = EvidenceStage.PRE_BACKFILL,
    config: SeedGateConfig = SeedGateConfig(),
) -> SeedGateResult:
    review_flags: list[str] = []
    candidate_match = match_request_to_candidate(request, candidate_evidence)
    candidate_status = candidate_match.request_candidate_identity_status
    resolved_request = replace(
        request,
        request_candidate_identity_status=candidate_status,
    )

    if (
        request.request_identity_completeness_status
        != RequestIdentityCompletenessStatus.COMPLETE
    ):
        return _result(
            resolved_request,
            candidate_match,
            SeedRejectReason.MISSING_REQUEST_IDENTITY_CONSTRAINT,
            review_flags,
        )
    if (
        candidate_status
        == RequestCandidateIdentityStatus.UNSUPPORTED_FRAGMENT_OBSERVATION_MODE
    ):
        return _result(
            resolved_request,
            candidate_match,
            SeedRejectReason.UNSUPPORTED_FRAGMENT_OBSERVATION_MODE,
            review_flags,
        )
    if (
        candidate_status
        == RequestCandidateIdentityStatus.MISSING_DISCOVERY_CANDIDATE_JOIN
    ):
        return _result(
            resolved_request,
            candidate_match,
            SeedRejectReason.MISSING_DISCOVERY_CANDIDATE_JOIN,
            review_flags,
        )
    if (
        candidate_status
        == RequestCandidateIdentityStatus.MISSING_DIAGNOSTIC_FRAGMENT_EVIDENCE
    ):
        return _result(
            resolved_request,
            candidate_match,
            SeedRejectReason.MISSING_DIAGNOSTIC_FRAGMENT_EVIDENCE,
            review_flags,
        )
    if (
        candidate_status
        == RequestCandidateIdentityStatus.REQUEST_CANDIDATE_IDENTITY_MISMATCH
    ):
        return _result(
            resolved_request,
            candidate_match,
            SeedRejectReason.REQUEST_CANDIDATE_IDENTITY_MISMATCH,
            review_flags,
        )

    if (
        candidate_evidence.evidence_stage != EvidenceStage.PRE_BACKFILL
        or owner_evidence_stage != EvidenceStage.PRE_BACKFILL
    ):
        return _result(
            resolved_request,
            candidate_match,
            SeedRejectReason.BACKFILL_ONLY_EVIDENCE,
            review_flags,
        )

    if owner_like is None:
        return _result(
            resolved_request,
            candidate_match,
            SeedRejectReason.NO_QUANTIFIABLE_OWNER,
            review_flags,
        )

    if owner_assignment_status not in _ALLOWED_OWNER_ASSIGNMENT_STATUSES:
        return _result(
            resolved_request,
            candidate_match,
            SeedRejectReason.AMBIGUOUS_OWNER,
            review_flags,
        )
    if owner_assignment_status == "unresolved":
        return _result(
            resolved_request,
            candidate_match,
            SeedRejectReason.NO_QUANTIFIABLE_OWNER,
            review_flags,
        )
    if owner_assignment_status == "ambiguous":
        return _result(
            resolved_request,
            candidate_match,
            SeedRejectReason.AMBIGUOUS_OWNER,
            review_flags,
        )
    if duplicate_loser:
        return _result(
            resolved_request,
            candidate_match,
            SeedRejectReason.DUPLICATE_LOSER,
            review_flags,
        )

    owner_values = {
        "owner_apex_rt": _getattr_or_none(owner_like, "owner_apex_rt"),
        "owner_peak_start_rt": _getattr_or_none(owner_like, "owner_peak_start_rt"),
        "owner_peak_end_rt": _getattr_or_none(owner_like, "owner_peak_end_rt"),
        "owner_area": _getattr_or_none(owner_like, "owner_area"),
        "owner_height": _getattr_or_none(owner_like, "owner_height"),
    }
    if any(not _finite_number(value) for value in owner_values.values()):
        return _result(
            resolved_request,
            candidate_match,
            SeedRejectReason.NONFINITE_PEAK,
            review_flags,
        )

    seed_rt = candidate_evidence.best_seed_rt
    if not _finite_number(seed_rt):
        return _result(
            resolved_request,
            candidate_match,
            SeedRejectReason.NONFINITE_PEAK,
            review_flags,
        )
    if (
        config.require_seed_rt_inside_owner_peak
        and not (
            owner_values["owner_peak_start_rt"]
            <= seed_rt
            <= owner_values["owner_peak_end_rt"]
        )
    ):
        return _result(
            resolved_request,
            candidate_match,
            SeedRejectReason.SEED_RT_OUTSIDE_OWNER_PEAK,
            review_flags,
        )

    scan_support = candidate_evidence.ms1_scan_support_score
    if scan_support is None:
        review_flags.append("ms1_scan_support_unavailable")
    elif (
        not _finite_number(scan_support)
        or scan_support < config.min_ms1_scan_support_score
    ):
        return _result(
            resolved_request,
            candidate_match,
            SeedRejectReason.LOW_MS1_SCAN_SUPPORT,
            review_flags,
        )

    return SeedGateResult(
        resolved_request=resolved_request,
        seed_gate_class=SeedGateClass.COHERENT_SEED,
        seed_reject_reason=None,
        candidate_match=candidate_match,
        review_flags=tuple(review_flags),
    )


def _result(
    resolved_request: IdentityCoherenceRequest,
    candidate_match: CandidateIdentityMatch,
    reason: SeedRejectReason,
    review_flags: list[str],
) -> SeedGateResult:
    return SeedGateResult(
        resolved_request=resolved_request,
        seed_gate_class=SeedGateClass.REVIEW_ONLY_SEED_GATE_FAILED,
        seed_reject_reason=reason,
        candidate_match=candidate_match,
        review_flags=tuple(review_flags),
    )


def _finite_number(value: object) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(value)
    )


def _getattr_or_none(value: object, name: str) -> Any:
    return getattr(value, name, None)
