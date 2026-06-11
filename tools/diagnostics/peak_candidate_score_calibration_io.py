from __future__ import annotations

import csv
from pathlib import Path

from tools.diagnostics.peak_candidate_score_calibration_models import (
    _REQUIRED_COLUMNS,
    PeakCandidateScoreRow,
    _split_labels,
)


def _read_peak_candidates(path: Path) -> tuple[PeakCandidateScoreRow, ...]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        fieldnames = tuple(reader.fieldnames or ())
        missing = [column for column in _REQUIRED_COLUMNS if column not in fieldnames]
        if missing:
            raise ValueError(f"{path}: missing required columns: {', '.join(missing)}")
        return tuple(
            _row_from_dict(path, row_number, row)
            for row_number, row in enumerate(reader, 2)
        )


def _row_from_dict(
    path: Path,
    row_number: int,
    row: dict[str, str],
) -> PeakCandidateScoreRow:
    return PeakCandidateScoreRow(
        sample_name=row["sample_name"],
        target_label=row["target_label"],
        resolver_mode=row["resolver_mode"],
        candidate_id=row["candidate_id"],
        proposal_sources=row["proposal_sources"],
        rt_apex_min=_optional_float(
            path,
            row_number,
            "rt_apex_min",
            row["rt_apex_min"],
        ),
        selected=_required_bool(path, row_number, "selected", row["selected"]),
        confidence=row["confidence"],
        raw_score=_optional_float(path, row_number, "raw_score", row["raw_score"]),
        support_labels=tuple(_split_labels(row["support_labels"])),
        concern_labels=tuple(_split_labels(row["concern_labels"])),
        cap_labels=tuple(_split_labels(row["cap_labels"])),
        reason=row["reason"],
        rejection_reason=row["rejection_reason"],
        ms2_present=row["ms2_present"],
        nl_match=row["nl_match"],
        ms2_trace_strength=row["ms2_trace_strength"],
    )


def _bool_value(value: str) -> bool | None:
    normalized = value.strip().upper()
    if normalized in {"TRUE", "T", "YES", "Y", "1"}:
        return True
    if normalized in {"FALSE", "F", "NO", "N", "0"}:
        return False
    return None


def _required_bool(
    path: Path,
    row_number: int,
    column: str,
    value: str,
) -> bool:
    parsed = _bool_value(value)
    if parsed is None:
        raise ValueError(f"{path}: row {row_number} invalid {column}: {value!r}")
    return parsed


def _optional_float(
    path: Path,
    row_number: int,
    column: str,
    value: str,
) -> float | None:
    text = value.strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError as exc:
        message = f"{path}: row {row_number} invalid {column}: {value!r}"
        raise ValueError(message) from exc
