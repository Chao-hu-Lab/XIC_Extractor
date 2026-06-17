"""Audit standard-peak reintegration stability from stored trace artifacts."""

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
from xic_extractor.config import ExtractionConfig
from xic_extractor.diagnostics.diagnostic_io import (
    file_sha256,
    format_diagnostic_value,
    optional_float,
    read_tsv_required,
    text_value,
    write_tsv,
)
from xic_extractor.signal_processing import find_peak_and_area

SCHEMA_VERSION = "standard_peak_reintegration_stability_audit_v1"
ACTIVATION_SCOPE_AUDIT_SCHEMA_VERSION = "standard_peak_activation_scope_audit_v1"
BOUNDARY_TOLERANCE_MIN = 0.1
AREA_RELATIVE_TOLERANCE = 0.1
DEFAULT_EXPECTED_WINDOW_PADDING_MIN = 0.5
MAX_EXPECTED_WINDOW_PADDING_MIN = 0.5

ACTIVATION_SCOPE_AUDIT_REQUIRED_COLUMNS = (
    "schema_version",
    "source_run_id",
    "feature_family_id",
    "sample_id",
    "matrix_value_effect",
    "matrix_value_source_row_sha256",
    "trace_match_status",
    "trace_status",
    "cell_area",
    "cell_start_rt",
    "cell_end_rt",
    "cell_apex_rt",
    "trace_data_path",
)

STABILITY_AUDIT_COLUMNS = (
    "schema_version",
    "source_run_id",
    "feature_family_id",
    "sample_id",
    "matrix_value_source_row_sha256",
    "matrix_value_effect",
    "trace_match_status",
    "trace_status",
    "trace_data_path",
    "stability_status",
    "stability_blockers",
    "reference_start_rt",
    "reference_end_rt",
    "reference_apex_rt",
    "reference_area",
    "full_trace_start_rt",
    "full_trace_end_rt",
    "full_trace_area",
    "bounded_window_start_rt",
    "bounded_window_end_rt",
    "bounded_window_area",
    "full_trace_boundary_error_min",
    "full_trace_area_relative_error",
    "bounded_window_boundary_error_min",
    "bounded_window_area_relative_error",
    "method_boundary_disagreement_min",
    "method_area_relative_disagreement",
    "expected_window_padding_min",
)

SUMMARY_COLUMNS = (
    "schema_version",
    "source_run_id",
    "status",
    "readiness_label",
    "writer_authority_status",
    "production_ready",
    "product_surface_changed",
    "matrix_contract_changed",
    "source_activation_scope_audit_tsv",
    "source_activation_scope_audit_sha256",
    "source_activation_scope_schema_version",
    "source_activation_scope_source_run_ids",
    "activation_scope_audit_row_count",
    "written_row_count",
    "eligible_written_count",
    "ineligible_written_count",
    "missing_evidence_written_count",
    "not_applicable_row_count",
    "expected_window_padding_min",
    "boundary_tolerance_min",
    "area_relative_tolerance",
    "reintegration_stability_audit_tsv",
    "remaining_blocker",
    "next_action",
)


@dataclass(frozen=True)
class ReintegrationStabilityAuditOutputs:
    audit_tsv: Path
    summary_tsv: Path
    summary_json: Path
    status: str
    audit_columns: tuple[str, ...] = STABILITY_AUDIT_COLUMNS


@dataclass(frozen=True)
class _ReferenceCell:
    start_rt: float
    end_rt: float
    apex_rt: float
    area: float


@dataclass(frozen=True)
class _ObservedIntegration:
    start_rt: float
    end_rt: float
    area: float


