import csv
import json
from pathlib import Path

from scripts.build_lockbox_shadow_automation_experiment_design import (
    GAUSSIAN_BOUNDARY_POLICY,
    SHADOW_EXPERIMENT_CASES,
    SHADOW_EXPERIMENT_SUMMARY,
    build_lockbox_shadow_automation_experiment_design,
    check_lockbox_shadow_automation_experiment_design,
)
from scripts.build_lockbox_single_owner_ai_challenge_gate import (
    GATE_SUMMARY as SINGLE_OWNER_GATE,
)
from xic_extractor.tabular_io import file_sha256


def test_current_shadow_automation_experiment_design_validates() -> None:
    assert check_lockbox_shadow_automation_experiment_design() == []


def test_current_shadow_automation_case_manifest_counts_and_authority() -> None:
    rows = _read_tsv(SHADOW_EXPERIMENT_CASES)

    assert len(rows) == 72
    assert _counts(rows, "shadow_experiment_role") == {
        "excluded_gaussian_boundary_unavailable": 1,
        "excluded_roundtrip_oracle_nontruth": 12,
        "manual_negative_control": 6,
        "owner_clean_positive_challenge": 53,
    }
    assert sum(row["included_in_shadow_experiment"] == "TRUE" for row in rows) == 59
    for field in (
        "may_feed_product_writer",
        "may_touch_matrix",
        "may_grant_product_authority",
        "may_change_workbook",
        "may_switch_selected_peak",
        "may_change_selected_area",
        "may_change_counted_detection",
        "may_change_default_extraction",
        "may_change_gui",
        "broad_backfill_unparked",
        "write_authority",
        "matrix_write_allowed",
        "may_satisfy_reviewer_slot2",
        "single_owner_evidence_is_truth_completion",
    ):
        assert {row[field] for row in rows} == {"FALSE"}
    assert {row["shadow_only"] for row in rows} == {"TRUE"}


def test_current_shadow_summary_is_design_only() -> None:
    summary = json.loads(SHADOW_EXPERIMENT_SUMMARY.read_text(encoding="utf-8"))

    assert summary["decision"] == "shadow_scoring_contract_adapter_v1_ready"
    assert summary["allowed_next_step"] == "define_production_acceptance_manifest_v1"
    assert summary["case_counts"] == {
        "excluded_gaussian_boundary_unavailable_cases": 1,
        "excluded_roundtrip_oracle_nontruth_cases": 12,
        "included_shadow_experiment_rows": 59,
        "manual_negative_control_cases": 6,
        "owner_clean_positive_challenge_cases": 53,
        "product_authority_rows": 0,
        "total_manifest_rows": 72,
    }
    assert (
        summary["shadow_experiment_contract"]["gaussian_boundary_policy"]
        == GAUSSIAN_BOUNDARY_POLICY
    )
    assert summary["contract_counts"]["shadow_decision"] == {
        "accept": 53,
        "not_scored": 13,
        "reject": 6,
    }
    assert summary["contract_counts"]["truth_status"] == {
        "manual_negative": 6,
        "not_truth_claimed": 65,
        "unresolved": 1,
    }
    assert summary["shadow_experiment_contract"]["shadow_decisions"] == [
        "accept",
        "flag",
        "not_scored",
        "reject",
    ]
    assert summary["shadow_experiment_contract"]["truth_statuses"] == [
        "external_truth_negative",
        "external_truth_positive",
        "manual_negative",
        "not_truth_claimed",
        "unresolved",
    ]
    assert (
        summary["shadow_experiment_contract"]["owner_clean_truth_status"]
        == "not_truth_claimed"
    )
    assert (
        summary["shadow_experiment_contract"]["owner_clean_challenge_status"]
        == "non_authoritative_challenge"
    )
    assert summary["shadow_experiment_contract"][
        "manual_negative_accept_hard_stop"
    ] is True
    assert summary["shadow_experiment_contract"][
        "right_unclear_unresolved_doublet_accept_hard_stop"
    ] is True
    assert summary["output_rules"] == {
        "matrix_write_allowed": False,
        "shadow_only": True,
        "write_authority": False,
    }
    assert summary["source_artifacts"]["source_case_manifest"] == (
        "docs/superpowers/validation/lockbox_shadow_automation_cases_v1.tsv"
    )
    assert len(summary["source_artifacts"]["shadow_case_manifest_sha256"]) == 64
    assert summary["authority_rules"]["may_satisfy_reviewer_slot2"] is False
    assert (
        summary["authority_rules"]["single_owner_evidence_is_truth_completion"]
        is False
    )
    assert set(summary["shadow_experiment_contract"]["promotion_requires"]) == {
        "authority_manifest_update",
        "expected_diff_gate",
        "focused output tests",
        "masked_or_product_writer_oracle",
        "separate product goal",
    }
    assert set(summary["authority_rules"].values()) == {False}


