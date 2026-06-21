"""Build/check RAW overlay trace identity for Backfill expansion cells.

This RAW-backed gate consumes the sample-local MS1/identity evidence map and
the evidence-only family MS1 overlay batch. It promotes only exact sample-local
cells with observed RAW trace signal into an expected-diff design candidate
bucket. It does not write Backfill values, mutate the default matrix, or grant
ProductWriter authority.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.check_backfill_expansion_sample_local_ms1_evidence import (  # noqa: E402
    CELL_EVIDENCE_COLUMNS as SAMPLE_LOCAL_CELL_EVIDENCE_COLUMNS,
)
from scripts.check_backfill_expansion_sample_local_ms1_evidence import (  # noqa: E402
    DEFAULT_DOCS_DIR as DEFAULT_SAMPLE_LOCAL_DOCS_DIR,
)
from scripts.check_backfill_expansion_sample_local_ms1_evidence import (  # noqa: E402
    DEFAULT_OUTPUT_DIR as DEFAULT_SAMPLE_LOCAL_OUTPUT_DIR,
)
from scripts.check_backfill_expansion_sample_local_ms1_evidence import (  # noqa: E402
    check_backfill_expansion_sample_local_ms1_evidence,
)
from xic_extractor.tabular_io import (  # noqa: E402
    file_sha256,
    optional_float,
    read_tsv_required,
    text_value,
    write_tsv,
)

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = "backfill_expansion_raw_overlay_trace_identity_v1"
DEFAULT_DOCS_DIR = (
    ROOT
    / "docs/superpowers/validation/"
    "backfill_expansion_raw_overlay_trace_identity_v1"
)
DEFAULT_OUTPUT_DIR = (
    ROOT / "output/validation/backfill_expansion_raw_overlay_trace_identity_v1"
)
DEFAULT_SAMPLE_LOCAL_SUMMARY_JSON = (
    DEFAULT_SAMPLE_LOCAL_DOCS_DIR
    / "backfill_expansion_sample_local_ms1_evidence_summary.json"
)
DEFAULT_SAMPLE_LOCAL_CHECKS_TSV = (
    DEFAULT_SAMPLE_LOCAL_DOCS_DIR
    / "backfill_expansion_sample_local_ms1_evidence_checks.tsv"
)
DEFAULT_SAMPLE_LOCAL_ROW_MANIFEST_TSV = (
    DEFAULT_SAMPLE_LOCAL_DOCS_DIR
    / "backfill_expansion_sample_local_ms1_evidence_row_manifest.tsv"
)
DEFAULT_SAMPLE_LOCAL_CELLS_TSV = (
    DEFAULT_SAMPLE_LOCAL_OUTPUT_DIR
    / "backfill_expansion_sample_local_ms1_evidence_cells.tsv"
)
DEFAULT_OVERLAY_BATCH_DIR = (
    DEFAULT_OUTPUT_DIR / "family_ms1_overlay_batch"
)
DEFAULT_OVERLAY_BATCH_SUMMARY_TSV = (
    DEFAULT_OVERLAY_BATCH_DIR / "family_ms1_overlay_batch_summary.tsv"
)
DEFAULT_OVERLAY_BATCH_SUMMARY_JSON = (
    DEFAULT_OVERLAY_BATCH_DIR / "family_ms1_overlay_batch_summary.json"
)

SUPPORT_FAMILY_VERDICT = "ms1_shape_supports_family_backfill"
TRACE_OBSERVED_STATUSES = {"detected", "rescued"}
LOW_LOCAL_GLOBAL_RATIO_THRESHOLD = 0.5
HIGH_LOCAL_APEX_DELTA_MIN_THRESHOLD = 0.15
LOW_APEX_SHAPE_SIMILARITY_THRESHOLD = 0.5

OVERLAY_BATCH_SUMMARY_COLUMNS = (
    "rank",
    "feature_family_id",
    "seed_group_id",
    "mz",
    "ppm",
    "rt_min",
    "rt_max",
    "family_center_rt",
    "output_prefix",
    "status",
    "family_verdict",
    "detected_count",
    "rescued_count",
    "detected_rescued_count",
    "trace_summary_tsv",
    "trace_data_json",
    "failure_reason",
    "top30_expansion_gate",
)
TRACE_SUMMARY_COLUMNS = (
    "sample_stem",
    "status",
    "cell_area",
    "cell_height",
    "cell_apex_rt",
    "cell_start_rt",
    "cell_end_rt",
    "trace_max_intensity",
    "trace_apex_rt",
    "global_trace_apex_delta_min",
    "local_window_max_intensity",
    "local_window_apex_delta_min",
    "local_window_to_global_max_ratio",
    "region_shadow_verdict",
    "source_candidate_id",
    "highlight_group",
    "apex_aligned_shape_similarity",
    "absolute_own_max_shape_similarity",
)
CHECK_COLUMNS = (
    "schema_version",
    "check_id",
    "status",
    "observed",
    "expected",
    "notes",
)
CELL_TRACE_GATE_COLUMNS = (
    "schema_version",
    "opportunity_scope",
    "peak_hypothesis_id",
    "sample_stem",
    "alignment_cell_evidence_status",
    "raw_overlay_family_status",
    "family_verdict",
    "raw_trace_row_status",
    "trace_status",
    "trace_max_intensity",
    "local_window_max_intensity",
    "local_window_to_global_max_ratio",
    "local_window_apex_delta_min",
    "apex_aligned_shape_similarity",
    "absolute_own_max_shape_similarity",
    "raw_trace_gate_status",
    "metric_warning_flags",
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
    "raw_trace_row_present_cell_count",
    "raw_trace_observed_cell_count",
    "raw_trace_absent_cell_count",
    "metric_warning_cell_count",
    "expected_diff_design_candidate_cell_count",
    "held_cell_count",
    "family_verdict",
    "product_authority_effect",
    "next_gate",
)
EXPECTED_COUNTS = {
    "active_pressure_cell_count": 929,
    "alignment_cell_evidence_present_cell_count": 675,
    "alignment_cell_evidence_missing_cell_count": 254,
    "overlay_batch_success_row_count": 20,
    "overlay_batch_support_row_count": 20,
    "raw_trace_row_present_cell_count": 675,
    "raw_trace_observed_cell_count": 666,
    "raw_trace_absent_cell_count": 9,
    "metric_warning_cell_count": 43,
    "expected_diff_design_candidate_cell_count": 666,
    "held_cell_count": 263,
}
EXPECTED_CHECK_IDS = (
    "sample_local_ms1_evidence_checker_pass",
    "active_pressure_cell_count",
    "alignment_cell_evidence_present_count",
    "alignment_cell_evidence_missing_count",
    "overlay_batch_success_row_count",
    "overlay_batch_support_row_count",
    "raw_trace_row_present_count",
    "raw_trace_observed_count",
    "raw_trace_absent_count",
    "metric_warning_count",
    "expected_diff_design_candidate_count",
    "held_cell_count",
    "raw_overlay_no_writer_changes",
    "no_row_or_family_projection",
)


def build_backfill_expansion_raw_overlay_trace_identity(
    *,
    docs_dir: Path = DEFAULT_DOCS_DIR,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    sample_local_summary_json: Path = DEFAULT_SAMPLE_LOCAL_SUMMARY_JSON,
    sample_local_checks_tsv: Path = DEFAULT_SAMPLE_LOCAL_CHECKS_TSV,
    sample_local_row_manifest_tsv: Path = DEFAULT_SAMPLE_LOCAL_ROW_MANIFEST_TSV,
    sample_local_cells_tsv: Path = DEFAULT_SAMPLE_LOCAL_CELLS_TSV,
    overlay_batch_summary_tsv: Path = DEFAULT_OVERLAY_BATCH_SUMMARY_TSV,
    overlay_batch_summary_json: Path = DEFAULT_OVERLAY_BATCH_SUMMARY_JSON,
) -> dict[str, Any]:
    sample_local_problems = check_backfill_expansion_sample_local_ms1_evidence(
        summary_json=sample_local_summary_json,
        checks_tsv=sample_local_checks_tsv,
        row_manifest_tsv=sample_local_row_manifest_tsv,
    )
    sample_local_rows = read_tsv_required(
        sample_local_cells_tsv,
        SAMPLE_LOCAL_CELL_EVIDENCE_COLUMNS,
    )
    overlay_rows = read_tsv_required(
        overlay_batch_summary_tsv,
        OVERLAY_BATCH_SUMMARY_COLUMNS,
    )
    overlay_by_row = _overlay_by_row(overlay_rows)
    trace_by_key = _trace_rows_by_key(overlay_rows)
    facts = _trace_gate_facts(
        sample_local_rows=sample_local_rows,
        overlay_by_row=overlay_by_row,
        trace_by_key=trace_by_key,
        sample_local_problem_count=len(sample_local_problems),
    )
    checks = _check_rows(facts)
    failed = [row["check_id"] for row in checks if row["status"] != "pass"]
    if failed:
        raise ValueError(
            "Backfill expansion raw overlay trace identity failed: "
            + ";".join(failed),
        )

    docs_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    checks_tsv = docs_dir / "backfill_expansion_raw_overlay_trace_identity_checks.tsv"
    row_manifest_tsv = (
        docs_dir / "backfill_expansion_raw_overlay_trace_identity_row_manifest.tsv"
    )
    cell_trace_gate_tsv = (
        output_dir / "backfill_expansion_raw_overlay_trace_identity_cells.tsv"
    )
    summary_json = (
        docs_dir / "backfill_expansion_raw_overlay_trace_identity_summary.json"
    )

    write_tsv(checks_tsv, checks, CHECK_COLUMNS, extrasaction="raise")
    write_tsv(
        row_manifest_tsv,
        facts["row_manifest_rows"],
        ROW_MANIFEST_COLUMNS,
        extrasaction="raise",
    )
    write_tsv(
        cell_trace_gate_tsv,
        facts["cell_trace_gate_rows"],
        CELL_TRACE_GATE_COLUMNS,
        extrasaction="raise",
    )
    payload = _summary_payload(
        facts=facts,
        checks_tsv=checks_tsv,
        row_manifest_tsv=row_manifest_tsv,
        cell_trace_gate_tsv=cell_trace_gate_tsv,
        sample_local_summary_json=sample_local_summary_json,
        sample_local_checks_tsv=sample_local_checks_tsv,
        sample_local_row_manifest_tsv=sample_local_row_manifest_tsv,
        sample_local_cells_tsv=sample_local_cells_tsv,
        overlay_batch_summary_tsv=overlay_batch_summary_tsv,
        overlay_batch_summary_json=overlay_batch_summary_json,
        overlay_rows=overlay_rows,
    )
    summary_json.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _write_readme(docs_dir / "README.md", payload=payload)
    return payload


def check_backfill_expansion_raw_overlay_trace_identity(
    *,
    summary_json: Path = (
        DEFAULT_DOCS_DIR
        / "backfill_expansion_raw_overlay_trace_identity_summary.json"
    ),
    checks_tsv: Path = (
        DEFAULT_DOCS_DIR / "backfill_expansion_raw_overlay_trace_identity_checks.tsv"
    ),
    row_manifest_tsv: Path = (
        DEFAULT_DOCS_DIR
        / "backfill_expansion_raw_overlay_trace_identity_row_manifest.tsv"
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
        ("validation_label", "raw_backfill_expansion_overlay_trace_identity"),
        ("product_lane", "backfill"),
        ("strongest_evidence_tier", "85RAW RAW-backed evidence-only overlay"),
        (
            "release_decision",
            "expected_diff_design_for_666_raw_trace_observed_cells_and_hold_263_cells",
        ),
        ("raw_or_85raw_ran", True),
        ("raw_alignment_rerun", False),
        ("evidence_only_overlay", True),
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
    _check_overlay_trace_artifact_hashes(payload, problems)
    _check_checks_tsv(checks_tsv, problems)
    _check_row_manifest_tsv(row_manifest_tsv, problems)
    _check_optional_externalized_artifact(payload, "cell_trace_gate_tsv", problems)
    return problems


def _trace_gate_facts(
    *,
    sample_local_rows: Sequence[Mapping[str, str]],
    overlay_by_row: Mapping[str, Mapping[str, str]],
    trace_by_key: Mapping[tuple[str, str], Mapping[str, str]],
    sample_local_problem_count: int,
) -> dict[str, Any]:
    cell_rows = [
        _cell_trace_gate_row(
            row,
            overlay=overlay_by_row.get(text_value(row.get("peak_hypothesis_id"))),
            trace=trace_by_key.get(
                (
                    text_value(row.get("peak_hypothesis_id")),
                    text_value(row.get("sample_stem")),
                ),
            ),
        )
        for row in sample_local_rows
    ]
    row_manifest_rows = _row_manifest_rows(cell_rows)
    return {
        "sample_local_problem_count": sample_local_problem_count,
        "active_pressure_cell_count": len(cell_rows),
        "alignment_cell_evidence_present_cell_count": _count(
            cell_rows,
            "alignment_cell_evidence_status",
            "present",
        ),
        "alignment_cell_evidence_missing_cell_count": _count(
            cell_rows,
            "alignment_cell_evidence_status",
            "missing",
        ),
        "overlay_batch_success_row_count": _count(
            list(overlay_by_row.values()),
            "status",
            "success",
        ),
        "overlay_batch_support_row_count": _count(
            list(overlay_by_row.values()),
            "family_verdict",
            SUPPORT_FAMILY_VERDICT,
        ),
        "raw_trace_row_present_cell_count": _count(
            cell_rows,
            "raw_trace_row_status",
            "present",
        ),
        "raw_trace_observed_cell_count": _count(
            cell_rows,
            "raw_trace_gate_status",
            "raw_trace_observed_expected_diff_candidate",
        ),
        "raw_trace_absent_cell_count": _count(
            cell_rows,
            "raw_trace_gate_status",
            "raw_trace_absent_hold",
        ),
        "metric_warning_cell_count": sum(
            1 for row in cell_rows if text_value(row.get("metric_warning_flags"))
        ),
        "expected_diff_design_candidate_cell_count": _count(
            cell_rows,
            "next_gate",
            "expected_diff_and_provenance_gate",
        ),
        "held_cell_count": _count(cell_rows, "next_gate", "hold_or_review"),
        "cell_trace_gate_rows": cell_rows,
        "row_manifest_rows": row_manifest_rows,
    }


def _cell_trace_gate_row(
    row: Mapping[str, str],
    *,
    overlay: Mapping[str, str] | None,
    trace: Mapping[str, str] | None,
) -> dict[str, str]:
    row_id = text_value(row.get("peak_hypothesis_id"))
    sample = text_value(row.get("sample_stem"))
    alignment_status = text_value(row.get("alignment_cell_evidence_status"))
    overlay_status = text_value(overlay.get("status") if overlay else "")
    family_verdict = text_value(overlay.get("family_verdict") if overlay else "")
    trace_status = text_value(trace.get("status") if trace else "")
    trace_row_status = "present" if trace is not None else "missing"
    observed = _trace_observed(trace)
    if alignment_status == "missing":
        gate_status = "missing_alignment_cell_evidence_hold"
        next_gate = "hold_or_review"
    elif overlay_status != "success" or family_verdict != SUPPORT_FAMILY_VERDICT:
        gate_status = "family_overlay_not_supportive_hold"
        next_gate = "hold_or_review"
    elif trace is None:
        gate_status = "raw_trace_missing_hold"
        next_gate = "hold_or_review"
    elif observed:
        gate_status = "raw_trace_observed_expected_diff_candidate"
        next_gate = "expected_diff_and_provenance_gate"
    else:
        gate_status = "raw_trace_absent_hold"
        next_gate = "hold_or_review"
    warnings = _metric_warnings(trace) if observed else ()
    return {
        "schema_version": SCHEMA_VERSION,
        "opportunity_scope": text_value(row.get("opportunity_scope")),
        "peak_hypothesis_id": row_id,
        "sample_stem": sample,
        "alignment_cell_evidence_status": alignment_status,
        "raw_overlay_family_status": overlay_status,
        "family_verdict": family_verdict,
        "raw_trace_row_status": trace_row_status,
        "trace_status": trace_status,
        "trace_max_intensity": text_value(
            trace.get("trace_max_intensity") if trace else "",
        ),
        "local_window_max_intensity": text_value(
            trace.get("local_window_max_intensity") if trace else "",
        ),
        "local_window_to_global_max_ratio": text_value(
            trace.get("local_window_to_global_max_ratio") if trace else "",
        ),
        "local_window_apex_delta_min": text_value(
            trace.get("local_window_apex_delta_min") if trace else "",
        ),
        "apex_aligned_shape_similarity": text_value(
            trace.get("apex_aligned_shape_similarity") if trace else "",
        ),
        "absolute_own_max_shape_similarity": text_value(
            trace.get("absolute_own_max_shape_similarity") if trace else "",
        ),
        "raw_trace_gate_status": gate_status,
        "metric_warning_flags": ";".join(warnings),
        "product_authority_effect": "candidate_only_no_write_authority",
        "next_gate": next_gate,
    }


def _row_manifest_rows(
    cell_rows: Sequence[Mapping[str, str]],
) -> list[dict[str, str]]:
    grouped: dict[str, list[Mapping[str, str]]] = defaultdict(list)
    for row in cell_rows:
        if text_value(row.get("alignment_cell_evidence_status")) == "missing":
            continue
        grouped[text_value(row.get("peak_hypothesis_id"))].append(row)
    rows: list[dict[str, str]] = []
    for row_id, group_rows in sorted(grouped.items()):
        observed_count = _count(
            group_rows,
            "raw_trace_gate_status",
            "raw_trace_observed_expected_diff_candidate",
        )
        held_count = sum(
            1
            for row in group_rows
            if text_value(row.get("next_gate")) == "hold_or_review"
        )
        family_verdicts = sorted(
            {text_value(row.get("family_verdict")) for row in group_rows}
        )
        next_gate = (
            "expected_diff_and_provenance_gate"
            if observed_count
            else "hold_or_review"
        )
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "row_scope": "active_default_row_blank_cell",
                "peak_hypothesis_id": row_id,
                "candidate_cell_count": str(len(group_rows)),
                "alignment_cell_evidence_present_cell_count": str(len(group_rows)),
                "alignment_cell_evidence_missing_cell_count": "0",
                "raw_trace_row_present_cell_count": str(
                    _count(group_rows, "raw_trace_row_status", "present"),
                ),
                "raw_trace_observed_cell_count": str(observed_count),
                "raw_trace_absent_cell_count": str(
                    _count(
                        group_rows,
                        "raw_trace_gate_status",
                        "raw_trace_absent_hold",
                    ),
                ),
                "metric_warning_cell_count": str(
                    sum(
                        1
                        for row in group_rows
                        if text_value(row.get("metric_warning_flags"))
                    ),
                ),
                "expected_diff_design_candidate_cell_count": str(observed_count),
                "held_cell_count": str(held_count),
                "family_verdict": ";".join(family_verdicts),
                "product_authority_effect": "no_new_backfill_authority_gate_only",
                "next_gate": next_gate,
            },
        )
    return rows


def _overlay_by_row(
    rows: Sequence[Mapping[str, str]],
) -> dict[str, Mapping[str, str]]:
    result: dict[str, Mapping[str, str]] = {}
    for row in rows:
        row_id = text_value(row.get("feature_family_id"))
        if not row_id:
            continue
        if row_id in result:
            raise ValueError(f"duplicate overlay batch row for {row_id}")
        result[row_id] = row
    return result


def _trace_rows_by_key(
    overlay_rows: Sequence[Mapping[str, str]],
) -> dict[tuple[str, str], Mapping[str, str]]:
    result: dict[tuple[str, str], Mapping[str, str]] = {}
    for overlay in overlay_rows:
        family_id = text_value(overlay.get("feature_family_id"))
        if text_value(overlay.get("status")) != "success":
            continue
        trace_summary_tsv = _artifact_path(
            text_value(overlay.get("trace_summary_tsv")),
        )
        trace_rows = read_tsv_required(trace_summary_tsv, TRACE_SUMMARY_COLUMNS)
        for row in trace_rows:
            key = (family_id, text_value(row.get("sample_stem")))
            if key in result:
                raise ValueError(
                    f"duplicate trace summary row for {key[0]} {key[1]}",
                )
            result[key] = row
    return result


def _trace_observed(trace: Mapping[str, str] | None) -> bool:
    if trace is None:
        return False
    if text_value(trace.get("status")) not in TRACE_OBSERVED_STATUSES:
        return False
    trace_max = optional_float(trace.get("trace_max_intensity"))
    local_max = optional_float(trace.get("local_window_max_intensity"))
    return (
        trace_max is not None
        and trace_max > 0
        and local_max is not None
        and local_max > 0
    )


def _metric_warnings(trace: Mapping[str, str] | None) -> tuple[str, ...]:
    if trace is None:
        return ()
    warnings: list[str] = []
    ratio = optional_float(trace.get("local_window_to_global_max_ratio"))
    delta = optional_float(trace.get("local_window_apex_delta_min"))
    shape = optional_float(trace.get("apex_aligned_shape_similarity"))
    if ratio is None:
        warnings.append("ratio_blank")
    elif ratio < LOW_LOCAL_GLOBAL_RATIO_THRESHOLD:
        warnings.append("ratio_low")
    if delta is None:
        warnings.append("delta_blank")
    elif abs(delta) > HIGH_LOCAL_APEX_DELTA_MIN_THRESHOLD:
        warnings.append("local_apex_delta_high")
    if shape is None:
        warnings.append("shape_blank")
    elif shape < LOW_APEX_SHAPE_SIMILARITY_THRESHOLD:
        warnings.append("shape_low")
    return tuple(warnings)


def _check_rows(facts: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [
        _check(
            "sample_local_ms1_evidence_checker_pass",
            facts["sample_local_problem_count"],
            0,
            facts["sample_local_problem_count"] == 0,
        ),
        _count_check(facts, "active_pressure_cell_count", "active_pressure_cell_count"),
        _count_check(
            facts,
            "alignment_cell_evidence_present_cell_count",
            "alignment_cell_evidence_present_count",
        ),
        _count_check(
            facts,
            "alignment_cell_evidence_missing_cell_count",
            "alignment_cell_evidence_missing_count",
        ),
        _count_check(
            facts,
            "overlay_batch_success_row_count",
            "overlay_batch_success_row_count",
        ),
        _count_check(
            facts,
            "overlay_batch_support_row_count",
            "overlay_batch_support_row_count",
        ),
        _count_check(
            facts,
            "raw_trace_row_present_cell_count",
            "raw_trace_row_present_count",
        ),
        _count_check(
            facts,
            "raw_trace_observed_cell_count",
            "raw_trace_observed_count",
        ),
        _count_check(facts, "raw_trace_absent_cell_count", "raw_trace_absent_count"),
        _count_check(facts, "metric_warning_cell_count", "metric_warning_count"),
        _count_check(
            facts,
            "expected_diff_design_candidate_cell_count",
            "expected_diff_design_candidate_count",
        ),
        _count_check(facts, "held_cell_count", "held_cell_count"),
        _check(
            "raw_overlay_no_writer_changes",
            "raw_overlay=TRUE;writer=FALSE;default_matrix=FALSE",
            "bounded evidence-only overlay gate",
            True,
        ),
        _check(
            "no_row_or_family_projection",
            "row_or_family_evidence_projected_to_cells=FALSE",
            "exact sample-local trace rows required",
            True,
        ),
    ]


def _count_check(
    facts: Mapping[str, Any],
    field: str,
    check_id: str,
) -> dict[str, Any]:
    return _check(
        check_id,
        facts[field],
        EXPECTED_COUNTS[field],
        facts[field] == EXPECTED_COUNTS[field],
    )


def _summary_payload(
    *,
    facts: Mapping[str, Any],
    checks_tsv: Path,
    row_manifest_tsv: Path,
    cell_trace_gate_tsv: Path,
    sample_local_summary_json: Path,
    sample_local_checks_tsv: Path,
    sample_local_row_manifest_tsv: Path,
    sample_local_cells_tsv: Path,
    overlay_batch_summary_tsv: Path,
    overlay_batch_summary_json: Path,
    overlay_rows: Sequence[Mapping[str, str]],
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "pass",
        "validation_label": "raw_backfill_expansion_overlay_trace_identity",
        "product_lane": "backfill",
        "trace_gate_scope": "cid_nl_active_blank_cells_with_sample_local_evidence",
        "strongest_evidence_tier": "85RAW RAW-backed evidence-only overlay",
        "release_decision": (
            "expected_diff_design_for_666_raw_trace_observed_cells_and_hold_263_cells"
        ),
        **{
            field: facts[field]
            for field in (
                "active_pressure_cell_count",
                "alignment_cell_evidence_present_cell_count",
                "alignment_cell_evidence_missing_cell_count",
                "overlay_batch_success_row_count",
                "overlay_batch_support_row_count",
                "raw_trace_row_present_cell_count",
                "raw_trace_observed_cell_count",
                "raw_trace_absent_cell_count",
                "metric_warning_cell_count",
                "expected_diff_design_candidate_cell_count",
                "held_cell_count",
            )
        },
        "raw_or_85raw_ran": True,
        "raw_alignment_rerun": False,
        "raw_run_scope": "bounded_20_row_evidence_only_overlay",
        "evidence_only_overlay": True,
        "product_writer_changed_by_checker": False,
        "default_quant_matrix_changed_by_checker": False,
        "workbook_or_gui_changed": False,
        "selected_peak_area_or_counting_changed": False,
        "backfill_writer_authority_changed_by_checker": False,
        "broad_backfill_unparked": False,
        "candidate_rows_are_matrix_rows": False,
        "row_or_family_evidence_projected_to_cells": False,
        "sample_local_key_match_required": True,
        "validation_reviewer_bypass_reason": (
            "multi_agent runtime policy allows subagents only when explicitly "
            "requested by the user; main agent performed preflight and acceptance"
        ),
        "decision_statement": (
            "The evidence-only RAW overlay succeeded for all 20 queued families. "
            "Exact trace rows exist for all 675 alignment-present cells, and 666 "
            "of those cells have observed RAW trace signal. The 9 trace-absent "
            "cells plus 254 missing-alignment cells remain held. The 43 metric "
            "warning cells are retained as expected-diff candidates with review "
            "notes, not direct writer authority."
        ),
        "authority_statement": (
            "This gate only narrows the Backfill expected-diff design set. It "
            "does not grant ProductWriter authority, write a default matrix, "
            "change selected peak/area/counting, or project row/family evidence "
            "onto sample cells."
        ),
        "input_artifacts": {
            "sample_local_summary_json": _artifact(sample_local_summary_json),
            "sample_local_checks_tsv": _artifact(sample_local_checks_tsv),
            "sample_local_row_manifest_tsv": _artifact(
                sample_local_row_manifest_tsv,
            ),
            "sample_local_cells_tsv": _artifact(sample_local_cells_tsv),
            "overlay_batch_summary_tsv": _artifact(overlay_batch_summary_tsv),
            "overlay_batch_summary_json": _artifact(overlay_batch_summary_json),
        },
        "overlay_trace_summary_artifacts": _overlay_trace_summary_artifacts(
            overlay_rows,
        ),
        "artifacts": {
            "summary_json": {
                "path": (
                    "docs/superpowers/validation/"
                    "backfill_expansion_raw_overlay_trace_identity_v1/"
                    "backfill_expansion_raw_overlay_trace_identity_summary.json"
                ),
                "retention_decision": "keep_summary",
            },
            "checks_tsv": _artifact(checks_tsv)
            | {"retention_decision": "keep_summary"},
            "row_manifest_tsv": _artifact(row_manifest_tsv)
            | {"retention_decision": "keep_contract"},
            "cell_trace_gate_tsv": _artifact(cell_trace_gate_tsv)
            | {
                "retention_decision": "externalize",
                "tracked_replacement_or_summary": (
                    "docs/superpowers/validation/"
                    "backfill_expansion_raw_overlay_trace_identity_v1/"
                    "backfill_expansion_raw_overlay_trace_identity_summary.json"
                ),
            },
        },
    }


def _write_readme(path: Path, *, payload: Mapping[str, Any]) -> None:
    lines = [
        "# Backfill Expansion RAW Overlay Trace Identity v1",
        "",
        "Status: `pass`.",
        "",
        "This gate consumes the 20-row evidence-only RAW overlay batch and "
        "joins each trace back to the exact `peak_hypothesis_id + sample_stem` "
        "Backfill pressure cell.",
        "",
        "## Decision",
        "",
        "Release decision: "
        "`expected_diff_design_for_666_raw_trace_observed_cells_and_hold_"
        "263_cells`.",
        "",
        "- Active Backfill pressure cells: "
        f"`{payload['active_pressure_cell_count']}`.",
        "- Exact sample-local alignment evidence present: "
        f"`{payload['alignment_cell_evidence_present_cell_count']}`.",
        "- Missing exact alignment evidence: "
        f"`{payload['alignment_cell_evidence_missing_cell_count']}`.",
        "- RAW trace rows found for alignment-present cells: "
        f"`{payload['raw_trace_row_present_cell_count']}`.",
        "- RAW trace observed cells: "
        f"`{payload['raw_trace_observed_cell_count']}`.",
        "- RAW trace absent cells: "
        f"`{payload['raw_trace_absent_cell_count']}`.",
        "- Metric warning cells retained with notes: "
        f"`{payload['metric_warning_cell_count']}`.",
        "- Held cells: "
        f"`{payload['held_cell_count']}`.",
        "",
        "The 666 observed cells may feed a future expected-diff/provenance "
        "design. They are not write-ready here. The 9 trace-absent cells and "
        "254 missing-alignment cells remain held.",
        "",
        "## Boundary",
        "",
        "This gate ran a bounded evidence-only RAW overlay, not an 85RAW "
        "alignment rerun. It does not write a default matrix, change "
        "ProductWriter authority, unpark broad Backfill, or change selected "
        "peak/area/counting.",
        "",
        "## Files",
        "",
        "- Summary JSON: "
        "`docs/superpowers/validation/"
        "backfill_expansion_raw_overlay_trace_identity_v1/"
        "backfill_expansion_raw_overlay_trace_identity_summary.json`",
        "- Checks TSV: "
        "`docs/superpowers/validation/"
        "backfill_expansion_raw_overlay_trace_identity_v1/"
        "backfill_expansion_raw_overlay_trace_identity_checks.tsv`",
        "- Compact row manifest: "
        "`docs/superpowers/validation/"
        "backfill_expansion_raw_overlay_trace_identity_v1/"
        "backfill_expansion_raw_overlay_trace_identity_row_manifest.tsv`",
        "- Full cell gate map: "
        "`output/validation/backfill_expansion_raw_overlay_trace_identity_v1/"
        "backfill_expansion_raw_overlay_trace_identity_cells.tsv`",
        "- RAW overlay batch outputs: "
        "`output/validation/backfill_expansion_raw_overlay_trace_identity_v1/"
        "family_ms1_overlay_batch/`",
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
        path = _artifact_path(path_text)
        if not path.is_file():
            problems.append(f"summary input_artifacts {artifact_id} missing")
            continue
        if file_sha256(path) != expected_hash:
            problems.append(f"summary input_artifacts {artifact_id} sha256 mismatch")


def _check_overlay_trace_artifact_hashes(
    payload: Mapping[str, Any],
    problems: list[str],
) -> None:
    artifacts = payload.get("overlay_trace_summary_artifacts")
    if not isinstance(artifacts, Mapping):
        problems.append("summary overlay_trace_summary_artifacts mismatch")
        return
    for family_id, raw_entry in artifacts.items():
        if not isinstance(raw_entry, Mapping):
            problems.append(f"overlay trace artifact {family_id} invalid")
            continue
        path_text = text_value(raw_entry.get("path"))
        expected_hash = text_value(raw_entry.get("sha256"))
        if not path_text or not expected_hash:
            problems.append(f"overlay trace artifact {family_id} incomplete")
            continue
        path = _artifact_path(path_text)
        if not path.is_file():
            problems.append(f"overlay trace artifact {family_id} missing")
            continue
        if file_sha256(path) != expected_hash:
            problems.append(f"overlay trace artifact {family_id} sha256 mismatch")


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
    if len(rows) != EXPECTED_COUNTS["overlay_batch_success_row_count"]:
        problems.append("row_manifest row count mismatch")
    observed_count = sum(
        _int(row.get("raw_trace_observed_cell_count")) for row in rows
    )
    held_count = sum(_int(row.get("held_cell_count")) for row in rows)
    if observed_count != EXPECTED_COUNTS["raw_trace_observed_cell_count"]:
        problems.append("row_manifest observed trace count mismatch")
    if held_count != EXPECTED_COUNTS["raw_trace_absent_cell_count"]:
        problems.append("row_manifest held trace count mismatch")
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
    path = _artifact_path(path_text)
    if path.exists() and file_sha256(path) != text_value(artifact.get("sha256")):
        problems.append(f"summary {artifact_id} sha256 mismatch")


def _overlay_trace_summary_artifacts(
    overlay_rows: Sequence[Mapping[str, str]],
) -> dict[str, dict[str, Any]]:
    artifacts: dict[str, dict[str, Any]] = {}
    for row in overlay_rows:
        family_id = text_value(row.get("feature_family_id"))
        trace_summary = _artifact_path(text_value(row.get("trace_summary_tsv")))
        if family_id and trace_summary.exists():
            artifacts[family_id] = _artifact(trace_summary)
    return artifacts


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


def _artifact_path(path_text: str) -> Path:
    path = Path(path_text)
    if path.is_absolute():
        return path
    return (ROOT / path).resolve(strict=False)


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
        "--sample-local-summary-json",
        type=Path,
        default=DEFAULT_SAMPLE_LOCAL_SUMMARY_JSON,
    )
    parser.add_argument(
        "--sample-local-checks-tsv",
        type=Path,
        default=DEFAULT_SAMPLE_LOCAL_CHECKS_TSV,
    )
    parser.add_argument(
        "--sample-local-row-manifest-tsv",
        type=Path,
        default=DEFAULT_SAMPLE_LOCAL_ROW_MANIFEST_TSV,
    )
    parser.add_argument(
        "--sample-local-cells-tsv",
        type=Path,
        default=DEFAULT_SAMPLE_LOCAL_CELLS_TSV,
    )
    parser.add_argument(
        "--overlay-batch-summary-tsv",
        type=Path,
        default=DEFAULT_OVERLAY_BATCH_SUMMARY_TSV,
    )
    parser.add_argument(
        "--overlay-batch-summary-json",
        type=Path,
        default=DEFAULT_OVERLAY_BATCH_SUMMARY_JSON,
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
            / "backfill_expansion_raw_overlay_trace_identity_summary.json"
        )
        checks_tsv = args.checks_tsv or (
            args.docs_dir / "backfill_expansion_raw_overlay_trace_identity_checks.tsv"
        )
        row_manifest_tsv = args.row_manifest_tsv or (
            args.docs_dir
            / "backfill_expansion_raw_overlay_trace_identity_row_manifest.tsv"
        )
        problems = check_backfill_expansion_raw_overlay_trace_identity(
            summary_json=summary_json,
            checks_tsv=checks_tsv,
            row_manifest_tsv=row_manifest_tsv,
        )
        for problem in problems:
            print(f"backfill_expansion_raw_overlay_trace_identity_problem: {problem}")
        return 2 if problems else 0

    try:
        payload = build_backfill_expansion_raw_overlay_trace_identity(
            docs_dir=args.docs_dir,
            output_dir=args.output_dir,
            sample_local_summary_json=args.sample_local_summary_json,
            sample_local_checks_tsv=args.sample_local_checks_tsv,
            sample_local_row_manifest_tsv=args.sample_local_row_manifest_tsv,
            sample_local_cells_tsv=args.sample_local_cells_tsv,
            overlay_batch_summary_tsv=args.overlay_batch_summary_tsv,
            overlay_batch_summary_json=args.overlay_batch_summary_json,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    summary_path = (
        args.docs_dir
        / "backfill_expansion_raw_overlay_trace_identity_summary.json"
    )
    print(f"backfill_expansion_raw_overlay_trace_identity_summary: {summary_path}")
    print(f"backfill_expansion_raw_overlay_trace_identity_status: {payload['status']}")
    print(
        "backfill_expansion_raw_overlay_trace_identity_release_decision: "
        f"{payload['release_decision']}"
    )
    if args.require_pass and payload.get("status") != "pass":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