def audit_reintegration_stability(
    *,
    activation_scope_audit_tsv: Path,
    output_dir: Path,
    source_run_id: str,
    expected_window_padding_min: float = DEFAULT_EXPECTED_WINDOW_PADDING_MIN,
    max_rows: int | None = None,
) -> ReintegrationStabilityAuditOutputs:
    """Write a no-RAW reintegration-stability audit for standard-peak writes."""

    _validate_expected_window_padding(expected_window_padding_min)
    if max_rows is not None and max_rows <= 0:
        raise ValueError("max_rows must be positive when provided")

    source_rows = read_tsv_required(
        activation_scope_audit_tsv,
        ACTIVATION_SCOPE_AUDIT_REQUIRED_COLUMNS,
    )
    _validate_activation_scope_audit_rows(source_rows, activation_scope_audit_tsv)
    rows_to_process = source_rows[:max_rows] if max_rows is not None else source_rows

    output_dir.mkdir(parents=True, exist_ok=True)
    audit_tsv = output_dir / "reintegration_stability_audit.tsv"
    summary_tsv = output_dir / "reintegration_stability_summary.tsv"
    summary_json = output_dir / "reintegration_stability_summary.json"

    audit_rows = tuple(
        _audit_row(
            row,
            source_run_id=source_run_id,
            expected_window_padding_min=expected_window_padding_min,
        )
        for row in rows_to_process
    )
    summary = _summary_row(
        audit_rows=audit_rows,
        activation_scope_audit_tsv=activation_scope_audit_tsv,
        source_activation_scope_source_run_ids=_source_run_ids(source_rows),
        source_run_id=source_run_id,
        expected_window_padding_min=expected_window_padding_min,
        audit_tsv=audit_tsv,
        source_row_count=len(source_rows),
    )

    write_tsv(
        audit_tsv,
        audit_rows,
        STABILITY_AUDIT_COLUMNS,
        formatter=format_diagnostic_value,
        lineterminator="\n",
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
    return ReintegrationStabilityAuditOutputs(
        audit_tsv=audit_tsv,
        summary_tsv=summary_tsv,
        summary_json=summary_json,
        status=summary["status"],
    )


def _audit_row(
    row: Mapping[str, str],
    *,
    source_run_id: str,
    expected_window_padding_min: float,
) -> dict[str, str]:
    base = {
        "schema_version": SCHEMA_VERSION,
        "source_run_id": source_run_id,
        "feature_family_id": text_value(row.get("feature_family_id")),
        "sample_id": text_value(row.get("sample_id")),
        "matrix_value_source_row_sha256": text_value(
            row.get("matrix_value_source_row_sha256"),
        ),
        "matrix_value_effect": text_value(row.get("matrix_value_effect")),
        "trace_match_status": text_value(row.get("trace_match_status")),
        "trace_status": text_value(row.get("trace_status")),
        "trace_data_path": text_value(row.get("trace_data_path")),
        "expected_window_padding_min": _float_text(expected_window_padding_min),
    }
    blanks = _blank_metric_fields()
    if base["matrix_value_effect"] != "written":
        return {
            **base,
            **blanks,
            "stability_status": "not_applicable",
            "stability_blockers": "not_written",
        }
    if base["trace_match_status"] != "matched":
        return {
            **base,
            **blanks,
            "stability_status": "missing_evidence",
            "stability_blockers": "trace_not_matched",
        }
    reference = _reference_cell(row)
    if reference is None:
        return {
            **base,
            **blanks,
            "stability_status": "missing_evidence",
            "stability_blockers": "reference_cell_missing",
        }
    trace = _trace_for_row(
        Path(base["trace_data_path"]),
        sample_id=base["sample_id"],
    )
    if trace is None:
        return {
            **base,
            **_reference_fields(reference),
            **_blank_observed_fields(),
            "stability_status": "missing_evidence",
            "stability_blockers": "trace_json_missing_or_sample_absent",
            "expected_window_padding_min": base["expected_window_padding_min"],
        }
    rt = _float_array(trace.get("rt"))
    intensity = _float_array(trace.get("intensity"))
    if rt is None or intensity is None or len(rt) != len(intensity):
        return {
            **base,
            **_reference_fields(reference),
            **_blank_observed_fields(),
            "stability_status": "missing_evidence",
            "stability_blockers": "trace_arrays_invalid",
            "expected_window_padding_min": base["expected_window_padding_min"],
        }

    full = _reintegrate(rt, intensity)
    bounded = _bounded_reintegrate(
        rt,
        intensity,
        reference,
        expected_window_padding_min=expected_window_padding_min,
    )
    blockers = _stability_blockers(full, bounded, reference)
    return {
        **base,
        **_reference_fields(reference),
        **_observed_fields(full, prefix="full_trace"),
        **_observed_fields(bounded, prefix="bounded_window"),
        **_agreement_fields(full, bounded, reference),
        "stability_status": "eligible" if not blockers else "ineligible",
        "stability_blockers": ";".join(blockers),
    }


def _reference_cell(row: Mapping[str, str]) -> _ReferenceCell | None:
    start = optional_float(row.get("cell_start_rt"))
    end = optional_float(row.get("cell_end_rt"))
    apex = optional_float(row.get("cell_apex_rt"))
    area = optional_float(row.get("cell_area"))
    if (
        start is None
        or end is None
        or apex is None
        or area is None
        or end <= start
        or area <= 0.0
    ):
        return None
    return _ReferenceCell(start_rt=start, end_rt=end, apex_rt=apex, area=area)


def _trace_for_row(trace_path: Path, *, sample_id: str) -> Mapping[str, Any] | None:
    if not trace_path.exists():
        return None
    try:
        data = json.loads(trace_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    traces = data.get("traces") if isinstance(data, Mapping) else None
    if not isinstance(traces, list):
        return None
    for trace in traces:
        if (
            isinstance(trace, Mapping)
            and text_value(trace.get("sample_stem")) == sample_id
        ):
            return trace
    return None


def _reintegrate(
    rt: np.ndarray,
    intensity: np.ndarray,
    *,
    preferred_rt: float | None = None,
    strict_preferred_rt: bool = False,
) -> _ObservedIntegration | None:
    if rt.size == 0 or intensity.size == 0:
        return None
    result = find_peak_and_area(
        rt,
        intensity,
        _trace_reintegration_config(),
        preferred_rt=preferred_rt,
        strict_preferred_rt=strict_preferred_rt,
    )
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
    area = (
        integration.area_ms1_morphology
        if integration is not None and integration.area_ms1_morphology is not None
        else result.peak.area
    )
    if area is None or area <= 0.0:
        return None
    return _ObservedIntegration(
        start_rt=result.peak.peak_start,
        end_rt=result.peak.peak_end,
        area=area,
    )


def _bounded_reintegrate(
    rt: np.ndarray,
    intensity: np.ndarray,
    reference: _ReferenceCell,
    *,
    expected_window_padding_min: float,
) -> _ObservedIntegration | None:
    lower = reference.start_rt - expected_window_padding_min
    upper = reference.end_rt + expected_window_padding_min
    mask = (rt >= lower) & (rt <= upper)
    return _reintegrate(
        rt[mask],
        intensity[mask],
        preferred_rt=reference.apex_rt,
        strict_preferred_rt=True,
    )


def _stability_blockers(
    full: _ObservedIntegration | None,
    bounded: _ObservedIntegration | None,
    reference: _ReferenceCell,
) -> tuple[str, ...]:
    blockers: list[str] = []
    if full is None:
        blockers.append("full_trace_missing_peak")
    else:
        if _boundary_error(full, reference) > BOUNDARY_TOLERANCE_MIN:
            blockers.append("full_trace_boundary_error_gt_0.1")
        if _area_error(full.area, reference.area) > AREA_RELATIVE_TOLERANCE:
            blockers.append("full_trace_area_error_gt_0.1")
    if bounded is None:
        blockers.append("bounded_window_missing_peak")
    else:
        if _boundary_error(bounded, reference) > BOUNDARY_TOLERANCE_MIN:
            blockers.append("bounded_window_boundary_error_gt_0.1")
        if _area_error(bounded.area, reference.area) > AREA_RELATIVE_TOLERANCE:
            blockers.append("bounded_window_area_error_gt_0.1")
    if full is not None and bounded is not None:
        if _method_boundary_delta(full, bounded) > BOUNDARY_TOLERANCE_MIN:
            blockers.append("method_boundary_disagreement_gt_0.1")
        if _area_error(full.area, bounded.area) > AREA_RELATIVE_TOLERANCE:
            blockers.append("method_area_disagreement_gt_0.1")
    return tuple(blockers)


def _summary_row(
    *,
    audit_rows: Sequence[Mapping[str, str]],
    activation_scope_audit_tsv: Path,
    source_activation_scope_source_run_ids: Sequence[str],
    source_run_id: str,
    expected_window_padding_min: float,
    audit_tsv: Path,
    source_row_count: int,
) -> dict[str, str]:
    counters = Counter(text_value(row.get("stability_status")) for row in audit_rows)
    written_count = sum(
        1
        for row in audit_rows
        if text_value(row.get("matrix_value_effect")) == "written"
    )
    eligible_count = counters["eligible"]
    status = "candidate_pool_blocked" if eligible_count else "inconclusive"
    return {
        "schema_version": SCHEMA_VERSION,
        "source_run_id": source_run_id,
        "status": status,
        "readiness_label": (
            "production_candidate" if eligible_count else "diagnostic_only"
        ),
        "writer_authority_status": "blocked",
        "production_ready": "FALSE",
        "product_surface_changed": "FALSE",
        "matrix_contract_changed": "FALSE",
        "source_activation_scope_audit_tsv": str(activation_scope_audit_tsv),
        "source_activation_scope_audit_sha256": file_sha256(
            activation_scope_audit_tsv,
        ),
        "source_activation_scope_schema_version": ACTIVATION_SCOPE_AUDIT_SCHEMA_VERSION,
        "source_activation_scope_source_run_ids": ";".join(
            source_activation_scope_source_run_ids,
        ),
        "activation_scope_audit_row_count": str(source_row_count),
        "written_row_count": str(written_count),
        "eligible_written_count": str(eligible_count),
        "ineligible_written_count": str(counters["ineligible"]),
        "missing_evidence_written_count": str(counters["missing_evidence"]),
        "not_applicable_row_count": str(counters["not_applicable"]),
        "expected_window_padding_min": _float_text(expected_window_padding_min),
        "boundary_tolerance_min": _float_text(BOUNDARY_TOLERANCE_MIN),
        "area_relative_tolerance": _float_text(AREA_RELATIVE_TOLERANCE),
        "reintegration_stability_audit_tsv": str(audit_tsv),
        "remaining_blocker": (
            "masked_product_writer_oracle_required_before_activation"
            if eligible_count
            else "no_boundary_stable_candidate_rows"
        ),
        "next_action": (
            "design_masked_product_writer_oracle_before_activation"
            if eligible_count
            else "revise_boundary_stability_evidence_class"
        ),
    }


def _source_run_ids(rows: Sequence[Mapping[str, str]]) -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                text_value(row.get("source_run_id"))
                for row in rows
                if text_value(row.get("source_run_id"))
            },
        ),
    )


