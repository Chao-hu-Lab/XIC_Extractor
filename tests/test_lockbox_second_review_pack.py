import csv
import json
import re
from pathlib import Path

from scripts.build_lockbox_next_action_plan import NEXT_ACTION_PLAN
from scripts.build_lockbox_second_review_pack import (
    SECOND_REVIEW_INDEX,
    SECOND_REVIEW_QUEUE,
    SECOND_REVIEW_SUMMARY,
    SECOND_REVIEW_TEMPLATE,
    build_lockbox_second_review_pack,
    check_lockbox_second_review_pack,
)
from scripts.check_lockbox_ai_challenge_results import AI_CHALLENGE_RESULT_SUMMARY
from scripts.import_lockbox_labels import STATIC_BUNDLE_INDEX


def test_current_lockbox_second_review_pack_validates() -> None:
    assert check_lockbox_second_review_pack() == []


def test_current_second_review_pack_counts_and_authority() -> None:
    queue_rows = _read_tsv(SECOND_REVIEW_QUEUE)
    template_rows = _read_tsv(SECOND_REVIEW_TEMPLATE)
    summary = json.loads(SECOND_REVIEW_SUMMARY.read_text(encoding="utf-8"))

    assert len(queue_rows) == 53
    assert len(template_rows) == 53
    assert summary["decision"] == "second_review_collection_ready_for_53_cases"
    assert (
        summary["upstream_ai_challenge_decision"]
        == "ai_challenge_no_owner_recheck_required"
    )
    assert summary["ai_challenge_flagged_cases"] == 0
    assert summary["case_counts"] == {
        "total_next_action_cases": 72,
        "second_review_queue_cases": 53,
        "second_review_template_rows": 53,
        "excluded_not_ready_for_second_review": 19,
        "product_authority_rows": 0,
    }
    assert summary["authority_rules"] == {
        "broad_backfill_unparked": False,
        "labels_prefilled": False,
        "may_feed_product_writer": False,
        "may_grant_product_authority": False,
        "may_touch_matrix": False,
        "round_trip_oracle_used_as_truth": False,
    }
    assert {row["gaussian_smoothing_method"] for row in queue_rows} == {"gaussian_15"}
    assert {row["gaussian_window_points"] for row in queue_rows} == {"15"}
    assert {row["may_feed_product_writer"] for row in queue_rows} == {"FALSE"}
    assert {row["may_touch_matrix"] for row in queue_rows} == {"FALSE"}
    assert {row["may_grant_product_authority"] for row in queue_rows} == {"FALSE"}
    assert {row["broad_backfill_unparked"] for row in queue_rows} == {"FALSE"}
    assert (
        summary["source_artifacts"]["ai_challenge_result_summary"]
        == "docs/superpowers/validation/lockbox_ai_challenge_result_summary_v1.json"
    )


def test_current_second_review_queue_is_exactly_next_action_ready_cases() -> None:
    queue_rows = _read_tsv(SECOND_REVIEW_QUEUE)
    next_action_rows = _read_tsv(NEXT_ACTION_PLAN)

    ready_cases = {
        row["lockbox_case_id"]
        for row in next_action_rows
        if row["next_action"] == "ready_for_second_independent_review"
    }

    assert {row["lockbox_case_id"] for row in queue_rows} == ready_cases
    assert all(
        "failed_oracle_negative" not in row["source_stratum"] for row in queue_rows
    )
    assert all(
        "manual_wrong_peak_or_no_peak" not in row["source_stratum"]
        for row in queue_rows
    )


def test_current_second_review_template_is_blank_slot_two_only() -> None:
    rows = _read_tsv(SECOND_REVIEW_TEMPLATE)
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

    assert {row["reviewer_slot"] for row in rows} == {"2"}
    for row in rows:
        for field in blank_fields:
            assert row[field] == ""
        assert row["round_trip_oracle_used"] == "FALSE"
        assert row["label_grants_product_authority"] == "FALSE"
        assert row["may_touch_matrix"] == "FALSE"


def test_current_second_review_index_links_all_cases() -> None:
    html = SECOND_REVIEW_INDEX.read_text(encoding="utf-8")
    hrefs = re.findall(r'href="([^"]+)"', html)

    assert "Lockbox Second Review v1" in html
    assert "Gaussian15" in html
    assert html.count("<tr><td>") == 53
    assert hrefs
    assert not [
        href
        for href in hrefs
        if not (SECOND_REVIEW_INDEX.parent / href).resolve().exists()
    ]


def test_second_review_builder_can_write_to_custom_paths(tmp_path: Path) -> None:
    queue = tmp_path / "second_review_queue.tsv"
    template = tmp_path / "second_review_template.tsv"
    summary = tmp_path / "second_review_summary.json"
    index = tmp_path / "index.html"

    result = build_lockbox_second_review_pack(
        second_review_queue_path=queue,
        second_review_template_path=template,
        second_review_summary_path=summary,
        second_review_index_path=index,
    )

    assert result["problems"] == []
    assert len(_read_tsv(queue)) == 53
    assert len(_read_tsv(template)) == 53
    assert json.loads(summary.read_text(encoding="utf-8"))["case_counts"][
        "product_authority_rows"
    ] == 0
    assert index.exists()


