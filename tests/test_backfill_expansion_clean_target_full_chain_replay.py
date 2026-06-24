from __future__ import annotations

import json
import shutil
from pathlib import Path

from scripts import check_backfill_expansion_clean_target_full_chain_replay as checker


def test_current_clean_target_full_chain_replay_is_held() -> None:
    assert checker.validate_backfill_expansion_clean_target_full_chain_replay() == []

    summary = json.loads(checker.DEFAULT_SUMMARY_JSON.read_text(encoding="utf-8"))

    assert (
        summary["validation_status"]
        == "diagnostic_clean_target_selective_projection_held"
    )
    assert summary["clean_target_candidate_cell_count"] == 112
    assert summary["boundary_review_excluded_cell_count"] == 37
    assert summary["off_target_hold_or_remap_excluded_cell_count"] == 29
    assert summary["missing_or_unclassified_excluded_cell_count"] == 0
    assert summary["row_manifest_group_count"] == 18
    assert summary["full_chain_complete"] is False
    assert summary["full_chain_pass_cell_count"] == 51
    assert summary["held_cell_count"] == 61
    assert summary["primary_blocker_counts"] == {
        "own_max_metric_below_threshold": 12,
        "own_max_metric_missing": 2,
        "shift_aware_gate_blocked_shift_aware_same_pattern_not_supported": 47,
    }
    assert summary["selective_evidence_pass_cell_count"] == 84
    assert summary["selective_evidence_held_cell_count"] == 28
    assert summary["old_shift_aware_blocker_cell_count"] == 47
    assert summary["old_shift_aware_blocker_selective_pass_cell_count"] == 33
    assert summary["old_shift_aware_blocker_selective_held_cell_count"] == 14
    assert summary["projected_selective_full_chain_pass_cell_count"] == 84
    assert summary["projected_selective_held_cell_count"] == 28
    assert summary["projected_selective_primary_blocker_counts"] == {
        "selective_own_max_metric_below_threshold": 21,
        "selective_source_family_shift_attention_only": 2,
        "selective_source_family_shift_not_same_hypothesis": 5,
    }
    assert summary["write_authority"] is False
    assert summary["product_writer_changed"] is False
    assert summary["default_quant_matrix_changed"] is False
    assert summary["raw_or_85raw_ran_by_checker"] is False


def test_clean_target_selector_uses_split_group_target_and_boundary() -> None:
    peak_rows = [
        _peak_mode_row("FAM_A", "TumorA_DNA", "tumor", "target_mode", "not_bridged"),
        _peak_mode_row(
            "FAM_A",
            "TumorB_DNA",
            "tumor",
            "target_mode",
            "bridges_lower_target_boundary",
        ),
        _peak_mode_row(
            "FAM_A",
            "TumorC_DNA",
            "tumor",
            "off_target_early",
            "not_bridged",
        ),
        _peak_mode_row(
            "FAM_A",
            "NormalA_DNA",
            "normal",
            "target_mode",
            "not_bridged",
        ),
    ]
    split_by_group = {
        ("FAM_A", "tumor"): {
            "peak_hypothesis_id": "FAM_A",
            "sample_subtype": "tumor",
        },
    }

    selected = checker._clean_target_peak_mode_rows(  # noqa: SLF001
        peak_rows,
        split_by_group,
    )

    assert [row["sample_stem"] for row in selected] == ["TumorA_DNA"]


def test_summary_authority_flag_fails_closed(tmp_path: Path) -> None:
    summary_json, checks_tsv, manifest_tsv, cells_tsv = _copy_contract(tmp_path)
    payload = json.loads(summary_json.read_text(encoding="utf-8"))
    payload["write_authority"] = True
    summary_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    problems = checker.validate_backfill_expansion_clean_target_full_chain_replay(
        summary_json=summary_json,
        checks_tsv=checks_tsv,
        row_manifest_tsv=manifest_tsv,
        cells_tsv=cells_tsv,
    )

    assert "summary write_authority must be false" in problems


def test_missing_declared_externalized_cells_tsv_is_not_clean_checkout_blocker(
    tmp_path: Path,
) -> None:
    summary_json, checks_tsv, manifest_tsv, _cells_tsv = _copy_contract(tmp_path)
    payload = json.loads(summary_json.read_text(encoding="utf-8"))
    relpath = (
        "output/validation/backfill_expansion_clean_target_full_chain_replay_v1/"
        "__missing_clean_checkout_cells.tsv"
    )
    payload["artifacts"]["cells_tsv"]["path"] = relpath
    summary_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    missing_cells_tsv = checker.ROOT / relpath
    assert not missing_cells_tsv.exists()

    problems = checker.validate_backfill_expansion_clean_target_full_chain_replay(
        summary_json=summary_json,
        checks_tsv=checks_tsv,
        row_manifest_tsv=manifest_tsv,
        cells_tsv=missing_cells_tsv,
    )

    assert problems == []


def test_missing_retained_cells_tsv_fails_closed(tmp_path: Path) -> None:
    summary_json, checks_tsv, manifest_tsv, _cells_tsv = _copy_contract(tmp_path)
    payload = json.loads(summary_json.read_text(encoding="utf-8"))
    relpath = (
        "docs/superpowers/validation/"
        "backfill_expansion_clean_target_full_chain_replay_v1/"
        "__missing_retained_cells.tsv"
    )
    payload["artifacts"]["cells_tsv"]["path"] = relpath
    payload["artifacts"]["cells_tsv"]["retention_decision"] = "externalize"
    summary_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    missing_cells_tsv = checker.ROOT / relpath
    assert not missing_cells_tsv.exists()

    problems = checker.validate_backfill_expansion_clean_target_full_chain_replay(
        summary_json=summary_json,
        checks_tsv=checks_tsv,
        row_manifest_tsv=manifest_tsv,
        cells_tsv=missing_cells_tsv,
    )

    assert f"cells TSV missing: {missing_cells_tsv}" in problems
    assert any("summary artifacts cells_tsv missing" in problem for problem in problems)


def _copy_contract(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    summary_json = tmp_path / "summary.json"
    checks_tsv = tmp_path / "checks.tsv"
    manifest_tsv = tmp_path / "manifest.tsv"
    cells_tsv = tmp_path / "cells.tsv"
    shutil.copyfile(checker.DEFAULT_SUMMARY_JSON, summary_json)
    shutil.copyfile(checker.DEFAULT_CHECKS_TSV, checks_tsv)
    shutil.copyfile(checker.DEFAULT_ROW_MANIFEST_TSV, manifest_tsv)
    return summary_json, checks_tsv, manifest_tsv, cells_tsv


def _peak_mode_row(
    family: str,
    sample: str,
    subtype: str,
    mode_assignment: str,
    boundary_bridge_status: str,
) -> dict[str, str]:
    return {
        "peak_hypothesis_id": family,
        "sample_stem": sample,
        "sample_subtype": subtype,
        "mode_assignment": mode_assignment,
        "boundary_bridge_status": boundary_bridge_status,
    }
