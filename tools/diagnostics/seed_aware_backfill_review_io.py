"""Input loading helpers for seed-aware backfill review diagnostics."""

from __future__ import annotations

import csv
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path


def _group_by_family(
    rows: Iterable[Mapping[str, str]],
) -> dict[str, tuple[Mapping[str, str], ...]]:
    grouped: dict[str, list[Mapping[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[row["feature_family_id"]].append(row)
    return {key: tuple(value) for key, value in grouped.items()}


def _read_tsv(path: Path, *, required_columns: Sequence[str]) -> list[dict[str, str]]:
    if not path.is_file():
        raise ValueError(f"Required TSV not found: {path}")
    with path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        fields = reader.fieldnames or ()
        missing = [column for column in required_columns if column not in fields]
        if missing:
            raise ValueError(f"{path} missing required columns: {', '.join(missing)}")
        return list(reader)


def _normalize_paths(path_or_paths: Path | Sequence[Path]) -> tuple[Path, ...]:
    if isinstance(path_or_paths, Path):
        return (path_or_paths,)
    return tuple(path_or_paths)
