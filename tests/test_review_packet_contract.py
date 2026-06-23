from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from scripts.check_productization_state import artifact_sha256

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "docs/superpowers/specs/review_packet_schema.v1.json"
QUEUE_PATH = ROOT / "docs/superpowers/validation/review_queue_v1.tsv"
DECISION_LOG_PATH = ROOT / "docs/superpowers/validation/review_decision_log_v1.tsv"
ADJUDICATION_INDEX_PATH = (
    ROOT / "docs/superpowers/validation/mechanical_adjudication_index_v1.tsv"
)

ALLOWED_ACTIONS = "approve_candidate;reject_candidate;escalate_unresolved"


def test_review_queue_matches_packet_schema_and_scope() -> None:
    schema = _read_json(SCHEMA_PATH)
    header, rows = _read_tsv(QUEUE_PATH)

    assert set(schema["packet_required_columns"]) <= set(header)
    assert len(rows) == 3015
    assert len({row["review_packet_id"] for row in rows}) == len(rows)
    assert len({row["row_id"] for row in rows}) == len(rows)

    assert {row["packet_status"] for row in rows} == {"review_ready"}
    assert {row["source_mechanical_decision"] for row in rows} == {
        "evidence_required"
    }
    assert {row["source_evidence_grade"] for row in rows} == {"C"}
    assert {row["why_machine_cannot_auto_write"] for row in rows} == {
        "independent_peak_choice_or_area_truth"
    }


def test_review_queue_is_approval_only_not_write_authority() -> None:
    _, rows = _read_tsv(QUEUE_PATH)

    assert {row["reviewer_allowed_actions"] for row in rows} == {ALLOWED_ACTIONS}
    assert {row["free_form_value_allowed"] for row in rows} == {"FALSE"}
    assert {row["approval_grants_product_authority"] for row in rows} == {
        "FALSE"
    }
    assert {row["approval_effect"] for row in rows} == {
        "review_decision_log_only"
    }
    assert {row["may_touch_matrix"] for row in rows} == {"FALSE"}


def test_review_queue_packets_have_trace_links_and_explicit_gaps() -> None:
    _, rows = _read_tsv(QUEUE_PATH)

    assert all(row["candidate_value_if_any"] for row in rows)
    assert all(row["candidate_area"] for row in rows)
    assert all(row["candidate_apex_rt_min"] for row in rows)
    assert all(row["candidate_start_rt_min"] for row in rows)
    assert all(row["candidate_end_rt_min"] for row in rows)
    assert all(row["trace_data_path"] for row in rows)
    assert all(row["overlay_png_path"] for row in rows)
    assert {row["nearest_competing_peak_context"] for row in rows} == {
        "not_available_in_current_artifacts"
    }


def test_review_decision_log_is_structured_and_empty_template() -> None:
    schema = _read_json(SCHEMA_PATH)
    header, rows = _read_tsv(DECISION_LOG_PATH)

    assert tuple(schema["decision_log_required_columns"]) == header
    assert rows == []


def test_review_queue_source_hash_links_to_adjudication_index() -> None:
    _, rows = _read_tsv(QUEUE_PATH)
    source_hash_sets = {row["source_hashes"] for row in rows}

    assert len(source_hash_sets) == 1
    source_hashes = _parse_semicolon_pairs(source_hash_sets.pop())
    assert (
        source_hashes["mechanical_adjudication_index"]
        == artifact_sha256(ADJUDICATION_INDEX_PATH)
    )


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_tsv(path: Path) -> tuple[tuple[str, ...], list[dict[str, str]]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        return tuple(reader.fieldnames or ()), list(reader)


def _parse_semicolon_pairs(value: str) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for part in value.split(";"):
        key, _, item = part.partition("=")
        parsed[key] = item
    return parsed
