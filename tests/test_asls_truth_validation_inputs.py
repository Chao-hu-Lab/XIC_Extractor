from __future__ import annotations

import csv
import datetime as dt
import json
import os
import subprocess
from pathlib import Path

from tools.diagnostics.asls_truth_validation_inputs import (
    FAIL,
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
TIER_A_ARTIFACT_DIR = FIXTURE_DIR / "asls_truth_tier_a_artifacts"
TIER_A_MANIFEST = FIXTURE_DIR / "asls_truth_tier_a_expected_manifest.json"
FIXTURE_MANIFEST = FIXTURE_DIR / "asls_truth_validation_fixture_manifest.json"
ROWS = TIER_A_ARTIFACT_DIR / "baseline_truth_audit_rows.tsv"
SUMMARY = TIER_A_ARTIFACT_DIR / "baseline_truth_audit_summary.tsv"
JSON_REPORT = TIER_A_ARTIFACT_DIR / "baseline_truth_audit.json"
MARKDOWN_REPORT = TIER_A_ARTIFACT_DIR / "baseline_truth_audit.md"


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


def test_validate_tier_a_requires_rt_and_boundary_status_columns(
    tmp_path: Path,
) -> None:
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


def test_linear_edge_pattern_coverage_includes_baseline_and_boundary_hard_cases() -> (
    None
):
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


def test_validate_tier_c_baseline_audit_passes_with_reviewed_linear_edge_support(
    tmp_path: Path,
) -> None:
    path = _write_json(tmp_path / "tier_c.json", _tier_c_baseline_evidence(tmp_path))

    result = validate_tier_c(path)

    assert result.status == PASS
    assert result.baseline_evidence_status == PASS
    assert result.blank_safety_status == NOT_APPLICABLE_WITH_EXCLUSION
    assert result.stress_axis_gate_status == PASS
    assert result.axis == "asls_vs_linear_edge_baseline_audit"
    assert result.row_blocker_count == 0
    assert result.review_required_count == 0
    assert result.stress_axis_disposition_statuses == ("blank_carryover=PASS",)


def test_validate_tier_c_resolves_relative_baseline_refs_from_evidence_json(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data = _make_refs_relative(_tier_c_baseline_evidence(tmp_path), root=tmp_path)
    baseline_artifacts = data["baseline_truth_artifacts"]
    assert isinstance(baseline_artifacts, dict)
    plot_dir = baseline_artifacts["plot_dir"]
    assert isinstance(plot_dir, str)
    baseline_artifacts["plot_dir"] = os.path.relpath(plot_dir, tmp_path)
    family_dispositions = data["family_dispositions"]
    assert isinstance(family_dispositions, list)
    for family in family_dispositions:
        assert isinstance(family, dict)
        plot_path = family["plot_path"]
        assert isinstance(plot_path, str)
        family["plot_path"] = os.path.relpath(plot_path, tmp_path)
        reviewed_rows = family["reviewed_rows"]
        assert isinstance(reviewed_rows, list)
        for reviewed_row in reviewed_rows:
            assert isinstance(reviewed_row, dict)
            reviewed_plot = reviewed_row["plot_path"]
            assert isinstance(reviewed_plot, str)
            reviewed_row["plot_path"] = os.path.relpath(reviewed_plot, tmp_path)
    path = _write_json(tmp_path / "tier_c.json", data)
    cwd = tmp_path / "cwd"
    cwd.mkdir()

    monkeypatch.chdir(cwd)

    assert validate_tier_c(path).status == PASS


def test_validate_tier_c_rejects_fixed_ratio_threshold_authority(
    tmp_path: Path,
) -> None:
    data = _tier_c_baseline_evidence(tmp_path)
    data["ratio_metrics_are_descriptive"] = False
    data["fixed_area_uplift_threshold"] = 1.25
    path = _write_json(tmp_path / "tier_c.json", data)

    result = validate_tier_c(path)

    assert result.status == INCONCLUSIVE_INVALID_INPUT
    assert "ratio_metrics_are_descriptive" in result.reasons[0]


def test_validate_tier_c_review_required_does_not_roll_up_to_pass(
    tmp_path: Path,
) -> None:
    path = _write_json(
        tmp_path / "tier_c.json",
        _tier_c_baseline_evidence(
            tmp_path,
            baseline_status=NOT_PROVIDED,
            tier_c_status="MIXED",
            family_disposition="REQUIRES_REVIEW",
            row_blockers=["mixed_or_review_required"],
        ),
    )

    result = validate_tier_c(path)

    assert result.status == "MIXED"
    assert result.baseline_evidence_status == NOT_PROVIDED
    assert result.row_blocker_count == 1
    assert result.review_required_count == 1


def test_validate_tier_c_hard_asls_blocker_fails_baseline_evidence(
    tmp_path: Path,
) -> None:
    path = _write_json(
        tmp_path / "tier_c.json",
        _tier_c_baseline_evidence(
            tmp_path,
            baseline_status=FAIL,
            tier_c_status=FAIL,
            family_disposition="FAIL",
            row_blockers=["asls_area_exceeds_raw_area"],
        ),
    )

    result = validate_tier_c(path)

    assert result.status == FAIL
    assert result.baseline_evidence_status == FAIL
    assert result.row_blocker_count == 1


def test_validate_tier_c_pass_family_with_hard_blocker_fails_baseline_evidence(
    tmp_path: Path,
) -> None:
    path = _write_json(
        tmp_path / "tier_c.json",
        _tier_c_baseline_evidence(
            tmp_path,
            family_disposition="PASS_BASELINE_SUPPORTED",
            row_blockers=["asls_area_exceeds_raw_area"],
        ),
    )

    result = validate_tier_c(path)

    assert result.status == FAIL
    assert result.baseline_evidence_status == FAIL
    assert result.row_blocker_count == 1


def test_validate_tier_c_declared_fail_cannot_be_upgraded_by_family_rollup(
    tmp_path: Path,
) -> None:
    path = _write_json(
        tmp_path / "tier_c.json",
        _tier_c_baseline_evidence(tmp_path, baseline_status=FAIL),
    )

    result = validate_tier_c(path)

    assert result.status == FAIL
    assert result.baseline_evidence_status == FAIL


def test_validate_tier_c_declared_unresolved_cannot_be_upgraded_by_family_rollup(
    tmp_path: Path,
) -> None:
    path = _write_json(
        tmp_path / "tier_c.json",
        _tier_c_baseline_evidence(
            tmp_path,
            baseline_status=NOT_PROVIDED,
            tier_c_status="MIXED",
        ),
    )

    result = validate_tier_c(path)

    assert result.status == "MIXED"
    assert result.baseline_evidence_status == NOT_PROVIDED


def test_validate_tier_c_rejects_neutral_unknown_axis(tmp_path: Path) -> None:
    data = _tier_c_baseline_evidence(tmp_path)
    data["tier_c_axis"] = "external_reference_axis"
    path = _write_json(tmp_path / "tier_c.json", data)

    result = validate_tier_c(path)

    assert result.status == INCONCLUSIVE_INVALID_INPUT
    assert "unsupported tier_c_axis" in result.reasons[0]


def test_validate_tier_c_blank_exclusion_requires_contract_tests(
    tmp_path: Path,
) -> None:
    data = _tier_c_baseline_evidence(tmp_path)
    data["consumer_contract_tests"] = []
    path = _write_json(tmp_path / "tier_c.json", data)

    result = validate_tier_c(path)

    assert result.status == INCONCLUSIVE_INVALID_INPUT
    assert "consumer_contract_tests" in result.reasons[0]


def test_validate_tier_c_blank_pass_requires_blank_evidence_refs(
    tmp_path: Path,
) -> None:
    data = _tier_c_baseline_evidence(
        tmp_path,
        blank_safety_status=PASS,
    )
    data["blank_control_evidence_refs"] = []
    path = _write_json(tmp_path / "tier_c.json", data)

    result = validate_tier_c(path)

    assert result.status == INCONCLUSIVE_INVALID_INPUT
    assert "blank_control_evidence_refs" in result.reasons[0]


def test_validate_tier_c_blank_gap_is_not_aggregate_pass(tmp_path: Path) -> None:
    path = _write_json(
        tmp_path / "tier_c.json",
        _tier_c_baseline_evidence(
            tmp_path,
            blank_safety_status=NOT_PROVIDED,
        ),
    )

    result = validate_tier_c(path)

    assert result.status == "MIXED"
    assert result.blank_safety_status == NOT_PROVIDED


def test_validate_tier_c_rejects_malformed_baseline_rows_artifact(
    tmp_path: Path,
) -> None:
    data = _tier_c_baseline_evidence(tmp_path)
    rows_ref = data["baseline_truth_artifacts"]["rows_tsv"]
    rows_path = Path(rows_ref["path"])
    rows_ref["sha256"] = _artifact_ref(rows_path, "target_label\nISTD-A\n")["sha256"]
    path = _write_json(tmp_path / "tier_c.json", data)

    result = validate_tier_c(path)

    assert result.status == INCONCLUSIVE_INVALID_INPUT
    assert "baseline rows fieldnames" in result.reasons[0]


def test_validate_tier_c_rejects_malformed_baseline_json_artifact(
    tmp_path: Path,
) -> None:
    data = _tier_c_baseline_evidence(tmp_path)
    json_ref = data["baseline_truth_artifacts"]["json"]
    json_path = Path(json_ref["path"])
    json_ref["sha256"] = _artifact_ref(json_path, '{"not_families": []}\n')[
        "sha256"
    ]
    path = _write_json(tmp_path / "tier_c.json", data)

    result = validate_tier_c(path)

    assert result.status == INCONCLUSIVE_INVALID_INPUT
    assert "baseline JSON families" in result.reasons[0]


def test_validate_tier_c_accepts_promoted_tier_a_baseline_row_columns(
    tmp_path: Path,
) -> None:
    data = _tier_c_baseline_evidence(tmp_path)
    rows_ref = data["baseline_truth_artifacts"]["rows_tsv"]
    assert isinstance(rows_ref, dict)
    rows_path = Path(str(rows_ref["path"]))
    promoted_rows = _baseline_rows_text(_tier_c_fixture_plot_path(data)).replace(
        "plot_path\n",
        "plot_path\trt_identity_status\tboundary_status\n",
    ).replace(
        "ISTD-A.png\n",
        "ISTD-A.png\tPASS\taccepted\n",
    )
    rows_ref["sha256"] = _artifact_ref(rows_path, promoted_rows)["sha256"]
    path = _write_json(tmp_path / "tier_c.json", data)

    result = validate_tier_c(path)

    assert result.status == PASS
    assert result.baseline_evidence_status == PASS


def test_validate_tier_c_accepts_p2_audit_summary_rows_json(
    tmp_path: Path,
) -> None:
    data = _tier_c_baseline_evidence(tmp_path)
    json_ref = data["baseline_truth_artifacts"]["json"]
    assert isinstance(json_ref, dict)
    json_path = Path(str(json_ref["path"]))
    json_ref["sha256"] = _artifact_ref(
        json_path,
        _baseline_json_text(Path("plots") / "ISTD-A.png").replace(
            '"families"',
            '"summary_rows"',
            1,
        ),
    )["sha256"]
    path = _write_json(tmp_path / "tier_c.json", data)

    result = validate_tier_c(path)

    assert result.status == PASS
    assert result.baseline_evidence_status == PASS


def test_validate_tier_c_rejects_baseline_rows_with_unexpected_column(
    tmp_path: Path,
) -> None:
    data = _tier_c_baseline_evidence(tmp_path)
    rows_ref = data["baseline_truth_artifacts"]["rows_tsv"]
    rows_path = Path(rows_ref["path"])
    bad_rows = rows_path.read_text(encoding="utf-8").replace(
        "plot_path\n",
        "plot_path\tunexpected_column\n",
    )
    rows_ref["sha256"] = _artifact_ref(rows_path, bad_rows)["sha256"]
    path = _write_json(tmp_path / "tier_c.json", data)

    result = validate_tier_c(path)

    assert result.status == INCONCLUSIVE_INVALID_INPUT
    assert "baseline rows fieldnames" in result.reasons[0]


def test_validate_tier_c_rejects_family_disposition_without_row_link(
    tmp_path: Path,
) -> None:
    data = _tier_c_baseline_evidence(tmp_path)
    data["family_dispositions"][0]["reviewed_rows"][0]["sample_stem"] = "missing_sample"
    path = _write_json(tmp_path / "tier_c.json", data)

    result = validate_tier_c(path)

    assert result.status == INCONCLUSIVE_INVALID_INPUT
    assert "reviewed row not found" in result.reasons[0]


def test_validate_tier_c_rejects_baseline_json_missing_summary_family(
    tmp_path: Path,
) -> None:
    data = _tier_c_baseline_evidence(tmp_path)
    plot_path = _tier_c_fixture_plot_path(data)
    summary_ref = data["baseline_truth_artifacts"]["summary_tsv"]
    assert isinstance(summary_ref, dict)
    summary_path = Path(str(summary_ref["path"]))
    summary_ref["sha256"] = _artifact_ref(
        summary_path,
        _baseline_summary_text(plot_path)
        + _second_baseline_summary_row_text(plot_path),
    )["sha256"]
    path = _write_json(tmp_path / "tier_c.json", data)

    result = validate_tier_c(path)

    assert result.status == INCONCLUSIVE_INVALID_INPUT
    assert "baseline JSON families missing baseline summary family" in result.reasons[0]


def test_validate_tier_c_rejects_missing_family_disposition_for_summary_family(
    tmp_path: Path,
) -> None:
    data = _tier_c_baseline_evidence(tmp_path)
    plot_path = _tier_c_fixture_plot_path(data)
    summary_ref = data["baseline_truth_artifacts"]["summary_tsv"]
    json_ref = data["baseline_truth_artifacts"]["json"]
    assert isinstance(summary_ref, dict)
    assert isinstance(json_ref, dict)
    summary_path = Path(str(summary_ref["path"]))
    json_path = Path(str(json_ref["path"]))
    summary_ref["sha256"] = _artifact_ref(
        summary_path,
        _baseline_summary_text(plot_path)
        + _second_baseline_summary_row_text(plot_path),
    )["sha256"]
    json_ref["sha256"] = _artifact_ref(
        json_path,
        _baseline_json_text(plot_path, include_second_family=True),
    )["sha256"]
    path = _write_json(tmp_path / "tier_c.json", data)

    result = validate_tier_c(path)

    assert result.status == INCONCLUSIVE_INVALID_INPUT
    assert "family_dispositions missing baseline summary family" in result.reasons[0]


def test_validate_tier_c_inconclusive_family_is_invalid_input(
    tmp_path: Path,
) -> None:
    data = _tier_c_baseline_evidence(
        tmp_path,
        baseline_status=NOT_PROVIDED,
        tier_c_status="MIXED",
        family_disposition="INCONCLUSIVE",
    )
    path = _write_json(tmp_path / "tier_c.json", data)

    result = validate_tier_c(path)

    assert result.status == INCONCLUSIVE_INVALID_INPUT
    assert "family_disposition=INCONCLUSIVE" in result.reasons[0]


def test_validate_tier_c_empty_stress_axis_is_not_retirement_ready(
    tmp_path: Path,
) -> None:
    data = _tier_c_baseline_evidence(tmp_path)
    data["stress_axis_dispositions"] = []
    path = _write_json(tmp_path / "tier_c.json", data)

    result = validate_tier_c(path)

    assert result.status == "MIXED"
    assert result.stress_axis_gate_status == NOT_PROVIDED


def test_validate_tier_c_stress_axis_pass_requires_evidence_refs(
    tmp_path: Path,
) -> None:
    data = _tier_c_baseline_evidence(tmp_path)
    data["stress_axis_dispositions"][0]["status"] = PASS
    data["stress_axis_dispositions"][0]["evidence_artifacts"] = []
    path = _write_json(tmp_path / "tier_c.json", data)

    result = validate_tier_c(path)

    assert result.status == INCONCLUSIVE_INVALID_INPUT
    assert "evidence_artifacts" in result.reasons[0]


def test_validate_tier_c_stress_axis_not_required_is_not_retirement_ready(
    tmp_path: Path,
) -> None:
    data = _tier_c_baseline_evidence(tmp_path)
    data["stress_axis_dispositions"][0]["status"] = "NOT_REQUIRED"
    data["stress_axis_dispositions"][0]["evidence_artifacts"] = []
    path = _write_json(tmp_path / "tier_c.json", data)

    result = validate_tier_c(path)

    assert result.status == "MIXED"
    assert result.stress_axis_gate_status == NOT_PROVIDED
    assert result.stress_axis_disposition_statuses == ("blank_carryover=NOT_REQUIRED",)


def test_validate_tier_c_rejects_unsupported_axis(tmp_path: Path) -> None:
    path = _write_json(
        tmp_path / "tier_c.json",
        {"tier_c_axis": "external_reference_axis", "tier_c_status": "PASS"},
    )

    assert validate_tier_c(path).status == INCONCLUSIVE_INVALID_INPUT


def test_validate_tier_c_rejects_unverifiable_pass_evidence(tmp_path: Path) -> None:
    path = _write_json(
        tmp_path / "tier_c.json",
        {
            "tier_c_axis": "asls_vs_linear_edge_baseline_audit",
            "tier_c_status": "PASS",
        },
    )

    assert validate_tier_c(path).status == INCONCLUSIVE_INVALID_INPUT


def test_validate_tier_c_rejects_unsupported_axis_even_when_status_fail(
    tmp_path: Path,
) -> None:
    path = _write_json(
        tmp_path / "tier_c.json",
        {"tier_c_axis": "external_reference_axis", "tier_c_status": "FAIL"},
    )

    assert validate_tier_c(path).status == INCONCLUSIVE_INVALID_INPUT


def test_validate_tier_c_accepts_not_provided_without_pretending_pass(
    tmp_path: Path,
) -> None:
    path = _write_json(
        tmp_path / "tier_c.json",
        {
            "tier_c_axis": "asls_vs_linear_edge_baseline_audit",
            "tier_c_status": NOT_PROVIDED,
        },
    )

    result = validate_tier_c(path)

    assert result.status == NOT_PROVIDED
    assert result.baseline_evidence_status == NOT_PROVIDED
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
            "waived_tier_c_evidence": ["asls_vs_linear_edge_baseline_audit"],
            "waiver_rationale": (
                "No baseline evidence audit is approved for this dataset."
            ),
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
            "waived_tier_c_evidence": [],
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
            "waived_tier_c_evidence": ["asls_vs_linear_edge_baseline_audit"],
            "waiver_rationale": (
                "No baseline evidence audit is approved for this dataset."
            ),
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


def test_valid_waiver_does_not_supply_baseline_evidence_authority(
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
            "waived_tier_c_evidence": ["asls_vs_linear_edge_baseline_audit"],
            "waiver_rationale": (
                "No baseline evidence audit is approved for this dataset."
            ),
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
    assert result.baseline_evidence_status == NOT_PROVIDED


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
            "affected_public_contracts_reviewed": [
                "alignment_cell_integration_audit.tsv"
            ],
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
            "affected_public_contracts_reviewed": [
                "alignment_cell_integration_audit.tsv"
            ],
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
            "affected_public_contracts_reviewed": [
                "alignment_cell_integration_audit.tsv"
            ],
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
            "affected_public_contracts_reviewed": [
                "alignment_cell_integration_audit.tsv"
            ],
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
            "affected_public_contracts_reviewed": [
                "alignment_cell_integration_audit.tsv"
            ],
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
            "affected_public_contracts_reviewed": [
                "alignment_cell_integration_audit.tsv"
            ],
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
            "affected_public_contracts_reviewed": [
                "alignment_cell_integration_audit.tsv"
            ],
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
            "affected_public_contracts_reviewed": [
                "alignment_cell_integration_audit.tsv"
            ],
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


def _artifact_ref(path: Path, text: str = "artifact\n") -> dict[str, str]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return {"path": str(path), "sha256": sha256_file(path)}


def _make_refs_relative(value: object, *, root: Path) -> object:
    if isinstance(value, dict):
        converted = {
            key: _make_refs_relative(item, root=root) for key, item in value.items()
        }
        if "path" in converted and isinstance(converted["path"], str):
            converted["path"] = os.path.relpath(converted["path"], root)
        return converted
    if isinstance(value, list):
        return [_make_refs_relative(item, root=root) for item in value]
    return value


def _baseline_rows_text(plot_path: Path) -> str:
    header = (
        "target_label",
        "feature_family_id",
        "sample_stem",
        "status",
        "raw_area",
        "linear_area",
        "asls_area",
        "linear_raw_pct",
        "asls_raw_pct",
        "asls_vs_linear_pct",
        "linear_baseline_subtracted_pct",
        "asls_baseline_subtracted_pct",
        "linear_edge_delta_pct",
        "outside_background_pct",
        "peak_start_rt",
        "apex_rt",
        "peak_end_rt",
        "trace_point_count",
        "classification",
        "review_reason",
        "plot_path",
    )
    row = (
        "ISTD-A",
        "ISTD-A::100.0::1.20",
        "sample_001",
        "PASS",
        "100.0",
        "60.0",
        "95.0",
        "60.0",
        "95.0",
        "58.3",
        "40.0",
        "5.0",
        "35.0",
        "20.0",
        "1.10",
        "1.20",
        "1.30",
        "11",
        "linear_edge_over_subtraction_plausible",
        "linear edge crosses the shoulder",
        str(plot_path),
    )
    return "\t".join(header) + "\n" + "\t".join(row) + "\n"


def _baseline_summary_text(plot_path: Path) -> str:
    header = (
        "target_label",
        "feature_family_id",
        "row_count",
        "dominant_classification",
        "classification_counts",
        "median_linear_baseline_subtracted_pct",
        "median_asls_baseline_subtracted_pct",
        "median_asls_vs_linear_pct",
        "max_asls_vs_linear_pct",
        "median_linear_edge_delta_pct",
        "median_outside_background_pct",
        "review_status",
        "plot_path",
    )
    row = (
        "ISTD-A",
        "ISTD-A::100.0::1.20",
        "1",
        "linear_edge_over_subtraction_plausible",
        '{"linear_edge_over_subtraction_plausible": 1}',
        "40.0",
        "5.0",
        "58.3",
        "58.3",
        "35.0",
        "20.0",
        "reviewed",
        str(plot_path),
    )
    return "\t".join(header) + "\n" + "\t".join(row) + "\n"


def _baseline_json_text(
    plot_path: Path,
    *,
    include_second_family: bool = False,
) -> str:
    families = [
        {
            "target_label": "ISTD-A",
            "feature_family_id": "ISTD-A::100.0::1.20",
            "dominant_classification": "linear_edge_over_subtraction_plausible",
            "plot_path": str(plot_path),
        }
    ]
    if include_second_family:
        families.append(
            {
                "target_label": "ISTD-B",
                "feature_family_id": "ISTD-B::200.0::2.20",
                "dominant_classification": (
                    "low_outside_background_with_baseline_disagreement"
                ),
                "plot_path": str(plot_path),
            }
        )
    return json.dumps(
        {"families": families}
    )


def _second_baseline_summary_row_text(plot_path: Path) -> str:
    row = (
        "ISTD-B",
        "ISTD-B::200.0::2.20",
        "1",
        "low_outside_background_with_baseline_disagreement",
        '{"low_outside_background_with_baseline_disagreement": 1}',
        "45.0",
        "15.0",
        "35.0",
        "35.0",
        "30.0",
        "12.0",
        "requires_review",
        str(plot_path),
    )
    return "\t".join(row) + "\n"


def _tier_c_fixture_plot_path(data: dict[str, object]) -> Path:
    families = data["family_dispositions"]
    assert isinstance(families, list)
    first_family = families[0]
    assert isinstance(first_family, dict)
    return Path(str(first_family["plot_path"]))


def _tier_c_baseline_evidence(
    tmp_path: Path,
    *,
    baseline_status: str = PASS,
    tier_c_status: str = PASS,
    family_disposition: str = "PASS_BASELINE_SUPPORTED",
    row_blockers: list[str] | None = None,
    blank_safety_status: str = NOT_APPLICABLE_WITH_EXCLUSION,
) -> dict[str, object]:
    plot_dir = tmp_path / "plots"
    plot_dir.mkdir(parents=True, exist_ok=True)
    plot_path = plot_dir / "ISTD-A.png"
    plot_path.write_text("plot\n", encoding="utf-8")
    contract_ref = _artifact_ref(tmp_path / "contract_test.txt", "pass\n")
    stress_ref = _artifact_ref(
        tmp_path / "stress_axis_evidence.tsv",
        "stress_axis\tstatus\nblank_carryover\tPASS\n",
    )
    blank_refs: list[dict[str, str]] = []
    blank_absence_proof = ["alignment_matrix.tsv excludes blank quantitation"]
    contract_tests = [contract_ref]
    if blank_safety_status == PASS:
        blank_refs = [
            _artifact_ref(
                tmp_path / "blank_control_evidence.tsv",
                "sample_stem\tblank_status\nblank_001\tPASS\n",
            )
        ]
        blank_absence_proof = []
        contract_tests = []
    blockers = [] if row_blockers is None else row_blockers
    return {
        "tier_c_axis": "asls_vs_linear_edge_baseline_audit",
        "tier_c_status": tier_c_status,
        "tier_c_baseline_evidence_status": baseline_status,
        "blank_safety_status": blank_safety_status,
        "ratio_metrics_are_descriptive": True,
        "fixed_area_uplift_threshold": None,
        "baseline_truth_artifacts": {
            "rows_tsv": _artifact_ref(
                tmp_path / "baseline_truth_audit_rows.tsv",
                _baseline_rows_text(plot_path),
            ),
            "summary_tsv": _artifact_ref(
                tmp_path / "baseline_truth_audit_summary.tsv",
                _baseline_summary_text(plot_path),
            ),
            "json": _artifact_ref(
                tmp_path / "baseline_truth_audit.json",
                _baseline_json_text(plot_path),
            ),
            "markdown": _artifact_ref(
                tmp_path / "baseline_truth_audit.md",
                "# audit\n",
            ),
            "plot_dir": str(plot_dir),
        },
        "family_dispositions": [
            {
                "target_label": "ISTD-A",
                "feature_family_id": "ISTD-A::100.0::1.20",
                "covered_samples": ["sample_001"],
                "dominant_classification": "linear_edge_over_subtraction_plausible",
                "review_status": "reviewed",
                "decision_scope": "C1B_RELEVANCE",
                "plot_path": str(plot_path),
                "reviewed_rows": [
                    {
                        "target_label": "ISTD-A",
                        "feature_family_id": "ISTD-A::100.0::1.20",
                        "sample_stem": "sample_001",
                        "peak_start_rt": "1.10",
                        "apex_rt": "1.20",
                        "peak_end_rt": "1.30",
                        "plot_path": str(plot_path),
                    }
                ],
                "family_disposition": family_disposition,
                "tier_c_row_blockers": blockers,
                "reviewer_disposition": (
                    "AsLS baseline is more plausible than linear edge."
                ),
                "reason": "Linear edge crosses the peak shoulder on the linked plot.",
            }
        ],
        "affected_outputs": ["alignment_matrix.tsv"],
        "blank_control_evidence_status": blank_safety_status,
        "blank_control_evidence_refs": blank_refs,
        "blank_rows_absence_proof": blank_absence_proof,
        "consumer_contract_tests": contract_tests,
        "stress_axis_dispositions": [
                {
                    "stress_axis": "blank_carryover",
                    "status": PASS,
                    "decision_scope": "RETIREMENT_ONLY",
                    "rationale": "Scoped outputs do not consume blank quantitation.",
                    "evidence_artifacts": [stress_ref],
                }
            ],
        "row_count": 1,
        "sample_count": 1,
        "raw_file_count": 1,
        "selected_istd_count": 1,
        "high_risk_morphology_row_count": 1,
        "covered_target_classes": ["ISTD"],
        "known_exclusions": [],
        "reviewer_or_generator": "methodology_owner",
        "output_scope": ["alignment_matrix.tsv"],
        "target_classes": ["ISTD"],
    }


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
