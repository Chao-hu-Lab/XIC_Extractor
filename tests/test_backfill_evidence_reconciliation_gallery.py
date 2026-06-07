from __future__ import annotations

import csv
import json
import os
from pathlib import Path

import pytest

from tools.diagnostics import backfill_evidence_reconciliation_gallery as cli
from xic_extractor.alignment.tsv_writer import (
    ALIGNMENT_CELLS_COLUMNS,
    ALIGNMENT_OWNER_BACKFILL_SEED_AUDIT_COLUMNS,
    ALIGNMENT_REVIEW_COLUMNS,
)
from xic_extractor.diagnostics import backfill_reconciliation_gallery as gallery

EXPECTED_GROUP_COLUMNS = (
    "schema_version",
    "priority_rank",
    "feature_family_id",
    "seed_group_id",
    "seed_group_basis",
    "seed_mz",
    "seed_rt",
    "seed_rt_window",
    "seed_ppm",
    "tag_or_class",
    "product_behavior_state",
    "evidence_authority_state",
    "reconciliation_class",
    "detected_cell_count",
    "rescued_cell_count",
    "provisional_cell_count",
    "top_product_reason",
    "top_support_component",
    "top_blocker",
    "missing_evidence",
    "overlay_png_path",
    "overlay_trace_json_path",
    "source_artifacts",
    "source_warnings",
)

EXPECTED_REPRESENTATIVE_CELL_COLUMNS = (
    "schema_version",
    "feature_family_id",
    "seed_group_id",
    "representative_roles",
    "sample_stem",
    "cell_status",
    "product_cell_state",
    "shape_similarity",
    "scan_support_score",
    "apex_delta_sec",
    "boundary_overlap",
    "interference_signal",
    "representative_reason",
    "source_row_key",
)

EXPECTED_AUTHORITY_STATES = (
    "product_grade_support",
    "review_only_visual_support",
    "dependent_context_only",
    "human_visual_judgment_only",
    "evidence_blocks_backfill",
    "evidence_inconclusive",
    "not_assessable",
)

EXPECTED_RECONCILIATION_CLASSES = (
    "product_accepts_and_product_grade_supports",
    "product_accepts_and_visual_supports",
    "product_rejects_but_product_grade_supports",
    "product_rejects_but_visual_supports",
    "product_accepts_but_evidence_conflicts",
    "product_rejects_and_evidence_blocks",
    "evidence_inconclusive",
    "not_assessable_missing_overlay",
    "not_assessable_missing_seed_provenance",
    "not_assessable_join_gap",
)

EXPECTED_RECONCILIATION_CLASS_PRIORITY = (
    "product_rejects_but_product_grade_supports",
    "product_rejects_but_visual_supports",
    "product_accepts_but_evidence_conflicts",
    "not_assessable_missing_overlay",
    "not_assessable_missing_seed_provenance",
    "not_assessable_join_gap",
    "evidence_inconclusive",
    "product_accepts_and_visual_supports",
    "product_accepts_and_product_grade_supports",
    "product_rejects_and_evidence_blocks",
)


def test_fixtures_use_real_alignment_writer_columns() -> None:
    assert set(_review_row("FAM001")) == set(ALIGNMENT_REVIEW_COLUMNS)
    assert set(_cell_row("FAM001", "S1", "detected")) == set(ALIGNMENT_CELLS_COLUMNS)
    assert set(_seed_row("FAM001", "S2")) == set(
        ALIGNMENT_OWNER_BACKFILL_SEED_AUDIT_COLUMNS,
    )


def test_builds_deterministic_seed_group_from_seed_audit() -> None:
    result = gallery.build_reconciliation_index(
        review_rows=[_review_row("FAM001")],
        cell_rows=[
            _cell_row("FAM001", "S1", "detected"),
            _cell_row("FAM001", "S2", "rescued"),
        ],
        seed_audit_rows=[_seed_row("FAM001", "S2")],
    )

    assert len(result.groups) == 1
    group = result.groups[0]
    assert group.feature_family_id == "FAM001"
    assert group.seed_group_basis == "seed_audit"
    assert group.seed_group_id == (
        "seed::FAM001::mz=269.145::rt=10.0000::"
        "window=9.0000-11.0000::ppm=10"
    )
    assert group.detected_cell_count == 1
    assert group.rescued_cell_count == 1
    assert group.product_behavior_state == "product_rescued_context_only"


def test_detected_zero_families_are_excluded_from_backfill_review_queue() -> None:
    result = gallery.build_reconciliation_index(
        review_rows=[
            _review_row("FAM_SEEDED"),
            _review_row("FAM_ZERO", detected="0", rescued="2"),
        ],
        cell_rows=[
            _cell_row("FAM_SEEDED", "S1", "detected"),
            _cell_row("FAM_SEEDED", "S2", "rescued"),
            _cell_row("FAM_ZERO", "S2", "rescued"),
        ],
        seed_audit_rows=[
            _seed_row("FAM_SEEDED", "S2"),
            _seed_row("FAM_ZERO", "S2"),
        ],
        seed_aware_family_rows=[
            {
                "feature_family_id": "FAM_ZERO",
                "review_classification": "seed_shape_supported_review_candidate",
                "png_paths": "plots/fam-zero.png",
            },
        ],
        candidate_gate_rows=[
            {
                "feature_family_id": "FAM_ZERO",
                "candidate_gate_status": "production_candidate",
                "support_components": "validated_tier2_trace_evidence",
                "challenge_blockers": "",
            },
        ],
    )

    assert [group.feature_family_id for group in result.groups] == ["FAM_SEEDED"]
    assert result.summary["excluded_family_counts"] == {
        "detected_zero_family": 1,
    }


