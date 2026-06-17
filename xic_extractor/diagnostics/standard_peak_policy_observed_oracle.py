"""Build row-specific observed oracle packets for Backfill policy candidates."""

from __future__ import annotations

import json
import math
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from xic_extractor.alignment.matrix_handoff import integration_from_peak_trace
from xic_extractor.diagnostics.diagnostic_io import (
    format_diagnostic_value,
    optional_float,
    text_value,
    write_tsv,
)
from xic_extractor.diagnostics.standard_peak_heldout_trace_oracle import (
    _trace_reintegration_config,
)
from xic_extractor.diagnostics.standard_peak_shadow_activation_inputs import (
    HELDOUT_ORACLE_FLOAT_ABS_TOLERANCE,
    HELDOUT_ORACLE_MAX_AREA_RELATIVE_ERROR,
    HELDOUT_ORACLE_MAX_BOUNDARY_DELTA_MIN,
)
from xic_extractor.signal_processing import find_peak_and_area
from xic_extractor.tabular_io import file_sha256, read_tsv_required

SCHEMA_VERSION = "standard_peak_policy_observed_oracle_v1"
SUMMARY_SCHEMA_VERSION = "standard_peak_policy_observed_oracle_summary_v1"
POLICY_SCHEMA_VERSION = "standard_peak_backfill_policy_v2"
ACTIVATION_SCOPE_AUDIT_SCHEMA_VERSION = "standard_peak_activation_scope_audit_v1"
DEFAULT_POLICY_DECISION = "detected_flagged"
OBSERVED_REINTEGRATION_MODE = "full_trace"

POLICY_REQUIRED_COLUMNS = (
    "schema_version",
    "feature_family_id",
    "peak_hypothesis_id",
    "sample_id",
    "matrix_value_effect",
    "matrix_value_source_row_sha256",
    "backfill_policy_decision",
    "backfill_policy_candidate_evidence_class",
)

ACTIVATION_SCOPE_AUDIT_REQUIRED_COLUMNS = (
    "schema_version",
    "feature_family_id",
    "peak_hypothesis_id",
    "sample_id",
    "matrix_value_effect",
    "source_cell_status",
    "matrix_value_source_row_sha256",
    "trace_data_path",
    "trace_match_status",
    "trace_status",
    "cell_area",
    "cell_height",
    "cell_start_rt",
    "cell_end_rt",
    "cell_apex_rt",
)

RESULT_COLUMNS = (
    "schema_version",
    "source_run_id",
    "oracle_case_id",
    "feature_family_id",
    "peak_hypothesis_id",
    "sample_id",
    "matrix_value_source_row_sha256",
    "policy_decision",
    "policy_candidate_evidence_class",
    "source_cell_status",
    "trace_match_status",
    "trace_status",
    "trace_data_path",
    "trace_data_sha256",
    "source_start_rt",
    "source_end_rt",
    "source_area",
    "observed_start_rt",
    "observed_end_rt",
    "observed_area",
    "observed_result_source",
    "observed_boundary_source",
    "observed_area_source",
    "observed_independence_basis",
    "boundary_error_min",
    "area_relative_error",
    "oracle_case_status",
    "inconclusive_reason",
    "included_in_product_acceptance",
)

SUMMARY_COLUMNS = (
    "schema_version",
    "source_run_id",
    "status",
    "observed_reintegration_mode",
    "source_backfill_policy_tsv",
    "source_backfill_policy_sha256",
    "source_activation_scope_audit_tsv",
    "source_activation_scope_audit_sha256",
    "candidate_policy_decision",
    "candidate_policy_row_count",
    "oracle_case_status_pass_count",
    "oracle_case_status_fail_boundary_count",
    "oracle_case_status_fail_area_count",
    "oracle_case_status_inconclusive_count",
    "included_in_product_acceptance_count",
    "max_boundary_error_min",
    "max_area_relative_error",
    "boundary_error_min_max_allowed",
    "area_relative_error_max_allowed",
    "policy_observed_oracle_tsv",
    "policy_observed_oracle_sha256",
    "next_action",
)


@dataclass(frozen=True)
class PolicyObservedOracleOutputs:
    summary_tsv: Path
    summary_json: Path
    results_tsv: Path
    status: str


