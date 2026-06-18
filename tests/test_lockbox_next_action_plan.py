import csv
import json
from pathlib import Path

from scripts.build_lockbox_next_action_plan import (
    NEXT_ACTION_PLAN,
    NEXT_ACTION_SUMMARY,
    build_lockbox_next_action_plan,
    check_lockbox_next_action_plan,
)


def test_current_lockbox_next_action_plan_validates() -> None:
    assert check_lockbox_next_action_plan() == []


def test_current_lockbox_next_action_plan_counts_and_authority() -> None:
    rows = _read_tsv(NEXT_ACTION_PLAN)
    summary = json.loads(NEXT_ACTION_SUMMARY.read_text(encoding="utf-8"))

    assert len(rows) == 72
    assert summary["decision"] == "second_review_ready_for_53_cases"
    assert summary["case_counts"] == {
        "total_cases": 72,
        "product_authority_rows": 0,
        "needs_second_reviewer": 53,
        "needs_visual_evidence_recovery": 1,
        "manual_negative_control_cases": 6,
        "oracle_negative_parked_cases": 12,
    }
    assert summary["next_action_counts"] == {
        "park_roundtrip_oracle_negative_as_nontruth": 12,
        "ready_for_second_independent_review": 53,
        "recover_or_mark_gaussian_boundary_unavailable": 1,
        "use_existing_manual_negative_control": 6,
    }
    assert summary["authority_rules"] == {
        "broad_backfill_unparked": False,
        "manual_negative_fixture_grants_write_authority": False,
        "may_feed_product_writer": False,
        "may_grant_product_authority": False,
        "may_touch_matrix": False,
        "round_trip_oracle_used_as_truth": False,
    }
    assert {row["may_feed_product_writer"] for row in rows} == {"FALSE"}
    assert {row["may_touch_matrix"] for row in rows} == {"FALSE"}
    assert {row["may_grant_product_authority"] for row in rows} == {"FALSE"}
    assert {row["round_trip_oracle_can_be_truth"] for row in rows} == {"FALSE"}


def test_current_next_action_plan_keeps_manual_negatives_separate() -> None:
    rows = _read_tsv(NEXT_ACTION_PLAN)
    manual_rows = [
        row for row in rows if row["source_stratum"] == "manual_wrong_peak_or_no_peak"
    ]

    assert len(manual_rows) == 6
    assert {row["next_action"] for row in manual_rows} == {
        "use_existing_manual_negative_control",
    }
    assert {row["next_action_class"] for row in manual_rows} == {"negative_control"}
    assert {row["can_use_existing_manual_negative_control"] for row in manual_rows} == {
        "TRUE",
    }
    assert {row["needs_visual_evidence_recovery"] for row in manual_rows} == {"FALSE"}
    assert {row["parked_for_broad_backfill"] for row in manual_rows} == {"FALSE"}
    assert all(
        "manual_negative_fixture=" in row["source_hashes"] for row in manual_rows
    )


def test_current_next_action_plan_parks_round_trip_oracle_negatives() -> None:
    rows = _read_tsv(NEXT_ACTION_PLAN)
    oracle_rows = [
        row for row in rows if row["source_stratum"] == "failed_oracle_negative"
    ]

    assert len(oracle_rows) == 12
    assert {row["next_action"] for row in oracle_rows} == {
        "park_roundtrip_oracle_negative_as_nontruth",
    }
    assert {row["next_action_class"] for row in oracle_rows} == {"parked_nontruth"}
    assert {row["parked_for_broad_backfill"] for row in oracle_rows} == {"TRUE"}
    assert {row["round_trip_oracle_can_be_truth"] for row in oracle_rows} == {"FALSE"}
    assert all("oracle_results=" in row["source_hashes"] for row in oracle_rows)


def test_current_next_action_plan_routes_plotted_clean_cases_to_second_review() -> None:
    rows = _read_tsv(NEXT_ACTION_PLAN)
    second_review = [
        row
        for row in rows
        if row["next_action"] == "ready_for_second_independent_review"
    ]

    assert len(second_review) == 53
    assert {row["plot_status"] for row in second_review} == {"plotted_gaussian15"}
    assert {row["imported_peak_choice_labels"] for row in second_review} == {"correct"}
    assert {row["imported_area_labels"] for row in second_review} == {"acceptable"}
    assert {row["imported_boundary_labels"] for row in second_review} == {"acceptable"}
    assert {row["needs_second_reviewer"] for row in second_review} == {"TRUE"}
    assert {row["parked_for_broad_backfill"] for row in second_review} == {"FALSE"}


def test_current_next_action_plan_marks_boundary_unavailable_as_evidence_gap() -> None:
    rows = _read_tsv(NEXT_ACTION_PLAN)
    boundary_gaps = [
        row
        for row in rows
        if row["next_action"] == "recover_or_mark_gaussian_boundary_unavailable"
    ]

    assert len(boundary_gaps) == 1
    assert boundary_gaps[0]["plot_status"] == "gaussian_review_boundary_unavailable"
    assert boundary_gaps[0]["needs_visual_evidence_recovery"] == "TRUE"
    assert boundary_gaps[0]["may_feed_product_writer"] == "FALSE"