def test_product_grade_and_visual_support_remain_separate() -> None:
    result = gallery.build_reconciliation_index(
        review_rows=[_review_row("FAM002")],
        cell_rows=[_cell_row("FAM002", "S2", "rescued")],
        seed_audit_rows=[_seed_row("FAM002", "S2")],
        candidate_gate_rows=[
            {
                "feature_family_id": "FAM002",
                "candidate_gate_status": "production_candidate",
                "support_components": "validated_tier2_trace_evidence",
                "challenge_blockers": "",
            },
        ],
        seed_aware_family_rows=[
            {
                "feature_family_id": "FAM002",
                "review_classification": "seed_shape_supported_review_candidate",
                "review_reason": "seed-specific overlays support MS1 shape",
                "png_paths": "plots/fam002.png",
            },
        ],
    )

    group = result.groups[0]
    assert group.evidence_authority_state == "product_grade_support"
    assert "validated_tier2_trace_evidence" in group.product_grade_support_components
    assert (
        "seed_shape_supported_review_candidate"
        in group.review_only_visual_components
    )
    assert group.reconciliation_class == "product_rejects_but_product_grade_supports"
    assert group.overlay_png_path == "plots/fam002.png"


def test_stale_candidate_gate_source_hash_fails_closed() -> None:
    result = gallery.build_reconciliation_index(
        review_rows=[_review_row("FAM_STALE")],
        cell_rows=[_cell_row("FAM_STALE", "S2", "rescued")],
        seed_audit_rows=[_seed_row("FAM_STALE", "S2")],
        candidate_gate_rows=[
            {
                "feature_family_id": "FAM_STALE",
                "candidate_gate_status": "production_candidate",
                "support_components": "validated_tier2_trace_evidence",
                "challenge_blockers": "",
                "source_review_sha256": "STALE_REVIEW_HASH",
                "source_cell_sha256": "expected_cell_hash",
            },
        ],
        input_artifacts={
            "alignment_review_sha256": "expected_review_hash",
            "alignment_cells_sha256": "expected_cell_hash",
        },
    )

    group = result.groups[0]
    assert group.evidence_authority_state == "not_assessable"
    assert group.reconciliation_class == "not_assessable_join_gap"
    assert group.product_grade_support_components == ()
    assert "stale_candidate_gate_review_sha256_mismatch" in group.missing_evidence
    assert "stale_candidate_gate_review_sha256_mismatch" in group.source_warnings


def test_malformed_candidate_gate_with_blockers_fails_closed() -> None:
    result = gallery.build_reconciliation_index(
        review_rows=[_review_row("FAM_BLOCKED")],
        cell_rows=[_cell_row("FAM_BLOCKED", "S2", "rescued")],
        seed_audit_rows=[_seed_row("FAM_BLOCKED", "S2")],
        candidate_gate_rows=[
            {
                "feature_family_id": "FAM_BLOCKED",
                "candidate_gate_status": "production_candidate",
                "support_components": "validated_tier2_trace_evidence",
                "challenge_blockers": "missing_seed_trace",
            },
        ],
    )

    group = result.groups[0]
    assert group.evidence_authority_state == "evidence_blocks_backfill"
    assert group.reconciliation_class == "product_rejects_and_evidence_blocks"
    assert group.product_grade_support_components == ()
    assert group.blocker_components == ("missing_seed_trace",)


def test_missing_overlay_and_join_gap_fail_closed() -> None:
    result = gallery.build_reconciliation_index(
        review_rows=[
            _review_row("FAM_MISSING_OVERLAY"),
            _review_row("FAM_JOIN_GAP"),
        ],
        cell_rows=[
            _cell_row("FAM_MISSING_OVERLAY", "S1", "rescued"),
            _cell_row("FAM_JOIN_GAP", "S1", "rescued"),
        ],
        seed_audit_rows=[
            _seed_row("FAM_MISSING_OVERLAY", "S1"),
            _seed_row("FAM_JOIN_GAP", "S_NOT_IN_CELLS"),
        ],
        seed_aware_family_rows=[
            {
                "feature_family_id": "FAM_MISSING_OVERLAY",
                "review_classification": "not_assessable",
                "review_reason": "overlay missing",
            },
        ],
    )

    by_family = {group.feature_family_id: group for group in result.groups}
    missing_overlay = by_family["FAM_MISSING_OVERLAY"]
    assert missing_overlay.evidence_authority_state == "not_assessable"
    assert missing_overlay.reconciliation_class == "not_assessable_missing_overlay"
    assert "missing_overlay" in missing_overlay.missing_evidence

    join_gap = by_family["FAM_JOIN_GAP"]
    assert join_gap.evidence_authority_state == "not_assessable"
    assert join_gap.reconciliation_class == "not_assessable_join_gap"
    assert "join_gap_seed_audit_sample_not_in_cells" in join_gap.source_warnings


def test_review_required_overlay_is_human_judgment_not_hard_blocker() -> None:
    result = gallery.build_reconciliation_index(
        review_rows=[
            _review_row(
                "FAM_REVIEW",
                identity_decision="production_family",
                include_in_primary_matrix="TRUE",
                row_flags="backfill_cell_evidence_required",
            ),
        ],
        cell_rows=[
            _cell_row("FAM_REVIEW", "S1", "detected"),
            _cell_row("FAM_REVIEW", "S2", "rescued"),
        ],
        seed_audit_rows=[_seed_row("FAM_REVIEW", "S2")],
        overlay_rows=[
            {
                "feature_family_id": "FAM_REVIEW",
                "family_verdict": "review_required_neighboring_ms1_interference",
                "png_path": "plots/fam-review.png",
            },
        ],
    )

    group = result.groups[0]
    assert group.evidence_authority_state == "human_visual_judgment_only"
    assert group.reconciliation_class == "evidence_inconclusive"
    assert group.top_blocker == "review_required_neighboring_ms1_interference"
    assert group.overlay_png_path == "plots/fam-review.png"


