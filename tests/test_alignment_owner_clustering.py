from xic_extractor.alignment import owner_clustering as owner_clustering_module
from xic_extractor.alignment.config import AlignmentConfig
from xic_extractor.alignment.edge_scoring import evaluate_owner_edge
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


def test_owner_clustering_collapses_5medc_like_class_drift() -> None:
    features = cluster_sample_local_owners(
        (
            _owner("tumor-a", "a", apex_rt=11.5674),
            _owner("qc-a", "b", apex_rt=12.1813),
            _owner("qc-b", "c", apex_rt=12.4051),
            _owner("normal-a", "d", apex_rt=12.6515),
            _owner("benign-a", "e", apex_rt=12.6673),
        ),
        config=AlignmentConfig(identity_rt_candidate_window_sec=180.0),
        drift_lookup=_DriftLookup(
            deltas={
                "tumor-a": -0.35,
                "qc-a": 0.0,
                "qc-b": 0.10,
                "normal-a": 0.35,
                "benign-a": 0.36,
            },
            orders={
                "tumor-a": 1,
                "qc-a": 20,
                "qc-b": 40,
                "normal-a": 60,
                "benign-a": 80,
            },
        ),
    )

    assert len(features) == 1
    assert len(features[0].event_cluster_ids) == 5
    assert features[0].evidence == "owner_complete_link;owner_count=5"


def test_owner_clustering_does_not_bridge_three_owner_complete_link_group() -> None:
    edge_evidence = []
    owners = (
        _owner("sample-a", "a", apex_rt=10.00),
        _owner("sample-b", "b", apex_rt=10.75),
        _owner("sample-c", "c", apex_rt=11.50),
    )
    config = AlignmentConfig(preferred_rt_sec=30.0, max_rt_sec=120.0)
    drift_lookup = _DriftLookup(
        deltas={
            "sample-a": 0.00,
            "sample-b": 0.50,
            "sample-c": 0.90,
        },
        orders={
            "sample-a": 1,
            "sample-b": 2,
            "sample-c": 3,
        },
    )

    features = cluster_sample_local_owners(
        owners,
        config=config,
        drift_lookup=drift_lookup,
        edge_evidence_sink=edge_evidence,
    )

    assert evaluate_owner_edge(
        owners[0],
        owners[1],
        config=config,
        drift_lookup=drift_lookup,
    ).decision == "strong_edge"
    assert evaluate_owner_edge(
        owners[1],
        owners[2],
        config=config,
        drift_lookup=drift_lookup,
    ).decision == "strong_edge"
    grouped_owner_ids = [feature.event_cluster_ids for feature in features]
    assert grouped_owner_ids == [
        ("OWN-sample-a-a", "OWN-sample-b-b"),
        ("OWN-sample-c-c",),
    ]
    assert _edge_decisions_by_pair(edge_evidence)[
        ("OWN-sample-a-a", "OWN-sample-c-c")
    ] == "weak_edge"


def test_owner_clustering_uses_drift_prior_for_strong_edge_over_strict_rt() -> None:
    edge_evidence = []

    features = cluster_sample_local_owners(
        (
            _owner("sample-a", "a", apex_rt=10.0),
            _owner("sample-b", "b", apex_rt=11.2),
        ),
        config=AlignmentConfig(preferred_rt_sec=60.0, max_rt_sec=180.0),
        drift_lookup=_DriftLookup(
            deltas={"sample-a": 0.0, "sample-b": 0.25},
            orders={},
        ),
        edge_evidence_sink=edge_evidence,
    )

    assert len(features) == 1
    assert features[0].event_cluster_ids == ("OWN-sample-a-a", "OWN-sample-b-b")
    assert [edge.decision for edge in edge_evidence] == ["strong_edge"]


def test_owner_clustering_preserves_weak_no_drift_rt_split() -> None:
    edge_evidence = []

    features = cluster_sample_local_owners(
        (
            _owner("sample-a", "a", apex_rt=10.0),
            _owner("sample-b", "b", apex_rt=11.2),
        ),
        config=AlignmentConfig(preferred_rt_sec=60.0, max_rt_sec=180.0),
        edge_evidence_sink=edge_evidence,
    )

    assert len(features) == 2
    assert [edge.decision for edge in edge_evidence] == ["weak_edge"]