def _validate_expected_window_padding(expected_window_padding_min: float) -> None:
    if not math.isfinite(expected_window_padding_min):
        raise ValueError("expected_window_padding_min must be finite")
    if expected_window_padding_min < 0.0:
        raise ValueError("expected_window_padding_min must be non-negative")
    if expected_window_padding_min > MAX_EXPECTED_WINDOW_PADDING_MIN:
        raise ValueError(
            "expected_window_padding_min must be <= "
            f"{MAX_EXPECTED_WINDOW_PADDING_MIN:g}",
        )


def _validate_activation_scope_audit_rows(
    rows: Sequence[Mapping[str, str]],
    path: Path,
) -> None:
    unexpected_versions = sorted(
        {
            text_value(row.get("schema_version"))
            for row in rows
            if text_value(row.get("schema_version"))
            != ACTIVATION_SCOPE_AUDIT_SCHEMA_VERSION
        },
    )
    if unexpected_versions:
        found = ", ".join(unexpected_versions)
        raise ValueError(
            f"{path}: expected schema_version "
            f"{ACTIVATION_SCOPE_AUDIT_SCHEMA_VERSION}; found {found}",
        )
    if rows and any(not text_value(row.get("source_run_id")) for row in rows):
        raise ValueError(f"{path}: source_run_id must be non-empty on all rows")