def test_overlay_metric_notes_render_evidence_chain_without_group_tsv_schema_change(
    tmp_path: Path,
) -> None:
    result = gallery.build_reconciliation_index(
        review_rows=[_review_row("FAM_OWNMAX")],
        cell_rows=[
            _cell_row("FAM_OWNMAX", "S1", "detected"),
            _cell_row("FAM_OWNMAX", "S2", "rescued"),
        ],
        seed_audit_rows=[_seed_row("FAM_OWNMAX", "S2")],
        overlay_rows=[
            {
                "feature_family_id": "FAM_OWNMAX",
                "family_verdict": "ms1_shape_supports_family_backfill",
                "png_path": "plots/fam-ownmax.png",
                "trace_data_json": "plots/fam-ownmax_trace_data.json",
                "shape_supported_fraction": "0.625",
                "absolute_own_max_shape_supported_fraction": "0.875",
                "absolute_trace_apex_cluster_fraction": "0.75",
                "global_apex_interference_fraction": "0.25",
                "low_selected_peak_dominance_fraction": "0",
            },
        ],
    )

    group = result.groups[0]
    assert "own-max shape support=0.875" in group.overlay_evidence_notes
    assert "absolute apex cluster=0.75" in group.overlay_evidence_notes

    html_path = tmp_path / "gallery.html"
    gallery.write_reconciliation_gallery_html(
        html_path,
        result,
        output_paths={
            "groups_tsv": tmp_path / "groups.tsv",
            "representative_cells_tsv": tmp_path / "representatives.tsv",
            "summary_json": tmp_path / "summary.json",
        },
    )
    text = html_path.read_text(encoding="utf-8")
    assert "overlay evidence metrics" in text
    assert "own-max shape support=0.875" in text
    assert "apex-aligned shape support=0.625" in text

    paths = gallery.write_reconciliation_outputs(tmp_path / "out", result)
    assert "overlay_evidence_notes" not in _read_header(paths["groups_tsv"])


def test_gallery_notes_include_anchor_peak_own_max_cell_evidence(
    tmp_path: Path,
) -> None:
    trace_json = tmp_path / "fam-anchor_trace_data.json"
    trace_json.write_text(
        json.dumps(
            {
                "family_id": "FAM_ANCHOR",
                "rt_min": 9.0,
                "rt_max": 11.0,
                "evidence_summary": {
                    "family_verdict": "review_required_neighboring_ms1_interference"
                },
                "traces": [
                    _overlay_trace("S_DET", "detected", 10.0, [0, 300, 1000, 300, 0]),
                    _overlay_trace(
                        "S_SUPPORT",
                        "rescued",
                        10.02,
                        [0, 280, 940, 310, 0],
                    ),
                    _overlay_trace(
                        "S_REVIEW",
                        "rescued",
                        10.03,
                        [900, 500, 80, 500, 920],
                    ),
                    _overlay_trace(
                        "S_DUP",
                        "rescued",
                        10.01,
                        [0, 270, 930, 305, 0],
                    ),
                ],
            }
        ),
        encoding="utf-8",
    )
    result = gallery.build_reconciliation_index(
        review_rows=[_review_row("FAM_ANCHOR", detected="1", rescued="3")],
        cell_rows=[
            _cell_row("FAM_ANCHOR", "S_DET", "detected", apex_rt="10.0"),
            _cell_row("FAM_ANCHOR", "S_SUPPORT", "rescued", apex_rt="10.02"),
            _cell_row("FAM_ANCHOR", "S_REVIEW", "rescued", apex_rt="10.03"),
            _cell_row(
                "FAM_ANCHOR",
                "S_DUP",
                "rescued",
                apex_rt="10.01",
                gap_fill_state="not_filled",
                gap_fill_reason="not_requested_duplicate_loser",
            ),
        ],
        seed_audit_rows=[
            _seed_row("FAM_ANCHOR", "S_SUPPORT"),
            _seed_row("FAM_ANCHOR", "S_REVIEW"),
            _seed_row("FAM_ANCHOR", "S_DUP"),
        ],
        overlay_rows=[
            {
                "feature_family_id": "FAM_ANCHOR",
                "family_verdict": "review_required_neighboring_ms1_interference",
                "png_path": "plots/fam-anchor.png",
                "trace_data_json": str(trace_json),
            },
        ],
    )

    group = result.groups[0]
    assert "anchor peak RT=10" in group.overlay_evidence_notes
    assert any(
        note.startswith("anchor same-peak rescued support=S_SUPPORT")
        for note in group.overlay_evidence_notes
    )
    assert any(
        note.startswith("anchor same-peak review=S_REVIEW")
        for note in group.overlay_evidence_notes
    )
    assert any(
        "S_DUP:alignment_gap_fill_duplicate_loser" in note
        for note in group.overlay_evidence_notes
    )

    html_path = tmp_path / "gallery.html"
    gallery.write_reconciliation_gallery_html(
        html_path,
        result,
        output_paths={
            "groups_tsv": tmp_path / "groups.tsv",
            "representative_cells_tsv": tmp_path / "representatives.tsv",
            "summary_json": tmp_path / "summary.json",
        },
    )
    text = html_path.read_text(encoding="utf-8")
    assert "anchor own-max shape threshold=0.5" in text
    assert "S_SUPPORT" in text
    assert "alignment_gap_fill_duplicate_loser" in text


