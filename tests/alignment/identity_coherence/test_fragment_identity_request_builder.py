from dataclasses import dataclass

import pytest

from xic_extractor.alignment.identity_coherence.models import (
    CidNeutralLossConstraint,
    FragmentIdentity,
    IdentityCoherenceRequest,
)
from xic_extractor.alignment.identity_coherence.request_builder import (
    build_identity_coherence_request,
)
from xic_extractor.alignment.identity_coherence.schema import (
    FragmentObservationMode,
    FragmentTagMatchPolicy,
    RequestCandidateIdentityStatus,
    RequestIdentityCompletenessStatus,
)
from xic_extractor.alignment.identity_coherence.tags import format_fragment_tags


def test_fragment_identity_request_model_can_hold_complete_cid_request():
    identity = FragmentIdentity(
        fragment_observation_mode=FragmentObservationMode.CID_NEUTRAL_LOSS,
        precursor_mz=500.0,
        product_mz=384.0,
        fragment_tags=("dR", "MeR"),
        fragment_tag_match_policy=FragmentTagMatchPolicy.ALL_REQUEST_TAGS_SUPPORTED,
        precursor_tolerance_ppm=10.0,
        product_tolerance_ppm=10.0,
        fragment_profile_id="profile-a",
        fragment_profile_hash="hash-a",
        mode_constraint=CidNeutralLossConstraint(
            cid_observed_loss_da=116.0,
            cid_observed_loss_tolerance_ppm=10.0,
        ),
    )

    request = IdentityCoherenceRequest(
        request_id="REQ-1",
        decision_id="DEC-1",
        seed_candidate_id="CAND-1",
        seed_sample="RAW-1",
        identity=identity,
        request_identity_completeness_status=RequestIdentityCompletenessStatus.COMPLETE,
        request_candidate_identity_status=RequestCandidateIdentityStatus.NOT_ASSESSED,
        request_builder_flags=(),
    )

    assert request.identity.fragment_tags == ("dR", "MeR")


@dataclass
class CandidateLike:
    candidate_id: str = "CAND-1"
    sample_name: str = "RAW-1"
    precursor_mz: float | None = 500.0
    product_mz: float | None = 384.0
    observed_neutral_loss_da: float | None = 116.0
    matched_tag_names: object = ("MeR", "dR")
    neutral_loss_tag: str | None = "dR"


def _build(candidate: CandidateLike):
    return build_identity_coherence_request(
        candidate,
        request_id="REQ-1",
        decision_id="DEC-1",
        precursor_tolerance_ppm=10.0,
        product_tolerance_ppm=10.0,
        cid_observed_loss_tolerance_ppm=10.0,
        fragment_profile_id="profile-a",
    )


def test_builder_creates_complete_cid_neutral_loss_request():
    request = _build(CandidateLike())

    assert request.request_identity_completeness_status is (
        RequestIdentityCompletenessStatus.COMPLETE
    )
    assert request.request_candidate_identity_status is (
        RequestCandidateIdentityStatus.NOT_ASSESSED
    )
    # Builder output is pre-gate; this object must not be emitted directly as
    # a frozen requests.tsv row until seed-gate matching resolves the status.
    assert request.identity.fragment_observation_mode is (
        FragmentObservationMode.CID_NEUTRAL_LOSS
    )
    assert request.identity.fragment_tags == ("MeR", "dR")
    assert request.identity.fragment_profile_hash == "unavailable"
    assert "fragment_profile_hash_unavailable" in request.request_builder_flags
    assert "legacy_single_tag_disagrees_with_matched_tags" not in (
        request.request_builder_flags
    )


@pytest.mark.parametrize(
    ("raw_tags", "expected"),
    [
        ("dR;MeR", ("MeR", "dR")),
        ("dR|MeR", ("MeR", "dR")),
        ("dR,MeR", ("MeR", "dR")),
        (["dR", "MeR"], ("MeR", "dR")),
        (("dR", "MeR"), ("MeR", "dR")),
        ({"dR", "MeR"}, ("MeR", "dR")),
    ],
)
def test_builder_accepts_common_tag_shapes_and_canonicalizes(raw_tags, expected):
    request = _build(CandidateLike(matched_tag_names=raw_tags, neutral_loss_tag=None))

    assert request.identity.fragment_tags == expected


def test_format_fragment_tags_uses_semicolon_for_tsv_projection():
    assert format_fragment_tags(("MeR", "dR")) == "MeR;dR"


def test_builder_preserves_case_variants_and_flags_them():
    request = _build(CandidateLike(matched_tag_names="base;BASE"))

    assert request.identity.fragment_tags == ("BASE", "base")
    assert "fragment_tag_case_variant_seen" in request.request_builder_flags


