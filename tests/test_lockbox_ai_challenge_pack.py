import csv
import json
import re
from pathlib import Path

from scripts.build_lockbox_ai_challenge_pack import (
    AI_CHALLENGE_INDEX,
    AI_CHALLENGE_QUEUE,
    AI_CHALLENGE_SUMMARY,
    AI_CHALLENGE_TEMPLATE,
    OWNER_BOUNDARY_CONFIRMATION,
    _source_hashes,
    build_lockbox_ai_challenge_pack,
    check_lockbox_ai_challenge_pack,
)
from scripts.build_lockbox_next_action_plan import NEXT_ACTION_PLAN


def test_current_lockbox_ai_challenge_pack_validates() -> None:
    assert check_lockbox_ai_challenge_pack() == []


def test_current_ai_challenge_counts_and_authority() -> None:
    queue_rows = _read_tsv(AI_CHALLENGE_QUEUE)
    template_rows = _read_tsv(AI_CHALLENGE_TEMPLATE)
    summary = json.loads(AI_CHALLENGE_SUMMARY.read_text(encoding="utf-8"))

    assert len(queue_rows) == 72
    assert len(template_rows) == 72
    assert summary["decision"] == "ai_challenge_packet_ready_for_72_cases"
    assert summary["case_counts"] == {
        "total_cases": 72,
        "challenge_template_rows": 72,
        "visual_contradiction_challenge_cases": 53,
        "route_or_evidence_integrity_cases": 19,
        "product_authority_rows": 0,
    }
    assert summary["challenge_scope_counts"] == {
        "evidence_gap_route_check": 1,
        "manual_negative_route_check": 6,
        "parked_nontruth_route_check": 12,
        "visual_contradiction_challenge": 53,
    }
    assert all(value is False for value in summary["authority_rules"].values())
    assert {row["may_satisfy_reviewer_slot2"] for row in queue_rows} == {"FALSE"}
    assert {row["may_feed_product_writer"] for row in queue_rows} == {"FALSE"}
    assert {row["may_touch_matrix"] for row in queue_rows} == {"FALSE"}
    assert {row["may_grant_product_authority"] for row in queue_rows} == {"FALSE"}
    assert {row["broad_backfill_unparked"] for row in queue_rows} == {"FALSE"}


def test_current_ai_challenge_queue_covers_next_action_cases() -> None:
    queue_rows = _read_tsv(AI_CHALLENGE_QUEUE)
    next_action_rows = _read_tsv(NEXT_ACTION_PLAN)

    assert {row["lockbox_case_id"] for row in queue_rows} == {
        row["lockbox_case_id"] for row in next_action_rows
    }
    visual = [
        row
        for row in queue_rows
        if row["challenge_scope"] == "visual_contradiction_challenge"
    ]
    non_visual = [
        row
        for row in queue_rows
        if row["challenge_scope"] != "visual_contradiction_challenge"
    ]
    assert len(visual) == 53
    assert {row["plot_status"] for row in visual} == {"plotted_gaussian15"}
    assert {row["gaussian_smoothing_method"] for row in visual} == {"gaussian_15"}
    assert {row["gaussian_window_points"] for row in visual} == {"15"}
    assert all(
        "visual_contradiction_suspected" in row["allowed_agent_outputs"]
        for row in visual
    )
    assert len(non_visual) == 19
    assert {row["next_action"] for row in non_visual} == {
        "park_roundtrip_oracle_negative_as_nontruth",
        "recover_or_mark_gaussian_boundary_unavailable",
        "use_existing_manual_negative_control",
    }
    assert all(
        "visual_contradiction_suspected" not in row["allowed_agent_outputs"]
        for row in non_visual
    )


def test_current_ai_challenge_template_is_blank_and_non_authoritative() -> None:
    rows = _read_tsv(AI_CHALLENGE_TEMPLATE)
    blank_fields = (
        "challenge_reviewer_id",
        "reviewed_at_utc",
        "challenge_result",
        "challenge_reason_code",
        "challenge_notes",
        "evidence_viewed",
    )
    for row in rows:
        for field in blank_fields:
            assert row[field] == ""
        assert row["may_satisfy_reviewer_slot2"] == "FALSE"
        assert row["may_feed_product_writer"] == "FALSE"
        assert row["may_touch_matrix"] == "FALSE"
        assert row["may_grant_product_authority"] == "FALSE"
        assert row["broad_backfill_unparked"] == "FALSE"


