from __future__ import annotations

import math
from typing import cast

from .models import (
    CandidateIdentityMatch,
    IdentityCoherenceRequest,
    SeedCandidateEvidence,
)
from .schema import (
    FragmentObservationMode,
    RequestCandidateIdentityStatus,
    RequestIdentityCompletenessStatus,
)


def match_request_to_candidate(
    request: IdentityCoherenceRequest,
    candidate_evidence: SeedCandidateEvidence | None,
) -> CandidateIdentityMatch:
    return _match_request_to_candidate(
        request,
        candidate_evidence,
        require_seed_candidate_id_match=True,
    )


def match_identity_constraints_to_candidate(
    request: IdentityCoherenceRequest,
    candidate_evidence: SeedCandidateEvidence | None,
) -> CandidateIdentityMatch:
    return _match_request_to_candidate(
        request,
        candidate_evidence,
        require_seed_candidate_id_match=False,
    )


def _match_request_to_candidate(
    request: IdentityCoherenceRequest,
    candidate_evidence: SeedCandidateEvidence | None,
    *,
    require_seed_candidate_id_match: bool,
) -> CandidateIdentityMatch:
    if (
        request.request_identity_completeness_status
        != RequestIdentityCompletenessStatus.COMPLETE
    ):
        return _match(RequestCandidateIdentityStatus.NOT_ASSESSED)

    identity = request.identity
    if (
        identity.fragment_observation_mode
        != FragmentObservationMode.CID_NEUTRAL_LOSS
    ):
        return _match(
            RequestCandidateIdentityStatus.UNSUPPORTED_FRAGMENT_OBSERVATION_MODE,
        )

    if candidate_evidence is None:
        return _match(
            RequestCandidateIdentityStatus.MISSING_DISCOVERY_CANDIDATE_JOIN,
            missing_fields=("candidate",),
        )
    if (
        require_seed_candidate_id_match
        and candidate_evidence.candidate_id != request.seed_candidate_id
    ):
        return _match(
            RequestCandidateIdentityStatus.MISSING_DISCOVERY_CANDIDATE_JOIN,
            missing_fields=("candidate_id",),
        )

    missing_fields: list[str] = []
    candidate_precursor_mz = candidate_evidence.precursor_mz
    candidate_product_mz = candidate_evidence.product_mz
    candidate_loss_da = candidate_evidence.cid_observed_loss_da
    candidate_tags = candidate_evidence.fragment_tags

    if not _finite_positive_number(candidate_precursor_mz):
        missing_fields.append("precursor_mz")
    if not _finite_positive_number(candidate_product_mz):
        missing_fields.append("product_mz")
    if not _finite_positive_number(candidate_loss_da):
        missing_fields.append("observed_neutral_loss_da")
    if not candidate_tags:
        missing_fields.append("fragment_tags")
    if missing_fields:
        return _match(
            RequestCandidateIdentityStatus.MISSING_DIAGNOSTIC_FRAGMENT_EVIDENCE,
            missing_fields=tuple(missing_fields),
            fragment_tags_supported=candidate_tags,
        )
    candidate_precursor_mz = cast(float, candidate_precursor_mz)
    candidate_product_mz = cast(float, candidate_product_mz)
    candidate_loss_da = cast(float, candidate_loss_da)

    if not all(
        _finite_positive_number(value)
        for value in (
            identity.precursor_mz,
            identity.product_mz,
            identity.mode_constraint.cid_observed_loss_da,
            identity.precursor_tolerance_ppm,
            identity.product_tolerance_ppm,
            identity.mode_constraint.cid_observed_loss_tolerance_ppm,
        )
    ):
        return _match(
            RequestCandidateIdentityStatus.MISSING_DIAGNOSTIC_FRAGMENT_EVIDENCE,
            missing_fields=("request_identity_numeric_invariant",),
            fragment_tags_supported=candidate_tags,
        )

    request_precursor_mz = cast(float, identity.precursor_mz)
    request_product_mz = cast(float, identity.product_mz)
    request_loss_da = cast(float, identity.mode_constraint.cid_observed_loss_da)
    precursor_tolerance_ppm = cast(float, identity.precursor_tolerance_ppm)
    product_tolerance_ppm = cast(float, identity.product_tolerance_ppm)
    loss_tolerance_ppm = cast(
        float,
        identity.mode_constraint.cid_observed_loss_tolerance_ppm,
    )

    precursor_error_ppm = _ppm_error(candidate_precursor_mz, request_precursor_mz)
    product_error_ppm = _ppm_error(candidate_product_mz, request_product_mz)
    loss_error_da = candidate_loss_da - request_loss_da
    loss_error_ppm = _ppm_error(candidate_loss_da, request_loss_da)

    mismatch_fields: list[str] = []
    if abs(precursor_error_ppm) > precursor_tolerance_ppm + 1e-9:
        mismatch_fields.append("precursor_mz")
    if abs(product_error_ppm) > product_tolerance_ppm + 1e-9:
        mismatch_fields.append("product_mz")
    if abs(loss_error_ppm) > loss_tolerance_ppm + 1e-9:
        mismatch_fields.append("cid_observed_loss_da")
    if any(tag not in candidate_tags for tag in identity.fragment_tags):
        mismatch_fields.append("fragment_tags")

    if mismatch_fields:
        return _match(
            RequestCandidateIdentityStatus.REQUEST_CANDIDATE_IDENTITY_MISMATCH,
            precursor_error_ppm=precursor_error_ppm,
            product_error_ppm=product_error_ppm,
            cid_observed_loss_error_ppm=loss_error_ppm,
            cid_observed_loss_error_da=loss_error_da,
            mismatch_fields=tuple(mismatch_fields),
            fragment_tags_supported=candidate_tags,
        )

    return _match(
        RequestCandidateIdentityStatus.MATCH,
        precursor_error_ppm=precursor_error_ppm,
        product_error_ppm=product_error_ppm,
        cid_observed_loss_error_ppm=loss_error_ppm,
        cid_observed_loss_error_da=loss_error_da,
        fragment_tags_supported=candidate_tags,
    )


def _ppm_error(observed: float, expected: float) -> float:
    return (observed - expected) / expected * 1_000_000.0


def _finite_positive_number(value: object) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(value)
        and value > 0
    )


def _match(
    status: RequestCandidateIdentityStatus,
    *,
    precursor_error_ppm: float | None = None,
    product_error_ppm: float | None = None,
    cid_observed_loss_error_ppm: float | None = None,
    cid_observed_loss_error_da: float | None = None,
    missing_fields: tuple[str, ...] = (),
    mismatch_fields: tuple[str, ...] = (),
    fragment_tags_supported: tuple[str, ...] = (),
) -> CandidateIdentityMatch:
    return CandidateIdentityMatch(
        request_candidate_identity_status=status,
        precursor_error_ppm=precursor_error_ppm,
        product_error_ppm=product_error_ppm,
        cid_observed_loss_error_ppm=cid_observed_loss_error_ppm,
        cid_observed_loss_error_da=cid_observed_loss_error_da,
        missing_fields=missing_fields,
        mismatch_fields=mismatch_fields,
        fragment_tags_supported=fragment_tags_supported,
    )
