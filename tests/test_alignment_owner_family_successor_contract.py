import csv
from dataclasses import replace
from pathlib import Path

import pytest

from tests.test_alignment_owner_clustering import _owner
from xic_extractor.alignment.config import AlignmentConfig
from xic_extractor.alignment.cross_sample_peak_groups import (
    cross_sample_peak_group_edge_fact_from_owner_edge,
    cross_sample_peak_group_edge_facts_from_owner_edges,
    cross_sample_peak_group_hard_gate_challenge_fact_from_owner_edge,
    cross_sample_peak_group_hypothesis_from_owner_feature,
)
from xic_extractor.alignment.edge_scoring import evaluate_owner_edge
from xic_extractor.alignment.owner_clustering import (
    cluster_sample_local_owners,
    review_only_features_from_ambiguous_records,
)
from xic_extractor.alignment.owner_family_successor_contract import (
    OWNER_FAMILY_INVARIANTS,
    owner_clustering_disposition,
    owner_family_successor_mapping,
)
from xic_extractor.alignment.owner_matrix import build_owner_alignment_matrix
from xic_extractor.alignment.ownership_models import AmbiguousOwnerRecord


def test_owner_family_successor_mapping_names_all_required_invariants() -> None:
    feature = _compact_owner_family_feature()
    feature = replace(
        feature,
        confirm_local_owners_with_backfill=True,
        backfill_seed_centers=((feature.family_center_mz, feature.family_center_rt),),
    )

    mappings = owner_family_successor_mapping(feature)
    by_invariant = {mapping.invariant: mapping for mapping in mappings}

    assert tuple(mapping.invariant for mapping in mappings) == OWNER_FAMILY_INVARIANTS
    assert (
        by_invariant["stable_cross_sample_family_membership"].disposition
        == "successor_owned"
    )
    assert by_invariant["owner_edge_evidence_projection"].disposition == (
        "active_policy"
    )
    assert (
        by_invariant["complete_link_edge_semantics"].disposition
        == "active_policy"
    )
    assert by_invariant["hard_family_split_gates"].disposition == "active_policy"
    assert by_invariant["review_only_owner_records"].disposition == "active_policy"
    assert (
        by_invariant["backfill_seed_and_matrix_delivery"].disposition
        == "successor_gap"
    )
    assert "owner_count=2" in by_invariant[
        "stable_cross_sample_family_membership"
    ].current_state
    assert "event_ids=sample-a#a;sample-a#support;sample-b#b" in by_invariant[
        "stable_cross_sample_family_membership"
    ].current_state
    assert "alignment_matrix.tsv" in by_invariant[
        "stable_cross_sample_family_membership"
    ].exit_rule


def test_cross_sample_peak_group_hypothesis_projects_owner_membership() -> None:
    feature = _compact_owner_family_feature()

    assert feature.owners[0].supporting_events

    hypothesis = cross_sample_peak_group_hypothesis_from_owner_feature(feature)

    assert hypothesis.group_hypothesis_id == feature.feature_family_id
    assert hypothesis.public_family_id == feature.feature_family_id
    assert hypothesis.owner_ids == feature.event_cluster_ids
    assert hypothesis.event_ids == (
        "sample-a#a",
        "sample-a#support",
        "sample-b#b",
    )
    assert hypothesis.event_member_count == feature.event_member_count == 3
    assert hypothesis.source == "owner_aligned_feature_shadow"


def test_strong_owner_edge_projects_support_fact_and_marks_successor_owned() -> None:
    edge_evidence = []
    feature = cluster_sample_local_owners(
        (_owner("sample-a", "a", apex_rt=8.40), _owner("sample-b", "b", apex_rt=8.60)),
        config=AlignmentConfig(),
        edge_evidence_sink=edge_evidence,
    )[0]

    assert len(edge_evidence) == 1
    assert edge_evidence[0].decision == "strong_edge"

    facts = cross_sample_peak_group_edge_facts_from_owner_edges(edge_evidence)
    assert facts == (
        cross_sample_peak_group_edge_fact_from_owner_edge(edge_evidence[0]),
    )

    fact = facts[0]
    assert fact.owner_pair_ids == ("OWN-sample-a-a", "OWN-sample-b-b")
    assert fact.decision == "strong_edge"
    assert fact.role == "membership_support"
    assert fact.failure_reason == ""
    assert fact.rt_raw_delta_sec == pytest.approx(12.0)
    assert fact.rt_drift_corrected_delta_sec is None
    assert fact.drift_prior_source == "none"
    assert fact.injection_order_gap is None
    assert fact.score == edge_evidence[0].score
    assert fact.reason == edge_evidence[0].reason
    assert fact.source == "owner_edge_evidence_shadow"

    by_invariant = {
        mapping.invariant: mapping
        for mapping in owner_family_successor_mapping(
            feature,
            edge_evidence=edge_evidence,
        )
    }

    edge_mapping = by_invariant["owner_edge_evidence_projection"]
    assert edge_mapping.disposition == "successor_owned"
    assert "edge_fact_count=1" in edge_mapping.current_state
    assert "support_count=1" in edge_mapping.current_state
    assert "challenge_count=0" in edge_mapping.current_state
    assert "CrossSamplePeakGroupEdgeFact" in edge_mapping.successor_surface
    assert by_invariant["complete_link_edge_semantics"].disposition == (
        "active_policy"
    )


