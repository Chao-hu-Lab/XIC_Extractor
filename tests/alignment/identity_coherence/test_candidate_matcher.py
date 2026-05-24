from dataclasses import dataclass, replace

import pytest

from xic_extractor.alignment.identity_coherence.candidate_matcher import (
    match_identity_constraints_to_candidate,
    match_request_to_candidate,
)
from xic_extractor.alignment.identity_coherence.request_builder import (
    build_identity_coherence_request,
    build_seed_candidate_evidence,
)
from xic_extractor.alignment.identity_coherence.schema import (
    RequestCandidateIdentityStatus,
    RequestIdentityCompletenessStatus,
)


@dataclass
class CandidateLike:
    candidate_id: str = "CAND-1"
    sample_name: str = "RAW-1"
    precursor_mz: float | None = 500.0
    product_mz: float | None = 384.0
    observed_neutral_loss_da: float | None = 116.0
    matched_tag_names: object = ("MeR", "dR")
    neutral_loss_tag: str | None = "dR"
    best_seed_rt: float | None = 7.83
    ms1_scan_support_score: float | None = 0.80


def _request(candidate: CandidateLike):
    return build_identity_coherence_request(
        candidate,
        request_id="REQ-1",
        decision_id="DEC-1",
        precursor_tolerance_ppm=10.0,
        product_tolerance_ppm=10.0,
        cid_observed_loss_tolerance_ppm=10.0,
        fragment_profile_id="profile-a",
    )


def _evidence(candidate: CandidateLike):
    return build_seed_candidate_evidence(candidate)


def test_match_request_to_candidate_accepts_matching_cid_neutral_loss():
    candidate = CandidateLike()
    match = match_request_to_candidate(_request(candidate), _evidence(candidate))

    assert match.request_candidate_identity_status is (
        RequestCandidateIdentityStatus.MATCH
    )
    assert match.precursor_error_ppm == 0.0
    assert match.product_error_ppm == 0.0
    assert match.cid_observed_loss_error_ppm == 0.0
    assert match.cid_observed_loss_error_da == 0.0
    assert match.fragment_tags_supported == ("MeR", "dR")


def test_match_request_to_candidate_checks_unsupported_mode_before_missing_join():
    request = _request(CandidateLike())
    unsupported_identity = replace(
        request.identity,
        fragment_observation_mode="hcd_product_ion",
    )
    unsupported_request = replace(request, identity=unsupported_identity)

    unsupported_match = match_request_to_candidate(unsupported_request, None)
    missing_join_match = match_request_to_candidate(request, None)

    assert unsupported_match.request_candidate_identity_status is (
        RequestCandidateIdentityStatus.UNSUPPORTED_FRAGMENT_OBSERVATION_MODE
    )
    assert missing_join_match.request_candidate_identity_status is (
        RequestCandidateIdentityStatus.MISSING_DISCOVERY_CANDIDATE_JOIN
    )
    assert missing_join_match.missing_fields == ("candidate",)


def test_match_request_to_candidate_accepts_schema_string_fragment_mode():
    request = _request(CandidateLike())
    string_identity = replace(
        request.identity,
        fragment_observation_mode="cid_neutral_loss",
    )
    string_request = replace(request, identity=string_identity)
    match = match_request_to_candidate(string_request, _evidence(CandidateLike()))

    assert match.request_candidate_identity_status is (
        RequestCandidateIdentityStatus.MATCH
    )


def test_match_request_to_candidate_rejects_mismatched_candidate_id():
    request = _request(CandidateLike())
    candidate = replace(_evidence(CandidateLike()), candidate_id="OTHER-CAND")
    match = match_request_to_candidate(request, candidate)

    assert match.request_candidate_identity_status is (
        RequestCandidateIdentityStatus.MISSING_DISCOVERY_CANDIDATE_JOIN
    )
    assert match.missing_fields == ("candidate_id",)


def test_match_request_to_candidate_reports_missing_diagnostic_evidence():
    request = _request(CandidateLike())
    candidate = _evidence(CandidateLike(product_mz=None))
    match = match_request_to_candidate(request, candidate)

    assert match.request_candidate_identity_status is (
        RequestCandidateIdentityStatus.MISSING_DIAGNOSTIC_FRAGMENT_EVIDENCE
    )
    assert "product_mz" in match.missing_fields


