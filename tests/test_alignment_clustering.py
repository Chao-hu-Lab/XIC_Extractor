import math
from dataclasses import dataclass, replace
from types import SimpleNamespace

import pytest

from xic_extractor.alignment.clustering import (
    alignment_candidate_sort_key,
    is_alignment_anchor,
)
from xic_extractor.alignment.config import AlignmentConfig


@dataclass(frozen=True)
class Candidate:
    candidate_id: str
    review_priority: str = "HIGH"
    evidence_score: int = 60
    seed_event_count: int = 2
    ms1_peak_found: bool = True
    ms1_scan_support_score: float | None = 0.5
    ms1_area: float | None = 100.0
    neutral_loss_mass_error_ppm: float = 1.0
    precursor_mz: float = 500.0
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
