"""Import Lockbox labels and build Truth Summary Gate v1.

This gate turns completed reviewer labels into a decision packet. It is
read-only with respect to product behavior: labels never grant ProductWriter
authority, never mutate matrix/workbook outputs, and never unpark broad
Backfill.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from scripts.build_lockbox_label_collection_pack import (
    LABEL_SCHEMA_VERSION,
    LABEL_TEMPLATE_HEADER,
)
from scripts.lockbox_reviewer_identity import (
    allowed_human_truth_reviewer_ids_from_schema,
    truth_label_reviewer_id_blocker,
)
from xic_extractor.tabular_io import (
    file_sha256,
    read_tsv_required,
    read_tsv_with_header,
    write_tsv,
)

ROOT = Path(__file__).resolve().parents[1]
STATIC_BUNDLE_INDEX = (
    ROOT / "docs/superpowers/validation/lockbox_static_review_v1/bundle_index.tsv"
)
LABEL_SCHEMA = ROOT / "docs/superpowers/specs/lockbox_label_schema_v1.json"
LABEL_LOG = ROOT / "docs/superpowers/validation/lockbox_reviewer_label_log_v1.tsv"
SUMMARY_JSON = ROOT / "docs/superpowers/validation/lockbox_truth_summary_v1.json"
CONFUSION_TABLE = (
    ROOT / "docs/superpowers/validation/lockbox_truth_confusion_table_v1.tsv"
)
FAILURE_MODES = ROOT / "docs/superpowers/validation/lockbox_failure_modes_v1.tsv"

TRUTH_SUMMARY_SCHEMA_VERSION = "lockbox_truth_summary_v1"
CONFUSION_SCHEMA_VERSION = "lockbox_truth_confusion_table_v1"
FAILURE_SCHEMA_VERSION = "lockbox_failure_modes_v1"
USER_BATCH_REVIEWER_ID = "user_batch_review_2026_06_18"
USER_BATCH_REVIEWED_AT_UTC = "2026-06-18T00:00:00Z"
NO_AUTHORITY = "FALSE"

CONFUSION_TABLE_HEADER = [
    "schema_version",
    "group_by",
    "group_value",
    "label_count",
    "peak_choice_correct",
    "peak_choice_wrong_peak",
    "peak_choice_wrong_family",
    "peak_choice_unresolved",
    "peak_choice_insufficient_evidence",
    "area_acceptable",
    "area_unacceptable",
    "area_not_assessable",
    "boundary_acceptable",
    "boundary_too_wide",
    "boundary_too_narrow",
    "boundary_shifted",
    "boundary_not_assessable",
    "reviewer_count",
    "may_grant_product_authority",
]

FAILURE_MODES_HEADER = [
    "schema_version",
    "failure_mode",
    "case_count",
    "example_lockbox_case_ids",
    "basis",
    "next_required_evidence",
    "may_grant_product_authority",
]


def build_user_batch_label_log(
    *,
    static_bundle_index_path: Path = STATIC_BUNDLE_INDEX,
    label_log_path: Path = LABEL_LOG,
) -> dict[str, object]:
    """Generate a one-reviewer label log from the 2026-06-18 user review."""

    static_rows = list(
        read_tsv_required(
            static_bundle_index_path,
            required_columns=(
                "lockbox_case_id",
                "case_html_sha256",
                "plot_status",
                "plot_sha256",
                "evidence_status",
                "source_artifact_hashes",
            ),
        ),
    )
    rows = [_user_batch_label_row(row, static_bundle_index_path) for row in static_rows]
    write_tsv(
        label_log_path,
        rows,
        LABEL_TEMPLATE_HEADER,
        extrasaction="raise",
        lineterminator="\n",
    )
    return {
        "label_log": label_log_path,
        "label_count": len(rows),
        "plotted_gaussian15": sum(
            1 for row in static_rows if row["plot_status"] == "plotted_gaussian15"
        ),
    }


def build_lockbox_truth_summary(
    *,
    label_log_path: Path = LABEL_LOG,
    static_bundle_index_path: Path = STATIC_BUNDLE_INDEX,
    summary_path: Path = SUMMARY_JSON,
    confusion_table_path: Path = CONFUSION_TABLE,
    failure_modes_path: Path = FAILURE_MODES,
    write_outputs: bool = True,
) -> dict[str, object]:
    problems, enriched_rows, static_rows = _load_and_validate_labels(
        label_log_path=label_log_path,
        static_bundle_index_path=static_bundle_index_path,
    )
    if problems:
        return {"problems": problems}

    summary = _summary_json(
        enriched_rows,
        static_rows,
        label_log_path=label_log_path,
        static_bundle_index_path=static_bundle_index_path,
        confusion_table_path=confusion_table_path,
        failure_modes_path=failure_modes_path,
    )
    confusion_rows = _confusion_table_rows(enriched_rows)
    failure_rows = _failure_mode_rows(enriched_rows)
    if write_outputs:
        summary_path.write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        write_tsv(
            confusion_table_path,
            confusion_rows,
            CONFUSION_TABLE_HEADER,
            extrasaction="raise",
            lineterminator="\n",
        )
        write_tsv(
            failure_modes_path,
            failure_rows,
            FAILURE_MODES_HEADER,
            extrasaction="raise",
            lineterminator="\n",
        )
    return {
        "problems": [],
        "summary": summary,
        "confusion_rows": confusion_rows,
        "failure_rows": failure_rows,
    }


def check_lockbox_truth_summary(
    *,
    label_log_path: Path = LABEL_LOG,
    static_bundle_index_path: Path = STATIC_BUNDLE_INDEX,
    summary_path: Path = SUMMARY_JSON,
    confusion_table_path: Path = CONFUSION_TABLE,
    failure_modes_path: Path = FAILURE_MODES,
) -> list[str]:
    result = build_lockbox_truth_summary(
        label_log_path=label_log_path,
        static_bundle_index_path=static_bundle_index_path,
        summary_path=summary_path,
        confusion_table_path=confusion_table_path,
        failure_modes_path=failure_modes_path,
        write_outputs=False,
    )
    problems = list(result.get("problems", []))
    if problems:
        return problems
    expected_summary = result["summary"]
    expected_confusion = result["confusion_rows"]
    expected_failures = result["failure_rows"]
    if not summary_path.exists():
        problems.append("truth summary JSON missing")
    else:
        actual_summary = json.loads(summary_path.read_text(encoding="utf-8"))
        if actual_summary != expected_summary:
            problems.append("truth summary JSON is stale")
    if not confusion_table_path.exists():
        problems.append("truth confusion table missing")
    else:
        header, rows = read_tsv_with_header(confusion_table_path)
        if list(header) != CONFUSION_TABLE_HEADER:
            problems.append("truth confusion table header mismatch")
        if rows != expected_confusion:
            problems.append("truth confusion table is stale")
    if not failure_modes_path.exists():
        problems.append("truth failure modes table missing")
    else:
        header, rows = read_tsv_with_header(failure_modes_path)
        if list(header) != FAILURE_MODES_HEADER:
            problems.append("truth failure modes header mismatch")
        if rows != expected_failures:
            problems.append("truth failure modes table is stale")
    return problems


def _user_batch_label_row(
    static_row: Mapping[str, str],
    static_bundle_index_path: Path,
) -> dict[str, str]:
    row = {field: "" for field in LABEL_TEMPLATE_HEADER}
    plotted = static_row["plot_status"] == "plotted_gaussian15"
    evidence_viewed = _evidence_viewed(static_row)
    if plotted:
        labels = {
            "peak_choice_label": "correct",
            "area_label": "acceptable",
            "boundary_label": "acceptable",
            "reviewer_confidence": "high",
            "reviewer_reason_code": "visual_trace_overlay_review",
            "reviewer_notes": (
                "User batch review 2026-06-18: available Gaussian15 static "
                "review plots were judged correct with well-defined "
                "Gaussian-derived boundaries; this label is review evidence "
                "only and grants no product authority."
            ),
        }
    else:
        labels = {
            "peak_choice_label": "insufficient_evidence",
            "area_label": "not_assessable",
            "boundary_label": "not_assessable",
            "reviewer_confidence": "high",
            "reviewer_reason_code": "insufficient_visual_evidence",
            "reviewer_notes": (
                "User batch review 2026-06-18: unavailable or unusable visual "
                "evidence could not be assessed; this remains an evidence gap "
                "and grants no product authority."
            ),
        }
    row.update(
        {
            "schema_version": LABEL_SCHEMA_VERSION,
            "lockbox_case_id": static_row["lockbox_case_id"],
            "reviewer_slot": "1",
            "row_id": static_row.get("row_id", ""),
            "family_id": static_row.get("family_id", ""),
            "sample_id": static_row.get("sample_id", ""),
            "analyte": static_row.get("analyte", ""),
            "reviewer_id": USER_BATCH_REVIEWER_ID,
            "reviewed_at_utc": USER_BATCH_REVIEWED_AT_UTC,
            "evidence_viewed": evidence_viewed,
            "source_artifact_hashes": _label_source_artifact_hashes(
                static_row,
                static_bundle_index_path,
            ),
            "round_trip_oracle_used": NO_AUTHORITY,
            "label_grants_product_authority": NO_AUTHORITY,
            "may_touch_matrix": NO_AUTHORITY,
        },
    )
    row.update(labels)
    return row


def _load_and_validate_labels(
    *,
    label_log_path: Path,
    static_bundle_index_path: Path,
) -> tuple[list[str], list[dict[str, str]], list[dict[str, str]]]:
    problems: list[str] = []
    schema = json.loads(LABEL_SCHEMA.read_text(encoding="utf-8"))
    static_rows = list(
        read_tsv_required(
            static_bundle_index_path,
            required_columns=("lockbox_case_id",),
        ),
    )
    static_by_case = {row["lockbox_case_id"]: row for row in static_rows}
    label_header, label_rows = read_tsv_with_header(label_log_path)
    if list(label_header) != LABEL_TEMPLATE_HEADER:
        problems.append("label log header must match lockbox label schema")
    if len(static_by_case) != len(static_rows):
        problems.append("static review bundle case IDs must be unique")
    label_cases = [row.get("lockbox_case_id", "") for row in label_rows]
    if set(label_cases) != set(static_by_case):
        problems.append("label log case IDs must match static bundle index")
    reviewers_by_case: dict[str, list[str]] = defaultdict(list)
    for row in label_rows:
        reviewers_by_case[row.get("lockbox_case_id", "")].append(
            row.get("reviewer_id", ""),
        )
    duplicate_reviewers = [
        case
        for case, reviewers in reviewers_by_case.items()
        if len(reviewers) != len(set(reviewers))
    ]
    if duplicate_reviewers:
        problems.append(
            "label log has duplicate reviewer_id per case: "
            + ", ".join(sorted(duplicate_reviewers)),
        )
    _validate_reviewer_slots(label_rows, problems)

    enum_fields = {
        "peak_choice_label": set(schema["allowed_peak_choice_labels"]),
        "area_label": set(schema["allowed_area_labels"]),
        "boundary_label": set(schema["allowed_boundary_labels"]),
        "reviewer_confidence": set(schema["allowed_reviewer_confidence"]),
        "reviewer_reason_code": set(schema["allowed_reviewer_reason_codes"]),
        "evidence_viewed": set(schema["allowed_evidence_viewed"]),
    }
    enriched_rows: list[dict[str, str]] = []
    for index, row in enumerate(label_rows, start=2):
        case_id = row.get("lockbox_case_id", "")
        static_row = static_by_case.get(case_id)
        _validate_label_row(
            row,
            static_row,
            static_bundle_index_path=static_bundle_index_path,
            enum_fields=enum_fields,
            allowed_human_truth_reviewer_ids=allowed_human_truth_reviewer_ids_from_schema(
                schema,
            ),
            row_number=index,
            problems=problems,
        )
        enriched = dict(row)
        if static_row:
            for field in (
                "plot_status",
                "evidence_status",
                "source_stratum",
                "current_machine_decision",
                "missing_evidence_reason",
            ):
                enriched[field] = static_row.get(field, "")
        enriched_rows.append(enriched)
    return problems, enriched_rows, static_rows


def _validate_reviewer_slots(
    rows: Sequence[Mapping[str, str]],
    problems: list[str],
) -> None:
    rows_by_case: dict[str, list[Mapping[str, str]]] = defaultdict(list)
    for row in rows:
        rows_by_case[row.get("lockbox_case_id", "")].append(row)
    for case_id, case_rows in rows_by_case.items():
        slots = [row.get("reviewer_slot", "") for row in case_rows]
        slot_set = set(slots)
        if len(case_rows) not in (1, 2):
            problems.append(f"{case_id}: label log must have one or two reviewer slots")
        if slot_set not in ({"1"}, {"1", "2"}):
            problems.append(f"{case_id}: reviewer slots must be 1 or 1..2")
        if len(slots) != len(slot_set):
            problems.append(f"{case_id}: reviewer slots must be distinct")


def _validate_label_row(
    row: Mapping[str, str],
    static_row: Mapping[str, str] | None,
    *,
    static_bundle_index_path: Path,
    enum_fields: Mapping[str, set[str]],
    allowed_human_truth_reviewer_ids: Sequence[str],
    row_number: int,
    problems: list[str],
) -> None:
    if row.get("schema_version") != LABEL_SCHEMA_VERSION:
        problems.append(f"label row {row_number}: invalid schema_version")
    for field in (
        "reviewer_id",
        "reviewed_at_utc",
        "peak_choice_label",
        "area_label",
        "boundary_label",
        "reviewer_confidence",
        "reviewer_reason_code",
        "evidence_viewed",
    ):
        if not row.get(field):
            problems.append(f"label row {row_number}: {field} is required")
    blocker = truth_label_reviewer_id_blocker(
        row.get("reviewer_id", ""),
        allowed_human_truth_reviewer_ids,
    )
    if blocker:
        problems.append(
            f"label row {row_number}: reviewer_id is not human truth: {blocker}",
        )
    for field, allowed in enum_fields.items():
        value = row.get(field, "")
        if value and value not in allowed:
            problems.append(f"label row {row_number}: invalid {field}")
    if row.get("round_trip_oracle_used") != NO_AUTHORITY:
        problems.append(f"label row {row_number}: round_trip_oracle_used must be FALSE")
    if row.get("label_grants_product_authority") != NO_AUTHORITY:
        problems.append(
            f"label row {row_number}: label_grants_product_authority must be FALSE",
        )
    if row.get("may_touch_matrix") != NO_AUTHORITY:
        problems.append(f"label row {row_number}: may_touch_matrix must be FALSE")
    if not static_row:
        problems.append(f"label row {row_number}: missing static review row")
        return
    for field in ("row_id", "family_id", "sample_id", "analyte"):
        if row.get(field, "") != static_row.get(field, ""):
            problems.append(f"label row {row_number}: {field} must match static bundle")
    expected_hashes = _label_source_artifact_hashes(
        static_row,
        static_bundle_index_path,
    )
    if row.get("source_artifact_hashes", "") != expected_hashes:
        problems.append(f"label row {row_number}: source_artifact_hashes mismatch")


def _summary_json(
    rows: Sequence[Mapping[str, str]],
    static_rows: Sequence[Mapping[str, str]],
    *,
    label_log_path: Path,
    static_bundle_index_path: Path,
    confusion_table_path: Path,
    failure_modes_path: Path,
) -> dict[str, Any]:
    peak_counts = Counter(row["peak_choice_label"] for row in rows)
    area_counts = Counter(row["area_label"] for row in rows)
    boundary_counts = Counter(row["boundary_label"] for row in rows)
    confidence_counts = Counter(row["reviewer_confidence"] for row in rows)
    plot_counts = Counter(row.get("plot_status", "") for row in rows)
    evidence_counts = Counter(row.get("evidence_status", "") for row in rows)
    assessable = [
        row for row in rows if row["peak_choice_label"] != "insufficient_evidence"
    ]
    decision, reasons = _gate_decision(rows)
    return {
        "schema_version": TRUTH_SUMMARY_SCHEMA_VERSION,
        "decision": decision,
        "decision_reasons": reasons,
        "source_artifacts": {
            "label_log": _repo_relative(label_log_path),
            "label_log_sha256": file_sha256(label_log_path),
            "static_review_bundle_index": _repo_relative(static_bundle_index_path),
            "static_review_bundle_index_sha256": file_sha256(
                static_bundle_index_path,
            ),
            "confusion_table": _repo_relative(confusion_table_path),
            "failure_modes": _repo_relative(failure_modes_path),
        },
        "authority_rules": {
            "labels_grant_product_authority": False,
            "may_touch_matrix": False,
            "product_writer_consumption": "forbidden",
            "broad_backfill_unparked": False,
            "round_trip_oracle_used_as_truth": False,
        },
        "case_counts": {
            "total_static_bundle_cases": len(static_rows),
            "labels_imported": len(rows),
            "assessable_labels": len(assessable),
            "insufficient_evidence_labels": peak_counts["insufficient_evidence"],
        },
        "plot_status_counts": dict(sorted(plot_counts.items())),
        "evidence_status_counts": dict(sorted(evidence_counts.items())),
        "peak_choice_counts": dict(sorted(peak_counts.items())),
        "area_counts": dict(sorted(area_counts.items())),
        "boundary_counts": dict(sorted(boundary_counts.items())),
        "reviewer_confidence_distribution": dict(sorted(confidence_counts.items())),
        "metrics": {
            "peak_choice_correct_rate_assessable": _rate(
                peak_counts["correct"],
                len(assessable),
            ),
            "peak_choice_correct_rate_all_cases": _rate(
                peak_counts["correct"],
                len(rows),
            ),
            "area_acceptable_rate_assessable": _rate(
                area_counts["acceptable"],
                len(assessable),
            ),
            "boundary_acceptable_rate_assessable": _rate(
                boundary_counts["acceptable"],
                len(assessable),
            ),
            "evidence_missing_or_unavailable_rate": _rate(
                peak_counts["insufficient_evidence"],
                len(rows),
            ),
        },
    }


def _gate_decision(rows: Sequence[Mapping[str, str]]) -> tuple[str, list[str]]:
    if not rows:
        return "truth_insufficient_collect_more_labels", ["no labels imported"]
    slots_by_case: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        slots_by_case[row["lockbox_case_id"]].add(row["reviewer_slot"])
    has_two_reviewers = all(slots == {"1", "2"} for slots in slots_by_case.values())
    insufficient = sum(
        1 for row in rows if row["peak_choice_label"] == "insufficient_evidence"
    )
    negative = sum(
        1
        for row in rows
        if row["peak_choice_label"] in {"wrong_peak", "wrong_family", "unresolved"}
        or row["area_label"] == "unacceptable"
        or row["boundary_label"] in {"too_wide", "too_narrow", "shifted"}
    )
    if has_two_reviewers and insufficient == 0 and negative == 0:
        return (
            "truth_supports_next_automation_experiment",
            [
                "all cases have two independent reviewer labels",
                "no insufficient evidence or negative labels were imported",
                (
                    "this still grants no write authority without a later "
                    "expected-diff goal"
                ),
            ],
        )
    return (
        "truth_supports_review_only",
        [
            "one reviewer batch confirms assessable Gaussian15 static plots",
            f"{insufficient} cases remain insufficient or not assessable",
            "two-reviewer lockbox completion and expected-diff are still missing",
        ],
    )


def _confusion_table_rows(
    rows: Sequence[Mapping[str, str]],
) -> list[dict[str, str]]:
    table_rows: list[dict[str, str]] = []
    for group_by in (
        "source_stratum",
        "current_machine_decision",
        "plot_status",
        "evidence_status",
    ):
        values = sorted({row.get(group_by, "") for row in rows})
        for value in values:
            grouped = [row for row in rows if row.get(group_by, "") == value]
            table_rows.append(_confusion_row(group_by, value, grouped))
    return table_rows


def _confusion_row(
    group_by: str,
    group_value: str,
    rows: Sequence[Mapping[str, str]],
) -> dict[str, str]:
    peak = Counter(row["peak_choice_label"] for row in rows)
    area = Counter(row["area_label"] for row in rows)
    boundary = Counter(row["boundary_label"] for row in rows)
    reviewers = {row["reviewer_id"] for row in rows if row.get("reviewer_id")}
    return {
        "schema_version": CONFUSION_SCHEMA_VERSION,
        "group_by": group_by,
        "group_value": group_value,
        "label_count": str(len(rows)),
        "peak_choice_correct": str(peak["correct"]),
        "peak_choice_wrong_peak": str(peak["wrong_peak"]),
        "peak_choice_wrong_family": str(peak["wrong_family"]),
        "peak_choice_unresolved": str(peak["unresolved"]),
        "peak_choice_insufficient_evidence": str(peak["insufficient_evidence"]),
        "area_acceptable": str(area["acceptable"]),
        "area_unacceptable": str(area["unacceptable"]),
        "area_not_assessable": str(area["not_assessable"]),
        "boundary_acceptable": str(boundary["acceptable"]),
        "boundary_too_wide": str(boundary["too_wide"]),
        "boundary_too_narrow": str(boundary["too_narrow"]),
        "boundary_shifted": str(boundary["shifted"]),
        "boundary_not_assessable": str(boundary["not_assessable"]),
        "reviewer_count": str(len(reviewers)),
        "may_grant_product_authority": NO_AUTHORITY,
    }


def _failure_mode_rows(
    rows: Sequence[Mapping[str, str]],
) -> list[dict[str, str]]:
    failure_rows: list[dict[str, str]] = []
    insufficient = [
        row for row in rows if row["peak_choice_label"] == "insufficient_evidence"
    ]
    missing = [
        row for row in rows if row.get("plot_status") == "missing_evidence_recorded"
    ]
    unavailable = [
        row
        for row in rows
        if row.get("plot_status") == "gaussian_review_boundary_unavailable"
    ]
    if insufficient:
        failure_rows.append(
            _failure_row(
                "insufficient_visual_evidence",
                insufficient,
                "reviewer could not assess peak choice, area, or boundary",
                "recover usable trace/overlay/hypothesis evidence before truth label",
            ),
        )
    if missing:
        failure_rows.append(
            _failure_row(
                "missing_overlay_or_trace_record",
                missing,
                "static review bundle records missing visual evidence",
                "recover overlay/trace/hypothesis artifacts",
            ),
        )
    if unavailable:
        failure_rows.append(
            _failure_row(
                "gaussian_boundary_unavailable",
                unavailable,
                "Gaussian15 trace could not produce a review boundary",
                "recover usable trace signal or mark case not assessable",
            ),
        )
    reviewers_by_case: dict[str, set[str]] = defaultdict(set)
    rows_by_case: dict[str, list[Mapping[str, str]]] = defaultdict(list)
    for row in rows:
        reviewers_by_case[row["lockbox_case_id"]].add(row.get("reviewer_id", ""))
        rows_by_case[row["lockbox_case_id"]].append(row)
    missing_second_reviewer = [
        rows_by_case[case][0]
        for case, reviewers in reviewers_by_case.items()
        if len(reviewers) < 2
    ]
    if missing_second_reviewer:
        failure_rows.append(
            _failure_row(
                "second_independent_reviewer_missing",
                missing_second_reviewer,
                "lockbox contract requires two reviewer slots per case",
                "collect second independent reviewer labels before automation gate",
            ),
        )
    return failure_rows


def _failure_row(
    failure_mode: str,
    rows: Sequence[Mapping[str, str]],
    basis: str,
    next_required_evidence: str,
) -> dict[str, str]:
    return {
        "schema_version": FAILURE_SCHEMA_VERSION,
        "failure_mode": failure_mode,
        "case_count": str(len(rows)),
        "example_lockbox_case_ids": ";".join(
            row["lockbox_case_id"] for row in rows[:5]
        ),
        "basis": basis,
        "next_required_evidence": next_required_evidence,
        "may_grant_product_authority": NO_AUTHORITY,
    }


def _evidence_viewed(static_row: Mapping[str, str]) -> str:
    if static_row["plot_status"] == "missing_evidence_recorded":
        return "packet_missing_evidence_record"
    if static_row.get("evidence_status") == "recovered_visual_evidence":
        return "packet_recovered_trace_overlay_hypothesis"
    return "packet_trace_overlay_hypothesis"


def _label_source_artifact_hashes(
    static_row: Mapping[str, str],
    static_bundle_index_path: Path,
) -> str:
    parts = [
        f"static_review_bundle_index={file_sha256(static_bundle_index_path)}",
        f"case_html={static_row.get('case_html_sha256', '')}",
        "plot="
        + (static_row.get("plot_sha256", "") or static_row.get("plot_status", "")),
        static_row.get("source_artifact_hashes", ""),
    ]
    return ";".join(part for part in parts if part)


def _repo_relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def _rate(numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return round(numerator / denominator, 6)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--static-bundle-index", type=Path, default=STATIC_BUNDLE_INDEX)
    parser.add_argument("--label-log", type=Path, default=LABEL_LOG)
    parser.add_argument("--summary", type=Path, default=SUMMARY_JSON)
    parser.add_argument("--confusion-table", type=Path, default=CONFUSION_TABLE)
    parser.add_argument("--failure-modes", type=Path, default=FAILURE_MODES)
    parser.add_argument(
        "--generate-user-batch-log",
        action="store_true",
        help="write the 2026-06-18 one-reviewer batch label log first",
    )
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args(argv)

    if args.generate_user_batch_log:
        build_user_batch_label_log(
            static_bundle_index_path=args.static_bundle_index,
            label_log_path=args.label_log,
        )
    if args.check_only:
        problems = check_lockbox_truth_summary(
            label_log_path=args.label_log,
            static_bundle_index_path=args.static_bundle_index,
            summary_path=args.summary,
            confusion_table_path=args.confusion_table,
            failure_modes_path=args.failure_modes,
        )
        if problems:
            for problem in problems:
                print(problem, file=sys.stderr)
            return 1
        print("Lockbox truth summary gate is valid and non-authoritative.")
        return 0
    result = build_lockbox_truth_summary(
        label_log_path=args.label_log,
        static_bundle_index_path=args.static_bundle_index,
        summary_path=args.summary,
        confusion_table_path=args.confusion_table,
        failure_modes_path=args.failure_modes,
    )
    problems = result.get("problems", [])
    if problems:
        for problem in problems:
            print(problem, file=sys.stderr)
        return 1
    summary = result["summary"]
    print(
        "Built lockbox truth summary gate: "
        f"{summary['case_counts']['labels_imported']} labels, "
        f"decision={summary['decision']}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
