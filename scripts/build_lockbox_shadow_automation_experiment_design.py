"""Build the Lockbox shadow automation experiment design v1.

This is a read-only design packet. It turns the single-owner + AI-challenge
gate into a concrete shadow-only experiment manifest while keeping every case
non-authoritative. It does not implement scoring, call ProductWriter, mutate
matrix/workbook outputs, switch selected peaks, rewrite areas, change counted
detection, enable GUI/default extraction, or unpark broad Backfill.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from scripts.build_lockbox_next_action_plan import (
    ACTION_EXISTING_MANUAL_NEGATIVE,
    ACTION_PARK_ORACLE_NEGATIVE,
    ACTION_READY_FOR_SECOND_REVIEW,
    ACTION_RECOVER_BOUNDARY,
    NEXT_ACTION_PLAN,
    NEXT_ACTION_SUMMARY,
    check_lockbox_next_action_plan,
)
from scripts.build_lockbox_single_owner_ai_challenge_gate import (
    DECISION_SUPPORTS_SHADOW_EXPERIMENT,
    check_lockbox_single_owner_ai_challenge_gate,
)
from scripts.build_lockbox_single_owner_ai_challenge_gate import (
    GATE_SUMMARY as SINGLE_OWNER_GATE,
)
from xic_extractor.tabular_io import (
    file_sha256,
    read_tsv_with_header,
    render_delimited_rows,
    write_tsv,
)

ROOT = Path(__file__).resolve().parents[1]
SHADOW_EXPERIMENT_CASES = (
    ROOT / "docs/superpowers/validation/lockbox_shadow_automation_cases_v1.tsv"
)
SHADOW_EXPERIMENT_SUMMARY = (
    ROOT
    / "docs/superpowers/validation/lockbox_shadow_automation_experiment_v1.json"
)

SCHEMA_VERSION = "lockbox_shadow_automation_cases_v1"
SUMMARY_SCHEMA_VERSION = "lockbox_shadow_automation_experiment_v1"
DECISION_READY = "shadow_scoring_contract_adapter_v1_ready"
ALLOWED_NEXT_STEP = "define_production_acceptance_manifest_v1"
NO_AUTHORITY = "FALSE"
YES = "TRUE"

ROLE_OWNER_CLEAN = "owner_clean_positive_challenge"
ROLE_MANUAL_NEGATIVE = "manual_negative_control"
ROLE_EXCLUDED_ORACLE = "excluded_roundtrip_oracle_nontruth"
ROLE_EXCLUDED_BOUNDARY = "excluded_gaussian_boundary_unavailable"

SHADOW_DECISION_ACCEPT = "accept"
SHADOW_DECISION_FLAG = "flag"
SHADOW_DECISION_REJECT = "reject"
SHADOW_DECISION_NOT_SCORED = "not_scored"
SHADOW_DECISIONS = {
    SHADOW_DECISION_ACCEPT,
    SHADOW_DECISION_FLAG,
    SHADOW_DECISION_REJECT,
    SHADOW_DECISION_NOT_SCORED,
}

TRUTH_STATUS_NOT_TRUTH = "not_truth_claimed"
TRUTH_STATUS_MANUAL_NEGATIVE = "manual_negative"
TRUTH_STATUS_EXTERNAL_POSITIVE = "external_truth_positive"
TRUTH_STATUS_EXTERNAL_NEGATIVE = "external_truth_negative"
TRUTH_STATUS_UNRESOLVED = "unresolved"
TRUTH_STATUSES = {
    TRUTH_STATUS_NOT_TRUTH,
    TRUTH_STATUS_MANUAL_NEGATIVE,
    TRUTH_STATUS_EXTERNAL_POSITIVE,
    TRUTH_STATUS_EXTERNAL_NEGATIVE,
    TRUTH_STATUS_UNRESOLVED,
}

OWNER_CLEAN_CHALLENGE_NON_AUTHORITY = "non_authoritative_challenge"
OWNER_CLEAN_CHALLENGE_NOT_APPLICABLE = "not_applicable"

MANUAL_NEGATIVE_NONE = "not_manual_negative"
MANUAL_NEGATIVE_EXISTING = "existing_manual_negative_control"

DOUBLET_STATUS_NO_CLAIM = "no_doublet_claim"
DOUBLET_STATUS_NOT_EVALUATED = "not_evaluated"
DOUBLET_STATUS_RIGHT_BLOCKED = "right_reference_blocked"
DOUBLET_STATUS_UNCLEAR_BLOCKED = "unclear_reference_blocked"
DOUBLET_STATUS_UNRESOLVED_BLOCKED = "unresolved_blocked"
DOUBLET_STATUSES = {
    DOUBLET_STATUS_NO_CLAIM,
    DOUBLET_STATUS_NOT_EVALUATED,
    DOUBLET_STATUS_RIGHT_BLOCKED,
    DOUBLET_STATUS_UNCLEAR_BLOCKED,
    DOUBLET_STATUS_UNRESOLVED_BLOCKED,
}
DOUBLET_ACCEPT_BLOCKED_STATUSES = {
    DOUBLET_STATUS_RIGHT_BLOCKED,
    DOUBLET_STATUS_UNCLEAR_BLOCKED,
    DOUBLET_STATUS_UNRESOLVED_BLOCKED,
}
DOUBLET_REFERENCE_SIDES = {"left", "right", "unclear", "unresolved", "not_applicable"}
DOUBLET_ACCEPT_BLOCKED_REFERENCE_SIDES = {"right", "unclear", "unresolved"}
DOUBLET_SOURCE = "gaussian_boundary_policy_v1"

GAUSSIAN_BOUNDARY_POLICY = (
    "gaussian15_smoothed_boundary_is_review_basis; "
    "raw_doublet_accept_only_when_backfill_detect_reference_is_left_peak; "
    "unclear_or_right_peak_reference_stays_flagged"
)

CASES_HEADER = [
    "schema_version",
    "lockbox_case_id",
    "row_id",
    "family_id",
    "sample_id",
    "analyte",
    "source_stratum",
    "current_machine_decision",
    "plot_status",
    "evidence_status",
    "imported_peak_choice_labels",
    "imported_area_labels",
    "imported_boundary_labels",
    "next_action",
    "shadow_experiment_role",
    "included_in_shadow_experiment",
    "shadow_decision",
    "truth_status",
    "owner_clean_challenge_status",
    "manual_negative_status",
    "shadow_only",
    "write_authority",
    "matrix_write_allowed",
    "may_satisfy_reviewer_slot2",
    "single_owner_evidence_is_truth_completion",
    "doublet_status",
    "doublet_reference_side",
    "doublet_allowed",
    "doublet_source",
    "shadow_oracle_basis",
    "expected_shadow_behavior",
    "future_action_if_mismatch",
    "gaussian_boundary_policy",
    "future_expected_diff_requirement",
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
    "source_artifacts",
    "source_hashes",
]


def build_lockbox_shadow_automation_experiment_design(
    *,
    next_action_plan_path: Path = NEXT_ACTION_PLAN,
    next_action_summary_path: Path = NEXT_ACTION_SUMMARY,
    single_owner_gate_path: Path = SINGLE_OWNER_GATE,
    shadow_cases_path: Path = SHADOW_EXPERIMENT_CASES,
    shadow_summary_path: Path = SHADOW_EXPERIMENT_SUMMARY,
    write_outputs: bool = True,
) -> dict[str, object]:
    problems, next_action_rows, next_action_summary, single_owner_gate = _load_inputs(
        next_action_plan_path=next_action_plan_path,
        next_action_summary_path=next_action_summary_path,
        single_owner_gate_path=single_owner_gate_path,
    )
    if problems:
        return {"problems": problems}

    case_rows = [
        _shadow_case_row(
            row,
            next_action_plan_path=next_action_plan_path,
            single_owner_gate_path=single_owner_gate_path,
        )
        for row in sorted(next_action_rows, key=lambda item: item["lockbox_case_id"])
    ]
    summary = _summary_json(
        case_rows,
        next_action_summary,
        single_owner_gate,
        next_action_plan_path=next_action_plan_path,
        next_action_summary_path=next_action_summary_path,
        single_owner_gate_path=single_owner_gate_path,
        shadow_cases_path=shadow_cases_path,
    )
    if write_outputs:
        write_tsv(
            shadow_cases_path,
            case_rows,
            CASES_HEADER,
            extrasaction="raise",
            lineterminator="\n",
        )
        shadow_summary_path.write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return {"problems": [], "case_rows": case_rows, "summary": summary}


def check_lockbox_shadow_automation_experiment_design(
    *,
    next_action_plan_path: Path = NEXT_ACTION_PLAN,
    next_action_summary_path: Path = NEXT_ACTION_SUMMARY,
    single_owner_gate_path: Path = SINGLE_OWNER_GATE,
    shadow_cases_path: Path = SHADOW_EXPERIMENT_CASES,
    shadow_summary_path: Path = SHADOW_EXPERIMENT_SUMMARY,
) -> list[str]:
    result = build_lockbox_shadow_automation_experiment_design(
        next_action_plan_path=next_action_plan_path,
        next_action_summary_path=next_action_summary_path,
        single_owner_gate_path=single_owner_gate_path,
        shadow_cases_path=shadow_cases_path,
        shadow_summary_path=shadow_summary_path,
        write_outputs=False,
    )
    problems = list(result.get("problems", []))
    if problems:
        return problems

    expected_rows = result["case_rows"]
    expected_summary = result["summary"]
    if not shadow_cases_path.exists():
        problems.append("shadow automation case manifest missing")
    else:
        header, rows = read_tsv_with_header(shadow_cases_path)
        if list(header) != CASES_HEADER:
            problems.append("shadow automation case manifest header mismatch")
        if rows != expected_rows:
            problems.append("shadow automation case manifest is stale")
        _check_case_rows(rows, problems)
    if not shadow_summary_path.exists():
        problems.append("shadow automation summary missing")
    else:
        actual_summary = _read_json(
            shadow_summary_path,
            problems,
            "shadow automation summary",
        )
        if actual_summary != expected_summary:
            problems.append("shadow automation summary is stale")
        _check_summary(actual_summary, problems)
    return problems


def _load_inputs(
    *,
    next_action_plan_path: Path,
    next_action_summary_path: Path,
    single_owner_gate_path: Path,
) -> tuple[
    list[str],
    list[dict[str, str]],
    Mapping[str, Any],
    Mapping[str, Any],
]:
    problems: list[str] = []
    problems.extend(
        check_lockbox_next_action_plan(
            next_action_plan_path=next_action_plan_path,
            next_action_summary_path=next_action_summary_path,
        ),
    )
    problems.extend(
        check_lockbox_single_owner_ai_challenge_gate(
            gate_summary_path=single_owner_gate_path,
        ),
    )
    if problems:
        return problems, [], {}, {}
    try:
        header, next_action_rows = read_tsv_with_header(
            next_action_plan_path,
            required_columns=(
                "lockbox_case_id",
                "next_action",
                "source_stratum",
                "may_feed_product_writer",
                "may_touch_matrix",
                "may_grant_product_authority",
            ),
        )
    except (OSError, ValueError) as exc:
        problems.append(f"could not read next-action plan: {exc}")
        header = ()
        next_action_rows = []
    if list(header) and len(next_action_rows) != 72:
        problems.append("shadow automation design requires 72 next-action rows")
    next_action_summary = _read_json(
        next_action_summary_path,
        problems,
        "next-action summary",
    )
    single_owner_gate = _read_json(
        single_owner_gate_path,
        problems,
        "single-owner gate",
    )
    _check_input_summary(next_action_summary, single_owner_gate, problems)
    return problems, next_action_rows, next_action_summary, single_owner_gate


def _check_input_summary(
    next_action_summary: Mapping[str, Any],
    single_owner_gate: Mapping[str, Any],
    problems: list[str],
) -> None:
    if next_action_summary.get("schema_version") != "lockbox_next_action_summary_v1":
        problems.append("next-action summary schema_version mismatch")
    if next_action_summary.get("decision") != "second_review_ready_for_53_cases":
        problems.append("shadow automation design requires current next-action split")
    if single_owner_gate.get("schema_version") != (
        "lockbox_single_owner_ai_challenge_gate_v1"
    ):
        problems.append("single-owner gate schema_version mismatch")
    if single_owner_gate.get("decision") != DECISION_SUPPORTS_SHADOW_EXPERIMENT:
        problems.append("shadow automation design requires single-owner AI gate")
    if single_owner_gate.get("allowed_next_step") != (
        "shadow_automation_experiment_design_only"
    ):
        problems.append("single-owner gate must allow only shadow design")


def _read_json(path: Path, problems: list[str], label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        problems.append(f"could not read {label}: {exc}")
        return {}
    except json.JSONDecodeError as exc:
        problems.append(f"invalid {label} JSON: {exc}")
        return {}
    if not isinstance(payload, dict):
        problems.append(f"{label} must be a JSON object")
        return {}
    return payload


def _shadow_case_row(
    row: Mapping[str, str],
    *,
    next_action_plan_path: Path,
    single_owner_gate_path: Path,
) -> dict[str, str]:
    role, included, basis, expected, mismatch = _role_contract(row)
    row_contract = _shadow_row_contract(role)
    return {
        "schema_version": SCHEMA_VERSION,
        "lockbox_case_id": row["lockbox_case_id"],
        "row_id": row.get("row_id", ""),
        "family_id": row.get("family_id", ""),
        "sample_id": row.get("sample_id", ""),
        "analyte": row.get("analyte", ""),
        "source_stratum": row.get("source_stratum", ""),
        "current_machine_decision": row.get("current_machine_decision", ""),
        "plot_status": row.get("plot_status", ""),
        "evidence_status": row.get("evidence_status", ""),
        "imported_peak_choice_labels": row.get("imported_peak_choice_labels", ""),
        "imported_area_labels": row.get("imported_area_labels", ""),
        "imported_boundary_labels": row.get("imported_boundary_labels", ""),
        "next_action": row["next_action"],
        "shadow_experiment_role": role,
        "included_in_shadow_experiment": included,
        **row_contract,
        "shadow_oracle_basis": basis,
        "expected_shadow_behavior": expected,
        "future_action_if_mismatch": mismatch,
        "gaussian_boundary_policy": GAUSSIAN_BOUNDARY_POLICY,
        "future_expected_diff_requirement": (
            "required_before_any_product_writer_or_matrix_authority"
        ),
        "may_feed_product_writer": NO_AUTHORITY,
        "may_touch_matrix": NO_AUTHORITY,
        "may_grant_product_authority": NO_AUTHORITY,
        "may_change_workbook": NO_AUTHORITY,
        "may_switch_selected_peak": NO_AUTHORITY,
        "may_change_selected_area": NO_AUTHORITY,
        "may_change_counted_detection": NO_AUTHORITY,
        "may_change_default_extraction": NO_AUTHORITY,
        "may_change_gui": NO_AUTHORITY,
        "broad_backfill_unparked": NO_AUTHORITY,
        "source_artifacts": (
            f"{_repo_relative(next_action_plan_path)};"
            f"{_repo_relative(single_owner_gate_path)}"
        ),
        "source_hashes": (
            f"next_action_plan={file_sha256(next_action_plan_path)};"
            f"single_owner_gate={file_sha256(single_owner_gate_path)};"
            f"row_source_hashes={row.get('source_hashes', '')}"
        ),
    }


def _role_contract(row: Mapping[str, str]) -> tuple[str, str, str, str, str]:
    action = row["next_action"]
    if action == ACTION_READY_FOR_SECOND_REVIEW:
        return (
            ROLE_OWNER_CLEAN,
            YES,
            "single_owner_gaussian15_boundary_plus_ai_no_flag",
            "future_shadow_logic_should_keep_owner_clean_case_unflagged",
            "flag_for_owner_recheck_only",
        )
    if action == ACTION_EXISTING_MANUAL_NEGATIVE:
        return (
            ROLE_MANUAL_NEGATIVE,
            YES,
            "existing_manual_wrong_peak_or_no_peak_fixture",
            "future_shadow_logic_should_flag_or_reject_manual_negative_control",
            "investigate_false_accept_in_shadow_only",
        )
    if action == ACTION_PARK_ORACLE_NEGATIVE:
        return (
            ROLE_EXCLUDED_ORACLE,
            NO_AUTHORITY,
            "roundtrip_oracle_is_nontruth_and_excluded",
            "not_scored_in_shadow_experiment",
            "not_applicable",
        )
    if action == ACTION_RECOVER_BOUNDARY:
        return (
            ROLE_EXCLUDED_BOUNDARY,
            NO_AUTHORITY,
            "gaussian_boundary_unavailable",
            "not_scored_until_gaussian_boundary_is_recovered",
            "not_applicable",
        )
    raise ValueError(f"unexpected next_action for shadow design: {action}")


def _shadow_row_contract(role: str) -> dict[str, str]:
    base = {
        "shadow_only": YES,
        "write_authority": NO_AUTHORITY,
        "matrix_write_allowed": NO_AUTHORITY,
        "may_satisfy_reviewer_slot2": NO_AUTHORITY,
        "single_owner_evidence_is_truth_completion": NO_AUTHORITY,
        "doublet_source": DOUBLET_SOURCE,
    }
    if role == ROLE_OWNER_CLEAN:
        return {
            **base,
            "shadow_decision": SHADOW_DECISION_ACCEPT,
            "truth_status": TRUTH_STATUS_NOT_TRUTH,
            "owner_clean_challenge_status": OWNER_CLEAN_CHALLENGE_NON_AUTHORITY,
            "manual_negative_status": MANUAL_NEGATIVE_NONE,
            "doublet_status": DOUBLET_STATUS_NO_CLAIM,
            "doublet_reference_side": "not_applicable",
            "doublet_allowed": YES,
        }
    if role == ROLE_MANUAL_NEGATIVE:
        return {
            **base,
            "shadow_decision": SHADOW_DECISION_REJECT,
            "truth_status": TRUTH_STATUS_MANUAL_NEGATIVE,
            "owner_clean_challenge_status": OWNER_CLEAN_CHALLENGE_NOT_APPLICABLE,
            "manual_negative_status": MANUAL_NEGATIVE_EXISTING,
            "doublet_status": DOUBLET_STATUS_NO_CLAIM,
            "doublet_reference_side": "not_applicable",
            "doublet_allowed": NO_AUTHORITY,
        }
    if role == ROLE_EXCLUDED_ORACLE:
        return {
            **base,
            "shadow_decision": SHADOW_DECISION_NOT_SCORED,
            "truth_status": TRUTH_STATUS_NOT_TRUTH,
            "owner_clean_challenge_status": OWNER_CLEAN_CHALLENGE_NOT_APPLICABLE,
            "manual_negative_status": MANUAL_NEGATIVE_NONE,
            "doublet_status": DOUBLET_STATUS_NOT_EVALUATED,
            "doublet_reference_side": "not_applicable",
            "doublet_allowed": NO_AUTHORITY,
        }
    if role == ROLE_EXCLUDED_BOUNDARY:
        return {
            **base,
            "shadow_decision": SHADOW_DECISION_NOT_SCORED,
            "truth_status": TRUTH_STATUS_UNRESOLVED,
            "owner_clean_challenge_status": OWNER_CLEAN_CHALLENGE_NOT_APPLICABLE,
            "manual_negative_status": MANUAL_NEGATIVE_NONE,
            "doublet_status": DOUBLET_STATUS_NOT_EVALUATED,
            "doublet_reference_side": "not_applicable",
            "doublet_allowed": NO_AUTHORITY,
        }
    raise ValueError(f"unexpected shadow role: {role}")


def _summary_json(
    rows: Sequence[Mapping[str, str]],
    next_action_summary: Mapping[str, Any],
    single_owner_gate: Mapping[str, Any],
    *,
    next_action_plan_path: Path,
    next_action_summary_path: Path,
    single_owner_gate_path: Path,
    shadow_cases_path: Path,
) -> dict[str, Any]:
    role_counts = Counter(row["shadow_experiment_role"] for row in rows)
    included_count = sum(
        1 for row in rows if row["included_in_shadow_experiment"] == YES
    )
    product_authority_rows = sum(
        1
        for row in rows
        if row["may_feed_product_writer"] == YES
        or row["may_touch_matrix"] == YES
        or row["may_grant_product_authority"] == YES
        or row["write_authority"] == YES
        or row["matrix_write_allowed"] == YES
    )
    return {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "decision": DECISION_READY,
        "allowed_next_step": ALLOWED_NEXT_STEP,
        "decision_reasons": [
            (
                "53 owner-clean Gaussian15 cases may be used as positive "
                "challenge cases for a shadow-only contract adapter"
            ),
            (
                "6 existing manual wrong-peak/no-peak cases reject the shadow "
                "decision and hard-stop any accept drift"
            ),
            (
                "12 round-trip-oracle negative cases and 1 boundary-unavailable "
                "case remain not_scored in the shadow contract"
            ),
            (
                "single-owner plus AI challenge evidence is not product truth "
                "and cannot grant writer authority"
            ),
        ],
        "case_counts": {
            "total_manifest_rows": len(rows),
            "included_shadow_experiment_rows": included_count,
            "owner_clean_positive_challenge_cases": role_counts[ROLE_OWNER_CLEAN],
            "manual_negative_control_cases": role_counts[ROLE_MANUAL_NEGATIVE],
            "excluded_roundtrip_oracle_nontruth_cases": role_counts[
                ROLE_EXCLUDED_ORACLE
            ],
            "excluded_gaussian_boundary_unavailable_cases": role_counts[
                ROLE_EXCLUDED_BOUNDARY
            ],
            "product_authority_rows": product_authority_rows,
        },
        "contract_counts": {
            "shadow_decision": dict(
                sorted(Counter(row["shadow_decision"] for row in rows).items())
            ),
            "truth_status": dict(
                sorted(Counter(row["truth_status"] for row in rows).items())
            ),
            "doublet_status": dict(
                sorted(Counter(row["doublet_status"] for row in rows).items())
            ),
        },
        "upstream_decisions": {
            "next_action_summary": next_action_summary.get("decision", ""),
            "single_owner_ai_challenge_gate": single_owner_gate.get("decision", ""),
        },
        "shadow_experiment_contract": {
            "shadow_decisions": sorted(SHADOW_DECISIONS),
            "truth_statuses": sorted(TRUTH_STATUSES),
            "doublet_statuses": sorted(DOUBLET_STATUSES),
            "doublet_reference_sides": sorted(DOUBLET_REFERENCE_SIDES),
            "owner_clean_truth_status": TRUTH_STATUS_NOT_TRUTH,
            "owner_clean_challenge_status": OWNER_CLEAN_CHALLENGE_NON_AUTHORITY,
            "manual_negative_accept_hard_stop": True,
            "right_unclear_unresolved_doublet_accept_hard_stop": True,
            "gaussian_boundary_policy": GAUSSIAN_BOUNDARY_POLICY,
            "result_is_allowed_to_write": "shadow_scores_and_review_flags_only",
            "mismatch_handling": "route_to_review_only_not_product_writer",
            "promotion_requires": [
                "separate product goal",
                "masked_or_product_writer_oracle",
                "expected_diff_gate",
                "authority_manifest_update",
                "focused output tests",
            ],
        },
        "authority_rules": {
            "may_feed_product_writer": False,
            "may_touch_matrix": False,
            "may_grant_product_authority": False,
            "write_authority": False,
            "matrix_write_allowed": False,
            "may_change_workbook": False,
            "may_switch_selected_peak": False,
            "may_change_selected_area": False,
            "may_change_counted_detection": False,
            "may_change_default_extraction": False,
            "may_change_gui": False,
            "broad_backfill_unparked": False,
            "may_satisfy_reviewer_slot2": False,
            "single_owner_evidence_is_truth_completion": False,
            "manual_negative_controls_grant_write_authority": False,
            "round_trip_oracle_used_as_truth": False,
        },
        "output_rules": {
            "shadow_only": True,
            "write_authority": False,
            "matrix_write_allowed": False,
        },
        "source_artifacts": {
            "next_action_plan": _repo_relative(next_action_plan_path),
            "next_action_plan_sha256": file_sha256(next_action_plan_path),
            "next_action_summary": _repo_relative(next_action_summary_path),
            "next_action_summary_sha256": file_sha256(next_action_summary_path),
            "single_owner_gate": _repo_relative(single_owner_gate_path),
            "single_owner_gate_sha256": file_sha256(single_owner_gate_path),
            "source_case_manifest": _repo_relative(shadow_cases_path),
            "shadow_case_manifest_sha256": _rows_sha256(rows),
        },
    }


def _check_case_rows(
    rows: Sequence[Mapping[str, str]],
    problems: list[str],
) -> None:
    if len(rows) != 72:
        problems.append("shadow automation case manifest must cover 72 cases")
    role_counts = Counter(row.get("shadow_experiment_role", "") for row in rows)
    expected_counts = {
        ROLE_OWNER_CLEAN: 53,
        ROLE_MANUAL_NEGATIVE: 6,
        ROLE_EXCLUDED_ORACLE: 12,
        ROLE_EXCLUDED_BOUNDARY: 1,
    }
    if dict(role_counts) != expected_counts:
        problems.append("shadow automation role counts drifted")
    for row_number, row in enumerate(rows, start=2):
        for field in (
            "write_authority",
            "matrix_write_allowed",
            "may_satisfy_reviewer_slot2",
            "single_owner_evidence_is_truth_completion",
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
        ):
            if row.get(field) != NO_AUTHORITY:
                problems.append(f"shadow row {row_number}: {field} must be FALSE")
        role = row.get("shadow_experiment_role", "")
        included = row.get("included_in_shadow_experiment", "")
        shadow_decision = row.get("shadow_decision", "")
        truth_status = row.get("truth_status", "")
        doublet_status = row.get("doublet_status", "")
        doublet_reference_side = row.get("doublet_reference_side", "")
        if row.get("schema_version") != SCHEMA_VERSION:
            problems.append(f"shadow row {row_number}: schema_version mismatch")
        if row.get("shadow_only") != YES:
            problems.append(f"shadow row {row_number}: shadow_only must be TRUE")
        if shadow_decision not in SHADOW_DECISIONS:
            problems.append(f"shadow row {row_number}: invalid shadow_decision")
        if truth_status not in TRUTH_STATUSES:
            problems.append(f"shadow row {row_number}: invalid truth_status")
        if doublet_status not in DOUBLET_STATUSES:
            problems.append(f"shadow row {row_number}: invalid doublet_status")
        if doublet_reference_side not in DOUBLET_REFERENCE_SIDES:
            problems.append(
                f"shadow row {row_number}: invalid doublet_reference_side"
            )
        if not row.get("doublet_source"):
            problems.append(f"shadow row {row_number}: doublet_source is required")
        if not row.get("source_artifacts") or not row.get("source_hashes"):
            problems.append(f"shadow row {row_number}: source paths/hashes required")
        if "row_source_hashes=" not in row.get("source_hashes", ""):
            problems.append(f"shadow row {row_number}: row source hashes required")
        if shadow_decision == SHADOW_DECISION_ACCEPT and (
            row.get("write_authority") == YES
            or row.get("matrix_write_allowed") == YES
            or row.get("may_feed_product_writer") == YES
            or row.get("may_touch_matrix") == YES
            or row.get("may_grant_product_authority") == YES
        ):
            problems.append(
                f"shadow row {row_number}: accept cannot grant write authority"
            )
        if (
            shadow_decision == SHADOW_DECISION_ACCEPT
            and truth_status == TRUTH_STATUS_MANUAL_NEGATIVE
        ):
            problems.append(
                f"shadow row {row_number}: manual negative cannot be accepted"
            )
        if shadow_decision == SHADOW_DECISION_ACCEPT and (
            doublet_status in DOUBLET_ACCEPT_BLOCKED_STATUSES
            or doublet_reference_side in DOUBLET_ACCEPT_BLOCKED_REFERENCE_SIDES
            or row.get("doublet_allowed") != YES
        ):
            problems.append(
                f"shadow row {row_number}: doublet state cannot be accepted"
            )
        if role in {ROLE_OWNER_CLEAN, ROLE_MANUAL_NEGATIVE}:
            if included != YES:
                problems.append(f"shadow row {row_number}: included flag drifted")
        elif included != NO_AUTHORITY:
            problems.append(f"shadow row {row_number}: excluded row is included")
        if role == ROLE_OWNER_CLEAN:
            if truth_status != TRUTH_STATUS_NOT_TRUTH:
                problems.append(
                    f"shadow row {row_number}: owner-clean cannot claim truth"
                )
            if row.get("owner_clean_challenge_status") != (
                OWNER_CLEAN_CHALLENGE_NON_AUTHORITY
            ):
                problems.append(
                    f"shadow row {row_number}: owner-clean must be challenge only"
                )
        if role == ROLE_MANUAL_NEGATIVE:
            if truth_status != TRUTH_STATUS_MANUAL_NEGATIVE:
                problems.append(
                    f"shadow row {row_number}: manual negative status drifted"
                )
            if shadow_decision == SHADOW_DECISION_ACCEPT:
                problems.append(
                    f"shadow row {row_number}: manual negative accepted"
                )
        if role in {ROLE_EXCLUDED_ORACLE, ROLE_EXCLUDED_BOUNDARY} and (
            shadow_decision != SHADOW_DECISION_NOT_SCORED
        ):
            problems.append(f"shadow row {row_number}: excluded row must not score")


def _check_summary(summary: Mapping[str, Any], problems: list[str]) -> None:
    if summary.get("schema_version") != SUMMARY_SCHEMA_VERSION:
        problems.append("shadow automation summary schema_version mismatch")
    if summary.get("decision") != DECISION_READY:
        problems.append("shadow automation summary decision mismatch")
    if summary.get("allowed_next_step") != ALLOWED_NEXT_STEP:
        problems.append("shadow automation summary allowed_next_step mismatch")
    counts = summary.get("case_counts", {})
    if not isinstance(counts, Mapping):
        problems.append("shadow automation summary case_counts must be an object")
    elif counts.get("product_authority_rows") != 0:
        problems.append("shadow automation summary product authority must be 0")
    contract = summary.get("shadow_experiment_contract", {})
    if not isinstance(contract, Mapping):
        problems.append("shadow automation summary contract must be an object")
    else:
        if contract.get("gaussian_boundary_policy") != GAUSSIAN_BOUNDARY_POLICY:
            problems.append("shadow automation Gaussian boundary policy drifted")
        if contract.get("shadow_decisions") != sorted(SHADOW_DECISIONS):
            problems.append("shadow automation shadow_decisions drifted")
        if contract.get("truth_statuses") != sorted(TRUTH_STATUSES):
            problems.append("shadow automation truth_statuses drifted")
        if contract.get("owner_clean_truth_status") != TRUTH_STATUS_NOT_TRUTH:
            problems.append("shadow automation owner-clean truth drifted")
        if contract.get("manual_negative_accept_hard_stop") is not True:
            problems.append("shadow automation manual-negative hard stop drifted")
        doublet_hard_stop = contract.get(
            "right_unclear_unresolved_doublet_accept_hard_stop"
        )
        if doublet_hard_stop is not True:
            problems.append("shadow automation doublet hard stop drifted")
    outputs = summary.get("output_rules", {})
    if not isinstance(outputs, Mapping):
        problems.append("shadow automation summary output_rules must be an object")
    else:
        if outputs.get("shadow_only") is not True:
            problems.append("shadow automation output must be shadow_only")
        if outputs.get("write_authority") is not False:
            problems.append("shadow automation output grants write authority")
        if outputs.get("matrix_write_allowed") is not False:
            problems.append("shadow automation output allows matrix write")
    sources = summary.get("source_artifacts", {})
    if not isinstance(sources, Mapping):
        problems.append("shadow automation summary source_artifacts must be an object")
    else:
        if not sources.get("source_case_manifest"):
            problems.append("shadow automation source case manifest missing")
        manifest_hash = sources.get("shadow_case_manifest_sha256", "")
        if not isinstance(manifest_hash, str) or len(manifest_hash) != 64:
            problems.append("shadow automation manifest sha mismatch")
    authority = summary.get("authority_rules", {})
    if not isinstance(authority, Mapping):
        problems.append("shadow automation summary authority_rules must be an object")
        return
    for key, value in authority.items():
        if value is not False:
            problems.append(f"shadow automation summary authority_rules.{key} drifted")


def _rows_sha256(rows: Sequence[Mapping[str, str]]) -> str:
    rendered = render_delimited_rows(
        rows,
        CASES_HEADER,
        delimiter="\t",
        extrasaction="raise",
        lineterminator="\n",
    )
    return hashlib.sha256(rendered.encode("utf-8")).hexdigest().upper()


def _repo_relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--next-action-plan", type=Path, default=NEXT_ACTION_PLAN)
    parser.add_argument("--next-action-summary", type=Path, default=NEXT_ACTION_SUMMARY)
    parser.add_argument("--single-owner-gate", type=Path, default=SINGLE_OWNER_GATE)
    parser.add_argument("--shadow-cases", type=Path, default=SHADOW_EXPERIMENT_CASES)
    parser.add_argument(
        "--shadow-summary",
        type=Path,
        default=SHADOW_EXPERIMENT_SUMMARY,
    )
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args(argv)
    kwargs = {
        "next_action_plan_path": args.next_action_plan,
        "next_action_summary_path": args.next_action_summary,
        "single_owner_gate_path": args.single_owner_gate,
        "shadow_cases_path": args.shadow_cases,
        "shadow_summary_path": args.shadow_summary,
    }
    if args.check_only:
        problems = check_lockbox_shadow_automation_experiment_design(**kwargs)
        if problems:
            for problem in problems:
                print(problem, file=sys.stderr)
            return 1
        print("Lockbox shadow automation experiment design is valid.")
        return 0
    result = build_lockbox_shadow_automation_experiment_design(**kwargs)
    problems = result.get("problems", [])
    if problems:
        for problem in problems:
            print(problem, file=sys.stderr)
        return 1
    summary = result["summary"]
    print(
        "Built lockbox shadow automation experiment design: "
        f"{summary['case_counts']['included_shadow_experiment_rows']} "
        "included shadow rows, "
        f"decision={summary['decision']}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
