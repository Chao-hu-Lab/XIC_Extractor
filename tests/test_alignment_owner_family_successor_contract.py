import csv
from dataclasses import replace
from pathlib import Path

from tests.test_alignment_owner_clustering import _owner
from xic_extractor.alignment.config import AlignmentConfig
from xic_extractor.alignment.cross_sample_peak_groups import (
    cross_sample_peak_group_hypothesis_from_owner_feature,
)
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


def test_owner_family_successor_mapping_keeps_review_only_records_active() -> None:
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

    by_invariant = {
        mapping.invariant: mapping
        for mapping in owner_family_successor_mapping(feature)
    }

    review_mapping = by_invariant["review_only_owner_records"]
    assert review_mapping.disposition == "active_policy"
    assert review_mapping.current_state == "review_only_present"
    assert "ambiguous cells" in review_mapping.exit_rule


def test_owner_clustering_disposition_keeps_stage_until_successor_parity() -> None:
    feature = cluster_sample_local_owners(
        (_owner("sample-a", "a"), _owner("sample-b", "b")),
        config=AlignmentConfig(),
    )[0]

    decision = owner_clustering_disposition(
        owner_family_successor_mapping(feature),
    )

    assert decision.disposition == "keep_as_stage"
    assert "successor spine does not yet own" in decision.reason
    assert "stable_cross_sample_family_membership" not in decision.blocking_invariants
    assert "complete_link_edge_semantics" in decision.blocking_invariants
    assert "hard_family_split_gates" in decision.blocking_invariants
    assert "review_only_owner_records" in decision.blocking_invariants
    assert "backfill_seed_and_matrix_delivery" in decision.blocking_invariants
    assert "alignment_matrix.tsv" in decision.exit_rule
    assert "alignment_cells.tsv" in decision.exit_rule
    assert "alignment_review.tsv" in decision.exit_rule


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
