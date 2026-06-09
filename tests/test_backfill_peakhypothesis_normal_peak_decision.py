import csv
import json
from pathlib import Path

from xic_extractor.diagnostics import (
    backfill_peakhypothesis_normal_peak_decision as decision,
)

EXPECTED_NORMAL_PEAK_SHAPE_DEFINITION = (
    "gaussian15_asls_residual_selected_segment_single_complete_unimodal_peak;"
    "raw_spikes_neighbor_contact_family_multiplet_not_blockers"
)


def test_normal_same_peak_non_primary_candidate_requires_backfill(
    tmp_path: Path,
) -> None:
    index = decision.build_normal_peak_decision_index(
        promotion_rows=[
            _promotion_row(
                peak_hypothesis_id="FAM000808",
                sample="TumorBC2263_DNA",
            ),
        ],
        raw85_slice_gate_rows=[
            _raw85_slice_row(
                peak_hypothesis_id="FAM000808",
                sample="TumorBC2263_DNA",
                matched_peak_hypothesis_id="FAM007718",
                include_primary="FALSE",
                consolidation_state="primary_loser",
                blockers=(
                    "raw85_candidate_not_primary_matrix_row;"
                    "raw85_candidate_family_consolidation_review_required"
                ),
            ),
        ],
        manual_verdict_rows=[
            _manual_verdict_row(
                source_peak_hypothesis_id="FAM000808",
                sample="TumorBC2263_DNA",
                matched_peak_hypothesis_id="FAM007718",
            ),
        ],
        source_run_id="unit",
    )

    row = index.rows[0]
    assert row["normal_peak_decision"] == "require_backfill"
    assert row["normal_peak_backfill_required"] is True
    assert row["normal_peak_shape_definition"] == (
        EXPECTED_NORMAL_PEAK_SHAPE_DEFINITION
    )
    assert row["normal_peak_decision_reasons"] == (
        "standard_peak_same_peak_supported;"
        "positive_gaussian15_area;"
        "consolidation_not_blocking_normal_peak"
    )
    assert row["normal_peak_decision_blockers"] == ""
    assert row["consolidation_policy_effect"] == (
        "allow_same_peak_peakhypothesis_candidate_despite_non_primary"
    )
    assert index.summary["normal_peak_candidate_count"] == 1
    assert index.summary["required_backfill_count"] == 1
    assert index.summary["consolidation_override_count"] == 1
    assert index.summary["normal_peak_policy_status"] == (
        "normal_peak_backfill_required_all_reviewed_candidates"
    )
    assert index.summary["normal_peak_shape_definition"] == (
        EXPECTED_NORMAL_PEAK_SHAPE_DEFINITION
    )
    assert index.summary["next_action"] == (
        "wire_normal_peak_decisions_into_activation_or_matrix_writer"
    )

    outputs = decision.write_normal_peak_decision_outputs(tmp_path, index)
    rows = _read_tsv(outputs.decisions_tsv)
    summary = json.loads(outputs.summary_json.read_text(encoding="utf-8"))
    assert rows[0]["normal_peak_decision"] == "require_backfill"
    assert rows[0]["normal_peak_backfill_required"] == "TRUE"
    assert summary["required_backfill_count"] == 1


