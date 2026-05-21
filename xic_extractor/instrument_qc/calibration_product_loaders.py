from __future__ import annotations

import csv
from pathlib import Path
from typing import Mapping


def read_tsv_rows(path: Path, *, required_columns: set[str]) -> tuple[dict[str, str], ...]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        fieldnames = set(reader.fieldnames or ())
        missing = sorted(required_columns - fieldnames)
        if missing:
            raise ValueError(
                f"{path.name} missing required columns: {', '.join(missing)}"
            )
        return tuple(dict(row) for row in reader)


def parse_optional_float(
    row: Mapping[str, str],
    column: str,
    *,
    path: Path,
    row_number: int,
) -> float | None:
    value = (row.get(column) or "").strip()
    if not value:
        return None
    try:
        return float(value)
    except ValueError as exc:
        raise ValueError(
            f"{path.name} column {column} row {row_number} has invalid numeric "
            f"value: {value!r}"
        ) from exc


def parse_optional_int(
    row: Mapping[str, str],
    column: str,
    *,
    path: Path,
    row_number: int,
) -> int | None:
    value = (row.get(column) or "").strip()
    if not value:
        return None
    try:
        return int(float(value))
    except ValueError as exc:
        raise ValueError(
            f"{path.name} column {column} row {row_number} has invalid integer "
            f"value: {value!r}"
        ) from exc
