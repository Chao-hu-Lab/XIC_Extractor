"""Build held-out trace reintegration oracle packets for standard peaks."""

from __future__ import annotations

import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from xic_extractor.alignment.matrix_handoff import integration_from_peak_trace
from xic_extractor.config import ExtractionConfig
from xic_extractor.diagnostics.diagnostic_io import (
    format_diagnostic_value,
    optional_float,
    text_value,
    write_tsv,
)
from xic_extractor.diagnostics.standard_peak_shadow_activation_inputs import (
    HELDOUT_ORACLE_MANIFEST_REQUIRED_COLUMNS,
    HELDOUT_ORACLE_MANIFEST_SCHEMA_VERSION,
    HELDOUT_ORACLE_OBSERVED_REQUIRED_COLUMNS,
    build_heldout_oracle_results,
    write_heldout_oracle_results,
)
from xic_extractor.signal_processing import find_peak_and_area
from xic_extractor.tabular_io import read_tsv_required

SCHEMA_VERSION = "standard_peak_heldout_trace_oracle_v1"

HIGH_SIGNAL_CLEAN_SCOPE = "standard_high_signal_clean_trace"
LOW_SCAN_CLEAN_SCOPE = "standard_low_scan_clean_trace"
LOW_HEIGHT_CLEAN_SCOPE = "standard_low_height_clean_trace"
APEX_DELTA_CLEAN_SCOPE = "standard_apex_delta_clean_trace"
WIDTH_CLEAN_SCOPE = "standard_width_clean_trace"
SUPPORTED_TARGET_SHAPE_CLASSES = (
    HIGH_SIGNAL_CLEAN_SCOPE,
    LOW_SCAN_CLEAN_SCOPE,
    LOW_HEIGHT_CLEAN_SCOPE,
    APEX_DELTA_CLEAN_SCOPE,
    WIDTH_CLEAN_SCOPE,
)

MIN_SHAPE_SIMILARITY = 0.95
MIN_LOCAL_GLOBAL_RATIO = 0.95
MIN_CELL_HEIGHT = 2_000_000.0
MIN_BOUNDARY_WIDTH_MIN = 0.30
MAX_BOUNDARY_WIDTH_MIN = 0.65
MAX_APEX_DELTA_ABS_MIN = 0.15
MIN_HIGH_SIGNAL_SCAN_COUNT = 10
MIN_LOW_SCAN_COUNT = 7
MAX_LOW_SCAN_COUNT = 9

CANDIDATE_COLUMNS = (
    "oracle_case_id",
    "target_shape_class",
    "feature_family_id",
    "sample_stem",
    "trace_path",
    "quality_score",
    "shape_similarity",
    "local_window_to_global_max_ratio",
    "cell_height",
    "oracle_width_min",
    "oracle_scan_count",
    "apex_delta_from_family_center_min",
    "zero_fraction",
    "oracle_area",
    "observed_boundary_error_min",
    "observed_area_relative_error",
)

FULL_POOL_COLUMNS = (
    "overall_quality_rank",
    "selected_case_rank",
    "selected_for_oracle",
    "selection_reason",
    *CANDIDATE_COLUMNS[:-2],
)

SUMMARY_COLUMNS = (
    "schema_version",
    "source_run_id",
    "target_shape_class",
    "status",
    "readiness_scope",
    "source_alignment_backfill_cell_evidence_tsv",
    "source_trace_root",
    "available_candidate_rows",
    "available_candidate_families",
    "selected_case_count",
    "selected_family_count",
    "oracle_case_status_pass_count",
    "oracle_case_status_fail_count",
    "included_in_product_acceptance_count",
    "max_observed_boundary_error_min",
    "max_observed_area_relative_error",
    "boundary_error_min_max_allowed",
    "area_relative_error_max_allowed",
    "non_claim",
    "heldout_trace_reintegration_candidates_tsv",
    "heldout_trace_reintegration_full_eligible_pool_tsv",
    "heldout_oracle_manifest_tsv",
    "heldout_observed_results_tsv",
    "heldout_oracle_results_tsv",
    "next_action",
)

