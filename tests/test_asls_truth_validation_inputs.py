from __future__ import annotations

import csv
import datetime as dt
import json
import os
import subprocess
from pathlib import Path

import pytest

from tools.diagnostics.asls_truth_validation_inputs import (
    NOT_APPLICABLE_WITH_EXCLUSION,
    NOT_PROVIDED,
    NOT_SATISFIED,
    PASS,
    VALID,
    build_coverage_rows,
    sha256_file,
    validate_retirement_prerequisites,
    validate_tier_a,
    validate_tier_c,
    validate_waiver,
)
from tools.diagnostics.asls_truth_validation_manifests import load_fixture_manifest
from tools.diagnostics.asls_truth_validation_models import (
    INCONCLUSIVE_FIXTURE_GAP,
    INCONCLUSIVE_INVALID_INPUT,
    INCONCLUSIVE_MISSING_P2B_85RAW_ACCEPTANCE,
    INCONCLUSIVE_REGENERATE_TIER_A,
)


FIXTURE_DIR = Path("docs/superpowers/fixtures")
TIER_A_MANIFEST = FIXTURE_DIR / "asls_truth_tier_a_expected_manifest.json"
FIXTURE_MANIFEST = FIXTURE_DIR / "asls_truth_validation_fixture_manifest.json"
ROWS = Path(
    "output/phase1_p2_baseline_truth_audit_all_statuses/"
    "baseline_truth_audit_rows.tsv"
)
SUMMARY = Path(
    "output/phase1_p2_baseline_truth_audit_all_statuses/"
    "baseline_truth_audit_summary.tsv"
)
JSON_REPORT = Path(
    "output/phase1_p2_baseline_truth_audit_all_statuses/"
    "baseline_truth_audit.json"
)
MARKDOWN_REPORT = Path(
    "output/phase1_p2_baseline_truth_audit_all_statuses/"
    "baseline_truth_audit.md"
)


def test_validate_tier_a_accepts_locked_six_family_artifacts() -> None:
    result = _validate_tier_a()

    assert result.status == PASS
    assert result.family_count == 6
    assert result.row_count == 48
    assert {row.old_p2_status for row in result.expected_families} == {"PASS", "FAIL"}


def test_validate_tier_a_rejects_missing_expected_family(tmp_path: Path) -> None:
    summary_path = _copy_tsv(SUMMARY, tmp_path / "summary.tsv")
    rows = _read_tsv(summary_path)
    _write_tsv(summary_path, rows[:-1])

    result = _validate_tier_a(
        summary_path=summary_path,
        verify_artifact_hashes=False,
    )

    assert result.status == "FAIL"
    assert "missing_expected_family" in result.reasons


def test_validate_tier_a_rejects_wrong_row_count(tmp_path: Path) -> None:
    rows_path = _copy_tsv(ROWS, tmp_path / "rows.tsv")
    rows = _read_tsv(rows_path)
    _write_tsv(rows_path, rows[:-1])

    result = _validate_tier_a(rows_path=rows_path, verify_artifact_hashes=False)

    assert result.status == "FAIL"
    assert "wrong_tier_a_row_count" in result.reasons


def test_validate_tier_a_rejects_missing_old_p2_pass_or_fail(tmp_path: Path) -> None:
    manifest_path = _copy_json(TIER_A_MANIFEST, tmp_path / "tier_a.json")
    data = _load_json(manifest_path)
    for row in data["expected_families"]:
        row["old_p2_status"] = "PASS"
    manifest_path.write_text(json.dumps(data), encoding="utf-8")

    result = _validate_tier_a(manifest_path=manifest_path)

    assert result.status == "FAIL"
    assert "missing_old_p2_status_representation" in result.reasons


def test_validate_tier_a_rejects_asls_area_exceeding_raw(tmp_path: Path) -> None:
    rows_path = _copy_tsv(ROWS, tmp_path / "rows.tsv")
    rows = _read_tsv(rows_path)
    rows[0]["asls_raw_pct"] = "100.01"
    _write_tsv(rows_path, rows)

    result = _validate_tier_a(rows_path=rows_path, verify_artifact_hashes=False)

    assert result.status == "FAIL"
    assert "asls_raw_pct_gt_100" in result.reasons


def test_validate_tier_a_rejects_under_subtraction_dominated_summary(
    tmp_path: Path,
) -> None:
    summary_path = _copy_tsv(SUMMARY, tmp_path / "summary.tsv")
    rows = _read_tsv(summary_path)
    for row in rows:
        row["dominant_classification"] = "asls_under_subtraction_plausible"
    _write_tsv(summary_path, rows)

    result = _validate_tier_a(
        summary_path=summary_path,
        verify_artifact_hashes=False,
    )

    assert result.status == "FAIL"
    assert "asls_under_subtraction_dominant" in result.reasons


def test_validate_tier_a_rejects_missing_required_plot_path(tmp_path: Path) -> None:
    summary_path = _copy_tsv(SUMMARY, tmp_path / "summary.tsv")
    rows = _read_tsv(summary_path)
    rows[0]["plot_path"] = "plots/missing.png"
    _write_tsv(summary_path, rows)

    result = _validate_tier_a(
        summary_path=summary_path,
        verify_artifact_hashes=False,
    )

    assert result.status == "FAIL"
    assert "missing_required_plot_path" in result.reasons


