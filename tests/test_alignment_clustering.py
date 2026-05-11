import math
from dataclasses import dataclass, replace
from types import SimpleNamespace

import pytest

from xic_extractor.alignment import clustering
from xic_extractor.alignment.clustering import (
    alignment_candidate_sort_key,
    is_alignment_anchor,
)
from xic_extractor.alignment.config import AlignmentConfig


@dataclass(frozen=True)
class Candidate:
    candidate_id: str
    neutral_loss_tag: str = "NL141"
    review_priority: str = "HIGH"
    evidence_score: int = 60
    seed_event_count: int = 2
    ms1_peak_found: bool = True
    ms1_scan_support_score: float | None = 0.5
    ms1_area: float | None = 100.0
    neutral_loss_mass_error_ppm: float = 1.0
    precursor_mz: float = 500.0
    product_mz: float = 359.0
    observed_neutral_loss_da: float = 141.0
    best_seed_rt: float | None = 5.0
    ms1_apex_rt: float | None = 5.0
    sample_stem: str = "sample-a"


@pytest.mark.parametrize(
    "candidate",
    [
        replace(
            Candidate(candidate_id="missing-ms1"),
            ms1_peak_found=False,
            ms1_scan_support_score=0.9,
        ),
        replace(
            Candidate(candidate_id="missing-apex"),
            ms1_apex_rt=None,
        ),
        replace(
            Candidate(candidate_id="nan-apex"),
            ms1_apex_rt=math.nan,
        ),
        replace(
            Candidate(candidate_id="missing-area"),
            ms1_area=None,
        ),
        replace(
            Candidate(candidate_id="zero-area"),
            ms1_area=0.0,
        ),
        replace(
            Candidate(candidate_id="negative-area"),
            ms1_area=-1.0,
        ),
    ],
)
def test_high_review_priority_with_weak_or_missing_ms1_is_not_anchor(candidate):
    assert is_alignment_anchor(candidate, AlignmentConfig()) is False


def test_candidate_meeting_default_anchor_policy_becomes_anchor():
    assert (
        is_alignment_anchor(Candidate(candidate_id="anchor"), AlignmentConfig())
        is True
    )


def test_anchor_min_evidence_score_affects_anchor_predicate():
    candidate = replace(Candidate(candidate_id="evidence"), evidence_score=69)

    assert (
        is_alignment_anchor(
            candidate,
            AlignmentConfig(anchor_min_evidence_score=70),
        )
        is False
    )
    assert (
        is_alignment_anchor(
            candidate,
            AlignmentConfig(anchor_min_evidence_score=69),
        )
        is True
    )


def test_anchor_min_seed_events_affects_anchor_predicate():
    candidate = replace(Candidate(candidate_id="seed-events"), seed_event_count=2)

    assert (
        is_alignment_anchor(
            candidate,
            AlignmentConfig(anchor_min_seed_events=3),
        )
        is False
    )
    assert (
        is_alignment_anchor(
            candidate,
            AlignmentConfig(anchor_min_seed_events=2),
        )
        is True
    )


def test_anchor_min_scan_support_score_affects_anchor_predicate():
    candidate = replace(
        Candidate(candidate_id="scan-support"),
        ms1_scan_support_score=0.74,
    )

    assert (
        is_alignment_anchor(
            candidate,
            AlignmentConfig(anchor_min_scan_support_score=0.75),
        )
        is False
    )
    assert (
        is_alignment_anchor(
            candidate,
            AlignmentConfig(anchor_min_scan_support_score=0.74),
        )
        is True
    )


def test_missing_scan_support_does_not_disqualify_anchor():
    candidate = replace(
        Candidate(candidate_id="missing-scan-support"),
        ms1_scan_support_score=None,
    )

    assert is_alignment_anchor(candidate, AlignmentConfig()) is True


def test_low_present_scan_support_disqualifies_anchor():
    candidate = replace(
        Candidate(candidate_id="low-scan-support"),
        ms1_scan_support_score=0.49,
    )

    assert is_alignment_anchor(candidate, AlignmentConfig()) is False