BACKFILL_EVIDENCE_REQUIRED_COLUMNS = (
    "feature_family_id",
    "sample_stem",
    "status",
    "production_cell_status",
    "write_matrix_value",
    "include_in_primary_matrix",
    "primary_matrix_area",
    "primary_matrix_area_source",
    "peak_start_rt",
    "peak_end_rt",
    "reason",
)


@dataclass(frozen=True)
class HeldoutTraceOracleOutputs:
    summary_tsv: Path
    summary_json: Path
    candidates_tsv: Path
    full_eligible_pool_tsv: Path
    manifest_tsv: Path
    observed_results_tsv: Path
    oracle_results_tsv: Path
    status: str


@dataclass(frozen=True)
class _TraceCandidate:
    target_shape_class: str
    feature_family_id: str
    sample_stem: str
    trace_path: Path
    quality_score: float
    shape_similarity: float
    local_global_ratio: float
    cell_height: float
    oracle_start_rt: float
    oracle_end_rt: float
    oracle_apex_rt: float
    family_center_rt: float
    oracle_width_min: float
    oracle_scan_count: int
    apex_delta_from_family_center_min: float
    zero_fraction: float
    oracle_area: float
    rt: tuple[float, ...]
    intensity: tuple[float, ...]


def run_heldout_trace_oracle(
    *,
    alignment_backfill_cell_evidence_tsv: Path,
    trace_root: Path,
    output_dir: Path,
    source_run_id: str,
    target_shape_class: str = HIGH_SIGNAL_CLEAN_SCOPE,
    max_cases: int = 20,
    max_cases_per_family: int = 1,
) -> HeldoutTraceOracleOutputs:
    """Build deterministic held-out trace oracle artifacts without opening RAW."""

    if target_shape_class not in SUPPORTED_TARGET_SHAPE_CLASSES:
        allowed = ", ".join(SUPPORTED_TARGET_SHAPE_CLASSES)
        raise ValueError(
            f"unsupported target_shape_class {target_shape_class!r}; "
            f"must be one of {allowed}",
        )
    if max_cases <= 0:
        raise ValueError("max_cases must be positive")
    if max_cases_per_family <= 0:
        raise ValueError("max_cases_per_family must be positive")

    output_dir.mkdir(parents=True, exist_ok=True)
    candidates_tsv = output_dir / "heldout_trace_reintegration_candidates.tsv"
    full_pool_tsv = output_dir / "heldout_trace_reintegration_full_eligible_pool.tsv"
    manifest_tsv = output_dir / "heldout_oracle_manifest.tsv"
    observed_tsv = output_dir / "heldout_observed_results.tsv"
    oracle_results_tsv = output_dir / "heldout_oracle_results.tsv"
    summary_tsv = output_dir / "summary.tsv"
    summary_json = output_dir / "summary.json"

    candidate_rows = _candidate_evidence_rows(alignment_backfill_cell_evidence_tsv)
    candidates = _discover_trace_candidates(
        candidate_rows,
        trace_root=trace_root,
        target_shape_class=target_shape_class,
    )
    selected = _select_candidates(
        candidates,
        max_cases=max_cases,
        max_cases_per_family=max_cases_per_family,
    )
    manifest_rows = _manifest_rows(
        selected,
        source_run_id=source_run_id,
        target_shape_class=target_shape_class,
    )
    observed_rows, observed_errors_by_case = _observed_rows(selected)
    write_tsv(
        observed_tsv,
        observed_rows,
        HELDOUT_ORACLE_OBSERVED_REQUIRED_COLUMNS,
        formatter=format_diagnostic_value,
        lineterminator="\n",
    )
    oracle_result_rows = build_heldout_oracle_results(
        manifest_rows,
        observed_rows,
        result_source_artifact_path=observed_tsv,
    )
    write_tsv(
        manifest_tsv,
        manifest_rows,
        HELDOUT_ORACLE_MANIFEST_REQUIRED_COLUMNS,
        formatter=format_diagnostic_value,
        lineterminator="\n",
    )
    write_heldout_oracle_results(oracle_results_tsv, oracle_result_rows)
    write_tsv(
        candidates_tsv,
        _candidate_output_rows(selected, observed_errors_by_case),
        CANDIDATE_COLUMNS,
        formatter=format_diagnostic_value,
        lineterminator="\n",
    )
    write_tsv(
        full_pool_tsv,
        _full_pool_rows(
            candidates,
            selected,
            max_cases=max_cases,
            max_cases_per_family=max_cases_per_family,
        ),
        FULL_POOL_COLUMNS,
        formatter=format_diagnostic_value,
        lineterminator="\n",
    )

    summary = _summary_row(
        source_run_id=source_run_id,
        target_shape_class=target_shape_class,
        alignment_backfill_cell_evidence_tsv=alignment_backfill_cell_evidence_tsv,
        trace_root=trace_root,
        candidates=candidates,
        selected=selected,
        oracle_result_rows=oracle_result_rows,
        observed_errors_by_case=observed_errors_by_case,
        candidates_tsv=candidates_tsv,
        full_pool_tsv=full_pool_tsv,
        manifest_tsv=manifest_tsv,
        observed_tsv=observed_tsv,
        oracle_results_tsv=oracle_results_tsv,
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
    return HeldoutTraceOracleOutputs(
        summary_tsv=summary_tsv,
        summary_json=summary_json,
        candidates_tsv=candidates_tsv,
        full_eligible_pool_tsv=full_pool_tsv,
        manifest_tsv=manifest_tsv,
        observed_results_tsv=observed_tsv,
        oracle_results_tsv=oracle_results_tsv,
        status=summary["status"],
    )


def _candidate_evidence_rows(
    alignment_backfill_cell_evidence_tsv: Path,
) -> dict[tuple[str, str], Mapping[str, str]]:
    rows = read_tsv_required(
        alignment_backfill_cell_evidence_tsv,
        BACKFILL_EVIDENCE_REQUIRED_COLUMNS,
    )
    candidates: dict[tuple[str, str], Mapping[str, str]] = {}
    for row in rows:
        if not _is_detected_oracle_source_row(row):
            continue
        key = (
            text_value(row.get("feature_family_id")),
            text_value(row.get("sample_stem")),
        )
        candidates.setdefault(key, row)
    return candidates


def _is_detected_oracle_source_row(row: Mapping[str, str]) -> bool:
    reason = text_value(row.get("reason"))
    return (
        text_value(row.get("status")) == "detected"
        and text_value(row.get("production_cell_status")) == "detected"
        and text_value(row.get("write_matrix_value")).upper() == "TRUE"
        and text_value(row.get("include_in_primary_matrix")).upper() == "TRUE"
        and text_value(row.get("primary_matrix_area_source"))
        == "gaussian15_positive_asls_residual"
        and "sample-local MS1 owner with original MS2 evidence" in reason
        and _positive_float(row.get("primary_matrix_area")) is not None
    )


def _discover_trace_candidates(
    evidence_rows_by_key: Mapping[tuple[str, str], Mapping[str, str]],
    *,
    trace_root: Path,
    target_shape_class: str,
) -> tuple[_TraceCandidate, ...]:
    if not trace_root.is_dir():
        raise ValueError(
            f"trace_root does not exist or is not a directory: {trace_root}",
        )
    candidates: list[_TraceCandidate] = []
    for trace_path in sorted(trace_root.rglob("*_trace_data.json")):
        trace_data = _read_trace_data(trace_path)
        family_id = text_value(trace_data.get("family_id"))
        family_center_rt = optional_float(trace_data.get("family_center_rt"))
        if not family_id or family_center_rt is None:
            continue
        traces = trace_data.get("traces")
        if not isinstance(traces, list):
            continue
        for trace in traces:
            if not isinstance(trace, Mapping):
                continue
            sample = text_value(trace.get("sample_stem"))
            evidence = evidence_rows_by_key.get((family_id, sample))
            if evidence is None:
                continue
            candidate = _candidate_from_trace(
                trace,
                evidence_row=evidence,
                target_shape_class=target_shape_class,
                trace_path=trace_path,
                family_id=family_id,
                family_center_rt=family_center_rt,
            )
            if candidate is not None:
                candidates.append(candidate)
    return tuple(sorted(candidates, key=_candidate_sort_key))


def _candidate_from_trace(
    trace: Mapping[str, Any],
    *,
    evidence_row: Mapping[str, str],
    target_shape_class: str,
    trace_path: Path,
    family_id: str,
    family_center_rt: float,
) -> _TraceCandidate | None:
    if text_value(trace.get("status")) != "detected":
        return None
    sample = text_value(trace.get("sample_stem"))
    shape = optional_float(trace.get("apex_aligned_shape_similarity"))
    local_global = optional_float(trace.get("local_window_to_global_max_ratio"))
    height = optional_float(trace.get("cell_height"))
    start = optional_float(trace.get("cell_start_rt"))
    end = optional_float(trace.get("cell_end_rt"))
    apex = optional_float(trace.get("cell_apex_rt"))
    oracle_area = _positive_float(evidence_row.get("primary_matrix_area"))
    rt_values = _float_tuple(trace.get("rt"))
    intensity_values = _float_tuple(trace.get("intensity"))
    if (
        not sample
        or shape is None
        or local_global is None
        or height is None
        or start is None
        or end is None
        or apex is None
        or oracle_area is None
        or not rt_values
        or len(rt_values) != len(intensity_values)
    ):
        return None
    width = end - start
    if width <= 0.0:
        return None
    scan_count = _integration_scan_count(rt_values, start, end)
    apex_delta = abs(apex - family_center_rt)
    if not _target_shape_class_matches(
        target_shape_class,
        shape=shape,
        local_global=local_global,
        height=height,
        width=width,
        apex_delta=apex_delta,
        scan_count=scan_count,
    ):
        return None
    zero_fraction = _zero_fraction(intensity_values)
    return _TraceCandidate(
        target_shape_class=target_shape_class,
        feature_family_id=family_id,
        sample_stem=sample,
        trace_path=trace_path,
        quality_score=_quality_score(
            shape=shape,
            local_global=local_global,
            height=height,
            width=width,
            apex_delta=apex_delta,
            scan_count=scan_count,
            zero_fraction=zero_fraction,
        ),
        shape_similarity=shape,
        local_global_ratio=local_global,
        cell_height=height,
        oracle_start_rt=start,
        oracle_end_rt=end,
        oracle_apex_rt=apex,
        family_center_rt=family_center_rt,
        oracle_width_min=width,
        oracle_scan_count=scan_count,
        apex_delta_from_family_center_min=apex_delta,
        zero_fraction=zero_fraction,
        oracle_area=oracle_area,
        rt=rt_values,
        intensity=intensity_values,
    )


def _target_shape_class_matches(
    target_shape_class: str,
    *,
    shape: float,
    local_global: float,
    height: float,
    width: float,
    apex_delta: float,
    scan_count: int,
) -> bool:
    clean_except_scan = (
        shape >= MIN_SHAPE_SIMILARITY
        and local_global >= MIN_LOCAL_GLOBAL_RATIO
        and height >= MIN_CELL_HEIGHT
        and MIN_BOUNDARY_WIDTH_MIN <= width <= MAX_BOUNDARY_WIDTH_MIN
        and apex_delta <= MAX_APEX_DELTA_ABS_MIN
    )
    if target_shape_class == HIGH_SIGNAL_CLEAN_SCOPE:
        return clean_except_scan and scan_count >= MIN_HIGH_SIGNAL_SCAN_COUNT
    if target_shape_class == LOW_SCAN_CLEAN_SCOPE:
        return (
            clean_except_scan
            and MIN_LOW_SCAN_COUNT <= scan_count <= MAX_LOW_SCAN_COUNT
        )
    if target_shape_class == LOW_HEIGHT_CLEAN_SCOPE:
        clean_except_height = (
            shape >= MIN_SHAPE_SIMILARITY
            and local_global >= MIN_LOCAL_GLOBAL_RATIO
            and MIN_BOUNDARY_WIDTH_MIN <= width <= MAX_BOUNDARY_WIDTH_MIN
            and apex_delta <= MAX_APEX_DELTA_ABS_MIN
            and scan_count >= MIN_HIGH_SIGNAL_SCAN_COUNT
        )
        return clean_except_height and height < MIN_CELL_HEIGHT
    if target_shape_class == APEX_DELTA_CLEAN_SCOPE:
        clean_except_apex_delta = (
            shape >= MIN_SHAPE_SIMILARITY
            and local_global >= MIN_LOCAL_GLOBAL_RATIO
            and height >= MIN_CELL_HEIGHT
            and MIN_BOUNDARY_WIDTH_MIN <= width <= MAX_BOUNDARY_WIDTH_MIN
            and scan_count >= MIN_HIGH_SIGNAL_SCAN_COUNT
        )
        return clean_except_apex_delta and apex_delta > MAX_APEX_DELTA_ABS_MIN
    if target_shape_class == WIDTH_CLEAN_SCOPE:
        clean_except_width = (
            shape >= MIN_SHAPE_SIMILARITY
            and local_global >= MIN_LOCAL_GLOBAL_RATIO
            and height >= MIN_CELL_HEIGHT
            and apex_delta <= MAX_APEX_DELTA_ABS_MIN
            and scan_count >= MIN_HIGH_SIGNAL_SCAN_COUNT
        )
        return clean_except_width and not (
            MIN_BOUNDARY_WIDTH_MIN <= width <= MAX_BOUNDARY_WIDTH_MIN
        )
    return False


def _select_candidates(
    candidates: Sequence[_TraceCandidate],
    *,
    max_cases: int,
    max_cases_per_family: int,
) -> tuple[_TraceCandidate, ...]:
    selected: list[_TraceCandidate] = []
    per_family: dict[str, int] = {}
    for candidate in candidates:
        if len(selected) >= max_cases:
            break
        family_count = per_family.get(candidate.feature_family_id, 0)
        if family_count >= max_cases_per_family:
            continue
        selected.append(candidate)
        per_family[candidate.feature_family_id] = family_count + 1
    return tuple(selected)


def _manifest_rows(
    candidates: Sequence[_TraceCandidate],
    *,
    source_run_id: str,
    target_shape_class: str,
) -> tuple[dict[str, str], ...]:
    return tuple(
        {
            "schema_version": HELDOUT_ORACLE_MANIFEST_SCHEMA_VERSION,
            "oracle_case_id": _oracle_case_id(index, candidate),
            "source_run_id": source_run_id,
            "mask_strategy": (
                "original_detected_cell_masked_from_seed_support_trace_reintegration"
            ),
            "masked_sample": candidate.sample_stem,
            "heldout_original_cell_status": "detected",
            "feature_family_id": candidate.feature_family_id,
            "peak_hypothesis_id": candidate.feature_family_id,
            "target_shape_class": target_shape_class,
            "oracle_source": (
                "85raw_alignment_backfill_cell_evidence_primary_matrix_area"
            ),
            "oracle_start_rt": _float_text(candidate.oracle_start_rt),
            "oracle_end_rt": _float_text(candidate.oracle_end_rt),
            "oracle_area": _float_text(candidate.oracle_area),
            "baseline_model_set": "local_minimum_asls_gaussian15_trace_reintegration",
            "baseline_epsilon": "",
            "baseline_residual_threshold": "",
            "acceptable_boundary_delta_min": "0.1",
            "acceptable_area_relative_error": "0.1",
            "expected_seed_guard_status": "sample_local_detected_heldout",
            "expected_integration_pathology": "none",
            "expected_matrix_write_allowed": "TRUE",
        }
        for index, candidate in enumerate(candidates, start=1)
    )


def _observed_rows(
    candidates: Sequence[_TraceCandidate],
) -> tuple[tuple[dict[str, str], ...], dict[str, tuple[float, float]]]:
    rows: list[dict[str, str]] = []
    errors_by_case: dict[str, tuple[float, float]] = {}
    config = _trace_reintegration_config()
    for index, candidate in enumerate(candidates, start=1):
        case_id = _oracle_case_id(index, candidate)
        rt = np.asarray(candidate.rt, dtype=float)
        intensity = np.asarray(candidate.intensity, dtype=float)
        result = find_peak_and_area(rt, intensity, config)
        if result.peak is None:
            continue
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
        boundary_error = max(
            abs(result.peak.peak_start - candidate.oracle_start_rt),
            abs(result.peak.peak_end - candidate.oracle_end_rt),
        )
        area_error = (
            abs(observed_area - candidate.oracle_area) / candidate.oracle_area
            if candidate.oracle_area > 0.0
            else math.inf
        )
        errors_by_case[case_id] = (boundary_error, area_error)
        rows.append(
            {
                "oracle_case_id": case_id,
                "observed_start_rt": _float_text(result.peak.peak_start),
                "observed_end_rt": _float_text(result.peak.peak_end),
                "observed_area": _float_text(observed_area),
                "observed_result_source": (
                    "heldout_trace_reintegration_local_minimum_v1"
                ),
                "observed_boundary_source": (
                    "find_peak_and_area_local_minimum_stored_trace_arrays"
                ),
                "observed_area_source": (
                    "integration_from_peak_trace_gaussian15_positive_asls_residual"
                ),
                "observed_independence_basis": (
                    "independent_boundary_reintegration_result"
                ),
            }
        )
    return tuple(rows), errors_by_case


def _candidate_output_rows(
    candidates: Sequence[_TraceCandidate],
    observed_errors_by_case: Mapping[str, tuple[float, float]],
) -> tuple[dict[str, str], ...]:
    rows: list[dict[str, str]] = []
    for index, candidate in enumerate(candidates, start=1):
        case_id = _oracle_case_id(index, candidate)
        boundary_error, area_error = observed_errors_by_case.get(
            case_id,
            (math.inf, math.inf),
        )
        rows.append(
            {
                **_candidate_base_row(candidate, case_id=case_id),
                "observed_boundary_error_min": _float_text(boundary_error),
                "observed_area_relative_error": _float_text(area_error),
            }
        )
    return tuple(rows)


def _full_pool_rows(
    candidates: Sequence[_TraceCandidate],
    selected: Sequence[_TraceCandidate],
    *,
    max_cases: int,
    max_cases_per_family: int,
) -> tuple[dict[str, str], ...]:
    selected_index = {
        candidate: index for index, candidate in enumerate(selected, start=1)
    }
    selected_family_counts: dict[str, int] = {}
    for candidate in selected:
        selected_family_counts[candidate.feature_family_id] = (
            selected_family_counts.get(candidate.feature_family_id, 0) + 1
        )
    rows: list[dict[str, str]] = []
    for overall_index, candidate in enumerate(candidates, start=1):
        selected_rank = selected_index.get(candidate)
        selected_flag = selected_rank is not None
        reason = "not_selected"
        case_id = ""
        if selected_flag and selected_rank is not None:
            reason = "selected_top_ranked_case_for_family"
            case_id = _oracle_case_id(selected_rank, candidate)
        elif (
            selected_family_counts.get(candidate.feature_family_id, 0)
            >= max_cases_per_family
        ):
            reason = "rejected_lower_ranked_same_family"
        elif len(selected) >= max_cases:
            reason = "rejected_after_max_cases"
        rows.append(
            {
                "overall_quality_rank": str(overall_index),
                "selected_case_rank": ""
                if selected_rank is None
                else str(selected_rank),
                "selected_for_oracle": "TRUE" if selected_flag else "FALSE",
                "selection_reason": reason,
                **_candidate_base_row(candidate, case_id=case_id),
            }
        )
    return tuple(rows)


def _candidate_base_row(
    candidate: _TraceCandidate,
    *,
    case_id: str,
) -> dict[str, str]:
    return {
        "oracle_case_id": case_id,
        "target_shape_class": candidate.target_shape_class,
        "feature_family_id": candidate.feature_family_id,
        "sample_stem": candidate.sample_stem,
        "trace_path": str(candidate.trace_path),
        "quality_score": _float_text(candidate.quality_score),
        "shape_similarity": _float_text(candidate.shape_similarity),
        "local_window_to_global_max_ratio": _float_text(candidate.local_global_ratio),
        "cell_height": _float_text(candidate.cell_height),
        "oracle_width_min": _float_text(candidate.oracle_width_min),
        "oracle_scan_count": str(candidate.oracle_scan_count),
        "apex_delta_from_family_center_min": _float_text(
            candidate.apex_delta_from_family_center_min,
        ),
        "zero_fraction": _float_text(candidate.zero_fraction),
        "oracle_area": _float_text(candidate.oracle_area),
    }


def _summary_row(
    *,
    source_run_id: str,
    target_shape_class: str,
    alignment_backfill_cell_evidence_tsv: Path,
    trace_root: Path,
    candidates: Sequence[_TraceCandidate],
    selected: Sequence[_TraceCandidate],
    oracle_result_rows: Sequence[Mapping[str, str]],
    observed_errors_by_case: Mapping[str, tuple[float, float]],
    candidates_tsv: Path,
    full_pool_tsv: Path,
    manifest_tsv: Path,
    observed_tsv: Path,
    oracle_results_tsv: Path,
) -> dict[str, str]:
    pass_count = sum(
        1
        for row in oracle_result_rows
        if text_value(row.get("oracle_case_status")) == "pass"
    )
    fail_count = sum(
        1
        for row in oracle_result_rows
        if text_value(row.get("oracle_case_status")) != "pass"
    )
    included_count = sum(
        1
        for row in oracle_result_rows
        if text_value(row.get("included_in_product_acceptance")) == "TRUE"
    )
    boundary_errors = tuple(value[0] for value in observed_errors_by_case.values())
    area_errors = tuple(value[1] for value in observed_errors_by_case.values())
    status = (
        "pass"
        if selected and fail_count == 0 and included_count == len(selected)
        else "fail"
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "source_run_id": source_run_id,
        "target_shape_class": target_shape_class,
        "status": status,
        "readiness_scope": f"{target_shape_class}_heldout_oracle",
        "source_alignment_backfill_cell_evidence_tsv": str(
            alignment_backfill_cell_evidence_tsv,
        ),
        "source_trace_root": str(trace_root),
        "available_candidate_rows": str(len(candidates)),
        "available_candidate_families": str(
            len({candidate.feature_family_id for candidate in candidates}),
        ),
        "selected_case_count": str(len(selected)),
        "selected_family_count": str(
            len({candidate.feature_family_id for candidate in selected}),
        ),
        "oracle_case_status_pass_count": str(pass_count),
        "oracle_case_status_fail_count": str(fail_count),
        "included_in_product_acceptance_count": str(included_count),
        "max_observed_boundary_error_min": _float_text(
            max(boundary_errors, default=math.inf),
        ),
        "max_observed_area_relative_error": _float_text(
            max(area_errors, default=math.inf),
        ),
        "boundary_error_min_max_allowed": "0.1",
        "area_relative_error_max_allowed": "0.1",
        "non_claim": (
            "Does not mutate matrices, authorize non-standard peaks, or broaden "
            "the Backfill product writer by itself."
        ),
        "heldout_trace_reintegration_candidates_tsv": str(candidates_tsv),
        "heldout_trace_reintegration_full_eligible_pool_tsv": str(full_pool_tsv),
        "heldout_oracle_manifest_tsv": str(manifest_tsv),
        "heldout_observed_results_tsv": str(observed_tsv),
        "heldout_oracle_results_tsv": str(oracle_results_tsv),
        "next_action": (
            "connect_passing_scope_to_activation_scope_audit_and_expected_diff"
            if status == "pass"
            else "review_heldout_trace_oracle_failures"
        ),
    }


def _read_trace_data(trace_path: Path) -> Mapping[str, Any]:
    try:
        data = json.loads(trace_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid trace JSON: {trace_path}") from exc
    if not isinstance(data, Mapping):
        raise ValueError(f"trace JSON root must be an object: {trace_path}")
    return data


def _trace_reintegration_config() -> ExtractionConfig:
    return ExtractionConfig(
        data_dir=Path("."),
        dll_dir=Path("."),
        output_csv=Path("unused.csv"),
        diagnostics_csv=Path("unused_diagnostics.csv"),
        smooth_window=15,
        smooth_polyorder=3,
        peak_rel_height=0.05,
        peak_min_prominence_ratio=0.0,
        ms2_precursor_tol_da=0.5,
        nl_min_intensity_ratio=0.0,
        resolver_mode="local_minimum",
        resolver_min_search_range_min=0.08,
        resolver_min_relative_height=0.02,
        resolver_min_ratio_top_edge=1.7,
        resolver_peak_duration_max=2.0,
        baseline_integration_method="asls",
    )


def _oracle_case_id(index: int, candidate: _TraceCandidate) -> str:
    sample = candidate.sample_stem.replace(" ", "_")
    return f"HOLDOUT85TRACE{index:03d}_{candidate.feature_family_id}_{sample}"


def _candidate_sort_key(candidate: _TraceCandidate) -> tuple[float, str, str, str]:
    return (
        -candidate.quality_score,
        candidate.feature_family_id,
        candidate.sample_stem,
        str(candidate.trace_path),
    )


def _quality_score(
    *,
    shape: float,
    local_global: float,
    height: float,
    width: float,
    apex_delta: float,
    scan_count: int,
    zero_fraction: float,
) -> float:
    height_score = min(math.log10(max(height, 1.0)), 9.0) / 9.0
    width_center_delta = abs(width - 0.45)
    scan_score = min(scan_count, 20) / 20.0
    return (
        shape * 4.0
        + local_global * 2.0
        + height_score
        + scan_score
        - apex_delta
        - width_center_delta
        - zero_fraction * 0.25
    )


def _integration_scan_count(
    rt_values: Sequence[float],
    start_rt: float,
    end_rt: float,
) -> int:
    return sum(1 for rt in rt_values if start_rt <= rt <= end_rt)


def _zero_fraction(values: Sequence[float]) -> float:
    if not values:
        return 1.0
    return sum(1 for value in values if value <= 0.0) / len(values)


def _positive_float(value: object) -> float | None:
    parsed = optional_float(value)
    if parsed is None or parsed <= 0.0:
        return None
    return parsed


def _float_tuple(value: object) -> tuple[float, ...]:
    if not isinstance(value, list):
        return ()
    parsed: list[float] = []
    for item in value:
        parsed_item = optional_float(item)
        if parsed_item is None:
            return ()
        parsed.append(parsed_item)
    return tuple(parsed)


def _float_text(value: float) -> str:
    if math.isinf(value):
        return "inf"
    return format_diagnostic_value(value)
