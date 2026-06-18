import csv
import json
from pathlib import Path

from scripts.import_lockbox_labels import (
    CONFUSION_TABLE,
    FAILURE_MODES,
    LABEL_LOG,
    STATIC_BUNDLE_INDEX,
    SUMMARY_JSON,
    build_lockbox_truth_summary,
    build_user_batch_label_log,
    check_lockbox_truth_summary,
)


def test_user_batch_label_log_is_one_reviewer_non_authoritative(
    tmp_path: Path,
) -> None:
    label_log = tmp_path / "labels.tsv"

    result = build_user_batch_label_log(label_log_path=label_log)
    rows = _read_tsv(label_log)

    assert result["label_count"] == 72
    assert result["plotted_gaussian15"] == 53
    assert len(rows) == 72
    assert {row["reviewer_id"] for row in rows} == {
        "user_batch_review_2026_06_18",
    }
    assert {row["reviewer_slot"] for row in rows} == {"1"}
    assert {row["label_grants_product_authority"] for row in rows} == {"FALSE"}
    assert {row["may_touch_matrix"] for row in rows} == {"FALSE"}
    assert {row["round_trip_oracle_used"] for row in rows} == {"FALSE"}
    assert sum(row["peak_choice_label"] == "correct" for row in rows) == 53
    assert (
        sum(row["peak_choice_label"] == "insufficient_evidence" for row in rows)
        == 19
    )
    assert sum(row["boundary_label"] == "acceptable" for row in rows) == 53
    assert sum(row["boundary_label"] == "not_assessable" for row in rows) == 19


def test_truth_summary_import_outputs_review_only_decision(
    tmp_path: Path,
) -> None:
    label_log = tmp_path / "labels.tsv"
    summary_path = tmp_path / "summary.json"
    confusion_path = tmp_path / "confusion.tsv"
    failure_path = tmp_path / "failures.tsv"

    build_user_batch_label_log(label_log_path=label_log)
    result = build_lockbox_truth_summary(
        label_log_path=label_log,
        summary_path=summary_path,
        confusion_table_path=confusion_path,
        failure_modes_path=failure_path,
    )

    assert result["problems"] == []
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    failures = _read_tsv(failure_path)
    assert summary["decision"] == "truth_supports_review_only"
    assert summary["case_counts"] == {
        "total_static_bundle_cases": 72,
        "labels_imported": 72,
        "assessable_labels": 53,
        "insufficient_evidence_labels": 19,
    }
    assert summary["metrics"]["peak_choice_correct_rate_assessable"] == 1.0
    assert summary["metrics"]["area_acceptable_rate_assessable"] == 1.0
    assert summary["metrics"]["boundary_acceptable_rate_assessable"] == 1.0
    assert summary["metrics"]["evidence_missing_or_unavailable_rate"] == 0.263889
    assert summary["authority_rules"]["labels_grant_product_authority"] is False
    assert {
        row["failure_mode"] for row in failures
    } >= {
        "insufficient_visual_evidence",
        "missing_overlay_or_trace_record",
        "gaussian_boundary_unavailable",
        "second_independent_reviewer_missing",
    }


def test_two_reviewer_clean_labels_can_support_next_automation_experiment(
    tmp_path: Path,
) -> None:
    label_log = tmp_path / "labels.tsv"
    summary_path = tmp_path / "summary.json"
    confusion_path = tmp_path / "confusion.tsv"
    failure_path = tmp_path / "failures.tsv"

    build_user_batch_label_log(label_log_path=label_log)
    header, rows = _read_tsv_with_header(label_log)
    clean_rows: list[dict[str, str]] = []
    for row in rows:
        row.update(
            {
                "peak_choice_label": "correct",
                "area_label": "acceptable",
                "boundary_label": "acceptable",
                "reviewer_reason_code": "visual_trace_overlay_review",
                "reviewer_confidence": "high",
            },
        )
        clean_rows.append(dict(row))
        second = dict(row)
        second["reviewer_slot"] = "2"
        second["reviewer_id"] = "second_human_lockbox_reviewer_v1"
        clean_rows.append(second)
    _write_tsv(label_log, header, clean_rows)

    result = build_lockbox_truth_summary(
        label_log_path=label_log,
        summary_path=summary_path,
        confusion_table_path=confusion_path,
        failure_modes_path=failure_path,
    )

    assert result["problems"] == []
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    failures = _read_tsv(failure_path)
    assert summary["decision"] == "truth_supports_next_automation_experiment"
    assert summary["case_counts"]["labels_imported"] == 144
    assert not any(
        row["failure_mode"] == "second_independent_reviewer_missing"
        for row in failures
    )


def test_truth_import_rejects_subagent_second_reviewer(
    tmp_path: Path,
) -> None:
    label_log = tmp_path / "labels.tsv"

    build_user_batch_label_log(label_log_path=label_log)
    header, rows = _read_tsv_with_header(label_log)
    second_rows: list[dict[str, str]] = list(rows)
    for row in rows:
        second = dict(row)
        second["reviewer_slot"] = "2"
        second["reviewer_id"] = "codex_subagent_challenge_review"
        second["peak_choice_label"] = "correct"
        second["area_label"] = "acceptable"
        second["boundary_label"] = "acceptable"
        second_rows.append(second)
    _write_tsv(label_log, header, second_rows)

    result = build_lockbox_truth_summary(
        label_log_path=label_log,
        summary_path=tmp_path / "summary.json",
        confusion_table_path=tmp_path / "confusion.tsv",
        failure_modes_path=tmp_path / "failures.tsv",
    )

    assert any(
        "reviewer_id is not human truth" in problem
        for problem in result["problems"]
    )