def run_policy_observed_oracle(
    *,
    backfill_policy_tsv: Path,
    activation_scope_audit_tsv: Path,
    output_dir: Path,
    source_run_id: str,
    candidate_policy_decision: str = DEFAULT_POLICY_DECISION,
) -> PolicyObservedOracleOutputs:
    policy_rows = read_tsv_required(backfill_policy_tsv, POLICY_REQUIRED_COLUMNS)
    _validate_schema_versions(
        policy_rows,
        expected=POLICY_SCHEMA_VERSION,
        path=backfill_policy_tsv,
    )
    source_rows = read_tsv_required(
        activation_scope_audit_tsv,
        ACTIVATION_SCOPE_AUDIT_REQUIRED_COLUMNS,
    )
    _validate_schema_versions(
        source_rows,
        expected=ACTIVATION_SCOPE_AUDIT_SCHEMA_VERSION,
        path=activation_scope_audit_tsv,
    )
    source_by_sha = _source_rows_by_sha(source_rows)
    candidate_rows = tuple(
        row
        for row in policy_rows
        if text_value(row.get("backfill_policy_decision")) == candidate_policy_decision
    )
    result_rows = tuple(
        _observed_oracle_row(
            policy_row,
            source_row=source_by_sha.get(
                text_value(policy_row.get("matrix_value_source_row_sha256")),
            ),
            source_run_id=source_run_id,
            row_index=index,
        )
        for index, policy_row in enumerate(candidate_rows, start=1)
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    results_tsv = output_dir / "standard_peak_policy_observed_oracle.tsv"
    summary_tsv = output_dir / "summary.tsv"
    summary_json = output_dir / "summary.json"
    write_tsv(
        results_tsv,
        result_rows,
        RESULT_COLUMNS,
        formatter=format_diagnostic_value,
        lineterminator="\n",
    )
    summary = _summary_row(
        result_rows,
        source_run_id=source_run_id,
        backfill_policy_tsv=backfill_policy_tsv,
        activation_scope_audit_tsv=activation_scope_audit_tsv,
        candidate_policy_decision=candidate_policy_decision,
        results_tsv=results_tsv,
    )
    write_tsv(
        summary_tsv,
        [summary],
        SUMMARY_COLUMNS,
        formatter=format_diagnostic_value,
        lineterminator="\n",
    )
    summary_json.write_text(
        json.dumps(summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return PolicyObservedOracleOutputs(
        summary_tsv=summary_tsv,
        summary_json=summary_json,
        results_tsv=results_tsv,
        status=summary["status"],
    )


def _observed_oracle_row(
    policy_row: Mapping[str, str],
    *,
    source_row: Mapping[str, str] | None,
    source_run_id: str,
    row_index: int,
) -> dict[str, str]:
    base = _base_result_row(policy_row, source_row, source_run_id, row_index)
    if source_row is None:
        return {
            **base,
            "oracle_case_status": "inconclusive_review_only",
            "inconclusive_reason": "missing_activation_scope_row",
            "included_in_product_acceptance": "FALSE",
        }
    trace_match_status = text_value(source_row.get("trace_match_status"))
    if trace_match_status != "matched":
        return {
            **base,
            "oracle_case_status": "inconclusive_review_only",
            "inconclusive_reason": f"trace_match_status:{trace_match_status}",
            "included_in_product_acceptance": "FALSE",
        }
    if text_value(policy_row.get("matrix_value_effect")) != "written":
        return {
            **base,
            "oracle_case_status": "inconclusive_review_only",
            "inconclusive_reason": "policy_matrix_value_effect_not_written",
            "included_in_product_acceptance": "FALSE",
        }
    if text_value(source_row.get("matrix_value_effect")) != "written":
        return {
            **base,
            "oracle_case_status": "inconclusive_review_only",
            "inconclusive_reason": "source_matrix_value_effect_not_written",
            "included_in_product_acceptance": "FALSE",
        }
    source_area = optional_float(source_row.get("cell_area"))
    source_start = optional_float(source_row.get("cell_start_rt"))
    source_end = optional_float(source_row.get("cell_end_rt"))
    if (
        source_area is None
        or source_area <= 0.0
        or source_start is None
        or source_end is None
    ):
        return {
            **base,
            "oracle_case_status": "inconclusive_review_only",
            "inconclusive_reason": "invalid_source_boundary_or_area",
            "included_in_product_acceptance": "FALSE",
        }
    trace_path = Path(text_value(source_row.get("trace_data_path")))
    if not trace_path.is_file():
        return {
            **base,
            "oracle_case_status": "inconclusive_review_only",
            "inconclusive_reason": "missing_trace_data_path",
            "included_in_product_acceptance": "FALSE",
        }
    trace = _trace_for_sample(trace_path, text_value(source_row.get("sample_id")))
    if trace is None:
        return {
            **base,
            "trace_data_sha256": file_sha256(trace_path),
            "oracle_case_status": "inconclusive_review_only",
            "inconclusive_reason": "sample_trace_missing",
            "included_in_product_acceptance": "FALSE",
        }
    observed = _reintegrate_trace(trace)
    if observed is None:
        return {
            **base,
            "trace_data_sha256": file_sha256(trace_path),
            "oracle_case_status": "inconclusive_review_only",
            "inconclusive_reason": "observed_peak_missing",
            "included_in_product_acceptance": "FALSE",
        }
    observed_start, observed_end, observed_area = observed
    boundary_error = abs(observed_start - source_start) + abs(observed_end - source_end)
    area_relative_error = abs(observed_area - source_area) / abs(source_area)
    status = "pass"
    if _exceeds_tolerance(boundary_error, HELDOUT_ORACLE_MAX_BOUNDARY_DELTA_MIN):
        status = "fail_boundary"
    elif _exceeds_tolerance(
        area_relative_error,
        HELDOUT_ORACLE_MAX_AREA_RELATIVE_ERROR,
    ):
        status = "fail_area"
    return {
        **base,
        "trace_data_sha256": file_sha256(trace_path),
        "observed_start_rt": _float_text(observed_start),
        "observed_end_rt": _float_text(observed_end),
        "observed_area": _float_text(observed_area),
        "observed_result_source": "policy_observed_full_trace_reintegration_v1",
        "observed_boundary_source": "find_peak_and_area_full_stored_trace_arrays",
        "observed_area_source": (
            "integration_from_peak_trace_gaussian15_positive_asls_residual"
        ),
        "observed_independence_basis": "independent_boundary_reintegration_result",
        "boundary_error_min": _float_text(boundary_error),
        "area_relative_error": _float_text(area_relative_error),
        "oracle_case_status": status,
        "inconclusive_reason": "",
        "included_in_product_acceptance": "TRUE" if status == "pass" else "FALSE",
    }


def _base_result_row(
    policy_row: Mapping[str, str],
    source_row: Mapping[str, str] | None,
    source_run_id: str,
    row_index: int,
) -> dict[str, str]:
    source = source_row or {}
    family = text_value(policy_row.get("feature_family_id"))
    sample = text_value(policy_row.get("sample_id"))
    return {
        "schema_version": SCHEMA_VERSION,
        "source_run_id": source_run_id,
        "oracle_case_id": _case_id(row_index, family, sample),
        "feature_family_id": family,
        "peak_hypothesis_id": text_value(policy_row.get("peak_hypothesis_id")),
        "sample_id": sample,
        "matrix_value_source_row_sha256": text_value(
            policy_row.get("matrix_value_source_row_sha256"),
        ),
        "policy_decision": text_value(policy_row.get("backfill_policy_decision")),
        "policy_candidate_evidence_class": text_value(
            policy_row.get("backfill_policy_candidate_evidence_class"),
        ),
        "source_cell_status": text_value(source.get("source_cell_status")),
        "trace_match_status": text_value(source.get("trace_match_status")),
        "trace_status": text_value(source.get("trace_status")),
        "trace_data_path": text_value(source.get("trace_data_path")),
        "trace_data_sha256": "",
        "source_start_rt": text_value(source.get("cell_start_rt")),
        "source_end_rt": text_value(source.get("cell_end_rt")),
        "source_area": text_value(source.get("cell_area")),
        "observed_start_rt": "",
        "observed_end_rt": "",
        "observed_area": "",
        "observed_result_source": "",
        "observed_boundary_source": "",
        "observed_area_source": "",
        "observed_independence_basis": "",
        "boundary_error_min": "",
        "area_relative_error": "",
        "oracle_case_status": "",
        "inconclusive_reason": "",
        "included_in_product_acceptance": "FALSE",
    }


def _source_rows_by_sha(
    source_rows: Sequence[Mapping[str, str]],
) -> dict[str, Mapping[str, str]]:
    shas = tuple(
        text_value(row.get("matrix_value_source_row_sha256"))
        for row in source_rows
    )
    duplicates = sorted(
        sha for sha, count in Counter(shas).items() if sha and count > 1
    )
    if duplicates:
        raise ValueError(
            "activation scope audit has duplicate matrix_value_source_row_sha256 "
            f"values: {';'.join(duplicates[:10])}",
        )
    return {
        text_value(row.get("matrix_value_source_row_sha256")): row
        for row in source_rows
    }


def _trace_for_sample(trace_path: Path, sample_id: str) -> Mapping[str, Any] | None:
    data = json.loads(trace_path.read_text(encoding="utf-8"))
    traces = data.get("traces")
    if not isinstance(traces, list):
        return None
    for trace in traces:
        if (
            isinstance(trace, Mapping)
            and text_value(trace.get("sample_stem")) == sample_id
        ):
            return trace
    return None


def _reintegrate_trace(trace: Mapping[str, Any]) -> tuple[float, float, float] | None:
    rt = _float_array(trace.get("rt"))
    intensity = _float_array(trace.get("intensity"))
    if rt.size == 0 or rt.size != intensity.size:
        return None
    result = find_peak_and_area(rt, intensity, _trace_reintegration_config())
    if result.peak is None:
        return None
    integration = integration_from_peak_trace(
        result.peak,
        rt,
        intensity,
        boundary_sources=("local_minimum",),
        integration_method="raw_trapezoid",
        baseline_integration_method="asls",
    )
    observed_area = (
        integration.area_ms1_morphology
        if integration is not None and integration.area_ms1_morphology is not None
        else result.peak.area
    )
    return result.peak.peak_start, result.peak.peak_end, observed_area


def _summary_row(
    result_rows: Sequence[Mapping[str, str]],
    *,
    source_run_id: str,
    backfill_policy_tsv: Path,
    activation_scope_audit_tsv: Path,
    candidate_policy_decision: str,
    results_tsv: Path,
) -> dict[str, str]:
    status_counts = Counter(row["oracle_case_status"] for row in result_rows)
    pass_count = status_counts.get("pass", 0)
    fail_boundary_count = status_counts.get("fail_boundary", 0)
    fail_area_count = status_counts.get("fail_area", 0)
    inconclusive_count = sum(
        count
        for status, count in status_counts.items()
        if status.startswith("inconclusive")
    )
    included_count = sum(
        1 for row in result_rows if row["included_in_product_acceptance"] == "TRUE"
    )
    boundary_errors = tuple(
        value
        for row in result_rows
        if (value := optional_float(row.get("boundary_error_min"))) is not None
    )
    area_errors = tuple(
        value
        for row in result_rows
        if (value := optional_float(row.get("area_relative_error"))) is not None
    )
    status = (
        "pass"
        if result_rows
        and pass_count == len(result_rows)
        and included_count == len(result_rows)
        else "fail"
    )
    return {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "source_run_id": source_run_id,
        "status": status,
        "observed_reintegration_mode": OBSERVED_REINTEGRATION_MODE,
        "source_backfill_policy_tsv": str(backfill_policy_tsv),
        "source_backfill_policy_sha256": file_sha256(backfill_policy_tsv),
        "source_activation_scope_audit_tsv": str(activation_scope_audit_tsv),
        "source_activation_scope_audit_sha256": file_sha256(activation_scope_audit_tsv),
        "candidate_policy_decision": candidate_policy_decision,
        "candidate_policy_row_count": str(len(result_rows)),
        "oracle_case_status_pass_count": str(pass_count),
        "oracle_case_status_fail_boundary_count": str(fail_boundary_count),
        "oracle_case_status_fail_area_count": str(fail_area_count),
        "oracle_case_status_inconclusive_count": str(inconclusive_count),
        "included_in_product_acceptance_count": str(included_count),
        "max_boundary_error_min": _float_text(
            max(boundary_errors) if boundary_errors else None,
        ),
        "max_area_relative_error": _float_text(
            max(area_errors) if area_errors else None,
        ),
        "boundary_error_min_max_allowed": _float_text(
            HELDOUT_ORACLE_MAX_BOUNDARY_DELTA_MIN,
        ),
        "area_relative_error_max_allowed": _float_text(
            HELDOUT_ORACLE_MAX_AREA_RELATIVE_ERROR,
        ),
        "policy_observed_oracle_tsv": str(results_tsv),
        "policy_observed_oracle_sha256": file_sha256(results_tsv),
        "next_action": (
            "eligible_for_policy_evidence_class_expected_diff_gate"
            if status == "pass"
            else "review_policy_observed_oracle_failures"
        ),
    }


def _validate_schema_versions(
    rows: Sequence[Mapping[str, str]],
    *,
    expected: str,
    path: Path,
) -> None:
    unexpected = sorted(
        {text_value(row.get("schema_version")) for row in rows}
        - {expected},
    )
    if unexpected:
        raise ValueError(
            f"{path}: expected schema_version {expected}; "
            f"found {', '.join(unexpected)}",
        )


def _float_array(value: object) -> np.ndarray:
    if not isinstance(value, list):
        return np.asarray((), dtype=float)
    try:
        return np.asarray([float(item) for item in value], dtype=float)
    except (TypeError, ValueError):
        return np.asarray((), dtype=float)


def _case_id(index: int, family: str, sample: str) -> str:
    safe_family = "".join(ch if ch.isalnum() else "_" for ch in family) or "family"
    safe_sample = "".join(ch if ch.isalnum() else "_" for ch in sample) or "sample"
    return f"POLICYOBS{index:03d}_{safe_family}_{safe_sample}"


def _float_text(value: float | None) -> str:
    if value is None or math.isnan(value) or math.isinf(value):
        return ""
    return f"{value:.6g}"


def _exceeds_tolerance(value: float, tolerance: float) -> bool:
    return value > tolerance + HELDOUT_ORACLE_FLOAT_ABS_TOLERANCE
