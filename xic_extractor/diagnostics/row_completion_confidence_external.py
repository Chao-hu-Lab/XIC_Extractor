"""Schema-only pregate for the external row-completion reviewer lane."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from xic_extractor.tabular_io import read_tsv_with_header

_REQUIRED_COLUMNS = (
    "external_tool",
    "external_run_id",
    "external_tool_version",
    "external_adapter_version",
    "sample_id",
    "feature_id",
    "mz",
    "rt",
    "area_or_intensity",
    "area_or_intensity_semantics",
    "mz_tolerance_unit",
    "rt_tolerance_unit",
    "duplicate_feature_policy",
    "missing_value_policy",
)


@dataclass(frozen=True)
class ExternalPregateResult:
    status: str
    mapping_status: str
    reason: str
    missing_evidence_code: str
    row_count: int


def validate_external_feature_table(path: Path | None) -> ExternalPregateResult:
    if path is None:
        return ExternalPregateResult(
            status="not_available",
            mapping_status="not_available",
            reason="external feature table path not provided",
            missing_evidence_code="missing_required_artifact",
            row_count=0,
        )

    try:
        _header, rows = read_tsv_with_header(
            path,
            required_columns=_REQUIRED_COLUMNS,
            encoding="utf-8-sig",
        )
    except FileNotFoundError as exc:
        return ExternalPregateResult(
            status="FAIL",
            mapping_status="FAIL",
            reason=str(exc),
            missing_evidence_code="missing_required_artifact",
            row_count=0,
        )
    except ValueError as exc:
        return ExternalPregateResult(
            status="FAIL",
            mapping_status="FAIL",
            reason=str(exc),
            missing_evidence_code="missing_required_column",
            row_count=0,
        )

    return ExternalPregateResult(
        status="schema_valid",
        mapping_status="schema_valid_mapping_quality_unavailable",
        reason=(
            "external feature table schema validated; "
            "mapping quality unavailable in version 1"
        ),
        missing_evidence_code="",
        row_count=len(rows),
    )
