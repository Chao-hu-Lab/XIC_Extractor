"""Check evidence availability for Backfill expansion pressure cells.

This no-RAW gate consumes the Backfill expansion census and asks whether the
current active blank cells already have sample-local Backfill evidence in the
existing mechanical adjudication / trace recovery surfaces.

It does not generate evidence, run RAW, write a matrix, change ProductWriter
authority, or project row/family evidence onto sample cells.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.check_backfill_expansion_census import (  # noqa: E402
    DEFAULT_DOCS_DIR as DEFAULT_CENSUS_DOCS_DIR,
)
from scripts.check_backfill_expansion_census import (  # noqa: E402
    DEFAULT_OUTPUT_DIR as DEFAULT_CENSUS_OUTPUT_DIR,
)
from scripts.check_backfill_expansion_census import (  # noqa: E402
    OPPORTUNITY_COLUMNS,
    check_backfill_expansion_census,
)
from scripts.validation_artifact_contracts import (  # noqa: E402
    artifact_hash_matches,
    check_summary_artifact_hashes,
)
from tools.diagnostics.docs_policy import (  # noqa: E402
    MECHANICAL_ADJUDICATION_INDEX_REL,
)
from xic_extractor.tabular_io import (  # noqa: E402
    file_sha256,
    read_tsv_required,
    text_value,
    write_tsv,
)

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = "backfill_expansion_evidence_availability_v1"
DEFAULT_DOCS_DIR = (
    ROOT / "docs/superpowers/validation/backfill_expansion_evidence_availability_v1"
)
DEFAULT_OUTPUT_DIR = (
    ROOT / "output/validation/backfill_expansion_evidence_availability_v1"
)
DEFAULT_CENSUS_SUMMARY_JSON = (
    DEFAULT_CENSUS_DOCS_DIR / "backfill_expansion_census_summary.json"
)
DEFAULT_CENSUS_CHECKS_TSV = (
    DEFAULT_CENSUS_DOCS_DIR / "backfill_expansion_census_checks.tsv"
)
DEFAULT_CENSUS_ROW_MANIFEST_TSV = (
    DEFAULT_CENSUS_DOCS_DIR / "backfill_expansion_census_row_manifest.tsv"
)
DEFAULT_CENSUS_OPPORTUNITY_CELLS_TSV = (
    DEFAULT_CENSUS_OUTPUT_DIR / "backfill_expansion_opportunity_cells.tsv"
)
DEFAULT_MECHANICAL_ADJUDICATION_INDEX_TSV = ROOT / MECHANICAL_ADJUDICATION_INDEX_REL
DEFAULT_TRACE_RECOVERY_REPORT_TSV = (
    ROOT / "docs/superpowers/validation/trace_overlay_recovery_report_v1.tsv"
)

MECHANICAL_COLUMNS = (
    "schema_version",
    "row_id",
    "family_id",
    "sample_id",
    "decision",
    "write_authority",
    "evidence_grade",
    "next_required_evidence",
    "may_touch_matrix",
    "explanation_only",
    "product_authority_scope",
)
TRACE_RECOVERY_COLUMNS = (
    "schema_version",
    "row_id",
    "family_id",
    "sample_id",
    "recovery_status",
    "sample_trace_present",
    "recovered_sample_trace_status",
    "post_recovery_mechanical_decision",
    "post_recovery_evidence_grade",
    "post_recovery_next_required_evidence",
    "may_touch_matrix",
    "may_grant_product_authority",
)
CHECK_COLUMNS = (
    "schema_version",
    "check_id",
    "status",
    "observed",
    "expected",
    "notes",
)
ROW_MANIFEST_COLUMNS = (
    "schema_version",
    "row_scope",
    "peak_hypothesis_id",
    "candidate_cell_count",
    "mechanical_covered_cell_count",
    "trace_recovered_cell_count",
    "immediate_expected_diff_ready_cell_count",
    "requires_new_sample_local_evidence_cell_count",
    "product_authority_effect",
    "next_gate",
)
CELL_AVAILABILITY_COLUMNS = (
    "schema_version",
    "opportunity_scope",
    "peak_hypothesis_id",
    "sample_stem",
    "mechanical_evidence_status",
    "trace_recovery_status",
    "evidence_availability_status",
    "product_authority_effect",
    "next_evidence_needed",
)
EXPECTED_COUNTS = {
    "active_pressure_cell_count": 929,
    "parked_pressure_cell_count": 1010,
    "active_mechanical_covered_cell_count": 0,
    "active_trace_recovered_cell_count": 0,
    "active_immediate_expected_diff_ready_cell_count": 0,
    "active_requires_new_sample_local_evidence_cell_count": 929,
    "parked_mechanical_covered_cell_count": 0,
    "parked_trace_recovered_cell_count": 0,
    "parked_immediate_expected_diff_ready_cell_count": 0,
    "cell_availability_output_row_count": 1939,
}
EXPECTED_CHECK_IDS = (
    "census_checker_pass",
    "active_pressure_cell_count",
    "parked_pressure_cell_count",
    "active_mechanical_coverage_absent",
    "active_trace_recovery_coverage_absent",
    "active_immediate_ready_count_zero",
    "active_requires_new_evidence_count",
    "parked_coverage_remains_parked",
    "cell_availability_output_count",
    "no_raw_or_writer_changes",
    "no_row_or_family_projection",
)


def build_backfill_expansion_evidence_availability(
    *,
    docs_dir: Path = DEFAULT_DOCS_DIR,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    census_summary_json: Path = DEFAULT_CENSUS_SUMMARY_JSON,
    census_checks_tsv: Path = DEFAULT_CENSUS_CHECKS_TSV,
    census_row_manifest_tsv: Path = DEFAULT_CENSUS_ROW_MANIFEST_TSV,
    census_opportunity_cells_tsv: Path = DEFAULT_CENSUS_OPPORTUNITY_CELLS_TSV,
    mechanical_adjudication_index_tsv: Path = (
        DEFAULT_MECHANICAL_ADJUDICATION_INDEX_TSV
    ),
    trace_recovery_report_tsv: Path = DEFAULT_TRACE_RECOVERY_REPORT_TSV,
) -> dict[str, Any]:
    census_problems = check_backfill_expansion_census(
        summary_json=census_summary_json,
        checks_tsv=census_checks_tsv,
        row_manifest_tsv=census_row_manifest_tsv,
    )
    census_summary = _read_json_object(census_summary_json)
    opportunity_rows = read_tsv_required(
        census_opportunity_cells_tsv,
        OPPORTUNITY_COLUMNS,
    )
    mechanical_rows = read_tsv_required(
        mechanical_adjudication_index_tsv,
        MECHANICAL_COLUMNS,
    )
    trace_rows = read_tsv_required(trace_recovery_report_tsv, TRACE_RECOVERY_COLUMNS)

    facts = _availability_facts(
        census_summary=census_summary,
        opportunity_rows=opportunity_rows,
        mechanical_rows=mechanical_rows,
        trace_rows=trace_rows,
        census_problem_count=len(census_problems),
    )
    checks = _check_rows(facts)
    failed = [row["check_id"] for row in checks if row["status"] != "pass"]
    if failed:
        raise ValueError(
            "Backfill expansion evidence availability failed: " + ";".join(failed)
        )

    docs_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    checks_tsv = docs_dir / "backfill_expansion_evidence_availability_checks.tsv"
    row_manifest_tsv = (
        docs_dir / "backfill_expansion_evidence_availability_row_manifest.tsv"
    )
    cell_availability_tsv = (
        output_dir / "backfill_expansion_evidence_availability_cells.tsv"
    )
    summary_json = (
        docs_dir / "backfill_expansion_evidence_availability_summary.json"
    )

    write_tsv(checks_tsv, checks, CHECK_COLUMNS, extrasaction="raise")
    write_tsv(
        row_manifest_tsv,
        facts["row_manifest_rows"],
        ROW_MANIFEST_COLUMNS,
        extrasaction="raise",
    )
    write_tsv(
        cell_availability_tsv,
        facts["cell_availability_rows"],
        CELL_AVAILABILITY_COLUMNS,
        extrasaction="raise",
    )
    payload = _summary_payload(
        facts=facts,
        checks_tsv=checks_tsv,
        row_manifest_tsv=row_manifest_tsv,
        cell_availability_tsv=cell_availability_tsv,
        census_summary_json=census_summary_json,
        census_checks_tsv=census_checks_tsv,
        census_row_manifest_tsv=census_row_manifest_tsv,
        census_opportunity_cells_tsv=census_opportunity_cells_tsv,
        mechanical_adjudication_index_tsv=mechanical_adjudication_index_tsv,
        trace_recovery_report_tsv=trace_recovery_report_tsv,
    )
    summary_json.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _write_readme(docs_dir / "README.md", payload=payload)
    return payload


def check_backfill_expansion_evidence_availability(
    *,
    summary_json: Path = (
        DEFAULT_DOCS_DIR / "backfill_expansion_evidence_availability_summary.json"
    ),
    checks_tsv: Path = (
        DEFAULT_DOCS_DIR / "backfill_expansion_evidence_availability_checks.tsv"
    ),
    row_manifest_tsv: Path = (
        DEFAULT_DOCS_DIR
        / "backfill_expansion_evidence_availability_row_manifest.tsv"
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
        ("validation_label", "no_raw_backfill_expansion_evidence_availability"),
        ("product_lane", "backfill"),
        ("strongest_evidence_tier", "85RAW-derived no-RAW artifact availability"),
        ("release_decision", "hold_for_new_sample_local_ms1_identity_evidence"),
        ("raw_or_85raw_ran", False),
        ("product_writer_changed_by_checker", False),
        ("default_quant_matrix_changed_by_checker", False),
        ("workbook_or_gui_changed", False),
        ("selected_peak_area_or_counting_changed", False),
        ("backfill_writer_authority_changed_by_checker", False),
        ("broad_backfill_unparked", False),
        ("candidate_rows_are_matrix_rows", False),
        ("row_or_family_evidence_projected_to_cells", False),
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
    _check_optional_externalized_artifact(payload, "cell_availability_tsv", problems)
    return problems


def _availability_facts(
    *,
    census_summary: Mapping[str, Any],
    opportunity_rows: Sequence[Mapping[str, str]],
    mechanical_rows: Sequence[Mapping[str, str]],
    trace_rows: Sequence[Mapping[str, str]],
    census_problem_count: int,
) -> dict[str, Any]:
    mechanical_by_key = {
        (text_value(row.get("family_id")), text_value(row.get("sample_id"))): row
        for row in mechanical_rows
    }
    trace_by_key = {
        (text_value(row.get("family_id")), text_value(row.get("sample_id"))): row
        for row in trace_rows
    }
    active_rows = [
        row
        for row in opportunity_rows
        if text_value(row.get("opportunity_scope")) == "active_default_row_blank_cell"
    ]
    parked_rows = [
        row
        for row in opportunity_rows
        if text_value(row.get("opportunity_scope"))
        == "parked_authorized_nonactive_row_blank_cell"
    ]
    active_facts = _cell_facts(
        active_rows,
        mechanical_by_key=mechanical_by_key,
        trace_by_key=trace_by_key,
        parked=False,
    )
    parked_facts = _cell_facts(
        parked_rows,
        mechanical_by_key=mechanical_by_key,
        trace_by_key=trace_by_key,
        parked=True,
    )
    all_cell_facts = active_facts + parked_facts
    row_manifest_rows = _row_manifest_rows(all_cell_facts)
    return {
        "census_problem_count": census_problem_count,
        "census_active_pressure_cell_count": _int(
            census_summary.get("new_backfill_pressure_candidate_cell_count"),
        ),
        "census_parked_pressure_cell_count": _int(
            census_summary.get("parked_future_pressure_candidate_cell_count"),
        ),
        "active_pressure_cell_count": len(active_facts),
        "parked_pressure_cell_count": len(parked_facts),
        "active_mechanical_covered_cell_count": _count(
            active_facts,
            "mechanical_evidence_status",
            "present",
        ),
        "active_trace_recovered_cell_count": _count(
            active_facts,
            "trace_recovery_status",
            "present",
        ),
        "active_immediate_expected_diff_ready_cell_count": _count(
            active_facts,
            "evidence_availability_status",
            "immediate_expected_diff_ready",
        ),
        "active_requires_new_sample_local_evidence_cell_count": _count(
            active_facts,
            "evidence_availability_status",
            "requires_new_sample_local_evidence",
        ),
        "parked_mechanical_covered_cell_count": _count(
            parked_facts,
            "mechanical_evidence_status",
            "present",
        ),
        "parked_trace_recovered_cell_count": _count(
            parked_facts,
            "trace_recovery_status",
            "present",
        ),
        "parked_immediate_expected_diff_ready_cell_count": _count(
            parked_facts,
            "evidence_availability_status",
            "immediate_expected_diff_ready",
        ),
        "cell_availability_output_row_count": len(all_cell_facts),
        "cell_availability_rows": all_cell_facts,
        "row_manifest_rows": row_manifest_rows,
    }


def _cell_facts(
    rows: Sequence[Mapping[str, str]],
    *,
    mechanical_by_key: Mapping[tuple[str, str], Mapping[str, str]],
    trace_by_key: Mapping[tuple[str, str], Mapping[str, str]],
    parked: bool,
) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    for row in rows:
        key = (
            text_value(row.get("peak_hypothesis_id")),
            text_value(row.get("sample_stem")),
        )
        mechanical = mechanical_by_key.get(key)
        trace = trace_by_key.get(key)
        mechanical_status = "present" if mechanical is not None else "absent"
        trace_status = "present" if trace is not None else "absent"
        immediate_ready = _is_immediate_expected_diff_ready(mechanical, trace)
        if immediate_ready:
            availability = "immediate_expected_diff_ready"
            next_evidence = "expected_diff_and_provenance_gate"
        elif parked:
            availability = "parked_until_discovery_active"
            next_evidence = "discovery_feature_inclusion_authority"
        else:
            availability = "requires_new_sample_local_evidence"
            next_evidence = "sample_local_ms1_identity_evidence"
        result.append(
            {
                "schema_version": SCHEMA_VERSION,
                "opportunity_scope": text_value(row.get("opportunity_scope")),
                "peak_hypothesis_id": key[0],
                "sample_stem": key[1],
                "mechanical_evidence_status": mechanical_status,
                "trace_recovery_status": trace_status,
                "evidence_availability_status": availability,
                "product_authority_effect": "candidate_only_no_write_authority",
                "next_evidence_needed": next_evidence,
            }
        )
    return result


def _is_immediate_expected_diff_ready(
    mechanical: Mapping[str, str] | None,
    trace: Mapping[str, str] | None,
) -> bool:
    if mechanical is None:
        return False
    if text_value(mechanical.get("decision")) != "write_ready":
        return False
    if text_value(mechanical.get("write_authority")) != "TRUE":
        return False
    if text_value(mechanical.get("may_touch_matrix")) != "TRUE":
        return False
    if text_value(mechanical.get("product_authority_scope")) != (
        "backfill_policy_write_ready_rows"
    ):
        return False
    if trace is not None and text_value(trace.get("may_grant_product_authority")) == (
        "TRUE"
    ):
        return True
    return trace is None


def _row_manifest_rows(
    cell_rows: Sequence[Mapping[str, str]],
) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[Mapping[str, str]]] = defaultdict(list)
    for row in cell_rows:
        grouped[
            (
                text_value(row.get("opportunity_scope")),
                text_value(row.get("peak_hypothesis_id")),
            )
        ].append(row)
    result: list[dict[str, Any]] = []
    for (scope, row_id), rows in sorted(grouped.items()):
        mechanical_count = _count(rows, "mechanical_evidence_status", "present")
        trace_count = _count(rows, "trace_recovery_status", "present")
        ready_count = _count(
            rows,
            "evidence_availability_status",
            "immediate_expected_diff_ready",
        )
        requires_new = _count(
            rows,
            "evidence_availability_status",
            "requires_new_sample_local_evidence",
        )
        next_gate = (
            "collect_sample_local_ms1_identity_evidence"
            if scope == "active_default_row_blank_cell"
            else "parked_until_discovery_feature_inclusion_authority_changes"
        )
        result.append(
            {
                "schema_version": SCHEMA_VERSION,
                "row_scope": scope,
                "peak_hypothesis_id": row_id,
                "candidate_cell_count": len(rows),
                "mechanical_covered_cell_count": mechanical_count,
                "trace_recovered_cell_count": trace_count,
                "immediate_expected_diff_ready_cell_count": ready_count,
                "requires_new_sample_local_evidence_cell_count": requires_new,
                "product_authority_effect": "no_new_backfill_authority_gate_only",
                "next_gate": next_gate,
            }
        )
    return result


def _check_rows(facts: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [
        _check(
            "census_checker_pass",
            facts["census_problem_count"],
            0,
            facts["census_problem_count"] == 0,
        ),
        _check(
            "active_pressure_cell_count",
            facts["active_pressure_cell_count"],
            EXPECTED_COUNTS["active_pressure_cell_count"],
            facts["active_pressure_cell_count"]
            == EXPECTED_COUNTS["active_pressure_cell_count"]
            and facts["census_active_pressure_cell_count"]
            == EXPECTED_COUNTS["active_pressure_cell_count"],
        ),
        _check(
            "parked_pressure_cell_count",
            facts["parked_pressure_cell_count"],
            EXPECTED_COUNTS["parked_pressure_cell_count"],
            facts["parked_pressure_cell_count"]
            == EXPECTED_COUNTS["parked_pressure_cell_count"]
            and facts["census_parked_pressure_cell_count"]
            == EXPECTED_COUNTS["parked_pressure_cell_count"],
        ),
        _check(
            "active_mechanical_coverage_absent",
            facts["active_mechanical_covered_cell_count"],
            EXPECTED_COUNTS["active_mechanical_covered_cell_count"],
            facts["active_mechanical_covered_cell_count"]
            == EXPECTED_COUNTS["active_mechanical_covered_cell_count"],
            "Existing mechanical adjudication has no sample-local rows for "
            "the CID-NL active blank cells.",
        ),
        _check(
            "active_trace_recovery_coverage_absent",
            facts["active_trace_recovered_cell_count"],
            EXPECTED_COUNTS["active_trace_recovered_cell_count"],
            facts["active_trace_recovered_cell_count"]
            == EXPECTED_COUNTS["active_trace_recovered_cell_count"],
            "Existing trace recovery artifacts have no sample-local rows for "
            "the CID-NL active blank cells.",
        ),
        _check(
            "active_immediate_ready_count_zero",
            facts["active_immediate_expected_diff_ready_cell_count"],
            EXPECTED_COUNTS["active_immediate_expected_diff_ready_cell_count"],
            facts["active_immediate_expected_diff_ready_cell_count"]
            == EXPECTED_COUNTS["active_immediate_expected_diff_ready_cell_count"],
        ),
        _check(
            "active_requires_new_evidence_count",
            facts["active_requires_new_sample_local_evidence_cell_count"],
            EXPECTED_COUNTS[
                "active_requires_new_sample_local_evidence_cell_count"
            ],
            facts["active_requires_new_sample_local_evidence_cell_count"]
            == EXPECTED_COUNTS[
                "active_requires_new_sample_local_evidence_cell_count"
            ],
        ),
        _check(
            "parked_coverage_remains_parked",
            (
                f"mechanical={facts['parked_mechanical_covered_cell_count']};"
                f"trace={facts['parked_trace_recovered_cell_count']};"
                f"ready={facts['parked_immediate_expected_diff_ready_cell_count']}"
            ),
            "mechanical=0;trace=0;ready=0",
            facts["parked_mechanical_covered_cell_count"] == 0
            and facts["parked_trace_recovered_cell_count"] == 0
            and facts["parked_immediate_expected_diff_ready_cell_count"] == 0,
        ),
        _check(
            "cell_availability_output_count",
            facts["cell_availability_output_row_count"],
            EXPECTED_COUNTS["cell_availability_output_row_count"],
            facts["cell_availability_output_row_count"]
            == EXPECTED_COUNTS["cell_availability_output_row_count"],
        ),
        _check(
            "no_raw_or_writer_changes",
            "raw_or_85raw=FALSE;writer=FALSE;default_matrix=FALSE",
            "diagnostic availability gate only",
            True,
        ),
        _check(
            "no_row_or_family_projection",
            "row_or_family_evidence_projected_to_cells=FALSE",
            "sample-local key match required",
            True,
        ),
    ]


def _summary_payload(
    *,
    facts: Mapping[str, Any],
    checks_tsv: Path,
    row_manifest_tsv: Path,
    cell_availability_tsv: Path,
    census_summary_json: Path,
    census_checks_tsv: Path,
    census_row_manifest_tsv: Path,
    census_opportunity_cells_tsv: Path,
    mechanical_adjudication_index_tsv: Path,
    trace_recovery_report_tsv: Path,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "pass",
        "validation_label": "no_raw_backfill_expansion_evidence_availability",
        "product_lane": "backfill",
        "availability_scope": "cid_nl_active_blank_cells_from_backfill_census_v1",
        "strongest_evidence_tier": "85RAW-derived no-RAW artifact availability",
        "release_decision": "hold_for_new_sample_local_ms1_identity_evidence",
        **{
            field: facts[field]
            for field in (
                "active_pressure_cell_count",
                "parked_pressure_cell_count",
                "active_mechanical_covered_cell_count",
                "active_trace_recovered_cell_count",
                "active_immediate_expected_diff_ready_cell_count",
                "active_requires_new_sample_local_evidence_cell_count",
                "parked_mechanical_covered_cell_count",
                "parked_trace_recovered_cell_count",
                "parked_immediate_expected_diff_ready_cell_count",
                "cell_availability_output_row_count",
            )
        },
        "raw_or_85raw_ran": False,
        "product_writer_changed_by_checker": False,
        "default_quant_matrix_changed_by_checker": False,
        "workbook_or_gui_changed": False,
        "selected_peak_area_or_counting_changed": False,
        "backfill_writer_authority_changed_by_checker": False,
        "broad_backfill_unparked": False,
        "candidate_rows_are_matrix_rows": False,
        "row_or_family_evidence_projected_to_cells": False,
        "decision_statement": (
            "Existing Backfill mechanical adjudication and trace recovery "
            "surfaces do not cover the 929 CID-NL active blank cells. The next "
            "product gate must collect or generate sample-local MS1/identity "
            "evidence before any expected-diff writer expansion can be proposed."
        ),
        "authority_statement": (
            "This gate proves an evidence gap only. It grants no ProductWriter "
            "authority, creates no default matrix writes, and does not allow "
            "row-level or family-level evidence to be projected onto sample cells."
        ),
        "input_artifacts": {
            "census_summary_json": _artifact(census_summary_json),
            "census_checks_tsv": _artifact(census_checks_tsv),
            "census_row_manifest_tsv": _artifact(census_row_manifest_tsv),
            "census_opportunity_cells_tsv": _artifact(
                census_opportunity_cells_tsv,
            ),
            "mechanical_adjudication_index_tsv": _artifact(
                mechanical_adjudication_index_tsv,
            ),
            "trace_recovery_report_tsv": _artifact(trace_recovery_report_tsv),
        },
        "artifacts": {
            "summary_json": {
                "path": (
                    "docs/superpowers/validation/"
                    "backfill_expansion_evidence_availability_v1/"
                    "backfill_expansion_evidence_availability_summary.json"
                ),
                "retention_decision": "keep_summary",
            },
            "checks_tsv": _artifact(checks_tsv)
            | {"retention_decision": "keep_summary"},
            "row_manifest_tsv": _artifact(row_manifest_tsv)
            | {"retention_decision": "keep_contract"},
            "cell_availability_tsv": _artifact(cell_availability_tsv)
            | {
                "retention_decision": "externalize",
                "tracked_replacement_or_summary": (
                    "docs/superpowers/validation/"
                    "backfill_expansion_evidence_availability_v1/"
                    "backfill_expansion_evidence_availability_summary.json"
                ),
            },
        },
    }


def _write_readme(path: Path, *, payload: Mapping[str, Any]) -> None:
    lines = [
        "# Backfill Expansion Evidence Availability v1",
        "",
        "Status: `pass`.",
        "",
        "This is a no-RAW evidence-availability gate over the Backfill pressure "
        "created by CID-NL Discovery activation. It checks whether the current "
        "mechanical adjudication and trace recovery artifacts already contain "
        "sample-local evidence for the active blank cells.",
        "",
        "## Decision",
        "",
        "Release decision: `hold_for_new_sample_local_ms1_identity_evidence`.",
        "",
        "- Active Backfill pressure cells: "
        f"`{payload['active_pressure_cell_count']}`.",
        "- Existing mechanical adjudication coverage: "
        f"`{payload['active_mechanical_covered_cell_count']}`.",
        "- Existing trace recovery coverage: "
        f"`{payload['active_trace_recovered_cell_count']}`.",
        "- Immediate expected-diff-ready cells: "
        f"`{payload['active_immediate_expected_diff_ready_cell_count']}`.",
        "- Cells requiring new sample-local evidence: "
        f"`{payload['active_requires_new_sample_local_evidence_cell_count']}`.",
        "",
        "The key rule is strict: evidence must match the exact "
        "`peak_hypothesis_id + sample_stem` cell. Existing row/family evidence "
        "is not projected onto these CID-NL cells.",
        "",
        "## Boundary",
        "",
        "This gate does not run RAW, does not write a default matrix, does not "
        "change ProductWriter authority, and does not unpark broad Backfill.",
        "",
        "## Files",
        "",
        "- Summary JSON: "
        "`docs/superpowers/validation/"
        "backfill_expansion_evidence_availability_v1/"
        "backfill_expansion_evidence_availability_summary.json`",
        "- Checks TSV: "
        "`docs/superpowers/validation/"
        "backfill_expansion_evidence_availability_v1/"
        "backfill_expansion_evidence_availability_checks.tsv`",
        "- Compact row manifest: "
        "`docs/superpowers/validation/"
        "backfill_expansion_evidence_availability_v1/"
        "backfill_expansion_evidence_availability_row_manifest.tsv`",
        "- Full cell map: "
        "`output/validation/backfill_expansion_evidence_availability_v1/"
        "backfill_expansion_evidence_availability_cells.tsv`",
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
        hash_matches = artifact_hash_matches(path, expected_hash)
    except OSError as exc:
        problems.append(f"{artifact_id} sha256 cannot read: {exc}")
        return
    if not hash_matches:
        problems.append(f"summary {artifact_id} sha256 mismatch")


def _check_summary_input_artifact_hashes(
    payload: Mapping[str, Any],
    problems: list[str],
) -> None:
    check_summary_artifact_hashes(
        payload,
        root=ROOT,
        problems=problems,
        section_names=("input_artifacts",),
    )


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
    row_scopes = Counter(row.get("row_scope", "") for row in rows)
    if row_scopes.get("active_default_row_blank_cell", 0) != 20:
        problems.append("row_manifest active row count mismatch")
    if row_scopes.get("parked_authorized_nonactive_row_blank_cell", 0) != 23:
        problems.append("row_manifest parked row count mismatch")
    active_requires = sum(
        _int(row.get("requires_new_sample_local_evidence_cell_count"))
        for row in rows
        if row.get("row_scope") == "active_default_row_blank_cell"
    )
    if active_requires != EXPECTED_COUNTS[
        "active_requires_new_sample_local_evidence_cell_count"
    ]:
        problems.append("row_manifest active evidence gap count mismatch")
    for row in rows:
        if row.get("schema_version") != SCHEMA_VERSION:
            problems.append("row_manifest schema_version mismatch")
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
    expected_hash = text_value(artifact.get("sha256"))
    if path.exists() and not artifact_hash_matches(path, expected_hash):
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
        "--census-summary-json",
        type=Path,
        default=DEFAULT_CENSUS_SUMMARY_JSON,
    )
    parser.add_argument(
        "--census-checks-tsv",
        type=Path,
        default=DEFAULT_CENSUS_CHECKS_TSV,
    )
    parser.add_argument(
        "--census-row-manifest-tsv",
        type=Path,
        default=DEFAULT_CENSUS_ROW_MANIFEST_TSV,
    )
    parser.add_argument(
        "--census-opportunity-cells-tsv",
        type=Path,
        default=DEFAULT_CENSUS_OPPORTUNITY_CELLS_TSV,
    )
    parser.add_argument(
        "--mechanical-adjudication-index-tsv",
        type=Path,
        default=DEFAULT_MECHANICAL_ADJUDICATION_INDEX_TSV,
    )
    parser.add_argument(
        "--trace-recovery-report-tsv",
        type=Path,
        default=DEFAULT_TRACE_RECOVERY_REPORT_TSV,
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
            args.docs_dir / "backfill_expansion_evidence_availability_summary.json"
        )
        checks_tsv = args.checks_tsv or (
            args.docs_dir / "backfill_expansion_evidence_availability_checks.tsv"
        )
        row_manifest_tsv = args.row_manifest_tsv or (
            args.docs_dir
            / "backfill_expansion_evidence_availability_row_manifest.tsv"
        )
        problems = check_backfill_expansion_evidence_availability(
            summary_json=summary_json,
            checks_tsv=checks_tsv,
            row_manifest_tsv=row_manifest_tsv,
        )
        for problem in problems:
            print(f"backfill_expansion_evidence_availability_problem: {problem}")
        return 2 if problems else 0

    try:
        payload = build_backfill_expansion_evidence_availability(
            docs_dir=args.docs_dir,
            output_dir=args.output_dir,
            census_summary_json=args.census_summary_json,
            census_checks_tsv=args.census_checks_tsv,
            census_row_manifest_tsv=args.census_row_manifest_tsv,
            census_opportunity_cells_tsv=args.census_opportunity_cells_tsv,
            mechanical_adjudication_index_tsv=(
                args.mechanical_adjudication_index_tsv
            ),
            trace_recovery_report_tsv=args.trace_recovery_report_tsv,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    summary_path = (
        args.docs_dir / "backfill_expansion_evidence_availability_summary.json"
    )
    print(f"backfill_expansion_evidence_availability_summary: {summary_path}")
    print(f"backfill_expansion_evidence_availability_status: {payload['status']}")
    print(
        "backfill_expansion_evidence_availability_release_decision: "
        f"{payload['release_decision']}"
    )
    if args.require_pass and payload.get("status") != "pass":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
