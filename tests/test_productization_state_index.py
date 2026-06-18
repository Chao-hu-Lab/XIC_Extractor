import csv
import json
from pathlib import Path

from scripts.check_productization_state import (
    DEFAULT_AUTHORITY_MANIFEST,
    DEFAULT_CONTROL_PLANE,
    DEFAULT_HANDOFF,
    DEFAULT_SCHEMA,
    DEFAULT_STATUS_INDEX,
    check_productization_state,
)


def test_productization_state_index_accepts_current_artifacts() -> None:
    assert check_productization_state() == []


def test_status_schema_matches_index_header() -> None:
    schema = json.loads(DEFAULT_SCHEMA.read_text(encoding="utf-8"))
    header, rows = _read_tsv(DEFAULT_STATUS_INDEX)

    assert header == schema["required_status_index_columns"]
    assert {row["lane_id"] for row in rows} == set(schema["required_lane_ids"])
    assert len(rows) == len(schema["required_lane_ids"])


def test_only_current_backfill_scope_has_writer_authority() -> None:
    _, rows = _read_tsv(DEFAULT_STATUS_INDEX)
    authority_rows = [row for row in rows if row["write_authority"] == "TRUE"]

    assert [row["lane_id"] for row in authority_rows] == [
        "backfill_current_write_ready_scope"
    ]
    authority = authority_rows[0]
    assert authority["product_authority_scope"] == "backfill_policy_write_ready_rows"
    assert authority["row_count"] == "511"
    assert authority["may_touch_matrix"] == "TRUE"


def test_peak_choice_lockbox_status_points_to_ai_challenge_results() -> None:
    _, rows = _read_tsv(DEFAULT_STATUS_INDEX)
    row = next(
        item for item in rows if item["lane_id"] == "peak_choice_truth_lockbox_v1"
    )

    assert (
        row["current_artifact"]
        == "docs/superpowers/validation/lockbox_ai_challenge_result_summary_v1.json"
    )
    assert row["public_surface"] == "lockbox_ai_challenge_result_v1"
    assert "ai_challenge_no_owner_recheck_required" in row["notes"]
    assert "owner_rule_detected_left_peak_resolved" in row["notes"]
    assert row["write_authority"] == "FALSE"


def test_checker_rejects_parked_broad_backfill_authority(tmp_path: Path) -> None:
    mutated = _mutated_index(
        tmp_path,
        "broad_backfill_autowrite",
        {
            "write_authority": "TRUE",
            "product_authority_scope": "backfill_policy_write_ready_rows",
            "may_touch_matrix": "TRUE",
        },
    )

    problems = _check_with_index(mutated)

    assert any("parked lane grants authority" in problem for problem in problems)
    assert any(
        "broad_backfill_autowrite must stay parked" in problem
        for problem in problems
    )


def test_checker_rejects_review_truth_or_recovery_authority(tmp_path: Path) -> None:
    for lane_id in (
        "review_packet_workflow_v1",
        "peak_choice_truth_lockbox_v1",
        "missing_overlay_evidence_recovery_v1",
    ):
        mutated = _mutated_index(
            tmp_path,
            lane_id,
            {
                "write_authority": "TRUE",
                "product_authority_scope": "backfill_policy_write_ready_rows",
                "may_touch_matrix": "TRUE",
            },
        )

        problems = _check_with_index(mutated)

        assert any("lane grants authority" in problem for problem in problems)


def test_checker_rejects_non_writer_scope_without_write_flag(tmp_path: Path) -> None:
    mutated = _mutated_index(
        tmp_path,
        "review_packet_workflow_v1",
        {"product_authority_scope": "backfill_policy_write_ready_rows"},
    )

    problems = _check_with_index(mutated)

    assert any("non-writer row has authority scope" in problem for problem in problems)


def test_checker_rejects_non_writer_product_output_changes(tmp_path: Path) -> None:
    mutated = _mutated_index(
        tmp_path,
        "peak_choice_truth_lockbox_v1",
        {
            "may_change_workbook": "TRUE",
            "may_change_selected_peak": "TRUE",
            "may_change_selected_area": "TRUE",
            "may_change_counted_detection": "TRUE",
        },
    )

    problems = _check_with_index(mutated)

    assert any(
        "non-writer row changes product output" in problem
        for problem in problems
    )


def test_checker_rejects_blank_doc_anchors(tmp_path: Path) -> None:
    mutated = _mutated_index(
        tmp_path,
        "mechanical_adjudication_contract_v1",
        {"handoff_anchor": "", "control_plane_anchor": ""},
    )

    problems = _check_with_index(mutated)

    assert any("handoff anchor is required" in problem for problem in problems)
    assert any("control-plane anchor is required" in problem for problem in problems)


def test_checker_rejects_artifact_hash_drift(tmp_path: Path) -> None:
    mutated = _mutated_index(
        tmp_path,
        "mechanical_adjudication_contract_v1",
        {"artifact_sha256": "0" * 64},
    )

    problems = _check_with_index(mutated)

    assert any("artifact_sha256 mismatch" in problem for problem in problems)


def _check_with_index(path: Path) -> list[str]:
    return check_productization_state(
        schema_path=DEFAULT_SCHEMA,
        status_index_path=path,
        authority_manifest_path=DEFAULT_AUTHORITY_MANIFEST,
        handoff_path=DEFAULT_HANDOFF,
        control_plane_path=DEFAULT_CONTROL_PLANE,
    )


def _mutated_index(
    tmp_path: Path,
    lane_id: str,
    updates: dict[str, str],
) -> Path:
    header, rows = _read_tsv(DEFAULT_STATUS_INDEX)
    for row in rows:
        if row["lane_id"] == lane_id:
            row.update(updates)
            break
    else:
        raise AssertionError(f"lane not found: {lane_id}")
    output = tmp_path / f"{lane_id}.tsv"
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=header)
        writer.writeheader()
        writer.writerows(rows)
    return output


def _read_tsv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        return list(reader.fieldnames or []), list(reader)