def _blank_metric_fields() -> dict[str, str]:
    return {
        **{
            "reference_start_rt": "",
            "reference_end_rt": "",
            "reference_apex_rt": "",
            "reference_area": "",
        },
        **_blank_observed_fields(),
    }


def _blank_observed_fields() -> dict[str, str]:
    return {
        "full_trace_start_rt": "",
        "full_trace_end_rt": "",
        "full_trace_area": "",
        "bounded_window_start_rt": "",
        "bounded_window_end_rt": "",
        "bounded_window_area": "",
        "full_trace_boundary_error_min": "",
        "full_trace_area_relative_error": "",
        "bounded_window_boundary_error_min": "",
        "bounded_window_area_relative_error": "",
        "method_boundary_disagreement_min": "",
        "method_area_relative_disagreement": "",
    }


def _reference_fields(reference: _ReferenceCell) -> dict[str, str]:
    return {
        "reference_start_rt": _float_text(reference.start_rt),
        "reference_end_rt": _float_text(reference.end_rt),
        "reference_apex_rt": _float_text(reference.apex_rt),
        "reference_area": _float_text(reference.area),
    }


def _observed_fields(
    observed: _ObservedIntegration | None,
    *,
    prefix: str,
) -> dict[str, str]:
    if observed is None:
        return {
            f"{prefix}_start_rt": "",
            f"{prefix}_end_rt": "",
            f"{prefix}_area": "",
        }
    return {
        f"{prefix}_start_rt": _float_text(observed.start_rt),
        f"{prefix}_end_rt": _float_text(observed.end_rt),
        f"{prefix}_area": _float_text(observed.area),
    }