def test_truth_import_rejects_unregistered_human_looking_reviewer(
    tmp_path: Path,
) -> None:
    label_log = tmp_path / "labels.tsv"

    build_user_batch_label_log(label_log_path=label_log)
    header, rows = _read_tsv_with_header(label_log)
    second_rows: list[dict[str, str]] = list(rows)
    for row in rows:
        second = dict(row)
        second["reviewer_slot"] = "2"
        second["reviewer_id"] = "reviewer_two"
        second["peak_choice_label"] = "correct"
        second["area_label"] = "acceptable"
        second["boundary_label"] = "acceptable"
        second_rows.append(second)
    _write_tsv(label_log, header, second_rows)

    result = build_lockbox_truth_summary(
        label_log_path=label_log,
        summary_path=tmp_path / "summary.json",
        confusion_table_path=tmp_path / "confusion.tsv",
        failure_modes_path=tmp_path / "failures.tsv",
    )

    assert any(
        "allowed human truth reviewer registry" in problem
        for problem in result["problems"]
    )


def test_truth_import_rejects_malformed_reviewer_slots(tmp_path: Path) -> None:
    label_log = tmp_path / "labels.tsv"

    build_user_batch_label_log(label_log_path=label_log)
    header, rows = _read_tsv_with_header(label_log)
    malformed_rows: list[dict[str, str]] = list(rows)
    for row in rows:
        second = dict(row)
        second["reviewer_slot"] = "3"
        second["reviewer_id"] = "second_human_lockbox_reviewer_v1"
        second["peak_choice_label"] = "correct"
        second["area_label"] = "acceptable"
        second["boundary_label"] = "acceptable"
        malformed_rows.append(second)
    _write_tsv(label_log, header, malformed_rows)

    result = build_lockbox_truth_summary(
        label_log_path=label_log,
        summary_path=tmp_path / "summary.json",
        confusion_table_path=tmp_path / "confusion.tsv",
        failure_modes_path=tmp_path / "failures.tsv",
    )

    assert any(
        "reviewer slots must be 1 or 1..2" in problem
        for problem in result["problems"]
    )


def test_current_truth_summary_outputs_validate() -> None:
    assert check_lockbox_truth_summary() == []


def test_import_rejects_stale_static_hash_binding(tmp_path: Path) -> None:
    label_log = tmp_path / "labels.tsv"
    build_user_batch_label_log(label_log_path=label_log)
    header, rows = _read_tsv_with_header(label_log)
    rows[0]["source_artifact_hashes"] = "stale"
    _write_tsv(label_log, header, rows)

    result = build_lockbox_truth_summary(
        label_log_path=label_log,
        summary_path=tmp_path / "summary.json",
        confusion_table_path=tmp_path / "confusion.tsv",
        failure_modes_path=tmp_path / "failures.tsv",
    )

    assert any(
        "source_artifact_hashes mismatch" in problem
        for problem in result["problems"]
    )


def test_import_rejects_authority_flags(tmp_path: Path) -> None:
    label_log = tmp_path / "labels.tsv"
    build_user_batch_label_log(label_log_path=label_log)
    header, rows = _read_tsv_with_header(label_log)
    rows[0]["label_grants_product_authority"] = "TRUE"
    rows[1]["may_touch_matrix"] = "TRUE"
    _write_tsv(label_log, header, rows)

    result = build_lockbox_truth_summary(
        label_log_path=label_log,
        summary_path=tmp_path / "summary.json",
        confusion_table_path=tmp_path / "confusion.tsv",
        failure_modes_path=tmp_path / "failures.tsv",
    )

    assert any(
        "label_grants_product_authority must be FALSE" in problem
        for problem in result["problems"]
    )
    assert any(
        "may_touch_matrix must be FALSE" in problem for problem in result["problems"]
    )


def test_import_rejects_duplicate_reviewer_per_case(tmp_path: Path) -> None:
    label_log = tmp_path / "labels.tsv"
    build_user_batch_label_log(label_log_path=label_log)
    header, rows = _read_tsv_with_header(label_log)
    rows.append(dict(rows[0]))
    _write_tsv(label_log, header, rows)

    result = build_lockbox_truth_summary(
        label_log_path=label_log,
        summary_path=tmp_path / "summary.json",
        confusion_table_path=tmp_path / "confusion.tsv",
        failure_modes_path=tmp_path / "failures.tsv",
    )

    assert any(
        "duplicate reviewer_id per case" in problem for problem in result["problems"]
    )


def test_current_truth_summary_paths_are_default_outputs() -> None:
    assert LABEL_LOG.name == "lockbox_reviewer_label_log_v1.tsv"
    assert SUMMARY_JSON.name == "lockbox_truth_summary_v1.json"
    assert CONFUSION_TABLE.name == "lockbox_truth_confusion_table_v1.tsv"
    assert FAILURE_MODES.name == "lockbox_failure_modes_v1.tsv"
    assert STATIC_BUNDLE_INDEX.name == "bundle_index.tsv"


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