def test_gallery_anchor_notes_are_scoped_to_seed_group_cells(tmp_path: Path) -> None:
    trace_json = tmp_path / "fam-seed-scope_trace_data.json"
    trace_json.write_text(
        json.dumps(
            {
                "family_id": "FAM_SEED_SCOPE",
                "rt_min": 9.0,
                "rt_max": 11.0,
                "evidence_summary": {
                    "family_verdict": "review_required_neighboring_ms1_interference"
                },
                "traces": [
                    _overlay_trace("S_DET", "detected", 10.0, [0, 300, 1000, 300, 0]),
                    _overlay_trace(
                        "S_SEED_A",
                        "rescued",
                        10.02,
                        [0, 280, 940, 310, 0],
                    ),
                    _overlay_trace(
                        "S_SEED_B",
                        "rescued",
                        10.03,
                        [0, 290, 930, 300, 0],
                    ),
                ],
            }
        ),
        encoding="utf-8",
    )
    result = gallery.build_reconciliation_index(
        review_rows=[_review_row("FAM_SEED_SCOPE", detected="1", rescued="2")],
        cell_rows=[
            _cell_row("FAM_SEED_SCOPE", "S_DET", "detected", apex_rt="10.0"),
            _cell_row("FAM_SEED_SCOPE", "S_SEED_A", "rescued", apex_rt="10.02"),
            _cell_row("FAM_SEED_SCOPE", "S_SEED_B", "rescued", apex_rt="10.03"),
        ],
        seed_audit_rows=[
            _seed_row(
                "FAM_SEED_SCOPE",
                "S_SEED_A",
                seed_rt="10.0000",
                rt_start="9.0000",
                rt_end="11.0000",
            ),
            _seed_row(
                "FAM_SEED_SCOPE",
                "S_SEED_B",
                seed_rt="10.2000",
                rt_start="9.2000",
                rt_end="11.2000",
            ),
        ],
        overlay_rows=[
            {
                "feature_family_id": "FAM_SEED_SCOPE",
                "family_verdict": "review_required_neighboring_ms1_interference",
                "png_path": "plots/fam-seed-scope.png",
                "trace_data_json": str(trace_json),
            },
        ],
    )

    by_seed = {group.seed_rt: group for group in result.groups}
    seed_a_notes = " ".join(by_seed["10.0000"].overlay_evidence_notes)
    seed_b_notes = " ".join(by_seed["10.2000"].overlay_evidence_notes)

    assert "S_SEED_A" in seed_a_notes
    assert "S_SEED_B" not in seed_a_notes
    assert "S_SEED_B" in seed_b_notes
    assert "S_SEED_A" not in seed_b_notes


def test_seed_specific_overlay_rows_do_not_broadcast_across_seed_groups() -> None:
    family = "FAM_SEED_JOIN"
    seed_b_id = (
        "seed::FAM_SEED_JOIN::mz=269.145::rt=10.5000::"
        "window=9.5000-11.5000::ppm=10"
    )
    result = gallery.build_reconciliation_index(
        review_rows=[_review_row(family, detected="1", rescued="2")],
        cell_rows=[
            _cell_row(family, "S1", "detected"),
            _cell_row(family, "S2", "rescued"),
            _cell_row(family, "S3", "rescued"),
        ],
        seed_audit_rows=[
            _seed_row(family, "S2"),
            _seed_row(
                family,
                "S3",
                seed_rt="10.5000",
                rt_start="9.5000",
                rt_end="11.5000",
            ),
        ],
        overlay_rows=[
            {
                "feature_family_id": family,
                "seed_group_id": "",
                "family_verdict": "ms1_shape_supports_family_backfill",
                "png_path": "plots/fam-legacy.png",
                "absolute_own_max_shape_supported_fraction": "0.9",
            },
            {
                "feature_family_id": family,
                "seed_group_id": seed_b_id,
                "family_verdict": "review_required_neighboring_ms1_interference",
                "png_path": "plots/fam-seed-b.png",
                "absolute_own_max_shape_supported_fraction": "0.1",
            },
        ],
    )

    by_seed = {group.seed_group_id: group for group in result.groups}
    seed_a = next(group for seed, group in by_seed.items() if seed != seed_b_id)
    seed_b = by_seed[seed_b_id]

    assert seed_a.evidence_authority_state == "review_only_visual_support"
    assert seed_a.top_support_component == "ms1_shape_supports_family_backfill"
    assert seed_a.top_blocker == ""
    assert seed_a.overlay_png_path == "plots/fam-legacy.png"
    assert seed_a.overlay_evidence_notes == ("own-max shape support=0.9",)

    assert seed_b.evidence_authority_state == "human_visual_judgment_only"
    assert seed_b.top_support_component == "seed_request_provenance"
    assert seed_b.top_blocker == "review_required_neighboring_ms1_interference"
    assert seed_b.overlay_png_path == "plots/fam-seed-b.png"
    assert seed_b.overlay_evidence_notes == ("own-max shape support=0.1",)


