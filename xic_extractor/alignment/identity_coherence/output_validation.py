from __future__ import annotations

from .models import IdentityCoherenceRequest, IdentityDecisionSummary
from .output_formatting import enum_value
from .output_models import IdentityCoherenceOutputRecord
from .schema import (
    RequestCandidateIdentityStatus,
    RequestIdentityCompletenessStatus,
)


def validate_frozen_request_status(request: IdentityCoherenceRequest) -> None:
    completeness = enum_value(request.request_identity_completeness_status)
    candidate_status = enum_value(request.request_candidate_identity_status)
    if (
        completeness == RequestIdentityCompletenessStatus.COMPLETE.value
        and candidate_status == RequestCandidateIdentityStatus.NOT_ASSESSED.value
    ):
        raise ValueError("complete request cannot be emitted as not_assessed")


def validate_decision_summary(summary: IdentityDecisionSummary) -> None:
    if summary.forbidden_evidence_used:
        raise ValueError("forbidden_evidence_used cannot be emitted")


def validate_output_record(
    record: IdentityCoherenceOutputRecord,
) -> IdentityCoherenceOutputRecord:
    request = record.seed_gate.resolved_request
    decision = record.row_result.decision
    if request.decision_id != decision.decision_id:
        raise ValueError("decision_id mismatch between request and decision")
    if request.seed_candidate_id != decision.seed_candidate_id:
        raise ValueError("seed_candidate_id mismatch between request and decision")
    if request.seed_sample != decision.seed_sample:
        raise ValueError("seed_sample mismatch between request and decision")
    if (
        request.request_identity_completeness_status
        != decision.request_identity_completeness_status
    ):
        raise ValueError(
            "request_identity_completeness_status mismatch between "
            "request and decision"
        )
    if (
        request.request_candidate_identity_status
        != decision.request_candidate_identity_status
    ):
        raise ValueError(
            "request_candidate_identity_status mismatch between "
            "request and decision"
        )
    validate_decision_summary(decision)
    if not request.seed_sample:
        raise ValueError("writer requires resolved seed_sample")
    for cell in record.row_result.cells:
        if cell.decision_id != decision.decision_id:
            raise ValueError("decision_id mismatch between decision and cell")
        if cell.identity_family_id != decision.identity_family_id:
            raise ValueError(
                "identity_family_id mismatch between decision and cell"
            )
        if request.seed_sample and cell.sample_id == request.seed_sample:
            raise ValueError("seed sample cannot be emitted in cell_evidence.tsv")
    return record
