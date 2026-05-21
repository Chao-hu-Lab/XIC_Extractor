from __future__ import annotations

import csv
import json
from pathlib import Path

from tools.diagnostics.rt_ms1_backfill_cross_evidence import main
from xic_extractor.instrument_qc.rt_ms1_backfill_cross_evidence_io import (
    build_rt_ms1_cross_evidence_from_files,
)

RT_COLUMNS = [
    "feature_id",
    "source_cell_key",
    "sample_stem",
    "feature_mz",
    "raw_feature_rt_min",
    "row_classification",
    "supporting_biological_istd_label",
    "review_reason",
]

SEED_COLUMNS = [
    "feature_family_id",
    "family_center_mz",
    "family_center_rt",
    "detected_count",
    "accepted_rescue_count",
    "accepted_cell_count",
    "review_classification",
    "recommended_next_action",
    "review_reason",
    "png_paths",
]

ALIGNMENT_REVIEW_COLUMNS = [
    "feature_family_id",
    "include_in_primary_matrix",
    "identity_decision",
    "accepted_cell_count",
    "detected_count",
    "accepted_rescue_count",
    "review_rescue_count",
]


def test_cross_evidence_requires_rt_and_ms1_support(tmp_path: Path) -> None:
    rt_tsv, seed_tsv = _write_inputs(
        tmp_path,
        rt_rows=[
            _rt_row("FAM001", "rt_supported_shadow_candidate"),
            _rt_row("FAM002", "rt_supported_shadow_candidate"),
        ],
        seed_rows=[
            _seed_row("FAM001", "seed_shape_supported_review_candidate"),
            _seed_row("FAM002", "neighbor_interference_review"),
        ],
    )

    result = build_rt_ms1_cross_evidence_from_files(
        rt_shadow_rows_tsv=rt_tsv,
        seed_aware_families_tsv=seed_tsv,
    )

    rows = {row.feature_family_id: row for row in result.rows}
    assert (
        rows["FAM001"].combined_classification
        == "rt_ms1_supported_review_candidate"
    )
    assert rows["FAM001"].evidence_grade == "A_dual_axis_supported"
    assert rows["FAM001"].final_matrix_status == "final_matrix_context_missing"
    assert rows["FAM001"].blocking_evidence == ""
    assert rows["FAM001"].missing_evidence == ""
    assert (
        rows["FAM002"].combined_classification
        == "rt_supported_ms1_interference_review"
    )
    assert rows["FAM002"].evidence_grade == "C_manual_review_interference"
    assert rows["FAM002"].blocking_evidence == "neighboring_ms1_interference"
    assert rows["FAM002"].recommended_next_action == "manual_review_required"
    assert result.rt_family_count == 2
    assert result.matched_family_count == 2


def test_final_matrix_status_by_evidence_grade(tmp_path: Path) -> None:
    rt_tsv, seed_tsv = _write_inputs(
        tmp_path,
        rt_rows=[
            _rt_row("FAM001", "rt_supported_shadow_candidate"),
            _rt_row("FAM002", "rt_model_uncertain"),
        ],
        seed_rows=[
            _seed_row("FAM001", "seed_shape_supported_review_candidate"),
            _seed_row("FAM002", "seed_shape_supported_review_candidate"),
        ],
    )
    review_tsv = tmp_path / "alignment_review.tsv"
    _write_tsv(
        review_tsv,
        ALIGNMENT_REVIEW_COLUMNS,
        [
            _review_row("FAM001", include=True, detected=4, rescued=78),
            _review_row("FAM002", include=False, detected=3, rescued=0),
        ],
    )

    result = build_rt_ms1_cross_evidence_from_files(
        rt_shadow_rows_tsv=rt_tsv,
        seed_aware_families_tsv=seed_tsv,
        alignment_review_tsv=review_tsv,
    )

    rows = {row.feature_family_id: row for row in result.rows}
    assert rows["FAM001"].final_matrix_status == (
        "in_final_matrix_with_accepted_rescue"
    )
    assert rows["FAM002"].final_matrix_status == "not_in_final_matrix"
    summary = {
        (row.evidence_grade, row.final_matrix_status): row
        for row in result.matrix_status_by_grade
    }
    grade_a = summary[
        ("A_dual_axis_supported", "in_final_matrix_with_accepted_rescue")
    ]
    assert grade_a.family_count == 1
    assert grade_a.accepted_rescue_count == 78
    assert result.counts_by_final_matrix_status == {
        "in_final_matrix_with_accepted_rescue": 1,
        "not_in_final_matrix": 1,
    }