def test_writer_schema_values_and_order_are_stable(tmp_path: Path) -> None:
    assert gallery.GROUP_TSV_COLUMNS == EXPECTED_GROUP_COLUMNS
    assert (
        gallery.REPRESENTATIVE_CELL_TSV_COLUMNS
        == EXPECTED_REPRESENTATIVE_CELL_COLUMNS
    )
    assert gallery.EVIDENCE_AUTHORITY_STATES == EXPECTED_AUTHORITY_STATES
    assert gallery.RECONCILIATION_CLASSES == EXPECTED_RECONCILIATION_CLASSES
    assert (
        gallery.RECONCILIATION_CLASS_PRIORITY
        == EXPECTED_RECONCILIATION_CLASS_PRIORITY
    )

    index = gallery.ReconciliationIndex(
        groups=tuple(
            _group(f"FAM{i:02d}", reconciliation_class, authority_state)
            for i, (reconciliation_class, authority_state) in enumerate(
                zip(
                    EXPECTED_RECONCILIATION_CLASSES,
                    (
                        "product_grade_support",
                        "review_only_visual_support",
                        "product_grade_support",
                        "review_only_visual_support",
                        "evidence_blocks_backfill",
                        "evidence_blocks_backfill",
                        "evidence_inconclusive",
                        "not_assessable",
                        "not_assessable",
                        "not_assessable",
                    ),
                    strict=True,
                ),
                start=1,
            )
        ),
        representative_cells=(
            gallery.RepresentativeCell(
                feature_family_id="FAM03",
                seed_group_id="seed::FAM03::mz=3::rt=3::window=2-4::ppm=10",
                representative_roles=("seed_representative",),
                sample_stem="S1",
                cell_status="rescued",
                product_cell_state="context_only",
                scan_support_score="0.75",
                representative_reason="seed/request representative",
                source_row_key="FAM03::S1",
            ),
        ),
    )

    paths = gallery.write_reconciliation_outputs(tmp_path, index)

    group_rows = _read_tsv(paths["groups_tsv"])
    representative_rows = _read_tsv(paths["representative_cells_tsv"])
    assert _read_header(paths["groups_tsv"]) == list(EXPECTED_GROUP_COLUMNS)
    assert _read_header(paths["representative_cells_tsv"]) == list(
        EXPECTED_REPRESENTATIVE_CELL_COLUMNS,
    )
    assert "backfill_score" not in _read_header(paths["groups_tsv"])
    assert {row["schema_version"] for row in group_rows} == {
        "backfill_evidence_reconciliation_v0",
    }
    assert {row["schema_version"] for row in representative_rows} == {
        "backfill_evidence_reconciliation_v0",
    }
    assert [row["reconciliation_class"] for row in group_rows] == list(
        EXPECTED_RECONCILIATION_CLASS_PRIORITY,
    )
    assert [row["priority_rank"] for row in group_rows] == [
        str(index + 1) for index in range(len(EXPECTED_RECONCILIATION_CLASSES))
    ]
    join_gap_row = next(
        row
        for row in group_rows
        if row["reconciliation_class"] == "not_assessable_join_gap"
    )
    assert (
        join_gap_row["missing_evidence"]
        == "join_gap_seed_audit_sample_not_in_cells"
    )
    assert (
        join_gap_row["source_warnings"]
        == "join_gap_seed_audit_sample_not_in_cells"
    )

    summary = json.loads(paths["summary_json"].read_text(encoding="utf-8"))
    assert summary["schema_version"] == "backfill_evidence_reconciliation_v0"
    assert summary["validation_label"] == "diagnostic_only"
    assert summary["matrix_contract_changed"] is False
    assert summary["product_behavior_changed"] is False
    assert summary["reconciliation_class_counts"]["not_assessable_join_gap"] == 1
    assert summary["missing_evidence_counts"][
        "join_gap_seed_audit_sample_not_in_cells"
    ] == 1


