"""Build/check sample-local MS1/identity evidence for Backfill expansion cells.

This no-RAW gate consumes the Backfill expansion opportunity cells and the
current 85RAW-derived CID-NL alignment evidence. It asks which active blank
cells already have exact sample-local alignment evidence, without granting any
Backfill writer authority or projecting row/family evidence onto cells.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.check_backfill_expansion_evidence_availability import (  # noqa: E402
    CELL_AVAILABILITY_COLUMNS,
    check_backfill_expansion_evidence_availability,
)
from scripts.check_backfill_expansion_evidence_availability import (
    DEFAULT_DOCS_DIR as DEFAULT_AVAILABILITY_DOCS_DIR,
)
from scripts.check_backfill_expansion_evidence_availability import (
    DEFAULT_OUTPUT_DIR as DEFAULT_AVAILABILITY_OUTPUT_DIR,
)
from xic_extractor.tabular_io import (  # noqa: E402
    file_sha256,
    optional_float,
    read_tsv_required,
    text_value,
    write_tsv,
)

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = "backfill_expansion_sample_local_ms1_evidence_v1"
DEFAULT_ALIGNMENT_DIR = (
    ROOT / "output/discovery/cid_nl_product_ready_alignment_85raw_20260620_fix3"
)
DEFAULT_ALIGNMENT_BACKFILL_CELL_EVIDENCE_TSV = (
    DEFAULT_ALIGNMENT_DIR / "alignment_backfill_cell_evidence.tsv"
)
DEFAULT_ALIGNMENT_REVIEW_TSV = DEFAULT_ALIGNMENT_DIR / "alignment_review.tsv"
DEFAULT_DOCS_DIR = (
    ROOT
    / "docs/superpowers/validation/"
    "backfill_expansion_sample_local_ms1_evidence_v1"
)
DEFAULT_OUTPUT_DIR = (
    ROOT / "output/validation/backfill_expansion_sample_local_ms1_evidence_v1"
)
DEFAULT_AVAILABILITY_SUMMARY_JSON = (
    DEFAULT_AVAILABILITY_DOCS_DIR
    / "backfill_expansion_evidence_availability_summary.json"
)
DEFAULT_AVAILABILITY_CHECKS_TSV = (
    DEFAULT_AVAILABILITY_DOCS_DIR
    / "backfill_expansion_evidence_availability_checks.tsv"
)
DEFAULT_AVAILABILITY_ROW_MANIFEST_TSV = (
    DEFAULT_AVAILABILITY_DOCS_DIR
    / "backfill_expansion_evidence_availability_row_manifest.tsv"
)
DEFAULT_AVAILABILITY_CELLS_TSV = (
    DEFAULT_AVAILABILITY_OUTPUT_DIR
    / "backfill_expansion_evidence_availability_cells.tsv"
)

ALIGNMENT_CELL_EVIDENCE_COLUMNS = (
    "schema_version",
    "feature_family_id",
    "group_hypothesis_id",
    "public_family_id",
    "sample_stem",
    "status",
    "production_cell_status",
    "write_matrix_value",
    "include_in_primary_matrix",
    "identity_decision",
    "row_flags",
    "area",
    "apex_rt",
    "height",
    "peak_start_rt",
    "peak_end_rt",
    "trace_quality",
    "scan_support_score",
    "gap_fill_state",
    "gap_fill_reason",
    "source_candidate_id",
    "source_raw_file",
    "neutral_loss_tag",
    "family_center_mz",
    "family_center_rt",
    "reason",
)
ALIGNMENT_REVIEW_COLUMNS = (
    "feature_family_id",
    "group_hypothesis_id",
    "public_family_id",
    "neutral_loss_tag",
    "family_center_mz",
    "family_center_rt",
    "family_product_mz",
    "detected_count",
    "identity_decision",
    "identity_confidence",
    "primary_evidence",
    "identity_reason",
    "quantifiable_detected_count",
    "quantifiable_rescue_count",
    "accepted_cell_count",
    "accepted_rescue_count",
    "review_rescue_count",
    "include_in_primary_matrix",
    "row_flags",
)
CHECK_COLUMNS = (
    "schema_version",
    "check_id",
    "status",
    "observed",
    "expected",
    "notes",
)
CELL_EVIDENCE_COLUMNS = (
    "schema_version",
    "opportunity_scope",
    "peak_hypothesis_id",
    "sample_stem",
    "alignment_cell_evidence_status",
    "alignment_cell_status",
    "production_cell_status",
    "alignment_write_matrix_value",
    "alignment_include_in_primary_matrix",
    "identity_decision",
    "neutral_loss_tag",
    "trace_quality",
    "scan_support_score",
    "area",
    "apex_rt",
    "height",
    "peak_start_rt",
    "peak_end_rt",
    "gap_fill_state",
    "gap_fill_reason",
    "source_candidate_id",
    "source_raw_file",
    "family_center_mz",
    "family_center_rt",
    "row_flags",
    "cell_evidence_reason",
    "raw_trace_evidence_status",
    "sample_trace_support_status",
    "product_authority_effect",
    "next_gate",
)
ROW_MANIFEST_COLUMNS = (
    "schema_version",
    "row_scope",
    "peak_hypothesis_id",
    "candidate_cell_count",
    "alignment_cell_evidence_present_cell_count",
    "alignment_cell_evidence_missing_cell_count",
    "review_rescue_cell_count",
    "dna_dr_tagged_cell_count",
    "production_family_identity_cell_count",
    "raw_trace_evidence_present_cell_count",
    "sample_trace_support_cell_count",
    "sample_trace_review_cell_count",
    "alignment_review_identity_decision",
    "alignment_review_identity_confidence",
    "alignment_review_neutral_loss_tag",
    "alignment_review_row_flags",
    "product_authority_effect",
    "next_gate",
)
OVERLAY_QUEUE_COLUMNS = (
    "rank",
    "feature_family_id",
    "seed_group_id",
    "family_center_mz",
    "family_center_rt",
    "suggested_rt_min",
    "suggested_rt_max",
    "suggested_output_prefix",
    "candidate_cell_count",
    "alignment_cell_evidence_present_cell_count",
    "alignment_cell_evidence_missing_cell_count",
    "backfill_request_ppm",
    "seed_window_basis",
    "product_authority_effect",
    "next_gate",
    "suggested_overlay_command_args",
)
EXPECTED_COUNTS = {
    "active_pressure_cell_count": 929,
    "alignment_cell_evidence_present_cell_count": 675,
    "alignment_cell_evidence_missing_cell_count": 254,
    "review_rescue_cell_count": 675,
    "dna_dr_tagged_cell_count": 675,
    "production_family_identity_cell_count": 675,
    "alignment_review_row_count": 20,
    "overlay_queue_row_count": 20,
}
EXPECTED_CHECK_IDS = (
    "availability_checker_pass",
    "active_pressure_cell_count",
    "alignment_cell_evidence_present_count",
    "alignment_cell_evidence_missing_count",
    "all_present_alignment_rows_are_review_rescue",
    "all_present_alignment_rows_have_dna_dr_tag",
    "all_present_alignment_rows_have_production_family_identity",
    "alignment_review_row_count",
    "overlay_queue_row_count",
    "no_raw_or_writer_changes",
    "no_row_or_family_projection",
)


def build_backfill_expansion_sample_local_ms1_evidence(
    *,
    docs_dir: Path = DEFAULT_DOCS_DIR,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    availability_summary_json: Path = DEFAULT_AVAILABILITY_SUMMARY_JSON,
    availability_checks_tsv: Path = DEFAULT_AVAILABILITY_CHECKS_TSV,
    availability_row_manifest_tsv: Path = DEFAULT_AVAILABILITY_ROW_MANIFEST_TSV,
    availability_cells_tsv: Path = DEFAULT_AVAILABILITY_CELLS_TSV,
    alignment_backfill_cell_evidence_tsv: Path = (
        DEFAULT_ALIGNMENT_BACKFILL_CELL_EVIDENCE_TSV
    ),
    alignment_review_tsv: Path = DEFAULT_ALIGNMENT_REVIEW_TSV,
) -> dict[str, Any]:
    availability_problems = check_backfill_expansion_evidence_availability(
        summary_json=availability_summary_json,
        checks_tsv=availability_checks_tsv,
        row_manifest_tsv=availability_row_manifest_tsv,
    )
    opportunity_rows = read_tsv_required(
        availability_cells_tsv,
        CELL_AVAILABILITY_COLUMNS,
    )
    active_rows = [
        row
        for row in opportunity_rows
        if text_value(row.get("opportunity_scope")) == "active_default_row_blank_cell"
    ]
    active_keys = {
        (text_value(row.get("peak_hypothesis_id")), text_value(row.get("sample_stem")))
        for row in active_rows
    }
    active_row_ids = {row_id for row_id, _sample in active_keys}
    review_by_row = _alignment_review_by_row(alignment_review_tsv, active_row_ids)
    evidence_by_key = _matching_alignment_cell_evidence(
        alignment_backfill_cell_evidence_tsv,
        active_keys=active_keys,
    )

    facts = _sample_local_facts(
        active_rows=active_rows,
        evidence_by_key=evidence_by_key,
        review_by_row=review_by_row,
        availability_problem_count=len(availability_problems),
    )
    checks = _check_rows(facts)
    failed = [row["check_id"] for row in checks if row["status"] != "pass"]
    if failed:
        raise ValueError(
            "Backfill expansion sample-local MS1 evidence failed: "
            + ";".join(failed),
        )

    docs_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    checks_tsv = docs_dir / "backfill_expansion_sample_local_ms1_evidence_checks.tsv"
    row_manifest_tsv = (
        docs_dir / "backfill_expansion_sample_local_ms1_evidence_row_manifest.tsv"
    )
    cell_evidence_tsv = (
        output_dir / "backfill_expansion_sample_local_ms1_evidence_cells.tsv"
    )
    overlay_queue_tsv = (
        output_dir / "backfill_expansion_sample_local_ms1_overlay_queue.tsv"
    )
    summary_json = (
        docs_dir / "backfill_expansion_sample_local_ms1_evidence_summary.json"
    )

    write_tsv(checks_tsv, checks, CHECK_COLUMNS, extrasaction="raise")
    write_tsv(
        row_manifest_tsv,
        facts["row_manifest_rows"],
        ROW_MANIFEST_COLUMNS,
        extrasaction="raise",
    )
    write_tsv(
        cell_evidence_tsv,
        facts["cell_evidence_rows"],
        CELL_EVIDENCE_COLUMNS,
        extrasaction="raise",
    )
    write_tsv(
        overlay_queue_tsv,
        facts["overlay_queue_rows"],
        OVERLAY_QUEUE_COLUMNS,
        extrasaction="raise",
    )
    payload = _summary_payload(
        facts=facts,
        checks_tsv=checks_tsv,
        row_manifest_tsv=row_manifest_tsv,
        cell_evidence_tsv=cell_evidence_tsv,
        overlay_queue_tsv=overlay_queue_tsv,
        availability_summary_json=availability_summary_json,
        availability_checks_tsv=availability_checks_tsv,
        availability_row_manifest_tsv=availability_row_manifest_tsv,
        availability_cells_tsv=availability_cells_tsv,
        alignment_backfill_cell_evidence_tsv=alignment_backfill_cell_evidence_tsv,
        alignment_review_tsv=alignment_review_tsv,
    )
    summary_json.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _write_readme(docs_dir / "README.md", payload=payload)
    return payload


def check_backfill_expansion_sample_local_ms1_evidence(
    *,
    summary_json: Path = (
        DEFAULT_DOCS_DIR
        / "backfill_expansion_sample_local_ms1_evidence_summary.json"
    ),
    checks_tsv: Path = (
        DEFAULT_DOCS_DIR / "backfill_expansion_sample_local_ms1_evidence_checks.tsv"
    ),
    row_manifest_tsv: Path = (
        DEFAULT_DOCS_DIR
        / "backfill_expansion_sample_local_ms1_evidence_row_manifest.tsv"
    ),
) -> list[str]:
    problems: list[str] = []
    try:
        payload = _read_json_object(summary_json)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return [str(exc)]

    expected_fields: tuple[tuple[str, object], ...] = (
        ("schema_version", SCHEMA_VERSION),
        ("status", "pass"),
        (
            "validation_label",
            "no_raw_backfill_expansion_sample_local_ms1_identity_evidence",
        ),
        ("product_lane", "backfill"),
        ("strongest_evidence_tier", "85RAW-derived alignment cell evidence"),
        (
            "release_decision",
            "raw_overlay_trace_identity_gate_for_675_present_cells_and_hold_254_missing_alignment_cells",
        ),
        ("raw_or_85raw_ran", False),
        ("product_writer_changed_by_checker", False),
        ("default_quant_matrix_changed_by_checker", False),
        ("workbook_or_gui_changed", False),
        ("selected_peak_area_or_counting_changed", False),
        ("backfill_writer_authority_changed_by_checker", False),
        ("broad_backfill_unparked", False),
        ("candidate_rows_are_matrix_rows", False),
        ("row_or_family_evidence_projected_to_cells", False),
        ("sample_local_key_match_required", True),
    )
    for field, expected in expected_fields:
        if payload.get(field) != expected:
            problems.append(f"summary {field} mismatch")
    for field, expected in EXPECTED_COUNTS.items():
        if payload.get(field) != expected:
            problems.append(f"summary {field} mismatch")

    _check_summary_artifact_hash(
        payload=payload,
        artifact_id="checks_tsv",
        path=checks_tsv,
        problems=problems,
    )
    _check_summary_artifact_hash(
        payload=payload,
        artifact_id="row_manifest_tsv",
        path=row_manifest_tsv,
        problems=problems,
    )
    _check_summary_input_artifact_hashes(payload, problems)
    _check_checks_tsv(checks_tsv, problems)
    _check_row_manifest_tsv(row_manifest_tsv, problems)
    _check_optional_externalized_artifact(payload, "cell_evidence_tsv", problems)
    _check_optional_externalized_artifact(payload, "overlay_queue_tsv", problems)
    return problems


def _sample_local_facts(
    *,
    active_rows: Sequence[Mapping[str, str]],
    evidence_by_key: Mapping[tuple[str, str], Mapping[str, str]],
    review_by_row: Mapping[str, Mapping[str, str]],
    availability_problem_count: int,
) -> dict[str, Any]:
    cell_rows: list[dict[str, str]] = []
    for row in sorted(
        active_rows,
        key=lambda item: (
            text_value(item.get("peak_hypothesis_id")),
            text_value(item.get("sample_stem")),
        ),
    ):
        row_id = text_value(row.get("peak_hypothesis_id"))
        sample = text_value(row.get("sample_stem"))
        evidence = evidence_by_key.get((row_id, sample))
        cell_rows.append(_cell_evidence_row(row, evidence))

    row_manifest_rows = _row_manifest_rows(cell_rows, review_by_row=review_by_row)
    overlay_queue_rows = _overlay_queue_rows(
        cell_rows,
        review_by_row=review_by_row,
    )
    present_rows = [
        row
        for row in cell_rows
        if row["alignment_cell_evidence_status"] == "present"
    ]
    return {
        "availability_problem_count": availability_problem_count,
        "active_pressure_cell_count": len(cell_rows),
        "alignment_cell_evidence_present_cell_count": len(present_rows),
        "alignment_cell_evidence_missing_cell_count": (
            len(cell_rows) - len(present_rows)
        ),
        "review_rescue_cell_count": _count(
            present_rows,
            "production_cell_status",
            "review_rescue",
        ),
        "dna_dr_tagged_cell_count": _count(
            present_rows,
            "neutral_loss_tag",
            "DNA_dR",
        ),
        "production_family_identity_cell_count": _count(
            present_rows,
            "identity_decision",
            "production_family",
        ),
        "alignment_review_row_count": len(review_by_row),
        "overlay_queue_row_count": len(overlay_queue_rows),
        "cell_evidence_rows": cell_rows,
        "row_manifest_rows": row_manifest_rows,
        "overlay_queue_rows": overlay_queue_rows,
    }


def _cell_evidence_row(
    opportunity: Mapping[str, str],
    evidence: Mapping[str, str] | None,
) -> dict[str, str]:
    row_id = text_value(opportunity.get("peak_hypothesis_id"))
    sample = text_value(opportunity.get("sample_stem"))
    if evidence is None:
        return {
            "schema_version": SCHEMA_VERSION,
            "opportunity_scope": text_value(opportunity.get("opportunity_scope")),
            "peak_hypothesis_id": row_id,
            "sample_stem": sample,
            "alignment_cell_evidence_status": "missing",
            "alignment_cell_status": "",
            "production_cell_status": "",
            "alignment_write_matrix_value": "",
            "alignment_include_in_primary_matrix": "",
            "identity_decision": "",
            "neutral_loss_tag": "",
            "trace_quality": "",
            "scan_support_score": "",
            "area": "",
            "apex_rt": "",
            "height": "",
            "peak_start_rt": "",
            "peak_end_rt": "",
            "gap_fill_state": "",
            "gap_fill_reason": "",
            "source_candidate_id": "",
            "source_raw_file": "",
            "family_center_mz": "",
            "family_center_rt": "",
            "row_flags": "",
            "cell_evidence_reason": "no_exact_alignment_cell_evidence_row",
            "raw_trace_evidence_status": "not_requested",
            "sample_trace_support_status": "missing_alignment_cell_evidence",
            "product_authority_effect": "candidate_only_no_write_authority",
            "next_gate": "missing_alignment_cell_evidence_review",
        }
    return {
        "schema_version": SCHEMA_VERSION,
        "opportunity_scope": text_value(opportunity.get("opportunity_scope")),
        "peak_hypothesis_id": row_id,
        "sample_stem": sample,
        "alignment_cell_evidence_status": "present",
        "alignment_cell_status": text_value(evidence.get("status")),
        "production_cell_status": text_value(evidence.get("production_cell_status")),
        "alignment_write_matrix_value": text_value(evidence.get("write_matrix_value")),
        "alignment_include_in_primary_matrix": text_value(
            evidence.get("include_in_primary_matrix"),
        ),
        "identity_decision": text_value(evidence.get("identity_decision")),
        "neutral_loss_tag": text_value(evidence.get("neutral_loss_tag")),
        "trace_quality": text_value(evidence.get("trace_quality")),
        "scan_support_score": text_value(evidence.get("scan_support_score")),
        "area": text_value(evidence.get("area")),
        "apex_rt": text_value(evidence.get("apex_rt")),
        "height": text_value(evidence.get("height")),
        "peak_start_rt": text_value(evidence.get("peak_start_rt")),
        "peak_end_rt": text_value(evidence.get("peak_end_rt")),
        "gap_fill_state": text_value(evidence.get("gap_fill_state")),
        "gap_fill_reason": text_value(evidence.get("gap_fill_reason")),
        "source_candidate_id": text_value(evidence.get("source_candidate_id")),
        "source_raw_file": text_value(evidence.get("source_raw_file")),
        "family_center_mz": text_value(evidence.get("family_center_mz")),
        "family_center_rt": text_value(evidence.get("family_center_rt")),
        "row_flags": text_value(evidence.get("row_flags")),
        "cell_evidence_reason": text_value(evidence.get("reason")),
        "raw_trace_evidence_status": "not_requested",
        "sample_trace_support_status": (
            "alignment_sample_local_ms1_identity_present_needs_raw_trace"
        ),
        "product_authority_effect": "candidate_only_no_write_authority",
        "next_gate": "raw_overlay_trace_identity_gate",
    }


def _row_manifest_rows(
    cell_rows: Sequence[Mapping[str, str]],
    *,
    review_by_row: Mapping[str, Mapping[str, str]],
) -> list[dict[str, str]]:
    grouped: dict[str, list[Mapping[str, str]]] = defaultdict(list)
    for row in cell_rows:
        grouped[text_value(row.get("peak_hypothesis_id"))].append(row)
    result: list[dict[str, str]] = []
    for row_id, rows in sorted(grouped.items()):
        present_count = _count(rows, "alignment_cell_evidence_status", "present")
        review = review_by_row.get(row_id, {})
        result.append(
            {
                "schema_version": SCHEMA_VERSION,
                "row_scope": "active_default_row_blank_cell",
                "peak_hypothesis_id": row_id,
                "candidate_cell_count": str(len(rows)),
                "alignment_cell_evidence_present_cell_count": str(present_count),
                "alignment_cell_evidence_missing_cell_count": str(
                    len(rows) - present_count,
                ),
                "review_rescue_cell_count": str(
                    _count(rows, "production_cell_status", "review_rescue"),
                ),
                "dna_dr_tagged_cell_count": str(
                    _count(rows, "neutral_loss_tag", "DNA_dR"),
                ),
                "production_family_identity_cell_count": str(
                    _count(rows, "identity_decision", "production_family"),
                ),
                "raw_trace_evidence_present_cell_count": "0",
                "sample_trace_support_cell_count": "0",
                "sample_trace_review_cell_count": "0",
                "alignment_review_identity_decision": text_value(
                    review.get("identity_decision"),
                ),
                "alignment_review_identity_confidence": text_value(
                    review.get("identity_confidence"),
                ),
                "alignment_review_neutral_loss_tag": text_value(
                    review.get("neutral_loss_tag"),
                ),
                "alignment_review_row_flags": text_value(review.get("row_flags")),
                "product_authority_effect": "no_new_backfill_authority_gate_only",
                "next_gate": (
                    "raw_overlay_trace_identity_gate"
                    if present_count
                    else "missing_alignment_cell_evidence_review"
                ),
            },
        )
    return result


def _overlay_queue_rows(
    cell_rows: Sequence[Mapping[str, str]],
    *,
    review_by_row: Mapping[str, Mapping[str, str]],
) -> list[dict[str, str]]:
    grouped: dict[str, list[Mapping[str, str]]] = defaultdict(list)
    for row in cell_rows:
        if text_value(row.get("alignment_cell_evidence_status")) != "present":
            continue
        grouped[text_value(row.get("peak_hypothesis_id"))].append(row)

    rows: list[dict[str, str]] = []
    for rank, row_id in enumerate(sorted(grouped), start=1):
        evidence_rows = grouped[row_id]
        review = review_by_row.get(row_id)
        if review is None:
            raise ValueError(f"missing alignment_review row for {row_id}")
        rt_min, rt_max = _rt_window(evidence_rows, row_id=row_id)
        family_center_mz = text_value(review.get("family_center_mz"))
        family_center_rt = text_value(review.get("family_center_rt"))
        output_prefix = f"{rank:03d}_{row_id.lower()}_backfill_expansion_ms1_evidence"
        command_args = (
            f"--family-id {row_id} --mz {family_center_mz} "
            f"--rt-min {_format_float(rt_min)} --rt-max {_format_float(rt_max)} "
            f"--ppm 10 --output-prefix {output_prefix}"
        )
        rows.append(
            {
                "rank": str(rank),
                "feature_family_id": row_id,
                "seed_group_id": (
                    f"backfill_expansion_sample_local_ms1::{row_id}"
                ),
                "family_center_mz": family_center_mz,
                "family_center_rt": family_center_rt,
                "suggested_rt_min": _format_float(rt_min),
                "suggested_rt_max": _format_float(rt_max),
                "suggested_output_prefix": output_prefix,
                "candidate_cell_count": str(
                    sum(
                        1
                        for row in cell_rows
                        if text_value(row.get("peak_hypothesis_id")) == row_id
                    ),
                ),
                "alignment_cell_evidence_present_cell_count": str(
                    len(evidence_rows),
                ),
                "alignment_cell_evidence_missing_cell_count": str(
                    sum(
                        1
                        for row in cell_rows
                        if text_value(row.get("peak_hypothesis_id")) == row_id
                        and text_value(row.get("alignment_cell_evidence_status"))
                        == "missing"
                    ),
                ),
                "backfill_request_ppm": "10",
                "seed_window_basis": "sample_local_alignment_peak_window_union",
                "product_authority_effect": "candidate_only_no_write_authority",
                "next_gate": "raw_overlay_trace_identity_gate",
                "suggested_overlay_command_args": command_args,
            },
        )
    return rows


def _alignment_review_by_row(
    path: Path,
    active_row_ids: set[str],
) -> dict[str, Mapping[str, str]]:
    rows = read_tsv_required(path, ALIGNMENT_REVIEW_COLUMNS)
    result: dict[str, Mapping[str, str]] = {}
    for row in rows:
        row_id = _row_identity(row)
        if row_id not in active_row_ids:
            continue
        if row_id in result:
            raise ValueError(f"duplicate alignment_review row for {row_id}")
        result[row_id] = row
    missing = sorted(active_row_ids - set(result))
    if missing:
        raise ValueError("missing alignment_review rows: " + ";".join(missing))
    return result


def _matching_alignment_cell_evidence(
    path: Path,
    *,
    active_keys: set[tuple[str, str]],
) -> dict[tuple[str, str], Mapping[str, str]]:
    result: dict[tuple[str, str], Mapping[str, str]] = {}
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        fieldnames = tuple(reader.fieldnames or ())
        missing = [
            column
            for column in ALIGNMENT_CELL_EVIDENCE_COLUMNS
            if column not in fieldnames
        ]
        if missing:
            raise ValueError(f"{path}: missing required columns: {', '.join(missing)}")
        for row in reader:
            key = (_row_identity(row), text_value(row.get("sample_stem")))
            if key not in active_keys:
                continue
            if key in result:
                raise ValueError(
                    "duplicate alignment_backfill_cell_evidence row for "
                    f"{key[0]} {key[1]}",
                )
            result[key] = row
    return result


def _check_rows(facts: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [
        _check(
            "availability_checker_pass",
            facts["availability_problem_count"],
            0,
            facts["availability_problem_count"] == 0,
        ),
        _check(
            "active_pressure_cell_count",
            facts["active_pressure_cell_count"],
            EXPECTED_COUNTS["active_pressure_cell_count"],
            facts["active_pressure_cell_count"]
            == EXPECTED_COUNTS["active_pressure_cell_count"],
        ),
        _check(
            "alignment_cell_evidence_present_count",
            facts["alignment_cell_evidence_present_cell_count"],
            EXPECTED_COUNTS["alignment_cell_evidence_present_cell_count"],
            facts["alignment_cell_evidence_present_cell_count"]
            == EXPECTED_COUNTS["alignment_cell_evidence_present_cell_count"],
            "Exact peak_hypothesis_id + sample_stem rows in alignment cell evidence.",
        ),
        _check(
            "alignment_cell_evidence_missing_count",
            facts["alignment_cell_evidence_missing_cell_count"],
            EXPECTED_COUNTS["alignment_cell_evidence_missing_cell_count"],
            facts["alignment_cell_evidence_missing_cell_count"]
            == EXPECTED_COUNTS["alignment_cell_evidence_missing_cell_count"],
        ),
        _check(
            "all_present_alignment_rows_are_review_rescue",
            facts["review_rescue_cell_count"],
            EXPECTED_COUNTS["review_rescue_cell_count"],
            facts["review_rescue_cell_count"]
            == EXPECTED_COUNTS["review_rescue_cell_count"],
        ),
        _check(
            "all_present_alignment_rows_have_dna_dr_tag",
            facts["dna_dr_tagged_cell_count"],
            EXPECTED_COUNTS["dna_dr_tagged_cell_count"],
            facts["dna_dr_tagged_cell_count"]
            == EXPECTED_COUNTS["dna_dr_tagged_cell_count"],
        ),
        _check(
            "all_present_alignment_rows_have_production_family_identity",
            facts["production_family_identity_cell_count"],
            EXPECTED_COUNTS["production_family_identity_cell_count"],
            facts["production_family_identity_cell_count"]
            == EXPECTED_COUNTS["production_family_identity_cell_count"],
        ),
        _check(
            "alignment_review_row_count",
            facts["alignment_review_row_count"],
            EXPECTED_COUNTS["alignment_review_row_count"],
            facts["alignment_review_row_count"]
            == EXPECTED_COUNTS["alignment_review_row_count"],
        ),
        _check(
            "overlay_queue_row_count",
            facts["overlay_queue_row_count"],
            EXPECTED_COUNTS["overlay_queue_row_count"],
            facts["overlay_queue_row_count"]
            == EXPECTED_COUNTS["overlay_queue_row_count"],
        ),
        _check(
            "no_raw_or_writer_changes",
            "raw_or_85raw=FALSE;writer=FALSE;default_matrix=FALSE",
            "diagnostic alignment-evidence gate only",
            True,
        ),
        _check(
            "no_row_or_family_projection",
            "row_or_family_evidence_projected_to_cells=FALSE",
            "exact sample-local key match required",
            True,
        ),
    ]


def _summary_payload(
    *,
    facts: Mapping[str, Any],
    checks_tsv: Path,
    row_manifest_tsv: Path,
    cell_evidence_tsv: Path,
    overlay_queue_tsv: Path,
    availability_summary_json: Path,
    availability_checks_tsv: Path,
    availability_row_manifest_tsv: Path,
    availability_cells_tsv: Path,
    alignment_backfill_cell_evidence_tsv: Path,
    alignment_review_tsv: Path,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "pass",
        "validation_label": (
            "no_raw_backfill_expansion_sample_local_ms1_identity_evidence"
        ),
        "product_lane": "backfill",
        "sample_local_scope": "cid_nl_active_blank_cells_from_backfill_census_v1",
        "strongest_evidence_tier": "85RAW-derived alignment cell evidence",
        "release_decision": (
            "raw_overlay_trace_identity_gate_for_675_present_cells_and_hold_"
            "254_missing_alignment_cells"
        ),
        **{
            field: facts[field]
            for field in (
                "active_pressure_cell_count",
                "alignment_cell_evidence_present_cell_count",
                "alignment_cell_evidence_missing_cell_count",
                "review_rescue_cell_count",
                "dna_dr_tagged_cell_count",
                "production_family_identity_cell_count",
                "alignment_review_row_count",
                "overlay_queue_row_count",
            )
        },
        "raw_trace_evidence_present_cell_count": 0,
        "sample_trace_support_cell_count": 0,
        "sample_trace_review_cell_count": 0,
        "raw_or_85raw_ran": False,
        "product_writer_changed_by_checker": False,
        "default_quant_matrix_changed_by_checker": False,
        "workbook_or_gui_changed": False,
        "selected_peak_area_or_counting_changed": False,
        "backfill_writer_authority_changed_by_checker": False,
        "broad_backfill_unparked": False,
        "candidate_rows_are_matrix_rows": False,
        "row_or_family_evidence_projected_to_cells": False,
        "sample_local_key_match_required": True,
        "decision_statement": (
            "The current fix3 CID-NL alignment evidence provides exact "
            "sample-local MS1/identity rows for 675 of 929 active Backfill "
            "pressure cells. The remaining 254 cells have no exact alignment "
            "cell evidence row and stay held. Present cells still require a "
            "bounded RAW overlay trace/identity gate before any Backfill "
            "expected-diff writer proposal."
        ),
        "authority_statement": (
            "This gate is evidence classification only. It grants no "
            "ProductWriter authority, creates no default matrix writes, does "
            "not change selected peak/area/counting, and does not project "
            "row/family identity onto sample cells."
        ),
        "input_artifacts": {
            "availability_summary_json": _artifact(availability_summary_json),
            "availability_checks_tsv": _artifact(availability_checks_tsv),
            "availability_row_manifest_tsv": _artifact(
                availability_row_manifest_tsv,
            ),
            "availability_cells_tsv": _artifact(availability_cells_tsv),
            "alignment_backfill_cell_evidence_tsv": _artifact(
                alignment_backfill_cell_evidence_tsv,
            ),
            "alignment_review_tsv": _artifact(alignment_review_tsv),
        },
        "artifacts": {
            "summary_json": {
                "path": (
                    "docs/superpowers/validation/"
                    "backfill_expansion_sample_local_ms1_evidence_v1/"
                    "backfill_expansion_sample_local_ms1_evidence_summary.json"
                ),
                "retention_decision": "keep_summary",
            },
            "checks_tsv": _artifact(checks_tsv)
            | {"retention_decision": "keep_summary"},
            "row_manifest_tsv": _artifact(row_manifest_tsv)
            | {"retention_decision": "keep_contract"},
            "cell_evidence_tsv": _artifact(cell_evidence_tsv)
            | {
                "retention_decision": "externalize",
                "tracked_replacement_or_summary": (
                    "docs/superpowers/validation/"
                    "backfill_expansion_sample_local_ms1_evidence_v1/"
                    "backfill_expansion_sample_local_ms1_evidence_summary.json"
                ),
            },
            "overlay_queue_tsv": _artifact(overlay_queue_tsv)
            | {
                "retention_decision": "externalize",
                "tracked_replacement_or_summary": (
                    "docs/superpowers/validation/"
                    "backfill_expansion_sample_local_ms1_evidence_v1/"
                    "backfill_expansion_sample_local_ms1_evidence_summary.json"
                ),
            },
        },
    }


def _write_readme(path: Path, *, payload: Mapping[str, Any]) -> None:
    lines = [
        "# Backfill Expansion Sample-Local MS1 Evidence v1",
        "",
        "Status: `pass`.",
        "",
        "This is a no-RAW gate over the 929 active Backfill pressure cells "
        "created by CID-NL Discovery activation. It joins the pressure cells "
        "against the current fix3 85RAW-derived alignment cell evidence using "
        "only the exact `peak_hypothesis_id + sample_stem` key.",
        "",
        "## Decision",
        "",
        "Release decision: "
        "`raw_overlay_trace_identity_gate_for_675_present_cells_and_hold_"
        "254_missing_alignment_cells`.",
        "",
        "- Active Backfill pressure cells: "
        f"`{payload['active_pressure_cell_count']}`.",
        "- Exact sample-local alignment evidence present: "
        f"`{payload['alignment_cell_evidence_present_cell_count']}`.",
        "- Missing exact alignment cell evidence: "
        f"`{payload['alignment_cell_evidence_missing_cell_count']}`.",
        "- Present cells with `review_rescue` state: "
        f"`{payload['review_rescue_cell_count']}`.",
        "- Present cells with `DNA_dR` tag evidence: "
        f"`{payload['dna_dr_tagged_cell_count']}`.",
        "- Present cells with `production_family` identity: "
        f"`{payload['production_family_identity_cell_count']}`.",
        "- RAW overlay queue rows: "
        f"`{payload['overlay_queue_row_count']}`.",
        "",
        "The present 675 cells are not write-ready. They are the bounded input "
        "for a future RAW overlay trace/identity gate. The missing 254 cells "
        "stay held because row/family evidence is not projected onto cells.",
        "",
        "## Boundary",
        "",
        "This gate does not run RAW, does not write a default matrix, does not "
        "change ProductWriter authority, does not unpark broad Backfill, and "
        "does not change selected peak/area/counting.",
        "",
        "## Files",
        "",
        "- Summary JSON: "
        "`docs/superpowers/validation/"
        "backfill_expansion_sample_local_ms1_evidence_v1/"
        "backfill_expansion_sample_local_ms1_evidence_summary.json`",
        "- Checks TSV: "
        "`docs/superpowers/validation/"
        "backfill_expansion_sample_local_ms1_evidence_v1/"
        "backfill_expansion_sample_local_ms1_evidence_checks.tsv`",
        "- Compact row manifest: "
        "`docs/superpowers/validation/"
        "backfill_expansion_sample_local_ms1_evidence_v1/"
        "backfill_expansion_sample_local_ms1_evidence_row_manifest.tsv`",
        "- Full cell evidence map: "
        "`output/validation/backfill_expansion_sample_local_ms1_evidence_v1/"
        "backfill_expansion_sample_local_ms1_evidence_cells.tsv`",
        "- RAW overlay queue: "
        "`output/validation/backfill_expansion_sample_local_ms1_evidence_v1/"
        "backfill_expansion_sample_local_ms1_overlay_queue.tsv`",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def _check(
    check_id: str,
    observed: object,
    expected: object,
    ok: bool,
    notes: str = "",
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "check_id": check_id,
        "status": "pass" if ok else "fail",
        "observed": observed,
        "expected": expected,
        "notes": notes,
    }


def _count(
    rows: Sequence[Mapping[str, str]],
    field: str,
    expected_value: str,
) -> int:
    return sum(1 for row in rows if text_value(row.get(field)) == expected_value)


def _check_summary_artifact_hash(
    *,
    payload: Mapping[str, Any],
    artifact_id: str,
    path: Path,
    problems: list[str],
) -> None:
    artifacts = payload.get("artifacts")
    if not isinstance(artifacts, Mapping):
        problems.append("summary artifacts mismatch")
        return
    artifact = artifacts.get(artifact_id)
    if not isinstance(artifact, Mapping):
        problems.append(f"summary artifacts missing {artifact_id}")
        return
    expected_hash = text_value(artifact.get("sha256"))
    if not expected_hash:
        problems.append(f"summary {artifact_id} sha256 missing")
        return
    try:
        observed_hash = file_sha256(path)
    except OSError as exc:
        problems.append(f"{artifact_id} sha256 cannot read: {exc}")
        return
    if observed_hash != expected_hash:
        problems.append(f"summary {artifact_id} sha256 mismatch")


def _check_summary_input_artifact_hashes(
    payload: Mapping[str, Any],
    problems: list[str],
) -> None:
    input_artifacts = payload.get("input_artifacts")
    if not isinstance(input_artifacts, Mapping):
        problems.append("summary input_artifacts mismatch")
        return
    for artifact_id, raw_entry in input_artifacts.items():
        if not isinstance(raw_entry, Mapping):
            problems.append(f"summary input_artifacts {artifact_id} invalid")
            continue
        path_text = text_value(raw_entry.get("path"))
        expected_hash = text_value(raw_entry.get("sha256"))
        if not path_text or not expected_hash:
            problems.append(f"summary input_artifacts {artifact_id} incomplete")
            continue
        path = (ROOT / path_text).resolve(strict=False)
        if not path.is_file():
            problems.append(f"summary input_artifacts {artifact_id} missing")
            continue
        if file_sha256(path) != expected_hash:
            problems.append(f"summary input_artifacts {artifact_id} sha256 mismatch")


def _check_checks_tsv(path: Path, problems: list[str]) -> None:
    try:
        rows = read_tsv_required(path, CHECK_COLUMNS)
    except (OSError, ValueError) as exc:
        problems.append(f"checks_tsv: {exc}")
        return
    check_ids = [row.get("check_id", "") for row in rows]
    if len(rows) != len(EXPECTED_CHECK_IDS):
        problems.append(f"checks row count mismatch: {len(rows)}")
    missing = sorted(set(EXPECTED_CHECK_IDS) - set(check_ids))
    unexpected = sorted(set(check_ids) - set(EXPECTED_CHECK_IDS))
    duplicate_count = len(check_ids) - len(set(check_ids))
    if missing:
        problems.append("checks missing required ids: " + ";".join(missing))
    if unexpected:
        problems.append("checks unexpected ids: " + ";".join(unexpected))
    if duplicate_count:
        problems.append(f"checks duplicate id count: {duplicate_count}")
    failed = [row["check_id"] for row in rows if row.get("status") != "pass"]
    if failed:
        problems.append("failed checks: " + ";".join(failed))


def _check_row_manifest_tsv(path: Path, problems: list[str]) -> None:
    try:
        rows = read_tsv_required(path, ROW_MANIFEST_COLUMNS)
    except (OSError, ValueError) as exc:
        problems.append(f"row_manifest_tsv: {exc}")
        return
    if len(rows) != EXPECTED_COUNTS["alignment_review_row_count"]:
        problems.append("row_manifest row count mismatch")
    present_count = sum(
        _int(row.get("alignment_cell_evidence_present_cell_count")) for row in rows
    )
    missing_count = sum(
        _int(row.get("alignment_cell_evidence_missing_cell_count")) for row in rows
    )
    if present_count != EXPECTED_COUNTS["alignment_cell_evidence_present_cell_count"]:
        problems.append("row_manifest present evidence count mismatch")
    if missing_count != EXPECTED_COUNTS["alignment_cell_evidence_missing_cell_count"]:
        problems.append("row_manifest missing evidence count mismatch")
    for row in rows:
        if row.get("schema_version") != SCHEMA_VERSION:
            problems.append("row_manifest schema_version mismatch")
        if row.get("row_scope") != "active_default_row_blank_cell":
            problems.append("row_manifest row_scope mismatch")
        if row.get("product_authority_effect") != (
            "no_new_backfill_authority_gate_only"
        ):
            problems.append("row_manifest product_authority_effect mismatch")


def _check_optional_externalized_artifact(
    payload: Mapping[str, Any],
    artifact_id: str,
    problems: list[str],
) -> None:
    artifacts = payload.get("artifacts")
    if not isinstance(artifacts, Mapping):
        return
    artifact = artifacts.get(artifact_id)
    if not isinstance(artifact, Mapping):
        problems.append(f"summary artifacts missing {artifact_id}")
        return
    path_text = text_value(artifact.get("path"))
    if not path_text:
        problems.append(f"summary {artifact_id} path missing")
        return
    path = (ROOT / path_text).resolve(strict=False)
    if path.exists() and file_sha256(path) != text_value(artifact.get("sha256")):
        problems.append(f"summary {artifact_id} sha256 mismatch")


def _read_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: expected JSON object")
    return payload


def _artifact(path: Path) -> dict[str, Any]:
    return {
        "path": _relative_or_absolute(path),
        "sha256": file_sha256(path),
        "size_bytes": path.stat().st_size,
    }


def _relative_or_absolute(path: Path) -> str:
    try:
        return (
            path.resolve(strict=False)
            .relative_to(ROOT.resolve(strict=False))
            .as_posix()
        )
    except ValueError:
        return str(path)


def _row_identity(row: Mapping[str, str]) -> str:
    return (
        text_value(row.get("group_hypothesis_id"))
        or text_value(row.get("feature_family_id"))
        or text_value(row.get("public_family_id"))
    )


def _rt_window(
    rows: Sequence[Mapping[str, str]],
    *,
    row_id: str,
) -> tuple[float, float]:
    starts = [optional_float(row.get("peak_start_rt")) for row in rows]
    ends = [optional_float(row.get("peak_end_rt")) for row in rows]
    start_values = [value for value in starts if value is not None]
    end_values = [value for value in ends if value is not None]
    if not start_values or not end_values:
        raise ValueError(f"missing peak RT window for {row_id}")
    return min(start_values), max(end_values)


def _format_float(value: float) -> str:
    return f"{value:.6g}"


def _int(value: object) -> int:
    text = text_value(value)
    if not text:
        return 0
    return int(float(text))


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--docs-dir", type=Path, default=DEFAULT_DOCS_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--availability-summary-json",
        type=Path,
        default=DEFAULT_AVAILABILITY_SUMMARY_JSON,
    )
    parser.add_argument(
        "--availability-checks-tsv",
        type=Path,
        default=DEFAULT_AVAILABILITY_CHECKS_TSV,
    )
    parser.add_argument(
        "--availability-row-manifest-tsv",
        type=Path,
        default=DEFAULT_AVAILABILITY_ROW_MANIFEST_TSV,
    )
    parser.add_argument(
        "--availability-cells-tsv",
        type=Path,
        default=DEFAULT_AVAILABILITY_CELLS_TSV,
    )
    parser.add_argument(
        "--alignment-backfill-cell-evidence-tsv",
        type=Path,
        default=DEFAULT_ALIGNMENT_BACKFILL_CELL_EVIDENCE_TSV,
    )
    parser.add_argument(
        "--alignment-review-tsv",
        type=Path,
        default=DEFAULT_ALIGNMENT_REVIEW_TSV,
    )
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--summary-json", type=Path)
    parser.add_argument("--checks-tsv", type=Path)
    parser.add_argument("--row-manifest-tsv", type=Path)
    parser.add_argument("--require-pass", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    if args.check_only:
        summary_json = args.summary_json or (
            args.docs_dir
            / "backfill_expansion_sample_local_ms1_evidence_summary.json"
        )
        checks_tsv = args.checks_tsv or (
            args.docs_dir
            / "backfill_expansion_sample_local_ms1_evidence_checks.tsv"
        )
        row_manifest_tsv = args.row_manifest_tsv or (
            args.docs_dir
            / "backfill_expansion_sample_local_ms1_evidence_row_manifest.tsv"
        )
        problems = check_backfill_expansion_sample_local_ms1_evidence(
            summary_json=summary_json,
            checks_tsv=checks_tsv,
            row_manifest_tsv=row_manifest_tsv,
        )
        for problem in problems:
            print(f"backfill_expansion_sample_local_ms1_evidence_problem: {problem}")
        return 2 if problems else 0

    try:
        payload = build_backfill_expansion_sample_local_ms1_evidence(
            docs_dir=args.docs_dir,
            output_dir=args.output_dir,
            availability_summary_json=args.availability_summary_json,
            availability_checks_tsv=args.availability_checks_tsv,
            availability_row_manifest_tsv=args.availability_row_manifest_tsv,
            availability_cells_tsv=args.availability_cells_tsv,
            alignment_backfill_cell_evidence_tsv=(
                args.alignment_backfill_cell_evidence_tsv
            ),
            alignment_review_tsv=args.alignment_review_tsv,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    summary_path = (
        args.docs_dir
        / "backfill_expansion_sample_local_ms1_evidence_summary.json"
    )
    print(f"backfill_expansion_sample_local_ms1_evidence_summary: {summary_path}")
    print(f"backfill_expansion_sample_local_ms1_evidence_status: {payload['status']}")
    print(
        "backfill_expansion_sample_local_ms1_evidence_release_decision: "
        f"{payload['release_decision']}"
    )
    if args.require_pass and payload.get("status") != "pass":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
