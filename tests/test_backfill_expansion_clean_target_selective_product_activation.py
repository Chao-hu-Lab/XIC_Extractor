from __future__ import annotations

import json
import shutil
from pathlib import Path

from scripts import (
    build_backfill_expansion_clean_target_selective_product_activation as checker,
)
from xic_extractor.tabular_io import read_tsv_required, write_tsv

validate_contract = (
    checker.validate_backfill_expansion_clean_target_selective_product_activation
)


def test_current_clean_target_selective_activation_candidate_is_stable() -> None:
    assert validate_contract() == []

    summary = json.loads(checker.DEFAULT_SUMMARY_JSON.read_text(encoding="utf-8"))

    assert summary["validation_status"] == "production_ready"
    assert summary["activation_label"] == "product_ready_default_matrix_activated"
    assert summary["product_authority_scope"] == (
        "backfill_expansion_clean_target_selective_activation_84_cells"
    )
    assert summary["default_activation_effect"] == (
        "write_backfill_expansion_clean_target_selective_default_cell"
    )
    assert summary["projected_pass_cell_count"] == 84
    assert summary["projected_held_cell_count"] == 28
    assert summary["candidate_peak_count"] == 7
    assert summary["expected_diff_count"] == "84"
    assert summary["written_backfill_count"] == "84"
    assert summary["unused_expected_diff_count"] == "0"
    assert summary["cell_provenance_accepted_count"] == 84
    assert summary["matrix_changed_cell_count"] == 84
    assert summary["boundary_review_excluded_cell_count"] == 37
    assert summary["off_target_hold_or_remap_excluded_cell_count"] == 29
    assert summary["projected_held_primary_blocker_counts"] == {
        "selective_own_max_metric_below_threshold": 21,
        "selective_source_family_shift_attention_only": 2,
        "selective_source_family_shift_not_same_hypothesis": 5,
    }
    assert summary["write_authority"] is True
    assert summary["product_writer_changed"] is True
    assert summary["default_quant_matrix_changed"] is True
    assert summary["default_matrix_files_written"] is True
    assert summary["workbook_or_gui_changed"] is False
    assert summary["selected_peak_area_or_counting_changed"] is False
    assert summary["candidate_rows_are_matrix_rows"] is False
    assert "84 clean-target cells" in summary["authority_statement"]


def test_missing_required_check_fails_closed(tmp_path: Path) -> None:
    summary_json, checks_tsv, compact_manifest_tsv = _copy_contract(tmp_path)
    rows = [
        row
        for row in read_tsv_required(checks_tsv, checker.CHECK_COLUMNS)
        if row["check_id"] != "written_backfill_count"
    ]
    write_tsv(checks_tsv, rows, checker.CHECK_COLUMNS, extrasaction="raise")

    problems = validate_contract(
        summary_json=summary_json,
        checks_tsv=checks_tsv,
        compact_manifest_tsv=compact_manifest_tsv,
    )

    assert any("checks missing required ids" in problem for problem in problems)


def test_summary_product_surface_underclaim_fails_closed(tmp_path: Path) -> None:
    summary_json, checks_tsv, compact_manifest_tsv = _copy_contract(tmp_path)
    payload = json.loads(summary_json.read_text(encoding="utf-8"))
    payload["write_authority"] = False
    payload["product_writer_changed"] = False
    payload["default_quant_matrix_changed"] = False
    payload["default_matrix_files_written"] = False
    payload["selected_peak_area_or_counting_changed"] = True
    summary_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    problems = validate_contract(
        summary_json=summary_json,
        checks_tsv=checks_tsv,
        compact_manifest_tsv=compact_manifest_tsv,
    )

    assert any("summary write_authority mismatch" in problem for problem in problems)
    assert any(
        "summary product_writer_changed mismatch" in problem for problem in problems
    )
    assert any(
        "summary default_quant_matrix_changed mismatch" in problem
        for problem in problems
    )
    assert any(
        "summary default_matrix_files_written mismatch" in problem
        for problem in problems
    )
    assert any(
        "summary selected_peak_area_or_counting_changed mismatch" in problem
        for problem in problems
    )


def test_compact_manifest_scope_drift_fails_closed(tmp_path: Path) -> None:
    summary_json, checks_tsv, compact_manifest_tsv = _copy_contract(tmp_path)
    rows = read_tsv_required(compact_manifest_tsv, checker.COMPACT_MANIFEST_COLUMNS)
    rows[0]["product_authority_scope"] = ""
    write_tsv(
        compact_manifest_tsv,
        rows,
        checker.COMPACT_MANIFEST_COLUMNS,
        extrasaction="raise",
    )

    problems = validate_contract(
        summary_json=summary_json,
        checks_tsv=checks_tsv,
        compact_manifest_tsv=compact_manifest_tsv,
    )

    assert any("compact manifest authority scope mismatch" in p for p in problems)


def _copy_contract(tmp_path: Path) -> tuple[Path, Path, Path]:
    summary_json = tmp_path / "summary.json"
    checks_tsv = tmp_path / "checks.tsv"
    compact_manifest_tsv = tmp_path / "compact_manifest.tsv"
    shutil.copyfile(checker.DEFAULT_SUMMARY_JSON, summary_json)
    shutil.copyfile(checker.DEFAULT_CHECKS_TSV, checks_tsv)
    shutil.copyfile(checker.DEFAULT_MANIFEST_TSV, compact_manifest_tsv)
    return summary_json, checks_tsv, compact_manifest_tsv