def test_html_gallery_is_table_first_accessible_and_safe(tmp_path: Path) -> None:
    html_path = tmp_path / "out" / "backfill_evidence_reconciliation_gallery.html"
    png_path = tmp_path / "evidence" / "plots" / "fam.png"
    png_path.parent.mkdir(parents=True)
    png_path.write_bytes(b"\x89PNG\r\n\x1a\n")
    review_tsv = tmp_path / "alignment" / "alignment_review.tsv"
    review_tsv.parent.mkdir(parents=True)
    review_tsv.write_text("feature_family_id\nFAM001\n", encoding="utf-8")
    malicious_family = 'FAM<script>alert("x")</script>'
    malicious_seed = (
        f"seed::{malicious_family}::mz=3::rt=3::window=2-4::ppm=10"
    )
    index = gallery.ReconciliationIndex(
        groups=(
            _group(
                malicious_family,
                "product_rejects_but_visual_supports",
                "review_only_visual_support",
                overlay_png_path=str(png_path),
                source_artifacts=("alignment_review.tsv", "alignment_cells.tsv"),
            ),
        ),
        representative_cells=(
            gallery.RepresentativeCell(
                feature_family_id=malicious_family,
                seed_group_id=malicious_seed,
                representative_roles=("seed_representative",),
                sample_stem='S1"><script>alert("sample")</script>',
                cell_status="rescued",
                representative_reason="escaped representative",
                source_row_key='FAM::S1"><script>',
            ),
        ),
        summary={
            "input_artifacts": {
                "alignment_review_tsv": str(review_tsv),
                "source_run_id": 'fixture"><script>alert("run")</script>',
            },
        },
    )

    gallery.write_reconciliation_gallery_html(
        html_path,
        index,
        output_paths={
            "groups_tsv": tmp_path / "backfill_evidence_reconciliation_groups.tsv",
            "representative_cells_tsv": tmp_path
            / "backfill_evidence_reconciliation_representative_cells.tsv",
            "summary_json": tmp_path / "backfill_evidence_reconciliation_summary.json",
        },
    )

    text = html_path.read_text(encoding="utf-8")
    png_href = os.path.relpath(png_path, html_path.parent).replace("\\", "/")
    review_href = os.path.relpath(review_tsv, html_path.parent).replace("\\", "/")
    assert '<html lang="zh-Hant">' in text
    assert "diagnostic_only" in text
    assert (
        "不會修改 alignment matrix、cells、review TSV、workbooks 或 product decisions"
        in text
    )
    assert "position: sticky" in text
    assert "max-width: 1120px" in text
    assert "width: 1114px" in text
    assert "margin: 0 auto" in text
    assert ".cell-family," in text
    assert ".cell-product," in text
    assert '<th scope="col">rank</th>' in text
    assert '<th scope="col">priority</th>' not in text
    assert "white-space: nowrap" in text
    assert "<details" in text
    assert '<caption id="galleryTableDescription">' in text
    assert '<th class="cell-family" scope="row" data-label="family / seed">' in text
    assert 'data-label="top issue"' in text
    assert "cells D/R/P" in text
    assert (
        'aria-label="cells: D detected, R rescued or backfilled, P provisional"'
        in text
    )
    assert 'data-label="cells D/R/P"' in text
    assert '<th scope="col">chain</th>' in text
    assert 'data-label="chain"' in text
    assert 'data-detail-toggle=' in text
    assert 'aria-expanded="false"' in text
    assert '<tr class="detail-row"' in text
    assert '<td colspan="8">' in text
    assert "cells D/R/P 是 cell counts" in text
    assert '<label for="categoryFilter">Focus</label>' in text
    assert '<option value="">All rows</option>' in text
    assert '<option value="needs_review">Needs review</option>' in text
    assert '<option value="accepted_supported">Accepted + supported</option>' in text
    assert '<option value="product_rejects_but_visual_supports">' not in text
    assert 'data-category="needs_review"' in text
    assert "const focusFilter = document.querySelector('[data-filter-control]')" in text
    assert "row.dataset.category" in text
    assert 'class="artifact-strip"' in text
    assert '<details class="provenance-panel">' in text
    assert 'class="summary-item artifact input-artifacts"' not in text
    assert 'class="family-details single-seed"' in text
    assert 'class="seed-table"' not in text
    assert 'class="seed-subdetails"' not in text
    assert "seed / request" not in text
    assert '<span class="seed-summary">1 seed · m/z 3 · RT 3</span>' in text
    assert '<span class="seed-window">window 2-4</span>' in text
    assert "m/z 3 · RT 3 · window 2-4" not in text
    assert "Gaussian15 own-max MS1 shape" in text
    assert "Candidate MS2 / NL or product-grade support" in text
    assert "representative cells" in text
    assert 'aria-modal="true"' in text
    assert 'aria-describedby="lightboxCaption"' in text
    assert 'class="lightbox-direct"' in text
    assert "direct.href = link.href || link.dataset.lightboxSrc" in text
    assert "'.review-table > tbody > tr[data-family-row]'" in text
    assert "setDetailOpen(button, false)" in text
    assert f'data-lightbox-src="{png_href}"' in text
    assert f'href="{png_href}"' in text
    assert f'href="{review_href}"' in text
    assert str(review_tsv) in text
    assert "&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt;" in text
    assert "<script>alert" not in text
    assert 'S1&quot;&gt;&lt;script&gt;alert(&quot;sample&quot;)&lt;/script&gt;' in text


def test_html_gallery_groups_seed_aliases_under_one_family_row(tmp_path: Path) -> None:
    html_path = tmp_path / "backfill_evidence_reconciliation_gallery.html"
    index = gallery.ReconciliationIndex(
        groups=(
            gallery.ReconciliationGroup(
                feature_family_id="FAM_DUP",
                seed_group_id="seed::FAM_DUP::mz=254.097::rt=13.3525::window=10-16::ppm=20",
                seed_group_basis="seed_audit",
                seed_mz="254.097",
                seed_rt="13.3525",
                seed_rt_window="10-16",
                seed_ppm="20",
                product_behavior_state="product_primary_backfilled",
                evidence_authority_state="human_visual_judgment_only",
                reconciliation_class="evidence_inconclusive",
                detected_cell_count=2,
                rescued_cell_count=6,
                top_blocker="review_required_neighboring_ms1_interference",
                overlay_png_path="plots/fam-dup-a.png",
            ),
            gallery.ReconciliationGroup(
                feature_family_id="FAM_DUP",
                seed_group_id="seed::FAM_DUP::mz=254.098::rt=13.1836::window=10-16::ppm=20",
                seed_group_basis="seed_audit",
                seed_mz="254.098",
                seed_rt="13.1836",
                seed_rt_window="10-16",
                seed_ppm="20",
                product_behavior_state="product_primary_backfilled",
                evidence_authority_state="human_visual_judgment_only",
                reconciliation_class="evidence_inconclusive",
                detected_cell_count=2,
                rescued_cell_count=6,
                top_blocker="review_required_neighboring_ms1_interference",
                overlay_png_path="plots/fam-dup-b.png",
            ),
        ),
        representative_cells=(),
    )

    gallery.write_reconciliation_gallery_html(
        html_path,
        index,
        output_paths={},
    )

    text = html_path.read_text(encoding="utf-8")
    assert text.count('data-family="FAM_DUP"') == 1
    assert "2 seed groups" in text
    assert (
        "2 seeds · m/z 254.097-254.098 · RT 13.1836-13.3525"
        in text
    )
    assert '<span class="seed-window">window 10-16</span>' in text
    assert "2 seeds · 0 reps" in text
    assert 'class="seed-table"' in text
    assert 'class="seed-subdetails"' in text
    assert ">seed 1</span>" in text
    assert ">seed 2</span>" in text
    assert "seed / request" in text
    assert "seed::FAM_DUP::mz=254.097" in text
    assert "seed::FAM_DUP::mz=254.098" in text