@pytest.mark.parametrize(
    ("field", "value", "missing_field"),
    [
        ("precursor_mz", float("nan"), "precursor_mz"),
        ("product_mz", float("inf"), "product_mz"),
        ("cid_observed_loss_da", 0.0, "observed_neutral_loss_da"),
        ("precursor_mz", -1.0, "precursor_mz"),
    ],
)
def test_match_request_to_candidate_rejects_invalid_candidate_numeric_evidence(
    field,
    value,
    missing_field,
):
    request = _request(CandidateLike())
    candidate = replace(_evidence(CandidateLike()), **{field: value})
    match = match_request_to_candidate(request, candidate)

    assert match.request_candidate_identity_status is (
        RequestCandidateIdentityStatus.MISSING_DIAGNOSTIC_FRAGMENT_EVIDENCE
    )
    assert missing_field in match.missing_fields


def test_match_request_to_candidate_rejects_product_mz_mismatch():
    request = _request(CandidateLike())
    candidate = _evidence(CandidateLike(product_mz=390.0))
    match = match_request_to_candidate(request, candidate)

    assert match.request_candidate_identity_status is (
        RequestCandidateIdentityStatus.REQUEST_CANDIDATE_IDENTITY_MISMATCH
    )
    assert "product_mz" in match.mismatch_fields


def test_match_request_to_candidate_rejects_precursor_mz_mismatch():
    request = _request(CandidateLike())
    candidate = _evidence(CandidateLike(precursor_mz=500.02))
    match = match_request_to_candidate(request, candidate)

    assert match.request_candidate_identity_status is (
        RequestCandidateIdentityStatus.REQUEST_CANDIDATE_IDENTITY_MISMATCH
    )
    assert "precursor_mz" in match.mismatch_fields


def test_match_request_to_candidate_rejects_cid_loss_ppm_mismatch():
    request = _request(CandidateLike())
    candidate = _evidence(CandidateLike(observed_neutral_loss_da=116.01))
    match = match_request_to_candidate(request, candidate)

    assert match.request_candidate_identity_status is (
        RequestCandidateIdentityStatus.REQUEST_CANDIDATE_IDENTITY_MISMATCH
    )
    assert "cid_observed_loss_da" in match.mismatch_fields


def test_match_request_to_candidate_accepts_exact_ppm_boundary():
    request = _request(CandidateLike())
    candidate = _evidence(
        CandidateLike(
            precursor_mz=500.005,
            product_mz=384.00384,
            observed_neutral_loss_da=116.00116,
        )
    )
    match = match_request_to_candidate(request, candidate)

    assert match.request_candidate_identity_status is (
        RequestCandidateIdentityStatus.MATCH
    )


def test_match_request_to_candidate_rejects_product_mz_just_above_tolerance():
    # The ppm gate adds only a 1e-9 floating-point guard; a real overage well
    # above that guard must still be rejected so the epsilon is not leniency.
    request = _request(CandidateLike())
    candidate = _evidence(CandidateLike(product_mz=384.004))
    match = match_request_to_candidate(request, candidate)

    assert match.request_candidate_identity_status is (
        RequestCandidateIdentityStatus.REQUEST_CANDIDATE_IDENTITY_MISMATCH
    )
    assert "product_mz" in match.mismatch_fields
    assert match.product_error_ppm > 10.0


def test_match_request_to_candidate_rejects_missing_request_tag_support():
    request = _request(CandidateLike(matched_tag_names=("MeR", "dR")))
    candidate = _evidence(
        CandidateLike(matched_tag_names=("dR",), neutral_loss_tag="dR"),
    )
    match = match_request_to_candidate(request, candidate)

    assert match.request_candidate_identity_status is (
        RequestCandidateIdentityStatus.REQUEST_CANDIDATE_IDENTITY_MISMATCH
    )
    assert "fragment_tags" in match.mismatch_fields


def test_match_request_to_candidate_leaves_incomplete_request_not_assessed():
    request = _request(CandidateLike(product_mz=None))
    match = match_request_to_candidate(request, _evidence(CandidateLike()))

    assert request.request_identity_completeness_status is (
        RequestIdentityCompletenessStatus.MISSING_PRODUCT_MZ
    )
    assert match.request_candidate_identity_status is (
        RequestCandidateIdentityStatus.NOT_ASSESSED
    )


def test_identity_constraint_match_allows_non_seed_candidate_id():
    request = _request(CandidateLike())
    non_seed_candidate = replace(
        _evidence(CandidateLike()),
        candidate_id="NON-SEED-CAND",
    )

    seed_join_match = match_request_to_candidate(request, non_seed_candidate)
    identity_match = match_identity_constraints_to_candidate(
        request,
        non_seed_candidate,
    )

    assert seed_join_match.request_candidate_identity_status is (
        RequestCandidateIdentityStatus.MISSING_DISCOVERY_CANDIDATE_JOIN
    )
    assert identity_match.request_candidate_identity_status is (
        RequestCandidateIdentityStatus.MATCH
    )