def test_ms1_supported_rt_uncertain_and_missing_context(tmp_path: Path) -> None:
    rt_tsv, seed_tsv = _write_inputs(
        tmp_path,
        rt_rows=[_rt_row("FAM001", "rt_model_uncertain")],
        seed_rows=[
            _seed_row("FAM001", "seed_shape_supported_review_candidate"),
            _seed_row("FAM003", "seed_shape_supported_review_candidate"),
        ],
    )

    result = build_rt_ms1_cross_evidence_from_files(
        rt_shadow_rows_tsv=rt_tsv,
        seed_aware_families_tsv=seed_tsv,
    )

    rows = {row.feature_family_id: row for row in result.rows}
    assert rows["FAM001"].combined_classification == "ms1_supported_rt_uncertain_review"
    assert (
        rows["FAM001"].evidence_grade
        == "B_ms1_shape_supported_rt_unconfirmed"
    )
    assert rows["FAM001"].missing_evidence == "rt_confirmation"
    assert rows["FAM003"].combined_classification == "ms1_supported_rt_context_missing"
    assert (
        rows["FAM003"].evidence_grade
        == "B_ms1_shape_supported_rt_unconfirmed"
    )
    assert rows["FAM003"].missing_evidence == "rt_context"


def test_rt_only_does_not_override_shape_insufficient_ms1(tmp_path: Path) -> None:
    rt_tsv, seed_tsv = _write_inputs(
        tmp_path,
        rt_rows=[_rt_row("FAM001", "rt_supported_shadow_candidate")],
        seed_rows=[_seed_row("FAM001", "shape_insufficient_review")],
    )

    result = build_rt_ms1_cross_evidence_from_files(
        rt_shadow_rows_tsv=rt_tsv,
        seed_aware_families_tsv=seed_tsv,
    )

    row = result.rows[0]
    assert row.combined_classification == "rt_only_review"
    assert row.evidence_grade == "D_single_axis_or_not_ready"
    assert row.blocking_evidence == "ms1_shape_insufficient"
    assert row.missing_evidence == "seed_shape_support"
    assert row.recommended_next_action == "generate_or_review_seed_specific_overlay"


def test_rt_uncertain_neighboring_interference_is_grade_c(tmp_path: Path) -> None:
    rt_tsv, seed_tsv = _write_inputs(
        tmp_path,
        rt_rows=[_rt_row("FAM001", "rt_model_uncertain")],
        seed_rows=[_seed_row("FAM001", "neighbor_interference_review")],
    )

    result = build_rt_ms1_cross_evidence_from_files(
        rt_shadow_rows_tsv=rt_tsv,
        seed_aware_families_tsv=seed_tsv,
    )

    row = result.rows[0]
    assert row.combined_classification == "rt_uncertain_review"
    assert row.evidence_grade == "C_manual_review_interference"
    assert row.blocking_evidence == "neighboring_ms1_interference"
    assert row.missing_evidence == "seed_shape_support;rt_confirmation"
    assert "neighboring interference" in row.review_reason