def test_standard_area_policy_uses_gaussian15_selected_segment() -> None:
    index = decision.build_normal_peak_decision_index(
        promotion_rows=[
            _promotion_row(
                peak_hypothesis_id="FAM_MIXED_CONTEXT",
                sample="Sample_A",
                area_uncertainty_reason=(
                    "gaussian15_selected_segment_single_peak;"
                    "raw_xic_spiky;family_window_contains_multiple_peaks;"
                    "neighbor_peak_contact"
                ),
            ),
        ],
        raw85_slice_gate_rows=[
            _raw85_slice_row(
                peak_hypothesis_id="FAM_MIXED_CONTEXT",
                sample="Sample_A",
                matched_peak_hypothesis_id="HYP_SELECTED_SEGMENT",
                blockers="",
            ),
        ],
        manual_verdict_rows=[
            _manual_verdict_row(
                source_peak_hypothesis_id="FAM_MIXED_CONTEXT",
                sample="Sample_A",
                matched_peak_hypothesis_id="HYP_SELECTED_SEGMENT",
            ),
        ],
    )

    row = index.rows[0]
    assert row["normal_peak_decision"] == "require_backfill"
    assert row["normal_peak_backfill_required"] is True
    assert row["normal_peak_decision_blockers"] == ""
    assert row["normal_peak_decision_reasons"] == (
        "standard_peak_same_peak_supported;"
        "positive_gaussian15_area"
    )


def test_nonstandard_peak_stays_review_only_even_with_same_peak_support() -> None:
    index = decision.build_normal_peak_decision_index(
        promotion_rows=[
            _promotion_row(
                peak_hypothesis_id="FAM_NONSTANDARD",
                sample="Sample_A",
                area_policy="nonstandard_assessable_area",
                matrix_quantitative_use="use_with_uncertainty",
                promotion_decision="blocked",
                promotion_blockers="nonstandard_area_review_only",
            ),
        ],
        raw85_slice_gate_rows=[
            _raw85_slice_row(
                peak_hypothesis_id="FAM_NONSTANDARD",
                sample="Sample_A",
                matched_peak_hypothesis_id="FAM_RAW85",
            ),
        ],
        manual_verdict_rows=[
            _manual_verdict_row(
                source_peak_hypothesis_id="FAM_NONSTANDARD",
                sample="Sample_A",
                matched_peak_hypothesis_id="FAM_RAW85",
            ),
        ],
    )

    row = index.rows[0]
    assert row["normal_peak_decision"] == "review_only_nonstandard_peak"
    assert row["normal_peak_backfill_required"] is False
    assert row["normal_peak_decision_blockers"] == (
        "nonstandard_peak_out_of_goal_scope"
    )
    assert index.summary["review_only_nonstandard_count"] == 1
    assert index.summary["required_backfill_count"] == 0


def test_same_peak_conflict_blocks_normal_peak_backfill() -> None:
    index = decision.build_normal_peak_decision_index(
        promotion_rows=[_promotion_row()],
        raw85_slice_gate_rows=[_raw85_slice_row()],
        manual_verdict_rows=[
            _manual_verdict_row(reviewer_verdict="same_peak_conflict"),
        ],
    )

    row = index.rows[0]
    assert row["normal_peak_decision"] == "blocked"
    assert row["normal_peak_backfill_required"] is False
    assert row["normal_peak_decision_blockers"] == (
        "manual_same_peak_not_supported"
    )
    assert index.summary["blocked_count"] == 1


def test_cli_writes_normal_peak_decision_outputs(tmp_path: Path) -> None:
    promotion_tsv = tmp_path / "promotion.tsv"
    raw85_tsv = tmp_path / "raw85.tsv"
    manual_tsv = tmp_path / "manual.tsv"
    output_dir = tmp_path / "out"
    _write_tsv(promotion_tsv, [_promotion_row()])
    _write_tsv(raw85_tsv, [_raw85_slice_row()])
    _write_tsv(manual_tsv, [_manual_verdict_row()])

    from tools.diagnostics import (
        backfill_peakhypothesis_normal_peak_decision as cli,
    )

    assert cli.main(
        [
            "--promotion-cells-tsv",
            str(promotion_tsv),
            "--raw85-slice-gate-tsv",
            str(raw85_tsv),
            "--raw85-manual-verdict-tsv",
            str(manual_tsv),
            "--output-dir",
            str(output_dir),
            "--source-run-id",
            "unit-cli",
        ],
    ) == 0

    rows = _read_tsv(
        output_dir / "backfill_peakhypothesis_normal_peak_decisions.tsv",
    )
    summary = json.loads(
        (
            output_dir
            / "backfill_peakhypothesis_normal_peak_decision_summary.json"
        ).read_text(encoding="utf-8"),
    )
    assert rows[0]["source_run_id"] == "unit-cli"
    assert rows[0]["normal_peak_decision"] == "require_backfill"
    assert summary["source_run_id"] == "unit-cli"
    assert summary["required_backfill_count"] == 1


