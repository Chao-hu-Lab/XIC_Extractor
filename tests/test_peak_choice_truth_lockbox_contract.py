import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

import pytest

from scripts.build_peak_choice_truth_lockbox import (
    FAILED_ORACLE_PATHS,
    INDEX_PATH,
    LABEL_LOG_HEADER,
    MANIFEST_HEADER,
    MANUAL_NEGATIVE_PATH,
    REVIEW_QUEUE_PATH,
    SOURCE_AUDIT_PATH,
    build_lockbox,
)

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "docs/superpowers/specs/truth_label_schema.v1.json"
MANIFEST_PATH = ROOT / "docs/superpowers/validation/lockbox_sampling_manifest_v1.tsv"
LABEL_LOG_PATH = ROOT / "docs/superpowers/validation/reviewer_label_log_v1.tsv"
SUMMARY_PATH = (
    ROOT / "docs/superpowers/validation/inter_reviewer_agreement_summary_v1.json"
)


def test_truth_label_schema_matches_lockbox_headers() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    assert schema["required_manifest_columns"] == MANIFEST_HEADER
    assert schema["required_label_log_columns"] == LABEL_LOG_HEADER
    assert schema["authority_rules"]["may_touch_matrix"] is False
    assert schema["authority_rules"]["may_grant_product_authority"] is False
    assert schema["source_policy"]["round_trip_oracle_is_not_peak_choice_truth"]
    assert schema["source_policy"][
        "quality_blockers_are_sampling_context_not_writer_predicates"
    ]


def test_lockbox_generator_is_deterministic_and_closed(
    tmp_path: Path,
) -> None:
    missing_sources = _missing_generator_sources()
    if missing_sources:
        pytest.skip(
            "lockbox generator requires external source artifacts: "
            + ", ".join(path.as_posix() for path in missing_sources),
        )

    result = build_lockbox(tmp_path)
    rows = _read_tsv(result["manifest_path"])
    log_rows = _read_tsv(result["label_log_path"])
    summary = json.loads(Path(result["summary_path"]).read_text(encoding="utf-8"))

    assert result["case_count"] == 72
    assert len(rows) == 72
    assert not log_rows
    assert summary["status"] == "no_labels_collected"
    assert summary["labels_collected"] == 0
    assert summary["authority"]["may_touch_matrix"] is False
    assert summary["authority"]["may_grant_product_authority"] is False
    assert summary["round_trip_oracle_truth_policy"] == (
        "forbidden_as_peak_choice_or_area_truth"
    )
    assert {row["may_touch_matrix"] for row in rows} == {"FALSE"}
    assert {row["may_grant_product_authority"] for row in rows} == {"FALSE"}
    assert {row["truth_label_status"] for row in rows} == {"unlabeled"}
    assert {row["required_reviewer_count"] for row in rows} == {"2"}
    assert all("not_assessed" in row["allowed_truth_labels"] for row in rows)
    assert all("unavailable" in row["allowed_truth_labels"] for row in rows)


def test_lockbox_manifest_covers_required_strata() -> None:
    rows = _read_tsv(MANIFEST_PATH)
    counts = Counter(row["source_stratum"] for row in rows)

    assert len(rows) == 72
    assert counts == {
        "approved_write_ready_control": 18,
        "unresolved_high_signal_dirty": 6,
        "unresolved_low_height": 6,
        "unresolved_apex_delta": 6,
        "unresolved_shape_width_scan": 6,
        "missing_overlay_evidence_gap": 12,
        "failed_oracle_negative": 12,
        "manual_wrong_peak_or_no_peak": 6,
    }


def test_lockbox_splits_by_family_not_row_id() -> None:
    rows = _read_tsv(MANIFEST_PATH)
    split_by_family: dict[str, set[str]] = defaultdict(set)
    split_by_row: dict[str, set[str]] = defaultdict(set)

    for row in rows:
        assert row["split_basis"] == "family_id"
        assert row["lockbox_split_id"].startswith("family_")
        split_by_family[row["family_id"]].add(row["lockbox_split_id"])
        if row["row_id"]:
            split_by_row[row["row_id"]].add(row["lockbox_split_id"])

    assert all(len(splits) == 1 for splits in split_by_family.values())
    assert len(split_by_family) < len(rows)
    assert split_by_row


def test_lockbox_rows_preserve_source_decision_boundaries() -> None:
    rows = _read_tsv(MANIFEST_PATH)
    by_stratum = defaultdict(list)
    for row in rows:
        by_stratum[row["source_stratum"]].append(row)

    assert {
        row["mechanical_decision"] for row in by_stratum["approved_write_ready_control"]
    } == {"write_ready"}
    approved = by_stratum["approved_write_ready_control"]
    assert {row["evidence_grade"] for row in approved} == {"A"}
    assert {row["source_write_authority"] for row in approved} == {"TRUE"}

    unresolved = (
        by_stratum["unresolved_high_signal_dirty"]
        + by_stratum["unresolved_low_height"]
        + by_stratum["unresolved_apex_delta"]
        + by_stratum["unresolved_shape_width_scan"]
    )
    assert {row["mechanical_decision"] for row in unresolved} == {"evidence_required"}
    assert {row["evidence_grade"] for row in unresolved} == {"C"}
    assert {row["source_write_authority"] for row in unresolved} == {"FALSE"}
    assert all(row["review_packet_id"] for row in unresolved)
    assert all(row["trace_data_path"] for row in unresolved)
    assert all(row["overlay_png_path"] for row in unresolved)

    missing = by_stratum["missing_overlay_evidence_gap"]
    assert {row["evidence_grade"] for row in missing} == {"D"}
    assert {row["source_write_authority"] for row in missing} == {"FALSE"}
    assert {row["area_label_required"] for row in missing} == {"FALSE"}
    assert all("missing_overlay" in row["risk_tags"] for row in missing)

    failed_oracle = by_stratum["failed_oracle_negative"]
    assert {row["source_write_authority"] for row in failed_oracle} == {"FALSE"}
    assert all("failed_oracle:" in row["risk_tags"] for row in failed_oracle)
    assert all("round_trip_oracle_not_truth" in row["notes"] for row in failed_oracle)

    manual = by_stratum["manual_wrong_peak_or_no_peak"]
    assert {row["source_write_authority"] for row in manual} == {"FALSE"}
    assert {row["mechanical_decision"] for row in manual} == {"known_manual_negative"}
    assert {row["risk_tags"] for row in manual} <= {"wrong_peak", "no_peak"}


def test_reviewer_label_log_and_summary_are_templates_not_labels() -> None:
    with LABEL_LOG_PATH.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle, delimiter="\t")
        assert next(reader) == LABEL_LOG_HEADER
        assert list(reader) == []

    summary = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
    assert summary["status"] == "no_labels_collected"
    assert summary["case_count"] == 72
    assert summary["labels_collected"] == 0
    assert summary["agreement_metrics"] == {
        "area_label_percent_agreement": None,
        "cohen_kappa_area_label": None,
        "cohen_kappa_peak_choice": None,
        "peak_choice_percent_agreement": None,
    }


def _read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def _missing_generator_sources() -> list[Path]:
    return [
        path
        for path in (
            INDEX_PATH,
            REVIEW_QUEUE_PATH,
            SOURCE_AUDIT_PATH,
            MANUAL_NEGATIVE_PATH,
            *FAILED_ORACLE_PATHS,
        )
        if not path.exists()
    ]