def test_validate_tier_a_rejects_missing_required_column(tmp_path: Path) -> None:
    rows_path = _copy_tsv(ROWS, tmp_path / "rows.tsv")
    rows = _read_tsv(rows_path)
    for row in rows:
        del row["linear_area"]
    _write_tsv(rows_path, rows)

    result = _validate_tier_a(rows_path=rows_path, verify_artifact_hashes=False)

    assert result.status == INCONCLUSIVE_INVALID_INPUT
    assert "missing_required_column" in result.reasons


def test_validate_tier_a_rejects_extra_schema_column(tmp_path: Path) -> None:
    rows_path = _copy_tsv(ROWS, tmp_path / "rows.tsv")
    rows = _read_tsv(rows_path)
    rows[0]["extra_column"] = "drift"
    _write_tsv(rows_path, rows)

    result = _validate_tier_a(rows_path=rows_path, verify_artifact_hashes=False)

    assert result.status == INCONCLUSIVE_INVALID_INPUT
    assert "unexpected_column" in result.reasons


def test_validate_tier_a_rejects_row_overflow_cells(tmp_path: Path) -> None:
    rows_path = _copy_tsv(ROWS, tmp_path / "rows.tsv")
    lines = rows_path.read_text(encoding="utf-8").splitlines()
    lines[1] = f"{lines[1]}\tunexpected"
    rows_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    result = _validate_tier_a(rows_path=rows_path, verify_artifact_hashes=False)

    assert result.status == INCONCLUSIVE_INVALID_INPUT
    assert "unexpected_column" in result.reasons


def test_validate_tier_a_requires_rt_and_boundary_status_columns(tmp_path: Path) -> None:
    rows_path = _copy_tsv(ROWS, tmp_path / "rows.tsv")
    rows = _read_tsv(rows_path)
    for row in rows:
        row.pop("rt_identity_status", None)
        row.pop("boundary_status", None)
    _write_tsv(rows_path, rows)

    result = _validate_tier_a(rows_path=rows_path, verify_artifact_hashes=False)

    assert result.status == INCONCLUSIVE_INVALID_INPUT
    assert "missing_required_column" in result.reasons


def test_validate_tier_a_rejects_invalid_numeric_field(tmp_path: Path) -> None:
    rows_path = _copy_tsv(ROWS, tmp_path / "rows.tsv")
    rows = _read_tsv(rows_path)
    rows[0]["asls_raw_pct"] = "not-a-number"
    _write_tsv(rows_path, rows)

    result = _validate_tier_a(rows_path=rows_path, verify_artifact_hashes=False)

    assert result.status == INCONCLUSIVE_INVALID_INPUT
    assert "invalid_numeric_field" in result.reasons


def test_validate_tier_a_rejects_invalid_summary_numeric_field(tmp_path: Path) -> None:
    summary_path = _copy_tsv(SUMMARY, tmp_path / "summary.tsv")
    rows = _read_tsv(summary_path)
    rows[0]["row_count"] = "not-a-number"
    _write_tsv(summary_path, rows)

    result = _validate_tier_a(
        summary_path=summary_path,
        verify_artifact_hashes=False,
    )

    assert result.status == INCONCLUSIVE_INVALID_INPUT
    assert "invalid_numeric_field" in result.reasons


def test_validate_tier_a_rejects_invalid_summary_metric_numeric_field(
    tmp_path: Path,
) -> None:
    summary_path = _copy_tsv(SUMMARY, tmp_path / "summary.tsv")
    rows = _read_tsv(summary_path)
    rows[0]["median_asls_vs_linear_pct"] = "not-a-number"
    _write_tsv(summary_path, rows)

    result = _validate_tier_a(
        summary_path=summary_path,
        verify_artifact_hashes=False,
    )

    assert result.status == INCONCLUSIVE_INVALID_INPUT
    assert "invalid_numeric_field" in result.reasons


def test_validate_tier_a_rejects_missing_artifact_path() -> None:
    result = _validate_tier_a(rows_path=Path("missing_rows.tsv"))

    assert result.status == INCONCLUSIVE_INVALID_INPUT
    assert "unreadable_tier_a_artifact" in result.reasons


def test_validate_tier_a_rejects_manifest_source_hash_mismatch(
    tmp_path: Path,
) -> None:
    manifest_path = _copy_json(TIER_A_MANIFEST, tmp_path / "tier_a.json")
    data = _load_json(manifest_path)
    data["source_inputs"]["p2_gate_rows_tsv"]["sha256"] = "0" * 64
    manifest_path.write_text(json.dumps(data), encoding="utf-8")

    result = _validate_tier_a(manifest_path=manifest_path)

    assert result.status == INCONCLUSIVE_REGENERATE_TIER_A
    assert "tier_a_manifest_freshness" in result.reasons


def test_validate_tier_a_rejects_wrong_rt_identity_status(tmp_path: Path) -> None:
    rows_path = _copy_tsv(ROWS, tmp_path / "rows.tsv")
    rows = _read_tsv(rows_path)
    rows[0]["rt_identity_status"] = "FAIL"
    _write_tsv(rows_path, rows)

    result = _validate_tier_a(rows_path=rows_path, verify_artifact_hashes=False)

    assert result.status == "FAIL"
    assert "rt_identity_status_fail" in result.reasons


