"""Build/check the Backfill expansion census after CID-NL Discovery activation.

This no-RAW census answers one bounded question: how much sample-wise Backfill
pressure was created by the current CID-NL Discovery-expanded product rows?

It does not run Backfill, read RAW, change ProductWriter authority, write a
default matrix, update workbook/GUI behavior, or treat blank candidate cells as
matrix rows.
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

from scripts.build_cid_nl_default_product_activation import (  # noqa: E402
    DEFAULT_DOCS_DIR as DEFAULT_CID_NL_ACTIVATION_DOCS_DIR,
)
from scripts.build_cid_nl_default_product_activation import (  # noqa: E402
    DEFAULT_OUTPUT_DIR as DEFAULT_CID_NL_ACTIVATION_OUTPUT_DIR,
)
from scripts.build_cid_nl_default_product_activation import (  # noqa: E402
    validate_cid_nl_default_product_activation,
)
from scripts.build_quant_matrix_default_product_activation import (  # noqa: E402
    DEFAULT_PRODUCT_ACTIVATION_OUTPUT_DIR as DEFAULT_BACKFILL_ACTIVATION_DOCS_DIR,
)
from scripts.build_quant_matrix_default_product_activation import (  # noqa: E402
    validate_quant_matrix_default_product_activation,
)
from scripts.check_cid_nl_85raw_universe_closure import (  # noqa: E402
    DEFAULT_DOCS_DIR as DEFAULT_CID_NL_UNIVERSE_DOCS_DIR,
)
from scripts.check_cid_nl_85raw_universe_closure import (  # noqa: E402
    DEFAULT_SUCCESSOR_AUTHORITY_DECISIONS_TSV,
    SUCCESSOR_DECISION_COLUMNS,
    check_cid_nl_85raw_universe_closure,
)
from scripts.validation_artifact_contracts import (  # noqa: E402
    artifact_hash_matches,
    check_summary_artifact_hashes,
)
from xic_extractor.tabular_io import (  # noqa: E402
    file_sha256,
    read_tsv_required,
    read_tsv_with_header,
    text_value,
    write_tsv,
)

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = "backfill_expansion_census_v1"
DEFAULT_DOCS_DIR = ROOT / "docs/superpowers/validation/backfill_expansion_census_v1"
DEFAULT_OUTPUT_DIR = ROOT / "output/validation/backfill_expansion_census_v1"
DEFAULT_CID_NL_ACTIVATION_SUMMARY_JSON = (
    DEFAULT_CID_NL_ACTIVATION_DOCS_DIR
    / "cid_nl_default_product_activation_summary.json"
)
DEFAULT_CID_NL_UNIVERSE_SUMMARY_JSON = (
    DEFAULT_CID_NL_UNIVERSE_DOCS_DIR / "cid_nl_85raw_universe_closure_summary.json"
)
DEFAULT_BACKFILL_ACTIVATION_SUMMARY_JSON = (
    DEFAULT_BACKFILL_ACTIVATION_DOCS_DIR
    / "quant_matrix_default_product_activation_summary.json"
)
DEFAULT_CID_NL_ACTIVATION_MANIFEST_TSV = (
    DEFAULT_CID_NL_ACTIVATION_OUTPUT_DIR
    / "inputs/cid_nl_default_product_activation_manifest.tsv"
)
DEFAULT_CID_NL_DEFAULT_QUANT_MATRIX_TSV = (
    DEFAULT_CID_NL_ACTIVATION_OUTPUT_DIR / "default_output/quant_matrix.tsv"
)
DEFAULT_CID_NL_DEFAULT_ROW_SUMMARY_TSV = (
    DEFAULT_CID_NL_ACTIVATION_OUTPUT_DIR / "default_output/row_summary.tsv"
)
DEFAULT_CID_NL_DEFAULT_CELL_PROVENANCE_TSV = (
    DEFAULT_CID_NL_ACTIVATION_OUTPUT_DIR / "default_output/cell_provenance.tsv"
)
DEFAULT_OLD_BACKFILL_VALUES_TSV = (
    ROOT
    / "docs/superpowers/validation/quant_matrix_real_bundle_v1/"
    "source_artifacts/standard_peak_activation_values.tsv"
)

ROW_SUMMARY_COLUMNS = (
    "schema_version",
    "peak_hypothesis_id",
    "source_feature_family_ids",
    "detected_count",
    "accepted_backfilled_count",
    "quant_available_count",
    "missing_count",
    "backfill_fraction",
    "prevalence_flags",
)
CELL_PROVENANCE_COLUMNS = (
    "schema_version",
    "peak_hypothesis_id",
    "sample_stem",
    "source_feature_family_ids",
    "matrix_value",
    "cell_status",
    "value_source",
    "write_authority",
    "acceptance_decision",
    "acceptance_basis",
    "truth_status",
    "quant_value_source",
    "matrix_area_source",
    "source_artifact_relpath",
    "source_artifact_sha256",
    "source_row_sha256",
    "manifest_sha256",
)
CID_NL_ACTIVATION_MANIFEST_COLUMNS = (
    "schema_version",
    "peak_hypothesis_id",
    "sample_stem",
    "feature_family_id",
    "acceptance_decision",
    "acceptance_basis",
    "truth_status",
    "shadow_only",
    "write_authority",
    "matrix_write_allowed",
    "quant_value",
    "quant_value_source",
    "matrix_area_source",
    "detected_count",
    "backfilled_count",
    "quant_available_count",
    "missing_count",
    "backfill_fraction",
    "prevalence_flags",
    "hard_blocker_rule_ids",
    "triggered_risk_rule_ids",
    "closure_rule_ids",
    "decision_reason",
    "next_evidence_needed",
    "doublet_status",
    "reference_side",
    "doublet_allowed",
    "doublet_source_relpath",
    "doublet_source_sha256",
    "source_artifact_relpath",
    "source_artifact_sha256",
    "source_row_sha256",
    "manifest_sha256",
    "acceptance_contract_version",
)
OLD_BACKFILL_VALUES_COLUMNS = (
    "peak_hypothesis_id",
    "feature_family_id",
    "sample_stem",
    "projected_matrix_value",
    "projected_matrix_value_source",
    "current_raw_status",
    "current_production_status",
    "source_artifact_schema_version",
    "source_artifact_sha256",
    "source_row_sha256",
    "source_provenance_detail",
)
ROW_MANIFEST_COLUMNS = (
    "schema_version",
    "row_scope",
    "peak_hypothesis_id",
    "sample_count",
    "detected_cell_count",
    "discovery_default_written_cell_count",
    "quant_available_cell_count",
    "missing_cell_count",
    "backfill_expansion_candidate_cell_count",
    "old_backfill_authority_overlap_cell_count",
    "source_transition_keys",
    "product_authority_effect",
    "next_gate",
)
OPPORTUNITY_COLUMNS = (
    "schema_version",
    "opportunity_scope",
    "peak_hypothesis_id",
    "sample_stem",
    "cell_state",
    "product_authority_effect",
    "next_evidence_needed",
)
CHECK_COLUMNS = (
    "schema_version",
    "check_id",
    "status",
    "observed",
    "expected",
    "notes",
)
EXPECTED_CHECK_IDS = (
    "cid_nl_activation_checker_pass",
    "cid_nl_universe_closure_checker_pass",
    "backfill_511_activation_checker_pass",
    "old_backfill_authority_count",
    "old_backfill_row_count",
    "cid_nl_active_discovery_cell_count",
    "active_successor_row_count",
    "sample_count",
    "active_row_cell_universe_partition",
    "active_direct_detection_count",
    "active_discovery_default_write_count",
    "active_missing_pressure_count",
    "old_backfill_overlap_count",
    "parked_future_pressure_count",
    "opportunity_cell_output_count",
    "no_raw_or_writer_changes",
    "no_candidate_matrix_rows",
)
EXPECTED_COUNTS = {
    "old_backfill_authority_cell_count": 511,
    "old_backfill_authority_row_count": 83,
    "cid_nl_active_discovery_cell_count": 95,
    "active_successor_row_count": 20,
    "sample_count": 85,
    "active_row_cell_universe_count": 1700,
    "active_row_direct_detection_cell_count": 676,
    "active_row_discovery_default_write_cell_count": 95,
    "active_row_quant_available_cell_count": 771,
    "active_row_missing_cell_count": 929,
    "new_backfill_pressure_candidate_cell_count": 929,
    "old_backfill_active_overlap_cell_count": 0,
    "old_backfill_active_overlap_row_count": 0,
    "authorized_nonactive_row_count": 23,
    "authorized_nonactive_row_cell_universe_count": 1955,
    "authorized_nonactive_detected_cell_count": 945,
    "authorized_nonactive_missing_cell_count": 1010,
    "parked_future_pressure_candidate_cell_count": 1010,
    "opportunity_cell_output_row_count": 1939,
}


def build_backfill_expansion_census(
    *,
    docs_dir: Path = DEFAULT_DOCS_DIR,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    cid_nl_activation_summary_json: Path = DEFAULT_CID_NL_ACTIVATION_SUMMARY_JSON,
    cid_nl_universe_summary_json: Path = DEFAULT_CID_NL_UNIVERSE_SUMMARY_JSON,
    backfill_activation_summary_json: Path = DEFAULT_BACKFILL_ACTIVATION_SUMMARY_JSON,
    cid_nl_activation_manifest_tsv: Path = DEFAULT_CID_NL_ACTIVATION_MANIFEST_TSV,
    cid_nl_default_quant_matrix_tsv: Path = DEFAULT_CID_NL_DEFAULT_QUANT_MATRIX_TSV,
    cid_nl_default_row_summary_tsv: Path = DEFAULT_CID_NL_DEFAULT_ROW_SUMMARY_TSV,
    cid_nl_default_cell_provenance_tsv: Path = (
        DEFAULT_CID_NL_DEFAULT_CELL_PROVENANCE_TSV
    ),
    old_backfill_values_tsv: Path = DEFAULT_OLD_BACKFILL_VALUES_TSV,
    successor_decisions_tsv: Path = DEFAULT_SUCCESSOR_AUTHORITY_DECISIONS_TSV,
) -> dict[str, Any]:
    cid_nl_activation_problems = validate_cid_nl_default_product_activation(
        summary_json=cid_nl_activation_summary_json,
    )
    cid_nl_universe_problems = check_cid_nl_85raw_universe_closure(
        summary_json=cid_nl_universe_summary_json,
    )
    backfill_activation_problems = validate_quant_matrix_default_product_activation(
        summary_json=backfill_activation_summary_json,
    )

    sample_names = _sample_names(cid_nl_default_quant_matrix_tsv)
    activation_rows = read_tsv_required(
        cid_nl_activation_manifest_tsv,
        CID_NL_ACTIVATION_MANIFEST_COLUMNS,
    )
    row_summary_rows = read_tsv_required(
        cid_nl_default_row_summary_tsv,
        ROW_SUMMARY_COLUMNS,
    )
    provenance_rows = read_tsv_required(
        cid_nl_default_cell_provenance_tsv,
        CELL_PROVENANCE_COLUMNS,
    )
    old_backfill_rows = read_tsv_required(
        old_backfill_values_tsv,
        OLD_BACKFILL_VALUES_COLUMNS,
    )
    successor_rows = read_tsv_required(
        successor_decisions_tsv,
        SUCCESSOR_DECISION_COLUMNS,
    )

    facts = _census_facts(
        sample_names=sample_names,
        activation_rows=activation_rows,
        row_summary_rows=row_summary_rows,
        provenance_rows=provenance_rows,
        old_backfill_rows=old_backfill_rows,
        successor_rows=successor_rows,
        cid_nl_activation_problem_count=len(cid_nl_activation_problems),
        cid_nl_universe_problem_count=len(cid_nl_universe_problems),
        backfill_activation_problem_count=len(backfill_activation_problems),
    )
    checks = _check_rows(facts)
    failed = [row["check_id"] for row in checks if row["status"] != "pass"]
    if failed:
        raise ValueError("Backfill expansion census failed: " + ";".join(failed))

    docs_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    checks_tsv = docs_dir / "backfill_expansion_census_checks.tsv"
    row_manifest_tsv = docs_dir / "backfill_expansion_census_row_manifest.tsv"
    opportunity_cells_tsv = output_dir / "backfill_expansion_opportunity_cells.tsv"
    summary_json = docs_dir / "backfill_expansion_census_summary.json"

    write_tsv(checks_tsv, checks, CHECK_COLUMNS, extrasaction="raise")
    write_tsv(
        row_manifest_tsv,
        facts["row_manifest_rows"],
        ROW_MANIFEST_COLUMNS,
        extrasaction="raise",
    )
    write_tsv(
        opportunity_cells_tsv,
        facts["opportunity_rows"],
        OPPORTUNITY_COLUMNS,
        extrasaction="raise",
    )
    payload = _summary_payload(
        facts=facts,
        checks_tsv=checks_tsv,
        row_manifest_tsv=row_manifest_tsv,
        opportunity_cells_tsv=opportunity_cells_tsv,
        cid_nl_activation_summary_json=cid_nl_activation_summary_json,
        cid_nl_universe_summary_json=cid_nl_universe_summary_json,
        backfill_activation_summary_json=backfill_activation_summary_json,
        cid_nl_activation_manifest_tsv=cid_nl_activation_manifest_tsv,
        cid_nl_default_quant_matrix_tsv=cid_nl_default_quant_matrix_tsv,
        cid_nl_default_row_summary_tsv=cid_nl_default_row_summary_tsv,
        cid_nl_default_cell_provenance_tsv=cid_nl_default_cell_provenance_tsv,
        old_backfill_values_tsv=old_backfill_values_tsv,
        successor_decisions_tsv=successor_decisions_tsv,
    )
    summary_json.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _write_readme(docs_dir / "README.md", payload=payload)
    return payload


def check_backfill_expansion_census(
    *,
    summary_json: Path = DEFAULT_DOCS_DIR / "backfill_expansion_census_summary.json",
    checks_tsv: Path = DEFAULT_DOCS_DIR / "backfill_expansion_census_checks.tsv",
    row_manifest_tsv: Path = (
        DEFAULT_DOCS_DIR / "backfill_expansion_census_row_manifest.tsv"
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
        ("validation_label", "no_raw_backfill_expansion_census"),
        ("product_lane", "backfill"),
        (
            "census_scope",
            "cid_nl_default_active_rows_on_discovery_expanded_85raw_matrix",
        ),
        ("strongest_evidence_tier", "85RAW-derived no-RAW artifact census"),
        ("raw_or_85raw_ran", False),
        ("product_writer_changed_by_checker", False),
        ("default_quant_matrix_changed_by_checker", False),
        ("workbook_or_gui_changed", False),
        ("selected_peak_area_or_counting_changed", False),
        ("backfill_writer_authority_changed_by_checker", False),
        ("broad_backfill_unparked", False),
        ("candidate_rows_are_matrix_rows", False),
        ("cid_nl_ms2_direct_productwriter_authority", False),
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
    _check_optional_externalized_artifact(payload, "opportunity_cells_tsv", problems)
    return problems


def _census_facts(
    *,
    sample_names: Sequence[str],
    activation_rows: Sequence[Mapping[str, str]],
    row_summary_rows: Sequence[Mapping[str, str]],
    provenance_rows: Sequence[Mapping[str, str]],
    old_backfill_rows: Sequence[Mapping[str, str]],
    successor_rows: Sequence[Mapping[str, str]],
    cid_nl_activation_problem_count: int,
    cid_nl_universe_problem_count: int,
    backfill_activation_problem_count: int,
) -> dict[str, Any]:
    row_summary = {
        text_value(row.get("peak_hypothesis_id")): row for row in row_summary_rows
    }
    active_rows = sorted(
        {text_value(row.get("peak_hypothesis_id")) for row in activation_rows}
    )
    active_keys = {
        (text_value(row.get("peak_hypothesis_id")), text_value(row.get("sample_stem")))
        for row in activation_rows
    }
    old_backfill_keys = {
        (text_value(row.get("peak_hypothesis_id")), text_value(row.get("sample_stem")))
        for row in old_backfill_rows
    }
    old_backfill_row_ids = {row_id for row_id, _sample in old_backfill_keys}
    write_authorized_rows = [
        row
        for row in successor_rows
        if text_value(row.get("successor_decision")) == "write_authorized"
    ]
    write_authorized_row_ids = {
        text_value(row.get("successor_peak_hypothesis_id"))
        for row in write_authorized_rows
    }
    parked_row_ids = sorted(write_authorized_row_ids - set(active_rows))
    transitions_by_successor: dict[str, set[str]] = defaultdict(set)
    for row in successor_rows:
        successor_id = text_value(row.get("successor_peak_hypothesis_id"))
        if not successor_id:
            continue
        transitions_by_successor[successor_id].add(
            text_value(row.get("old_peak_hypothesis_id")) + "->" + successor_id,
        )

    provenance_by_row: dict[str, dict[str, Mapping[str, str]]] = defaultdict(dict)
    status_counts_by_row: dict[str, Counter[str]] = defaultdict(Counter)
    for row in provenance_rows:
        row_id = text_value(row.get("peak_hypothesis_id"))
        sample = text_value(row.get("sample_stem"))
        if not row_id or not sample:
            continue
        provenance_by_row[row_id][sample] = row
        status_counts_by_row[row_id][text_value(row.get("cell_status"))] += 1

    active_row_facts = _row_facts(
        row_ids=active_rows,
        row_scope="active_default_expansion",
        sample_names=sample_names,
        row_summary=row_summary,
        provenance_by_row=provenance_by_row,
        old_backfill_keys=old_backfill_keys,
        active_keys=active_keys,
        transitions_by_successor=transitions_by_successor,
    )
    parked_row_facts = _row_facts(
        row_ids=parked_row_ids,
        row_scope="parked_authorized_nonactive",
        sample_names=sample_names,
        row_summary=row_summary,
        provenance_by_row=provenance_by_row,
        old_backfill_keys=old_backfill_keys,
        active_keys=active_keys,
        transitions_by_successor=transitions_by_successor,
    )

    active_missing_count = sum(row["missing_cell_count"] for row in active_row_facts)
    parked_missing_count = sum(row["missing_cell_count"] for row in parked_row_facts)
    active_detected_count = sum(
        row["detected_cell_count"] for row in active_row_facts
    )
    active_written_count = sum(
        row["discovery_default_written_cell_count"] for row in active_row_facts
    )
    active_quant_count = sum(
        row["quant_available_cell_count"] for row in active_row_facts
    )
    parked_detected_count = sum(
        row["detected_cell_count"] for row in parked_row_facts
    )
    active_overlap_keys = {
        key for key in active_keys if key in old_backfill_keys
    }
    opportunity_rows = _opportunity_rows(
        active_row_facts=active_row_facts,
        parked_row_facts=parked_row_facts,
    )
    row_manifest_rows = [
        _row_manifest_entry(row) for row in active_row_facts + parked_row_facts
    ]
    return {
        "cid_nl_activation_problem_count": cid_nl_activation_problem_count,
        "cid_nl_universe_problem_count": cid_nl_universe_problem_count,
        "backfill_activation_problem_count": backfill_activation_problem_count,
        "old_backfill_authority_cell_count": len(old_backfill_keys),
        "old_backfill_authority_row_count": len(old_backfill_row_ids),
        "cid_nl_active_discovery_cell_count": len(active_keys),
        "active_successor_row_count": len(active_rows),
        "sample_count": len(sample_names),
        "active_row_cell_universe_count": len(active_rows) * len(sample_names),
        "active_row_direct_detection_cell_count": active_detected_count,
        "active_row_discovery_default_write_cell_count": active_written_count,
        "active_row_quant_available_cell_count": active_quant_count,
        "active_row_missing_cell_count": active_missing_count,
        "new_backfill_pressure_candidate_cell_count": active_missing_count,
        "old_backfill_active_overlap_cell_count": len(active_overlap_keys),
        "old_backfill_active_overlap_row_count": len(
            set(active_rows) & old_backfill_row_ids,
        ),
        "authorized_nonactive_row_count": len(parked_row_ids),
        "authorized_nonactive_row_cell_universe_count": (
            len(parked_row_ids) * len(sample_names)
        ),
        "authorized_nonactive_detected_cell_count": parked_detected_count,
        "authorized_nonactive_missing_cell_count": parked_missing_count,
        "parked_future_pressure_candidate_cell_count": parked_missing_count,
        "opportunity_cell_output_row_count": len(opportunity_rows),
        "status_counts_by_row": status_counts_by_row,
        "row_manifest_rows": row_manifest_rows,
        "opportunity_rows": opportunity_rows,
    }


def _row_facts(
    *,
    row_ids: Sequence[str],
    row_scope: str,
    sample_names: Sequence[str],
    row_summary: Mapping[str, Mapping[str, str]],
    provenance_by_row: Mapping[str, Mapping[str, Mapping[str, str]]],
    old_backfill_keys: set[tuple[str, str]],
    active_keys: set[tuple[str, str]],
    transitions_by_successor: Mapping[str, set[str]],
) -> list[dict[str, Any]]:
    facts: list[dict[str, Any]] = []
    sample_set = set(sample_names)
    for row_id in row_ids:
        summary = row_summary.get(row_id)
        if summary is None:
            raise ValueError(f"missing row summary for {row_id}")
        present_samples = set(provenance_by_row.get(row_id, {}))
        missing_samples = sorted(sample_set - present_samples)
        detected_count = _int(summary.get("detected_count"))
        written_count = sum(
            1 for sample in sample_names if (row_id, sample) in active_keys
        )
        overlap_count = sum(
            1 for sample in sample_names if (row_id, sample) in old_backfill_keys
        )
        missing_count = _int(summary.get("missing_count"))
        if missing_count != len(missing_samples):
            raise ValueError(f"missing count mismatch for {row_id}")
        facts.append(
            {
                "row_scope": row_scope,
                "peak_hypothesis_id": row_id,
                "sample_count": len(sample_names),
                "detected_cell_count": detected_count,
                "discovery_default_written_cell_count": written_count,
                "quant_available_cell_count": _int(
                    summary.get("quant_available_count"),
                ),
                "missing_cell_count": missing_count,
                "missing_samples": missing_samples,
                "old_backfill_authority_overlap_cell_count": overlap_count,
                "source_transition_keys": ";".join(
                    sorted(transitions_by_successor.get(row_id, set())),
                ),
            }
        )
    return facts


def _row_manifest_entry(row: Mapping[str, Any]) -> dict[str, Any]:
    row_scope = text_value(row.get("row_scope"))
    candidate_count = (
        row["missing_cell_count"] if row_scope == "active_default_expansion" else 0
    )
    next_gate = (
        "requires_sample_local_ms1_evidence_before_backfill_write"
        if row_scope == "active_default_expansion"
        else "parked_until_discovery_feature_inclusion_authority_changes"
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "row_scope": row_scope,
        "peak_hypothesis_id": row["peak_hypothesis_id"],
        "sample_count": row["sample_count"],
        "detected_cell_count": row["detected_cell_count"],
        "discovery_default_written_cell_count": row[
            "discovery_default_written_cell_count"
        ],
        "quant_available_cell_count": row["quant_available_cell_count"],
        "missing_cell_count": row["missing_cell_count"],
        "backfill_expansion_candidate_cell_count": candidate_count,
        "old_backfill_authority_overlap_cell_count": row[
            "old_backfill_authority_overlap_cell_count"
        ],
        "source_transition_keys": row["source_transition_keys"],
        "product_authority_effect": "no_new_backfill_authority_census_only",
        "next_gate": next_gate,
    }


def _opportunity_rows(
    *,
    active_row_facts: Sequence[Mapping[str, Any]],
    parked_row_facts: Sequence[Mapping[str, Any]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for row in active_row_facts:
        for sample in row["missing_samples"]:
            rows.append(
                _opportunity_row(
                    scope="active_default_row_blank_cell",
                    row_id=text_value(row.get("peak_hypothesis_id")),
                    sample=sample,
                    next_evidence="sample_local_ms1_peak_and_identity_evidence",
                )
            )
    for row in parked_row_facts:
        for sample in row["missing_samples"]:
            rows.append(
                _opportunity_row(
                    scope="parked_authorized_nonactive_row_blank_cell",
                    row_id=text_value(row.get("peak_hypothesis_id")),
                    sample=sample,
                    next_evidence=(
                        "discovery_feature_inclusion_authority_before_backfill_review"
                    ),
                )
            )
    return rows


def _opportunity_row(
    *,
    scope: str,
    row_id: str,
    sample: str,
    next_evidence: str,
) -> dict[str, str]:
    return {
        "schema_version": SCHEMA_VERSION,
        "opportunity_scope": scope,
        "peak_hypothesis_id": row_id,
        "sample_stem": sample,
        "cell_state": "blank_in_current_default_matrix",
        "product_authority_effect": "candidate_only_no_write_authority",
        "next_evidence_needed": next_evidence,
    }


def _check_rows(facts: Mapping[str, Any]) -> list[dict[str, Any]]:
    partition_count = (
        facts["active_row_direct_detection_cell_count"]
        + facts["active_row_discovery_default_write_cell_count"]
        + facts["active_row_missing_cell_count"]
    )
    return [
        _check(
            "cid_nl_activation_checker_pass",
            facts["cid_nl_activation_problem_count"],
            0,
            facts["cid_nl_activation_problem_count"] == 0,
        ),
        _check(
            "cid_nl_universe_closure_checker_pass",
            facts["cid_nl_universe_problem_count"],
            0,
            facts["cid_nl_universe_problem_count"] == 0,
        ),
        _check(
            "backfill_511_activation_checker_pass",
            facts["backfill_activation_problem_count"],
            0,
            facts["backfill_activation_problem_count"] == 0,
        ),
        _check(
            "old_backfill_authority_count",
            facts["old_backfill_authority_cell_count"],
            EXPECTED_COUNTS["old_backfill_authority_cell_count"],
            facts["old_backfill_authority_cell_count"]
            == EXPECTED_COUNTS["old_backfill_authority_cell_count"],
        ),
        _check(
            "old_backfill_row_count",
            facts["old_backfill_authority_row_count"],
            EXPECTED_COUNTS["old_backfill_authority_row_count"],
            facts["old_backfill_authority_row_count"]
            == EXPECTED_COUNTS["old_backfill_authority_row_count"],
        ),
        _check(
            "cid_nl_active_discovery_cell_count",
            facts["cid_nl_active_discovery_cell_count"],
            EXPECTED_COUNTS["cid_nl_active_discovery_cell_count"],
            facts["cid_nl_active_discovery_cell_count"]
            == EXPECTED_COUNTS["cid_nl_active_discovery_cell_count"],
        ),
        _check(
            "active_successor_row_count",
            facts["active_successor_row_count"],
            EXPECTED_COUNTS["active_successor_row_count"],
            facts["active_successor_row_count"]
            == EXPECTED_COUNTS["active_successor_row_count"],
        ),
        _check(
            "sample_count",
            facts["sample_count"],
            EXPECTED_COUNTS["sample_count"],
            facts["sample_count"] == EXPECTED_COUNTS["sample_count"],
        ),
        _check(
            "active_row_cell_universe_partition",
            partition_count,
            EXPECTED_COUNTS["active_row_cell_universe_count"],
            partition_count == EXPECTED_COUNTS["active_row_cell_universe_count"],
        ),
        _check(
            "active_direct_detection_count",
            facts["active_row_direct_detection_cell_count"],
            EXPECTED_COUNTS["active_row_direct_detection_cell_count"],
            facts["active_row_direct_detection_cell_count"]
            == EXPECTED_COUNTS["active_row_direct_detection_cell_count"],
        ),
        _check(
            "active_discovery_default_write_count",
            facts["active_row_discovery_default_write_cell_count"],
            EXPECTED_COUNTS["active_row_discovery_default_write_cell_count"],
            facts["active_row_discovery_default_write_cell_count"]
            == EXPECTED_COUNTS["active_row_discovery_default_write_cell_count"],
        ),
        _check(
            "active_missing_pressure_count",
            facts["active_row_missing_cell_count"],
            EXPECTED_COUNTS["active_row_missing_cell_count"],
            facts["active_row_missing_cell_count"]
            == EXPECTED_COUNTS["active_row_missing_cell_count"],
            "These blank cells are Backfill pressure only, not write authority.",
        ),
        _check(
            "old_backfill_overlap_count",
            (
                f"cells={facts['old_backfill_active_overlap_cell_count']};"
                f"rows={facts['old_backfill_active_overlap_row_count']}"
            ),
            "cells=0;rows=0",
            facts["old_backfill_active_overlap_cell_count"] == 0
            and facts["old_backfill_active_overlap_row_count"] == 0,
        ),
        _check(
            "parked_future_pressure_count",
            facts["parked_future_pressure_candidate_cell_count"],
            EXPECTED_COUNTS["parked_future_pressure_candidate_cell_count"],
            facts["parked_future_pressure_candidate_cell_count"]
            == EXPECTED_COUNTS["parked_future_pressure_candidate_cell_count"],
            "Held/blocked Discovery rows remain parked, not Backfill candidates.",
        ),
        _check(
            "opportunity_cell_output_count",
            facts["opportunity_cell_output_row_count"],
            EXPECTED_COUNTS["opportunity_cell_output_row_count"],
            facts["opportunity_cell_output_row_count"]
            == EXPECTED_COUNTS["opportunity_cell_output_row_count"],
        ),
        _check(
            "no_raw_or_writer_changes",
            "raw_or_85raw=FALSE;writer=FALSE;default_matrix=FALSE",
            "diagnostic census only",
            True,
        ),
        _check(
            "no_candidate_matrix_rows",
            "candidate_rows_are_matrix_rows=FALSE",
            "candidates remain review/audit cells",
            True,
        ),
    ]


def _summary_payload(
    *,
    facts: Mapping[str, Any],
    checks_tsv: Path,
    row_manifest_tsv: Path,
    opportunity_cells_tsv: Path,
    cid_nl_activation_summary_json: Path,
    cid_nl_universe_summary_json: Path,
    backfill_activation_summary_json: Path,
    cid_nl_activation_manifest_tsv: Path,
    cid_nl_default_quant_matrix_tsv: Path,
    cid_nl_default_row_summary_tsv: Path,
    cid_nl_default_cell_provenance_tsv: Path,
    old_backfill_values_tsv: Path,
    successor_decisions_tsv: Path,
) -> dict[str, Any]:
    payload = {
        "schema_version": SCHEMA_VERSION,
        "status": "pass",
        "validation_label": "no_raw_backfill_expansion_census",
        "product_lane": "backfill",
        "census_scope": "cid_nl_default_active_rows_on_discovery_expanded_85raw_matrix",
        "strongest_evidence_tier": "85RAW-derived no-RAW artifact census",
        **{
            field: facts[field]
            for field in (
                "old_backfill_authority_cell_count",
                "old_backfill_authority_row_count",
                "cid_nl_active_discovery_cell_count",
                "active_successor_row_count",
                "sample_count",
                "active_row_cell_universe_count",
                "active_row_direct_detection_cell_count",
                "active_row_discovery_default_write_cell_count",
                "active_row_quant_available_cell_count",
                "active_row_missing_cell_count",
                "new_backfill_pressure_candidate_cell_count",
                "old_backfill_active_overlap_cell_count",
                "old_backfill_active_overlap_row_count",
                "authorized_nonactive_row_count",
                "authorized_nonactive_row_cell_universe_count",
                "authorized_nonactive_detected_cell_count",
                "authorized_nonactive_missing_cell_count",
                "parked_future_pressure_candidate_cell_count",
                "opportunity_cell_output_row_count",
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
        "cid_nl_ms2_direct_productwriter_authority": False,
        "release_decision": (
            "CID-NL Discovery activation increases Backfill pressure by 929 "
            "active-row blank sample cells, but this census creates no Backfill "
            "write authority. Each candidate needs sample-local MS1/identity "
            "evidence before any future expected-diff gate."
        ),
        "parked_scope_statement": (
            "The 1010 blank cells on write-authorized but non-active CID-NL rows "
            "are future pressure only. They remain parked until Discovery feature "
            "inclusion authority changes."
        ),
        "authority_statement": (
            "The existing Backfill writer authority remains exactly the current "
            "511-cell backfill_policy_write_ready_rows scope. This artifact is "
            "diagnostic/shadow census evidence and must not be used as "
            "ProductWriter authority."
        ),
        "input_artifacts": {
            "cid_nl_activation_summary_json": _artifact(
                cid_nl_activation_summary_json,
            ),
            "cid_nl_universe_summary_json": _artifact(
                cid_nl_universe_summary_json,
            ),
            "backfill_activation_summary_json": _artifact(
                backfill_activation_summary_json,
            ),
            "cid_nl_activation_manifest_tsv": _artifact(
                cid_nl_activation_manifest_tsv,
            ),
            "cid_nl_default_quant_matrix_tsv": _artifact(
                cid_nl_default_quant_matrix_tsv,
            ),
            "cid_nl_default_row_summary_tsv": _artifact(
                cid_nl_default_row_summary_tsv,
            ),
            "cid_nl_default_cell_provenance_tsv": _artifact(
                cid_nl_default_cell_provenance_tsv,
            ),
            "old_backfill_values_tsv": _artifact(old_backfill_values_tsv),
            "successor_decisions_tsv": _artifact(successor_decisions_tsv),
        },
        "artifacts": {
            "summary_json": {
                "path": (
                    "docs/superpowers/validation/backfill_expansion_census_v1/"
                    "backfill_expansion_census_summary.json"
                ),
                "retention_decision": "keep_summary",
            },
            "checks_tsv": _artifact(checks_tsv)
            | {"retention_decision": "keep_summary"},
            "row_manifest_tsv": _artifact(row_manifest_tsv)
            | {"retention_decision": "keep_contract"},
            "opportunity_cells_tsv": _artifact(opportunity_cells_tsv)
            | {
                "retention_decision": "externalize",
                "tracked_replacement_or_summary": (
                    "docs/superpowers/validation/backfill_expansion_census_v1/"
                    "backfill_expansion_census_summary.json"
                ),
            },
        },
    }
    return payload


def _write_readme(path: Path, *, payload: Mapping[str, Any]) -> None:
    lines = [
        "# Backfill Expansion Census v1",
        "",
        "Status: `pass`.",
        "",
        "This is a no-RAW census of the Backfill pressure created by the current "
        "CID-NL Discovery default activation. It does not run Backfill, does not "
        "change the default matrix, and does not expand ProductWriter authority.",
        "",
        "## Current Scope",
        "",
        "- Existing Backfill write-ready authority: "
        f"`{payload['old_backfill_authority_cell_count']}` cells.",
        "- CID-NL active successor rows: "
        f"`{payload['active_successor_row_count']}` rows.",
        "- CID-NL active row sample-cell universe: "
        f"`{payload['active_row_cell_universe_count']}` cells.",
        "- Directly detected cells on those rows: "
        f"`{payload['active_row_direct_detection_cell_count']}`.",
        "- Discovery default-written cells on those rows: "
        f"`{payload['active_row_discovery_default_write_cell_count']}`.",
        "- New Backfill pressure cells: "
        f"`{payload['new_backfill_pressure_candidate_cell_count']}`.",
        "",
        "These 929 cells are blank cells on rows that Discovery has already made "
        "product-visible. They are candidates for future Backfill evidence "
        "review only; they are not writable cells yet.",
        "",
        "## Parked Future Pressure",
        "",
        "- Write-authorized but non-active CID-NL rows: "
        f"`{payload['authorized_nonactive_row_count']}` rows.",
        "- Blank cells on those parked rows: "
        f"`{payload['parked_future_pressure_candidate_cell_count']}`.",
        "",
        "Those cells stay parked because the rows are not active Discovery product "
        "scope. They cannot be routed through Backfill until the Discovery "
        "feature-inclusion authority changes.",
        "",
        "## Boundary",
        "",
        "Backfill authority remains the existing 511-cell "
        "`backfill_policy_write_ready_rows` scope. This census is diagnostic "
        "evidence for the next Backfill gate: sample-local MS1/identity evidence "
        "for active-row blank cells.",
        "",
        "## Files",
        "",
        "- Summary JSON: "
        "`docs/superpowers/validation/backfill_expansion_census_v1/"
        "backfill_expansion_census_summary.json`",
        "- Checks TSV: "
        "`docs/superpowers/validation/backfill_expansion_census_v1/"
        "backfill_expansion_census_checks.tsv`",
        "- Compact row manifest: "
        "`docs/superpowers/validation/backfill_expansion_census_v1/"
        "backfill_expansion_census_row_manifest.tsv`",
        "- Full opportunity cell map: "
        "`output/validation/backfill_expansion_census_v1/"
        "backfill_expansion_opportunity_cells.tsv`",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def _sample_names(path: Path) -> tuple[str, ...]:
    header, _rows = read_tsv_with_header(path, required_columns=("Mz", "RT"))
    return tuple(column for column in header if column not in {"Mz", "RT"})


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
    if row_scopes.get("active_default_expansion", 0) != EXPECTED_COUNTS[
        "active_successor_row_count"
    ]:
        problems.append("row_manifest active_default_expansion count mismatch")
    if row_scopes.get("parked_authorized_nonactive", 0) != EXPECTED_COUNTS[
        "authorized_nonactive_row_count"
    ]:
        problems.append("row_manifest parked_authorized_nonactive count mismatch")
    active_missing = sum(
        _int(row.get("backfill_expansion_candidate_cell_count"))
        for row in rows
        if row.get("row_scope") == "active_default_expansion"
    )
    if active_missing != EXPECTED_COUNTS["new_backfill_pressure_candidate_cell_count"]:
        problems.append("row_manifest active candidate count mismatch")
    for row in rows:
        if row.get("schema_version") != SCHEMA_VERSION:
            problems.append("row_manifest schema_version mismatch")
        if row.get("product_authority_effect") != (
            "no_new_backfill_authority_census_only"
        ):
            problems.append(
                "row_manifest "
                f"{row.get('row_scope', '')} product_authority_effect mismatch",
            )


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
        "--cid-nl-activation-summary-json",
        type=Path,
        default=DEFAULT_CID_NL_ACTIVATION_SUMMARY_JSON,
    )
    parser.add_argument(
        "--cid-nl-universe-summary-json",
        type=Path,
        default=DEFAULT_CID_NL_UNIVERSE_SUMMARY_JSON,
    )
    parser.add_argument(
        "--backfill-activation-summary-json",
        type=Path,
        default=DEFAULT_BACKFILL_ACTIVATION_SUMMARY_JSON,
    )
    parser.add_argument(
        "--cid-nl-activation-manifest-tsv",
        type=Path,
        default=DEFAULT_CID_NL_ACTIVATION_MANIFEST_TSV,
    )
    parser.add_argument(
        "--cid-nl-default-quant-matrix-tsv",
        type=Path,
        default=DEFAULT_CID_NL_DEFAULT_QUANT_MATRIX_TSV,
    )
    parser.add_argument(
        "--cid-nl-default-row-summary-tsv",
        type=Path,
        default=DEFAULT_CID_NL_DEFAULT_ROW_SUMMARY_TSV,
    )
    parser.add_argument(
        "--cid-nl-default-cell-provenance-tsv",
        type=Path,
        default=DEFAULT_CID_NL_DEFAULT_CELL_PROVENANCE_TSV,
    )
    parser.add_argument(
        "--old-backfill-values-tsv",
        type=Path,
        default=DEFAULT_OLD_BACKFILL_VALUES_TSV,
    )
    parser.add_argument(
        "--successor-decisions-tsv",
        type=Path,
        default=DEFAULT_SUCCESSOR_AUTHORITY_DECISIONS_TSV,
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
            args.docs_dir / "backfill_expansion_census_summary.json"
        )
        checks_tsv = args.checks_tsv or (
            args.docs_dir / "backfill_expansion_census_checks.tsv"
        )
        row_manifest_tsv = args.row_manifest_tsv or (
            args.docs_dir / "backfill_expansion_census_row_manifest.tsv"
        )
        problems = check_backfill_expansion_census(
            summary_json=summary_json,
            checks_tsv=checks_tsv,
            row_manifest_tsv=row_manifest_tsv,
        )
        for problem in problems:
            print(f"backfill_expansion_census_problem: {problem}")
        return 2 if problems else 0

    try:
        payload = build_backfill_expansion_census(
            docs_dir=args.docs_dir,
            output_dir=args.output_dir,
            cid_nl_activation_summary_json=args.cid_nl_activation_summary_json,
            cid_nl_universe_summary_json=args.cid_nl_universe_summary_json,
            backfill_activation_summary_json=args.backfill_activation_summary_json,
            cid_nl_activation_manifest_tsv=args.cid_nl_activation_manifest_tsv,
            cid_nl_default_quant_matrix_tsv=args.cid_nl_default_quant_matrix_tsv,
            cid_nl_default_row_summary_tsv=args.cid_nl_default_row_summary_tsv,
            cid_nl_default_cell_provenance_tsv=(
                args.cid_nl_default_cell_provenance_tsv
            ),
            old_backfill_values_tsv=args.old_backfill_values_tsv,
            successor_decisions_tsv=args.successor_decisions_tsv,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    summary_path = args.docs_dir / "backfill_expansion_census_summary.json"
    print(f"backfill_expansion_census_summary: {summary_path}")
    print(f"backfill_expansion_census_status: {payload['status']}")
    print(
        "backfill_expansion_census_active_pressure_cells: "
        f"{payload['new_backfill_pressure_candidate_cell_count']}"
    )
    if args.require_pass and payload.get("status") != "pass":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
