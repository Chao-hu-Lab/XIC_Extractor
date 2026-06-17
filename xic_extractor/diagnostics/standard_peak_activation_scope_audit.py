"""Audit high-signal clean coverage for standard-peak activation writes."""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from xic_extractor.diagnostics.diagnostic_io import (
    file_sha256,
    format_diagnostic_value,
    optional_float,
    text_value,
    write_tsv,
)
from xic_extractor.tabular_io import read_tsv_with_header

SCHEMA_VERSION = "standard_peak_activation_scope_audit_v1"
NARROW_EXPECTED_DIFF_ACCEPTANCE_SCHEMA_VERSION = (
    "standard_peak_narrow_activation_expected_diff_acceptance_v1"
)
LOW_SCAN_EXPECTED_DIFF_ACCEPTANCE_SCHEMA_VERSION = (
    "standard_peak_low_scan_activation_expected_diff_acceptance_v1"
)
LOW_HEIGHT_EXPECTED_DIFF_ACCEPTANCE_SCHEMA_VERSION = (
    "standard_peak_low_height_activation_expected_diff_acceptance_v1"
)

MIN_SHAPE_SIMILARITY = 0.95
MIN_LOCAL_GLOBAL_RATIO = 0.95
MIN_CELL_HEIGHT = 2_000_000.0
MIN_BOUNDARY_WIDTH_MIN = 0.30
MAX_BOUNDARY_WIDTH_MIN = 0.65
MAX_APEX_DELTA_ABS_MIN = 0.15
MIN_INTEGRATION_SCAN_COUNT = 10
MIN_LOW_SCAN_CLEAN_SCAN_COUNT = 7
MAX_LOW_SCAN_CLEAN_SCAN_COUNT = 9
SUPPORTED_TRACE_STATUSES = frozenset({"detected", "rescued"})

ACTIVATION_DELTA_REQUIRED_COLUMNS = (
    "feature_family_id",
    "sample_id",
    "peak_hypothesis_id",
    "matrix_value_source_row_sha256",
    "matrix_value_effect",
    "activated_matrix_value",
    "source_cell_status",
)

SHADOW_PROJECTION_REQUIRED_COLUMNS = (
    "feature_family_id",
    "sample_stem",
    "peak_hypothesis_id",
    "shadow_projection_row_sha256",
    "overlay_png_path",
)

AUDIT_COLUMNS = (
    "schema_version",
    "source_run_id",
    "feature_family_id",
    "peak_hypothesis_id",
    "sample_id",
    "matrix_value_effect",
    "source_cell_status",
    "activated_matrix_value",
    "matrix_value_source_row_sha256",
    "projection_match_status",
    "projection_feature_family_id",
    "projection_sample_stem",
    "projection_peak_hypothesis_id",
    "projection_cell_status",
    "projection_gap_fill_state",
    "projection_local_global_ratio",
    "projection_overlay_png_path",
    "trace_data_path",
    "trace_match_status",
    "trace_status",
    "cell_area",
    "cell_height",
    "cell_start_rt",
    "cell_end_rt",
    "cell_apex_rt",
    "family_center_rt",
    "boundary_width_min",
    "apex_delta_abs_min",
    "integration_scan_count",
    "apex_aligned_shape_similarity",
    "local_window_to_global_max_ratio",
    "high_signal_clean_status",
    "high_signal_clean_blockers",
    "low_scan_clean_status",
    "low_scan_clean_blockers",
    "low_height_clean_status",
    "low_height_clean_blockers",
)

SUMMARY_COLUMNS = (
    "schema_version",
    "source_run_id",
    "activation_value_delta_tsv",
    "activation_value_delta_sha256",
    "shadow_projection_cells_tsv",
    "shadow_projection_cells_sha256",
    "activation_value_delta_row_count",
    "written_activation_row_count",
    "projection_matched_written_count",
    "projection_missing_written_count",
    "projection_ambiguous_written_count",
    "trace_matched_written_count",
    "missing_overlay_path_written_count",
    "missing_trace_json_written_count",
    "missing_trace_sample_written_count",
    "trace_json_parse_error_written_count",
    "high_signal_clean_eligible_written_count",
    "high_signal_clean_ineligible_written_count",
    "high_signal_clean_missing_evidence_written_count",
    "low_scan_clean_eligible_written_count",
    "low_scan_clean_ineligible_written_count",
    "low_scan_clean_missing_evidence_written_count",
    "low_height_clean_eligible_written_count",
    "low_height_clean_ineligible_written_count",
    "low_height_clean_missing_evidence_written_count",
    "eligible_scope_fraction_of_written",
    "low_scan_clean_scope_fraction_of_written",
    "low_height_clean_scope_fraction_of_written",
    "broad_activation_scope_status",
    "narrow_activation_scope_status",
    "low_scan_clean_activation_scope_status",
    "low_height_clean_activation_scope_status",
    "remaining_blocker",
    "audit_tsv",
    "eligible_activation_value_delta_tsv",
    "low_scan_clean_activation_value_delta_tsv",
    "low_height_clean_activation_value_delta_tsv",
)

NARROW_EXPECTED_DIFF_ACCEPTANCE_COLUMNS = (
    "schema_version",
    "source_run_id",
    "acceptance_status",
    "expected_scope",
    "activation_value_delta_tsv",
    "activation_value_delta_sha256",
    "activation_scope_audit_tsv",
    "activation_scope_audit_sha256",
    "eligible_activation_value_delta_tsv",
    "eligible_activation_value_delta_sha256",
    "full_written_delta_row_count",
    "eligible_audit_row_count",
    "eligible_delta_row_count",
    "duplicate_delta_key_count",
    "missing_delta_row_count",
    "unexpected_delta_row_count",
    "non_eligible_delta_row_count",
    "not_written_delta_row_count",
    "unchanged_delta_row_count",
    "blank_activated_value_count",
    "blocking_reasons",
    "product_surface_changed",
    "next_action",
)