def test_weak_owner_edge_projects_challenge_fact() -> None:
    edge_evidence = []

    cluster_sample_local_owners(
        (_owner("sample-a", "a", apex_rt=8.50), _owner("sample-b", "b", apex_rt=9.70)),
        config=AlignmentConfig(),
        edge_evidence_sink=edge_evidence,
    )

    assert len(edge_evidence) == 1
    assert edge_evidence[0].decision == "weak_edge"

    fact = cross_sample_peak_group_edge_fact_from_owner_edge(edge_evidence[0])

    assert fact.owner_pair_ids == ("OWN-sample-a-a", "OWN-sample-b-b")
    assert fact.decision == "weak_edge"
    assert fact.role == "membership_challenge"
    assert fact.failure_reason == ""
    assert fact.rt_raw_delta_sec == pytest.approx(72.0)
    assert fact.score == edge_evidence[0].score
    assert fact.reason == edge_evidence[0].reason


def test_edge_projection_ignores_edges_outside_owner_family() -> None:
    edge_evidence = []
    features = cluster_sample_local_owners(
        (
            _owner("sample-a", "a", apex_rt=10.00),
            _owner("sample-b", "b", apex_rt=10.20),
            _owner("sample-c", "c", apex_rt=11.50),
        ),
        config=AlignmentConfig(preferred_rt_sec=30.0, max_rt_sec=120.0),
        edge_evidence_sink=edge_evidence,
    )

    family = next(feature for feature in features if len(feature.owners) == 2)
    hypothesis = cross_sample_peak_group_hypothesis_from_owner_feature(
        family,
        edge_evidence=edge_evidence,
    )

    assert hypothesis.owner_ids == ("OWN-sample-a-a", "OWN-sample-b-b")
    assert tuple(fact.owner_pair_ids for fact in hypothesis.edge_facts) == (
        ("OWN-sample-a-a", "OWN-sample-b-b"),
    )


def test_blocked_owner_edge_projects_challenge_fact_without_policy_promotion() -> None:
    edge = evaluate_owner_edge(
        _owner("sample-a", "a"),
        _owner("sample-a", "b"),
        config=AlignmentConfig(),
    )

    assert edge.decision == "blocked_edge"
    assert edge.failure_reason == "same_sample"

    fact = cross_sample_peak_group_edge_fact_from_owner_edge(edge)

    assert fact.decision == "blocked_edge"
    assert fact.role == "membership_challenge"
    assert fact.failure_reason == "same_sample"
    assert fact.construction_policy == "construction_time_hard_gate_observed"
    assert "blocked: same_sample" in fact.reason


def test_identity_conflict_review_only_feature_projects_review_challenge_fact() -> None:
    feature = cluster_sample_local_owners(
        (
            _owner("sample-a", "conflict", identity_conflict=True),
            _owner("sample-b", "clean"),
        ),
        config=AlignmentConfig(),
    )[0]

    hypothesis = cross_sample_peak_group_hypothesis_from_owner_feature(feature)

    assert len(hypothesis.review_facts) == 1
    fact = hypothesis.review_facts[0]
    assert fact.feature_family_id == feature.feature_family_id
    assert fact.public_family_id == feature.feature_family_id
    assert fact.review_only is True
    assert fact.identity_conflict is True
    assert fact.reason == "identity_conflict"
    assert fact.evidence == "identity_conflict_review_only"
    assert fact.ambiguous_sample_stem is None
    assert fact.ambiguous_candidate_ids == ()
    assert fact.source == "owner_aligned_feature_review_shadow"

    by_invariant = {
        mapping.invariant: mapping
        for mapping in owner_family_successor_mapping(feature)
    }

    review_mapping = by_invariant["review_only_owner_records"]
    assert review_mapping.disposition == "successor_owned"
    assert "review_fact_count=1" in review_mapping.current_state
    assert "identity_conflict=1" in review_mapping.current_state
    assert "CrossSamplePeakGroupReviewFact" in review_mapping.successor_surface