def test_validate_tier_a_rejects_unacceptable_boundary_expansion_status(
    tmp_path: Path,
) -> None:
    rows_path = _copy_tsv(ROWS, tmp_path / "rows.tsv")
    rows = _read_tsv(rows_path)
    rows[0]["boundary_status"] = "expanded_unaccepted"
    _write_tsv(rows_path, rows)

    result = _validate_tier_a(rows_path=rows_path, verify_artifact_hashes=False)

    assert result.status == "FAIL"
    assert "boundary_status_fail" in result.reasons


def test_coverage_gap_returns_fixture_gap(tmp_path: Path) -> None:
    summary_path = _copy_tsv(SUMMARY, tmp_path / "summary.tsv")
    rows = _read_tsv(summary_path)
    rows[0]["dominant_classification"] = "unmapped_pattern"
    _write_tsv(summary_path, rows)
    fixture_manifest = load_fixture_manifest(FIXTURE_MANIFEST)

    coverage = build_coverage_rows(_read_tsv(summary_path), fixture_manifest)

    assert any(row.coverage_status == INCONCLUSIVE_FIXTURE_GAP for row in coverage)


def test_linear_edge_pattern_coverage_includes_baseline_and_boundary_hard_cases() -> None:
    fixture_manifest = load_fixture_manifest(FIXTURE_MANIFEST)

    coverage = build_coverage_rows(
        [
            {
                "target_label": "d3-5-hmdC",
                "feature_family_id": "FAM000153",
                "row_count": "8",
                "dominant_classification": "linear_edge_over_subtraction_plausible",
            }
        ],
        fixture_manifest,
    )

    assert coverage[0].coverage_status == PASS
    assert {
        "sloped_baseline_peak",
        "tailing_peak",
        "adjacent_shoulder",
        "flat_peak_control",
    }.issubset(set(coverage[0].required_b1_fixture_classes))
    assert "hump_baseline_peak" not in coverage[0].required_b1_fixture_classes
    assert "hump_baseline_peak" in coverage[0].b2_stress_fixture_classes


def test_validate_tier_a_hash_mismatch_requests_regeneration(tmp_path: Path) -> None:
    rows_path = _copy_tsv(ROWS, tmp_path / "rows.tsv")
    rows = _read_tsv(rows_path)
    rows[0]["asls_raw_pct"] = "99.99"
    _write_tsv(rows_path, rows)

    result = _validate_tier_a(rows_path=rows_path)

    assert result.status == INCONCLUSIVE_REGENERATE_TIER_A
    assert "artifact_hash_mismatch" in result.reasons


def test_validate_tier_a_git_sha_mismatch_without_compatibility_requests_regeneration(
    tmp_path: Path,
) -> None:
    manifest_path = _copy_json(TIER_A_MANIFEST, tmp_path / "tier_a.json")
    data = _load_json(manifest_path)
    data["generated_by_git_sha"] = "deadbeef"
    data["current_code_compatibility_status"] = "missing"
    manifest_path.write_text(json.dumps(data), encoding="utf-8")

    result = _validate_tier_a(manifest_path=manifest_path)

    assert result.status == INCONCLUSIVE_REGENERATE_TIER_A
    assert "current_code_compatibility" in result.reasons


def test_current_git_sha_matches_worktree_head() -> None:
    from tools.diagnostics.asls_truth_validation_inputs import _current_git_sha

    expected = subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        text=True,
    ).strip()

    assert _current_git_sha() == expected


def test_current_git_sha_fallback_resolves_linked_worktree_head(monkeypatch) -> None:
    from tools.diagnostics import asls_truth_validation_inputs as inputs

    expected = subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        text=True,
    ).strip()

    def fail_check_output(*args, **kwargs):
        raise subprocess.CalledProcessError(1, "git")

    monkeypatch.setattr(inputs.subprocess, "check_output", fail_check_output)

    assert inputs._current_git_sha(TIER_A_MANIFEST) == expected


def test_validate_tier_a_requires_p2b_85raw_refs_for_retirement(tmp_path: Path) -> None:
    manifest_path = _copy_json(TIER_A_MANIFEST, tmp_path / "tier_a.json")
    data = _load_json(manifest_path)
    data["p2b_85raw_acceptance_refs"] = []
    manifest_path.write_text(json.dumps(data), encoding="utf-8")

    result = _validate_tier_a(
        manifest_path=manifest_path,
        require_p2b_85raw_acceptance=True,
    )

    assert result.status == INCONCLUSIVE_MISSING_P2B_85RAW_ACCEPTANCE


def test_validate_tier_c_spike_in_axis_requires_levels_replicates_and_recovery(
    tmp_path: Path,
) -> None:
    path = _write_json(
        tmp_path / "tier_c.json",
        {
            "tier_c_axis": "spike_in_recovery",
            "tier_c_status": "PASS",
            "level_count": 3,
            "replicates_per_level": 5,
            "median_recovery_pct": 105.0,
            **_evidence_metadata(),
        },
    )

    assert validate_tier_c(path).nonblank_status == PASS

    bad = _write_json(
        tmp_path / "bad_tier_c.json",
        {
            "tier_c_axis": "spike_in_recovery",
            "tier_c_status": "PASS",
            "level_count": 2,
            "replicates_per_level": 5,
            "median_recovery_pct": 105.0,
            **_evidence_metadata(),
        },
    )
    assert validate_tier_c(bad).status == INCONCLUSIVE_INVALID_INPUT