def _agreement_fields(
    full: _ObservedIntegration | None,
    bounded: _ObservedIntegration | None,
    reference: _ReferenceCell,
) -> dict[str, str]:
    return {
        "full_trace_boundary_error_min": _optional_float_text(
            _boundary_error(full, reference) if full is not None else None,
        ),
        "full_trace_area_relative_error": _optional_float_text(
            _area_error(full.area, reference.area) if full is not None else None,
        ),
        "bounded_window_boundary_error_min": _optional_float_text(
            _boundary_error(bounded, reference) if bounded is not None else None,
        ),
        "bounded_window_area_relative_error": _optional_float_text(
            _area_error(bounded.area, reference.area) if bounded is not None else None,
        ),
        "method_boundary_disagreement_min": _optional_float_text(
            _method_boundary_delta(full, bounded)
            if full is not None and bounded is not None
            else None,
        ),
        "method_area_relative_disagreement": _optional_float_text(
            _area_error(full.area, bounded.area)
            if full is not None and bounded is not None
            else None,
        ),
    }


def _boundary_error(
    observed: _ObservedIntegration,
    reference: _ReferenceCell,
) -> float:
    return max(
        abs(observed.start_rt - reference.start_rt),
        abs(observed.end_rt - reference.end_rt),
    )


def _method_boundary_delta(
    left: _ObservedIntegration,
    right: _ObservedIntegration,
) -> float:
    return max(
        abs(left.start_rt - right.start_rt),
        abs(left.end_rt - right.end_rt),
    )


def _area_error(observed_area: float, reference_area: float) -> float:
    if reference_area <= 0.0:
        return math.inf
    return abs(observed_area - reference_area) / reference_area


def _float_array(value: object) -> np.ndarray | None:
    if not isinstance(value, list):
        return None
    parsed: list[float] = []
    for item in value:
        parsed_item = optional_float(item)
        if parsed_item is None:
            return None
        parsed.append(parsed_item)
    return np.asarray(parsed, dtype=float)


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


def _float_text(value: float) -> str:
    if math.isinf(value):
        return "inf"
    return format_diagnostic_value(value)


def _optional_float_text(value: float | None) -> str:
    return "" if value is None else _float_text(value)