@dataclass(frozen=True)
class ActivationScopeAuditOutputs:
    audit_tsv: Path
    summary_tsv: Path
    summary_json: Path
    eligible_activation_value_delta_tsv: Path
    low_scan_clean_activation_value_delta_tsv: Path
    low_height_clean_activation_value_delta_tsv: Path
    narrow_expected_diff_acceptance_tsv: Path
    narrow_expected_diff_acceptance_json: Path
    low_scan_expected_diff_acceptance_tsv: Path
    low_scan_expected_diff_acceptance_json: Path
    low_height_expected_diff_acceptance_tsv: Path
    low_height_expected_diff_acceptance_json: Path
    status: str


def run_activation_scope_audit(
    *,
    activation_value_delta_tsv: Path,
    shadow_projection_cells_tsv: Path,
    output_dir: Path,
    source_run_id: str = "",
) -> ActivationScopeAuditOutputs:
    """Read existing no-RAW artifacts and write high-signal clean scope audit TSVs."""

    delta_header, delta_rows = read_tsv_with_header(
        activation_value_delta_tsv,
        required_columns=ACTIVATION_DELTA_REQUIRED_COLUMNS,
        encoding="utf-8-sig",
    )
    _shadow_header, shadow_rows = read_tsv_with_header(
        shadow_projection_cells_tsv,
        required_columns=SHADOW_PROJECTION_REQUIRED_COLUMNS,
        encoding="utf-8-sig",
    )
    audit_rows, summary = audit_activation_scope(
        activation_value_delta_rows=delta_rows,
        shadow_projection_rows=shadow_rows,
        activation_value_delta_tsv=activation_value_delta_tsv,
        shadow_projection_cells_tsv=shadow_projection_cells_tsv,
        source_run_id=source_run_id,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    audit_tsv = output_dir / "activation_high_signal_clean_scope_audit.tsv"
    summary_tsv = output_dir / "activation_high_signal_clean_scope_summary.tsv"
    summary_json = output_dir / "activation_high_signal_clean_scope_summary.json"
    eligible_delta_tsv = output_dir / "eligible_activation_value_delta.tsv"
    low_scan_delta_tsv = output_dir / "low_scan_clean_activation_value_delta.tsv"
    low_height_delta_tsv = output_dir / "low_height_clean_activation_value_delta.tsv"
    narrow_acceptance_tsv = (
        output_dir / "narrow_activation_expected_diff_acceptance.tsv"
    )
    narrow_acceptance_json = (
        output_dir / "narrow_activation_expected_diff_acceptance.json"
    )
    low_scan_acceptance_tsv = (
        output_dir / "low_scan_clean_activation_expected_diff_acceptance.tsv"
    )
    low_scan_acceptance_json = (
        output_dir / "low_scan_clean_activation_expected_diff_acceptance.json"
    )
    low_height_acceptance_tsv = (
        output_dir / "low_height_clean_activation_expected_diff_acceptance.tsv"
    )
    low_height_acceptance_json = (
        output_dir / "low_height_clean_activation_expected_diff_acceptance.json"
    )
    eligible_hashes = {
        text_value(row.get("matrix_value_source_row_sha256"))
        for row in audit_rows
        if text_value(row.get("high_signal_clean_status")) == "eligible"
    }
    low_scan_hashes = {
        text_value(row.get("matrix_value_source_row_sha256"))
        for row in audit_rows
        if text_value(row.get("low_scan_clean_status")) == "eligible"
    }
    low_height_hashes = {
        text_value(row.get("matrix_value_source_row_sha256"))
        for row in audit_rows
        if text_value(row.get("low_height_clean_status")) == "eligible"
    }
    eligible_delta_rows = tuple(
        row
        for row in delta_rows
        if text_value(row.get("matrix_value_effect")) == "written"
        and text_value(row.get("matrix_value_source_row_sha256")) in eligible_hashes
    )
    low_scan_delta_rows = tuple(
        row
        for row in delta_rows
        if text_value(row.get("matrix_value_effect")) == "written"
        and text_value(row.get("matrix_value_source_row_sha256")) in low_scan_hashes
    )
    low_height_delta_rows = tuple(
        row
        for row in delta_rows
        if text_value(row.get("matrix_value_effect")) == "written"
        and text_value(row.get("matrix_value_source_row_sha256")) in low_height_hashes
    )

    summary = dict(summary)
    summary["audit_tsv"] = str(audit_tsv)
    summary["eligible_activation_value_delta_tsv"] = str(eligible_delta_tsv)
    summary["low_scan_clean_activation_value_delta_tsv"] = str(low_scan_delta_tsv)
    summary["low_height_clean_activation_value_delta_tsv"] = str(
        low_height_delta_tsv,
    )
    write_tsv(
        audit_tsv,
        audit_rows,
        AUDIT_COLUMNS,
        formatter=format_diagnostic_value,
        lineterminator="\n",
    )
    write_tsv(
        eligible_delta_tsv,
        eligible_delta_rows,
        delta_header,
        formatter=format_diagnostic_value,
        lineterminator="\n",
    )
    write_tsv(
        low_scan_delta_tsv,
        low_scan_delta_rows,
        delta_header,
        formatter=format_diagnostic_value,
        lineterminator="\n",
    )
    write_tsv(
        low_height_delta_tsv,
        low_height_delta_rows,
        delta_header,
        formatter=format_diagnostic_value,
        lineterminator="\n",
    )
    narrow_acceptance = build_narrow_expected_diff_acceptance(
        audit_rows=audit_rows,
        eligible_activation_value_delta_rows=eligible_delta_rows,
        activation_value_delta_rows=delta_rows,
        activation_value_delta_tsv=activation_value_delta_tsv,
        activation_scope_audit_tsv=audit_tsv,
        eligible_activation_value_delta_tsv=eligible_delta_tsv,
        source_run_id=source_run_id,
    )
    low_scan_acceptance = build_scope_expected_diff_acceptance(
        audit_rows=audit_rows,
        eligible_activation_value_delta_rows=low_scan_delta_rows,
        activation_value_delta_rows=delta_rows,
        activation_value_delta_tsv=activation_value_delta_tsv,
        activation_scope_audit_tsv=audit_tsv,
        eligible_activation_value_delta_tsv=low_scan_delta_tsv,
        source_run_id=source_run_id,
        scope_status_column="low_scan_clean_status",
        expected_scope="low_scan_clean_eligible_activation_rows",
        schema_version=LOW_SCAN_EXPECTED_DIFF_ACCEPTANCE_SCHEMA_VERSION,
        no_rows_blocker="no_low_scan_clean_eligible_delta_rows",
        product_decision_next_action=(
            "product_decision_required_before_writing_low_scan_clean_activation_output"
        ),
    )
    low_height_acceptance = build_scope_expected_diff_acceptance(
        audit_rows=audit_rows,
        eligible_activation_value_delta_rows=low_height_delta_rows,
        activation_value_delta_rows=delta_rows,
        activation_value_delta_tsv=activation_value_delta_tsv,
        activation_scope_audit_tsv=audit_tsv,
        eligible_activation_value_delta_tsv=low_height_delta_tsv,
        source_run_id=source_run_id,
        scope_status_column="low_height_clean_status",
        expected_scope="low_height_clean_eligible_activation_rows",
        schema_version=LOW_HEIGHT_EXPECTED_DIFF_ACCEPTANCE_SCHEMA_VERSION,
        no_rows_blocker="no_low_height_clean_eligible_delta_rows",
        product_decision_next_action=(
            "product_decision_required_before_writing_low_height_clean_activation_output"
        ),
    )
    write_tsv(
        narrow_acceptance_tsv,
        (narrow_acceptance,),
        NARROW_EXPECTED_DIFF_ACCEPTANCE_COLUMNS,
        formatter=format_diagnostic_value,
        lineterminator="\n",
    )
    narrow_acceptance_json.write_text(
        json.dumps(narrow_acceptance, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    write_tsv(
        low_scan_acceptance_tsv,
        (low_scan_acceptance,),
        NARROW_EXPECTED_DIFF_ACCEPTANCE_COLUMNS,
        formatter=format_diagnostic_value,
        lineterminator="\n",
    )
    low_scan_acceptance_json.write_text(
        json.dumps(low_scan_acceptance, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    write_tsv(
        low_height_acceptance_tsv,
        (low_height_acceptance,),
        NARROW_EXPECTED_DIFF_ACCEPTANCE_COLUMNS,
        formatter=format_diagnostic_value,
        lineterminator="\n",
    )
    low_height_acceptance_json.write_text(
        json.dumps(low_height_acceptance, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    write_tsv(
        summary_tsv,
        (summary,),
        SUMMARY_COLUMNS,
        formatter=format_diagnostic_value,
        lineterminator="\n",
    )
    summary_json.write_text(
        json.dumps(summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return ActivationScopeAuditOutputs(
        audit_tsv=audit_tsv,
        summary_tsv=summary_tsv,
        summary_json=summary_json,
        eligible_activation_value_delta_tsv=eligible_delta_tsv,
        low_scan_clean_activation_value_delta_tsv=low_scan_delta_tsv,
        low_height_clean_activation_value_delta_tsv=low_height_delta_tsv,
        narrow_expected_diff_acceptance_tsv=narrow_acceptance_tsv,
        narrow_expected_diff_acceptance_json=narrow_acceptance_json,
        low_scan_expected_diff_acceptance_tsv=low_scan_acceptance_tsv,
        low_scan_expected_diff_acceptance_json=low_scan_acceptance_json,
        low_height_expected_diff_acceptance_tsv=low_height_acceptance_tsv,
        low_height_expected_diff_acceptance_json=low_height_acceptance_json,
        status=summary["broad_activation_scope_status"],
    )


def audit_activation_scope(
    *,
    activation_value_delta_rows: Sequence[Mapping[str, str]],
    shadow_projection_rows: Sequence[Mapping[str, str]],
    activation_value_delta_tsv: Path,
    shadow_projection_cells_tsv: Path,
    source_run_id: str = "",
) -> tuple[tuple[dict[str, str], ...], dict[str, str]]:
    projection_by_sha = _rows_by_sha(
        shadow_projection_rows,
        "shadow_projection_row_sha256",
    )
    trace_cache: dict[Path, tuple[str, dict[str, Any] | None]] = {}
    audit_rows = tuple(
        _audit_delta_row(
            row,
            projection_by_sha=projection_by_sha,
            trace_cache=trace_cache,
            source_run_id=source_run_id,
        )
        for row in activation_value_delta_rows
    )
    summary = _summary_row(
        audit_rows,
        activation_value_delta_tsv=activation_value_delta_tsv,
        shadow_projection_cells_tsv=shadow_projection_cells_tsv,
        source_run_id=source_run_id,
    )
    return audit_rows, summary


def build_narrow_expected_diff_acceptance(
    *,
    audit_rows: Sequence[Mapping[str, str]],
    eligible_activation_value_delta_rows: Sequence[Mapping[str, str]],
    activation_value_delta_rows: Sequence[Mapping[str, str]],
    activation_value_delta_tsv: Path,
    activation_scope_audit_tsv: Path,
    eligible_activation_value_delta_tsv: Path,
    source_run_id: str = "",
) -> dict[str, str]:
    """Validate the filtered high-signal-clean delta as a narrow expected diff."""

    return build_scope_expected_diff_acceptance(
        audit_rows=audit_rows,
        eligible_activation_value_delta_rows=eligible_activation_value_delta_rows,
        activation_value_delta_rows=activation_value_delta_rows,
        activation_value_delta_tsv=activation_value_delta_tsv,
        activation_scope_audit_tsv=activation_scope_audit_tsv,
        eligible_activation_value_delta_tsv=eligible_activation_value_delta_tsv,
        source_run_id=source_run_id,
        scope_status_column="high_signal_clean_status",
        expected_scope="high_signal_clean_eligible_activation_rows",
        schema_version=NARROW_EXPECTED_DIFF_ACCEPTANCE_SCHEMA_VERSION,
        no_rows_blocker="no_high_signal_clean_eligible_delta_rows",
        product_decision_next_action=(
            "product_decision_required_before_writing_narrow_activation_output"
        ),
    )


def build_scope_expected_diff_acceptance(
    *,
    audit_rows: Sequence[Mapping[str, str]],
    eligible_activation_value_delta_rows: Sequence[Mapping[str, str]],
    activation_value_delta_rows: Sequence[Mapping[str, str]],
    activation_value_delta_tsv: Path,
    activation_scope_audit_tsv: Path,
    eligible_activation_value_delta_tsv: Path,
    source_run_id: str = "",
    scope_status_column: str,
    expected_scope: str,
    schema_version: str,
    no_rows_blocker: str,
    product_decision_next_action: str,
) -> dict[str, str]:
    """Validate a filtered activation delta as an explicit expected diff."""

    written_full_keys = {
        _delta_key(row)
        for row in activation_value_delta_rows
        if text_value(row.get("matrix_value_effect")) == "written"
    }
    eligible_audit_keys = {
        _audit_key(row)
        for row in audit_rows
        if text_value(row.get(scope_status_column)) == "eligible"
        and text_value(row.get("matrix_value_effect")) == "written"
    }
    eligible_delta_keys = [
        _delta_key(row) for row in eligible_activation_value_delta_rows
    ]
    eligible_delta_key_set = set(eligible_delta_keys)
    duplicate_delta_key_count = len(eligible_delta_keys) - len(eligible_delta_key_set)
    missing_delta_keys = eligible_audit_keys - eligible_delta_key_set
    unexpected_delta_keys = eligible_delta_key_set - written_full_keys
    non_eligible_delta_keys = eligible_delta_key_set - eligible_audit_keys
    not_written_delta_count = sum(
        1
        for row in eligible_activation_value_delta_rows
        if text_value(row.get("matrix_value_effect")) != "written"
    )
    unchanged_delta_count = sum(
        1
        for row in eligible_activation_value_delta_rows
        if text_value(row.get("value_changed")) != "TRUE"
    )
    blank_activated_value_count = sum(
        1
        for row in eligible_activation_value_delta_rows
        if not text_value(row.get("activated_matrix_value"))
    )
    blocking_reasons = _narrow_expected_diff_blockers(
        eligible_delta_row_count=len(eligible_activation_value_delta_rows),
        duplicate_delta_key_count=duplicate_delta_key_count,
        missing_delta_count=len(missing_delta_keys),
        unexpected_delta_count=len(unexpected_delta_keys),
        non_eligible_delta_count=len(non_eligible_delta_keys),
        not_written_delta_count=not_written_delta_count,
        unchanged_delta_count=unchanged_delta_count,
        blank_activated_value_count=blank_activated_value_count,
        no_rows_blocker=no_rows_blocker,
    )
    return {
        "schema_version": schema_version,
        "source_run_id": source_run_id,
        "acceptance_status": "pass" if not blocking_reasons else "fail",
        "expected_scope": expected_scope,
        "activation_value_delta_tsv": str(activation_value_delta_tsv),
        "activation_value_delta_sha256": _file_sha_text(activation_value_delta_tsv),
        "activation_scope_audit_tsv": str(activation_scope_audit_tsv),
        "activation_scope_audit_sha256": _file_sha_text(activation_scope_audit_tsv),
        "eligible_activation_value_delta_tsv": str(eligible_activation_value_delta_tsv),
        "eligible_activation_value_delta_sha256": _file_sha_text(
            eligible_activation_value_delta_tsv,
        ),
        "full_written_delta_row_count": str(len(written_full_keys)),
        "eligible_audit_row_count": str(len(eligible_audit_keys)),
        "eligible_delta_row_count": str(len(eligible_activation_value_delta_rows)),
        "duplicate_delta_key_count": str(duplicate_delta_key_count),
        "missing_delta_row_count": str(len(missing_delta_keys)),
        "unexpected_delta_row_count": str(len(unexpected_delta_keys)),
        "non_eligible_delta_row_count": str(len(non_eligible_delta_keys)),
        "not_written_delta_row_count": str(not_written_delta_count),
        "unchanged_delta_row_count": str(unchanged_delta_count),
        "blank_activated_value_count": str(blank_activated_value_count),
        "blocking_reasons": ";".join(blocking_reasons),
        "product_surface_changed": "FALSE",
        "next_action": (
            product_decision_next_action
            if not blocking_reasons
            else "review_narrow_expected_diff_acceptance_failures"
        ),
    }


def _audit_delta_row(
    row: Mapping[str, str],
    *,
    projection_by_sha: Mapping[str, tuple[Mapping[str, str], ...]],
    trace_cache: dict[Path, tuple[str, dict[str, Any] | None]],
    source_run_id: str,
) -> dict[str, str]:
    source_sha = text_value(row.get("matrix_value_source_row_sha256"))
    matrix_value_effect = text_value(row.get("matrix_value_effect"))
    projections = projection_by_sha.get(source_sha, ())
    base = {
        "schema_version": SCHEMA_VERSION,
        "source_run_id": source_run_id,
        "feature_family_id": text_value(row.get("feature_family_id")),
        "peak_hypothesis_id": text_value(row.get("peak_hypothesis_id")),
        "sample_id": text_value(row.get("sample_id")),
        "matrix_value_effect": matrix_value_effect,
        "source_cell_status": text_value(row.get("source_cell_status")),
        "activated_matrix_value": text_value(row.get("activated_matrix_value")),
        "matrix_value_source_row_sha256": source_sha,
    }
    if matrix_value_effect != "written":
        return _with_projection_trace_defaults(
            base,
            projection_match_status="not_written",
            trace_match_status="not_applicable",
            high_signal_clean_status="not_written",
            blockers=(),
        )
    if not projections:
        return _with_projection_trace_defaults(
            base,
            projection_match_status="missing_projection_row",
            trace_match_status="not_available",
            high_signal_clean_status="missing_evidence",
            blockers=("missing_projection_row",),
        )
    if len(projections) > 1:
        return _with_projection_trace_defaults(
            base,
            projection_match_status="ambiguous_projection_row",
            trace_match_status="not_available",
            high_signal_clean_status="missing_evidence",
            blockers=("ambiguous_projection_row",),
        )
    projection = projections[0]
    out = _with_projection(base, projection, projection_match_status="matched")
    overlay_path = text_value(projection.get("overlay_png_path"))
    if not overlay_path:
        return _with_trace_defaults(
            out,
            trace_match_status="missing_overlay_path",
            high_signal_clean_status="missing_evidence",
            blockers=("missing_overlay_path",),
        )
    trace_path = _trace_json_path_from_overlay_path(Path(overlay_path))
    out["trace_data_path"] = str(trace_path)
    trace_status, trace_data = _load_trace_json(trace_path, trace_cache)
    if trace_status != "loaded" or trace_data is None:
        return _with_trace_defaults(
            out,
            trace_match_status=trace_status,
            high_signal_clean_status="missing_evidence",
            blockers=(trace_status,),
        )
    trace = _trace_for_sample(trace_data, text_value(row.get("sample_id")))
    if trace is None:
        return _with_trace_defaults(
            out,
            trace_match_status="missing_trace_sample",
            high_signal_clean_status="missing_evidence",
            blockers=("missing_trace_sample",),
        )
    return _with_trace_metrics(out, trace, trace_data)


def _delta_key(row: Mapping[str, str]) -> tuple[str, str, str]:
    return (
        text_value(row.get("peak_hypothesis_id")),
        text_value(row.get("sample_id")),
        text_value(row.get("matrix_value_source_row_sha256")),
    )


def _audit_key(row: Mapping[str, str]) -> tuple[str, str, str]:
    return (
        text_value(row.get("peak_hypothesis_id")),
        text_value(row.get("sample_id")),
        text_value(row.get("matrix_value_source_row_sha256")),
    )


def _narrow_expected_diff_blockers(
    *,
    eligible_delta_row_count: int,
    duplicate_delta_key_count: int,
    missing_delta_count: int,
    unexpected_delta_count: int,
    non_eligible_delta_count: int,
    not_written_delta_count: int,
    unchanged_delta_count: int,
    blank_activated_value_count: int,
    no_rows_blocker: str = "no_high_signal_clean_eligible_delta_rows",
) -> tuple[str, ...]:
    blockers: list[str] = []
    if eligible_delta_row_count == 0:
        blockers.append(no_rows_blocker)
    if duplicate_delta_key_count:
        blockers.append("duplicate_eligible_delta_keys")
    if missing_delta_count:
        blockers.append("eligible_audit_rows_missing_from_delta")
    if unexpected_delta_count:
        blockers.append("eligible_delta_rows_missing_from_full_delta")
    if non_eligible_delta_count:
        blockers.append("eligible_delta_contains_noneligible_rows")
    if not_written_delta_count:
        blockers.append("eligible_delta_contains_non_written_rows")
    if unchanged_delta_count:
        blockers.append("eligible_delta_contains_unchanged_rows")
    if blank_activated_value_count:
        blockers.append("eligible_delta_contains_blank_activated_values")
    return tuple(blockers)


def _with_trace_metrics(
    out: dict[str, str],
    trace: Mapping[str, Any],
    trace_data: Mapping[str, Any],
) -> dict[str, str]:
    trace_status = text_value(trace.get("status"))
    cell_start_rt = optional_float(trace.get("cell_start_rt"))
    cell_end_rt = optional_float(trace.get("cell_end_rt"))
    cell_apex_rt = optional_float(trace.get("cell_apex_rt"))
    family_center_rt = optional_float(trace_data.get("family_center_rt"))
    boundary_width = (
        cell_end_rt - cell_start_rt
        if cell_start_rt is not None and cell_end_rt is not None
        else None
    )
    apex_delta = (
        abs(cell_apex_rt - family_center_rt)
        if cell_apex_rt is not None and family_center_rt is not None
        else None
    )
    rt_values = trace.get("rt")
    integration_scan_count = _integration_scan_count(
        rt_values if isinstance(rt_values, list) else (),
        cell_start_rt,
        cell_end_rt,
    )
    shape = optional_float(trace.get("apex_aligned_shape_similarity"))
    local_global = optional_float(trace.get("local_window_to_global_max_ratio"))
    height = optional_float(trace.get("cell_height"))
    blockers = _high_signal_clean_blockers(
        trace_status=trace_status,
        shape=shape,
        local_global=local_global,
        height=height,
        boundary_width=boundary_width,
        apex_delta=apex_delta,
        integration_scan_count=integration_scan_count,
    )
    low_scan_blockers = _low_scan_clean_blockers(
        trace_status=trace_status,
        shape=shape,
        local_global=local_global,
        height=height,
        boundary_width=boundary_width,
        apex_delta=apex_delta,
        integration_scan_count=integration_scan_count,
    )
    low_height_blockers = _low_height_clean_blockers(
        trace_status=trace_status,
        shape=shape,
        local_global=local_global,
        height=height,
        boundary_width=boundary_width,
        apex_delta=apex_delta,
        integration_scan_count=integration_scan_count,
    )
    out.update(
        {
            "trace_match_status": "matched",
            "trace_status": trace_status,
            "cell_area": _metric_text(trace.get("cell_area")),
            "cell_height": _metric_text(height),
            "cell_start_rt": _metric_text(cell_start_rt),
            "cell_end_rt": _metric_text(cell_end_rt),
            "cell_apex_rt": _metric_text(cell_apex_rt),
            "family_center_rt": _metric_text(family_center_rt),
            "boundary_width_min": _metric_text(boundary_width),
            "apex_delta_abs_min": _metric_text(apex_delta),
            "integration_scan_count": ""
            if integration_scan_count is None
            else str(integration_scan_count),
            "apex_aligned_shape_similarity": _metric_text(shape),
            "local_window_to_global_max_ratio": _metric_text(local_global),
            "high_signal_clean_status": "eligible" if not blockers else "ineligible",
            "high_signal_clean_blockers": ";".join(blockers),
            "low_scan_clean_status": (
                "eligible" if not low_scan_blockers else "ineligible"
            ),
            "low_scan_clean_blockers": ";".join(low_scan_blockers),
            "low_height_clean_status": (
                "eligible" if not low_height_blockers else "ineligible"
            ),
            "low_height_clean_blockers": ";".join(low_height_blockers),
        }
    )
    return out


def _high_signal_clean_blockers(
    *,
    trace_status: str,
    shape: float | None,
    local_global: float | None,
    height: float | None,
    boundary_width: float | None,
    apex_delta: float | None,
    integration_scan_count: int | None,
) -> tuple[str, ...]:
    blockers: list[str] = []
    if trace_status not in SUPPORTED_TRACE_STATUSES:
        blockers.append("unsupported_trace_status")
    if shape is None or shape < MIN_SHAPE_SIMILARITY:
        blockers.append("shape_lt_0.95")
    if local_global is None or local_global < MIN_LOCAL_GLOBAL_RATIO:
        blockers.append("local_global_ratio_lt_0.95")
    if height is None or height < MIN_CELL_HEIGHT:
        blockers.append("height_lt_2000000")
    if (
        boundary_width is None
        or boundary_width < MIN_BOUNDARY_WIDTH_MIN
        or boundary_width > MAX_BOUNDARY_WIDTH_MIN
    ):
        blockers.append("width_outside_0.30_0.65")
    if apex_delta is None or apex_delta > MAX_APEX_DELTA_ABS_MIN:
        blockers.append("apex_delta_gt_0.15")
    if (
        integration_scan_count is None
        or integration_scan_count < MIN_INTEGRATION_SCAN_COUNT
    ):
        blockers.append("scan_count_lt_10")
    return tuple(blockers)


def _low_scan_clean_blockers(
    *,
    trace_status: str,
    shape: float | None,
    local_global: float | None,
    height: float | None,
    boundary_width: float | None,
    apex_delta: float | None,
    integration_scan_count: int | None,
) -> tuple[str, ...]:
    blockers = list(
        _clean_except_scan_blockers(
            trace_status=trace_status,
            shape=shape,
            local_global=local_global,
            height=height,
            boundary_width=boundary_width,
            apex_delta=apex_delta,
        )
    )
    if (
        integration_scan_count is None
        or integration_scan_count < MIN_LOW_SCAN_CLEAN_SCAN_COUNT
    ):
        blockers.append("scan_count_lt_7")
    elif integration_scan_count > MAX_LOW_SCAN_CLEAN_SCAN_COUNT:
        blockers.append("scan_count_gt_9")
    return tuple(blockers)


def _low_height_clean_blockers(
    *,
    trace_status: str,
    shape: float | None,
    local_global: float | None,
    height: float | None,
    boundary_width: float | None,
    apex_delta: float | None,
    integration_scan_count: int | None,
) -> tuple[str, ...]:
    blockers = list(
        _clean_except_height_blockers(
            trace_status=trace_status,
            shape=shape,
            local_global=local_global,
            boundary_width=boundary_width,
            apex_delta=apex_delta,
            integration_scan_count=integration_scan_count,
        )
    )
    if height is None:
        blockers.append("height_missing")
    elif height >= MIN_CELL_HEIGHT:
        blockers.append("height_gte_2000000")
    return tuple(blockers)


def _clean_except_height_blockers(
    *,
    trace_status: str,
    shape: float | None,
    local_global: float | None,
    boundary_width: float | None,
    apex_delta: float | None,
    integration_scan_count: int | None,
) -> tuple[str, ...]:
    blockers: list[str] = []
    if trace_status not in SUPPORTED_TRACE_STATUSES:
        blockers.append("unsupported_trace_status")
    if shape is None or shape < MIN_SHAPE_SIMILARITY:
        blockers.append("shape_lt_0.95")
    if local_global is None or local_global < MIN_LOCAL_GLOBAL_RATIO:
        blockers.append("local_global_ratio_lt_0.95")
    if (
        boundary_width is None
        or boundary_width < MIN_BOUNDARY_WIDTH_MIN
        or boundary_width > MAX_BOUNDARY_WIDTH_MIN
    ):
        blockers.append("width_outside_0.30_0.65")
    if apex_delta is None or apex_delta > MAX_APEX_DELTA_ABS_MIN:
        blockers.append("apex_delta_gt_0.15")
    if (
        integration_scan_count is None
        or integration_scan_count < MIN_INTEGRATION_SCAN_COUNT
    ):
        blockers.append("scan_count_lt_10")
    return tuple(blockers)


def _clean_except_scan_blockers(
    *,
    trace_status: str,
    shape: float | None,
    local_global: float | None,
    height: float | None,
    boundary_width: float | None,
    apex_delta: float | None,
) -> tuple[str, ...]:
    blockers: list[str] = []
    if trace_status not in SUPPORTED_TRACE_STATUSES:
        blockers.append("unsupported_trace_status")
    if shape is None or shape < MIN_SHAPE_SIMILARITY:
        blockers.append("shape_lt_0.95")
    if local_global is None or local_global < MIN_LOCAL_GLOBAL_RATIO:
        blockers.append("local_global_ratio_lt_0.95")
    if height is None or height < MIN_CELL_HEIGHT:
        blockers.append("height_lt_2000000")
    if (
        boundary_width is None
        or boundary_width < MIN_BOUNDARY_WIDTH_MIN
        or boundary_width > MAX_BOUNDARY_WIDTH_MIN
    ):
        blockers.append("width_outside_0.30_0.65")
    if apex_delta is None or apex_delta > MAX_APEX_DELTA_ABS_MIN:
        blockers.append("apex_delta_gt_0.15")
    return tuple(blockers)


def _summary_row(
    audit_rows: Sequence[Mapping[str, str]],
    *,
    activation_value_delta_tsv: Path,
    shadow_projection_cells_tsv: Path,
    source_run_id: str,
) -> dict[str, str]:
    written_rows = [
        row
        for row in audit_rows
        if text_value(row.get("matrix_value_effect")) == "written"
    ]
    counters = Counter(
        text_value(row.get("high_signal_clean_status")) for row in written_rows
    )
    low_scan_counters = Counter(
        text_value(row.get("low_scan_clean_status")) for row in written_rows
    )
    low_height_counters = Counter(
        text_value(row.get("low_height_clean_status")) for row in written_rows
    )
    projection_counters = Counter(
        text_value(row.get("projection_match_status")) for row in written_rows
    )
    trace_counters = Counter(
        text_value(row.get("trace_match_status")) for row in written_rows
    )
    written_count = len(written_rows)
    eligible_count = counters["eligible"]
    missing_count = counters["missing_evidence"]
    ineligible_count = counters["ineligible"]
    low_scan_eligible_count = low_scan_counters["eligible"]
    low_scan_missing_count = low_scan_counters["missing_evidence"]
    low_scan_ineligible_count = low_scan_counters["ineligible"]
    low_height_eligible_count = low_height_counters["eligible"]
    low_height_missing_count = low_height_counters["missing_evidence"]
    low_height_ineligible_count = low_height_counters["ineligible"]
    broad_ready = written_count > 0 and eligible_count == written_count
    narrow_ready = eligible_count > 0
    low_scan_ready = low_scan_eligible_count > 0
    low_height_ready = low_height_eligible_count > 0
    return {
        "schema_version": SCHEMA_VERSION,
        "source_run_id": source_run_id,
        "activation_value_delta_tsv": str(activation_value_delta_tsv),
        "activation_value_delta_sha256": _file_sha_text(activation_value_delta_tsv),
        "shadow_projection_cells_tsv": str(shadow_projection_cells_tsv),
        "shadow_projection_cells_sha256": _file_sha_text(shadow_projection_cells_tsv),
        "activation_value_delta_row_count": str(len(audit_rows)),
        "written_activation_row_count": str(written_count),
        "projection_matched_written_count": str(projection_counters["matched"]),
        "projection_missing_written_count": str(
            projection_counters["missing_projection_row"]
        ),
        "projection_ambiguous_written_count": str(
            projection_counters["ambiguous_projection_row"]
        ),
        "trace_matched_written_count": str(trace_counters["matched"]),
        "missing_overlay_path_written_count": str(
            trace_counters["missing_overlay_path"]
        ),
        "missing_trace_json_written_count": str(trace_counters["missing_trace_json"]),
        "missing_trace_sample_written_count": str(
            trace_counters["missing_trace_sample"]
        ),
        "trace_json_parse_error_written_count": str(
            trace_counters["trace_json_parse_error"]
        ),
        "high_signal_clean_eligible_written_count": str(eligible_count),
        "high_signal_clean_ineligible_written_count": str(ineligible_count),
        "high_signal_clean_missing_evidence_written_count": str(missing_count),
        "low_scan_clean_eligible_written_count": str(low_scan_eligible_count),
        "low_scan_clean_ineligible_written_count": str(low_scan_ineligible_count),
        "low_scan_clean_missing_evidence_written_count": str(
            low_scan_missing_count,
        ),
        "low_height_clean_eligible_written_count": str(low_height_eligible_count),
        "low_height_clean_ineligible_written_count": str(
            low_height_ineligible_count,
        ),
        "low_height_clean_missing_evidence_written_count": str(
            low_height_missing_count,
        ),
        "eligible_scope_fraction_of_written": _fraction_text(
            eligible_count,
            written_count,
        ),
        "low_scan_clean_scope_fraction_of_written": _fraction_text(
            low_scan_eligible_count,
            written_count,
        ),
        "low_height_clean_scope_fraction_of_written": _fraction_text(
            low_height_eligible_count,
            written_count,
        ),
        "broad_activation_scope_status": "ready" if broad_ready else "not_ready",
        "narrow_activation_scope_status": (
            "ready_if_product_scope_is_limited_to_eligible_rows"
            if narrow_ready
            else "not_ready"
        ),
        "low_scan_clean_activation_scope_status": (
            "ready_if_product_scope_is_limited_to_low_scan_clean_rows"
            if low_scan_ready
            else "not_ready"
        ),
        "low_height_clean_activation_scope_status": (
            "candidate_only_pending_low_height_heldout_oracle"
            if low_height_ready
            else "not_ready"
        ),
        "remaining_blocker": _remaining_blocker(
            written_count=written_count,
            eligible_count=eligible_count,
            missing_count=missing_count,
            ineligible_count=ineligible_count,
            low_scan_eligible_count=low_scan_eligible_count,
            low_height_eligible_count=low_height_eligible_count,
        ),
        "audit_tsv": "",
        "eligible_activation_value_delta_tsv": "",
        "low_scan_clean_activation_value_delta_tsv": "",
        "low_height_clean_activation_value_delta_tsv": "",
    }


def _remaining_blocker(
    *,
    written_count: int,
    eligible_count: int,
    missing_count: int,
    ineligible_count: int,
    low_scan_eligible_count: int = 0,
    low_height_eligible_count: int = 0,
) -> str:
    if written_count == 0:
        return "no_activation_writes"
    if eligible_count == written_count:
        return ""
    parts: list[str] = []
    if eligible_count:
        parts.append("product_scope_decision_required_for_high_signal_clean_subset")
    if low_scan_eligible_count:
        parts.append("product_scope_decision_required_for_low_scan_clean_subset")
    if low_height_eligible_count:
        parts.append("product_scope_decision_required_for_low_height_clean_subset")
    if missing_count:
        parts.append("missing_trace_or_projection_evidence_for_some_writes")
    if ineligible_count:
        parts.append("current_writes_outside_high_signal_clean_evidence_envelope")
    return ";".join(parts)


def _with_projection(
    base: Mapping[str, str],
    projection: Mapping[str, str],
    *,
    projection_match_status: str,
) -> dict[str, str]:
    out = dict(base)
    out.update(
        {
            "projection_match_status": projection_match_status,
            "projection_feature_family_id": text_value(
                projection.get("feature_family_id"),
            ),
            "projection_sample_stem": text_value(projection.get("sample_stem")),
            "projection_peak_hypothesis_id": text_value(
                projection.get("peak_hypothesis_id")
            ),
            "projection_cell_status": text_value(projection.get("cell_status")),
            "projection_gap_fill_state": text_value(projection.get("gap_fill_state")),
            "projection_local_global_ratio": text_value(
                projection.get("local_global_ratio")
            ),
            "projection_overlay_png_path": text_value(
                projection.get("overlay_png_path"),
            ),
        }
    )
    return _with_trace_defaults(
        out,
        trace_match_status="not_checked",
        high_signal_clean_status="missing_evidence",
        blockers=("trace_not_checked",),
    )


def _with_projection_trace_defaults(
    base: Mapping[str, str],
    *,
    projection_match_status: str,
    trace_match_status: str,
    high_signal_clean_status: str,
    blockers: Sequence[str],
) -> dict[str, str]:
    out = dict(base)
    out.update(
        {
            "projection_match_status": projection_match_status,
            "projection_feature_family_id": "",
            "projection_sample_stem": "",
            "projection_peak_hypothesis_id": "",
            "projection_cell_status": "",
            "projection_gap_fill_state": "",
            "projection_local_global_ratio": "",
            "projection_overlay_png_path": "",
        }
    )
    return _with_trace_defaults(
        out,
        trace_match_status=trace_match_status,
        high_signal_clean_status=high_signal_clean_status,
        blockers=blockers,
    )


def _with_trace_defaults(
    out: Mapping[str, str],
    *,
    trace_match_status: str,
    high_signal_clean_status: str,
    blockers: Sequence[str],
) -> dict[str, str]:
    row = dict(out)
    row.update(
        {
            "trace_data_path": row.get("trace_data_path", ""),
            "trace_match_status": trace_match_status,
            "trace_status": "",
            "cell_area": "",
            "cell_height": "",
            "cell_start_rt": "",
            "cell_end_rt": "",
            "cell_apex_rt": "",
            "family_center_rt": "",
            "boundary_width_min": "",
            "apex_delta_abs_min": "",
            "integration_scan_count": "",
            "apex_aligned_shape_similarity": "",
            "local_window_to_global_max_ratio": "",
            "high_signal_clean_status": high_signal_clean_status,
            "high_signal_clean_blockers": ";".join(blockers),
            "low_scan_clean_status": high_signal_clean_status,
            "low_scan_clean_blockers": ";".join(blockers),
            "low_height_clean_status": high_signal_clean_status,
            "low_height_clean_blockers": ";".join(blockers),
        }
    )
    return row


def _rows_by_sha(
    rows: Sequence[Mapping[str, str]],
    column: str,
) -> dict[str, tuple[Mapping[str, str], ...]]:
    grouped: dict[str, list[Mapping[str, str]]] = {}
    for row in rows:
        key = text_value(row.get(column))
        if key:
            grouped.setdefault(key, []).append(row)
    return {key: tuple(items) for key, items in grouped.items()}


def _trace_json_path_from_overlay_path(path: Path) -> Path:
    return path.with_name(f"{path.stem}_trace_data.json")


def _load_trace_json(
    path: Path,
    cache: dict[Path, tuple[str, dict[str, Any] | None]],
) -> tuple[str, dict[str, Any] | None]:
    if path in cache:
        return cache[path]
    result: tuple[str, dict[str, Any] | None]
    if not path.is_file():
        result = ("missing_trace_json", None)
    else:
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            result = ("trace_json_parse_error", None)
        else:
            result = ("loaded", loaded if isinstance(loaded, dict) else None)
    cache[path] = result
    return result


def _trace_for_sample(
    trace_data: Mapping[str, Any],
    sample_id: str,
) -> Mapping[str, Any] | None:
    traces = trace_data.get("traces")
    if not isinstance(traces, list):
        return None
    for trace in traces:
        if not isinstance(trace, dict):
            continue
        if text_value(trace.get("sample_stem")) == sample_id:
            return trace
    return None


def _integration_scan_count(
    rt_values: Sequence[Any],
    start_rt: float | None,
    end_rt: float | None,
) -> int | None:
    if start_rt is None or end_rt is None:
        return None
    return sum(
        1
        for value in rt_values
        if (parsed := optional_float(value)) is not None
        and start_rt <= parsed <= end_rt
    )


def _metric_text(value: object) -> str:
    parsed = optional_float(value)
    if parsed is None:
        return ""
    return format_diagnostic_value(parsed)


def _fraction_text(numerator: int, denominator: int) -> str:
    if denominator <= 0:
        return ""
    return format_diagnostic_value(numerator / denominator)


def _file_sha_text(path: Path) -> str:
    return file_sha256(path) if path.is_file() else ""
