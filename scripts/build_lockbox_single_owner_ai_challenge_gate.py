"""Build the Lockbox single-owner + AI-challenge gate v1.

This is a read-only decision packet. It lets the project proceed to a later
shadow automation experiment design when the owner-reviewed clean subset has no
open AI challenge flags. It does not satisfy the two-human truth lockbox and it
does not grant ProductWriter, matrix, workbook, selected-peak, selected-area,
counted-detection, GUI, default-extraction, or broad Backfill authority.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from scripts.build_lockbox_ai_challenge_pack import OWNER_BOUNDARY_CONFIRMATION
from scripts.build_lockbox_second_review_pack import (
    SECOND_REVIEW_SUMMARY,
    check_lockbox_second_review_pack,
)
from scripts.check_lockbox_ai_challenge_results import (
    AI_CHALLENGE_RESULT_SUMMARY,
    DECISION_NO_OWNER_RECHECK,
    check_lockbox_ai_challenge_results,
)
from scripts.check_lockbox_ai_challenge_results import (
    SUMMARY_SCHEMA_VERSION as AI_RESULT_SCHEMA_VERSION,
)
from scripts.import_lockbox_labels import (
    SUMMARY_JSON as TRUTH_SUMMARY,
)
from scripts.import_lockbox_labels import (
    TRUTH_SUMMARY_SCHEMA_VERSION,
    check_lockbox_truth_summary,
)
from xic_extractor.tabular_io import file_sha256

ROOT = Path(__file__).resolve().parents[1]
GATE_SUMMARY = (
    ROOT
    / "docs/superpowers/validation/lockbox_single_owner_ai_challenge_gate_v1.json"
)

SCHEMA_VERSION = "lockbox_single_owner_ai_challenge_gate_v1"
DECISION_SUPPORTS_SHADOW_EXPERIMENT = (
    "single_owner_ai_challenge_supports_shadow_automation_experiment"
)
NO_AUTHORITY = "forbidden"


def build_lockbox_single_owner_ai_challenge_gate(
    *,
    truth_summary_path: Path = TRUTH_SUMMARY,
    ai_challenge_result_summary_path: Path = AI_CHALLENGE_RESULT_SUMMARY,
    second_review_summary_path: Path = SECOND_REVIEW_SUMMARY,
    owner_boundary_confirmation_path: Path = OWNER_BOUNDARY_CONFIRMATION,
    gate_summary_path: Path = GATE_SUMMARY,
    write_summary: bool = True,
) -> dict[str, object]:
    problems = _source_problems(
        truth_summary_path=truth_summary_path,
        ai_challenge_result_summary_path=ai_challenge_result_summary_path,
        second_review_summary_path=second_review_summary_path,
        owner_boundary_confirmation_path=owner_boundary_confirmation_path,
    )
    truth_summary = _read_json(truth_summary_path, problems, "truth summary")
    ai_summary = _read_json(
        ai_challenge_result_summary_path,
        problems,
        "AI challenge result summary",
    )
    second_review = _read_json(
        second_review_summary_path,
        problems,
        "second-review summary",
    )
    owner_boundary = _read_json(
        owner_boundary_confirmation_path,
        problems,
        "owner-boundary confirmation",
    )
    if problems:
        return {"problems": problems}

    _check_truth_summary(truth_summary, problems)
    _check_ai_summary(ai_summary, problems)
    _check_second_review_summary(second_review, problems)
    _check_owner_boundary(owner_boundary, problems)
    if problems:
        return {"problems": problems}

    summary = _summary_json(
        truth_summary,
        ai_summary,
        second_review,
        truth_summary_path=truth_summary_path,
        ai_challenge_result_summary_path=ai_challenge_result_summary_path,
        second_review_summary_path=second_review_summary_path,
        owner_boundary_confirmation_path=owner_boundary_confirmation_path,
    )
    if write_summary:
        gate_summary_path.write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return {"problems": [], "summary": summary}


def check_lockbox_single_owner_ai_challenge_gate(
    *,
    truth_summary_path: Path = TRUTH_SUMMARY,
    ai_challenge_result_summary_path: Path = AI_CHALLENGE_RESULT_SUMMARY,
    second_review_summary_path: Path = SECOND_REVIEW_SUMMARY,
    owner_boundary_confirmation_path: Path = OWNER_BOUNDARY_CONFIRMATION,
    gate_summary_path: Path = GATE_SUMMARY,
) -> list[str]:
    result = build_lockbox_single_owner_ai_challenge_gate(
        truth_summary_path=truth_summary_path,
        ai_challenge_result_summary_path=ai_challenge_result_summary_path,
        second_review_summary_path=second_review_summary_path,
        owner_boundary_confirmation_path=owner_boundary_confirmation_path,
        gate_summary_path=gate_summary_path,
        write_summary=False,
    )
    problems = list(result.get("problems", []))
    if problems:
        return problems
    expected = result["summary"]
    if not gate_summary_path.exists():
        problems.append("single-owner AI challenge gate summary missing")
        return problems
    actual = _read_json(gate_summary_path, problems, "gate summary")
    if not actual:
        return problems
    if actual != expected:
        problems.append("single-owner AI challenge gate summary is stale")
    _check_gate_summary(actual, problems)
    return problems


def _source_problems(
    *,
    truth_summary_path: Path,
    ai_challenge_result_summary_path: Path,
    second_review_summary_path: Path,
    owner_boundary_confirmation_path: Path,
) -> list[str]:
    problems = []
    problems.extend(
        check_lockbox_truth_summary(summary_path=truth_summary_path),
    )
    problems.extend(
        check_lockbox_ai_challenge_results(
            ai_challenge_result_summary_path=ai_challenge_result_summary_path,
        ),
    )
    problems.extend(
        check_lockbox_second_review_pack(
            ai_challenge_result_summary_path=ai_challenge_result_summary_path,
            second_review_summary_path=second_review_summary_path,
        ),
    )
    for path, label in (
        (second_review_summary_path, "second-review summary"),
        (owner_boundary_confirmation_path, "owner-boundary confirmation"),
    ):
        if not path.exists():
            problems.append(f"{label} missing")
    return problems


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


def _check_truth_summary(summary: Mapping[str, Any], problems: list[str]) -> None:
    if summary.get("schema_version") != TRUTH_SUMMARY_SCHEMA_VERSION:
        problems.append("truth summary schema_version mismatch")
    if summary.get("decision") != "truth_supports_review_only":
        problems.append("single-owner gate requires review-only truth summary")
    counts = summary.get("case_counts", {})
    if not isinstance(counts, Mapping):
        problems.append("truth summary case_counts must be an object")
        return
    if counts.get("total_static_bundle_cases") != 72:
        problems.append("truth summary must cover 72 lockbox cases")
    if counts.get("assessable_labels") != 53:
        problems.append("truth summary must record 53 assessable owner labels")
    if counts.get("insufficient_evidence_labels") != 19:
        problems.append("truth summary must record 19 not-assessable labels")
    metrics = summary.get("metrics", {})
    if not isinstance(metrics, Mapping):
        problems.append("truth summary metrics must be an object")
        return
    for key in (
        "peak_choice_correct_rate_assessable",
        "area_acceptable_rate_assessable",
        "boundary_acceptable_rate_assessable",
    ):
        if metrics.get(key) != 1.0:
            problems.append(f"truth summary {key} must be 1.0")


def _check_ai_summary(summary: Mapping[str, Any], problems: list[str]) -> None:
    if summary.get("schema_version") != AI_RESULT_SCHEMA_VERSION:
        problems.append("AI challenge result summary schema_version mismatch")
    if summary.get("decision") != DECISION_NO_OWNER_RECHECK:
        problems.append("single-owner gate requires AI no-owner-recheck decision")
    counts = summary.get("case_counts", {})
    if not isinstance(counts, Mapping):
        problems.append("AI challenge result summary case_counts must be an object")
    elif counts.get("flagged_cases") != 0:
        problems.append("single-owner gate requires zero AI challenge flags")
    if summary.get("flagged_cases"):
        problems.append("single-owner gate requires empty AI flagged_cases")


def _check_second_review_summary(
    summary: Mapping[str, Any],
    problems: list[str],
) -> None:
    if summary.get("schema_version") != "lockbox_second_review_summary_v1":
        problems.append("second-review summary schema_version mismatch")
    if summary.get("decision") != "second_review_collection_ready_for_53_cases":
        problems.append("single-owner gate requires current second-review pack")
    if summary.get("upstream_ai_challenge_decision") != DECISION_NO_OWNER_RECHECK:
        problems.append("second-review summary must record AI no-owner-recheck")
    if summary.get("ai_challenge_flagged_cases") != 0:
        problems.append("second-review summary must record zero AI flags")


def _check_owner_boundary(
    summary: Mapping[str, Any],
    problems: list[str],
) -> None:
    if summary.get("schema_version") != "lockbox_owner_boundary_confirmation_v1":
        problems.append("owner-boundary schema_version mismatch")
    artifacts = summary.get("source_artifacts", {})
    if not isinstance(artifacts, Mapping):
        problems.append("owner-boundary source_artifacts must be an object")
        return
    if "second_review_summary" in artifacts:
        problems.append("owner-boundary must not hash downstream second review")
    for key, value in artifacts.items():
        if key.endswith("_sha256"):
            continue
        expected = artifacts.get(f"{key}_sha256", "")
        if not expected:
            continue
        path = _repo_path(str(value))
        if not path.exists():
            problems.append(f"owner-boundary source_artifacts.{key} missing")
        elif file_sha256(path) != expected:
            problems.append(
                f"owner-boundary source_artifacts.{key} hash mismatch",
            )


def _summary_json(
    truth_summary: Mapping[str, Any],
    ai_summary: Mapping[str, Any],
    second_review: Mapping[str, Any],
    *,
    truth_summary_path: Path,
    ai_challenge_result_summary_path: Path,
    second_review_summary_path: Path,
    owner_boundary_confirmation_path: Path,
) -> dict[str, Any]:
    truth_counts = truth_summary["case_counts"]
    ai_counts = ai_summary["case_counts"]
    second_counts = second_review["case_counts"]
    return {
        "schema_version": SCHEMA_VERSION,
        "decision": DECISION_SUPPORTS_SHADOW_EXPERIMENT,
        "decision_reasons": [
            "one owner/domain review pass labels 53 assessable Gaussian15 cases clean",
            "AI challenge result is current with zero owner re-review flags",
            "19 lockbox cases remain insufficient/not assessable and excluded",
            (
                "this is not two-human truth completion and cannot grant writer "
                "authority"
            ),
        ],
        "allowed_next_step": "shadow_automation_experiment_design_only",
        "forbidden_next_steps": [
            "ProductWriter consumption",
            "matrix or workbook mutation",
            "selected peak or selected area rewrite",
            "counted detection change",
            "GUI/default extraction behavior change",
            "broad Backfill unpark",
            "treating AI challenge as reviewer_slot_2 truth",
        ],
        "case_counts": {
            "total_lockbox_cases": truth_counts["total_static_bundle_cases"],
            "owner_assessable_clean_cases": truth_counts["assessable_labels"],
            "owner_not_assessable_cases": truth_counts[
                "insufficient_evidence_labels"
            ],
            "second_review_collection_cases": second_counts[
                "second_review_queue_cases"
            ],
            "ai_challenge_total_cases": ai_counts["total_cases"],
            "ai_challenge_flagged_cases": ai_counts["flagged_cases"],
            "product_authority_rows": 0,
        },
        "source_decisions": {
            "truth_summary": truth_summary["decision"],
            "ai_challenge_result": ai_summary["decision"],
            "second_review_summary": second_review["decision"],
        },
        "authority_rules": {
            "may_satisfy_reviewer_slot2": False,
            "may_grant_truth_completion": False,
            "may_feed_product_writer": False,
            "may_touch_matrix": False,
            "may_touch_workbook": False,
            "may_switch_selected_peak": False,
            "may_change_selected_area": False,
            "may_change_counted_detection": False,
            "may_change_default_extraction": False,
            "may_change_gui": False,
            "broad_backfill_unparked": False,
            "product_writer_consumption": NO_AUTHORITY,
        },
        "source_artifacts": {
            "truth_summary": _repo_relative(truth_summary_path),
            "truth_summary_sha256": file_sha256(truth_summary_path),
            "ai_challenge_result_summary": _repo_relative(
                ai_challenge_result_summary_path,
            ),
            "ai_challenge_result_summary_sha256": file_sha256(
                ai_challenge_result_summary_path,
            ),
            "second_review_summary": _repo_relative(second_review_summary_path),
            "second_review_summary_sha256": file_sha256(second_review_summary_path),
            "owner_boundary_confirmation": _repo_relative(
                owner_boundary_confirmation_path,
            ),
            "owner_boundary_confirmation_sha256": file_sha256(
                owner_boundary_confirmation_path,
            ),
        },
    }


def _check_gate_summary(summary: Mapping[str, Any], problems: list[str]) -> None:
    if summary.get("schema_version") != SCHEMA_VERSION:
        problems.append("single-owner AI challenge gate schema_version mismatch")
    if summary.get("decision") != DECISION_SUPPORTS_SHADOW_EXPERIMENT:
        problems.append("single-owner AI challenge gate decision mismatch")
    if summary.get("allowed_next_step") != "shadow_automation_experiment_design_only":
        problems.append("single-owner AI challenge gate next step mismatch")
    counts = summary.get("case_counts", {})
    if not isinstance(counts, Mapping):
        problems.append("single-owner AI challenge gate case_counts must be an object")
    elif counts.get("product_authority_rows") != 0:
        problems.append("single-owner AI challenge gate product authority must be 0")
    authority = summary.get("authority_rules", {})
    if not isinstance(authority, Mapping):
        problems.append("single-owner AI challenge gate authority_rules missing")
        return
    for key, value in authority.items():
        if key == "product_writer_consumption":
            if value != NO_AUTHORITY:
                problems.append("single-owner AI challenge gate must forbid writer")
        elif value is not False:
            problems.append(
                f"single-owner AI challenge gate authority_rules.{key} must be false",
            )


def _repo_relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def _repo_path(path_value: str) -> Path:
    path = Path(path_value)
    return path if path.is_absolute() else ROOT / path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--truth-summary", type=Path, default=TRUTH_SUMMARY)
    parser.add_argument(
        "--ai-challenge-result-summary",
        type=Path,
        default=AI_CHALLENGE_RESULT_SUMMARY,
    )
    parser.add_argument(
        "--second-review-summary",
        type=Path,
        default=SECOND_REVIEW_SUMMARY,
    )
    parser.add_argument(
        "--owner-boundary-confirmation",
        type=Path,
        default=OWNER_BOUNDARY_CONFIRMATION,
    )
    parser.add_argument("--gate-summary", type=Path, default=GATE_SUMMARY)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args(argv)

    kwargs = {
        "truth_summary_path": args.truth_summary,
        "ai_challenge_result_summary_path": args.ai_challenge_result_summary,
        "second_review_summary_path": args.second_review_summary,
        "owner_boundary_confirmation_path": args.owner_boundary_confirmation,
        "gate_summary_path": args.gate_summary,
    }
    if args.check_only:
        problems = check_lockbox_single_owner_ai_challenge_gate(**kwargs)
        if problems:
            for problem in problems:
                print(problem, file=sys.stderr)
            return 1
        print("Lockbox single-owner AI challenge gate is valid and non-authoritative.")
        return 0
    result = build_lockbox_single_owner_ai_challenge_gate(**kwargs)
    if result["problems"]:
        for problem in result["problems"]:
            print(problem, file=sys.stderr)
        return 1
    summary = result["summary"]
    print(
        "Built lockbox single-owner AI challenge gate: "
        f"{summary['case_counts']['owner_assessable_clean_cases']} owner-clean "
        "cases, "
        f"decision={summary['decision']}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