def test_second_review_checker_rejects_prefilled_second_label(tmp_path: Path) -> None:
    queue, template, summary, index = _build_custom_pack(tmp_path)
    header, rows = _read_tsv_with_header(template)
    rows[0]["peak_choice_label"] = "correct"
    _write_tsv(template, header, rows)

    problems = check_lockbox_second_review_pack(
        second_review_queue_path=queue,
        second_review_template_path=template,
        second_review_summary_path=summary,
        second_review_index_path=index,
    )

    assert any("second-review template is stale" in problem for problem in problems)
    assert any(
        "peak_choice_label must be blank" in problem for problem in problems
    )


def test_second_review_checker_rejects_queue_authority_flag(tmp_path: Path) -> None:
    queue, template, summary, index = _build_custom_pack(tmp_path)
    header, rows = _read_tsv_with_header(queue)
    rows[0]["may_feed_product_writer"] = "TRUE"
    _write_tsv(queue, header, rows)

    problems = check_lockbox_second_review_pack(
        second_review_queue_path=queue,
        second_review_template_path=template,
        second_review_summary_path=summary,
        second_review_index_path=index,
    )

    assert any("second-review queue is stale" in problem for problem in problems)
    assert any(
        "may_feed_product_writer must be FALSE" in problem for problem in problems
    )


def test_second_review_checker_rejects_open_ai_challenge_flag(
    tmp_path: Path,
) -> None:
    queue, template, summary, index = _build_custom_pack(tmp_path)
    ai_summary = tmp_path / "ai_challenge_summary.json"
    payload = json.loads(AI_CHALLENGE_RESULT_SUMMARY.read_text(encoding="utf-8"))
    payload["decision"] = "ai_challenge_owner_recheck_required"
    payload["case_counts"]["flagged_cases"] = 1
    payload["flagged_cases"] = [
        {
            "lockbox_case_id": "LOCKBOXV1_60CEB35837FAF38CC4DE9021",
            "challenge_result": "visual_contradiction_suspected",
        },
    ]
    ai_summary.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    problems = check_lockbox_second_review_pack(
        ai_challenge_result_summary_path=ai_summary,
        second_review_queue_path=queue,
        second_review_template_path=template,
        second_review_summary_path=summary,
        second_review_index_path=index,
    )

    assert any("AI challenge result summary JSON is stale" in p for p in problems)
    assert any("requires AI challenge no-owner-recheck decision" in p for p in problems)
    assert any("requires zero AI challenge flags" in p for p in problems)
    assert any("requires empty AI flagged_cases" in p for p in problems)


def test_second_review_checker_rejects_non_gaussian_queue_row(
    tmp_path: Path,
) -> None:
    queue, template, summary, index = _build_custom_pack(tmp_path)
    header, rows = _read_tsv_with_header(queue)
    rows[0]["gaussian_smoothing_method"] = "raw_trace"
    _write_tsv(queue, header, rows)

    problems = check_lockbox_second_review_pack(
        second_review_queue_path=queue,
        second_review_template_path=template,
        second_review_summary_path=summary,
        second_review_index_path=index,
    )

    assert any("second-review queue is stale" in problem for problem in problems)
    assert any(
        "gaussian_smoothing_method must be gaussian_15" in problem
        for problem in problems
    )


def test_second_review_checker_rejects_stale_static_plot_hash(
    tmp_path: Path,
) -> None:
    static_index = tmp_path / "bundle_index.tsv"
    header, rows = _read_tsv_with_header(STATIC_BUNDLE_INDEX)
    row = next(row for row in rows if row["plot_status"] == "plotted_gaussian15")
    row["plot_sha256"] = "0" * 64
    _write_tsv(static_index, header, rows)

    problems = check_lockbox_second_review_pack(
        static_bundle_index_path=static_index,
        second_review_queue_path=tmp_path / "queue.tsv",
        second_review_template_path=tmp_path / "template.tsv",
        second_review_summary_path=tmp_path / "summary.json",
        second_review_index_path=tmp_path / "index.html",
    )

    assert any("plot_sha256 must match linked PNG" in problem for problem in problems)


def test_second_review_checker_rejects_stale_summary(tmp_path: Path) -> None:
    queue, template, summary, index = _build_custom_pack(tmp_path)
    payload = json.loads(summary.read_text(encoding="utf-8"))
    payload["decision"] = "stale"
    summary.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    problems = check_lockbox_second_review_pack(
        second_review_queue_path=queue,
        second_review_template_path=template,
        second_review_summary_path=summary,
        second_review_index_path=index,
    )

    assert any("second-review summary JSON is stale" in problem for problem in problems)


def _build_custom_pack(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    queue = tmp_path / "second_review_queue.tsv"
    template = tmp_path / "second_review_template.tsv"
    summary = tmp_path / "second_review_summary.json"
    index = tmp_path / "index.html"
    build_lockbox_second_review_pack(
        second_review_queue_path=queue,
        second_review_template_path=template,
        second_review_summary_path=summary,
        second_review_index_path=index,
    )
    return queue, template, summary, index


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