def test_owner_clustering_edge_evidence_sink_keeps_unique_sorted_pairs() -> None:
    edge_evidence = []

    cluster_sample_local_owners(
        (
            _owner("sample-a", "a", apex_rt=10.00),
            _owner("sample-b", "b", apex_rt=10.20),
            _owner("sample-c", "c", apex_rt=10.40),
            _owner("sample-c", "c", apex_rt=10.40),
        ),
        config=AlignmentConfig(preferred_rt_sec=30.0, max_rt_sec=120.0),
        edge_evidence_sink=edge_evidence,
    )

    sorted_pairs = [
        tuple(sorted((edge.left_owner_id, edge.right_owner_id)))
        for edge in edge_evidence
    ]
    assert len(sorted_pairs) == len(set(sorted_pairs))
    assert all(left <= right for left, right in sorted_pairs)


def test_owner_clustering_skips_impossible_mz_group_without_edge_sink(
    monkeypatch,
) -> None:
    real_evaluate_owner_edge = owner_clustering_module.evaluate_owner_edge

    def guard_far_owner_scoring(left, right, *, config, drift_lookup=None):
        if any(owner.owner_id.endswith("-far") for owner in (left, right)):
            raise AssertionError("far owner should be rejected by group prefilter")
        return real_evaluate_owner_edge(
            left,
            right,
            config=config,
            drift_lookup=drift_lookup,
        )

    monkeypatch.setattr(
        owner_clustering_module,
        "evaluate_owner_edge",
        guard_far_owner_scoring,
    )

    features = cluster_sample_local_owners(
        (
            _owner("sample-a", "near-a", precursor_mz=500.0000),
            _owner("sample-b", "near-b", precursor_mz=500.0050),
            _owner("sample-c", "far", precursor_mz=700.0000),
        ),
        config=AlignmentConfig(max_ppm=20.0),
    )

    assert [feature.event_cluster_ids for feature in features] == [
        ("OWN-sample-a-near-a", "OWN-sample-b-near-b"),
        ("OWN-sample-c-far",),
    ]


def test_owner_clustering_records_blocked_edge_without_merging() -> None:
    edge_evidence = []

    features = cluster_sample_local_owners(
        (
            _owner("sample-a", "a", neutral_loss_tag="NL116"),
            _owner("sample-b", "b", neutral_loss_tag="NL141"),
        ),
        config=AlignmentConfig(),
        edge_evidence_sink=edge_evidence,
    )

    assert len(features) == 2
    assert [edge.failure_reason for edge in edge_evidence] == [
        "neutral_loss_tag_mismatch",
    ]


def test_owner_clustering_rejects_product_or_observed_loss_conflict() -> None:
    features = cluster_sample_local_owners(
        (
            _owner("sample-a", "a", product_mz=126.066, observed_loss=116.048),
            _owner("sample-b", "b", product_mz=126.066, observed_loss=116.500),
            _owner("sample-c", "c", product_mz=127.000, observed_loss=116.048),
        ),
        config=AlignmentConfig(
            product_mz_tolerance_ppm=20.0,
            observed_loss_tolerance_ppm=20.0,
        ),
    )

    assert len(features) == 3


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


class _DriftLookup:
    source = "targeted_istd_trend"

    def __init__(
        self,
        *,
        deltas: dict[str, float],
        orders: dict[str, int],
    ) -> None:
        self._deltas = deltas
        self._orders = orders

    def sample_delta_min(self, sample_stem: str) -> float | None:
        return self._deltas.get(sample_stem)

    def injection_order(self, sample_stem: str) -> int | None:
        return self._orders.get(sample_stem)


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


def _edge_decisions_by_pair(edge_evidence):
    return {
        tuple(sorted((edge.left_owner_id, edge.right_owner_id))): edge.decision
        for edge in edge_evidence
    }
