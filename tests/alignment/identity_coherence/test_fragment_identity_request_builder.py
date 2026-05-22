from xic_extractor.alignment.identity_coherence.models import (
    CidNeutralLossConstraint,
    FragmentIdentity,
    IdentityCoherenceRequest,
)
from xic_extractor.alignment.identity_coherence.schema import (
    FragmentObservationMode,
    FragmentTagMatchPolicy,
    RequestCandidateIdentityStatus,
    RequestIdentityCompletenessStatus,
)


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
