from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from xic_extractor.discovery.models import (
    DISCOVERY_CANDIDATE_COLUMNS,
    DiscoveryCandidate,
    GroupPrecursorMzBasis,
    NeutralLossErrorBasis,
)

_BATCH_REQUIRED_COLUMNS = ("sample_stem", "raw_file", "candidate_csv")
_BATCH_UNESCAPE_FIELDS = {"sample_stem", "raw_file", "candidate_csv", "review_csv"}
_CANDIDATE_UNESCAPE_FIELDS = {
    "sample_stem",
    "raw_file",
    "candidate_id",
    "feature_family_id",
    "feature_superfamily_id",
}

_INT_FIELDS = {
    "evidence_score",
    "feature_family_size",
    "feature_superfamily_size",
    "seed_event_count",
    "best_ms2_scan_id",
    "selected_tag_count",
    "matched_tag_count",
}
_FLOAT_FIELDS = {
    "precursor_mz",
    "product_mz",
    "observed_neutral_loss_da",
    "best_seed_rt",
    "ms1_apex_rt",
    "ms1_area",
    "ms2_product_max_intensity",
    "configured_neutral_loss_da",
    "neutral_loss_mass_error_ppm",
    "scan_precursor_mz",
    "scan_precursor_delta_da",
    "max_scan_precursor_abs_delta_da",
    "rt_seed_min",
    "rt_seed_max",
    "ms1_search_rt_min",
    "ms1_search_rt_max",
    "ms1_seed_delta_min",
    "ms1_peak_rt_start",
    "ms1_peak_rt_end",
    "ms1_height",
    "ms1_scan_support_score",
}

_ALLOWED_PRECURSOR_MZ_BASIS = {
    "scan_precursor",
    "product_plus_neutral_loss",
    "mixed",
}
_ALLOWED_NEUTRAL_LOSS_ERROR_BASIS = {
    "measured_scan_precursor_product",
    "configured_loss_inferred_precursor",
    "mixed",
}
_ROW_ID_MZ_TOLERANCE_DA = 0.001
_ROW_ID_PATTERN = re.compile(
    r"^(?P<sample>.+)#(?P<scan>\d+)@mz(?P<precursor>\d+(?:\.\d+)?)"
    r"_p(?P<product>\d+(?:\.\d+)?)$",
)


@dataclass(frozen=True)
class DiscoveryBatchInput:
    sample_order: tuple[str, ...]
    candidate_csvs: dict[str, Path]
    raw_files: dict[str, Path | None]
    review_csvs: dict[str, Path | None]


@dataclass(frozen=True)
class _CandidateRowIdentity:
    sample_stem: str
    scan_id: int
    precursor_mz: float
    product_mz: float


def read_discovery_batch_index(path: Path) -> DiscoveryBatchInput:
    rows, fieldnames = _read_csv_rows(path)
    _require_columns(path, fieldnames, _BATCH_REQUIRED_COLUMNS)

    sample_order: list[str] = []
    candidate_csvs: dict[str, Path] = {}
    raw_files: dict[str, Path | None] = {}
    review_csvs: dict[str, Path | None] = {}
    for row_number, row in rows:
        sample_stem = _machine_text(row.get("sample_stem", ""))
        candidate_csv = _machine_text(row.get("candidate_csv", ""))
        raw_file = _machine_text(row.get("raw_file", ""))
        review_csv = _machine_text(row.get("review_csv", ""))
        if not sample_stem:
            raise ValueError(f"{path}: row {row_number}: sample_stem is required")
        if not candidate_csv:
            raise ValueError(f"{path}: row {row_number}: candidate_csv is required")
        sample_order.append(sample_stem)
        candidate_csvs[sample_stem] = _resolve_artifact_path(path.parent, candidate_csv)
        raw_files[sample_stem] = Path(raw_file) if raw_file else None
        review_csvs[sample_stem] = (
            _resolve_artifact_path(path.parent, review_csv) if review_csv else None
        )
    return DiscoveryBatchInput(
        sample_order=tuple(sample_order),
        candidate_csvs=candidate_csvs,
        raw_files=raw_files,
        review_csvs=review_csvs,
    )


