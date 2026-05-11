from xic_extractor.alignment.config import AlignmentConfig
from xic_extractor.alignment.owner_clustering import (
    cluster_sample_local_owners,
    review_only_features_from_ambiguous_records,
)
from xic_extractor.alignment.ownership_models import (
    AmbiguousOwnerRecord,
    IdentityEvent,
    SampleLocalMS1Owner,
)


def test_owner_clustering_allows_plausible_rt_drift_with_complete_link() -> None:
    features = cluster_sample_local_owners(
        (
            _owner("sample-a", "a", apex_rt=12.59),
            _owner("sample-b", "b", apex_rt=12.88),
        ),
        config=AlignmentConfig(identity_rt_candidate_window_sec=180.0),
    )

    assert len(features) == 1
    assert features[0].event_cluster_ids == ("OWN-sample-a-a", "OWN-sample-b-b")
    assert features[0].evidence == "owner_complete_link;owner_count=2"


def test_owner_clustering_keeps_different_neutral_loss_tags_separate() -> None:
    features = cluster_sample_local_owners(
        (
            _owner("sample-a", "a", neutral_loss_tag="NL116"),
            _owner("sample-b", "b", neutral_loss_tag="NL141"),
        ),
        config=AlignmentConfig(),
    )

    assert len(features) == 2
    assert [feature.neutral_loss_tag for feature in features] == ["NL116", "NL141"]


def test_identity_conflict_owner_becomes_review_only_feature() -> None:
    features = cluster_sample_local_owners(
        (
            _owner("sample-a", "conflict", identity_conflict=True),
            _owner("sample-b", "clean"),
        ),
        config=AlignmentConfig(),
    )

    conflict, clean = features
    assert conflict.identity_conflict is True
    assert conflict.review_only is True
    assert conflict.evidence == "identity_conflict_review_only"
    assert clean.review_only is False


def test_implausible_rt_distance_does_not_merge_owner_clusters() -> None:
    features = cluster_sample_local_owners(
        (
            _owner("sample-a", "a", apex_rt=8.0),
            _owner("sample-b", "b", apex_rt=12.0),
        ),
        config=AlignmentConfig(identity_rt_candidate_window_sec=180.0),
    )

    assert len(features) == 2


def test_owner_clustering_does_not_merge_two_owners_from_same_sample() -> None:
    features = cluster_sample_local_owners(
        (
            _owner("sample-a", "a1", apex_rt=8.0),
            _owner("sample-a", "a2", apex_rt=8.001),
            _owner("sample-b", "b", apex_rt=8.0),
        ),
        config=AlignmentConfig(),
    )

    assert len(features) == 2
    assert sorted(len(feature.owners) for feature in features) == [1, 2]


def test_owner_clustering_api_has_no_cell_status_input() -> None:
    assert cluster_sample_local_owners.__annotations__["owners"] != "AlignmentMatrix"


def test_ambiguous_records_become_review_only_features_without_owners() -> None:
    features = review_only_features_from_ambiguous_records(
        (
            AmbiguousOwnerRecord(
                ambiguity_id="AMB-sample-a-000001",
                sample_stem="sample-a",
                candidate_ids=("sample-a#1", "sample-a#2"),
                reason="owner_multiplet_ambiguity",
                neutral_loss_tag="NL116",
                precursor_mz=500.0,
                apex_rt=8.5,
                product_mz=383.9526,
                observed_neutral_loss_da=116.0474,
            ),
        ),
        start_index=10,
    )

    assert len(features) == 1
    assert features[0].feature_family_id == "FAM000010"
    assert features[0].review_only is True
    assert features[0].owners == ()
    assert features[0].ambiguous_sample_stem == "sample-a"
    assert features[0].ambiguous_candidate_ids == ("sample-a#1", "sample-a#2")


def _owner(
    sample_stem: str,
    suffix: str,
    *,
    apex_rt: float = 8.5,
    neutral_loss_tag: str = "NL116",
    precursor_mz: float = 500.0,
    product_mz: float = 383.9526,
    observed_loss: float = 116.0474,
    identity_conflict: bool = False,
) -> SampleLocalMS1Owner:
    event = IdentityEvent(
        candidate_id=f"{sample_stem}#{suffix}",
        sample_stem=sample_stem,
        raw_file=f"{sample_stem}.raw",
        neutral_loss_tag=neutral_loss_tag,
        precursor_mz=precursor_mz,
        product_mz=product_mz,
        observed_neutral_loss_da=observed_loss,
        seed_rt=apex_rt,
        evidence_score=80,
        seed_event_count=2,
    )
    return SampleLocalMS1Owner(
        owner_id=f"OWN-{sample_stem}-{suffix}",
        sample_stem=sample_stem,
        raw_file=f"{sample_stem}.raw",
        precursor_mz=precursor_mz,
        owner_apex_rt=apex_rt,
        owner_peak_start_rt=apex_rt - 0.05,
        owner_peak_end_rt=apex_rt + 0.05,
        owner_area=1000.0,
        owner_height=100.0,
        primary_identity_event=event,
        supporting_events=(),
        identity_conflict=identity_conflict,
        assignment_reason="owner_exact_apex_match",
    )
