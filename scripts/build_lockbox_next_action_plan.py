"""Build the Lockbox next-action plan v1.

This packet routes the imported one-reviewer lockbox labels into the next
review/evidence actions. It is deliberately non-authoritative: no row may feed
ProductWriter, touch matrices, grant product authority, or unpark broad
Backfill.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from scripts.check_productization_state import artifact_sha256
from scripts.import_lockbox_labels import (
    LABEL_LOG,
    STATIC_BUNDLE_INDEX,
    SUMMARY_JSON,
    check_lockbox_truth_summary,
)
from xic_extractor.tabular_io import (
    read_tsv_required,
    read_tsv_with_header,
    render_delimited_rows,
    write_tsv,
)

ROOT = Path(__file__).resolve().parents[1]
NEXT_ACTION_PLAN = (
    ROOT / "docs/superpowers/validation/lockbox_next_action_plan_v1.tsv"
)
NEXT_ACTION_SUMMARY = (
    ROOT / "docs/superpowers/validation/lockbox_next_action_summary_v1.json"
)

SCHEMA_VERSION = "lockbox_next_action_plan_v1"
SUMMARY_SCHEMA_VERSION = "lockbox_next_action_summary_v1"
NO_AUTHORITY = "FALSE"
YES = "TRUE"

ACTION_READY_FOR_SECOND_REVIEW = "ready_for_second_independent_review"
ACTION_READY_FOR_AUTOMATION_GATE = "ready_for_truth_summary_gate"
ACTION_EXISTING_MANUAL_NEGATIVE = "use_existing_manual_negative_control"
ACTION_PARK_ORACLE_NEGATIVE = "park_roundtrip_oracle_negative_as_nontruth"
ACTION_RECOVER_BOUNDARY = "recover_or_mark_gaussian_boundary_unavailable"
ACTION_REVIEW_CONFLICT = "resolve_review_label_conflict"
ACTION_EVIDENCE_REQUIRED = "evidence_required_review_only"

NEXT_ACTION_PLAN_HEADER = [
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
    "reviewer_count",
    "imported_peak_choice_labels",
    "imported_area_labels",
    "imported_boundary_labels",
    "next_action",
    "next_action_class",
    "needs_second_reviewer",
    "needs_visual_evidence_recovery",
    "can_use_existing_manual_negative_control",
    "parked_for_broad_backfill",
    "round_trip_oracle_can_be_truth",
    "may_feed_product_writer",
    "may_touch_matrix",
    "may_grant_product_authority",
    "blocker_reason",
    "next_required_evidence",
    "source_artifacts",
    "source_hashes",
]


def build_lockbox_next_action_plan(
    *,
    static_bundle_index_path: Path = STATIC_BUNDLE_INDEX,
    label_log_path: Path = LABEL_LOG,
    truth_summary_path: Path = SUMMARY_JSON,
    next_action_plan_path: Path = NEXT_ACTION_PLAN,
    next_action_summary_path: Path = NEXT_ACTION_SUMMARY,
    write_outputs: bool = True,
) -> dict[str, object]:
    problems, static_rows, label_rows, truth_summary = _load_inputs(
        static_bundle_index_path=static_bundle_index_path,
        label_log_path=label_log_path,
        truth_summary_path=truth_summary_path,
    )
    if problems:
        return {"problems": problems}

    labels_by_case = _labels_by_case(label_rows)
    action_rows = [
        _next_action_row(row, labels_by_case.get(row["lockbox_case_id"], ()))
        for row in sorted(static_rows, key=lambda item: item["lockbox_case_id"])
    ]
    summary = _summary_json(
        action_rows,
        truth_summary,
        static_bundle_index_path=static_bundle_index_path,
        label_log_path=label_log_path,
        truth_summary_path=truth_summary_path,
        next_action_plan_path=next_action_plan_path,
    )
    if write_outputs:
        write_tsv(
            next_action_plan_path,
            action_rows,
            NEXT_ACTION_PLAN_HEADER,
            extrasaction="raise",
            lineterminator="\n",
        )
        next_action_summary_path.write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return {
        "problems": [],
        "action_rows": action_rows,
        "summary": summary,
    }


def check_lockbox_next_action_plan(
    *,
    static_bundle_index_path: Path = STATIC_BUNDLE_INDEX,
    label_log_path: Path = LABEL_LOG,
    truth_summary_path: Path = SUMMARY_JSON,
    next_action_plan_path: Path = NEXT_ACTION_PLAN,
    next_action_summary_path: Path = NEXT_ACTION_SUMMARY,
) -> list[str]:
    problems = check_lockbox_truth_summary(
        label_log_path=label_log_path,
        static_bundle_index_path=static_bundle_index_path,
        summary_path=truth_summary_path,
    )
    result = build_lockbox_next_action_plan(
        static_bundle_index_path=static_bundle_index_path,
        label_log_path=label_log_path,
        truth_summary_path=truth_summary_path,
        next_action_plan_path=next_action_plan_path,
        next_action_summary_path=next_action_summary_path,
        write_outputs=False,
    )
    problems.extend(result.get("problems", []))
    if problems:
        return problems

    expected_rows = result["action_rows"]
    expected_summary = result["summary"]
    if not next_action_plan_path.exists():
        problems.append("lockbox next action plan TSV missing")
    else:
        header, rows = read_tsv_with_header(next_action_plan_path)
        if list(header) != NEXT_ACTION_PLAN_HEADER:
            problems.append("lockbox next action plan header mismatch")
        if rows != expected_rows:
            problems.append("lockbox next action plan is stale")
        _check_no_authority(rows, problems)
    if not next_action_summary_path.exists():
        problems.append("lockbox next action summary JSON missing")
    else:
        actual_summary = json.loads(
            next_action_summary_path.read_text(encoding="utf-8"),
        )
        if actual_summary != expected_summary:
            problems.append("lockbox next action summary JSON is stale")
        _check_summary_authority_rules(actual_summary, problems)
    return problems


def _load_inputs(
    *,
    static_bundle_index_path: Path,
    label_log_path: Path,
    truth_summary_path: Path,
) -> tuple[
    list[str],
    list[dict[str, str]],
    list[dict[str, str]],
    Mapping[str, Any],
]:
    problems: list[str] = []
    static_rows = list(
        read_tsv_required(
            static_bundle_index_path,
            required_columns=(
                "lockbox_case_id",
                "source_stratum",
                "current_machine_decision",
                "plot_status",
                "evidence_status",
                "source_artifact_hashes",
                "may_touch_matrix",
                "may_grant_product_authority",
            ),
        ),
    )
    label_header, label_rows = read_tsv_with_header(
        label_log_path,
        required_columns=(
            "lockbox_case_id",
            "reviewer_id",
            "peak_choice_label",
            "area_label",
            "boundary_label",
            "label_grants_product_authority",
            "may_touch_matrix",
            "round_trip_oracle_used",
        ),
    )
    if not label_header:
        problems.append("lockbox label log header is empty")
    try:
        truth_summary = json.loads(truth_summary_path.read_text(encoding="utf-8"))
    except OSError as exc:
        problems.append(f"could not read truth summary: {exc}")
        truth_summary = {}
    except json.JSONDecodeError as exc:
        problems.append(f"invalid truth summary JSON: {exc}")
        truth_summary = {}
    _check_input_case_sets(static_rows, label_rows, problems)
    _check_input_authority(static_rows, label_rows, problems)
    if truth_summary.get("schema_version") != "lockbox_truth_summary_v1":
        problems.append("truth summary schema_version mismatch")
    if truth_summary.get("authority_rules", {}).get("product_writer_consumption") != (
        "forbidden"
    ):
        problems.append("truth summary must forbid ProductWriter consumption")
    return problems, static_rows, label_rows, truth_summary


def _check_input_case_sets(
    static_rows: Sequence[Mapping[str, str]],
    label_rows: Sequence[Mapping[str, str]],
    problems: list[str],
) -> None:
    static_cases = [row["lockbox_case_id"] for row in static_rows]
    label_cases = {row["lockbox_case_id"] for row in label_rows}
    if len(static_cases) != len(set(static_cases)):
        problems.append("static bundle case IDs must be unique")
    if set(static_cases) != label_cases:
        problems.append("label log case IDs must match static bundle case IDs")


def _check_input_authority(
    static_rows: Sequence[Mapping[str, str]],
    label_rows: Sequence[Mapping[str, str]],
    problems: list[str],
) -> None:
    for row_number, row in enumerate(static_rows, start=2):
        if row.get("may_touch_matrix") != NO_AUTHORITY:
            problems.append(f"static row {row_number}: may_touch_matrix must be FALSE")
        if row.get("may_grant_product_authority") != NO_AUTHORITY:
            problems.append(
                f"static row {row_number}: may_grant_product_authority must be FALSE",
            )
    for row_number, row in enumerate(label_rows, start=2):
        if row.get("label_grants_product_authority") != NO_AUTHORITY:
            problems.append(
                f"label row {row_number}: label_grants_product_authority must be FALSE",
            )
        if row.get("may_touch_matrix") != NO_AUTHORITY:
            problems.append(f"label row {row_number}: may_touch_matrix must be FALSE")
        if row.get("round_trip_oracle_used") != NO_AUTHORITY:
            problems.append(
                f"label row {row_number}: round_trip_oracle_used must be FALSE",
            )


def _labels_by_case(
    label_rows: Sequence[Mapping[str, str]],
) -> dict[str, tuple[Mapping[str, str], ...]]:
    grouped: dict[str, list[Mapping[str, str]]] = defaultdict(list)
    for row in label_rows:
        grouped[row["lockbox_case_id"]].append(row)
    return {case_id: tuple(rows) for case_id, rows in grouped.items()}


def _next_action_row(
    static_row: Mapping[str, str],
    label_rows: Sequence[Mapping[str, str]],
) -> dict[str, str]:
    labels = _label_summary(label_rows)
    action = _classify_action(static_row, labels)
    return {
        "schema_version": SCHEMA_VERSION,
        "lockbox_case_id": static_row["lockbox_case_id"],
        "row_id": static_row.get("row_id", ""),
        "family_id": static_row.get("family_id", ""),
        "sample_id": static_row.get("sample_id", ""),
        "analyte": static_row.get("analyte", ""),
        "source_stratum": static_row.get("source_stratum", ""),
        "current_machine_decision": static_row.get("current_machine_decision", ""),
        "plot_status": static_row.get("plot_status", ""),
        "evidence_status": static_row.get("evidence_status", ""),
        "reviewer_count": str(labels["reviewer_count"]),
        "imported_peak_choice_labels": labels["peak_choice_labels"],
        "imported_area_labels": labels["area_labels"],
        "imported_boundary_labels": labels["boundary_labels"],
        **action,
        "round_trip_oracle_can_be_truth": NO_AUTHORITY,
        "may_feed_product_writer": NO_AUTHORITY,
        "may_touch_matrix": NO_AUTHORITY,
        "may_grant_product_authority": NO_AUTHORITY,
        "source_artifacts": (
            "docs/superpowers/validation/lockbox_static_review_v1/bundle_index.tsv;"
            "docs/superpowers/validation/lockbox_reviewer_label_log_v1.tsv;"
            "docs/superpowers/validation/lockbox_truth_summary_v1.json"
        ),
        "source_hashes": static_row.get("source_artifact_hashes", ""),
    }


def _label_summary(label_rows: Sequence[Mapping[str, str]]) -> dict[str, object]:
    reviewers = {
        row.get("reviewer_id", "")
        for row in label_rows
        if row.get("reviewer_id")
    }
    peak = _unique_values(row.get("peak_choice_label", "") for row in label_rows)
    area = _unique_values(row.get("area_label", "") for row in label_rows)
    boundary = _unique_values(row.get("boundary_label", "") for row in label_rows)
    clean_count = sum(
        1
        for row in label_rows
        if row.get("peak_choice_label") == "correct"
        and row.get("area_label") == "acceptable"
        and row.get("boundary_label") == "acceptable"
    )
    conflict_count = sum(
        1
        for row in label_rows
        if row.get("peak_choice_label") in {"wrong_peak", "wrong_family", "unresolved"}
        or row.get("area_label") == "unacceptable"
        or row.get("boundary_label") in {"too_wide", "too_narrow", "shifted"}
    )
    insufficient_count = sum(
        1
        for row in label_rows
        if row.get("peak_choice_label") == "insufficient_evidence"
        or row.get("area_label") == "not_assessable"
        or row.get("boundary_label") == "not_assessable"
    )
    return {
        "reviewer_count": len(reviewers),
        "peak_choice_labels": ";".join(peak),
        "area_labels": ";".join(area),
        "boundary_labels": ";".join(boundary),
        "all_clean": bool(label_rows) and clean_count == len(label_rows),
        "has_conflict": conflict_count > 0,
        "has_insufficient": insufficient_count > 0,
    }


def _unique_values(values: Sequence[str] | Any) -> list[str]:
    return sorted({value for value in values if value})


def _classify_action(
    static_row: Mapping[str, str],
    labels: Mapping[str, object],
) -> dict[str, str]:
    source_stratum = static_row.get("source_stratum", "")
    plot_status = static_row.get("plot_status", "")
    all_clean = bool(labels["all_clean"])
    reviewer_count = int(labels["reviewer_count"])
    if source_stratum == "manual_wrong_peak_or_no_peak":
        return _action(
            next_action=ACTION_EXISTING_MANUAL_NEGATIVE,
            next_action_class="negative_control",
            can_use_existing_manual_negative_control=YES,
            blocker_reason=(
                "case is backed by the existing manual wrong-peak/no-peak fixture, "
                "not by current static overlay evidence"
            ),
            next_required_evidence=(
                "consume only as a manual negative-control fixture in a later "
                "truth-control contract; do not use it as matrix write authority"
            ),
        )
    if source_stratum == "failed_oracle_negative":
        return _action(
            next_action=ACTION_PARK_ORACLE_NEGATIVE,
            next_action_class="parked_nontruth",
            parked_for_broad_backfill=YES,
            blocker_reason=(
                "round-trip oracle negative evidence is not independent peak-choice "
                "or area truth"
            ),
            next_required_evidence=(
                "collect independent trace/overlay review or keep parked; do not "
                "derive ProductWriter rules from this oracle-negative class"
            ),
        )
    if plot_status == "gaussian_review_boundary_unavailable":
        return _action(
            next_action=ACTION_RECOVER_BOUNDARY,
            next_action_class="evidence_gap",
            needs_visual_evidence_recovery=YES,
            blocker_reason="trace exists but Gaussian15 review boundary is unavailable",
            next_required_evidence=(
                "recover usable signal/overlay evidence or leave the case "
                "not_assessable; do not send it to automation"
            ),
        )
    if bool(labels["has_conflict"]):
        return _action(
            next_action=ACTION_REVIEW_CONFLICT,
            next_action_class="review_conflict",
            needs_second_reviewer=YES,
            blocker_reason=(
                "imported reviewer labels contain negative or conflicting evidence"
            ),
            next_required_evidence=(
                "resolve with independent review; any later automation gate must "
                "preserve the disagreement record"
            ),
        )
    if plot_status == "plotted_gaussian15" and all_clean and reviewer_count >= 2:
        return _action(
            next_action=ACTION_READY_FOR_AUTOMATION_GATE,
            next_action_class="truth_summary_gate",
            blocker_reason="two clean reviewer labels exist for the plotted case",
            next_required_evidence=(
                "eligible only for a later masked/product-writer oracle plus "
                "expected-diff goal; still no current write authority"
            ),
        )
    if plot_status == "plotted_gaussian15" and all_clean:
        return _action(
            next_action=ACTION_READY_FOR_SECOND_REVIEW,
            next_action_class="second_review",
            needs_second_reviewer=YES,
            blocker_reason=(
                "one clean reviewer label exists; "
                "second independent reviewer is missing"
            ),
            next_required_evidence=(
                "collect a second independent label over the same Gaussian15 "
                "review boundary before any automation experiment"
            ),
        )
    return _action(
        next_action=ACTION_EVIDENCE_REQUIRED,
        next_action_class="evidence_gap",
        needs_visual_evidence_recovery=(
            YES if bool(labels["has_insufficient"]) else NO_AUTHORITY
        ),
        blocker_reason="case lacks assessable clean visual truth labels",
        next_required_evidence=(
            "recover visual evidence or collect structured reviewer labels; no "
            "writer authority is implied"
        ),
    )


def _action(
    *,
    next_action: str,
    next_action_class: str,
    needs_second_reviewer: str = NO_AUTHORITY,
    needs_visual_evidence_recovery: str = NO_AUTHORITY,
    can_use_existing_manual_negative_control: str = NO_AUTHORITY,
    parked_for_broad_backfill: str = NO_AUTHORITY,
    blocker_reason: str,
    next_required_evidence: str,
) -> dict[str, str]:
    return {
        "next_action": next_action,
        "next_action_class": next_action_class,
        "needs_second_reviewer": needs_second_reviewer,
        "needs_visual_evidence_recovery": needs_visual_evidence_recovery,
        "can_use_existing_manual_negative_control": (
            can_use_existing_manual_negative_control
        ),
        "parked_for_broad_backfill": parked_for_broad_backfill,
        "blocker_reason": blocker_reason,
        "next_required_evidence": next_required_evidence,
    }


def _summary_json(
    action_rows: Sequence[Mapping[str, str]],
    truth_summary: Mapping[str, Any],
    *,
    static_bundle_index_path: Path,
    label_log_path: Path,
    truth_summary_path: Path,
    next_action_plan_path: Path,
) -> dict[str, Any]:
    action_counts = Counter(row["next_action"] for row in action_rows)
    class_counts = Counter(row["next_action_class"] for row in action_rows)
    second_review_count = action_counts[ACTION_READY_FOR_SECOND_REVIEW]
    manual_negative_count = action_counts[ACTION_EXISTING_MANUAL_NEGATIVE]
    oracle_negative_count = action_counts[ACTION_PARK_ORACLE_NEGATIVE]
    boundary_unavailable_count = action_counts[ACTION_RECOVER_BOUNDARY]
    product_authority_count = sum(
        1
        for row in action_rows
        if row["may_feed_product_writer"] == YES
        or row["may_touch_matrix"] == YES
        or row["may_grant_product_authority"] == YES
    )
    return {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "decision": f"second_review_ready_for_{second_review_count}_cases",
        "decision_reasons": [
            (
                f"{second_review_count} plotted Gaussian15 cases have one "
                "clean reviewer label "
                "and should move to second independent review"
            ),
            (
                f"{manual_negative_count} manual wrong-peak/no-peak cases "
                "are existing negative controls, not missing visual unknowns"
            ),
            (
                f"{oracle_negative_count} failed round-trip oracle negatives "
                "stay parked as non-truth evidence"
            ),
            (
                f"{boundary_unavailable_count} Gaussian boundary-unavailable "
                "case needs signal/evidence recovery or remains not assessable"
            ),
            (
                "this packet grants no ProductWriter, matrix, workbook, "
                "selected-peak, selected-area, counted-detection, or broad "
                "Backfill authority"
            ),
        ],
        "source_artifacts": {
            "static_review_bundle_index": _repo_relative(static_bundle_index_path),
            "static_review_bundle_index_sha256": artifact_sha256(
                static_bundle_index_path,
            ),
            "label_log": _repo_relative(label_log_path),
            "label_log_sha256": artifact_sha256(label_log_path),
            "truth_summary": _repo_relative(truth_summary_path),
            "truth_summary_sha256": artifact_sha256(truth_summary_path),
            "next_action_plan": _repo_relative(next_action_plan_path),
            "next_action_plan_sha256": _rows_sha256(action_rows),
        },
        "upstream_truth_summary_decision": truth_summary.get("decision", ""),
        "authority_rules": {
            "may_feed_product_writer": False,
            "may_touch_matrix": False,
            "may_grant_product_authority": False,
            "broad_backfill_unparked": False,
            "round_trip_oracle_used_as_truth": False,
            "manual_negative_fixture_grants_write_authority": False,
        },
        "case_counts": {
            "total_cases": len(action_rows),
            "product_authority_rows": product_authority_count,
            "needs_second_reviewer": sum(
                1 for row in action_rows if row["needs_second_reviewer"] == YES
            ),
            "needs_visual_evidence_recovery": sum(
                1
                for row in action_rows
                if row["needs_visual_evidence_recovery"] == YES
            ),
            "manual_negative_control_cases": action_counts[
                ACTION_EXISTING_MANUAL_NEGATIVE
            ],
            "oracle_negative_parked_cases": action_counts[
                ACTION_PARK_ORACLE_NEGATIVE
            ],
        },
        "next_action_counts": dict(sorted(action_counts.items())),
        "next_action_class_counts": dict(sorted(class_counts.items())),
    }


def _check_no_authority(
    rows: Sequence[Mapping[str, str]],
    problems: list[str],
) -> None:
    for row_number, row in enumerate(rows, start=2):
        for field in (
            "round_trip_oracle_can_be_truth",
            "may_feed_product_writer",
            "may_touch_matrix",
            "may_grant_product_authority",
        ):
            if row.get(field) != NO_AUTHORITY:
                problems.append(f"next-action row {row_number}: {field} must be FALSE")
        parked_for_broad = row.get("parked_for_broad_backfill")
        is_oracle_negative = (
            row.get("source_stratum") == "failed_oracle_negative"
            and row.get("next_action") == ACTION_PARK_ORACLE_NEGATIVE
        )
        if is_oracle_negative and parked_for_broad != YES:
            problems.append(
                f"next-action row {row_number}: oracle-negative row must be parked",
            )
        if not is_oracle_negative and parked_for_broad != NO_AUTHORITY:
            problems.append(
                f"next-action row {row_number}: parked_for_broad_backfill "
                "is only allowed for oracle-negative rows",
            )


def _check_summary_authority_rules(
    summary: Mapping[str, Any],
    problems: list[str],
) -> None:
    rules = summary.get("authority_rules")
    if not isinstance(rules, Mapping):
        problems.append("next-action summary authority_rules must be an object")
        return
    expected_false = (
        "may_feed_product_writer",
        "may_touch_matrix",
        "may_grant_product_authority",
        "broad_backfill_unparked",
        "round_trip_oracle_used_as_truth",
        "manual_negative_fixture_grants_write_authority",
    )
    for key in expected_false:
        if rules.get(key) is not False:
            problems.append(f"next-action summary authority_rules.{key} must be false")
    for key, value in rules.items():
        if key in expected_false:
            continue
        if value is not False:
            problems.append(
                f"next-action summary authority_rules.{key} must be false",
            )


def _rows_sha256(rows: Sequence[Mapping[str, str]]) -> str:
    rendered = render_delimited_rows(
        rows,
        NEXT_ACTION_PLAN_HEADER,
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
    parser.add_argument("--static-bundle-index", type=Path, default=STATIC_BUNDLE_INDEX)
    parser.add_argument("--label-log", type=Path, default=LABEL_LOG)
    parser.add_argument("--truth-summary", type=Path, default=SUMMARY_JSON)
    parser.add_argument("--next-action-plan", type=Path, default=NEXT_ACTION_PLAN)
    parser.add_argument("--next-action-summary", type=Path, default=NEXT_ACTION_SUMMARY)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args(argv)
    if args.check_only:
        problems = check_lockbox_next_action_plan(
            static_bundle_index_path=args.static_bundle_index,
            label_log_path=args.label_log,
            truth_summary_path=args.truth_summary,
            next_action_plan_path=args.next_action_plan,
            next_action_summary_path=args.next_action_summary,
        )
        if problems:
            for problem in problems:
                print(problem, file=sys.stderr)
            return 1
        print("Lockbox next-action plan is valid and non-authoritative.")
        return 0
    result = build_lockbox_next_action_plan(
        static_bundle_index_path=args.static_bundle_index,
        label_log_path=args.label_log,
        truth_summary_path=args.truth_summary,
        next_action_plan_path=args.next_action_plan,
        next_action_summary_path=args.next_action_summary,
    )
    problems = result.get("problems", [])
    if problems:
        for problem in problems:
            print(problem, file=sys.stderr)
        return 1
    summary = result["summary"]
    print(
        "Built lockbox next-action plan: "
        f"{summary['case_counts']['total_cases']} cases, "
        f"decision={summary['decision']}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