def test_owner_clean_rows_are_positive_challenge_only() -> None:
    rows = _read_tsv(SHADOW_EXPERIMENT_CASES)
    positives = [
        row
        for row in rows
        if row["shadow_experiment_role"] == "owner_clean_positive_challenge"
    ]

    assert len(positives) == 53
    assert {row["included_in_shadow_experiment"] for row in positives} == {"TRUE"}
    assert {row["plot_status"] for row in positives} == {"plotted_gaussian15"}
    assert {row["imported_peak_choice_labels"] for row in positives} == {"correct"}
    assert {row["imported_area_labels"] for row in positives} == {"acceptable"}
    assert {row["imported_boundary_labels"] for row in positives} == {"acceptable"}
    assert {row["shadow_oracle_basis"] for row in positives} == {
        "single_owner_gaussian15_boundary_plus_ai_no_flag",
    }
    assert {row["shadow_decision"] for row in positives} == {"accept"}
    assert {row["truth_status"] for row in positives} == {"not_truth_claimed"}
    assert {row["owner_clean_challenge_status"] for row in positives} == {
        "non_authoritative_challenge",
    }
    assert {row["future_action_if_mismatch"] for row in positives} == {
        "flag_for_owner_recheck_only",
    }


def test_manual_negative_controls_are_not_writer_authority() -> None:
    rows = _read_tsv(SHADOW_EXPERIMENT_CASES)
    controls = [
        row
        for row in rows
        if row["shadow_experiment_role"] == "manual_negative_control"
    ]

    assert len(controls) == 6
    assert {row["included_in_shadow_experiment"] for row in controls} == {"TRUE"}
    assert {row["shadow_oracle_basis"] for row in controls} == {
        "existing_manual_wrong_peak_or_no_peak_fixture",
    }
    assert {row["expected_shadow_behavior"] for row in controls} == {
        "future_shadow_logic_should_flag_or_reject_manual_negative_control",
    }
    assert {row["shadow_decision"] for row in controls} == {"reject"}
    assert {row["truth_status"] for row in controls} == {"manual_negative"}
    assert {row["may_feed_product_writer"] for row in controls} == {"FALSE"}


def test_oracle_negative_and_boundary_gap_rows_are_excluded() -> None:
    rows = _read_tsv(SHADOW_EXPERIMENT_CASES)
    excluded = [
        row
        for row in rows
        if row["shadow_experiment_role"]
        in {
            "excluded_roundtrip_oracle_nontruth",
            "excluded_gaussian_boundary_unavailable",
        }
    ]

    assert len(excluded) == 13
    assert {row["included_in_shadow_experiment"] for row in excluded} == {"FALSE"}
    assert {
        row["expected_shadow_behavior"]
        for row in excluded
        if row["shadow_experiment_role"] == "excluded_roundtrip_oracle_nontruth"
    } == {"not_scored_in_shadow_experiment"}
    assert {
        row["expected_shadow_behavior"]
        for row in excluded
        if row["shadow_experiment_role"] == "excluded_gaussian_boundary_unavailable"
    } == {"not_scored_until_gaussian_boundary_is_recovered"}
    assert {row["shadow_decision"] for row in excluded} == {"not_scored"}


def test_builder_rejects_stale_single_owner_gate(tmp_path: Path) -> None:
    gate = tmp_path / "single_owner_gate.json"
    payload = json.loads(SINGLE_OWNER_GATE.read_text(encoding="utf-8"))
    payload["decision"] = "stale"
    gate.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    result = build_lockbox_shadow_automation_experiment_design(
        single_owner_gate_path=gate,
        shadow_cases_path=tmp_path / "cases.tsv",
        shadow_summary_path=tmp_path / "summary.json",
    )

    assert any(
        "single-owner AI challenge gate summary is stale" in problem
        for problem in result["problems"]
    )


def test_checker_rejects_case_manifest_authority_drift(tmp_path: Path) -> None:
    cases = tmp_path / "cases.tsv"
    summary = tmp_path / "summary.json"
    build_lockbox_shadow_automation_experiment_design(
        shadow_cases_path=cases,
        shadow_summary_path=summary,
    )
    header, rows = _read_tsv_with_header(cases)
    rows[0]["may_feed_product_writer"] = "TRUE"
    _write_tsv(cases, header, rows)

    problems = check_lockbox_shadow_automation_experiment_design(
        shadow_cases_path=cases,
        shadow_summary_path=summary,
    )

    assert any("shadow automation case manifest is stale" in p for p in problems)
    assert any("may_feed_product_writer must be FALSE" in p for p in problems)


def test_checker_rejects_summary_authority_drift(tmp_path: Path) -> None:
    cases = tmp_path / "cases.tsv"
    summary = tmp_path / "summary.json"
    build_lockbox_shadow_automation_experiment_design(
        shadow_cases_path=cases,
        shadow_summary_path=summary,
    )
    payload = json.loads(summary.read_text(encoding="utf-8"))
    payload["authority_rules"]["may_touch_matrix"] = True
    summary.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    problems = check_lockbox_shadow_automation_experiment_design(
        shadow_cases_path=cases,
        shadow_summary_path=summary,
    )

    assert any("shadow automation summary is stale" in p for p in problems)
    assert any("authority_rules.may_touch_matrix drifted" in p for p in problems)