def test_cli_writes_outputs(tmp_path: Path) -> None:
    rt_tsv, seed_tsv = _write_inputs(
        tmp_path,
        rt_rows=[_rt_row("FAM001", "rt_supported_shadow_candidate")],
        seed_rows=[_seed_row("FAM001", "seed_shape_supported_review_candidate")],
    )
    output_dir = tmp_path / "out"

    exit_code = main(
        [
            "--rt-shadow-rows-tsv",
            str(rt_tsv),
            "--seed-aware-families-tsv",
            str(seed_tsv),
            "--output-dir",
            str(output_dir),
        ]
    )

    assert exit_code == 0
    payload = json.loads(
        (output_dir / "rt_ms1_backfill_cross_evidence.json").read_text(
            encoding="utf-8"
        )
    )
    assert payload["counts_by_classification"] == {
        "rt_ms1_supported_review_candidate": 1
    }
    assert payload["counts_by_evidence_grade"] == {
        "A_dual_axis_supported": 1
    }
    assert (
        output_dir / "rt_ms1_backfill_final_matrix_grade_summary.tsv"
    ).exists()
    assert payload["matched_family_count"] == 1
    markdown = (output_dir / "rt_ms1_backfill_cross_evidence.md").read_text(
        encoding="utf-8"
    )
    assert "rt_ms1_supported_review_candidate" in markdown


def test_missing_required_columns_fail_clearly(tmp_path: Path) -> None:
    rt_tsv = tmp_path / "rt.tsv"
    seed_tsv = tmp_path / "seed.tsv"
    _write_tsv(rt_tsv, ["feature_id"], [{"feature_id": "FAM001"}])
    _write_tsv(seed_tsv, SEED_COLUMNS, [_seed_row("FAM001", "not_assessable")])

    exit_code = main(
        [
            "--rt-shadow-rows-tsv",
            str(rt_tsv),
            "--seed-aware-families-tsv",
            str(seed_tsv),
            "--output-dir",
            str(tmp_path / "out"),
        ]
    )

    assert exit_code == 2


def _write_inputs(
    tmp_path: Path,
    *,
    rt_rows: list[dict[str, str]],
    seed_rows: list[dict[str, str]],
) -> tuple[Path, Path]:
    rt_tsv = tmp_path / "rt_shadow_rows.tsv"
    seed_tsv = tmp_path / "seed_families.tsv"
    _write_tsv(rt_tsv, RT_COLUMNS, rt_rows)
    _write_tsv(seed_tsv, SEED_COLUMNS, seed_rows)
    return rt_tsv, seed_tsv


def _rt_row(family_id: str, classification: str) -> dict[str, str]:
    return {
        "feature_id": family_id,
        "source_cell_key": f"{family_id}|QC1",
        "sample_stem": "QC1",
        "feature_mz": "283.154",
        "raw_feature_rt_min": "10.5",
        "row_classification": classification,
        "supporting_biological_istd_label": "15N5-8-oxodG",
        "review_reason": "fixture",
    }


def _seed_row(family_id: str, classification: str) -> dict[str, str]:
    return {
        "feature_family_id": family_id,
        "family_center_mz": "283.154",
        "family_center_rt": "10.5",
        "detected_count": "5",
        "accepted_rescue_count": "79",
        "accepted_cell_count": "84",
        "review_classification": classification,
        "recommended_next_action": "fixture",
        "review_reason": "fixture",
        "png_paths": "overlay.png",
    }


def _review_row(
    family_id: str,
    *,
    include: bool,
    detected: int,
    rescued: int,
) -> dict[str, str]:
    accepted = detected + rescued
    return {
        "feature_family_id": family_id,
        "include_in_primary_matrix": "TRUE" if include else "FALSE",
        "identity_decision": "production_family" if include else "audit_family",
        "accepted_cell_count": str(accepted if include else 0),
        "detected_count": str(detected),
        "accepted_rescue_count": str(rescued if include else 0),
        "review_rescue_count": "0",
    }


def _write_tsv(
    path: Path,
    fieldnames: list[str],
    rows: list[dict[str, str]],
) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)
