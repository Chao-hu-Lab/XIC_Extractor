import json
from pathlib import Path

from scripts.build_lockbox_second_review_pack import SECOND_REVIEW_SUMMARY
from scripts.build_lockbox_single_owner_ai_challenge_gate import (
    GATE_SUMMARY,
    build_lockbox_single_owner_ai_challenge_gate,
    check_lockbox_single_owner_ai_challenge_gate,
)
from scripts.check_lockbox_ai_challenge_results import AI_CHALLENGE_RESULT_SUMMARY
from scripts.import_lockbox_labels import SUMMARY_JSON as TRUTH_SUMMARY


def test_current_single_owner_ai_challenge_gate_validates() -> None:
    assert check_lockbox_single_owner_ai_challenge_gate() == []


def test_current_single_owner_ai_challenge_gate_is_non_authoritative() -> None:
    summary = json.loads(GATE_SUMMARY.read_text(encoding="utf-8"))

    assert (
        summary["decision"]
        == "single_owner_ai_challenge_supports_shadow_automation_experiment"
    )
    assert summary["allowed_next_step"] == "shadow_automation_experiment_design_only"
    assert summary["case_counts"] == {
        "ai_challenge_flagged_cases": 0,
        "ai_challenge_total_cases": 72,
        "owner_assessable_clean_cases": 53,
        "owner_not_assessable_cases": 19,
        "product_authority_rows": 0,
        "second_review_collection_cases": 53,
        "total_lockbox_cases": 72,
    }
    assert summary["source_decisions"] == {
        "ai_challenge_result": "ai_challenge_no_owner_recheck_required",
        "second_review_summary": "second_review_collection_ready_for_53_cases",
        "truth_summary": "truth_supports_review_only",
    }
    assert summary["authority_rules"] == {
        "broad_backfill_unparked": False,
        "may_change_counted_detection": False,
        "may_change_default_extraction": False,
        "may_change_gui": False,
        "may_change_selected_area": False,
        "may_feed_product_writer": False,
        "may_grant_truth_completion": False,
        "may_satisfy_reviewer_slot2": False,
        "may_switch_selected_peak": False,
        "may_touch_matrix": False,
        "may_touch_workbook": False,
        "product_writer_consumption": "forbidden",
    }


def test_gate_rejects_open_ai_challenge_flag(tmp_path: Path) -> None:
    ai_summary = tmp_path / "ai_summary.json"
    payload = json.loads(AI_CHALLENGE_RESULT_SUMMARY.read_text(encoding="utf-8"))
    payload["decision"] = "ai_challenge_owner_recheck_required"
    payload["case_counts"]["flagged_cases"] = 1
    payload["flagged_cases"] = [{"lockbox_case_id": "LOCKBOXV1_TEST"}]
    ai_summary.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    result = build_lockbox_single_owner_ai_challenge_gate(
        ai_challenge_result_summary_path=ai_summary,
        gate_summary_path=tmp_path / "gate.json",
    )

    assert any(
        "AI challenge result summary JSON is stale" in problem
        for problem in result["problems"]
    )


def test_gate_rejects_truth_summary_promoted_to_automation(tmp_path: Path) -> None:
    truth_summary = tmp_path / "truth_summary.json"
    payload = json.loads(TRUTH_SUMMARY.read_text(encoding="utf-8"))
    payload["decision"] = "truth_supports_next_automation_experiment"
    truth_summary.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    result = build_lockbox_single_owner_ai_challenge_gate(
        truth_summary_path=truth_summary,
        gate_summary_path=tmp_path / "gate.json",
    )

    assert any(
        "truth summary JSON is stale" in problem for problem in result["problems"]
    )


def test_gate_rejects_stale_second_review_summary(tmp_path: Path) -> None:
    second_review = tmp_path / "second_review.json"
    payload = json.loads(SECOND_REVIEW_SUMMARY.read_text(encoding="utf-8"))
    payload["decision"] = "stale"
    second_review.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    result = build_lockbox_single_owner_ai_challenge_gate(
        second_review_summary_path=second_review,
        gate_summary_path=tmp_path / "gate.json",
    )

    assert any(
        "second-review summary JSON is stale" in problem
        for problem in result["problems"]
    )


def test_gate_rejects_owner_boundary_cycle(tmp_path: Path) -> None:
    owner_boundary = tmp_path / "owner_boundary.json"
    payload = json.loads(
        Path(
            "docs/superpowers/validation/lockbox_owner_boundary_confirmation_v1.json",
        ).read_text(encoding="utf-8"),
    )
    payload["source_artifacts"][
        "second_review_summary"
    ] = "docs/superpowers/validation/lockbox_second_review_summary_v1.json"
    owner_boundary.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    result = build_lockbox_single_owner_ai_challenge_gate(
        owner_boundary_confirmation_path=owner_boundary,
        gate_summary_path=tmp_path / "gate.json",
    )

    assert any(
        "must not hash downstream second review" in problem
        for problem in result["problems"]
    )


def test_gate_rejects_owner_boundary_hash_drift(tmp_path: Path) -> None:
    owner_boundary = tmp_path / "owner_boundary.json"
    payload = json.loads(
        Path(
            "docs/superpowers/validation/lockbox_owner_boundary_confirmation_v1.json",
        ).read_text(encoding="utf-8"),
    )
    payload["source_artifacts"]["label_log_sha256"] = "0" * 64
    owner_boundary.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    result = build_lockbox_single_owner_ai_challenge_gate(
        owner_boundary_confirmation_path=owner_boundary,
        gate_summary_path=tmp_path / "gate.json",
    )

    assert any(
        "owner-boundary source_artifacts.label_log hash mismatch" in problem
        for problem in result["problems"]
    )


def test_gate_checker_rejects_authority_drift(tmp_path: Path) -> None:
    gate = tmp_path / "gate.json"
    result = build_lockbox_single_owner_ai_challenge_gate(gate_summary_path=gate)
    assert result["problems"] == []
    payload = json.loads(gate.read_text(encoding="utf-8"))
    payload["authority_rules"]["may_feed_product_writer"] = True
    gate.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    problems = check_lockbox_single_owner_ai_challenge_gate(gate_summary_path=gate)

    assert any("single-owner AI challenge gate summary is stale" in p for p in problems)
    assert any(
        "authority_rules.may_feed_product_writer must be false" in p
        for p in problems
    )
