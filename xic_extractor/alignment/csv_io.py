from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from xic_extractor.discovery.models import (
    DISCOVERY_CANDIDATE_COLUMNS,
    DiscoveryCandidate,
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


@dataclass(frozen=True)
class DiscoveryBatchInput:
    sample_order: tuple[str, ...]
    candidate_csvs: dict[str, Path]
    raw_files: dict[str, Path | None]
    review_csvs: dict[str, Path | None]


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
    for row_number, row in rows:
        candidates.append(_parse_candidate_row(path, row_number, row))
    return tuple(candidates)


def _read_csv_rows(
    path: Path,
) -> tuple[list[tuple[int, dict[str, str]]], tuple[str, ...]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fieldnames = tuple(reader.fieldnames or ())
        return [(index, row) for index, row in enumerate(reader, start=2)], fieldnames


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
    return DiscoveryCandidate(
        review_priority=_required_text(path, row_number, row, "review_priority"),  # type: ignore[arg-type]
        evidence_tier=_required_text(path, row_number, row, "evidence_tier"),
        evidence_score=_parse_int(path, row_number, row, "evidence_score"),
        ms2_support=_required_text(path, row_number, row, "ms2_support"),
        ms1_support=_required_text(path, row_number, row, "ms1_support"),
        rt_alignment=_required_text(path, row_number, row, "rt_alignment"),
        family_context=_required_text(path, row_number, row, "family_context"),
        candidate_id=_machine_field(row, "candidate_id"),
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
        precursor_mz=_parse_float(path, row_number, row, "precursor_mz"),
        product_mz=_parse_float(path, row_number, row, "product_mz"),
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
        sample_stem=_machine_field(row, "sample_stem"),
        best_ms2_scan_id=_parse_int(path, row_number, row, "best_ms2_scan_id"),
        seed_scan_ids=_parse_int_tuple(path, row_number, row, "seed_scan_ids"),
        neutral_loss_tag=_required_text(path, row_number, row, "neutral_loss_tag"),
        configured_neutral_loss_da=_parse_float(
            path, row_number, row, "configured_neutral_loss_da"
        ),
        neutral_loss_mass_error_ppm=_parse_float(
            path, row_number, row, "neutral_loss_mass_error_ppm"
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