def test_ambiguous_review_only_feature_projects_candidate_review_details() -> None:
    feature = review_only_features_from_ambiguous_records(
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
        start_index=1,
    )[0]

    hypothesis = cross_sample_peak_group_hypothesis_from_owner_feature(feature)

    assert len(hypothesis.review_facts) == 1
    fact = hypothesis.review_facts[0]
    assert fact.reason == "ambiguous_owner"
    assert fact.review_only is True
    assert fact.identity_conflict is False
    assert fact.ambiguous_sample_stem == "sample-a"
    assert fact.ambiguous_candidate_ids == ("sample-a#1", "sample-a#2")
    assert fact.evidence == "ambiguous_ms1_owner_review_only"

    by_invariant = {
        mapping.invariant: mapping
        for mapping in owner_family_successor_mapping(feature)
    }

    review_mapping = by_invariant["review_only_owner_records"]
    assert review_mapping.disposition == "successor_owned"
    assert "review_fact_count=1" in review_mapping.current_state
    assert "ambiguous_owner=1" in review_mapping.current_state
    assert "sample-a#1,sample-a#2" in review_mapping.current_state


def test_blocked_edge_projects_hard_gate_observation_without_policy_promotion() -> None:
    owners = (_owner("sample-a", "a"), _owner("sample-a", "b"))
    edge = evaluate_owner_edge(owners[0], owners[1], config=AlignmentConfig())
    feature = replace(
        _compact_owner_family_feature(),
        feature_family_id="FAM999999",
        owners=owners,
        evidence="manual_blocked_edge_shadow_fixture",
    )

    assert edge.decision == "blocked_edge"
    assert edge.failure_reason == "same_sample"

    challenge = cross_sample_peak_group_hard_gate_challenge_fact_from_owner_edge(
        edge,
    )
    assert challenge is not None
    assert challenge.owner_pair_ids == ("OWN-sample-a-a", "OWN-sample-a-b")
    assert challenge.failure_reason == "same_sample"
    assert challenge.role == "split_gate_challenge"
    assert challenge.construction_policy == "construction_time_hard_gate_observed"

    hypothesis = cross_sample_peak_group_hypothesis_from_owner_feature(
        feature,
        edge_evidence=(edge,),
    )
    assert hypothesis.hard_gate_challenge_facts == (challenge,)

    by_invariant = {
        mapping.invariant: mapping
        for mapping in owner_family_successor_mapping(
            feature,
            edge_evidence=(edge,),
        )
    }

    assert by_invariant["owner_edge_evidence_projection"].disposition == (
        "successor_owned"
    )
    assert by_invariant["complete_link_edge_semantics"].disposition == (
        "active_policy"
    )
    assert by_invariant["hard_family_split_gates"].disposition == "active_policy"
    assert "hard_gate_challenge_fact_count=1" in by_invariant[
        "hard_family_split_gates"
    ].current_state
    assert "same_sample" in by_invariant["hard_family_split_gates"].current_state


def test_owner_clustering_keeps_stage_after_review_fact_projection() -> None:
    feature = cluster_sample_local_owners(
        (
            _owner("sample-a", "conflict", identity_conflict=True),
            _owner("sample-b", "clean"),
        ),
        config=AlignmentConfig(),
    )[0]

    decision = owner_clustering_disposition(owner_family_successor_mapping(feature))

    assert decision.disposition == "keep_as_stage"
    assert "review_only_owner_records" not in decision.blocking_invariants
    assert "complete_link_edge_semantics" in decision.blocking_invariants
    assert "hard_family_split_gates" in decision.blocking_invariants
    assert "backfill_seed_and_matrix_delivery" in decision.blocking_invariants