@pytest.mark.parametrize(
    "candidate",
    [
        SimpleNamespace(
            review_priority="HIGH",
            evidence_score=60,
            seed_event_count=2,
            ms1_peak_found=True,
        ),
        replace(Candidate(candidate_id="string-evidence"), evidence_score="60"),
        replace(Candidate(candidate_id="bool-seed-count"), seed_event_count=True),
        replace(
            Candidate(candidate_id="nan-scan-support"),
            ms1_scan_support_score=math.nan,
        ),
    ],
)
def test_anchor_predicate_fails_closed_for_missing_or_malformed_values(candidate):
    assert is_alignment_anchor(candidate, AlignmentConfig()) is False


def test_candidate_ordering_prioritizes_anchors_before_non_anchors():
    config = AlignmentConfig()
    anchor = Candidate(candidate_id="anchor")
    high_score_non_anchor = replace(
        Candidate(candidate_id="high-score-non-anchor"),
        evidence_score=100,
        seed_event_count=10,
        ms1_scan_support_score=0.49,
    )

    ordered = sorted(
        [high_score_non_anchor, anchor],
        key=lambda candidate: alignment_candidate_sort_key(candidate, config),
    )

    assert [candidate.candidate_id for candidate in ordered] == [
        "anchor",
        "high-score-non-anchor",
    ]


def test_candidate_ordering_prefers_evidence_before_review_priority():
    config = AlignmentConfig()
    high = replace(
        Candidate(candidate_id="high"),
        review_priority="HIGH",
        evidence_score=60,
        ms1_scan_support_score=0.49,
    )
    medium = replace(
        Candidate(candidate_id="medium"),
        review_priority="MEDIUM",
        evidence_score=100,
        ms1_scan_support_score=0.49,
    )
    low = replace(
        Candidate(candidate_id="low"),
        review_priority="LOW",
        evidence_score=80,
        ms1_scan_support_score=0.49,
    )

    ordered = sorted(
        [low, medium, high],
        key=lambda candidate: alignment_candidate_sort_key(candidate, config),
    )

    assert [candidate.candidate_id for candidate in ordered] == [
        "medium",
        "low",
        "high",
    ]


def test_candidate_ordering_uses_winner_metrics_after_anchor_status():
    config = AlignmentConfig()
    candidates = [
        replace(
            Candidate(candidate_id="a-nl-worse"),
            review_priority="LOW",
            evidence_score=80,
            seed_event_count=2,
            ms1_area=100.0,
            neutral_loss_mass_error_ppm=-3.0,
        ),
        replace(
            Candidate(candidate_id="z-area-best"),
            review_priority="LOW",
            evidence_score=80,
            seed_event_count=2,
            ms1_area=200.0,
            neutral_loss_mass_error_ppm=3.0,
        ),
        replace(
            Candidate(candidate_id="seed-best"),
            review_priority="LOW",
            evidence_score=80,
            seed_event_count=3,
            ms1_area=10.0,
            neutral_loss_mass_error_ppm=3.0,
        ),
        replace(
            Candidate(candidate_id="evidence-best"),
            review_priority="LOW",
            evidence_score=90,
            seed_event_count=1,
            ms1_area=10.0,
            neutral_loss_mass_error_ppm=3.0,
        ),
        replace(
            Candidate(candidate_id="z-nl-best"),
            review_priority="LOW",
            evidence_score=80,
            seed_event_count=2,
            ms1_area=100.0,
            neutral_loss_mass_error_ppm=1.0,
        ),
    ]

    ordered = sorted(
        candidates,
        key=lambda candidate: alignment_candidate_sort_key(candidate, config),
    )

    assert [candidate.candidate_id for candidate in ordered] == [
        "evidence-best",
        "seed-best",
        "z-area-best",
        "z-nl-best",
        "a-nl-worse",
    ]