def test_next_action_builder_can_write_to_custom_paths(tmp_path: Path) -> None:
    plan = tmp_path / "next_action.tsv"
    summary = tmp_path / "next_action.json"

    result = build_lockbox_next_action_plan(
        next_action_plan_path=plan,
        next_action_summary_path=summary,
    )

    assert result["problems"] == []
    assert plan.exists()
    assert summary.exists()
    assert len(_read_tsv(plan)) == 72
    assert json.loads(summary.read_text(encoding="utf-8"))["case_counts"][
        "product_authority_rows"
    ] == 0


def test_next_action_checker_rejects_stale_plan(tmp_path: Path) -> None:
    plan = tmp_path / "next_action.tsv"
    summary = tmp_path / "next_action.json"
    build_lockbox_next_action_plan(
        next_action_plan_path=plan,
        next_action_summary_path=summary,
    )
    header, rows = _read_tsv_with_header(plan)
    rows[0]["next_action"] = "ready_for_truth_summary_gate"
    _write_tsv(plan, header, rows)

    problems = check_lockbox_next_action_plan(
        next_action_plan_path=plan,
        next_action_summary_path=summary,
    )

    assert any("next action plan is stale" in problem for problem in problems)


def test_next_action_checker_rejects_stale_summary_json(tmp_path: Path) -> None:
    plan = tmp_path / "next_action.tsv"
    summary = tmp_path / "next_action.json"
    build_lockbox_next_action_plan(
        next_action_plan_path=plan,
        next_action_summary_path=summary,
    )
    payload = json.loads(summary.read_text(encoding="utf-8"))
    payload["decision"] = "stale"
    summary.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    problems = check_lockbox_next_action_plan(
        next_action_plan_path=plan,
        next_action_summary_path=summary,
    )

    assert any("next action summary JSON is stale" in problem for problem in problems)


def test_next_action_checker_rejects_authority_flag_in_plan(tmp_path: Path) -> None:
    plan = tmp_path / "next_action.tsv"
    summary = tmp_path / "next_action.json"
    build_lockbox_next_action_plan(
        next_action_plan_path=plan,
        next_action_summary_path=summary,
    )
    header, rows = _read_tsv_with_header(plan)
    rows[0]["may_feed_product_writer"] = "TRUE"
    _write_tsv(plan, header, rows)

    problems = check_lockbox_next_action_plan(
        next_action_plan_path=plan,
        next_action_summary_path=summary,
    )

    assert any(
        "may_feed_product_writer must be FALSE" in problem for problem in problems
    )


def test_next_action_checker_rejects_summary_authority_rule(tmp_path: Path) -> None:
    plan = tmp_path / "next_action.tsv"
    summary = tmp_path / "next_action.json"
    build_lockbox_next_action_plan(
        next_action_plan_path=plan,
        next_action_summary_path=summary,
    )
    payload = json.loads(summary.read_text(encoding="utf-8"))
    payload["authority_rules"]["may_feed_product_writer"] = True
    summary.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    problems = check_lockbox_next_action_plan(
        next_action_plan_path=plan,
        next_action_summary_path=summary,
    )

    assert any(
        "authority_rules.may_feed_product_writer must be false" in problem
        for problem in problems
    )


def test_next_action_checker_rejects_extra_truthy_summary_authority_rule(
    tmp_path: Path,
) -> None:
    plan = tmp_path / "next_action.tsv"
    summary = tmp_path / "next_action.json"
    build_lockbox_next_action_plan(
        next_action_plan_path=plan,
        next_action_summary_path=summary,
    )
    payload = json.loads(summary.read_text(encoding="utf-8"))
    payload["authority_rules"]["may_change_workbook"] = True
    summary.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    problems = check_lockbox_next_action_plan(
        next_action_plan_path=plan,
        next_action_summary_path=summary,
    )

    assert any(
        "authority_rules.may_change_workbook must be false" in problem
        for problem in problems
    )


def test_next_action_checker_rejects_parked_flag_outside_oracle_negative(
    tmp_path: Path,
) -> None:
    plan = tmp_path / "next_action.tsv"
    summary = tmp_path / "next_action.json"
    build_lockbox_next_action_plan(
        next_action_plan_path=plan,
        next_action_summary_path=summary,
    )
    header, rows = _read_tsv_with_header(plan)
    second_review = next(
        row
        for row in rows
        if row["next_action"] == "ready_for_second_independent_review"
    )
    second_review["parked_for_broad_backfill"] = "TRUE"
    _write_tsv(plan, header, rows)

    problems = check_lockbox_next_action_plan(
        next_action_plan_path=plan,
        next_action_summary_path=summary,
    )

    assert any(
        "parked_for_broad_backfill is only allowed for oracle-negative rows"
        in problem
        for problem in problems
    )


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