def test_c6_b_final_disposition_keeps_stage_after_shadow_evidence() -> None:
    edge_evidence = []
    edge_feature = cluster_sample_local_owners(
        (_owner("sample-a", "a"), _owner("sample-b", "b")),
        config=AlignmentConfig(),
        edge_evidence_sink=edge_evidence,
    )[0]
    review_feature = cluster_sample_local_owners(
        (
            _owner("sample-a", "conflict", identity_conflict=True),
            _owner("sample-b", "clean"),
        ),
        config=AlignmentConfig(),
    )[0]

    a2_mappings = owner_family_successor_mapping(
        edge_feature,
        edge_evidence=edge_evidence,
    )
    a3_review_mapping = next(
        mapping
        for mapping in owner_family_successor_mapping(review_feature)
        if mapping.invariant == "review_only_owner_records"
    )
    mappings = tuple(
        a3_review_mapping
        if mapping.invariant == "review_only_owner_records"
        else mapping
        for mapping in a2_mappings
    )
    by_invariant = {mapping.invariant: mapping for mapping in mappings}
    decision = owner_clustering_disposition(mappings)

    assert by_invariant["stable_cross_sample_family_membership"].disposition == (
        "successor_owned"
    )
    assert by_invariant["owner_edge_evidence_projection"].disposition == (
        "successor_owned"
    )
    assert by_invariant["review_only_owner_records"].disposition == "successor_owned"
    assert decision.disposition == "keep_as_stage"
    assert "C6-B final disposition" in decision.reason
    assert "shadow projection" in decision.reason
    assert "stable_cross_sample_family_membership" not in decision.blocking_invariants
    assert "owner_edge_evidence_projection" not in decision.blocking_invariants
    assert "complete_link_edge_semantics" in decision.blocking_invariants
    assert "hard_family_split_gates" in decision.blocking_invariants
    assert "review_only_owner_records" not in decision.blocking_invariants
    assert "backfill_seed_and_matrix_delivery" in decision.blocking_invariants
    assert "alignment_matrix.tsv" in decision.exit_rule
    assert "alignment_cells.tsv" in decision.exit_rule
    assert "alignment_review.tsv" in decision.exit_rule
    assert "owner_edge_evidence.tsv" in decision.exit_rule
    assert "when emitted" in decision.exit_rule
    assert "Do not promote" in decision.exit_rule
    assert "successor-owned" in decision.exit_rule