def test_html_gallery_rejects_dangerous_png_schemes(tmp_path: Path) -> None:
    html_path = tmp_path / "backfill_evidence_reconciliation_gallery.html"
    index = gallery.ReconciliationIndex(
        groups=(
            _group(
                "FAM_JS",
                "product_rejects_but_visual_supports",
                "review_only_visual_support",
                overlay_png_path="javascript:alert(1)",
            ),
            _group(
                "FAM_CONTROL",
                "product_rejects_but_visual_supports",
                "review_only_visual_support",
                overlay_png_path="java\nscript:alert(2)",
            ),
            _group(
                "FAM_DATA",
                "product_rejects_but_visual_supports",
                "review_only_visual_support",
                overlay_png_path="data:text/html,<script>alert(3)</script>",
            ),
        ),
        representative_cells=(),
    )

    gallery.write_reconciliation_gallery_html(
        html_path,
        index,
        output_paths={},
    )

    text = html_path.read_text(encoding="utf-8")
    assert 'data-lightbox-src="' not in text
    assert 'href="javascript:' not in text.lower()
    assert "java\nscript:alert" not in text
    assert "data:text/html" not in text
    assert text.count("no overlay") >= 3


def test_cli_writes_outputs_without_raw_or_dll_contract(tmp_path: Path, capsys) -> None:
    alignment_dir = tmp_path / "alignment"
    alignment_dir.mkdir()
    _write_tsv(
        alignment_dir / "alignment_review.tsv",
        [_review_row("FAM_CLI")],
        ALIGNMENT_REVIEW_COLUMNS,
    )
    _write_tsv(
        alignment_dir / "alignment_cells.tsv",
        [_cell_row("FAM_CLI", "S1", "rescued")],
        ALIGNMENT_CELLS_COLUMNS,
    )
    _write_tsv(
        alignment_dir / "alignment_owner_backfill_seed_audit.tsv",
        [_seed_row("FAM_CLI", "S1")],
        ALIGNMENT_OWNER_BACKFILL_SEED_AUDIT_COLUMNS,
    )
    _write_tsv(
        alignment_dir / "alignment_production_candidate_gate.tsv",
        [
            {
                "feature_family_id": "FAM_CLI",
                "candidate_gate_status": "production_candidate",
                "support_components": "validated_tier2_trace_evidence",
                "challenge_blockers": "",
            },
        ],
        (
            "feature_family_id",
            "candidate_gate_status",
            "support_components",
            "challenge_blockers",
        ),
    )
    _write_tsv(
        alignment_dir / "alignment_matrix.tsv",
        [{"Mz": "269.145", "RT": "10.0", "S1": "1200"}],
        ("Mz", "RT", "S1"),
    )
    output_dir = tmp_path / "out"

    code = cli.main(
        [
            "--alignment-review-tsv",
            str(alignment_dir / "alignment_review.tsv"),
            "--alignment-cells-tsv",
            str(alignment_dir / "alignment_cells.tsv"),
            "--backfill-seed-audit-tsv",
            str(alignment_dir / "alignment_owner_backfill_seed_audit.tsv"),
            "--candidate-gate-tsv",
            str(alignment_dir / "alignment_production_candidate_gate.tsv"),
            "--alignment-matrix-tsv",
            str(alignment_dir / "alignment_matrix.tsv"),
            "--output-dir",
            str(output_dir),
            "--source-run-id",
            "fixture-run",
        ],
    )

    assert code == 0
    assert (output_dir / "backfill_evidence_reconciliation_groups.tsv").is_file()
    assert (
        output_dir / "backfill_evidence_reconciliation_representative_cells.tsv"
    ).is_file()
    assert (output_dir / "backfill_evidence_reconciliation_summary.json").is_file()
    assert (output_dir / "backfill_evidence_reconciliation_gallery.html").is_file()
    assert "backfill evidence reconciliation groups TSV" in capsys.readouterr().out

    with pytest.raises(SystemExit):
        cli._parse_args(["--raw-dir", "RAW", "--dll-dir", "DLL"])
    with pytest.raises(SystemExit) as help_exit:
        cli._parse_args(["--help"])
    assert help_exit.value.code == 0
    help_text = capsys.readouterr().out
    assert "--raw-dir" not in help_text
    assert "--dll-dir" not in help_text


def test_cli_reports_missing_required_inputs(tmp_path: Path, capsys) -> None:
    code = cli.main(
        [
            "--alignment-review-tsv",
            str(tmp_path / "missing_review.tsv"),
            "--alignment-cells-tsv",
            str(tmp_path / "missing_cells.tsv"),
            "--output-dir",
            str(tmp_path / "out"),
        ],
    )

    assert code == 2
    assert "Required TSV not found" in capsys.readouterr().err


def _blank_row(columns: tuple[str, ...]) -> dict[str, str]:
    return {column: "" for column in columns}


def _review_row(
    family: str,
    *,
    identity_decision: str = "provisional_discovery",
    include_in_primary_matrix: str = "FALSE",
    row_flags: str = "single_detected_seed;provisional_retention_candidate",
    detected: str = "1",
    rescued: str = "2",
) -> dict[str, str]:
    row = _blank_row(ALIGNMENT_REVIEW_COLUMNS)
    row.update(
        {
            "feature_family_id": family,
            "group_hypothesis_id": f"{family}::group",
            "public_family_id": family,
            "group_construction_role": "single_detected_seed",
            "group_delivery_role": "review",
            "group_membership_source": "owner_family",
            "family_center_mz": "269.145",
            "family_center_rt": "10.0000",
            "detected_count": detected,
            "accepted_cell_count": str(int(detected) + int(rescued)),
            "accepted_rescue_count": rescued,
            "quantifiable_detected_count": detected,
            "quantifiable_rescue_count": rescued,
            "review_rescue_count": "0",
            "identity_decision": identity_decision,
            "identity_confidence": "review_only",
            "primary_evidence": "owner_backfill_context",
            "identity_reason": "owner_backfill_context",
            "include_in_primary_matrix": include_in_primary_matrix,
            "row_flags": row_flags,
            "reason": "fixture",
        },
    )
    return row


