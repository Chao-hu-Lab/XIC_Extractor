"""Input loading helpers for the alignment decision diagnostic report."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class TsvTable:
    fieldnames: tuple[str, ...]
    rows: tuple[dict[str, str], ...]


def read_tsv(path: Path, *, required_columns: tuple[str, ...]) -> TsvTable:
    try:
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle, delimiter="\t")
            fieldnames = tuple(reader.fieldnames or ())
            missing = tuple(
                column for column in required_columns if column not in fieldnames
            )
            if missing:
                raise ValueError(
                    f"{path}: missing required columns: {', '.join(missing)}"
                )
            return TsvTable(
                fieldnames=fieldnames,
                rows=tuple(dict(row) for row in reader),
            )
    except OSError as exc:
        raise ValueError(f"{path}: could not read TSV: {exc}") from exc


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: JSON root must be an object")
    return payload