def test_validate_tier_c_linearity_axis_requires_fit_quality(tmp_path: Path) -> None:
    path = _write_json(
        tmp_path / "tier_c.json",
        {
            "tier_c_axis": "linearity",
            "tier_c_status": "PASS",
            "level_count": 5,
            "replicates_per_level": 3,
            "slope": 1.5,
            "r2": 0.99,
            **_evidence_metadata(),
        },
    )

    assert validate_tier_c(path).nonblank_status == PASS

    bad = _write_json(
        tmp_path / "bad_tier_c.json",
        {
            "tier_c_axis": "linearity",
            "tier_c_status": "PASS",
            "level_count": 5,
            "replicates_per_level": 3,
            "slope": -1.0,
            "r2": 0.99,
            **_evidence_metadata(),
        },
    )
    assert validate_tier_c(bad).status == INCONCLUSIVE_INVALID_INPUT


def test_validate_tier_c_blank_axis_is_safety_not_nonblank_authority(
    tmp_path: Path,
) -> None:
    path = _write_json(
        tmp_path / "tier_c.json",
        {
            "tier_c_axis": "blank_carryover",
            "tier_c_status": "PASS",
            "blank_control_row_count": 8,
            "blank_below_threshold_pct": 95.0,
            **_evidence_metadata(),
        },
    )

    result = validate_tier_c(path)

    assert result.status == PASS
    assert result.nonblank_status == NOT_PROVIDED
    assert result.blank_safety_status == PASS


def test_validate_tier_c_rejects_no_blank_controls_statement_as_retirement_pass(
    tmp_path: Path,
) -> None:
    path = _write_json(
        tmp_path / "tier_c.json",
        {
            "tier_c_axis": "blank_carryover",
            "tier_c_status": "PASS",
            "accepted_no_controls_statement": True,
            "accepted_residual_risk": "No blank controls exist for this dataset.",
            **_evidence_metadata(),
        },
    )

    result = validate_tier_c(path)

    assert result.status == INCONCLUSIVE_INVALID_INPUT


def test_validate_tier_c_accepts_machine_checkable_blank_exclusion_contract(
    tmp_path: Path,
) -> None:
    path = _write_json(
        tmp_path / "tier_c.json",
        {
            "tier_c_axis": "blank_carryover",
            "tier_c_status": "PASS",
            "blank_exclusion_contract": {
                "affected_outputs": ["alignment_matrix.tsv"],
                "evidence_artifacts": [_hashed_ref(MARKDOWN_REPORT)],
                "approved": True,
            },
            **_evidence_metadata(),
        },
    )

    result = validate_tier_c(path)

    assert result.blank_safety_status == NOT_APPLICABLE_WITH_EXCLUSION


def test_validate_tier_c_blinded_manual_axis_requires_review_depth(
    tmp_path: Path,
) -> None:
    path = _write_json(
        tmp_path / "tier_c.json",
        {
            "tier_c_axis": "blinded_manual_integration",
            "tier_c_status": "PASS",
            "stratified_row_count": 30,
            "median_relative_difference_pct": 8.0,
            "unreviewed_above_25pct_count": 0,
            **_evidence_metadata(),
        },
    )

    assert validate_tier_c(path).nonblank_status == PASS


def test_validate_tier_c_real_85raw_axis_requires_cohort_safety(
    tmp_path: Path,
) -> None:
    path = _write_json(
        tmp_path / "tier_c.json",
        {
            "tier_c_axis": "real_85raw_cohort",
            "tier_c_status": "PASS",
            "raw_file_count": 85,
            "sample_count": 85,
            "selected_istd_count": 6,
            "high_risk_morphology_row_count": 30,
            "blank_control_row_count": 8,
            "covered_target_classes": ["ISTD"],
            "known_exclusions": [],
            "unaccepted_rt_boundary_mismatch_count": 0,
            "asls_raw_area_exceedance_count": 0,
            "quantitative_truth_comparator_type": "manual_integration_review",
            "max_unreviewed_relative_difference_pct": 25.0,
            "median_nonblank_drift_pct": 10.0,
            **_evidence_metadata(),
        },
    )

    assert validate_tier_c(path).nonblank_status == PASS


def test_validate_tier_c_rejects_unsupported_axis(tmp_path: Path) -> None:
    path = _write_json(
        tmp_path / "tier_c.json",
        {"tier_c_axis": "external_tool_vibes", "tier_c_status": "PASS"},
    )

    assert validate_tier_c(path).status == INCONCLUSIVE_INVALID_INPUT


def test_validate_tier_c_rejects_unverifiable_pass_evidence(tmp_path: Path) -> None:
    path = _write_json(
        tmp_path / "tier_c.json",
        {
            "tier_c_axis": "spike_in_recovery",
            "tier_c_status": "PASS",
            "level_count": 3,
            "replicates_per_level": 5,
            "median_recovery_pct": 105.0,
        },
    )

    assert validate_tier_c(path).status == INCONCLUSIVE_INVALID_INPUT