def read_discovery_candidates_csv(path: Path) -> tuple[DiscoveryCandidate, ...]:
    rows, fieldnames = _read_csv_rows(path)
    _require_columns(path, fieldnames, DISCOVERY_CANDIDATE_COLUMNS)

    candidates: list[DiscoveryCandidate] = []
    seen_candidate_ids: dict[str, int] = {}
    for row_number, row in rows:
        candidate = _parse_candidate_row(path, row_number, row)
        previous_row = seen_candidate_ids.get(candidate.candidate_id)
        if previous_row is not None:
            raise ValueError(
                f"{path}: row {row_number}: duplicate candidate_id "
                f"{candidate.candidate_id!r}; first seen at row {previous_row}"
            )
        seen_candidate_ids[candidate.candidate_id] = row_number
        candidates.append(candidate)
    return tuple(candidates)


def _read_csv_rows(
    path: Path,
) -> tuple[list[tuple[int, dict[str, str]]], tuple[str, ...]]:
    try:
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            fieldnames = tuple(reader.fieldnames or ())
            return (
                [(index, row) for index, row in enumerate(reader, start=2)],
                fieldnames,
            )
    except OSError as exc:
        raise ValueError(f"{path}: CSV file could not be read: {exc}") from exc


def _require_columns(
    path: Path,
    fieldnames: tuple[str, ...],
    required_columns: tuple[str, ...],
) -> None:
    missing = [column for column in required_columns if column not in fieldnames]
    if missing:
        joined = ", ".join(missing)
        raise ValueError(f"{path}: missing required columns: {joined}")


def _parse_candidate_row(
    path: Path,
    row_number: int,
    row: dict[str, str],
) -> DiscoveryCandidate:
    candidate_id = _machine_field(row, "candidate_id")
    row_identity = _parse_row_identity_candidate_id(path, row_number, candidate_id)
    precursor_mz = _parse_float(path, row_number, row, "precursor_mz")
    product_mz = _parse_float(path, row_number, row, "product_mz")
    sample_stem = _machine_field(row, "sample_stem")
    best_ms2_scan_id = _parse_int(path, row_number, row, "best_ms2_scan_id")
    _require_candidate_id_matches_row(
        path,
        row_number,
        candidate_id,
        row_identity,
        sample_stem=sample_stem,
        best_ms2_scan_id=best_ms2_scan_id,
        precursor_mz=precursor_mz,
        product_mz=product_mz,
    )
    return DiscoveryCandidate(
        review_priority=_required_text(path, row_number, row, "review_priority"),  # type: ignore[arg-type]
        evidence_tier=_required_text(path, row_number, row, "evidence_tier"),
        evidence_score=_parse_int(path, row_number, row, "evidence_score"),
        ms2_support=_required_text(path, row_number, row, "ms2_support"),
        ms1_support=_required_text(path, row_number, row, "ms1_support"),
        rt_alignment=_required_text(path, row_number, row, "rt_alignment"),
        family_context=_required_text(path, row_number, row, "family_context"),
        candidate_id=candidate_id,
        feature_family_id=_machine_field(row, "feature_family_id"),
        feature_family_size=_parse_int(path, row_number, row, "feature_family_size"),
        feature_superfamily_id=_machine_field(row, "feature_superfamily_id"),
        feature_superfamily_size=_parse_int(
            path, row_number, row, "feature_superfamily_size"
        ),
        feature_superfamily_role=_required_text(
            path, row_number, row, "feature_superfamily_role"
        ),
        feature_superfamily_confidence=_required_text(
            path, row_number, row, "feature_superfamily_confidence"
        ),
        feature_superfamily_evidence=_required_text(
            path, row_number, row, "feature_superfamily_evidence"
        ),
        precursor_mz=precursor_mz,
        product_mz=product_mz,
        observed_neutral_loss_da=_parse_float(
            path, row_number, row, "observed_neutral_loss_da"
        ),
        best_seed_rt=_parse_float(path, row_number, row, "best_seed_rt"),
        seed_event_count=_parse_int(path, row_number, row, "seed_event_count"),
        ms1_peak_found=_parse_bool(path, row_number, row, "ms1_peak_found"),
        ms1_apex_rt=_parse_optional_float(path, row_number, row, "ms1_apex_rt"),
        ms1_area=_parse_optional_float(path, row_number, row, "ms1_area"),
        ms2_product_max_intensity=_parse_float(
            path, row_number, row, "ms2_product_max_intensity"
        ),
        reason=_required_text(path, row_number, row, "reason"),
        raw_file=Path(_machine_field(row, "raw_file")),
        sample_stem=sample_stem,
        best_ms2_scan_id=best_ms2_scan_id,
        seed_scan_ids=_parse_int_tuple(path, row_number, row, "seed_scan_ids"),
        neutral_loss_tag=_required_text(path, row_number, row, "neutral_loss_tag"),
        configured_neutral_loss_da=_parse_float(
            path, row_number, row, "configured_neutral_loss_da"
        ),
        neutral_loss_mass_error_ppm=_parse_float(
            path, row_number, row, "neutral_loss_mass_error_ppm"
        ),
        neutral_loss_error_basis=_parse_neutral_loss_error_basis(
            path, row_number, row
        ),
        precursor_mz_basis=_parse_precursor_mz_basis(path, row_number, row),
        scan_precursor_mz=_parse_optional_float(
            path, row_number, row, "scan_precursor_mz"
        ),
        scan_precursor_delta_da=_parse_optional_float(
            path, row_number, row, "scan_precursor_delta_da"
        ),
        max_scan_precursor_abs_delta_da=_parse_optional_float(
            path, row_number, row, "max_scan_precursor_abs_delta_da"
        ),
        rt_seed_min=_parse_float(path, row_number, row, "rt_seed_min"),
        rt_seed_max=_parse_float(path, row_number, row, "rt_seed_max"),
        ms1_search_rt_min=_parse_float(path, row_number, row, "ms1_search_rt_min"),
        ms1_search_rt_max=_parse_float(path, row_number, row, "ms1_search_rt_max"),
        ms1_seed_delta_min=_parse_optional_float(
            path, row_number, row, "ms1_seed_delta_min"
        ),
        ms1_peak_rt_start=_parse_optional_float(
            path, row_number, row, "ms1_peak_rt_start"
        ),
        ms1_peak_rt_end=_parse_optional_float(
            path, row_number, row, "ms1_peak_rt_end"
        ),
        ms1_height=_parse_optional_float(path, row_number, row, "ms1_height"),
        ms1_trace_quality=_required_text(path, row_number, row, "ms1_trace_quality"),
        ms1_scan_support_score=_parse_optional_float(
            path, row_number, row, "ms1_scan_support_score"
        ),
        selected_tag_count=_parse_int(path, row_number, row, "selected_tag_count"),
        matched_tag_count=_parse_int(path, row_number, row, "matched_tag_count"),
        matched_tag_names=_parse_text_tuple(row, "matched_tag_names"),
        primary_tag_name=_required_text(path, row_number, row, "primary_tag_name"),
        tag_combine_mode=_required_text(path, row_number, row, "tag_combine_mode"),  # type: ignore[arg-type]
        tag_intersection_status=_required_text(  # type: ignore[arg-type]
            path, row_number, row, "tag_intersection_status"
        ),
        tag_evidence_json=_required_text(path, row_number, row, "tag_evidence_json"),
    )


