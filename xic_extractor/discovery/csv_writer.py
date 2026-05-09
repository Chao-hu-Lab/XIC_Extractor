"""CSV writer for untargeted discovery review candidates."""

import csv
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from xic_extractor.discovery.models import (
    DISCOVERY_CANDIDATE_COLUMNS,
    DiscoveryCandidate,
)

_PRIORITY_RANK = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}


def write_discovery_candidates_csv(
    path: Path, candidates: Iterable[DiscoveryCandidate]
) -> Path:
    """Write review-first discovery candidates to a stable CSV contract."""
    path.parent.mkdir(parents=True, exist_ok=True)
    sorted_candidates = sorted(candidates, key=_candidate_sort_key)

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=DISCOVERY_CANDIDATE_COLUMNS)
        writer.writeheader()
        for candidate in sorted_candidates:
            writer.writerow(_candidate_row(candidate))

    return path


def _candidate_sort_key(candidate: DiscoveryCandidate) -> tuple[Any, ...]:
    area_is_missing = candidate.ms1_area is None
    area_desc = 0.0 if candidate.ms1_area is None else -candidate.ms1_area
    return (
        _PRIORITY_RANK.get(candidate.review_priority, len(_PRIORITY_RANK)),
        -candidate.feature_family_size,
        candidate.feature_family_id,
        -candidate.seed_event_count,
        -candidate.ms2_product_max_intensity,
        area_is_missing,
        area_desc,
        candidate.best_seed_rt,
    )


def _candidate_row(candidate: DiscoveryCandidate) -> dict[str, str]:
    return {
        column: _format_csv_value(column, getattr(candidate, column))
        for column in DISCOVERY_CANDIDATE_COLUMNS
    }


def _format_csv_value(column: str, value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if column == "seed_scan_ids":
        if isinstance(value, str):
            return value
        if isinstance(value, tuple):
            return ";".join(str(scan_id) for scan_id in value)
        return str(value)
    if isinstance(value, Path):
        return _escape_excel_formula(str(value))
    if isinstance(value, float):
        return f"{value:.6g}"
    return _escape_excel_formula(str(value))


def _escape_excel_formula(value: str) -> str:
    if value.startswith(("=", "+", "-", "@")):
        return f"'{value}"
    return value