def test_candidate_ordering_uses_stable_tie_breakers_not_input_order():
    config = AlignmentConfig()
    candidates = [
        replace(
            Candidate(candidate_id="same", sample_stem="sample-z"),
            precursor_mz=500.0,
            ms1_apex_rt=4.9,
        ),
        replace(
            Candidate(candidate_id="same", sample_stem="sample-z"),
            precursor_mz=499.9,
            ms1_apex_rt=9.0,
        ),
        replace(
            Candidate(candidate_id="candidate-b"),
            precursor_mz=499.0,
            ms1_apex_rt=1.0,
            sample_stem="sample-a",
        ),
        replace(
            Candidate(candidate_id="same", sample_stem="sample-b"),
            precursor_mz=500.0,
            ms1_apex_rt=5.0,
        ),
        replace(
            Candidate(candidate_id="same", sample_stem="sample-a"),
            precursor_mz=500.0,
            ms1_apex_rt=5.0,
        ),
        replace(
            Candidate(candidate_id="candidate-a"),
            precursor_mz=501.0,
            ms1_apex_rt=9.0,
            sample_stem="sample-z",
        ),
        replace(
            Candidate(candidate_id="same", sample_stem="sample-z"),
            precursor_mz=500.0,
            ms1_apex_rt=5.0,
        ),
    ]

    ordered = sorted(
        candidates,
        key=lambda candidate: alignment_candidate_sort_key(candidate, config),
    )
    reverse_ordered = sorted(
        reversed(candidates),
        key=lambda candidate: alignment_candidate_sort_key(candidate, config),
    )

    expected = [
        "candidate-a",
        "candidate-b",
        "same",
        "same",
        "same",
        "same",
        "same",
    ]
    assert [candidate.candidate_id for candidate in ordered] == expected
    assert [candidate.candidate_id for candidate in reverse_ordered] == expected
    assert [candidate.sample_stem for candidate in ordered[2:]] == [
        "sample-a",
        "sample-b",
        "sample-z",
        "sample-z",
        "sample-z",
    ]
    assert [candidate.precursor_mz for candidate in ordered[4:]] == [
        499.9,
        500.0,
        500.0,
    ]
    assert [candidate.ms1_apex_rt for candidate in ordered[5:]] == [4.9, 5.0]


def test_greedy_clustering_merges_compatible_candidates_from_different_samples():
    anchor_a = Candidate(candidate_id="anchor-a", sample_stem="sample-a")
    anchor_b = replace(
        Candidate(candidate_id="anchor-b"),
        precursor_mz=500.005,
        product_mz=359.002,
        observed_neutral_loss_da=141.001,
        ms1_apex_rt=5.2,
        sample_stem="sample-b",
    )
    non_anchor = replace(
        Candidate(candidate_id="non-anchor"),
        review_priority="LOW",
        precursor_mz=500.004,
        product_mz=359.001,
        observed_neutral_loss_da=141.001,
        ms1_apex_rt=5.1,
        sample_stem="sample-c",
    )

    clusters = clustering._cluster_candidates_greedy(
        (non_anchor, anchor_b, anchor_a),
        AlignmentConfig(),
    )

    assert _cluster_member_ids(clusters) == {
        frozenset({"anchor-a", "anchor-b", "non-anchor"}),
    }
    cluster = clusters[0]
    assert cluster.has_anchor is True
    assert _ids(cluster.anchor_members) == ("anchor-a", "anchor-b")


def test_greedy_clustering_does_not_merge_different_neutral_loss_strata():
    nl141 = Candidate(candidate_id="nl141", neutral_loss_tag="NL141")
    nl120 = replace(
        Candidate(candidate_id="nl120"),
        neutral_loss_tag="NL120",
        product_mz=380.0,
        observed_neutral_loss_da=120.0,
    )

    clusters = clustering._cluster_candidates_greedy(
        (nl120, nl141),
        AlignmentConfig(),
    )

    assert _cluster_member_ids(clusters) == {
        frozenset({"nl141"}),
        frozenset({"nl120"}),
    }
    assert {cluster.neutral_loss_tag for cluster in clusters} == {"NL141", "NL120"}


def test_same_sample_collision_loser_can_join_another_compatible_cluster():
    anchor_a = Candidate(candidate_id="anchor-a", sample_stem="sample-a")
    anchor_c = replace(
        Candidate(candidate_id="anchor-c"),
        precursor_mz=500.049,
        ms1_apex_rt=5.3,
        sample_stem="sample-c",
    )
    winner = replace(
        Candidate(candidate_id="sample-b-winner"),
        review_priority="LOW",
        evidence_score=80,
        precursor_mz=500.004,
        product_mz=359.001,
        observed_neutral_loss_da=141.001,
        sample_stem="sample-b",
    )
    loser = replace(
        Candidate(candidate_id="sample-b-loser"),
        review_priority="LOW",
        evidence_score=70,
        precursor_mz=500.024,
        ms1_apex_rt=5.2,
        sample_stem="sample-b",
    )

    clusters = clustering._cluster_candidates_greedy(
        (loser, winner, anchor_c, anchor_a),
        AlignmentConfig(),
    )

    assert _cluster_member_ids(clusters) == {
        frozenset({"anchor-a", "sample-b-winner"}),
        frozenset({"anchor-c", "sample-b-loser"}),
    }
    for cluster in clusters:
        assert len({candidate.sample_stem for candidate in cluster.members}) == len(
            cluster.members,
        )