def _resolve_artifact_path(parent: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else parent / path


def _machine_field(row: dict[str, str], column: str) -> str:
    value = row.get(column, "")
    if column in _CANDIDATE_UNESCAPE_FIELDS or column in _BATCH_UNESCAPE_FIELDS:
        return _machine_text(value)
    return value


def _machine_text(value: str) -> str:
    if len(value) >= 2 and value[0] == "'" and value[1] in ("=", "+", "-", "@"):
        return value[1:]
    return value


def _parse_row_identity_candidate_id(
    path: Path,
    row_number: int,
    candidate_id: str,
) -> _CandidateRowIdentity:
    match = _ROW_ID_PATTERN.match(candidate_id)
    if match is None:
        raise ValueError(
            f"{path}: row {row_number}: candidate_id must include row identity "
            "suffix '<sample>#<scan>@mz<precursor>_p<product>'; stale "
            "'<sample>#<scan>' discovery artifacts must be regenerated"
        )
    return _CandidateRowIdentity(
        sample_stem=match.group("sample"),
        scan_id=int(match.group("scan")),
        precursor_mz=float(match.group("precursor")),
        product_mz=float(match.group("product")),
    )


def _require_candidate_id_matches_row(
    path: Path,
    row_number: int,
    candidate_id: str,
    row_identity: _CandidateRowIdentity,
    *,
    sample_stem: str,
    best_ms2_scan_id: int,
    precursor_mz: float,
    product_mz: float,
) -> None:
    if row_identity.sample_stem != sample_stem:
        raise ValueError(
            f"{path}: row {row_number}: candidate_id sample stem does not match "
            f"sample_stem for {candidate_id!r}"
        )
    if row_identity.scan_id != best_ms2_scan_id:
        raise ValueError(
            f"{path}: row {row_number}: candidate_id scan id does not match "
            f"best_ms2_scan_id for {candidate_id!r}"
        )
    _require_candidate_id_mz_matches_row(
        path,
        row_number,
        candidate_id,
        column="precursor_mz",
        id_value=row_identity.precursor_mz,
        row_value=precursor_mz,
    )
    _require_candidate_id_mz_matches_row(
        path,
        row_number,
        candidate_id,
        column="product_mz",
        id_value=row_identity.product_mz,
        row_value=product_mz,
    )


def _require_candidate_id_mz_matches_row(
    path: Path,
    row_number: int,
    candidate_id: str,
    *,
    column: str,
    id_value: float,
    row_value: float,
) -> None:
    if abs(id_value - row_value) <= _ROW_ID_MZ_TOLERANCE_DA:
        return
    raise ValueError(
        f"{path}: row {row_number}: candidate_id {column} does not match "
        f"{column} for {candidate_id!r}: id={id_value:g}, row={row_value:g}"
    )


def _parse_neutral_loss_error_basis(
    path: Path,
    row_number: int,
    row: dict[str, str],
) -> NeutralLossErrorBasis:
    value = _required_text(path, row_number, row, "neutral_loss_error_basis")
    if value not in _ALLOWED_NEUTRAL_LOSS_ERROR_BASIS:
        allowed = ", ".join(sorted(_ALLOWED_NEUTRAL_LOSS_ERROR_BASIS))
        raise ValueError(
            f"{path}: row {row_number}: neutral_loss_error_basis must be one "
            f"of {allowed}: {value!r}"
        )
    return cast(NeutralLossErrorBasis, value)


def _parse_precursor_mz_basis(
    path: Path,
    row_number: int,
    row: dict[str, str],
) -> GroupPrecursorMzBasis:
    value = _required_text(path, row_number, row, "precursor_mz_basis")
    if value not in _ALLOWED_PRECURSOR_MZ_BASIS:
        allowed = ", ".join(sorted(_ALLOWED_PRECURSOR_MZ_BASIS))
        raise ValueError(
            f"{path}: row {row_number}: precursor_mz_basis must be one of "
            f"{allowed}: {value!r}"
        )
    return cast(GroupPrecursorMzBasis, value)


def _required_text(
    path: Path,
    row_number: int,
    row: dict[str, str],
    column: str,
) -> str:
    value = row.get(column, "")
    if value == "":
        raise ValueError(f"{path}: row {row_number}: {column} is required")
    return value


def _parse_int(path: Path, row_number: int, row: dict[str, str], column: str) -> int:
    value = row.get(column, "")
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(
            f"{path}: row {row_number}: {column} must be an integer: {value!r}"
        ) from exc


def _parse_float(
    path: Path,
    row_number: int,
    row: dict[str, str],
    column: str,
) -> float:
    value = row.get(column, "")
    try:
        return float(value)
    except ValueError as exc:
        raise ValueError(
            f"{path}: row {row_number}: {column} must be a float: {value!r}"
        ) from exc


def _parse_optional_float(
    path: Path,
    row_number: int,
    row: dict[str, str],
    column: str,
) -> float | None:
    value = row.get(column, "")
    if value == "":
        return None
    return _parse_float(path, row_number, row, column)


def _parse_bool(path: Path, row_number: int, row: dict[str, str], column: str) -> bool:
    value = row.get(column, "")
    if value == "TRUE":
        return True
    if value == "FALSE":
        return False
    raise ValueError(
        f"{path}: row {row_number}: {column} must be TRUE or FALSE: {value!r}"
    )


def _parse_int_tuple(
    path: Path,
    row_number: int,
    row: dict[str, str],
    column: str,
) -> tuple[int, ...]:
    value = row.get(column, "")
    if value == "":
        return ()
    try:
        return tuple(int(item) for item in value.split(";") if item)
    except ValueError as exc:
        raise ValueError(
            f"{path}: row {row_number}: {column} must be semicolon-separated integers"
        ) from exc


def _parse_text_tuple(row: dict[str, str], column: str) -> tuple[str, ...]:
    value = row.get(column, "")
    if value == "":
        return ()
    return tuple(item for item in value.split(";") if item)
