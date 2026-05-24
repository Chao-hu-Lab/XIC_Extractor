from __future__ import annotations

import csv
from pathlib import Path

from openpyxl import load_workbook

from tools.diagnostics.cwt_peak_candidate_audit_models import (
    _REQUIRED_COLUMNS,
    CwtCandidateRow,
)


def _read_peak_candidates(path: Path) -> tuple[CwtCandidateRow, ...]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        fieldnames = tuple(reader.fieldnames or ())
        missing = [column for column in _REQUIRED_COLUMNS if column not in fieldnames]
        if missing:
            raise ValueError(f"{path}: missing required columns: {', '.join(missing)}")
        return tuple(
            _row_from_dict(path, index, row) for index, row in enumerate(reader, 2)
        )


def _read_target_mz(path: Path) -> dict[str, float]:
    workbook = load_workbook(path, read_only=True, data_only=True)
    try:
        if "Targets" not in workbook.sheetnames:
            raise ValueError(f"{path}: missing required sheet: Targets")
        rows = workbook["Targets"].iter_rows(values_only=True)
        header = next(rows, None)
        if header is None:
            raise ValueError(f"{path}: Targets sheet is empty")
        indexes = _required_indexes(header, ("Label", "m/z"), "Targets")
        target_mz: dict[str, float] = {}
        for row_number, row in enumerate(rows, 2):
            label = _text(row[indexes["Label"]])
            if not label:
                continue
            target_mz[label] = _float_value(
                path,
                row_number,
                "m/z",
                _text(row[indexes["m/z"]]),
            )
        return target_mz
    finally:
        workbook.close()


def _required_indexes(
    header: object,
    required: tuple[str, ...],
    sheet_name: str,
) -> dict[str, int]:
    if not isinstance(header, tuple):
        raise ValueError(f"{sheet_name}: header row is invalid")
    indexes = {_text(value): index for index, value in enumerate(header)}
    missing = [column for column in required if column not in indexes]
    if missing:
        raise ValueError(
            f"{sheet_name}: missing required columns: {', '.join(missing)}"
        )
    return {column: indexes[column] for column in required}


def _row_from_dict(
    path: Path,
    row_number: int,
    row: dict[str, str],
) -> CwtCandidateRow:
    return CwtCandidateRow(
        sample_name=row["sample_name"],
        target_label=row["target_label"],
        resolver_mode=row["resolver_mode"],
        candidate_id=row["candidate_id"],
        proposal_sources=row["proposal_sources"],
        rt_apex_min=_float_value(path, row_number, "rt_apex_min", row["rt_apex_min"]),
        selected=row["selected"].strip().upper() == "TRUE",
        confidence=row["confidence"],
        raw_score=row["raw_score"],
        reason=row["reason"],
        ms2_present=row.get("ms2_present", ""),
        nl_match=row.get("nl_match", ""),
        ms2_trace_strength=row.get("ms2_trace_strength", ""),
    )


def _float_value(path: Path, row_number: int, column: str, value: str) -> float:
    try:
        return float(value)
    except ValueError as exc:
        message = f"{path}: row {row_number} invalid {column}: {value!r}"
        raise ValueError(message) from exc


def _text(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()
