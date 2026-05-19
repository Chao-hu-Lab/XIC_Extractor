"""Input loaders for low MS1 coverage review diagnostics."""

from __future__ import annotations

import csv
from collections.abc import Mapping, Sequence
from pathlib import Path

from tools.diagnostics.low_ms1_coverage_review_models import (
    BACKFILL_SEED_AUDIT_REQUIRED_COLUMNS,
    DISCOVERY_REQUIRED_COLUMNS,
)


def _trace_summary_path(candidate: Mapping[str, str], overlay_dir: Path) -> Path:
    prefix = candidate.get("suggested_output_prefix", "")
    if not prefix:
        raise ValueError(
            f"{candidate.get('feature_family_id', '<unknown>')}: "
            "missing suggested_output_prefix",
        )
    return overlay_dir / f"{prefix}_trace_summary.tsv"


def _read_tsv(
    path: Path,
    *,
    required_columns: Sequence[str],
) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        fieldnames = tuple(reader.fieldnames or ())
        missing = [column for column in required_columns if column not in fieldnames]
        if missing:
            raise ValueError(f"{path}: missing required columns: {', '.join(missing)}")
        return [dict(row) for row in reader]


def _read_csv(
    path: Path,
    *,
    required_columns: Sequence[str],
) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fieldnames = tuple(reader.fieldnames or ())
        missing = [column for column in required_columns if column not in fieldnames]
        if missing:
            raise ValueError(f"{path}: missing required columns: {', '.join(missing)}")
        return [dict(row) for row in reader]


def _load_discovery_candidate(
    discovery_dir: Path,
    source_candidate_id: str,
) -> dict[str, str] | None:
    sample_stem = source_candidate_id.split("#", 1)[0]
    path = discovery_dir / sample_stem / "discovery_candidates.csv"
    if not path.exists():
        return None
    rows = _read_csv(path, required_columns=DISCOVERY_REQUIRED_COLUMNS)
    for row in rows:
        if row.get("candidate_id") == source_candidate_id:
            return row
    return None


def _backfill_seed_rows_by_family(
    path: Path | None,
) -> dict[str, tuple[dict[str, str], ...]]:
    if path is None:
        return {}
    rows = _read_tsv(path, required_columns=BACKFILL_SEED_AUDIT_REQUIRED_COLUMNS)
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        grouped.setdefault(row["feature_family_id"], []).append(row)
    return {family_id: tuple(family_rows) for family_id, family_rows in grouped.items()}