def _promotion_row(
    peak_hypothesis_id: str = "FAM001",
    sample: str = "Sample_A",
    *,
    area_policy: str = "standard_assessable_area",
    area_uncertainty_reason: str = "",
    matrix_quantitative_use: str = "standard_quantitative_use",
    promotion_decision: str = "promote_matrix_write",
    promotion_blockers: str = "",
) -> dict[str, str]:
    return {
        "schema_version": "backfill_peakhypothesis_promotion_v1",
        "peak_hypothesis_id": peak_hypothesis_id,
        "activation_unit_scope": "peak_hypothesis",
        "feature_family_id": peak_hypothesis_id,
        "seed_group_id": f"seed::{peak_hypothesis_id}",
        "sample_stem": sample,
        "promotion_decision": promotion_decision,
        "promotion_reasons": "allowlisted_peakhypothesis_same_peak_backfill",
        "promotion_blockers": promotion_blockers,
        "current_raw_status": "rescued",
        "current_matrix_written": "FALSE",
        "projected_matrix_value": "123.4",
        "area_policy": area_policy,
        "area_uncertainty_reason": area_uncertainty_reason,
        "matrix_quantitative_use": matrix_quantitative_use,
        "shadow_projection_row_sha256": "row-sha",
    }


def _raw85_slice_row(
    peak_hypothesis_id: str = "FAM001",
    sample: str = "Sample_A",
    *,
    matched_peak_hypothesis_id: str = "FAM_RAW85",
    include_primary: str = "TRUE",
    consolidation_state: str = "primary_winner",
    blockers: str = "raw85_candidate_family_consolidation_review_required",
) -> dict[str, str]:
    return {
        "schema_version": "backfill_peakhypothesis_raw85_slice_gate_v1",
        "peak_hypothesis_id": peak_hypothesis_id,
        "feature_family_id": peak_hypothesis_id,
        "seed_group_id": f"seed::{peak_hypothesis_id}",
        "sample_stem": sample,
        "raw85_anchor_mz": "301.165",
        "raw85_anchor_rt": "16.0841",
        "raw85_matched_peak_hypothesis_id": matched_peak_hypothesis_id,
        "raw85_cell_status": "rescued",
        "raw85_primary_matrix_area": "298267",
        "raw85_primary_matrix_area_source": "gaussian15_positive_asls_residual",
        "raw85_include_in_primary_matrix": include_primary,
        "raw85_consolidation_state": consolidation_state,
        "raw85_slice_gate_status": "hypothesis_candidate_review",
        "raw85_slice_blockers": blockers,
    }


def _manual_verdict_row(
    source_peak_hypothesis_id: str = "FAM001",
    sample: str = "Sample_A",
    *,
    matched_peak_hypothesis_id: str = "FAM_RAW85",
    reviewer_verdict: str = "same_peak_supported",
) -> dict[str, str]:
    return {
        "schema_version": "backfill_peakhypothesis_raw85_manual_verdict_v1",
        "source_peak_hypothesis_id": source_peak_hypothesis_id,
        "source_feature_family_id": source_peak_hypothesis_id,
        "sample_stem": sample,
        "raw85_matched_peak_hypothesis_id": matched_peak_hypothesis_id,
        "reviewer_verdict": reviewer_verdict,
        "review_basis": "visual_review_raw_plus_gaussian15_overlay_gallery",
        "reviewer": "user",
        "reviewed_at": "2026-06-09",
    }


def _read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def _write_tsv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
