"""Build the Lockbox AI challenge review packet v1.

This packet lets an agent/subagent perform non-authoritative QA over the 72-case
lockbox. It is not a truth-label collection sheet, not reviewer slot 2, and not
ProductWriter input. Agent output may only flag cases for owner re-review or
artifact/route repair.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
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
from scripts.check_productization_state import artifact_sha256
from scripts.import_lockbox_labels import LABEL_LOG, STATIC_BUNDLE_INDEX
from xic_extractor.tabular_io import (
    read_tsv_required,
    read_tsv_with_header,
    render_delimited_rows,
    write_tsv,
)

ROOT = Path(__file__).resolve().parents[1]
OWNER_BOUNDARY_CONFIRMATION = (
    ROOT
    / "docs/superpowers/validation/lockbox_owner_boundary_confirmation_v1.json"
)
AI_CHALLENGE_QUEUE = (
    ROOT / "docs/superpowers/validation/lockbox_ai_challenge_queue_v1.tsv"
)
AI_CHALLENGE_TEMPLATE = (
    ROOT / "docs/superpowers/validation/lockbox_ai_challenge_template_v1.tsv"
)
AI_CHALLENGE_SUMMARY = (
    ROOT / "docs/superpowers/validation/lockbox_ai_challenge_summary_v1.json"
)
AI_CHALLENGE_RENDERED_OUTPUT_DIR = (
    ROOT
    / "local_validation_artifacts/externalized_superpowers_validation/"
    "lockbox_ai_challenge_v1"
)
AI_CHALLENGE_INDEX = AI_CHALLENGE_RENDERED_OUTPUT_DIR / "index.html"

SCHEMA_VERSION = "lockbox_ai_challenge_packet_v1"
SUMMARY_SCHEMA_VERSION = "lockbox_ai_challenge_summary_v1"
CHALLENGE_ROW_SCHEMA_VERSION = "lockbox_ai_challenge_result_v1"
NO_AUTHORITY = "FALSE"
YES = "TRUE"

QUEUE_HEADER = [
    "schema_version",
    "lockbox_case_id",
    "row_id",
    "family_id",
    "sample_id",
    "analyte",
    "source_stratum",
    "current_machine_decision",
    "next_action",
    "next_action_class",
    "plot_status",
    "evidence_status",
    "case_html_path",
    "review_plot_png_path",
    "plot_sha256",
    "gaussian_smoothing_method",
    "gaussian_window_points",
    "gaussian_review_boundary_start_rt",
    "gaussian_review_boundary_end_rt",
    "gaussian_review_apex_rt",
    "owner_peak_choice_label",
    "owner_area_label",
    "owner_boundary_label",
    "challenge_scope",
    "challenge_question",
    "allowed_agent_outputs",
    "source_artifacts",
    "source_hashes",
    "may_satisfy_reviewer_slot2",
    "may_feed_product_writer",
    "may_touch_matrix",
    "may_grant_product_authority",
    "broad_backfill_unparked",
]

TEMPLATE_HEADER = [
    "schema_version",
    "lockbox_case_id",
    "challenge_reviewer_id",
    "reviewed_at_utc",
    "challenge_result",
    "challenge_reason_code",
    "challenge_notes",
    "evidence_viewed",
    "source_hashes",
    "may_satisfy_reviewer_slot2",
    "may_feed_product_writer",
    "may_touch_matrix",
    "may_grant_product_authority",
    "broad_backfill_unparked",
]

BLANK_TEMPLATE_FIELDS = (
    "challenge_reviewer_id",
    "reviewed_at_utc",
    "challenge_result",
    "challenge_reason_code",
    "challenge_notes",
    "evidence_viewed",
)

AUTHORITY_FIELDS = (
    "may_satisfy_reviewer_slot2",
    "may_feed_product_writer",
    "may_touch_matrix",
    "may_grant_product_authority",
    "broad_backfill_unparked",
)


def build_lockbox_ai_challenge_pack(
    *,
    next_action_plan_path: Path = NEXT_ACTION_PLAN,
    next_action_summary_path: Path = NEXT_ACTION_SUMMARY,
    static_bundle_index_path: Path = STATIC_BUNDLE_INDEX,
    label_log_path: Path = LABEL_LOG,
    owner_boundary_confirmation_path: Path = OWNER_BOUNDARY_CONFIRMATION,
    ai_challenge_queue_path: Path = AI_CHALLENGE_QUEUE,
    ai_challenge_template_path: Path = AI_CHALLENGE_TEMPLATE,
    ai_challenge_summary_path: Path = AI_CHALLENGE_SUMMARY,
    ai_challenge_index_path: Path = AI_CHALLENGE_INDEX,
    write_outputs: bool = True,
) -> dict[str, object]:
    problems, action_rows, static_by_case, labels_by_case, owner_boundary = (
        _load_inputs(
            next_action_plan_path=next_action_plan_path,
            next_action_summary_path=next_action_summary_path,
            static_bundle_index_path=static_bundle_index_path,
            label_log_path=label_log_path,
            owner_boundary_confirmation_path=owner_boundary_confirmation_path,
        )
    )
    if problems:
        return {"problems": problems}

    queue_rows = [
        _queue_row(
            action_row,
            static_by_case[action_row["lockbox_case_id"]],
            labels_by_case[action_row["lockbox_case_id"]],
            next_action_plan_path=next_action_plan_path,
            static_bundle_index_path=static_bundle_index_path,
            label_log_path=label_log_path,
            owner_boundary_confirmation_path=owner_boundary_confirmation_path,
        )
        for action_row in sorted(action_rows, key=lambda row: row["lockbox_case_id"])
    ]
    template_rows = [_template_row(row) for row in queue_rows]
    index_html = _render_index_html(
        queue_rows,
        template_path=ai_challenge_template_path,
        index_path=ai_challenge_index_path,
    )
    summary = _summary_json(
        queue_rows,
        template_rows,
        index_html,
        owner_boundary,
        next_action_plan_path=next_action_plan_path,
        next_action_summary_path=next_action_summary_path,
        static_bundle_index_path=static_bundle_index_path,
        label_log_path=label_log_path,
        owner_boundary_confirmation_path=owner_boundary_confirmation_path,
        ai_challenge_queue_path=ai_challenge_queue_path,
        ai_challenge_template_path=ai_challenge_template_path,
        ai_challenge_index_path=ai_challenge_index_path,
    )

    if write_outputs:
        write_tsv(
            ai_challenge_queue_path,
            queue_rows,
            QUEUE_HEADER,
            extrasaction="raise",
            lineterminator="\n",
        )
        write_tsv(
            ai_challenge_template_path,
            template_rows,
            TEMPLATE_HEADER,
            extrasaction="raise",
            lineterminator="\n",
        )
        ai_challenge_index_path.parent.mkdir(parents=True, exist_ok=True)
        ai_challenge_index_path.write_text(index_html, encoding="utf-8")
        ai_challenge_summary_path.write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return {
        "problems": [],
        "queue_rows": queue_rows,
        "template_rows": template_rows,
        "index_html": index_html,
        "summary": summary,
    }


def check_lockbox_ai_challenge_pack(
    *,
    next_action_plan_path: Path = NEXT_ACTION_PLAN,
    next_action_summary_path: Path = NEXT_ACTION_SUMMARY,
    static_bundle_index_path: Path = STATIC_BUNDLE_INDEX,
    label_log_path: Path = LABEL_LOG,
    owner_boundary_confirmation_path: Path = OWNER_BOUNDARY_CONFIRMATION,
    ai_challenge_queue_path: Path = AI_CHALLENGE_QUEUE,
    ai_challenge_template_path: Path = AI_CHALLENGE_TEMPLATE,
    ai_challenge_summary_path: Path = AI_CHALLENGE_SUMMARY,
    ai_challenge_index_path: Path = AI_CHALLENGE_INDEX,
    require_rendered_local: bool = False,
) -> list[str]:
    problems = check_lockbox_next_action_plan(
        static_bundle_index_path=static_bundle_index_path,
        label_log_path=label_log_path,
        next_action_plan_path=next_action_plan_path,
        next_action_summary_path=next_action_summary_path,
    )
    result = build_lockbox_ai_challenge_pack(
        next_action_plan_path=next_action_plan_path,
        next_action_summary_path=next_action_summary_path,
        static_bundle_index_path=static_bundle_index_path,
        label_log_path=label_log_path,
        owner_boundary_confirmation_path=owner_boundary_confirmation_path,
        ai_challenge_queue_path=ai_challenge_queue_path,
        ai_challenge_template_path=ai_challenge_template_path,
        ai_challenge_summary_path=ai_challenge_summary_path,
        ai_challenge_index_path=ai_challenge_index_path,
        write_outputs=False,
    )
    problems.extend(result.get("problems", []))
    if problems:
        return problems

    _check_tsv(
        ai_challenge_queue_path,
        QUEUE_HEADER,
        result["queue_rows"],
        "AI challenge queue",
        _check_queue_contract,
        problems,
    )
    _check_tsv(
        ai_challenge_template_path,
        TEMPLATE_HEADER,
        result["template_rows"],
        "AI challenge template",
        _check_template_contract,
        problems,
    )
    if require_rendered_local:
        if not ai_challenge_index_path.exists():
            problems.append("AI challenge HTML index missing")
        else:
            actual_index = ai_challenge_index_path.read_text(encoding="utf-8")
            if actual_index != result["index_html"]:
                problems.append("AI challenge HTML index is stale")
            _check_index_links(actual_index, ai_challenge_index_path, problems)
    if not ai_challenge_summary_path.exists():
        problems.append("AI challenge summary JSON missing")
    else:
        actual_summary = json.loads(
            ai_challenge_summary_path.read_text(encoding="utf-8"),
        )
        if actual_summary != result["summary"]:
            problems.append("AI challenge summary JSON is stale")
        _check_summary_contract(actual_summary, problems)
    return problems


def _load_inputs(
    *,
    next_action_plan_path: Path,
    next_action_summary_path: Path,
    static_bundle_index_path: Path,
    label_log_path: Path,
    owner_boundary_confirmation_path: Path,
) -> tuple[
    list[str],
    list[dict[str, str]],
    dict[str, dict[str, str]],
    dict[str, dict[str, str]],
    dict[str, Any],
]:
    problems: list[str] = []
    action_rows = list(
        read_tsv_required(
            next_action_plan_path,
            required_columns=(
                "lockbox_case_id",
                "next_action",
                "next_action_class",
                "plot_status",
                "evidence_status",
                "may_feed_product_writer",
                "may_touch_matrix",
                "may_grant_product_authority",
            ),
        ),
    )
    static_rows = list(
        read_tsv_required(
            static_bundle_index_path,
            required_columns=(
                "lockbox_case_id",
                "case_html_path",
                "case_html_sha256",
                "review_plot_png_path",
                "plot_status",
                "plot_sha256",
                "gaussian_smoothing_method",
                "gaussian_window_points",
                "may_touch_matrix",
                "may_grant_product_authority",
            ),
        ),
    )
    label_rows = list(
        read_tsv_required(
            label_log_path,
            required_columns=(
                "lockbox_case_id",
                "reviewer_slot",
                "peak_choice_label",
                "area_label",
                "boundary_label",
                "label_grants_product_authority",
                "may_touch_matrix",
            ),
        ),
    )
    owner_boundary = _read_owner_boundary(
        owner_boundary_confirmation_path,
        problems,
    )
    _check_next_action_summary(next_action_summary_path, problems)
    static_by_case = _unique_by_case(static_rows, "static bundle", problems)
    labels_by_case = _owner_labels_by_case(label_rows, problems)
    action_cases = [row["lockbox_case_id"] for row in action_rows]
    if len(action_cases) != 72:
        problems.append("AI challenge packet expects 72 lockbox cases")
    if len(action_cases) != len(set(action_cases)):
        problems.append("next-action plan case IDs must be unique")
    if set(action_cases) != set(static_by_case):
        problems.append("next-action plan case IDs must match static bundle")
    if set(action_cases) != set(labels_by_case):
        problems.append("next-action plan case IDs must match owner label log")
    _check_input_authority(action_rows, static_rows, label_rows, problems)
    return problems, action_rows, static_by_case, labels_by_case, owner_boundary


def _read_owner_boundary(path: Path, problems: list[str]) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        problems.append(f"could not read owner boundary confirmation: {exc}")
        return {}
    except json.JSONDecodeError as exc:
        problems.append(f"invalid owner boundary confirmation JSON: {exc}")
        return {}
    if payload.get("schema_version") != "lockbox_owner_boundary_confirmation_v1":
        problems.append("owner boundary confirmation schema_version mismatch")
    scope = payload.get("scope", {})
    if scope.get("owner_assessed_plotted_gaussian15_cases") != 53:
        problems.append("owner boundary confirmation must record 53 assessed cases")
    if scope.get("not_assessable_or_excluded_cases") != 19:
        problems.append("owner boundary confirmation must record 19 excluded cases")
    review_boundary = payload.get("subagent_review_boundary", {})
    if review_boundary.get("may_satisfy_reviewer_slot_2") is not False:
        problems.append("owner boundary must forbid subagent reviewer slot 2")
    authority = payload.get("authority_rules", {})
    for key, value in authority.items():
        if key == "product_writer_consumption":
            if value != "forbidden":
                problems.append("owner boundary must forbid ProductWriter")
        elif value is not False:
            problems.append(f"owner boundary authority_rules.{key} must be false")
    artifacts = payload.get("source_artifacts", {})
    if isinstance(artifacts, Mapping):
        for key, value in artifacts.items():
            if key.endswith("_sha256"):
                continue
            expected = artifacts.get(f"{key}_sha256", "")
            if expected and artifact_sha256(_repo_path(str(value))) != expected:
                problems.append(f"owner boundary source_artifacts.{key} hash mismatch")
    return dict(payload)


def _check_next_action_summary(path: Path, problems: list[str]) -> None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        problems.append(f"could not read next-action summary: {exc}")
        return
    except json.JSONDecodeError as exc:
        problems.append(f"invalid next-action summary JSON: {exc}")
        return
    if payload.get("schema_version") != "lockbox_next_action_summary_v1":
        problems.append("next-action summary schema_version mismatch")


def _unique_by_case(
    rows: Sequence[dict[str, str]],
    label: str,
    problems: list[str],
) -> dict[str, dict[str, str]]:
    by_case: dict[str, dict[str, str]] = {}
    duplicates: list[str] = []
    for row in rows:
        case_id = row["lockbox_case_id"]
        if case_id in by_case:
            duplicates.append(case_id)
        by_case[case_id] = row
    if duplicates:
        problems.append(f"{label} case IDs must be unique: {', '.join(duplicates)}")
    return by_case


def _owner_labels_by_case(
    rows: Sequence[dict[str, str]],
    problems: list[str],
) -> dict[str, dict[str, str]]:
    owner_rows = [row for row in rows if row.get("reviewer_slot") == "1"]
    by_case = _unique_by_case(owner_rows, "owner label log", problems)
    for row in owner_rows:
        if row.get("label_grants_product_authority") != NO_AUTHORITY:
            problems.append(f"{row['lockbox_case_id']}: owner label grants authority")
        if row.get("may_touch_matrix") != NO_AUTHORITY:
            problems.append(f"{row['lockbox_case_id']}: owner label may touch matrix")
    return by_case


def _check_input_authority(
    action_rows: Sequence[Mapping[str, str]],
    static_rows: Sequence[Mapping[str, str]],
    label_rows: Sequence[Mapping[str, str]],
    problems: list[str],
) -> None:
    for row in action_rows:
        for field in (
            "may_feed_product_writer",
            "may_touch_matrix",
            "may_grant_product_authority",
        ):
            if row.get(field) != NO_AUTHORITY:
                problems.append(f"{row['lockbox_case_id']}: {field} must be FALSE")
    for row in static_rows:
        for field in ("may_touch_matrix", "may_grant_product_authority"):
            if row.get(field) != NO_AUTHORITY:
                problems.append(
                    f"{row['lockbox_case_id']}: static {field} must be FALSE",
                )
    for row in label_rows:
        if row.get("label_grants_product_authority") != NO_AUTHORITY:
            problems.append(f"{row['lockbox_case_id']}: label authority must be FALSE")
        if row.get("may_touch_matrix") != NO_AUTHORITY:
            problems.append(
                f"{row['lockbox_case_id']}: label matrix flag must be FALSE",
            )


def _queue_row(
    action_row: Mapping[str, str],
    static_row: Mapping[str, str],
    label_row: Mapping[str, str],
    *,
    next_action_plan_path: Path,
    static_bundle_index_path: Path,
    label_log_path: Path,
    owner_boundary_confirmation_path: Path,
) -> dict[str, str]:
    scope, question = _challenge_scope_and_question(action_row)
    return {
        "schema_version": SCHEMA_VERSION,
        "lockbox_case_id": action_row["lockbox_case_id"],
        "row_id": action_row.get("row_id", ""),
        "family_id": action_row.get("family_id", ""),
        "sample_id": action_row.get("sample_id", ""),
        "analyte": action_row.get("analyte", ""),
        "source_stratum": action_row.get("source_stratum", ""),
        "current_machine_decision": action_row.get("current_machine_decision", ""),
        "next_action": action_row.get("next_action", ""),
        "next_action_class": action_row.get("next_action_class", ""),
        "plot_status": action_row.get("plot_status", ""),
        "evidence_status": action_row.get("evidence_status", ""),
        "case_html_path": static_row.get("case_html_path", ""),
        "review_plot_png_path": static_row.get("review_plot_png_path", ""),
        "plot_sha256": static_row.get("plot_sha256", ""),
        "gaussian_smoothing_method": static_row.get("gaussian_smoothing_method", ""),
        "gaussian_window_points": static_row.get("gaussian_window_points", ""),
        "gaussian_review_boundary_start_rt": static_row.get(
            "gaussian_review_boundary_start_rt",
            "",
        ),
        "gaussian_review_boundary_end_rt": static_row.get(
            "gaussian_review_boundary_end_rt",
            "",
        ),
        "gaussian_review_apex_rt": static_row.get("gaussian_review_apex_rt", ""),
        "owner_peak_choice_label": label_row.get("peak_choice_label", ""),
        "owner_area_label": label_row.get("area_label", ""),
        "owner_boundary_label": label_row.get("boundary_label", ""),
        "challenge_scope": scope,
        "challenge_question": question,
        "allowed_agent_outputs": _allowed_agent_outputs(scope),
        "source_artifacts": (
            "docs/superpowers/validation/lockbox_next_action_plan_v1.tsv;"
            "docs/superpowers/validation/lockbox_static_review_v1/bundle_index.tsv;"
            "docs/superpowers/validation/lockbox_reviewer_label_log_v1.tsv;"
            "docs/superpowers/validation/lockbox_owner_boundary_confirmation_v1.json"
        ),
        "source_hashes": _source_hashes(
            static_row,
            next_action_plan_path=next_action_plan_path,
            static_bundle_index_path=static_bundle_index_path,
            label_log_path=label_log_path,
            owner_boundary_confirmation_path=owner_boundary_confirmation_path,
        ),
        "may_satisfy_reviewer_slot2": NO_AUTHORITY,
        "may_feed_product_writer": NO_AUTHORITY,
        "may_touch_matrix": NO_AUTHORITY,
        "may_grant_product_authority": NO_AUTHORITY,
        "broad_backfill_unparked": NO_AUTHORITY,
    }


def _challenge_scope_and_question(row: Mapping[str, str]) -> tuple[str, str]:
    action = row.get("next_action", "")
    if action == ACTION_READY_FOR_SECOND_REVIEW:
        return (
            "visual_contradiction_challenge",
            (
                "Check the linked Gaussian15 page for an obvious contradiction "
                "to the owner clean label. Do not assign a truth label; flag only "
                "if owner re-review is needed."
            ),
        )
    if action == ACTION_RECOVER_BOUNDARY:
        return (
            "evidence_gap_route_check",
            (
                "Confirm this case remains an evidence gap or boundary-unavailable "
                "route. Do not infer peak or area truth."
            ),
        )
    if action == ACTION_PARK_ORACLE_NEGATIVE:
        return (
            "parked_nontruth_route_check",
            (
                "Confirm this round-trip oracle negative remains parked as "
                "non-truth evidence and is not routed to writer authority."
            ),
        )
    if action == ACTION_EXISTING_MANUAL_NEGATIVE:
        return (
            "manual_negative_route_check",
            (
                "Confirm this case is only an existing manual negative-control "
                "route and is not being used as ProductWriter authority."
            ),
        )
    return (
        "route_integrity_check",
        "Check route integrity only; flag any mismatch for owner review.",
    )


def _allowed_agent_outputs(scope: str) -> str:
    common_outputs = (
        "no_issue",
        "flag_for_owner_recheck",
        "artifact_integrity_problem",
        "route_mismatch",
        "evidence_missing_or_unusable",
    )
    if scope == "visual_contradiction_challenge":
        return "|".join((*common_outputs, "visual_contradiction_suspected"))
    return "|".join(common_outputs)


def _template_row(queue_row: Mapping[str, str]) -> dict[str, str]:
    return {
        "schema_version": CHALLENGE_ROW_SCHEMA_VERSION,
        "lockbox_case_id": queue_row["lockbox_case_id"],
        "challenge_reviewer_id": "",
        "reviewed_at_utc": "",
        "challenge_result": "",
        "challenge_reason_code": "",
        "challenge_notes": "",
        "evidence_viewed": "",
        "source_hashes": queue_row["source_hashes"],
        "may_satisfy_reviewer_slot2": NO_AUTHORITY,
        "may_feed_product_writer": NO_AUTHORITY,
        "may_touch_matrix": NO_AUTHORITY,
        "may_grant_product_authority": NO_AUTHORITY,
        "broad_backfill_unparked": NO_AUTHORITY,
    }


def _summary_json(
    queue_rows: Sequence[Mapping[str, str]],
    template_rows: Sequence[Mapping[str, str]],
    index_html: str,
    owner_boundary: Mapping[str, Any],
    *,
    next_action_plan_path: Path,
    next_action_summary_path: Path,
    static_bundle_index_path: Path,
    label_log_path: Path,
    owner_boundary_confirmation_path: Path,
    ai_challenge_queue_path: Path,
    ai_challenge_template_path: Path,
    ai_challenge_index_path: Path,
) -> dict[str, Any]:
    scope_counts = Counter(row["challenge_scope"] for row in queue_rows)
    return {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "decision": "ai_challenge_packet_ready_for_72_cases",
        "decision_reasons": [
            "all 72 lockbox cases are represented for QA/challenge review",
            "53 plotted Gaussian15 cases may receive visual contradiction checks",
            "19 non-ready cases are route/evidence integrity checks only",
            "AI/subagent output cannot satisfy reviewer slot 2 or grant authority",
        ],
        "case_counts": {
            "total_cases": len(queue_rows),
            "challenge_template_rows": len(template_rows),
            "visual_contradiction_challenge_cases": scope_counts[
                "visual_contradiction_challenge"
            ],
            "route_or_evidence_integrity_cases": len(queue_rows)
            - scope_counts["visual_contradiction_challenge"],
            "product_authority_rows": 0,
        },
        "challenge_scope_counts": dict(sorted(scope_counts.items())),
        "authority_rules": {
            "ai_challenge_grants_truth_label": False,
            "may_satisfy_reviewer_slot2": False,
            "may_feed_product_writer": False,
            "may_touch_matrix": False,
            "may_grant_product_authority": False,
            "may_touch_workbook": False,
            "may_switch_selected_peak": False,
            "may_change_selected_area": False,
            "may_change_counted_detection": False,
            "may_change_default_extraction": False,
            "may_change_gui": False,
            "broad_backfill_unparked": False,
        },
        "owner_boundary_confirmation": {
            "path": _repo_relative(owner_boundary_confirmation_path),
            "sha256": artifact_sha256(owner_boundary_confirmation_path),
            "owner_assessed_plotted_gaussian15_cases": owner_boundary.get(
                "scope",
                {},
            ).get("owner_assessed_plotted_gaussian15_cases"),
            "not_assessable_or_excluded_cases": owner_boundary.get("scope", {}).get(
                "not_assessable_or_excluded_cases",
            ),
        },
        "source_artifacts": {
            "next_action_plan": _repo_relative(next_action_plan_path),
            "next_action_plan_sha256": artifact_sha256(next_action_plan_path),
            "next_action_summary": _repo_relative(next_action_summary_path),
            "next_action_summary_sha256": artifact_sha256(next_action_summary_path),
            "static_review_bundle_index": _repo_relative(static_bundle_index_path),
            "static_review_bundle_index_sha256": artifact_sha256(
                static_bundle_index_path,
            ),
            "label_log": _repo_relative(label_log_path),
            "label_log_sha256": artifact_sha256(label_log_path),
            "ai_challenge_queue": _repo_relative(ai_challenge_queue_path),
            "ai_challenge_queue_sha256": _rows_sha256(queue_rows, QUEUE_HEADER),
            "ai_challenge_template": _repo_relative(ai_challenge_template_path),
            "ai_challenge_template_sha256": _rows_sha256(
                template_rows,
                TEMPLATE_HEADER,
            ),
            "ai_challenge_index": _repo_relative(ai_challenge_index_path),
            "ai_challenge_index_sha256": _text_sha256(index_html),
        },
    }


def _render_index_html(
    queue_rows: Sequence[Mapping[str, str]],
    *,
    template_path: Path,
    index_path: Path,
) -> str:
    rows = "\n".join(
        _render_index_row(row, index_path=index_path) for row in queue_rows
    )
    template_href = html.escape(_relative_href(template_path, index_path))
    return (
        "<!doctype html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        "<title>Lockbox AI Challenge v1</title>\n"
        "<style>\n"
        "body{font-family:Arial,sans-serif;margin:24px;background:#f6f8fb;"
        "color:#111827}table{border-collapse:collapse;width:100%;background:white}"
        "th,td{border:1px solid #d1d5db;padding:8px;text-align:left;"
        "vertical-align:top}th{background:#e5e7eb}.warn{border-left:4px solid "
        "#b91c1c;background:#fff1f2;padding:10px;margin:14px 0}.small{font-size:"
        "12px;color:#4b5563}a{color:#075985}\n"
        "</style>\n"
        "</head>\n"
        "<body>\n"
        "<h1>Lockbox AI Challenge v1</h1>\n"
        '<div class="warn">Challenge QA only. Fill findings in '
        f'<a href="{template_href}">lockbox_ai_challenge_template_v1.tsv</a>. '
        "Do not enter truth labels, replacement values, reviewer-slot-2 labels, "
        "or ProductWriter/matrix authority.</div>\n"
        '<p class="small">For plotted cases, challenge only obvious visual '
        "contradictions against the owner-confirmed Gaussian15 boundary. For "
        "non-plotted cases, check route and evidence integrity only.</p>\n"
        "<table>\n"
        "<thead><tr><th>Case</th><th>Family / Sample</th><th>Route</th>"
        "<th>Scope</th><th>Owner label</th><th>Evidence</th></tr></thead>\n"
        "<tbody>\n"
        f"{rows}\n"
        "</tbody>\n"
        "</table>\n"
        "</body>\n"
        "</html>\n"
    )


def _render_index_row(row: Mapping[str, str], *, index_path: Path) -> str:
    case_link = _html_link(
        row["case_html_path"],
        row["lockbox_case_id"],
        index_path=index_path,
    )
    evidence = (
        _html_link(row["review_plot_png_path"], "plot", index_path=index_path)
        if row["review_plot_png_path"]
        else html.escape(row["plot_status"])
    )
    owner_label = (
        f"{row['owner_peak_choice_label']} / {row['owner_area_label']} / "
        f"{row['owner_boundary_label']}"
    )
    return (
        "<tr>"
        f"<td>{case_link}</td>"
        f"<td>{html.escape(row['family_id'])}<br>{html.escape(row['sample_id'])}</td>"
        f"<td>{html.escape(row['next_action'])}</td>"
        f"<td>{html.escape(row['challenge_scope'])}</td>"
        f"<td>{html.escape(owner_label)}</td>"
        f"<td>{evidence}</td>"
        "</tr>"
    )


def _check_tsv(
    path: Path,
    header: Sequence[str],
    expected_rows: object,
    label: str,
    row_checker: Any,
    problems: list[str],
) -> None:
    if not path.exists():
        problems.append(f"{label} TSV missing")
        return
    actual_header, rows = read_tsv_with_header(path)
    if list(actual_header) != list(header):
        problems.append(f"{label} header mismatch")
    if rows != expected_rows:
        problems.append(f"{label} is stale")
    row_checker(rows, problems)


def _check_queue_contract(
    rows: Sequence[Mapping[str, str]],
    problems: list[str],
) -> None:
    if len(rows) != 72:
        problems.append("AI challenge queue must contain 72 rows")
    scopes = Counter(row.get("challenge_scope", "") for row in rows)
    if scopes["visual_contradiction_challenge"] != 53:
        problems.append("AI challenge queue must contain 53 visual challenge rows")
    for index, row in enumerate(rows, start=2):
        if row.get("schema_version") != SCHEMA_VERSION:
            problems.append(f"AI challenge queue row {index}: invalid schema_version")
        allowed_outputs = row.get("allowed_agent_outputs", "").split("|")
        if row.get("challenge_scope") == "visual_contradiction_challenge":
            if row.get("plot_status") != "plotted_gaussian15":
                problems.append(
                    f"AI challenge queue row {index}: visual scope requires plot",
                )
            if row.get("gaussian_smoothing_method") != "gaussian_15":
                problems.append(
                    f"AI challenge queue row {index}: "
                    "visual scope requires gaussian_15",
                )
            if "visual_contradiction_suspected" not in allowed_outputs:
                problems.append(
                    f"AI challenge queue row {index}: "
                    "visual scope must allow visual_contradiction_suspected",
                )
        elif "visual_contradiction_suspected" in allowed_outputs:
            problems.append(
                f"AI challenge queue row {index}: "
                "route/evidence scope must not allow visual_contradiction_suspected",
            )
        for field in AUTHORITY_FIELDS:
            if row.get(field) != NO_AUTHORITY:
                problems.append(
                    f"AI challenge queue row {index}: {field} must be FALSE",
                )


def _check_template_contract(
    rows: Sequence[Mapping[str, str]],
    problems: list[str],
) -> None:
    if len(rows) != 72:
        problems.append("AI challenge template must contain 72 rows")
    for index, row in enumerate(rows, start=2):
        if row.get("schema_version") != CHALLENGE_ROW_SCHEMA_VERSION:
            problems.append(
                f"AI challenge template row {index}: invalid schema_version",
            )
        for field in BLANK_TEMPLATE_FIELDS:
            if row.get(field):
                problems.append(
                    f"AI challenge template row {index}: {field} must be blank",
                )
        for field in AUTHORITY_FIELDS:
            if row.get(field) != NO_AUTHORITY:
                problems.append(
                    f"AI challenge template row {index}: {field} must be FALSE",
                )


def _check_index_links(
    index_html: str,
    index_path: Path,
    problems: list[str],
) -> None:
    for href in _hrefs(index_html):
        if not (index_path.parent / href).resolve().exists():
            problems.append(f"AI challenge HTML link missing: {href}")


def _hrefs(index_html: str) -> list[str]:
    return [
        part.split('"', 1)[0]
        for part in index_html.split('href="')[1:]
        if '"' in part
    ]


def _check_summary_contract(
    summary: Mapping[str, Any],
    problems: list[str],
) -> None:
    if summary.get("schema_version") != SUMMARY_SCHEMA_VERSION:
        problems.append("AI challenge summary schema_version mismatch")
    if summary.get("decision") != "ai_challenge_packet_ready_for_72_cases":
        problems.append("AI challenge summary decision mismatch")
    counts = summary.get("case_counts", {})
    if counts.get("total_cases") != 72:
        problems.append("AI challenge summary total_cases must be 72")
    if counts.get("visual_contradiction_challenge_cases") != 53:
        problems.append("AI challenge summary visual cases must be 53")
    if counts.get("route_or_evidence_integrity_cases") != 19:
        problems.append("AI challenge summary route/evidence cases must be 19")
    if counts.get("product_authority_rows") != 0:
        problems.append("AI challenge summary product authority rows must be 0")
    authority = summary.get("authority_rules", {})
    if not isinstance(authority, Mapping):
        problems.append("AI challenge summary authority_rules must be an object")
        return
    for key, value in authority.items():
        if value is not False:
            problems.append(f"AI challenge summary authority_rules.{key} must be false")


def _source_hashes(
    static_row: Mapping[str, str],
    *,
    next_action_plan_path: Path,
    static_bundle_index_path: Path,
    label_log_path: Path,
    owner_boundary_confirmation_path: Path,
) -> str:
    parts = [
        f"lockbox_next_action_plan={artifact_sha256(next_action_plan_path)}",
        f"static_review_bundle_index={artifact_sha256(static_bundle_index_path)}",
        f"lockbox_reviewer_label_log={artifact_sha256(label_log_path)}",
        f"owner_boundary_confirmation={artifact_sha256(owner_boundary_confirmation_path)}",
        f"case_html={static_row.get('case_html_sha256', '')}",
    ]
    if static_row.get("review_plot_png_path"):
        parts.append(f"plot={static_row.get('plot_sha256', '')}")
    parts.append(static_row.get("source_artifact_hashes", ""))
    return ";".join(part for part in parts if part)


def _rows_sha256(rows: Sequence[Mapping[str, str]], header: Sequence[str]) -> str:
    rendered = render_delimited_rows(
        rows,
        header,
        delimiter="\t",
        extrasaction="raise",
        lineterminator="\n",
    )
    return _text_sha256(rendered)


def _text_sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest().upper()


def _html_link(path_value: str, label: str, *, index_path: Path) -> str:
    escaped_label = html.escape(label)
    escaped_href = html.escape(_relative_href(_repo_path(path_value), index_path))
    return f'<a href="{escaped_href}">{escaped_label}</a>'


def _repo_path(path_value: str) -> Path:
    path = Path(path_value)
    return path if path.is_absolute() else ROOT / path


def _relative_href(target_path: Path, index_path: Path) -> str:
    return os.path.relpath(
        target_path.resolve(),
        index_path.resolve().parent,
    ).replace("\\", "/")


def _repo_relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--next-action-plan", type=Path, default=NEXT_ACTION_PLAN)
    parser.add_argument("--next-action-summary", type=Path, default=NEXT_ACTION_SUMMARY)
    parser.add_argument("--static-bundle-index", type=Path, default=STATIC_BUNDLE_INDEX)
    parser.add_argument("--label-log", type=Path, default=LABEL_LOG)
    parser.add_argument(
        "--owner-boundary-confirmation",
        type=Path,
        default=OWNER_BOUNDARY_CONFIRMATION,
    )
    parser.add_argument("--ai-challenge-queue", type=Path, default=AI_CHALLENGE_QUEUE)
    parser.add_argument(
        "--ai-challenge-template",
        type=Path,
        default=AI_CHALLENGE_TEMPLATE,
    )
    parser.add_argument(
        "--ai-challenge-summary",
        type=Path,
        default=AI_CHALLENGE_SUMMARY,
    )
    parser.add_argument(
        "--rendered-output-dir",
        type=Path,
        default=AI_CHALLENGE_RENDERED_OUTPUT_DIR,
    )
    parser.add_argument("--ai-challenge-index", type=Path, default=None)
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--require-rendered-local", action="store_true")
    args = parser.parse_args(argv)
    ai_challenge_index = args.ai_challenge_index or (
        args.rendered_output_dir / "index.html"
    )

    if args.check_only:
        problems = check_lockbox_ai_challenge_pack(
            next_action_plan_path=args.next_action_plan,
            next_action_summary_path=args.next_action_summary,
            static_bundle_index_path=args.static_bundle_index,
            label_log_path=args.label_log,
            owner_boundary_confirmation_path=args.owner_boundary_confirmation,
            ai_challenge_queue_path=args.ai_challenge_queue,
            ai_challenge_template_path=args.ai_challenge_template,
            ai_challenge_summary_path=args.ai_challenge_summary,
            ai_challenge_index_path=ai_challenge_index,
            require_rendered_local=args.require_rendered_local,
        )
        if problems:
            for problem in problems:
                print(problem, file=sys.stderr)
            return 1
        print("Lockbox AI challenge packet is valid and non-authoritative.")
        return 0

    result = build_lockbox_ai_challenge_pack(
        next_action_plan_path=args.next_action_plan,
        next_action_summary_path=args.next_action_summary,
        static_bundle_index_path=args.static_bundle_index,
        label_log_path=args.label_log,
        owner_boundary_confirmation_path=args.owner_boundary_confirmation,
        ai_challenge_queue_path=args.ai_challenge_queue,
        ai_challenge_template_path=args.ai_challenge_template,
        ai_challenge_summary_path=args.ai_challenge_summary,
        ai_challenge_index_path=ai_challenge_index,
    )
    problems = result.get("problems", [])
    if problems:
        for problem in problems:
            print(problem, file=sys.stderr)
        return 1
    summary = result["summary"]
    print(
        "Built lockbox AI challenge packet: "
        f"{summary['case_counts']['total_cases']} cases, "
        f"decision={summary['decision']}.",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
