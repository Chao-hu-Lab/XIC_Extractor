"""Build the Lockbox second-review collection pack v1.

This packet takes only the cases already routed to
``ready_for_second_independent_review`` and creates a reviewer-slot-2 template
plus a small HTML index that links back to the existing Gaussian15 review plots.
It is collection infrastructure only: no ProductWriter, matrix, workbook,
selected peak, selected area, counted detection, default extraction, or broad
Backfill behavior changes.
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

from scripts.build_lockbox_label_collection_pack import (
    LABEL_SCHEMA_VERSION,
    LABEL_TEMPLATE_HEADER,
)
from scripts.build_lockbox_next_action_plan import (
    ACTION_READY_FOR_SECOND_REVIEW,
    NEXT_ACTION_PLAN,
    NEXT_ACTION_SUMMARY,
    check_lockbox_next_action_plan,
)
from scripts.check_lockbox_ai_challenge_results import (
    AI_CHALLENGE_RESULT_SUMMARY,
    DECISION_NO_OWNER_RECHECK,
    check_lockbox_ai_challenge_results,
)
from scripts.check_lockbox_ai_challenge_results import (
    SUMMARY_SCHEMA_VERSION as AI_CHALLENGE_RESULT_SUMMARY_SCHEMA_VERSION,
)
from scripts.import_lockbox_labels import LABEL_LOG, STATIC_BUNDLE_INDEX
from xic_extractor.tabular_io import (
    file_sha256,
    read_tsv_required,
    read_tsv_with_header,
    render_delimited_rows,
    write_tsv,
)

ROOT = Path(__file__).resolve().parents[1]
SECOND_REVIEW_QUEUE = (
    ROOT / "docs/superpowers/validation/lockbox_second_review_queue_v1.tsv"
)
SECOND_REVIEW_TEMPLATE = (
    ROOT / "docs/superpowers/validation/lockbox_second_review_template_v1.tsv"
)
SECOND_REVIEW_SUMMARY = (
    ROOT / "docs/superpowers/validation/lockbox_second_review_summary_v1.json"
)
SECOND_REVIEW_INDEX = (
    ROOT / "docs/superpowers/validation/lockbox_second_review_v1/index.html"
)

SCHEMA_VERSION = "lockbox_second_review_pack_v1"
SUMMARY_SCHEMA_VERSION = "lockbox_second_review_summary_v1"
NO_AUTHORITY = "FALSE"
YES = "TRUE"
SECOND_REVIEWER_SLOT = "2"

QUEUE_HEADER = [
    "schema_version",
    "lockbox_case_id",
    "row_id",
    "family_id",
    "sample_id",
    "analyte",
    "source_stratum",
    "current_machine_decision",
    "case_html_path",
    "review_plot_png_path",
    "plot_sha256",
    "gaussian_smoothing_method",
    "gaussian_window_points",
    "gaussian_review_boundary_start_rt",
    "gaussian_review_boundary_end_rt",
    "gaussian_review_apex_rt",
    "gaussian_review_area",
    "gaussian_review_area_source",
    "gaussian_review_boundary_source",
    "gaussian_review_segment_class",
    "first_reviewer_id",
    "first_peak_choice_label",
    "first_area_label",
    "first_boundary_label",
    "first_reviewer_confidence",
    "first_evidence_viewed",
    "second_reviewer_slot",
    "review_question",
    "reviewer_instruction",
    "source_artifacts",
    "source_hashes",
    "round_trip_oracle_can_be_truth",
    "may_feed_product_writer",
    "may_touch_matrix",
    "may_grant_product_authority",
    "broad_backfill_unparked",
]


def build_lockbox_second_review_pack(
    *,
    next_action_plan_path: Path = NEXT_ACTION_PLAN,
    next_action_summary_path: Path = NEXT_ACTION_SUMMARY,
    ai_challenge_result_summary_path: Path = AI_CHALLENGE_RESULT_SUMMARY,
    static_bundle_index_path: Path = STATIC_BUNDLE_INDEX,
    label_log_path: Path = LABEL_LOG,
    second_review_queue_path: Path = SECOND_REVIEW_QUEUE,
    second_review_template_path: Path = SECOND_REVIEW_TEMPLATE,
    second_review_summary_path: Path = SECOND_REVIEW_SUMMARY,
    second_review_index_path: Path = SECOND_REVIEW_INDEX,
    write_outputs: bool = True,
) -> dict[str, object]:
    problems, action_rows, static_by_case, labels_by_case = _load_inputs(
        next_action_plan_path=next_action_plan_path,
        next_action_summary_path=next_action_summary_path,
        ai_challenge_result_summary_path=ai_challenge_result_summary_path,
        static_bundle_index_path=static_bundle_index_path,
        label_log_path=label_log_path,
    )
    if problems:
        return {"problems": problems}

    ready_rows = [
        row
        for row in sorted(action_rows, key=lambda item: item["lockbox_case_id"])
        if row["next_action"] == ACTION_READY_FOR_SECOND_REVIEW
    ]
    queue_rows = [
        _queue_row(
            action_row,
            static_by_case[action_row["lockbox_case_id"]],
            labels_by_case[action_row["lockbox_case_id"]],
            next_action_plan_path=next_action_plan_path,
            static_bundle_index_path=static_bundle_index_path,
            label_log_path=label_log_path,
        )
        for action_row in ready_rows
    ]
    template_rows = [_template_row(row) for row in queue_rows]
    index_html = _render_index_html(
        queue_rows,
        template_path=second_review_template_path,
        index_path=second_review_index_path,
    )
    summary = _summary_json(
        action_rows,
        queue_rows,
        template_rows,
        index_html,
        next_action_plan_path=next_action_plan_path,
        next_action_summary_path=next_action_summary_path,
        ai_challenge_result_summary_path=ai_challenge_result_summary_path,
        static_bundle_index_path=static_bundle_index_path,
        label_log_path=label_log_path,
        second_review_queue_path=second_review_queue_path,
        second_review_template_path=second_review_template_path,
        second_review_index_path=second_review_index_path,
    )

    if write_outputs:
        write_tsv(
            second_review_queue_path,
            queue_rows,
            QUEUE_HEADER,
            extrasaction="raise",
            lineterminator="\n",
        )
        write_tsv(
            second_review_template_path,
            template_rows,
            LABEL_TEMPLATE_HEADER,
            extrasaction="raise",
            lineterminator="\n",
        )
        second_review_index_path.parent.mkdir(parents=True, exist_ok=True)
        second_review_index_path.write_text(index_html, encoding="utf-8")
        second_review_summary_path.write_text(
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


def check_lockbox_second_review_pack(
    *,
    next_action_plan_path: Path = NEXT_ACTION_PLAN,
    next_action_summary_path: Path = NEXT_ACTION_SUMMARY,
    ai_challenge_result_summary_path: Path = AI_CHALLENGE_RESULT_SUMMARY,
    static_bundle_index_path: Path = STATIC_BUNDLE_INDEX,
    label_log_path: Path = LABEL_LOG,
    second_review_queue_path: Path = SECOND_REVIEW_QUEUE,
    second_review_template_path: Path = SECOND_REVIEW_TEMPLATE,
    second_review_summary_path: Path = SECOND_REVIEW_SUMMARY,
    second_review_index_path: Path = SECOND_REVIEW_INDEX,
) -> list[str]:
    problems = check_lockbox_next_action_plan(
        static_bundle_index_path=static_bundle_index_path,
        label_log_path=label_log_path,
        next_action_plan_path=next_action_plan_path,
        next_action_summary_path=next_action_summary_path,
    )
    problems.extend(
        check_lockbox_ai_challenge_results(
            ai_challenge_result_summary_path=ai_challenge_result_summary_path,
        ),
    )
    result = build_lockbox_second_review_pack(
        next_action_plan_path=next_action_plan_path,
        next_action_summary_path=next_action_summary_path,
        ai_challenge_result_summary_path=ai_challenge_result_summary_path,
        static_bundle_index_path=static_bundle_index_path,
        label_log_path=label_log_path,
        second_review_queue_path=second_review_queue_path,
        second_review_template_path=second_review_template_path,
        second_review_summary_path=second_review_summary_path,
        second_review_index_path=second_review_index_path,
        write_outputs=False,
    )
    problems.extend(result.get("problems", []))
    if problems:
        return problems

    expected_queue = result["queue_rows"]
    expected_template = result["template_rows"]
    expected_summary = result["summary"]
    expected_index = result["index_html"]

    if not second_review_queue_path.exists():
        problems.append("lockbox second-review queue TSV missing")
    else:
        header, rows = read_tsv_with_header(second_review_queue_path)
        if list(header) != QUEUE_HEADER:
            problems.append("lockbox second-review queue header mismatch")
        if rows != expected_queue:
            problems.append("lockbox second-review queue is stale")
        _check_queue_contract(rows, problems)

    if not second_review_template_path.exists():
        problems.append("lockbox second-review template TSV missing")
    else:
        header, rows = read_tsv_with_header(second_review_template_path)
        if list(header) != LABEL_TEMPLATE_HEADER:
            problems.append("lockbox second-review template header mismatch")
        if rows != expected_template:
            problems.append("lockbox second-review template is stale")
        _check_template_contract(rows, problems)

    if not second_review_index_path.exists():
        problems.append("lockbox second-review HTML index missing")
    else:
        actual_index = second_review_index_path.read_text(encoding="utf-8")
        if actual_index != expected_index:
            problems.append("lockbox second-review HTML index is stale")

    if not second_review_summary_path.exists():
        problems.append("lockbox second-review summary JSON missing")
    else:
        actual_summary = json.loads(
            second_review_summary_path.read_text(encoding="utf-8"),
        )
        if actual_summary != expected_summary:
            problems.append("lockbox second-review summary JSON is stale")
        _check_summary_contract(actual_summary, problems)
    return problems


def _load_inputs(
    *,
    next_action_plan_path: Path,
    next_action_summary_path: Path,
    ai_challenge_result_summary_path: Path,
    static_bundle_index_path: Path,
    label_log_path: Path,
) -> tuple[
    list[str],
    list[dict[str, str]],
    dict[str, dict[str, str]],
    dict[str, dict[str, str]],
]:
    problems: list[str] = []
    action_rows = list(
        read_tsv_required(
            next_action_plan_path,
            required_columns=(
                "lockbox_case_id",
                "next_action",
                "plot_status",
                "imported_peak_choice_labels",
                "imported_area_labels",
                "imported_boundary_labels",
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
                "review_plot_png_path",
                "plot_status",
                "plot_sha256",
                "gaussian_smoothing_method",
                "gaussian_window_points",
                "source_artifact_hashes",
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
                "reviewer_id",
                "peak_choice_label",
                "area_label",
                "boundary_label",
                "reviewer_confidence",
                "evidence_viewed",
                "round_trip_oracle_used",
                "label_grants_product_authority",
                "may_touch_matrix",
            ),
        ),
    )
    try:
        next_action_summary = json.loads(
            next_action_summary_path.read_text(encoding="utf-8"),
        )
    except OSError as exc:
        problems.append(f"could not read next-action summary: {exc}")
        next_action_summary = {}
    except json.JSONDecodeError as exc:
        problems.append(f"invalid next-action summary JSON: {exc}")
        next_action_summary = {}
    try:
        ai_challenge_summary = json.loads(
            ai_challenge_result_summary_path.read_text(encoding="utf-8"),
        )
    except OSError as exc:
        problems.append(f"could not read AI challenge result summary: {exc}")
        ai_challenge_summary = {}
    except json.JSONDecodeError as exc:
        problems.append(f"invalid AI challenge result summary JSON: {exc}")
        ai_challenge_summary = {}

    static_by_case = _unique_by_case(static_rows, "static bundle", problems)
    labels_by_case = _unique_by_case(label_rows, "label log", problems)
    action_cases = [row["lockbox_case_id"] for row in action_rows]
    if len(action_cases) != len(set(action_cases)):
        problems.append("next-action plan case IDs must be unique")
    if set(action_cases) != set(static_by_case):
        problems.append("next-action plan case IDs must match static bundle")
    if set(action_cases) != set(labels_by_case):
        problems.append("next-action plan case IDs must match label log")
    if next_action_summary.get("schema_version") != "lockbox_next_action_summary_v1":
        problems.append("next-action summary schema_version mismatch")
    _check_ai_challenge_summary(ai_challenge_summary, problems)

    ready_rows = [
        row
        for row in action_rows
        if row["next_action"] == ACTION_READY_FOR_SECOND_REVIEW
    ]
    if len(ready_rows) != 53:
        problems.append(
            "second-review pack expects 53 ready_for_second_independent_review cases",
        )
    for row in ready_rows:
        _check_ready_action_row(row, problems)
        case_id = row["lockbox_case_id"]
        static_row = static_by_case.get(case_id)
        label_row = labels_by_case.get(case_id)
        if static_row:
            _check_ready_static_row(static_row, problems)
        if label_row:
            _check_ready_label_row(label_row, problems)
    return problems, action_rows, static_by_case, labels_by_case


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


def _check_ready_action_row(row: Mapping[str, str], problems: list[str]) -> None:
    case_id = row["lockbox_case_id"]
    if row.get("plot_status") != "plotted_gaussian15":
        problems.append(f"{case_id}: second-review case must be plotted_gaussian15")
    expected_labels = {
        "imported_peak_choice_labels": "correct",
        "imported_area_labels": "acceptable",
        "imported_boundary_labels": "acceptable",
        "needs_second_reviewer": YES,
    }
    for field, expected in expected_labels.items():
        if row.get(field) != expected:
            problems.append(f"{case_id}: {field} must be {expected}")
    for field in (
        "round_trip_oracle_can_be_truth",
        "may_feed_product_writer",
        "may_touch_matrix",
        "may_grant_product_authority",
        "parked_for_broad_backfill",
    ):
        if row.get(field) != NO_AUTHORITY:
            problems.append(f"{case_id}: {field} must be FALSE")


def _check_ready_static_row(row: Mapping[str, str], problems: list[str]) -> None:
    case_id = row["lockbox_case_id"]
    if row.get("plot_status") != "plotted_gaussian15":
        problems.append(f"{case_id}: static review plot must be plotted_gaussian15")
    if row.get("gaussian_smoothing_method") != "gaussian_15":
        problems.append(f"{case_id}: static review must use gaussian_15 smoothing")
    if row.get("gaussian_window_points") != "15":
        problems.append(f"{case_id}: static review must use 15-point smoothing")
    for field in ("case_html_path", "review_plot_png_path"):
        path_value = row.get(field, "")
        if not _repo_path(path_value).exists():
            problems.append(f"{case_id}: {field} missing on disk")
    plot_path = row.get("review_plot_png_path", "")
    expected_plot_hash = _hash_optional(plot_path)
    if row.get("plot_sha256") != expected_plot_hash:
        problems.append(f"{case_id}: plot_sha256 must match linked PNG")
    if row.get("may_touch_matrix") != NO_AUTHORITY:
        problems.append(f"{case_id}: static row may_touch_matrix must be FALSE")
    if row.get("may_grant_product_authority") != NO_AUTHORITY:
        problems.append(
            f"{case_id}: static row may_grant_product_authority must be FALSE",
        )


def _check_ready_label_row(row: Mapping[str, str], problems: list[str]) -> None:
    case_id = row["lockbox_case_id"]
    expected = {
        "reviewer_slot": "1",
        "peak_choice_label": "correct",
        "area_label": "acceptable",
        "boundary_label": "acceptable",
    }
    for field, value in expected.items():
        if row.get(field) != value:
            problems.append(f"{case_id}: first-review {field} must be {value}")
    for field in (
        "round_trip_oracle_used",
        "label_grants_product_authority",
        "may_touch_matrix",
    ):
        if row.get(field) != NO_AUTHORITY:
            problems.append(f"{case_id}: first-review {field} must be FALSE")


def _check_ai_challenge_summary(
    summary: Mapping[str, Any],
    problems: list[str],
) -> None:
    if summary.get("schema_version") != AI_CHALLENGE_RESULT_SUMMARY_SCHEMA_VERSION:
        problems.append("AI challenge result summary schema_version mismatch")
    if summary.get("decision") != DECISION_NO_OWNER_RECHECK:
        problems.append(
            "second-review pack requires AI challenge no-owner-recheck decision",
        )
    case_counts = summary.get("case_counts", {})
    if not isinstance(case_counts, Mapping):
        problems.append("AI challenge result summary case_counts must be an object")
    elif case_counts.get("flagged_cases") != 0:
        problems.append("second-review pack requires zero AI challenge flags")
    flagged_cases = summary.get("flagged_cases", [])
    if flagged_cases:
        problems.append("second-review pack requires empty AI flagged_cases")
    authority = summary.get("authority_rules", {})
    if not isinstance(authority, Mapping):
        problems.append("AI challenge result summary authority_rules must be an object")
        return
    for key, value in authority.items():
        if value is not False:
            problems.append(
                f"AI challenge result summary authority_rules.{key} must be false",
            )


def _queue_row(
    action_row: Mapping[str, str],
    static_row: Mapping[str, str],
    label_row: Mapping[str, str],
    *,
    next_action_plan_path: Path,
    static_bundle_index_path: Path,
    label_log_path: Path,
) -> dict[str, str]:
    source_hashes = _source_hashes(
        static_row,
        next_action_plan_path=next_action_plan_path,
        static_bundle_index_path=static_bundle_index_path,
        label_log_path=label_log_path,
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "lockbox_case_id": action_row["lockbox_case_id"],
        "row_id": action_row.get("row_id", ""),
        "family_id": action_row.get("family_id", ""),
        "sample_id": action_row.get("sample_id", ""),
        "analyte": action_row.get("analyte", ""),
        "source_stratum": action_row.get("source_stratum", ""),
        "current_machine_decision": action_row.get("current_machine_decision", ""),
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
        "gaussian_review_area": static_row.get("gaussian_review_area", ""),
        "gaussian_review_area_source": static_row.get(
            "gaussian_review_area_source",
            "",
        ),
        "gaussian_review_boundary_source": static_row.get(
            "gaussian_review_boundary_source",
            "",
        ),
        "gaussian_review_segment_class": static_row.get(
            "gaussian_review_segment_class",
            "",
        ),
        "first_reviewer_id": label_row.get("reviewer_id", ""),
        "first_peak_choice_label": label_row.get("peak_choice_label", ""),
        "first_area_label": label_row.get("area_label", ""),
        "first_boundary_label": label_row.get("boundary_label", ""),
        "first_reviewer_confidence": label_row.get("reviewer_confidence", ""),
        "first_evidence_viewed": label_row.get("evidence_viewed", ""),
        "second_reviewer_slot": SECOND_REVIEWER_SLOT,
        "review_question": (
            "Independently review the existing Gaussian15 overlay and label "
            "peak choice, area acceptability, and boundary quality."
        ),
        "reviewer_instruction": (
            "Use the Gaussian15 smoothed boundary shown in the linked static "
            "review page; do not enter replacement values and do not treat this "
            "review as ProductWriter authority."
        ),
        "source_artifacts": (
            "docs/superpowers/validation/lockbox_next_action_plan_v1.tsv;"
            "docs/superpowers/validation/lockbox_static_review_v1/bundle_index.tsv;"
            "docs/superpowers/validation/lockbox_reviewer_label_log_v1.tsv;"
            f"{static_row.get('case_html_path', '')};"
            f"{static_row.get('review_plot_png_path', '')}"
        ),
        "source_hashes": source_hashes,
        "round_trip_oracle_can_be_truth": NO_AUTHORITY,
        "may_feed_product_writer": NO_AUTHORITY,
        "may_touch_matrix": NO_AUTHORITY,
        "may_grant_product_authority": NO_AUTHORITY,
        "broad_backfill_unparked": NO_AUTHORITY,
    }


def _template_row(queue_row: Mapping[str, str]) -> dict[str, str]:
    return {
        "schema_version": LABEL_SCHEMA_VERSION,
        "lockbox_case_id": queue_row["lockbox_case_id"],
        "reviewer_slot": SECOND_REVIEWER_SLOT,
        "row_id": queue_row.get("row_id", ""),
        "family_id": queue_row.get("family_id", ""),
        "sample_id": queue_row.get("sample_id", ""),
        "analyte": queue_row.get("analyte", ""),
        "reviewer_id": "",
        "reviewed_at_utc": "",
        "peak_choice_label": "",
        "area_label": "",
        "boundary_label": "",
        "reviewer_confidence": "",
        "reviewer_reason_code": "",
        "reviewer_notes": "",
        "evidence_viewed": "",
        "source_artifact_hashes": queue_row["source_hashes"],
        "round_trip_oracle_used": NO_AUTHORITY,
        "label_grants_product_authority": NO_AUTHORITY,
        "may_touch_matrix": NO_AUTHORITY,
    }


def _summary_json(
    action_rows: Sequence[Mapping[str, str]],
    queue_rows: Sequence[Mapping[str, str]],
    template_rows: Sequence[Mapping[str, str]],
    index_html: str,
    *,
    next_action_plan_path: Path,
    next_action_summary_path: Path,
    ai_challenge_result_summary_path: Path,
    static_bundle_index_path: Path,
    label_log_path: Path,
    second_review_queue_path: Path,
    second_review_template_path: Path,
    second_review_index_path: Path,
) -> dict[str, Any]:
    action_counts = Counter(row["next_action"] for row in action_rows)
    product_authority_rows = sum(
        1
        for row in queue_rows
        if row["may_feed_product_writer"] == YES
        or row["may_touch_matrix"] == YES
        or row["may_grant_product_authority"] == YES
    )
    return {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "decision": f"second_review_collection_ready_for_{len(queue_rows)}_cases",
        "decision_reasons": [
            (
                f"{len(queue_rows)} plotted Gaussian15 cases were copied into "
                "a reviewer-slot-2 collection queue"
            ),
            "all label fields are blank; Codex did not invent second-review labels",
            (
                f"{len(action_rows) - len(queue_rows)} non-ready cases remain "
                "excluded from this collection pack"
            ),
            (
                "this packet grants no ProductWriter, matrix, workbook, "
                "selected-peak, selected-area, counted-detection, or broad "
                "Backfill authority"
            ),
        ],
        "source_artifacts": {
            "next_action_plan": _repo_relative(next_action_plan_path),
            "next_action_plan_sha256": file_sha256(next_action_plan_path),
            "next_action_summary": _repo_relative(next_action_summary_path),
            "next_action_summary_sha256": file_sha256(next_action_summary_path),
            "ai_challenge_result_summary": _repo_relative(
                ai_challenge_result_summary_path,
            ),
            "ai_challenge_result_summary_sha256": file_sha256(
                ai_challenge_result_summary_path,
            ),
            "static_review_bundle_index": _repo_relative(static_bundle_index_path),
            "static_review_bundle_index_sha256": file_sha256(
                static_bundle_index_path,
            ),
            "label_log": _repo_relative(label_log_path),
            "label_log_sha256": file_sha256(label_log_path),
            "second_review_queue": _repo_relative(second_review_queue_path),
            "second_review_queue_sha256": _rows_sha256(queue_rows, QUEUE_HEADER),
            "second_review_template": _repo_relative(second_review_template_path),
            "second_review_template_sha256": _rows_sha256(
                template_rows,
                LABEL_TEMPLATE_HEADER,
            ),
            "second_review_index": _repo_relative(second_review_index_path),
            "second_review_index_sha256": _text_sha256(index_html),
        },
        "upstream_ai_challenge_decision": DECISION_NO_OWNER_RECHECK,
        "ai_challenge_flagged_cases": 0,
        "authority_rules": {
            "labels_prefilled": False,
            "may_feed_product_writer": False,
            "may_touch_matrix": False,
            "may_grant_product_authority": False,
            "broad_backfill_unparked": False,
            "round_trip_oracle_used_as_truth": False,
        },
        "case_counts": {
            "total_next_action_cases": len(action_rows),
            "second_review_queue_cases": len(queue_rows),
            "second_review_template_rows": len(template_rows),
            "excluded_not_ready_for_second_review": len(action_rows) - len(queue_rows),
            "product_authority_rows": product_authority_rows,
        },
        "source_next_action_counts": dict(sorted(action_counts.items())),
        "review_contract": {
            "reviewer_slot": SECOND_REVIEWER_SLOT,
            "reviewer_scope": "second_independent_review_only",
            "expected_label_state": "blank_until_human_review",
            "boundary_basis": "existing_gaussian15_static_review_boundary",
            "output_effect": "truth_collection_only",
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
        "<title>Lockbox Second Review v1</title>\n"
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
        "<h1>Lockbox Second Review v1</h1>\n"
        '<div class="warn">Reviewer-slot-2 collection only. Fill labels in '
        f'<a href="{template_href}">lockbox_second_review_template_v1.tsv</a>. '
        "Do not enter replacement values; labels do not grant ProductWriter "
        "or matrix authority.</div>\n"
        '<p class="small">Review the linked Gaussian15 static pages. Boundary '
        "and area basis are the smoothed Gaussian15 traces already plotted in "
        "the static review bundle.</p>\n"
        "<table>\n"
        "<thead><tr><th>Case</th><th>Family / Sample</th><th>Stratum</th>"
        "<th>Gaussian15 boundary</th><th>First review</th><th>Evidence</th>"
        "</tr></thead>\n"
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
    plot_link = _html_link(row["review_plot_png_path"], "plot", index_path=index_path)
    boundary = (
        f"{row['gaussian_review_boundary_start_rt']} - "
        f"{row['gaussian_review_boundary_end_rt']} min; apex "
        f"{row['gaussian_review_apex_rt']} min"
    )
    first_review = (
        f"{row['first_peak_choice_label']} / {row['first_area_label']} / "
        f"{row['first_boundary_label']} ({row['first_reviewer_confidence']})"
    )
    return (
        "<tr>"
        f"<td>{case_link}</td>"
        f"<td>{html.escape(row['family_id'])}<br>{html.escape(row['sample_id'])}</td>"
        f"<td>{html.escape(row['source_stratum'])}</td>"
        f"<td>{html.escape(boundary)}</td>"
        f"<td>{html.escape(first_review)}</td>"
        f"<td>{plot_link}</td>"
        "</tr>"
    )


def _html_link(path_value: str, label: str, *, index_path: Path) -> str:
    escaped_label = html.escape(label)
    escaped_href = html.escape(_relative_href(_repo_path(path_value), index_path))
    return f'<a href="{escaped_href}">{escaped_label}</a>'


def _check_queue_contract(
    rows: Sequence[Mapping[str, str]],
    problems: list[str],
) -> None:
    for index, row in enumerate(rows, start=2):
        if row.get("schema_version") != SCHEMA_VERSION:
            problems.append(f"second-review queue row {index}: invalid schema_version")
        if row.get("second_reviewer_slot") != SECOND_REVIEWER_SLOT:
            problems.append(
                f"second-review queue row {index}: second_reviewer_slot must be 2",
            )
        if row.get("gaussian_smoothing_method") != "gaussian_15":
            problems.append(
                f"second-review queue row {index}: gaussian_smoothing_method "
                "must be gaussian_15",
            )
        if row.get("gaussian_window_points") != "15":
            problems.append(
                f"second-review queue row {index}: gaussian_window_points must be 15",
            )
        for field in (
            "round_trip_oracle_can_be_truth",
            "may_feed_product_writer",
            "may_touch_matrix",
            "may_grant_product_authority",
            "broad_backfill_unparked",
        ):
            if row.get(field) != NO_AUTHORITY:
                problems.append(
                    f"second-review queue row {index}: {field} must be FALSE",
                )


def _check_template_contract(
    rows: Sequence[Mapping[str, str]],
    problems: list[str],
) -> None:
    blank_fields = (
        "reviewer_id",
        "reviewed_at_utc",
        "peak_choice_label",
        "area_label",
        "boundary_label",
        "reviewer_confidence",
        "reviewer_reason_code",
        "reviewer_notes",
        "evidence_viewed",
    )
    for index, row in enumerate(rows, start=2):
        if row.get("schema_version") != LABEL_SCHEMA_VERSION:
            problems.append(
                f"second-review template row {index}: invalid schema_version",
            )
        if row.get("reviewer_slot") != SECOND_REVIEWER_SLOT:
            problems.append(
                f"second-review template row {index}: reviewer_slot must be 2",
            )
        for field in blank_fields:
            if row.get(field):
                problems.append(
                    f"second-review template row {index}: {field} must be blank",
                )
        for field in (
            "round_trip_oracle_used",
            "label_grants_product_authority",
            "may_touch_matrix",
        ):
            if row.get(field) != NO_AUTHORITY:
                problems.append(
                    f"second-review template row {index}: {field} must be FALSE",
                )


def _check_summary_contract(
    summary: Mapping[str, Any],
    problems: list[str],
) -> None:
    if summary.get("schema_version") != SUMMARY_SCHEMA_VERSION:
        problems.append("second-review summary schema_version mismatch")
    authority = summary.get("authority_rules")
    if not isinstance(authority, Mapping):
        problems.append("second-review summary authority_rules must be an object")
        return
    for key, value in authority.items():
        if value is not False:
            problems.append(
                f"second-review summary authority_rules.{key} must be false",
            )
    counts = summary.get("case_counts")
    if isinstance(counts, Mapping):
        if counts.get("product_authority_rows") != 0:
            problems.append("second-review summary product_authority_rows must be 0")


def _source_hashes(
    static_row: Mapping[str, str],
    *,
    next_action_plan_path: Path,
    static_bundle_index_path: Path,
    label_log_path: Path,
) -> str:
    parts = [
        f"lockbox_next_action_plan={file_sha256(next_action_plan_path)}",
        f"static_review_bundle_index={file_sha256(static_bundle_index_path)}",
        f"lockbox_reviewer_label_log={file_sha256(label_log_path)}",
        f"case_html={_hash_optional(static_row.get('case_html_path', ''))}",
        f"plot={_hash_optional(static_row.get('review_plot_png_path', ''))}",
        static_row.get("source_artifact_hashes", ""),
    ]
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


def _hash_optional(path_value: str) -> str:
    path = _repo_path(path_value)
    return file_sha256(path) if path.exists() else ""


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
    parser.add_argument(
        "--ai-challenge-result-summary",
        type=Path,
        default=AI_CHALLENGE_RESULT_SUMMARY,
    )
    parser.add_argument("--static-bundle-index", type=Path, default=STATIC_BUNDLE_INDEX)
    parser.add_argument("--label-log", type=Path, default=LABEL_LOG)
    parser.add_argument("--second-review-queue", type=Path, default=SECOND_REVIEW_QUEUE)
    parser.add_argument(
        "--second-review-template",
        type=Path,
        default=SECOND_REVIEW_TEMPLATE,
    )
    parser.add_argument(
        "--second-review-summary",
        type=Path,
        default=SECOND_REVIEW_SUMMARY,
    )
    parser.add_argument("--second-review-index", type=Path, default=SECOND_REVIEW_INDEX)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args(argv)

    if args.check_only:
        problems = check_lockbox_second_review_pack(
            next_action_plan_path=args.next_action_plan,
            next_action_summary_path=args.next_action_summary,
            ai_challenge_result_summary_path=args.ai_challenge_result_summary,
            static_bundle_index_path=args.static_bundle_index,
            label_log_path=args.label_log,
            second_review_queue_path=args.second_review_queue,
            second_review_template_path=args.second_review_template,
            second_review_summary_path=args.second_review_summary,
            second_review_index_path=args.second_review_index,
        )
        if problems:
            for problem in problems:
                print(problem, file=sys.stderr)
            return 1
        print("Lockbox second-review pack is valid and non-authoritative.")
        return 0

    result = build_lockbox_second_review_pack(
        next_action_plan_path=args.next_action_plan,
        next_action_summary_path=args.next_action_summary,
        ai_challenge_result_summary_path=args.ai_challenge_result_summary,
        static_bundle_index_path=args.static_bundle_index,
        label_log_path=args.label_log,
        second_review_queue_path=args.second_review_queue,
        second_review_template_path=args.second_review_template,
        second_review_summary_path=args.second_review_summary,
        second_review_index_path=args.second_review_index,
    )
    problems = result.get("problems", [])
    if problems:
        for problem in problems:
            print(problem, file=sys.stderr)
        return 1
    summary = result["summary"]
    print(
        "Built lockbox second-review pack: "
        f"{summary['case_counts']['second_review_queue_cases']} cases, "
        f"decision={summary['decision']}.",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