@pytest.mark.parametrize(
    ("better_updates", "worse_updates", "expected_winner_id"),
    [
        (
            {"candidate_id": "anchor-status-winner", "review_priority": "HIGH"},
            {
                "candidate_id": "non-anchor-loser",
                "review_priority": "LOW",
                "evidence_score": 100,
            },
            "anchor-status-winner",
        ),
        (
            {"candidate_id": "evidence-winner", "evidence_score": 80},
            {"candidate_id": "evidence-loser", "evidence_score": 70},
            "evidence-winner",
        ),
        (
            {"candidate_id": "seed-winner", "seed_event_count": 4},
            {"candidate_id": "seed-loser", "seed_event_count": 3},
            "seed-winner",
        ),
        (
            {"candidate_id": "area-winner", "ms1_area": 200.0},
            {"candidate_id": "area-loser", "ms1_area": 100.0},
            "area-winner",
        ),
        (
            {
                "candidate_id": "neutral-loss-error-winner",
                "neutral_loss_mass_error_ppm": -1.0,
            },
            {
                "candidate_id": "neutral-loss-error-loser",
                "neutral_loss_mass_error_ppm": 2.0,
            },
            "neutral-loss-error-winner",
        ),
        (
            {"candidate_id": "candidate-a"},
            {"candidate_id": "candidate-b"},
            "candidate-a",
        ),
    ],
)
def test_same_sample_collision_uses_documented_winner_tie_breaks(
    better_updates,
    worse_updates,
    expected_winner_id,
):
    anchor = Candidate(candidate_id="anchor", sample_stem="sample-a")
    base_collision = replace(
        Candidate(candidate_id="base"),
        review_priority="LOW",
        evidence_score=70,
        seed_event_count=3,
        ms1_area=100.0,
        neutral_loss_mass_error_ppm=2.0,
        precursor_mz=500.004,
        product_mz=359.001,
        observed_neutral_loss_da=141.001,
        sample_stem="sample-b",
    )
    better = replace(base_collision, **better_updates)
    worse = replace(base_collision, **worse_updates)

    clusters = clustering._cluster_candidates_greedy(
        (worse, better, anchor),
        AlignmentConfig(),
    )

    anchor_cluster = _cluster_containing(clusters, "anchor")
    assert frozenset(_ids(anchor_cluster.members)) == frozenset(
        {"anchor", expected_winner_id},
    )
    assert _cluster_member_ids(clusters) == {
        frozenset({"anchor", expected_winner_id}),
        frozenset({worse.candidate_id}),
    }


def test_non_anchor_outside_anchor_clusters_becomes_unanchored_cluster():
    anchor = Candidate(candidate_id="anchor", sample_stem="sample-a")
    distant_non_anchor = replace(
        Candidate(candidate_id="distant-non-anchor"),
        review_priority="LOW",
        precursor_mz=501.0,
        product_mz=360.0,
        observed_neutral_loss_da=141.0,
        sample_stem="sample-b",
    )

    clusters = clustering._cluster_candidates_greedy(
        (distant_non_anchor, anchor),
        AlignmentConfig(),
    )

    unanchored = _cluster_containing(clusters, "distant-non-anchor")
    assert _ids(unanchored.members) == ("distant-non-anchor",)
    assert unanchored.has_anchor is False
    assert unanchored.anchor_members == ()


def _ids(candidates):
    return tuple(candidate.candidate_id for candidate in candidates)


def _cluster_member_ids(clusters):
    return {frozenset(_ids(cluster.members)) for cluster in clusters}


def _cluster_containing(clusters, candidate_id):
    for cluster in clusters:
        if candidate_id in _ids(cluster.members):
            return cluster
    raise AssertionError(f"missing cluster containing {candidate_id}")
