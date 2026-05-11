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
            Candidate(candidate_id="missing-scan-support"),
            ms1_scan_support_score=None,
        ),
        replace(
            Candidate(candidate_id="weak-scan-support"),
            ms1_scan_support_score=0.49,
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


def test_candidate_ordering_prefers_higher_review_priority_within_anchor_status():
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
        evidence_score=100,
        ms1_scan_support_score=0.49,
    )

    ordered = sorted(
        [low, medium, high],
        key=lambda candidate: alignment_candidate_sort_key(candidate, config),
    )

    assert [candidate.candidate_id for candidate in ordered] == [
        "high",
        "medium",
        "low",
    ]


def test_candidate_ordering_uses_stable_tie_breakers_not_input_order():
    config = AlignmentConfig()
    candidates = [
        replace(
            Candidate(candidate_id="sample-b"),
            precursor_mz=500.0,
            ms1_apex_rt=5.0,
            sample_stem="sample-b",
        ),
        replace(
            Candidate(candidate_id="sample-a-z"),
            precursor_mz=500.0,
            ms1_apex_rt=5.0,
            sample_stem="sample-a",
        ),
        replace(
            Candidate(candidate_id="sample-a-a"),
            precursor_mz=500.0,
            ms1_apex_rt=5.0,
            sample_stem="sample-a",
        ),
        replace(
            Candidate(candidate_id="lower-rt"),
            precursor_mz=500.0,
            ms1_apex_rt=4.9,
            sample_stem="sample-z",
        ),
        replace(
            Candidate(candidate_id="lower-mz"),
            precursor_mz=499.9,
            ms1_apex_rt=9.0,
            sample_stem="sample-z",
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
        "lower-mz",
        "lower-rt",
        "sample-a-a",
        "sample-a-z",
        "sample-b",
    ]
    assert [candidate.candidate_id for candidate in ordered] == expected
    assert [candidate.candidate_id for candidate in reverse_ordered] == expected