def test_compact_owner_family_tsv_triad_keeps_full_schema_and_rows(
    tmp_path: Path,
) -> None:
    from xic_extractor.alignment.tsv_writer import (
        write_alignment_cells_tsv,
        write_alignment_matrix_tsv,
        write_alignment_review_tsv,
    )

    feature = _compact_owner_family_feature()
    matrix = build_owner_alignment_matrix(
        (feature,),
        sample_order=("sample-a", "sample-b", "sample-c"),
        ambiguous_by_sample={},
        rescued_cells=(),
    )

    matrix_path = write_alignment_matrix_tsv(
        tmp_path / "alignment_matrix.tsv",
        matrix,
    )
    cells_path = write_alignment_cells_tsv(tmp_path / "alignment_cells.tsv", matrix)
    review_path = write_alignment_review_tsv(
        tmp_path / "alignment_review.tsv",
        matrix,
    )

    assert _tsv_rows(matrix_path) == [
        [
            "feature_family_id",
            "neutral_loss_tag",
            "family_center_mz",
            "family_center_rt",
            "sample-a",
            "sample-b",
            "sample-c",
        ],
        ["FAM000001", "NL116", "500", "8.5", "1000", "1000", ""],
    ]
    assert _tsv_rows(cells_path) == [
        [
            "feature_family_id",
            "sample_stem",
            "status",
            "area",
            "apex_rt",
            "height",
            "peak_start_rt",
            "peak_end_rt",
            "rt_delta_sec",
            "trace_quality",
            "scan_support_score",
            "source_candidate_id",
            "source_raw_file",
            "neutral_loss_tag",
            "family_center_mz",
            "family_center_rt",
            "reason",
            "region_candidate_count",
            "region_selected_proposal_sources",
            "region_selected_merge_note",
            "region_shadow_status",
            "region_shadow_verdict",
            "region_merge_suggestion_source",
            "region_area_ratio",
            "region_selected_interval_count",
            "region_selected_interval_gap_max_min",
            "region_local_mixture_diagnostic",
            "region_local_mixture_reason",
            "region_review_reason",
        ],
        [
            "FAM000001",
            "sample-a",
            "detected",
            "1000",
            "8.4",
            "100",
            "8.35",
            "8.45",
            "'-6",
            "owner_exact_apex_match",
            "",
            "sample-a#a",
            "",
            "NL116",
            "500",
            "8.5",
            "sample-local MS1 owner with original MS2 evidence",
            *[""] * 12,
        ],
        [
            "FAM000001",
            "sample-b",
            "detected",
            "1000",
            "8.6",
            "100",
            "8.55",
            "8.65",
            "6",
            "owner_exact_apex_match",
            "",
            "sample-b#b",
            "",
            "NL116",
            "500",
            "8.5",
            "sample-local MS1 owner with original MS2 evidence",
            *[""] * 12,
        ],
        [
            "FAM000001",
            "sample-c",
            "absent",
            "",
            "",
            "",
            "",
            "",
            "",
            "absent",
            "",
            "",
            "",
            "NL116",
            "500",
            "8.5",
            "no local MS1 owner",
            *[""] * 12,
        ],
    ]
    assert _tsv_rows(review_path) == [
        [
            "feature_family_id",
            "neutral_loss_tag",
            "family_center_mz",
            "family_center_rt",
            "family_product_mz",
            "family_observed_neutral_loss_da",
            "has_anchor",
            "event_cluster_count",
            "event_cluster_ids",
            "event_member_count",
            "detected_count",
            "absent_count",
            "unchecked_count",
            "duplicate_assigned_count",
            "ambiguous_ms1_owner_count",
            "present_rate",
            "identity_decision",
            "identity_confidence",
            "primary_evidence",
            "identity_reason",
            "quantifiable_detected_count",
            "quantifiable_rescue_count",
            "accepted_cell_count",
            "accepted_rescue_count",
            "review_rescue_count",
            "include_in_primary_matrix",
            "row_flags",
            "artificial_adduct_role",
            "artificial_adduct_name",
            "artificial_adduct_related_family_id",
            "artificial_adduct_mz_delta_error_ppm",
            "artificial_adduct_rt_delta_min",
            "representative_samples",
            "family_evidence",
            "warning",
            "reason",
        ],
        [
            "FAM000001",
            "NL116",
            "500",
            "8.5",
            "383.953",
            "116.047",
            "TRUE",
            "2",
            "OWN-sample-a-a;OWN-sample-b-b",
            "3",
            "2",
            "1",
            "0",
            "0",
            "0",
            "0.666667",
            "production_family",
            "high",
            "owner_complete_link",
            "owner_complete_link",
            "2",
            "0",
            "2",
            "0",
            "0",
            "TRUE",
            *[""] * 6,
            "sample-a;sample-b",
            "owner_complete_link;owner_count=2",
            "",
            "anchor family; 2/3 present; 0 MS1 backfilled; "
            "merged 2 event clusters",
        ],
    ]


def test_cross_sample_peak_group_shadow_has_no_production_path_imports() -> None:
    shared_peak_identity_dir = (
        Path("xic_extractor/alignment")
        / ("shared_peak_identity_" + "explanation")
    )
    production_paths = [
        Path("xic_extractor/alignment/__init__.py"),
        Path("xic_extractor/alignment/pipeline.py"),
        Path("xic_extractor/alignment/pipeline_outputs.py"),
        Path("xic_extractor/alignment/process_backend.py"),
        Path("xic_extractor/alignment/owner_backfill.py"),
        Path("xic_extractor/alignment/owner_matrix.py"),
        Path("xic_extractor/alignment/tsv_writer.py"),
        Path("xic_extractor/alignment/xlsx_writer.py"),
        Path("xic_extractor/peak_detection/hypotheses.py"),
        *shared_peak_identity_dir.rglob("*.py"),
    ]

    for path in production_paths:
        text = path.read_text(encoding="utf-8")
        assert "CrossSamplePeakGroupHypothesis" not in text
        assert "CrossSamplePeakGroupEdgeFact" not in text
        assert "CrossSamplePeakGroupReviewFact" not in text
        assert "CrossSamplePeakGroupHardGateChallengeFact" not in text
        assert "cross_sample_peak_group" not in text


def _compact_owner_family_feature():
    owner_a = _owner("sample-a", "a", apex_rt=8.40)
    supporting_event = replace(
        owner_a.primary_identity_event,
        candidate_id="sample-a#support",
        evidence_score=70,
        seed_event_count=1,
    )
    owner_a = replace(owner_a, supporting_events=(supporting_event,))
    return cluster_sample_local_owners(
        (
            owner_a,
            _owner("sample-b", "b", apex_rt=8.60),
        ),
        config=AlignmentConfig(identity_rt_candidate_window_sec=180.0),
    )[0]


def _tsv_rows(path: Path) -> list[list[str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.reader(handle, delimiter="\t"))
