"""Validate and summarize Lockbox AI challenge result logs.

AI challenge results are a non-authoritative QA surface. They can flag owner
re-review, route repair, or evidence repair, but they are not truth labels,
reviewer-slot-2 labels, ProductWriter input, or matrix/workbook authority.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from scripts.build_lockbox_ai_challenge_pack import (
    AI_CHALLENGE_QUEUE,
    AI_CHALLENGE_SUMMARY,
    AUTHORITY_FIELDS,
    CHALLENGE_ROW_SCHEMA_VERSION,
    NO_AUTHORITY,
    TEMPLATE_HEADER,
    check_lockbox_ai_challenge_pack,
)
from scripts.check_productization_state import artifact_sha256
from xic_extractor.tabular_io import (
    read_tsv_required,
    read_tsv_with_header,
)

ROOT = Path(__file__).resolve().parents[1]
AI_CHALLENGE_RESULT_LOG = (
    ROOT / "docs/superpowers/validation/lockbox_ai_challenge_result_log_v1.tsv"
)
AI_CHALLENGE_RESULT_SUMMARY = (
    ROOT / "docs/superpowers/validation/lockbox_ai_challenge_result_summary_v1.json"
)

SUMMARY_SCHEMA_VERSION = "lockbox_ai_challenge_result_summary_v1"
DECISION_NO_OWNER_RECHECK = "ai_challenge_no_owner_recheck_required"
DECISION_OWNER_RECHECK = "ai_challenge_owner_recheck_required"
OWNER_RULE_RESOLVED_CASE_ID = "LOCKBOXV1_60CEB35837FAF38CC4DE9021"
OWNER_RULE_RESOLVED_REASON = "owner_rule_detected_left_peak_resolved"
OWNER_RULE_REQUIRED_NOTE_TOKENS = (
    "cell_apex_rt=15.1553",
    "trace_apex_rt=15.1553",
    "right_peak_rt=15.4366",
)

ALLOWED_REASON_CODES = {
    "no_obvious_visual_contradiction",
    OWNER_RULE_RESOLVED_REASON,
    "route_integrity_confirmed",
    "artifact_integrity_problem",
    "route_mismatch",
    "evidence_missing_or_unusable",
    "visual_contradiction_suspected",
}
ALLOWED_EVIDENCE_VIEWED = {
    "packet",
    "packet_trace_overlay_hypothesis",
    "packet_recovered_trace_overlay_hypothesis",
    "packet_missing_evidence_record",
    "route_artifacts_only",
}
FLAG_RESULTS = {
    "flag_for_owner_recheck",
    "artifact_integrity_problem",
    "route_mismatch",
    "evidence_missing_or_unusable",
    "visual_contradiction_suspected",
}


def check_lockbox_ai_challenge_results(
    *,
    ai_challenge_queue_path: Path = AI_CHALLENGE_QUEUE,
    ai_challenge_packet_summary_path: Path = AI_CHALLENGE_SUMMARY,
    ai_challenge_result_log_path: Path = AI_CHALLENGE_RESULT_LOG,
    ai_challenge_result_summary_path: Path = AI_CHALLENGE_RESULT_SUMMARY,
) -> list[str]:
    problems = check_lockbox_ai_challenge_pack(
        ai_challenge_queue_path=ai_challenge_queue_path,
        ai_challenge_summary_path=ai_challenge_packet_summary_path,
    )
    result = build_lockbox_ai_challenge_result_summary(
        ai_challenge_queue_path=ai_challenge_queue_path,
        ai_challenge_packet_summary_path=ai_challenge_packet_summary_path,
        ai_challenge_result_log_path=ai_challenge_result_log_path,
        write_summary=False,
    )
    problems.extend(result.get("problems", []))
    if problems:
        return problems

    expected_summary = result["summary"]
    if not ai_challenge_result_summary_path.exists():
        problems.append("AI challenge result summary JSON missing")
        return problems
    actual_summary = json.loads(
        ai_challenge_result_summary_path.read_text(encoding="utf-8"),
    )
    if actual_summary != expected_summary:
        problems.append("AI challenge result summary JSON is stale")
    _check_summary_contract(actual_summary, problems)
    return problems


def build_lockbox_ai_challenge_result_summary(
    *,
    ai_challenge_queue_path: Path = AI_CHALLENGE_QUEUE,
    ai_challenge_packet_summary_path: Path = AI_CHALLENGE_SUMMARY,
    ai_challenge_result_log_path: Path = AI_CHALLENGE_RESULT_LOG,
    ai_challenge_result_summary_path: Path = AI_CHALLENGE_RESULT_SUMMARY,
    write_summary: bool = True,
) -> dict[str, Any]:
    problems: list[str] = []
    queue_rows = list(
        read_tsv_required(
            ai_challenge_queue_path,
            required_columns=(
                "lockbox_case_id",
                "challenge_scope",
                "allowed_agent_outputs",
                "source_hashes",
            ),
        ),
    )
    queue_by_case = {row["lockbox_case_id"]: row for row in queue_rows}
    if len(queue_by_case) != len(queue_rows):
        problems.append("AI challenge queue contains duplicate lockbox_case_id")

    header, result_rows = _read_result_log(ai_challenge_result_log_path, problems)
    if header and tuple(header) != tuple(TEMPLATE_HEADER):
        problems.append("AI challenge result log header mismatch")

    _check_result_rows(result_rows, queue_rows, queue_by_case, problems)
    summary = _summary_json(
        queue_rows,
        result_rows,
        ai_challenge_queue_path=ai_challenge_queue_path,
        ai_challenge_packet_summary_path=ai_challenge_packet_summary_path,
        ai_challenge_result_log_path=ai_challenge_result_log_path,
    )
    if write_summary and not problems:
        ai_challenge_result_summary_path.write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return {"problems": problems, "summary": summary, "result_rows": result_rows}


def _read_result_log(
    path: Path,
    problems: list[str],
) -> tuple[Sequence[str], list[dict[str, str]]]:
    if not path.exists():
        problems.append("AI challenge result log TSV missing")
        return (), []
    try:
        return read_tsv_with_header(path)
    except (OSError, ValueError) as exc:
        problems.append(f"could not read AI challenge result log TSV: {exc}")
        return (), []


def _check_result_rows(
    result_rows: Sequence[Mapping[str, str]],
    queue_rows: Sequence[Mapping[str, str]],
    queue_by_case: Mapping[str, Mapping[str, str]],
    problems: list[str],
) -> None:
    if len(result_rows) != len(queue_rows):
        problems.append("AI challenge result log must contain 72 rows")
    seen: set[str] = set()
    queue_case_ids = [row["lockbox_case_id"] for row in queue_rows]
    result_case_ids = [row.get("lockbox_case_id", "") for row in result_rows]
    if set(result_case_ids) != set(queue_case_ids):
        problems.append("AI challenge result log case coverage mismatch")
    for index, row in enumerate(result_rows, start=2):
        case_id = row.get("lockbox_case_id", "")
        queue_row = queue_by_case.get(case_id)
        if not case_id:
            problems.append(f"AI challenge result row {index}: missing case id")
            continue
        if case_id in seen:
            problems.append(f"AI challenge result row {index}: duplicate case id")
        seen.add(case_id)
        if row.get("schema_version") != CHALLENGE_ROW_SCHEMA_VERSION:
            problems.append(f"AI challenge result row {index}: invalid schema_version")
        if not row.get("challenge_reviewer_id", "").startswith("ai_challenge_"):
            problems.append(
                f"AI challenge result row {index}: "
                "challenge_reviewer_id must start with ai_challenge_",
            )
        if not row.get("reviewed_at_utc", "").endswith("Z"):
            problems.append(
                f"AI challenge result row {index}: reviewed_at_utc must end with Z",
            )
        result = row.get("challenge_result", "")
        if queue_row is None:
            continue
        allowed_results = set(queue_row.get("allowed_agent_outputs", "").split("|"))
        if result not in allowed_results:
            problems.append(
                f"AI challenge result row {index}: "
                f"challenge_result {result!r} not allowed for case",
            )
        if (
            result == "visual_contradiction_suspected"
            and queue_row.get("challenge_scope") != "visual_contradiction_challenge"
        ):
            problems.append(
                f"AI challenge result row {index}: "
                "visual_contradiction_suspected is visual-scope only",
            )
        if row.get("challenge_reason_code") not in ALLOWED_REASON_CODES:
            problems.append(
                f"AI challenge result row {index}: invalid challenge_reason_code",
            )
        if row.get("challenge_reason_code") == OWNER_RULE_RESOLVED_REASON:
            if case_id != OWNER_RULE_RESOLVED_CASE_ID:
                problems.append(
                    f"AI challenge result row {index}: "
                    f"{OWNER_RULE_RESOLVED_REASON} is case-specific",
                )
            if result != "no_issue":
                problems.append(
                    f"AI challenge result row {index}: "
                    f"{OWNER_RULE_RESOLVED_REASON} must resolve to no_issue",
                )
            notes = row.get("challenge_notes", "")
            for token in OWNER_RULE_REQUIRED_NOTE_TOKENS:
                if token not in notes:
                    problems.append(
                        f"AI challenge result row {index}: "
                        f"{OWNER_RULE_RESOLVED_REASON} missing note token {token}",
                    )
        if row.get("evidence_viewed") not in ALLOWED_EVIDENCE_VIEWED:
            problems.append(f"AI challenge result row {index}: invalid evidence_viewed")
        if row.get("source_hashes") != queue_row.get("source_hashes"):
            problems.append(f"AI challenge result row {index}: source_hashes mismatch")
        for field in AUTHORITY_FIELDS:
            if row.get(field) != NO_AUTHORITY:
                problems.append(
                    f"AI challenge result row {index}: {field} must be FALSE",
                )


def _summary_json(
    queue_rows: Sequence[Mapping[str, str]],
    result_rows: Sequence[Mapping[str, str]],
    *,
    ai_challenge_queue_path: Path,
    ai_challenge_packet_summary_path: Path,
    ai_challenge_result_log_path: Path,
) -> dict[str, Any]:
    result_counts = Counter(row.get("challenge_result", "") for row in result_rows)
    reason_counts = Counter(row.get("challenge_reason_code", "") for row in result_rows)
    scope_by_case = {
        row["lockbox_case_id"]: row.get("challenge_scope", "") for row in queue_rows
    }
    flagged_cases = [
        {
            "lockbox_case_id": row.get("lockbox_case_id", ""),
            "challenge_result": row.get("challenge_result", ""),
            "challenge_reason_code": row.get("challenge_reason_code", ""),
            "challenge_notes": row.get("challenge_notes", ""),
            "challenge_scope": scope_by_case.get(row.get("lockbox_case_id", ""), ""),
        }
        for row in result_rows
        if row.get("challenge_result") in FLAG_RESULTS
    ]
    visual_rows = [
        row
        for row in result_rows
        if scope_by_case.get(row.get("lockbox_case_id", ""))
        == "visual_contradiction_challenge"
    ]
    route_rows = len(result_rows) - len(visual_rows)
    return {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "decision": (
            DECISION_OWNER_RECHECK
            if flagged_cases
            else DECISION_NO_OWNER_RECHECK
        ),
        "decision_reasons": [
            "AI/subagent challenge output is non-authoritative QA only",
            "challenge findings can only route cases back to owner re-review",
            "challenge output cannot satisfy reviewer slot 2 or grant writer authority",
        ],
        "case_counts": {
            "total_cases": len(result_rows),
            "visual_challenge_cases": len(visual_rows),
            "route_or_evidence_integrity_cases": route_rows,
            "flagged_cases": len(flagged_cases),
            "product_authority_rows": 0,
        },
        "challenge_result_counts": dict(sorted(result_counts.items())),
        "challenge_reason_counts": dict(sorted(reason_counts.items())),
        "flagged_cases": flagged_cases,
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
        "source_artifacts": {
            "ai_challenge_queue": _repo_relative(ai_challenge_queue_path),
            "ai_challenge_queue_sha256": artifact_sha256(ai_challenge_queue_path),
            "ai_challenge_packet_summary": _repo_relative(
                ai_challenge_packet_summary_path,
            ),
            "ai_challenge_packet_summary_sha256": artifact_sha256(
                ai_challenge_packet_summary_path,
            ),
            "ai_challenge_result_log": _repo_relative(
                ai_challenge_result_log_path,
            ),
            "ai_challenge_result_log_sha256": artifact_sha256(
                ai_challenge_result_log_path,
            )
            if ai_challenge_result_log_path.exists()
            else "",
        },
    }


def _check_summary_contract(
    summary: Mapping[str, Any],
    problems: list[str],
) -> None:
    if summary.get("schema_version") != SUMMARY_SCHEMA_VERSION:
        problems.append("AI challenge result summary schema_version mismatch")
    if summary.get("decision") not in {
        DECISION_NO_OWNER_RECHECK,
        DECISION_OWNER_RECHECK,
    }:
        problems.append("AI challenge result summary decision mismatch")
    counts = summary.get("case_counts", {})
    if counts.get("total_cases") != 72:
        problems.append("AI challenge result summary total_cases must be 72")
    if counts.get("visual_challenge_cases") != 53:
        problems.append("AI challenge result summary visual cases must be 53")
    if counts.get("route_or_evidence_integrity_cases") != 19:
        problems.append("AI challenge result summary route/evidence cases must be 19")
    if counts.get("product_authority_rows") != 0:
        problems.append("AI challenge result summary product authority rows must be 0")
    authority = summary.get("authority_rules", {})
    if not isinstance(authority, Mapping):
        problems.append("AI challenge result summary authority_rules must be an object")
        return
    for key, value in authority.items():
        if value is not False:
            problems.append(
                f"AI challenge result summary authority_rules.{key} must be false",
            )


def _repo_relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def _main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queue", type=Path, default=AI_CHALLENGE_QUEUE)
    parser.add_argument("--packet-summary", type=Path, default=AI_CHALLENGE_SUMMARY)
    parser.add_argument("--result-log", type=Path, default=AI_CHALLENGE_RESULT_LOG)
    parser.add_argument(
        "--result-summary",
        type=Path,
        default=AI_CHALLENGE_RESULT_SUMMARY,
    )
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()

    if args.check_only:
        problems = check_lockbox_ai_challenge_results(
            ai_challenge_queue_path=args.queue,
            ai_challenge_packet_summary_path=args.packet_summary,
            ai_challenge_result_log_path=args.result_log,
            ai_challenge_result_summary_path=args.result_summary,
        )
        if problems:
            for problem in problems:
                print(problem, file=sys.stderr)
            return 1
        print("Lockbox AI challenge results are valid and non-authoritative.")
        return 0

    result = build_lockbox_ai_challenge_result_summary(
        ai_challenge_queue_path=args.queue,
        ai_challenge_packet_summary_path=args.packet_summary,
        ai_challenge_result_log_path=args.result_log,
        ai_challenge_result_summary_path=args.result_summary,
        write_summary=True,
    )
    if result["problems"]:
        for problem in result["problems"]:
            print(problem, file=sys.stderr)
        return 1
    summary = result["summary"]
    print(
        "Built lockbox AI challenge result summary: "
        f"{summary['case_counts']['total_cases']} cases, "
        f"flagged={summary['case_counts']['flagged_cases']}, "
        f"decision={summary['decision']}.",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
