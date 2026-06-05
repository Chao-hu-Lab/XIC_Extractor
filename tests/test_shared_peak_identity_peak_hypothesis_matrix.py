from __future__ import annotations

import csv
import json
from pathlib import Path

from tools.diagnostics.build_peak_hypothesis_matrix import main
from xic_extractor.alignment.shared_peak_identity_explanation import (
    peak_hypothesis_matrix,
)


def test_peak_hypothesis_matrix_splits_family_before_output() -> None:
    construction = peak_hypothesis_matrix.construct_peak_hypothesis_matrix(
        matrix_header=(
            "feature_family_id",
            "neutral_loss_tag",
            "family_center_mz",
            "family_center_rt",
            "S1",
            "S2",
            "S3",
        ),
        matrix_rows=[
            _matrix_row("FAM_SPLIT", mz="400.4", rt="10.4", S1="111", S2="222"),
            _matrix_row("FAM_PROJECT", mz="500.5", rt="11.5", S1="50"),
            _matrix_row("FAM_BLOCK", mz="600.6", rt="12.6", S1="80"),
        ],
        review_rows=[
            _review_row("FAM_SPLIT", mz="400.4", rt="10.4"),
            _review_row("FAM_PROJECT", mz="500.5", rt="11.5"),
            _review_row("FAM_BLOCK", mz="600.6", rt="12.6"),
        ],
        cell_rows=[
            _cell_row("FAM_SPLIT", "S1", area="111"),
            _cell_row("FAM_SPLIT", "S2", area="222"),
            _cell_row("FAM_SPLIT", "S3", area="333"),
            _cell_row("FAM_PROJECT", "S1", area="50"),
            _cell_row("FAM_BLOCK", "S1", area="80", status="rescued"),
        ],
        peak_hypothesis_selection_rows=[
            _peak_row("FAM_SPLIT", "S1", "blue"),
            _peak_row("FAM_SPLIT", "S2", "green"),
            _peak_row("FAM_SPLIT", "S3", "red"),
            _peak_row(
                "FAM_BLOCK",
                "S1",
                "wrong",
                status="cross_mode_rescue_blocked",
                scope="sample_cell",
                action="block_cross_mode_rescue",
                blocker="cross_mode_rescue",
            ),
        ],
        hypothesis_consistency_rows=[
            _consistency_row("FAM_SPLIT", "S1", "blue", status="consistent"),
            _consistency_row("FAM_SPLIT", "S2", "green", status="consistent"),
            _consistency_row("FAM_SPLIT", "S3", "red", status="consistent"),
            _consistency_row(
                "FAM_BLOCK",
                "S1",
                "wrong",
                status="split_required",
                split_readiness="cross_mode_rescue_blocked",
                blockers="cross_mode_rescue",
            ),
        ],
    )

    matrix_rows = {
        row["peak_hypothesis_id"]: row for row in construction.matrix_rows
    }
    assert matrix_rows["FAM_SPLIT::blue"]["S1"] == "111"
    assert matrix_rows["FAM_SPLIT::blue"]["S2"] == ""
    assert matrix_rows["FAM_SPLIT::green"]["S1"] == ""
    assert matrix_rows["FAM_SPLIT::green"]["S2"] == "222"
    assert "FAM_PROJECT::family_projection" not in matrix_rows
    assert "FAM_BLOCK::wrong" not in matrix_rows

    assignments = {
        (row["feature_family_id"], row["sample_id"]): row
        for row in construction.assignment_rows
    }
    assert assignments[("FAM_SPLIT", "S1")]["construction_assignment_status"] == (
        "assigned"
    )
    assert assignments[("FAM_SPLIT", "S3")]["construction_assignment_status"] == (
        "recorded_no_source_matrix_value"
    )
    assert assignments[("FAM_SPLIT", "S3")]["source_cell_area"] == "333"
    assert assignments[("FAM_BLOCK", "S1")]["construction_assignment_status"] == (
        "blocked"
    )
    assert assignments[("FAM_BLOCK", "S1")]["matrix_value_effect"] == "blanked"

    inventory = {
        row["peak_hypothesis_id"]: row for row in construction.inventory_rows
    }
    assert inventory["FAM_SPLIT::blue"]["assigned_cell_count"] == "1"
    assert inventory["FAM_BLOCK::wrong"]["blocked_cell_count"] == "1"
    assert inventory["FAM_PROJECT::family_projection"]["projected_family_count"] == "1"

    summary = construction.summary_row
    assert summary["matrix_row_identity"] == "peak_hypothesis_id"
    assert summary["assigned_cell_count"] == "2"
    assert summary["projected_cell_count"] == "1"
    assert summary["blocked_cell_count"] == "1"
    assert summary["missing_source_matrix_value_count"] == "1"
    assert summary["construction_gate_status"] == "blocked"


