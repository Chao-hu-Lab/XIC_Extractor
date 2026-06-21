"""Build/check Backfill expansion expected-diff provenance packet.

This gate turns the RAW-observed Backfill expansion cells into a bounded
candidate activation packet. It reuses ProductionAcceptanceManifest,
QuantMatrixVersion expected-diff, and the existing dry-run writer, but it does
not change the public default matrix, ProductWriter authority, workbook, GUI, or
active product lane.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.build_quant_matrix_version import run_activation  # noqa: E402
from scripts.check_backfill_expansion_raw_overlay_trace_identity import (  # noqa: E402
    CELL_TRACE_GATE_COLUMNS,
    check_backfill_expansion_raw_overlay_trace_identity,  # noqa: E402
)
from scripts.check_backfill_expansion_raw_overlay_trace_identity import (
    DEFAULT_DOCS_DIR as DEFAULT_RAW_TRACE_DOCS_DIR,
)
from scripts.check_backfill_expansion_raw_overlay_trace_identity import (
    DEFAULT_OUTPUT_DIR as DEFAULT_RAW_TRACE_OUTPUT_DIR,  # noqa: E402
)
from scripts.check_production_acceptance_manifest import (  # noqa: E402
    REQUIRED_COLUMNS as ACCEPTANCE_COLUMNS,
)
from scripts.check_production_acceptance_manifest import (  # noqa: E402
    check_production_acceptance_manifest,
    production_acceptance_manifest_sha256,
)
from tools.diagnostics.cid_nl_activation_copy_candidate import (  # noqa: E402
    DEFAULT_ALIGNMENT_MATRIX_IDENTITY_TSV,
)
from xic_extractor.alignment.quant_matrix_version import (  # noqa: E402
    CELL_PROVENANCE_COLUMNS,
    EXPECTED_DIFF_COLUMNS,
    EXPECTED_DIFF_SUMMARY_COLUMNS,
)
from xic_extractor.tabular_io import (  # noqa: E402
    file_sha256,
    numeric_equal,
    optional_float,
    optional_int,
    read_tsv_required,
    read_tsv_with_header,
    render_delimited_rows,
    text_value,
    write_tsv,
)

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = "backfill_expansion_expected_diff_provenance_v1"
DEFAULT_DOCS_DIR = (
    ROOT
    / "docs/superpowers/validation/"
    "backfill_expansion_expected_diff_provenance_v1"
)
DEFAULT_OUTPUT_DIR = (
    ROOT / "output/validation/backfill_expansion_expected_diff_provenance_v1"
)
DEFAULT_RAW_TRACE_SUMMARY_JSON = (
    DEFAULT_RAW_TRACE_DOCS_DIR
    / "backfill_expansion_raw_overlay_trace_identity_summary.json"
)
DEFAULT_RAW_TRACE_CHECKS_TSV = (
    DEFAULT_RAW_TRACE_DOCS_DIR
    / "backfill_expansion_raw_overlay_trace_identity_checks.tsv"
)
DEFAULT_RAW_TRACE_ROW_MANIFEST_TSV = (
    DEFAULT_RAW_TRACE_DOCS_DIR
    / "backfill_expansion_raw_overlay_trace_identity_row_manifest.tsv"
)
DEFAULT_RAW_TRACE_CELLS_TSV = (
    DEFAULT_RAW_TRACE_OUTPUT_DIR
    / "backfill_expansion_raw_overlay_trace_identity_cells.tsv"
)
DEFAULT_ALIGNMENT_CELL_EVIDENCE_TSV = (
    ROOT
    / "output/discovery/cid_nl_product_ready_alignment_85raw_20260620_fix3/"
    "alignment_backfill_cell_evidence.tsv"
)
DEFAULT_BASELINE_QUANT_MATRIX_TSV = (
    ROOT
    / "output/validation/cid_nl_default_product_activation_v1/default_output/"
    "quant_matrix.tsv"
)

CANDIDATE_TRACE_GATE_STATUS = "raw_trace_observed_expected_diff_candidate"
PRODUCT_AUTHORITY_SCOPE = "backfill_expansion_candidate_activation_packet_666_cells"
PRODUCT_AUTHORITY_EFFECT = "candidate_packet_only_no_active_writer_lane"
EXPECTED_REASON = f"{SCHEMA_VERSION}:raw_trace_observed_sample_local_ms1_identity"
QUANT_VALUE_SOURCE = "alignment_backfill_cell_evidence.primary_matrix_area"
MATRIX_EFFECT = "write_accepted_backfill"
TRUE = "TRUE"
FALSE = "FALSE"

EXPECTED_COUNTS = {
    "candidate_cell_count": 666,
    "candidate_peak_count": 20,
    "baseline_blank_cell_count": 666,
    "manifest_row_count": 666,
    "expected_diff_count": 666,
    "dry_run_written_backfill_count": 666,
    "unused_expected_diff_count": 0,
    "cell_provenance_accepted_count": 666,
    "matrix_changed_cell_count": 666,
    "held_cell_count": 263,
}

ALIGNMENT_CELL_COLUMNS = (
    "schema_version",
    "feature_family_id",
    "public_family_id",
    "sample_stem",
    "status",
    "production_cell_status",
    "rescue_tier",
    "write_matrix_value",
    "include_in_primary_matrix",
    "identity_decision",
    "area",
    "primary_matrix_area",
    "primary_matrix_area_source",
    "apex_rt",
    "height",
    "trace_quality",
    "scan_support_score",
    "neutral_loss_tag",
    "family_center_mz",
    "family_center_rt",
    "reason",
)
SOURCE_EVIDENCE_COLUMNS = (
    "schema_version",
    "peak_hypothesis_id",
    "sample_stem",
    "feature_family_id",
    "baseline_value",
    "candidate_quant_value",
    "candidate_quant_value_source",
    "matrix_area_source",
    "alignment_status",
    "production_cell_status",
    "identity_decision",
    "neutral_loss_tag",
    "alignment_area",
    "primary_matrix_area",
    "apex_rt",
    "height",
    "raw_trace_status",
    "trace_max_intensity",
    "local_window_max_intensity",
    "raw_trace_gate_status",
    "metric_warning_flags",
    "source_row_sha256",
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
    "baseline_available_cell_count",
    "candidate_expected_diff_cell_count",
    "activated_available_cell_count",
    "missing_cell_count",
    "metric_warning_cell_count",
    "product_authority_effect",
    "next_gate",
)
EXPECTED_CHECK_IDS = (
    "raw_trace_identity_gate_pass",
    "candidate_cell_count",
    "candidate_peak_count",
    "baseline_blank_cell_count",
    "primary_matrix_area_value_count",
    "manifest_schema_pass",
    "manifest_row_count",
    "expected_diff_count",
    "dry_run_written_backfill_count",
    "unused_expected_diff_count",
    "cell_provenance_accepted_count",
    "matrix_changed_cell_count",
    "no_public_default_or_productwriter_change",
)


def build_backfill_expansion_expected_diff_provenance(
    *,
    docs_dir: Path = DEFAULT_DOCS_DIR,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    raw_trace_summary_json: Path = DEFAULT_RAW_TRACE_SUMMARY_JSON,
    raw_trace_checks_tsv: Path = DEFAULT_RAW_TRACE_CHECKS_TSV,
    raw_trace_row_manifest_tsv: Path = DEFAULT_RAW_TRACE_ROW_MANIFEST_TSV,
    raw_trace_cells_tsv: Path = DEFAULT_RAW_TRACE_CELLS_TSV,
    alignment_cell_evidence_tsv: Path = DEFAULT_ALIGNMENT_CELL_EVIDENCE_TSV,
    baseline_quant_matrix_tsv: Path = DEFAULT_BASELINE_QUANT_MATRIX_TSV,
    input_matrix_identity_tsv: Path = DEFAULT_ALIGNMENT_MATRIX_IDENTITY_TSV,
) -> dict[str, Any]:
    raw_trace_problems = check_backfill_expansion_raw_overlay_trace_identity(
        summary_json=raw_trace_summary_json,
        checks_tsv=raw_trace_checks_tsv,
        row_manifest_tsv=raw_trace_row_manifest_tsv,
    )
    raw_trace_rows = read_tsv_required(raw_trace_cells_tsv, CELL_TRACE_GATE_COLUMNS)
    alignment_rows = read_tsv_required(
        alignment_cell_evidence_tsv,
        ALIGNMENT_CELL_COLUMNS,
    )
    matrix_header, baseline_rows = read_tsv_with_header(baseline_quant_matrix_tsv)
    identity_rows = read_tsv_required(
        input_matrix_identity_tsv,
        ("matrix_row_index", "peak_hypothesis_id", "source_feature_family_ids"),
    )
    sample_columns = _sample_columns(matrix_header)
    identity_by_peak = _identity_by_peak(identity_rows, len(baseline_rows))
    source_family_by_peak = {
        row["peak_hypothesis_id"]: row.get("source_feature_family_ids", "")
        for row in identity_rows
    }
    facts = _candidate_facts(
        raw_trace_problems=raw_trace_problems,
        raw_trace_rows=raw_trace_rows,
        alignment_rows=alignment_rows,
        baseline_rows=baseline_rows,
        sample_columns=sample_columns,
        identity_by_peak=identity_by_peak,
        source_family_by_peak=source_family_by_peak,
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    docs_dir.mkdir(parents=True, exist_ok=True)
    inputs_dir = output_dir / "inputs"
    dry_run_dir = output_dir / "dry_run_quant_matrix_version"
    inputs_dir.mkdir(parents=True, exist_ok=True)

    source_evidence_tsv = (
        output_dir / "backfill_expansion_expected_diff_provenance_source_evidence.tsv"
    )
    write_tsv(
        source_evidence_tsv,
        facts["source_evidence_rows"],
        SOURCE_EVIDENCE_COLUMNS,
        extrasaction="raise",
        lineterminator="\n",
    )
    source_artifact_relpath = _repo_relpath(source_evidence_tsv)
    source_artifact_sha = file_sha256(source_evidence_tsv)
    manifest_rows = _manifest_rows(
        source_rows=facts["source_evidence_rows"],
        row_context=facts["row_context"],
        source_artifact_relpath=source_artifact_relpath,
        source_artifact_sha=source_artifact_sha,
    )
    manifest_sha = production_acceptance_manifest_sha256(manifest_rows)
    for row in manifest_rows:
        row["manifest_sha256"] = manifest_sha

    production_manifest_tsv = inputs_dir / "production_acceptance_manifest.tsv"
    expected_diff_tsv = inputs_dir / "expected_diff.tsv"
    write_tsv(
        production_manifest_tsv,
        manifest_rows,
        ACCEPTANCE_COLUMNS,
        extrasaction="raise",
        lineterminator="\n",
    )
    write_tsv(
        expected_diff_tsv,
        facts["expected_diff_rows"],
        EXPECTED_DIFF_COLUMNS,
        extrasaction="raise",
        lineterminator="\n",
    )

    manifest_problems = check_production_acceptance_manifest(
        manifest_path=production_manifest_tsv,
        repo_root=ROOT,
    )
    activation_outputs = run_activation(
        input_quant_matrix_tsv=baseline_quant_matrix_tsv,
        input_matrix_identity_tsv=input_matrix_identity_tsv,
        production_acceptance_manifest_tsv=production_manifest_tsv,
        expected_diff_tsv=expected_diff_tsv,
        output_dir=dry_run_dir,
        manifest_root=ROOT,
    )
    dry_run_facts = _dry_run_facts(
        baseline_quant_matrix_tsv=baseline_quant_matrix_tsv,
        activated_quant_matrix_tsv=activation_outputs["quant_matrix"],
        input_matrix_identity_tsv=input_matrix_identity_tsv,
        expected_keys=facts["candidate_keys"],
        expected_values=facts["expected_values"],
        cell_provenance_tsv=activation_outputs["cell_provenance"],
        expected_diff_summary_tsv=activation_outputs["expected_diff_summary"],
    )
    checks = _check_rows(
        facts=facts,
        dry_run_facts=dry_run_facts,
        raw_trace_problem_count=len(raw_trace_problems),
        manifest_problem_count=len(manifest_problems),
    )
    failed = [row["check_id"] for row in checks if row["status"] != "pass"]
    if failed:
        raise ValueError(
            "Backfill expansion expected-diff provenance failed: "
            + ";".join(failed),
        )

    checks_tsv = docs_dir / "backfill_expansion_expected_diff_provenance_checks.tsv"
    row_manifest_tsv = (
        docs_dir / "backfill_expansion_expected_diff_provenance_row_manifest.tsv"
    )
    summary_json = docs_dir / "backfill_expansion_expected_diff_provenance_summary.json"
    write_tsv(checks_tsv, checks, CHECK_COLUMNS, extrasaction="raise")
    write_tsv(
        row_manifest_tsv,
        facts["row_manifest_rows"],
        ROW_MANIFEST_COLUMNS,
        extrasaction="raise",
    )
    payload = _summary_payload(
        docs_dir=docs_dir,
        output_dir=output_dir,
        checks_tsv=checks_tsv,
        row_manifest_tsv=row_manifest_tsv,
        raw_trace_summary_json=raw_trace_summary_json,
        raw_trace_cells_tsv=raw_trace_cells_tsv,
        alignment_cell_evidence_tsv=alignment_cell_evidence_tsv,
        baseline_quant_matrix_tsv=baseline_quant_matrix_tsv,
        input_matrix_identity_tsv=input_matrix_identity_tsv,
        source_evidence_tsv=source_evidence_tsv,
        production_manifest_tsv=production_manifest_tsv,
        expected_diff_tsv=expected_diff_tsv,
        activation_outputs=activation_outputs,
        facts=facts,
        dry_run_facts=dry_run_facts,
        check_rows=checks,
    )
    summary_json.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _write_readme(docs_dir / "README.md", payload=payload)
    return payload


def check_backfill_expansion_expected_diff_provenance(
    *,
    summary_json: Path = DEFAULT_DOCS_DIR
    / "backfill_expansion_expected_diff_provenance_summary.json",
    checks_tsv: Path = DEFAULT_DOCS_DIR
    / "backfill_expansion_expected_diff_provenance_checks.tsv",
    row_manifest_tsv: Path = DEFAULT_DOCS_DIR
    / "backfill_expansion_expected_diff_provenance_row_manifest.tsv",
) -> list[str]:
    problems: list[str] = []
    try:
        payload = _read_json_object(summary_json)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return [str(exc)]
    _check_summary_fields(payload, problems)
    _check_artifact_hashes(payload, problems)
    _check_checks_tsv(checks_tsv, payload, problems)
    _check_row_manifest_tsv(row_manifest_tsv, payload, problems)

    artifacts = payload.get("artifacts")
    if isinstance(artifacts, Mapping):
        manifest = _artifact_path(artifacts, "production_acceptance_manifest")
        expected_diff = _artifact_path(artifacts, "expected_diff")
        expected_summary = _artifact_path(artifacts, "expected_diff_summary")
        cell_provenance = _artifact_path(artifacts, "cell_provenance")
        if manifest is not None:
            problems.extend(
                "production manifest: " + problem
                for problem in check_production_acceptance_manifest(
                    manifest_path=manifest,
                    repo_root=ROOT,
                )
            )
        if expected_diff is not None:
            _check_expected_diff_file(expected_diff, payload, problems)
        if expected_summary is not None:
            _check_expected_diff_summary_file(expected_summary, payload, problems)
        if cell_provenance is not None:
            _check_cell_provenance_file(cell_provenance, payload, problems)
    return problems


def _candidate_facts(
    *,
    raw_trace_problems: Sequence[str],
    raw_trace_rows: Sequence[Mapping[str, str]],
    alignment_rows: Sequence[Mapping[str, str]],
    baseline_rows: Sequence[Mapping[str, str]],
    sample_columns: Sequence[str],
    identity_by_peak: Mapping[str, int],
    source_family_by_peak: Mapping[str, str],
) -> dict[str, Any]:
    candidate_rows = [
        row
        for row in raw_trace_rows
        if row.get("raw_trace_gate_status") == CANDIDATE_TRACE_GATE_STATUS
    ]
    candidate_keys = {
        (row.get("peak_hypothesis_id", ""), row.get("sample_stem", ""))
        for row in candidate_rows
    }
    alignment_by_key = _rows_by_key(
        alignment_rows,
        peak_field="public_family_id",
        sample_field="sample_stem",
        label="alignment cell evidence",
    )
    raw_by_key = _rows_by_key(
        candidate_rows,
        peak_field="peak_hypothesis_id",
        sample_field="sample_stem",
        label="raw trace candidate",
    )
    source_rows: list[dict[str, str]] = []
    expected_diff_rows: list[dict[str, str]] = []
    expected_values: dict[tuple[str, str], str] = {}
    row_candidate_counts = Counter(peak for peak, _sample in candidate_keys)
    metric_warning_counts = Counter(
        row.get("peak_hypothesis_id", "")
        for row in candidate_rows
        if row.get("metric_warning_flags", "")
    )
    baseline_blank_count = 0
    primary_value_count = 0
    for key in sorted(candidate_keys):
        peak, sample = key
        raw_row = raw_by_key[key]
        alignment = alignment_by_key.get(key)
        if alignment is None:
            raise ValueError(f"{peak}/{sample}: missing alignment cell evidence")
        row_index = identity_by_peak.get(peak)
        if row_index is None:
            raise ValueError(f"{peak}/{sample}: peak missing from matrix identity")
        baseline_value = text_value(baseline_rows[row_index - 1].get(sample, ""))
        if baseline_value == "":
            baseline_blank_count += 1
        quant_value = text_value(alignment.get("primary_matrix_area", ""))
        if optional_float(quant_value) is not None:
            primary_value_count += 1
        _require_candidate_alignment_state(peak, sample, alignment)
        source_row = {
            "schema_version": SCHEMA_VERSION,
            "peak_hypothesis_id": peak,
            "sample_stem": sample,
            "feature_family_id": alignment.get("feature_family_id", peak),
            "baseline_value": baseline_value,
            "candidate_quant_value": quant_value,
            "candidate_quant_value_source": QUANT_VALUE_SOURCE,
            "matrix_area_source": alignment.get("primary_matrix_area_source", ""),
            "alignment_status": alignment.get("status", ""),
            "production_cell_status": alignment.get("production_cell_status", ""),
            "identity_decision": alignment.get("identity_decision", ""),
            "neutral_loss_tag": alignment.get("neutral_loss_tag", ""),
            "alignment_area": alignment.get("area", ""),
            "primary_matrix_area": quant_value,
            "apex_rt": alignment.get("apex_rt", ""),
            "height": alignment.get("height", ""),
            "raw_trace_status": raw_row.get("trace_status", ""),
            "trace_max_intensity": raw_row.get("trace_max_intensity", ""),
            "local_window_max_intensity": raw_row.get("local_window_max_intensity", ""),
            "raw_trace_gate_status": raw_row.get("raw_trace_gate_status", ""),
            "metric_warning_flags": raw_row.get("metric_warning_flags", ""),
            "source_row_sha256": "",
        }
        source_row["source_row_sha256"] = _row_sha256(
            source_row,
            SOURCE_EVIDENCE_COLUMNS,
            blank_fields=("source_row_sha256",),
        )
        source_rows.append(source_row)
        expected_values[key] = quant_value
        expected_diff_rows.append(
            {
                "schema_version": "quant_matrix_version_expected_diff_v1",
                "peak_hypothesis_id": peak,
                "sample_stem": sample,
                "baseline_value": baseline_value,
                "activated_value": quant_value,
                "expected_matrix_effect": MATRIX_EFFECT,
                "expected_reason": EXPECTED_REASON,
            }
        )

    row_context = _row_context(
        candidate_keys=candidate_keys,
        baseline_rows=baseline_rows,
        sample_columns=sample_columns,
        identity_by_peak=identity_by_peak,
        source_family_by_peak=source_family_by_peak,
    )
    row_manifest_rows = [
        {
            "schema_version": SCHEMA_VERSION,
            "row_scope": "backfill_expansion_expected_diff_candidate_row",
            "peak_hypothesis_id": peak,
            "baseline_available_cell_count": context["baseline_available_count"],
            "candidate_expected_diff_cell_count": row_candidate_counts[peak],
            "activated_available_cell_count": context["activated_available_count"],
            "missing_cell_count": context["missing_count"],
            "metric_warning_cell_count": metric_warning_counts[peak],
            "product_authority_effect": PRODUCT_AUTHORITY_EFFECT,
            "next_gate": "explicit_public_default_activation_change",
        }
        for peak, context in sorted(row_context.items())
    ]
    return {
        "raw_trace_problem_count": len(raw_trace_problems),
        "candidate_rows": candidate_rows,
        "candidate_keys": candidate_keys,
        "candidate_peak_count": len(row_candidate_counts),
        "baseline_blank_count": baseline_blank_count,
        "primary_matrix_area_value_count": primary_value_count,
        "source_evidence_rows": source_rows,
        "expected_diff_rows": expected_diff_rows,
        "expected_values": expected_values,
        "row_context": row_context,
        "row_manifest_rows": row_manifest_rows,
        "metric_warning_cell_count": sum(metric_warning_counts.values()),
    }


def _manifest_rows(
    *,
    source_rows: Sequence[Mapping[str, str]],
    row_context: Mapping[str, Mapping[str, str]],
    source_artifact_relpath: str,
    source_artifact_sha: str,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for source in source_rows:
        peak = source["peak_hypothesis_id"]
        context = row_context[peak]
        rows.append(
            {
                "schema_version": "production_acceptance_manifest_v1",
                "peak_hypothesis_id": peak,
                "sample_stem": source["sample_stem"],
                "feature_family_id": source["feature_family_id"],
                "acceptance_decision": "accept_basic_backfill",
                "acceptance_basis": "machine_basic",
                "truth_status": "not_truth_claimed",
                "shadow_only": FALSE,
                "write_authority": TRUE,
                "matrix_write_allowed": TRUE,
                "quant_value": source["candidate_quant_value"],
                "quant_value_source": QUANT_VALUE_SOURCE,
                "matrix_area_source": source["matrix_area_source"],
                "detected_count": context["baseline_available_count"],
                "backfilled_count": context["candidate_count"],
                "quant_available_count": context["activated_available_count"],
                "missing_count": context["missing_count"],
                "backfill_fraction": context["backfill_fraction"],
                "prevalence_flags": "",
                "hard_blocker_rule_ids": "",
                "triggered_risk_rule_ids": "",
                "closure_rule_ids": (
                    "backfill_expansion_raw_trace_observed;"
                    "sample_local_ms1_identity;"
                    "expected_diff_provenance_dry_run"
                ),
                "decision_reason": _decision_reason(source),
                "next_evidence_needed": "explicit_public_default_activation_change",
                "doublet_status": "no_doublet_claim",
                "reference_side": "not_applicable",
                "doublet_allowed": TRUE,
                "doublet_source_relpath": source_artifact_relpath,
                "doublet_source_sha256": source_artifact_sha,
                "source_artifact_relpath": source_artifact_relpath,
                "source_artifact_sha256": source_artifact_sha,
                "source_row_sha256": source["source_row_sha256"],
                "manifest_sha256": "",
                "acceptance_contract_version": (
                    "production_acceptance_manifest_contract_v1"
                ),
            }
        )
    return rows


def _dry_run_facts(
    *,
    baseline_quant_matrix_tsv: Path,
    activated_quant_matrix_tsv: Path,
    input_matrix_identity_tsv: Path,
    expected_keys: set[tuple[str, str]],
    expected_values: Mapping[tuple[str, str], str],
    cell_provenance_tsv: Path,
    expected_diff_summary_tsv: Path,
) -> dict[str, Any]:
    expected_diff_summary = read_tsv_required(
        expected_diff_summary_tsv,
        EXPECTED_DIFF_SUMMARY_COLUMNS,
    )
    if len(expected_diff_summary) != 1:
        raise ValueError("expected_diff_summary must have exactly one row")
    matrix_changed = _matrix_changed_keys(
        baseline_quant_matrix_tsv=baseline_quant_matrix_tsv,
        activated_quant_matrix_tsv=activated_quant_matrix_tsv,
        input_matrix_identity_tsv=input_matrix_identity_tsv,
        expected_values=expected_values,
    )
    provenance_rows = read_tsv_required(cell_provenance_tsv, CELL_PROVENANCE_COLUMNS)
    accepted_rows = [
        row for row in provenance_rows if row.get("cell_status") == "accepted_backfill"
    ]
    accepted_keys = {
        (row.get("peak_hypothesis_id", ""), row.get("sample_stem", ""))
        for row in accepted_rows
    }
    value_mismatch_count = sum(
        1
        for row in accepted_rows
        if not numeric_equal(
            row.get("matrix_value", ""),
            expected_values.get(
                (row.get("peak_hypothesis_id", ""), row.get("sample_stem", "")),
                "",
            ),
        )
    )
    source_count = Counter(row.get("value_source", "") for row in accepted_rows)
    summary_row = expected_diff_summary[0]
    return {
        "expected_diff_summary": summary_row,
        "written_backfill_count": optional_int(summary_row["written_backfill_count"]),
        "unused_expected_diff_count": optional_int(
            summary_row["unused_expected_diff_count"],
        ),
        "matrix_changed_keys": matrix_changed,
        "matrix_changed_cell_count": len(matrix_changed),
        "matrix_changed_keyset_matches": set(matrix_changed) == expected_keys,
        "cell_provenance_accepted_count": len(accepted_rows),
        "cell_provenance_keyset_matches": accepted_keys == expected_keys,
        "cell_provenance_value_mismatch_count": value_mismatch_count,
        "cell_provenance_value_sources": dict(source_count),
    }


def _check_rows(
    *,
    facts: Mapping[str, Any],
    dry_run_facts: Mapping[str, Any],
    raw_trace_problem_count: int,
    manifest_problem_count: int,
) -> list[dict[str, str]]:
    candidate_count = len(facts["candidate_keys"])
    checks = [
        _count_check("raw_trace_identity_gate_pass", raw_trace_problem_count, 0),
        _count_check(
            "candidate_cell_count",
            candidate_count,
            EXPECTED_COUNTS["candidate_cell_count"],
        ),
        _count_check(
            "candidate_peak_count",
            facts["candidate_peak_count"],
            EXPECTED_COUNTS["candidate_peak_count"],
        ),
        _count_check(
            "baseline_blank_cell_count",
            facts["baseline_blank_count"],
            EXPECTED_COUNTS["baseline_blank_cell_count"],
        ),
        _count_check(
            "primary_matrix_area_value_count",
            facts["primary_matrix_area_value_count"],
            EXPECTED_COUNTS["candidate_cell_count"],
        ),
        _count_check("manifest_schema_pass", manifest_problem_count, 0),
        _count_check(
            "manifest_row_count",
            candidate_count,
            EXPECTED_COUNTS["manifest_row_count"],
        ),
        _count_check(
            "expected_diff_count",
            len(facts["expected_diff_rows"]),
            EXPECTED_COUNTS["expected_diff_count"],
        ),
        _count_check(
            "dry_run_written_backfill_count",
            dry_run_facts["written_backfill_count"],
            EXPECTED_COUNTS["dry_run_written_backfill_count"],
        ),
        _count_check(
            "unused_expected_diff_count",
            dry_run_facts["unused_expected_diff_count"],
            EXPECTED_COUNTS["unused_expected_diff_count"],
        ),
        _count_check(
            "cell_provenance_accepted_count",
            dry_run_facts["cell_provenance_accepted_count"],
            EXPECTED_COUNTS["cell_provenance_accepted_count"],
        ),
        _count_check(
            "matrix_changed_cell_count",
            dry_run_facts["matrix_changed_cell_count"],
            EXPECTED_COUNTS["matrix_changed_cell_count"],
            notes=(
                ""
                if dry_run_facts["matrix_changed_keyset_matches"]
                else "changed keyset mismatch"
            ),
        ),
        {
            "schema_version": SCHEMA_VERSION,
            "check_id": "no_public_default_or_productwriter_change",
            "status": "pass",
            "observed": "candidate packet only",
            "expected": "candidate packet only",
            "notes": "dry-run output is externalized under output/validation",
        },
    ]
    for check in checks:
        if check["check_id"] == "matrix_changed_cell_count" and check["notes"]:
            check["status"] = "fail"
    if not dry_run_facts["cell_provenance_keyset_matches"]:
        checks.append(
            _fail_check(
                "cell_provenance_keyset",
                "mismatch",
                "exact candidate keyset",
            ),
        )
    if dry_run_facts["cell_provenance_value_mismatch_count"]:
        checks.append(
            _fail_check(
                "cell_provenance_values",
                dry_run_facts["cell_provenance_value_mismatch_count"],
                "0",
            ),
        )
    if dry_run_facts["cell_provenance_value_sources"] != {
        "ProductionAcceptanceManifest": EXPECTED_COUNTS["candidate_cell_count"],
    }:
        checks.append(
            _fail_check(
                "cell_provenance_value_source",
                dry_run_facts["cell_provenance_value_sources"],
                "ProductionAcceptanceManifest only",
            ),
        )
    return checks


def _summary_payload(
    *,
    docs_dir: Path,
    output_dir: Path,
    checks_tsv: Path,
    row_manifest_tsv: Path,
    raw_trace_summary_json: Path,
    raw_trace_cells_tsv: Path,
    alignment_cell_evidence_tsv: Path,
    baseline_quant_matrix_tsv: Path,
    input_matrix_identity_tsv: Path,
    source_evidence_tsv: Path,
    production_manifest_tsv: Path,
    expected_diff_tsv: Path,
    activation_outputs: Mapping[str, Path],
    facts: Mapping[str, Any],
    dry_run_facts: Mapping[str, Any],
    check_rows: Sequence[Mapping[str, str]],
) -> dict[str, Any]:
    artifacts = {
        "checks_tsv": checks_tsv,
        "row_manifest_tsv": row_manifest_tsv,
        "source_evidence": source_evidence_tsv,
        "production_acceptance_manifest": production_manifest_tsv,
        "expected_diff": expected_diff_tsv,
        "dry_run_quant_matrix": activation_outputs["quant_matrix"],
        "cell_provenance": activation_outputs["cell_provenance"],
        "row_summary": activation_outputs["row_summary"],
        "expected_diff_summary": activation_outputs["expected_diff_summary"],
        "source_summary": activation_outputs["source_summary"],
    }
    input_artifacts = {
        "raw_trace_summary_json": raw_trace_summary_json,
        "raw_trace_cells_tsv": raw_trace_cells_tsv,
        "alignment_cell_evidence_tsv": alignment_cell_evidence_tsv,
        "baseline_quant_matrix_tsv": baseline_quant_matrix_tsv,
        "input_matrix_identity_tsv": input_matrix_identity_tsv,
    }
    checks_pass = all(row.get("status") == "pass" for row in check_rows)
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "pass" if checks_pass else "fail",
        "validation_status": "production_candidate_contract_only",
        "product_authority_scope": PRODUCT_AUTHORITY_SCOPE,
        "product_authority_effect": PRODUCT_AUTHORITY_EFFECT,
        "candidate_cell_count": len(facts["candidate_keys"]),
        "candidate_peak_count": facts["candidate_peak_count"],
        "baseline_blank_cell_count": facts["baseline_blank_count"],
        "primary_matrix_area_value_count": facts["primary_matrix_area_value_count"],
        "manifest_row_count": len(facts["candidate_keys"]),
        "expected_diff_count": len(facts["expected_diff_rows"]),
        "dry_run_written_backfill_count": dry_run_facts["written_backfill_count"],
        "unused_expected_diff_count": dry_run_facts["unused_expected_diff_count"],
        "cell_provenance_accepted_count": dry_run_facts[
            "cell_provenance_accepted_count"
        ],
        "matrix_changed_cell_count": dry_run_facts["matrix_changed_cell_count"],
        "held_cell_count": EXPECTED_COUNTS["held_cell_count"],
        "metric_warning_cell_count": facts["metric_warning_cell_count"],
        "product_writer_changed": False,
        "default_quant_matrix_changed": False,
        "default_matrix_files_written": False,
        "validation_dry_run_matrix_written": True,
        "workbook_or_gui_changed": False,
        "selected_peak_area_or_counting_changed": False,
        "broad_backfill_unparked": False,
        "cid_nl_ms2_direct_productwriter_authority": False,
        "candidate_rows_are_matrix_rows": False,
        "next_gate": "explicit_public_default_activation_change",
        "checks": {row["check_id"]: row["status"] for row in check_rows},
        "artifacts": {
            label: _artifact_entry(path, base_dir=ROOT)
            for label, path in artifacts.items()
        },
        "input_artifacts": {
            label: _artifact_entry(path, base_dir=ROOT)
            for label, path in input_artifacts.items()
        },
        "docs_dir": _repo_relpath(docs_dir),
        "output_dir": _repo_relpath(output_dir),
    }


def _write_readme(path: Path, *, payload: Mapping[str, Any]) -> None:
    lines = [
        "# Backfill Expansion Expected-Diff Provenance v1",
        "",
        "This gate converts the RAW-observed Backfill expansion cells into a",
        "candidate activation packet. It uses the existing",
        "ProductionAcceptanceManifest and QuantMatrixVersion expected-diff",
        "contracts, then runs a validation-only dry-run matrix writer under",
        "`output/validation/`.",
        "",
        "It does not change ProductWriter authority, the public default matrix,",
        "workbooks, GUI behavior, selected peak/area/counting, or the active",
        "product lane.",
        "",
        f"- Candidate cells: `{payload['candidate_cell_count']}`.",
        f"- Candidate rows: `{payload['candidate_peak_count']}`.",
        f"- Dry-run written cells: `{payload['dry_run_written_backfill_count']}`.",
        f"- Unused expected-diff rows: `{payload['unused_expected_diff_count']}`.",
        f"- Held cells kept out: `{payload['held_cell_count']}`.",
        f"- Next gate: `{payload['next_gate']}`.",
        "",
        "Full source evidence, manifest, expected-diff, dry-run matrix, and full",
        "cell provenance stay externalized under `output/validation/`.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def _check_summary_fields(payload: Mapping[str, Any], problems: list[str]) -> None:
    expected_fields: tuple[tuple[str, object], ...] = (
        ("schema_version", SCHEMA_VERSION),
        ("status", "pass"),
        ("validation_status", "production_candidate_contract_only"),
        ("product_authority_effect", PRODUCT_AUTHORITY_EFFECT),
        ("candidate_cell_count", EXPECTED_COUNTS["candidate_cell_count"]),
        ("candidate_peak_count", EXPECTED_COUNTS["candidate_peak_count"]),
        ("baseline_blank_cell_count", EXPECTED_COUNTS["baseline_blank_cell_count"]),
        ("manifest_row_count", EXPECTED_COUNTS["manifest_row_count"]),
        ("expected_diff_count", EXPECTED_COUNTS["expected_diff_count"]),
        (
            "dry_run_written_backfill_count",
            EXPECTED_COUNTS["dry_run_written_backfill_count"],
        ),
        ("unused_expected_diff_count", EXPECTED_COUNTS["unused_expected_diff_count"]),
        (
            "cell_provenance_accepted_count",
            EXPECTED_COUNTS["cell_provenance_accepted_count"],
        ),
        ("matrix_changed_cell_count", EXPECTED_COUNTS["matrix_changed_cell_count"]),
        ("held_cell_count", EXPECTED_COUNTS["held_cell_count"]),
        ("product_writer_changed", False),
        ("default_quant_matrix_changed", False),
        ("default_matrix_files_written", False),
        ("validation_dry_run_matrix_written", True),
        ("workbook_or_gui_changed", False),
        ("selected_peak_area_or_counting_changed", False),
        ("broad_backfill_unparked", False),
        ("cid_nl_ms2_direct_productwriter_authority", False),
        ("candidate_rows_are_matrix_rows", False),
        ("next_gate", "explicit_public_default_activation_change"),
    )
    for field, expected in expected_fields:
        if payload.get(field) != expected:
            problems.append(f"summary {field} mismatch")


def _check_artifact_hashes(payload: Mapping[str, Any], problems: list[str]) -> None:
    for group_name in ("artifacts", "input_artifacts"):
        group = payload.get(group_name)
        if not isinstance(group, Mapping):
            problems.append(f"summary {group_name} must be an object")
            continue
        for label, entry in group.items():
            if not isinstance(entry, Mapping):
                problems.append(f"summary {group_name} {label} must be an object")
                continue
            relpath = entry.get("path")
            expected_sha = entry.get("sha256")
            if not isinstance(relpath, str) or not isinstance(expected_sha, str):
                problems.append(f"summary {group_name} {label} artifact malformed")
                continue
            path = ROOT / relpath
            if not path.exists():
                problems.append(f"summary {group_name} {label} missing: {relpath}")
                continue
            if file_sha256(path) != expected_sha:
                problems.append(f"summary {group_name} {label} sha256 mismatch")


def _check_checks_tsv(
    checks_tsv: Path,
    payload: Mapping[str, Any],
    problems: list[str],
) -> None:
    try:
        rows = read_tsv_required(checks_tsv, CHECK_COLUMNS)
    except (OSError, ValueError) as exc:
        problems.append(f"could not read checks TSV: {exc}")
        return
    ids = {row["check_id"] for row in rows}
    missing = sorted(set(EXPECTED_CHECK_IDS) - ids)
    if missing:
        problems.append("checks missing required ids: " + ";".join(missing))
    failing = [row["check_id"] for row in rows if row.get("status") != "pass"]
    if failing:
        problems.append("checks must all pass: " + ";".join(failing))
    checks = payload.get("checks")
    if isinstance(checks, Mapping):
        for check_id in EXPECTED_CHECK_IDS:
            if checks.get(check_id) != "pass":
                problems.append(f"summary check {check_id} must pass")


def _check_row_manifest_tsv(
    row_manifest_tsv: Path,
    payload: Mapping[str, Any],
    problems: list[str],
) -> None:
    try:
        rows = read_tsv_required(row_manifest_tsv, ROW_MANIFEST_COLUMNS)
    except (OSError, ValueError) as exc:
        problems.append(f"could not read row manifest TSV: {exc}")
        return
    if len(rows) != EXPECTED_COUNTS["candidate_peak_count"]:
        problems.append("row manifest candidate peak count mismatch")
    candidate_sum = sum(
        optional_int(row.get("candidate_expected_diff_cell_count", "")) or 0
        for row in rows
    )
    if candidate_sum != EXPECTED_COUNTS["candidate_cell_count"]:
        problems.append("row manifest candidate cell sum mismatch")
    for row in rows:
        if row.get("product_authority_effect") != PRODUCT_AUTHORITY_EFFECT:
            problems.append("row manifest product_authority_effect mismatch")
        if row.get("next_gate") != payload.get("next_gate"):
            problems.append("row manifest next_gate mismatch")


def _check_expected_diff_file(
    expected_diff: Path,
    payload: Mapping[str, Any],
    problems: list[str],
) -> None:
    try:
        rows = read_tsv_required(expected_diff, EXPECTED_DIFF_COLUMNS)
    except (OSError, ValueError) as exc:
        problems.append(f"could not read expected_diff: {exc}")
        return
    if len(rows) != payload.get("expected_diff_count"):
        problems.append("expected_diff row count mismatch")
    bad_effect = [
        row for row in rows if row.get("expected_matrix_effect") != MATRIX_EFFECT
    ]
    if bad_effect:
        problems.append("expected_diff contains non-backfill effect")
    nonblank_baseline = [row for row in rows if row.get("baseline_value")]
    if nonblank_baseline:
        problems.append("expected_diff contains nonblank baseline values")


def _check_expected_diff_summary_file(
    expected_summary: Path,
    payload: Mapping[str, Any],
    problems: list[str],
) -> None:
    try:
        rows = read_tsv_required(expected_summary, EXPECTED_DIFF_SUMMARY_COLUMNS)
    except (OSError, ValueError) as exc:
        problems.append(f"could not read expected_diff_summary: {exc}")
        return
    if len(rows) != 1:
        problems.append("expected_diff_summary must have one row")
        return
    row = rows[0]
    if optional_int(row.get("written_backfill_count", "")) != payload.get(
        "dry_run_written_backfill_count",
    ):
        problems.append("expected_diff_summary written count mismatch")
    if optional_int(row.get("unused_expected_diff_count", "")) != 0:
        problems.append("expected_diff_summary unused expected diff mismatch")


def _check_cell_provenance_file(
    cell_provenance: Path,
    payload: Mapping[str, Any],
    problems: list[str],
) -> None:
    try:
        rows = read_tsv_required(cell_provenance, CELL_PROVENANCE_COLUMNS)
    except (OSError, ValueError) as exc:
        problems.append(f"could not read cell_provenance: {exc}")
        return
    accepted = [row for row in rows if row.get("cell_status") == "accepted_backfill"]
    if len(accepted) != payload.get("cell_provenance_accepted_count"):
        problems.append("cell_provenance accepted count mismatch")
    bad_source = [
        row
        for row in accepted
        if row.get("value_source") != "ProductionAcceptanceManifest"
    ]
    if bad_source:
        problems.append("cell_provenance accepted value_source mismatch")


def _count_check(
    check_id: str,
    observed: object,
    expected: object,
    *,
    notes: str = "",
) -> dict[str, str]:
    return {
        "schema_version": SCHEMA_VERSION,
        "check_id": check_id,
        "status": "pass" if observed == expected else "fail",
        "observed": text_value(observed),
        "expected": text_value(expected),
        "notes": notes,
    }


def _fail_check(check_id: str, observed: object, expected: object) -> dict[str, str]:
    return {
        "schema_version": SCHEMA_VERSION,
        "check_id": check_id,
        "status": "fail",
        "observed": text_value(observed),
        "expected": text_value(expected),
        "notes": "",
    }


def _require_candidate_alignment_state(
    peak: str,
    sample: str,
    alignment: Mapping[str, str],
) -> None:
    checks = {
        "production_cell_status": "review_rescue",
        "write_matrix_value": FALSE,
        "include_in_primary_matrix": TRUE,
        "identity_decision": "production_family",
        "neutral_loss_tag": "DNA_dR",
    }
    for field, expected in checks.items():
        if alignment.get(field) != expected:
            raise ValueError(
                f"{peak}/{sample}: alignment {field} must be {expected}",
            )
    value = optional_float(alignment.get("primary_matrix_area", ""))
    if value is None or value <= 0:
        raise ValueError(f"{peak}/{sample}: primary_matrix_area must be positive")
    if not alignment.get("primary_matrix_area_source"):
        raise ValueError(f"{peak}/{sample}: primary_matrix_area_source is required")
    if alignment.get("primary_matrix_area_source") == "alignment_cells_area_only":
        raise ValueError(f"{peak}/{sample}: naked alignment area cannot write")


def _row_context(
    *,
    candidate_keys: set[tuple[str, str]],
    baseline_rows: Sequence[Mapping[str, str]],
    sample_columns: Sequence[str],
    identity_by_peak: Mapping[str, int],
    source_family_by_peak: Mapping[str, str],
) -> dict[str, dict[str, str]]:
    by_peak = Counter(peak for peak, _sample in candidate_keys)
    context: dict[str, dict[str, str]] = {}
    for peak, candidate_count in sorted(by_peak.items()):
        row_index = identity_by_peak[peak]
        baseline_available = sum(
            1 for sample in sample_columns if baseline_rows[row_index - 1].get(sample)
        )
        activated_available = baseline_available + candidate_count
        missing = len(sample_columns) - activated_available
        backfill_fraction = (
            0.0 if activated_available == 0 else candidate_count / activated_available
        )
        context[peak] = {
            "source_feature_family_ids": source_family_by_peak.get(peak, peak),
            "baseline_available_count": str(baseline_available),
            "candidate_count": str(candidate_count),
            "activated_available_count": str(activated_available),
            "missing_count": str(missing),
            "backfill_fraction": f"{backfill_fraction:.6f}",
        }
    return context


def _matrix_changed_keys(
    *,
    baseline_quant_matrix_tsv: Path,
    activated_quant_matrix_tsv: Path,
    input_matrix_identity_tsv: Path,
    expected_values: Mapping[tuple[str, str], str],
) -> set[tuple[str, str]]:
    baseline_header, baseline_rows = read_tsv_with_header(baseline_quant_matrix_tsv)
    activated_header, activated_rows = read_tsv_with_header(activated_quant_matrix_tsv)
    if tuple(baseline_header) != tuple(activated_header):
        raise ValueError("baseline and activated matrix headers differ")
    if len(baseline_rows) != len(activated_rows):
        raise ValueError("baseline and activated matrix row counts differ")
    identity_rows = read_tsv_required(
        input_matrix_identity_tsv,
        ("matrix_row_index", "peak_hypothesis_id"),
    )
    peak_by_index = {
        int(row["matrix_row_index"]): row["peak_hypothesis_id"] for row in identity_rows
    }
    sample_columns = _sample_columns(baseline_header)
    changed: set[tuple[str, str]] = set()
    for index, (baseline, activated) in enumerate(
        zip(baseline_rows, activated_rows, strict=True),
        start=1,
    ):
        peak = peak_by_index[index]
        for sample in sample_columns:
            before = baseline.get(sample, "")
            after = activated.get(sample, "")
            if numeric_equal(before, after):
                continue
            key = (peak, sample)
            changed.add(key)
            expected = expected_values.get(key, "")
            if not expected or not numeric_equal(after, expected):
                raise ValueError(f"{peak}/{sample}: activated value mismatch")
    return changed


def _rows_by_key(
    rows: Sequence[Mapping[str, str]],
    *,
    peak_field: str,
    sample_field: str,
    label: str,
) -> dict[tuple[str, str], Mapping[str, str]]:
    result: dict[tuple[str, str], Mapping[str, str]] = {}
    for row in rows:
        key = (row.get(peak_field, ""), row.get(sample_field, ""))
        if not key[0] or not key[1]:
            raise ValueError(f"{label}: missing key")
        if key in result:
            raise ValueError(f"{label}: duplicate key {key[0]}/{key[1]}")
        result[key] = row
    return result


def _sample_columns(header: Sequence[str]) -> tuple[str, ...]:
    if len(header) < 3 or tuple(header[:2]) != ("Mz", "RT"):
        raise ValueError("quant matrix header must start with Mz, RT")
    return tuple(column for column in header if column not in {"Mz", "RT"})


def _identity_by_peak(
    rows: Sequence[Mapping[str, str]],
    matrix_row_count: int,
) -> dict[str, int]:
    result: dict[str, int] = {}
    for row in rows:
        peak = row.get("peak_hypothesis_id", "")
        try:
            row_index = int(row.get("matrix_row_index", ""))
        except ValueError as exc:
            raise ValueError("invalid matrix_row_index") from exc
        if not peak:
            raise ValueError("matrix identity row missing peak_hypothesis_id")
        if row_index < 1 or row_index > matrix_row_count:
            raise ValueError("matrix identity row index out of range")
        previous = result.setdefault(peak, row_index)
        if previous != row_index:
            raise ValueError(f"duplicate peak_hypothesis_id: {peak}")
    return result


def _decision_reason(source: Mapping[str, str]) -> str:
    reason = (
        f"{EXPECTED_REASON};matrix_area_source={source['matrix_area_source']};"
        f"raw_trace_status={source['raw_trace_status']}"
    )
    if source.get("metric_warning_flags"):
        reason += f";metric_warnings={source['metric_warning_flags']}"
    return reason


def _row_sha256(
    row: Mapping[str, str],
    columns: Sequence[str],
    *,
    blank_fields: Sequence[str] = (),
) -> str:
    canonical = {column: row.get(column, "") for column in columns}
    for field in blank_fields:
        canonical[field] = ""
    rendered = render_delimited_rows(
        [canonical],
        columns,
        delimiter="\t",
        extrasaction="raise",
        lineterminator="\n",
    )
    return hashlib.sha256(rendered.encode("utf-8")).hexdigest().upper()


def _artifact_entry(path: Path, *, base_dir: Path) -> dict[str, Any]:
    resolved = path.resolve()
    return {
        "path": resolved.relative_to(base_dir.resolve()).as_posix(),
        "sha256": file_sha256(resolved),
        "bytes": resolved.stat().st_size,
        "line_count": _line_count(resolved),
    }


def _artifact_path(
    artifacts: Mapping[str, Any],
    label: str,
) -> Path | None:
    entry = artifacts.get(label)
    if not isinstance(entry, Mapping) or not isinstance(entry.get("path"), str):
        return None
    return ROOT / entry["path"]


def _repo_relpath(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def _line_count(path: Path) -> int:
    with path.open("rb") as handle:
        return sum(1 for _line in handle)


def _read_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: JSON payload must be an object")
    return payload


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--require-pass", action="store_true")
    parser.add_argument("--docs-dir", type=Path, default=DEFAULT_DOCS_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--raw-trace-summary-json",
        type=Path,
        default=DEFAULT_RAW_TRACE_SUMMARY_JSON,
    )
    parser.add_argument(
        "--raw-trace-checks-tsv",
        type=Path,
        default=DEFAULT_RAW_TRACE_CHECKS_TSV,
    )
    parser.add_argument(
        "--raw-trace-row-manifest-tsv",
        type=Path,
        default=DEFAULT_RAW_TRACE_ROW_MANIFEST_TSV,
    )
    parser.add_argument(
        "--raw-trace-cells-tsv",
        type=Path,
        default=DEFAULT_RAW_TRACE_CELLS_TSV,
    )
    parser.add_argument(
        "--alignment-cell-evidence-tsv",
        type=Path,
        default=DEFAULT_ALIGNMENT_CELL_EVIDENCE_TSV,
    )
    parser.add_argument(
        "--baseline-quant-matrix-tsv",
        type=Path,
        default=DEFAULT_BASELINE_QUANT_MATRIX_TSV,
    )
    parser.add_argument(
        "--input-matrix-identity-tsv",
        type=Path,
        default=DEFAULT_ALIGNMENT_MATRIX_IDENTITY_TSV,
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    summary_json = (
        args.docs_dir / "backfill_expansion_expected_diff_provenance_summary.json"
    )
    checks_tsv = (
        args.docs_dir / "backfill_expansion_expected_diff_provenance_checks.tsv"
    )
    row_manifest_tsv = (
        args.docs_dir
        / "backfill_expansion_expected_diff_provenance_row_manifest.tsv"
    )
    try:
        if args.check_only:
            problems = check_backfill_expansion_expected_diff_provenance(
                summary_json=summary_json,
                checks_tsv=checks_tsv,
                row_manifest_tsv=row_manifest_tsv,
            )
        else:
            build_backfill_expansion_expected_diff_provenance(
                docs_dir=args.docs_dir,
                output_dir=args.output_dir,
                raw_trace_summary_json=args.raw_trace_summary_json,
                raw_trace_checks_tsv=args.raw_trace_checks_tsv,
                raw_trace_row_manifest_tsv=args.raw_trace_row_manifest_tsv,
                raw_trace_cells_tsv=args.raw_trace_cells_tsv,
                alignment_cell_evidence_tsv=args.alignment_cell_evidence_tsv,
                baseline_quant_matrix_tsv=args.baseline_quant_matrix_tsv,
                input_matrix_identity_tsv=args.input_matrix_identity_tsv,
            )
            problems = check_backfill_expansion_expected_diff_provenance(
                summary_json=summary_json,
                checks_tsv=checks_tsv,
                row_manifest_tsv=row_manifest_tsv,
            )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if problems:
        for problem in problems:
            print(problem, file=sys.stderr)
        return 2 if args.require_pass else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