def test_summary_records_actual_case_manifest_path(tmp_path: Path) -> None:
    cases = tmp_path / "custom_cases.tsv"
    summary = tmp_path / "custom_summary.json"
    build_lockbox_shadow_automation_experiment_design(
        shadow_cases_path=cases,
        shadow_summary_path=summary,
    )

    payload = json.loads(summary.read_text(encoding="utf-8"))
    expected_path = cases.resolve().relative_to(Path.cwd()).as_posix()

    assert payload["source_artifacts"]["source_case_manifest"] == expected_path
    assert payload["source_artifacts"]["shadow_case_manifest_sha256"] == file_sha256(
        cases,
    )


def test_checker_rejects_manual_negative_accept_drift(tmp_path: Path) -> None:
    cases = tmp_path / "cases.tsv"
    summary = tmp_path / "summary.json"
    build_lockbox_shadow_automation_experiment_design(
        shadow_cases_path=cases,
        shadow_summary_path=summary,
    )
    header, rows = _read_tsv_with_header(cases)
    manual = next(
        row
        for row in rows
        if row["shadow_experiment_role"] == "manual_negative_control"
    )
    manual["shadow_decision"] = "accept"
    manual["doublet_allowed"] = "TRUE"
    _write_tsv(cases, header, rows)

    problems = check_lockbox_shadow_automation_experiment_design(
        shadow_cases_path=cases,
        shadow_summary_path=summary,
    )

    assert any("shadow automation case manifest is stale" in p for p in problems)
    assert any("manual negative cannot be accepted" in p for p in problems)


def test_checker_rejects_accept_with_blocked_doublet_states(tmp_path: Path) -> None:
    blocked_cases = (
        ("right_reference_blocked", "right"),
        ("unclear_reference_blocked", "unclear"),
        ("unresolved_blocked", "unresolved"),
    )
    for index, (status, side) in enumerate(blocked_cases):
        cases = tmp_path / f"cases_{index}.tsv"
        summary = tmp_path / f"summary_{index}.json"
        build_lockbox_shadow_automation_experiment_design(
            shadow_cases_path=cases,
            shadow_summary_path=summary,
        )
        header, rows = _read_tsv_with_header(cases)
        accepted = next(row for row in rows if row["shadow_decision"] == "accept")
        accepted["doublet_status"] = status
        accepted["doublet_reference_side"] = side
        accepted["doublet_allowed"] = "TRUE"
        _write_tsv(cases, header, rows)

        problems = check_lockbox_shadow_automation_experiment_design(
            shadow_cases_path=cases,
            shadow_summary_path=summary,
        )

        assert any("shadow automation case manifest is stale" in p for p in problems)
        assert any("doublet state cannot be accepted" in p for p in problems)


def test_checker_rejects_owner_clean_truth_completion(tmp_path: Path) -> None:
    cases = tmp_path / "cases.tsv"
    summary = tmp_path / "summary.json"
    build_lockbox_shadow_automation_experiment_design(
        shadow_cases_path=cases,
        shadow_summary_path=summary,
    )
    header, rows = _read_tsv_with_header(cases)
    owner_clean = next(
        row
        for row in rows
        if row["shadow_experiment_role"] == "owner_clean_positive_challenge"
    )
    owner_clean["truth_status"] = "external_truth_positive"
    owner_clean["owner_clean_challenge_status"] = "truth_completion"
    _write_tsv(cases, header, rows)

    problems = check_lockbox_shadow_automation_experiment_design(
        shadow_cases_path=cases,
        shadow_summary_path=summary,
    )

    assert any("shadow automation case manifest is stale" in p for p in problems)
    assert any("owner-clean cannot claim truth" in p for p in problems)


def test_checker_rejects_missing_source_hashes(tmp_path: Path) -> None:
    cases = tmp_path / "cases.tsv"
    summary = tmp_path / "summary.json"
    build_lockbox_shadow_automation_experiment_design(
        shadow_cases_path=cases,
        shadow_summary_path=summary,
    )
    header, rows = _read_tsv_with_header(cases)
    rows[0]["source_hashes"] = "next_action_plan=HASH_ONLY"
    _write_tsv(cases, header, rows)

    problems = check_lockbox_shadow_automation_experiment_design(
        shadow_cases_path=cases,
        shadow_summary_path=summary,
    )

    assert any("shadow automation case manifest is stale" in p for p in problems)
    assert any("row source hashes required" in p for p in problems)


def _counts(rows: list[dict[str, str]], field: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        counts[row[field]] = counts.get(row[field], 0) + 1
    return dict(sorted(counts.items()))


def _read_tsv(path: Path) -> list[dict[str, str]]:
    return _read_tsv_with_header(path)[1]


def _read_tsv_with_header(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        return list(reader.fieldnames or []), list(reader)


def _write_tsv(path: Path, header: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=header)
        writer.writeheader()
        writer.writerows(rows)