def test_validate_tier_c_rejects_unsupported_axis_even_when_status_fail(
    tmp_path: Path,
) -> None:
    path = _write_json(
        tmp_path / "tier_c.json",
        {"tier_c_axis": "external_tool_vibes", "tier_c_status": "FAIL"},
    )

    assert validate_tier_c(path).status == INCONCLUSIVE_INVALID_INPUT


def test_validate_tier_c_resolves_repo_relative_refs_from_other_cwd(
    tmp_path: Path,
) -> None:
    path = _write_json(
        tmp_path / "tier_c.json",
        {
            "tier_c_axis": "spike_in_recovery",
            "tier_c_status": "PASS",
            "level_count": 3,
            "replicates_per_level": 5,
            "median_recovery_pct": 105.0,
            **_evidence_metadata(),
        },
    )
    original_cwd = Path.cwd()
    try:
        os.chdir(tmp_path)
        result = validate_tier_c(path)
    finally:
        os.chdir(original_cwd)

    assert result.status == PASS


def test_validate_tier_c_does_not_resolve_refs_from_process_cwd(
    tmp_path: Path,
) -> None:
    input_dir = tmp_path / "input"
    cwd_dir = tmp_path / "cwd"
    input_dir.mkdir()
    cwd_dir.mkdir()
    cwd_only = cwd_dir / "cwd_only.md"
    cwd_only.write_text(MARKDOWN_REPORT.read_text(encoding="utf-8"), encoding="utf-8")
    path = _write_json(
        input_dir / "tier_c.json",
        {
            "tier_c_axis": "spike_in_recovery",
            "tier_c_status": "PASS",
            "level_count": 3,
            "replicates_per_level": 5,
            "median_recovery_pct": 105.0,
            "evidence_artifacts": [
                {"path": cwd_only.name, "sha256": sha256_file(cwd_only)}
            ],
            "thresholds_used": ["p2c_task4_test_thresholds"],
            "reviewer_or_generator": "pytest",
            "output_scope": ["alignment_matrix.tsv"],
            "target_classes": ["ISTD"],
            "known_exclusions": [],
        },
    )
    original_cwd = Path.cwd()
    try:
        os.chdir(cwd_dir)
        result = validate_tier_c(path)
    finally:
        os.chdir(original_cwd)

    assert result.status == INCONCLUSIVE_INVALID_INPUT


def test_validate_tier_c_accepts_not_provided_without_pretending_pass(
    tmp_path: Path,
) -> None:
    path = _write_json(
        tmp_path / "tier_c.json",
        {"tier_c_axis": "spike_in_recovery", "tier_c_status": NOT_PROVIDED},
    )

    result = validate_tier_c(path)

    assert result.status == NOT_PROVIDED
    assert result.nonblank_status == NOT_PROVIDED
    assert result.blank_safety_status == NOT_PROVIDED


def test_validate_waiver_requires_owner_scope_and_deletion_statement(
    tmp_path: Path,
) -> None:
    path = _write_json(
        tmp_path / "waiver.json",
        {
            "methodology_owner": "methodology_owner",
            "approved": True,
            "review_date": "2026-05-27",
            "review_artifact_path": str(MARKDOWN_REPORT),
            "review_artifact_sha256": sha256_file(MARKDOWN_REPORT),
            "blank_carryover_disposition": "accepted_residual_risk",
            "accepted_residual_risks": ["Tier C unavailable"],
            "output_scope": ["alignment_matrix.tsv"],
            "expiry_or_revalidation_trigger": "2026-12-31",
            "waived_decision": "c1b-plan",
            "waived_tier_c_axes": ["spike_in_recovery"],
            "waiver_rationale": "No spike-in series exists for this dataset.",
            "branch_scope": "codex/peak-pipeline-modernization",
            "target_classes": ["ISTD"],
            "sample_classes": ["tissue"],
            "supporting_evidence": [
                {"path": str(MARKDOWN_REPORT), "sha256": sha256_file(MARKDOWN_REPORT)}
            ],
            "delete_only_after_c1a_c5_rollback_deprecation": True,
        },
    )

    assert validate_waiver(path).waiver_state == VALID

    bad = _write_json(tmp_path / "bad_waiver.json", {"approved": True})
    assert validate_waiver(bad).status == INCONCLUSIVE_INVALID_INPUT


def test_validate_waiver_rejects_empty_scope_and_bad_expiry(tmp_path: Path) -> None:
    bad = _write_json(
        tmp_path / "bad_waiver.json",
        {
            "methodology_owner": "methodology_owner",
            "approved": True,
            "review_date": "2026-05-27",
            "review_artifact_path": str(MARKDOWN_REPORT),
            "review_artifact_sha256": sha256_file(MARKDOWN_REPORT),
            "blank_carryover_disposition": "accepted_residual_risk",
            "accepted_residual_risks": [],
            "output_scope": [],
            "expiry_or_revalidation_trigger": "not-a-date",
            "waived_decision": "c1b-plan",
            "waived_tier_c_axes": [],
            "waiver_rationale": "",
            "branch_scope": "",
            "target_classes": [],
            "sample_classes": [],
            "supporting_evidence": [],
            "delete_only_after_c1a_c5_rollback_deprecation": True,
        },
    )

    assert validate_waiver(bad).status == INCONCLUSIVE_INVALID_INPUT