def _cell_row(
    family: str,
    sample: str,
    status: str,
    *,
    scan_support: str = "0.80",
    apex_rt: str = "10.10",
    gap_fill_state: str | None = None,
    gap_fill_reason: str | None = None,
) -> dict[str, str]:
    row = _blank_row(ALIGNMENT_CELLS_COLUMNS)
    resolved_gap_state = (
        gap_fill_state
        if gap_fill_state is not None
        else ("owner_backfill" if status == "rescued" else "observed")
    )
    resolved_gap_reason = (
        gap_fill_reason
        if gap_fill_reason is not None
        else ("owner_backfill" if status == "rescued" else "")
    )
    apex = float(apex_rt) if apex_rt else 10.10
    row.update(
        {
            "feature_family_id": family,
            "group_hypothesis_id": f"{family}::group",
            "public_family_id": family,
            "group_construction_role": "single_detected_seed",
            "group_delivery_role": "review",
            "group_membership_source": "owner_family",
            "gap_fill_state": resolved_gap_state,
            "gap_fill_reason": resolved_gap_reason,
            "sample_stem": sample,
            "status": status,
            "area": "1200.0",
            "primary_matrix_area": "1200.0" if status == "detected" else "",
            "primary_matrix_area_source": "detected" if status == "detected" else "",
            "primary_matrix_area_reason": "observed" if status == "detected" else "",
            "apex_rt": apex_rt,
            "peak_start_rt": f"{apex - 0.08:.4f}",
            "peak_end_rt": f"{apex + 0.08:.4f}",
            "rt_delta_sec": "0",
            "scan_support_score": scan_support,
            "reason": "fixture",
        },
    )
    return row


def _seed_row(
    family: str,
    sample: str,
    *,
    seed_mz: str = "269.145",
    seed_rt: str = "10.0000",
    rt_start: str = "9.0000",
    rt_end: str = "11.0000",
    ppm: str = "10",
) -> dict[str, str]:
    row = _blank_row(ALIGNMENT_OWNER_BACKFILL_SEED_AUDIT_COLUMNS)
    row.update(
        {
            "feature_family_id": family,
            "group_hypothesis_id": f"{family}::group",
            "public_family_id": family,
            "group_construction_role": "single_detected_seed",
            "group_delivery_role": "review",
            "group_membership_source": "owner_family",
            "gap_fill_state": "owner_backfill",
            "gap_fill_reason": "owner_backfill",
            "sample_stem": sample,
            "status": "rescued",
            "area": "1200.0",
            "apex_rt": seed_rt,
            "family_center_mz": "269.145",
            "family_center_rt": "10.0000",
            "backfill_seed_mz": seed_mz,
            "backfill_seed_rt": seed_rt,
            "backfill_request_rt_min": rt_start,
            "backfill_request_rt_max": rt_end,
            "backfill_request_ppm": ppm,
            "reason": "fixture",
        },
    )
    return row


def _overlay_trace(
    sample: str,
    status: str,
    apex_rt: float,
    intensity: list[float],
) -> dict[str, object]:
    return {
        "sample_stem": sample,
        "status": status,
        "cell_apex_rt": apex_rt,
        "cell_start_rt": apex_rt - 0.08,
        "cell_end_rt": apex_rt + 0.08,
        "cell_height": max(intensity),
        "local_window_max_intensity": max(intensity),
        "trace_max_intensity": max(intensity),
        "apex_aligned_shape_similarity": 0.0,
        "local_window_to_global_max_ratio": 1.0,
        "local_window_apex_delta_min": 0.0,
        "global_trace_apex_delta_min": 0.0,
        "rt": [apex_rt - 0.2, apex_rt - 0.1, apex_rt, apex_rt + 0.1, apex_rt + 0.2],
        "intensity": intensity,
    }


def _group(
    family: str,
    reconciliation_class: str,
    authority_state: str,
    *,
    overlay_png_path: str = "",
    source_artifacts: tuple[str, ...] = (),
) -> gallery.ReconciliationGroup:
    missing = (
        ("join_gap_seed_audit_sample_not_in_cells",)
        if reconciliation_class == "not_assessable_join_gap"
        else ()
    )
    return gallery.ReconciliationGroup(
        feature_family_id=family,
        seed_group_id=f"seed::{family}::mz=3::rt=3::window=2-4::ppm=10",
        seed_group_basis="seed_audit",
        seed_mz="3",
        seed_rt="3",
        seed_rt_window="2-4",
        seed_ppm="10",
        tag_or_class="class",
        product_behavior_state=(
            "product_primary_backfilled"
            if reconciliation_class.startswith("product_accepts")
            else "product_rescued_context_only"
        ),
        evidence_authority_state=authority_state,
        reconciliation_class=reconciliation_class,
        detected_cell_count=1,
        rescued_cell_count=2,
        provisional_cell_count=0,
        top_product_reason="fixture",
        top_support_component=(
            "validated_tier2_trace_evidence"
            if authority_state == "product_grade_support"
            else ""
        ),
        top_blocker=(
            "neighbor_interference_review"
            if authority_state == "evidence_blocks_backfill"
            else ""
        ),
        missing_evidence=missing,
        overlay_png_path=overlay_png_path,
        source_artifacts=source_artifacts,
        source_warnings=missing,
    )


def _write_tsv(
    path: Path,
    rows: list[dict[str, str]],
    fieldnames: tuple[str, ...],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def _read_header(path: Path) -> list[str]:
    with path.open(encoding="utf-8", newline="") as handle:
        return next(csv.reader(handle, delimiter="\t"))