def test_current_ai_challenge_index_links_existing_files() -> None:
    html = AI_CHALLENGE_INDEX.read_text(encoding="utf-8")
    hrefs = re.findall(r'href="([^"]+)"', html)

    assert "Lockbox AI Challenge v1" in html
    assert html.count("<tr><td>") == 72
    assert hrefs
    assert not [
        href
        for href in hrefs
        if not (AI_CHALLENGE_INDEX.parent / href).resolve().exists()
    ]


def test_ai_challenge_builder_can_write_to_custom_paths(tmp_path: Path) -> None:
    queue = tmp_path / "queue.tsv"
    template = tmp_path / "template.tsv"
    summary = tmp_path / "summary.json"
    index = tmp_path / "index.html"

    result = build_lockbox_ai_challenge_pack(
        ai_challenge_queue_path=queue,
        ai_challenge_template_path=template,
        ai_challenge_summary_path=summary,
        ai_challenge_index_path=index,
    )

    assert result["problems"] == []
    assert len(_read_tsv(queue)) == 72
    assert len(_read_tsv(template)) == 72
    assert json.loads(summary.read_text(encoding="utf-8"))["case_counts"][
        "product_authority_rows"
    ] == 0
    assert index.exists()


def test_ai_challenge_source_hashes_canonicalize_validation_text_line_endings(
    tmp_path: Path,
) -> None:
    validation_dir = tmp_path / "docs/superpowers/validation"
    validation_dir.mkdir(parents=True)
    next_action_plan = validation_dir / "next_action.tsv"
    static_bundle_index = validation_dir / "static_index.html"
    label_log = validation_dir / "labels.tsv"
    owner_boundary = validation_dir / "owner_boundary.json"
    case_html = validation_dir / "case.html"
    plot_png = validation_dir / "plot.png"
    for path in (
        next_action_plan,
        static_bundle_index,
        label_log,
        owner_boundary,
        case_html,
    ):
        path.write_bytes(b"header\nvalue\n")
    plot_png.write_bytes(b"png bytes")
    static_row = {
        "case_html_path": str(case_html),
        "review_plot_png_path": str(plot_png),
        "source_artifact_hashes": "nested_source=ABC",
    }

    lf_hashes = _source_hashes(
        static_row,
        next_action_plan_path=next_action_plan,
        static_bundle_index_path=static_bundle_index,
        label_log_path=label_log,
        owner_boundary_confirmation_path=owner_boundary,
    )
    for path in (
        next_action_plan,
        static_bundle_index,
        label_log,
        owner_boundary,
        case_html,
    ):
        path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))

    assert (
        _source_hashes(
            static_row,
            next_action_plan_path=next_action_plan,
            static_bundle_index_path=static_bundle_index,
            label_log_path=label_log,
            owner_boundary_confirmation_path=owner_boundary,
        )
        == lf_hashes
    )


def test_ai_challenge_checker_rejects_template_authority_flag(
    tmp_path: Path,
) -> None:
    queue, template, summary, index = _build_custom_pack(tmp_path)
    header, rows = _read_tsv_with_header(template)
    rows[0]["may_satisfy_reviewer_slot2"] = "TRUE"
    rows[0]["may_feed_product_writer"] = "TRUE"
    _write_tsv(template, header, rows)

    problems = check_lockbox_ai_challenge_pack(
        ai_challenge_queue_path=queue,
        ai_challenge_template_path=template,
        ai_challenge_summary_path=summary,
        ai_challenge_index_path=index,
    )

    assert any("AI challenge template is stale" in problem for problem in problems)
    assert any("may_satisfy_reviewer_slot2 must be FALSE" in p for p in problems)
    assert any("may_feed_product_writer must be FALSE" in p for p in problems)