def test_peak_hypothesis_matrix_rejects_multi_family_hypothesis_collapse() -> None:
    try:
        peak_hypothesis_matrix.construct_peak_hypothesis_matrix(
            matrix_header=(
                "feature_family_id",
                "family_center_mz",
                "family_center_rt",
                "S1",
            ),
            matrix_rows=[
                _matrix_row("FAM_A", mz="100", rt="5", S1="10"),
                _matrix_row("FAM_B", mz="100", rt="5", S1="30"),
            ],
            review_rows=[
                _review_row("FAM_A", mz="100", rt="5"),
                _review_row("FAM_B", mz="100", rt="5"),
            ],
            cell_rows=[
                _cell_row("FAM_A", "S1", area="10"),
                _cell_row("FAM_B", "S1", area="30"),
            ],
            peak_hypothesis_selection_rows=[
                _peak_row("FAM_A", "S1", "shared"),
                _peak_row("FAM_B", "S1", "shared", peak_id="FAM_A::shared"),
            ],
        )
    except ValueError as exc:
        assert "requires exactly one source_feature_family_id" in str(exc)
    else:
        raise AssertionError("expected multi-family PeakHypothesis collapse guard")


def test_peak_hypothesis_matrix_expands_overlay_modes_before_output(
    tmp_path: Path,
) -> None:
    overlay_json = tmp_path / "fam_multi_overlay_trace_data.json"
    overlay_json.write_text(
        json.dumps(
            {
                "family_id": "FAM_MULTI",
                "mode_windows": {
                    "mode_6min": [5.8, 6.2],
                    "mode_8min": [7.8, 8.2],
                },
                "samples": [
                    {
                        "sample_stem": "S1",
                        "rt": [5.8, 6.0, 6.2, 7.8, 8.0, 8.2],
                        "intensity": [0, 10, 0, 0, 20, 0],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    expanded_rows = peak_hypothesis_matrix.load_overlay_peak_candidate_rows(
        (overlay_json,)
    )

    construction = peak_hypothesis_matrix.construct_peak_hypothesis_matrix(
        matrix_header=(
            "feature_family_id",
            "neutral_loss_tag",
            "family_center_mz",
            "family_center_rt",
            "S1",
        ),
        matrix_rows=[
            _matrix_row("FAM_MULTI", mz="345.1", rt="7.1", S1="999"),
        ],
        review_rows=[_review_row("FAM_MULTI", mz="345.1", rt="7.1")],
        cell_rows=[_cell_row("FAM_MULTI", "S1", area="999")],
        peak_hypothesis_selection_rows=[],
        expanded_peak_candidate_rows=expanded_rows,
    )

    matrix_rows = {
        row["peak_hypothesis_id"]: row for row in construction.matrix_rows
    }
    assert set(matrix_rows) == {
        "FAM_MULTI::mode_6min",
        "FAM_MULTI::mode_8min",
    }
    assert matrix_rows["FAM_MULTI::mode_6min"]["S1"] == "2"
    assert matrix_rows["FAM_MULTI::mode_8min"]["S1"] == "4"
    assignments = {
        row["peak_hypothesis_id"]: row for row in construction.assignment_rows
    }
    assert assignments["FAM_MULTI::mode_6min"][
        "construction_assignment_status"
    ] == "expanded_candidate"
    assert assignments["FAM_MULTI::mode_8min"]["candidate_peak_rt"] == "8"
    assert construction.summary_row["expanded_candidate_cell_count"] == "2"
    assert construction.summary_row["projected_cell_count"] == "0"
    assert construction.summary_row["canonical_row_identity_ready"] == "FALSE"
    assert construction.summary_row["canonical_row_identity_blockers"] == (
        "raw_mode_review_only"
    )
    assert construction.summary_row["construction_gate_status"] == "diagnostic_only"


def test_peak_hypothesis_matrix_infers_overlay_mode_windows_from_apex_clusters(
    tmp_path: Path,
) -> None:
    overlay_json = tmp_path / "fam_multi_inferred_overlay_trace_data.json"
    trace_rt = [5.8, 6.0, 6.2, 7.8, 8.0, 8.2]
    trace_intensity = [0, 10, 0, 0, 20, 0]
    overlay_json.write_text(
        json.dumps(
            {
                "feature_family_id": "FAM_MULTI",
                "evidence_summary": {
                    "family_verdict": "ms1_shape_supports_family_backfill",
                },
                "rt_min": 5.5,
                "rt_max": 8.5,
                "samples": [
                    {
                        "sample_stem": "S1",
                        "cell_apex_rt": 6.0,
                        "raw_rt": trace_rt,
                        "intensity": trace_intensity,
                    },
                    {
                        "sample_stem": "S2",
                        "cell_apex_rt": 6.1,
                        "raw_rt": trace_rt,
                        "intensity": trace_intensity,
                    },
                    {
                        "sample_stem": "S3",
                        "cell_apex_rt": 8.0,
                        "raw_rt": trace_rt,
                        "intensity": trace_intensity,
                    },
                    {
                        "sample_stem": "S4",
                        "cell_apex_rt": 8.1,
                        "raw_rt": trace_rt,
                        "intensity": trace_intensity,
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    expanded_rows = peak_hypothesis_matrix.load_overlay_peak_candidate_rows(
        (overlay_json,)
    )

    sample_1_rows = {
        row["peak_hypothesis_id"]: row
        for row in expanded_rows
        if row["sample_id"] == "S1"
    }
    assert set(sample_1_rows) == {
        "FAM_MULTI::raw_mode_1_6.10min",
        "FAM_MULTI::raw_mode_2_8.10min",
    }
    assert sample_1_rows["FAM_MULTI::raw_mode_1_6.10min"]["candidate_peak_rt"] == "6"
    assert sample_1_rows["FAM_MULTI::raw_mode_2_8.10min"]["candidate_peak_rt"] == "8"
    assert sample_1_rows["FAM_MULTI::raw_mode_1_6.10min"][
        "peak_hypothesis_status"
    ] == "raw_mode_review_only"
    assert sample_1_rows["FAM_MULTI::raw_mode_1_6.10min"][
        "product_selection_blocker"
    ] == "raw_mode_review_only"
    assert sample_1_rows["FAM_MULTI::raw_mode_1_6.10min"]["reason"] == (
        "raw_apex_gap_inferred_mode_window_review_only"
    )


def test_peak_hypothesis_matrix_demotes_overlay_mode_window_product_status(
    tmp_path: Path,
) -> None:
    overlay_json = tmp_path / "fam_typed_overlay_trace_data.json"
    overlay_json.write_text(
        json.dumps(
            {
                "family_id": "FAM_TYPED",
                "mode_windows": {
                    "irt_blue_core": {
                        "start_rt": 7.8,
                        "end_rt": 8.2,
                        "peak_hypothesis_status": "product_candidate_core",
                        "product_selection_action": "select_mode_peak_hypothesis",
                        "product_selection_blocker": "none",
                        "evidence_consistency_status": "consistent",
                        "split_readiness_status": "peak_hypothesis_ready",
                        "consistency_blockers": "",
                        "candidate_value_basis": (
                            "explicit_mode_hypothesis_raw_overlay_area"
                        ),
                        "reason": "typed_irt_mode_hypothesis_window",
                    }
                },
                "samples": [
                    {
                        "sample_stem": "S1",
                        "rt": [7.8, 8.0, 8.2],
                        "intensity": [0, 20, 0],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    expanded_rows = peak_hypothesis_matrix.load_overlay_peak_candidate_rows(
        (overlay_json,)
    )

    assert len(expanded_rows) == 1
    row = expanded_rows[0]
    assert row["peak_hypothesis_id"] == "FAM_TYPED::irt_blue_core"
    assert row["peak_hypothesis_status"] == "raw_mode_review_only"
    assert row["product_selection_action"] == "require_raw_mode_review"
    assert row["product_selection_blocker"] == "raw_mode_review_only"
    assert row["evidence_consistency_status"] == "review_only"
    assert row["split_readiness_status"] == "review_required"
    assert row["consistency_blockers"] == (
        "raw_overlay_mode_window_not_product_authority"
    )
    assert row["reason"] == (
        "typed_irt_mode_hypothesis_window_review_only_product_status_ignored"
    )


def test_peak_hypothesis_selection_takes_precedence_over_overlay_candidates() -> None:
    construction = peak_hypothesis_matrix.construct_peak_hypothesis_matrix(
        matrix_header=(
            "feature_family_id",
            "neutral_loss_tag",
            "family_center_mz",
            "family_center_rt",
            "S1",
        ),
        matrix_rows=[
            _matrix_row("FAM_PRIORITY", mz="345.1", rt="7.1", S1="999"),
        ],
        review_rows=[_review_row("FAM_PRIORITY", mz="345.1", rt="7.1")],
        cell_rows=[_cell_row("FAM_PRIORITY", "S1", area="999")],
        peak_hypothesis_selection_rows=[
            _peak_row("FAM_PRIORITY", "S1", "irt_blue_core"),
        ],
        expanded_peak_candidate_rows=[
            {
                "feature_family_id": "FAM_PRIORITY",
                "sample_id": "S1",
                "peak_hypothesis_id": "FAM_PRIORITY::raw_mode_1_6.10min",
                "mode_id": "raw_mode_1_6.10min",
                "candidate_peak_start_rt": "5.8",
                "candidate_peak_end_rt": "6.2",
                "candidate_peak_rt": "6.0",
                "candidate_peak_height": "10",
                "candidate_area": "2",
                "candidate_value_source": "unit_test_overlay.json",
            },
        ],
    )

    matrix_rows = {
        row["peak_hypothesis_id"]: row for row in construction.matrix_rows
    }
    assert matrix_rows["FAM_PRIORITY::irt_blue_core"]["S1"] == "999"
    assert matrix_rows["FAM_PRIORITY::raw_mode_1_6.10min"]["S1"] == "2"

    assignments = {
        (row["peak_hypothesis_id"], row["construction_assignment_status"])
        for row in construction.assignment_rows
    }
    assert ("FAM_PRIORITY::irt_blue_core", "assigned") in assignments
    assert ("FAM_PRIORITY::raw_mode_1_6.10min", "expanded_candidate") in assignments
    assert construction.summary_row["canonical_row_identity_ready"] == "FALSE"
    assert construction.summary_row["canonical_row_identity_blockers"] == (
        "raw_mode_review_only"
    )


def test_peak_hypothesis_matrix_does_not_infer_modes_from_review_required_overlay(
    tmp_path: Path,
) -> None:
    overlay_json = tmp_path / "fam_interference_overlay_trace_data.json"
    overlay_json.write_text(
        json.dumps(
            {
                "family_id": "FAM_INTERFERENCE",
                "evidence_summary": {
                    "family_verdict": "review_required_neighboring_ms1_interference",
                },
                "traces": [
                    {
                        "sample_stem": "S1",
                        "cell_apex_rt": 6.0,
                        "rt": [5.8, 6.0, 6.2],
                        "intensity": [0, 10, 0],
                    },
                    {
                        "sample_stem": "S2",
                        "cell_apex_rt": 6.1,
                        "rt": [5.8, 6.0, 6.2],
                        "intensity": [0, 10, 0],
                    },
                    {
                        "sample_stem": "S3",
                        "cell_apex_rt": 8.0,
                        "rt": [7.8, 8.0, 8.2],
                        "intensity": [0, 20, 0],
                    },
                    {
                        "sample_stem": "S4",
                        "cell_apex_rt": 8.1,
                        "rt": [7.8, 8.0, 8.2],
                        "intensity": [0, 20, 0],
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    expanded_rows = peak_hypothesis_matrix.load_overlay_peak_candidate_rows(
        (overlay_json,)
    )

    assert expanded_rows == ()


def test_peak_hypothesis_matrix_cli_writes_sidecars(tmp_path: Path) -> None:
    matrix = tmp_path / "alignment_matrix.tsv"
    review = tmp_path / "alignment_review.tsv"
    cells = tmp_path / "alignment_cells.tsv"
    peak_selection = tmp_path / "shared_peak_identity_peak_hypothesis_selection.tsv"
    _write_tsv(
        matrix,
        (
            "feature_family_id",
            "neutral_loss_tag",
            "family_center_mz",
            "family_center_rt",
            "S1",
        ),
        [_matrix_row("FAM_SPLIT", mz="400.4", rt="10.4", S1="111")],
    )
    _write_tsv(
        review,
        (
            "feature_family_id",
            "neutral_loss_tag",
            "family_center_mz",
            "family_center_rt",
        ),
        [_review_row("FAM_SPLIT", mz="400.4", rt="10.4")],
    )
    _write_tsv(
        cells,
        ("feature_family_id", "sample_stem", "status", "area"),
        [_cell_row("FAM_SPLIT", "S1", area="111")],
    )
    _write_tsv(
        peak_selection,
        (
            "feature_family_id",
            "sample_stem",
            "peak_hypothesis_id",
            "peak_hypothesis_status",
            "product_unit_scope",
            "selected_mode_id",
            "selected_mode_role",
            "selected_mode_tag_status",
            "family_mode_class",
            "family_mode_count",
            "tag_bearing_mode_count",
            "product_selection_action",
            "product_selection_blocker",
            "reason",
            "diagnostic_only",
        ),
        [_peak_row("FAM_SPLIT", "S1", "blue")],
    )

    assert (
        main(
            [
                "--alignment-matrix-tsv",
                str(matrix),
                "--alignment-review-tsv",
                str(review),
                "--alignment-cells-tsv",
                str(cells),
                "--peak-hypothesis-selection-tsv",
                str(peak_selection),
                "--output-dir",
                str(tmp_path / "out"),
            ]
        )
        == 0
    )
    assert (tmp_path / "out" / "alignment_matrix.tsv").exists()
    assert (tmp_path / "out" / "peak_hypothesis_inventory.tsv").exists()
    assert (tmp_path / "out" / "peak_hypothesis_cell_assignments.tsv").exists()
    assert (tmp_path / "out" / "peak_hypothesis_matrix_summary.tsv").exists()


def test_peak_hypothesis_matrix_cli_can_require_complete_identity(
    tmp_path: Path,
) -> None:
    matrix = tmp_path / "alignment_matrix.tsv"
    review = tmp_path / "alignment_review.tsv"
    cells = tmp_path / "alignment_cells.tsv"
    peak_selection = tmp_path / "shared_peak_identity_peak_hypothesis_selection.tsv"
    _write_tsv(
        matrix,
        (
            "feature_family_id",
            "neutral_loss_tag",
            "family_center_mz",
            "family_center_rt",
            "S1",
        ),
        [_matrix_row("FAM_SPLIT", mz="400.4", rt="10.4", S1="111")],
    )
    _write_tsv(
        review,
        (
            "feature_family_id",
            "neutral_loss_tag",
            "family_center_mz",
            "family_center_rt",
        ),
        [_review_row("FAM_SPLIT", mz="400.4", rt="10.4")],
    )
    _write_tsv(
        cells,
        ("feature_family_id", "sample_stem", "status", "area"),
        [_cell_row("FAM_SPLIT", "S1", area="111")],
    )
    _write_tsv(
        peak_selection,
        _PEAK_SELECTION_FIELDS,
        [_peak_row("FAM_SPLIT", "S1", "blue")],
    )

    assert (
        main(
            [
                "--alignment-matrix-tsv",
                str(matrix),
                "--alignment-review-tsv",
                str(review),
                "--alignment-cells-tsv",
                str(cells),
                "--peak-hypothesis-selection-tsv",
                str(peak_selection),
                "--output-dir",
                str(tmp_path / "out"),
                "--require-complete-peak-hypothesis-identity",
            ]
        )
        == 0
    )


def test_peak_hypothesis_matrix_cli_rejects_family_projection_as_complete(
    tmp_path: Path,
) -> None:
    matrix = tmp_path / "alignment_matrix.tsv"
    review = tmp_path / "alignment_review.tsv"
    cells = tmp_path / "alignment_cells.tsv"
    peak_selection = tmp_path / "shared_peak_identity_peak_hypothesis_selection.tsv"
    _write_tsv(
        matrix,
        (
            "feature_family_id",
            "neutral_loss_tag",
            "family_center_mz",
            "family_center_rt",
            "S1",
        ),
        [_matrix_row("FAM_PROJECT", mz="500.5", rt="11.5", S1="50")],
    )
    _write_tsv(
        review,
        (
            "feature_family_id",
            "neutral_loss_tag",
            "family_center_mz",
            "family_center_rt",
        ),
        [_review_row("FAM_PROJECT", mz="500.5", rt="11.5")],
    )
    _write_tsv(
        cells,
        ("feature_family_id", "sample_stem", "status", "area"),
        [_cell_row("FAM_PROJECT", "S1", area="50")],
    )
    _write_tsv(peak_selection, _PEAK_SELECTION_FIELDS, [])

    assert (
        main(
            [
                "--alignment-matrix-tsv",
                str(matrix),
                "--alignment-review-tsv",
                str(review),
                "--alignment-cells-tsv",
                str(cells),
                "--peak-hypothesis-selection-tsv",
                str(peak_selection),
                "--output-dir",
                str(tmp_path / "out"),
                "--require-complete-peak-hypothesis-identity",
            ]
        )
        == 2
    )


_PEAK_SELECTION_FIELDS = (
    "feature_family_id",
    "sample_stem",
    "peak_hypothesis_id",
    "peak_hypothesis_status",
    "product_unit_scope",
    "selected_mode_id",
    "selected_mode_role",
    "selected_mode_tag_status",
    "family_mode_class",
    "family_mode_count",
    "tag_bearing_mode_count",
    "product_selection_action",
    "product_selection_blocker",
    "reason",
    "diagnostic_only",
)


def _matrix_row(
    family_id: str,
    *,
    mz: str,
    rt: str,
    **samples: str,
) -> dict[str, str]:
    row = {
        "feature_family_id": family_id,
        "neutral_loss_tag": "DNA_dR",
        "family_center_mz": mz,
        "family_center_rt": rt,
    }
    row.update(samples)
    return row


def _review_row(family_id: str, *, mz: str, rt: str) -> dict[str, str]:
    return {
        "feature_family_id": family_id,
        "neutral_loss_tag": "DNA_dR",
        "family_center_mz": mz,
        "family_center_rt": rt,
    }


def _cell_row(
    family_id: str,
    sample: str,
    *,
    area: str,
    status: str = "detected",
) -> dict[str, str]:
    return {
        "feature_family_id": family_id,
        "sample_stem": sample,
        "status": status,
        "area": area,
    }


def _peak_row(
    family_id: str,
    sample: str,
    mode: str,
    *,
    peak_id: str | None = None,
    status: str = "product_candidate_core",
    scope: str = "mode_level",
    action: str = "select_mode_peak_hypothesis",
    blocker: str = "none",
) -> dict[str, str]:
    return {
        "feature_family_id": family_id,
        "sample_stem": sample,
        "peak_hypothesis_id": peak_id or f"{family_id}::{mode}",
        "peak_hypothesis_status": status,
        "product_unit_scope": scope,
        "selected_mode_id": mode,
        "selected_mode_role": "tag_bearing_core",
        "selected_mode_tag_status": "tag_supported",
        "family_mode_class": "rt_mode_pure",
        "family_mode_count": "2",
        "tag_bearing_mode_count": "1",
        "product_selection_action": action,
        "product_selection_blocker": blocker,
        "reason": "unit_test_peak_hypothesis_selection",
        "diagnostic_only": "TRUE",
    }


def _consistency_row(
    family_id: str,
    sample: str,
    mode: str,
    *,
    status: str,
    split_readiness: str = "peak_hypothesis_ready",
    blockers: str = "",
) -> dict[str, str]:
    return {
        "feature_family_id": family_id,
        "sample_stem": sample,
        "peak_hypothesis_id": f"{family_id}::{mode}",
        "peak_hypothesis_status": "product_candidate_core",
        "product_unit_scope": "mode_level",
        "product_selection_action": "select_mode_peak_hypothesis",
        "product_selection_blocker": "none",
        "evidence_consistency_status": status,
        "split_readiness_status": split_readiness,
        "consistency_blockers": blockers,
        "diagnostic_only": "TRUE",
    }


def _write_tsv(
    path: Path,
    fieldnames: tuple[str, ...],
    rows: list[dict[str, str]],
) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
            delimiter="\t",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)