def test_validate_waiver_rejects_expired_waiver(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from tools.diagnostics import asls_truth_validation_inputs as inputs

    monkeypatch.setattr(inputs, "_current_date", lambda: dt.date(2026, 5, 27))
    bad = _write_json(
        tmp_path / "bad_waiver.json",
        {
            "methodology_owner": "methodology_owner",
            "approved": True,
            "review_date": "2026-05-25",
            "review_artifact_path": str(MARKDOWN_REPORT),
            "review_artifact_sha256": sha256_file(MARKDOWN_REPORT),
            "blank_carryover_disposition": "accepted_residual_risk",
            "accepted_residual_risks": ["Tier C unavailable"],
            "output_scope": ["alignment_matrix.tsv"],
            "expiry_or_revalidation_trigger": "2026-05-26",
            "waived_decision": "c1b-plan",
            "waived_tier_c_axes": ["spike_in_recovery"],
            "waiver_rationale": "No spike-in series exists for this dataset.",
            "branch_scope": "codex/peak-pipeline-modernization",
            "target_classes": ["ISTD"],
            "sample_classes": ["tissue"],
            "supporting_evidence": [
                {"path": str(MARKDOWN_REPORT), "sha256": sha256_file(MARKDOWN_REPORT)}
            ],
            "delete_only_after_c1a_c5_rollback_deprecation": True,
        },
    )

    assert validate_waiver(bad).status == INCONCLUSIVE_INVALID_INPUT


def test_valid_waiver_does_not_supply_nonblank_tier_c_authority(
    tmp_path: Path,
) -> None:
    waiver = _write_json(
        tmp_path / "waiver.json",
        {
            "methodology_owner": "methodology_owner",
            "approved": True,
            "review_date": "2026-05-27",
            "review_artifact_path": str(MARKDOWN_REPORT),
            "review_artifact_sha256": sha256_file(MARKDOWN_REPORT),
            "blank_carryover_disposition": "accepted_residual_risk",
            "accepted_residual_risks": ["Tier C unavailable"],
            "output_scope": ["alignment_matrix.tsv"],
            "expiry_or_revalidation_trigger": "2026-12-31",
            "waived_decision": "linear-edge-retirement",
            "waived_tier_c_axes": ["spike_in_recovery"],
            "waiver_rationale": "No spike-in series exists for this dataset.",
            "branch_scope": "codex/peak-pipeline-modernization",
            "target_classes": ["ISTD"],
            "sample_classes": ["tissue"],
            "supporting_evidence": [
                {"path": str(MARKDOWN_REPORT), "sha256": sha256_file(MARKDOWN_REPORT)}
            ],
            "delete_only_after_c1a_c5_rollback_deprecation": True,
        },
    )

    result = validate_waiver(waiver)

    assert result.waiver_state == VALID
    assert result.nonblank_tier_c_status == NOT_PROVIDED


def test_validate_retirement_prerequisites_rejects_unsupported_status_enum(
    tmp_path: Path,
) -> None:
    artifact = _write_post_rollback_schema_artifact(tmp_path / "schema.tsv")
    path = _write_json(
        tmp_path / "prereq.json",
        {
            "c1a_status": "MAYBE",
            "c5_status": "LANDED_VALIDATED",
            "rollback_column_status": "DEPRECATED_BY_APPROVED_SCHEMA_NOTE",
            "c1a_validation_note": _hashed_ref(MARKDOWN_REPORT),
            "c5_validation_note": _hashed_ref(MARKDOWN_REPORT),
            "rollback_schema_deprecation_note": _hashed_ref(MARKDOWN_REPORT),
            "post_rollback_audit_schema_artifact": _hashed_ref(artifact),
            "post_rollback_absent_columns": [
                "area_baseline_corrected_linear_edge",
                "baseline_score_linear_edge",
            ],
            "affected_public_contracts_reviewed": ["alignment_cell_integration_audit.tsv"],
            "reviewer_identity": "reviewer",
            "review_date": "2026-05-27",
        },
    )

    assert validate_retirement_prerequisites(path).status == INCONCLUSIVE_INVALID_INPUT


def test_validate_retirement_prerequisites_distinguishes_not_satisfied(
    tmp_path: Path,
) -> None:
    artifact = _write_post_rollback_schema_artifact(tmp_path / "schema.tsv")
    path = _write_json(
        tmp_path / "prereq.json",
        {
            "c1a_status": "PLANNED",
            "c5_status": "LANDED_VALIDATED",
            "rollback_column_status": "DEPRECATED_BY_APPROVED_SCHEMA_NOTE",
            "c1a_validation_note": _hashed_ref(MARKDOWN_REPORT),
            "c5_validation_note": _hashed_ref(MARKDOWN_REPORT),
            "rollback_schema_deprecation_note": _hashed_ref(MARKDOWN_REPORT),
            "post_rollback_audit_schema_artifact": _hashed_ref(artifact),
            "post_rollback_absent_columns": [
                "area_baseline_corrected_linear_edge",
                "baseline_score_linear_edge",
            ],
            "affected_public_contracts_reviewed": ["alignment_cell_integration_audit.tsv"],
            "reviewer_identity": "reviewer",
            "review_date": "2026-05-27",
        },
    )

    result = validate_retirement_prerequisites(path)

    assert result.status == NOT_SATISFIED
    assert not result.satisfied


def test_validate_retirement_prerequisites_requires_hashes_and_schema_artifact(
    tmp_path: Path,
) -> None:
    path = _write_json(
        tmp_path / "prereq.json",
        {
            "c1a_status": "LANDED_VALIDATED",
            "c5_status": "LANDED_VALIDATED",
            "rollback_column_status": "DEPRECATED_BY_APPROVED_SCHEMA_NOTE",
            "c1a_validation_note": {"path": str(MARKDOWN_REPORT), "sha256": "0" * 64},
            "c5_validation_note": _hashed_ref(MARKDOWN_REPORT),
            "rollback_schema_deprecation_note": _hashed_ref(MARKDOWN_REPORT),
            "post_rollback_audit_schema_artifact": _hashed_ref(MARKDOWN_REPORT),
            "post_rollback_absent_columns": [
                "area_baseline_corrected_linear_edge",
                "baseline_score_linear_edge",
            ],
            "affected_public_contracts_reviewed": ["alignment_cell_integration_audit.tsv"],
            "reviewer_identity": "reviewer",
            "review_date": "2026-05-27",
        },
    )

    assert validate_retirement_prerequisites(path).status == INCONCLUSIVE_INVALID_INPUT


def test_validate_retirement_prerequisites_rejects_non_schema_artifact(
    tmp_path: Path,
) -> None:
    path = _write_json(
        tmp_path / "prereq.json",
        {
            "c1a_status": "LANDED_VALIDATED",
            "c5_status": "LANDED_VALIDATED",
            "rollback_column_status": "DEPRECATED_BY_APPROVED_SCHEMA_NOTE",
            "c1a_validation_note": _hashed_ref(MARKDOWN_REPORT),
            "c5_validation_note": _hashed_ref(MARKDOWN_REPORT),
            "rollback_schema_deprecation_note": _hashed_ref(MARKDOWN_REPORT),
            "post_rollback_audit_schema_artifact": _hashed_ref(MARKDOWN_REPORT),
            "post_rollback_absent_columns": [
                "area_baseline_corrected_linear_edge",
                "baseline_score_linear_edge",
            ],
            "affected_public_contracts_reviewed": ["alignment_cell_integration_audit.tsv"],
            "reviewer_identity": "reviewer",
            "review_date": "2026-05-27",
        },
    )

    assert validate_retirement_prerequisites(path).status == INCONCLUSIVE_INVALID_INPUT


def test_validate_retirement_prerequisites_rejects_weak_two_column_schema_artifact(
    tmp_path: Path,
) -> None:
    artifact = _write_tsv_artifact(tmp_path / "schema.tsv", ["sample", "area_asls"])
    path = _write_json(
        tmp_path / "prereq.json",
        {
            "c1a_status": "LANDED_VALIDATED",
            "c5_status": "LANDED_VALIDATED",
            "rollback_column_status": "DEPRECATED_BY_APPROVED_SCHEMA_NOTE",
            "c1a_validation_note": _hashed_ref(MARKDOWN_REPORT),
            "c5_validation_note": _hashed_ref(MARKDOWN_REPORT),
            "rollback_schema_deprecation_note": _hashed_ref(MARKDOWN_REPORT),
            "post_rollback_audit_schema_artifact": _hashed_ref(artifact),
            "post_rollback_absent_columns": [
                "area_baseline_corrected_linear_edge",
                "baseline_score_linear_edge",
            ],
            "affected_public_contracts_reviewed": ["alignment_cell_integration_audit.tsv"],
            "reviewer_identity": "reviewer",
            "review_date": "2026-05-27",
        },
    )

    assert validate_retirement_prerequisites(path).status == INCONCLUSIVE_INVALID_INPUT


def test_validate_retirement_prerequisites_resolves_repo_relative_refs_from_other_cwd(
    tmp_path: Path,
) -> None:
    artifact = _write_post_rollback_schema_artifact(tmp_path / "schema.tsv")
    path = _write_json(
        tmp_path / "prereq.json",
        {
            "c1a_status": "PLANNED",
            "c5_status": "LANDED_VALIDATED",
            "rollback_column_status": "DEPRECATED_BY_APPROVED_SCHEMA_NOTE",
            "c1a_validation_note": _hashed_ref(MARKDOWN_REPORT),
            "c5_validation_note": _hashed_ref(MARKDOWN_REPORT),
            "rollback_schema_deprecation_note": _hashed_ref(MARKDOWN_REPORT),
            "post_rollback_audit_schema_artifact": _hashed_ref(artifact),
            "post_rollback_absent_columns": [
                "area_baseline_corrected_linear_edge",
                "baseline_score_linear_edge",
            ],
            "affected_public_contracts_reviewed": ["alignment_cell_integration_audit.tsv"],
            "reviewer_identity": "reviewer",
            "review_date": "2026-05-27",
        },
    )
    original_cwd = Path.cwd()
    try:
        os.chdir(tmp_path)
        result = validate_retirement_prerequisites(path)
    finally:
        os.chdir(original_cwd)

    assert result.status == NOT_SATISFIED


def test_validate_retirement_prerequisites_requires_absent_linear_edge_columns(
    tmp_path: Path,
) -> None:
    artifact = _write_tsv_artifact(
        tmp_path / "schema.tsv",
        [
            *_POST_ROLLBACK_SCHEMA_COLUMNS,
            "area_baseline_corrected_linear_edge",
        ],
    )
    path = _write_json(
        tmp_path / "prereq.json",
        {
            "c1a_status": "LANDED_VALIDATED",
            "c5_status": "LANDED_VALIDATED",
            "rollback_column_status": "DEPRECATED_BY_APPROVED_SCHEMA_NOTE",
            "c1a_validation_note": _hashed_ref(MARKDOWN_REPORT),
            "c5_validation_note": _hashed_ref(MARKDOWN_REPORT),
            "rollback_schema_deprecation_note": _hashed_ref(MARKDOWN_REPORT),
            "post_rollback_audit_schema_artifact": _hashed_ref(artifact),
            "post_rollback_absent_columns": ["area_baseline_corrected_linear_edge"],
            "affected_public_contracts_reviewed": ["alignment_cell_integration_audit.tsv"],
            "reviewer_identity": "reviewer",
            "review_date": "2026-05-27",
        },
    )

    assert validate_retirement_prerequisites(path).status == INCONCLUSIVE_INVALID_INPUT


def test_validate_retirement_prerequisites_requires_absent_columns_list(
    tmp_path: Path,
) -> None:
    artifact = _write_post_rollback_schema_artifact(tmp_path / "schema.tsv")
    path = _write_json(
        tmp_path / "prereq.json",
        {
            "c1a_status": "LANDED_VALIDATED",
            "c5_status": "LANDED_VALIDATED",
            "rollback_column_status": "DEPRECATED_BY_APPROVED_SCHEMA_NOTE",
            "c1a_validation_note": _hashed_ref(MARKDOWN_REPORT),
            "c5_validation_note": _hashed_ref(MARKDOWN_REPORT),
            "rollback_schema_deprecation_note": _hashed_ref(MARKDOWN_REPORT),
            "post_rollback_audit_schema_artifact": _hashed_ref(artifact),
            "post_rollback_absent_columns": {
                "area_baseline_corrected_linear_edge": True,
                "baseline_score_linear_edge": True,
            },
            "affected_public_contracts_reviewed": ["alignment_cell_integration_audit.tsv"],
            "reviewer_identity": "reviewer",
            "review_date": "2026-05-27",
        },
    )

    assert validate_retirement_prerequisites(path).status == INCONCLUSIVE_INVALID_INPUT


def _validate_tier_a(
    *,
    rows_path: Path = ROWS,
    summary_path: Path = SUMMARY,
    json_path: Path = JSON_REPORT,
    report_path: Path = MARKDOWN_REPORT,
    manifest_path: Path = TIER_A_MANIFEST,
    verify_artifact_hashes: bool = True,
    require_p2b_85raw_acceptance: bool = True,
):
    return validate_tier_a(
        rows_path=rows_path,
        summary_path=summary_path,
        json_path=json_path,
        report_path=report_path,
        manifest_path=manifest_path,
        fixture_manifest=load_fixture_manifest(FIXTURE_MANIFEST),
        verify_artifact_hashes=verify_artifact_hashes,
        require_p2b_85raw_acceptance=require_p2b_85raw_acceptance,
    )


def _copy_tsv(source: Path, destination: Path) -> Path:
    destination.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    return destination


def _copy_json(source: Path, destination: Path) -> Path:
    destination.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    return destination


def _load_json(path: Path) -> dict[str, object]:
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    assert isinstance(value, dict)
    return value


def _write_json(path: Path, value: dict[str, object]) -> Path:
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def _read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def _write_tsv(path: Path, rows: list[dict[str, str]]) -> None:
    assert rows
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def _hashed_ref(path: Path) -> dict[str, str]:
    return {"path": str(path), "sha256": sha256_file(path)}


def _evidence_metadata() -> dict[str, object]:
    return {
        "evidence_artifacts": [_hashed_ref(MARKDOWN_REPORT)],
        "thresholds_used": ["p2c_task4_test_thresholds"],
        "reviewer_or_generator": "pytest",
        "output_scope": ["alignment_matrix.tsv"],
        "target_classes": ["ISTD"],
        "known_exclusions": [],
    }


_POST_ROLLBACK_SCHEMA_COLUMNS = [
    "feature_family_id",
    "sample_stem",
    "status",
    "area",
    "apex_rt",
    "peak_start_rt",
    "peak_end_rt",
    "area_baseline_corrected",
    "area_uncertainty",
    "baseline_type",
    "baseline_score",
    "integration_scan_count",
]


def _write_post_rollback_schema_artifact(path: Path) -> Path:
    return _write_tsv_artifact(path, _POST_ROLLBACK_SCHEMA_COLUMNS)


def _write_tsv_artifact(path: Path, columns: list[str]) -> Path:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t")
        writer.writerow(columns)
        writer.writerow(["dummy" for _ in columns])
    return path