def test_matched_tags_win_over_legacy_single_tag_and_flag_disagreement():
    request = _build(CandidateLike(matched_tag_names=("MeR",), neutral_loss_tag="dR"))

    assert request.identity.fragment_tags == ("MeR",)
    assert "legacy_single_tag_disagrees_with_matched_tags" in (
        request.request_builder_flags
    )


def test_missing_product_mz_builds_incomplete_request():
    request = _build(CandidateLike(product_mz=None))

    assert request.request_identity_completeness_status is (
        RequestIdentityCompletenessStatus.MISSING_PRODUCT_MZ
    )
    assert "missing_product_mz" in request.request_builder_flags


def test_missing_tags_builds_incomplete_request():
    request = _build(CandidateLike(matched_tag_names=None, neutral_loss_tag=None))

    assert request.request_identity_completeness_status is (
        RequestIdentityCompletenessStatus.MISSING_FRAGMENT_TAGS
    )


def test_missing_common_tolerance_builds_incomplete_request():
    request = build_identity_coherence_request(
        CandidateLike(),
        request_id="REQ-1",
        decision_id="DEC-1",
        precursor_tolerance_ppm=None,
        product_tolerance_ppm=10.0,
        cid_observed_loss_tolerance_ppm=10.0,
        fragment_profile_id="profile-a",
    )

    assert request.request_identity_completeness_status is (
        RequestIdentityCompletenessStatus.MISSING_TOLERANCE
    )
    assert "missing_precursor_tolerance_ppm" in request.request_builder_flags


def test_missing_mode_tolerance_builds_missing_tolerance_request():
    request = build_identity_coherence_request(
        CandidateLike(),
        request_id="REQ-1",
        decision_id="DEC-1",
        precursor_tolerance_ppm=10.0,
        product_tolerance_ppm=10.0,
        cid_observed_loss_tolerance_ppm=None,
        fragment_profile_id="profile-a",
    )

    assert request.request_identity_completeness_status is (
        RequestIdentityCompletenessStatus.MISSING_TOLERANCE
    )
    assert "missing_cid_observed_loss_tolerance_ppm" in request.request_builder_flags


def test_missing_cid_loss_payload_builds_missing_mode_constraint_request():
    request = _build(CandidateLike(observed_neutral_loss_da=None))

    assert request.request_identity_completeness_status is (
        RequestIdentityCompletenessStatus.MISSING_MODE_SPECIFIC_CONSTRAINT
    )
    assert "missing_mode_specific_constraint" in request.request_builder_flags


@pytest.mark.parametrize("field", ["request_id", "decision_id", "fragment_profile_id"])
def test_missing_required_request_metadata_raises_value_error(field):
    kwargs = {
        "request_id": "REQ-1",
        "decision_id": "DEC-1",
        "precursor_tolerance_ppm": 10.0,
        "product_tolerance_ppm": 10.0,
        "cid_observed_loss_tolerance_ppm": 10.0,
        "fragment_profile_id": "profile-a",
    }
    kwargs[field] = ""

    with pytest.raises(ValueError):
        build_identity_coherence_request(CandidateLike(), **kwargs)


def test_missing_candidate_id_raises_value_error():
    with pytest.raises(ValueError):
        _build(CandidateLike(candidate_id=""))


def test_nonfinite_precursor_mz_builds_incomplete_request():
    request = _build(CandidateLike(precursor_mz=float("nan")))

    assert request.request_identity_completeness_status is (
        RequestIdentityCompletenessStatus.MISSING_PRECURSOR_MZ
    )
    assert "missing_precursor_mz" in request.request_builder_flags


def test_zero_cid_loss_payload_builds_missing_mode_constraint_request():
    request = _build(CandidateLike(observed_neutral_loss_da=0.0))

    assert request.request_identity_completeness_status is (
        RequestIdentityCompletenessStatus.MISSING_MODE_SPECIFIC_CONSTRAINT
    )
    assert "missing_mode_specific_constraint" in request.request_builder_flags


def test_nonfinite_common_tolerance_builds_missing_tolerance_request():
    request = build_identity_coherence_request(
        CandidateLike(),
        request_id="REQ-1",
        decision_id="DEC-1",
        precursor_tolerance_ppm=float("inf"),
        product_tolerance_ppm=10.0,
        cid_observed_loss_tolerance_ppm=10.0,
        fragment_profile_id="profile-a",
    )

    assert request.request_identity_completeness_status is (
        RequestIdentityCompletenessStatus.MISSING_TOLERANCE
    )
    assert "missing_precursor_tolerance_ppm" in request.request_builder_flags