def test_ai_challenge_checker_rejects_prefilled_template(
    tmp_path: Path,
) -> None:
    queue, template, summary, index = _build_custom_pack(tmp_path)
    header, rows = _read_tsv_with_header(template)
    rows[0]["challenge_result"] = "no_issue"
    _write_tsv(template, header, rows)

    problems = check_lockbox_ai_challenge_pack(
        ai_challenge_queue_path=queue,
        ai_challenge_template_path=template,
        ai_challenge_summary_path=summary,
        ai_challenge_index_path=index,
    )

    assert any("AI challenge template is stale" in problem for problem in problems)
    assert any("challenge_result must be blank" in problem for problem in problems)


def test_ai_challenge_checker_rejects_stale_owner_boundary_hash(
    tmp_path: Path,
) -> None:
    owner_boundary = tmp_path / "owner_boundary.json"
    payload = json.loads(OWNER_BOUNDARY_CONFIRMATION.read_text(encoding="utf-8"))
    payload["source_artifacts"]["label_log_sha256"] = "0" * 64
    owner_boundary.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    problems = check_lockbox_ai_challenge_pack(
        owner_boundary_confirmation_path=owner_boundary,
        ai_challenge_queue_path=tmp_path / "queue.tsv",
        ai_challenge_template_path=tmp_path / "template.tsv",
        ai_challenge_summary_path=tmp_path / "summary.json",
        ai_challenge_index_path=tmp_path / "index.html",
    )

    assert any(
        "owner boundary source_artifacts.label_log hash mismatch" in p
        for p in problems
    )


def test_ai_challenge_checker_rejects_queue_authority_flag(
    tmp_path: Path,
) -> None:
    queue, template, summary, index = _build_custom_pack(tmp_path)
    header, rows = _read_tsv_with_header(queue)
    rows[0]["may_touch_matrix"] = "TRUE"
    _write_tsv(queue, header, rows)

    problems = check_lockbox_ai_challenge_pack(
        ai_challenge_queue_path=queue,
        ai_challenge_template_path=template,
        ai_challenge_summary_path=summary,
        ai_challenge_index_path=index,
    )

    assert any("AI challenge queue is stale" in problem for problem in problems)
    assert any("may_touch_matrix must be FALSE" in p for p in problems)


def test_ai_challenge_checker_rejects_stale_index(
    tmp_path: Path,
) -> None:
    queue, template, summary, index = _build_custom_pack(tmp_path)
    index.write_text(
        index.read_text(encoding="utf-8").replace(
            "Lockbox AI Challenge v1",
            "Stale Lockbox AI Challenge v1",
            1,
        ),
        encoding="utf-8",
    )

    problems = check_lockbox_ai_challenge_pack(
        ai_challenge_queue_path=queue,
        ai_challenge_template_path=template,
        ai_challenge_summary_path=summary,
        ai_challenge_index_path=index,
    )

    assert any("AI challenge HTML index is stale" in problem for problem in problems)


def test_ai_challenge_checker_rejects_stale_summary_authority(
    tmp_path: Path,
) -> None:
    queue, template, summary, index = _build_custom_pack(tmp_path)
    payload = json.loads(summary.read_text(encoding="utf-8"))
    payload["authority_rules"]["may_feed_product_writer"] = True
    summary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")

    problems = check_lockbox_ai_challenge_pack(
        ai_challenge_queue_path=queue,
        ai_challenge_template_path=template,
        ai_challenge_summary_path=summary,
        ai_challenge_index_path=index,
    )

    assert any("AI challenge summary JSON is stale" in problem for problem in problems)
    assert any(
        "AI challenge summary authority_rules.may_feed_product_writer must be false"
        in problem
        for problem in problems
    )


def _build_custom_pack(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    queue = tmp_path / "queue.tsv"
    template = tmp_path / "template.tsv"
    summary = tmp_path / "summary.json"
    index = tmp_path / "index.html"
    build_lockbox_ai_challenge_pack(
        ai_challenge_queue_path=queue,
        ai_challenge_template_path=template,
        ai_challenge_summary_path=summary,
        ai_challenge_index_path=index,
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